# NO fence, jal, ebreak, ecall

ALU_R_INST_STARTS = 54956 - 4   # 16
ALU_I_INST_STARTS = 54952 - 4
SFT_R_INST_STARTS = 54960 - 4   # 18
SFT_I_INST_STARTS = 54952 - 4   # 16
LOAD_IMM_INST = 54948 - 4       # 16
CMP_R_INST = 54956 - 4
CMP_I_INST = 54956 - 4

FORWARD_STEP = 20

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