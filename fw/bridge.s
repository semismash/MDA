; UART <-> SPI bridge using all three threads, doorbells and shared memory.
;   thread 0: UART receiver (pin #0)  --ring_prev-->  thread 2: SPI master (pins 2, 8, 11, 14)  --ring_prev-->  thread 1: UART transmitter (pin #10)
; Each received byte b is sent as the SPI frame [b, 0x00]; the second byte returned by the SPI device is sent back over UART.
; The data moves through two one-byte mailboxes in data memory, the doorbells only say "a byte is ready".
.mda
.equ DIV,     434
.equ WAITDL,  207
.equ RX_ARM,  0 | W_NEG
.equ RX_CFG,  RX_ARM | ROLE_DIN
.equ TX_CFG,  10 | SRC_DATA | IDLE1
.equ CFG_MISO, 2  | ROLE_DIN
.equ CFG_MOSI, 8  | SRC_DATA
.equ CFG_SCLK, 11 | SRC_CLK
.equ CFG_CS,   14 | SRC_DIRECT | IDLE1

.data
mbox_in:  .word 0
mbox_out: .word 0

.text
; ---------------------------------------------------------------- thread 0: UART RX
.entry0
    lli  r5, RX_CFG
    cfg  #PIN, r5
    lli  r5, DIV
    cfg  #ENG_DIV, r5
    lbi  r6, 0
    cfg  #ENG_CTL, r6
    $li  r4, mbox_in
    lbi  r5, RX_ARM
    lli  r1, M_PE
    lbi  r7, M_ISR_RDY
    lbi  r0, 0
rx:
    waitev r1, @any, @set
    cfg  #WATCH, r6
    dl   WAITDL
    inp  9
    waitev r7, @any, @set
    pull r2, 23
    cfg  #WATCH, r5
    shri r3, r2, 8
    jof  Z, @inv, rx_ok
    addi r0, r0, 1                      ; framing error count
rx_ok:
    sb   r2, 0(r4)                      ; byte -> mailbox
    flg  @ring_prev                     ; doorbell to thread 2
    jnl  rx

; ---------------------------------------------------------------- thread 1: UART TX
.entry1
    lli  r5, TX_CFG
    cfg  #PIN, r5
    lli  r5, DIV
    cfg  #ENG_DIV, r5
    lbi  r5, 0
    cfg  #ENG_CTL, r5
    lli  r1, M_MSG_N                    ; doorbell from thread 2
    lli  r6, 0x200
    lli  r7, M_OSR_EMPTY
    $li  r4, mbox_out
tx_loop:
    waitev r1, @any, @set, @consume
    lb   r2, 0(r4)
    shli r2, r2, 1
    or   r2, r2, r6
    push r2, 0
    outp 10
    waitev r7, @any, @set               ; frame done before taking the next byte
    jnl  tx_loop

; ---------------------------------------------------------------- thread 2: SPI master
.entry2
    lli  r5, CFG_MISO
    cfg  #PIN, r5
    lli  r5, CFG_MOSI
    cfg  #PIN, r5
    lli  r5, CFG_SCLK
    cfg  #PIN, r5
    lli  r5, CFG_CS
    cfg  #PIN, r5
    lbi  r5, 4
    cfg  #ENG_DIV, r5
    lbi  r5, ENG_MSB | ENG_DUPLEX
    cfg  #ENG_CTL, r5
    lbi  r0, 0
    lbi  r7, 1
    lli  r1, M_MSG_N
    lbi  r4, M_ISR_RDY
    $li  r5, mbox_in
    $li  r6, mbox_out
sp_loop:
    waitev r1, @any, @set, @consume     ; doorbell from thread 0
    lb   r2, 0(r5)
    shli r2, r2, 8                      ; {byte, 0x00} in the low 16 bits
    wpin r0, #14                        ; CS low
    dl   15
    push r2, 16                         ; 16 bits MSB first: align to the top
    inp  16
    waitev r4, @any, @set
    pull r3, 0
    wpin r7, #14                        ; CS high
    lbi  r2, 255
    and  r3, r3, r2                     ; second byte = the reply
    sb   r3, 0(r6)
    flg  @ring_prev                     ; doorbell to thread 1
    jnl  sp_loop
