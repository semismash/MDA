# MDA decoder: interface, suffix mechanism, rules and draft decode matrix

Location: `spec/`. Status: working document for the decoder and its two companions. Port names follow `mda_decoder.sv`. The matrix in section 6 is generated from `tools/isa/isa.yaml`. It is a proposal to check against the specification, not a final truth.

## 1. Partition

The decoder is a pure combinational function, which keeps it exhaustively testable over all 65,536 words. State and data-dependent work live in two neighbours.

| Block | Kind | Role |
|---|---|---|
| `mda_decoder` | combinational | `instr`, `suffix_pend` and `suffix_rd` in, control signals out |
| `mda_suffix` | 3 pending bits (reset) plus 33 payload flops | Per-thread suffix state for the two-word `lli`, indexed by the thread in ID (section 3) |
| `mda_imm_gen` | combinational | `instr`, `imm_sel`, `rs1_data` and `suffix_imm8` in, the 32-bit `imm_out` out. ALU and LSU immediates only (10 formats). `rs1_data` is used only by `lui` |
| `mda_branch_unit` | combinational | Slices the PC offset from the raw instruction and computes the link value, besides the jump controls (see `Stage_A_Microarchitecture.md`) |

Fields that need no decoding stay in the registered raw instruction and are read in EX: the `jof` flag number (`instr[15:12]`), the `joc` invert bit (`instr[15]`) and all Stage B fields (pin numbers, shift counts, modes, `waitev` options). The raw instruction travels in `mda_id_ex` anyway for the trace.

## 2. Decoder ports

Inputs: `instr` (`Instruction`), `suffix_pend` (1), `suffix_rd` (`RegAddr`).

| Group | Output | Type | Consumer | Meaning |
|---|---|---|---|---|
| Register file | `rs1_addr` | `RegAddr` | read port 1 | `instr[12:10]`. The `rd` field (`instr[15:13]`) for `lui`. Don't-care in a suffix slot |
|  | `rs2_addr` | `RegAddr` | read port 2 | `instr[9:7]`. Used by RR and the stores |
|  | `rd_addr` | `RegAddr` | write-back, LSU | `instr[15:13]`. `suffix_rd` in a suffix slot. For loads it is registered by the LSU for the load return |
|  | `reg_write` | 1 bit | write enable | EX-stage register write: ALU, immediate-load, link, Stage B result, or the suffix slot of `lli`. The `wb` bit (`instr[6]` in both RR and RI-A). **Low for loads** (the load-return path writes), stores, jumps without link, `@na` forms and word A of `lli` |
| ALU and result | `alu_op` | `AluOp` | `mda_alu` | RR: `funct[2:0]`. RI-A: `{1'b0, funct[1:0]}` |
|  | `use_imm` | 1 bit | `mda_alu` | Operand B is `imm` (RI-A) and not `rs2` (RR) |
|  | `fwd_imm` | 1 bit | `mda_alu` | Result is `imm`. High for the immediate loads (`lbi`, `lui`, the suffix slot) and, by rule, for every instruction whose ALU result is unused (jumps, Stage B), so the ALU sees quiet inputs and the write enables decide what is written. **Low for loads and stores**, where the ALU is the address adder (`alu_op = ALU_ADD`, `use_imm = 1`, no flag update) |
|  | `res_sel` | `ResSel` | EX result mux | `RES_ALU` (ALU output or forwarded immediate), `RES_LINK` (`link` from `mda_branch_unit`, for `jmp` and `jrg`), `RES_SP` (Stage B result, for `pull` and `rpin`) |
|  | `imm_sel` | `ImmSel` | `mda_imm_gen` | One of 10 formats, section 4. Jumps use `IMM_NONE` |
| Flags | `f_u_alu` | 1 bit | `mda_flags.u_alu` | The instruction updates Z and N: 12 instructions. Gated outside by "valid and this thread is in EX". It is the only flag enable: `u_alu_carry = u_alu & alu_carry_upd`, and the ALU raises `alu_carry_upd` only for add and for a shift by a nonzero amount |
|  | `illegal` | 1 bit | fault path | Illegal word (unused funct, reserved bits, bad `rpin` mode). Registered to EX, where it becomes `u_err = 1`, `f_err = 1`, `f_errc = CAUSE_ILLEGAL` (Stage B). Stage A only exposes it on the trace |
| Branch | `br_type` | `BrType` | `mda_branch_unit` | The branch unit turns it into `pc_in1`, `pc_in2`, `pc_cin`, `pc_offset` and `taken`, and computes `link` |
|  | `br_jof_inv` | 1 bit | branch unit | High for the `jof` invert variant (funct 7). The `joc` invert bit is read from the raw instruction in EX |
|  | `br_joc_all` | 1 bit | branch unit | `joc` all-of (`COND_ALL`) or any-of (`COND_ANY`) |
| Memory | `mem_op` | `MemOp` | LSU | None, load, store |
|  | `mem_byte` | 1 bit | LSU | Byte (`lb`, `sb`) or word |
| Suffix | `lli_first` | 1 bit | `mda_suffix` | The word is word A of `lli`: set the pending bit and capture `rd` and `imm8` |
| Stage B | `sp_valid` | 1 bit | Stage B units | A spatial, temporal or event instruction. A no-op in Stage A |
|  | `sp_op` | `SpOp` | Stage B units | `SP_PULL` to `SP_FLG` (1 to 11), `SP_NONE` otherwise |

