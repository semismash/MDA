import mda_pkg::*;

module pc #(
    parameter ADDR_WIDTH = mda_pkg::IMEM_ADDR_WIDTH
) (
    // clock & reset
    input  logic  clk,
    input  logic  rst_n,
    // INPUTS:
    // input 1
    input  logic  pc_in1,    // choose between PC itself and rs1 for the first PC input
    input  PcAddr rs1_in,    // (MUX if above input is high, take only bottom 10 bits)
    // input 2
    input  logic  pc_in2,    // choose between +1 and imm in for second PC input
    input  PcAddr imm_in,    // (MUX if above input is high, take only bottom 10 bits)
    // output
    output pc_out
);

    PcAddr pc, pc_next;

    always_comb begin
        Word in1, in2;
        in1 = (pc_in1) ? pc : rs1_in;
        in2 = (pc_in2) ? {{(IMEM_ADDR_WIDTH-1){1'b0}}, 1'b1} : imm_in;
        pc_next = in1 + in2;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) pc <= '0;
        else pc <= pc_next;
    end

endmodule
