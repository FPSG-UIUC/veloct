# Implements pickle serialization with memoization for solver related objects

import pickle
from symex.solver import Solver, SolverTerm

from loguru import logger
from cvc5 import Kind


class HollowState:
    # TODO: HollowState should also record assumptions and assertions from solver and restore it on instantiate
    # TODO: HollowState should also record the solver options and restore it on instantiate
    def __init__(self, serialized):
        self.serialized = serialized

    def instantiate(self, solver=Solver(**{"produce-models": "true", "bitblast": "eager"})):
        from symex.symex import State
        state = {}
        vars = {}
        for name, sterm in self.serialized.items():
            term = sterm[0](*sterm[1])
            vars[name] = term.instantiate(solver, state)

        return State(solver, vars)
    
    

class HollowTerm:
    def __init__(self, root, adj):
        self.root = root
        self.adj = adj

    def instantiate(self, solver=Solver(**{"produce-models": "true", "bitblast": "eager"}), state={}):
        wq = [self.root]

        while wq:
            current = wq[-1]

            if current in state:
                wq.pop()
                continue

            kind, args = self.adj[current]

            if kind in [Kind.CONSTANT, Kind.CONST_BITVECTOR, Kind.CONST_BOOLEAN]:
                if kind == Kind.CONSTANT:
                    name, sort = args
                    if name in state:
                        continue
                    if sort[0] == "bitvector":
                        sort = solver.solver.mkBitVectorSort(sort[1])
                    elif sort[0] == "bool":
                        sort = solver.solver.getBooleanSort()
                    elif sort[0] == "function":
                        args = [solver.solver.mkBitVectorSort(arg) for arg in sort[1:-1]]
                        ret = solver.solver.mkBitVectorSort(sort[-1])
                        sort = solver.solver.mkFunctionSort(args, ret)
                    else:
                        raise ValueError(f"Unsupported sort: {sort}")
                    term = solver.solver.mkConst(sort, name)
                elif kind == Kind.CONST_BITVECTOR:
                    name, sort = args
                    value, width = sort
                    term = solver.solver.mkBitVector(width, str(value), 10)
                elif kind == Kind.CONST_BOOLEAN:
                    name, sort = args
                    value = sort[0]
                    term = solver.solver.mkBoolean(value)
                
                solver_term = SolverTerm(solver, term)
                state[current] = solver_term
                continue

            if kind in [Kind.BITVECTOR_SIGN_EXTEND, Kind.BITVECTOR_ZERO_EXTEND]:
                kind = solver.solver.mkOp(kind, args[0])
                args = args[1:]
            elif kind == Kind.BITVECTOR_EXTRACT:
                kind = solver.solver.mkOp(kind, args[0], args[1])
                args = args[2:]

            new_q = []
            for arg in args:
                if arg not in state:
                    new_q.append(arg)

            if not new_q:
                current = wq.pop()
                solver_term = SolverTerm(solver, solver.solver.mkTerm(kind, *[state[arg].var for arg in args]))
                state[current] = solver_term
            else:
                wq.extend(new_q)

        return state[self.root]
    

def dump_state(state):
    """
    Serialize a state into a pickled string
    """

    adj = {}
    serialized = {}

    for name, term in state.vars.items():
        h = hash(term)
        if h in adj:
            serialized[name] = (HollowTerm, (h, adj))
        else:
            serialized[name] = dump_term(term, adj)

    return (HollowState, (serialized,))


def dump_term(term, adj={}):
    """
    Serialize a term into a pickled string
    """

    wq = [term]

    while wq:
        current = wq.pop(0)
        h = hash(current)
        
        if h in adj:
            continue

        args = tuple(current.operands)
        kind = current.var.getKind()

        # If kind is a Constant, then we need to put in additional information to reconstruct the term.
        if kind == Kind.CONSTANT:
            name = current.var.getSymbol()
            sort = current.var.getSort()
            # If the type of sort is bitvector, get its width.
            if sort.isBitVector():
                sort = ("bitvector", sort.getBitVectorSize())
            # Check if it is a boolean sort
            elif sort.isBoolean():
                sort = "bool"
            elif sort.isFunction():
                args = [arg.getBitVectorSize() for arg in sort.getFunctionDomainSorts()]
                ret = sort.getFunctionCodomainSort().getBitVectorSize()
                sort = ("function", *args, ret)
            else:
                # Log a error and return None
                logger.error(f"Unsupported sort: {sort}")
                sort = str(sort)
            
            args = (name, sort)
        elif kind == Kind.CONST_BITVECTOR:
            value = int(current.var.getBitVectorValue(), 2)
            width = current.var.getSort().getBitVectorSize()
            sort = (value, width)
            name = f"const${value}${width}"
            args = (name, sort)
        elif kind == Kind.CONST_BOOLEAN:
            value = current.var.getBooleanValue()
            sort = value
            name = f"const${value}"
            args = (name, sort)
        elif kind in [Kind.BITVECTOR_SIGN_EXTEND, Kind.BITVECTOR_ZERO_EXTEND]:
            wq.extend(args)
            op = current.var.getOp()
            args = tuple([op[0].toPythonObj()]) + tuple([hash(arg) for arg in args])
        elif kind == Kind.BITVECTOR_EXTRACT:
            wq.extend(args)
            op = current.var.getOp()
            args = (op[0].toPythonObj(), op[1].toPythonObj()) + tuple([hash(arg) for arg in args])
        else:
            wq.extend(args)
            args = tuple([hash(arg) for arg in args])
        
        adj[h] = (kind, args)

    return (HollowTerm, (hash(term), adj))