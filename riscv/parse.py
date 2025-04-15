from .constants import *
import re
import glob
import os
import pprint
import logging
import yaml
import argparse


from loguru import logger

pp = pprint.PrettyPrinter(indent=2)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:: %(message)s")


def process_enc_line(line, ext):
    """
    This function processes each line of the encoding files (rv*). As part of
    the processing, the function ensures that the encoding is legal through the
    following checks::

        - there is no over specification (same bits assigned different values)
        - there is no under specification (some bits not assigned values)
        - bit ranges are in the format hi..lo=val where hi > lo
        - value assigned is representable in the bit range
        - also checks that the mapping of arguments of an instruction exists in
          arg_lut.

    If the above checks pass, then the function returns a tuple of the name and
    a dictionary containing basic information of the instruction which includes:
        - variables: list of arguments used by the instruction whose mapping
          exists in the arg_lut dictionary
        - encoding: this contains the 32-bit encoding of the instruction where
          '-' is used to represent position of arguments and 1/0 is used to
          reprsent the static encoding of the bits
        - extension: this field contains the rv* filename from which this
          instruction was included
        - match: hex value representing the bits that need to match to detect
          this instruction
        - mask: hex value representin the bits that need to be masked to extract
          the value required for matching.
    """
    single_dict = {}

    # fill all bits with don't care. we use '-' to represent don't care
    # TODO: hardcoded for 32-bits.
    encoding = ["-"] * 32

    # get the name of instruction by splitting based on the first space
    [name, remaining] = line.split(" ", 1)

    # replace dots with underscores as dot doesn't work with C/Sverilog, etc
    name = name.replace(".", "_")

    # remove leading whitespaces
    remaining = remaining.lstrip()

    # check each field for it's length and overlapping bits
    # ex: 1..0=5 will result in an error --> x<y
    # ex: 5..0=0 2..1=2 --> overlapping bits
    for s2, s1, entry in fixed_ranges.findall(remaining):
        msb = int(s2)
        lsb = int(s1)

        # check msb < lsb
        if msb < lsb:
            logging.error(
                f'{line.split(" ")[0]:<10} has position {msb} less than position {lsb} in it\'s encoding'
            )
            raise SystemExit(1)

        # illegal value assigned as per bit width
        entry_value = int(entry, 0)
        if entry_value >= (1 << (msb - lsb + 1)):
            logging.error(
                f'{line.split(" ")[0]:<10} has an illegal value {entry_value} assigned as per the bit width {msb - lsb}'
            )
            raise SystemExit(1)

        for ind in range(lsb, msb + 1):
            # overlapping bits
            if encoding[31 - ind] != "-":
                logging.error(
                    f'{line.split(" ")[0]:<10} has {ind} bit overlapping in it\'s opcodes'
                )
                raise SystemExit(1)
            bit = str((entry_value >> (ind - lsb)) & 1)
            encoding[31 - ind] = bit

    # extract bit pattern assignments of the form hi..lo=val
    remaining = fixed_ranges.sub(" ", remaining)

    # do the same as above but for <lsb>=<val> pattern. single_fixed is a regex
    # expression present in constants.py
    for lsb, value, drop in single_fixed.findall(remaining):
        lsb = int(lsb, 0)
        value = int(value, 0)
        if encoding[31 - lsb] != "-":
            logging.error(
                f'{line.split(" ")[0]:<10} has {lsb} bit overlapping in it\'s opcodes'
            )
            raise SystemExit(1)
        encoding[31 - lsb] = str(value)

    # convert the list of encodings into a single string for match and mask
    match = "".join(encoding).replace("-", "0")
    mask = "".join(encoding).replace("0", "1").replace("-", "0")

    # check if all args of the instruction are present in arg_lut present in
    # constants.py
    args = single_fixed.sub(" ", remaining).split()
    encoding_args = encoding.copy()
    locations = dict()
    for a in args:
        if a not in arg_lut:
            logging.error(
                f" Found variable {a} in instruction {name} whose mapping in arg_lut does not exist"
            )
            raise SystemExit(1)
        else:
            (msb, lsb) = arg_lut[a]
            for ind in range(lsb, msb + 1):
                # overlapping bits
                if encoding_args[31 - ind] != "-":
                    logging.error(
                        f" Found variable {a} in instruction {name} overlapping {encoding_args[31 - ind]} variable in bit {ind}"
                    )
                    raise SystemExit(1)
                encoding_args[31 - ind] = a
                locations[a] = [msb, lsb]

    # update the fields of the instruction as a dict and return back along with
    # the name of the instruction
    single_dict["encoding"] = "".join(encoding)
    single_dict["variable_fields"] = args
    single_dict["extension"] = [ext.split("/")[-1]]
    single_dict["match"] = hex(int(match, 2))
    single_dict["mask"] = hex(int(mask, 2))
    single_dict["arg_locs"] = locations

    return (name, single_dict)


