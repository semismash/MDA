// Simulation-only STAND-IN for the IHP 1024x16 macro (not the foundry model).
// Behavior assumed from the datasheet: one-cycle read, 1 in A_BM means the bit is written,
// both enables set is write-through. Replace with the foundry model when it is available.
`timescale 1ns/10ps
module RM_IHPSG13_1P_1024x16_c2_bm_bist (
    input A_CLK,
    input A_MEN,
    input A_WEN,
    input A_REN,
    input [9:0] A_ADDR,
    input [15:0] A_DIN,
    input A_DLY,
    output [15:0] A_DOUT,
    input [15:0] A_BM,
    input A_BIST_CLK,
    input A_BIST_EN,
    input A_BIST_MEN,
    input A_BIST_WEN,
    input A_BIST_REN,
    input [9:0] A_BIST_ADDR,
    input [15:0] A_BIST_DIN,
    input [15:0] A_BIST_BM
);
  reg [15:0] mem [0:1023];
  reg [15:0] dout_r;
  assign A_DOUT = dout_r;

  initial dout_r = 16'bx;

  wire [15:0] merged = (mem[A_ADDR] & ~A_BM) | (A_DIN & A_BM);

  always @(posedge A_CLK) begin
    if (A_DLY !== 1'b1) $display("%m: A_DLY must be tied to 1");
    if (A_MEN && !A_BIST_EN) begin
      if (A_WEN) mem[A_ADDR] <= merged;
      if (A_REN) dout_r <= A_WEN ? merged : mem[A_ADDR];
    end
  end
endmodule
