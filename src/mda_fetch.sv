import mda_pkg::*;

// Fetch: the three program counters, the IF address mux and the EX PC mux. Each PC updates only when its thread's instruction is in EX.
module mda_fetch (
    // clock and reset
    input  logic    clk,
    input  logic    rst_n,
    // INPUTS:
    input  logic    go,             // load the three entry points
    input  PcAddr   entry_pc0,
    input  PcAddr   entry_pc1,
    input  PcAddr   entry_pc2,
    input  Thread   if_thread,      // thread in IF
    // EX stage
    input  logic    ex_v,           // the EX stage holds a real instruction
    input  Thread   ex_thread,      // thread in EX
    input  logic    pc_in1,         // from mda_branch_unit: 1 = rs1 as the base, 0 = PC
    input  PcAddr   rs1_pc,         // rs1, low bits (jrg base)
    input  logic    pc_in2,         // from mda_branch_unit: 1 = offset, 0 = +1
    input  PcAddr   pc_offset,      // sign-extended offset
    input  logic    pc_cin,         // carry-in
    // OUTPUTS:
    output PcAddr   if_pc,          // PC of the thread in IF (the instruction memory address)
    output PcAddr   ex_pc           // PC of the thread in EX (the address of the instruction in EX)
);

    PcAddr pc0, pc1, pc2;
    logic  pc_en0, pc_en1, pc_en2;

    assign pc_en0 = ex_v & (ex_thread == THREAD_0);
    assign pc_en1 = ex_v & (ex_thread == THREAD_1);
    assign pc_en2 = ex_v & (ex_thread == THREAD_2);

    mda_pc u_pc0 (
        .clk      (clk),
        .rst_n    (rst_n),
        .load_en  (go),
        .entry_pc (entry_pc0),
        .pc_en    (pc_en0),
        .pc_in1   (pc_in1),
        .rs1_in   (rs1_pc),
        .pc_in2   (pc_in2),
        .imm_in   (pc_offset),
        .pc_cin   (pc_cin),
        .pc_out   (pc0)
    );

    mda_pc u_pc1 (
        .clk      (clk),
        .rst_n    (rst_n),
        .load_en  (go),
        .entry_pc (entry_pc1),
        .pc_en    (pc_en1),
        .pc_in1   (pc_in1),
        .rs1_in   (rs1_pc),
        .pc_in2   (pc_in2),
        .imm_in   (pc_offset),
        .pc_cin   (pc_cin),
        .pc_out   (pc1)
    );

    mda_pc u_pc2 (
        .clk      (clk),
        .rst_n    (rst_n),
        .load_en  (go),
        .entry_pc (entry_pc2),
        .pc_en    (pc_en2),
        .pc_in1   (pc_in1),
        .rs1_in   (rs1_pc),
        .pc_in2   (pc_in2),
        .imm_in   (pc_offset),
        .pc_cin   (pc_cin),
        .pc_out   (pc2)
    );

    always_comb begin
        case (if_thread)
            THREAD_1: if_pc = pc1;
            THREAD_2: if_pc = pc2;
            default:  if_pc = pc0;
        endcase
        case (ex_thread)
            THREAD_1: ex_pc = pc1;
            THREAD_2: ex_pc = pc2;
            default:  ex_pc = pc0;
        endcase
    end

endmodule