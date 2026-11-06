import mda_pkg::*;

// Register bank: one register file per thread. Reads select the bank of the ID thread, writes are routed by the thread tags.
module mda_regbank (
    // clock
    input  logic    clk,
    // INPUTS:
    // read (ID stage)
    input  Thread   rd_thread,      // thread in ID
    input  RegAddr  r_addr1,        // rs1 read address
    input  RegAddr  r_addr2,        // rs2 read address
    // EX write
    input  logic    w_ex_we,
    input  Thread   w_ex_thread,
    input  RegAddr  w_ex_addr,
    input  Word     w_ex_data,
    // load-return write
    input  logic    w_ld_we,
    input  Thread   w_ld_thread,
    input  RegAddr  w_ld_addr,
    input  Word     w_ld_data,
    // OUTPUTS:
    output Word     r_data1,        // rs1 data
    output Word     r_data2         // rs2 data
);

    // Each bank has one write port. The EX write and the load-return write never hit the same bank in one cycle
    // (a load returns while its thread is in IF, not in EX), so the EX write is simply given priority.
    logic   ex_hit0, ex_hit1, ex_hit2;
    logic   ld_hit0, ld_hit1, ld_hit2;
    logic   we0, we1, we2;
    RegAddr wa0, wa1, wa2;
    Word    wd0, wd1, wd2;
    Word    b0_r1, b0_r2, b1_r1, b1_r2, b2_r1, b2_r2;

    assign ex_hit0 = w_ex_we & (w_ex_thread == THREAD_0);
    assign ex_hit1 = w_ex_we & (w_ex_thread == THREAD_1);
    assign ex_hit2 = w_ex_we & (w_ex_thread == THREAD_2);
    assign ld_hit0 = w_ld_we & (w_ld_thread == THREAD_0);
    assign ld_hit1 = w_ld_we & (w_ld_thread == THREAD_1);
    assign ld_hit2 = w_ld_we & (w_ld_thread == THREAD_2);

    assign we0 = ex_hit0 | ld_hit0;
    assign we1 = ex_hit1 | ld_hit1;
    assign we2 = ex_hit2 | ld_hit2;
    assign wa0 = ex_hit0 ? w_ex_addr : w_ld_addr;
    assign wa1 = ex_hit1 ? w_ex_addr : w_ld_addr;
    assign wa2 = ex_hit2 ? w_ex_addr : w_ld_addr;
    assign wd0 = ex_hit0 ? w_ex_data : w_ld_data;
    assign wd1 = ex_hit1 ? w_ex_data : w_ld_data;
    assign wd2 = ex_hit2 ? w_ex_data : w_ld_data;

    mda_regfile u_bank0 (
        .clk      (clk),
        .r_addr1  (r_addr1),
        .r_addr2  (r_addr2),
        .w_addr   (wa0),
        .w_data   (wd0),
        .w_enable (we0),
        .r_data1  (b0_r1),
        .r_data2  (b0_r2)
    );

    mda_regfile u_bank1 (
        .clk      (clk),
        .r_addr1  (r_addr1),
        .r_addr2  (r_addr2),
        .w_addr   (wa1),
        .w_data   (wd1),
        .w_enable (we1),
        .r_data1  (b1_r1),
        .r_data2  (b1_r2)
    );

    mda_regfile u_bank2 (
        .clk      (clk),
        .r_addr1  (r_addr1),
        .r_addr2  (r_addr2),
        .w_addr   (wa2),
        .w_data   (wd2),
        .w_enable (we2),
        .r_data1  (b2_r1),
        .r_data2  (b2_r2)
    );

    // read mux by the thread in ID (thread 3 is unused and reads bank 0)
    always_comb begin
        case (rd_thread)
            THREAD_1: begin
                r_data1 = b1_r1;
                r_data2 = b1_r2;
            end
            THREAD_2: begin
                r_data1 = b2_r1;
                r_data2 = b2_r2;
            end
            default: begin
                r_data1 = b0_r1;
                r_data2 = b0_r2;
            end
        endcase
    end

endmodule
