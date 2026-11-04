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

### D4. `lli` as two micro-operations.
The instruction word carries the upper byte `[23:16]`, and the suffix halfword carries `[15:0]`.
- Slot 1 (the `lli` itself): write `rd = imm8 << 16`.
- Slot 2 (the suffix): write `rd = rd | suffix`. The decoder treats the suffix word as raw data, not as an instruction, because `suffix_pend[t]` is set.
- Per-thread state: `suffix_pend` (1 bit) and `suffix_rd` (3 bits), 12 flops in total, kept in `mda_core`. The suffix slot reads `rd` through port A (`rs1_idx = suffix_rd`), ORs the zero-extended suffix with it in the ALU, writes it back, and **does not update flags** (`lli` sets none).
- A jump that lands on a suffix address finds `suffix_pend = 0` and decodes it as an ordinary instruction, as the spec requires.
- The alternative of holding `imm8` per thread costs 33 flops; the 12-flop version is preferred.

The checks to cover in tests: a flag-setting instruction right before `lli`, `lli` followed by a jump to its own suffix address, and `lli` as the last word before the PC wraps.

### D5. Flags.
Z, N, C live per thread in `mda_flags`. Instructions that set flags: `add xor and or cmp cmpa shl shr addi xori shli shri`. Nothing else does (`lbi`/`lli`/`lui`, loads, stores and jumps leave them alone). `C` is updated by `add`/`addi`, and by shifts only when the amount is not 0. A branch in EX reads the flags written 3 cycles earlier by the thread's previous instruction. Event flags join `mda_flags` in Stage B, so it exposes a 16-bit view from the start (bits above 2 read as 0).

### D6. Faults in Stage A.
The LSU produces `fault` and `fault_cause` (misaligned `000`, out of bounds `001`) and the decoder produces `illegal` (`110`). The faulting store is suppressed (`A_MEN` low), the faulting load returns 0, and illegal instructions execute as no-ops. Stage A only **exposes** the faults on the trace port. The `ERR` flag and cause latching arrive with `mda_events` in Stage B. Timing is never affected, as the spec requires.

### D7. Memory access details.
- Word index = `addr[DMEM_ADDR_WIDTH+1:2]`. Out of bounds if `addr[31:DMEM_ADDR_WIDTH+2] != 0`. Misaligned if `lw`/`sw` and `addr[1:0] != 0`.
- Byte store: `A_BM = 32'hFF << (8*addr[1:0])`, `A_DIN = {4{byte}}`. Word store: all-ones mask.
- Byte load: the lane is selected from the registered `addr[1:0]` of the load.
- IMEM macro: `A_MEN = 1`, `A_REN = 1` every cycle while running, `A_BM = 16'hFFFF`, `A_DLY = 1`, `A_BIST_* = 0`.
- Cross-thread visibility: a store at EX in cycle k is visible to any load whose address is issued from cycle k+1 onward, which is the soonest another thread can issue one.

### D8. Stage A needs a way to keep the logic alive for hardening.
With no loader and no pins, the synthesizer would remove most of the design. The Stage A `mda_tt_top` should expose a trace hash (an 8-bit XOR/rotate accumulator of EX results, mapped to `uo_out`), and the unused inputs should be consumed in the `_unused` idiom. Memory contents are unknown after reset (the macros have no reset), so the cores run garbage, which still exercises everything. Programs for simulation are loaded through the testbench. A real loader is Stage B.

### D9. Trace port (always present, left open at the TT wrapper).
Do not use `ifdef` for this: synthesis removes the unused logic anyway, and the port set stays identical in simulation and formal. Fields, all registered at the end of EX: `tr_valid`, `tr_t` (thread, one-hot), `tr_pc`, `tr_instr`, `tr_rd_we`, `tr_rd`, `tr_wdata`, `tr_flags_we`, `tr_flags`, `tr_taken`, `tr_next_pc`, `tr_mem_we`, `tr_mem_addr`, `tr_mem_wdata`, `tr_fault`, `tr_cause`; plus a second event for a load return one cycle later (`tr_ld_valid`, `tr_ld_t`, `tr_ld_rd`, `tr_ld_data`). This is the interface that the lockstep checker against the reference model compares.

## 2. Updated Stage A file list

Compared with the earlier file tree: `mda_if_id` removed (D2), `mda_pc` merged into `mda_fetch` (a standalone PC module would be a thin wrapper), `mda_ex` removed (pure wiring, `mda_core` instantiates its children directly), and `mda_spatial` moved to Stage B. That makes **21 `src/` files plus the 2 macro stubs for Stage A**:

