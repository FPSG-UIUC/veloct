# Implements solver interface for symex using cvc5 interface

import copy
from typing import Any
from loguru import logger
import functools

import cvc5
from cvc5 import Kind


class Solver:
    """
    Wrapper around cvc5.Solver.

    This class is used to wrap cvc5.Solver objects and provide a more pythonic interface to them.

    NOTE: Do not add assertions specific to a particular check-sat call outside of a verification context. This will
    cause the assertion to be added to the solver permanently, and will cause the solver to return unsat after an initial unsat query.

    Ideally, one adds top-level assertions / assumptions directly to a solver and creates a new verification context for specific check-sat calls.
    The verification context is responsible for managing the solver context with `solver.push()` and `solver.pop()` calls.

    Usage examples:

    >>> solver = Solver(**{'produce-models': 'true'})
    >>> x = solver.new_var("x", 8)
    >>> y = solver.new_var("y", 8)
    >>> z = solver.new_var("z", 8)

    # Add top-level assertions directly to solver.
    >>> solver.add_assertion(x < 5)
    >>> solver.add_assertion(y < 5)

    # Create a new verification context and make a query that is unsat.
    >>> with solver.new_vc() as vc:
    ...     vc.add_assertion(z > 10)
    ...     assert vc.check_sat().isUnsat()

    # Any assertions added within the above with block will be popped off the solver when the context is deleted.
    # Now, Make another query that is sat.
    >>> with solver.new_vc() as vc:
    ...     vc.add_assertion(z < 10)
    ...     assert vc.check_sat().isSat()
    ...     z_value = vc.evaluate(z)

    # In the above example, the solver will be popped back to its original state when the context is deleted.

    The model returned by a SAT query will only be valid as long as the `vc` object is valid, and is automatically deleted with vc is deleted:
    explicitly, or implicitly when it goes out of scope. Therefore, it is recommended to evaluate expressions within the context of the vc object.

    We can also explicitly create new vc objects without using the `with` statement:

    >>> vc = solver.new_vc()
    >>> vc.add_assertion(z < 10)
    >>> assert vc.check_sat().isSat()
    >>> z_value = vc.evaluate(z)
    >>> del vc

    It is recommended that you do not push/pop the solver directly when using verification contexts as this can mess up the
    solver state if you are not careful, especially when the vc goes out of scope. As a rule of thumb, do not `solver.pop()` states that
    you did not explicitly `solver.push()`, and similarly, always `solver.pop()` states that you do `solver.push()`.

    Example:

    >>> vc = solver.new_vc()
    >>> vc.add_assertion(z < 10)
    >>> assert vc.check_sat().isSat()
    >>> solver.pop()
    >>> del vc   # Will cause the solver to pop an additional state!

    As a general rule, use vc to manage the solver stack and do not push/pop the solver directly.

    You can also chain multiple verification contexts together to implement a hierarchy, e.g., for a backtracking search:

    >>> vc = solver.new_vc()
    >>> vc.add_assertion(z < 5)            # We know z < 5
    >>> assert vc.check_sat().isSat()
    >>> vc1 = vc.new_vc()
    >>> vc1.add_assertion(z < 10)          # Is z < 10?
    >>> assert vc1.check_sat().isSat()
    >>> vc2 = vc1.new_vc()
    >>> vc2.add_assertion(z < 15)          # Is z < 15?
    >>> assert vc2.check_sat().isUnsat()   # No, backtrack to vc1
    >>> del vc2
    >>> assert vc1.check_sat().isSat()     # Yes, z < 10
    >>> z_value = vc1.evaluate(z)
    >>> del vc1
    >>> del vc

    """

    def __init__(self, **kwargs):
        """
        Create a new solver instance.

        :param kwargs: Any keyword arguments will be passed to cvc5.Solver.setOption
        """
        self.ctr = 0
        self.solver = cvc5.Solver()

        for k, v in kwargs.items():
            self.solver.setOption(k, v)

        self.solver.setLogic("QF_UFBV")
        self.solver.setOption("model-cores", "non-implied")
        
        self._vars = [{}]

    @property
    def vars(self):
        return self._vars[-1]
  
    def add_assertion(self, assertion):
        logger.warning(
            "[x] Adding an assertion outside of any verification context! Make sure this is intended."
        )
        if isinstance(assertion, SolverTerm):
            assertion = assertion.var
        logger.debug(f"Adding assertion: {assertion}")
        self.solver.assertFormula(assertion)

    def reset_assertions(self):
        """Reset all assertions added to the solver."""
        self.solver.resetAssertions()

    def new_vc(self):
        """Create a new verification context."""
        return VerificationContext(self)

    def push(self, frames=1):
        """Push the solver stack. NOTE: Avoid using this directly. Use `VerificationContext` to manage contexts instead."""
        self.solver.push(frames)
        self._vars.extend([copy.deepcopy({}) for _ in range(frames)])

    def pop(self, frames=1):
        """Push the solver stack. NOTE: Avoid using this directly. Use `VerificationContext` to manage contexts instead."""
        self.solver.pop(frames)
        del self._vars[-frames:]

    def simplify(self, expr):
        """Simplify an expression."""
        return self.solver.simplify(expr)

    def check_sat(self):
        """Check satisfiability."""
        return self.solver.checkSat()

    def get_model(self):
        model = {}
        for frame in self._vars:
            for k, t in frame.items():
                if not self.solver.isModelCoreSymbol(t.var):
                    continue
                model[k] = t.get_value().toPythonObj()
        return model

    def evaluate(self, exprs):
        """
        Evaluate an expression or a list of expressions.

        :param exprs: A collection (list or dict) of `SolverTerm` objects.

        :return: The value of the expression(s).
        """
        result = None
        # TODO: Maybe have a special case for State as well.
        if isinstance(exprs, list):
            result = [self.get_value(expr) for expr in exprs]
        elif isinstance(exprs, dict):
            result = {k: v.get_value() for k, v in exprs.items()}
        else:
            result = self.get_value(exprs)

        return result

    def get_value(self, expr):
        """
        Get the value of an expression.

        :param expr: A cvc5.Term object.
        """
        return self.solver.getValue(expr)

    def get_unsat_core(self):
        return self.solver.getUnsatCore()

    def is_unsat(self):
        """Check if the solver is unsat."""
        return self.solver.checkSat().isUnsat()

    def new_var(self, name, width):
        """
        Create a new bitvector variable.

        :param name: The name of the variable.
        :param width: The width of the variable in bits.

        :return: A `SolverTerm` object representing the variable.
        """
        unique_name = f"{name}${self.ctr}"
        sort = self.solver.mkBitVectorSort(width)
        var = self.solver.mkConst(sort, unique_name)
        self.ctr += 1
        term = SolverTerm(self, var)

        self.vars[unique_name] = term
        return term
    
    def new_uf(self, name, args):
        sorts = [self.solver.mkBitVectorSort(width) for width in args]
        uf_sort = self.solver.mkFunctionSort(sorts[:-1], sorts[-1])
        uf = self.solver.mkConst(uf_sort, name)
        return SolverTerm(self, uf)

    def new_bool_var(self, name):
        return self.new_var(name, 1)

    def bvv(self, value, width):
        """
        Create a new bitvector constant.

        :param value: The value of the constant.
        :param width: The width of the constant in bits.

        :return: A `SolverTerm` object representing the constant.
        """
        return SolverTerm(self, self.solver.mkBitVector(width, str(value), 10))

    def false(self):
        return SolverTerm(self, self.solver.mkFalse())

    def true(self):
        return SolverTerm(self, self.solver.mkTrue())

    def create_choice(self, choices):
        """
        Create a choice between multiple expressions.

        :param choices: A list of `SolverTerm` objects.

        :return: A `SolverTerm` object representing the choice.
        """
        return functools.reduce(
            lambda x, y: self.new_bool_var("b").ite(x, y), choices[::-1]
        ).simplify()

    def forall(self, vars, body):
        """
        Create a forall expression.
        """
        consts = [var.var for var in vars]
        binds = [self.solver.mkVar(c.getSort(), str(c)) for c in consts]
        subbed = body.var.substitute(consts, binds)
        fa = self.solver.mkTerm(
            Kind.FORALL, self.solver.mkTerm(Kind.VARIABLE_LIST, *binds), subbed
        )
        return SolverTerm(self, fa)


