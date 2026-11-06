# MDA Stage A: microarchitecture decisions and port lists

Location: `spec/Processor Architecture/`. This document is a plan for RTL that does not yet exist. Estimates are marked as such. Timing figures are back-of-envelope values for the slow corner at a 20 ns clock, to be replaced by the first hardening report.

## 1. Decisions to lock before writing RTL

### D1. Memory access happens in EX. The register file is three banks, one write port each.

This was verified with a slot-schedule script. Over 3,000 cycles of random instruction mixes there were 0 same-bank double writes, 0 read-after-write violations, and 0 cases where a bank is read in ID while it is written (so no write-through bypass is needed). A single shared write port would have conflicted in 13% of write cycles.

Why it works, for a thread `t`:

| Cycle | Thread t does | What is written |
|---|---|---|
| k (IF) | Fetch at `pc[t]` | |
| k+1 (ID) | Instruction word arrives from IMEM, decode, read registers | |
| k+2 (EX) | ALU or branch or address generation. Load/store address goes to DMEM | ALU result written to bank t at the end of the cycle |
| k+3 (IF of next instruction) | | **Load data** arrives from DMEM and is written to bank t at the end of the cycle |
| k+4 (ID of next) | Reads registers | |

The load return always lands while thread `t` is in its IF slot, which is a different phase from its EX slot. Bank `t` is therefore never written by both paths in the same cycle. Each bank has one write port with a 2:1 data mux (EX result or load data), selected by the slot. The mux costs about 96 mux2 cells in total. The next instruction of the same thread reads in ID at k+4, after the load write at k+3, so no forwarding is needed.

The load-return thread is always **the thread currently in IF**, so `mda_wb` needs no extra thread tracking, only a registered `rd` index, byte lane and byte flag from the load's EX cycle.

Generating the load address in ID instead would need only one write port, but it was rejected: the path would be IMEM output (up to about 7.4 ns slow) + register read + 32-bit add + bounds check into the DMEM macro, which estimates near 16-17 ns of a 20 ns budget. The banked design keeps every path under about 14 ns.

### D2. No IF/ID register module.
The IMEM macro's registered output is the IF/ID stage register: the instruction word is valid for exactly cycle k+1, and the decoder reads it straight from the macro. `mda_if_id.sv` is therefore not needed. Only `mda_id_ex` is a real pipeline register. Registering the instruction word and decoding a cycle later is not possible: that adds a stage **before** EX, so EX would land in the same cycle as the thread's next fetch, a taken branch could not update the PC in time, and every taken branch would cost that thread a 3-cycle bubble, breaking the spec's zero-penalty rule. (A stage **after** EX is fine, and the load return in D1 is effectively one.) If a named IF/ID stage is wanted for readability, `mda_if_id.sv` can be kept as a thin module with no registers (thread id, valid bit after `go`, suffix state).

The ID-stage path is then macro clock-to-out (6.4-7.4 ns slow) + decode + register read + operand mux, estimated at about 14 ns. The register-read indices come straight from instruction bits (`rs1` at `[12:10]`, `rs2` at `[9:7]`), with a 1-bit mux for `lui` (reads `rd`) and for the `lli` second slot, so they do not wait for the decoder.

### D3. PC convention.
`pc[t]` always holds the address of the **next** instruction to fetch.
- In IF (cycle k), thread `t` fetches `pc[t]` and increments it at the end of the cycle.
- In EX (cycle k+2), `pc[t]` already equals instruction address + 1, which is exactly what jumps use: `target = pc + offset` for `jmp`/`jnl`/`jof`/`joc` (offsets are relative to PC+1), `target = rs1 + imm` for `jrg`, and the link value is `pc`.
- A taken jump overwrites `pc[t]` at the end of EX, and it is fetched at k+3. No instruction address needs to travel down the pipeline.
- `waitev` (Stage B) holds a thread by writing `pc - 1` back. The override interface is `ex_pc_we` / `ex_pc_val`.

IF increments the PC of the IF thread and EX overwrites the PC of the EX thread. These are different threads in every cycle, so there is no conflict.

