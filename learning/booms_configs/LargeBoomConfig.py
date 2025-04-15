# NO fence, jal, ebreak, ecall

ALU_R_INST_STARTS = 76776
ALU_I_INST_STARTS = 76776
SFT_R_INST_STARTS = 76780
SFT_I_INST_STARTS = 76776
LOAD_IMM_INST = 76776
CMP_R_INST = 76776
CMP_I_INST = 76776

FORWARD_STEP = 34

BOOM_BTOR_FILE_NAME = "targets/largeboomcore.btor"
BOOM_LOG_FOLDER = "./pexs/logs-largeboom/"

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
    ("gate.int_issue_unit_slots_{idx}_state", "gate.int_issue_unit_slots_{idx}_", range(32)),  #  idx: 0-7
    ("gate.fp_pipeline_fp_issue_unit_slots_{idx}_state", "gate.fp_pipeline_fp_issue_unit_slots_{idx}_", range(24)),  #  idx: 0-7
    ("gate.fp_pipeline_fpiu_unit_queue_valids_{idx}", "gate.fp_pipeline_fpiu_unit_queue_uops_{idx}", range(7)),   # idx: 0-6
    ("gate.fp_pipeline_fpiu_unit_fp_sdq_valids_{idx}", "gate.fp_pipeline_fpiu_unit_fp_sdq_uops_{idx}", range(3)),  # idx: 0-2
    ("gate.fp_pipeline_fpiu_unit_fpu_r_valids_{idx}", "gate.fp_pipeline_fpiu_unit_fpu_r_uops_{idx}", range(4)),  # idx: 0-3
    ("gate.csr_exe_unit_alu_r_valids_{idx}", "gate.csr_exe_unit_alu_r_uops_{idx}", range(0)),  # idx: 0-2
    # ("gate.csr_exe_unit_imul_r_valids_{idx}", "gate.csr_exe_unit_imul_r_uops_{idx}", range(3)),  # idx: 0-2
    # ("gate.csr_exe_unit_imul_imul_inPipe_valid", "gate.csr_exe_unit_imul_imul_inPipe_bits_"),
    ("gate.csr_exe_unit_ifpu_r_valids_{idx}", "gate.csr_exe_unit_ifpu_r_uops_{idx}", range(2)),
    ("gate.csr_exe_unit_ifpu_ifpu_inPipe_valid", "gate.csr_exe_unit_ifpu_ifpu_inPipe_bits_"),
    ("gate.mem_issue_unit_slots_{idx}_state", "gate.mem_issue_unit_slots_{idx}_slot", range(16)),  # idx: 0-7
    ("gate.rename_stage_r_valid", "gate.rename_stage_r_uop_"),
    ("gate.rename_stage_r_valid_{idx}", "gate.rename_stage_r_uop_{idx}_", range(1, 3)),
    ("gate.csr_exe_unit_queue_valids_{idx}", "gate.csr_exe_unit_queue_uops_{idx}", range(5)),
    ("gate.fp_pipeline_fregister_read_exe_reg_valids_0", "gate.fp_pipeline_fregister_read_exe_reg_uops_0"),
    ("gate.iregister_read_rrd_valids_{idx}_REG", "gate.iregister_read_rrd_uops_{idx}_REG", range(1, 3)),
    ("gate.iregister_read_exe_reg_valids_{idx}", "gate.iregister_read_exe_reg_uops_{idx}", range(1, 4)),
    ("gate.fp_pipeline_fregister_read_rrd_valids_0_REG", "gate.fp_pipeline_fregister_read_uops_valids_0_REG"),

    ("gate.jmp_pc_req_valid_REG", "gate.jmp_pc_req_bits_REG"),
    ("gate.jmp_unit_alu_r_valids_{idx}", "gate.jmp_unit_alu_r_uops_{idx}", range(0)),
    # ("gate.jmp_unit_imul_r_valids_{idx}", "gate.jmp_unit_imul_r_uops_{idx}", range(3)),
    # ("gate.jmp_unit_imul_imul_inPipe_valid", "gate.jmp_unit_imul_imul_inPipe_bits_"),
    # ("gate.jmp_unit_ifpu_r_valids_{idx}", "gate.jmp_unit_ifpu_r_uops_{idx}", range(2)),
    # ("gate.jmp_unit_ifpu_ifpu_inPipe_valid", "gate.jmp_unit_ifpu_ifpu_inPipe_bits_"),
    # ("gate.jmp_unit_queue_ram_{idx}_fflags_valid", "gate.jmp_unit_queue_ram_{idx}_fflags_bits_", range(5)),
    # ("gate.jmp_unit_queue_valids_{idx}", "gate.jmp_unit_queue_uops_{idx}", range(5)),
    # ("gate.csr_exe_unit_div_div_state", "gate.csr_exe_unit_div_div_")
    ("gate.alu_exe_unit_imul_r_valids_{idx}", "gate.alu_exe_unit_imul_r_uops_{idx}_", range(3)),  # idx: 0-2 
    ("gate.alu_exe_unit_alu_r_valids_{idx}", "gate.alu_exe_unit_alu_r_uops_{idx}_", range(3)),  # idx: 0-2 
    ("gate.jmp_unit_div_div_state", "gate.jmp_unit_div_div_"), 
]

