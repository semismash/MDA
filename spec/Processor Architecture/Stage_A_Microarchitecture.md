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

The load-return thread is always **the thread currently in IF**, which is a useful invariant to assert. The LSU still registers the thread tag of the load (`ld_thread`) together with the registered `rd` index, byte lane and byte flag from the load's EX cycle.

Generating the load address in ID instead would need only one write port, but it was rejected: the path would be IMEM output (up to about 7.4 ns slow) + register read + 32-bit add + bounds check into the DMEM macro, which estimates near 16-17 ns of a 20 ns budget. The banked design keeps every path under about 14 ns.

### D2. No IF/ID register module.
The IMEM macro's registered output is the IF/ID stage register: the instruction word is valid for exactly cycle k+1, and the decoder reads it straight from the macro. `mda_if_id.sv` is therefore not needed. Only `mda_id_ex` is a real pipeline register. Registering the instruction word and decoding a cycle later is not possible: that adds a stage **before** EX, so EX would land in the same cycle as the thread's next fetch, a taken branch could not update the PC in time, and every taken branch would cost that thread a 3-cycle bubble, breaking the spec's zero-penalty rule. (A stage **after** EX is fine, and the load return in D1 is effectively one.) If a named IF/ID stage is wanted for readability, `mda_if_id.sv` can be kept as a thin module with no registers (thread id, valid bit after `go`, suffix state).

The ID-stage path is then macro clock-to-out (6.4-7.4 ns slow) + decode + register read + operand mux, estimated at about 14 ns. The register-read indices come straight from instruction bits (`rs1` at `[12:10]`, `rs2` at `[9:7]`), with a 1-bit mux for `lui` (reads `rd`) and for the `lli` second slot, so they do not wait for the decoder.

### D3. PC convention.
`pc[t]` holds the address of the **current** instruction of thread `t` (the one in IF, then ID, then EX). It changes only at the end of that thread's EX.
- IF (cycle k): thread `t` fetches `pc[t]`.
- EX (cycle k+2): `mda_pc` computes `next = A + B + carry`, with `A` = the PC or `rs1`, `B` = +1 or the offset, and a carry-in. Sequential flow is `PC + 1 + 0`, relative jumps are `PC + offset + 1` (offsets count from PC + 1) and `jrg` is `rs1 + imm`. `mda_branch_unit` sets the three selects, and the register updates with `pc_en = ex_v & (ex_thread == t)`.
- The link value is `ex_pc + 1`, computed once in `mda_branch_unit` from the PC of the thread in EX, which `mda_fetch` selects by `ex_thread`.
- The new PC is fetched in IF at k+3. No instruction address travels down the pipeline.
- `waitev` (Stage B) holds a thread with `B` = offset 0 and no carry, so `next = PC`.

IF reads the PC of the IF thread and EX updates the PC of the EX thread. These are different threads in every cycle, so there is no conflict.

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

### D9. Trace port (always present, observed in tests, hashed at the TT wrapper).
Do not use `ifdef` for this: synthesis removes the unused logic anyway, and the port set stays identical in simulation and formal. The core exposes one record per instruction in EX (combinational, valid for that cycle) and one record per load return: `tr_valid`, `tr_thread`, `tr_pc` (address of the instruction), `tr_instr`, `tr_rd_we`, `tr_rd`, `tr_wdata`, `tr_flags` (flags of the thread as seen by this instruction), `tr_zn_we`, `tr_z`, `tr_n`, `tr_c_we`, `tr_c` (the flag updates), `tr_taken`, `tr_fault`, `tr_fault_cause`, `tr_mem_addr` (effective address; the strobe and data are the `dm_*` ports); and `tr_ld_valid`, `tr_ld_thread`, `tr_ld_rd`, `tr_ld_data` for the load return one cycle later.

### D10. Reset policy.

`rst_n` resets control state only. Data storage is never reset. A flop is reset when a wrong value after reset would change what the machine does. Register files, memories and pipeline payload are not reset.

