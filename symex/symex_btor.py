# Implements btor based symbolic execution

import copy
from typing import Callable, Dict, List, Optional, Set, Type

import typer
from typing_extensions import Annotated

from cvc5 import *

from symex.solver import Solver as CSolver
from symex.solver import SolverTerm

from loguru import logger


BtorExprHandler = Callable[
    [Type["BtorPrgm"], Type["BtorState"], Type["BtorState"]], SolverTerm
]


def raise_(ex: Exception):
    """Wrapper to raise an exception."""
    raise ex


def not_implemented(
    op: str,
) -> Callable[[Type["BtorPrgm"], Type["BtorState"], Type["BtorState"]], None]:
    """Return a function that raises a NotImplementedError with the given op."""
    return lambda _p, _s, _sp: raise_(NotImplementedError(op))


class BtorState:
    """
    Represents the state of a btor program.

    Members:
    - varmap: A map from variable names to indices
    - _state: A map from indices to SolverTerms
    """

    def __init__(self):
        self.varmap: Dict[str, int] = dict()
        self.rvarmap: Dict[int, str] = dict()
        self._state: Dict[int, SolverTerm] = dict()
        self.pairmap: Dict[str, List[int]] = dict()

    def update(self, idx: int, value: SolverTerm) -> int:
        self._state[idx] = value
        return idx

    def __getitem__(self, idx: int) -> SolverTerm:
        return self._state[idx]
    
    def name_of(self, idx: int) -> str:
        return self.rvarmap[idx]
    
    def index_of(self, name: str) -> int:
        return self.varmap[name]

    @staticmethod
    def from_prgm(prgm: "BtorPrgm", slv: CSolver) -> Type["BtorState"]:
        state = BtorState()

        for var, init in prgm._make_state.items():
            idx = init(prgm, state)
            state.varmap[var] = idx
            state.rvarmap[idx] = var

        return state


