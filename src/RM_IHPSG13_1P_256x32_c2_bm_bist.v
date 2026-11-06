// Blackbox stub of the IHP SRAM macro: netlist view in config.json, also listed in info.yaml source_files.
// Port widths assumed from the 1024x16 member of the family: check against the PDK file verilog/RM_IHPSG13_1P_256x32_c2_bm_bist.v.
(* blackbox *)
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

endmodule