class VerificationContext(Solver):
    def __init__(self, solver):
        self.ctr = solver.ctr
        self.solver = solver.solver
        self._vars = solver._vars
        # Create a new solver context
        self.push()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Do nothing on exit. We will pop the solver back to its original state when the vc is deleted.
        pass

    def __del__(self):
        self.pop()

    def add_assertion(self, assertion):
        if isinstance(assertion, SolverTerm):
            assertion = assertion.var
        self.solver.assertFormula(assertion)



class SolverTerm:
    """
    Wrapper around cvc5.Term

    This class is used to wrap cvc5.Term objects and provide a more pythonic interface to them.
    """

    def __init__(self, solver, term):
        self._solver = solver
        self.var = term

    @property
    def id(self):
        return self.var.getId()

    def __str__(self):
        return self.var.__str__()

    def make_assert(self):
        """Add this term as an assertion to the solver."""
        self._solver.add_assertion(self.var)

    def get_value(self):
        """Get the value of this term. Requires a SAT query to be made prior to this call."""
        return self._solver.get_value(self.var)
    
    def value(self):
        return self.var.toPythonObj()

    def simplify(self):
        """Simplify this term using CVC5. Modifies the term in-place."""
        # simpl_term = self._solver.simplify(self.var)
        # self.var = simpl_term
        return self

    def syntactic_eq(self, other):
        """Check if this term is syntactically equal to another term."""
        return self.id == other.id

    def ite(self, true, false):
        """
        Create an if-then-else expression.

        :param true: The expression to evaluate if this term is true.
        :param false: The expression to evaluate if this term is false.

        :return: A `SolverTerm` object representing the if-then-else expression.
        """
        if self.var.getSort().isBoolean():
            term = self._solver.solver.mkTerm(Kind.ITE, self.var, true.var, false.var)
        else:
            term = self._solver.solver.mkTerm(
                Kind.BITVECTOR_ITE, self.var, true.var, false.var
            )
        return SolverTerm(self._solver, term)

    def implies(self, other):
        """
        Create an implication.

        :param other: The expression to imply.

        :return: A `SolverTerm` object representing the implication.
        """
        term = self._solver.solver.mkTerm(Kind.IMPLIES, self.var, other.var)
        return SolverTerm(self._solver, term)

    def append(self, other):
        """
        Concatenate two bitvectors.

        :param other: The bitvector to concatenate with this one.

        :return: A `SolverTerm` object representing the concatenated bitvector.
        """
        term = self._solver.solver.mkTerm(Kind.BITVECTOR_CONCAT, self.var, other.var)
        return SolverTerm(self._solver, term)

    def zero_extend(self, width):
        diff = width - len(self)
        op = self._solver.solver.mkOp(Kind.BITVECTOR_ZERO_EXTEND, diff)
        term = self._solver.solver.mkTerm(op, self.var)
        return SolverTerm(self._solver, term)

    def sign_extend(self, width):
        diff = width - len(self)
        op = self._solver.solver.mkOp(Kind.BITVECTOR_SIGN_EXTEND, diff)
        term = self._solver.solver.mkTerm(op, self.var)
        return SolverTerm(self._solver, term)
    
    def zero_extend_d(self, diff):
        op = self._solver.solver.mkOp(Kind.BITVECTOR_ZERO_EXTEND, diff)
        term = self._solver.solver.mkTerm(op, self.var)
        return SolverTerm(self._solver, term)

    def sign_extend_d(self, diff):
        op = self._solver.solver.mkOp(Kind.BITVECTOR_SIGN_EXTEND, diff)
        term = self._solver.solver.mkTerm(op, self.var)
        return SolverTerm(self._solver, term)

    def __add__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_ADD, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __sub__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_SUB, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __mul__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_MULT, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __truediv__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_UDIV, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __floordiv__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_UDIV, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __mod__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_UREM, self.var, other.var)
        return SolverTerm(self._solver, term)
    
    def srem(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_SREM, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __and__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())
        term = self._solver.solver.mkTerm(Kind.BITVECTOR_AND, self.var, other.var)
        return SolverTerm(self._solver, term)

    def band(self, other):
        term = self._solver.solver.mkTerm(Kind.AND, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __or__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_OR, self.var, other.var)
        return SolverTerm(self._solver, term)

    def bor(self, other):
        term = self._solver.solver.mkTerm(Kind.OR, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __xor__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_XOR, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __lshift__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())
        term = self._solver.solver.mkTerm(Kind.BITVECTOR_SHL, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __rshift__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_ASHR, self.var, other.var)
        return SolverTerm(self._solver, term)

    def lshr(self, other):
        term = self._solver.solver.mkTerm(Kind.BITVECTOR_LSHR, self.var, other.var)
        return SolverTerm(self._solver, term)
    
    def redxor(self):
        bv_size = len(self)
        result = self._solver.bvv(0, 1)
        for i in range(bv_size):
            result = result ^ self[i]
        return result

    def __eq__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        if self.is_bv():
            term = self._solver.solver.mkTerm(Kind.BITVECTOR_COMP, self.var, other.var)
        else:
            term = self._solver.solver.mkTerm(Kind.EQUAL, self.var, other.var)
        return SolverTerm(self._solver, term)

    def beq(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())
        term = self._solver.solver.mkTerm(Kind.EQUAL, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __ne__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        if self.is_bv():
            term = self._solver.solver.mkTerm(Kind.BITVECTOR_NOT, 
                                self._solver.solver.mkTerm(Kind.BITVECTOR_COMP, self.var, other.var))
        else:
            term = self._solver.solver.mkTerm(Kind.DISTINCT, self.var, other.var)

        return SolverTerm(self._solver, term)
    
    def bv2bool(self):
        width = self.var.getSort().getBitVectorSize()
        other = self._solver.bvv(0, width).var
        return SolverTerm(self._solver, self._solver.solver.mkTerm(Kind.EQUAL, self.var, other)).bnot()

    def __lt__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_ULTBV, self.var, other.var)
        return SolverTerm(self._solver, term)

    def slt(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())
        term = self._solver.solver.mkTerm(Kind.BITVECTOR_SLTBV, self.var, other.var)
        return SolverTerm(self._solver, term)

    def __le__(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term_a = self.__lt__(other)
        term_b = self.__eq__(other)

        term = term_a | term_b
        return term

    def sle(self, other):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term_a = self.slt(other)
        term_b = self.__eq__(other)

        term = term_a | term_b
        return term

    def __gt__(self, other):
        return  self.__le__(other).bvnot()

    def sgt(self, other):
        return self.sle(other).bvnot()

    def __ge__(self, other):
        return self.__lt__(other).bvnot()

    def sge(self, other):
        return self.slt(other).bvnot()

    def bvnot(self):
        term = self._solver.solver.mkTerm(Kind.BITVECTOR_NOT, self.var)
        return SolverTerm(self._solver, term)

    def bnot(self):
        term = self._solver.solver.mkTerm(Kind.NOT, self.var)
        return SolverTerm(self._solver, term)

    def __invert__(self):
        term = self._solver.solver.mkTerm(Kind.BITVECTOR_NEG, self.var)
        return SolverTerm(self._solver, term)

    def __abs__(self):
        if isinstance(other, int):
            other = self._solver.bvv(other, self.var.getSort().getBitVectorSize())

        term = self._solver.solver.mkTerm(Kind.BITVECTOR_ABS, self.var)
        return SolverTerm(self._solver, term)

    def __getitem__(self, index):
        """
        Extract a bitvector slice.

        :param index: An integer index or a slice object.

        :return: A `SolverTerm` object representing the extracted slice.
        """
        # Handle slicing
        if isinstance(index, slice):
            if index.step is not None:
                raise ValueError("Slice step not supported")

            if index.start is None:
                start = 0
            else:
                start = index.start

            if index.stop is None:
                stop = len(self) - 1
            else:
                stop = index.stop

            # if start < 0 or stop < 0:
            #     raise ValueError("Negative indices not supported")
            # if start > stop:
            #     raise ValueError("Start index must be less than stop index")

            clen = len(self)
            if stop >= clen or start >= clen:
                print("WARNING: Index out of bounds", clen, start, stop)

            op = self._solver.solver.mkOp(Kind.BITVECTOR_EXTRACT, start, stop)
            term = self._solver.solver.mkTerm(op, self.var)
        else:
            op = self._solver.solver.mkOp(Kind.BITVECTOR_EXTRACT, index, index)
            term = self._solver.solver.mkTerm(op, self.var)
        return SolverTerm(self._solver, term)

    def __len__(self):
        """Get the width of this bitvector in bits."""
        return self.var.getSort().getBitVectorSize()

    def __hash__(self):
        return self.var.__hash__()

    def __repr__(self):
        return self.var.__repr__()

    def __bool__(self):
        if self.var.isBooleanValue():
            return self.var.getBooleanValue()
        return False

    def __deepcopy__(self, memo):
        return SolverTerm(self._solver, self.var)

    def __reduce__(self):
        from symex.serialization import dump_term
        return dump_term(self)

    @property
    def operands(self):
        for child in self.var:
            yield SolverTerm(self._solver, child)

    def is_ite(self):
        return (
            self.var.getKind() == Kind.ITE or self.var.getKind() == Kind.BITVECTOR_ITE
        )

    def is_bv(self):
        return self.var.getSort().isBitVector()

    def to_nat(self):
        return self._solver.solver.mkTerm(Kind.BITVECTOR_TO_NAT, self.var)
    
    def apply_call(self, args):
        return SolverTerm(self._solver, self._solver.solver.mkTerm(Kind.APPLY_UF, self.var, *[arg.var for arg in args]))