"""
Implements classes to represent predicates for invariant learning
"""


import functools
from typing import Dict, List, Optional, Type, Union
import cvc5

from cvc5 import Kind
from symex.solver import SolverTerm

from symex.symex_btor import BtorState


class Predicate:
    """
    Abstract class that represents a predicate
    """
    def __init__(self):
        pass

    def to_smt(self, state: Type[BtorState]) -> Type[cvc5.Term]:
        """
        Convert the predicate to an SMT term

        :param solver: Solver object
        :return: SMT term
        """
        raise NotImplementedError

    def assert_smt(self, state: Type[BtorState]):
        """
        Assert the predicate in the given state

        :param state: State object
        """
        state._solver.add(self.to_smt(state))

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        raise NotImplementedError
    
    def eval(self, state: Type[BtorState]) -> bool:
        raise NotImplementedError
            
    @classmethod
    def from_smt(cls, smt: Type[cvc5.Term], state: BtorState) -> Type[Union['Predicate', str, int]]:
        kind = smt.getKind()

        if kind == Kind.CONSTANT:
            name = smt.getSymbol()
            # Names are of the format <var>@<cycle>-<side>$<uid>
            name = name.split("@", 1)[0]
            idx = state.index_of(name)
            return idx
        elif kind == Kind.CONST_BITVECTOR:
            return int(smt.getBitVectorValue(), 2)
        elif kind == Kind.AND:
            return AndPred([Predicate.from_smt(smt[i], state) for i in range(smt.getNumChildren())])
        elif kind == Kind.EQUAL:
            lvar = Predicate.from_smt(smt[0], state)
            rvar = Predicate.from_smt(smt[1], state)
            
            return EqPred(lvar, rvar)
        elif kind == Kind.NOT:
            child = smt[0]

            assert child.getKind() == Kind.EQUAL, f"Unknown kind: {child.getKind()}"

            lvar = Predicate.from_smt(child[0], state)
            rval = Predicate.from_smt(child[1], state)

            if isinstance(rval, int):
                return NEqPred(lvar, rval)
            else:
                return NEqPred(lvar, rval)
        elif kind == Kind.BITVECTOR_NOT:
            child = smt[0]

            assert child.getKind() == Kind.BITVECTOR_COMP, f"Unknown kind: {child.getKind()}"

            lvar = Predicate.from_smt(child[0], state)
            rval = Predicate.from_smt(child[1], state)

            if isinstance(rval, int):
                return NEqPred(lvar, rval)
            else:
                assert lvar == rval
                return NEqPred(lvar, rval)
        elif kind == Kind.IMPLIES:
            lhs = Predicate.from_smt(smt[0], state)
            rhs = Predicate.from_smt(smt[1], state)

            return PImplPred(lhs, rhs)
        else:
            raise NotImplementedError(f"Unknown kind: {kind}")
        
    def __hash__(self) -> int:
        return hash(self.__repr__())


class EqPred(Predicate):
    def __init__(self, lvar: int, rvar: Optional[int]=None):
        self.lvar = lvar
        self.rvar = rvar

    @property
    def var_L(self) -> int:
        return self.lvar
    
    @property
    def var_R(self) -> int:
        return self.rvar

    def get_vars(self):
        if self.rvar:
            return [self.lvar, self.rvar]
        return [self.lvar]

    def to_smt(self, state: Type[BtorState]) -> SolverTerm:
        if self.rvar:
            return state[self.lvar].beq(state[self.rvar])
        else:
            expr = state[self.lvar]
            # assert expr.var.getKind() == Kind.EQUAL, f"Unknown kind: {expr.var.getKind()}"
            return expr.beq(1)
    
    def eval(self, model: Dict[int, int]) -> bool:
        if not (self.var_L in model and self.var_R in model):
            return False
        
        return model[self.var_L] == model[self.var_R]

    def __repr__(self):
        return f"{self.var_L} == {self.var_R}"

    def pretty_print(self, state: BtorState):
        if self.rvar:
            return f"({state.name_of(self.var_L)} == {state.name_of(self.var_R)})"
        else:
            return f"Eq({state.name_of(self.var_L)})"
        

