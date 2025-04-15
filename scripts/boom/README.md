# Boom setup instructions

## Precondition: Setup Chipyard and Get Boom Verilog
```
# before chipyard we need to install conda and run following command 
conda install -n base conda-lock=1.4
conda activate base

# chipyard install
git clone https://github.com/ucb-bar/chipyard.git
cd chipyard
# checkout latest official chipyard release
# note: this may not be the latest release if the documentation version != "stable"
git checkout 1.10.0

./build-setup.sh riscv-tools -s 7 -s 9 # skip pre-compiling FireSim sources and FireMarshal default buildroot Linux sources

# source env
source env.sh

# build boom
cd chipyard/sims/verilator
make debug CONFIG=SmallBoomConfig
```
The last command will wait a while, this will generated a executable called ```simulator-chipyard.harness-SmallBoomConfig-debug```. But that's not what we want. We want to get modify the main function in simulator source. 

## Step 1: Add verilator annotation in Boom Verilog
After above step, the verilog source will be stored in ```chipyard/sims/verilator/generated-src/chipyard.harness.TestHarness.SmallBoomConfig/gen-collateral``` folder. 

We can need to run the following command to add annotation

```
python3 annotator.py chipyard/sims/verilator/generated-src/chipyard.harness.TestHarness.SmallBoomConfig/model_module_hierarchy.json chipyard/sims/verilator/generated-src/chipyard.harness.TestHarness.SmallBoomConfig/gen-collateral
```
This will also generate two file ```reglist.txt``` and ```memlist.txt```, which are all register name and Memoey (2d array in verilog) name needed for Step3. 

## Step 2: Run verilator command to generate C++ files for simulation
Open ```run.sh```, replace ```$chipyard_home``` with the ```chipyard``` repo path. Then run ```run.sh```, the result C++ file will be in folder called ```verilator_generated_src``` folder.

## Step 3: Compile the verilator and get executable
1. We need to replace the verilator main file with our own main ```VTestDriver__main.cpp```. We run command 
```
cp VTestDriver__main.cpp verilator_generated_src/VTestDriver__main.cpp
```
2. We go to ```verilator_generated_src``` folder, make the folder
```
cd verilator_generated_src/
make VM_PARALLEL_BUILDS=1 -C . -f VTestDriver.mk
```
It will generated executable called ```simulator-chipyard.harness-SmallBoomConfig-debug```. To run program, simply do
```
./simulator-chipyard.harness-SmallBoomConfig-debug valid_riscv_program
```

## Step 4: Get the dump
The dump file are stored in log.txt (temp name for now). It's a json file and schema are contained in ```VTestDriver__main.cpp```. 


