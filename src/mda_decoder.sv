import mda_pkg::*;
import mda_isa_pkg::*;

module mda_decoder #(
    parameter DATA_WIDTH = mda_pkg::DATA_WIDTH,
    parameter ADDR_WIDTH = mda_pkg::REG_ADDR_WIDTH
) (
    // INPUTS:
    input  Instruction  instr,          // input instruction word
    input  logic        suffix_pend,    // if suffix instruction is pending still
    input  RegAddr      suffix_rd,      // suffix rd
    // OUTPUTS:
    // register file
    output RegAddr      rs1_addr,   // register 1 addr (x)
    output RegAddr      rs2_addr,   // register 2 addr (x)
    output RegAddr      rd_addr,    // destinnation reg addr (x)
    output logic        reg_write,  // if register write_back (x)
    // alu
    output AluOp        alu_op,     // ALU operation (x)
    output logic        use_imm,    // use immediate (alu, for rs2 MUXing) (x)
    output logic        fwd_imm,    // forward immediatae directly to ALU result (x)
    output ResSel       res_sel,    // source of EX stage result (NOTE: by default its ALU as ALU allows passthrough/bypass :])
    output ImmSel       imm_sel,    // immediate selection for immedate generator
    // flags
    output logic        f_u_alu,    // update ALU flag
    output logic        illegal,    // illegal instruction
    // branch
    output BrType       br_type,    // branch type
    output logic        br_jof_inv, // jof, branch inversion
    output logic        br_joc_all, // joc, all selection
    // memory
    output MemOp        mem_op,     // none, load, store
    output logic        mem_byte,   // 1 = byte access, 0 = word access
    // suffix
    output logic        lli_first,  // lets the suffix buffer know that another instruction word is coming... suffix
    // future (stage B)
    output logic        sp_valid,   // for spatial, temporal, or event instruction, currently a NOP in stage A
    output SpOp         sp_op       // specific special purpose OP (added in stage B)
);

    OpCode opcode;
    Funct3 funct3;
    Funct2 funct2;
    logic wb;
    logic is_lui;

    assign opcode = instr[2:0];
    assign funct3 = instr[5:3];
    assign funct2 = instr[4:3];

    assign rd_addr = suffix_pend ? suffix_rd : instr[15:13]; // in a suffix slot the word has no register field, so the destination comes from the suffix buffer
    assign is_lui = (opcode == OPC_DIL) && (funct2 == FN_DIL_LUI); // lui keeps the low 24 bits of rd, so it reads rd (instr[15:13]) through port 1 instead of the rs1 field
    assign rs1_addr = is_lui ? instr[15:13] : instr[12:10];
    assign rs2_addr = instr[9:7];

    assign wb = instr[6];   // WB bit is always instr[6]

    always_comb begin
        // defaults:
        alu_op = ALU_ADD;
        reg_write = 1'b0;
        use_imm = 1'b1;
        fwd_imm = 1'b1;
        res_sel = RES_ALU;
        imm_sel = IMM_NONE;
        f_u_alu = 1'b0;
        illegal = 1'b0;
        br_type = BR_NONE;
        br_jof_inv = 1'b0;
        br_joc_all = 1'b0;
        mem_op = MEM_NONE;
        mem_byte = 1'b0;
        lli_first = 1'b0;
        sp_valid = 1'b0;
        sp_op = SP_NONE;
        // decoder logic:
        case (opcode)
            OPC_RR: begin
                reg_write = (wb) ? 1'b1 : 1'b0;
                use_imm = 1'b0;
                fwd_imm = 1'b0;
                f_u_alu = 1'b1;
                case (funct3)
                    FN_RR_ADD:  alu_op = ALU_ADD;
                    FN_RR_XOR:  alu_op = ALU_XOR;
                    FN_RR_AND:  alu_op = ALU_AND;
                    FN_RR_OR:   alu_op = ALU_OR;
                    FN_RR_CMP:  alu_op = ALU_CMP;
                    FN_RR_CMPA: alu_op = ALU_CMPA;
                    FN_RR_SHL:  alu_op = ALU_SHL;
                    FN_RR_SHR:  alu_op = ALU_SHR;
                endcase
            end
            OPC_RIA: begin
                reg_write = (wb) ? 1'b1 : 1'b0;
                fwd_imm = 1'b0;
                f_u_alu = 1'b1;
                case (funct2)
                    FN_RIA_ADDI: begin alu_op = ALU_ADD; imm_sel = IMM_S4; end
                    FN_RIA_XORI: begin alu_op = ALU_XOR; imm_sel = IMM_S4; end
                    FN_RIA_SHLI: begin alu_op = ALU_SHL; imm_sel = IMM_U4; end
                    FN_RIA_SHRI: begin alu_op = ALU_SHR; imm_sel = IMM_U4; end
                endcase
            end
            OPC_RIZ: begin
                // pls note: loads use the ALU as the address adder (alu_op = ADD and use_imm = 1 are the defaults), so fwd_imm stays 0 for them and no flags are updated
                fwd_imm = 1'b0;
                case (funct2)
                    FN_RIZ_LB: begin
                        mem_op = MEM_LOAD;
                        mem_byte = 1'b1;
                        imm_sel = IMM_MEM_B;
                    end
                    FN_RIZ_LW: begin
                        mem_op = MEM_LOAD;
                        mem_byte = 1'b0;
                        imm_sel = IMM_MEM_W;
                    end
                    FN_RIZ_JRG: begin
                        reg_write = 1'b1;
                        res_sel = RES_LINK;
                        fwd_imm = 1'b1;
                        br_type = BR_JRG;
                    end
                    default: illegal = 1'b1;
                endcase
            end
            OPC_DIL: begin
                case (funct2)
                    FN_DIL_LBI: begin
                        reg_write = 1'b1;
                        imm_sel = IMM_LBI;
                    end
                    FN_DIL_LLI: begin
                        lli_first = 1'b1;
                    end
                    FN_DIL_LUI: begin
                        reg_write = 1'b1;
                        imm_sel = IMM_LUI;
                    end
                    default: illegal = 1'b1;
                endcase
            end
            OPC_DIZ: begin
                reg_write = 1'b1;
                case (funct2)
                    FN_DIZ_JMP: begin
                        res_sel = RES_LINK;
                        br_type = BR_JMP;
                    end
                    FN_DIZ_PULL: begin  // Stage B instruction, and its reserved bits must be zero
                        res_sel = RES_SP;
                        sp_valid = 1'b1;
                        sp_op = SP_PULL;
                        if ((instr & RSV_PULL) != 16'h0000) illegal = 1'b1;
                    end
                    FN_DIZ_RPIN: begin  // rpin writes rd with the Stage B result. Modes above RPIN_MODE_MAX_LEGAL are illegal
                        res_sel = RES_SP;
                        sp_valid = 1'b1;
                        sp_op = SP_RPIN;
                        if (instr[7:5] > RPIN_MODE_MAX_LEGAL) illegal = 1'b1;
                    end
                    default: illegal = 1'b1;
                endcase
            end
            OPC_NX: begin
                case (funct3)
                    FN_NX_JNL: begin
                        br_type = BR_JNL;
                    end
                    FN_NX_JOF: begin
                        br_type = BR_JOF;
                    end
                    FN_NX_JOF_INV: begin
                        br_type = BR_JOF;
                        br_jof_inv = 1'b1;
                    end
                    FN_NX_INP: begin
                        sp_valid = 1'b1;
                        sp_op = SP_INP;
                        if ((instr & RSV_INP) != 16'h0000) illegal = 1'b1;
                    end
                    FN_NX_OUTP: begin
                        sp_valid = 1'b1;
                        sp_op = SP_OUTP;
                        if ((instr & RSV_OUTP) != 16'h0000) illegal = 1'b1;
                    end
                    FN_NX_DL: begin
                        sp_valid = 1'b1;
                        sp_op = SP_DL;
                    end
                    FN_NX_FLG: begin
                        sp_valid = 1'b1;
                        sp_op = SP_FLG;
                        if ((instr & RSV_FLG) != 16'h0000) illegal = 1'b1;
                    end
                    default: illegal = 1'b1;
                endcase
            end
            OPC_RX: begin
                case (funct3)
                    FN_RX_JOC_ANY: begin
                        br_type = BR_JOC;
                    end
                    FN_RX_JOC_ALL: begin
                        br_type = BR_JOC;
                        br_joc_all = 1'b1;
                    end
                    FN_RX_PUSH: begin
                        sp_valid = 1'b1;
                        sp_op = SP_PUSH;
                        if ((instr & RSV_PUSH) != 16'h0000) illegal = 1'b1;
                    end
                    FN_RX_WPIN: begin
                        sp_valid = 1'b1;
                        sp_op = SP_WPIN;
                        if ((instr & RSV_WPIN) != 16'h0000) illegal = 1'b1;
                    end
                    FN_RX_DLRG: begin
                        sp_valid = 1'b1;
                        sp_op = SP_DLRG;
                    end
                    FN_RX_WAITEV: begin
                        sp_valid = 1'b1;
                        sp_op = SP_WAITEV;
                        if ((instr & RSV_WAITEV) != 16'h0000) illegal = 1'b1;
                    end
                    FN_RX_CFG: begin
                        sp_valid = 1'b1;
                        sp_op = SP_CFG;
                        if ((instr & RSV_CFG) != 16'h0000) illegal = 1'b1;
                    end
                    default: illegal = 1'b1;
                endcase
            end
            OPC_SX: begin
                // stores use the ALU as the address adder (rs1 + imm), so fwd_imm stays 0 and no flags are updated, w/ rs2 being the store data
                fwd_imm = 1'b0;
                case (funct2)
                    FN_SX_SB: begin
                        mem_op = MEM_STORE;
                        mem_byte = 1'b1;
                        imm_sel = IMM_ST_B;
                    end
                    FN_SX_SW: begin
                        mem_op = MEM_STORE;
                        mem_byte = 1'b0;
                        imm_sel = IMM_ST_W;
                    end
                    default: illegal = 1'b1;
                endcase
            end
            default: illegal = 1'b1;
        endcase

        // illegal functions as a NOP
        if (illegal) begin
            reg_write = 1'b0;
            f_u_alu = 1'b0;
            mem_op = MEM_NONE;
            br_type = BR_NONE;
            lli_first = 1'b0;
            sp_valid = 1'b0;
            sp_op = SP_NONE;
        end

        // SUFFIX SLOT OVERRIDE:
        // The word is data (the lower 16 bits of an lli constant), so it is never illegal and it never decodes as an instruction
        // The immediate generator builds the whole constant, the ALU forwards it and rd (from suffix_rd) is written once
        if (suffix_pend) begin
            alu_op = ALU_ADD;
            reg_write = 1'b1;
            use_imm = 1'b1;
            fwd_imm = 1'b1;
            res_sel = RES_ALU;
            imm_sel = IMM_SUFFIX;
            f_u_alu = 1'b0;
            illegal = 1'b0;
            br_type = BR_NONE;
            br_jof_inv = 1'b0;
            br_joc_all = 1'b0;
            mem_op = MEM_NONE;
            mem_byte = 1'b0;
            lli_first = 1'b0;
            sp_valid = 1'b0;
            sp_op = SP_NONE;
        end

    end

endmodule
