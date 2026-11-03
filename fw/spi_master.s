; SPI master, mode 0, MSB first, thread 2 (pins 2, 8, 11, 14 all belong to thread 2 by default).
;   MISO #2 (ui, engine data-in)   MOSI #8 (uo, engine data)   SCLK #11 (uo, engine clock)   CS #14 (uo, direct)
; DIV is the clock half-period in cycles, so SCLK = 50 MHz / (2 * DIV).
; Transaction 1 reads a JEDEC ID with ONE 32-bit duplex engine run (no gaps inside the word).
; Transaction 2 does the same with four 8-bit runs, to show the gap between engine words.
.mda
.equ DIV,      4                        ; SCLK = 6.25 MHz
.equ CFG_MISO, 2  | ROLE_DIN
.equ CFG_MOSI, 8  | SRC_DATA
.equ CFG_SCLK, 11 | SRC_CLK
.equ CFG_CS,   14 | SRC_DIRECT | IDLE1  ; direct pin, starts high (idle level = initial level)

.data
result32: .word 0
result8:  .skip 4

.text
.entry0
    $park rt0
.entry1
    $park rt0

.entry2
    lli  r5, CFG_MISO
    cfg  #PIN, r5
    lli  r5, CFG_MOSI
    cfg  #PIN, r5
    lli  r5, CFG_SCLK
    cfg  #PIN, r5
    lli  r5, CFG_CS
    cfg  #PIN, r5
    lli  r5, DIV
    cfg  #ENG_DIV, r5
    lbi  r5, ENG_MSB | ENG_DUPLEX
    cfg  #ENG_CTL, r5
    lbi  r0, 0                          ; r0 = 0 (CS low / zero data)
    lbi  r7, 1                          ; r7 = 1 (CS high)
    lbi  r4, M_ISR_RDY                  ; waitev mask
    ; ---- transaction 1: 32-bit word
    $li  r2, 0x9F000000                 ; command in the top byte
    wpin r0, #14                        ; CS low
    dl   30                             ; CS setup
    push r2, 0                          ; MSB first: data already at the top
    inp  32                             ; duplex: shifts the OSR out while the ISR fills
    waitev r4, @any, @set
    pull r3, 0                          ; MSB-first input lands in the low bits
    wpin r7, #14                        ; CS high
    $li  r1, result32
    sw   r3, 0(r1)
    dl   60
    ; ---- transaction 2: command + 3 dummy bytes, CS held low, one 8-bit run each
    wpin r0, #14
    dl   30
    lbi  r2, 0x9F
    push r2, 24                         ; 8 bits MSB first: align to the top
    inp  8
    waitev r4, @any, @set
    pull r3, 0
    $li  r1, result8
    sb   r3, 0(r1)
    addi r1, r1, 1
    lbi  r5, 3
byte_loop:
    push r0, 24
    inp  8
    waitev r4, @any, @set
    pull r3, 0
    sb   r3, 0(r1)
    addi r1, r1, 1
    addi r5, r5, -1
    jof  Z, @inv, byte_loop
    wpin r7, #14                        ; CS high
    $halt
