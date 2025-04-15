yosys read_verilog boom/mediumboomcore_src/BoomCore.sv
yosys cd BoomCore
yosys delete -output *
yosys expose rob_io_commit_arch_valids_0
yosys cd ..
yosys miter -equiv BoomCore BoomCore miter_BoomCore
yosys hierarchy -top miter_BoomCore
yosys cd miter_BoomCore
yosys ls
yosys add -assert trigger
yosys cd ..
yosys prep -top miter_BoomCore
yosys hierarchy -check
yosys memory -nomap
yosys chformal -assume -early
yosys flatten
yosys write_btor mediumboomcore.btor