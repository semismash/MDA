import mda_pkg::*;

// Jump control: the taken decision, the PC adder controls (mda_pc), the PC offset and the link value. Ports only.
module mda_branch_unit (
    // INPUTS:
    input  logic        ex_v,           // the EX stage holds a real instruction
    input  BrType       br_type,        // jump kind
    input  logic        br_jof_inv,     // jof, branch inversion
    input  logic        br_joc_all,     // joc, all selection
    input  Instruction  instr,          // raw EX word (jof flag number, joc invert bit, and the offset fields)
    input  Flags        flags,          // flags of the thread in EX
    input  Word         rs1_data,       // joc flag mask in the low 16 bits
    input  PcAddr       ex_pc,          // PC of the thread in EX (selected by the wrapper)
    // OUTPUTS:
    output logic        taken,          // the jump is taken (used by trace)
    output logic        pc_in1,         // to mda_pc: 1 = rs1 as the base, 0 = PC
    output logic        pc_in2,         // to mda_pc: 1 = pc_offset, 0 = +1
    output logic        pc_cin,         // to mda_pc: carry-in, high for taken PC-relative jumps
    output PcAddr       pc_offset,      // to mda_pc imm_in: sign-extended offset sliced from instr
    output PcAddr       link            // ex_pc + 1, to mda_wb (the link value of jmp and jrg)
);

    always_comb begin
        taken = 1'b0;
        pc_in1 = 1'b0;
        pc_in2 = 1'b0;
        pc_cin = 1'b0;
        if (ex_v) begin
            case (br_type)
                BR_JMP: begin
                    
                end
            endcase
        end
    end

endmodule