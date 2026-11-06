import mda_pkg::*;

// MDA core, Stage A: three-thread barrel pipeline (IF, ID, EX). The instruction and data memories are outside, behind the imem_* and dm_* ports.
module mda_core (
    // clock and reset
    input  logic         clk,
    input  logic         rst_n,
    // INPUTS:
    input  logic         go,            // one-cycle pulse: load the entry points and release the threads
    input  PcAddr        entry_pc0,
    input  PcAddr        entry_pc1,
    input  PcAddr        entry_pc2,
    input  Instruction   imem_data,     // instruction memory read data (valid the cycle after imem_addr)
    input  Word          dm_rdata,      // data memory read data (valid the cycle after a load)
    // OUTPUTS:
    // instruction memory
    output logic         imem_en,
    output PcAddr        imem_addr,
    // data memory
    output logic         dm_en,
    output logic         dm_we,
    output DmemWordAddr  dm_addr,
    output Word          dm_wdata,
    output logic [3:0]   dm_wstrb,
    // trace: one record per instruction in EX, and one per load return
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

    // run: set by go, cleared by reset
    logic run;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)  run <= 1'b0;
        else if (go) run <= 1'b1;
    end

    // scheduler
    Thread if_thread, id_thread;
    logic  id_v;

    mda_sched u_sched (
        .clk       (clk),
        .rst_n     (rst_n),
        .run       (run),
        .if_thread (if_thread),
        .id_thread (id_thread),
        .id_v      (id_v)
    );

    // EX stage signals (from mda_id_ex), needed by fetch
    logic        ex_v;
    Thread       ex_thread;
    Instruction  ex_instr;
    Word         ex_rs1_data, ex_rs2_data, ex_imm;
    RegAddr      ex_rd_addr;
    logic        ex_reg_write, ex_use_imm, ex_fwd_imm, ex_f_u_alu, ex_illegal;
    logic        ex_br_jof_inv, ex_br_joc_all, ex_mem_byte, ex_sp_valid;
    AluOp        ex_alu_op;
    ResSel       ex_res_sel;
    BrType       ex_br_type;
    MemOp        ex_mem_op;
    SpOp         ex_sp_op;

    // fetch
    PcAddr if_pc, ex_pc;
    logic  pc_in1, pc_in2, pc_cin;
    PcAddr pc_offset;

    mda_fetch u_fetch (
        .clk        (clk),
        .rst_n      (rst_n),
        .go         (go),
        .entry_pc0  (entry_pc0),
        .entry_pc1  (entry_pc1),
        .entry_pc2  (entry_pc2),
        .if_thread  (if_thread),
        .ex_v       (ex_v),
        .ex_thread  (ex_thread),
        .pc_in1     (pc_in1),
        .rs1_pc     (ex_rs1_data[IMEM_ADDR_WIDTH-1:0]),
        .pc_in2     (pc_in2),
        .pc_offset  (pc_offset),
        .pc_cin     (pc_cin),
        .if_pc      (if_pc),
        .ex_pc      (ex_pc)
    );

    assign imem_en   = run;
    assign imem_addr = if_pc;

    // ID stage: the instruction memory output is the IF/ID register
    Instruction id_instr;
    assign id_instr = imem_data;

    ThreadSel id_t;
    assign id_t = {(id_thread == THREAD_2), (id_thread == THREAD_1), (id_thread == THREAD_0)};

    logic       suffix_pend;
    RegAddr     suffix_rd;
    logic [7:0] suffix_imm8;
    logic       lli_first;

    RegAddr rs1_addr, rs2_addr, rd_addr;
    logic   reg_write, use_imm, fwd_imm, f_u_alu, illegal;
    logic   br_jof_inv, br_joc_all, mem_byte, sp_valid;
    AluOp   alu_op;
    ResSel  res_sel;
    ImmSel  imm_sel;
    BrType  br_type;
    MemOp   mem_op;
    SpOp    sp_op;

    mda_decoder u_decoder (
        .instr       (id_instr),
        .suffix_pend (suffix_pend),
        .suffix_rd   (suffix_rd),
        .rs1_addr    (rs1_addr),
        .rs2_addr    (rs2_addr),
        .rd_addr     (rd_addr),
        .reg_write   (reg_write),
        .alu_op      (alu_op),
        .use_imm     (use_imm),
        .fwd_imm     (fwd_imm),
        .res_sel     (res_sel),
        .imm_sel     (imm_sel),
        .f_u_alu     (f_u_alu),
        .illegal     (illegal),
        .br_type     (br_type),
        .br_jof_inv  (br_jof_inv),
        .br_joc_all  (br_joc_all),
        .mem_op      (mem_op),
        .mem_byte    (mem_byte),
        .lli_first   (lli_first),
        .sp_valid    (sp_valid),
        .sp_op       (sp_op)
    );

    mda_suffix u_suffix (
        .clk         (clk),
        .rst_n       (rst_n),
        .id_t        (id_t),
        .id_v        (id_v),
        .lli_first   (lli_first),
        .instr       (id_instr),
        .suffix_pend (suffix_pend),
        .suffix_rd   (suffix_rd),
        .suffix_imm8 (suffix_imm8)
    );

    // register bank: read in ID, written from EX (and the load return)
    Word    id_rs1_data, id_rs2_data, id_imm;
    logic   w_ex_we, w_ld_we;
    Thread  w_ex_thread, w_ld_thread;
    RegAddr w_ex_addr, w_ld_addr;
    Word    w_ex_data, w_ld_data;

    mda_regbank u_regbank (
        .clk         (clk),
        .rd_thread   (id_thread),
        .r_addr1     (rs1_addr),
        .r_addr2     (rs2_addr),
        .w_ex_we     (w_ex_we),
        .w_ex_thread (w_ex_thread),
        .w_ex_addr   (w_ex_addr),
        .w_ex_data   (w_ex_data),
        .w_ld_we     (w_ld_we),
        .w_ld_thread (w_ld_thread),
        .w_ld_addr   (w_ld_addr),
        .w_ld_data   (w_ld_data),
        .r_data1     (id_rs1_data),
        .r_data2     (id_rs2_data)
    );

    mda_imm_gen u_imm_gen (
        .instr       (id_instr),
        .imm_sel     (imm_sel),
        .rs1_data    (id_rs1_data),
        .suffix_imm8 (suffix_imm8),
        .imm_out     (id_imm)
    );

    // ID/EX register
    mda_id_ex u_id_ex (
        .clk           (clk),
        .rst_n         (rst_n),
        .id_v          (id_v),
        .id_thread     (id_thread),
        .id_instr      (id_instr),
        .id_rs1_data   (id_rs1_data),
        .id_rs2_data   (id_rs2_data),
        .id_imm        (id_imm),
        .id_rd_addr    (rd_addr),
        .id_reg_write  (reg_write),
        .id_alu_op     (alu_op),
        .id_use_imm    (use_imm),
        .id_fwd_imm    (fwd_imm),
        .id_res_sel    (res_sel),
        .id_f_u_alu    (f_u_alu),
        .id_illegal    (illegal),
        .id_br_type    (br_type),
        .id_br_jof_inv (br_jof_inv),
        .id_br_joc_all (br_joc_all),
        .id_mem_op     (mem_op),
        .id_mem_byte   (mem_byte),
        .id_sp_valid   (sp_valid),
        .id_sp_op      (sp_op),
        .ex_v          (ex_v),
        .ex_thread     (ex_thread),
        .ex_instr      (ex_instr),
        .ex_rs1_data   (ex_rs1_data),
        .ex_rs2_data   (ex_rs2_data),
        .ex_imm        (ex_imm),
        .ex_rd_addr    (ex_rd_addr),
        .ex_reg_write  (ex_reg_write),
        .ex_alu_op     (ex_alu_op),
        .ex_use_imm    (ex_use_imm),
        .ex_fwd_imm    (ex_fwd_imm),
        .ex_res_sel    (ex_res_sel),
        .ex_f_u_alu    (ex_f_u_alu),
        .ex_illegal    (ex_illegal),
        .ex_br_type    (ex_br_type),
        .ex_br_jof_inv (ex_br_jof_inv),
        .ex_br_joc_all (ex_br_joc_all),
        .ex_mem_op     (ex_mem_op),
        .ex_mem_byte   (ex_mem_byte),
        .ex_sp_valid   (ex_sp_valid),
        .ex_sp_op      (ex_sp_op)
    );

    // EX stage
    mda_ex u_ex (
        .clk            (clk),
        .rst_n          (rst_n),
        .ex_v           (ex_v),
        .ex_thread      (ex_thread),
        .ex_instr       (ex_instr),
        .ex_rs1_data    (ex_rs1_data),
        .ex_rs2_data    (ex_rs2_data),
        .ex_imm         (ex_imm),
        .ex_rd_addr     (ex_rd_addr),
        .ex_reg_write   (ex_reg_write),
        .ex_alu_op      (ex_alu_op),
        .ex_use_imm     (ex_use_imm),
        .ex_fwd_imm     (ex_fwd_imm),
        .ex_res_sel     (ex_res_sel),
        .ex_f_u_alu     (ex_f_u_alu),
        .ex_illegal     (ex_illegal),
        .ex_br_type     (ex_br_type),
        .ex_br_jof_inv  (ex_br_jof_inv),
        .ex_br_joc_all  (ex_br_joc_all),
        .ex_mem_op      (ex_mem_op),
        .ex_mem_byte    (ex_mem_byte),
        .ex_sp_valid    (ex_sp_valid),
        .ex_pc          (ex_pc),
        .dm_rdata       (dm_rdata),
        .pc_in1         (pc_in1),
        .pc_in2         (pc_in2),
        .pc_cin         (pc_cin),
        .pc_offset      (pc_offset),
        .dm_en          (dm_en),
        .dm_we          (dm_we),
        .dm_addr        (dm_addr),
        .dm_wdata       (dm_wdata),
        .dm_wstrb       (dm_wstrb),
        .w_ex_we        (w_ex_we),
        .w_ex_thread    (w_ex_thread),
        .w_ex_addr      (w_ex_addr),
        .w_ex_data      (w_ex_data),
        .w_ld_we        (w_ld_we),
        .w_ld_thread    (w_ld_thread),
        .w_ld_addr      (w_ld_addr),
        .w_ld_data      (w_ld_data),
        .tr_flags       (tr_flags),
        .tr_zn_we       (tr_zn_we),
        .tr_z           (tr_z),
        .tr_n           (tr_n),
        .tr_c_we        (tr_c_we),
        .tr_c           (tr_c),
        .tr_taken       (tr_taken),
        .tr_fault       (tr_fault),
        .tr_fault_cause (tr_fault_cause),
        .tr_mem_addr    (tr_mem_addr)
    );

    // trace
    assign tr_valid     = ex_v;
    assign tr_thread    = ex_thread;
    assign tr_pc        = ex_pc;
    assign tr_instr     = ex_instr;
    assign tr_rd_we     = w_ex_we;
    assign tr_rd        = w_ex_addr;
    assign tr_wdata     = w_ex_data;
    assign tr_ld_valid  = w_ld_we;
    assign tr_ld_thread = w_ld_thread;
    assign tr_ld_rd     = w_ld_addr;
    assign tr_ld_data   = w_ld_data;

endmodule
