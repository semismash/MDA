import mda_pkg::*;

// thread scheduler: a slot counter (the thread in IF), the thread in ID, and the ID-stage valid bit, one instance for the whole core
module mda_sched (
    // clock and reset
    input  logic  clk,
    input  logic  rst_n,
    // INPUTS:
    input  logic  run,          // threads released (the counter is held at thread 0 while low)
    // OUTPUTS:
    output Thread if_thread,    // thread in IF
    output Thread id_thread,    // thread in ID (the thread that was in IF last cycle)
    output logic  id_v          // the ID stage holds a real instruction
);

    Thread slot;
    assign if_thread = slot;

    // control state, reset
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            slot <= THREAD_0;
            id_v <= 1'b0;
        end else begin
            id_v <= run;
            // thread 0 is in IF in the first cycle with run high, and any pause realigns the schedule to thread 0
            if (run) slot <= (slot == THREAD_2) ? THREAD_0 : slot + 2'd1;
            else     slot <= THREAD_0;
        end
    end

    // payload, not reset (qualified by id_v)
    always_ff @(posedge clk) begin
        if (run) id_thread <= slot;
    end

endmodule
