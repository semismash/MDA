import mda_pkg::*;

// MDA top: the core with its instruction and data memories, and the loader write ports (used by the testbench, later by the hardware loader).
module mda_top (
    // clock and reset
    input  logic         clk,
    input  logic         rst_n,
    // INPUTS:
    input  logic         go,
    input  PcAddr        entry_pc0,
    input  PcAddr        entry_pc1,
    input  PcAddr        entry_pc2,
    // loader write ports (only while the threads are held)
    input  logic         imem_ld_we,
    input  PcAddr        imem_ld_addr,
    input  Instruction   imem_ld_data,
    input  logic         dmem_ld_we,
    input  DmemWordAddr  dmem_ld_addr,
    input  Word          dmem_ld_data,
    // OUTPUTS: trace, passed through from the core
    output logic         tr_valid,
    output Thread        tr_thread,
    output PcAddr        tr_pc,
    output Instruction   tr_instr,
    output logic         tr_rd_we,
    output RegAddr       tr_rd,
    output Word          tr_wdata,
    output Flags         tr_flags,
    output logic         tr_zn_we,
    output logic         tr_z,
    output logic         tr_n,
    output logic         tr_c_we,
    output logic         tr_c,
    output logic         tr_taken,
    output logic         tr_fault,
    output Cause         tr_fault_cause,
    output Word          tr_mem_addr,
    output logic         tr_ld_valid,
    output Thread        tr_ld_thread,
    output RegAddr       tr_ld_rd,
    output Word          tr_ld_data
);

    logic        imem_en;
    PcAddr       imem_addr;
    Instruction  imem_data;
    logic        dm_en, dm_we;
    DmemWordAddr dm_addr;
    Word         dm_wdata, dm_rdata;
    logic [3:0]  dm_wstrb;

    mda_core u_core (
        .clk            (clk),
        .rst_n          (rst_n),
        .go             (go),
        .entry_pc0      (entry_pc0),
        .entry_pc1      (entry_pc1),
        .entry_pc2      (entry_pc2),
        .imem_data      (imem_data),
        .dm_rdata       (dm_rdata),
        .imem_en        (imem_en),
        .imem_addr      (imem_addr),
        .dm_en          (dm_en),
        .dm_we          (dm_we),
        .dm_addr        (dm_addr),
        .dm_wdata       (dm_wdata),
        .dm_wstrb       (dm_wstrb),
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

    mda_imem u_imem (
        .clk     (clk),
        .if_en   (imem_en),
        .if_addr (imem_addr),
        .ld_we   (imem_ld_we),
        .ld_addr (imem_ld_addr),
        .ld_data (imem_ld_data),
        .if_data (imem_data)
    );

    mda_dmem u_dmem (
        .clk        (clk),
        .core_en    (dm_en),
        .core_we    (dm_we),
        .core_addr  (dm_addr),
        .core_wdata (dm_wdata),
        .core_wstrb (dm_wstrb),
        .ld_we      (dmem_ld_we),
        .ld_addr    (dmem_ld_addr),
        .ld_wdata   (dmem_ld_data),
        .core_rdata (dm_rdata)
    );

endmodule