```
mda_pkg  mda_isa_pkg  mda_tt_top  mda_top  mda_core  mda_sched  mda_fetch  mda_id_ex  mda_decoder
mda_regfile  mda_alu  mda_shifter  mda_branch_unit  mda_cond  mda_flags  mda_lsu  mda_wb
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

`FLAG_*` and `CAUSE_*` are not defined in `mda_pkg`. `mda_isa_pkg` holds opcode and funct constants, reserved-field masks, flag indices and fault causes, generated from `tools/isa/isa.yaml` and marked do-not-edit. `tools/isa/check_names.py` verifies that the two packages share no identifier and that the ALU codes match the funct codes.

## 4. Port lists

All modules have `clk` (and `rst_n` where there is reset state). A one-hot vector is written `t[2:0]`. Control signals cross module boundaries as individual vectors, not packed structs (support for structs on ports in the flow's Yosys has not been verified).

### `mda_sched`
| Port | Dir | Width | Description |
|---|---|---|---|
| `run` | in | 1 | Hold the ring until threads are released |
| `if_t`, `id_t`, `ex_t` | out | 3 each | One-hot thread in each stage |
| `id_v`, `ex_v` | out | 1 each | Stage holds a real instruction (low for the first cycles after `run` rises) |

A 3-bit one-hot ring, nothing else. Keep it small so formal can prove "exactly one thread per stage, every stage rotates every cycle".

### `mda_fetch` (contains the three PCs)
| Port | Dir | Width | Description |
|---|---|---|---|
| `go` | in | 1 | Load the entry PCs and start |
| `entry_pc` | in | 3*IMEM_ADDR_WIDTH | Entry PC of each thread |
| `if_t`, `ex_t` | in | 3 each | From `mda_sched` |
| `ex_pc_we`, `ex_pc_val` | in | 1, IMEM_ADDR_WIDTH | Override from EX (taken jump) |
| `imem_addr` | out | IMEM_ADDR_WIDTH | `pc[if_t]`, to `mda_imem` |
| `ex_pc` | out | IMEM_ADDR_WIDTH | `pc[ex_t]` = instruction address + 1 |

### `mda_decoder`
| Port | Dir | Width | Description |
|---|---|---|---|
| `instr` | in | 16 | Word from IMEM |
| `suffix_pend`, `suffix_rd` | in | 1, 3 | Per-thread suffix state of the thread in ID (selected in `mda_core`) |
| `rs1_idx`, `rs2_idx` | out | 3 each | Register read indices (`rs1_idx` = `rd` for `lui`, = `suffix_rd` for a suffix) |
| `rd_idx` | out | 3 | Destination |
| `rd_we` | out | 1 | An EX-stage register write (ALU, immediates, link) |
| `res_link` | out | 1 | The result is the link value (`jmp`, `jrg`), not the ALU output |
| `alu_op` | out | 4 | |
| `imm` | out | 32 | Extended immediate (`lli` slot 1: `imm8 << 16`; suffix: zero-extended word) |
| `b_imm` | out | 1 | Operand B is the immediate |
| `flag_zn_we`, `flag_c_we` | out | 1 each | Flag updates |
| `br_type` | out | 3 | |
| `br_off` | out | IMEM_ADDR_WIDTH | Sign-extended, truncated to the PC width |
| `jof_flag` | out | 4 | Flag index for `jof` |
| `br_inv`, `joc_all` | out | 1, 1 | Condition variants (`COND_ANY` / `COND_ALL`; the invert option is `br_inv`) |
| `mem_op` | out | 2 | None, load, store |
| `mem_byte` | out | 1 | |
| `mem_off` | out | 5 | Unscaled offset |
| `sp_valid`, `sp_op`, `sp_imm` | out | 1, 5, 10 | Spatial/temporal/event instructions, decoded for Stage B and ignored in Stage A |
| `lli_first` | out | 1 | Set `suffix_pend` for the thread |
| `illegal` | out | 1 | Undefined encoding or reserved bits set (never checked on a suffix) |

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

No reset on the registers (the spec leaves them uninitialized). Add an assertion that `ex_t` and `if_t` banks never write in the same cycle with the same bank (they cannot, by D1).

### `mda_id_ex`
Registers the decoder outputs and operands at the end of ID. Inputs are the decoder outputs plus `opa` (rs1 value), `opb` (`b_imm ? imm : rs2 value`), `sdata` (rs2 value, for stores), and `instr` (for the trace only). Outputs are the same signals, registered, and a `valid` bit.

### `mda_alu`
| Port | Dir | Width | Description |
|---|---|---|---|
| `op` | in | 4 | |
| `a`, `b` | in | 32 each | |
| `y` | out | 32 | |
| `z`, `n` | out | 1 each | Derived from `y` for every operation: `z = ~(\|y)`, `n = y[31]` |
| `c`, `c_upd` | out | 1 each | Carry or shifted-out bit, and whether to update `C` (not for logic ops or a shift by 0) |

For `cmp` and `cmpa`, `y` is the three-way result: bits `[31:1]` are `lt` and bit 0 is `lt | ~eq`, so `y` is all ones when less, `0` when equal and `1` when greater. The flags then need no special case.

`mda_shifter`: `a[31:0]`, `amt[4:0]`, `left` in; `y[31:0]`, `c_out` out. It is shared with `pull`/`push` in Stage B.

### `mda_cond`
| Port | Dir | Width | Description |
|---|---|---|---|
| `flags` | in | 16 | Flag view of the thread in EX |
| `mask` | in | 16 | One-hot for `jof`, register value for `joc` |
| `all_mode`, `inv` | in | 1 each | The four conditions: all/any x set/clear |
| `hit` | out | 1 | |

Shared with `waitev` in Stage B, so give it no instruction-specific knowledge.

### `mda_branch_unit`
Inputs: `br_type`, `br_off`, `jof_flag`, `br_inv`, `joc_all`, `opa`, `opb`, `ex_pc`, `flags`. Outputs: `taken`, `target` (IMEM_ADDR_WIDTH bits), `link` (= `ex_pc`).

### `mda_flags`
Inputs: `ex_t`, `ex_v`, `zn_we`, `z_in`, `n_in`, `c_we`, `c_in`. Output: `flags_ex[15:0]` (flags of the thread in EX). Z/N/C only in Stage A.

### `mda_lsu`
| Port | Dir | Width | Description |
|---|---|---|---|
| `ex_v`, `mem_op`, `mem_byte` | in | 1, 2, 1 | |
| `base`, `off`, `sdata` | in | 32, 5, 32 | `off` scaled here by 4 for words |
| `rd_idx` | in | 3 | Registered for the load return |
| `dm_en`, `dm_we` | out | 1 each | To `mda_dmem` (low on a fault) |
| `dm_addr` | out | DMEM_ADDR_WIDTH | |
| `dm_din`, `dm_bm` | out | 32 each | |
| `dm_dout` | in | 32 | Valid the cycle after a load |
| `fault`, `fault_cause` | out | 1, 3 | |
| `ld_valid`, `ld_rd`, `ld_data` | out | 1, 3, 32 | Load return for the thread now in IF (zero on a fault, lane-selected for bytes) |

### `mda_wb`
Combines the EX result mux (ALU output or link) with the register write requests for both paths. Inputs: `ex_v`, `rd_we`, `rd_idx`, `res_link`, `alu_y`, `link`, `ld_valid`, `ld_rd`, `ld_data`. Outputs: `w_ex_we/idx/data` and `w_ld_we/idx/data`, as seen by `mda_regfile`.

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
| `c_en`, `c_we`, `c_addr` | in | 1, 1, DMEM_ADDR_WIDTH | Core port |
| `c_din`, `c_bm` | in | 32 each | Data and per-bit write mask (`1` = write) |
| `c_dout` | out | 32 | Valid the cycle after a read |
| `l_we`, `l_addr`, `l_din` | in | 1, DMEM_ADDR_WIDTH, 32 | Loader write port, full word |

Same macro-or-simulation arrangement, with `RM_IHPSG13_1P_256x32_c2_bm_bist`.

### `mda_sram_sim`
Parameters `AW`, `DW`. One port, synchronous read with a registered output, per-bit write mask (1 writes), write-through if both enables are set. It must behave like the macro in the cases the tests use, and nothing more.

### `mda_sync`
Parameter `W`. `d[W-1:0]` in, `q[W-1:0]` out, 2-flop synchronizer. Instantiated for reset in `mda_tt_top`, and for pins in Stage B.

### `mda_core`
Ports: `clk`, `rst_n`, `go`, `entry_pc[3*IMEM_ADDR_WIDTH]`, the IMEM interface (`imem_addr`, `imem_data`, `imem_en`), the DMEM interface (the `dm_*` signals above), and the trace port (D9). It owns `suffix_pend`/`suffix_rd`, selects them with `id_t`, and instantiates `mda_sched`, `mda_fetch`, `mda_decoder`, `mda_regfile`, `mda_id_ex`, `mda_alu`, `mda_branch_unit`, `mda_flags`, `mda_lsu` and `mda_wb`.

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
2. In order: `mda_pkg`, `mda_sync`, `mda_sched`, `mda_regfile`, `mda_alu` + `mda_shifter`, `mda_decoder`, then the rest of the pipeline. Test each leaf module with its own small bench before integration.
3. A first hardening run of the Stage A core with both macros.