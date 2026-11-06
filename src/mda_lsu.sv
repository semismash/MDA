import mda_pkg::*;

// Load/store unit: checks, data memory controls, store strobe and data, and the load-return registers, takes ALU result for address
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
    input  Thread        ex_thread,     // thread of the instruction in EX
    input  Word          dm_rdata,      // data memory read data (valid the cycle after the access)
    // OUTPUTS:
    // data memory (to mda_dmem core port)
    output logic         dm_en,         // mem access valid
    output logic         dm_we,         // HIGH = write, LOW = read
    output DmemWordAddr  dm_addr,       // data memory address for access (no seperate read or write, only one at a time)
    output Word          dm_wdata,      // data memory data for load/store
    output logic [3:0]   dm_wstrb,      // strobe (for differentiating between byte and word accesses)
    // fault (to mda_fault)
    output logic         fault,             // low = is fault, high = iss not fault
    output logic         lsu_fault_type,    // low = misaligned, high = out of bounds
    // load return (to mda_wb)
    output logic         ld_valid,
    output RegAddr       ld_rd,
    output Thread        ld_thread,
    output Word          ld_data
);

    // is there a memory access in EX
    logic is_access;
    logic is_store;
    assign is_access = ex_v & (|mem_op);
    assign is_store  = is_access & (mem_op == MEM_STORE);

    // prechecks: a word access must be aligned, and the address must be inside the data memory
    logic misaligned;
    logic out_of_bounds;
    assign misaligned    = ~mem_byte & (addr[1:0] != 2'b00);
    assign out_of_bounds = |addr[DATA_WIDTH-1:DMEM_BYTE_ADDR_WIDTH];
    assign fault         = is_access & (misaligned | out_of_bounds);
    assign lsu_fault_type = out_of_bounds & ~misaligned;    // misaligned wins when both apply

    // data memory request: one access per cycle, nothing is ever in flight longer than one cycle. A faulting access sends no request
    assign dm_en    = is_access & ~fault;
    assign dm_we    = is_store;
    assign dm_addr  = addr[DMEM_ADDR_WIDTH+1:2];
    assign dm_wdata = mem_byte ? {4{store_data[7:0]}} : store_data;     // byte store repeats the byte, the strobe picks the lane

    // byte strobe (little-endian: lane 0 is bits [7:0])
    always_comb begin
        casez ({is_store, mem_byte})
            2'b0?:   dm_wstrb = 4'b0000;                // load or no access
            2'b10:   dm_wstrb = 4'b1111;                // sw
            default: dm_wstrb = 4'b0001 << addr[1:0];   // sb
        endcase
    end

    // load return: the memory data arrives one cycle after the access, when EX already holds the next thread's instruction
    logic       ld_byte;
    logic [1:0] ld_lane;
    logic       ld_fault;

    // control state, reset
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) ld_valid <= 1'b0;
        else        ld_valid <= is_access & (mem_op == MEM_LOAD);   // a faulting load still returns (zero)
    end

    // payload, not reset (qualified by ld_valid)
    always_ff @(posedge clk) begin
        ld_rd     <= rd_addr;
        ld_thread <= ex_thread;
        ld_byte   <= mem_byte;
        ld_lane   <= addr[1:0];
        ld_fault  <= fault;
    end

    logic [7:0] byte_val;
    always_comb begin
        case (ld_lane)
            2'd0:    byte_val = dm_rdata[7:0];
            2'd1:    byte_val = dm_rdata[15:8];
            2'd2:    byte_val = dm_rdata[23:16];
            default: byte_val = dm_rdata[31:24];
        endcase
    end

    // lb zero-extends the selected byte, lw passes the word, a faulting load returns 0
    assign ld_data = ld_fault ? '0 : (ld_byte ? {{(DATA_WIDTH-8){1'b0}}, byte_val} : dm_rdata);

endmodule
