### Events
Events are changes in the hardware state that can be observed in the CPU. They do not represent changes in the control flow itself, but can be handled by doing so, via software, hence preserving determinism.
- Events are latched. When an event occurs, it gets latched to high to be handled later by the suitable even handler. Events are not required to be explicitly handled.
- Examples of events include, but are not limited to - Pin rising and falling edges, memory subsystem events, channel state changes, expired timers, software triggered events (tentative) etc.
- Events can be observed using a combination of CPU flags (via conditional jumps) and dedicated instructions, allowing the program to handle an event when it occurs.

*\[Disclaimer\] The text below was written in part using generative AI, although the design decisions were made and/or evaluated by a human.*
### Event Flags
- Event state is held in the `FLAGS` register, so events are observed using the same conditional jumps as the ALU flags (`jof`, `joc`). Flags are of three kinds -
	- **Sticky** - Set by hardware, and cleared only by software (using `flg`, or by consuming them in `waitev`). Examples - pin edge events, expired timers, `ERR`, `OVR`.
	- **Live** - Mirror the current hardware state, and clear themselves. Examples - pin level conditions, ISR/OSR status.
	- **Channel** - Mirror the state of the IPC channel registers, and are updated by the channel reads and writes themselves (see `Threading.md`).
- Flags are either local to a thread (each thread has its own copy) or global to all threads.
- Every thread sees the flags as they were at the start of its own slot.

### Flag Layout
**NOTE: The below content is tentative and is subject to change.**
- There are 16 flags, all reachable by `jof` and `joc`. If the word size moves to 32 bits, this may be extended to 32 flags (with a 5-bit flag index in `jof`).
- Local flags (one copy per thread) -
	- 0, 1, 2 - `Z`, `N`, `C` (ALU flags)
	- 3 - `ERR` - Sticky. A fault occurred (memory access or IPC). The cause is held in a 2-bit cause field.
	- 4, 5 - `W0`, `W1` - Pin watcher events.
	- 6 - `ISR_READY` - ISR threshold reached, or input shift engine finished.
	- 7 - `OSR_EMPTY` - OSR is now empty (needs refill), or output shift engine finished.
	- 13 - `TMR` - Timer expired.
- Global flags (shared by all threads) -
	- 8-11 - IPC status. These are a view relative to the reading thread - data waiting from each of the two other threads, and the thread's outgoing register to each of the two other threads still being full.
	- 12 - `OVR` - Sticky. An event or channel data was overwritten before it was handled.
	- 14 - `SIG` - Software triggered event.
	- 15 - Spare Flag.
- This layout is illustrative and may change. The most frequently branched flags should stay in the lower 16.

### Pin Watchers
- Each watcher is configured (using `cfg`) with a pin number and a mode -
	- `RISE` and `FALL` - Sticky, set on the respective edge.
	- `HIGH` and `LOW` - Live, follow the pin's level.
	- To detect any edge, use two watchers on the same pin.
- Configuring a watcher clears its flag, so edges that occurred before arming it are never seen.
- The detection latency is fixed - 2 synchronizer cycles + 1 detection cycle, followed by the 0-2 cycles it takes for the thread's next slot.
- Each watcher also latches a 2-bit phase when its event occurs (where in the 3-cycle slot rotation the edge landed). Software can read it using `flg` and compensate for the slot quantization, which allows cycle-exact edge timing.
- Pulses shorter than one clock cycle may be missed.

### Waiting on Events
- `waitev` puts the thread to sleep until the flags selected by a mask register meet a condition. The thread still occupies its slot (executing nothing), hence other threads are never stalled.
- The mode selects - any selected flag or all selected flags, wait for set or wait for clear, whether sticky flags are consumed (cleared) on wake up, and an optional post-event delay of 0-15 cycles, to wake up a precise number of cycles after the event.
- Consume only applies to sticky flags. If two threads consume the same global flag in the same slot rotation, the earlier thread in the schedule gets it.
- A timeout can be built by including `TMR` in the mask, after starting the timer.

### Determinism Rules
- Flags are latched at slot boundaries, and a thread sees their state as of the start of its own slot.
- If a flag is set and cleared in the same cycle, set wins, so events are never lost.
- If an event arrives while its sticky flag is already set, `OVR` is set.
- The wake up time is a pure function of the event time and the programmed delay, rounded up to the thread's next slot.
- An event never changes the timing of any thread other than the one waiting on it.

### Faults
- Faults are treated as events. A fault never changes the timing of an instruction, which still completes in its normal slot.
- Sources of faults are misaligned memory accesses, out-of-bounds memory accesses, failed IPC channel reads, and instruction fetches outside of the instruction memory.
- A fault sets the thread's `ERR` flag, along with a 2-bit cause - `00` misaligned access, `01` out-of-bounds access, `10` IPC channel fault, `11` instruction fetch fault.
- If `ERR` is already set when another fault occurs, the first cause is kept and `OVR` is set. If a single access is both misaligned and out-of-bounds, it is reported as misaligned. Clearing `ERR` also clears the cause.
- An instruction fetch fault freezes the thread (tentative) - the PC stops advancing, no instruction memory is accessed, and no registers or flags change except for `ERR`. The thread keeps its slot, so other threads are not affected. Another thread is needed to recover it, and how it does so is yet to be decided (e.g. an inter-thread write to the frozen thread's PC and flags, or a reset command via `cfg`).

### Interrupts
- MDA does not have dedicated interrupts (tentative). Instead, a thread can be used as an event handler, parked in a `waitev` on the events it handles (e.g. `SIG`, `ERR`, `OVR`, pin watchers). Its response time is fixed and bounded to a few slots, with no effect on the timing of the other threads.
- The tradeoff is thread capacity, as a dedicated handler thread leaves two threads for other work.
- If interrupt-like vectoring is ever added, it should be opt-in per thread, so the default stays fully deterministic.

### Example
- Detecting the start bit of a UART frame on pin 3 (syntax is tentative) -
```
lli r1, 0x03          ; watcher config - pin 3, falling edge (encoding TBD)
cfg @watch0, r1       ; arm watcher W0 (also clears its flag)
lli r2, 0x10          ; mask for flag 4 (W0)
waitev r2, @any, @consume
dl 12                 ; wait until the middle of the bit
rpin r3, #3           ; sample the bit
```