# MDA protocol evaluation

*\<Disclaimer: This Evaluation was conducted using Claude to quickly help assess the feasibility of the architecture with different protocols as designed in MDA.\>*

Firmware results for UART, SPI and I2C, quick feasibility for PS/2, JTAG, SWD, 1-Wire and CAN, and an architecture study for USB and Ethernet.

Date: 3 Nov 2026. Based on the spec docs after the 2 Nov fixes (`Instruction_Set`, `Events`, `I-O_Interface`, `Threading`, `Assembly`). The spec is treated as locked. Everything marked "proposal" is for you to decide.

## 0. How much to trust this

- Every number below that says **measured** comes from a cycle-level model I wrote from the spec (`tools/mda_sim.py`), running real MDA assembly (`fw/*.s`) against protocol models (`tools/mda_dev.py`). It is **not** your reference model and **not** the RTL. It encodes my reading of the spec, and section 4 lists every place where I had to assume something.
- The device models (the "other end" of each protocol) are mine too. Three of the bugs I found along the way were in my own models (engine events applied one cycle late relative to the pad, watcher events visible a cycle early, and an I2C master that ignored tLOW after START), which is a reminder that checkers need independent checkers.
- Not modelled: pad delays and the Tiny Tapeout IO mux, analog behaviour, glitches, and gate-level effects. Real SPI/I2C limits will be lower than the model's where pads matter.
- Sections 6 and 7 (other protocols, USB, Ethernet) are paper analysis, with confidence levels stated.
- Confidence labels: **high** = arithmetic or directly measured, **medium** = measured in the model but depends on an assumption, **low** = paper estimate.

## 1. Summary

| Protocol | Result (measured in the model) | Primitives used | Code size | Verdict |
|---|---|---|---|---|
| UART TX | Decodes correctly up to 8.3 Mbaud (DIV=6, the highest tested), exact bit widths. Gap between back-to-back frames 11-13 cycles | engine (10-bit frames), `push`/`outp`, `waitev` | 28 halfwords | Works, pad-limited |
| UART RX | 1 Mbaud back-to-back, fails at 1.25 Mbaud. Tolerates +-4% baud error at 115200. 12 instructions per byte, awake 0.83% of slots at 115200 | NEG watcher, `dl`, engine (9 bits), `pull` | 27 | Works |
| SPI master | Mode 0, 32-bit word with no gap, 8-bit words with a 23-cycle gap. Max SCLK depends on slave delay (table 2.3) | engine clock-out, duplex, direct CS | 54 | Works |
| SPI slave, preloaded frame | 8.3 MHz in the model (about 4-6 MHz realistic). Aborted frames handled | engine clock-in, gate role, `ENG_ABORT` | 32 | Works |
| SPI slave, register read | Up to 1.14 MHz (decode must finish in half a clock) | same, plus table lookup | 36 | Works |
| I2C master | 388 kHz max, all fast-mode timings met, clock stretching, timeout | `wpin`/`rpin`, open-drain, `dl`, `TMR` | 119 | Works |
| I2C slave | Fast-mode corners pass (tLOW/tHIGH at the minimum, tSU;DAT 100 ns, 12/12 start phases). Clean to about 670 kHz. No clock stretching | polling, `rpin`, `wpin`, watcher for the idle state | 109 | Works, but needs a thread in polling mode |
| UART to SPI to UART bridge | "ABCD" in, "QRST" out, 4.5 us hand-off latency, 0 faults | 3 threads, doorbells, mailboxes | 88 | Works |
| Determinism twin-run | Victim pin waveforms identical to the cycle with a thread raising 14,544 faults and a doorbell storm | n/a | n/a | Passes (in the model, by construction) |

Total firmware for all seven protocol programs is about 405 halfwords, which is about 40% of a 1024x16 instruction memory and about 79% of a 512x16 (see section 8).

