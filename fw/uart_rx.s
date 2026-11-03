; UART receiver, 8N1, thread 0 (owns pin #0 by default). Bytes go to rxbuf, framing errors are counted in r0.
; The falling edge of the start bit is caught by a pin watcher. The thread then waits (dl) until the middle
; of the start bit and launches the engine for 9 bits (8 data + stop). The engine samples every DIV cycles,
; so the first sample lands in the middle of data bit 0, and the rest follow with no software involvement.
.mda
.equ DIV,    434                         ; 50 MHz / 115200
.equ WAITDL, 207                         ; dl before inp: about DIV/2 - 10, rounded down to a multiple of 3
.equ RXPIN,  0
.equ RX_ARM, RXPIN | W_NEG               ; watcher on the falling edge (fits lbi)
.equ RX_CFG, RX_ARM | ROLE_DIN           ; plus the engine data-in role

.data
rxbuf:  .skip 64

.text
.entry1
    $park rt0
.entry2
    $park rt0

.entry0
    lli  r5, RX_CFG
    cfg  #PIN, r5                        ; pin 0: data-in role, falling-edge watcher armed
    lli  r5, DIV
    cfg  #ENG_DIV, r5
    lbi  r6, 0
    cfg  #ENG_CTL, r6                    ; LSB first
    $li  r4, rxbuf                       ; r4 = write pointer
    lbi  r5, RX_ARM                      ; r5 = watcher arm value
    lli  r1, M_PE                        ; r1 = mask: any pin event
    lbi  r7, M_ISR_RDY                   ; r7 = mask: engine finished
    lbi  r0, 0                           ; r0 = framing error count
rx:
    waitev r1, @any, @set                ; sleep until the start bit edge
    cfg  #WATCH, r6                      ; watcher off (value 0 = pin 0, mode OFF), data bits would set OVR
    dl   WAITDL                          ; to the middle of the start bit
    inp  9                               ; first sample DIV cycles from now = middle of data bit 0
    waitev r7, @any, @set                ; done in the middle of the stop bit
    pull r2, 23                          ; 9 bits arrive LSB first in [31:23] -> {stop, d7..d0}
    cfg  #WATCH, r5                      ; re-arm for the next start bit
    shri r3, r2, 8                       ; stop bit
    jof  Z, @inv, ok
    addi r0, r0, 1                       ; framing error
ok:
    sb   r2, 0(r4)
    addi r4, r4, 1
    jnl  rx
