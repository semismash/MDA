The Minimalist Deterministic Architecture (MDA) is a CPU architecture aimed to prioritize deterministic execution, modularity in design, compatibility with other devices, while maintaining a small area footprint and being highly efficient. It is being constructed for the [Jane Street Protocol Emulator Challenge 2026](https://blog.janestreet.com/protocol-emulator-asic-competition/).

## Core Specification and Features

### Core Architecture

- Minimalist 3-thread 3-stage pipelined (IF/ID/EX) CPU core
- Interleaved Barrel Processing - Switches between 3 independent hardware threads in a strict round-robin order
- Hazard Handling - None. Many data hazards are avoided within the design itself.
- Timing Model - 100% Deterministic. This avoids many stalls and makes sure that every single instruction is predictable. Faults and events never change the timing of any thread other than the one waiting on them.
- Events and Faults - Hardware state changes are latched into per-thread flags and handled by software (no dedicated interrupts, a thread can be used as an event handler). Threads signal each other using doorbells and shared memory.
- I/O - 24 pins with per-thread ownership and per-pin watchers. Autonomous shift engines with a programmable divisor give cycle-exact bit timing, with the protocols themselves in firmware.

### Instructions and Memory

- 16-bit Instruction width (constant, 2-byte alignment), with a 16-bit suffix halfword after `lli`
- Minimally Variable Encoding between instruction types
- Word Width - 32-bit data word. 8 GPRs per thread
- Minimal Register file with 8 GPRs per thread (24 total)
- Memory-on-chip approach. Fast SRAM, with separate instruction and data memory. Zero extra cycles of mem-access penalty.
- Firmware is loaded into the SRAM by a small hardware loader at startup (TENTATIVE, see [`Core_Components.md`](Core%20Components.md)).

### ISA

- Minimalist Dual-nature Instruction Set, includes both core operational and execution instructions, along with special types of architecture specific instruction to aid with determinism. There are 35 instructions in total.
- Encoding is based on the instruction type, with minimal variation of fields between different instructions to keep decoder complexity low.
- Types of instructions -
    - Operational - CPU Execution Instructions (Register, Immediate, Mem Access, Jump/Branch)
    - Spatial - Interfacing with CPU's direct I/O modules
    - Temporal - Deterministic time control, such as delays and timers
    - Event - Observing, configuring and waiting on events, such as pin edges and faults

### Target Features -

_Note: Largely implemented in software._

- UART, SPI, I2C
- USB, 10Mb Ethernet
- (TENTATIVE) USB low-speed is considered realistic, 10Mb Ethernet and USB full-speed depend on the hardware assistance available.
- (Other protocols) JTAG, SWD, PS/2, CAN Bus
- FPGA Implementation