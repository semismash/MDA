There are 9 types of instructions in the MDA ISA. They are `R`, `RI`, `I`, `LI`, `D`, `J`, `N`, `P`, and `S`. Out of them, they are encoded in a variety of 8 different formats. The following types of fields include -
- `OPCODE` - Opcode determining the type of instruction and its encoding. Always at `[2:0]`
- `FUNCT` - Sub-field of opcode giving more information about the instruction type, operation, and details about it's encoding. Can be either 2 or 3 bits.
- `RD` - Destination Register where the executed information is to be stored.
- `RS1` - Source Register 1, the first register which is used for an operation.
- `RS2` - Source Register 2, the second register which may be used for an operation.
- `IMM` - Immediate field, such bits are normally chopped up and spread across remaining spaces in the instruction encoding, constructed back to 16 bit by the decoder.
- `WB` - A special encoding bit in certain variants, determines if the instruction is to write back or not. If the instruction doesn't encode an explicit WB bit, it's implicitly determined based on the type of the instruction.
- Other fields - Listed within the ISA spec.

The encoding for the 9 types of instructions are listed as follows -
- R-Type - `[(15:13) RD, (12:10) RS1, (9:7) RS2, (6:6) WB, (5:3) FUNCT, (2:0) OPCODE]`
- RI-Type - `[(15:13) RD, (12:10) RS1, (9:7) IMM[3:1], (6:6) WB, (5:5) IMM[0], (4:3) FUNCT, (2:0) OPCODE]`
- I-Type - `[(15:13) RD, (12:10) RS1, (9:5) IMM[4:0], (4:3) FUNCT, (2:0) OPCODE]`
- LI-Type & D-Type - `[(15:13) RD, (12:5) IMM, (4:3) FUNCT, (2:0) OPCODE]`
- J-Type - `[(15:5) IMM, (4:3) FUNCT, (2:0) OPCODE]`
- N-Type - `[(15:6) IMM, (5:5) RS1_VALID = 0, (4:3) FUNCT, (2:0) OPCODE]`
- P-Type - `[(15:13) IMM[6:4], (12:10) RS1, (9:6) IMM[3:0], (5:5) RS1_VALID = 1, (4:3) FUNCT, (2:0) OPCODE]`
- S-Type - `[(15:13) IMM[4:2], (12:10) RS1, (9:7) RS2, (6:5) IMM[1:0], (4:3) FUNCT, (2:0) OPCODE]`

The instruction type spec-sheet is given as follows -

| **Instruction Type** | **Opcode** | **Funct Size** | **RS1** | **RS2** | **RD** | **Imm Size** | **WB**    |
| -------------------- | ---------- | -------------- | ------- | ------- | ------ | ------------ | --------- |
| R                    | `000`      | 3 bits         | Yes     | Yes     | Yes    | N/A          | Optional* |
| RI                   | `010`      | 2 bits         | Yes     | No      | Yes    | 4 bits       | Optional* |
| I                    | `011`      | 2 bits         | Yes     | No      | Yes    | 5 bits       | Yes       |
| LI                   | `110`      | 2 bits         | No      | No      | Yes    | 8 bits       | Yes       |
| D                    | `111`      | 2 bits         | No      | No      | Yes    | 8 bits       | Yes       |
| J                    | `001`      | 2 bits         | No      | No      | No     | 11 bits      | No        |
| N                    | `101`      | 2 bits         | No      | No      | No     | 10 bits      | No        |
| P                    | `101`      | 2 bit          | Yes     | No      | No     | 7 bits       | No        |
| S                    | `100`      | 2 bits         | Yes     | Yes     | No     | 5 bits       | No        |
*\*To be determined by the entity that is writing the code or encoding the program.*