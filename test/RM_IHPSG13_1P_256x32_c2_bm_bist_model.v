// Simulation-only STAND-IN for the IHP 256x32 macro (not the foundry model).
// Behavior assumed from the datasheet: one-cycle read, 1 in A_BM means the bit is written,
// both enables set is write-through. Replace with the foundry model when it is available.
`timescale 1ns/10ps
module RM_IHPSG13_1P_256x32_c2_bm_bist (
    input A_CLK,
    input A_MEN,
    input A_WEN,
    input A_REN,
    input [7:0] A_ADDR,
    input [31:0] A_DIN,
    input A_DLY,
    output [31:0] A_DOUT,
    input [31:0] A_BM,
    input A_BIST_CLK,
    input A_BIST_EN,
    input A_BIST_MEN,
    input A_BIST_WEN,
    input A_BIST_REN,
    input [7:0] A_BIST_ADDR,
    input [31:0] A_BIST_DIN,
    input [31:0] A_BIST_BM
);
  reg [31:0] mem [0:255];
  reg [31:0] dout_r;
  assign A_DOUT = dout_r;

  initial dout_r = 32'bx;

  wire [31:0] merged = (mem[A_ADDR] & ~A_BM) | (A_DIN & A_BM);

  always @(posedge A_CLK) begin
    if (A_DLY !== 1'b1) $display("%m: A_DLY must be tied to 1");
    if (A_MEN && !A_BIST_EN) begin
      if (A_WEN) mem[A_ADDR] <= merged;
      if (A_REN) dout_r <= A_WEN ? merged : mem[A_ADDR];
    end
  end
endmodule
