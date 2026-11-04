# Instruction Set
The MDA ISA is a minimalist dual-nature instruction set which merges CPU operations with deterministic execution.

- Instructions are 16-bits long, fixed size. The one exception is `lli`, which is followed by a 16-bit suffix halfword.
- They're encoded in little-endian order.
- Registers and data are 32 bits wide, with 8 GPRs per thread.
- Instructions can set flags, as stored in the `FLAGS` register.
    - The three basic flags are Zero `Z`, Negative `N`, and Carry `C`
    - In addition to these, the `FLAGS` register also holds event flags. There are 16 flag slots in total, all local to a thread. The flag layout is given in the [`Events.md`](../Processor%20Architecture/Events.md)) file. There are a total of 35 instructions in the MDA instruction set, plus pseudo-instructions which assemble to one or more of them. _NOTE: The encoding of the instructions is not part of this file, it is defined in [`Instruction_Encoding.md`](Instruction%20Encoding.md)._

## Instruction Types

Instructions are classified into the following types -

|Type|Instructions|Count|
|---|---|---|
|Register operations|`add` `xor` `and` `or` `cmp` `cmpa` `shl` `shr`|8|
|Immediate operations|`addi` `xori` `shli` `shri`|4|
|Immediate loading|`lbi` `lli` `lui`|3|
|Jumps|`jmp` `jrg` `jnl` `jof` `joc`|5|
|Memory access|`lb` `lw` `sb` `sw`|4|
|Spatial|`pull` `push` `inp` `outp` `rpin` `wpin`|6|
|Temporal & event|`dl` `dlrg` `waitev`|3|
|Configuration & signalling|`cfg` `flg`|2|

#### Operational Instructions

- Register Operations -
    - Performs an operation on two registers, and stores the value in a third register
    - There is no hardwired zero register, all 8 GPRs are usable.
    - Encoded instructions contain a dedicated write-back (WB) bit which tells if the result is to be written back to a register. Based on how the assembly instruction is written, the register is chosen to be updated accordingly.
        - Flags in the `FLAGS` register are always set, regardless of the WB bit.
        - In all cases, the `Z` flag is set to `1` if the result is all 0, and the `N` flag is set to `1` if the MSB is 1. The one exception is `cmp` and `cmpa`, as given below.
    - Sub-types include -

|Instruction|Operation|
|---|---|
|`add`|Adds two register values. Sets `C` flag to `1` if carry.|
|`and`|Logical AND on two register values.|
|`or`|Logical OR on two register values.|
|`xor`|Logical XOR on two register values.|
|`cmp`|Sets a register value to 1 if rs1 is greater than rs2, -1 (so 0xFFFFFFFF) if `rs1` is lesser than `rs2`, and 0 if both are equal. Sets `N` to `1` if less than and `Z` to `1` if equal to, and sets both to `0` otherwise.|
|`cmpa`|Same as `cmp` but performs a signed comparison instead.|
|`shl`|Performs a logical left shift with zero extension on `rs1` by amount specified in `rs2`. Sets `C` flag to the last bit that was shifted out. A shift by 0 leaves `C` unchanged.|
|`shr`|Performs a logical right shift with zero extension, otherwise same as above.|

- Immediate Operations-
    - Performs an operation on a register and an immediate, and stores the value in a third register
    - Encoded instructions contain a dedicated write-back bit which tells if the result is to be written back to a register. Based on how the assembly instruction is written, the register is chosen to be updated accordingly.
        - Flags in the `FLAGS` register are always set, regardless of the WB bit.
        - In all cases, the `Z` flag is set to `1` if the result is all 0, and the `N` flag is set to `1` if the MSB is 1.
    - The immediates of the given instructions are sign extended in case of `addi` and `xori`, and zero extended in case of `shli` and `shri`.
    - The immediate of `addi` and `xori` is 4 bits (-8 to 7), and the immediate of `shli` and `shri` is 4 bits (shifts of 0-15). Longer shifts use `shl` and `shr` with a register.
    - Sub-types include -

|Instruction|Operation|
|---|---|
|`addi`|Adds a register value to an immediate. Sets `C` flag to `1` if carry. A negative immediate subtracts.|
|`xori`|Logical XOR on a register value and an immediate. With an immediate of -1, this is a bitwise NOT.|
|`shli`|Performs a logical left shift with zero extension on `rs1` by amount specified by the immediate. Sets `C` flag to the last bit that was shifted out. A shift by 0 leaves `C` unchanged.|
|`shri`|Performs a logical right shift with zero extension on `rs1` by amount specified by the immediate. Otherwise, same as above.|

- Immediate Loading -
    - Performs operations involving immediate values, specifically loading constants into a register. These instructions do not set any flags.
    - Sub-types include -