prs2_mask = [
    ("rename_stage_r_uop_lrs2_rtype", "rename_stage_r_uop_prs2"),
    ("rename_stage_r_uop_{idx}_lrs2_rtype", "rename_stage_r_uop_{idx}_prs2", range(1, 3)),
    ("fp_rename_stage_r_uop_lrs2_rtype", "fp_rename_stage_r_uop_prs2"),
    ("fp_rename_stage_r_uop_{idx}_lrs2_rtype", "fp_rename_stage_r_uop_{idx}_prs2", range(1, 3)),
    ("mem_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "mem_issue_unit_slots_{idx}_slot_uop_prs2", range(16)),
    ("int_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "int_issue_unit_slots_{idx}_slot_uop_prs2", range(32)),
    ("iregister_read_rrd_uops_{idx}_REG_lrs2_rtype", "iregister_read_rrd_uops_{idx}_REG_prs2", range(1, 4)), # iregister_read_rrd_uops_0_REG is not used

    ("rename_stage_r_uop_dst_rtype", "rename_stage_r_uop_pdst"),
    ("rename_stage_r_uop_{idx}_dst_rtype", "rename_stage_r_uop_{idx}_pdst", range(1, 3)),
    ("fp_rename_stage_r_uop_dst_rtype", "fp_rename_stage_r_uop_pdst"),
    ("fp_rename_stage_r_uop_{idx}_dst_rtype", "fp_rename_stage_r_uop_{idx}_pdst", range(1, 3)),
    ("int_issue_unit_slots_{idx}_slot_uop_dst_rtype", "int_issue_unit_slots_{idx}_slot_uop_pdst", range(32)),
    ("iregister_read_rrd_uops_{idx}_REG_dst_rtype", "iregister_read_rrd_uops_{idx}_REG_pdst", range(1, 4)), # iregister_read_rrd_uops_0_REG is not used
    ("fp_pipeline_fregister_read_exe_reg_uops_0_dst_rtype", "fp_pipeline_fregister_read_exe_reg_uops_0_pdst"),
    ("jmp_unit_alu_r_uops_0_dst_rtype", "jmp_unit_alu_r_uops_0_pdst"),
    ("jmp_unit_div_r_uop_dst_rtype", "jmp_unit_div_r_uop_pdst"),
    ("csr_exe_unit_alu_r_uops_0_dst_rtype", "csr_exe_unit_alu_r_uops_0_pdst"),
    ("csr_exe_unit_ifpu_r_uops_{idx}_dst_rtype", "csr_exe_unit_ifpu_r_uops_{idx}_pdst", range(2)),
    ("csr_exe_unit_queue_uops_{idx}_dst_rtype", "csr_exe_unit_queue_uops_{idx}_pdst", range(5)),
    ("alu_exe_unit_alu_r_uops_{idx}_dst_rtype", "alu_exe_unit_alu_r_uops_{idx}_pdst", range(3)),
    ("alu_exe_unit_imul_r_uops_{idx}_dst_rtype", "alu_exe_unit_imul_r_uops_{idx}_pdst", range(3)),
    ("fp_pipeline_fpiu_unit_fpu_r_uops_{idx}_dst_rtype", "fp_pipeline_fpiu_unit_fpu_r_uops_{idx}_pdst", range(4)),
    ("fp_pipeline_fpiu_unit_fdivsqrt_r_buffer_req_uop_dst_rtype", "fp_pipeline_fpiu_unit_fdivsqrt_r_buffer_req_uop_pdst"),
    ("fp_pipeline_fpiu_unit_fdivsqrt_r_divsqrt_uop_dst_rtype", "fp_pipeline_fpiu_unit_fdivsqrt_r_divsqrt_uop_pdst"),
    ("fp_pipeline_fpiu_unit_fdivsqrt_r_out_uop_dst_rtype", "fp_pipeline_fpiu_unit_fdivsqrt_r_out_uop_pdst"),
    ("fp_pipeline_fpiu_unit_queue_uops_{idx}_dst_rtype", "fp_pipeline_fpiu_unit_queue_uops_{idx}_pdst", range(7)),
    ("fp_pipeline_fpiu_unit_fp_sdq_uops_{idx}_dst_rtype", "fp_pipeline_fpiu_unit_fp_sdq_uops_{idx}_pdst", range(3)),
    ("fp_pipeline_fp_issue_unit_slots_{idx}_slot_uop_dst_rtype", "fp_pipeline_fp_issue_unit_slots_{idx}_slot_uop_pdst", range(24)),
    ("fp_pipeline_fregister_read_rrd_uops_0_REG_dst_rtype", "fp_pipeline_fregister_read_rrd_uops_0_REG_pdst"),
    ("iregister_read_exe_reg_uops_1_dst_rtype", "iregister_read_exe_reg_uops_1_pdst", range(1, 4)),
    ("rob_rob_uop_{idx}_dst_rtype", "rob_rob_uop_{idx}_pdst", range(32)),
    ("rob_rob_uop_1_{idx}_dst_rtype", "rob_rob_uop_1_{idx}_ldst", range(32)),
    ("rob_rob_uop_2_{idx}_dst_rtype", "rob_rob_uop_2_{idx}_ldst", range(32)),


    ("rename_stage_r_uop_lrs1_rtype", "rename_stage_r_uop_prs1"),
    ("rename_stage_r_uop_{idx}_lrs1_rtype", "rename_stage_r_uop_{idx}_prs1", range(1, 3)),
    ("fp_rename_stage_r_uop_lrs1_rtype", "fp_rename_stage_r_uop_prs1"),
    ("fp_rename_stage_r_uop_{idx}_lrs1_rtype", "fp_rename_stage_r_uop_{idx}_prs1", range(1, 3)),
    ("mem_issue_unit_slots_{idx}_slot_uop_lrs1_rtype", "mem_issue_unit_slots_{idx}_slot_uop_prs1", range(16)),
    ("int_issue_unit_slots_{idx}_slot_uop_lrs1_rtype", "int_issue_unit_slots_{idx}_slot_uop_prs1", range(32)),
    ("iregister_read_rrd_uops_{idx}_REG_lrs1_rtype", "iregister_read_rrd_uops_{idx}_REG_prs1", range(1, 4)), # iregister_read_rrd_uops_0_REG is not used
]

rob_regex = [
    ("rob_rob_val_{idx}", "^rob_rob_uop_{idx}_(?!\d)", range(32)),
    ("rob_rob_val_1_{idx}", "^rob_rob_uop_1_{idx}_(?!\d)", range(32)),
    ("rob_rob_val_2_{idx}", "^rob_rob_uop_2_{idx}_(?!\d)", range(32)),
]
rob_exact = [
    ("rob_rob_val_{idx}", "rob_rob_bsy_{idx}", range(32)),
    ("rob_rob_val_1_{idx}", "rob_rob_bsy_1_{idx}", range(32)),
    ("rob_rob_val_2_{idx}", "rob_rob_bsy_2_{idx}", range(32)),

    ("rob_rob_val_{idx}", "rob_rob_exception_{idx}", range(32)),
    ("rob_rob_val_1_{idx}", "rob_rob_exception_1_{idx}", range(32)),
    ("rob_rob_val_2_{idx}", "rob_rob_exception_2_{idx}", range(32)),

    ("rob_rob_val_{idx}", "rob_rob_predicated_{idx}", range(32)),
    ("rob_rob_val_1_{idx}", "rob_rob_predicated_1_{idx}", range(32)),
    ("rob_rob_val_2_{idx}", "rob_rob_predicated_2_{idx}", range(32)),
]

uopc_vars = dict([(3993, 3945), (3994, 3946), (3995, 3947), (35118, 35100), (35110, 35099), (35102, 35098), (3933, 3732), (4015, 3873), (4016, 3874), (4017, 3875), (4018, 3876), (4019, 3877), (4020, 3878), (4021, 3879), (3981, 3980), (34933, 34931), (13781, 1996), (15823, 15798), (15800, 15797), (15374, 15319), (15347, 15318), (15321, 15317), (6054, 3559), (6079, 1878), (5864, 1876), (34617, 34500), (34727, 34250), (34738, 34225), (34749, 34200), (34760, 34175), (34771, 34150), (34782, 34125), (34793, 34100), (34804, 34075), (34815, 34050), (34826, 34025), (34628, 34475), (34639, 34450), (34837, 34000), (34848, 33975), (34859, 33950), (34870, 33912), (34650, 34425), (34661, 34400), (34672, 34375), (34683, 34350), (34694, 34325), (34705, 34300), (34716, 34275), (14667, 8173), (14777, 8478), (14788, 8508), (14799, 8538), (14810, 8568), (14821, 8598), (14832, 8628), (14843, 8658), (14854, 8688), (14865, 8718), (14876, 8748), (14678, 8209), (14689, 8238), (14887, 8778), (14898, 8808), (14909, 8838), (14920, 8868), (14931, 8898), (14942, 8928), (14953, 8958), (14964, 8988), (14975, 9018), (14986, 9048), (14700, 8268), (14997, 9078), (15008, 9108), (14711, 8298), (14722, 8328), (14733, 8358), (14744, 8388), (14755, 8418), (14766, 8448)])
fu_vars = dict([(35122, 35100), (35114, 35099), (35106, 35098), (3930, 3732), (33932, 3980), (34938, 34931), (1997, 1996), (15834, 15798), (15811, 15797), (15389, 15319), (15361, 15318), (15335, 15317), (6069, 3559), (6094, 1878), (5925, 1876), (34517, 34500), (34267, 34250), (34242, 34225), (34217, 34200), (34192, 34175), (34167, 34150), (34142, 34125), (34117, 34100), (34092, 34075), (34067, 34050), (34042, 34025), (34492, 34475), (34467, 34450), (34017, 34000), (33992, 33975), (33967, 33950), (33929, 33912), (34442, 34425), (34417, 34400), (34392, 34375), (34367, 34350), (34342, 34325), (34317, 34300), (34292, 34275), (8192, 8173), (8495, 8478), (8525, 8508), (8555, 8538), (8585, 8568), (8615, 8598), (8645, 8628), (8675, 8658), (8705, 8688), (8735, 8718), (8765, 8748), (8226, 8209), (8255, 8238), (8795, 8778), (8825, 8808), (8855, 8838), (8885, 8868), (8915, 8898), (8945, 8928), (8975, 8958), (9005, 8988), (9035, 9018), (9065, 9048), (8285, 8268), (9095, 9078), (9125, 9108), (8315, 8298), (8345, 8328), (8375, 8358), (8405, 8388), (8435, 8418), (8465, 8448), (10696, 10346), (10500, 10453), (10741, 10469), (10780, 10762), (11970, 11713), (11950, 11725), (11685, 11678), (10676, 10351), (10656, 10359), (10636, 10370), (10616, 10382), (10596, 10394), (10576, 10406), (10556, 10418), (10536, 10430), (10336, 10329)])

fu_state_vars = [34500, 34250, 34225, 34200, 34175, 34150, 34125, 34100, 34075, 34050, 34025, 34475, 34450, 34000, 33975, 33950, 33912, 34425, 34400, 34375, 34350, 34325, 34300, 34275, 8173, 8478, 8508, 8538, 8568, 8598, 8628, 8658, 8688, 8718, 8748, 8209, 8238, 8778, 8808, 8838, 8868, 8898, 8928, 8958, 8988, 9018, 9048, 8268, 9078, 9108, 8298, 8328, 8358, 8388, 8418, 8448, 10346, 10453, 10469, 10762, 11713, 11725, 11678, 10351, 10359, 10370, 10382, 10394, 10406, 10418, 10430, 10329]
