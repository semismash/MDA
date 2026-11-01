The MDA assembly language is an assembly language based on the MDA ISA. It features both instructions and pseudo-instructions.

### Syntax

The MDA ASM has syntax that is very similar to other major assembly languages. The syntax is outlined as follows -

- `mnemonic` - Mnemonic which identifies the operation, specifically an ASM instruction.
- `$mnemonic` - Mnemonic which identifies a pseudo-instruction. The `$` is a warning sign that the mnemonic may expand to more than one instruction, which changes the cycle count, so timing never changes without it being visible in the source.
- `r0-r7` - Register number to be specified from 0 to 7 for GPR. The ABI names (`rsp`, `rad`, `ra0`, `ra1`, `rt0`, `rt1`, `rs0`, `rs1`) are aliases for `r0-r7` in that order, see the ABI section.
- `#0-#23` - Pin numbers to be specified from 0 to 23.
- `#TARGET` - Target name for `cfg` (e.g. `#TMR`), see the notes on the instructions below.
- `42` - Immediate, given in decimal form (use `-` for negative numbers).
- `0x2A` - Immediate, given in hexadecimal form.
- `0b101010` - Immediate, given in binary form.
- `label_name` - Label name defined (note, must account for jump distance restrictions in the ISA).
- `,` - Separator, used to separate tokens.
- `:` - Colon, appended after labels.
- `()` - Parentheses, indicating adding offsets to register values in mem access instructions.
- `@keyword` - Modifier keywords for instructions that take a mode, given in the table below.
- `;` or `//` - Single line comments.
- `/* comment here */` - Multi-line bounded comments

(TENTATIVE) The keyword names below are not final, they are what the docs use so far.

|Keyword|Used with|Meaning|
|---|---|---|
|`@na`|Any instruction with a destination register|No write back, only update the flags|
|`@inv`, `@noinv`|`jof`|Invert the flag's outcome or not. `@noinv` is the default if the keyword is left out|
|`@all`, `@any`, `@none`, `@notall`|`joc`|Mode - all selected flags set, any selected flag set, no selected flag set, not all selected flags set|
|`@any`, `@all`, `@set`, `@clear`, `@consume`|`waitev`|Condition (any or all of the selected flags, set or clear) and whether the sticky flags are consumed on wake up|
|`@level`, `@event`, `@event_clr`, `@pend`, `@pend_clr`|`rpin`|Read the pin level, the pin's event bit (with or without clearing it), or the mask of pending events (with or without clearing it)|
|`@ack_err`, `@ack_ovr`, `@ack_msgn`, `@ack_msgp`, `@ring_next`, `@ring_prev`|`flg`|Acknowledge `ERR` (and its cause), `OVR`, `MSG_N` or `MSG_P`, or ring the next or previous thread's doorbell. Several can be given at once, separated by `,`|

- **Flag names** - The flags can be written by name, e.g. `jof Z, label` (the numbering is given in `Events.md`). (TENTATIVE) Every flag name also has a mask constant with the prefix `M_` (e.g. `M_PE`), and masks can be combined using `|`, for use as a flag mask in `joc` and `waitev`.

|Flag|Index|
|---|---|
|`Z`, `N`, `C`|0, 1, 2|
|`ERR`, `ERRC0`, `ERRC1`, `ERRC2`|3, 4, 5, 6|
|`ISR_RDY`, `OSR_EMPTY`|7, 8|
|`MSG_N`, `MSG_P`|9, 10|
|`PE`, `OVR`, `TMR`|11, 12, 13|

MDA ASM instructions are written in formats, given by the examples below.

