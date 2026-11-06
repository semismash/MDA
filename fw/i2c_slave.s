; I2C slave (7-bit address 0x2A) with a 32-byte register file at data address 0, thread 1
; (SCL #19 and SDA #22 are uio pins owned by thread 1 by default). Write: [addr+W][pointer][data...].
; Read: [addr+R][data...] from the pointer, with a repeated START between the pointer write and the read.
;
; Design: fully polled. The shift engine cannot be used for the bits, because START and STOP (SDA changing while SCL is
; high) have to be detected while a byte is in flight, and the pin watchers cannot tell a data edge from a START/STOP.
; While the bus is free the thread sleeps: a falling-edge watcher on SDA wakes it and SCL is read (on a free bus any SDA fall
; with SCL high is a START). While following traffic for another device it polls (see the bus tracker).
; Inside a byte the thread polls SCL (and, during the first bit only, SDA) and drives SDA with wpin.
.mda
.equ SCL,     19
.equ SDA,     22
.equ ADDR7,   0x2A
.equ CFG_SCL, SCL | SRC_DIRECT | OD | IDLE1
.equ CFG_SDA, SDA | SRC_DIRECT | OD | IDLE1 | W_NEG
.equ ARM,     SDA | W_NEG                     ; watcher arm value (fits lbi)
.equ OFF,     SDA

.data
regs:   .byte 0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F
        .byte 0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1A,0x1B,0x1C,0x1D,0x1E,0x1F

.text
.entry0
    $park rt0
.entry2
    $park rt0

.entry1
    lli  r5, CFG_SCL
    cfg  #PIN, r5
    lli  r5, CFG_SDA
    cfg  #PIN, r5
    lbi  r0, 0                           ; r0 = 0, r7 = 1: constants for wpin and masking
    lbi  r7, 1
    lbi  r5, 0                           ; r5 = register pointer
idle:
    lbi  r1, ARM
    cfg  #WATCH, r1                      ; falling edge on SDA (also clears the old event)
    lli  r1, M_PE
    waitev r1, @any, @set
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, idle                         ; SCL low: just an SDA data edge of other traffic
    lbi  r1, OFF
    cfg  #WATCH, r1                      ; follow the bus by polling from here
    jnl  new_start                       ; (the bus tracker below sits between here and new_start)
; ---------------------------------------------------------------- bus tracker (ignored transaction, or after a NACK)
; Polls until a STOP (-> idle, sleeping) or a START (-> new_start). SDA is read BEFORE SCL, and a change only counts when SCL
; was high in two consecutive iterations. A watcher plus a single SCL read cannot be used here: a normal data edge followed by
; SCL rising within the minimum setup time (100 ns) would look like a START.
track:
    lbi  r2, 0                           ; SCL level of the previous iteration
    rpin r6, #SDA, @level                ; SDA level of the previous iteration
trk:
    rpin r3, #SDA, @level
    rpin r4, #SCL, @level
    and  @na, r2, r4                     ; SCL high now AND last time?
    jof  Z, trk_next
    xor  @na, r3, r6
    jof  Z, trk_next                     ; SDA unchanged
    addi @na, r3, 0
    jof  Z, trk_start                    ; SDA fell while SCL high: START
    jnl  idle                            ; SDA rose while SCL high: STOP, the bus is free
trk_start:
    jnl  new_start
trk_next:
    $mv  r2, r4
    $mv  r6, r3
    jnl  trk
new_start:
st_w:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, st_w                   ; wait until SCL goes low (end of the START condition)
    $call rx_byte                        ; address byte -> r2
    shri r3, r2, 1
    lbi  r1, ADDR7
    $bne r3, r1, to_track                ; not our address: follow the bus until STOP / START
    wpin r0, #SDA                        ; ACK
    and  @na, r2, r7                     ; R/W bit
    jof  Z, wr_path                      ; 0 = write
    jnl  rd_path
to_track:
    jnl  track

; ---------------------------------------------------------------- write: pointer, then data bytes
wr_path:
    $call ack_clk
    wpin r7, #SDA                        ; release SDA
    $call rx_byte                        ; pointer
    $mv  r5, r2
    wpin r0, #SDA
    $call ack_clk
    wpin r7, #SDA
wr_loop:
    $call rx_byte                        ; data byte
    sb   r2, 0(r5)
    addi r5, r5, 1
    wpin r0, #SDA                        ; ACK
    $call ack_clk
    wpin r7, #SDA
    jnl  wr_loop

; ---------------------------------------------------------------- read: bytes from the pointer
rd_path:
    $call ack_clk                        ; ends right after SCL falls: first data bit goes out now
tx_byte:
    lb   r2, 0(r5)
    lbi  r4, 8
tx_bit:
    shri r3, r2, 7
    wpin r3, #SDA                        ; bit 7 (1 releases the open-drain pin)
    shli r2, r2, 1
tx_r:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, tx_r                         ; wait for SCL high
tx_f:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, tx_f                   ; wait for SCL low
    addi r4, r4, -1
    jof  Z, @inv, tx_bit
    wpin r7, #SDA                        ; release for the master's ACK / NACK
tx_ar:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, tx_ar
    rpin r6, #SDA, @level                ; 0 = ACK, 1 = NACK
tx_af:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, tx_af
    addi @na, r6, 0
    jof  Z, @inv, tx_nack                ; NACK: the master is done
    addi r5, r5, 1
    jnl  tx_byte
tx_nack:
    jnl  track

; ---------------------------------------------------------------- helpers (link rad)
ack_clk:                                 ; wait for one full SCL pulse
ac_r:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, ac_r
ac_f:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, ac_f
    $ret

; Receive 8 bits (SCL low on entry) into r2. During the first bit's high phase, an SDA change means START or STOP.
; Uses r2, r3, r4, r6 only: r1 (rad, the return address) and r5 (the register pointer) must survive.
rx_byte:
rx_w1:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, rx_w1                        ; wait for SCL high
    rpin r6, #SDA, @level                ; first bit
    $mv  r2, r6
rx_fb:                                   ; read SDA FIRST, then SCL: if SCL is still high afterwards, the SDA value
    rpin r3, #SDA, @level                ; was read while SCL was high, so a change is really a START / STOP
    rpin r4, #SCL, @level
    addi @na, r4, 0
    jof  Z, rx_fdone                     ; SCL fell: normal bit
    xor  @na, r3, r6
    jof  Z, rx_fb                        ; SDA unchanged: keep watching
    addi @na, r3, 0
    jof  Z, rx_start                     ; SDA fell while SCL high: START
    jnl  rx_stop                         ; SDA rose: STOP
rx_start:
    jnl  new_start
rx_stop:
    jnl  idle
rx_fdone:
    lbi  r4, 7
rx_bit:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, rx_bit                       ; wait for SCL high
    rpin r6, #SDA, @level
    shli r2, r2, 1
    or   r2, r2, r6
rx_fall:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, rx_fall                ; wait for SCL low
    addi r4, r4, -1
    jof  Z, @inv, rx_bit
    $ret