class BtorPrgm:
    """
    Represents a btor program.

    Members:
    - prgm: The program string
    - slv: The solver
    - stmts: A list of statements, where each statement is a function
             that takes a BtorPrgm, a BtorState, and a BtorState and returns a SolverTerm
    - _make_state: A map from name to statement that defines this element
    - assertion: The index of the assertion statement, i.e., 'bad' from a btor program

    Methods:
    - __getitem__: Get a statement by index
    - _make_unique_name: Make a unique name for a state element without a name
    - _do_parse: Parse the program string and populate the stmts list
    - interpret_node_id: Interpret a node id in the context of a state and populate the next state
    """

    def __init__(self, prgm: str, slv: Optional[Type[CSolver]] = None):
        self.prgm: str = prgm
        self.inputs: List[int] = []
        self.nexts: Dict[int, int] = {}

        self.slv = slv
        if self.slv is None:
            self.slv = CSolver()

        self.stmts: List[BtorExprHandler] = ["_"]

        # Map from name to statement that defines this element
        self._make_state: Dict[str, Callable[["BtorPrgm", "BtorState"], int]] = dict()

        # The index of the assertion statement
        self.assertion: int = None

        self.deps: Dict[int, Set[int]] = dict()

        self.template_state = None
        
        self._memo = {}

        self._do_parse(prgm)

    def __getitem__(self, idx: int) -> BtorExprHandler:
        return self.stmts[idx]
    
    def deps_of(self, idx: int) -> Set[int]:
        return self.deps[idx]

    def is_input(self, idx: int) -> bool:
        return idx in self.inputs

    def _make_unique_name(self, idx: int) -> str:
        return f"var_{idx}"

    def _do_parse(self, prgm: str) -> None:
        slv = self.slv

        for line in prgm.split("\n"):
            idx, op, ty, *args = line.split(" ")
            idx = int(idx)

            pfn = None

            self.deps[idx] = set()

            if op == "state" or op == "input":
                ty = int(ty)

                if len(args) > 0:
                    name = args[0]
                else:
                    name = self._make_unique_name(idx)

                assert (
                    name not in self._make_state
                ), f"State element {name} defined twice"

                pfn = lambda _p, s, _sp, idx=idx: s[idx]

                self._make_state[
                    name
                ] = lambda p, s, ty=ty, name=name, idx=idx: s.update(
                    idx, SolverTerm(slv, slv.solver.mkConst(p[ty](p, s, None), name))
                )

                self.deps[idx].add(idx)

                if op == 'input':
                    self.inputs.append(idx)
            elif op == "output":
                ty = int(ty)
                pfn = lambda p, s, sp, ty=ty: p[ty](p, s, sp)
                self.deps[idx] = self.deps[ty]
            elif op == "init":
                raise NotImplementedError("init")
            elif op == "next":
                se = int(args[0])
                eidx = int(args[1])
                pfn = lambda p, s, sp, se=se, eidx=eidx: sp.update(
                    se, p[eidx](p, s, sp)
                )
                self.deps[idx] = self.deps[eidx]
                self.nexts[se] = idx
            elif op == "sort":
                assert ty == "bitvec", f"Unknown sort: {ty}"
                pfn = lambda _p, _s, _sp, args=args: slv.solver.mkBitVectorSort(
                    int(args[0])
                )
            elif op == "bad":
                ty = int(ty)
                self.assertion = idx
                pfn = lambda p, s, sp, ty=ty, idx=idx: sp.update(idx, p[ty](p, s, sp))
                self.deps[idx] = self.deps[ty]
                self.nexts[idx] = idx
                bv1 = slv.solver.mkBitVectorSort(1)
                self._make_state["bad"] = lambda p, s, ty=ty, name=name, idx=idx: s.update(
                    idx, SolverTerm(slv, slv.solver.mkConst(bv1, "bad"))
                )
            elif op in ["const", "constd", "consth"]:
                sid = int(ty)
                value = None
                if op == "const":
                    value = int(args[0], 2)
                elif op == "constd":
                    value = int(args[0])
                elif op == "consth":
                    value = int(args[0], 16)

                pfn = lambda p, s, sp, sid=sid, value=value: SolverTerm(
                    slv,
                    slv.solver.mkBitVector(p[sid](p, s, sp).getBitVectorSize(), value),
                )
            else:
                # Now we deal with SMT operators
                args[0] = int(args[0])
                if len(args) > 1:
                    args[1] = int(args[1])

                if op == "sext":
                    pfn = lambda p, s, sp, args=args: p[args[0]](
                        p, s, sp
                    ).sign_extend_d(int(args[1]))
                    self.deps[idx] = self.deps[args[0]]
                elif op == "uext":
                    pfn = lambda p, s, sp, args=args: p[args[0]](
                        p, s, sp
                    ).zero_extend_d(int(args[1]))
                    self.deps[idx] = self.deps[args[0]]
                elif op == "slice":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp)[
                        int(args[1]) : int(args[2])
                    ]
                    self.deps[idx] = self.deps[args[0]]
                elif op == "not":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).bvnot()
                    self.deps[idx] = self.deps[args[0]]
                elif op == "inc":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) + 1
                    self.deps[idx] = self.deps[args[0]]
                elif op == "dec":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) - 1
                    self.deps[idx] = self.deps[args[0]]
                elif op == "neg":
                    pfn = lambda p, s, sp, args=args: ~p[args[0]](p, s, sp)
                    self.deps[idx] = self.deps[args[0]]
                elif op == "redor":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) != 0
                    self.deps[idx] = self.deps[args[0]]
                elif op == "redxor":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).redxor()
                    self.deps[idx] = self.deps[args[0]]
                elif op == "redand":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).bvnot() == 0
                    self.deps[idx] = self.deps[args[0]]
                elif op == "iff":
                    logger.warning("iff not implemented")
                    pfn = not_implemented("iff")
                elif op == "implies":
                    logger.warning("implies not implemented")
                    pfn = not_implemented("implies")
                elif op == "eq":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) == p[
                        args[1]
                    ](p, s, sp)
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "neq":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) != p[
                        args[1]
                    ](p, s, sp)
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "sgt":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).sgt(
                        p[args[1]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "ugt":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) > p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "sgte":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).sge(
                        p[args[1]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "ugte":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) >= p[
                        args[1]
                    ](p, s, sp)
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "slt":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).slt(
                        p[args[1]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "ult":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) < p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "slte":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).sle(
                        p[args[1]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "ulte":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) <= p[
                        args[1]
                    ](p, s, sp)
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "and":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) & p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "nand":
                    pfn = lambda p, s, sp, args=args: (
                        p[args[0]](p, s, sp) & p[args[1]](p, s, sp)
                    ).bvnot()
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "or":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) | p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "nor":
                    pfn = lambda p, s, sp, args=args: (
                        p[args[0]](p, s, sp) | p[args[1]](p, s, sp)
                    ).bvnot()
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "xor":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) ^ p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "xnor":
                    pfn = lambda p, s, sp, args=args: (
                        p[args[0]](p, s, sp) ^ p[args[1]](p, s, sp)
                    ).bvnot()
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "rol":
                    logger.warning("rol not implemented")
                    pfn = not_implemented("rol")
                elif op == "ror":
                    logger.warning("ror not implemented")
                    pfn = not_implemented("ror")
                elif op == "sll":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) << p[
                        args[1]
                    ](p, s, sp)
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "srl":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).lshr(
                        p[args[1]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "sra":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) >> p[
                        args[1]
                    ](p, s, sp)
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "add":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) + p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "sub":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) - p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "mul":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) * p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "udiv":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) / p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "sdiv":
                    # XXX
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) / p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "urem":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) % p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "srem":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).srem(
                        p[args[1]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "smod":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp) % p[args[1]](
                        p, s, sp
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "saddo":
                    logger.warning("saddo not implemented")
                    pfn = not_implemented("saddo")
                elif op == "uaddo":
                    logger.warning("uaddo not implemented")
                    pfn = not_implemented("uaddo")
                elif op == "ssubo":
                    logger.warning("ssubo not implemented")
                    pfn = not_implemented("ssubo")
                elif op == "usubo":
                    logger.warning("usubo not implemented")
                    pfn = not_implemented("usubo")
                elif op == "smulo":
                    logger.warning("smulo not implemented")
                    pfn = not_implemented("smulo")
                elif op == "umulo":
                    logger.warning("umulo not implemented")
                    pfn = not_implemented("umulo")
                elif op == "sdivo":
                    logger.warning("sdivo not implemented")
                    pfn = not_implemented("sdivo")
                elif op == "concat":
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).append(
                        p[args[1]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]])
                elif op == "read":
                    logger.warning("read not implemented")
                    pfn = not_implemented("read")
                elif op == "ite":
                    args[2] = int(args[2])
                    pfn = lambda p, s, sp, args=args: p[args[0]](p, s, sp).ite(
                        p[args[1]](p, s, sp), p[args[2]](p, s, sp)
                    )
                    self.deps[idx] = self.deps[args[0]].union(self.deps[args[1]]).union(self.deps[args[2]])
                elif op == "write":
                    logger.warning("write not implemented")
                    pfn = not_implemented("write")
                else:
                    raise NotImplementedError(f"Unknown op: {op}")

            self.stmts.append(pfn)

    def interpret_node_id(
        self, idx: int, state: BtorState, next_state: Optional[BtorState] = None
    ) -> SolverTerm:
        if next_state is None:
            next_state = BtorState()
            next_state.varmap = state.varmap

        return self.stmts[idx](self, state, next_state)
    
    def next(self, state: BtorState) -> BtorState:
        next_state = self.blank_state()

        for _, idx in self.nexts.items():
            logger.debug(f"Interpreting node {idx}")
            self.interpret_node_id(idx, state, next_state)

        # if self.assertion:
            # self.interpret_node_id(self.assertion, state, next_state)

        return next_state

    def next_of_idx(self, idx: int) -> int:
        return self.nexts[idx]
    
    def init_state(self) -> BtorState:
        if self.template_state:
            state = copy.deepcopy(self.template_state)
        else:
            state = BtorState()

        for var, init in self._make_state.items():
            idx = init(self, state)

            if self.template_state:
                continue
                
            # Build the state from scratch so that we can save it as a template for later use.
            state.varmap[var] = idx
            state.rvarmap[idx] = var

            if var.startswith("gate.") or var.startswith("gold."):
                prefix, basename = var.split(".", 1)

                if basename not in state.pairmap:
                    state.pairmap[basename] = [None, None]

                if prefix == "gate":
                    state.pairmap[basename][0] = idx
                else:
                    state.pairmap[basename][1] = idx
            else:
                state.pairmap[var] = [idx, idx]
            
        if not self.template_state:
            self.template_state = BtorState()
            self.template_state.varmap = state.varmap
            self.template_state.rvarmap = state.rvarmap
            self.template_state.pairmap = state.pairmap

        # if self.assertion:
        #     next = self.blank_state()
        #     _ = self.interpret_node_id(self.assertion, state, next)
        #     state._state[self.assertion] = next._state[self.assertion]

        return state

    def blank_state(self) -> BtorState:
        if self.template_state:
            return copy.deepcopy(self.template_state)
        
        _ = self.init_state()
        return copy.deepcopy(self.template_state)
    

    def check_invariant(self, invar: "Invariant") -> bool: # type: ignore
        state = self.init_state()
        indicies = set()

        for pred in invar:
            self.slv.add_assertion(pred.to_smt(state))
            indicies.add(pred.lvar)
            try:
                if pred.rvar:
                    indicies.add(pred.rvar)
            except:
                pass


        # Take a step and check self.assertion
        next_state = self.blank_state()
        for idx in indicies:
            if self.is_input(idx):
                next_state.update(idx, state[idx])
                continue
            next_of = self.next_of_idx(idx)
            self.interpret_node_id(next_of, state, next_state)

        logger.success("Done creating step")

        for pred in invar:
            self.slv.add_assertion(pred.to_smt(next_state).bnot())

        logger.success("Checking invariant")

        if not self.slv.is_unsat():
            raise AssertionError("Invariant violated!")
        else:
            logger.success("Invariant holds")
            return True


app = typer.Typer()


@app.command()
def symex(
    btor: Annotated[str, typer.Argument(help="Btor file to be verified")],
):
    with open(btor, "r") as f:
        prgm = f.read()

    btor_prgm = BtorPrgm(prgm)

    state = btor_prgm.init_state()

    print(btor_prgm.interpret_node_id(btor_prgm.assertion, state))
    print([state.name_of(x) for x in btor_prgm.deps_of(btor_prgm.assertion)])


if __name__ == "__main__":
    app()