### D4. `lli` as a hold-then-build constant.
The instruction word (word A) carries the upper byte `[23:16]` of the constant, and the suffix halfword (word B) carries `[15:0]`.
- **Word A** executes as a no-operation. The decoder raises `lli_first`, and `mda_suffix` captures `rd` and `imm8` for the thread in ID and marks a suffix as pending.
- **Word B (the suffix slot):** `suffix_pend` tells the decoder to treat the word as data. The immediate generator builds the whole constant `{8'b0, suffix_imm8, instr}`, the ALU forwards it (`fwd_imm`), and `rd = suffix_rd` is written once. The result is a single architectural register write and a single trace event, at the suffix slot. No intermediate value appears in `rd`, and the suffix slot needs no register read.
- **State:** `mda_suffix` holds, per thread, a pending bit (reset), `rd` (3 bits) and `imm8` (8 bits) (unreset payload, qualified by the pending bit). That is 36 flops in total. The alternative of two micro-operations that merge in the register file needs 12 flops but writes `rd` twice and needs a register read in the suffix slot.
- **A jump that lands directly on a suffix word** finds the pending bit clear, and the word decodes as an ordinary instruction, as the spec requires.
- The next instruction of the thread is in ID three cycles after the suffix slot's ID, one cycle after its write, so no forwarding is needed.
- Neither slot updates flags.

The scheme was checked at model level against the direct meaning of `lli` over 5,000 random three-thread programs (random suffix words, junk words, and 2,009 jumps that landed directly on suffix words), with no mismatches. Three deliberate breaks of the scheme (one shared buffer entry, suffix decoded as an instruction, pending bit never cleared) were all caught.

The checks to cover in RTL tests: a flag-setting instruction right before `lli`, `lli` followed by a jump to its own suffix address, `lli` as the last word before the PC wraps, back-to-back `lli` words, all three threads interleaving `lli`, and a suffix word that looks like an `lli` or an illegal encoding.

### D5. Flags.
Z, N, C live per thread in `mda_flags`. Instructions that set flags: `add xor and or cmp cmpa shl shr addi xori shli shri`. Nothing else does (`lbi`/`lli`/`lui`, loads, stores and jumps leave them alone). `C` is updated by `add`/`addi`, and by shifts only when the amount is not 0. The ALU output `alu_carry_upd` encodes exactly this (high for add and for a shift by a nonzero amount, low for every other operation), so the decoder needs a single flag enable (`f_u_alu`) and the flags module receives `u_alu_carry = u_alu & alu_carry_upd`. A branch in EX reads the flags written 3 cycles earlier by the thread's previous instruction. Event flags join `mda_flags` in Stage B, so it exposes a 16-bit view from the start (bits above 2 read as 0).

### D6. Faults in Stage A.
The LSU produces `fault` and `fault_cause` (misaligned `000`, out of bounds `001`) and the decoder produces `illegal` (`110`). The faulting store is suppressed (`A_MEN` low), the faulting load returns 0, and illegal instructions execute as no-ops. Stage A only **exposes** the faults on the trace port. The `ERR` flag and cause latching arrive with `mda_events` in Stage B. Timing is never affected, as the spec requires.

### D7. Memory access details.
- Loads and stores use the ALU as the address adder: the decoder sets `alu_op = ALU_ADD`, `use_imm = 1`, `fwd_imm = 0` and no flag update, and the LSU takes the ALU result as `addr`. This saves a 32-bit adder. The EX path is ID/EX registers, ALU add, bounds and alignment check, DMEM macro setup, and is estimated well inside the cycle.
- Word index = `addr[DMEM_ADDR_WIDTH+1:2]`. Out of bounds if `addr[31:DMEM_ADDR_WIDTH+2] != 0`. Misaligned if `lw`/`sw` and `addr[1:0] != 0`.
- Byte store: `dm_wstrb = 4'b0001 << addr[1:0]` and `dm_wdata = {4{rs2[7:0]}}`. Word store: `dm_wstrb = 4'b1111`. `mda_dmem` expands the strobe to the per-bit mask that the macro takes.
- Byte load: the lane is selected from the registered `addr[1:0]` of the load.
- IMEM macro: `A_MEN = 1`, `A_REN = 1` every cycle while running, `A_BM = 16'hFFFF`, `A_DLY = 1`, `A_BIST_* = 0`.
- Cross-thread visibility: a store at EX in cycle k is visible to any load whose address is issued from cycle k+1 onward, which is the soonest another thread can issue one.

### D8. Stage A needs a way to keep the logic alive for hardening.
With no loader and no pins, the synthesizer would remove most of the design. The Stage A `mda_tt_top` should expose a trace hash (an 8-bit XOR/rotate accumulator of EX results, mapped to `uo_out`), and the unused inputs should be consumed in the `_unused` idiom. Memory contents are unknown after reset (the macros have no reset), so the cores run garbage, which still exercises everything. Programs for simulation are loaded through the testbench. A real loader is Stage B.

