import argparse
import json
import os
import re

verilator_pargma = "/*verilator public_flat_rd*/"

parser = argparse.ArgumentParser(
    prog="Annotator",
    description="Verilog annototor for verilator",
    epilog="Text at the bottom of help")


parser.add_argument("vrilog_file")

args = parser.parse_args()

v_file = args.vrilog_file

name_prefix = "TOP.TestDriver.testHarness.chiptop0.system.tile_prci_domain.tile_reset_domain_tile"
reg_list = open("reglist.txt", "w")
mem_list = open("memlist.txt", "w")
module_set = []
memory_set = {}

replace_dict = {}


def replace_reg(file):
    with open(file, "r") as v_file:
        lines = v_file.readlines()
        for line in lines:
            token = re.split(r'[ \t]+', line.strip())
            if token[0] == "reg":
                # modify files
                reg_name = token[2] if token[1][0] == '[' else token[1]
                if reg_name[0] == "\\" and reg_name != "\$auto$verilog_backend.cc:2253:dump_module$2844":
                    dot_pos = reg_name.find(".")
                    replace_dict[reg_name] = reg_name[1:dot_pos] + "DOT" + reg_name[dot_pos + 1:]
    with open(file, "r") as v_file:
        filedata = v_file.read()

        # Replace the target string
    for k,v, in replace_dict.items():
        print(k,v)
        filedata = filedata.replace(k, v)

    # Write the file out again
    with open(file, 'w') as v_file:
        v_file.write(filedata) 

def annotate(file):
    name = "core"
    temp_file_name = file + '-a.sv'
    temp_file = open(temp_file_name, 'w')
    module_file_name = file    
    with open(module_file_name, "r") as v_file:
        lines = v_file.readlines()
        for line in lines:
            token = re.split(r'[ \t]+', line.strip())
            if token[0] == "reg" and token[1] != "\$auto$verilog_backend.cc:2253:dump_module$2844":
                # modify files
                reg_name = token[2] if token[1][0] == '[' else token[1]
                if len(token) >= 4 and token[3][0] == "[":
                    reg_length = 1
                    memory_set[f'{name_prefix}.{name}.{reg_name}'] = str(reg_length)
                else:
                    reg_list.write(f'{name_prefix}.{name}.{reg_name}\n')
               
    
                semicolon = line.find(';')
                output_line = line[:semicolon] + " " + verilator_pargma + " " + line[semicolon:]
                temp_file.write(output_line)
            else:
                    temp_file.write(line)

        temp_file.close()
        os.remove(module_file_name)
        os.rename(temp_file_name, module_file_name)


replace_reg(v_file)
annotate(v_file)
for pair in memory_set.items():
    mem_list.write(f"{pair[0]}\n")

reg_list.close()
mem_list.close()





