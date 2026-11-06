MDA Revision -

A) Main specifications -

0) FIRST, LET'S DECIDE 32-BIT OR 16-BIT WORD SIZE (I AM LEANING TOWARDS 32 BIT BUT IF YOU SAY 16 BIT THEN LETS SEE). INSTRUCTION LENGTH IS CONFIRMED TO BE 16-BIT. (Reason I want it confirmed fast is because due to our tight budget and the amount of our instruction set and specifications depending upon the word width, lets not specify it using a simple WIDTH parameter).

1) CORE SPECIFICATIONS & ARCHITECTURE -
-> Word Size: 16-bit or 32-bit (TBD as mentioned before)
-> Instruction Size: 16-bit
-> 8 General Purpose Registers (NO zero-hardwired register) - All are truly general purpose, although MDA assembly & ABI will assign certain registers some specific uses (like ra, a0, a1, t0, t1, s0, s1, sp etc. not decided)
-> 3 Threads - Scheduled in strict round-robin order. Each thread has its own register file, own ISR/OSR, own channels, and own local flags. However, as for the main pipeline, I/O ports, on-chip memory, and other global flags and components, only one is present.
-> Pipeline - 3-stage (IF -> ID -> EX)
-> Clock-speed - 50MHz target (MAX, not more than that, aiming b/w 25-50MHz)
-> Memory - On-chip SRAM (Size TBD)
-> PC Width - Currently 10-bit, but subject to change, depends on what we are targeting as the total addressable space (directly depend on our on-chip SRAM estimations).