Total: 37 output bits. The address outputs and `lli_first` are consumed in ID. The rest, about 30 bits, are registered into `mda_id_ex`. The constants `ImmSel`, `ResSel` and `SpOp` are defined in `mda_pkg.sv`.

## 3. The `lli` suffix mechanism

`lli rd, c` takes two halfwords. Word A has `rd` and `imm8` (constant bits `[23:16]`), and word B is the raw 16-bit suffix (bits `[15:0]`). Word B has no opcode and no register field, so everything it needs is remembered from word A.

**`mda_suffix` ports.** In: `clk`, `rst_n`, `id_t` (`ThreadSel`, one-hot thread in ID), `id_v` (ID holds a real instruction), `lli_first` (from the decoder), `instr`. Out, for the thread in ID: `suffix_pend`, `suffix_rd` (`RegAddr`), `suffix_imm8` (8 bits).

**Update rule**, on each valid ID slot of thread `t`: if `pend[t]` is set, clear it. Otherwise, if `lli_first`, set it and capture `rd = instr[15:13]`, `imm8 = instr[12:5]`. The pending bits are reset. The captured values are payload and are not (D10).

| Step | Thread 0 in ID | Decoder | Effect |
|---|---|---|---|
| ID of word A | `lli r1` with `imm8 = 0x12` | `lli_first = 1`, `reg_write = 0`, `imm_sel = IMM_NONE`, no flags | Buffer sets `pend[0]`, `rd[0] = 1`, `imm8[0] = 0x12`. A no-op for the pipeline |
| (other threads use their slots) | | | |
| ID of word B, three cycles later | suffix `0x3456` | `suffix_pend = 1` overrides the opcode bits: `rd_addr = suffix_rd`, `reg_write = 1`, `fwd_imm = 1`, `imm_sel = IMM_SUFFIX`, `res_sel = RES_ALU`, no flags | `mda_imm_gen` produces `{8'b0, 0x12, 0x3456} = 0x00123456`. The ALU forwards it and r1 is written once. The buffer clears `pend[0]` |

Properties to preserve: a jump that lands directly on a suffix word finds `pend` clear and decodes it as an ordinary instruction. A suffix word is data even if its bits look like an `lli` or an illegal encoding. The three threads' entries are independent. Neither slot sets flags.

## 4. `imm_sel` formats

| `imm_sel` | Result in `imm` | Used by |
|---|---|---|
| `IMM_NONE` | unused | most non-immediate instructions, word A of `lli`, and all jumps |
| `IMM_S4` | `{instr[9:7], instr[5]}` sign-extended (sign bit `instr[9]`) | `addi`, `xori` |
| `IMM_U4` | `{instr[9:7], instr[5]}` zero-extended | `shli`, `shri` |
| `IMM_MEM_B` | `instr[9:5]` zero-extended (byte offset) | `lb` |
| `IMM_MEM_W` | `instr[9:5] << 2` | `lw` |
| `IMM_ST_B` | `{instr[15:13], instr[6:5]}` zero-extended | `sb` |
| `IMM_ST_W` | `{instr[15:13], instr[6:5]} << 2` | `sw` |
| `IMM_LBI` | `instr[12:5]` zero-extended | `lbi` |
| `IMM_LUI` | `{instr[12:5], rs1_data[23:0]}` (`rs1_data` is the old `rd`) | `lui` |
| `IMM_SUFFIX` | `{8'b0, suffix_imm8, instr}`, a zero-extended 24-bit constant | the `lli` suffix slot |

Memory offsets are scaled in the immediate generator (word offsets times 4), so the LSU only adds. Jump offsets are not produced here: `mda_branch_unit` slices them from the raw instruction (below), and the `+1` that makes the target `PC + 1 + offset` comes from `pc_cin` in `mda_pc`.

**PC offsets (in `mda_branch_unit`).**