### D9. Trace port (always present, left open at the TT wrapper).
Do not use `ifdef` for this: synthesis removes the unused logic anyway, and the port set stays identical in simulation and formal. Fields, all registered at the end of EX: `tr_valid`, `tr_t` (thread, one-hot), `tr_pc`, `tr_instr`, `tr_rd_we`, `tr_rd`, `tr_wdata`, `tr_flags_we`, `tr_flags`, `tr_taken`, `tr_next_pc`, `tr_mem_we`, `tr_mem_addr`, `tr_mem_wdata`, `tr_fault`, `tr_cause`; plus a second event for a load return one cycle later (`tr_ld_valid`, `tr_ld_t`, `tr_ld_rd`, `tr_ld_data`). This is the interface that the lockstep checker against the reference model compares.

### D10. Reset policy.

`rst_n` resets control state only. Data storage is never reset. A flop is reset when a wrong value after reset would change what the machine does. Register files, memories and pipeline payload are not reset.

**Distribution.** `rst_n` is active low. `mda_tt_top` passes the pin through the 2-flop synchronizer (`mda_sync`, `W` = 1). The synchronized signal drives the asynchronous reset input of every resettable flop (`always_ff @(posedge clk or negedge rst_n)`). Assertion therefore reaches the design up to two clock cycles after the pin, and release is synchronous to `clk`. Reset is held for at least three cycles on the board and at least five in testbenches. Resettable control flops and unreset payload flops are written in separate `always_ff` blocks, because the reset branch of a block resets every register assigned in it.

**Sequence.** Reset leaves `run` low and the design idle. A testbench or the loader then fills IMEM and DMEM and pulses `go` for one cycle. `go` loads the three entry PCs and sets `run`. Thread 0 is in IF in the first cycle with `run` high, and the first valid instruction reaches EX two cycles later.

| State | Module | Reset | Reason |
|---|---|---|---|
| `run` | `mda_core` | Yes, low | Nothing executes until `go` |
| Scheduler ring position | `mda_sched` | Yes, thread 0 in IF | All threads start in a known slot |
| `id_v` | `mda_sched` | Yes, low | No instruction is in ID after reset |
| `ex_v` | `mda_id_ex` | Yes, low | A stale valid bit would execute garbage |
| `ld_valid` | `mda_lsu` | Yes, low | A stale load return would write a register bank |
| `suffix_pend` (per thread) | `mda_suffix` | Yes, low | A stale flag would decode the first word as an `lli` suffix |
| Captured `rd` and `imm8` of a pending `lli` | `mda_suffix` | No | Payload, qualified by `suffix_pend` |
| Flags `Z`, `N`, `C` | `mda_flags` | Yes, 0 | Start state in `Threading.md` |
| Trace hash | `mda_tt_top` | Yes, 0 | Observable output of the hardening harness |
| PCs | `mda_fetch` | No | Loaded by `go`. Fetch is disabled while `run` is low |
| GPRs | `mda_regfile` | **No** | Uninitialized by specification. Random-initial-state tests rely on this |
| Operands, immediates, control and instruction bits in `mda_id_ex` | `mda_id_ex` | No | Payload, qualified by `valid` |
| `ld_rd`, `ld_lane`, `ld_byte` | `mda_lsu` | No | Payload, qualified by `ld_valid` |
| IMEM and DMEM | macros | No | The macros have no reset. The loader or testbench fills them |

Stage B adds the following reset state, matching the start state in `Threading.md`: the event flags (all clear, `OSR_EMPTY` set), sleep state, timers (disarmed), doorbells (clear), pin configuration (output off, roles cleared, watchers off, event bits clear, default owners), shift-engine busy state (idle), the loader state machine with its sticky error latch, and CRC accumulators. Not reset: the pin synchronizer flops (data) and ISR/OSR contents ("empty" is a flag). Whether the engine configuration registers (divisor, control) are reset is not specified and remains to be decided.

**Verification.**
- Assertions: after reset and before `go`, no register write, memory write or PC change occurs, and `A_WEN` of both macros stays low. After `go`, the first valid instruction reaches EX exactly two cycles after the first IF.
- Control state is known after reset in a 4-state simulator (no `X` on any reset flop).
- Data state is randomized, not reset. Verilator is run with `--x-initial unique` and `+verilator+rand+reset+2` with different seeds, and the determinism tests require identical traces across seeds.
- `mda_sched` is checked formally: exactly one thread per stage after reset and in every later cycle.

## 2. Updated Stage A file list