**Distribution.** `rst_n` is active low. `mda_tt_top` passes the pin through the 2-flop synchronizer (`mda_sync`, `W` = 1). The synchronized signal drives the asynchronous reset input of every resettable flop (`always_ff @(posedge clk or negedge rst_n)`). Assertion therefore reaches the design up to two clock cycles after the pin, and release is synchronous to `clk`. Reset is held for at least three cycles on the board and at least five in testbenches. Resettable control flops and unreset payload flops are written in separate `always_ff` blocks, because the reset branch of a block resets every register assigned in it.

**Sequence.** Reset leaves `run` low and the design idle. A testbench or the loader then fills IMEM and DMEM and pulses `go` for one cycle. `go` loads the three entry PCs and sets `run`. Thread 0 is in IF in the first cycle with `run` high, and the first valid instruction reaches EX two cycles later.

| State | Module | Reset | Reason |
|---|---|---|---|
| `run` | `mda_core` | Yes, low | Nothing executes until `go` |
| Slot counter | `mda_sched` | Yes, thread 0 in IF | All threads start in a known slot |
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

Compared with the earlier file tree: `mda_if_id` removed (D2), `mda_spatial` moved to Stage B, `mda_shifter` dropped (the shifts live in `mda_alu`), `mda_suffix` and `mda_imm_gen` split out of the decoder, `mda_fault` added, and the register file split into the one-bank `mda_regfile` and the three-bank wrapper `mda_regbank`. That makes **26 `src/` files plus the 2 macro stubs for Stage A**, listed in `rtl.f` (the single source for `info.yaml` and `test/Makefile`, synchronized by `tools/sync_sources.py`):

```
mda_pkg  mda_isa_pkg  mda_tt_top  mda_top  mda_core  mda_ex  mda_sched  mda_fetch  mda_pc  mda_id_ex  mda_decoder  mda_suffix  mda_imm_gen  mda_fault
mda_regbank  mda_regfile  mda_alu  mda_branch_unit  mda_cond  mda_flags  mda_lsu  mda_wb
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
| Types | `Word`, `Instruction`, `PcAddr`, `RegAddr`, `Thread`, `ThreadSel`, `Flags`, `DmemWordAddr`, `Cause` | Typedef'd logic vectors. `Thread` is the 2-bit thread number (`THREAD_0` to `THREAD_2`, 3 unused) carried with each instruction. `ThreadSel` is a one-hot thread select, decoded from it where per-thread enables are needed |
| Constants | `NOP_INSTR` (`jnl 0`), `ILLEGAL_INSTR` | Fill values for tests |
| Decode classes | `AluOp` / `ALU_*`, `BrType` / `BR_*`, `MemOp` / `MEM_*`, `COND_ANY` / `COND_ALL` | `ALU_*` values equal the RR funct codes. `ALU_PASSB` and `ALU_LUI` (`{B[7:0], A[23:0]}`) complete the set |
| Stage B names | `WATCH_*`, `OSRC_*`, `OWN_*`, `PINCFG_*`, `ENGCTL_*`, `LDR_*`, pin grouping | Fixed in advance, unused in Stage A |
| Build variants | `SAMPLE_COMP_DEFAULT`, `PIN_INVERT_DEFAULT`, `ENG_GAPLESS_DEFAULT` | Default 0. Top-level modules expose them as parameters |

`FLAG_*` and `CAUSE_*` are not defined in `mda_pkg`. `mda_isa_pkg` holds opcode and funct constants (typed with `OpCode`, `Funct3` and `Funct2`, plus `RpinMode` and `CfgTarget`), reserved-field masks, flag indices and fault causes, generated from `tools/isa/isa.yaml` and marked do-not-edit. `tools/isa/check_names.py` verifies that the two packages share no identifier and that the ALU codes match the funct codes.

## 4. Port lists

All modules have `clk` (and `rst_n` where there is reset state). A one-hot vector is written `t[2:0]`. Control signals cross module boundaries as individual vectors, not packed structs (support for structs on ports in the flow's Yosys has not been verified).

### `mda_sched`
One instance for the whole core: a slot counter and a registered ID thread. The thread in EX is not produced here, it is the tag `ex_thread` that travels down the pipeline in `mda_id_ex`.

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk`, `rst_n` | in | 1 | Clock and reset |
| `run` | in | 1 | Threads released. While low the counter is held at thread 0 |
| `if_thread` | out | `Thread` | Thread in IF. Counts 0, 1, 2, 0, ... every cycle while `run` is high |
| `id_thread` | out | `Thread` | Thread in ID: the thread that was in IF in the previous cycle. Payload, qualified by `id_v` |
| `id_v` | out | 1 | The ID stage holds a real instruction. `run` delayed by one cycle |

