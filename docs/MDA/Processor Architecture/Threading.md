Given below is the threading design and implementation for MDA.

- **Interleaved barrel processor** - Switching between the IF, ID, and EX stages in a round the robin fashion. When one thread is fetching, another thread is decoding and the other one is executing.
- **3 independent threads** - The processor contains three independent hardware threads, each with their own separate PC, register files, local flags, ISR/OSR, shift engine (TENTATIVE) and timers. All three threads share the same core controller and datapath components, such as the decoder, ALU, LSU, etc., along with the pins and the memories.
    - As threads are independent from each other in terms of resources, and are executed in a strict round-the-robin fashion, intra-thread data hazards are strictly eliminated for non inter-thread access instructions.
- **Deterministic Delays** - Temporal instructions are designed to specifically preserve the scheduling order in the CPU, hence maintaining determinism. This means that if a delay instruction is executed by a specific thread, the resulting 'true' deterministic delay may be between 0-2 clock cycles more than the instructed delay, to match the strict scheduling sequence set by the CPU.
    - The scheduling order of the CPU is always Thread 0 -> Thread 1 -> Thread 2 -> Thread 0, albeit relatively mundane in hardware as all threads are functionally identical.
    - (TENTATIVE) The optional post-event delay in `waitev` and the optional phase capture in pin watchers (see `Events.md`) can be used to compensate for this variation when exact timing relative to an input event is needed.
- **Instruction ordering and spacing** - Every instruction on a specific threads is each spaced by N instructions, where N is the number of threads in the CPU.
    - An instruction that is followed by a suffix halfword (`lli`) takes two slots of its thread, 6 cycles, deterministically.
- **Inter-thread communication** - Threads share the same data memory, and signal each other using doorbells. The data moves through memory, and the doorbell only tells the other thread that something is ready. There are no channel registers.
    - A doorbell is a single sticky bit. There are three threads and each can ring the other two, so there are 6 physical doorbell bits, one for every (sender, receiver) pair.
    - Each thread sees its two incoming bits as local flags, relative to itself - `MSG_N` (rung by the next thread) and `MSG_P` (rung by the previous thread). The flag layout is therefore the same for every thread, and the code can be the same on every thread. Next means thread `(i + 1) mod 3`, and previous means thread `(i - 1) mod 3`.
    - A doorbell is rung using `flg`, which has a mask over the next and previous thread. Ringing the next thread sets that thread's `MSG_P`, and ringing the previous thread sets that thread's `MSG_N`. Ringing both is a broadcast. A thread cannot ring itself.
    - The receiver observes the doorbell using `waitev` or `jof`/`joc`, reads the data from memory, and then clears the bit, using `waitev` consume or an acknowledge with `flg`.
    - Ringing a doorbell that is still set does not lose the doorbell, but it sets `OVR` in the sender, as the sender is the one that made the mistake. The receiver is not told.
    - Doorbells never block, so every instruction takes a fixed time. A thread that wants to wait does so explicitly, using `waitev` on the doorbell flag.
    - Data written before ringing is always visible to the receiver, since a store completes in its own slot, and a doorbell ring takes effect after the sender's instruction.
    - (TENTATIVE) A ring becomes visible to one of the two other threads after 1 cycle, and to the other one after 2 cycles, deterministically, depending on where it sits in the schedule. Which of `MSG_N` and `MSG_P` is the faster one is to be confirmed with a timing diagram.
    - The memory used for passing data (which region belongs to whom, and whether it is one-deep or a ring buffer) is a software convention, to be defined in the ABI. If a sender wants to know that the receiver has consumed the data, the receiver can clear a "full" word in shared memory, and the sender can check it before writing.

```
; thread A (producer)                ; thread B (consumer)
sw    r1, 0(r7)    ; write data      waitev r2, @any, @consume   ; r2 = MSG_P mask
flg   ring_next    ; ring B          lw    r1, 0(r7)             ; read data
```

- **Flags** - All flags are local to a thread, there are no global flags. The doorbell state is the only physically shared flag state, and each thread only sees its two incoming bits. Just like the other local flags, the doorbell flags can be accessed using the `jof` and `joc` instructions, and waited on using `waitev`. The flag layout is given in `Events.md`.
- **Fault Isolation** - A fault (e.g. a memory access fault) in one thread never changes the timing of the other threads. A fault only sets the flags of the thread that caused it. A thread that is sleeping in a delay or in a `waitev` keeps its slot in the schedule, just like a running thread. As the PC wraps around the instruction memory, there are no instruction fetch faults, and no thread can be frozen by one.
- **Handler Threads** - MDA does not have dedicated interrupts. A thread can instead be used as an event handler, parked in a `waitev` (see `Events.md`).
- **Thread startup** - (TENTATIVE) The firmware loader (see `Core_Components.md`) sets the entry PC of every thread and a thread enable mask in its final command, so no thread ID instruction is needed. Threads that are not enabled stay in reset.
- **Stacks** - Threads share the same data memory. Each thread's stack is its own region of it (TENTATIVE).