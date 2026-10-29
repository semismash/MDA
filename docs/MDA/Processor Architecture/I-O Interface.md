Given below is the I/O interface design for MDA. Anything that is not final is marked (TENTATIVE).

- **Pins** - MDA has 24 general purpose I/O pins (`#0-#23`), shared by all threads. Protocols are implemented in firmware, there is no dedicated UART, SPI or I2C hardware.
    - The pins come in the three Tiny Tapeout groups, and a pin can only be given a role that its group is capable of. A role that a pin cannot do is an I/O fault.
    - (TENTATIVE) The assumed mapping of pin numbers to groups, to be confirmed against the template -

|Pins|Group|Capability|Notes|
|---|---|---|---|
|`#0-#7`|`ui`|Input only|Can be read and watched, never driven|
|`#8-#15`|`uo`|Output only|Drive 0 when their output source is off, as they cannot float|
|`#16-#23`|`uio`|Bidirectional|Needed for open-drain (e.g. I2C SDA and SCL), and for any pin that is both read and driven|

- **Pin ownership** - Every pin always belongs to exactly one thread, there are no unowned (orphan) pins. The owner is the only thread that can configure, drive or watch the pin.
    - At reset, pin `n` belongs to thread `n mod 3`, so every thread gets a mix of input, output and bidirectional pins (and at least 2 bidirectional pins, enough for one I2C bus each, without any transfer).

|Thread|Default pins|
|---|---|
|0|0, 3, 6, 9, 12, 15, 18, 21|
|1|1, 4, 7, 10, 13, 16, 19, 22|
|2|2, 5, 8, 11, 14, 17, 20, 23|

- Ownership rules -
    - Ownership is changed only by the current owner, using `cfg` on the pin (the value carries the new owner). A thread cannot take a pin from another thread, `cfg` on a pin that is not owned is a fault.
    - A transfer resets the pin to idle - output source off, roles cleared, watcher off, event bit cleared - so the new owner starts clean and no old events leak across. A transfer of a pin that is bound to a busy shift engine is a fault.
    - Reading the level of a pin using `rpin` is read-only and needs no ownership. Everything else (driving, event reads, watching, roles) needs it.
    - Ownership state is 2 bits per pin, 24 pins.
- **Pin configuration** - Each pin has a static configuration, set by its owner using `cfg` (target `PIN`) with a packed value in a register. There is no arbitration between sources, as the source of every output pin is selected statically.

|Field|Options| Meaning                                                                                       |
|---|---|---|
|Pin|`#0-#23`| The pin that is being configured                                                              |
|New owner|Thread 0, 1 or 2| Transfers ownership (see above)                                                               |
|Output source|Off, direct, engine data, engine clock| What drives the pin. `direct` means `wpin`                                                    |
|Input roles|Engine data-in, engine clock-in| What the pin feeds. A pin can have an input role and an output source together (e.g. I2C SDA) |
|Open-drain|On or off| When on, driving 1 releases the pin instead of driving it high (for I2C)                      |
|Watcher mode|`000`-`111`| Pin event detection, see [`Events.md`](Events.md)                                             |

- (TENTATIVE) Two more fields are proposed, to be decided - an **idle level** (what the pin drives from the engine while no transfer is running, e.g. high for UART TX and the SPI clock idle level), and a **gate** input role (the engine only shifts while the gate pin is asserted, e.g. chip select for an SPI slave, so the frame starts and aborts cleanly).
- **Input synchronization** - Every input pin goes through a 2-flop synchronizer followed by a "previous sample" flop. These are shared by all threads, and are used by `rpin`, the shift engines and the pin watchers (see [`Events.md`](Events.md)).
- **Direct access** - `rpin` reads from a pin directly into a register, and `wpin` writes a register directly to a pin. Each such access takes place in the thread's slot, so the timing is quantized to the 3-cycle slot rotation.
    - `wpin rs1, #pin` - Writes bit 0 of `rs1` to the pin (with open-drain on, 1 means release). The pin must be owned by the thread and have the output source `direct`, otherwise it is a fault.
    - `rpin rd, #pin, mode` - Reads from a pin, or from the pin event bits, depending on the mode -

|Mode|Returns|Needs ownership|
|---|---|---|
|LEVEL|The synchronized level of the pin (about 2-3 cycles old)|No|
|EVENT|The pin's event bit|Yes|
|EVENT+CLEAR|The pin's event bit, then clears it|Yes|
|PENDING|A mask of the event bits of all pins owned by the thread (bit `n` is pin `n`)|n/a|
|PENDING+CLEAR|The same mask, then clears exactly the bits that were read|n/a|

- The PENDING modes do not use the pin field. Three mode codes are spare. A mode that reads all 24 levels at once is a possible use for one of them (TENTATIVE).
- **ISR and OSR** - Each thread has its own input shift register (ISR) and output shift register (OSR), 32 bits wide like the word.
    - `pull rd, #shift` moves the ISR data into a register, and `push rs1, #shift` moves register data into the OSR. The shift amount uses the idle ALU shifter to align the data, e.g. LSB-first data of `n` bits lands in the top of the ISR, and `pull` with a shift of `32 - n` aligns it.
    - (TENTATIVE) `pull` shifts the ISR right by the amount, and `push` shifts left. `pull` clears `ISR_RDY`, and `push` clears `OSR_EMPTY`.
