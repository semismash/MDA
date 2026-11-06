.mda
.equ TX_CFG,   10 | SRC_DATA | IDLE1
.equ CFG_MISO, 2  | ROLE_DIN
.equ CFG_MOSI, 8  | SRC_DATA
.equ CFG_SCLK, 11 | SRC_CLK
.equ CFG_CS,   14 | SRC_DIRECT | IDLE1
.data
msg:    .asciz "MDA determinism!"
        .align 4
res32:  .word 0
.text
.entry0
    $li  r4, 0xFFFFFFFF                  ; constant with reserved bits: every cfg using it is a bad cfg
    lli  r3, 0xFFFF00                    ; out of bounds data address
    lbi  r0, 1                           ; misaligned base
noise:
    flg  @ring_next, @ring_prev          ; doorbell storm towards threads 1 and 2
    lw   r2, 1(r0)                       ; misaligned load -> fault
    sw   r2, 0(r3)                       ; out of bounds store -> fault
    cfg  #PIN, r4                        ; bad cfg
    rpin r5, #12, @level                 ; output-only pin -> bad pin access
    wpin r2, #3                          ; pin not in direct mode -> bad pin access
    inp  8                               ; launching with no engine pins -> fault
    xor  r6, r6, r4
    add  r7, r7, r6
    flg  @ack_err, @ack_ovr
    jnl  noise

.entry1
    lli  r5, TX_CFG
    cfg  #PIN, r5
    lli  r5, 434
    cfg  #ENG_DIV, r5
    lbi  r5, 0
    cfg  #ENG_CTL, r5
    $li  r4, msg
    lli  r6, 0x200
    lli  r7, M_OSR_EMPTY
    lb   r2, 0(r4)
    shli r2, r2, 1
    or   r2, r2, r6
tx_next:
    push r2, 0
    outp 10
    addi r4, r4, 1
    lb   r2, 0(r4)
    $beqz r2, tx_last
    shli r2, r2, 1
    or   r2, r2, r6
    waitev r7, @any, @set
    jnl  tx_next
tx_last:
    waitev r7, @any, @set
    $halt

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
    lbi  r4, M_ISR_RDY
    $li  r6, res32
    lbi  r1, 5                          ; five 32-bit transactions
sp_loop:
    $li  r2, 0xA5C30F1E
    wpin r0, #14
    dl   30
    push r2, 0
    inp  32
    waitev r4, @any, @set
    pull r3, 0
    sw   r3, 0(r6)
    wpin r7, #14
    dl   90
    addi r1, r1, -1
    jof  Z, @inv, sp_loop
    $halt
