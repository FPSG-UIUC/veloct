# NO fence, jal, ebreak, ecall

ALU_R_INST_STARTS = 64448
ALU_I_INST_STARTS = 64444
SFT_R_INST_STARTS = 64448
SFT_I_INST_STARTS = 64444
LOAD_IMM_INST = 64444
CMP_R_INST = 64448
CMP_I_INST = 64448

FORWARD_STEP = 34

BOOM_BTOR_FILE_NAME = "targets/mediumboomcore.btor"
BOOM_LOG_FOLDER = "./pexs/logs-mediumboom/"

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
    ("gate.int_issue_unit_slots_{idx}_state", "gate.int_issue_unit_slots_{idx}_", range(20)),  #  idx: 0-7
    ("gate.fp_pipeline_fp_issue_unit_slots_{idx}_state", "gate.fp_pipeline_fp_issue_unit_slots_{idx}_", range(16)),  #  idx: 0-7
    ("gate.fp_pipeline_fpiu_unit_queue_valids_{idx}", "gate.fp_pipeline_fpiu_unit_queue_uops_{idx}", range(7)),   # idx: 0-6
    ("gate.fp_pipeline_fpiu_unit_fp_sdq_valids_{idx}", "gate.fp_pipeline_fpiu_unit_fp_sdq_uops_{idx}", range(3)),  # idx: 0-2
    ("gate.fp_pipeline_fpiu_unit_fpu_r_valids_{idx}", "gate.fp_pipeline_fpiu_unit_fpu_r_uops_{idx}", range(4)),  # idx: 0-3
    ("gate.csr_exe_unit_alu_r_valids_{idx}", "gate.csr_exe_unit_alu_r_uops_{idx}", range(0)),  # idx: 0-2
    # ("gate.csr_exe_unit_imul_r_valids_{idx}", "gate.csr_exe_unit_imul_r_uops_{idx}", range(3)),  # idx: 0-2
    # ("gate.csr_exe_unit_imul_imul_inPipe_valid", "gate.csr_exe_unit_imul_imul_inPipe_bits_"),
    # ("gate.csr_exe_unit_ifpu_r_valids_{idx}", "gate.csr_exe_unit_ifpu_r_uops_{idx}", range(2)),
    # ("gate.csr_exe_unit_ifpu_ifpu_inPipe_valid", "gate.csr_exe_unit_ifpu_ifpu_inPipe_bits_"),
    ("gate.mem_issue_unit_slots_{idx}_state", "gate.mem_issue_unit_slots_{idx}_slot", range(12)),  # idx: 0-7
    ("gate.rename_stage_r_valid", "gate.rename_stage_r_uop_"),
    # ("gate.csr_exe_unit_queue_valids_{idx}", "gate.csr_exe_unit_queue_uops_{idx}", range(5)),
    ("gate.fp_pipeline_fregister_read_exe_reg_valids_0", "gate.fp_pipeline_fregister_read_exe_reg_uops_0"),
    ("gate.iregister_read_rrd_valids_{idx}_REG", "gate.iregister_read_rrd_uops_{idx}_REG", range(1, 3)),
    ("gate.iregister_read_exe_reg_valids_{idx}", "gate.iregister_read_exe_reg_uops_{idx}", range(1, 3)),
    ("gate.fp_pipeline_fregister_read_rrd_valids_0_REG", "gate.fp_pipeline_fregister_read_uops_valids_0_REG"),

    ("gate.jmp_pc_req_valid_REG", "gate.jmp_pc_req_bits_REG"),
    ("gate.jmp_unit_alu_r_valids_{idx}", "gate.jmp_unit_alu_r_uops_{idx}", range(3)),
    ("gate.jmp_unit_imul_r_valids_{idx}", "gate.jmp_unit_imul_r_uops_{idx}", range(3)),
    ("gate.jmp_unit_imul_imul_inPipe_valid", "gate.jmp_unit_imul_imul_inPipe_bits_"),
    ("gate.jmp_unit_ifpu_r_valids_{idx}", "gate.jmp_unit_ifpu_r_uops_{idx}", range(2)),
    ("gate.jmp_unit_ifpu_ifpu_inPipe_valid", "gate.jmp_unit_ifpu_ifpu_inPipe_bits_"),
    ("gate.jmp_unit_queue_ram_{idx}_fflags_valid", "gate.jmp_unit_queue_ram_{idx}_fflags_bits_", range(5)),
    ("gate.jmp_unit_queue_valids_{idx}", "gate.jmp_unit_queue_uops_{idx}", range(5)),
    ("gate.csr_exe_unit_div_div_state", "gate.csr_exe_unit_div_div_")

]