class EqPredConst(Predicate):
    def __init__(self, lvar: int, val: int):
        self.lvar = lvar
        self.val = val

    @property
    def var_L(self) -> int:
        return self.lvar
    
    @property
    def var_R(self) -> int:
        return self.val

    def get_vars(self):
        return [self.lvar]

    def to_smt(self, state: Type[BtorState]) -> SolverTerm:
        left_term = state[self.lvar]
        solver = left_term._solver
        bw = len(left_term)
        return state[self.lvar].beq(solver.bvv(self.val, bw))
    
    def eval(self, model: Dict[int, int]) -> bool:
        if not (self.var_L in model):
            return False
        
        return model[self.var_L] == self.var_R

    def __repr__(self):
        return f"{self.var_L} := {self.var_R}"
    
    def pretty_print(self, state: BtorState):
        return f"({state.name_of(self.var_L)} == {self.var_R})"


class PImplPred(Predicate):
    def __init__(self, lhs: Type[Predicate], rhs: Type[Predicate]):
        self.lhs = lhs
        self.rhs = rhs

    def get_vars(self):
        return self.rhs.get_vars()

    def to_smt(self, state) -> SolverTerm:
        lhs = self.lhs.to_smt(state).bnot()
        slv = lhs._solver.solver
        return SolverTerm(lhs._solver,
            slv.mkTerm(
                Kind.OR,
                lhs.var,
                self.rhs.to_smt(state).var
            ))
        # return self.lhs.to_smt(state).implies(self.rhs.to_smt(state))
    
    def eval(self, model: Dict[str, int]) -> bool:
        lhs_e = self.lhs.eval(model)
        rhs_e = self.rhs.eval(model)

        if rhs_e:
            return True
        else:
            return not lhs_e

    def __repr__(self):
        return f"impl_{self.lhs.lvar}_{self.rhs.lvar}_{self.rhs.val},{self.rhs.mask}"
    
    def pretty_print(self, state: BtorState):
        return f"({self.lhs.pretty_print(state)} => {self.rhs.pretty_print(state)})"
    

class SynthesizablePImplPred(Predicate):
    def __init__(self, lhs: "NEqPred", rhs: SolverTerm, synth_fn_apply: cvc5.Term, masking_fn: cvc5.Term):
        self.lhs = lhs
        self.rhs = rhs
        self.synth_fn_apply = synth_fn_apply
        self.masking_fn = masking_fn

    def get_vars(self):
        raise NotImplementedError
    
    def eval(self, model: Dict[str, int]) -> bool:
        raise NotImplementedError
    
    def pretty_print(self, state: BtorState):
        raise NotImplementedError
    
    def to_smt(self, state: BtorState) -> SolverTerm:
        rhs_eq = self.rhs.to_smt(state)
        rhs_lvar = state[self.rhs.lvar]
        slv = rhs_eq._solver.solver

        # (lhs is equal) OR ((rhs AND <mask>) != <const>)
        return SolverTerm(rhs_eq._solver,
            slv.mkTerm(
                Kind.OR,
                slv.mkTerm(Kind.NOT, self.lhs.to_smt(state).var),
                slv.mkTerm(
                    Kind.NOT,
                    slv.mkTerm(Kind.EQUAL, 
                               slv.mkTerm(Kind.BITVECTOR_AND, rhs_lvar.var, self.masking_fn),
                               self.synth_fn_apply)),
            ))
    
    def concretize(self, value: int, mask: int) -> PImplPred:
        return PImplPred(self.lhs, NEqPred(self.rhs.lvar, value=value, mask=mask))



class NEqPred(Predicate):
    def __init__(self, lvar: int, rvar: Optional[int] = None, value: Optional[cvc5.Term] = None, mask: Optional[cvc5.Term] = None):
        self.lvar = lvar
        self.rvar = rvar
        self.val = value
        self.mask = mask

    @property
    def var_L(self) -> int:
        return self.lvar
    
    @property
    def var_R(self) -> Optional[int]:
        return self.rvar
    
    def get_vars(self):
        if self.val is not None:
            return [self.lvar]
        return [self.lvar, self.rvar]

    def to_smt(self, state: Type[BtorState]) -> SolverTerm:
        if self.val is None:
            return state[self.lvar].beq(state[self.rvar]).bnot()
        else:
            vl = state[self.lvar]
            sort = vl.var.getSort()
            slv = vl._solver.solver
            expr = vl.var
            if self.mask:
                expr = slv.mkTerm(Kind.BITVECTOR_AND, expr, slv.mkBitVector(sort.getBitVectorSize(), self.mask))
            return SolverTerm(
                vl._solver,
                slv.mkTerm(Kind.NOT, slv.mkTerm(Kind.EQUAL, expr, slv.mkBitVector(sort.getBitVectorSize(), self.val)))
            )
        
    def eval(self, model: Dict[str, int]) -> bool:
        if not self.val:
            if not (self.var_L in model and self.var_R in model):
                return True
            return model[self.var_L] != model[self.var_R]
        else:
            if not (self.var_L in model):
                return True
            return model[self.var_L] != self.val

    def __repr__(self):
        if self.val is None:
            return f"{self.var_L} != {self.var_R}"
        else:
            return f"{self.var_L} != {self.val}"
        
    def pretty_print(self, state: BtorState):
        if self.val is None:
            return f"({state.name_of(self.var_L)} != {state.name_of(self.var_R)})"
        else:
            return f"({state.name_of(self.var_L)} != {self.val})"


