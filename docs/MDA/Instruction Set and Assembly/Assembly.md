The MDA assembly language is an assembly language based on the MDA ISA. It features both instructions and pseudo-instructions.
### Syntax
The MDA ASM has syntax that is very similar to other major assembly languages. The syntax is outlined as follows -
- `mnemonic` - Mnemonic which identifies the operation, specifically an ASM instruction.
- `$mnemonic` - Mnemonic which identifies a pseudo-instruction.
- `r0-r7` - Register number to be specified from 0 to 7 for GPR.
- `#0-#23` - Pin numbers to be specified from 0 to 23.
- `42` - Immediate, given in decimal form (use `-` for negative numbers).
- `0x2A` - Immediate, given in hexadecimal form.
- `0b101010` - Immediate, given in binary form.
- `label_name` - Label name defined (note, must account for jump distance restrictions in the ISA).
- `,` - Separator, used to separate tokens.
- `:` - Colon, appended in front of labels.
- `()` - Parentheses, indicating adding offsets to register values in mem access instructions.
- `@na` - Keyword to be substituted for destination register field to indicate no write back for destination register
- `@posedge` or `@negedge` - To be used for temporal instructions to specify positive edge or negative edge detection.
- `@inv` or `@noinv` - To be used with condition jumps to determine if the condition's outcome is to be inverted for a jump.
- `;`, `#` or `//` - Single line comments
- `/* comment here */` - Multi-line bounded comments
MDA ASM instructions are written in formats, given by the examples below.
- Register-register operation - `add r0, r5, r6` (Add r5 and r6, and store in r0)
- Register-immediate operation - `shli r1, r2, 5` (Shift r2 value left 5 bits, and store in r1)
- Jump operation - `jmp r4, my_label` (Jump to address at label_name and store return address + 1 in r4)
- Label definition - `my_label:`  (subject to jump distance restrictions)
- No WB - `xori @na, r7, r2` (XOR r7 and r2, don't store result, update flags)
- Edge-tracking - `waitp #17, @posedge` (Thread sleep till posedge for pin #17).
- Condition inversion - `joc 0b00011, @inv` (Jump if either of the last two flags are not set)
- Memory access - `lb r3, -10(rs2)` (Load data from address at `rs2 - 10` to rs3)
- Pseudo-instruction - `$mv r2, r3` (Copy data from r3 to r2)
- Comments - `cmpa r0, r2, r7  # This is a comment!` 
### Instructions
The 33 assembly instructions are as follows -
1. `add` - `add rd, rs1, rs2`
2. `xor` - `xor rd, rs1, rs2`
3. `and` - `and rd, rs1, rs2`
4. `or` - `or rd, rs1, rs2`
5. `cmp` - `cmp rd, rs1, rs2`
6. `cmpa` - `cmpa rd, rs1, rs2`
7. `shl` - `shl rd, rs1, rs2`
8. `shr` - `shr rd, rs1, rs2`
9. `addi` - `addi rd, rs1, imm`
10.  `xori` - `xori rd, rs1, imm`
11.  `shli` - `shli rd, rs1, imm`
12.  `shri` - `shri rd, rs1, imm`
13. `lli` - `lli rd, imm`
14. `lui` - `lui rd, imm`
15. `alipc` - `alipc rd, imm`
16. `auipc` - `auipc rd, imm`
17. `jmp` - `jmp rd, label_name`
18.  `jrg` - `jrg rd, rs1, label_name`
19. `jof` - `jof immf, [@inv | @noinv], label_name`
20. `joc` - `joc immf, [@inv | @noinv], label_name`
21. `lb` - `lb rd, offset(rs1)`
22. `lw` - `lw rd, offset(rs1)`
23. `sb` - `sb rs2, offset(rs1)`
24. `sw` - `sw rs2, offset(rs1)`
25. `pull` - `pull rd`
26. `push` - `push rs1`
27. `inp` - `inp pin_idx, count`
28. `outp` - `outp pin_idx, count`
29. `rpin` - `rpin rd, pin_idx`
30. `wpin` - `wpin rd, pin_idx`
31. `dl` - `dl imm`
32. `dlrg` - `dlrg rs1, imm`
33. `waitp` - `waitp pin_idx [@posedge | @negedge]`