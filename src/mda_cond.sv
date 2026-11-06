import mda_pkg::*;

// flag-mask condition, shared by jof, joc and (Stage B) waitev
module mda_cond (
    // INPUTS:
    input  Flags    flags,      // flags of the thread in EX
    input  Flags    mask,       // flag select (one-hot for jof, rs1[15:0] for joc)
    input  logic    all_mode,   // 1: all flags in the mask must be set, 0: any
    input  logic    inv,        // invert the result
    // OUTPUTS:
    output logic    hit         // conditiion (i.e. branch) valid
);

    Flags selected_flags;
    logic flg_red;
    assign selected_flags = flags & mask;
    assign flg_red = (all_mode) ? (selected_flags == mask) : |selected_flags;
    assign hit = (inv) ? ~flg_red : flg_red;

endmodule