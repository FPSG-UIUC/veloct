# NO fence, jal, ebreak, ecall

ALU_R_INST_STARTS = 64712
ALU_I_INST_STARTS = 64708
SFT_R_INST_STARTS = 64718
SFT_I_INST_STARTS = 64708
LOAD_IMM_INST = 64704
CMP_R_INST = 64712
CMP_I_INST = 64712

FORWARD_STEP = 34

BOOM_BTOR_FILE_NAME = "targets/smallboomcore.btor"
BOOM_LOG_FOLDER = "./pexs/logs-smallboom/"

inst_starts = {
    "add": ALU_R_INST_STARTS,
    "sub": ALU_R_INST_STARTS,
    "xor": ALU_R_INST_STARTS,
    "and": ALU_R_INST_STARTS,
    "or": ALU_R_INST_STARTS,

    "mul": ALU_R_INST_STARTS,
    "mulh": ALU_R_INST_STARTS,
    "mulhsu": ALU_R_INST_STARTS,
    "mulhu": ALU_R_INST_STARTS,
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
    # "auipc": LOAD_IMM_INST,

    "slt": CMP_R_INST,
    "sltu": CMP_R_INST,

    "slti": CMP_I_INST,
    "sltiu": CMP_I_INST,
}

regexs = [
    ("gate.int_issue_unit_slots_{idx}_state", "gate.int_issue_unit_slots_{idx}_", range(8)),  #  idx: 0-7
    ("gate.fp_pipeline_fp_issue_unit_slots_{idx}_state", "gate.fp_pipeline_fp_issue_unit_slots_{idx}_", range(8)),  #  idx: 0-7
    ("gate.fp_pipeline_fpiu_unit_queue_valids_{idx}", "gate.fp_pipeline_fpiu_unit_queue_uops_{idx}", range(7)),   # idx: 0-6
    ("gate.fp_pipeline_fpiu_unit_fp_sdq_valids_{idx}", "gate.fp_pipeline_fpiu_unit_fp_sdq_uops_{idx}", range(3)),  # idx: 0-2
    ("gate.fp_pipeline_fpiu_unit_fpu_r_valids_{idx}", "gate.fp_pipeline_fpiu_unit_fpu_r_uops_{idx}", range(4)),  # idx: 0-3
    ("gate.csr_exe_unit_alu_r_valids_{idx}", "gate.csr_exe_unit_alu_r_uops_{idx}", range(3)),  # idx: 0-2
    ("gate.csr_exe_unit_imul_r_valids_{idx}", "gate.csr_exe_unit_imul_r_uops_{idx}", range(3)),  # idx: 0-2
    ("gate.csr_exe_unit_imul_imul_inPipe_valid", "gate.csr_exe_unit_imul_imul_inPipe_bits_"),
    ("gate.csr_exe_unit_ifpu_r_valids_{idx}", "gate.csr_exe_unit_ifpu_r_uops_{idx}", range(2)),
    ("gate.csr_exe_unit_ifpu_ifpu_inPipe_valid", "gate.csr_exe_unit_ifpu_ifpu_inPipe_bits_"),
    ("gate.mem_issue_unit_slots_{idx}_state", "gate.mem_issue_unit_slots_{idx}_slot", range(8)),  # idx: 0-7
    ("gate.rename_stage_r_valid", "gate.rename_stage_r_uop_"),
    ("gate.csr_exe_unit_queue_valids_{idx}", "gate.csr_exe_unit_queue_uops_{idx}", range(5)),
    ("gate.fp_pipeline_fregister_read_exe_reg_valids_0", "gate.fp_pipeline_fregister_read_exe_reg_uops_0"),
    ("gate.iregister_read_rrd_valids_1_REG", "gate.iregister_read_rrd_uops_1_REG"),
    ("gate.iregister_read_exe_reg_valids_1", "gate.iregister_read_exe_reg_uops_1"),
    ("gate.fp_pipeline_fregister_read_rrd_valids_0_REG", "gate.fp_pipeline_fregister_read_uops_valids_0_REG"),
]

prs2_mask = [
    ("rename_stage_r_uop_lrs2_rtype", "rename_stage_r_uop_prs2"),
    ("fp_rename_stage_r_uop_lrs2_rtype", "fp_rename_stage_r_uop_prs2"),
    ("mem_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "mem_issue_unit_slots_{idx}_slot_uop_prs2", range(8)),
    ("int_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "int_issue_unit_slots_{idx}_slot_uop_prs2", range(8)),
    ("iregister_read_rrd_uops_{idx}_REG_lrs2_rtype", "iregister_read_rrd_uops_{idx}_REG_prs2", range(1, 2)) # iregister_read_rrd_uops_0_REG is not used
]

rob_regex = [
    
]
rob_exact = [
    
]

# fu_vars = [3208, 3247, 3278, 3310, 3342, 3374, 3406, 3438, 3791, 3771, 3751, 3731, 3711, 3691, 3671, 3535, 11947, 11922, 11897, 11872, 11847, 11822, 11797, 11759, 12232, 12224, 12216, 1613, 4817, 12096, 11762, 795, 2536]

uopc_vars = dict([(4667, 3189), (4678, 3230), (4689, 3261), (4700, 3293), (4711, 3325), (4722, 3357), (4733, 3389), (4744, 3421), (11983, 11930), (11994, 11905), (12005, 11880), (12016, 11855), (12027, 11830), (12038, 11805), (12049, 11780), (12060, 11742), (1699, 1557), (1700, 1558), (1701, 1559), (1702, 1560), (1703, 1561), (1704, 1562), (1705, 1563), (1677, 1628), (1678, 1629), (1679, 1630), (12228, 12210), (12220, 12209), (12212, 12208), (1616, 1423), (2520, 1317), (1665, 1664), (4802, 4800), (5099, 794), (12091, 12089)])
fu_vars = dict([(3208, 3189), (3247, 3230), (3278, 3261), (3310, 3293), (3342, 3325), (3374, 3357), (3406, 3389), (3438, 3421), (3791, 3544), (3771, 3546), (3751, 3555), (3731, 3563), (3711, 3571), (3691, 3579), (3671, 3587), (3535, 3528), (11947, 11930), (11922, 11905), (11897, 11880), (11872, 11855), (11847, 11830), (11822, 11805), (11797, 11780), (11759, 11742), (12232, 12210), (12224, 12209), (12216, 12208), (1613, 1423), (4817, 4800), (12096, 12089), (11762, 1664), (795, 794), (2536, 1317)])

fu_state_vars = [3189, 3230, 3261, 3293, 3325, 3357, 3389, 3421, 3544, 3546, 3555, 3563, 3571, 3579, 3587, 3528, 11930, 11905, 11880, 11855, 11830, 11805, 11780, 11742]
