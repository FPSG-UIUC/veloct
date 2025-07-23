
import asyncio
from collections import namedtuple, deque
import json
import random

from loguru import logger
from typing_extensions import Annotated
import ray

import cvc5
from cvc5 import Kind
import typer
import redis
import pickle
import time
import argparse

from motor.motor_asyncio import AsyncIOMotorClient

from typing import Dict, List, Optional, Tuple, Type, Union

import yaml

# import learning.RocketConfig as rocket
from learning.examples import ConcreteExample
from learning.predicates import EqPred, EqPredConst, Invariant, IsSafeInstrPred, NEqPred, PImplPred, Predicate, SynthesizablePImplPred, TruePred
from learning.utilities import debug_check_max_sat, debug_dump_sat_solutions
from symex.solver import Solver, SolverTerm
from symex.symex_btor import BtorPrgm, BtorState
import logging as logger


REDIS_HOST = "localhost"
REDIS_PORT = 6379
MAX_CTRL_WIDTH = 257
DEBUG_LEVEL = logger.INFO
DEBUG_POINT = -1
MONGO_URL = "mongodb://localhost:27017"
MONGO_COLLECTION = "rocket-13"


def expand_concrete_example(f1: str, f2: str, starting_cycle: int, state: BtorState) -> List[ConcreteExample]:
    result = []

    with open(f1, "r") as trace1:
        trace1_json_temp = json.load(trace1)["examples"]
        current_state = {}
        for key, value in trace1_json_temp.items():
            # recover to complete states
            for subkey, subv in value.items():
                current_state[subkey] = int(subv, 2)
            if int(key) >= starting_cycle and int(key) < starting_cycle + 12:
                annotated_states = {}
                for subkey, subv in current_state.items():
                    if subkey in state.varmap:
                        varname = subkey
                        var_idx = state.index_of(varname)
                    else:
                        try:
                            varname = f"gold.{subkey}"
                            var_idx = state.index_of(varname)
                        except KeyError:
                            continue
                    annotated_states[var_idx] = subv
                result.append(annotated_states)

    with open(f2, "r") as trace2:
        trace2_json_temp = json.load(trace2)["examples"]
        current_state = {}
        for key, value in trace2_json_temp.items():
            for subkey, subv in value.items():
                current_state[subkey] = int(subv, 2)
            if int(key) >= starting_cycle and int(key) < starting_cycle + 12:
                index = int(key) - starting_cycle
                for subkey, subv in current_state.items():
                    if subkey in state.varmap:
                        varname = subkey
                        var_idx = state.index_of(varname)
                    else:
                        try:
                            varname = f"gate.{subkey}"
                            var_idx = state.index_of(varname)
                        except KeyError:
                            continue
                    result[index // 2][var_idx] = subv

    result_concrete_examples = [ConcreteExample(x) for x in result]
    return result_concrete_examples


DiscoveredPredicates = namedtuple("DiscoveredPredicates", "eq impl_head allowed_values")


async def add_telementry_record(collection, predicate: Predicate, type: str, current: float):
    try:
        record = { 'type': type, 'predicate': str(predicate), 'time': current }
        await collection.insert_one(record)
    except Exception as e:
        logger.critical(f"Error adding telementry record: {e}")


@ray.remote(num_returns=1)
def synthesize_target(
    prgm_str: str,
    examples: List[ConcreteExample],
    predicate: Predicate,
    inst_spec_p: str,
    safe_insts: List[str],
    redis_host: str="localhost",
    ) -> Tuple[Union[Invariant, bool], Predicate]:
    return asyncio.run(synthesize_target_async(prgm_str, examples, predicate, inst_spec_p, safe_insts, redis_host))


async def synthesize_target_async(
    prgm_str: str,
    examples: List[ConcreteExample],
    predicate: Predicate,
    inst_spec_p: str,
    safe_insts: List[str],
    redis_host: str="localhost",
    ) -> Tuple[Union[Invariant, bool], Predicate]:
    
    # Connect to redis database for results
    # TODO: Allow this to take host and port as arguments
    result_map = redis.Redis(host=redis_host, port=REDIS_PORT)

    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client['veloct-stats']
    collection = db[MONGO_COLLECTION]
    awaitables = []

    awaitables.append(add_telementry_record(collection, predicate, 'start', time.time()))
    
    root = logger.getLogger()
    root.setLevel(DEBUG_LEVEL)

    inst_spec_p = yaml.safe_load(open(inst_spec_p))
    IsSafeInstrPred.initialize(inst_spec_p, safe_insts)

    def get_result(result_map: redis.Redis, predicate: Predicate) -> Optional[Union[Invariant, bool]]:
        key = str(predicate)
        value = result_map.get(key)
        if value is None:
            return None
        return pickle.loads(value)

    def set_result(result_map: redis.Redis, predicate: Predicate, result: Union[Invariant, bool]):
        key = str(predicate)
        result_map[key] = result

    def init(prgm: BtorPrgm) -> Tuple[BtorPrgm, BtorState, BtorState]:
        solver = Solver(
            **{
               "sygus": "true", 
                # "produce-unsat-cores": "true"
                # "rlimit-per": "100000",
                # "incremental": "true",
                # "produce-interpolants": "true",
            }
        )
        # solver.solver.setOption("rlimit-per", "100000")

        prgm = BtorPrgm(prgm, solver)

        return prgm, prgm.init_state(), prgm.blank_state()

    def get_deps(prgm: BtorPrgm, predicate: Predicate, state: BtorState, next_state: BtorState) -> List[int]:
        deps = []

        for used in predicate.get_vars():
            if prgm.is_input(used):
                # Inputs need to be initialized in next state
                input_name = state.name_of(used)
                prgm._make_state[input_name](prgm, next_state)
                continue
            nxt = prgm.next_of_idx(used)
            deps.extend(prgm.deps_of(nxt))
            if prgm.assertion != used and used not in next_state._state:
                _ = prgm.interpret_node_id(nxt, state, next_state)
            elif prgm.assertion == used:
                _ = prgm.interpret_node_id(used, state, next_state)

        if isinstance(predicate, PImplPred):
            lhs_vars = predicate.lhs.get_vars()
            for var in lhs_vars:
                if prgm.is_input(var):
                    input_name = state.name_of(var)
                    prgm._make_state[input_name](prgm, next_state)
                else:
                    nxt = prgm.next_of_idx(var)
                    if var not in next_state._state:
                        _ = prgm.interpret_node_id(nxt, state, next_state)

        return deps

    def does_predicate_not_hold(result_map: redis.Redis, predicate: Predicate) -> bool:
        key = str(predicate)
        result = get_result(result_map, key)
        if result is False:
            return True
        return False

    def make_predicate_set(
        deps: List[int], state: BtorState, positive_examples: List[ConcreteExample]
    ) -> Type[DiscoveredPredicates]:
        eq_set = {}
        neq_set = []

        paired_deps = set()
        completed = set()

        # Organize the deps into pairs
        for dep in deps:
            name = state.name_of(dep)
            prefix = ""
            if name.startswith("gold.") or name.startswith("gate."):
                prefix, name = name.split(".", 1)
                prefix = prefix + "."

            if name in completed:
                continue

            pair = state.pairmap[name]
            paired_deps.add(tuple(pair))

        for varl, varr in paired_deps:
            pred = EqPred(varl, varr)

            if does_predicate_not_hold(result_map, pred):
                neq_set.append((varl, varr))
            elif any(
                [
                    not pexample.does_predicate_hold(pred)
                    for pexample in positive_examples
                ]
            ):
                neq_set.append((varl, varr))
            else:
                values = [
                    pexample.value_of(varl)
                    for pexample in positive_examples
                ]
                eq_set[(varl, varr)] = values

        return DiscoveredPredicates(
            [EqPred(varl, varr) for varl, varr in eq_set],
            [NEqPred(varl, varr) for varl, varr in neq_set],
            eq_set,
        )

    def get_var_sort(var: int, state: BtorState) -> cvc5.Sort:
        return state[var].var.getSort()
    
    def add_safe_instruction_preds(predicate_set: DiscoveredPredicates, parse_map: Dict[str, Predicate], examples: List[ConcreteExample], state: BtorState, solver: cvc5.Solver):
        for pred in predicate_set.eq:
            # Get the width of variable, if it is not 32, then it cannot be an instruction holding reg so we continue
            if get_var_sort(pred.lvar, state).getBitVectorSize() != 32:
                continue
            # XXX: HACK
            if pred.lvar in [2812, 2658]:
                continue
            # Check if all the examples satisfy the predicate
            safe_pred = IsSafeInstrPred(pred.lvar)
            if any([not pexample.does_predicate_hold(safe_pred) for pexample in examples]):
                print(f"Cannot add safe instruction predicate to {pred.lvar} as an example violates it.")
                continue
            else:
                print(f"Adding safe instruction predicate to {pred.lvar}")
                smt = safe_pred.to_smt(state).var
                solver.assertFormula(smt)
                parse_map[hash(smt)] = safe_pred
        # assert False
    
    def unsat_produce_abduct(solver: cvc5.Solver, predicate: Predicate, predicate_set: DiscoveredPredicates, examples: ConcreteExample, state: BtorState, next_state: BtorState, result_map: redis.Redis) -> Tuple[Union[Invariant, bool], Predicate]:  
        # if isinstance(predicate, EqPred) and predicate.rvar is None:
        #     return [], predicate
        
        solver.setOption("produce-unsat-cores", "true")
        solver.setOption("incremental", "true")
        solver.setOption("sygus", "false")
        solver.setOption("minimal-unsat-cores", "true")
        solver.setOption("produce-models", "true")

        solver.push()

        parse_map = dict()

        for eq in predicate_set.eq:
            smt = eq.to_smt(state).var
            solver.assertFormula(smt)
            parse_map[hash(smt)] = eq

            allowed_values = set(predicate_set.allowed_values[(eq.lvar, eq.rvar)])
            # XXX: This is a hack to synthesize more precise predicates. Not sure if we should keep.
            if len(allowed_values) == 1 and get_var_sort(eq.lvar, state).getBitVectorSize() < 256:
                value = allowed_values.pop()
                pred_eq_const = EqPredConst(eq.lvar, value)
                if not does_predicate_not_hold(result_map, pred_eq_const):
                    smt = pred_eq_const.to_smt(state).var
                    logger.debug(f"Adding const constraint {eq.lvar} {value}")
                    solver.assertFormula(smt)
                    parse_map[hash(smt)] = pred_eq_const
                    continue
                else:
                    logger.debug(f"  - {str(predicate)} : Skip {str(pred_eq_const)}")
            
        solver.assertFormula(predicate.to_smt(state).var)
        parse_map[hash(predicate.to_smt(state).var)] = predicate

        solver.assertFormula(predicate.to_smt(next_state).bnot().var)
        awaitables.append(add_telementry_record(collection, predicate, 'smt_start', time.time()))
        if solver.checkSat().isUnsat():
            core = solver.getUnsatCore()
            awaitables.append(add_telementry_record(collection, predicate, 'smt_end', time.time()))
            invar = [parse_map[hash(smt)] for smt in core if hash(smt) in parse_map]
            set_result(result_map, predicate, pickle.dumps(invar))
            return invar, predicate
        else:
            awaitables.append(add_telementry_record(collection, predicate, 'smt_end', time.time()))

            add_safe_instruction_preds(predicate_set, parse_map, examples, state, solver)

            awaitables.append(add_telementry_record(collection, predicate, 'smt_start', time.time()))
            if solver.checkSat().isUnsat():
                core = solver.getUnsatCore()

                awaitables.append(add_telementry_record(collection, predicate, 'smt_end', time.time()))

                invar = [parse_map[hash(smt)] for smt in core if hash(smt) in parse_map]
                set_result(result_map, predicate, pickle.dumps(invar))
                return invar, predicate
            else:
                awaitables.append(add_telementry_record(collection, predicate, 'smt_end', time.time()))
                lvar = state.name_of(predicate.lvar)
                logger.warning(f"Solver returned SAT for {predicate} ({lvar})")
                set_result(result_map, predicate, pickle.dumps(False))
                # solver.pop()
                return False, predicate
            
    ### =================================================================================================
    ### Body of the synthesis flow starts here
    ### =================================================================================================

    logger.info(f"Synthesizing {predicate}")
    cached_result = get_result(result_map, predicate)
    if cached_result is not None:
        logger.info(f"Found cached for {str(predicate)}")
        awaitables.append(add_telementry_record(collection, predicate, 'return_memoized', time.time()))
        await asyncio.gather(*awaitables)
        return cached_result, predicate

    prgm, state, next_state = init(prgm_str)
    solver = prgm.slv.solver

    awaitables.append(add_telementry_record(collection, predicate, 'deps_start', time.time()))
    deps = get_deps(prgm, predicate, state, next_state)
    awaitables.append(add_telementry_record(collection, predicate, 'deps_end', time.time()))

    # This predicate holds true trivially as there are no dependencies
    if not deps:
        set_result(result_map, predicate, pickle.dumps(True))
        awaitables.append(add_telementry_record(collection, predicate, 'return_trivial', time.time()))
        await asyncio.gather(*awaitables)
        return [], predicate

    awaitables.append(add_telementry_record(collection, predicate, 'predicate_start', time.time()))
    predicate_set = make_predicate_set(deps, state, examples)
    awaitables.append(add_telementry_record(collection, predicate, 'predicate_end', time.time()))

    invar, predicate = unsat_produce_abduct(solver, predicate, predicate_set, examples, state, next_state, result_map)

    if invar is False:
        awaitables.append(add_telementry_record(collection, predicate, 'return_fail', time.time()))
        await asyncio.gather(*awaitables)
        return False, predicate
    
    awaitables.append(add_telementry_record(collection, predicate, 'return_success', time.time()))
    _results = await asyncio.gather(*awaitables)

    return invar, predicate


def get_completed_result(in_flight: List[str], results_map: redis.Redis, pred: Predicate) -> Optional[Union[Invariant, bool]]:
    pkey = str(pred)
    if pkey in in_flight:
        return None
    result = results_map.get(pkey)
    if result is None:
        return result
    return pickle.loads(result)


def maybe_spawn_tasks(
    rocket: str, 
    positive_examples: List[ConcreteExample],
    preds: List[Predicate],
    results_map: redis.Redis,
    running_tasks: List[ray.ObjectRef],
    in_flight: List[str],
    force: bool=True,
    inst_spec_p: str=None,
    safe_insts: List[str]=None,
    collection=None,
):
    for pred in preds:
        key = str(pred)
        # If the pred is in-flight, don't mess with it
        if key in in_flight:
            continue

        cached = results_map.get(key)
        # We have synthesized this before and there is *no* invariant possible. Don't try again.
        if cached is False:
            continue

        # If cached is None, we have never processed this instruction (because we know it is not in-flight)
        # Otherwise, the only reason to respawn the task is if force is set to True
        if force or cached is None:
            logger.debug(f"Spawning: {str(pred)} {cached}")
            task = synthesize_target.remote(rocket, positive_examples, pred, inst_spec_p, safe_insts)
            running_tasks.append(task)
            in_flight.add(key)

            # Add a record to stats to indicated that a task was queued
            loop = asyncio.get_event_loop()
            loop.run_until_complete(add_telementry_record(collection, pred, 'queued', time.time()))


def dfs_no_recurse(rocket: str, positive_examples: List[ConcreteExample], top_pred: Predicate, inst_spec_p: str, safe_insts: List[str]) -> bool:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    result_map = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client['veloct-stats']
    collection = db[MONGO_COLLECTION]

    priorities = dict()
    running_tasks = []
    in_flight = set()
    dependency_map = {}

    maybe_spawn_tasks(
        rocket, positive_examples, [top_pred], result_map, running_tasks, in_flight, inst_spec_p=inst_spec_p, safe_insts=safe_insts, collection=collection,
    )

    while running_tasks:
        num_returns = min(len(running_tasks), 10)
        ready, running_tasks = ray.wait(
            running_tasks, num_returns=num_returns, timeout=None,
        )

        results = ray.get(ready)

        # As long as we haven't processed a result through this loop, the predicates and their results are still considered to be "in flight"
        for invar, pred in results:
            # Remove the tasks that have returned
            pkey = str(pred)
            in_flight.remove(pkey)

            if invar is True:
                # Trivially true result. No need to do anything.
                logger.debug(f"{pkey} is trivially true.")
                continue

            if invar is False:
                logger.debug(f"{pkey} does not have a solution!")
                # Respawn the tasks that were dependent on this task returning a result so that they can be re-synthesized
                # If the task has no dependents, then it is a top-level predicate we were trying to synthesize and it failed, return False
                if pkey not in dependency_map:
                    # There is no invariant
                    logger.critical(f"[X] No Invariant found because task {pred} failed!")
                    return False
                
                # Delete the results of all dependent tasks so that they can regenerate their solutions
                for dep in dependency_map[pkey]:
                    original_solution = result_map.get(str(dep))
                    if original_solution is True:
                        # Trivial task, no need to delete and re-run
                        continue

                    if original_solution:
                        # Original solution is something other than None or False.
                        result_map.delete(str(dep))

                maybe_spawn_tasks(
                    rocket,
                    positive_examples,
                    dependency_map[pkey],
                    result_map,
                    running_tasks,
                    in_flight,
                    inst_spec_p=inst_spec_p,
                    safe_insts=safe_insts,
                    collection=collection,
                )
                continue

            # Do not allow self-dependency
            invar = [inv for inv in invar if str(inv) != pkey]

            # Now we have an invariant for sure. Check if any of the preds that we used in the result
            # has returned False by now. If so, we need to re-synthesize the invariant.
            solution_is_valid = True
            for child in invar:
                # We have no yet processed the child's result. Therefore, we will not lookup its map.
                # In case the child (eventually or already has) failed, the child will be responsible to respawn the task.
                cached = get_completed_result(in_flight, result_map, child)
                if cached is False:
                    solution_is_valid = False
                    break

            if not solution_is_valid:
                # Delete the result of current task
                result_map.delete(pkey)

                # retry the current task
                maybe_spawn_tasks(
                    rocket,
                    positive_examples,
                    [pred],
                    result_map,
                    running_tasks,
                    in_flight,
                    inst_spec_p=inst_spec_p,
                    safe_insts=safe_insts,
                    collection=collection,
                )
            else:
                logger.debug(f"Got valid solution for {pkey} : {invar}")
                # We have a valid solution. Add dependencies to the dependency map.
                for child in invar:
                    key = str(child)
                    
                    if key not in dependency_map:
                        dependency_map[key] = []
                    
                    dependency_map[key].append(pred)

                    # Keep track of impls that have been synthesized
                    if key.startswith("impl"):
                        base_key, const_mask = key.rsplit("_", 1)
                        const, mask = const_mask.split(",")
                        tried_consts = result_map.get(base_key)
                        if tried_consts:
                            tried_consts = pickle.loads(tried_consts)
                        else:
                            tried_consts = set()
                        mask = int(mask) if mask != 'None' else None
                        tried_consts.add((int(const), mask))
                        result_map[base_key] = pickle.dumps(tried_consts)
                        
                # Spawn tasks for children if we haven't already
                maybe_spawn_tasks(
                    rocket,
                    positive_examples,
                    invar,
                    result_map,
                    running_tasks,
                    in_flight,
                    force=False,
                    inst_spec_p=inst_spec_p,
                    safe_insts=safe_insts,
                    collection=collection,
                )

    logger.info("[*] All invariants synthesized")
    loop.close()
    return True


# NO fence, jal, ebreak, ecall

ALU_R_INST_STARTS = 54956 - 4
ALU_I_INST_STARTS = 54952 - 4
SFT_R_INST_STARTS = 54960 - 4
SFT_I_INST_STARTS = 54952 - 4
LOAD_IMM_INST = 54948 - 4
CMP_R_INST = 54956 - 4
CMP_I_INST = 54956 - 4

inst_starts = {
    "add": ALU_R_INST_STARTS,
    "sub": ALU_R_INST_STARTS,
    "xor": ALU_R_INST_STARTS,
    "and": ALU_R_INST_STARTS,
    "or": ALU_R_INST_STARTS,
    # "mul": ALU_R_INST_STARTS,
    # "mulh": ALU_R_INST_STARTS,
    # "mulhsu": ALU_R_INST_STARTS,
    # "mulhu": ALU_R_INST_STARTS,
    # "div": ALU_R_INST_STARTS,
    # "divu": ALU_R_INST_STARTS,
    # "rem": ALU_R_INST_STARTS,
    # "remu": ALU_R_INST_STARTS,

    "addi": ALU_I_INST_STARTS,
    "xori": ALU_I_INST_STARTS,
    "ori": ALU_I_INST_STARTS,
    "andi": ALU_I_INST_STARTS,

    "sll": SFT_R_INST_STARTS,
    "srl": SFT_R_INST_STARTS,
    "sra": SFT_R_INST_STARTS,

    "slli": SFT_I_INST_STARTS,
    "srli": SFT_I_INST_STARTS,
    "srai": SFT_I_INST_STARTS,

    "lui": LOAD_IMM_INST,
    "auipc": LOAD_IMM_INST,

    "slt": CMP_R_INST,
    "sltu": CMP_R_INST,

    "slti": CMP_I_INST,
    "sltiu": CMP_I_INST,

}

app = typer.Typer()

@app.command()
def learn_invariant(
    prgm_file: Annotated[str, typer.Argument(help="The path to the program file in btor format")]="./targets/rocket.btor",
    sims_dir: Annotated[str, typer.Argument(help="The path to the first trace file")]="./pexs",
    # f1: Annotated[str, typer.Argument(help="The path to the first trace file")]="./boom/logs/add-1.json",
    # f2: Annotated[str, typer.Argument(help="The path to the second trace file")]="./boom/logs/add-2.json",
    # start_point: Annotated[int, typer.Argument(help="The starting point of the trace")]=54956,
    instr_spec: Annotated[str, typer.Argument(help="RISCV Instruction specification file")]="./spec/instr_dict.yaml",
    safe_instructions: Annotated[List[str], typer.Argument(help="List of safe instructions")]=None,
    logfile: Annotated[str, typer.Option(help="The path to the log file")]="hl-conjunct.log",
    loglevel: Annotated[str, typer.Option(help="The log level")]="INFO",
):
    ray.init(namespace="conjunct")

    # Add a logger to the file
    root = logger.getLogger()
    root.setLevel(logger.INFO)
    # logger.add(logfile, level=loglevel)

    with open(prgm_file) as fd:
        prgm_data = fd.read()

    prgm = BtorPrgm(prgm_data)
    state = prgm.init_state()

    positive_examples = []
    for inst, start_point in inst_starts.items():
        print(f"Expanding example {inst}")
        f1 = f'{sims_dir}/logs/{inst}/{inst}-1.json'
        f2 = f'{sims_dir}/logs/{inst}/{inst}-2.json'
        inst_examples = expand_concrete_example(f1, f2, start_point, state)
        positive_examples.extend(inst_examples)

    instruction_spec = yaml.safe_load(open(instr_spec))
    if not safe_instructions:
        safe_instructions = inst_starts.keys()
    
    # Initialize safe instruction predicate
    IsSafeInstrPred.initialize(instruction_spec, safe_instructions)

    top_pred = EqPred(prgm.assertion)
    # top_pred = EqPredConst(2372, 0)
    # top_pred = IsSafeInstrPred(1626)

    result = dfs_no_recurse(prgm_data, positive_examples, top_pred, instr_spec, safe_instructions)

    assert result, "Invariant could not be synthesized!"


@app.command()  
def get_invar(
    prgm_file: Annotated[str, typer.Argument(help="The path to the program file in btor format")]="./targets/rocket.btor",
    instr_spec: Annotated[str, typer.Argument(help="RISCV Instruction specification file")]="./spec/instr_dict.yaml",
    safe_instructions: Annotated[List[str], typer.Argument(help="List of safe instructions")]=None,
):
    with open(prgm_file) as fd:
        prgm_data = fd.read()

    prgm = BtorPrgm(prgm_data)
    top_pred = EqPred(prgm.assertion)

    instruction_spec = yaml.safe_load(open(instr_spec))
    if not safe_instructions:
        safe_instructions = inst_starts.keys()
    
    # Initialize safe instruction predicate
    IsSafeInstrPred.initialize(instruction_spec, safe_instructions)

    invar = get_invar_internal(top_pred)

    assert prgm.check_invariant(invar), "Invariant is not valid!"

    # Pretty print the invariant
    state = prgm.blank_state()

    print(f"=== Printing Invariant ({len(invar)} Predicates) ===")

    lines = []

    for pred in invar:
        if isinstance(pred, EqPred):
            if pred.lvar == prgm.assertion:
                continue
            lines.append(f"\t⋀ {state.rvarmap[pred.lvar]} == {state.rvarmap[pred.rvar]}")
        elif isinstance(pred, EqPredConst):
            lines.append(f"\t⋀ {state.rvarmap[pred.lvar]} := {pred.val}")
        elif isinstance(pred, IsSafeInstrPred):
            lines.append(f"\t⋀ {state.rvarmap[pred.lvar]} ∈ Safe")
        else:
            raise ValueError(f"Unknown predicate type: {type(pred)}")

    print("\n".join(sorted(lines)))
    get_start_end_time(top_pred)
    

def get_start_end_time(top_pred):
    result_map = redis.Redis()
    top_pred_stats = result_map.lrange(f"stats:{str(top_pred)}", 0, -1)
    for stats in top_pred_stats:
        stat = json.loads(stats)
        if stat["type"] == "start":
            start_time = stat["time"]
    
    key_list = result_map.keys("stats:*")
    stats_list = []
    for key in key_list:
        stats_list.append(json.loads(result_map.lrange(key, 0, 0)[0]))
    stats_list.sort(key= lambda x: x["time"], reverse=True)
    synthesize_time = stats_list[0]["time"] - start_time
    print(f"All predicates synthesized in {synthesize_time} seconds. ")

    
def get_invar_internal(top_pred: Predicate):
    result_map = redis.Redis()

    def get_result(predicate):
        key = str(predicate)
        value = result_map.get(key)
        if value is None:
            return None
        return pickle.loads(value)
    
    visited = set()
    invar = set([top_pred])

    queue = deque()
    queue.append(str(top_pred))

    while queue:
        front_pred = queue.popleft()
        visited.add(front_pred)
        deps = get_result(front_pred)

        if deps is None or deps is False:
            logger.critical(f"No solution for: {front_pred}")
            raise ValueError(f"No solution for: {front_pred}")
            continue
        elif deps is True:
            visited.add(front_pred)
        else:
            for dep in deps:
                dep_k = str(dep)
                if dep_k in visited or dep_k in queue:
                    continue
                else:
                    queue.append(dep_k)
                    invar.add(dep)

    return list(invar)

   
if __name__ == "__main__":
    app()
