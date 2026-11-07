There are 8 encoding types of instructions in the MDA ISA, plus the suffix halfword which follows `lli`. They are `RR`, `RI-A`, `RI-Z`, `DI-L`, `DI-Z`, `NX`, `RX`, `SX` and the `SUFFIX`. There are 35 instructions, which are encoded in 37 opcode and FUNCT combinations, as `jof` and `joc` each have two variants (see the section on variants).

- Instructions are 16 bits long. The loader sends them as 16-bit units, so there is no byte order on the load path. In a byte-oriented file (e.g. a hex dump), the low byte comes first (little-endian).
- The PC counts instruction addresses, which are 16-bit halfwords (so the byte address divided by 2). All jump offsets are relative to the next instruction (PC + 1).

### Types and Fields
The following types of fields include -

- `OPCODE` - `[2:0]` - Opcode determining the type of instruction and its encoding. Always at `[2:0]`.
- `FUNCT` - `[5:3]` or `[4:3]` - Sub-field of opcode giving more information about the instruction type, operation, and details about its encoding. It is 3 bits in `RR`, `NX` and `RX`, and 2 bits in the others.
- `RD` - `[15:13]` - 3-bit destination register address field, where the result is to be stored.
- `RS1` - `[12:10]` - 3-bit source register 1 address field, the first register which is used for an operation.
- `RS2` - `[9:7]` - 3-bit source register 2 address field, the second register which may be used for an operation.
- `IMM` - Immediate field, whose bits are normally chopped up and spread across the remaining bits of the instruction, and constructed back by the decoder. Its size and extension depend on the instruction.
- `WB` - A special encoding bit in `RR` and `RI-A`, which determines if the instruction is to write back to `rd` or not. If the instruction doesn't encode an explicit WB bit, it's implicitly determined based on the type of the instruction.
- Other fields - Listed within the encoding of each instruction.

|Type|Used for|Instructions|
|---|---|---|
|RR|Register-register instructions, with `rd`|`add` `xor` `and` `or` `cmp` `cmpa` `shl` `shr`|
|RI-A|Register-immediate instructions, with `rd`, ALU type|`addi` `xori` `shli` `shri`|
|RI-Z|Register-immediate instructions, with `rd`, other type|`lb` `lw` `jrg`|
|DI-L|Direct immediate instructions, with `rd`, load immediate type|`lbi` `lli` `lui`|
|DI-Z|Direct immediate instructions, with `rd`, other type|`jmp` `pull` `rpin`|
|NX|No `rd`, only an immediate|`jnl` `jof` `inp` `outp` `dl` `flg`|
|RX|No `rd`, an immediate and `rs1`|`joc` `push` `wpin` `dlrg` `waitev` `cfg`|
|SX|No `rd`, an immediate, `rs1` and `rs2`|`sb` `sw`|
|SUFFIX|The 16-bit word that comes after `lli`|(part of `lli`)|

### Encoding Formats

The bit layouts of the types are given as follows (bit 15 to bit 0) -

- RR Type - `[(15:13) RD, (12:10) RS1, (9:7) RS2, (6:6) WB, (5:3) FUNCT, (2:0) OPCODE]`
- RI-A Type - `[(15:13) RD, (12:10) RS1, (9:7) IMM[3:1], (6:6) WB, (5:5) IMM[0], (4:3) FUNCT, (2:0) OPCODE]`
- RI-Z Type - `[(15:13) RD, (12:10) RS1, (9:5) IMM[4:0], (4:3) FUNCT, (2:0) OPCODE]`
- DI-L and DI-Z Types - `[(15:13) RD, (12:5) IMM[7:0], (4:3) FUNCT, (2:0) OPCODE]`
- NX Type - `[(15:6) IMM[9:0], (5:3) FUNCT, (2:0) OPCODE]`
- RX Type - `[(15:13) IMM[6:4], (12:10) RS1, (9:6) IMM[3:0], (5:3) FUNCT, (2:0) OPCODE]`
- SX Type - `[(15:13) IMM[4:2], (12:10) RS1, (9:7) RS2, (6:5) IMM[1:0], (4:3) FUNCT, (2:0) OPCODE]`
- SUFFIX Type - `[(15:0) raw 16 bits]`, no opcode, it is only ever read as part of `lli`.

The instruction type spec-sheet is given as follows -

