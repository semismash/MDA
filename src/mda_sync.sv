// Tto-flop synchronizer for async inputs (pins, reset), q follows d after two clock edges
module mda_sync #(
    parameter WIDTH = 1
) (
    input  logic clk,               // clock
    input  logic [WIDTH-1:0] d,     // asynchronous input
    output logic [WIDTH-1:0] q      // input synchronized to clk
);

    (* ASYNC_REG = "TRUE" *) logic [WIDTH-1:0] meta;   // first stage, may go metastable

    always_ff @(posedge clk) begin
        meta <= d;      // stage 1
        q    <= meta;   // stage 2
    end

endmodule