2) INSTRUCTION SET -
-> Reg-reg instructions are fine (ADD, XOR, AND, OR, CMP, CMPA, SHL, SHR)
-> Reg-imm instructions are fine (ADDI, XORI, SHLI, SHRI)
-> Load immediate instructions - LUI & AUIPC more likely required, lets evaluate LLI and ALIPC depending upon the encoding space we have.
-> Jump instructions - JMP and JRG are fine, but I'm confused if I should make one of them save return address and the other one not (probably lets not do smth like that, most likely we will be relying on the conditional jumps for branches that don't save return address). JOF will select a certain flag (and invert the condition if requested). JOC is more versatile, first checking a bitmask of flags using a register (number of flags = word width) to select which flags to evaluate, then selecting if OR or AND of the flags, then selecting if invert or not, then jump accordingly. Lower jump range for latter is intentional, it can be used in chain with the better jumps for far jumps (HOWEVER, I HAVE A CONSIDERATION WHERE WE CAN POTENTIALLY ADD A JOC LIKE INSTRUCTION, PERHAPS A 32 BIT TWO-PART INSTRUCTION OR A COMBIANTION OF A CONFIG + JUMP INSTRUCTION OR SMTH, TO ALLOW FAR JUMPS TO STUFF LIKE EVENT HANDLERS... JUST A CONSIDERATION! WE CAN TRY SMTH ELSE IF YOU WISH :)))
-> Memory access instructions - ALL LOADS ARE UNSIGNED. Confirmed - LB, SB, LW, SW. Unconfirmed - LH, SH. Latter only there if 32-bit word size. For 16-bit, LW and SW access 2 bytes. For 32-bit, it's 4 bytes.
-> IPC instructions - Two instructions - CHRD (channel read), and CHWR (channel write). Used to transfer data between threads. CHWR writes to a channel register (the channel can be to the other two threads, determined by a single bit, more on that later in the IPC section), which must be separately claimed by another thread using CHRD.
-> Spatial instructions - PULL & PUSH are fine. IN and OUT directly take from ISR or to OSR between it and the corresponding pin, and shift it out at a rate determined by a clock divisor (perhaps encoded in an rs1 field in the instruction). What I mentioned is serial communication, so it can happen in parallel with direct pin communication for extra throughput. RPIN and WPIN are the parallel communication instructions, directly writes a value to another pin. Still a bit fuzzy about that whole parallel thing, need to discuss it, also not sure about the OSR and ISR stuff, but yeah it happens in parallel with the OSR and ISR thing, that's all I know. Let's discuss it more indepth, cuz I want to see if we really need WPIN and RPIN direct instructions or if they are unnecessary, and how they could end up complementing (or conflicting with) our waitev instructions for pins.
-> Temporal instructions - DL & DLRG are fine. WAITEV is good but needs more elaboration, but for what we know, it sets a watcher and utilizes the flags register to observe events. The FLAGS register (or registers - plural - as there are both local and global flags) is basically the main register that the entire processor uses for events. That's what I want it to be, don't make this shit too complex or something like that (also that's why I was pushing for 32-bit word size, will give us 32 flags, which is a very good amount to add a lot of unique events). To watch a pin specifically, use the CFG instruction, and the FLG instruction does smth with flags, even idk I have to see.
> SUGGESTION!!! Instructions or conditions to break out of a delay early to prevent stalling forever? Could be useful if we do waitev or smth, and an event never ends up happening, and we have to break a thread out of the stall... pretty important, don't you think? Doesn't have to be a new instruction to break it out, as it could break determinism, but we can set up a certain condition before the temporal instruction is asserted.

> TO BE CONSIDERED (Not included in count below): Stuff like environment calls like ecall and ebreak, most likely won't add tho, but worth mentioning.

ONE MORE THING!!! I was thinking of introducing a specific 'null' flag or smth that's always set to low (or maybe high, idk just help me decide), giving us 15/31 effective flags, very useful for certain jump instructions (i.e. jof so you jump unconditionally without storing).

Total instruction count -
> 16-bit: 33-37 (depending upon if LLI, ALIPC, RPIN, and WPIN are included in the end).
> 32-bit: 35-39 (depending upon if LLI, ALIPC, RPIN, and WPIN are included in the end).

-> Assembly language to be finalized later based on this, however it is mostly to be the same as what we have already decided.

3) INSTRUCTION ENCODING -
OKAY, SO LOOKS LIKE WE HAVE TO COMPLETELY REVISE THIS LOL, IT'S KIND OF FUCKED WITH OUR CURRENT INSTRUCTION SET AND SMALL AHH SIZES. But, I'll lay out a basic set of rules and try to evaluate however much my idiotic ass useless brain permits.
- Register fields (RD, RS1, RS2), goes [15:13], [12:10], [9:7]. Register fields don't have to be present in all types of instructions, only certain ones.
- [2:0] is always opcode. No changes at all.
- [3] is (probably) always reserved for FUNCT. [4] has a high chance of being reserved for FUNCT. [5] may or may not be reserved for FUNCT, to be decided later. [7] Is never for funct, perhaps for WB bit or smth else.
- If the above fields are not assigned something special, they will be of immediate field. Immediates are chopped and scattered across the instructions, and may be of a different length in each encoding format, specified by the encoding itself. They can either determine a simple value, or in part, the intrinsic behaviour of a specific instruction, particularly concerning it's output.
Assertions -
-> Encoding will have to be done a bit smartly. R-types have 6 bits for for just identifying the function (so 8 instructions). Assuming all other encoding types have 2 FUNCT bits, we get (7 (for the remaining opcodes) * 2^2 = 28 instructions). Add to 8 from before, giving us space for 36 instructions. This has a very high chance of conflicting with our budget (outright not being enough if we have like 37 or 39 instructions, and even if we had less than that, we need to keep consistent encoding to maintain decoder simplicity), so I propose two solutions -
> Some instruction types will have to effectively have 3 FUNCT bits (kind of like we did with merging P & N type encoding better, but cleaner).
> Some instructions are effectively '32 bits', requiring the instruction with the opcode itself, followed a 16-bit value which the instruction will use for the CPU. These instructions inherently take multiple cycles to execute, and each 2 byte part needs to be spaced with 2 other 16-bit instructions in between to main strict round-robin ordering. (This in particular may not be inherently required if we decide word size to be 16-bit, but is practically mandatory for 32-bit word size).
-> Let's leave encoding for now, first lets finalize our ISA spec, as encoding depending on that.