|**Instruction Type**|**Opcode**|**Funct Size**|**RS1**|**RS2**|**RD**|**Imm Size**|**WB**|
|---|---|---|---|---|---|---|---|
|RR|`000`|3 bits|Yes|Yes|Yes|N/A|Optional*|
|NX|`001`|3 bits|No|No|No|10 bits|No|
|RI-A|`010`|2 bits|Yes|No|Yes|4 bits|Optional*|
|RI-Z|`011`|2 bits|Yes|No|Yes|5 bits|Yes|
|SX|`100`|2 bits|Yes|Yes|No|5 bits|No|
|RX|`101`|3 bits|Yes|No|No|7 bits|No|
|DI-L|`110`|2 bits|No|No|Yes|8 bits|Yes|
|DI-Z|`111`|2 bits|No|No|Yes|8 bits|Yes|

_*To be determined by the entity that is writing the code or encoding the program. It is the WB bit. When it is 0 (`@na` in assembly), the instruction only updates the flags, and the assembler writes the `RD` field as `000`, which the hardware ignores._

### Funct Assignments

The funct codes of every type are given as follows. A code that is marked unused is an illegal instruction (see the section on illegal encodings).

|Type|Funct codes|
|---|---|
|RR|`add` (000), `xor` (001), `shl` (010), `shr` (011), `cmp` (100), `cmpa` (101), `and` (110), `or` (111)|
|RI-A|`addi` (00), `xori` (01), `shli` (10), `shri` (11)|
|RI-Z|`lb` (00), `lw` (01), `jrg` (10), unused (11)|
|DI-L|`lui` (00), `lbi` (01), unused (10), `lli` (11)|
|DI-Z|`jmp` (00), `pull` (01), unused (10), `rpin` (11)|
|NX|`inp` (000), `outp` (001), `jnl` (010), `jof` (011), `dl` (100), unused (101), `flg` (110), `jof` inverted (111)|
|RX|`joc` any (000), `push` (001), `joc` all (010), `wpin` (011), `dlrg` (100), unused (101), `waitev` (110), `cfg` (111)|
|SX|`sb` (00), `sw` (01), unused (10), unused (11)|

### Instruction Variants

- `jof` and `joc` are each encoded with two funct codes, which differ by exactly one bit. They are not extra instructions, the mnemonics and the assembly stay the same, the bit is a condition modifier. This keeps the full 6-bit offset (-32 to 31) of the conditional jumps.
    - `jof` - funct `011` jumps if the flag is set, funct `111` (bit 2 set) is the inverted variant, which jumps if the flag is clear.
    - `joc` - funct `010` is the all variant, and funct `000` (bit 1 clear) is the any variant. In each, the invert bit in the immediate (`IMM[6]`) inverts the condition. So `@all` is funct `010` with invert 0, `@notall` is funct `010` with invert 1, `@any` is funct `000` with invert 0, and `@none` is funct `000` with invert 1.

### Encoding of Each Instruction

Notation - `IMM[a:b]` are bits of the immediate, and "bits" are bits of the instruction word. Reserved fields must be 0 (see the section on illegal encodings). All offsets are in instruction addresses (halfwords), relative to the next instruction (PC + 1).

#### RR Type (OPCODE `000`)

All RR instructions are encoded as `[RD, RS1, RS2, WB, FUNCT, 000]`, and have no immediate. `rd` is written only if `WB` is 1. The flags are always set.

|Instruction|Assembly|FUNCT|Notes|
|---|---|---|---|
|`add`|`add rd, rs1, rs2`|`000`|Sets `Z`, `N`, `C`|
|`xor`|`xor rd, rs1, rs2`|`001`|Sets `Z`, `N`|
|`shl`|`shl rd, rs1, rs2`|`010`|`rs2` is the shift amount. Sets `Z`, `N`, `C`|
|`shr`|`shr rd, rs1, rs2`|`011`|`rs2` is the shift amount. Sets `Z`, `N`, `C`|
|`cmp`|`cmp rd, rs1, rs2`|`100`|Unsigned three-way compare. `rd` = 1 if `rs1` > `rs2`, -1 (so 0xFFFFFFFF) if `rs1` < `rs2`, 0 if equal. `N` is set if less, `Z` if equal, otherwise both are 0|
|`cmpa`|`cmpa rd, rs1, rs2`|`101`|The same, signed|
|`and`|`and rd, rs1, rs2`|`110`|Sets `Z`, `N`|
|`or`|`or rd, rs1, rs2`|`111`|Sets `Z`, `N`|

