; SPI slave, mode 0, MSB first, thread 1. Register-read device: frame = command byte, then ONE data byte.
;   command c (0..31) -> data byte = regs[c]
; The decode has to happen between the 8th falling clock edge and the first bit of the response, so the
; register table sits at data address 0 and the command is used directly as the address (lb r2, 0(r3)).
; Critical path after the command byte completes: waitev wake, jof, pull, lb, push, inp.
.mda
.equ CFG_SCLK, 1  | ROLE_CIN
.equ CFG_CS,   4  | ROLE_GATE | W_POS
.equ CFG_MOSI, 7  | ROLE_DIN
.equ CFG_MISO, 10 | SRC_DATA

.data
regs:   .byte 0xA0,0xA1,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7,0xA8,0xA9,0xAA,0xAB,0xAC,0xAD,0xAE,0xAF
        .byte 0xB0,0xB1,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,0xB8,0xB9,0xBA,0xBB,0xBC,0xBD,0xBE,0xBF

.text
.entry0
    $park rt0
.entry2
    $park rt0

.entry1
    lli  r5, CFG_SCLK
    cfg  #PIN, r5
    lli  r5, CFG_CS
    cfg  #PIN, r5
    lli  r5, CFG_MOSI
    cfg  #PIN, r5
    lli  r5, CFG_MISO
    cfg  #PIN, r5
    lbi  r5, ENG_MSB | ENG_DUPLEX
    cfg  #ENG_CTL, r5
    lli  r1, M_ISR_RDY | M_PE
    lli  r7, M_PE
    lbi  r0, 0
rearm:
    rpin r6, #4, @event_clr
    push r0, 24                          ; command phase: MISO shows zeros
    inp  8
wait_cmd:
    waitev r1, @any, @set
    jof  ISR_RDY, @inv, abort
    pull r3, 0                           ; command byte
    lb   r2, 0(r3)                       ; regs[command], table at address 0
    push r2, 24                          ; response byte, MSB first
    inp  8                               ; first response bit goes out when this launches
wait_resp:
    waitev r1, @any, @set
    jof  ISR_RDY, @inv, abort
    pull r5, 0                           ; discard the dummy byte (also clears ISR_RDY)
    waitev r7, @any, @set                ; CS rises: frame over
    jnl  rearm
abort:
    cfg  #ENG_ABORT, r0
    waitev r7, @any, @set                ; make sure CS is high before re-arming
    jnl  rearm
