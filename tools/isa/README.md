# tools/isa: the ISA as data

`isa.yaml` is the single source of truth for the MDA instruction encoding. Everything else is generated from it or checked against it.

```
isa.yaml           the encoding (edit this)
isa_gen.py         validator and generator (needs: pip install pyyaml)
out/
  mda_isa_pkg.sv       -> copy to src/mda_isa_pkg.sv   (opcodes, funct codes, reserved masks, flag and cause constants)
  isa_tables.md        -> doc tables for spec/
  isa_tables.json      -> for your assembler and reference model
  golden_decode.csv.gz -> classification of all 65,536 words (regenerate with --exhaustive, see below)
```

## Commands

```
python3 isa_gen.py --check --doc "<path>/Instruction Encoding.md"      # always run after editing isa.yaml
python3 isa_gen.py --check --out out --exhaustive out/golden_decode.csv  # regenerate everything
```

`--check` fails (exit code 1) if any of these break: a funct slot assigned twice or not at all; a bit of an encoding claimed twice or not
at all; an example not encoding to the documented word; a legal word that does not round-trip; a legal-word count that differs from the
analytic count; a doc-derived special word with the wrong legality; the examples differing from the doc's table. Add `--asm <mda_asm.py>`
to also compare value ranges with an assembler.

## Conventions in isa.yaml

- Bit ranges are `"hi:lo"` (or `"n"`), in instruction-word bit numbers. A field with several ranges is their **concatenation, MSB first**:
  `["14:13", "9:6"]` is a 6-bit value, top 2 bits from word bits 14:13, low 4 from bits 9:6.
- Operand value = raw (sign-extended if `signed`) + `bias`. `bias: 1` is how `inp 8` is stored as 7. `addr_scale: 4` (lw/sw) is how the
  hardware forms the address (`rs1 + 4 * offset`). It is not part of the operand value, `lw r3, 3(r2)` has the operand 3.
- `reserved` ranges must be 0 or the word is illegal. `illegal_values` marks field values that make the word illegal. A value that is a
  valid encoding but a run-time fault (rpin pin above 23, cfg target 6 or 7) is deliberately legal here.
- `stage: A` executes in Stage A, `stage: B` decodes in Stage A and executes in Stage B.
- YAML 1.1 reads bare `y n yes no on off` as booleans. Never use those as bare names (that is why flag `N` is quoted and the jump field is
  called `offset`). `isa_gen.py` loads the file with a strict loader, but other tools may not.

## What is independent and what is not

- **Independent of this file:** the 27 worked examples and the ~30 `special_words` (legality of specific words) come from the statements in
  `Instruction Encoding.md`, derived by hand. `--doc` also checks the examples against the doc's table text.
- **Not independent:** `golden_decode.csv` and `mda_isa_pkg.sv` are generated from the same YAML. If the YAML were wrong in a way the checks
  above do not catch, the RTL package and the golden vectors would be wrong together. Your hand-written reference model, the examples and the
  special words are what protect you from that, so keep adding doc-derived words whenever you find an edge case.
- Edit a word in `special_words` by recomputing it from the layouts, not by changing the YAML until the check passes. (Two of my own
  hand-computed words were wrong when I first wrote the list. The checker found them, and the YAML was right.)

## Suggested use for the decoder test

For each of the 65,536 words, compare your RTL decoder's `illegal` output, and the instruction it identifies, with `golden_decode.csv`.
Compare control outputs (register usage, flag updates, memory and branch class) against the `src`, `dst`, `dst_when`, `flags`, `mem` and
`branch` attributes in `isa_tables.json`. The legal and illegal counts to expect are 44,288 and 21,248
(unused funct 12,288, reserved bits 8,192, reserved values 768).
