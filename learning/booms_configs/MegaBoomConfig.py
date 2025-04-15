# NO fence, jal, ebreak, ecall

ALU_R_INST_STARTS = 85414
ALU_I_INST_STARTS = 85414
SFT_R_INST_STARTS = 85414
SFT_I_INST_STARTS = 85414
LOAD_IMM_INST = 85414
CMP_R_INST = 85414
CMP_I_INST = 85414

FORWARD_STEP = 34

BOOM_BTOR_FILE_NAME = "targets/megaboomcore.btor"
BOOM_LOG_FOLDER = "./pexs/logs-megaboom/"

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
    # "auipc": LOAD_IMM_INST,

    "slt": CMP_R_INST,
    "sltu": CMP_R_INST,

    "slti": CMP_I_INST,
    "sltiu": CMP_I_INST,
}

regexs = [
    ("gate.int_issue_unit_slots_{idx}_state", "gate.int_issue_unit_slots_{idx}_", range(40)),  #  idx: 0-7
    ("gate.csr_exe_unit_alu_r_valids_{idx}", "gate.csr_exe_unit_alu_r_uops_{idx}", range(1)),  # idx: 0-2
    # ("gate.csr_exe_unit_imul_r_valids_{idx}", "gate.csr_exe_unit_imul_r_uops_{idx}", range(3)),  # idx: 0-2
    # ("gate.csr_exe_unit_imul_imul_inPipe_valid", "gate.csr_exe_unit_imul_imul_inPipe_bits_"),
    ("gate.mem_issue_unit_slots_{idx}_state", "gate.mem_issue_unit_slots_{idx}_slot", range(16)),  # idx: 0-7
    ("gate.rename_stage_r_valid", "gate.rename_stage_r_uop_"),
    ("gate.rename_stage_r_valid_{idx}", "gate.rename_stage_r_uop_{idx}_", range(1, 4)),
    ("gate.iregister_read_rrd_valids_{idx}_REG", "gate.iregister_read_rrd_uops_{idx}_REG", range(2, 6)),
    ("gate.iregister_read_exe_reg_valids_{idx}", "gate.iregister_read_exe_reg_uops_{idx}", range(2, 6)),

    ("gate.jmp_pc_req_valid_REG", "gate.jmp_pc_req_bits_REG"),
    ("gate.jmp_unit_alu_r_valids_{idx}", "gate.jmp_unit_alu_r_uops_{idx}", range(1)),
    # ("gate.jmp_unit_imul_r_valids_{idx}", "gate.jmp_unit_imul_r_uops_{idx}", range(3)),
    # ("gate.jmp_unit_imul_imul_inPipe_valid", "gate.jmp_unit_imul_imul_inPipe_bits_"),
    ("gate.jmp_unit_ifpu_r_valids_{idx}", "gate.jmp_unit_ifpu_r_uops_{idx}", range(2)),
    ("gate.jmp_unit_ifpu_ifpu_inPipe_valid", "gate.jmp_unit_ifpu_ifpu_inPipe_bits_"),
    ("gate.jmp_unit_queue_ram_{idx}_fflags_valid", "gate.jmp_unit_queue_ram_{idx}_fflags_bits_", range(5)),
    ("gate.jmp_unit_queue_valids_{idx}", "gate.jmp_unit_queue_uops_{idx}", range(5)),
    # ("gate.csr_exe_unit_div_div_state", "gate.csr_exe_unit_div_div_")
    ("gate.alu_exe_unit_imul_r_valids_{idx}", "gate.alu_exe_unit_imul_r_uops_{idx}_", range(3)),  # idx: 0-2 
    ("gate.alu_exe_unit_alu_r_valids_{idx}", "gate.alu_exe_unit_alu_r_uops_{idx}_", range(3)),  # idx: 0-2 

    ("gate.alu_exe_unit_imul_imul_inPipe_valid", "gate.alu_exe_unit_imul_imul_inPipe_bits_"),
    ("gate.alu_exe_unit_1_alu_r_valids_0", "gate.alu_exe_unit_1_alu_r_uops_0_"),
    ("gate.fp_pipeline_fpiu_unit_fpu_fpu_dfma_valid", "gate.fp_pipeline_fpiu_unit_fpu_fpu_dfma_"),
    ("gate.fp_pipeline_fpiu_unit_fpu_fpu_sfma_valid", "gate.fp_pipeline_fpiu_unit_fpu_fpu_sfma_"),
    ("gate.fp_pipeline_fpiu_unit_fpu_fpu_fpiu_outPipe_valid_{idx}", "gate.fp_pipeline_fpiu_unit_fpu_fpu_fpiu_outPipe_bits_{idx}_", range(1, 3)),
    ("gate.fp_pipeline_fpiu_unit_fpu_fpu_fpmu_inPipe_valid", "gate.fp_pipeline_fpiu_unit_fpu_fpu_fpmu_inPipe_bits_"),
    ("gate.brinfos_{idx}_valid", "gate.brinfos_{idx}_", range(4)),

    ("gate.alu_exe_unit_1_div_div_state", "gate.alu_exe_unit_1_div_div_")

]

