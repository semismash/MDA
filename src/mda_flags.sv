import mda_pkg::*;
import mda_isa_pkg::*;

module mda_flags (
    // clk and reset
    input  logic clk,
    input  logic rst_n,
    // INPUTS:
    // 1) ALU
    input  logic u_alu,
    input  logic f_alu_zero,
    input  logic f_alu_neg,
    input  logic f_alu_carry,
    input  logic u_alu_carry,
    // 2) ERROR
    input  logic u_err,
    input  logic f_err,
    input  logic [2:0] f_errc,
    // 3) SHIFT ENGINES
    input  logic f_isr_rdy,
    input  logic f_osr_empty,
    // 4) IPC DOORBELLS
    input  logic u_msg_n,
    input  logic f_msg_n,
    input  logic u_msg_p,
    input  logic f_msg_p,
    // 5) PE, OVR, TMR
    input  logic f_pe,  // pin event (LIVE)
    input  logic u_ovr, // overrun for event or data
    input  logic f_ovr,
    input  logic u_tmr, // timer complete
    input  logic f_tmr,
    // OUTPUTS:
    output Flags flags_out
);

    Flags flag_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            flag_reg <= '0;
            flag_reg[FLAG_OSR_EMPTY] <= 1'b1;
        end else begin
            // 1) ALU
            if (u_alu) begin
                flag_reg[FLAG_Z] <= f_alu_zero;
                flag_reg[FLAG_N] <= f_alu_neg;
                if (u_alu_carry) flag_reg[FLAG_C] <= f_alu_carry;
            end
            // 2) ERROR
            if (u_err) begin
                flag_reg[FLAG_ERR] <= f_err;
                if (f_err) begin
                    flag_reg[FLAG_ERRC0] <= f_errc[0];
                    flag_reg[FLAG_ERRC1] <= f_errc[1];
                    flag_reg[FLAG_ERRC2] <= f_errc[2];
                end else begin
                    flag_reg[FLAG_ERRC0] <= 1'b0;
                    flag_reg[FLAG_ERRC1] <= 1'b0;
                    flag_reg[FLAG_ERRC2] <= 1'b0;
                end
            end
            // 3) SHIFT ENGINES
            flag_reg[FLAG_ISR_RDY] <= f_isr_rdy;
            flag_reg[FLAG_OSR_EMPTY] <= f_osr_empty;
            // 4) IPC DOORBELLS
            if (u_msg_n) flag_reg[FLAG_MSG_N] <= f_msg_n;
            if (u_msg_p) flag_reg[FLAG_MSG_P] <= f_msg_p;
            // 5) PE, OVER, TMR
            flag_reg[FLAG_PE] <= f_pe;
            if (u_ovr) flag_reg[FLAG_OVR] <= f_ovr;
            if (u_tmr) flag_reg[FLAG_TMR] <= f_tmr;
            // 6) SPARE
            flag_reg[FLAG_SPARE_0] <= 1'b0; // hold down to zero for spare flags, as they are unused
            flag_reg[FLAG_SPARE_1] <= 1'b0;
        end
    end
    
    assign flags_out = flag_reg;

endmodule