#### RI-A Type (OPCODE `010`)

Encoded as `[RD, RS1, IMM[3:1] (bits 9:7), WB (bit 6), IMM[0] (bit 5), FUNCT, 010]`. The immediate is 4 bits, split around the `WB` bit (`IMM[3:1]` is bits 9:7 and `IMM[0]` is bit 5), and `WB` is bit 6 as in the RR type. `rd` is written only if `WB` is 1. The flags are always set.

|Instruction|Assembly|FUNCT|Immediate|
|---|---|---|---|
|`addi`|`addi rd, rs1, imm`|`00`|`IMM[3:1]` = bits 9:7 and `IMM[0]` = bit 5, signed, -8 to 7. Sets `C` on carry|
|`xori`|`xori rd, rs1, imm`|`01`|`IMM[3:1]` = bits 9:7 and `IMM[0]` = bit 5, signed, -8 to 7 (-1 is a NOT)|
|`shli`|`shli rd, rs1, imm`|`10`|`IMM[3:1]` = bits 9:7 and `IMM[0]` = bit 5, unsigned, the shift amount, 0 to 15|
|`shri`|`shri rd, rs1, imm`|`11`|`IMM[3:1]` = bits 9:7 and `IMM[0]` = bit 5, unsigned, the shift amount, 0 to 15|

#### RI-Z Type (OPCODE `011`)

Encoded as `[RD, RS1, IMM[4:0] (bits 9:5), FUNCT, 011]`. The immediate is 5 bits, and `rd` is always written. None of these set flags.

|Instruction|Assembly|FUNCT|Immediate|
|---|---|---|---|
|`lb`|`lb rd, offset(rs1)`|`00`|`IMM[4:0]` = bits 9:5, unsigned byte offset 0 to 31. Address = `rs1` + offset|
|`lw`|`lw rd, offset(rs1)`|`01`|`IMM[4:0]` = bits 9:5, unsigned word offset 0 to 31, scaled by 4. Address = `rs1` + 4 x offset|
|`jrg`|`jrg rd, rs1, imm`|`10`|`IMM[4:0]` = bits 9:5, signed, -16 to 15. Jumps to `rs1` (the low bits that fit the PC) + imm. `rd` = the address of the next instruction|

#### DI-L Type (OPCODE `110`)

Encoded as `[RD, IMM[7:0] (bits 12:5), FUNCT, 110]`. The immediate is 8 bits, and `rd` is always written. None of these set flags.

|Instruction|Assembly|FUNCT|Immediate|
|---|---|---|---|
|`lui`|`lui rd, imm`|`00`|`IMM[7:0]` = bits 12:5, unsigned. Written to `rd[31:24]`, and the rest of `rd` is kept|
|`lbi`|`lbi rd, imm`|`01`|`IMM[7:0]` = bits 12:5, unsigned 0 to 255, zero extended to 32 bits|
|`lli`|`lli rd, imm`|`11`|`IMM[7:0]` = bits 12:5 are bits `[23:16]` of the constant. The suffix halfword that follows is bits `[15:0]`. The 24-bit constant is zero extended to 32 bits|

- The suffix halfword has no fields. It is the raw 16 bits `[15:0]` of the constant, so every value is allowed, and the decoder only treats it as data when it comes right after an `lli`. The pair takes 2 instruction addresses and 2 slots of the thread.

#### DI-Z Type (OPCODE `111`)

Encoded as `[RD, IMM[7:0] (bits 12:5), FUNCT, 111]`. The immediate is 8 bits, and `rd` is always written.

|Instruction|Assembly|FUNCT|Immediate|
|---|---|---|---|
|`jmp`|`jmp rd, label`|`00`|`IMM[7:0]` = bits 12:5, signed offset -128 to 127. Jumps to PC + 1 + offset. `rd` = PC + 1|
|`pull`|`pull rd, shift`|`01`|`IMM[4:0]` = bits 9:5, the shift amount 0 to 31. `IMM[7:5]` = bits 12:10 are reserved (0)|
|`rpin`|`rpin rd, #pin, mode`|`11`|`IMM[7:3]` = bits 12:8, the pin number (0 to 23). `IMM[2:0]` = bits 7:5, the mode|

