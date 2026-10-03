### Instruction Encoding
R - 8 - add, xor, and, or, cmp, cmpa, shl, shr
RI - 4 - addi, xori, shli, shri
I - 3 - jrg, lb, lw
LI - 4 - lui, lli, auipc, alipc
D - 4 - jmp, dlrg, pull, rpin
J - 2 - jof, joc
N - 4 - inp, outp, dl, waitp
P - 2 - push, wpin
S - 2 - sb, sw
related encoding pairs -
R - isolated
RI and I - related (WB vs no WB)
LI and D - related (same encoding, different purpose)
J - isolated (but close to N)
N and P - related (RS1 valid vs RS1 invalid)
S - isolated (but close to P)
WHY THE INSTRUCTIONS WERE ENCODED THIS WAY?!?! (i'm not smoking crack i promise 🥹🥹🥹)
- based on instructions that were decided, we needed to account for operational, memory access, jumping, spatial, and temporal instructions all within just 8-bits of opcode space (and a few extra bits in funct)
- many of the bits are already gobbled up by the 3 bit opcodes, funct, register fields etc., meaning that encoding must be decided based on a multitude of factors -
	- number of instructions per encoding type
	- similarity between encoding and instruction forms
	- immediate bit count priority (basically, which instructions would preferably require more bits, from 'eh, ig i can shave off a few imm bits' to absolutely non-negotiable)
	- prevent explosion of decoder complexity (fitting more info into less bits inherently makes the decoder more complex, so it must be determined smartly)
- here are few design quirks you may notice -
	- TF IS WB?!??!?! basically, it's a bit that tells if the instruction is to write back to RD or not. if the instruction has a WB field, that field determines if the result writes back to RD. if the instruction doesn't, WB is determined by whether the field exists or not. it's my solution to preventing hardwiring an entire fucking register to zero (like rv32i does)
	- WAIT! WHY IS N AND P THE SAME OPCODE BUT DIFFERENT ENCODING!!! AND LI AND D ARE THE SAME ENCODING BUT BUT DIFFERENT OPCODE!??! ARE YOU CRAZY!?!? seems counter intuitive at first, yeah, but the reason is because i could physically not fit 8 instructions of all the LI/D type format within just a single bit of encoding without adding another bit to funct. and that was absolutely non negotiable, as the lli and lui (from LI) and D instructions pretty much require 8-bit imms to prevent it from becoming too less to be able to represent. in comparison, N and P have imm fields that can be more lenient in length and do not strictly have to be the highest amount as possible, hence i compromised by making a specific rs1_valid bit in both instr types as a secondary layer of encoding for classification. ugly tradeoff, but i have like 16 fucking bits what do you expect me to do 🫩
### Jumps
THE MAIN JUMP INSTRUCTIONS -
jmp - unconditional jump, updates pc to pc + 8-bit imm (sign extended), saves return address in rd, encoding format - [(3 bit) rd, (8 bit) imm, (2 bit) funct, (3 bit) opcode]
jrg - unconditional jump, updates pc to rs1 (lower 10 bits) + 5-bit imm (sign extended), saves return address in rd, encoding format - [(3 bit) rd, (3 bit) rs1, (5 bit) imm, (2 bit) funct, (3 bit) opcode]
jof - conditional jump, updates pc to pc + immj, determines if jump is to be performed based on a single flag, encoding format - [(11 bit) immj + immi + immf, (2 bit) funct, (3 bit) opcode], immf is a 2-3 bit field (3 if number of flags > 4), 1 bit immi for invert, and remaining for immj (it can jump farther than joc, but is less versatile)
joc - conditional jump, updates pc to pc + immj, determines if jump is to be performed based on flags (bitmasked, compares a specific flag and checks if high based on the selected flags in encoding), encoding format - [(11 bit) immj + immi + immf, (2 bit) funct, (3 bit) opcode], here, immf is the immediate that is used to determine the flags to be checked to perform the jump (immf is size of the flag register), immi is a single bit which determines if the outcome from the immj bitmasking is to be inverted, and imma is the immediate to be added to pc for jumping (size of the remaining bits, 11 - immf - immi)
more about the bitmasking logic - essentially, each bit of the bitmask determines which flag in the FLAGS register is to be checked. then, all of the results are ANDed together (only from the selected flags). after that, based on immi, the result is inverted to give the final outcome of whether the jump is to be performed. for example (assuming there are 4 flag register fields, not actually 4 but lets just assume), beq pseudoinstruction will have immf encoded as 0b0001 and immi as 0 (checks the 0th flag, i.e. Z flag, if its high), blt will have immf encoded as 0b0010 and immi as 0 (checks 1st flag, i.e. N flag, if its high), bge will have immf encoded as 0b0010 and immi as 1 (checks 1st flag, i.e. N flag, if its high, immi inverts to check if its low), and so on. this approach is meant for maximum versatility to be used with any flag, not just for eq or neg, even if pretty fucking unconventional
as for the remaining bit in funct which can be used for a 4th jump instruction, few ideas come to mind -
one suggestion is adding some kind of jab instruction (jump absolute), which sets pc to an 11 bit imm (only 10 bits considered), kind of redunadant with jrg but does in just one instruction... NVM jof is finalized

### Assembly Syntax
- Why $ prefix for pseudoinstructions? Think of the dollar as a warning sign saying that this mnemonic may expand to more than one instruction after encoding, which can help a lot with preventing potential logical errors causing with timing and shit, maintaining determinism.