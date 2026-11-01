The MDA assembly language is an assembly language based on the MDA ISA. It features both instructions and pseudo-instructions.

### Syntax
The MDA ASM has syntax that is very similar to other major assembly languages. The syntax is outlined as follows -
- `mnemonic` - Mnemonic which identifies the operation, specifically an ASM instruction.
- `$mnemonic` - Mnemonic which identifies a pseudo-instruction. The `$` is a warning sign that the mnemonic may expand to more than one instruction, which changes the cycle count, so timing never changes without it being visible in the source.
- `r0-r7` - Register number to be specified from 0 to 7 for GPR.
- `#0-#23` - Pin numbers to be specified from 0 to 23.
- `#NAME` - Target name for `cfg` (e.g. `#TMR`), see the `cfg` section below.
- `42` - Immediate, given in decimal form (use `-` for negative numbers).
- `0x2A` - Immediate, given in hexadecimal form.
- `0b101010` - Immediate, given in binary form.
- `label_name` - Label name defined (note, must account for jump distance restrictions in the ISA).
- `,` - Separator, used to separate tokens.
- `:` - Colon, appended after labels.
- `()` - Parentheses, indicating adding offsets to register values in mem access instructions.
- `@na` - Keyword to be substituted for destination register field to indicate no write back for destination register
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
- Jump operation - `jmp r4, my_label` (Jump to address at label_name and store return address + 1 in r4)
- Label definition - `my_label:` (subject to jump distance restrictions)
- No WB - `xori @na, r7, r2` (XOR r7 and r2, don't store result, update flags)
- Flag jump - `jof Z, @inv, my_label` (Jump if the `Z` flag is not set)
- Condition inversion - `joc r2, @notall, my_label` (Jump if not all of the flags selected by the mask in r2 are set, e.g. the mask `M_Z | M_N` jumps if either of those two flags is not set)
- Memory access - `lb r3, 10(r2)` (Load data from address at `r2 + 10` to r3. Offsets are unsigned)
- Pin access - `rpin r3, #17, @level` (Read the level of pin #17 into r3)
- Event wait - `waitev r2, @any, @set` (Thread sleep until any of the flags selected by the mask in r2 is set)
- Configuration - `cfg #TMR, r1` (Arm the timer with the count in r1)
- Pseudo-instruction - `$mv r2, r3` (Copy data from r3 to r2)
- Comments - `cmpa r0, r2, r7 # This is a comment!`
- Immediates are written without a prefix (e.g. `inp 8`, `dl 12`), the `#` prefix is only used for pins and `cfg` targets.
- (TENTATIVE) The range of every immediate follows from the encoding, and will be added here once the encoding is final.

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
    - `jof` and `joc` reach ±32 instructions, `jmp` reaches ±128 and `jnl` reaches the whole instruction memory. A label that is out of range is an assembler error, it is never fixed silently. Use the far pseudo-instructions below.
    - The `cfg` targets are `#PIN`, `#WATCH`, `#ENG_DIV`, `#ENG_CTL`, `#ENG_ABORT` and `#TMR`. (TENTATIVE) The packing of the value in `rs1` follows the encoding of the fields in `I-O_Interface.md`, and the assembler may provide helper constants for it.

### Pseudo-instructions

- Why the `$` prefix for pseudo-instructions? Think of the dollar as a warning sign saying that this mnemonic may expand to more than one instruction after encoding, which can help a lot with preventing potential logical errors causing issues with timing, maintaining determinism.

|Pseudo-instruction|Assembles to|Cycle cost|
|---|---|---|
|`$mv rd, rs1`|`addi rd, rs1, 0`|1 slot|
|`$not rd, rs1`|`xori rd, rs1, -1`|1 slot|
|`$sub rd, rs1, rs2`|`xori` with -1 on `rs2`, `addi` 1, then `add`. Needs a scratch register when `rd` is also a source|3 slots|
|`$li rd, imm`|`lli rd, imm` followed by `lui rd, imm`, for a 32-bit constant|3 slots (`lli` takes 2)|
|`$jof flag, mode, label`|Far conditional jump. An inverted `jof` over a `jnl` to the label|2 slots (+1 when the jump is taken)|
|`$joc rs1, mode, label`|Far conditional jump. An inverted `joc` over a `jnl` to the label|2 slots (+1 when the jump is taken)|
|`$waitp #pin, @posedge`|(TENTATIVE) Wait for a pin edge. Arms the pin's watcher and sleeps in a `waitev` on `PE`. The expansion and its scratch registers are to be defined|Several slots|

- (TENTATIVE) The assembler may shorten `$li` to a single `lbi` or `lli` when the constant fits, as the size is known when assembling.
- (TENTATIVE) Branch names for the common comparisons after `cmp` or `cmpa` can be provided as aliases of `jof` - `$beq` is `jof Z`, `$bne` is `jof Z, @inv`, `$blt` is `jof N` and `$bge` is `jof N, @inv`.