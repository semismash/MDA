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

- **Event and I/O hardware** - 24 pins shared by all threads, each with a per-pin watcher (3-bit mode and an event bit) and an ownership field (2 bits), all behind a 2-flop synchronizer and a "previous sample" flop that are shared by all threads. Each thread has one shift engine (TENTATIVE) with a 16-bit divisor, and its own timer. See [`I-O Interface.md`](I-O%20Interface.md) and [`Events.md`](Events.md).
- **Boot** - SRAM is volatile, so the chip starts empty and a hardware loader fills it. The loader is a small FSM (not a program), as it has to write the instruction memory, which a program cannot do, and it needs no arbitration as the threads are held in reset while it runs.
    - (TENTATIVE) A few fixed pins (clock, data, enable) feed the loader. It takes a write command (which memory, address, length, payload) and a final "go" command, which carries the entry PC of each thread and a thread enable mask. It is reset-triggered, so a reset reloads the firmware. After loading, the pins are normal pins.
    - (TENTATIVE) The loader can write the data memory as well as the instruction memory, so constant tables can be loaded with the firmware.
- **Clock** - Targeting 25-50 MHz until the real limit is verified.
- **Area (estimates for a 6x4 Tiny Tapeout IHP design)** - 24 tiles of about 200um x 150um, and roughly 1K logic cells (about 320 flops) per tile. Roughly 24K logic cells nominal, 15-18K realistically. The design is estimated at 8-10K cells, or about 10-11 tiles, plus the SRAM macros.
    - (TENTATIVE) A larger 8x4 design (about 30% more area) may become available, which is why memory sizes are kept parametrizable.
- **Deferred** - Dual core (6 threads), variable length instructions other than the constant-loading suffix, and half-word loads and stores (`lh` and `sh`).