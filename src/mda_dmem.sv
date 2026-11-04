import mda_pkg::*;

// data memory wrapper
//   - core side: loads and stores, at most one access per cycle (only one thread is in EX)
//   - loader side: word writes while the threads are held (priority over the core port)
//   - single port: load data appears the cycle after the address
//   - stores use a per-bit write mask (1 = write), so byte stores are done by the caller with a mask
// Selection of the memory implementation:
//   MDA_SRAM_MACRO defined: the IHP 256x32 macro (ASIC build)
//   otherwise:              sram_sim, a behavioral RAM (simulation and FPGA)
// ADDR_WIDTH must stay equal to DMEM_ADDR_WIDTH. The macro exists only in the 256 x 32 size.
module mda_dmem #(
    parameter ADDR_WIDTH = DMEM_ADDR_WIDTH
) (
    // clock
    input  logic        clk,
    // INPUTS:
    // core port
    input  logic        core_en,        // access enable
    input  logic        core_we,        // 1: store, 0: load
    input  DmemWordAddr core_addr,      // word index
    input  Word         core_wdata,     // store data, already aligned to its byte lane
    input  Word         core_wmask,     // per-bit write mask, 1 = write
    // loader port
    input  logic        ld_we,          // write enable, priority over the core port
    input  DmemWordAddr ld_addr,        // word index
    input  Word         ld_wdata,       // full-word write data
    // OUTPUTS:
    output Word         core_rdata      // load data, valid in the cycle after core_addr
);

    logic         mem_en, mem_we, mem_re;
    DmemWordAddr  mem_addr;
    Word          mem_wdata, mem_wmask;

    assign mem_en    = core_en | ld_we;
    assign mem_we    = ld_we | (core_en & core_we);
    assign mem_re    = core_en & ~core_we & ~ld_we;
    assign mem_addr  = ld_we ? ld_addr  : core_addr;
    assign mem_wdata = ld_we ? ld_wdata : core_wdata;
    assign mem_wmask = ld_we ? {DATA_WIDTH{1'b1}} : core_wmask;

`ifdef MDA_SRAM_MACRO
    RM_IHPSG13_1P_256x32_c2_bm_bist u_sram (
        .A_CLK       (clk),
        .A_MEN       (mem_en),
        .A_WEN       (mem_we),
        .A_REN       (mem_re),
        .A_ADDR      (mem_addr),
        .A_DIN       (mem_wdata),
        .A_DLY       (1'b1),
        .A_DOUT      (core_rdata),
        .A_BM        (mem_wmask),
        .A_BIST_CLK  (1'b0),
        .A_BIST_EN   (1'b0),
        .A_BIST_MEN  (1'b0),
        .A_BIST_WEN  (1'b0),
        .A_BIST_REN  (1'b0),
        .A_BIST_ADDR ({ADDR_WIDTH{1'b0}}),
        .A_BIST_DIN  ({DATA_WIDTH{1'b0}}),
        .A_BIST_BM   ({DATA_WIDTH{1'b0}})
    );
`else
    mda_sram_sim #(
        .ADDR_WIDTH (ADDR_WIDTH),
        .DATA_WIDTH (DATA_WIDTH)
    ) u_sram (
        .clk    (clk),
        .mem_en (mem_en),
        .mem_we (mem_we),
        .mem_re (mem_re),
        .addr   (mem_addr),
        .wdata  (mem_wdata),
        .wmask  (mem_wmask),
        .rdata  (core_rdata)
    );
`endif

endmodule