def create_inst_dict(file_filter, include_pseudo=False, include_pseudo_ops=[]):
    """
    This function return a dictionary containing all instructions associated
    with an extension defined by the file_filter input. The file_filter input
    needs to be rv* file name with out the 'rv' prefix i.e. '_i', '32_i', etc.

    Each node of the dictionary will correspond to an instruction which again is
    a dictionary. The dictionary contents of each instruction includes:
        - variables: list of arguments used by the instruction whose mapping
          exists in the arg_lut dictionary
        - encoding: this contains the 32-bit encoding of the instruction where
          '-' is used to represent position of arguments and 1/0 is used to
          reprsent the static encoding of the bits
        - extension: this field contains the rv* filename from which this
          instruction was included
        - match: hex value representing the bits that need to match to detect
          this instruction
        - mask: hex value representin the bits that need to be masked to extract
          the value required for matching.

    In order to build this dictionary, the function does 2 passes over the same
    rv<file_filter> file. The first pass is to extract all standard
    instructions. In this pass, all pseudo ops and imported instructions are
    skipped. For each selected line of the file, we call process_enc_line
    function to create the above mentioned dictionary contents of the
    instruction. Checks are performed in this function to ensure that the same
    instruction is not added twice to the overall dictionary.

    In the second pass, this function parses only pseudo_ops. For each pseudo_op
    this function checks if the dependent extension and instruction, both, exit
    before parsing it. The pseudo op is only added to the overall dictionary is
    the dependent instruction is not present in the dictionary, else its
    skipped.


    """
    instr_dict = {}

    # file_names contains all files to be parsed in the riscv-opcodes directory
    file_names = []
    for fil in file_filter:
        file_names += glob.glob(f"{fil}")
    file_names.sort(reverse=True)
    # first pass if for standard/regular instructions
    logging.debug("Collecting standard instructions first")
    for f in file_names:
        logging.debug(f"Parsing File: {f} for standard instructions")
        with open(f) as fp:
            lines = (line.rstrip() for line in fp)  # All lines including the blank ones
            lines = list(line for line in lines if line)  # Non-blank lines
            lines = list(
                line for line in lines if not line.startswith("#")
            )  # remove comment lines

        # go through each line of the file
        for line in lines:
            # if the an instruction needs to be imported then go to the
            # respective file and pick the line that has the instruction.
            # The variable 'line' will now point to the new line from the
            # imported file

            # ignore all lines starting with $import and $pseudo
            if "$import" in line or "$pseudo" in line:
                continue
            logging.debug(f"     Processing line: {line}")

            # call process_enc_line to get the data about the current
            # instruction
            (name, single_dict) = process_enc_line(line, f)

            # if an instruction has already been added to the filtered
            # instruction dictionary throw an error saying the given
            # instruction is already imported and raise SystemExit
            if name in instr_dict:
                var = instr_dict[name]["extension"]
                if instr_dict[name]["encoding"] != single_dict["encoding"]:
                    err_msg = f"instruction : {name} from "
                    err_msg += f'{f.split("/")[-1]} is already '
                    err_msg += f"added from {var} but each have different encodings for the same instruction"
                    logging.error(err_msg)
                    raise SystemExit(1)
                instr_dict[name]["extension"].append(single_dict["extension"])

            # update the final dict with the instruction
            instr_dict[name] = single_dict

    # second pass if for pseudo instructions
    logging.debug("Collecting pseudo instructions now")
    for f in file_names:
        logging.debug(f"Parsing File: {f} for pseudo_ops")
        with open(f) as fp:
            lines = (line.rstrip() for line in fp)  # All lines including the blank ones
            lines = list(line for line in lines if line)  # Non-blank lines
            lines = list(
                line for line in lines if not line.startswith("#")
            )  # remove comment lines

        # go through each line of the file
        for line in lines:
            # ignore all lines not starting with $pseudo
            if "$pseudo" not in line:
                continue
            logging.debug(f"     Processing line: {line}")

            # use the regex pseudo_regex from constants.py to find the dependent
            # extension, dependent instruction, the pseudo_op in question and
            # its encoding
            (ext, orig_inst, pseudo_inst, line) = pseudo_regex.findall(line)[0]

            ext = os.path.join(os.path.dirname(f), ext)
            # check if the file of the dependent extension exist. Throw error if
            # it doesn't
            if not os.path.exists(ext):
                ext1 = f"unratified/{ext}"
                if not os.path.exists(ext1):
                    logging.error(
                        f"Pseudo op {pseudo_inst} in {f} depends on {ext} which is not available"
                    )
                    raise SystemExit(1)
                else:
                    ext = ext1

            # check if the dependent instruction exist in the dependent
            # extension. Else throw error.
            found = False
            for oline in open(ext):
                if not re.findall(f"^\s*{orig_inst}", oline):
                    continue
                else:
                    found = True
                    break
            if not found:
                logging.error(
                    f"Orig instruction {orig_inst} not found in {ext}. Required by pseudo_op {pseudo_inst} present in {f}"
                )
                raise SystemExit(1)

            (name, single_dict) = process_enc_line(pseudo_inst + " " + line, f)
            # add the pseudo_op to the dictionary only if the original
            # instruction is not already in the dictionary.
            if (
                orig_inst.replace(".", "_") not in instr_dict
                or include_pseudo
                or name in include_pseudo_ops
            ):
                # update the final dict with the instruction
                if name not in instr_dict:
                    instr_dict[name] = single_dict
                    logging.debug(f"    including pseudo_ops:{name}")
            else:
                logging.debug(
                    f"Skipping pseudo_op {pseudo_inst} since original instruction {orig_inst} already selected in list"
                )

    # third pass if for imported instructions
    logging.debug("Collecting imported instructions")
    for f in file_names:
        logging.debug(f"Parsing File: {f} for imported ops")
        with open(f) as fp:
            lines = (line.rstrip() for line in fp)  # All lines including the blank ones
            lines = list(line for line in lines if line)  # Non-blank lines
            lines = list(
                line for line in lines if not line.startswith("#")
            )  # remove comment lines

        # go through each line of the file
        for line in lines:
            # if the an instruction needs to be imported then go to the
            # respective file and pick the line that has the instruction.
            # The variable 'line' will now point to the new line from the
            # imported file

            # ignore all lines starting with $import and $pseudo
            if "$import" not in line:
                continue
            logging.debug(f"     Processing line: {line}")

            (import_ext, reg_instr) = imported_regex.findall(line)[0]

            # check if the file of the dependent extension exist. Throw error if
            # it doesn't
            if not os.path.exists(import_ext):
                ext1 = f"unratified/{import_ext}"
                if not os.path.exists(ext1):
                    logging.error(
                        f"Instruction {reg_instr} in {f} cannot be imported from {import_ext}"
                    )
                    raise SystemExit(1)
                else:
                    ext = ext1
            else:
                ext = import_ext

            # check if the dependent instruction exist in the dependent
            # extension. Else throw error.
            found = False
            for oline in open(ext):
                if not re.findall(f"^\s*{reg_instr}", oline):
                    continue
                else:
                    found = True
                    break
            if not found:
                logging.error(
                    f"imported instruction {reg_instr} not found in {ext}. Required by {line} present in {f}"
                )
                logging.error(f"Note: you cannot import pseudo ops.")
                raise SystemExit(1)

            # call process_enc_line to get the data about the current
            # instruction
            (name, single_dict) = process_enc_line(oline, f)

            # if an instruction has already been added to the filtered
            # instruction dictionary throw an error saying the given
            # instruction is already imported and raise SystemExit
            if name in instr_dict:
                var = instr_dict[name]["extension"]
                if instr_dict[name]["encoding"] != single_dict["encoding"]:
                    err_msg = f"imported instruction : {name} in "
                    err_msg += f'{f.split("/")[-1]} is already '
                    err_msg += f"added from {var} but each have different encodings for the same instruction"
                    logging.error(err_msg)
                    raise SystemExit(1)
                instr_dict[name]["extension"].append(single_dict["extension"])

            # update the final dict with the instruction
            instr_dict[name] = single_dict
    return instr_dict