Biggest architecture findings, detailed in sections 3 and 5:
1. **Synchronizer compensation** of the engine's sample strobe doubles the usable SPI master clock. It is a very cheap change.
2. **I2C START/STOP detection** is the one place where the current watchers are not enough. A polled slave works, and costs a whole thread. A "qualified edge" watcher would fix it at small cost.
3. **The word-to-word gap** is 4-8 slots in real firmware, not the 2-3 slots the I/O doc says. This matters for USB and Ethernet.
4. **Conditional jumps (+-32)** forced 8 hand-written trampolines. `$jof` already solves this, the checker just did not expand it.

## 2. Core protocols

All programs follow the default pin ownership (pin n belongs to thread n mod 3), so no ownership transfers are needed.

### 2.1 UART (`fw/uart_tx.s`, `fw/uart_rx.s`)

Full duplex needs two threads because there is one engine per thread: RX on thread 0 (pin #0), TX on thread 1 (pin #10).

**TX.** One engine run sends a 10-bit frame: bit 0 is the start bit, bits 1-8 the data, bit 9 the stop bit. The thread builds the next frame while the current one is on the wire, so the only gap is the `push` + `outp` latency: **11-13 cycles** between frames at every baud rate tested. That stretches the stop bit by 0.3% at 115200 and by about 7% at 3 Mbaud, which receivers tolerate. The bit widths are exact: every run width in the waveform is a multiple of DIV except the stretched stop bit.

**RX.** A falling-edge watcher on the RX pin wakes the thread (`waitev`). The thread disarms the watcher (data bits would set `OVR`), waits `dl` until the middle of the start bit, and launches `inp 9` (8 data bits and the stop bit). The engine's rule that the first sample comes DIV cycles after launch puts it in the middle of data bit 0, so the rest follows with no software. `pull r2, 23` aligns the 9 LSB-first bits, and the stop bit is checked for framing.

Alignment arithmetic (so you can reuse it): wake takes 6-8 cycles from the pad edge, so `WAITDL = floor((DIV/2 - 10) / 3) * 3` puts the launch within 2 cycles of the middle of the start bit.

| Test | Result |
|---|---|
| Back-to-back frames, zero baud error | 115200, 230400, 460800, 921600 and 1 Mbaud (DIV=50) pass. 1.25 Mbaud (DIV=40) fails |
| Baud error at 115200, 16 back-to-back bytes | +-4% passes, +-5% fails |
| Sender start phase (12 offsets, DIV 434 and 54) | 12/12 pass |
| Cost | 12 executed instructions per byte, awake 0.83% of the thread's slots at 115200 |

My reading of why 1 Mbaud is the limit: after the engine finishes (middle of the stop bit), the loop needs about 24 cycles to be back in `waitev`, and the next start bit arrives half a bit later. At DIV=40 that is 20 cycles, so the thread is late and the `dl` alignment is lost. Confidence: high (measured, and the arithmetic agrees).

Compared with the earlier paper estimate ("comfortable to about 460 kbaud"): the receiver is better than expected.

### 2.2 SPI master (`fw/spi_master.s`)

Pins: MISO #2, MOSI #8, SCLK #11, CS #14, all owned by thread 2. Mode 0, MSB first, duplex engine. CS is a direct pin, and its initial level comes from the idle-level bit (assumption A8).

- **32-bit word:** one `inp 32` shifts the whole word, with no gap and no software inside. The ID read returned `0x00EF4018` correctly.
- **8-bit words with CS held low:** the SCLK gap at each byte boundary is **23 cycles** (about 8 slots) on top of the normal clock period. Effective throughput at DIV=4 is 4.6 Mbit/s instead of 6.25.

**Maximum SCLK.** The engine samples the synchronized MISO pin, which is 2 cycles old. The slave's clock-to-MISO delay (tCO) therefore eats into the half period:

| DIV (SCLK) | tCO = 1 cycle (20 ns) | tCO = 2 (40 ns) | tCO = 3 (60 ns) | tCO = 4 (80 ns) |
|---|---|---|---|---|
| 8 (3.1 MHz) | ok | ok | ok | ok |
| 5 (5.0 MHz) | ok | ok | ok | FAIL |
| 4 (6.25 MHz) | ok | ok | FAIL | FAIL |
| 3 (8.3 MHz) | ok | FAIL | FAIL | FAIL |
| 2 (12.5 MHz) | FAIL | FAIL | FAIL | FAIL |

Without compensation the rule is **DIV >= tCO + 2**. If the engine delays its sample strobe by 2 cycles so that it samples the pad value at the nominal instant (**proposal P1**), the rule becomes **DIV >= tCO**: 6.25 MHz works with tCO up to 4 cycles, and 12.5 MHz works with tCO = 2. The cost is that completion arrives 2 cycles later. Confidence: medium (model result; the pad and IO mux delays are not modelled).

### 2.3 SPI slave (`fw/spi_slave_frame.s`, `fw/spi_slave_reg.s`)

Pins: SCLK #1 (clock-in role), CS #4 (gate role plus a rising-edge watcher), MOSI #7 (data-in), MISO #10 (engine data). Thread 1.

**Preloaded frame (ROM-like device).** The whole response (8 dummy bits, then a 24-bit ID) is loaded into the OSR **before CS falls**, and one 32-bit duplex run handles the frame. The first MISO bit is on the pin from the launch, as the I/O doc specifies. After the frame the thread stores what the master sent, waits for CS to rise, clears the event and re-arms.

- MISO becomes valid **3 cycles (60 ns) after the SCLK falling edge** (2 synchronizer cycles + 1 output register). The model works down to a 3-cycle half period (8.3 MHz) with zero setup margin, so I would call **4-6 MHz** realistic once pad delays and a master's setup time are included.
- Re-arm: the slave needs about **12 cycles** between CS rising and the first SCLK edge of the next frame (CS high time plus CS-fall-to-first-clock).

**Register read (command decode).** After the command byte the response must be driven within half a clock, so the table sits at data address 0 and the command byte is used directly as the address. The critical path is `waitev` wake, `jof` (aborted-frame check), `pull`, `lb`, `push`, `inp`. It works up to **1.14 MHz** (22-cycle half period) and fails at 1.25 MHz, in line with the earlier paper estimate of about 1 MHz. An aborted frame (CS rising after one byte) is handled with `ENG_ABORT` and was tested.

Findings:
- The gate role is what makes both variants possible: the engine can be armed early and ignores clock edges while CS is high.
- If the gate deasserts mid-frame the engine does nothing by itself (assumption A7), so software has to abort. That is what the watcher on CS is for.
- **MISO cannot be tri-stated.** MISO is on a `uo` pin (output only), and the engine drives it from the launch, even while CS is high. This is fine for a single slave. On a shared SPI bus it conflicts with other slaves. The workaround is a `uio` pin with open-drain and an external pull-up, which limits speed. A small option (**proposal P4**) would make an engine-driven `uio` pin's output enable follow the gate.

### 2.4 I2C master (`fw/i2c_master.s`)

SCL #18, SDA #21 (`uio`, owned by thread 0), configured as direct, open-drain, idle high. Software bit-banging: `wpin` releases or pulls the line, `rpin` reads it back (so stretching is visible), `dl` sets every phase. Nested calls use different link registers (`$call`/`$ret` use `rad`; the bit routine uses `jmp r5` / `jrg r5, r5, 0`), so no stack is needed.

Test: write 2 bytes to register 0x10 of device 0x50, then repeated-START read both back (ACK, NACK), against an EEPROM-like slave model. Everything read back correctly.

Timing measured on the pads (fast-mode minimums in brackets):

| Parameter | Measured min | Spec min |
|---|---|---|
| tLOW | 1440 ns | 1300 |
| tHIGH | 1140 ns | 600 |
| tSU;STA | 1020 ns | 600 |
| tHD;STA | 720 ns | 600 |
| tSU;STO | 1020 ns | 600 |
| tBUF | 1620 ns | 1300 |
| tSU;DAT | 240 ns | 100 |
| tHD;DAT | 20 ns | 0 |
| SCL period (min) | 2580 ns (**388 kHz**) | 2500 |

My first version had a minimum period of 2340 ns, which is above the fast-mode frequency limit even though every individual time met its minimum. It had to be retuned by lengthening `THI`. This is the kind of thing only a measurement catches.

- **Clock stretching:** survives a slave holding SCL low for up to 20 us after every byte. The poll loop waits 6 cycles before its first read, because a read right after the release returns the old (synchronized) level.
- **Timeout:** a `TMR` armed per transaction gives up when the bus is stuck, releases both lines and sets an error marker (tested with a slave that holds SCL for 100,000 cycles).
- Cost: 12 instructions executed per bit, 119 halfwords.

### 2.5 I2C slave (`fw/i2c_slave.s`)

SCL #19, SDA #22 (thread 1), address 0x2A, 32-byte register file at address 0. Write: `[addr+W][pointer][data...]`. Read: `[addr+R][data...]`, including repeated START.

**Why the engine is not used for the bits.** START and STOP are SDA changing while SCL is high. They have to be recognized while a byte is in flight (a repeated START arrives instead of the first bit of the next byte). A pin watcher fires on every SDA edge, data edges included, and cannot say what SCL was at that instant. So the slave is **fully polled**, and the thread is busy for the whole transfer. It sleeps (`waitev` on an SDA falling-edge watcher) only while the bus is known to be free.

Two real races found and fixed during the work (both would pass a casual test):
1. In the first-bit loop I read SCL and then SDA. If the master changes SDA right after SCL falls (hold time can be 0 ns), SDA looks changed while SCL looked high: a false START/STOP. Reading **SDA first, then SCL**, removes it.
2. After a foreign address I used the sleeping watcher and read SCL once, 6-8 cycles after the SDA edge. With the minimum data setup (100 ns = 5 cycles), a data edge can already have SCL high by then, which looks like a START. The fix is a **bus tracker**: poll with the SDA-before-SCL order and count a change only if SCL was high on two consecutive iterations.

Results:

| Test | Result |
|---|---|
| 100 kHz, 400 kHz nominal, and the fast-mode corner (tLOW 1300 ns, tHIGH 600 ns, tSU;DAT 100 ns, tHD;DAT 0) | pass, 12/12 master start phases each |
| Foreign address (0xA0) | ignored, register file untouched |
| Faster masters | clean (correct data and no late ACK/data) down to a 1.48 us period (about 670 kHz). 800 ns tLOW starts to show late SDA. 1 MHz fails |

Limits: no clock stretching by the slave, no general call, no 10-bit addressing. The thread does nothing else during a transfer. The allowance for driving data or ACK after SCL falls is 0.9 us (45 cycles), and the master model's late-SDA counter stays at 0 down to a 1.48 us period, so the reaction time is within budget. It is still the least elegant of the programs.

**Proposal P2 (qualified-edge watcher).** Use the reserved watcher mode `011`: the event fires on an SDA edge only if the thread's clock-in pin (SCL) is high at that same synchronized instant. That makes START/STOP a clean sticky event, removes both races, and lets a sleeping `waitev` replace the polling. The cost is one AND gate and some decode per watcher. It would also fix the idle-state weakness (a data edge followed by SCL within 5 cycles).

### 2.6 UART to SPI to UART bridge (`fw/bridge.s`)

Thread 0 (UART RX) rings thread 2 (`flg @ring_prev`), which does an SPI frame and rings thread 1 (UART TX). Data moves through two one-byte mailboxes, and the doorbells only say "ready". Thread 2 sees the ring as `MSG_N`, thread 1 as `MSG_N` as well (the sender is each one's "next" thread), consumed with `waitev ... @consume`.

- "ABCD" in, "QRST" out (the SPI device returns `command + 0x10`), no faults, no `OVR`, no framing errors.
- Latency from the end of the received stop bit to the start of the transmitted frame: **0.2 us** for the first byte (the hand-off itself takes about 4.5 us from the middle of the stop bit). In a back-to-back stream the lag grows by 25 cycles per byte (the bridge's TX loop is not pipelined like `uart_tx.s`, so it leaves about 25 cycles between frames), so a long stream needs a ring buffer instead of one mailbox.
- Doorbell latency is as documented: `MSG_P` after 1 cycle, `MSG_N` after 2.

## 3. How the architecture stacks up

What worked well:
- **Cycle-exact bit timing without software.** UART and SPI wire timing is exact (all run widths are multiples of DIV). Software only sets up and tears down.
- **The `waitev` condition set and the doorbells** made multi-thread flow control very short (the whole bridge is 88 halfwords).
- **Sleeping costs nothing.** UART RX is awake 0.83% of the time, so one thread can serve many slow tasks.
- **Fault model as a debugging tool.** The model caught my misaligned `sw` (a data word after an odd-length string), which would have been invisible on a core without alignment faults.
- **Flexible link registers** in `jmp`/`jrg` allow nested calls with no stack.

What was awkward or limiting:
- **Word-to-word gap** (see section 7): 11-13 cycles for UART frames and 23 for SPI bytes, against the 2-3 slots (6-9 cycles) in the I/O doc.
- **Conditional jump range (+-32 halfwords):** I wrote 8 trampolines by hand (3 in the I2C master, 5 in the slave). The `$jof` pseudo-instruction already expands these, the checker just did not implement it.
- **No zero register and no `andi`:** masks and zeros take a register (`r0 = 0`, `r7 = 1` in most programs). The I2C slave uses all 8 registers.
- **`rad` hazard:** I clobbered `r1` inside a routine called with `$call` and returned to address 0. A lint that warns when a call target writes `rad` would catch this.
- **Alignment hazard:** `.word` after an odd-length `.asciz` silently misaligns. The assembler should align `.word`, or warn.
- **One engine per thread** forces two threads for full-duplex UART.
- **Event wake-up latency** is 6-8 cycles (measured, matching the doc), which is fine for UART/SPI/I2C but sets a floor for fast reaction loops.

## 4. Spec assumptions I had to make

Each is marked ASSUMPTION in `tools/mda_sim.py`. They need a definition in the docs, or my results shift.

| # | Assumption | Why it matters |
|---|---|---|
| A1 | An instruction at cycle t affects pins and launches the engine at t+1 | The spec says "a fixed delay". UART RX alignment (`WAITDL`) depends on it |
| A2 | The readable pin level is the pad value 2 cycles earlier. A watcher event is visible 3 cycles after the pad edge | Gives the documented 6-8 cycle wake-up |
| A3 | `dl N` resumes at the first slot at or after N cycles, never sooner than the next slot | Delays of 0-2 are one slot |
| A4 | The engine does not compensate its sample strobe for the synchronizer delay | See P1 |
| A5 | Master CPHA=1: data changes on the leading edge, sample on the trailing edge (not exercised) | `ENG_CTL` phase is undefined in the docs |
| A6 | Slave mode: the clock-in pin's idle-level bit is CPOL. Only CPHA=0 is modelled. I2C (CPOL=1, CPHA=1) is not | Needed before any engine-based I2C slave |
| A7 | If the gate deasserts mid-transfer, the engine ignores clock edges until `ENG_ABORT` | Firmware must abort explicitly |
| A8 | A direct-driven pin starts at its idle level | Otherwise CS glitches low between `cfg` and the first `wpin` |
| A9 | A slave transfer completes at the n-th trailing edge, detected 2 cycles late, flag visible a cycle later | |
| A10 | The ISR is cleared at `inp` launch; the OSR is shifted by the engine | |
| A11 | `uo` pins cannot be tri-stated, so an engine-driven MISO on a `uo` pin drives while CS is high | Shared SPI buses |
| A12 | `rpin @level` works on a `uio` pin that is being driven open-drain | I2C needs it |

## 5. Proposals

None of these are in the spec. Each row says what it costs and what it buys. Order is by value for effort.

| # | Proposal | Cost | Buys | Recommendation |
|---|---|---|---|---|
| P1 | Delay the engine's sample strobe (and completion) by the 2 synchronizer cycles | A 2-cycle delay line on the strobe, 2 cycles later completion | SPI master usable at about 2x the clock for the same slave (table 2.2) | **Accept**, very cheap, low risk |
| P3 | Define A1-A12 in the docs, and correct the "2-3 slot" word-gap figure to 4-8 slots (measured 11-23 cycles) | Documentation | Fewer surprises in RTL | **Accept** |
| P5 | Tooling: expand `$jof/$joc` far forms, auto-align `.word`, lint for `rad` writes in call targets | Assembler work | Removes 3 bug classes I hit | **Accept** |
| P6 | Reserve free `ENG_CTL` bits (continuous mode, Manchester) and a per-pin output-invert bit | Zero logic, just reserved codes | Keeps the USB/Ethernet door open | **Accept now** |
| P2 | Qualified-edge watcher on reserved mode `011` (SDA edge qualified by SCL high) | About 1 gate per watcher plus decode | Race-free START/STOP, sleeping I2C slave | Decide during Stage B. Not required, the polled slave works |
| P4 | Output enable of an engine-driven `uio` pin follows the gate role | A few gates | Multi-slave SPI MISO | Low priority |
| P7 | Shadow ISR/OSR with a continuous-run mode | About 192 flops (about 9.4k um2 at the 49 um2 per flop seen in the dry run), plus muxes, roughly 0.3 tile | Gapless streaming, needed for USB and Ethernet | **Decision gate**, see section 7 |
| P8 | Per-pin output invert (complementary pair) | 24 flops | Differential USB D+/D-, Ethernet TD+/TD- | With P7 |
| P9 | Line-coding modes in the engine (Manchester, NRZI, bit-stuffing) | A few gates per engine | Removes software encoding at 12 Mb/s-class rates | After P7 |

## 6. Quick feasibility: PS/2, JTAG, SWD, 1-Wire, CAN

Paper analysis only (no firmware was run), using the engine and timing facts measured above. 1 slot = 3 cycles = 60 ns.

| Protocol | Verdict | How it would be done | Main risk | Confidence |
|---|---|---|---|---|
| **PS/2** (device to host and host to device) | Easy | Clock is 10-16.7 kHz (3000-5000 cycles per bit). Receive with a clock-in engine, falling-edge sampling (CPOL=1, CPHA=0 is the supported combination): `inp 11`, parity in software. Host to device: pull CLK low for 100 us (`dlrg`), pull DATA low, release CLK, then clock data out. Both lines on `uio` open-drain with external pull-ups. About 60 halfwords | Exactly when the host must change data during the host-to-device frame needs checking against the PS/2 spec | High (receive), medium (transmit) |
| **JTAG master** | Feasible, TCK up to about 8 MHz (DIV=3) | TCK from the engine clock-out, TDI/TDO from engine data, TMS a direct pin. TMS must change on specific TCK edges, so a shift of n bits is split: n-1 bits with TMS=0, then 1 bit with TMS=1, with a short clock pause between engine runs (legal in JTAG). Navigating TAP states is 1-bit runs | Overhead of the split runs for short scans | Medium-high |
| **SWD master** | Probably, up to about 2 MHz | SWCLK from the engine. SWDIO must switch direction at the turnaround: a `cfg #PIN` between phases (fits in one clock period at 1-2 MHz). Request (8 bits), ACK (3), data (32 + parity) as separate engine runs | Open-drain cannot drive SWDIO high fast enough, so direction must be switched with push-pull. Clock pauses mid-transaction need target tolerance | Medium |
| **1-Wire master** | Easy | `wpin` / `rpin` / `dl` on an open-drain `uio` pin. Reset, presence detect and slots are 1-480 us (50-24,000 cycles). `dl` resolution is 60 ns. Overdrive slots (1 us low, 8 us total) are 133 slots, plenty. Search-ROM logic in software. `TMR` for timeouts | None significant | High |
| **CAN, 125-250 kbit/s** | Plausible, software only | A bit is 400/200 cycles (133/66 slots). Per bit: sample point (`rpin`), arbitration compare, bit stuffing counter, CRC-15 update, and hard-sync on edges (watcher plus `TMR` restart). I estimate 25-35 slots per bit, so it fits at 250 kbit/s with the thread dedicated | The estimate is mine, not measured. Needs an external transceiver (3.3 V logic) | Medium-low |
| CAN at 500 kbit/s or more | Not realistic in software | 33 slots per bit is too tight. Pre-stuffed transmit through the engine would need gapless words | | High |

Other UART-like protocols (DMX, LIN, IR codes) fit the same engine pattern as the UART.

## 7. USB and Ethernet: architecture study

This section does not change the locked spec. It collects what would have to change, what it costs, and what it enables, so you can decide at a gate.

### 7.1 What the protocols demand, against what the engine does today

Measured in this evaluation: the gap between two engine runs is **11-13 cycles** (UART frames, 2 slots of preparation plus `push`/`outp`/loop) and **23 cycles** for SPI bytes. The sample strobe is 2 cycles late (assumption A4). The engine's smallest tested divisor was 6 for UART transmit. All of this is fine up to a few Mbit/s and wrong by a wide margin for the rates below.

| Protocol | Bit time at the chosen clock | Gap tolerance | Today |
|---|---|---|---|
| USB low-speed (1.5 Mb/s) | 666 ns = 32 cycles at 48 MHz (33.3 at 50 MHz) | none inside a packet | A gap of 11-23 cycles is a third to two thirds of a bit |
| USB full-speed (12 Mb/s) | 83 ns = 4 cycles at 48 MHz | none | Out of reach without the changes below, plus hardware clock recovery on receive |
| 10BASE-T (10 Mb/s Manchester) | 100 ns = 4 cycles at 40 MHz, half-bit = 2 cycles | none | At 50 MHz a half-bit is 2.5 cycles, which cannot be made |

**Clock.** USB and Ethernet need a different clock than the 50 MHz target. 48 MHz gives exactly 32 cycles per low-speed USB bit, and 40 MHz gives exactly 4 cycles per 10BASE-T bit. Both are slower than 50 MHz, so timing closure is easier. A different clock means it is set by the demo board (other entries document that the Tiny Tapeout clock input is specified to about 66 MHz). The effect of the IO mux and pad bandwidth at 20-40 MHz toggling has not been checked anywhere in this work and is a real risk. Confidence: high on the arithmetic, low on the pads.

### 7.2 Candidate changes

| Option | What it adds | Rough cost (low confidence) | Enables |
|---|---|---|---|
| 0. No change | | | UART, SPI, I2C and the section 6 protocols |
| 1. Gapless streaming (P7) | Shadow ISR/OSR, a continuous-run bit in `ENG_CTL` | About 0.3 tile, new states to verify | Transmit or receive streams of any length with no gap. The prerequisite for everything below |
| 2. Complementary pin pair (P8) | Output-invert bit per pin | 24 flops | Differential USB D+/D-, Ethernet TD+/TD- |
| 3. Line coders (P9) | Manchester encode, NRZI, transmit bit-stuffing | A few gates per engine | Less software on the transmit path, optional (software can pre-encode, since the data is known in advance) |
| 4. Fast capture | `inp` at DIV=1 with the shadow register pulled every 32 cycles (about 10 slots) | None beyond option 1, check the pin rate | Raw oversampled receive into memory, decode in software afterwards |
| 5. Second engine per thread | Independent TX and RX | Large | Full duplex in one thread. Not needed for USB or Ethernet |

### 7.3 What each stretch goal would need

**USB low-speed as a device (the realistic one).** Needs options 1 and 2, and the 48 MHz clock.
- **Transmit:** software pre-computes the whole packet (sync, PID, data, CRC, bit-stuffing and NRZI) as line states, and the engine shifts them gaplessly. End-of-packet (SE0 for two bit times) is done with direct writes, since both lines low is not a complementary state. Per-bit budget is generous.
- **Receive from the host:** the host's clock is accurate to 500 ppm, so a fixed-rate sample of 32 cycles per bit is fine for a packet of up to about 100 bits (drift 0.05 bit). This is why the device role is much easier than the host role.
- **The hard part is the response deadline.** A device must answer within about 7.5 bit times (about 80 slots at 48 MHz; from memory, check the USB 2.0 spec). A trick that may make it fit: since the device knows its own address and endpoints, it can **precompute the raw line pattern of every token addressed to it** (the CRC5 included) and just compare the received raw words with a short table (about 3 slots per candidate), with no NRZI or destuffing in the deadline path. Data packets need the CRC-16 check before the ACK, which has to be computed on the fly while receiving, at about 10 slots per bit.
- **USB host or full-speed:** not realistic here. A host has to receive from a device that is only accurate to 1.5%, which needs clock recovery, and 12 Mb/s is 4 cycles per bit.
- Verdict: **possible with options 1 and 2, with a real deadline risk**. Confidence: low (paper only, no firmware).

**10BASE-T Ethernet.** Needs options 1 and 2, and a 40 MHz clock.
- **Transmit only:** software pre-encodes the frame as Manchester half-bits (a minimum frame is 576 bits, so 1152 half-bits, about 144 bytes), the engine shifts it gaplessly at DIV=2 (2 cycles per half-bit), and `TMR` generates the link pulses. The CRC32 is computed before sending, with no deadline. A word of 32 half-bits lasts 64 cycles, so refilling the shadow register is easy.
- **Receive:** a comparator or PHY is required outside the chip. Capture oversampled raw samples (4 per bit, 576 x 4 = 2304 bits = 288 bytes for a minimum frame) with option 4, and decode in software afterwards, locking onto the stream's own edges, which removes the clock drift problem. Short frames only: the 4 KB data memory limits this to a few hundred bytes of capture.
- **Electrical:** the pins are 3.3 V CMOS, so a real 10BASE-T connection needs magnetics and a differential receiver. A practical demo would be transmit into a scope or into an external PHY.
- Verdict: **transmit is plausible with options 1 and 2, receive of short frames with option 4, link negotiation not**. Confidence: low.

### 7.4 My recommendation

1. **Now, for free:** accept P6 (reserve the `ENG_CTL` bits and the pin invert bit) and P1. They do not add risk.
2. **Keep the scope locked** and publish the envelope table with the numbers from this document, including the arithmetic above for why USB and Ethernet are out of range of the current engine. A specific explanation of a limit reads as engineering, not as a gap.
3. **Decision gate in mid-December**, after the core and Stage B pass your lockstep tests. If you are ahead, option 1 is the single change that unlocks both stretch goals. Then pick one. USB low-speed device is more valuable and more fragile. 10BASE-T transmit is smaller.
4. Whichever you pick, write the firmware first (against the reference model), because the response-deadline and capture budgets are the things that decide feasibility.

## 8. Consequences for decisions already on the table

- **Instruction memory size.** The seven protocol programs in `fw/` total about 405 halfwords (code only, with some duplicated setup). A 1024x16 macro leaves about 600 halfwords for everything else (a loader tool, bridges, USB or Ethernet code). A 512x16 would hold these programs with only about 100 halfwords to spare, so it only makes sense if you drop the stretch goals. I would keep 1024x16.
- **Data memory:** none of these programs needs more than a few hundred bytes. 1 KB (256x32) is enough for them, but Ethernet capture would want more.
- **Spec doc edits** (your call): the word-gap figure in `I-O_Interface`, the assumptions in section 4, P1 and P6 if accepted.
- **Test plan:** `tools/run_determinism.py` is a template for the RTL twin-run test (same program, perturbed neighbours, compare pin waveforms, random initial state). The protocol models and the pass criteria transfer directly to a cocotb testbench. The two races found in the I2C slave and the phase-sweep method (12 start offsets) are the kind of cases your random tests should reach.

## 9. Files and how to run

```
mda-eval/
  MDA_Protocol_Evaluation.md      this document
  fw/                             the firmware (MDA assembly)
    uart_tx.s uart_rx.s spi_master.s spi_slave_frame.s spi_slave_reg.s
    i2c_master.s i2c_slave.s bridge.s determinism_noisy.s determinism_parked.s
  tools/                          Python 3, no dependencies
    mda_asm.py    assembler checker: 35 instructions, the pseudo-instructions the firmware uses, label and range checks
    mda_sim.py    cycle-level simulator
    mda_dev.py    protocol models and bus analyzers
    run_*.py      one test per program   sweep_*.py   speed and tolerance sweeps
```

Run from `tools/`: `python3 run_uart_rx.py`, `python3 sweep_spi_master.py`, and so on. Every `.equ` parameter in a firmware file can be overridden from a test (`mda_util.with_equ`).

The assembler checker does not produce binary and does not expand `$jof` / `$joc` far forms. It rejects out-of-range immediates and jumps, which is how the trampolines in section 3 were found.