|Instruction|Length|Operation|
|---|---|---|
|`lbi`|1 slot|Load byte immediate. Loads the 8-bit immediate, zero extended, into the destination register.|
|`lli`|2 slots (suffix)|Load lower immediate. Loads a 24-bit immediate, zero extended, into the destination register. The immediate is made of 8 bits in the instruction, and the 16-bit suffix halfword that follows it.|
|`lui`|1 slot|Load upper immediate. Updates the upper 8 bits (`[31:24]`) of the destination register with the 8-bit immediate, and keeps the lower 24 bits.|

- A full 32-bit constant is built with `lli` followed by `lui`, which the assembler provides as the pseudo-instruction `$li`.
- The suffix halfword is not a separate instruction. It is read as part of `lli`, in the second slot of the thread, so the instruction takes 6 cycles in total, deterministically. A jump that lands on a suffix halfword decodes it as an ordinary instruction (most likely an illegal instruction, see [`Events.md`](../Processor%20Architecture/Events.md)), and the assembler rejects an `lli` in the last instruction address, as the suffix would wrap around to address 0.
- Negative constants are made using `xori` with -1, or `addi`.
- There are no PC-relative address instructions (`alipc` and `auipc` were dropped). Code is loaded at fixed addresses, so labels can be built with `lli`, and a linking jump can be used to read the PC.
- Jumps -
    - Performs a jump operation by updating the PC to a certain value. The PC is as wide as the instruction memory address, and wraps around. The PC counts instruction addresses (16-bit halfwords, so the byte address divided by 2), and jump offsets are relative to the next instruction (PC + 1).
    - Sub-types include -

|Instruction|Operation|
|---|---|
|`jmp`|Performs an unconditional jump to PC + 1 + IMM (8 bits, sign extended, so -128 to 127 instructions) and saves the address of the next instruction (PC + 1) to `rd`.|
|`jrg`|Performs an unconditional jump to `rs1` (the lower bits that fit the PC) + IMM (5 bits, sign extended, so -16 to 15) and saves the address of the next instruction (PC + 1) to `rd`.|
|`jnl`|Performs a non-linking unconditional jump (no `rd`), with enough reach to hit any instruction address. Used for far jumps. The offset is 10 bits, sign extended (-512 to 511), relative to PC + 1, and it wraps around the instruction memory, so it reaches any instruction address as long as the instruction memory has at most 1024 instruction addresses.|
|`jof`|Performs a conditional jump to PC + 1 + IMM (6 bits, sign extended, so -32 to 31) without saving the return address. Checks one specific flag (out of the 16), and jumps if it's `1` (or if it's `0` for the inverted variant of the instruction).|
|`joc`|Performs a conditional jump to PC + 1 + IMM (6 bits, sign extended, so -32 to 31) without saving the return address. The flag mask is taken from the register `rs1` (only its low 16 bits are used), so any of the flags can be selected. The selected flags are checked according to a mode, and the jump is performed if the condition holds.|

- The modes of `joc` are - all selected flags set, any selected flag set, no selected flag set, not all selected flags set. The instruction selects all or any, and an invert bit in the immediate inverts the condition. `jof` has an inverted variant in the same way. These are variants of the same instruction (see `Instruction_Encoding.md`), so there are still 35 instructions. `waitev` uses the same four conditions (see `Events.md`).
- Conditional jumps (`jof` and `joc`) reach -32 to 31 instructions. A farther conditional jump is expanded by the assembler into an inverted conditional jump over a `jnl` (flagged using the `$` prefix, as it changes the cycle count).
- Jumps have no penalty in the barrel pipeline, as the next instruction of the same thread is only fetched 3 cycles later.
- Jump offsets are relative to the next instruction (PC + 1), in instruction addresses (an `lli` counts as 2). So a linking jump with an offset of 0 reads the address of the next instruction into `rd`, and `jnl` with an offset of 0 does nothing (it is used as `$nop`).
- Choosing a jump -

|Need|Use|Reach|Links|
|---|---|---|---|
|Call or jump to a nearby label|`jmp`|-128 to 127|Yes|
|Jump to an address in a register|`jrg`|Register + (-16 to 15)|Yes|
|Far jump without a return address|`jnl`|Whole instruction memory|No|
|Branch on one flag (e.g. `Z`, `ERR`)|`jof`|-32 to 31|No|
|Branch on a combination of flags|`joc`|-32 to 31|No|

#### Memory Access Instructions -

- Performs a memory access, either a LOAD or a STORE, with the chip's on board SRAM-based data memory.
- All memory accesses are unsigned (i.e. there are no signed loads). They can access one byte or one word at a time. Addresses are byte addresses.
- (TENTATIVE) The size of the data memory depends on the SRAM macro used. Addresses are not wrapped. Any access outside of the memory is an out-of-bounds fault.
- Word accesses must be aligned to a word (4 bytes), a misaligned access is a fault.
- Faults - A faulting access still completes in its normal slot, so timing is never affected. A faulting store is suppressed (memory is not changed), and a faulting load returns 0 to `rd`. In both cases, the thread's `ERR` flag is set along with the fault cause (see [`Events.md`](../Processor%20Architecture/Events.md)).
- Offsets - Offsets are unsigned and scaled by the access size, e.g. a 5-bit offset reaches 31 bytes with a byte access, but 31 words with a word access.
- Sub-types include -