Compared with the earlier file tree: `mda_if_id` removed (D2), `mda_pc` merged into `mda_fetch` (a standalone PC module would be a thin wrapper), `mda_ex` removed (pure wiring, `mda_core` instantiates its children directly), and `mda_spatial` moved to Stage B. That makes **22 `src/` files plus the 2 macro stubs for Stage A** (`mda_suffix` and `mda_imm_gen` were split out of the decoder, and `mda_shifter` was dropped because the shifts live in `mda_alu`):

```
mda_pkg  mda_isa_pkg  mda_tt_top  mda_top  mda_core  mda_sched  mda_fetch  mda_id_ex  mda_decoder  mda_suffix  mda_imm_gen
mda_regfile  mda_alu  mda_branch_unit  mda_cond  mda_flags  mda_lsu  mda_wb
mda_imem  mda_dmem  mda_sram_sim  mda_sync
RM_IHPSG13_1P_1024x16_c2_bm_bist.v   RM_IHPSG13_1P_256x32_c2_bm_bist.v
```
Stage B then adds 17: `mda_spatial mda_cfg_unit mda_events mda_doorbell mda_sleep mda_timer mda_io mda_pins mda_pin_in mda_pin_cfg mda_pin_watch mda_pin_out mda_engine mda_eng_sched mda_eng_shift mda_loader mda_crc16`.

## 3. Package contents (`mda_pkg`)

| Group | Names | Meaning |
|---|---|---|
| Sizes | `NUM_THREADS` = 3, `DATA_WIDTH` = 32, `INSTR_WIDTH` = 16, `REG_ADDR_WIDTH` = 3, `NUM_REGS`, `FLAGS_WIDTH` = 16 | Datapath sizes |
| Instruction memory | `IMEM_ADDR_WIDTH` = 10, `IMEM_SIZE_HALFWORDS` | Halfword addresses, 1024 x 16 macro |
| Data memory | `DMEM_ADDR_WIDTH` = 8, `DMEM_SIZE_WORDS`, `DMEM_SIZE_BYTES`, `DMEM_BYTE_ADDR_WIDTH` | Word index width, 256 x 32 macro (1 KB) |
| Types | `Word`, `Instruction`, `PcAddr`, `RegAddr`, `ThreadSel`, `Flags`, `DmemWordAddr`, `Cause` | Typedef'd logic vectors. `ThreadSel` is a one-hot thread select |
| Constants | `NOP_INSTR` (`jnl 0`), `ILLEGAL_INSTR` | Fill values for tests |
| Decode classes | `AluOp` / `ALU_*`, `BrType` / `BR_*`, `MemOp` / `MEM_*`, `COND_ANY` / `COND_ALL` | `ALU_*` values equal the RR funct codes. `ALU_PASSB` and `ALU_LUI` (`{B[7:0], A[23:0]}`) complete the set |
| Stage B names | `WATCH_*`, `OSRC_*`, `OWN_*`, `PINCFG_*`, `ENGCTL_*`, `LDR_*`, pin grouping | Fixed in advance, unused in Stage A |
| Build variants | `SAMPLE_COMP_DEFAULT`, `PIN_INVERT_DEFAULT`, `ENG_GAPLESS_DEFAULT` | Default 0. Top-level modules expose them as parameters |

`FLAG_*` and `CAUSE_*` are not defined in `mda_pkg`. `mda_isa_pkg` holds opcode and funct constants (typed with `OpCode`, `Funct3` and `Funct2`, plus `RpinMode` and `CfgTarget`), reserved-field masks, flag indices and fault causes, generated from `tools/isa/isa.yaml` and marked do-not-edit. `tools/isa/check_names.py` verifies that the two packages share no identifier and that the ALU codes match the funct codes.

## 4. Port lists

