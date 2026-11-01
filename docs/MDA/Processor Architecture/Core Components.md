Given below are the core components of MDA. Most of this is tentative, and the area figures are rough estimates, to be checked using synthesis with the IHP sg13g2 library.

- **Threads and registers** - 3 threads, each with 8 GPRs (24 total), its own PC, local flags, ISR/OSR, a timer and a delay counter. There is no hardwired zero register.
- **Word width** - 32-bit data word, 16-bit instructions (locked). The register file is 768 flops, and the ISR/OSR (32 bits each, per thread) add 192 more. This allows 32-bit ISR/OSR, 32-bit timers, and a cheaper CRC32. Memory sizes are kept parametrizable.
- **ALU** - Add, logic operations, compares, and a barrel shifter. No hardware multiplier or divider (deliberate). The shifter is also used by `pull` and `push` for alignment.
- **Pipeline** - 3-stage IF/ID/EX barrel pipeline. Branches resolve in EX with no penalty, as the next instruction of the same thread is fetched 3 cycles later. An instruction followed by a suffix halfword (`lli`) takes two slots of its thread.
- **Memory** - Separate instruction and data memory, using single-port SRAM macros. A single shared macro would conflict, as the IF of one thread and the EX of another happen in the same cycle. The macro's 1-cycle read latency is hidden by the 3-cycle thread spacing.
    - The instruction memory is 16 bits wide. The PC is as wide as the instruction memory address, and wraps around, so there are no instruction fetch faults.
    - (TENTATIVE) The split between instruction and data memory, and their sizes, are decided later, based on the firmware size. Estimated sizes of the SRAM macros (from the Tiny Tapeout memory page) -

|Macro|Estimated area (tiles)|
|---|---|
|256x32|~1.6|
|512x32|~2.5|
|1024x32|~4.4|
|1024x16|~2.5|

- **Event and I/O hardware** - 24 pins shared by all threads, each with a per-pin watcher (3-bit mode and an event bit) and an ownership field (2 bits), all behind a 2-flop synchronizer and a "previous sample" flop that are shared by all threads. Each thread has one shift engine (TENTATIVE) with a 16-bit divisor, and its own timer. See [`I-O Interface.md`](/I-O%20Interface.md) and [`Events.md`](Events.md).
- **Boot** - SRAM is volatile, so the chip starts empty and a hardware loader fills it. The loader is a small FSM (not a program), kept separate from the CPU, as it has to write the instruction memory, which a program cannot do, and it needs no arbitration as the threads are held in reset while it runs. It runs on the system clock, and is reset-triggered, so a reset reloads the firmware.
    - **Pins** - The loader uses four fixed pins, and nothing about the existing pin hardware changes. It reads three input pins through the normal 2-flop synchronizers (so the load clock is just a data input, with no second clock domain), and drives one output pin. All other output pins are idle while loading. After loading, the four pins become normal pins with their default owners (see `I-O Interface.md`). (TENTATIVE) The pins are - load clock `#0`, load data `#1` and load enable `#2` (inputs), and load error `#8` (output).
    - **Load clock** - The host dictates the load clock, like an SPI slave. It has to be well below the system clock, as it is sampled by it. (TENTATIVE) System clock divided by 8, or slower.
    - **Protocol** - Everything is sent in 16-bit units (halfwords), which matches the instruction width and removes any byte order. (TENTATIVE) The bits of a halfword are sent MSB first. The enable pin is high for the duration of one command, and low between commands.
    - The commands are -

|Command|Code (TENTATIVE)|Followed by|
|---|---|---|
|`WRITE_I`|`0xA55A`|Offset, count, then `count` instruction halfwords|
|`WRITE_D`|`0x5AA5`|Offset, count, then `count × 2` halfwords (low half first)|
|`ENTRY0`|`0xC33C`|Start PC of thread 0|
|`ENTRY1`|`0x3CC3`|Start PC of thread 1|
|`ENTRY2`|`0x9696`|Start PC of thread 2|
|`GO`|`0x6969`|Checksum|

- **Loader rules** -
    - The codes differ from each other, and from all-zeros and all-ones, in at least 8 bits, so noise cannot turn one valid command into another. Anything that is not an exact match is an error.
    - Offsets and counts are in units of the target memory's word (one halfword for instruction memory, two for data memory). The data memory can be written too, so constant tables can be loaded with the firmware.
    - An `ENTRY` record carries only the start PC of that thread. The upper bits of the PC halfword must be zero, as the PC is only as wide as the instruction memory. All three `ENTRY` records are mandatory, and there is no hardware mechanism to disable a thread (see `Threading.md`).
    - The loaded code is decoupled from the entry points. The entry records and the writes can come in any order before `GO`, the host tool sends the entry records first, then the whole program, then `GO`.
    - `GO` carries a CRC-16 of every halfword received since reset, except the checksum itself. (TENTATIVE) A plain 16-bit sum is a cheaper alternative.
    - After a valid `GO`, the loader writes the PCs, hands the SRAM ports to the cores, and releases all three threads on the same cycle, a fixed number of cycles after the last bit of `GO`.
    - The loader sets the load error pin (active-high, low means OK) if it sees an unknown command code, an offset plus count past the end of the memory, a PC outside the instruction memory, `EN` dropping off a 16-bit boundary or in the middle of a command, a bad checksum, or a `GO` without all three `ENTRY` records. The error is sticky until reset, and the threads are not released while it is set. The host checks the pin after `GO`.
    - The GPRs are not initialized by loading. All other state is reset (see `Threading.md`).
    - The assembler produces the images and the three entry PCs, and a host tool (also used by the testbench) packs them into commands, so the load path is exercised in every simulation.
- **Clock** - Targeting 25-50 MHz until the real limit is verified.
- **Area (estimates for a 6x4 Tiny Tapeout IHP design)** - 24 tiles of about 200um x 150um, and roughly 1K logic cells (about 320 flops) per tile. Roughly 24K logic cells nominal, 15-18K realistically. The design is estimated at 8-10K cells, or about 10-11 tiles, plus the SRAM macros.
    - (TENTATIVE) A larger 8x4 design (about 30% more area) may become available, which is why memory sizes are kept parametrizable.