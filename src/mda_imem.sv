import mda_pkg::*;

// instruction memory wrapper
//   - core side: read only, one fetch per cycle while the threads run
//   - loader side: write only, used while the threads are held (priority over fetch)
//   - single port: the data of a fetch appears the cycle after if_addr (this is the IF/ID stage register)
// Selection of the memory implementation:
//   MDA_SRAM_MACRO defined: the IHP 1024x16 macro (ASIC build)
//   otherwise:              sram_sim, a behavioral RAM (simulation and FPGA)
// ADDR_WIDTH must stay equal to IMEM_ADDR_WIDTH. The macro exists only in the 1024 x 16 size.
module mda_imem #(
    parameter ADDR_WIDTH = IMEM_ADDR_WIDTH
) (
    // clock
    input  logic       clk,
    // INPUTS:
    // fetch port (core)
    input  logic       if_en,       // fetch enable (threads running)
    input  PcAddr      if_addr,     // fetch address, in halfwords
    // loader port
    input  logic       ld_we,       // write enable, priority over fetch
    input  PcAddr      ld_addr,     // write address, in halfwords
    input  Instruction ld_data,     // write data
    // OUTPUTS:
    output Instruction if_data      // fetched instruction, valid in the cycle after if_addr
);

    logic   mem_en, mem_we, mem_re;
    PcAddr  mem_addr;

    assign mem_en   = if_en | ld_we;
    assign mem_we   = ld_we;
    assign mem_re   = if_en & ~ld_we;
    assign mem_addr = ld_we ? ld_addr : if_addr;

`ifdef MDA_SRAM_MACRO
    RM_IHPSG13_1P_1024x16_c2_bm_bist u_sram (
        .A_CLK       (clk),
        .A_MEN       (mem_en),
        .A_WEN       (mem_we),
        .A_REN       (mem_re),
        .A_ADDR      (mem_addr),
        .A_DIN       (ld_data),
        .A_DLY       (1'b1),
        .A_DOUT      (if_data),
        .A_BM        ({INSTR_WIDTH{1'b1}}),
        .A_BIST_CLK  (1'b0),
        .A_BIST_EN   (1'b0),
        .A_BIST_MEN  (1'b0),
        .A_BIST_WEN  (1'b0),
        .A_BIST_REN  (1'b0),
        .A_BIST_ADDR ({ADDR_WIDTH{1'b0}}),
        .A_BIST_DIN  ({INSTR_WIDTH{1'b0}}),
        .A_BIST_BM   ({INSTR_WIDTH{1'b0}})
    );
`else
    mda_sram_sim #(
        .ADDR_WIDTH (ADDR_WIDTH),
        .DATA_WIDTH (INSTR_WIDTH)
    ) u_sram (
        .clk    (clk),
        .mem_en (mem_en),
        .mem_we (mem_we),
        .mem_re (mem_re),
        .addr   (mem_addr),
        .wdata  (ld_data),
        .wmask  ({INSTR_WIDTH{1'b1}}),
        .rdata  (if_data)
    );
`endif

endmodule
