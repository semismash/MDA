<!-- GENERATED from isa.yaml (sha256 a2def3e3217f9752) by isa_gen.py. Do not edit by hand. -->
# MDA instruction encoding tables (generated)

Bit ranges are instruction-word bits. A field with several ranges is their concatenation, MSB first.

## RR (opcode `000`, funct [5:3])

Registers: rd [15:13], rs1 [12:10], rs2 [9:7], wb [6].

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `add` | `000` | A | - | - | Z,N,C |  |
| `xor` | `001` | A | - | - | Z,N |  |
| `shl` | `010` | A | - | - | Z,N,C | rs2 is the shift amount (low 5 bits). A shift by 0 leaves C unchanged |
| `shr` | `011` | A | - | - | Z,N,C | logical shift right. A shift by 0 leaves C unchanged |
| `cmp` | `100` | A | - | - | Z,N | unsigned. rd = 1 if rs1 < rs2. N = less, Z = equal, otherwise both 0 |
| `cmpa` | `101` | A | - | - | Z,N | signed compare, same flag rules as cmp |
| `and` | `110` | A | - | - | Z,N |  |
| `or` | `111` | A | - | - | Z,N |  |

## NX (opcode `001`, funct [5:3])

Registers: no registers. Unused funct codes (illegal): 5.

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `inp` | `000` | B | `count` [10:6] unsigned, +1 (1 to 32) | [15:11] | - |  |
| `outp` | `001` | B | `count` [10:6] unsigned, +1 (1 to 32) | [15:11] | - |  |
| `jnl` | `010` | A | `offset` [15:6] signed (-512 to 511) | - | - | target = PC + 1 + off, wrapping around the instruction memory. Offset 0 is the nop |
| `jof` | `011` | A | `flag` [15:12] unsigned (0 to 15); `offset` [11:6] signed (-32 to 31) | - | - | jumps if the flag is set |
| `dl` | `100` | B | `imm` [15:6] unsigned (0 to 1023) | - | - |  |
| `flg` | `110` | B | `ack_err` [6] unsigned (0 to 1); `ack_ovr` [7] unsigned (0 to 1); `ack_msgn` [8] unsigned (0 to 1); `ack_msgp` [9] unsigned (0 to 1); `ring_next` [10] unsigned (0 to 1); `ring_prev` [11] unsigned (0 to 1) | [15:12] | - | all-zero flags is legal and does nothing |
| `jof` (jof_inv) | `111` | A | `flag` [15:12] unsigned (0 to 15); `offset` [11:6] signed (-32 to 31) | - | - | the inverted variant: jumps if the flag is clear (assembly: @inv) |

## RI-A (opcode `010`, funct [4:3])

Registers: rd [15:13], rs1 [12:10], wb [5].

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `addi` | `00` | A | `imm` [9:6] signed (-8 to 7) | - | Z,N,C |  |
| `xori` | `01` | A | `imm` [9:6] signed (-8 to 7) | - | Z,N | imm = -1 is a NOT |
| `shli` | `10` | A | `imm` [9:6] unsigned (0 to 15) | - | Z,N,C |  |
| `shri` | `11` | A | `imm` [9:6] unsigned (0 to 15) | - | Z,N,C |  |

## RI-Z (opcode `011`, funct [4:3])

Registers: rd [15:13], rs1 [12:10]. Unused funct codes (illegal): 3.

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `lb` | `00` | A | `offset` [9:5] unsigned (0 to 31) | - | - | address = rs1 + off. Unsigned load |
| `lw` | `01` | A | `offset` [9:5] unsigned, address x4 (0 to 31) | - | - | address = rs1 + 4 * off. Aligned |
| `jrg` | `10` | A | `imm` [9:5] signed (-16 to 15) | - | - | target = rs1 + imm (low bits that fit the PC), rd = address of the next instruction |

## SX (opcode `100`, funct [4:3])

Registers: rs1 [12:10], rs2 [9:7]. Unused funct codes (illegal): 2, 3.

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `sb` | `00` | A | `offset` [15:13,6:5] unsigned (0 to 31) | - | - | address = rs1 + off, data = rs2[7:0] |
| `sw` | `01` | A | `offset` [15:13,6:5] unsigned, address x4 (0 to 31) | - | - | address = rs1 + 4 * off, data = rs2 |

## RX (opcode `101`, funct [5:3])

Registers: rs1 [12:10]. Unused funct codes (illegal): 5.

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `joc` (joc_any) | `000` | A | `inv` [15] unsigned (0 to 1); `offset` [14:13,9:6] signed (-32 to 31) | - | - | any (inv = 0) or none (inv = 1) of the flags in the mask rs1[15:0] are set |
| `push` | `001` | B | `shift` [13,9:6] unsigned (0 to 31) | [15:14] | - |  |
| `joc` (joc_all) | `010` | A | `inv` [15] unsigned (0 to 1); `offset` [14:13,9:6] signed (-32 to 31) | - | - | all (inv = 0) or not-all (inv = 1) of the flags in the mask rs1[15:0] are set |
| `wpin` | `011` | B | `pin` [13,9:6] unsigned (0 to 31) | [15:14] | - |  |
| `dlrg` | `100` | B | `imm` [15:13,9:6] unsigned (0 to 127) | - | - |  |
| `waitev` | `110` | B | `all` [6] unsigned (0 to 1); `clear` [7] unsigned (0 to 1); `consume` [8] unsigned (0 to 1) | [9], [15:13] | - | reserved bits are the post-event delay and must be 0 for now |
| `cfg` | `111` | B | `target` [8:6] unsigned (0 to 7) | [9], [15:13] | - | targets 6 and 7 are a bad cfg at run time, not illegal words |

## DI-L (opcode `110`, funct [4:3])

Registers: rd [15:13]. Unused funct codes (illegal): 2.

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `lui` | `00` | A | `imm` [12:5] unsigned (0 to 255) | - | - | rd[31:24] = imm, the rest of rd is kept (rd is also a source) |
| `lbi` | `01` | A | `imm` [12:5] unsigned (0 to 255) | - | - | rd = imm, zero extended |
| `lli` | `11` | A | `imm` [12:5] unsigned (0 to 255) | - | - | imm is bits [23:16] of the 24-bit constant. The suffix halfword that follows is bits [15:0]. Takes 2 addresses and 2 slots |

## DI-Z (opcode `111`, funct [4:3])

Registers: rd [15:13]. Unused funct codes (illegal): 2.

| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |
|---|---|---|---|---|---|---|
| `jmp` | `00` | A | `offset` [12:5] signed (-128 to 127) | - | - | target = PC + 1 + off, rd = PC + 1 |
| `pull` | `01` | B | `shift` [9:5] unsigned (0 to 31) | [12:10] | - |  |
| `rpin` | `11` | B | `pin` [12:8] unsigned (0 to 31); `mode` [7:5] unsigned (0 to 7) | - | - | pin number above 23 is a runtime fault (bad pin access), not an illegal word. For the two pending modes the pin field is ignored Illegal values: mode=[5, 6, 7]. |

