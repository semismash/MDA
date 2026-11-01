### Events

Events are changes in the hardware state that can be observed in the CPU. They do not represent changes in the control flow itself, but can be handled by doing so, via software, hence preserving determinism.

- Events are latched. When an event occurs, it gets latched to high to be handled later by the suitable even handler. Events are not required to be explicitly handled.
- Examples of events include, but are not limited to - Pin edges and levels, shift engine completion, expired timers, doorbells rung by other threads, faults etc.
- Events can be observed using a combination of CPU flags (via conditional jumps) and dedicated instructions, allowing the program to handle an event when it occurs.

### Event Flags

- Event state is held in the `FLAGS` register, so events are observed using the same conditional jumps as the ALU flags (`jof`, `joc`), and can be waited on using `waitev`. Flags are of two kinds -
    - **Sticky** - Holds its value until it is cleared or overwritten. Event flags are set by hardware (or by a doorbell ring from another thread), and cleared only by software (using `flg`, by consuming them in `waitev`, or by re-arming the thing that sets them). Examples - pin edge events, `TMR`, `ERR`, `OVR`, doorbells. The ALU flags (`Z`, `N`, `C`) are sticky as well, but they are set by an instruction instead of by a hardware event, and they are overwritten by the next instruction that sets them.
    - **Live** - Mirror the current hardware state, and clear themselves. Examples - pin level conditions, `PE`, ISR/OSR status.
