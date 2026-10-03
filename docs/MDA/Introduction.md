The Minimalist Deterministic Architecture (MDA) is a CPU architecture aimed to prioritize deterministic execution, modularity in design, compatibility with other devices, while maintaining a small area footprint and being highly efficient. It is being constructed for the [Jane Street Protocol Emulator Challenge 2026](https://blog.janestreet.com/protocol-emulator-asic-competition/).

## Core Specification and Features
### Core Architecture
- Minimalist 3-thread CPU 3-stage pipelined (IF/ID/EX) CPU core
- Interleaved Barrel Processing - Switches between 3 independent hardware threads in a strict round-robin order
- Hazard Handling - None. Hazards are avoided within the design itself.
- Timing Model - 100% Deterministic. This avoids stalls and makes sure that every single instruction is predictable.
### Instructions and Memory
- 16-bit Instruction width (constant, 2-byte alignment)
- Minimally Variable Encoding between instruction types
- 16-bit Word Width
- Minimal Register file with 8 GPRs per thread (24 total)
- Memory-on-chip approach. Fast SRAM with zero extra cycles of mem-access penalty.
### ISA
- Minimalist Dual-nature Instruction Set, includes both core operational and execution instructions, along with special types of architecture specific instruction to aid with determinism.
- Encoding is based on the instruction type, with minimal variation of fields between different instructions to keep decoder complexity low.
- Types of instructions -
	- Operational - CPU Execution Instructions (Register, Immediate, Mem Access, Jump/Branch)
	- Spatial - Interfacing with CPU's direct I/O modules
	- Temporal - Deterministic time control, such as delays and edge tracking
### Target Features -
*Note: Largely implemented in software.*
- UART, SPI, I2C
- USB, 10Mb Ethernet
- (Other protocols) JTAG, SWD, PS/2, CAN Bus
- FPGA Implementation