import pickle
import re
from collections import defaultdict
from typing import Dict
from learning.predicates import Predicate

from symex.solver import Solver
import ray
from symex.symex_btor import BtorState


class SymbolicExample:
    def __init__(self, state):
        # Copy over everything from state
        self.state = state

    def does_predicate_hold(self, predicate):
        with self._solver.new_vc() as vc:
            smt = predicate.to_smt(self.state)
            vc.add_assertion(smt.bnot())
            return vc.is_unsat()


class ConcreteExample:
    def __init__(self, state: Dict[int, int]):
        self._model = state

    def does_predicate_hold(self, predicate: Predicate):
        return predicate.eval(self._model)
    
    @staticmethod
    def from_solver(solver: Solver, state: BtorState) -> 'ConcreteExample':
        examples = defaultdict(dict)
        minimal_model = solver.get_model()

        # Create a regex to match f"{name}@{cycle}-{optional_side}"
        r = re.compile(r"(.*)")
        for name, value in minimal_model.items():
            m = r.match(name)
            
            if m is None:
                continue

            var_name = m.group(1)

            var_index = state.index_of(var_name)
            examples[cycle][var_index] = value

        examples_list = []
        for cycle, values in sorted(examples.items()):
            examples_list.append(values)
        
        return examples_list
    
    def value_of(self, var: int):
        return self._model.get(var, None)


@ray.remote
class PositiveExample(SymbolicExample):
    def __init__(self, state):
        self.state = state

    def instantiate(self, solver=None):
        if solver is None:
            solver = Solver()
        state = pickle.loads(self.state).instantiate(solver)
        self.state = state
        self._solver = solver


@ray.remote
class NegativeExample(ConcreteExample):
    
    @staticmethod
    def from_solver(solver, base_name):
        examples = ConcreteExample.from_solver(solver)
        return [NegativeExample.options(name=f"{base_name}@{i}", get_if_exists=False, lifetime="detached").remote(example) for i, example in enumerate(examples)]


class ImplicationExample(ConcreteExample):
    def __init__(self, state, state_prime):
        super().__init__(state)
        self.model_prime = state_prime.get_minimal_model()

    @staticmethod
    def from_solver(solver):
        examples = ConcreteExample.from_solver(solver)
        assert len(examples) == 2

        return ImplicationExample(examples[0], examples[1])

    def does_predicate_hold(self, predicate):
        # Predicate holds on an implication example if it holds on initial state and state_prime
        # Or, it doesn't hold on initial state itself.
        holds_initially = predicate.eval(self._model)
        if not holds_initially:
            return True
        else:
            return predicate.eval(self.model_prime)