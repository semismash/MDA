[![docs](https://github.com/semismash/MDA/actions/workflows/docs.yaml/badge.svg)](https://github.com/semismash/MDA/actions/workflows/docs.yaml)
[![test](https://github.com/semismash/MDA/actions/workflows/test.yaml/badge.svg)](https://github.com/semismash/MDA/actions/workflows/test.yaml)
[![gds](https://github.com/semismash/MDA/actions/workflows/gds.yaml/badge.svg)](https://github.com/semismash/MDA/actions/workflows/gds.yaml)
[![fpga](https://github.com/semismash/MDA/actions/workflows/fpga.yaml/badge.svg)](https://github.com/semismash/MDA/actions/workflows/fpga.yaml)

# MDA: Minimalist Deterministic Architecture

A three-thread barrel processor for cycle-exact protocol emulation. Entry in the [Jane Street Protocol Emulator ASIC Competition](https://blog.janestreet.com/protocol-emulator-asic-competition/), targeting [Tiny Tapeout](https://tinytapeout.com) on IHP SG13CMOS5L (6x4 tiles, submission deadline 18 January 2027).

![MDA Stage A layout: two SRAM macros along the bottom edge, standard cells above](docs/img/gds_render.png)

*Stage A hardened layout (GDS render). The instruction memory (left) and data memory (right) are SRAM macros; the processor logic occupies about a third of the core.*

**Status.** Stage A (the processor core) is complete, verified and hardened with clean signoff. Stage B (pin and event hardware for the protocol engines) is in design.

## Overview

Three hardware threads share one short pipeline in strict round-robin order. Each thread executes one instruction every three cycles, whatever the other threads are doing, so the cycle timing of a thread's firmware is fixed by its own code alone. That property is the point of the design: firmware that bit-bangs a bus protocol produces the same waveform on every run, which makes scripted, exactly repeatable behaviour possible, for example fault injection in a device emulator.

| | |
| --- | --- |
| Threads | 3, strict round-robin, no stalls |
| Pipeline | Three stages shared by all threads: IF (address), ID (data and decode), EX |
| Instructions | 16 bits wide, 35 mnemonics (37 encodings), `lli` builds a 24-bit constant over two words |
| Datapath | 32 bits, 8 general registers per thread (three register banks) |
| Flags | One flag register per thread (Z, N, C, ERR, ERRC, OVR, ...) read by flag-mask jumps |
| Memories | Instruction: 1024 × 16 SRAM macro. Data: 256 × 32 SRAM macro (1 KB), byte and word access |
| Faults | Misaligned or out-of-bounds accesses and illegal instructions set ERR with a cause code; a second fault sets OVR |

## Project status

| Stage | Scope | State |
| --- | --- | --- |
| A | Processor core, both memories, Tiny Tapeout wrapper | Done: RTL verified, hardened, CI green |
| B | Pin and event hardware, shift engines, protocol firmware | In design; simulation first, then an FPGA bring-up |

The plan puts the Stage B go/no-go gate on 8 December 2026 and the feature freeze on 15 December 2026.

## Stage A results

From the second hardening run (full report in [docs/Stage_A_Baseline.md](docs/Stage_A_Baseline.md)).

| | |
| --- | --- |
| Die / core | 1289.28 × 710.64 µm (0.916 mm²) / 0.902 mm² |
| Area used | 30.4% of the core: 145,406 µm² of standard cells (10,452 cells) and 129,162 µm² of macros |
| Clock | 20 ns (50 MHz) met in all corners; worst setup slack +3.86 ns (slow corner), worst hold slack +0.106 ns |
| Signoff | KLayout DRC 0 errors, LVS 0 differences, antenna 0 violations |
| Power estimate | 6.4 mW at 50 MHz (default switching activity) |

## Verification

- **Instruction decode:** exhaustive over all 65,536 instruction words and both suffix states, against expectations generated from `tools/isa/isa.yaml`, the single source of truth for every encoding.
- **Leaf modules:** ALU (80,000 random cases against an independent reference), load/store unit (against a byte-addressable reference memory), fault logic (exhaustive), scheduler and branch unit.
- **Whole design:** `verif/mda_e2e.py` runs assembled programs on the elaborated RTL, including the memories and loader ports, and compares registers, flags and data memory withthe separately written cycle-level model in `tools/eval_model/`. A directed program and hundreds of random three-thread programs match, and 25 deliberately injected plumbing bugs were each caught.
- **CI:** a cocotb test loads a program into the memories and checks the resulting data memory, and a gate-level test runs on the synthesized netlist.
- **Lint:** Verilator `-Wall` clean in the simulation-RAM, macro and generated-Verilog configurations.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/` | SystemVerilog RTL (`mda_*.sv`), the generated synthesis source `mda_synth.v`, SRAM macro stubs, `config.json` and the power-grid files |
| `spec/` | Architecture, instruction set, encoding, events and I/O documents |
| `docs/` | Stage A baseline report, positioning notes and images |
| `tools/` | `isa/` (encoding generator and checks), `eval_model/` (assembler and cycle-level simulator), `gen_synth.py`, `sync_sources.py`, `lint.sh` |
| `verif/` | Verification: decoder harness, end-to-end differential test, and the interpreter they run on |
| `fw/` | Firmware used to evaluate the instruction set |
| `test/` | Tiny Tapeout cocotb test and simulation models of the macros |
| `macro/` | SRAM macro LEF files used by the power-stripe step |
| `rtl.f` | The ordered source list; `info.yaml` and `test/Makefile` are generated from it |

## Build and check

Run from the repository root. `lint.sh` needs Verilator (MSYS2 UCRT64 shell); `gen_synth.py` needs [sv2v](https://github.com/zachjs/sv2v).

```
python3 tools/isa/isa_gen.py --check          # encodings, tables and documents agree
python3 verif/harness_decoder.py              # exhaustive decoder test
python3 verif/mda_e2e.py directed             # directed program against the reference simulator
python3 verif/mda_e2e.py fuzz --count 100     # random three-thread programs
bash tools/lint.sh                            # Verilator lint, three configurations
python3 tools/gen_synth.py                    # regenerate src/mda_synth.v after RTL changes
python3 tools/sync_sources.py                 # update info.yaml and test/Makefile from rtl.f
```

The SystemVerilog is the source of truth. Tiny Tapeout's tools read the design with a Verilog front end that cannot parse package imports, so CI synthesizes `src/mda_synth.v`, generated from the SystemVerilog with sv2v and committed. `python3 tools/gen_synth.py --check` reports when it is stale.

## Documentation

- [Instruction set](spec/Instruction%20Set%20and%20Assembly/Instruction%20Set.md), [encoding](spec/Instruction%20Set%20and%20Assembly/Instruction%20Encoding.md) and [assembly syntax](spec/Instruction%20Set%20and%20Assembly//Assembly.md)
- [Threading](spec/Processor%20Architecture/Threading.md), [events](spec/Processor%20Architecture/Events.md) and [I/O interface](spec/Processor%20Architecture/I-O%20Interface.md)
- [Stage A microarchitecture](spec/Processor%20Architecture/Stage_A_Microarchitecture.md).
- [Stage A baseline report](docs/Stage_A_Baseline.md)

## Third-party material

- The power-stripe step (`odb_sram_stripes.py`, `librelane_plugin_sram_pdn.py`) is adapted from [kdp1965/protocol-emulator](https://github.com/kdp1965/protocol-emulator) (cmos5l), which in turn follows the approach of `ihp-um-janestreet-prism`. Check the licenses of those projects before redistributing.
- SRAM macros and PDK: IHP Open PDK (SG13CMOS5L). Flow: Tiny Tapeout `tt-gds-action` with LibreLane. Project template: Tiny Tapeout.

## AI assistance

AI assistance (Claude) was used for drafting RTL, building the verification tooling and writing documentation. Design decisions, review and testing are the author's.

## License

Apache-2.0, see `LICENSE`, except for the third-party files above, which keep their own terms.