- **Shift engines** - Each thread has one shift engine (TENTATIVE, see below). `inp #count` and `outp #count` start a transfer of `count` bits (1 to 32) instead of moving a single bit per instruction. The pins the engine uses are configured beforehand using `cfg`, so the instructions only carry a count (TENTATIVE).
    - The engine samples (`inp`) or drives (`outp`) one bit every DIV clock cycles. It runs on the raw clock, independent of the thread's slot, so the bit timing is cycle-exact. Only the start of a transfer is aligned to the thread's slot, by a fixed delay.
    - The first sample of an input transfer happens DIV cycles after the launch. This is fixed, there is no configurable offset. For a UART receiver, launching at the middle of the start bit puts the first sample in the middle of the first data bit.
    - The instruction returns immediately, and the thread can do other work. When the transfer finishes, `ISR_RDY` (`inp`) or `OSR_EMPTY` (`outp`) is set. Completion means the end of the `n`-th bit period, not the moment of the last sample.
    - Pacing comes from the pin roles. With no clock-in role the engine is paced by the divider (UART, SPI master). With a clock-in role, it is paced by that pin (SPI slave, I2C slave).
    - In duplex mode, either `inp` or `outp` starts one transfer that shifts both registers, and completion sets both flags.
    - In clock-out mode, DIV is the half-period of the clock, so the clock pin toggles every DIV cycles.
    - When an output transfer is armed, the first bit is driven on the pin at the launch (so, for example, an SPI slave has its first bit ready before the first clock edge).
    - Launching `inp` while `ISR_RDY` is set clears it and sets `OVR`. A word that finishes before the previous one was pulled overwrites it and sets `OVR`.
    - Launching a transfer while the engine is busy, or with no engine pins configured, is a fault (`ERR`).
    - The engine can be stopped at any time using the abort target of `cfg`, e.g. when an SPI slave sees chip select rise in the middle of a frame.
    - DIV is a 16-bit per-thread divisor, set using `cfg`. Putting the divisor in the `inp` and `outp` instructions directly was considered, but there is no room for it.
    - With the engine, the per-bit instruction budget of a protocol disappears for shifting, the budget becomes the number of instructions between word transfers.
    - (TENTATIVE) There is a gap of about 2-3 slots between consecutive words, as the thread has to `pull` or `push` and relaunch. Continuous streams are therefore sent as frames of up to 32 bits per engine run. A shadow register would remove the gap, at an area cost.
    - (TENTATIVE) There is only one engine per thread, for both directions. A full duplex UART (receiving and sending at independent timing) therefore needs two threads. A second engine per thread would remove this, at an area cost.
- **Clock output** - A pin whose output source is `engine clock` is toggled by the engine, so a whole word can be clocked out with no software involvement (e.g. SPI). The polarity and phase come from the engine configuration. (TENTATIVE) Its area cost is to be confirmed with synthesis, it is the first feature to cut if area gets tight.
- **Open-drain** - For I2C, a pin with open-drain on only ever pulls low or releases. A pin that is released can still be read, so the thread can see another device holding the line (clock stretching).
- **Configuration** - `cfg #target, rs1` writes configuration to the issuing thread's own pins, engine or timer, with the value in `rs1`. It takes effect at the thread's next slot. It never touches another thread's resources.

| Target      | Value in `rs1`                                                       | Effect                                                                                     |
| ----------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `PIN`       | Pin, new owner, output source, input roles, open-drain, watcher mode | Full configuration of an owned pin. Clears the pin's event bit                             |
| `WATCH`     | Pin, watcher mode                                                    | Watcher only, on an owned pin. Clears the event bit, so it is the cheap way to re-arm      |
| `ENG_DIV`   | 16-bit divisor                                                       | Sets the sample interval or clock-out half-period. The engine must be idle                 |
| `ENG_CTL`   | Bit order, duplex, clock polarity, clock phase                       | Sets the engine mode. The engine must be idle                                              |
| `ENG_ABORT` | Ignored                                                              | Stops the engine, discards partial input, sets no completion flag, and marks the OSR empty |
| `TMR`       | 32-bit count (0 disarms)                                             | Starts or disarms the timer. Clears `TMR` (see [`Events.md`](Events.md))                   |

- `cfg` changes how the hardware behaves, never what it reports, with two exceptions. Re-arming something clears its own flag (so events from before arming are never seen), and `ENG_ABORT` and `TMR` start or stop something instead of just configuring it.
- A faulting `cfg` has no effect, and sets `ERR` with cause `10` (see [`Events.md`](Events.md)).
- **Shared pins** - Two threads can never drive the same pin, as a pin has exactly one owner and a static output source. A thread that wants a pin owned by another thread has to ask the owner to transfer it, e.g. by using a doorbell and shared memory.
- **Firmware loading** - (TENTATIVE) A small hardware loader (see [`Core Components.md`](Core%20Components.md)) uses a few fixed pins while the threads are held in reset. After loading, those pins are normal pins, owned by their default owners.