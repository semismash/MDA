import mda_pkg::*;

// Load/store unit: checks, data memory controls, store strobe, and the load-return registers
module mda_lsu (
    // clock and reset
    input  logic         clk,
    input  logic         rst_n,
    // INPUTS:
    input  logic         ex_v,          // the EX stage holds a real instruction
    input  MemOp         mem_op,        // none, load, store
    input  logic         mem_byte,      // 1 = byte access, 0 = word access
    input  Word          addr,          // effective byte address (the ALU result)
    input  Word          store_data,    // rs2 value
    input  RegAddr       rd_addr,       // destination of a load
    input  Word          dm_rdata,      // data memory read data (valid the cycle after the access)
    // OUTPUTS:
    // data memory (to mda_dmem core port)
    output logic         dm_en,
    output logic         dm_we,
    output DmemWordAddr  dm_addr,
    output Word          dm_wdata,
    output logic [3:0]   dm_wstrb,
    // faults (in EX)
    output logic         fault,
    output Cause         fault_cause,
    // load return (to mda_wb)
    output logic         ld_valid,
    output RegAddr       ld_rd,
    output Word          ld_data
);



endmodule