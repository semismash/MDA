import mda_pkg::*;
import mda_isa_pkg::*;

// Suffix buffer for the two-word lli instruction.
//   Word A (the lli) carries rd and imm8, which is bits [23:16] of the constant. Word B (the suffix) carries bits [15:0].
//   When the decoder sees word A it raises lli_first. This buffer then remembers rd and imm8 for the thread in ID and marks
//   a suffix as pending. Word A executes as a no-operation. When word B reaches ID, suffix_pend tells the decoder to treat
//   the word as data, and suffix_rd and suffix_imm8 supply the destination register and the upper byte. The immediate
//   generator builds the whole 24-bit constant, which is forwarded through the ALU and written once, in the suffix slot.
//   One entry per thread. The thread in ID is selected by the one-hot id_t.
// Reset: only the pending bits are reset. The captured rd and imm8 are payload, qualified by suffix_pend (D10).
// A jump that lands directly on a suffix word finds suffix_pend low, so the word decodes as an ordinary instruction.
module mda_suffix (
    // clock and reset
    input  logic        clk,
    input  logic        rst_n,
    // INPUTS:
    input  ThreadSel    id_t,           // one-hot, thread whose instruction is in ID
    input  logic        id_v,           // the ID stage holds a real instruction
    input  logic        lli_first,      // from the decoder, this word is the first half of lli
    input  Instruction  instr,          // word in ID, rd and imm8 are captured from it
    // OUTPUTS (for the thread in ID):
    output logic        suffix_pend,    // this word is the suffix of a pending lli
    output RegAddr      suffix_rd,      // destination register of the pending lli
    output logic [7:0]  suffix_imm8     // bits [23:16] of the constant, captured from word A
);

    logic [NUM_THREADS-1:0] pend;
    RegAddr                 rd_q   [0:NUM_THREADS-1];
    logic [7:0]             imm8_q [0:NUM_THREADS-1];

    // select the entry of the thread in ID (id_t is one-hot, so this is an AND-OR)
    always_comb begin
        suffix_pend = 1'b0;
        suffix_rd   = '0;
        suffix_imm8 = '0;
        for (int t = 0; t < NUM_THREADS; t = t + 1) begin
            suffix_pend = suffix_pend | (id_t[t] & pend[t]);
            suffix_rd   = suffix_rd   | ({REG_ADDR_WIDTH{id_t[t]}} & rd_q[t]);
            suffix_imm8 = suffix_imm8 | ({8{id_t[t]}}              & imm8_q[t]);
        end
    end

    // control state, reset
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pend <= '0;
        end else begin
            for (int t = 0; t < NUM_THREADS; t = t + 1) begin
                if (id_t[t] && id_v) begin
                    if (pend[t])             pend[t] <= 1'b0;    // suffix consumed
                    else if (lli_first)      pend[t] <= 1'b1;    // first half of lli seen
                end
            end
        end
    end

    // payload, not reset, captured with word A
    always_ff @(posedge clk) begin
        for (int t = 0; t < NUM_THREADS; t = t + 1) begin
            if (id_t[t] && id_v && !pend[t] && lli_first) begin
                rd_q[t]   <= instr[RD_HI:RD_LO];
                imm8_q[t] <= instr[12:5];
            end
        end
    end

endmodule