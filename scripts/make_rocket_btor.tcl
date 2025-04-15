yosys read_verilog rocketchip/verilog_src/Rocket.v
yosys cd Rocket
yosys delete -output *
yosys expose ctrl_killd
yosys cd ..
yosys miter -equiv Rocket Rocket miter_Rocket
yosys hierarchy -top miter_Rocket
yosys cd miter_Rocket
yosys ls
yosys add -assert trigger
yosys cd ..
yosys prep -top miter_Rocket
yosys hierarchy -check
yosys memory -nomap
yosys chformal -assume -early
yosys flatten
yosys write_btor rocket.btor