All modules have `clk` (and `rst_n` where there is reset state). A one-hot vector is written `t[2:0]`. Control signals cross module boundaries as individual vectors, not packed structs (support for structs on ports in the flow's Yosys has not been verified).

### `mda_sched`
Three-flop one-hot ring plus a valid flop. Nothing else.

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk`, `rst_n` | in | 1 | Clock and reset |
| `run` | in | 1 | Threads released. While low the ring holds at its reset state (thread 0 in IF) |
| `if_t` | out | `ThreadSel` | One-hot thread in IF. Rotates thread 0, 1, 2 every cycle while `run` is high |
| `id_t` | out | `ThreadSel` | One-hot thread in ID. Wiring of `if_t`: `{if_t[0], if_t[2], if_t[1]}` |
| `ex_t` | out | `ThreadSel` | One-hot thread in EX. Wiring of `if_t`: `{if_t[1], if_t[0], if_t[2]}` |
| `id_v` | out | 1 | The ID stage holds a real instruction. `run` delayed by one cycle, reset low |

`ex_v` is held by `mda_id_ex`. Properties for the formal check: each of the three vectors is one-hot in every cycle, the three vectors name three different threads, and the ring advances every cycle while `run` is high.

### `mda_fetch` (contains the three PCs)
| Port | Dir | Width | Description |
|---|---|---|---|
| `go` | in | 1 | Load the entry PCs and start |
| `entry_pc` | in | 3*IMEM_ADDR_WIDTH | Entry PC of each thread |
| `if_t`, `ex_t` | in | 3 each | From `mda_sched` |
| `ex_pc_we`, `ex_pc_val` | in | 1, IMEM_ADDR_WIDTH | Override from EX (taken jump) |
| `imem_addr` | out | IMEM_ADDR_WIDTH | `pc[if_t]`, to `mda_imem` |
| `ex_pc` | out | IMEM_ADDR_WIDTH | `pc[ex_t]` = instruction address + 1 |

### `mda_decoder`, `mda_suffix`, `mda_imm_gen`
The ports of these three blocks, the immediate formats, the decoding rules and the draft decode matrix are specified in `Decoder_Interface.md`, which supersedes the proposal that was listed here. In outline: `mda_decoder` is a combinational function of `instr`, `suffix_pend` and `suffix_rd`. `mda_suffix` holds the per-thread suffix state (D4). `mda_imm_gen` builds the 32-bit immediate from `instr`, `imm_sel`, `rs1_data` (only for `lui`) and `suffix_imm8`.

### `mda_regfile`
| Port | Dir | Width | Description |
|---|---|---|---|
| `id_t` | in | 3 | Bank to read (one-hot) |
| `ra_idx`, `rb_idx` | in | 3 each | |
| `ra_data`, `rb_data` | out | 32 each | |
| `ex_t` | in | 3 | Bank for the EX write |
| `w_ex_we`, `w_ex_idx`, `w_ex_data` | in | 1, 3, 32 | |
| `if_t` | in | 3 | Bank for the load-return write |
| `w_ld_we`, `w_ld_idx`, `w_ld_data` | in | 1, 3, 32 | |

No reset on the registers (the spec leaves them uninitialized), so the module has no `rst_n` port (D10). Add an assertion that `ex_t` and `if_t` banks never write in the same cycle with the same bank (they cannot, by D1).

### `mda_id_ex`
ID/EX pipeline register. Inputs carry the prefix `id_`, outputs the prefix `ex_`, and the names follow the decoder outputs.

| Group | Signals |
|---|---|
| Valid | `id_v` in, `ex_v` out. The only reset state. `ex_v` follows `id_v` one cycle later |
| Raw word | `instr` (16). For the trace, the `jof` flag number, the `joc` invert bit and the Stage B fields |
| Operands | `rs1_data`, `rs2_data` (store data), `imm` (32 each) |
| Decoder outputs | `rd_addr`, `reg_write`, `alu_op`, `use_imm`, `fwd_imm`, `res_sel`, `f_u_alu`, `illegal`, `br_type`, `br_jof_inv`, `br_joc_all`, `mem_op`, `mem_byte`, `sp_valid`, `sp_op` |

Not registered: `rs1_addr`, `rs2_addr` and `lli_first`, which are consumed in ID. About 138 payload flops plus `ex_v`. The payload is not reset (D10), so every consumer qualifies it with `ex_v`.

### `mda_alu`
| Port | Dir | Width | Description |
|---|---|---|---|
| `op` | in | 4 | |
| `a`, `b` | in | 32 each | |
| `y` | out | 32 | |
| `z`, `n` | out | 1 each | Derived from `y` for every operation: `z = ~(\|y)`, `n = y[31]` |
| `c`, `c_upd` | out | 1 each | Carry or shifted-out bit, and whether the operation updates `C`: high for add and for a shift by a nonzero amount, low for every other operation |

For `cmp` and `cmpa`, `y` is the three-way result: bits `[31:1]` are `lt` and bit 0 is `lt | ~eq`, so `y` is all ones when less, `0` when equal and `1` when greater. The flags then need no special case.

There is no separate shifter module: the shifts are done inside `mda_alu` with a 33-bit shift that also yields the carry.

### `mda_cond`
Flag-mask condition, shared with `waitev` in Stage B. Combinational, with no knowledge of any instruction.

| Port | Dir | Type | Description |
|---|---|---|---|
| `flags` | in | `Flags` | Flags of the thread in EX |
| `mask` | in | `Flags` | One-hot flag select for `jof`, the register mask (`rs1_data[15:0]`) for `joc` |
| `all_mode` | in | 1 | 1: all flags in the mask must be set. 0: any flag in the mask |
| `inv` | in | 1 | Invert the result |
| `hit` | out | 1 | `(all_mode ? ((flags & mask) == mask) : |(flags & mask)) ^ inv` |

Test point: an empty mask with `all_mode` (vacuously true), and the four combinations with `inv`.

### `mda_branch_unit`
Owns all of the control flow except the adder itself: the taken decision (with `mda_cond`), the select bits of the PC adder in `mda_pc`, the PC offset, and the link value. Combinational, one instance shared by the three threads. It contains an instance of `mda_cond`.

| Port | Dir | Type | Description |
|---|---|---|---|
| `ex_v` | in | 1 | The EX stage holds a real instruction. All outputs are inactive when low |
| `br_type` | in | `BrType` | Jump kind, from `mda_id_ex` |
| `br_jof_inv` | in | 1 | `jof` invert variant |
| `br_joc_all` | in | 1 | `joc` all-of or any-of |
| `instr` | in | `Instruction` | Raw EX word: the `jof` flag number is `instr[15:12]`, the `joc` invert bit is `instr[15]`, and the offset fields below |
| `flags` | in | `Flags` | Flags of the thread in EX |
| `rs1_data` | in | `Word` | `joc` flag mask in the low 16 bits |
| `ex_pc` | in | `PcAddr` | PC of the thread in EX, selected from the three PCs by the wrapper |
| `taken` | out | 1 | The jump is taken (trace and PC controls) |
| `pc_in1` | out | 1 | To `mda_pc`: 1 selects `rs1` as the base, 0 selects the PC |
| `pc_in2` | out | 1 | To `mda_pc`: 1 selects `pc_offset`, 0 selects +1 |
| `pc_cin` | out | 1 | To `mda_pc`: carry-in, high for taken PC-relative jumps |
| `pc_offset` | out | `PcAddr` | To `mda_pc.imm_in`: the offset below, sign-extended to the PC width |
| `link` | out | `PcAddr` | `ex_pc + 1`, to `mda_wb` |

| Case | `pc_in1` | `pc_in2` | `pc_cin` | `taken` |
|---|---|---|---|---|
| Not a jump, not taken, or `ex_v` low | 0 | 0 | 0 | 0 |
| Taken `jmp`, `jnl`, `jof`, `joc` (target `PC + 1 + offset`) | 0 | 1 | 1 | 1 |
| `jrg` (always taken, target `rs1 + imm`) | 1 | 1 | 0 | 1 |

So `pc_in1 = ex_v & (br_type == BR_JRG)`, `pc_in2 = taken` and `pc_cin = taken & (br_type != BR_JRG)`.

| `br_type` | `pc_offset` |
|---|---|
| `BR_JMP` | `instr[12:5]`, 8 bits, sign-extended |
| `BR_JNL` | `instr[15:6]`, 10 bits |
| `BR_JOF` | `instr[11:6]`, 6 bits, sign-extended |
| `BR_JOC` | `{instr[14:13], instr[9:6]}`, 6 bits, sign-extended |
| `BR_JRG` | `instr[9:5]`, 5 bits, sign-extended |
| other | 0 |

`taken` is always 1 for `jmp`, `jnl` and `jrg`, and `hit` from `mda_cond` for `jof` and `joc` (mask `16'h0001 << instr[15:12]` with `all_mode = 0` and `inv = br_jof_inv` for `jof`, mask `rs1_data[15:0]` with `all_mode = br_joc_all` and `inv = instr[15]` for `joc`). The wrapper forms `pc_en = ex_v & ex_t[t]` for each thread's PC.

These rules were checked against the specification by driving `mda_pc` over 30,000 random cases covering every jump kind, both outcomes, non-jump words and `ex_v` low.

### `mda_flags`
Inputs: `ex_t`, `ex_v`, `zn_we`, `z_in`, `n_in`, `c_we`, `c_in`. Output: `flags_ex[15:0]` (flags of the thread in EX). Z/N/C only in Stage A.

### `mda_lsu`
Load/store unit. The effective address is the ALU result (`rs1 + imm`, with word offsets already scaled by the immediate generator), so the unit has no adder. The load-return registers live here.

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk`, `rst_n` | in | 1 | Clock and reset |
| `ex_v` | in | 1 | The EX stage holds a real instruction |
| `mem_op` | in | `MemOp` | None, load, store |
| `mem_byte` | in | 1 | Byte (1) or word (0) access |
| `addr` | in | `Word` | Effective byte address (the ALU result) |
| `store_data` | in | `Word` | `rs2` value |
| `rd_addr` | in | `RegAddr` | Destination of a load |
| `dm_rdata` | in | `Word` | Data memory read data, valid the cycle after a load is issued |
| `dm_en` | out | 1 | To `mda_dmem.core_en`. Low on a fault |
| `dm_we` | out | 1 | `core_we`: 1 for a store |
| `dm_addr` | out | `DmemWordAddr` | Word index, `addr[DMEM_ADDR_WIDTH+1:2]` |
| `dm_wdata` | out | `Word` | Word store: `store_data`. Byte store: the byte replicated into all four lanes |
| `dm_wstrb` | out | 4 | Word store: `4'b1111`. Byte store: `4'b0001 << addr[1:0]` |
| `fault` | out | 1 | A faulting access in EX |
| `fault_cause` | out | `Cause` | `CAUSE_MISALIGNED` or `CAUSE_OUT_OF_BOUNDS` |
| `ld_valid` | out | 1 | A load result is available (registered, reset low) |
| `ld_rd` | out | `RegAddr` | Registered `rd_addr` of that load |
| `ld_data` | out | `Word` | Aligned and zero-extended load data. 0 for a faulting load |

Faults: misaligned is a word access with `addr[1:0] != 0`. Out of bounds is any of `addr[31:DMEM_BYTE_ADDR_WIDTH]` set. A faulting store is suppressed (`dm_en` low), and a faulting load still produces a result, which is 0. All outputs are qualified by `ex_v`. Registered at the end of EX: `ld_valid` (reset), and the payload `ld_rd`, the byte flag, `addr[1:0]` and the fault flag, which `ld_data` uses when the memory data arrives. Byte loads select lane `addr[1:0]` (little-endian) and zero-extend. The cause when both faults apply must be checked against `Events.md`.

### `mda_wb`
Selects the EX result and forms the two register write requests. Combinational.

| Port | Dir | Type | Description |
|---|---|---|---|
| `ex_v`, `reg_write`, `sp_valid` | in | 1 each | EX qualifier and decoder controls |
| `rd_addr` | in | `RegAddr` | Destination register |
| `res_sel` | in | `ResSel` | `RES_ALU`, `RES_LINK` or `RES_SP` |
| `alu_result` | in | `Word` | ALU output or forwarded immediate |
| `link` | in | `PcAddr` | Link value from `mda_branch_unit`, zero-extended to 32 bits |
| `sp_result` | in | `Word` | Stage B result. Tie to 0 in Stage A |
| `ld_valid`, `ld_rd`, `ld_data` | in | 1, `RegAddr`, `Word` | Load return from the LSU |
| `w_ex_we`, `w_ex_addr`, `w_ex_data` | out | | EX write request, for the bank of the thread in EX |
| `w_ld_we`, `w_ld_addr`, `w_ld_data` | out | | Load-return write request, for the bank of the thread in IF. A pass-through of the load return |

Parameter `HAS_STAGE_B` (default 0): when 0, the EX write is masked for Stage B instructions (`pull`, `rpin`), which execute as no-ops in Stage A. `w_ex_we = ex_v & reg_write & (HAS_STAGE_B | ~sp_valid)`.

### `mda_imem`
| Port | Dir | Width | Description |
|---|---|---|---|
| `f_en`, `f_addr` | in | 1, IMEM_ADDR_WIDTH | Fetch request |
| `f_data` | out | 16 | Valid the next cycle |
| `l_we`, `l_addr`, `l_data` | in | 1, IMEM_ADDR_WIDTH, 16 | Loader / testbench write port (priority over fetch) |

With `` `ifdef MDA_SRAM_MACRO `` it instantiates `RM_IHPSG13_1P_1024x16_c2_bm_bist` (`A_MEN = f_en | l_we`, `A_WEN = l_we`, `A_REN = f_en & ~l_we`). Otherwise it instantiates `mda_sram_sim`.

### `mda_dmem`
| Port | Dir | Width | Description |
|---|---|---|---|
| `core_en`, `core_we`, `core_addr` | in | 1, 1, DMEM_ADDR_WIDTH | Core port, from the LSU |
| `core_wdata` | in | 32 | Store data, already placed in its byte lane(s) |
| `core_wstrb` | in | 4 | Byte strobe, bit n writes byte lane n. Expanded inside to the per-bit mask of the macro |
| `core_rdata` | out | 32 | Valid the cycle after a read |
| `ld_we`, `ld_addr`, `ld_wdata` | in | 1, DMEM_ADDR_WIDTH, 32 | Loader write port, full word, priority over the core |

Same macro-or-simulation arrangement, with `RM_IHPSG13_1P_256x32_c2_bm_bist`.

### `mda_sram_sim`
Parameters `AW`, `DW`. One port, synchronous read with a registered output, per-bit write mask (1 writes), write-through if both enables are set. It must behave like the macro in the cases the tests use, and nothing more.

### `mda_sync`
| Port | Dir | Width | Description |
|---|---|---|---|
| `clk` | in | 1 | |
| `d` | in | `WIDTH` | Asynchronous input |
| `q` | out | `WIDTH` | `d` synchronized by two flops. No reset |

Parameter `WIDTH`. Used for the reset input in `mda_tt_top` (both edges synchronized, so assertion takes up to two cycles) and for the Stage B pin inputs.

### `mda_core`
Ports: `clk`, `rst_n`, `go`, `entry_pc[3*IMEM_ADDR_WIDTH]`, the IMEM interface (`imem_addr`, `imem_data`, `imem_en`), the DMEM interface (the `dm_*` signals above), and the trace port (D9). It instantiates `mda_sched`, `mda_fetch`, `mda_decoder`, `mda_suffix` (selected with `id_t`), `mda_imm_gen`, `mda_regfile`, `mda_id_ex`, `mda_alu`, `mda_branch_unit`, `mda_flags`, `mda_lsu` and `mda_wb`.

### `mda_top`
`mda_core` + `mda_imem` + `mda_dmem`, with the loader write ports and the trace exposed as plain ports. Stage B adds the I/O and event blocks.

### `mda_tt_top`
The `tt_um_<yourname>_mda` wrapper: Tiny Tapeout pin mapping, reset synchronizer, the trace hash on `uo_out` (D8), unused inputs consumed. Check the top module name against `info.yaml`.

## 5. Verification for Stage A

- **Decoder:** exhaustive over all 65,536 words against the reference model (encoded legal fields, every illegal encoding, reserved bits). Suffix words are checked as data, not instructions.
- **Lockstep:** random programs on all three threads, compared event by event over the trace port. Cover: every instruction at its range limits, `lli` corner cases from D4, PC wrap, byte lanes for loads and stores, misaligned and out-of-bounds loads and stores (store suppressed, load returns 0), a store by one thread followed by a load by another, and illegal words as no-ops.
- **Random initial state:** run each program twice with different random initial registers and DMEM contents and require identical traces for everything the program initializes.
- **Formal (small modules only):** `mda_sched` (exactly one thread per stage, rotation every cycle), and an assertion that the two regfile write banks never coincide.

## 6. Risks to plan for

- **Two macros in one hardening run.** The stripe script from the dry run hard-codes one macro name and one LEF. It needs to loop over the two macros (1024x16 and 256x32), and `config.json` needs an instance entry and `PDN_MACRO_CONNECTIONS` lines for each. Expect to spend a day on this in Stage A.
- **Instance names.** The macro instance paths in `config.json` must match the flattened hierarchy (for example `u_top.u_imem.u_sram`). Renaming a wrapper breaks the flow.
- **Macro views for the 256x32.** The PDK library file names have not been checked (the dry run used only the 1024x16). A wrong name fails as "file not found".
- **Macro timing at slow corner.** The data macro's clock-to-out is the longest single delay in the load-return path (macro + lane mux + bank write mux), estimated around 10 ns. Check it in the first report.
- **ID-stage path.** The longest path is IMEM macro output + decode + register read, estimated around 14 ns of 20 ns at the slow corner. If the first timing report shows it is too tight, move most of the decode into EX and register the raw instruction bits at the end of ID (3 stages are kept, since the register-read indices come straight from the instruction bits), or lower the clock to 40 MHz, before considering anything else.
- **Decoder fan-out.** The decoder drives many control wires into `mda_id_ex`. If the ID path is the critical one, the fix is to reduce decoder depth (predecode in the ISA table), not to add a stage.

## 7. Next steps

1. `isa.yaml`, the generated `mda_isa_pkg` and the golden encoding vectors: done (`tools/isa/`).
2. In order: `mda_pkg`, `mda_sync`, `mda_sched`, `mda_regfile`, `mda_alu`, `mda_decoder`, then the rest of the pipeline. Test each leaf module with its own small bench before integration.
3. A first hardening run of the Stage A core with both macros.