prs2_mask = [
    ("rename_stage_r_uop_lrs2_rtype", "rename_stage_r_uop_prs2"),
    ("rename_stage_r_uop_{idx}_lrs2_rtype", "rename_stage_r_uop_{idx}_prs2", range(1, 4)),
    ("fp_rename_stage_r_uop_lrs2_rtype", "fp_rename_stage_r_uop_prs2"),
    ("fp_rename_stage_r_uop_{idx}_lrs2_rtype", "fp_rename_stage_r_uop_{idx}_prs2", range(1, 4)),
    ("mem_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "mem_issue_unit_slots_{idx}_slot_uop_prs2", range(24)),
    ("int_issue_unit_slots_{idx}_slot_uop_lrs2_rtype", "int_issue_unit_slots_{idx}_slot_uop_prs2", range(40)),
    ("iregister_read_rrd_uops_{idx}_REG_lrs2_rtype", "iregister_read_rrd_uops_{idx}_REG_prs2", range(2, 6)), # iregister_read_rrd_uops_0_REG is not used

    # ("rename_stage_r_uop_dst_rtype", "rename_stage_r_uop_pdst"),
    # ("rename_stage_r_uop_{idx}_dst_rtype", "rename_stage_r_uop_{idx}_pdst", range(1, 3)),
    # ("fp_rename_stage_r_uop_dst_rtype", "fp_rename_stage_r_uop_pdst"),
    # ("fp_rename_stage_r_uop_{idx}_dst_rtype", "fp_rename_stage_r_uop_{idx}_pdst", range(1, 3)),
    # ("int_issue_unit_slots_{idx}_slot_uop_dst_rtype", "int_issue_unit_slots_{idx}_slot_uop_pdst", range(32)),
    # ("iregister_read_rrd_uops_{idx}_REG_dst_rtype", "iregister_read_rrd_uops_{idx}_REG_pdst", range(1, 4)), # iregister_read_rrd_uops_0_REG is not used
    # ("fp_pipeline_fregister_read_exe_reg_uops_0_dst_rtype", "fp_pipeline_fregister_read_exe_reg_uops_0_pdst"),
    # ("jmp_unit_alu_r_uops_0_dst_rtype", "jmp_unit_alu_r_uops_0_pdst"),
    # ("jmp_unit_div_r_uop_dst_rtype", "jmp_unit_div_r_uop_pdst"),
    # ("csr_exe_unit_alu_r_uops_0_dst_rtype", "csr_exe_unit_alu_r_uops_0_pdst"),
    # ("csr_exe_unit_ifpu_r_uops_{idx}_dst_rtype", "csr_exe_unit_ifpu_r_uops_{idx}_pdst", range(2)),
    # ("csr_exe_unit_queue_uops_{idx}_dst_rtype", "csr_exe_unit_queue_uops_{idx}_pdst", range(5)),
    # ("alu_exe_unit_alu_r_uops_{idx}_dst_rtype", "alu_exe_unit_alu_r_uops_{idx}_pdst", range(3)),
    # ("alu_exe_unit_imul_r_uops_{idx}_dst_rtype", "alu_exe_unit_imul_r_uops_{idx}_pdst", range(3)),
    # ("fp_pipeline_fpiu_unit_fpu_r_uops_{idx}_dst_rtype", "fp_pipeline_fpiu_unit_fpu_r_uops_{idx}_pdst", range(4)),
    # ("fp_pipeline_fpiu_unit_fdivsqrt_r_buffer_req_uop_dst_rtype", "fp_pipeline_fpiu_unit_fdivsqrt_r_buffer_req_uop_pdst"),
    # ("fp_pipeline_fpiu_unit_fdivsqrt_r_divsqrt_uop_dst_rtype", "fp_pipeline_fpiu_unit_fdivsqrt_r_divsqrt_uop_pdst"),
    # ("fp_pipeline_fpiu_unit_fdivsqrt_r_out_uop_dst_rtype", "fp_pipeline_fpiu_unit_fdivsqrt_r_out_uop_pdst"),
    # ("fp_pipeline_fpiu_unit_queue_uops_{idx}_dst_rtype", "fp_pipeline_fpiu_unit_queue_uops_{idx}_pdst", range(7)),
    # ("fp_pipeline_fpiu_unit_fp_sdq_uops_{idx}_dst_rtype", "fp_pipeline_fpiu_unit_fp_sdq_uops_{idx}_pdst", range(3)),
    # ("fp_pipeline_fp_issue_unit_slots_{idx}_slot_uop_dst_rtype", "fp_pipeline_fp_issue_unit_slots_{idx}_slot_uop_pdst", range(24)),
    # ("fp_pipeline_fregister_read_rrd_uops_0_REG_dst_rtype", "fp_pipeline_fregister_read_rrd_uops_0_REG_pdst"),
    # ("iregister_read_exe_reg_uops_1_dst_rtype", "iregister_read_exe_reg_uops_1_pdst", range(1, 4)),
    # ("rob_rob_uop_{idx}_dst_rtype", "rob_rob_uop_{idx}_pdst", range(32)),
    # ("rob_rob_uop_1_{idx}_dst_rtype", "rob_rob_uop_1_{idx}_ldst", range(32)),
    # ("rob_rob_uop_2_{idx}_dst_rtype", "rob_rob_uop_2_{idx}_ldst", range(32)),

    ("rename_stage_r_uop_lrs1_rtype", "rename_stage_r_uop_prs1"),
    ("rename_stage_r_uop_{idx}_lrs1_rtype", "rename_stage_r_uop_{idx}_prs1", range(1, 4)),
    ("fp_rename_stage_r_uop_lrs1_rtype", "fp_rename_stage_r_uop_prs1"),
    ("fp_rename_stage_r_uop_{idx}_lrs1_rtype", "fp_rename_stage_r_uop_{idx}_prs1", range(1, 4)),
    ("mem_issue_unit_slots_{idx}_slot_uop_lrs1_rtype", "mem_issue_unit_slots_{idx}_slot_uop_prs1", range(24)),
    ("int_issue_unit_slots_{idx}_slot_uop_lrs1_rtype", "int_issue_unit_slots_{idx}_slot_uop_prs1", range(40)),
    ("iregister_read_rrd_uops_{idx}_REG_lrs1_rtype", "iregister_read_rrd_uops_{idx}_REG_prs1", range(2, 6)), # iregister_read_rrd_uops_0_REG is not used
]

rob_regex = [
    ("rob_rob_val_{idx}", "^rob_rob_uop_{idx}_(?!\d)", range(32)),
    ("rob_rob_val_1_{idx}", "^rob_rob_uop_1_{idx}_(?!\d)", range(32)),
    ("rob_rob_val_2_{idx}", "^rob_rob_uop_2_{idx}_(?!\d)", range(32)),
    ("rob_rob_val_3_{idx}", "^rob_rob_uop_3_{idx}_(?!\d)", range(32)),
]

rob_exact = [
    ("rob_rob_val_{idx}", "rob_rob_bsy_{idx}", range(32)),
    ("rob_rob_val_1_{idx}", "rob_rob_bsy_1_{idx}", range(32)),
    ("rob_rob_val_2_{idx}", "rob_rob_bsy_2_{idx}", range(32)),
    ("rob_rob_val_3_{idx}", "rob_rob_bsy_3_{idx}", range(32)),

    ("rob_rob_val_{idx}", "rob_rob_exception_{idx}", range(32)),
    ("rob_rob_val_1_{idx}", "rob_rob_exception_1_{idx}", range(32)),
    ("rob_rob_val_2_{idx}", "rob_rob_exception_2_{idx}", range(32)),
    ("rob_rob_val_3_{idx}", "rob_rob_exception_3_{idx}", range(32)),

    ("rob_rob_val_{idx}", "rob_rob_predicated_{idx}", range(32)),
    ("rob_rob_val_1_{idx}", "rob_rob_predicated_1_{idx}", range(32)),
    ("rob_rob_val_2_{idx}", "rob_rob_predicated_2_{idx}", range(32)),
    ("rob_rob_val_3_{idx}", "rob_rob_predicated_3_{idx}", range(32)),
]

uopc_vars = dict(
    [(48567, 48418), (48742, 48168), (48760, 48143), (48778, 48118), (48796, 48093), (48814, 48068), (48832, 48043), (48850, 48018), (48868, 47993), (48886, 47968), (48904, 47943), (48581, 48393), (48598, 48368), (48922, 47918), (48940, 47893), (48958, 47868), (48976, 47843), (48994, 47818), (49012, 47793), (49030, 47768), (49048, 47743), (49066, 47718), (49084, 47693), (48616, 48343), (49102, 47668), (49120, 47630), (48634, 48318), (48652, 48293), (48670, 48268), (48688, 48243), (48706, 48218), (48724, 48193), (21309, 19413), (21419, 19163), (21430, 19138), (21441, 19113), (21452, 19088), (21463, 19063), (21474, 19038), (21485, 19013), (21496, 18988), (21507, 18963), (21518, 18938), (21320, 19388), (21331, 19363), (21529, 18913), (21540, 18888), (21551, 18863), (21562, 18838), (21573, 18813), (21584, 18788), (21595, 18763), (21606, 18738), (21617, 18713), (21628, 18688), (21342, 19338), (21639, 18663), (21650, 18638), (21661, 18613), (21672, 18588), (21683, 18563), (21694, 18538), (21705, 18513), (21716, 18486), (21727, 18463), (21738, 18431), (21353, 19313), (21364, 19288), (21375, 19263), (21386, 19238), (21397, 19213), (21408, 19188), (5159, 5111), (5160, 5112), (5161, 5113), (52480, 52462), (52472, 52461), (52464, 52460), (5099, 4889), (5181, 5043), (5182, 5044), (5183, 5045), (5184, 5046), (5185, 5047), (5186, 5048), (5187, 5049), (5147, 5146), (49303, 49302), (49280, 49271), (49272, 49270), (17406, 17067), (22771, 22725), (22748, 22724), (22727, 2637), (22243, 22162), (22216, 22161), (22190, 22160), (22164, 22159), (7910, 4676), (7931, 2478), (7952, 2475), (7620, 2474)])
fu_vars = dict(
    [(52484, 52462), (52476, 52461), (52468, 52460), (5096, 4889), (47650, 5146), (49307, 49302), (49285, 49271), (17068, 17067), (22782, 22725), (22759, 22724), (2638, 2637), (22258, 22162), (22230, 22161), (22204, 22160), (22178, 22159), (7923, 4676), (7944, 2478), (7965, 2475), (7694, 2474), (49642, 49628), (49637, 49627), (49632, 49626), (5439, 5361), (48435, 48418), (48185, 48168), (48160, 48143), (48135, 48118), (48110, 48093), (48085, 48068), (48060, 48043), (48035, 48018), (48010, 47993), (47985, 47968), (47960, 47943), (48410, 48393), (48385, 48368), (47935, 47918), (47910, 47893), (47885, 47868), (47860, 47843), (47835, 47818), (47810, 47793), (47785, 47768), (47760, 47743), (47735, 47718), (47710, 47693), (48360, 48343), (47685, 47668), (47647, 47630), (48335, 48318), (48310, 48293), (48285, 48268), (48260, 48243), (48235, 48218), (48210, 48193), (19430, 19413), (19180, 19163), (19155, 19138), (19130, 19113), (19105, 19088), (19080, 19063), (19055, 19038), (19030, 19013), (19005, 18988), (18980, 18963), (18955, 18938), (19405, 19388), (19380, 19363), (18930, 18913), (18905, 18888), (18880, 18863), (18855, 18838), (18830, 18813), (18805, 18788), (18780, 18763), (18755, 18738), (18730, 18713), (18705, 18688), (19355, 19338), (18680, 18663), (18655, 18638), (18630, 18613), (18605, 18588), (18580, 18563), (18555, 18538), (18530, 18513), (18503, 18486), (18480, 18463), (18450, 18431), (19330, 19313), (19305, 19288), (19280, 19263), (19255, 19238), (19230, 19213), (19205, 19188), (12210, 11846), (12014, 11951), (12317, 11967), (12361, 11983), (12407, 12389), (13973, 13436), (13953, 13448), (13933, 13460), (13913, 13472), (13893, 13484), (13873, 13496), (12190, 11851), (12170, 11859), (13853, 13508), (13833, 13520), (13813, 13532), (13408, 13401), (12150, 11869), (12130, 11880), (12110, 11892), (12090, 11904), (12070, 11916), (12050, 11928), (11836, 11829)]
    )

fu_state_vars = [48418, 48168, 48143, 48118, 48093, 48068, 48043, 48018, 47993, 47968, 47943, 48393, 48368, 47918, 47893, 47868, 47843, 47818, 47793, 47768, 47743, 47718, 47693, 48343, 47668, 47630, 48318, 48293, 48268, 48243, 48218, 48193, 19413, 19163, 19138, 19113, 19088, 19063, 19038, 19013, 18988, 18963, 18938, 19388, 19363, 18913, 18888, 18863, 18838, 18813, 18788, 18763, 18738, 18713, 18688, 19338, 18663, 18638, 18613, 18588, 18563, 18538, 18513, 18486, 18463, 18431, 19313, 19288, 19263, 19238, 19213, 19188, 11846, 11951, 11967, 11983, 12389, 13436, 13448, 13460, 13472, 13484, 13496, 11851, 11859, 13508, 13520, 13532, 13401, 11869, 11880, 11892, 11904, 11916, 11928, 11829]