class IsSafeInstrPred(Predicate):
    INST_SPEC = None
    SAFE_SET = None

    def __init__(self, lvar: int):
        # print("IsSafeInstrPred", IsSafeInstrPred.INST_SPEC, IsSafeInstrPred.SAFE_SET)
        is_initialized = IsSafeInstrPred.INST_SPEC is not None and IsSafeInstrPred.SAFE_SET is not None
        assert is_initialized, "Call IsSafeInstrPred.initialize() first" 
        self.lvar = lvar

    def get_vars(self):
        return [self.lvar]
    
    def to_smt(self, state: Type[BtorState]) -> SolverTerm:
        lval = state[self.lvar]
        slv = lval._solver

        safe_expressions = [
            (lval & slv.bvv(IsSafeInstrPred.INST_SPEC[inst]["mask"], 32)).beq(slv.bvv(IsSafeInstrPred.INST_SPEC[inst]["match"], 32))
            for inst in IsSafeInstrPred.SAFE_SET
        ]

        return functools.reduce(lambda x, y: x.bor(y), safe_expressions)

    def eval(self, model: Dict[int, int]) -> bool:
        lval = model[self.lvar]
        for inst in IsSafeInstrPred.SAFE_SET:
            data = IsSafeInstrPred.INST_SPEC[inst]
            # print(f"Checking: {inst}")
            # print(f"lval: {lval}; {lval & data['mask']}; mask: {data['mask']}; match: {data['match']}")
            if (lval & data['mask']) == data['match']:
                # print(f"Matched: {inst}")
                return True
        return False

    def __repr__(self):
        return f"safe({self.lvar})"
    
    def pretty_print(self, state: BtorState):
        return f"safe({state.name_of(self.lvar)})"
    
    @classmethod
    def initialize(cls, inst_spec, safe_set):
        cls.INST_SPEC = {
            k: {
                'mask': int(v['mask'], 16),
                'match': int(v['match'], 16),
            } for k, v in inst_spec.items()
        }

        cls.SAFE_SET = list(safe_set)


class TruePred(Predicate):
    def __init__(self):
        self.lvar = "true"

    def get_vars(self):
        return []

    def to_smt(self, state: Type[BtorState]) -> SolverTerm:
        for some_term in state._state.values():
            return some_term._solver.true()
    
    def eval(self, model: Dict[int, int]) -> bool:
        return True

    def __repr__(self):
        return "true"
    
    def pretty_print(self, state: BtorState):
        return "true"
    

class AndPred(Predicate):
    def __init__(self, ps: List[Type[Predicate]]):
        self.ps = ps

    def get_vars(self):
        deps = []
        for p in self.ps:
            deps.extend(p.get_vars())
        return deps

    def to_smt(self, state: Type[BtorState]) -> SolverTerm:
        return functools.reduce(lambda x, y: x.band(y), [p.to_smt(state) for p in self.ps])
    
    def eval(self, model: Dict[int, int]) -> bool:
        return all([p.eval(model) for p in self.ps])

    def __repr__(self):
        return f"and({self.ps})"
    
    def __iter__(self):
        self.stack = [iter(self.ps)]  # Initialize a stack with the iterator of self.ps
        return self

    def __next__(self):
        while self.stack:
            try:
                current = next(self.stack[-1])  # Get the next element from the top iterator
                if isinstance(current, AndPred):
                    self.stack.append(iter(current.ps))  # Push the iterator of the nested AndPred
                else:
                    return current
            except StopIteration:
                self.stack.pop()  # Pop the exhausted iterator

        raise StopIteration
    
    def pretty_print(self, state: BtorState):
        return " and ".join([p.pretty_print(state) for p in self.ps])
    


    



class Invariant(AndPred):
    @classmethod
    def from_smt(cls, smt, state: BtorState):
        ap = super().from_smt(smt, state)
        if isinstance(ap, AndPred):
            return Invariant(ap.ps)
        else:
            return Invariant([ap])