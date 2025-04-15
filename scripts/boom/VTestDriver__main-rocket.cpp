// Verilated -*- C++ -*-
// DESCRIPTION: main() calling loop, created with Verilator --main

#include "verilated.h"
#include "VTestDriver.h"
#include "verilated_vpi.h"
#include "VTestDriver___024root.h"

#include <fcntl.h>
#include <unistd.h>

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <unordered_map>

/* Concrete Example schema
 * {
 *   "examples":{
 *               "$cycle_number": {  reg_name: value, 
 *                   .....
 *                   memlist_name: [
 *                                  value1, value2, value3
 *                                 ]
 *               },
 *               ...
 *               }
 * }
 */

std::unordered_map<std::string, std::string> reg_map;
std::vector<std::string> v_reglist;
std::vector<std::string> v_memlist;
std::string line;

std::string file_to_write = "./log.json";

uint64_t main_time = 0;   // See comments in first example
double sc_time_stamp() { return main_time; }

//======================
std::string read_and_check_mem(std::string& memlist_name) {
    std::string trimmed_name = memlist_name.substr(88);
    vpiHandle vh1 = vpi_handle_by_name((PLI_BYTE8 *)memlist_name.c_str(), NULL);
    if (!vh1) return "";
    // const char* name = vpi_get_str(vpiName, vh1);
    // const char* type = vpi_get_str(vpiType, vh1);
    // const int size = vpi_get(vpiSize, vh1);
    // printf("register name: %s, type: %s, size: %d\n", name, type, size); 

    int indx = 0;
    vpiHandle el;
    s_vpi_value v;
    v.format = vpiBinStrVal;
    std::string result = "\"" + memlist_name.substr(88) + "\"" + ":" + "[";
    std::string raw_result = "";
    while ( (el = vpi_handle_by_index(vh1, indx)) ){
        vpi_get_value(el, &v);
        //printf("    Memory[%d]=%s\n", indx, v.value.str);
        result += "\"" + std::string(v.value.str) + "\"" + ",";
        raw_result += std::string(v.value.str);
        indx++;
    }
    if(result.back() == ',')
        result.pop_back();
    result.push_back(']');
    if(reg_map.find(trimmed_name) == reg_map.end() || reg_map[trimmed_name] != raw_result){
        reg_map[trimmed_name] = raw_result;
        return result + ",";
    }else{
        return "";
    }
    
}

std::string read_and_check(std::string& reg_name) {
    // return json like map element in $reg_name: $value
    vpiHandle vh1 = vpi_handle_by_name((PLI_BYTE8*)reg_name.c_str(), NULL);
    if (!vh1) return "";
    // const char* name = vpi_get_str(vpiName, vh1);
    // const char* type = vpi_get_str(vpiType, vh1);
    // const int size = vpi_get(vpiSize, vh1);
    // printf("register name: %s, type: %s, size: %d\n", name, type, size);  // Prints "register name: readme, type: vpiReg, size: 32"

    s_vpi_value v;
    v.format = vpiBinStrVal;
    vpi_get_value(vh1, &v);
    //printf("Value of %s: %s\n", name, v.value.str);  // Prints "Value of readme: 0"
    std::string trimmed_name = reg_name.substr(88);
    std::string reg_val = std::string(v.value.str); 
    if(reg_map.find(trimmed_name) == reg_map.end() || reg_map[trimmed_name] != reg_val){
        reg_map[trimmed_name] = reg_val; 
        return "\"" + trimmed_name + "\"" + ":" + "\"" + reg_val + "\"" + ",";
    }else{
        return "";
    }
    
}

void write_to_reg(std::string &reg_name, int reg_val){
    vpiHandle vh1 = vpi_handle_by_name((PLI_BYTE8*)reg_name.c_str(), NULL);
    if (!vh1){
        std::cout << "unable to get value";
        return;
    }
    s_vpi_value value;
    value.format = vpiIntVal;
    value.value.integer = reg_val;
    vpi_put_value(vh1, &value, NULL, vpiNoDelay);
}

std::string read_and_dump_state(auto topp){
    std::string dump = "{";
    for(int i = 0; i < v_reglist.size(); i++){
        dump += read_and_check(v_reglist[i]);
        //dump += ",";
    }
    for(int i = 0; i < v_memlist.size(); i++){
        dump += read_and_check_mem(v_memlist[i]);
        //dump += ",";
    }
    std::string commit_sig = std::to_string(topp->rootp->TestDriver__DOT__testHarness__DOT__chiptop0__DOT__system__DOT__tile_prci_domain__DOT__tile_reset_domain_tile__DOT__core__DOT__ctrl_killd);
    if(reg_map["commit"] != commit_sig){
        dump = dump + ("\"commit\":\"");
        dump += commit_sig;
        dump += "\"";
        dump += "},";
    }
    return dump;
}


int main(int argc, char** argv, char**) {
    // parse register file with name


    std::ifstream reglist("../reglist-rocket.txt");    
    std::ifstream mem_list("../memlist-rocket.txt");     

    while(std::getline(reglist, line)){
        v_reglist.push_back(line);
    }

    while(std::getline(mem_list, line)){
        v_memlist.push_back(line);
    }

    int write_fd = open(argv[1], O_RDWR | O_CREAT | O_LARGEFILE | O_TRUNC, S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH);
    if(write_fd == -1){
        std::cout << "error opening files\n";
        exit(-1);
    }
    off64_t length = 0;


    std::string header = "{\"examples\":{";
    write(write_fd, header.c_str(), header.size());

    // Setup context, defaults, and parse command line
    Verilated::debug(0);
    const std::unique_ptr<VerilatedContext> contextp{new VerilatedContext};
    contextp->traceEverOn(true);
    contextp->commandArgs(argc - 1, argv + 1);

    // Construct the Verilated model, from Vtop.h generated from Verilating
    VTestDriver* topp = new VTestDriver{contextp.get()};
    int clock_edge = 0;
    std::string dump = "";
    std::string cycle_header = "";
    // Simulate until $finish
    while (!contextp->gotFinish()) {
        // Evaluate model
	    topp->eval();
        // Advance time
        if (!topp->eventsPending()) break;
        contextp->time(topp->nextTimeSlot());
        VerilatedVpi::callValueCbs();  // For signal callbacks
        if(clock_edge >= 50000){       // first 40,00 cycles are the same
            if(clock_edge % 2 == 0){
                cycle_header = "\"" + std::to_string(clock_edge) + "\":"; 
                write(write_fd, cycle_header.c_str(), cycle_header.size());

                dump = read_and_dump_state(topp);
                write(write_fd, dump.c_str(), dump.size());
            }   
        }
        clock_edge++;     
    }
    lseek(write_fd, -1, SEEK_END);   //rewrite over the last comma, satisfy json format

    write(write_fd, "}}", 2); 
    if (!contextp->gotFinish()) {
        VL_DEBUG_IF(VL_PRINTF("+ Exiting without $finish; no events left\n"););
    }

    // Final model cleanup
    topp->final();
    close(write_fd);
    return 0;
}