4) THREADING AND IPC -
-> Interleaved barrel processor, 3 threads as described before.
-> Threads are independent from each other, cannot interact with one another except using explicit IPC instructions (chrd and chwr).
-> Strictly enforced round-the-robin order (always execute in order Thread 0 -> Thread 1 -> Thread 2 -> Thread 0 and repeat).
-> Delays are deterministic. An induced delay will always be made to align with the next execution slot of that particular thread (i.e. can consume 0-2 extra cycles for alignment).
-> Every instruction for a specific thread is spaced every N other instructions, where N is the number of threads in the CPU (in this design, N = 3).
-> Threads communicate with each other using bi-directional channels. Since there are three threads, and each thread has two channels between them (two uni-directional channels -> one bi-directional), there are a total of 6 channels in total.
> Every thread has two channels originating from it, and two channels leaving it. A single bit can be used to multiplex between these channels for IPC.
> Channels have 'channel registers' in between them, which store data that is transferred during IPC. Inter-thread hazards are eliminated.
> Channel registers have validity bits which are used to verify IPC communication. Here are the following rules (model using Mealy State Machine) -
- Write done to channel & Validity Bit = 0 -> Value stored and Validity bit = 1
- Write done to channel & Validity Bit = 1 -> (PROPOSED) Value overwritten and global (decide if global or local, I suggest former) flag set, Validity bit = 1
- Read done from channel & Validity Bit = 0 -> Invalid Read (PROPOSED -> Set a flag, ERR) and Validity bit = 0 (FAULT!!!)
- Read done from channel & Validity Bit = 1 -> Value read successfully and Validity bit = 0
> IPC instructions take at least two instructions (chwr and chrd) to complete (2 CP in forward channels, 3 CP in backward channels).
-> Threads share the same datamemory, and hence may have dedicated stacks within the same memory.
-> Faults or events in one thread do not disrupt the timing of other threads. More is covered in the events section.

5) MEM & I/O INTERFACE -
-> Memory is on-chip SRAM -> Single Cycle MEM Accesses. Completely reprogrammable, however size is not yet confirmed.
-> Current pin count was 24, was thinking of extended to 32 though (mathematical feasibility as 2^5 = 32, however yet to check if 24->32 is practically possible, total addressable pin count should be 32 though, unless we change the addressing method).
-> Access to pins can be done in 3 (or 2 ???) main ways.
> Using waitev to track pins using watchers (described in events). (DETECTING PIN EVENTS)
> Using inp and outp to shift data to and from pins at a set rate.
> ISR shifts into pin at set rate (decided by configured divisor). OSR shifts out of pin at set rate (decided by configured divisor).
> Using wpin and rpin to directly interface and shift data at a fixed rate (STILL NEED TO DECIDE THE EXACT FUNCTIONALITY OF THIS, I DECIDED THIS EARLIER WITHOUT THINKING MUCH AND JUST LOOKING AT EXISTING SPECS FROM EXISTING HARDWARE, BUT WE CAN STRIP THIS IF NOT REQUIRED, OR REVISE IT SOME OTHER WAY).
NOTE: IF we keep both inp/outp and wpin/rpin, we need to make sure that both of them don't conflict (both pins don't write to the same pin). And of course, if we have even one of them (inp/outp is most likely confirmed to be there), we need to make sure to synchronize waitev to inp to actually record pin inputs, perhaps using inter-thread communication or smth (that's what my proposal is, since detecting an edge and reading that same edge synchronously cannot be done in one thread, so maybe we can configure outp to be auto or smth? idk I'm really confused about this, so we need to discuss more about this, and the actual model.
> cfg and flg instructions are used to interact with pins. Still need to evaluate those instructions though as you suggested them and I'm confused about their functioning.
> Clock output pin is undecided (depends on area).
> Two threads driving the same pin - TBD still, and evaluated. Simultaneous driving will be a conflict and not allowed (raise fault).

6) EVENTS -
-> Events are observed changes in hardware state in the CPU.
> Faults and interrupts are unified under the events model to maintain determinism. They are always deferred, and will not break the strict scheduling order or create unnecessary stalls and jumps.
-> Events are solely observed using CPU flags. When events are triggered, the update the respective CPU flag (or a combination of them). This allows instructions like waitev to watch a possible configured event, and instructions jof and joc to mask and them (see the note about jof and joc I mentioned earlier, could leverage it maybe, if we need high range to jump for event handlers, I do want to keep potential event handling logic as minimal as possible, so we will have to think a bit about this).
-> Every pin has watchers that can be set. Watchers are two bits, for four states - LOW, HIGH, POSEDGE, NEGEDGE. Same as what we discussed before, can be integrated into the events system with the waitev instruction, but need more clarification regarding it cuz I'm still confused we may be conflating the two together, and I'm not able to devise a clean model yet.
-> Event handling is synchronized to the scheduling order (0-2 cycles delay).
-> Flags:
> Two types - Sticky and live. Sticky flags stack stuck until cleared. Live are permanently tied to a specific value.
> Two more types - Local and global. Local are thread specific (total three, each thread has one). Global are accessible by any thread (only one set, common to all threads).
> Flag suggestions - (NAME NOT DECIDED) Permanent High/Low flag (need to decide whether permanent high or low, doesn't matter that much due to invert bit but still), Zero, Negative, Carry, Overwrite, Error/fault, ISR or/and OSR full or/and empty, pin events, IPC status, software triggered events, etc. (now you see why I prefer 32 flags, hence, 32-bit word size).
> No specific interrupt vectors or smth, since events are deferred to event handlers anyways (which can be optionally set too), interrupts are naturally handled that way, same with faults.
> Other stuff is too early to confirm without clarifying the model first.

7) POTENTIAL FEATURE CONSIDERATIONS AND SUGGESTIONS -
> 32-bit word size (again, this is the biggest feature we have to discuss, sorry to keep mentioning this)
> Effective variable length instructions, although better to term them as prefix/suffix instructions (most instrs are 16-bit, if not all, but some 16-bit words (or halfwords if 32 bit) can be used in tandem with certain instructions for transporting large values.
> Probably won't consider this at all, but if there is a lot of leftover space, dual core considerations could be made for higher performance (although I imagine this is more of a late stage thing and adds too much complexity and area, better we do not consider it at all rn, only later on if we get time).

B) Project Features & Implementation Pipeline -

