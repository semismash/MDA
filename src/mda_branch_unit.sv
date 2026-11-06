import mda_pkg::*;

// Jump control: the taken decision, the PC adder controls (mda_pc), the PC offset and the link value
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

    localparam JOF_MASK_START_BIT   = 15;
    localparam JOF_MASK_END_BIT     = 12;
    localparam JOC_INV_BIT          = 15;
    localparam JMP_OFFSET_START_BIT     = 12;
    localparam JMP_OFFSET_END_BIT       = 5;
    localparam JNL_OFFSET_START_BIT     = 15;
    localparam JNL_OFFSET_END_BIT       = 6;
    localparam JOF_OFFSET_START_BIT     = 11;
    localparam JOF_OFFSET_END_BIT       = 6;
    localparam JOC_OFFSET_HI_START_BIT  = 14;   // joc keeps its offset in two ranges: the upper bits...
    localparam JOC_OFFSET_HI_END_BIT    = 13;
    localparam JOC_OFFSET_LO_START_BIT  = 9;    // ...and the lower bits
    localparam JOC_OFFSET_LO_END_BIT    = 6;
    localparam JRG_OFFSET_START_BIT     = 9;
    localparam JRG_OFFSET_END_BIT       = 5;

    localparam JMP_OFFSET_WIDTH = JMP_OFFSET_START_BIT - JMP_OFFSET_END_BIT + 1;    // 8
    localparam JOF_OFFSET_WIDTH = JOF_OFFSET_START_BIT - JOF_OFFSET_END_BIT + 1;    // 6
    localparam JOC_OFFSET_WIDTH = (JOC_OFFSET_HI_START_BIT - JOC_OFFSET_HI_END_BIT + 1) + (JOC_OFFSET_LO_START_BIT - JOC_OFFSET_LO_END_BIT + 1);    // 6
    localparam JRG_OFFSET_WIDTH = JRG_OFFSET_START_BIT - JRG_OFFSET_END_BIT + 1;    // 5

    logic  is_jrg;
    Flags  cond_mask;
    logic  cond_all;
    logic  cond_inv;
    logic  hit;

    assign is_jrg = (br_type == BR_JRG); // if the branch is jrg

    // drives mda_cond, see below this block, masks from 15:12 for condition mask (4 bits, 16 flags)
    // jof looks at one flag (the flag number is instr[15:12]), joc looks at the flags selected by rs1[15:0]
    always_comb begin
        cond_mask = '0;
        cond_all  = 1'b0;
        cond_inv  = 1'b0;
        case (br_type)
            BR_JOF: begin
                cond_mask = 16'h0001 << instr[JOF_MASK_START_BIT:JOF_MASK_END_BIT];
                cond_all  = 1'b0;
                cond_inv  = br_jof_inv;
            end
            BR_JOC: begin
                cond_mask = rs1_data[15:0];
                cond_all  = br_joc_all;
                cond_inv  = instr[JOC_INV_BIT];
            end
            default: begin
            end
        endcase
    end

    // the flag-mask condition, shared with waitev later
    mda_cond u_cond (
        .flags    (flags),
        .mask     (cond_mask),
        .all_mode (cond_all),
        .inv      (cond_inv),
        .hit      (hit)
    );

    always_comb begin
        taken = 1'b0;
        if (ex_v) begin
            case (br_type)
                BR_JMP: begin
                    taken = 1'b1;
                end
                BR_JNL: begin
                    taken = 1'b1;
                end
                BR_JRG: begin
                    taken = 1'b1;
                end
                BR_JOF: begin
                    taken = hit;
                end
                BR_JOC: begin
                    taken = hit;
                end
                default: begin
                    taken = 1'b0;
                end
            endcase
        end
    end

    assign pc_in1 = ex_v & is_jrg;
    assign pc_in2 = taken;
    assign pc_cin = taken & ~is_jrg;

    always_comb begin
        case (br_type)
            BR_JMP:  pc_offset = {{(IMEM_ADDR_WIDTH-JMP_OFFSET_WIDTH){instr[JMP_OFFSET_START_BIT]}}, instr[JMP_OFFSET_START_BIT:JMP_OFFSET_END_BIT]};                                                              // 8 bits
            BR_JNL:  pc_offset = instr[JNL_OFFSET_START_BIT:JNL_OFFSET_END_BIT];                                                                                                                                  // 10 bits, the whole PC width
            BR_JOF:  pc_offset = {{(IMEM_ADDR_WIDTH-JOF_OFFSET_WIDTH){instr[JOF_OFFSET_START_BIT]}}, instr[JOF_OFFSET_START_BIT:JOF_OFFSET_END_BIT]};                                                              // 6 bits
            BR_JOC:  pc_offset = {{(IMEM_ADDR_WIDTH-JOC_OFFSET_WIDTH){instr[JOC_OFFSET_HI_START_BIT]}}, instr[JOC_OFFSET_HI_START_BIT:JOC_OFFSET_HI_END_BIT], instr[JOC_OFFSET_LO_START_BIT:JOC_OFFSET_LO_END_BIT]};   // 6 bits from two ranges
            BR_JRG:  pc_offset = {{(IMEM_ADDR_WIDTH-JRG_OFFSET_WIDTH){instr[JRG_OFFSET_START_BIT]}}, instr[JRG_OFFSET_START_BIT:JRG_OFFSET_END_BIT]};                                                              // 5 bits
            default: pc_offset = '0;
        endcase
    end

    // the link value is the address of the next instruction
    assign link = ex_pc + 1'b1;

endmodule
