## How it works

A small FSM writes 16 words to an IHP single-port SRAM macro (1024x16), rewrites the low
bytes using the per-bit write mask, reads every word back and compares it with the expected
value. It reports done, pass and fail on uo[0], uo[1] and uo[2], and shows the low nibble of
the last word read on uo[7:4]. This design only exists to prove the SRAM macro flow.

## How to test

Apply reset and a clock. uo[0] goes high when the test has finished, then uo[1] means pass
and uo[2] means fail.

## External hardware

None.