Reset sets the counter to thread 0 and `id_v` low. The counter also returns to thread 0 whenever `run` is low, so every start is aligned the same way. Timeline after `run` rises:

| Cycle | IF | ID | EX |
|---|---|---|---|
| 0 | T0 | empty | empty |
| 1 | T1 | T0 | empty |
| 2 | T2 | T1 | T0 |
| 3 | T0 | T2 | T1 |

The wrapper decodes `Thread` to the one-hot `ThreadSel` wherever it needs per-thread enables (PC enables, flag gating, register bank writes, the suffix buffer select). The thread tag in `mda_id_ex` and the schedule carry the same information, so the lockstep and formal checks assert that `ex_thread` equals the schedule.

### `mda_fetch`
The three program counters (three `mda_pc` instances), the IF address mux and the EX PC mux. All three PCs see the same adder controls, and only the one whose thread is in EX is enabled.

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk`, `rst_n` | in | 1 | Clock and reset |
| `go` | in | 1 | Load the three entry points |
| `entry_pc0`, `entry_pc1`, `entry_pc2` | in | `PcAddr` | Entry point of each thread |
| `if_thread` | in | `Thread` | Thread in IF |
| `ex_v`, `ex_thread` | in | 1, `Thread` | EX qualifier and thread tag, give the PC enables |
| `pc_in1`, `pc_in2`, `pc_cin`, `pc_offset` | in | 1, 1, 1, `PcAddr` | From `mda_branch_unit` |
| `rs1_pc` | in | `PcAddr` | Low bits of `rs1`, the `jrg` base |
| `if_pc` | out | `PcAddr` | PC of the thread in IF, the instruction memory address |
| `ex_pc` | out | `PcAddr` | PC of the thread in EX, the address of the instruction in EX |

### `mda_pc`
One thread's program counter and its adder, `next = A + B + carry`.

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk`, `rst_n` | in | 1 | Clock and reset (the PC resets to 0) |
| `load_en`, `entry_pc` | in | 1, `PcAddr` | Entry point load, with priority over the update |
| `pc_en` | in | 1 | Update enable, high when this thread's instruction is in EX |
| `pc_in1`, `rs1_in` | in | 1, `PcAddr` | `A`: 1 selects `rs1_in`, 0 selects the PC |
| `pc_in2`, `imm_in` | in | 1, `PcAddr` | `B`: 1 selects `imm_in`, 0 selects +1 |
| `pc_cin` | in | 1 | Carry-in |
| `pc_out` | out | `PcAddr` | The PC |

### `mda_decoder`, `mda_suffix`, `mda_imm_gen`
The ports of these three blocks, the immediate formats, the decoding rules and the draft decode matrix are specified in `Decoder_Interface.md`, which supersedes the proposal that was listed here. In outline: `mda_decoder` is a combinational function of `instr`, `suffix_pend` and `suffix_rd`. `mda_suffix` holds the per-thread suffix state (D4). `mda_imm_gen` builds the 32-bit immediate from `instr`, `imm_sel`, `rs1_data` (only for `lui`) and `suffix_imm8`.

