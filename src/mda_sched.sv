import mda_pkg::*;

// thread scheduler: one-hot ring (threads in IF, ID and EX) and the ID-stage valid bit
module mda_sched (
    // clock and reset
    input  logic     clk,
    input  logic     rst_n,
    // INPUTS:
    input  logic     run,       // threads released (the ring holds at reset while low)
    // OUTPUTS:
    output ThreadSel if_t,      // one-hot, thread in IF
    output ThreadSel id_t,      // one-hot, thread in ID
    output ThreadSel ex_t,      // one-hot, thread in EX
    output logic     id_v       // the ID stage holds a real instruction
);

    logic [2:0] ring;

    always_ff @(posedge clk or negedge rst_n) begin
        // TBA
    end

endmodule