import mda_pkg::*;
import mda_isa_pkg::*;

// EX stage: ALU, jump control, load/store, fault collection, write-back and the three per-thread flag registers. Only the thread in EX is active.
module mda_ex (
    // clock and reset
    input  logic        clk,
    input  logic        rst_n,
    // INPUTS (from mda_id_ex):
    input  logic        ex_v,
    input  Thread       ex_thread,
    input  Instruction  ex_instr,
    input  Word         ex_rs1_data,
    input  Word         ex_rs2_data,
    input  Word         ex_imm,
    input  RegAddr      ex_rd_addr,
    input  logic        ex_reg_write,
    input  AluOp        ex_alu_op,
    input  logic        ex_use_imm,
    input  logic        ex_fwd_imm,
    input  ResSel       ex_res_sel,
    input  logic        ex_f_u_alu,
    input  logic        ex_illegal,
    input  BrType       ex_br_type,
    input  logic        ex_br_jof_inv,
    input  logic        ex_br_joc_all,
    input  MemOp        ex_mem_op,
    input  logic        ex_mem_byte,
    input  logic        ex_sp_valid,
    // from mda_fetch and the data memory
    input  PcAddr       ex_pc,          // PC of the thread in EX
    input  Word         dm_rdata,       // data memory read data
    // OUTPUTS:
    // to mda_fetch
    output logic        pc_in1,
    output logic        pc_in2,
    output logic        pc_cin,
    output PcAddr       pc_offset,
    // to the data memory
    output logic        dm_en,
    output logic        dm_we,
    output DmemWordAddr dm_addr,
    output Word         dm_wdata,
    output logic [3:0]  dm_wstrb,
    // to mda_regbank
    output logic        w_ex_we,
    output Thread       w_ex_thread,
    output RegAddr      w_ex_addr,
    output Word         w_ex_data,
    output logic        w_ld_we,
    output Thread       w_ld_thread,
    output RegAddr      w_ld_addr,
    output Word         w_ld_data,
    // trace
    output Flags        tr_flags,       // flags of the thread in EX, as seen by this instruction
    output logic        tr_zn_we,       // this instruction updates Z and N
    output logic        tr_z,
    output logic        tr_n,
    output logic        tr_c_we,        // this instruction updates C
    output logic        tr_c,
    output logic        tr_taken,       // the jump is taken
    output logic        tr_fault,       // a fault in this instruction
    output Cause        tr_fault_cause,
    output Word         tr_mem_addr     // effective address (the ALU result)
);

    // ALU
    Word  alu_result;
    logic alu_zero, alu_neg, alu_carry, alu_carry_upd;

    mda_alu u_alu (
        .alu_op        (ex_alu_op),
        .rs1_data      (ex_rs1_data),
        .rs2_data      (ex_rs2_data),
        .use_imm       (ex_use_imm),
        .imm           (ex_imm),
        .fwd_imm       (ex_fwd_imm),
        .result        (alu_result),
        .alu_zero      (alu_zero),
        .alu_neg       (alu_neg),
        .alu_carry     (alu_carry),
        .alu_carry_upd (alu_carry_upd)
    );

    // jump control
    logic  taken;
    PcAddr link;
    Flags  flags_ex;

    mda_branch_unit u_branch (
        .ex_v       (ex_v),
        .br_type    (ex_br_type),
        .br_jof_inv (ex_br_jof_inv),
        .br_joc_all (ex_br_joc_all),
        .instr      (ex_instr),
        .flags      (flags_ex),
        .rs1_data   (ex_rs1_data),
        .ex_pc      (ex_pc),
        .taken      (taken),
        .pc_in1     (pc_in1),
        .pc_in2     (pc_in2),
        .pc_cin     (pc_cin),
        .pc_offset  (pc_offset),
        .link       (link)
    );

    // load/store
    logic lsu_fault, lsu_fault_type;
    logic ld_valid;
    RegAddr ld_rd;
    Thread  ld_thread;
    Word    ld_data;

    mda_lsu u_lsu (
        .clk            (clk),
        .rst_n          (rst_n),
        .ex_v           (ex_v),
        .mem_op         (ex_mem_op),
        .mem_byte       (ex_mem_byte),
        .addr           (alu_result),
        .store_data     (ex_rs2_data),
        .rd_addr        (ex_rd_addr),
        .ex_thread      (ex_thread),
        .dm_rdata       (dm_rdata),
        .dm_en          (dm_en),
        .dm_we          (dm_we),
        .dm_addr        (dm_addr),
        .dm_wdata       (dm_wdata),
        .dm_wstrb       (dm_wstrb),
        .fault          (lsu_fault),
        .lsu_fault_type (lsu_fault_type),
        .ld_valid       (ld_valid),
        .ld_rd          (ld_rd),
        .ld_thread      (ld_thread),
        .ld_data        (ld_data)
    );

    // faults
    logic u_err, f_err, u_ovr, f_ovr;
    Cause f_errc;
    logic err_now;
    assign err_now = flags_ex[FLAG_ERR];

    mda_fault u_fault (
        .ex_v           (ex_v),
        .illegal        (ex_illegal),
        .lsu_fault      (lsu_fault),
        .lsu_fault_type (lsu_fault_type),
        .err_now        (err_now),
        .u_err          (u_err),
        .f_err          (f_err),
        .f_errc         (f_errc),
        .u_ovr          (u_ovr),
        .f_ovr          (f_ovr)
    );

    // write-back
    mda_wb u_wb (
        .ex_v        (ex_v),
        .ex_thread   (ex_thread),
        .reg_write   (ex_reg_write),
        .sp_valid    (ex_sp_valid),
        .rd_addr     (ex_rd_addr),
        .res_sel     (ex_res_sel),
        .alu_result  (alu_result),
        .link        (link),
        .sp_result   (32'd0),
        .ld_valid    (ld_valid),
        .ld_rd       (ld_rd),
        .ld_thread   (ld_thread),
        .ld_data     (ld_data),
        .w_ex_we     (w_ex_we),
        .w_ex_addr   (w_ex_addr),
        .w_ex_thread (w_ex_thread),
        .w_ex_data   (w_ex_data),
        .w_ld_we     (w_ld_we),
        .w_ld_addr   (w_ld_addr),
        .w_ld_thread (w_ld_thread),
        .w_ld_data   (w_ld_data)
    );

    // per-thread flags: only the register of the thread in EX is updated
    logic u_alu_ex, u_carry_ex;
    logic sel0, sel1, sel2;
    Flags flags0, flags1, flags2;

    assign u_alu_ex   = ex_v & ex_f_u_alu;
    assign u_carry_ex = u_alu_ex & alu_carry_upd;
    assign sel0 = (ex_thread == THREAD_0);
    assign sel1 = (ex_thread == THREAD_1);
    assign sel2 = (ex_thread == THREAD_2);

    mda_flags u_flags0 (
        .clk         (clk),
        .rst_n       (rst_n),
        .u_alu       (u_alu_ex & sel0),
        .f_alu_zero  (alu_zero),
        .f_alu_neg   (alu_neg),
        .f_alu_carry (alu_carry),
        .u_alu_carry (u_carry_ex & sel0),
        .u_err       (u_err & sel0),
        .f_err       (f_err),
        .f_errc      (f_errc),
        .f_isr_rdy   (1'b0),
        .f_osr_empty (1'b1),
        .u_msg_n     (1'b0),
        .f_msg_n     (1'b0),
        .u_msg_p     (1'b0),
        .f_msg_p     (1'b0),
        .f_pe        (1'b0),
        .u_ovr       (u_ovr & sel0),
        .f_ovr       (f_ovr),
        .u_tmr       (1'b0),
        .f_tmr       (1'b0),
        .flags_out   (flags0)
    );

    mda_flags u_flags1 (
        .clk         (clk),
        .rst_n       (rst_n),
        .u_alu       (u_alu_ex & sel1),
        .f_alu_zero  (alu_zero),
        .f_alu_neg   (alu_neg),
        .f_alu_carry (alu_carry),
        .u_alu_carry (u_carry_ex & sel1),
        .u_err       (u_err & sel1),
        .f_err       (f_err),
        .f_errc      (f_errc),
        .f_isr_rdy   (1'b0),
        .f_osr_empty (1'b1),
        .u_msg_n     (1'b0),
        .f_msg_n     (1'b0),
        .u_msg_p     (1'b0),
        .f_msg_p     (1'b0),
        .f_pe        (1'b0),
        .u_ovr       (u_ovr & sel1),
        .f_ovr       (f_ovr),
        .u_tmr       (1'b0),
        .f_tmr       (1'b0),
        .flags_out   (flags1)
    );

    mda_flags u_flags2 (
        .clk         (clk),
        .rst_n       (rst_n),
        .u_alu       (u_alu_ex & sel2),
        .f_alu_zero  (alu_zero),
        .f_alu_neg   (alu_neg),
        .f_alu_carry (alu_carry),
        .u_alu_carry (u_carry_ex & sel2),
        .u_err       (u_err & sel2),
        .f_err       (f_err),
        .f_errc      (f_errc),
        .f_isr_rdy   (1'b0),
        .f_osr_empty (1'b1),
        .u_msg_n     (1'b0),
        .f_msg_n     (1'b0),
        .u_msg_p     (1'b0),
        .f_msg_p     (1'b0),
        .f_pe        (1'b0),
        .u_ovr       (u_ovr & sel2),
        .f_ovr       (f_ovr),
        .u_tmr       (1'b0),
        .f_tmr       (1'b0),
        .flags_out   (flags2)
    );

    // flags of the thread in EX (thread 3 is unused and reads thread 0)
    always_comb begin
        case (ex_thread)
            THREAD_1: flags_ex = flags1;
            THREAD_2: flags_ex = flags2;
            default:  flags_ex = flags0;
        endcase
    end

    assign tr_flags       = flags_ex;
    assign tr_zn_we       = u_alu_ex;
    assign tr_z           = alu_zero;
    assign tr_n           = alu_neg;
    assign tr_c_we        = u_carry_ex;
    assign tr_c           = alu_carry;
    assign tr_taken       = taken;
    assign tr_fault       = ex_v & (lsu_fault | ex_illegal);
    assign tr_fault_cause = f_errc;
    assign tr_mem_addr    = alu_result;

endmodule
