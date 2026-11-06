import mda_pkg::*;

module mda_imm_gen #(
    parameter DATA_WIDTH = mda_pkg::DATA_WIDTH
) (
    input  Instruction  instr,
    input  ImmSel       imm_sel,
    input  Word         rs1_data,
    input  logic [7:0]  suffix_imm8,
    output Word         imm_out
);

    always_comb begin
        imm_out = '0;
        case (imm_sel)
            IMM_NONE:   imm_out = '0;
            IMM_S4:     imm_out = {{(DATA_WIDTH-4){instr[9]}}, instr[9:7], instr[5]};                    // addi, xori: signed 4 bits
            IMM_U4:     imm_out = {{(DATA_WIDTH-4){1'b0}}, instr[9:7], instr[5]};                        // shli, shri: unsigned 4 bits
            IMM_MEM_B:  imm_out = {{(DATA_WIDTH-5){1'b0}}, instr[9:5]};                                  // lb: byte offset
            IMM_MEM_W:  imm_out = {{(DATA_WIDTH-7){1'b0}}, instr[9:5], 2'b00};                           // lw: word offset times 4
            IMM_ST_B:   imm_out = {{(DATA_WIDTH-5){1'b0}}, instr[15:13], instr[6:5]};                    // sb: byte offset
            IMM_ST_W:   imm_out = {{(DATA_WIDTH-7){1'b0}}, instr[15:13], instr[6:5], 2'b00};             // sw: word offset times 4
            IMM_LBI:    imm_out = {{(DATA_WIDTH-8){1'b0}}, instr[12:5]};                                 // lbi: unsigned 8 bits
            IMM_LUI:    imm_out = {instr[12:5], rs1_data[23:0]};                                         // lui: new top byte, old low 24 bits of rd
            IMM_SUFFIX: imm_out = {{(DATA_WIDTH-24){1'b0}}, suffix_imm8, instr};                         // lli suffix slot: 24-bit constant
            default:    imm_out = '0;
        endcase
    end

endmodule