### `mda_regfile`
One thread's register file: 8 registers, two read ports, one write port, no reset (the spec leaves the registers uninitialized, D10).

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk` | in | 1 | Clock |
| `r_addr1`, `r_addr2` | in | `RegAddr` | Read addresses |
| `w_addr`, `w_data`, `w_enable` | in | `RegAddr`, `Word`, 1 | Write port |
| `r_data1`, `r_data2` | out | `Word` | Read data (combinational) |

### `mda_regbank`
Three `mda_regfile` banks, one per thread. Reads select the bank of the ID thread, writes are routed by the thread tags (`w_ex_thread`, `w_ld_thread`). The EX write and the load-return write never hit the same bank in one cycle (a load returns while its thread is in IF, not EX), so the EX write simply has priority. Thread value 3 is unused and reads bank 0.

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk` | in | 1 | Clock |
| `rd_thread`, `r_addr1`, `r_addr2` | in | `Thread`, `RegAddr` | Read side (ID stage) |
| `w_ex_we`, `w_ex_thread`, `w_ex_addr`, `w_ex_data` | in | | EX write |
| `w_ld_we`, `w_ld_thread`, `w_ld_addr`, `w_ld_data` | in | | Load-return write |
| `r_data1`, `r_data2` | out | `Word` | Read data |

### `mda_id_ex`
ID/EX pipeline register. Inputs carry the prefix `id_`, outputs the prefix `ex_`, and the names follow the decoder outputs.

| Group | Signals |
|---|---|
| Valid | `id_v` in, `ex_v` out. The only reset state. `ex_v` follows `id_v` one cycle later |
| Thread | `id_thread` in, `ex_thread` out (`Thread`). The one source for the thread in EX: write-back, jumps, flags, faults and the load return all use it |
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
Load/store unit. The effective address is the ALU result (`rs1 + imm`, with word offsets already scaled by the immediate generator), so the unit has no adder. The memory is a single-port macro with a fixed one-cycle read, so there is no handshake: a load issued in EX returns its data one cycle later, while the next thread is in EX.

| Port | Dir | Type | Description |
|---|---|---|---|
| `clk`, `rst_n` | in | 1 | Clock and reset (for the load-return registers) |
| `ex_v` | in | 1 | The EX stage holds a real instruction |
| `mem_op` | in | `MemOp` | None, load, store |
| `mem_byte` | in | 1 | Byte (1) or word (0) access |
| `addr` | in | `Word` | Effective byte address (the ALU result) |
| `store_data` | in | `Word` | `rs2` value |
| `rd_addr` | in | `RegAddr` | Destination of a load |
| `ex_thread` | in | `Thread` | Thread of the instruction in EX |
| `dm_rdata` | in | `Word` | Data memory read data, valid the cycle after the access |
| `dm_en` | out | 1 | To `mda_dmem.core_en`: `is_access & ~fault` |
| `dm_we` | out | 1 | `core_we`: 1 for a store |
| `dm_addr` | out | `DmemWordAddr` | Word index, `addr[DMEM_ADDR_WIDTH+1:2]` |
| `dm_wdata` | out | `Word` | Word store: `store_data`. Byte store: the byte repeated in all four lanes |
| `dm_wstrb` | out | 4 | Word store `4'b1111`, byte store `4'b0001 << addr[1:0]` (little-endian), otherwise 0 |
| `fault` | out | 1 | A faulting access in EX |
| `lsu_fault_type` | out | 1 | Low: misaligned. High: out of bounds. Misaligned wins when both apply |
| `ld_valid` | out | 1 | A load result is available (registered, reset low). A faulting load also returns |
| `ld_rd` | out | `RegAddr` | Registered destination of that load |
| `ld_thread` | out | `Thread` | Registered thread of that load |
| `ld_data` | out | `Word` | Selected byte (zero-extended) or word. 0 for a faulting load |

`is_access = ex_v & (|mem_op)`. Misaligned is a word access with `addr[1:0] != 0`. Out of bounds is any of `addr[31:DMEM_BYTE_ADDR_WIDTH]` set. A faulting store sends no request, so memory is unchanged. Registered at the end of EX: `ld_valid` (reset), and the payload `ld_rd`, `ld_thread`, the byte flag, `addr[1:0]` and the fault flag. The module was checked against a byte-addressable reference memory over random accesses (6,000 cycles, with misaligned, out-of-bounds, byte and word cases).

### `mda_wb`
Selects the EX result and forms the two register write requests. Combinational.

