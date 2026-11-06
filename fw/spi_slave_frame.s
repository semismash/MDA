; SPI slave, mode 0, MSB first, thread 1 (pins 1, 4, 7, 10 belong to thread 1 by default).
;   SCLK #1 (clock-in)   CS #4 (gate role, rising-edge watcher)   MOSI #7 (data-in)   MISO #10 (engine data)
; "Preloaded frame" variant: a ROM-like device. The whole 32-bit response (8 dummy bits for the command phase,
; then a 24-bit ID) is loaded into the OSR BEFORE chip select falls, and ONE 32-bit duplex engine run
; handles the entire frame, so no software runs inside the frame and the clock can be fast.
; The received frame (command + dummy) is stored in memory for later checking.
.mda
.equ ID_WORD,  0x00EF4018
.equ CFG_SCLK, 1  | ROLE_CIN
.equ CFG_CS,   4  | ROLE_GATE | W_POS    ; engine runs only while CS is low; a watcher sees CS rise
.equ CFG_MOSI, 7  | ROLE_DIN
.equ CFG_MISO, 10 | SRC_DATA

.data
rxframe: .word 0

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
    lli  r1, M_ISR_RDY | M_PE            ; frame done, or CS rose
    lli  r2, M_PE
    lli  r4, ID_WORD
    $li  r6, rxframe
rearm:
    rpin r3, #4, @event_clr              ; forget any old CS-rise event
    push r4, 0                           ; response word, MSB first
    inp  32                              ; armed: MISO already shows bit 31, waits for CS low and clock edges
wait_frame:
    waitev r1, @any, @set
    jof  ISR_RDY, @inv, abort            ; CS rose before 32 bits: aborted frame
    pull r3, 0
    sw   r3, 0(r6)                       ; keep what the master sent
    waitev r2, @any, @set                ; wait for CS to rise (frame end)
    jnl  rearm
abort:
    cfg  #ENG_ABORT, r0
    jnl  rearm