- Register-register operation - `add r0, r5, r6` (Add r5 and r6, and store in r0)
- Register-immediate operation - `shli r1, r2, 5` (Shift r2 value left 5 bits, and store in r1)
- Constant loading - `lbi r1, 200` (load the 8-bit constant 200 into r1)
- Jump operation - `jmp r4, my_label` (Jump to address at label_name and store the address of the next instruction in r4)
- Label definition - `my_label:` (subject to jump distance restrictions)
- No WB - `xori @na, r7, r2` (XOR r7 and r2, don't store result, update flags)
- Flag jump - `jof Z, @inv, my_label` (Jump if the `Z` flag is not set)
- Condition inversion - `joc r2, @notall, my_label` (Jump if not all of the flags selected by the mask in r2 are set, e.g. the mask `M_Z | M_N` jumps if either of those two flags is not set)
- Memory access - `lb r3, 10(r2)` (Load data from address at `r2 + 10` to r3. Offsets are unsigned)
- Pin access - `rpin r3, #17, @level` (Read the level of pin #17 into r3)
- Event wait - `waitev r2, @any, @set` (Thread sleep until any of the flags selected by the mask in r2 is set)
- Configuration - `cfg #TMR, r1` (Arm the timer with the count in r1)
- Pseudo-instruction - `$mv r2, r3` (Copy data from r3 to r2)
- Comments - `cmpa r0, r2, r7 ; This is a comment!`
- Immediates are written without a prefix (e.g. `inp 8`, `dl 12`), the `#` prefix is only used for pins and `cfg` targets.
- The range of every immediate is given in the table below. A jump offset is counted in instruction addresses (halfwords, so an `lli` counts as 2) from the next instruction, and the assembler works it out from the label.

|Instruction|Immediate|Range|
|---|---|---|
|`addi`, `xori`|Signed 4 bits|-8 to 7|
|`shli`, `shri`|Shift amount|0 to 15|
|`lbi`, `lui`|Unsigned 8 bits|0 to 255|
|`lli`|Unsigned 24 bits|0 to 16777215|
|`lb`, `sb`|Offset, in bytes|0 to 31|
|`lw`, `sw`|Offset, in words (scaled by 4)|0 to 31|
|`jrg`|Signed 5 bits|-16 to 15|
|`jmp`|Signed 8 bits|-128 to 127|
|`jof`, `joc`|Signed 6 bits|-32 to 31|
|`jnl`|Signed 10 bits (wraps around the instruction memory)|-512 to 511|
|`pull`, `push`|Shift amount|0 to 31|
|`inp`, `outp`|Count|1 to 32|
|`dl`|Cycles|0 to 1023|
|`dlrg`|Offset added to `rs1`|0 to 127|
|`rpin`, `wpin`|Pin number|0 to 23|

### Instructions

The 35 assembly instructions are as follows -

1. `add` - `add rd, rs1, rs2`
2. `xor` - `xor rd, rs1, rs2`
3. `and` - `and rd, rs1, rs2`
4. `or` - `or rd, rs1, rs2`
5. `cmp` - `cmp rd, rs1, rs2`
6. `cmpa` - `cmpa rd, rs1, rs2`
7. `shl` - `shl rd, rs1, rs2`
8. `shr` - `shr rd, rs1, rs2`
9. `addi` - `addi rd, rs1, imm`
10. `xori` - `xori rd, rs1, imm`
11. `shli` - `shli rd, rs1, imm`
12. `shri` - `shri rd, rs1, imm`
13. `lbi` - `lbi rd, imm`
14. `lli` - `lli rd, imm`
15. `lui` - `lui rd, imm`
16. `jmp` - `jmp rd, label_name`
17. `jrg` - `jrg rd, rs1, imm`
18. `jnl` - `jnl label_name`
19. `jof` - `jof flag, [@inv | @noinv], label_name`
20. `joc` - `joc rs1, mode, label_name`
21. `lb` - `lb rd, offset(rs1)`
22. `lw` - `lw rd, offset(rs1)`
23. `sb` - `sb rs2, offset(rs1)`
24. `sw` - `sw rs2, offset(rs1)`
25. `pull` - `pull rd, shift`
26. `push` - `push rs1, shift`
27. `inp` - `inp count`
28. `outp` - `outp count`
29. `rpin` - `rpin rd, #pin, mode` (for the `@pend` and `@pend_clr` modes the pin is left out, as in `rpin rd, @pend_clr`)
30. `wpin` - `wpin rs1, #pin`
31. `dl` - `dl imm`
32. `dlrg` - `dlrg rs1, imm`
33. `waitev` - `waitev rs1, mode`
34. `cfg` - `cfg #target, rs1`
35. `flg` - `flg @keyword[, @keyword ...]` (TENTATIVE)

- Notes on the instructions -
    - `lbi` loads an 8-bit constant, `lli` a 24-bit constant (the assembler emits the suffix halfword by itself), and `lui` sets the upper 8 bits. A 32-bit constant is made with `$li`.
    - `inp` and `outp` only take a count, the pins come from the engine configuration set by `cfg` (TENTATIVE).
    - `joc` takes its flag mask from a register, and only the low 16 bits of it are used (so does `waitev`).
    - `jof` with `@inv` and the four modes of `joc` are variants of the same instructions (see `Instruction_Encoding.md`), so the mnemonics do not change.
    - `jof` and `joc` reach -32 to 31 and `jmp` reaches -128 to 127, in units of instruction memory addresses (halfwords, so an `lli` counts as 2) from the next instruction, and `jnl` (-512 to 511, wrapping around) reaches the whole instruction memory. For the plain instructions, a label that is out of range is an assembler error, it is never fixed silently. The pseudo-instructions below choose the far form by themselves.
    - The `cfg` targets are `#PIN`, `#WATCH`, `#ENG_DIV`, `#ENG_CTL`, `#ENG_ABORT` and `#TMR`. (TENTATIVE) The packing of the value in `rs1` follows the encoding of the fields in `I-O_Interface.md`, and the assembler may provide helper constants for it.

### Register Conventions (ABI)

- The ABI gives every register a name and a role. It is a convention for shared code and subroutines, the hardware does not enforce it, and tight loops can use all 8 registers freely. The names are aliases for `r0-r7`.

|Register|Name|Role|Across calls|
|---|---|---|---|
|`r0`|`rsp`|Stack and data pointer|Preserved|
|`r1`|`rad`|Return address|Clobbered|
|`r2`|`ra0`|Argument 0 and return value|Clobbered|
|`r3`|`ra1`|Argument 1 and second return value|Clobbered|
|`r4`|`rt0`|Temporary|Clobbered|
|`r5`|`rt1`|Temporary|Clobbered|
|`r6`|`rs0`|Saved|Preserved|
|`r7`|`rs1`|Saved|Preserved|

- There is no hardwired zero register. To compare a register with zero, use `addi @na, rs, 0` (which is what `$beqz` and `$bnez` do).
- Return values are returned in `ra0` (and `ra1`).
- The stack grows down, and `rsp` is word aligned. As offsets are unsigned and scaled by the access size, locals sit at positive offsets from `rsp` (`lw rd, 3(rsp)` is word 3). Each thread has its own stack region, the top of each is a symbol defined in the linker script (e.g. `__stack_top0`).
- Registers are not initialized at startup, so the entry code of every thread sets `rsp` first.
- `rad` is clobbered by any call, so a function that calls others saves it first (`$spush rad`).
- Pseudo-instructions only touch the registers that are named as their operands, plus `rad` for `$call` and `$ret`, and the flags where the table below says so.

### Pseudo-instructions

- Why the `$` prefix for pseudo-instructions? Think of the dollar as a warning sign saying that this mnemonic may expand to more than one instruction after encoding, which can help a lot with preventing potential logical errors causing issues with timing, maintaining determinism.
- A pseudo-instruction that needs a scratch register takes it as an explicit operand (`rt` below), it never uses a hidden register.
- Flags - the last column of the tables says which flags a pseudo-instruction overwrites. Flags are always set by the instructions that set them, regardless of `@na`.

|Pseudo-instruction|Assembles to|Usage|Cycle cost|Flags|
|---|---|---|---|---|
|`$nop`|`jnl` with an offset of 0 (to the next instruction)|No operation, creates a bubble. Touches no register and no flag|1 slot|None|
|`$mv rd, rs1`|`addi rd, rs1, 0`|Move contents from one register to another|1 slot|Z, N, C|
|`$not rd, rs1`|`xori rd, rs1, -1`|Inverts all bits in a register|1 slot|Z, N|
|`$neg rd, rs1`|`xori rd, rs1, -1`, then `addi rd, rd, 1`|Two's complement negation|2 slots|Z, N, C|
|`$sub rd, rs1, rs2`|Three instructions, see below|Subtracts `rs2` from `rs1`|3 slots|Z, N (C is not meaningful)|
|`$li rd, imm`|`lbi` for 0-255, `lli` up to 24 bits, otherwise `lli` followed by `lui`|Load a constant into a register, using the shortest form|1, 2 or 3 slots (`lli` takes 2)|None|
|`$jof flag, mode, label`|A plain `jof` if the label is in range, otherwise an inverted `jof` over a `jnl` to the label|Conditional jump on one flag, any distance|1 slot (far - 1 not taken, 2 taken)|None|
|`$joc rs1, mode, label`|A plain `joc` if the label is in range, otherwise an inverted `joc` over a `jnl` to the label|Conditional jump on a flag mask, any distance|1 slot (far - 1 not taken, 2 taken)|None|
|`$call label`|`jmp rad, label`, or if it is too far, `lli rad, label` followed by `jrg rad, rad, 0`|Call a subroutine, the return address goes to `rad`|1 slot (far - 3)|None|
|`$ret`|`jrg rad, rad, 0`|Return from a subroutine (`jrg` always links, so `rad` is overwritten)|1 slot|None|
|`$spush rs`|`addi rsp, rsp, -4`, then `sw rs, 0(rsp)`|Push a register onto the stack|2 slots|Z, N, C|
|`$spop rd`|`lw rd, 0(rsp)`, then `addi rsp, rsp, 4`|Pop a register from the stack|2 slots|Z, N, C|
|`$halt`|`jnl` to itself (an offset of -1)|Spin forever, the thread keeps its slot|1 slot per loop|None|
|`$park rt`|`lli rt, M_MSG_N \| M_MSG_P`, then `waitev rt, @any, @set`, then `jnl` back to the `waitev`|Park a thread until another thread rings its doorbell, going back to sleep if woken for no reason|3 slots, then asleep|None|
|`$waitp rt, #pin, @mode`|Sequence given below|Sleep until an event on one pin. The mode is `@posedge`, `@negedge`, `@anyedge`, `@high` or `@low`|About 12 slots plus the wait|Z, N, C|

- (TENTATIVE) `$sub` is done with no scratch register -
    - If `rd` is not `rs2` - `xori rd, rs1, -1`, then `add rd, rd, rs2`, then `xori rd, rd, -1`.
    - If `rd` is `rs2` - `xori rd, rd, -1`, then `add rd, rd, rs1`, then `addi rd, rd, 1`.
    - `Z` and `N` reflect the result, but `C` is not meaningful after it, so use `cmp` or `cmpa` for comparisons.
- `$li` - `lli` sets the lower 24 bits and zero extends, so in the 32-bit form it comes before `lui`, which sets the upper 8 bits. A negative constant such as `-1` is a full 32-bit value, so it takes 3 slots. A label operand always uses `lli` (24 bits), so the size never depends on where the label ends up.
- The far forms of `$jof`, `$joc` and the branches below are the inverted condition jumping over a `jnl` - `$jof flag, @noinv, L` far is `jof flag, @inv, skip`, then `jnl L`, then `skip:`. For `jof` the `@inv` and `@noinv` swap, and for `joc` the modes swap (`@all` and `@notall`, `@any` and `@none`). If the original condition is true it falls into the `jnl` (2 slots), if not it skips it (1 slot), so the timing of a far jump depends on the outcome, unlike a near one. Timing critical code should keep its jumps in range. The assembler picks the plain form when the label is in range, growing forms until nothing changes.
- Compare and branch - these do the compare and the jump together, as two registers are almost always needed, and a jump on existing flags is already `jof` or `joc`. They overwrite `Z` and `N`.

|Pseudo-instruction|Assembles to|
|---|---|
|`$beq rs1, rs2, label`|`cmp @na, rs1, rs2`, then `jof Z, label`|
|`$bne rs1, rs2, label`|`cmp @na, rs1, rs2`, then `jof Z, @inv, label`|
|`$bltu rs1, rs2, label`|`cmp @na, rs1, rs2`, then `jof N, label`|
|`$bgeu rs1, rs2, label`|`cmp @na, rs1, rs2`, then `jof N, @inv, label`|
|`$bgtu rs1, rs2, label`|`cmp @na, rs2, rs1`, then `jof N, label`|
|`$bleu rs1, rs2, label`|`cmp @na, rs2, rs1`, then `jof N, @inv, label`|
|`$blt`, `$bge`, `$bgt`, `$ble`|The same as `$bltu`, `$bgeu`, `$bgtu` and `$bleu`, with `cmpa` (signed)|
|`$beqz rs, label`|`addi @na, rs, 0`, then `jof Z, label`|
|`$bnez rs, label`|`addi @na, rs, 0`, then `jof Z, @inv, label`|

- The compare and branch pseudo-instructions take 2 slots when the label is in range. If it is out of range they use the far form, which is 2 slots when not taken and 3 when taken. They rely on `cmp` and `cmpa` setting both `N` and `Z` to 0 when the compare is false (see `Instruction_Set.md`).
- `$spush` and `$spop` are named so as not to be confused with the `push` and `pull` instructions, which move data to and from the shift registers. The immediates -4 and 4 fit in the 4-bit range of `addi` (-8 to 7).
- (TENTATIVE) `$waitp` is one-shot, it leaves the pin's watcher off. It loops, because `PE` is the OR of all of the pins the thread owns, so an event on another pin can wake it. The pseudo-instruction is expensive, for timing critical code (e.g. a UART receiver) use the explicit instructions instead.

```
    lli    rt, <pin and mode>     ; arm the watcher, this clears its event bit
    cfg    #WATCH, rt
wait:
    lli    rt, M_PE
    waitev rt, @any, @set
    rpin   rt, #pin, @event_clr   ; was it this pin's event?
    addi   @na, rt, 0
    jof    Z, wait                ; no, go back to sleep
    lli    rt, <pin and OFF>      ; disarm the watcher
    cfg    #WATCH, rt
```

- The modes of `$waitp` map to the watcher modes `POS`, `NEG`, `ANY`, `HIGH` and `LOW` (see `Events.md`).

### Assembler Directives

The MDA assembler additionally support many assembler directives which are used by the assembler to process inputs, allocate memory, and many other assembler-specific functions. **They are not assembled into binary code or instructions themselves.** MDA assembly directives are directly based on GAS syntax.

#### Indicator

The `.mda` directive must be present at the top of any program that the MDA assembler uses, to indicate the file uses MDA assembly. As MDA assembly files use `.s` file extensions like any other assembly file, the `.mda` directive must be present as the first directive in the program to be able to be assembled.

#### Section Management

The following directives help manage different sections of the code. MDA has separate instruction and data memories, so the sections are split between the two, and each has its own address space starting at 0.

- `.section <section_type>` - Tells the assembler that the subsequent lines of code are part of a new section. The section spans from the next word from where `.section` was declared, all the way to the final word before the next section or EOF. The following directives are to be appended in front of `.section` to tell the assembler which section it is (e.g. `.section .data`).
- `.text` - Tells the assembler that the section is executable instructions, placed in the instruction memory. Only instructions are allowed in it (no data allocation), as the instruction memory cannot be read by loads.
- `.data` - Tells the assembler that the section is reserved for initialized static global variables, placed in the data memory and loaded by the loader. It supports both reading and writing.
- `.bss` - Tells the assembler that the section contains uninitialized space in the data memory, meant for runtime allocation, supporting both reading and writing. It is not loaded, so its contents are undefined until the program writes them.
- `.rodata` - Tells the assembler that the section contains read-only data which is initialized once, placed in the data memory with `.data`. It is read-only by convention only, as the hardware does not protect the memory.
- Custom section names are not supported as of now. Each MDA assembly section has a strict purpose which determines how the program is assembled. Instructions are not allowed in the data sections.
- Labels in `.text` are instruction memory addresses (in halfwords), and labels in the data sections are byte addresses in the data memory.

#### Data Allocation

The following directives help allocate data, and are allowed in the data sections only. Data is little-endian, and every data section is padded with zeros up to a whole number of words, as the loader writes whole words.

- `.byte <num1, num2, num3...>` - Allocates 8-bit integers (bytes).
- `.short/.hword <num1, num2, num3...>` - Allocates 16-bit integers (halfwords).
- `.int/.word <num1, num2, num3...>` - Allocates 32-bit integers (words).
- `.ascii <str1, str2, str3...>` - Emits character strings without a null-terminator byte
- `.asciz/.string <str1, str2, str3...>` - Emits character strings with the `\0` null terminator byte.
- `.skip/.space <qty>` - Emits a certain number of uninitialized bytes (specified by `qty`) to pad the memory.
- `.align/.balign <alignment>` - Aligns location counter to a specified alignment (in bytes).

#### Threading

This is the MDA specific directive which deals with how the program is split between the threads.

- `.entry0/.entry1/.entry2` - Marks the current location in `.text` as the entry point of that thread, hence where its PC starts when the chip begins running. It takes no argument, and the code that follows it is the code of that thread, for example -

```
.entry0
    $li   rsp, __stack_top0
    $call uart_rx_init
loop0:
    ...
    jnl   loop0

.entry1
    $li   rsp, __stack_top1
    ...
    $halt

.entry2
    $park rt0

uart_rx_init:              ; shared code, belongs to no thread
    ...
    $ret
```

- Each of the three must appear exactly once, in any order. A missing one is an error, as the loader needs all three entry points. A thread that is not needed is given a park block, as above.
- The assembler lays code out in the order it is written, there is no reordering. Two threads can start at the same place by writing two entry directives one after the other.
- Code that is not under an entry (e.g. a shared subroutine) belongs to no thread. It is just code under a label, and can be called from any thread.
- (TENTATIVE) The assembler warns if the last instruction before an `.entryN` directive can fall through, i.e. it is not an unconditional jump, `$ret`, `$halt` or `$park`.
- The entry points are passed on to the loader (see `Core_Components.md`).

#### Miscellaneous

These are other directives provided in the MDA assembly language.

- `.equ`/`.set` - Assign a constant symbolic value or expression, which is then inlined into any specific instance of that constant being mentioned in the code.
- `.macro` - Assigns a reusable block of code (macro) which is copy pasted into every instance of it being used. A macro is invoked with a `$` prefix (e.g. `$my_macro r1, r2`), like a pseudo-instruction, so that a block of code with a hidden cycle cost is visible where it is used.
- `.endm` - Ends the macro code block.

### Linker Script

The linker script places the sections in memory. It uses a subset of the GNU ld script syntax, and must end in the `.ld` extension. As MDA has separate instruction and data memories, it has two memories, both starting at address 0.

- `MEMORY` - Defines the instruction memory `IMEM` and the data memory `DMEM`, with their origin and length (in bytes).
- `SECTIONS` - Places `.text` in `IMEM`, and `.data`, `.rodata` and `.bss` in `DMEM`.
- Symbol assignments - Define symbols such as the stack top of each thread (`__stack_top0`, `__stack_top1`, `__stack_top2`), which the startup code of each thread uses to set `rsp`. A stack top must be word aligned.
- The memory sizes are also used by the assembler to check the program, e.g. that the entry points and the sections fit.
- (TENTATIVE) Only a subset is supported - `MEMORY`, `SECTIONS` with simple placement, and symbol assignments with simple expressions. Anything else is rejected with an error.
- An example (the sizes are only examples) -

```
MEMORY {
    IMEM (rx) : ORIGIN = 0, LENGTH = 2K
    DMEM (rw) : ORIGIN = 0, LENGTH = 4K
}
SECTIONS {
    .text   : { *(.text) }   > IMEM
    .data   : { *(.data) }   > DMEM
    .rodata : { *(.rodata) } > DMEM
    .bss    : { *(.bss) }    > DMEM
}
__stack_top0 = ORIGIN(DMEM) + LENGTH(DMEM);
__stack_top1 = __stack_top0 - 0x400;
__stack_top2 = __stack_top1 - 0x400;
```

### Assembler Output

- The assembler produces the instruction image (in halfwords), the data image (in words), and the three entry PCs.
- (TENTATIVE) A host tool, which the testbench uses too, packs these into the loader commands (see `Core_Components.md`), including the checksum.
- (TENTATIVE) A listing file with the address and slot cost of every instruction, and the cumulative cycle count of each block, as every instruction has a fixed cost.

### Tentative Features

These features are tentative, and either are being considered to be added or to be added in the future.

- Multi-file programs: Assembling multiple assembly files in to a single binary.
- `.global`/`.globl`, `.include` directives: Depends on if we end up adding multiple file systems.
- `.if`/`.else`/`.endif`, `.rept`/`.endr` - To be added in the future if time permits.