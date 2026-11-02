/*
 * MDA SRAM dry run
 * Exercises one IHP 1024x16 single-port SRAM macro through the Tiny Tapeout flow.
 * After reset it writes 16 words, overwrites their low bytes using the bit mask,
 * reads them back, and reports pass/fail on the output pins.
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_mda_sram_dryrun (
    input  wire [7:0] ui_in,    // Dedicated inputs (unused)
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path (unused)
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  assign uio_out = 8'b0;
  assign uio_oe  = 8'b0;

  // rst_n comes from the board, so its release is synchronized to clk
  reg [1:0] rst_pipe;
  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) rst_pipe <= 2'b00;
    else        rst_pipe <= {rst_pipe[0], 1'b1};
  end
  wire rst_sync_n = rst_pipe[1];

  localparam [2:0] S_WR_FULL  = 3'd0;  // write 16 full words
  localparam [2:0] S_WR_LOW   = 3'd1;  // overwrite the low byte of the same 16 words (mask 0x00FF)
  localparam [2:0] S_RD_ISSUE = 3'd2;  // issue a read
  localparam [2:0] S_RD_CAP   = 3'd3;  // read data is valid in this cycle, compare it
  localparam [2:0] S_DONE     = 3'd4;

  reg [2:0] state;
  reg [3:0] idx;
  reg       fail;
  reg [3:0] dout_q;

  wire wr_full = (state == S_WR_FULL);
  wire wr_low  = (state == S_WR_LOW);
  wire rd_iss  = (state == S_RD_ISSUE);
  wire rd_cap  = (state == S_RD_CAP);
  wire done    = (state == S_DONE);

  // macro controls come straight from flops, they are sampled at the next clock edge
  wire        mem_we   = wr_full | wr_low;
  wire        mem_re   = rd_iss;
  wire        mem_en   = mem_we | mem_re;
  wire [9:0]  mem_addr = {6'b0, idx};
  wire [15:0] mem_din  = wr_full ? {idx, 4'hA, ~idx, 4'h5} : {8'hEE, 4'h3, idx};
  wire [15:0] mem_bm   = wr_full ? 16'hFFFF : 16'h00FF;  // 1 = this bit is written
  wire [15:0] mem_dout;

  // after both writes: high byte from the first write, low byte from the masked write
  wire [15:0] expected = {idx, 4'hA, 4'h3, idx};

  always @(posedge clk) begin
    if (!rst_sync_n) begin
      state  <= S_WR_FULL;
      idx    <= 4'd0;
      fail   <= 1'b0;
      dout_q <= 4'd0;
    end else begin
      case (state)
        S_WR_FULL: begin
          idx <= idx + 4'd1;
          if (idx == 4'd15) state <= S_WR_LOW;
        end
        S_WR_LOW: begin
          idx <= idx + 4'd1;
          if (idx == 4'd15) state <= S_RD_ISSUE;
        end
        S_RD_ISSUE: begin
          state <= S_RD_CAP;
        end
        S_RD_CAP: begin
          // an X on the read data makes fail an X in simulation, which is visible
          fail   <= fail | (|(mem_dout ^ expected));
          dout_q <= mem_dout[3:0];
          idx    <= idx + 4'd1;
          state  <= (idx == 4'd15) ? S_DONE : S_RD_ISSUE;
        end
        default: begin
          state <= S_DONE;
        end
      endcase
    end
  end

  wire pass = done & ~fail;

  // uo[0] done, uo[1] pass, uo[2] fail, uo[3] unused, uo[7:4] low nibble of the last read
  assign uo_out = {dout_q, 1'b0, fail, pass, done};

  RM_IHPSG13_1P_1024x16_c2_bm_bist sram (
      .A_CLK(clk),
      .A_MEN(mem_en),
      .A_WEN(mem_we),
      .A_REN(mem_re),
      .A_ADDR(mem_addr),
      .A_DIN(mem_din),
      .A_DLY(1'b1),
      .A_DOUT(mem_dout),
      .A_BM(mem_bm),
      .A_BIST_CLK(1'b0),
      .A_BIST_EN(1'b0),
      .A_BIST_MEN(1'b0),
      .A_BIST_WEN(1'b0),
      .A_BIST_REN(1'b0),
      .A_BIST_ADDR(10'b0),
      .A_BIST_DIN(16'b0),
      .A_BIST_BM(16'b0)
  );

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, ui_in, uio_in, rd_cap, 1'b0};

endmodule