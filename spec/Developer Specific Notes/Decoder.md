# MDA decoder: interface, rules and draft decode matrix

Location: `spec/`. Status: working draft for the decoder and its two companions. The matrix in section 5 is generated from `tools/isa/isa.yaml`. It is a proposal to correct, not a final truth. Signal names follow the style of the existing RTL (`flag_zn_we` feeds `u_alu` in `mda_flags`, `alu_op` is the `AluOp` of `mda_alu`, and so on).

## 1. Partition

The decoder is a pure combinational function. State and data-dependent work live in two small neighbours, which keeps the decoder exhaustively testable over all 65,536 words.

| Block | Kind | Role |
|---|---|---|
| `mda_decoder` | combinational | `instr`, `suffix_pend` and `suffix_rd` in; control signals out |
| `mda_suffix` (suffix buffer) | 12 flops, reset | Per-thread `suffix_pend` and `suffix_rd`, indexed by the thread in ID. Set by `lli_first`, cleared by the suffix slot |
| `mda_immgen` | combinational | `instr`, `imm_sel` and `rs1_data` in; the 32-bit `imm` out. Needs `rs1_data` only for `lui` and the `lli` suffix merge |

Fields that need no decoding stay in the registered raw instruction and are read in EX: the `jof` flag number (`instr[15:12]`), the `joc` invert bit, and all Stage B fields (pin numbers, shift counts, modes, `waitev` options). The raw instruction travels in `mda_id_ex` anyway for the trace.

## 2. Decoder ports

Inputs: `instr` (16), `suffix_pend` (1), `suffix_rd` (3).

| Group | Output | Width | Consumer | Meaning |
|---|---|---|---|---|
| Register file | `rs1_addr` | 3 | `mda_regfile` read port 1 | `instr[12:10]`. `rd` field (`instr[15:13]`) for `lui`. `suffix_rd` in a suffix slot |
|  | `rs2_addr` | 3 | read port 2 | `instr[9:7]`. Used by RR and the stores |
|  | `rd_addr` | 3 | write-back, LSU | `instr[15:13]`. `suffix_rd` in a suffix slot. For loads it is registered by the LSU for the load return |
|  | `reg_write` | 1 | write enable | EX-stage register write: ALU, immediate-load, link or Stage B result. The `wb` bit for RR and RI-A. **Low for loads** (the load-return path writes), stores, jumps without link, and `@na` forms |
| ALU and result | `alu_op` | 3 | `mda_alu` | `AluOp`. RR: `funct[2:0]`. RI-A: `{1'b0, funct[1:0]}` |
|  | `use_imm` | 1 | `mda_alu` | Operand B is `imm` (RI-A) and not `rs2` (RR) |
|  | `fwd_imm` | 1 | `mda_alu` | Result is `imm`. High for the immediate loads and, by rule, for **every instruction that does not use the ALU result**, so the ALU sees quiet inputs and the write enables decide what is written |
|  | `res_sel` | 2 | EX result mux | `RES_ALU` (ALU or forwarded immediate), `RES_LINK` (`pc_plus1`, for `jmp` and `jrg`), `RES_SP` (Stage B result, for `pull` and `rpin`) |
|  | `imm_sel` | 4 | `mda_immgen` | One of 16 formats, section 3 |
| Flags | `flag_zn_we` | 1 | `mda_flags.u_alu` | Instruction updates Z and N. 12 instructions. Gated outside by "valid and this thread is in EX" |
|  | `flag_c_we` | 1 | `mda_flags.u_alu_carry` | Instruction may update C. 6 instructions. In the parent: `u_alu_carry = flag_c_we & alu_carry_upd`, also gated |
|  | `illegal` | 1 | fault path | Illegal word (unused funct, reserved bits, bad `rpin` mode). Registered to EX, where it becomes `u_err = 1`, `f_err = 1`, `f_errc = CAUSE_ILLEGAL` (Stage B). Stage A only exposes it on the trace |
| Branch | `br_type` | 3 | branch unit, `mda_pc` | `BrType`. The branch unit turns it into `pc_en`, `pc_in1`, `pc_in2` and `pc_cin` with the `taken` result |
|  | `br_inv` | 1 | branch unit | `jof` invert variant (funct 7), or the `joc` invert bit |
|  | `br_all` | 1 | branch unit | `joc` all-of (`COND_ALL`) or any-of (`COND_ANY`) |
| Memory | `mem_op` | 2 | LSU | `MemOp` |
|  | `mem_byte` | 1 | LSU | Byte (`lb`, `sb`) or word |
| Stage B | `sp_valid` | 1 | Stage B units | A spatial, temporal or event instruction. Executes as a no-op in Stage A |
|  | `sp_op` | 4 | Stage B units | `SP_PULL`=1, `PUSH`=2, `INP`=3, `OUTP`=4, `RPIN`=5, `WPIN`=6, `DL`=7, `DLRG`=8, `WAITEV`=9, `CFG`=10, `FLG`=11 |
| Suffix | `lli_first` | 1 | `mda_suffix` | The word is the first half of `lli`: set `suffix_pend` and capture `rd` |

