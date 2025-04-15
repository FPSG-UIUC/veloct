import argparse
import json
import os
import re

verilator_pargma = "/*verilator public_flat_rd*/"

parser = argparse.ArgumentParser(
    prog="Annotator",
    description="Verilog annototor for verilator",
    epilog="Text at the bottom of help")


parser.add_argument("hierachy_file")
parser.add_argument("verilog_root")

args = parser.parse_args()

hierachy_file = args.hierachy_file
v_root = args.verilog_root + "/"

with open(hierachy_file, "r") as hierachy:
    data = json.load(hierachy)

boomtile_root = data["instances"][0]["instances"][0]["instances"][12]["instances"][0]["instances"][7]
reg_name_prefix = "TOP.TestDriver.testHarness.chiptop0.system.tile_prci_domain.tile_reset_domain_tile"
module_set = []
memory_set = {}
reg_list = open("reglist.txt", "w")
mem_list = open("memlist.txt", "w")


def DFS(module, name_prefix):
    # adding pargma to each reg variable
    name = module["instance_name"]
    module_name = module["module_name"]

    if module_name[-4:] == "_ext" or module_name == "plusarg_reader":
        return
    if module_name in module_set:
        annotated = True
    else:
        annotated = False
        module_set.append(module_name)

    if not annotated:
        temp_file_name = v_root + module_name + '-a.sv'
        temp_file = open(temp_file_name, 'w')
    module_file_name = v_root + module_name + '.sv' if module_name != "plusarg_reader" else v_root + module_name + '.v'
    with open(module_file_name, "r") as v_file:
        lines = v_file.readlines()
        for line in lines:
            token = re.split(r'[ \t]+', line.strip())
            if token[0] == "reg":
                # modify files
                reg_name = token[2] if token[1][0] == '[' else token[1]
                if len(reg_name) > 6 and reg_name[:6] == "Memory":
                    reg_length = int(reg_name[9:-2]) + 1
                    memory_set[f'{name_prefix}.{name}.{reg_name[:6]}'] = str(reg_length)
                else:
                    reg_list.write(f'{name_prefix}.{name}.{reg_name[:-1]}\n')
                if not annotated:
                    semicolon = line.find(';')
                    output_line = line[:semicolon] + " " + verilator_pargma + " " + line[semicolon:]
                    temp_file.write(output_line)
            else:
                if not annotated:
                    temp_file.write(line)
    if not annotated:
        temp_file.close()
        os.remove(module_file_name)
        os.rename(temp_file_name, module_file_name)

    # search for files in next hierarchy
    if len(module["instances"]) != 0:
        for instance in module["instances"]:
            DFS(instance, name_prefix + "." + name)

DFS(boomtile_root, reg_name_prefix)
for pair in memory_set.items():
    mem_list.write(f"{pair[0]}\n")

reg_list.close()
mem_list.close()