- The `rpin` modes are - `000` level, `001` event bit, `010` event bit and clear, `011` pending mask, `100` pending mask and clear. The modes `101`, `110` and `111` are reserved. For the two pending modes the pin field is ignored, and the assembler writes 0.

#### NX Type (OPCODE `001`)

Encoded as `[IMM[9:0] (bits 15:6), FUNCT, 001]`. The immediate is 10 bits, `IMM[k]` is bit `k + 6`.

|Instruction|Assembly|FUNCT|Immediate|
|---|---|---|---|
|`inp`|`inp count`|`000`|`IMM[4:0]` = bits 10:6, the count minus 1 (so 1 to 32 bits). `IMM[9:5]` = bits 15:11 are reserved (0)|
|`outp`|`outp count`|`001`|The same as `inp`|
|`jnl`|`jnl label`|`010`|`IMM[9:0]` = bits 15:6, signed offset -512 to 511, relative to PC + 1, wrapping around the instruction memory. No `rd`|
|`jof`|`jof flag, @noinv, label`|`011`|`IMM[9:6]` = bits 15:12, the flag index (0 to 15). `IMM[5:0]` = bits 11:6, signed offset -32 to 31. Jumps if the flag is set|
|`jof` inverted|`jof flag, @inv, label`|`111`|The same fields as above. Jumps if the flag is clear|
|`dl`|`dl imm`|`100`|`IMM[9:0]` = bits 15:6, unsigned, the delay in cycles, 0 to 1023|
|`flg`|`flg @keyword, ...`|`110`|`IMM[0]` bit 6 acknowledge `ERR` (and its cause), `IMM[1]` bit 7 acknowledge `OVR`, `IMM[2]` bit 8 acknowledge `MSG_N`, `IMM[3]` bit 9 acknowledge `MSG_P`, `IMM[4]` bit 10 ring the next thread, `IMM[5]` bit 11 ring the previous thread. `IMM[9:6]` = bits 15:12 are reserved (0)|

- A `flg` with no bits set does nothing, and is legal.
- `jnl` reaches every instruction address as long as the instruction memory has at most 1024 instruction addresses (a 10-bit PC). `jnl` with an offset of 0 does nothing, which is `$nop`.

#### RX Type (OPCODE `101`)

Encoded as `[IMM[6:4] (bits 15:13), RS1, IMM[3:0] (bits 9:6), FUNCT, 101]`. The immediate is 7 bits. `IMM[3:0]` is bits 9:6 and `IMM[6:4]` is bits 15:13.

|Instruction|Assembly|FUNCT|Immediate|
|---|---|---|---|
|`joc` any|`joc rs1, @any \| @none, label`|`000`|`IMM[6]` = bit 15, invert (0 for any, 1 for none). `IMM[5:0]` = bits 14:13 and 9:6, signed offset -32 to 31. `rs1` is the flag mask (low 16 bits)|
|`push`|`push rs1, shift`|`001`|`IMM[4:0]` = bit 13 and bits 9:6, the shift amount 0 to 31. `IMM[6:5]` = bits 15:14 are reserved (0)|
|`joc` all|`joc rs1, @all \| @notall, label`|`010`|The same fields as `joc` any. `IMM[6]` = bit 15 is the invert (0 for all, 1 for not all)|
|`wpin`|`wpin rs1, #pin`|`011`|`IMM[4:0]` = bit 13 and bits 9:6, the pin number (0 to 23). `IMM[6:5]` = bits 15:14 are reserved (0)|
|`dlrg`|`dlrg rs1, imm`|`100`|`IMM[6:0]` = bits 15:13 and 9:6, unsigned, the offset added to `rs1`, 0 to 127|
|`waitev`|`waitev rs1, mode`|`110`|`IMM[0]` bit 6 = all (0 is any). `IMM[1]` bit 7 = clear (0 is set). `IMM[2]` bit 8 = consume. `IMM[6:3]` = bit 9 and bits 15:13 are reserved for the post-event delay, and must be 0 for now|
|`cfg`|`cfg #target, rs1`|`111`|`IMM[2:0]` = bits 8:6, the target - `000` `PIN`, `001` `WATCH`, `010` `ENG_DIV`, `011` `ENG_CTL`, `100` `ENG_ABORT`, `101` `TMR`. `110` and `111` are reserved targets (a bad `cfg`). `IMM[6:3]` = bit 9 and bits 15:13 are reserved (0)|