HERE, I WILL BE SPECIFYIN THE MAIN PARTS OF OUR PROJECT, SO YOU HAVE A BETTER IDEA OF WHAT OUR ENTIRE STACK IS.

1) CPU & ISA SPECIFICATIONS - Whatever I described above. As mentioned, freeze it asap. After hardware is frozen, software should be planned. I have knowledge in UART and SPI (have implemented both protocols myself before), I2C shouldn't be too difficult. Other protocols, we need to evaluate the feasibility, lets try for implementing max, but if something doesn't work out inevitably... can't do much about it.
2) RTL DESIGN - Implement our designed core in RTL. Should not be too difficult. I've already made my own RISC-V core in RTL (including forwarding and branch prediction), so I have experience with that. SystemVerilog will be used as the language for RTL implementation.
3) RTL Verification - Use Verilator to verify basic veracity of the components, by using simple encoded programs and instructions.
4) Assembly - Repurpose my existing assembler architecture and rewrite some of the code to fit our new assembly language, so programs can be easily assembled for testing -> This will play a big role in our verification journey.
5) Software - Remember: Our challenge is a protocol emulator. UART, SPI, I2C all implemented, along with other protocols (evaluate feasibility, then check what all can be done. This includes: low-speed USB, Ethernet, JTAG, SWD, PS/2, CAN bus, as mentioned in website). Our ISA must be leveraged properly to implement this with max code density and performance. Determinism may not be explicitly accounted for in software, as it's already a cornerstone feature in our hardware.
6) Simulation - Verilator used for existing tests and verification. Cocotb (in template folder) to integrate assembler and other parts of our stack together (basically, creating an integrated verification stack). IVerilog may also be required (in template).
> AI-assisted Verification - Write testbenches using AI models, based on trained assertions from the extension documentation we provide. And then use a second model trained upon our ISA spec directly, and check disagreements in testbenches, ambiguities (that new Claude Pro subscription I got on my other account could really come in handy, hmm...). Read more about mutation with Yosys by deliberately injecting bugs.
> Testbenches should follow a strict priority order - Veracity & Adherence to Spec > Determinism > Performance & Execution Time. Specific metrics can be optimized for separately.
> This isn't final obviously, we need to come up with novel methodologies later, but we have time for that. This gives us a good base.
7) Synthesis & As you had mentioned earlier: I have the Arty A7 100T board from Digilent. Way more than enough to synthesize our CPU and test. For the actual flow, use Yosys for the synthesis. Need to check more about SymbiYosys. Use OpenLane RTL-to-GDSII flow to synthesize the proper chip (ig with P&R and everything). Reference with TTHIP Verilog template. Check Area and Power constraints.
8) FINAL - Tie up everything into a proper usable stack. ISA + RTL + Assembler + Software + Testbenches & Simulation + Final GDSII after Synthesis. Compile existing docs on ISA spec along with our methodology at every step of the process, though processes during designing, and test results into one proper comprehensive master document.
9) If time permits, very valuable addition - Exploring integrating and modifying C ABI and potentially LLVM into our ASM language, so we can compile regular C programs for our architecture. Although, this may take precious time we don't have, so leave it for last.

C) Physical Layout and Constraints -
Too lazy to write this, so just refer to what we already know, and TinyTapeout template for CMOS5L 130nm PDK.