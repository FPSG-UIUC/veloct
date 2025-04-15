from cvc5 import Kind

from learning.predicates import EqPredConst


def log_to_file(filename):
    """
    Decorator to write all print() statements to a file within a function.
    
    Args:
        filename (str): The name of the file to write the logs to.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with open(filename, 'w') as f:
                # Redirect stdout to the file
                import sys
                original_stdout = sys.stdout
                sys.stdout = f
                
                # Call the original function
                result = func(*args, **kwargs)
                
                # Restore stdout
                sys.stdout = original_stdout
            return result
        return wrapper
    return decorator


@log_to_file('output.log')
def debug_check_max_sat(solver, state, next_state, literals, predicate, predicate_set):
    def fix_1744_neq_ctrl_killd():
        solver.assertFormula(solver.mkTerm(Kind.EQUAL, state[1743].var, solver.mkBitVector(1, 0)))

    def get_var_sort(var, state):
        return state[var].var.getSort()

    def add_pex_constraints():
        for t in predicate_set.eq:
            sort = get_var_sort(t.lvar, state)
            allowed_values = set(predicate_set.allowed_values[(t.lvar, t.rvar)])
            if len(allowed_values) == 1:
                value = allowed_values.pop()
                solver.assertFormula(solver.mkTerm(Kind.EQUAL, state[t.lvar].var, solver.mkBitVector(sort.getBitVectorSize(), value)))
                print(f"- {state.rvarmap[t.lvar]}: {value}")
            else:
                print(f"++++ {state.rvarmap[t.lvar]}")
    
    solver.setOption("produce-unsat-cores", "true")
    solver.setOption("incremental", "true")
    solver.setOption("sygus", "false")
    solver.setOption("minimal-unsat-cores", "true")
    solver.setOption("produce-models", "true")

    for lit in literals:
        print(lit)
        solver.assertFormula(lit)
                                            
    # fix_1744_neq_ctrl_killd()

    add_pex_constraints()

    solver.assertFormula(predicate.to_smt(state).var)
    solver.assertFormula(predicate.to_smt(next_state).bnot().var)

    # solver.assertFormula(EqPredConst(2146, 0b1000001000000110110011).to_smt(state).var)
    # solver.assertFormula(EqPredConst(1626, 0b1000001000000110110011).to_smt(state).var)
    # solver.assertFormula(EqPredConst(1664, 0b1000001000000110110011).to_smt(state).var)

    # solver.assertFormula(EqPredConst(1783, 0b10000000000000000000000111100100).to_smt(state).var)
    # solver.assertFormula(EqPredConst(1660, 0b10000000000000000000000111100100).to_smt(state).var)
    
    if solver.checkSat().isUnsat():
        # for t in predicate_set.eq:
            # print(f"{state.rvarmap[t.lvar]}({t.lvar}): {solver.getValue(state[t.lvar].var)}; {state.rvarmap[t.rvar]}: {solver.getValue(state[t.rvar].var)}")
        print("==== CORE ====")
        print(solver.getUnsatCore())
        assert False, "EQS are SUFFICIENT"
    else:
        debug_dump_sat_solutions(solver, predicate, state, next_state, predicate_set)


def debug_dump_sat_solutions(solver, predicate, state, next_state, predicate_set):
    with open(f"debug_logs/{predicate}.log", 'w') as fd:
        # fd.write(f"Target: ", solver.getValue(next_state[1785].var))
        fd.write(f"FIRST: {predicate.to_smt(state).var}, {solver.getValue(predicate.to_smt(state).var)}\n")
        fd.write(f"NEXT: {solver.getValue(predicate.to_smt(next_state).var)}\n")
        fd.write("====================================\n")
        fd.write(f" --- Expression: {predicate.to_smt(next_state).var}\n")
        fd.write("====================================\n")
        for h in predicate_set.impl_head:
            lval = solver.getValue(state[h.lvar].var)
            rval = solver.getValue(state[h.rvar].var)
            if lval.toPythonObj() != rval.toPythonObj():
                fd.write(f"xxx {state.rvarmap[h.lvar]}({h.lvar}): {lval}; {state.rvarmap[h.rvar]}({h.rvar}): {rval}\n")
            else:
                fd.write(f"--- {state.rvarmap[h.lvar]}({h.lvar}): {lval}; {state.rvarmap[h.rvar]}({h.rvar}): {rval}\n")
        
        for t in predicate_set.eq:
            lval = solver.getValue(state[t.lvar].var)
            fd.write(f"{state.rvarmap[t.lvar]}({t.lvar}): {lval}; {state.rvarmap[t.rvar]}({t.rvar}): {solver.getValue(state[t.rvar].var)}\n")
            pos_values = set()
            for value in predicate_set.allowed_values[(t.lvar, t.rvar)]:
                pos_values.add(value)
            if lval.toPythonObj() not in pos_values:
                fd.write(f"  xxx Possible values: {[bin(x) for x in pos_values]}\n")
            else:
                fd.write(f"  --- Possible values: {[bin(x) for x in pos_values]}\n")
    
    # assert False, "NOT SUFFICIENT"


def positive_examples_to_csv(examples, state, output_file="positive_examples.csv"):
    import pandas as pd

    data = {}

    print(len(examples))

    # Iterate over examples in chuncks of 17
    for cycle, example in enumerate(examples):
        cycle = cycle % 17
        if cycle not in data:
            data[cycle] = {}

        for var, value in example._model.items():
            # print(var, value)
            name = state.rvarmap[var]
            if name not in data[cycle]:
                data[cycle][name] = []
            data[cycle][name].append(value)

    for _, v in data.items():
        for n in v:
            v[n] = list(dict.fromkeys(v[n]))

    df = pd.DataFrame(data)
    print(df)
    df.to_csv(output_file)