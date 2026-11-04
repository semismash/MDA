import mda_pkg::*;

module alu #(
    parameter DATA_WIDTH = mda_pkg::DATA_WIDTH,
    parameter ADDR_WIDTH = mda_pkg::REG_ADDR_WIDTH
) (
    // INPUTS:
    input  AluOp alu_op,        // ALU operation
    // register data
    input  Word  rs1_data,      // rs1 data from file
    input  Word  rs2_data,      // rs2 data from file
    // alu in2 field
    input  logic use_imm,       // use imm instead of rs2
    input  Word  imm,           // immediate from decoder (imm gen)
    // other
    input  logic alu_bypass,    // bypass ALU, directly output 0 as result
    input  logic fwd_imm,       // forward result to imm directly
    // OUTPUTS:
    output Word  result,        // ALU result
    output logic alu_zero,      // goes to zero flag (if ALU result is zero)
    output logic alu_neg,       // goes to negative flag (if ALU result is negative)
    output logic alu_carry,     // goes to carry flag (if ALU result has carry)
    output logic alu_carry_upd  // update enable for the carry flag; low for a shift by 0, high otherwise. ANDed with alu_carry updation to make sure ALU carry remains not updated during shift w/ 0
);

    localparam SHAMT_WIDTH = $clog2(DATA_WIDTH);
    logic [SHAMT_WIDTH-1:0] shamt;

    Word data_1, data_2;
    assign data_1 = rs1_data;   // always rs1 data, unlike rs2 which can be either imm or reg data
    assign data_2 = use_imm ? imm : rs2_data;   // data_2 chooses between imm and rs2_data
    assign shamt  = data_2[SHAMT_WIDTH-1:0];

    Word one;   // 0x00000001
    assign one = {{(DATA_WIDTH-1){1'b0}}, 1'b1};

    // use 33-bit shifts to give the shift carry without indexing; shl_ext[DATA_WIDTH] is rs1[32-n]
    // the last bit shifted out through the MSB; shr_ext[0] is rs1[n-1], the last bit shifted out through the LSB
    logic [DATA_WIDTH:0] shl_ext, shr_ext;
    assign shl_ext = {1'b0, data_1} << shamt;
    assign shr_ext = {data_1, 1'b0} >> shamt;

    always_comb begin
        result = '0;
        alu_carry = 1'b0;
        alu_carry_upd = 1'b1;
        if (alu_bypass) begin
            result = '0;
        end else if (fwd_imm) begin
            result = imm;
        end else begin
            case (alu_op)
                ALU_ADD:  {alu_carry, result} = data_1 + data_2;
                ALU_XOR:  result = data_1 ^ data_2;
                ALU_AND:  result = data_1 & data_2;
                ALU_OR:   result = data_1 | data_2;
                ALU_CMP:  result = (data_1 == data_2) ? '0 : ((data_1 > data_2) ? one : '1);
                ALU_CMPA: result = (data_1 == data_2) ? '0 : (($signed(data_1) > $signed(data_2)) ? one : '1);
                ALU_SHL: begin
                    {alu_carry, result} = shl_ext;
                    alu_carry_upd = (shamt != '0);  // shift by 0 leaves the bit unchanged, alu_carry_upd
                end
                ALU_SHR: begin  
                    {result, alu_carry} = shr_ext;
                    alu_carry_upd = (shamt != '0);
                end
                default:  result = '0;
            endcase
        end
    end

    assign alu_zero = ~(|result);
    assign alu_neg  = result[DATA_WIDTH - 1];

endmodule