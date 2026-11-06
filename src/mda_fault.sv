import mda_pkg::*;
import mda_isa_pkg::*;

// fault collector: turns the fault sources of the EX instruction into the ERR and OVR updates of its thread's flags
// please note: Stage B fault sources will be joined here later
module mda_fault (
    // INPUTS:
    input  logic    ex_v,               // the EX stage holds a real instruction
    input  logic    illegal,            // illegal instruction (from the decoder, via mda_id_ex)
    input  logic    lsu_fault,          // load/store fault (from the LSU)
    input  logic    lsu_fault_type,     // low = misaligned, high = out of bounds
    input  logic    err_now,            // the ERR flag of the thread in EX
    // OUTPUTS: (to the flags of the thread in EX, which the wrapper selects)
    output logic    u_err,              // set ERR and latch the cause (first fault only)
    output logic    f_err,
    output Cause    f_errc,             // fault cause
    output logic    u_ovr,              // set OVR (a second fault while ERR is already set)
    output logic    f_ovr
);

    logic any_fault;
    Cause cause;

    // a decoded-illegal instruction is a no-op, so it never reaches the LSU with an access: the two sources cannot fire together
    always_comb begin
        any_fault = 1'b0;
        cause     = CAUSE_ILLEGAL;
        if (ex_v) begin
            if (lsu_fault) begin
                any_fault = 1'b1;
                cause     = lsu_fault_type ? CAUSE_OUT_OF_BOUNDS : CAUSE_MISALIGNED;
            end else if (illegal) begin
                any_fault = 1'b1;
                cause     = CAUSE_ILLEGAL;
            end
        end
    end

    assign u_err  = any_fault & ~err_now;   // the cause of the first fault is the one that stays
    assign f_err  = 1'b1;
    assign f_errc = cause;
    assign u_ovr  = any_fault & err_now;    // a second fault while ERR is set overruns
    assign f_ovr  = 1'b1;

endmodule
