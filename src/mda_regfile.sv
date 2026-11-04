import mda_pkg::*;

// synchronous writes, asynchronous reads
module reg_file #(
    parameter DATA_WIDTH = mda_pkg::DATA_WIDTH,
    parameter ADDR_WIDTH = mda_pkg::REG_ADDR_WIDTH
) (
    // clk and reset
    input  logic    clk,
    input  logic    rst_n,
    // INPUTS:
    // read logic
    input  RegAddr  r_addr1,    // rs1 read address
    input  RegAddr  r_addr2,    // rs2 read address
    // write logic
    input  RegAddr  w_addr,     // write-back address
    input  Word     w_data,     // write-back data
    input  logic    w_enable,   // write_enable
    // OUTPUTS:
    output Word     r_data1,    // fetched read data rs1
    output Word     r_data2     // fetched read data rs2
);

    Word register_file [2**ADDR_WIDTH - 1:0];

    // read logic
    assign r_data1 = register_file[r_addr1]; // no RAW forwarding required, RAW hazards are eliminated as one thread writes every 3 cycles
    assign r_data2 = register_file[r_addr2];

    // write logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i = 0 ; i < 2**ADDR_WIDTH ; i = i+1) begin
                register_file[i] <= '0;
            end
        end else begin
            if (w_enable) register_file[w_addr] <= w_data;
        end
    end

endmodule