#### SX Type (OPCODE `100`)

Encoded as `[IMM[4:2] (bits 15:13), RS1, RS2, IMM[1:0] (bits 6:5), FUNCT, 100]`. The immediate is a 5-bit unsigned offset, 0 to 31. `IMM[4:2]` is bits 15:13 and `IMM[1:0]` is bits 6:5. The data comes from `rs2` and the address from `rs1`. None of these set flags.

|Instruction|Assembly|FUNCT|Address|
|---|---|---|---|
|`sb`|`sb rs2, offset(rs1)`|`00`|`rs1` + offset (bytes)|
|`sw`|`sw rs2, offset(rs1)`|`01`|`rs1` + 4 x offset|

### Reserved and Illegal Encodings

- An instruction is illegal if its funct code is unused, or if a reserved field is not 0. The reserved fields are -
    - `pull`: `IMM[7:5]`. `push` and `wpin`: `IMM[6:5]`. `inp` and `outp`: `IMM[9:5]`.
    - `flg`: `IMM[9:6]`. `waitev`: `IMM[6:3]`. `cfg`: `IMM[6:3]`.
    - `rpin`: the modes `101` to `111`.
- An illegal instruction has no architectural effect at all (no register, flag, memory or pin changes), it only sets `ERR` with cause `110` (see `Events.md`). It takes its normal slot, and the thread keeps running.
- Values that are valid encodings but have no meaning at runtime are faults of their own, not illegal instructions - a reserved `cfg` target (`110`, `111`) or a pin number above 23 is a bad `cfg` or a bad pin access.
- The all-zero word is `add @na, r0, r0`, which only overwrites the flags. The all-one word is an illegal `rpin`.
- A jump that lands on a suffix halfword decodes it as an ordinary instruction.

### Examples

The following examples are computed from the layouts above -

|Instruction|Word|Binary|
|---|---|---|
|`add r0, r5, r6`|`0x1740`|`0001011101000000`|
|`xori @na, r7, -1`|`0x1FAA`|`0001111110101010`|
|`addi r1, r2, -4`|`0x2B42`|`0010101101000010`|
|`lw r3, 3(r2)`|`0x686B`|`0110100001101011`|
|`jrg r1, r1, 0`|`0x2413`|`0010010000010011`|
|`lbi r1, 200`|`0x390E`|`0011100100001110`|
|`lli r1, 0x123456 (first halfword)`|`0x225E`|`0010001001011110`|
|`lui r1, 0xAB`|`0x3566`|`0011010101100110`|
|`jmp r4, -2`|`0x9FC7`|`1001111111000111`|
|`pull r2, 24`|`0x430F`|`0100001100001111`|
|`rpin r3, @pend_clr`|`0x609F`|`0110000010011111`|
|`rpin r3, #17, @level`|`0x711F`|`0111000100011111`|
|`inp 8`|`0x01C1`|`0000000111000001`|
|`jnl 0 ($nop)`|`0x0011`|`0000000000010001`|
|`jof ERR, label (+5)`|`0x3159`|`0011000101011001`|
|`jof ERR, @inv, label (+5)`|`0x3179`|`0011000101111001`|
|`dl 12`|`0x0321`|`0000001100100001`|
|`flg @ack_err, @ack_ovr`|`0x00F1`|`0000000011110001`|
|`joc r2, @all, label (-3)`|`0x6B55`|`0110101101010101`|
|`joc r2, @none, label (-3)`|`0xEB45`|`1110101101000101`|
|`push r5, 24`|`0x360D`|`0011011000001101`|
|`wpin r1, #3`|`0x04DD`|`0000010011011101`|
|`dlrg r2, 5`|`0x0965`|`0000100101100101`|
|`waitev r2, @any, @set, @consume`|`0x0935`|`0000100100110101`|
|`cfg #TMR, r1`|`0x057D`|`0000010101111101`|
|`sb r1, 5(r7)`|`0x3CA4`|`0011110010100100`|
|`sw r1, 5(r7)`|`0x3CAC`|`0011110010101100`|

- For `lli r1, 0x123456`, the second halfword (the suffix) is `0x3456`.