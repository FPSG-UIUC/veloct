# Implements Houdini / SORCAR invariant learning
from learning.predicates import EqPred, AndPred, NEqPred, PImplPred, Invariant
from learning.examples import PositiveExample, ImplicationExample

import ray
import copy

from symex.symex import State


class InvariantLearner:
    def __init__(self, symex, vars, examples):
        self.symex = symex
        self._solver = symex._solver

        self.vars = vars
        self.examples = examples

        self.H = self.initial_H()
        self.start_state = self.initial_state()

    def initial_H(self):
        # TODO: Only add regs
        ps = []
        for var in self.vars:
            if not (var.type == "Reg" or var.type == 'Input' or var.type == 'Inout'):
                continue
            
            base_name, side = var.name.rsplit("-", 1)
            if side != "L":
                continue
            ps.append(EqPred(base_name))

        return Invariant(ps)
    
    def initial_state(self):
        varmap = {}
        for var in self.vars:
            base_name, side = var.name.rsplit("-", 1)
            varmap[var.name] = self._solver.new_var(f"{base_name}@0-{side}", var.w)
        
        return State(self._solver, varmap)

    def learn_invariant(self):
        # First, filter out predicates and consider only ones that hold on positive examples
        self.refine_H_pos(self.H)
        self.start_state = self.initial_state()

        while True:
            start_state = copy.deepcopy(self.start_state)
            with self._solver.new_vc() as vc:
                self.init_H_state(start_state, vc)
                neg_ex = self.check_H_safe()
                if neg_ex:
                    self.refine_H_neg(neg_ex)
                    continue

                impl_ex = self.check_H_ind()
                if not impl_ex:
                    return self.H
                else:
                    self.refine_H_impl(impl_ex)

    def init_H_state(self, state, vc):
        for p in self.H:
            smt = p.to_smt(state)
            vc.add_assertion(smt)
        self.symex._state = [state]
        self.symex.cycle = 0

    def check_H_safe(self):
        result = self.symex.check_safety()
        if result.is_safe:
            return None
        else:
            return result

    def refine_H_neg(self, neg_ex):
        pass

    def refine_H_impl(self, impl_ex):
        pass

    def check_H_ind(self):
        self.symex.step()
        initial_state = self.symex._states[0]
        new_state = self.symex.state
        with self._solver.new_vc() as vc:
            smt = self.H.to_smt(new_state)
            vc.add_assertion(smt.bnot())
            if vc.is_unsat():
                return None
            else:
                return ImplicationExample(
                    vc.get_minimal_model(initial_state), vc.get_minimal_model(new_state)
                )

    def refine_H_pos(self, preds):
        # TODO: This is limiting parallelism
        valid = [p for p in preds if self.predicate_holds_on_examples(p)]
        print("*******", preds, valid)
        return AndPred(valid)

    def predicate_holds_on_examples(self, pred):
        remotes = []
        print("Checking", pred)
        for example_type, example in self.examples:
            if example_type != "PositiveExample":
                continue
            np = AndPred([pred] + [EqPred(obs) for obs in self.symex.annotations.obs])
            ref = example.does_predicate_hold.remote(np)
            remotes.append(ref)

        while remotes:
            done, remotes = ray.wait(remotes, timeout=3*60)
            if not done:
                print("Timeout")
                _ = [ray.cancel(ref) for ref in remotes]
                return True
            
            results = ray.get(done)
            if not all(results):
                _ = [ray.cancel(ref) for ref in remotes]
                return False

        return True