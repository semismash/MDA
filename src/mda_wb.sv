import mda_pkg::*;

// Write-back: selects the EX result (ALU, link or Stage B) and forms the two register write requests (EX result and load return).
// With HAS_STAGE_B = 0 the Stage B instructions execute as no-ops, so their register write is masked.
module mda_wb #(
    parameter HAS_STAGE_B = 0
) (
    // INPUTS:
    // EX stage
    input  logic    ex_v,           // the EX stage holds a real instruction
    input  Thread   ex_thread,
    input  logic    reg_write,      // decoder write enable
    input  logic    sp_valid,       // decoder: Stage B instruction
    input  RegAddr  rd_addr,        // destination register
    input  ResSel   res_sel,        // result source
    input  Word     alu_result,     // ALU result, or the forwarded immediate
    input  PcAddr   link,           // link value (PC + 1 of the thread in EX)
    input  Word     sp_result,      // Stage B result (tie to 0 in Stage A)
    // load return (from the LSU)
    input  logic    ld_valid,       // a load result is available
    input  RegAddr  ld_rd,          // load destination register
    input  Thread   ld_thread,
    input  Word     ld_data,        // aligned load data (0 on a faulting load)
    // OUTPUTS:
    // EX write request (to the bank of the thread in EX)
    output logic    w_ex_we,
    output RegAddr  w_ex_addr,
    output Thread   w_ex_thread,
    output Word     w_ex_data,
    // load-return write request (to the bank of the thread in IF)
    output logic    w_ld_we,
    output RegAddr  w_ld_addr,
    output Thread   w_ld_thread,
    output Word     w_ld_data
);

    Word link_value;
    assign link_value = {{(DATA_WIDTH-IMEM_ADDR_WIDTH){1'b0}}, link};

    // EX result select
    always_comb begin
        case (res_sel)
            RES_LINK: w_ex_data = link_value;
            RES_SP:   w_ex_data = sp_result;
            default:  w_ex_data = alu_result;   // RES_ALU
        endcase
    end

    assign w_ex_we   = ex_v & reg_write & ((HAS_STAGE_B != 0) | ~sp_valid);
    assign w_ex_addr = rd_addr;
    assign w_ex_thread = ex_thread;

    // the load return passes through unchanged
    assign w_ld_we   = ld_valid;
    assign w_ld_addr = ld_rd;
    assign w_ld_thread = ld_thread;
    assign w_ld_data = ld_data;

endmodule
