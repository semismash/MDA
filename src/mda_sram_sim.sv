// Behavioral single-port synchronous RAM with a per-bit write mask
//
// Models the IHP SRAM macro interface used by mda_imem and mda_dmem:
//   - one access per cycle, selected by mem_en
//   - mem_we writes the bits of wdata selected by wmask (1 = write)
//   - mem_re reads; the data appears on rdata in the next cycle and is held until the next read
//   - both mem_we and mem_re in one cycle: write-through, rdata returns the merged (new) data
// Used for simulation and for FPGA builds (the array infers block or distributed RAM).

module mda_sram_sim #(
    parameter ADDR_WIDTH = 10,
    parameter DATA_WIDTH = 16
) (
    // clock
    input  logic                  clk,
    // INPUTS:
    input  logic                  mem_en,       // access enable
    input  logic                  mem_we,       // write enable
    input  logic                  mem_re,       // read enable
    input  logic [ADDR_WIDTH-1:0] addr,         // word address
    input  logic [DATA_WIDTH-1:0] wdata,        // write data
    input  logic [DATA_WIDTH-1:0] wmask,        // per-bit write mask, 1 = write this bit
    // OUTPUTS:
    output logic [DATA_WIDTH-1:0] rdata         // read data, valid the cycle after the read
);

    logic [DATA_WIDTH-1:0] mem [0:(1 << ADDR_WIDTH) - 1];
    logic [DATA_WIDTH-1:0] merged;

    // old data with the masked bits replaced
    assign merged = (mem[addr] & ~wmask) | (wdata & wmask);

    always_ff @(posedge clk) begin
        if (mem_en) begin
            if (mem_we) mem[addr] <= merged;
            if (mem_re) rdata <= mem_we ? merged : mem[addr];
        end
    end

endmodule