prs2_mask = [
    ("rename_stage_r_uop_lrs2_rtype", "rename_stage_r_uop_prs2"),
    ("fp_rename_stage_r_uop_lrs2_rtype", "fp_rename_stage_r_uop_prs2"),
    ("mem_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "mem_issue_unit_slots_{idx}_slot_uop_prs2", range(12)),
    ("int_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "int_issue_unit_slots_{idx}_slot_uop_prs2", range(20)),
    ("iregister_read_rrd_uops_{idx}_REG_lrs2_rtype", "iregister_read_rrd_uops_{idx}_REG_prs2", range(1, 3)), # iregister_read_rrd_uops_0_REG is not used
    
    ("rename_stage_r_uop_1_lrs2_rtype", "rename_stage_r_uop_1_prs2"),
    ("fp_rename_stage_r_uop_1_lrs2_rtype", "fp_rename_stage_r_uop_1_prs2"),

]

rob_regex = [
    
]
rob_exact = [
    
]

uopc_vars = dict([(24338, 24253), (24448, 24003), (24459, 23978), (24470, 23953), (24481, 23928), (24492, 23903), (24503, 23865), (24349, 24228), (24360, 24203), (24371, 24178), (24382, 24153), (24393, 24128), (24404, 24103), (24415, 24078), (24426, 24053), (24437, 24028), (10460, 5664), (10570, 5986), (10581, 6018), (10592, 6050), (10603, 6082), (10614, 6114), (10625, 6146), (10636, 6178), (10647, 6210), (10658, 6242), (10669, 6274), (10471, 5699), (10482, 5730), (10493, 5762), (10504, 5794), (10515, 5826), (10526, 5858), (10537, 5890), (10548, 5922), (10559, 5954), (2838, 2790), (2839, 2791), (2840, 2792), (24712, 24694), (24704, 24693), (24696, 24692), (2778, 2574), (2860, 2718), (2861, 2719), (2862, 2720), (2863, 2721), (2864, 2722), (2865, 2723), (2866, 2724), (2826, 2825), (24550, 24548), (9369, 8775), (11225, 1428), (10857, 10828), (10830, 10827), (4316, 1302), (4209, 2442)])
fu_vars = dict([(24716, 24694), (24708, 24693), (24700, 24692), (2775, 2574), (23885, 2825), (24555, 24548), (8776, 8775), (1429, 1428), (10872, 10828), (10844, 10827), (4329, 1302), (4253, 2442), (24270, 24253), (24020, 24003), (23995, 23978), (23970, 23953), (23945, 23928), (23920, 23903), (23882, 23865), (24245, 24228), (24220, 24203), (24195, 24178), (24170, 24153), (24145, 24128), (24120, 24103), (24095, 24078), (24070, 24053), (24045, 24028), (5683, 5664), (6003, 5986), (6035, 6018), (6067, 6050), (6099, 6082), (6131, 6114), (6163, 6146), (6195, 6178), (6227, 6210), (6259, 6242), (6291, 6274), (5716, 5699), (5747, 5730), (5779, 5762), (5811, 5794), (5843, 5826), (5875, 5858), (5907, 5890), (5939, 5922), (5971, 5954), (7039, 6703), (6843, 6812), (7086, 7068), (7019, 6708), (6999, 6717), (6979, 6729), (6959, 6741), (6939, 6753), (6919, 6765), (6899, 6777), (6879, 6789), (6693, 6686)])

fu_state_vars = [24253, 24003, 23978, 23953, 23928, 23903, 23865, 24228, 24203, 24178, 24153, 24128, 24103, 24078, 24053, 24028, 5664, 5986, 6018, 6050, 6082, 6114, 6146, 6178, 6210, 6242, 6274, 5699, 5730, 5762, 5794, 5826, 5858, 5890, 5922, 5954, 6703, 6812, 7068, 6708, 6717, 6729, 6741, 6753, 6765, 6777, 6789, 6686]

