# Implements riscv instruction generator for symex

from riscv.parse import create_inst_dict
import functools
from symex.solver import SolverTerm
import copy


class InstGen:
    """
    Class to generate symbolic/concrete instructions for a given ISA.

    :param isa: List of paths to ISA files
    :param solver: Solver object

    Methods:
        assemble: Assembles an instruction from the given operands
        create_assemblers: Creates assemblers for each instruction in the ISA
        create: Creates a symbolic instruction
        create_all: Creates all symbolic instructions
        is_inst: Checks if the given bytes represent an instruction
        recognize: Recognizes the instruction from the given bytes

    Example Usage:
        >>> from symex.instgen import InstGen
        >>> from symex.solver import Solver
        >>> solver = Solver(**{'produce-models': 'true'})
        >>> instgen = InstGen(["./third-party/riscv-opcodes/rv_i"], solver)

        # Assemble an instruction
        >>> inst = instgen.assemble('addi', rd=solver.bvv(0, 5), rs1=solver.bvv(0, 5), imm12=solver.bvv(0, 12))

        # Create a symbolic instruction
        >>> add_inst = instgen.create('add')

        # Check if the given bytes represent an instruction
        >>> t = instgen.is_inst('add', add_inst)

        # Recognize the instruction from the given bytes
        >>> t = instgen.recognize(add_inst)   # t is 'add'

        # Create all symbolic instructions
        >>> instructions = instgen.create_all()
    """

    def __init__(self, isa, solver):
        self._solver = solver
        self.isa = isa

        self.assemblers = dict()
        self.symbolic_creators = dict()
        self.recognizers = dict()

        instr_dict = create_inst_dict(isa)
        self.create_assemblers(instr_dict)

    def create_assemblers(self, instr_dict):
        for k, info in sorted(instr_dict.items()):
            fields = []

            rev_arg_map = dict([(v[0], k) for k, v in info["arg_locs"].items()])

            ptr = 31
            last = 31
            sym_vars = []

            while ptr >= 0:
                if ptr in rev_arg_map:
                    if last > ptr:
                        # Need to copy over concrete bits
                        value = int(info["encoding"][31 - last : 31 - ptr], base=2)
                        sz = last - ptr
                        fields.append((value, sz))
                    argname = rev_arg_map[ptr]
                    fields.append(argname)
                    ptr = info["arg_locs"][argname][1] - 1
                    last = ptr

                    # Add to symvars for (create-inst) function
                    sz = info["arg_locs"][argname][0] - info["arg_locs"][argname][1] + 1
                    sym_vars.append((argname, sz))
                else:
                    ptr -= 1

            if last > ptr:
                # Need to copy over concrete bits
                value = int(info["encoding"][31 - last : 31 - ptr], base=2)
                sz = last - ptr
                fields.append((value, sz))

            # Create a lambda function that will assemble an instruction. The operand names for the function are in `operands` and the `fields`
            # contains a mix of concrete bitvectors and operand names. The lambda function needs to return a concatenation of operands and concrete
            # bits in the order specified by `fields`.

            self.assemblers[k] = functools.partial(
                lambda operands, fields, solver, inst_name: InstTerm(
                    solver, inst_name, operands, fields
                ),
                fields=copy.deepcopy(fields),
                solver=self._solver,
                inst_name=k,
            )

            self.symbolic_creators[k] = functools.partial(
                lambda svars, asm, solver: asm(
                    dict([(v[0], solver.new_var(v[0], v[1])) for v in svars])
                ),
                svars=copy.deepcopy(sym_vars),
                solver=self._solver,
                asm=self.assemblers[k],
            )
            mask = int(info["mask"][2:], base=16)
            match = int(info["match"][2:], base=16)
            self.recognizers[k] = functools.partial(
                lambda bv, mask, match, solver: (bv & solver.bvv(mask, 32))
                == solver.bvv(match, 32),
                mask=mask,
                match=match,
                solver=self._solver,
            )

        if "addi" in instr_dict:
            self.symbolic_creators["nop"] = lambda: self.assemblers["addi"](
                {
                    "rd": self._solver.bvv(0, 5),
                    "rs1": self._solver.bvv(0, 5),
                    "imm12": self._solver.bvv(0, 12),
                }
            )

    def assemble(self, inst_name, **kwargs):
        return self.assemblers[inst_name](kwargs)

    def is_inst(self, inst_name, bytes):
        return self.recognizers[inst_name](bytes).simplify()

    def recognize(self, bytes):
        for k in self.recognizers:
            if self.is_inst(k, bytes):
                return k
        return None

    def create(self, inst_name):
        return self.symbolic_creators[inst_name]()

    def create_all(self):
        insts = []
        for k in self.symbolic_creators:
            insts.append(self.symbolic_creators[k]())
        return insts


class InstTerm(SolverTerm):
    def __init__(self, solver, inst_name, operands, fields):
        self._solver = solver
        self.inst_name = inst_name
        self._operands = operands
        self.fields = [
            self._solver.bvv(fld[0], fld[1])
            if not isinstance(fld, str)
            else self._operands[fld]
            for fld in fields
        ]

    @property
    def var(self):
        var = functools.reduce(lambda x, y: x.append(y), self.fields)
        var.simplify()
        return var.var

    def simplify(self):
        return self