|Instruction|Operation|
|---|---|
|`lb`|Loads one byte from the memory, zero extended, into specified register `rd`. Calculates the memory address from `rs1` + IMM.|
|`lw`|Loads one word (4 bytes) from the memory into specified register `rd`. Calculates the memory address from `rs1` + IMM. The address must be word aligned.|
|`sb`|Stores one byte from specified register `rs2` into memory. Calculates the memory address from `rs1` + IMM.|
|`sw`|Stores one word (4 bytes) from specified register `rs2` into memory. Calculates the memory address from `rs1` + IMM. The address must be word aligned.|

- Half-word loads and stores (`lh` and `sh`) are not part of the ISA for now.
- Threads signal each other using doorbells, rung by `flg` (see below), and pass data through the shared data memory (see [`Threading.md`](../Processor%20Architecture/Threading.md)). There are no dedicated inter-thread read and write instructions.

#### Spatial Instructions

- Spatial Instructions are used to communicate with the I/O ports within the processor. The details of the pins, ownership and the shift engine are given in [`I-O Interface.md`](../Processor%20Architecture/I-O%20Interface.md). The following spatial instructions are included within the ISA -

|Instruction|Parameters|Operation|
|---|---|---|
|`pull`|`rd, #shift`|Pull data from ISR into GPR, shifted by the given amount (0 to 31). Clears `ISR_RDY`.|
|`push`|`rs1, #shift`|Push data from GPR into OSR, shifted by the given amount (0 to 31). Clears `OSR_EMPTY`.|
|`inp`|`#count`|Start the shift engine receiving `count` bits (1 to 32) into the ISR. The pins are taken from the engine configuration, set using `cfg`.|
|`outp`|`#count`|Start the shift engine sending `count` bits (1 to 32) from the OSR. The pins are taken from the engine configuration, set using `cfg`.|
|`rpin`|`rd, #pin, mode`|Read directly from a pin into a register. The mode selects the pin level, the pin's event bit (with or without clearing it), or the mask of pending pin events.|
|`wpin`|`rs1, #pin`|Send bit 0 of a register directly to a pin. The pin must be owned by the thread, and in direct mode.|

- `inp` and `outp` return immediately. When the transfer is done, the `ISR_RDY` (for `inp`) or `OSR_EMPTY` (for `outp`) flag is set, which the thread can observe using `jof`, `joc` or `waitev`.
- Starting a transfer while the engine is busy, or with no engine pins configured, is a fault.
- Only the owner of a pin can drive it or read its events. Reading the level of a pin is allowed for any thread.

#### Temporal & Event Instructions

- Temporal instructions are used for temporal control, and add deterministic delays within the processor's execution. Event instructions observe events (see [`Events.md`](../Processor%20Architecture/Events.md)).
- The following temporal and event instructions are -

|Instruction|Parameters|Operation||
|---|---|---|---|
|`dl`|`#cycles`|Put a processor's thread to sleep for IMM clock cycles (0 to 1023).||
|`dlrg`|`rs1, #offset`|Put a processor's thread to sleep for RS1 + IMM (offset, 0 to 127) clock cycles. `rs1` is a 32-bit count, so a thread can sleep for a long time.||
|`waitev`|`rs1, mode`|Put a processor's thread to sleep until the flags selected by the mask in `rs1` meet a condition (any or all selected flags set or clear), optionally consuming the sticky flags when it wakes up.||

- The true delay of `dl` and `dlrg` may be 0-2 cycles more than the instructed delay, as a thread always wakes up in its own slot (see [`Threading.md`](../Processor%20Architecture/Threading.md)).

#### Configuration & Signaling Instructions

- These instructions configure the I/O and event hardware, and signal other threads.

| Instruction | Parameters     | Operation                                                                                                                                                                                                                                                                               |
| ----------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cfg`       | `#target, rs1` | Configure the issuing thread's own pins, shift engine or timer. The target is selected by the immediate, and the value is taken from `rs1`. The targets are given in [`I-O Interface.md`](../Processor%20Architecture/I-O%20Interface.md).                                              |
| `flg`       | `#mask`        | Acknowledges (clears) sticky flags of the issuing thread - `ERR` (with its cause), `OVR`, `MSG_N` and `MSG_P` - or rings the doorbell of the next or previous thread. It is the only instruction that writes a flag of another thread, and it can only set that thread's doorbell flag. |