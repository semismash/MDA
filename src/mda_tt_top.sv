import mda_pkg::*;

// Tiny Tapeout wrapper, Stage A harness: reset synchronizer, an automatic go after reset, and an 8-bit trace hash on uo_out that keeps the core alive.
// The module name must match top_module in info.yaml. Programs run from whatever the memories hold until the hardware loader exists (Stage B).
module tt_um_mda (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    // reset: both edges synchronized, the synchronized signal drives the asynchronous reset of every flop
    logic rst_n_sync;
    mda_sync #(.WIDTH(1)) u_rst_sync (
        .clk (clk),
        .d   (rst_n),
        .q   (rst_n_sync)
    );

    // go: one pulse in the first cycle after reset is released
    logic rst_q;
    logic go;
    always_ff @(posedge clk or negedge rst_n_sync) begin
        if (!rst_n_sync) rst_q <= 1'b0;
        else             rst_q <= 1'b1;
    end
    assign go = rst_n_sync & ~rst_q;

    logic         tr_valid, tr_rd_we, tr_zn_we, tr_z, tr_n, tr_c_we, tr_c, tr_taken, tr_fault, tr_ld_valid;
    Thread        tr_thread, tr_ld_thread;
    PcAddr        tr_pc;
    Instruction   tr_instr;
    RegAddr       tr_rd, tr_ld_rd;
    Word          tr_wdata, tr_mem_addr, tr_ld_data;
    Flags         tr_flags;
    Cause         tr_fault_cause;

    mda_top u_top (
        .clk            (clk),
        .rst_n          (rst_n_sync),
        .go             (go),
        .entry_pc0      ({IMEM_ADDR_WIDTH{1'b0}}),
        .entry_pc1      ({IMEM_ADDR_WIDTH{1'b0}}),
        .entry_pc2      ({IMEM_ADDR_WIDTH{1'b0}}),
        .imem_ld_we     (1'b0),
        .imem_ld_addr   ({IMEM_ADDR_WIDTH{1'b0}}),
        .imem_ld_data   ({INSTR_WIDTH{1'b0}}),
        .dmem_ld_we     (1'b0),
        .dmem_ld_addr   ({DMEM_ADDR_WIDTH{1'b0}}),
        .dmem_ld_data   ({DATA_WIDTH{1'b0}}),
        .tr_valid       (tr_valid),
        .tr_thread      (tr_thread),
        .tr_pc          (tr_pc),
        .tr_instr       (tr_instr),
        .tr_rd_we       (tr_rd_we),
        .tr_rd          (tr_rd),
        .tr_wdata       (tr_wdata),
        .tr_flags       (tr_flags),
        .tr_zn_we       (tr_zn_we),
        .tr_z           (tr_z),
        .tr_n           (tr_n),
        .tr_c_we        (tr_c_we),
        .tr_c           (tr_c),
        .tr_taken       (tr_taken),
        .tr_fault       (tr_fault),
        .tr_fault_cause (tr_fault_cause),
        .tr_mem_addr    (tr_mem_addr),
        .tr_ld_valid    (tr_ld_valid),
        .tr_ld_thread   (tr_ld_thread),
        .tr_ld_rd       (tr_ld_rd),
        .tr_ld_data     (tr_ld_data)
    );

    // trace hash: folds every register write, load return, jump and fault into 8 bits
    logic [7:0] hash;
    logic [7:0] fold_ex, fold_ld;
    assign fold_ex = tr_wdata[7:0] ^ tr_wdata[15:8] ^ tr_wdata[23:16] ^ tr_wdata[31:24];
    assign fold_ld = tr_ld_data[7:0] ^ tr_ld_data[15:8] ^ tr_ld_data[23:16] ^ tr_ld_data[31:24];

    always_ff @(posedge clk or negedge rst_n_sync) begin
        if (!rst_n_sync) hash <= 8'd0;
        else             hash <= 
        {hash[6:0], hash[7]}
            ^ ((tr_valid & tr_rd_we) ? fold_ex : 8'd0)
            ^ (tr_ld_valid ? fold_ld : 8'd0)
            ^ {6'd0, tr_taken, tr_fault}
            ^ (tr_valid ? tr_pc[7:0] : 8'd0);
    end

    assign uo_out  = hash;
    assign uio_out = 8'd0;
    assign uio_oe  = 8'd0;

    // inputs not used in Stage A
    wire _unused = &{ena, ui_in, uio_in, 1'b0};

endmodule