| Jump | Offset slice | Width |
|---|---|---|
| `jmp` | `instr[12:5]` | 8, signed |
| `jnl` | `instr[15:6]` | 10, signed |
| `jof` (both variants) | `instr[11:6]` | 6, signed |
| `joc` (both variants) | `{instr[14:13], instr[9:6]}` | 6, signed |
| `jrg` | `instr[9:5]` | 5, signed |

Each is sign-extended to the PC width (10 bits) and fed to `mda_pc.imm_in`. Only ten bits are needed because the PC adder wraps modulo the instruction memory size.

**`mda_imm_gen` ports.** In: `instr` (`Instruction`), `imm_sel` (`ImmSel`), `rs1_data` (`Word`), `suffix_imm8` (8 bits). Out: `imm_out` (`Word`). Combinational.

## 5. Rules

1. **Defaults first.** Every output starts at its benign value (no writes, no branch, no memory access, no Stage B), and each case overrides.
2. **A suffix slot overrides everything.** When `suffix_pend` is high the word is data: `rd_addr = suffix_rd`, `imm_sel = IMM_SUFFIX`, `fwd_imm = 1`, `reg_write = 1`, `res_sel = RES_ALU`, `f_u_alu = 0`, `lli_first = 0`, no legality checks.
3. **Word A of `lli` is a no-op.** `lli_first = 1`, `reg_write = 0`, `f_u_alu = 0`, `imm_sel = IMM_NONE`.
4. **Illegal means no-op.** After the case, if `illegal` is high, clear `reg_write`, `f_u_alu`, `mem_op`, `br_type`, `sp_valid` and `lli_first`. The fault is recorded and timing is unaffected.
5. **Legality** comes from the generated constants: `(instr & RSV_X) != 0` for reserved fields, the default branch of each funct `case` for unused codes, and an `rpin` mode above `RPIN_MODE_MAX_LEGAL`. Fault-class cases that are valid words (pin above 23, `cfg` target 6 or 7) are not illegal here.
6. **The register-address path is the critical one.** `rs1_addr` and `rs2_addr` should depend on the instruction bits through at most one 2:1 select (for `lui`), so the register read does not wait for the full decode.
7. **Per-thread gating is outside the decoder.** The flags module holds one thread's flags, so its enables are `f_u_alu & ex_v & ex_t[t]`, and `u_alu_carry = u_alu & alu_carry_upd`.
8. **Stage A has no Stage B hardware**, so the core masks `reg_write` with `~sp_valid` (`pull` and `rpin` would otherwise write a result that does not exist). Stage B instructions then execute as no-ops, as planned.
9. **Constructs to avoid until the toolchain probe has run:** casts to typedef'd types (`RegAddr'(x)`), enumerated types, and `return` inside functions. Plain slices (`assign rs1_addr = instr[12:10];`) and `case` statements cover everything needed.

## 6. Draft decode matrix (generated)

`-` means not applicable. `fwd_imm` is 1 wherever the ALU result is unused, except for loads and stores, where the ALU adds `rs1 + imm` for the address. `reg_write` of `wb bit` means the instruction's WB bit. `f_u_alu` is 1 for the 12 flag-setting instructions.

| Instruction | Type / funct | rs1 | rs2 | rd | reg_write | alu_op | use_imm | fwd_imm | res_sel | imm_sel | f_u_alu | br_type | br_jof_inv | br_joc_all | mem_op | mem_byte | sp_op | lli_first |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `add` | RR / 0 | rs1 | rs2 | rd | wb bit | ALU_ADD | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `xor` | RR / 1 | rs1 | rs2 | rd | wb bit | ALU_XOR | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `shl` | RR / 2 | rs1 | rs2 | rd | wb bit | ALU_SHL | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `shr` | RR / 3 | rs1 | rs2 | rd | wb bit | ALU_SHR | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `cmp` | RR / 4 | rs1 | rs2 | rd | wb bit | ALU_CMP | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `cmpa` | RR / 5 | rs1 | rs2 | rd | wb bit | ALU_CMPA | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `and` | RR / 6 | rs1 | rs2 | rd | wb bit | ALU_AND | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `or` | RR / 7 | rs1 | rs2 | rd | wb bit | ALU_OR | 0 | 0 | ALU | - | 1 | - | - | - | - | - | - | 0 |
| `addi` | RI-A / 0 | rs1 | - | rd | wb bit | ALU_ADD | 1 | 0 | ALU | S4 | 1 | - | - | - | - | - | - | 0 |
| `xori` | RI-A / 1 | rs1 | - | rd | wb bit | ALU_XOR | 1 | 0 | ALU | S4 | 1 | - | - | - | - | - | - | 0 |
| `shli` | RI-A / 2 | rs1 | - | rd | wb bit | ALU_SHL | 1 | 0 | ALU | U4 | 1 | - | - | - | - | - | - | 0 |
| `shri` | RI-A / 3 | rs1 | - | rd | wb bit | ALU_SHR | 1 | 0 | ALU | U4 | 1 | - | - | - | - | - | - | 0 |
| `lb` | RI-Z / 0 | rs1 | - | rd | 0 (load return) | ALU_ADD | 1 | 0 | - | MEM_B | 0 | - | - | - | MEM_LOAD | 1 | - | 0 |
| `lw` | RI-Z / 1 | rs1 | - | rd | 0 (load return) | ALU_ADD | 1 | 0 | - | MEM_W | 0 | - | - | - | MEM_LOAD | 0 | - | 0 |
| `jrg` | RI-Z / 2 | rs1 | - | rd | 1 | - | - | 1 | LINK | - | 0 | BR_JRG | - | - | - | - | - | 0 |
| `lui` | DI-L / 0 | rd | - | rd | 1 | - | - | 1 | ALU | LUI | 0 | - | - | - | - | - | - | 0 |
| `lbi` | DI-L / 1 | - | - | rd | 1 | - | - | 1 | ALU | LBI | 0 | - | - | - | - | - | - | 0 |
| `lli` | DI-L / 3 | - | - | - | 0 (word A is a no-op) | - | - | 1 | - | NONE | 0 | - | - | - | - | - | - | 1 |
| `jmp` | DI-Z / 0 | - | - | rd | 1 | - | - | 1 | LINK | - | 0 | BR_JMP | - | - | - | - | - | 0 |
| `pull` | DI-Z / 1 | - | - | rd | 1 | - | - | 1 | SP | - | 0 | - | - | - | - | - | 1 | 0 |
| `rpin` | DI-Z / 3 | - | - | rd | 1 | - | - | 1 | SP | - | 0 | - | - | - | - | - | 5 | 0 |
| `inp` | NX / 0 | - | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 3 | 0 |
| `outp` | NX / 1 | - | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 4 | 0 |
| `jnl` | NX / 2 | - | - | - | 0 | - | - | 1 | - | - | 0 | BR_JNL | - | - | - | - | - | 0 |
| `jof` | NX / 3 | - | - | - | 0 | - | - | 1 | - | - | 0 | BR_JOF | 0 | - | - | - | - | 0 |
| `dl` | NX / 4 | - | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 7 | 0 |
| `flg` | NX / 6 | - | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 11 | 0 |
| `jof_inv (jof)` | NX / 7 | - | - | - | 0 | - | - | 1 | - | - | 0 | BR_JOF | 1 | - | - | - | - | 0 |
| `joc_any (joc)` | RX / 0 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | BR_JOC | - | 0 | - | - | - | 0 |
| `push` | RX / 1 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 2 | 0 |
| `joc_all (joc)` | RX / 2 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | BR_JOC | - | 1 | - | - | - | 0 |
| `wpin` | RX / 3 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 6 | 0 |
| `dlrg` | RX / 4 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 8 | 0 |
| `waitev` | RX / 6 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 9 | 0 |
| `cfg` | RX / 7 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | - | - | - | - | - | 10 | 0 |
| `sb` | SX / 0 | rs1 | rs2 | - | 0 | ALU_ADD | 1 | 0 | - | ST_B | 0 | - | - | - | MEM_STORE | 1 | - | 0 |
| `sw` | SX / 1 | rs1 | rs2 | - | 0 | ALU_ADD | 1 | 0 | - | ST_W | 0 | - | - | - | MEM_STORE | 0 | - | 0 |
| suffix slot | (data) | - | - | `suffix_rd` | 1 | - | - | 1 | ALU | SUFFIX | 0 | - | - | - | - | - | - | 0 |

## 7. Working order for the decoder

1. Check the matrix row by row against the specification. Anything marked `-` that matters, or any row that looks wrong, is a decision to settle before writing RTL.
2. Write the decoder as defaults, then the suffix override, then `case (instr[2:0])` on the generated `OPC_*` constants with a second `case` on the funct field inside each type, then the legality checks, then the final illegal gating.
3. Write `mda_imm_gen` from the table in section 4, and instantiate `mda_suffix` as given. Test each block alone.
4. Test the decoder over all 65,536 words, with `suffix_pend` both low and high, against an independent model. `golden_decode.csv` gives the legal and illegal classification and the instruction identity. The matrix gives the expected control values for the legal ones.
5. Check invariants rather than only values: an illegal word never enables a write, a store never sets `reg_write`, a load never sets `reg_write`, only the 12 listed instructions set `f_u_alu`, and in a suffix slot nothing but the register write and the immediate path is active.
6. Connect the three blocks in `mda_core` and run the `lli` corner cases listed in D4 of `Stage_A_Microarchitecture.md`.