Total: 38 output bits. About 31 of them are registered into `mda_id_ex` (the address outputs and `lli_first` are consumed in ID).

Constants to add to `mda_pkg` (values are suggestions): `RES_ALU`=0, `RES_LINK`=1, `RES_SP`=2; `IMM_*` and `SP_*` as in this document.

## 3. `imm_sel` formats

| `imm_sel` | Result in `imm` | Used by |
|---|---|---|
| `IMM_NONE` | unused | most non-immediate instructions |
| `IMM_S4` | `instr[9:6]` sign-extended | `addi`, `xori` |
| `IMM_U4` | `instr[9:6]` zero-extended | `shli`, `shri` |
| `IMM_MEM_B` | `instr[9:5]`, zero-extended (byte offset) | `lb` |
| `IMM_MEM_W` | `instr[9:5] << 2` | `lw` |
| `IMM_ST_B` | `{instr[15:13], instr[6:5]}`, zero-extended | `sb` |
| `IMM_ST_W` | `{instr[15:13], instr[6:5]} << 2` | `sw` |
| `IMM_S5` | `instr[9:5]` sign-extended | `jrg` |
| `IMM_LBI` | `instr[12:5]` zero-extended | `lbi` |
| `IMM_LLI` | `instr[12:5] << 16` | `lli`, first slot |
| `IMM_LUI` | `{instr[12:5], rs1_data[23:0]}` (`rs1_data` is the old `rd`) | `lui` |
| `IMM_SUFFIX` | `rs1_data \| instr` (`rs1_data` is the old `rd`, `instr` the 16-bit suffix) | the `lli` suffix slot |
| `IMM_S8` | `instr[12:5]` sign-extended | `jmp` |
| `IMM_S10` | `instr[15:6]` sign-extended | `jnl` |
| `IMM_S6` | `instr[11:6]` sign-extended | `jof`, both variants |
| `IMM_S6B` | `{instr[14:13], instr[9:6]}` sign-extended | `joc`, both variants |

Memory offsets are scaled in the immediate generator (word offsets times 4), so the LSU only adds. Relative jump offsets leave the generator unscaled. The `+1` that makes the target `PC + 1 + offset` comes from `pc_cin` in `mda_pc`.

## 4. Rules

