import mda_pkg::*;

module mda_pc #(
    parameter ADDR_WIDTH = mda_pkg::IMEM_ADDR_WIDTH
) (
    // clock & reset
    input  logic  clk,
    input  logic  rst_n,
    // INPUTS:
    input  logic  load_en,   // entry point load, asserted by go. Loads the thread's entry PC and has priority over the update
    input  PcAddr entry_pc,
    input  logic  pc_en,     // enable pc, high only when PC enable (when thread inst in EX, hence next slot for PC to inc for thread)
    // input 1
    input  logic  pc_in1,    // choose between PC itself and rs1 for the first PC input
    input  PcAddr rs1_in,    // (MUX if above input is high, take only bottom 10 bits)
    // input 2
    input  logic  pc_in2,    // choose between +1 and imm in for second PC input
    input  PcAddr imm_in,    // (MUX if above input is high, take only bottom 10 bits)
    input  logic  pc_cin,    // carry-in of the PC adder, HIGH for taken PC-relative jumps, so the target is PC + imm + 1 (offsets are relative to PC + 1); Low for jrg, which uses rs1 + imm, and for sequential flow
    // output
    output PcAddr pc_out
);

    PcAddr pc, pc_next;
    PcAddr in1, in2;

    always_comb begin
        in1 = (pc_in1) ? rs1_in : pc;
        in2 = (pc_in2) ? imm_in : {{(IMEM_ADDR_WIDTH-1){1'b0}}, 1'b1}; // the latter is just "1" lol
        pc_next = in1 + in2 + pc_cin;   // pc_cin acts as carry
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) pc <= '0;
        else if (load_en) pc <= entry_pc;   // entry load has priority, then the update, otherwise the PC holds its value
        else if (pc_en) pc <= pc_next;
    end

    assign pc_out   = pc;

endmodule