def generate_rkt_assembler(instr_dict):
    body = [
        "#lang rosette",
        "(provide (all-defined-out))",
        "(require racket/lazy-require)",
        '(lazy-require ["../lang.rkt" (State-vs State-vs-set!)])',
    ]

    inst_and_fn = []

    for k, info in sorted(instr_dict.items()):
        fields = []

        rev_arg_map = dict([(v[0], k) for k, v in info["arg_locs"].items()])

        ptr = 31
        last = 31
        sym_vars = []
        sym_saves = []
        while ptr >= 0:
            if ptr in rev_arg_map:
                if last > ptr:
                    # Need to copy over concrete bits
                    value = info["encoding"][31 - last : 31 - ptr]
                    sz = last - ptr
                    fields.append(f"(bv #b{value} {sz})")
                argname = rev_arg_map[ptr]
                fields.append(argname)
                ptr = info["arg_locs"][argname][1] - 1
                last = ptr

                # Add to symvars for (create-inst) function
                sz = info["arg_locs"][argname][0] - info["arg_locs"][argname][1] + 1
                sym_vars.append(f"  (define-symbolic* {argname} (bitvector {sz}))")
                sym_saves.append(
                    f"    (State-vs-set! S (- idx {len(sym_saves) + 1}) {argname})"
                )
            else:
                ptr -= 1

        if last > ptr:
            # Need to copy over concrete bits
            value = info["encoding"][31 - last : 31 - ptr]
            sz = last - ptr
            fields.append(f"(bv #b{value} {sz})")

        operands = info["variable_fields"]
        opstr = " ".join(operands)
        f = " ".join(fields)
        asm = [f"(define (asm-{k} {opstr})", f"  (concat {f})" ")"]

        create = [
            f"(define (create-{k} #:fuzz [S #f])",
            *sym_vars,
        ]

        if sym_saves:
            create.extend(
                [
                    "  (when (not (false? S)) (begin",
                    "    (define idx (vector-length (State-vs S)))",
                    *sym_saves,
                    "))",
                ]
            )

        create.extend(
            [
                f"  (asm-{k} {opstr})",
                ")",
            ]
        )

        mask = f"(bv #x{info['mask'][2:]} 32)"
        match = f"(bv #x{info['match'][2:]} 32)"

        recognize_inst = [
            f"(define (is-{k}? val)",
            f"  (bveq (bvand val {mask}) {match}))",
        ]

        body.append("\n")
        body.append(f";-------- {k}")
        body.extend(asm)
        body.append("")
        body.extend(create)
        body.append("")
        body.extend(recognize_inst)

        # Add to list of all instructions
        inst_and_fn.append(f'(cons "{k}" create-{k})')

    # Add a special entry, NOP, that is mapped to addi
    if "addi" in instr_dict:
        logger.info("Added nop to available instructions")
        create = [
            "(define (create-nop #:fuzz [S #f])",
            "  (asm-addi (bv 0 5) (bv 0 5) (bv 0 12)))",
        ]
        body.append("\n")
        body.append(";-------- nop")
        body.extend(create)
        inst_and_fn.append('(cons "nop" create-nop)')
    else:
        logger.warning("[x] Skipped creating NOP: addi not in list!")

    inst_and_fn = "\n".join(inst_and_fn)
    inst_iterator = [
        "(define (create-all-insts #:filter [fil '()])",
        "  (map (lambda (v) ((cdr v)))",
        "    (filter (lambda (v) (not (member (car v) fil)))",
        f"    (list {inst_and_fn})",
        ")))",
    ]

    body.append("")
    body.extend(inst_iterator)
    return "\n".join(body)


if __name__ == "__main__":
    argp = argparse.ArgumentParser()

    argp.add_argument("files", type=str, nargs="+", help="Opcode files to parse")
    argp.add_argument(
        "-o", type=str, default="instr_dict.yaml", help="Output file to write to"
    )

    argp.add_argument("--rkt", type=str, help="Generate rkt assembler for instructions")

    args = argp.parse_args()

    instr_dict = create_inst_dict(args.files, False)

    if args.rkt:
        rkt = generate_rkt_assembler(instr_dict)
        with open(args.rkt, "w") as fd:
            fd.write(rkt)

    with open(args.o, "w") as outfile:
        yaml.dump(instr_dict, outfile, default_flow_style=False)