| Port | Dir | Type | Description |
|---|---|---|---|
| `ex_v`, `reg_write`, `sp_valid` | in | 1 each | EX qualifier and decoder controls |
| `ex_thread`, `ld_thread` | in | `Thread` | Thread of the EX instruction and of the load return |
| `rd_addr` | in | `RegAddr` | Destination register |
| `res_sel` | in | `ResSel` | `RES_ALU`, `RES_LINK` or `RES_SP` |
| `alu_result` | in | `Word` | ALU output or forwarded immediate |
| `link` | in | `PcAddr` | Link value from `mda_branch_unit`, zero-extended to 32 bits |
| `sp_result` | in | `Word` | Stage B result. Tie to 0 in Stage A |
| `ld_valid`, `ld_rd`, `ld_data` | in | 1, `RegAddr`, `Word` | Load return from the LSU |
| `w_ex_we`, `w_ex_addr`, `w_ex_data`, `w_ex_thread` | out | | EX write request. The thread tag selects the register bank |
| `w_ld_we`, `w_ld_addr`, `w_ld_data`, `w_ld_thread` | out | | Load-return write request. A pass-through of the load return, with its thread tag |

Parameter `HAS_STAGE_B` (default 0): when 0, the EX write is masked for Stage B instructions (`pull`, `rpin`), which execute as no-ops in Stage A. `w_ex_we = ex_v & reg_write & (HAS_STAGE_B | ~sp_valid)`.

### `mda_fault`
Fault collector: turns the fault sources of the EX instruction into the `ERR` and `OVR` updates of that thread's flags. Combinational. Stage B sources (bad `cfg`, bad pin access, bad engine launch, bad `waitev`) join here as more inputs with a priority.

| Port | Dir | Type | Description |
|---|---|---|---|
| `ex_v` | in | 1 | The EX stage holds a real instruction |
| `illegal` | in | 1 | From the decoder, via `mda_id_ex` |
| `lsu_fault`, `lsu_fault_type` | in | 1 each | From the LSU (type low: misaligned, high: out of bounds) |
| `err_now` | in | 1 | The `ERR` flag of the thread in EX (selected by the wrapper) |
| `u_err`, `f_err`, `f_errc` | out | 1, 1, `Cause` | Set `ERR` and latch the cause, only when `ERR` is clear (the cause of the first fault stays) |
| `u_ovr`, `f_ovr` | out | 1 each | Set `OVR` when a second fault arrives while `ERR` is set (`Events.md`) |

The outputs feed the `mda_flags` instance of the thread named by `ex_thread`, so the wrapper gates `u_err` and `u_ovr` with the decoded thread. A decoded-illegal instruction is a no-op and never has a memory access, so the decoder and LSU sources cannot fire together.

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

### `mda_ex`
The EX stage: `mda_alu`, `mda_branch_unit`, `mda_lsu`, `mda_fault`, `mda_wb` and the three `mda_flags` (only the flags of the thread in EX are updated, gated by `ex_thread`; the Stage B event inputs are tied off, with `f_osr_empty` high). Inputs are the `ex_*` signals of `mda_id_ex`, `ex_pc` and `dm_rdata`. Outputs: the PC controls (`pc_in1`, `pc_in2`, `pc_cin`, `pc_offset`), the data memory request (`dm_*`), the register write requests (`w_ex_*`, `w_ld_*`) and the trace fields (`tr_flags`, `tr_zn_we`, `tr_z`, `tr_n`, `tr_c_we`, `tr_c`, `tr_taken`, `tr_fault`, `tr_fault_cause`, `tr_mem_addr`).

### `mda_core`
Ports: `clk`, `rst_n`, `go` (a one-cycle pulse), `entry_pc0` to `entry_pc2`, the instruction memory interface (`imem_en`, `imem_addr`, `imem_data`), the data memory interface (`dm_en`, `dm_we`, `dm_addr`, `dm_wdata`, `dm_wstrb`, `dm_rdata`) and the trace port (D9). It holds the `run` flop (set by `go`, cleared by reset), the ID stage (decoder, suffix buffer, register read, immediate generator) and instantiates `mda_sched`, `mda_fetch`, `mda_regbank`, `mda_id_ex` and `mda_ex`. The instruction memory output is the IF/ID register (D2), and the Stage B `ex_sp_op` is left open.