1. **Defaults first.** Every output starts at its benign value (no writes, no branch, no memory access, no Stage B), and each case overrides.
2. **A suffix slot overrides everything.** When `suffix_pend` is high the word is data: `rs1_addr = rd_addr = suffix_rd`, `imm_sel = IMM_SUFFIX`, `fwd_imm = 1`, `reg_write = 1`, `res_sel = RES_ALU`, no flags, no legality checks.
3. **Illegal means no-op.** After the case, if `illegal` is high, clear `reg_write`, `flag_zn_we`, `flag_c_we`, `mem_op`, `br_type`, `sp_valid` and `lli_first`. The fault is recorded and timing is unaffected.
4. **Legality** comes from the generated constants: `(instr & RSV_X) != 0` for reserved fields, the default branch of each funct `case` for unused codes, and `rpin` mode above `RPIN_MODE_MAX_LEGAL`. Fault-class cases that are valid words (pin above 23, `cfg` target 6 or 7) are not illegal here.
5. **The register-address path is the critical one.** `rs1_addr` and `rs2_addr` should depend on the instruction bits through at most one 2:1 select (for `lui` and the suffix slot), so the register read does not wait for the full decode.
6. **Per-thread gating is outside the decoder.** The flags module holds one thread's flags, so its enables are `decoder output & ex_v & ex_t[t]`.
7. **Constructs to avoid until the toolchain probe has run:** casts to typedef'd types (`RegAddr'(x)`), enumerated types, and `return` inside functions. Plain slices (`assign rs1_addr = instr[12:10];`) and `case` statements cover everything needed.

## 5. Draft decode matrix (generated)

`-` means not applicable. `fwd_imm` is 1 wherever the ALU result is unused (rule in section 2). `reg_write` of `wb bit` means the instruction's WB bit.

| Instruction | Type / funct | rs1 | rs2 | rd | reg_write | alu_op | use_imm | fwd_imm | res_sel | imm_sel | zn | c | br_type | br_inv | br_all | mem_op | mem_byte | sp_op | lli_first |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `add` | RR / 0 | rs1 | rs2 | rd | wb bit | ALU_ADD | 0 | 0 | ALU | - | 1 | 1 | - | - | - | - | - | - | 0 |
| `xor` | RR / 1 | rs1 | rs2 | rd | wb bit | ALU_XOR | 0 | 0 | ALU | - | 1 | 0 | - | - | - | - | - | - | 0 |
| `shl` | RR / 2 | rs1 | rs2 | rd | wb bit | ALU_SHL | 0 | 0 | ALU | - | 1 | 1 | - | - | - | - | - | - | 0 |
| `shr` | RR / 3 | rs1 | rs2 | rd | wb bit | ALU_SHR | 0 | 0 | ALU | - | 1 | 1 | - | - | - | - | - | - | 0 |
| `cmp` | RR / 4 | rs1 | rs2 | rd | wb bit | ALU_CMP | 0 | 0 | ALU | - | 1 | 0 | - | - | - | - | - | - | 0 |
| `cmpa` | RR / 5 | rs1 | rs2 | rd | wb bit | ALU_CMPA | 0 | 0 | ALU | - | 1 | 0 | - | - | - | - | - | - | 0 |
| `and` | RR / 6 | rs1 | rs2 | rd | wb bit | ALU_AND | 0 | 0 | ALU | - | 1 | 0 | - | - | - | - | - | - | 0 |
| `or` | RR / 7 | rs1 | rs2 | rd | wb bit | ALU_OR | 0 | 0 | ALU | - | 1 | 0 | - | - | - | - | - | - | 0 |
| `addi` | RI-A / 0 | rs1 | - | rd | wb bit | ALU_ADD | 1 | 0 | ALU | S4 | 1 | 1 | - | - | - | - | - | - | 0 |
| `xori` | RI-A / 1 | rs1 | - | rd | wb bit | ALU_XOR | 1 | 0 | ALU | S4 | 1 | 0 | - | - | - | - | - | - | 0 |
| `shli` | RI-A / 2 | rs1 | - | rd | wb bit | ALU_SHL | 1 | 0 | ALU | U4 | 1 | 1 | - | - | - | - | - | - | 0 |
| `shri` | RI-A / 3 | rs1 | - | rd | wb bit | ALU_SHR | 1 | 0 | ALU | U4 | 1 | 1 | - | - | - | - | - | - | 0 |
| `lb` | RI-Z / 0 | rs1 | - | rd | 0 (load return) | - | - | 1 | - | MEM_B | 0 | 0 | - | - | - | MEM_LOAD | 1 | - | 0 |
| `lw` | RI-Z / 1 | rs1 | - | rd | 0 (load return) | - | - | 1 | - | MEM_W | 0 | 0 | - | - | - | MEM_LOAD | 0 | - | 0 |
| `jrg` | RI-Z / 2 | rs1 | - | rd | 1 | - | - | 1 | LINK | S5 | 0 | 0 | BR_JRG | - | - | - | - | - | 0 |
| `lui` | DI-L / 0 | rd | - | rd | 1 | - | - | 1 | ALU | LUI | 0 | 0 | - | - | - | - | - | - | 0 |
| `lbi` | DI-L / 1 | - | - | rd | 1 | - | - | 1 | ALU | LBI | 0 | 0 | - | - | - | - | - | - | 0 |
| `lli` | DI-L / 3 | - | - | rd | 1 | - | - | 1 | ALU | LLI | 0 | 0 | - | - | - | - | - | - | 1 |
| `jmp` | DI-Z / 0 | - | - | rd | 1 | - | - | 1 | LINK | S8 | 0 | 0 | BR_JMP | - | - | - | - | - | 0 |
| `pull` | DI-Z / 1 | - | - | rd | 1 | - | - | 1 | SP | - | 0 | 0 | - | - | - | - | - | 1 | 0 |
| `rpin` | DI-Z / 3 | - | - | rd | 1 | - | - | 1 | SP | - | 0 | 0 | - | - | - | - | - | 5 | 0 |
| `inp` | NX / 0 | - | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 3 | 0 |
| `outp` | NX / 1 | - | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 4 | 0 |
| `jnl` | NX / 2 | - | - | - | 0 | - | - | 1 | - | S10 | 0 | 0 | BR_JNL | - | - | - | - | - | 0 |
| `jof` | NX / 3 | - | - | - | 0 | - | - | 1 | - | S6 | 0 | 0 | BR_JOF | 0 | - | - | - | - | 0 |
| `dl` | NX / 4 | - | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 7 | 0 |
| `flg` | NX / 6 | - | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 11 | 0 |
| `jof_inv (jof)` | NX / 7 | - | - | - | 0 | - | - | 1 | - | S6 | 0 | 0 | BR_JOF | 1 | - | - | - | - | 0 |
| `joc_any (joc)` | RX / 0 | rs1 | - | - | 0 | - | - | 1 | - | S6B | 0 | 0 | BR_JOC | instr[15] | 0 | - | - | - | 0 |
| `push` | RX / 1 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 2 | 0 |
| `joc_all (joc)` | RX / 2 | rs1 | - | - | 0 | - | - | 1 | - | S6B | 0 | 0 | BR_JOC | instr[15] | 1 | - | - | - | 0 |
| `wpin` | RX / 3 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 6 | 0 |
| `dlrg` | RX / 4 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 8 | 0 |
| `waitev` | RX / 6 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 9 | 0 |
| `cfg` | RX / 7 | rs1 | - | - | 0 | - | - | 1 | - | - | 0 | 0 | - | - | - | - | - | 10 | 0 |
| `sb` | SX / 0 | rs1 | rs2 | - | 0 | - | - | 1 | - | ST_B | 0 | 0 | - | - | - | MEM_STORE | 1 | - | 0 |
| `sw` | SX / 1 | rs1 | rs2 | - | 0 | - | - | 1 | - | ST_W | 0 | 0 | - | - | - | MEM_STORE | 0 | - | 0 |
| suffix slot | (data) | rd (`suffix_rd`) | - | rd (`suffix_rd`) | 1 | - | - | 1 | ALU | SUFFIX | 0 | 0 | - | - | - | - | - | - | 0 |

## 6. How to work through it

1. Check the matrix row by row against the spec before writing any RTL. Anything marked `-` that matters, or any row that looks wrong, is a design decision to settle first.
2. Write the decoder as defaults followed by `case (instr[2:0])` on the generated `OPC_*` constants, with a second `case` on the funct field inside each type.
3. Build the three blocks separately (decoder, suffix buffer, immediate generator) and test each alone.
4. Test the decoder over all 65,536 words with every suffix state against an independent model. `golden_decode.csv` gives the legal and illegal classification and the instruction identity. The matrix gives the expected control values for the legal ones.
5. Check the invariants rather than only values: an illegal word never enables a write, a store never sets `reg_write`, a load never sets `reg_write`, and only the 12 listed instructions set `flag_zn_we`.