- All flags are local to a thread, each thread has its own view of them. There are no global flags. The doorbell state is physically shared between threads (6 bits), but each thread only sees its own two incoming bits (see [`Threading.md`](Threading.md)).
- Every thread sees the flags as they were at the start of its own slot.
- **One writer rule** - Every flag has exactly one source that sets it (an instruction, hardware, or another thread's doorbell ring). Software never writes a flag that mirrors hardware state. The only direct software writes are acknowledging sticky flags (`ERR`, `OVR`, `MSG_N`, `MSG_P`) and ringing another thread's doorbell, both using `flg`. This keeps every flag traceable to a single source, which makes it checkable in verification.

### Flag Layout

- There are 16 flag slots, all reachable by `jof` and `joc`, of which 14 are used and 2 are spare. `joc` and `waitev` take the flag numbering as a mask in a register. Only the low 16 bits of the mask (one per flag slot) are checked, the upper bits are ignored, and the spare flags read as 0.
- (TENTATIVE) The flag numbering is illustrative and may change. The most frequently branched flags should stay in the lower 16.

|Index|Flag|Kind|Set by|Cleared by|
|---|---|---|---|---|
|0|`Z`|Sticky (ALU)|Any flag-setting instruction, if the result is all 0|Overwritten by the next flag-setting instruction|
|1|`N`|Sticky (ALU)|Any flag-setting instruction, if the MSB of the result is 1|Overwritten by the next flag-setting instruction|
|2|`C`|Sticky (ALU)|Carry of `add` and `addi`, last bit shifted out by shifts|Overwritten by the next instruction that sets it|
|3|`ERR`|Sticky|Any fault in this thread|`flg` acknowledge (also clears the cause)|
|4|`ERRC0`|Sticky|Bit 0 of the fault cause, latched with the first fault|Cleared together with `ERR`|
|5|`ERRC1`|Sticky|Bit 1 of the fault cause, latched with the first fault|Cleared together with `ERR`|
|6|`ERRC2`|Sticky|Bit 2 of the fault cause, latched with the first fault|Cleared together with `ERR`|
|7|`ISR_RDY`|Live|Shift engine completes an input word|`pull`, or launching `inp`|
|8|`OSR_EMPTY`|Live|Shift engine finishes shifting out a word, and at reset|`push`|
|9|`MSG_N`|Sticky|Doorbell rung by the next thread|`flg` acknowledge, or `waitev` consume|
|10|`MSG_P`|Sticky|Doorbell rung by the previous thread|`flg` acknowledge, or `waitev` consume|
|11|`PE`|Live (derived)|OR of the event bits of all pins owned by this thread|Clearing the pin event bits (`rpin` with clear), re-arming the watcher, ownership transfer|
|12|`OVR`|Sticky|An event or data was lost (see overrun rules below)|`flg` acknowledge|
|13|`TMR`|Sticky|The thread's timer expires|`cfg` re-arm or disarm of the timer, or `waitev` consume|
|14-15|Spare|-|-|-|

- The ALU flag behavior of each instruction is given in [`Instruction Set.md`](../Instruction%20Set%20and%20Assembly/Instruction%20Set.md).
- The next thread of thread `i` is thread `(i + 1) mod 3`, and the previous thread is `(i - 1) mod 3`.

### Overrun Rules

- If an event arrives while its sticky flag is already set, or data is overwritten before it was consumed, `OVR` is set. `OVR` is always set in the thread that is responsible for the loss, so the thread that can fix it is the one that is told.

|Overrun|`OVR` is set in|
|---|---|
|A pin event while the pin's sticky event bit is already set|The thread that owns the pin|
|`inp` launched while `ISR_RDY` is set, or an input word finishes before it was pulled|The thread that owns the engine|
|`push` while `OSR_EMPTY` is clear|The thread that executed `push`|
|A doorbell ring while the target's doorbell bit is still set|The thread that rang (the sender)|
|A second fault while `ERR` is already set|The thread that faulted|

### Pin Watchers

- Pin events are detected by pin watchers. Every pin has its own watcher, and its events are routed to the thread that owns the pin (see [`I-O Interface.md`](I-O%20Interface.md)). There is no fixed number of watchers per thread.
- All 24 pins pass through a 2-flop synchronizer, followed by a "previous sample" flop. These are shared by all threads. A rising edge is `current & ~previous`, and a falling edge is `~current & previous`.
- Each watcher has a 3-bit mode, configured using `cfg`, and a one bit event bit -

|Mode|Name|Kind|Event bit is set when|
|---|---|---|---|
|`000`|OFF|-|Never (watcher disabled)|
|`001`|LOW|Live|The pin is low|
|`010`|HIGH|Live|The pin is high|
|`011`|-|-|Reserved|
|`100`|OFF|-|Never (watcher disabled)|
|`101`|POS|Sticky|A rising edge occurs|
|`110`|NEG|Sticky|A falling edge occurs|
|`111`|ANY|Sticky|Either a rising or a falling edge occurs|

- The top bit of the mode selects level or edge, and the lower two bits are independent enables (low and high in the level group, rising and falling in the edge group). `ANY` is therefore just both edge enables set, with no special case.
- The event bits of all the pins a thread owns are ORed into that thread's `PE` flag. To find out which pin fired, software reads the event bits using `rpin` (see [`I-O_Interface.md`](I-O%20Interface.md)).
- Configuring a watcher (or transferring the pin) clears its event bit, so edges that occurred before arming it are never seen.
- The detection latency is fixed - 2 synchronizer cycles + 1 detection cycle, followed by the 0-2 cycles it takes for the thread's next slot.
- (TENTATIVE) Each watcher can also latch a 2-bit phase when its event occurs (where in the 3-cycle slot rotation the edge landed), which software can read to compensate for the slot quantization. This is an optional feature, to be decided later.
- Pulses shorter than one clock cycle may be missed.
- A watcher left armed on a toggling pin (e.g. a data pin while a shift engine is running) will keep setting `OVR`. Software should disarm it (mode OFF) before starting the engine, and re-arm it afterwards.

### Waiting on Events

- `waitev rs1, mode` puts the thread to sleep until the flags selected by the mask in `rs1` meet a condition. The thread still occupies its slot (executing nothing), hence other threads are never stalled.
- The mask uses the same flag numbering as `jof` and `joc`, and only its low 16 bits (one per flag slot) are checked, the upper bits are ignored and the spare flags read as 0. The condition is chosen by two independent fields, and gives exactly the same four conditions as `joc` -

|Fields|Condition|`joc` mode|
|---|---|---|
|ALL + SET|All selected flags are set|`00`|
|ANY + SET|Any selected flag is set|`01`|
|ALL + CLEAR|No selected flag is set|`10`|
|ANY + CLEAR|Not all selected flags are set|`11`|

- A third field, CONSUME, clears the sticky event flags in the mask (that were set at wake up) when the thread wakes. Only `MSG_N`, `MSG_P` and `TMR` can be consumed. The ALU flags, `ERR`, `OVR` and the live flags are never affected (`ERR` and `OVR` are cleared using `flg`).
- (TENTATIVE) A 4-bit field is kept reserved for an optional post-event delay of 0-15 cycles, to wake up a precise number of cycles after the event. It must be zero for now.
- `waitev` does not look at edges, it checks the flag levels as they were at the start of the thread's slot. Edges are turned into sticky flags by the watchers beforehand.
- Rules -
    - If the condition is already true, `waitev` takes one slot and falls through. A sticky event that arrived earlier is therefore never missed. To wait for a new event, clear the flag first.
    - Otherwise, the thread sleeps and wakes at the first slot whose snapshot meets the condition. The next instruction runs one slot later. The wake up time is a pure function of the event time.
    - Consume only applies to `MSG_N`, `MSG_P` and `TMR`, and is ignored when waiting for CLEAR. The ALU flags, `ERR`, `OVR` and the live flags (`ISR_RDY`, `OSR_EMPTY`, `PE`) are never affected. A new event arriving in the same cycle as a consume counts as a new event, the flag stays set.
    - Consuming is useful for waiting on a single flag. When waiting on several flags together, consuming clears the one that woke the thread, so it can no longer be told apart. In that case, wait without consume and dispatch using `jof` on the flags.
    - `PE` is not consumed by `waitev`, since it would hide events from other pins. Pin events are cleared individually using `rpin` with clear.
    - An empty mask (low 16 bits all zero) is a fault (cause `101`), and the thread falls through. Waiting forever would be a deadlock with no interrupts to recover from, if that is wanted a thread can spin on a self-jump instead.
    - (TENTATIVE) The latency from a pin edge to the next instruction after `waitev` is roughly 6-8 cycles, to be verified by the reference model.
- A timeout can be built by including `TMR` in the mask, after starting the timer.

### Timer

- Every thread has its own 32-bit timer, which counts down in the background at the clock rate and sets the sticky `TMR` flag at zero. It is separate from the counter used by `dl` and `dlrg`, so a thread can run a timer while using delays.
- It is set up using `cfg` (target `TMR`) with the count in a register -
    - A non-zero count starts the timer and clears `TMR`. Writing it again restarts it.
    - A count of 0 disarms the timer and clears `TMR`.
    - The timer is one-shot.
- Where it is used -

|Use|How|Examples|
|---|---|---|
|Timeout|Arm the timer, `waitev` on the event and `TMR` together, then `jof` on `TMR`|Receiver giving up on a byte, a bus that never responds|
|Fixed period loop|Arm the timer, do variable length work, then `waitev` on `TMR`|Software timed bit-banging where `dl` would drift|
|Idle detection|Re-arm the timer on every edge, expiry means the line has been quiet for the count|UART idle or break detection, I2C bus free time|

- A timeout looks like -

```
cfg    #TMR, r1             ; give up after N cycles
waitev r2, @any, @set       ; r2 = mask of the event flag and TMR
jof    TMR, timed_out       ; which one woke us?
; ... handle the event ...
cfg    #TMR, r0             ; disarm
```

### Determinism Rules

- Flags are latched at slot boundaries, and a thread sees their state as of the start of its own slot.
- If a flag is set and cleared in the same cycle, set wins, so events are never lost.
- If an event arrives while its sticky flag is already set, `OVR` is set (see the overrun rules above).
- The wake up time is a pure function of the event time and the programmed delay, rounded up to the thread's next slot.
- An event never changes the timing of any thread other than the one waiting on it. A doorbell ring only changes the flag of the thread it is addressed to, not its timing.
- Every flag has a single source (the one writer rule), so the only way a thread can influence another thread's flags is a doorbell ring.

### Faults

- Faults are treated as events. A fault never changes the timing of an instruction, which still completes in its normal slot.
- A fault sets the thread's `ERR` flag, along with a 3-bit cause (`ERRC2`, `ERRC1`, `ERRC0`), given in the table below. The cause `111` is reserved.
- If `ERR` is already set when another fault occurs, the first cause is kept and `OVR` is set. If a single access is both misaligned and out-of-bounds, it is reported as misaligned. Clearing `ERR` also clears the cause.
- There are no instruction fetch faults. The PC is as wide as the instruction memory address, and wraps around, so every PC value is a valid address.
- A fault is never required to be handled, `ERR` is a sticky flag that software can look at (using `jof` or `waitev`) or ignore.

|Fault|Trigger|Effect|Cause|
|---|---|---|---|
|Misaligned access|`lw` or `sw` on an address that is not word aligned|Store suppressed, load returns 0|`000`|
|Out-of-bounds access|Any data memory access outside of the memory|Store suppressed, load returns 0|`001`|
|Bad `cfg`|Reserved target, pin number above 23, pin not owned by the thread, role the pin cannot do, divisor of 0, engine write while the engine is busy (except abort)|No effect|`010`|
|Bad pin access|`wpin` on a pin that is not owned or not in direct mode, `rpin` event modes on a pin that is not owned, `rpin` on an output-only pin|No effect, reads return 0|`011`|
|Bad engine launch|`inp` or `outp` with no engine pins configured, or while the engine is busy|No effect|`100`|
|Bad `waitev`|Empty mask|Falls through|`101`|
|Illegal instruction|Undefined encoding, or reserved bits set|Executes as a NOP|`110`|

### Interrupts

- MDA does not have dedicated interrupts. Instead, a thread can be used as an event handler, parked in a `waitev` on the events it handles (e.g. doorbells, `ERR`, `OVR`, pin events). Its response time is fixed and bounded to a few slots, with no effect on the timing of the other threads.
- The tradeoff is thread capacity, as a dedicated handler thread leaves two threads for other work.
- If interrupt-like vectoring is ever added, it should be opt-in per thread, so the default stays fully deterministic.

### Example

- Detecting the start bit of a UART frame on pin 3 (pin 3 belongs to thread 0 by default, syntax is TENTATIVE) -

```
lli r1, WATCH_P3_NEG        ; watcher config - pin 3, mode NEG (value packing TBD)
cfg #WATCH, r1              ; arm the watcher (also clears its event bit)
lli r2, PE_MASK             ; mask for the PE flag
waitev r2, @any, @set       ; sleep until a pin event
rpin r4, #0, @pend_clr      ; read which pins fired, and clear them
dl 12                       ; wait until the middle of the bit
rpin r3, #3, @level         ; sample the bit
```

- The example is pseudocode. Instructions are scheduled in round robin order, so every consecutive instruction of a thread is scheduled in that thread's next slot, and delays are rounded up to the thread's next slot (see `Threading.md`). The per-thread throughput is therefore at most one instruction per 3 cycles (3 CPI), so a multithreaded approach should be preferred.