### `mda_top`
`mda_core` + `mda_imem` + `mda_dmem`, with the loader write ports (`imem_ld_*`, `dmem_ld_*`, used while the threads are held) and the trace passed through as plain ports. Stage B adds the I/O and event blocks.

### `tt_um_mda` (`mda_tt_top.sv`)
The Tiny Tapeout wrapper: pin mapping, the reset synchronizer (`mda_sync`), a one-cycle `go` pulse in the first cycle after reset is released (entry points all 0, no loader in this harness), an 8-bit trace hash on `uo_out` that folds register writes, load returns, jumps, faults and the PC (D8), `uio_*` driven low and the unused inputs consumed. The module name must match `top_module` in `info.yaml`.

## 5. Verification for Stage A

Done, without a compiler (model-level, with the interpreter in `verif/`):
- **Decoder and immediate generator:** exhaustive over all 65,536 words and both suffix states against expectations derived from `isa.yaml`, with mutation checks.
- **Leaf modules:** `mda_alu` (60,000 random cases against an independent reference), `mda_lsu` (against a byte-addressable reference memory), `mda_fault` (exhaustive), `mda_sched`, `mda_branch_unit` (over every word, with the decoder in front), `mda_id_ex`, `mda_wb`.
- **Whole design, `verif/mda_e2e.py`:** the elaborated `mda_top` (core, memories, loader ports) runs assembled programs and is compared with the independent eval simulator on final registers, flags and the whole data memory. A directed three-thread program plus about 490 random three-thread programs (loops, byte and word accesses, `lli`, `jrg`, misaligned and out-of-bounds faults, with per-thread fault rates) all match. 25 injected plumbing bugs (wrong thread tags, bank routing, PC enables, flag gating, jump polarity) were each caught. `tt_um_mda` was also checked: reset synchronizer, a single `go` pulse, hash activity, mid-run reset.

Still to do:
- **Lint** with Verilator and a Yosys probe of the constructs used (`casez`, typed localparams, `import` at file scope), since nothing has been compiled yet.
- **Lockstep on the trace port** event by event, which needs the reference model to emit the same records (the end-to-end test compares final state only).
- **Random initial state twins:** run each program twice with different random initial registers and DMEM contents and require identical traces for everything the program initializes.
- **Formal (small modules only):** `mda_sched` (exactly one thread per stage, rotation every cycle), `ex_thread` equals the schedule, and the two regbank write ports never hit the same bank.

## 6. Risks to plan for

- **Two macros in one hardening run.** The stripe script from the dry run hard-codes one macro name and one LEF. It needs to loop over the two macros (1024x16 and 256x32), and `config.json` needs an instance entry and `PDN_MACRO_CONNECTIONS` lines for each. Expect to spend a day on this in Stage A.
- **Instance names.** The macro instance paths in `config.json` must match the flattened hierarchy (for example `u_top.u_imem.u_sram`). Renaming a wrapper breaks the flow.
- **Macro views for the 256x32.** The PDK library file names have not been checked (the dry run used only the 1024x16). A wrong name fails as "file not found".
- **Macro timing at slow corner.** The data macro's clock-to-out is the longest single delay in the load-return path (macro + lane mux + bank write mux), estimated around 10 ns. Check it in the first report.
- **ID-stage path.** The longest path is IMEM macro output + decode + register read, estimated around 14 ns of 20 ns at the slow corner. If the first timing report shows it is too tight, move most of the decode into EX and register the raw instruction bits at the end of ID (3 stages are kept, since the register-read indices come straight from the instruction bits), or lower the clock to 40 MHz, before considering anything else.
- **Decoder fan-out.** The decoder drives many control wires into `mda_id_ex`. If the ID path is the critical one, the fix is to reduce decoder depth (predecode in the ISA table), not to add a stage.

## 7. Next steps

1. Lint all of `src/`, then re-run `python3 verif/mda_e2e.py directed` and a fuzz batch after every fix.
2. Run `python3 tools/sync_sources.py` so `info.yaml` and `test/Makefile` follow `rtl.f`, set `top_module` to `tt_um_mda` (or rename the module), and remove `project.v` and the other stale files.
3. A first hardening run of the Stage A core with both macros (the second macro in `config.json` and the stripe script are the open items).