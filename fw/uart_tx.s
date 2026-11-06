; UART transmitter, 8N1, thread 1 (owns pin #10 by default: 10 mod 3 = 1).
; The shift engine sends one 10-bit frame per run: bit0 = start (0), bits 1..8 = data LSB first, bit 9 = stop (1).
; While a frame is on the wire the thread already prepares the next one, so the gap between frames is
; only the push + outp latency.
.mda
.equ DIV,    434                       ; 50 MHz / 115200
.equ TXPIN,  10
.equ TX_CFG, TXPIN | SRC_DATA | IDLE1  ; engine data output, idles high

.data
msg:    .asciz "Hello, MDA!\n"

.text
.entry0
    $park rt0
.entry2
    $park rt0

.entry1
    lli  r5, TX_CFG
    cfg  #PIN, r5
    lli  r5, DIV
    cfg  #ENG_DIV, r5
    lbi  r5, 0
    cfg  #ENG_CTL, r5            ; LSB first, simplex, phase 0
    $li  r4, msg                 ; r4 = byte pointer
    lli  r6, 0x200               ; stop bit (bit 9)
    lli  r7, M_OSR_EMPTY         ; mask for waitev
    lb   r2, 0(r4)
    shli r2, r2, 1               ; bit0 = start bit (0)
    or   r2, r2, r6              ; bit9 = stop bit (1)
next:
    push r2, 0                   ; OSR <- frame
    outp 10                      ; send 10 bits, the engine runs on its own
    addi r4, r4, 1
    lb   r2, 0(r4)               ; prepare the next frame while this one is on the wire
    $beqz r2, last
    shli r2, r2, 1
    or   r2, r2, r6
    waitev r7, @any, @set        ; sleep until the engine has shifted the frame out
    jnl  next
last:
    waitev r7, @any, @set
    $halt
