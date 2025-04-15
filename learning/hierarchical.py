# Module that implemenets hierarchical invariant learning

import copy
import functools
import itertools
from typing import Set, Type, List, Optional
from loguru import logger

import learning
from learning.predicates import AndPred, Invariant, EqPred, NEqPred, PImplPred

import symex
from symex.solver import Solver, SolverTerm


from collections import namedtuple

import cvc5
from cvc5 import Kind
from symex.symex_btor import BtorPrgm, BtorState


DiscoveredPredicates = namedtuple("DiscoveredPredicates", "eq impl_head allowed_values")


class HierarchicalLearner:
    def __init__(self,
                 prgm: str,
                 positive_examples: List[Type[learning.examples.PositiveExample]],
                 negative_examples: List[Type[learning.examples.NegativeExample]],
                ):
        """
        Initializes a HierarchicalLearner object with the given program, positive examples, and negative examples.
        
        Args:
        - prgm (str): file-like object containing the program to learn invariants for (in btor format).
        - positive_examples (List[Type[learning.examples.PositiveExample]]): A list of positive examples to use for learning.
        - negative_examples (List[Type[learning.examples.NegativeExample]]): A list of negative examples to use for learning.
        """
        
        self._solver = Solver(**{"produce-abducts": "true", "produce-models": "true", "sygus": "true"})
        # self._solver = Solver(**{"sygus": "true", "incremental": "false"})
        self._solver.solver.setOption('rlimit-per', "1000000")


        prgm = prgm.read()
        self.prgm = BtorPrgm(prgm, self._solver)     

        # Create states
        self.state = self.prgm.init_state()
        # Create next state
        self.next_state = self.prgm.blank_state()
        
        self.positive_examples = positive_examples
        self.negative_examples = negative_examples
        self.visited = set()

        self.do_not_hold = set()

    def learn(self) -> Optional[Invariant]:
        """
        Learns an invariant for the given program and examples.
        """
        target = self.prgm.assertion
        target_predicate = EqPred(target)
        _ = self.prgm.interpret_node_id(target, self.state, self.next_state)
        inv = self.preserve_target_predicate(target_predicate, top=True)
        
        if not inv:
            logger.error("No valid invariant")
            return None

        return Invariant(inv)
    
    def preserve_target_predicate(self, target_predicate: Type[learning.predicates.Predicate], top=False) -> Optional[Type[Invariant]]:
        # TODO: Need to memoize work
        # TODO: Handle loops
        # TODO: We should disallow any predicates on the output from the register file and the top-level input to instructions
        if str(target_predicate) in self.visited:
            return []
        
        self.visited.add(str(target_predicate))
        print(self.visited)

        logger.info(f"[*] Trying to preserve: {target_predicate}")

        # Figure out the type of predicate
        used_vars = target_predicate.get_vars()

        deps = []
        for used in used_vars:
            if self.prgm.is_input(used):
                continue
            nxt = self.prgm.next_of_idx(used)
            deps.extend(self.prgm.deps_of(nxt))
            if not top and used not in self.next_state._state:
                _ = self.prgm.interpret_node_id(nxt, self.state, self.next_state)
        
        if not deps:
            # No need to preserve this predicate.
            return []

        logger.debug(f"Deps: {target_predicate, deps}")
        predicate_set = self._make_predicate_set(deps)
        
        if not predicate_set.eq:
            logger.warning(f"[x] {target_predicate}: No eq predicates found. Cannot continue with no eq predicates.")
            return None

        while predicate_set:
            inv = self.synthesize_invariant(target_predicate, predicate_set)
            if not top:
                ind = set([target_predicate])
            else:
                ind = set()
            
            if inv is None:
                logger.warning("No way to preserve predicate {target_predicate}", target_predicate=target_predicate)
                return None
            
            for pred in inv:
                if all([self.prgm.is_input(var) for var in pred.get_vars()]):
                    # We do not need to preserve this predicate
                    continue
                inv_p = self.preserve_target_predicate(pred)
                if inv_p is None:
                    # There is not way to preserve a predicate that is currently in the invariant
                    logger.debug("No way to preserve predicate {pred}", pred=pred)
                    eq_preds = predicate_set.eq
                    predicate_set = DiscoveredPredicates([p for p in eq_preds if p != pred], predicate_set.impl_head, predicate_set.allowed_values)
                    continue

                ind.update(inv_p)

            # Ok, we have found an inv that is inductive
            ind.update(list(inv))
            return Invariant(list(ind))

        # If we're here, there is no way to preserve the target predicate
        return None
            
    def synthesize_invariant(self, target_predicate: Type[learning.predicates.Predicate], predicate_set: Type[DiscoveredPredicates]) -> Optional[Type[Invariant]]:
        # TODO: Set solver timeout
        # TODO: Introduce parallelism using ray
        # TODO: Expose these through the solver API
        solver = self._solver.solver

        solver.push()

        # print(predicate_set)

        # grammar = self._define_grammar(self._solver, predicate_set)

        # # Add some assertions on things that need not be eq
        # # XXX: This may cause bugs? What we really want to explore is the space of possibilities when
        # # the head is true and when it is not true.
        # for neq in predicate_set.impl_head:
        #     self._solver.add_assertion(neq.to_smt(self.state))

        # # Add assertions on eq variables that are allowed to take certain values
        # # for var_name, values in predicate_set.allowed_values.items():
        # #     var = self.state.vars_L(var_name)
        # #     self._solver.add_assertion(functools.reduce(lambda x, y: x.bor(y), [var.beq(value) for value in values]))

        # print("Target predicate in SMT:", target_predicate.to_smt(self.next_state))

        # abd = solver.getAbduct(target_predicate.to_smt(self.next_state).var, grammar)
       
        # if abd.isNull():
        #     print("No abduct found")
        #     solver.pop()
        #     return None

        get_synth_fn, G, pred_map = self._define_grammar_for_synth(self._solver, predicate_set)
        # solver.addSygusConstraint(
        #     solver.mkTerm(Kind.AND, 
        #                   get_synth_fn,
        #                 #   target_predicate.to_smt(self.state).var,
        #                   target_predicate.to_smt(self.next_state).var, 
        #     )
        # )

        # for eq_pred in predicate_set.eq:
        solver.addSygusAssume(get_synth_fn)

        solver.addSygusConstraint(target_predicate.to_smt(self.next_state).var)

        # solver.addSygusAssume(get_synth_fn)
        # solver.addSygusConstraint(solver.mkTerm(Kind.IMPLIES, get_synth_fn, target_predicate.to_smt(self.next_state).var))

        if not solver.checkSynth().hasSolution():
            return None

        abd = solver.getSynthSolutions([G])
        
        wq = [abd[0][1]]
        invar = []
        while wq:
            current = wq.pop()
            # If the kind is an AND push to WQ
            if current.getKind() == Kind.AND:
                wq.extend(current)
            elif current.getKind() == Kind.VARIABLE:
                name = str(current.getSymbol())
                if name in pred_map:
                    invar.append(pred_map[name])
            else:
                print("Unknown kind: ", current.getKind())

        invar = Invariant(invar)
        print(invar.pretty_print(self.state))

        # invar = Invariant.from_smt(abd, self.state)
        invar_holds = all([invar.eval(pexample._model) for pexample in self.positive_examples])

        # XXX: Currently, there is no guarantee that the invariant generated from CVC5 will hold on
        # positive examples as there is no way to constrain the grammar to disallow a certain constant value.
        # There is some effort to add this into cvc5 but will need recompilation/testing on my end. Need to
        # follow-up on github. Once that support is added, we do not need to poll here for a resuly anymore.
        while not invar_holds:
            abd = solver.getAbductNext()
            if abd.isNull():
                solver.pop()
                return None
            
            invar = Invariant.from_smt(abd)
            invar_holds = all([invar.eval(pexample._model) for pexample in self.positive_examples])
                      
        solver.pop()
        return invar

    def _define_grammar(self, s: Type[symex.solver.Solver], predicate_set: Type[DiscoveredPredicates]) -> Type[cvc5.Grammar]:
        solver = s.solver

        boolean = solver.getBooleanSort()
        
        constants = {}
        tails = []

        # Any Eq pred can be in the tail
        for eq_pred in predicate_set.eq:
            var = self.state[eq_pred.lvar]
            # print("++++", var)
            width = len(var)
            if width not in constants:
                bitvec = solver.mkBitVectorSort(width)
                const = SolverTerm(s, solver.mkVar(bitvec, f"const_{width}"))
                constants[width] = const
            
            # Not sure if we should keep the and here: eq_pred.to_smt(self.state).band(...)
            tails.append(var.beq(constants[width]).bnot().var)
     
        start = solver.mkVar(boolean, 'start')
        pred = solver.mkVar(boolean, 'pred')
        eq = solver.mkVar(boolean, 'eq')

        terminals = []
        if predicate_set.impl_head:
            impl_head = solver.mkVar(boolean, 'impl_head')
            impl_tail = solver.mkVar(boolean, 'impl_tail')
            non_terminals = [start, pred, impl_head, impl_tail, eq] + [c.var for c in constants.values()]
        else:
            non_terminals = [start, pred, eq]
        
        g = solver.mkGrammar(terminals, non_terminals)

        g.addRules(start, [pred])

        And = solver.mkTerm(Kind.AND, pred, pred)
        if predicate_set.impl_head:
            Impl = solver.mkTerm(Kind.IMPLIES, impl_head, impl_tail)

            g.addRules(pred, [And, eq, Impl])
            g.addRules(impl_head, [neq.to_smt(self.state).var for neq in predicate_set.impl_head])
            g.addRules(impl_tail, tails)

            for w, const in constants.items():
                g.addAnyConstant(const.var)

        else:
            g.addRules(pred, [And, eq]) 

        g.addRules(eq, [e.to_smt(self.state).var for e in predicate_set.eq])

        print(g)

        return g
    
    def _define_grammar_for_synth(self, s: Type[symex.solver.Solver], predicate_set: Type[DiscoveredPredicates]) -> Type[cvc5.Grammar]:
        solver = s.solver

        boolean = solver.getBooleanSort()

        start = solver.mkVar(boolean, 'start')
        pred = solver.mkVar(boolean, 'pred')

        terminals = []
        literals = []
        pred_map = {}

        for eq_pred in predicate_set.eq:
            name = f"eq_{eq_pred.lvar}_{eq_pred.rvar}"
            terminals.append(solver.mkVar(boolean, name))
            literals.append(eq_pred.to_smt(self.state).var)
            pred_map[name] = eq_pred

        for h, t in itertools.product(predicate_set.impl_head, predicate_set.eq):
            name = f"impl_{h}_{t}"
            terminals.append(solver.mkVar(boolean, name))
            literals.append(solver.mkTerm(Kind.IMPLIES, h, t))
            pred_map[name] = PImplPred(h, t)

              
        lit = solver.mkVar(boolean, "lit")

        g = solver.mkGrammar(terminals, [start, pred, lit])

        g.addRules(start, [pred])
        g.addRules(pred, [lit, solver.mkTerm(Kind.AND, lit, pred)]) 
        g.addRules(lit, terminals)

        G = solver.synthFun("G", terminals, boolean)
        appl_g = solver.mkTerm(Kind.APPLY_UF, G, *literals)

        return appl_g, G, pred_map
    

    def _make_predicate_set(self, deps: List[int]) -> Type[DiscoveredPredicates]:
        eq_set = {}
        neq_set = []

        paired_deps = []
        completed = set()
        # Organize the deps into pairs
        for dep in deps:
            name = self.state.name_of(dep)
            prefix = ""
            if name.startswith("gold.") or name.startswith("gate."):
                prefix, name = name.split(".", 1)
                prefix = prefix + "."
            
            if name in completed:
                continue

            pair = self.state.pairmap[name]
            paired_deps.append(pair)

        for varl, varr in paired_deps:
            pred = EqPred(varl, varr)

            if pred in self.do_not_hold:
                neq_set.append((varl, varr))
            elif any([not pexample.does_predicate_hold(pred) for pexample in self.positive_examples]):
                neq_set.append((varl, varr))
                self.do_not_hold.add(pred)
            else:
                # lvar and rvar are equal, just get the value of lvar
                values = [pexample.value_of(f"{prefix}{varl}") for pexample in self.positive_examples]
                eq_set[(varl, varr)] = values


        return DiscoveredPredicates([EqPred(varl, varr) for varl, varr in eq_set], 
                                    [NEqPred(varl, varr) for varl, varr in neq_set], 
                                    eq_set)