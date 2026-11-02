`timescale 1ns/1ps
// Run from the repository root (needs Icarus Verilog):
//   iverilog -g2005 -o sim test/tb.v test/RM_IHPSG13_1P_1024x16_c2_bm_bist_model.v src/project.v
//   vvp sim
module tb;
  reg        clk = 1'b0;
  reg        rst_n;
  reg  [7:0] ui_in  = 8'b0;
  reg  [7:0] uio_in = 8'b0;
  wire [7:0] uo_out, uio_out, uio_oe;
  integer    cycles;

  tt_um_mda_sram_dryrun dut (
      .ui_in(ui_in), .uo_out(uo_out),
      .uio_in(uio_in), .uio_out(uio_out), .uio_oe(uio_oe),
      .ena(1'b1), .clk(clk), .rst_n(rst_n)
  );

  always #10 clk = ~clk;  // 50 MHz

  initial begin
    $dumpfile("tb.vcd");
    $dumpvars(0, tb);
    rst_n = 1'b1;
    #5 rst_n = 1'b0;
    repeat (5) @(posedge clk);
    rst_n = 1'b1;
    cycles = 0;
    while (uo_out[0] !== 1'b1 && cycles < 1000) begin
      @(posedge clk);
      cycles = cycles + 1;
    end
    if (uo_out[0] !== 1'b1)
      $display("FAIL: timeout, done was never set");
    else if (uo_out[1] === 1'b1 && uo_out[2] === 1'b0)
      $display("PASS: finished after %0d cycles", cycles);
    else
      $display("FAIL: done, but pass=%b fail=%b", uo_out[1], uo_out[2]);
    $finish;
  end
endmodule
