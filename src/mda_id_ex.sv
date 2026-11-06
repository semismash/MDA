import mda_pkg::*;

// ID/EX pipeline register
// please note that only nly ex_v is reset; the payload is not, v just indicdates if its valid or NOP
module mda_id_ex (
    // clock and reset
    input  logic        clk,
    input  logic        rst_n,
    // INPUTS (ID stage):
    input  logic        id_v,           // the ID stage holds a real instruction
    input  Instruction  id_instr,       // raw instruction word (trace, Stage B fields, jof flag, joc invert)
    // operands
    input  Word         id_rs1_data,    // register read port 1
    input  Word         id_rs2_data,    // register read port 2 (store data)
    input  Word         id_imm,         // immediate from mda_imm_gen
    // decoder outputs
    input  RegAddr      id_rd_addr,
    input  logic        id_reg_write,
    input  AluOp        id_alu_op,
    input  logic        id_use_imm,
    input  logic        id_fwd_imm,
    input  ResSel       id_res_sel,
    input  logic        id_f_u_alu,
    input  logic        id_illegal,
    input  BrType       id_br_type,
    input  logic        id_br_jof_inv,
    input  logic        id_br_joc_all,
    input  MemOp        id_mem_op,
    input  logic        id_mem_byte,
    input  logic        id_sp_valid,
    input  SpOp         id_sp_op,
    // OUTPUTS (EX stage):
    output logic        ex_v,           // the EX stage holds a real instruction
    output Instruction  ex_instr,
    output Word         ex_rs1_data,
    output Word         ex_rs2_data,
    output Word         ex_imm,
    output RegAddr      ex_rd_addr,
    output logic        ex_reg_write,
    output AluOp        ex_alu_op,
    output logic        ex_use_imm,
    output logic        ex_fwd_imm,
    output ResSel       ex_res_sel,
    output logic        ex_f_u_alu,
    output logic        ex_illegal,
    output BrType       ex_br_type,
    output logic        ex_br_jof_inv,
    output logic        ex_br_joc_all,
    output MemOp        ex_mem_op,
    output logic        ex_mem_byte,
    output logic        ex_sp_valid,
    output SpOp         ex_sp_op
);

    // control state, reset
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) ex_v <= 1'b0;
        else        ex_v <= id_v;
    end

    // payload, not reset
    always_ff @(posedge clk) begin
        ex_instr      <= id_instr;
        ex_rs1_data   <= id_rs1_data;
        ex_rs2_data   <= id_rs2_data;
        ex_imm        <= id_imm;
        ex_rd_addr    <= id_rd_addr;
        ex_reg_write  <= id_reg_write;
        ex_alu_op     <= id_alu_op;
        ex_use_imm    <= id_use_imm;
        ex_fwd_imm    <= id_fwd_imm;
        ex_res_sel    <= id_res_sel;
        ex_f_u_alu    <= id_f_u_alu;
        ex_illegal    <= id_illegal;
        ex_br_type    <= id_br_type;
        ex_br_jof_inv <= id_br_jof_inv;
        ex_br_joc_all <= id_br_joc_all;
        ex_mem_op     <= id_mem_op;
        ex_mem_byte   <= id_mem_byte;
        ex_sp_valid   <= id_sp_valid;
        ex_sp_op      <= id_sp_op;
    end

endmodule