; I2C master, thread 0 (SCL #18 and SDA #21 are uio pins owned by thread 0 by default).
; Pure software with direct access: wpin drives the open-drain pins (1 = release), rpin reads them back, which also
; shows clock stretching. dl sets every phase length. Nested calls use different link registers:
;   $call / $ret use rad (r1) for the byte-level routines, the bit routine is called with jmp r5 / jrg r5.
; r0 = 0, r7 = 1 (constants for wpin), r6 = scratch, results go to memory.
; Transaction: write 0x55,0xAA to register pointer 0x10 of device 0x50, then repeated-START read of both back.
.mda
.equ SCL, 18
.equ SDA, 21
.equ CFG_SCL, SCL | SRC_DIRECT | OD | IDLE1      ; released at start (idle level = initial level)
.equ CFG_SDA, SDA | SRC_DIRECT | OD | IDLE1
.equ TMO,   20000                                 ; stretch timeout (cycles) armed per transaction
.equ TSET,  9                                     ; data setup before SCL rises
.equ THI,   24                                    ; SCL high hold after the release was seen
.equ TLO,   45                                    ; SCL low hold after the falling edge

.data
results: .skip 16

.text
.entry1
    $park rt0
.entry2
    $park rt0

.entry0
    lli  r5, CFG_SCL
    cfg  #PIN, r5
    lli  r5, CFG_SDA
    cfg  #PIN, r5
    lbi  r0, 0
    lbi  r7, 1
    lli  r3, TMO
    cfg  #TMR, r3
    dl   300                          ; bus idle
    ; ---- write: START, 0xA0, 0x10, 0x55, 0xAA, STOP
    $call i2c_start
    lbi  r2, 0xA0
    $call i2c_wbyte
    $li  r6, results
    sb   r2, 0(r6)                    ; ACK of the address (0 = ACK)
    lbi  r2, 0x10
    $call i2c_wbyte
    lbi  r2, 0x55
    $call i2c_wbyte
    lbi  r2, 0xAA
    $call i2c_wbyte
    $call i2c_stop
    ; ---- read: START, 0xA0, 0x10, repeated START, 0xA1, read 2 bytes (ACK, NACK), STOP
    $call i2c_start
    lbi  r2, 0xA0
    $call i2c_wbyte
    lbi  r2, 0x10
    $call i2c_wbyte
    $call i2c_rstart
    lbi  r2, 0xA1
    $call i2c_wbyte
    lbi  r2, 0                        ; ACK after the first byte
    $call i2c_rbyte
    $li  r6, results + 4
    sb   r2, 0(r6)
    lbi  r2, 1                        ; NACK after the last byte
    $call i2c_rbyte
    $li  r6, results + 5
    sb   r2, 0(r6)
    $call i2c_stop
    $halt

; ---------------------------------------------------------------- bit level (link r5)
; SCL is low on entry. r3 = bit to send (bit 0). Returns the sampled SDA level in r3.
i2c_bit:
    wpin r3, #SDA                     ; data changes while SCL is low
    dl   TSET                         ; data setup
    wpin r7, #SCL                     ; release SCL
    dl   6                            ; let the 2-flop synchronizer see it before the first read
bit_wait:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, bit_high            ; SCL really high: go on
    jof  TMR, bit_tmo                 ; stretched for too long (a conditional jump only reaches +-32 halfwords)
    jnl  bit_wait
bit_tmo:
    jnl  i2c_timeout
bit_high:
    dl   THI                          ; SCL high time
    rpin r3, #SDA, @level             ; sample SDA at the end of the high time
    wpin r0, #SCL                     ; SCL low
    dl   TLO
    jrg  r5, r5, 0

; ---------------------------------------------------------------- byte level (link rad)
; r2 = byte in, r2 = ACK (0) / NACK (1) out
i2c_wbyte:
    lbi  r4, 8
wb_loop:
    shri r3, r2, 7                    ; bit 7 into bit 0
    jmp  r5, i2c_bit
    shli r2, r2, 1
    addi r4, r4, -1
    jof  Z, @inv, wb_loop
    lbi  r3, 1                        ; release SDA for the ACK clock
    jmp  r5, i2c_bit
    $mv  r2, r3
    $ret

; r2 = ACK bit to send (0 = ACK, 1 = NACK) in, r2 = byte out
i2c_rbyte:
    $mv  r6, r2
    lbi  r2, 0
    lbi  r4, 8
rb_loop:
    lbi  r3, 1                        ; release SDA and clock a bit in
    jmp  r5, i2c_bit
    shli r2, r2, 1
    or   r2, r2, r3
    addi r4, r4, -1
    jof  Z, @inv, rb_loop
    $mv  r3, r6
    jmp  r5, i2c_bit                  ; send the ACK / NACK
    $ret

; ---------------------------------------------------------------- bus conditions (link rad)
i2c_start:                            ; bus idle (SDA = SCL = 1)
    wpin r0, #SDA                     ; SDA falls while SCL is high
    dl   33                           ; tHD;STA
    wpin r0, #SCL
    dl   TLO
    $ret

i2c_rstart:                           ; SCL low on entry
    wpin r7, #SDA
    dl   TSET
    wpin r7, #SCL
    dl   6
rs_wait:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, rs_high
    jof  TMR, rs_tmo
    jnl  rs_wait
rs_tmo:
    jnl  i2c_timeout
rs_high:
    dl   33                           ; tSU;STA
    wpin r0, #SDA                     ; START
    dl   33                           ; tHD;STA
    wpin r0, #SCL
    dl   TLO
    $ret

i2c_stop:                             ; SCL low on entry
    wpin r0, #SDA
    dl   TSET
    wpin r7, #SCL
    dl   6
sp_wait:
    rpin r3, #SCL, @level
    addi @na, r3, 0
    jof  Z, @inv, sp_high
    jof  TMR, sp_tmo
    jnl  sp_wait
sp_tmo:
    jnl  i2c_timeout
sp_high:
    dl   33                           ; tSU;STO
    wpin r7, #SDA                     ; SDA rises while SCL is high = STOP
    dl   70                           ; tBUF
    $ret

i2c_timeout:                          ; bus stuck: release both lines and stop
    wpin r7, #SDA
    wpin r7, #SCL
    $li  r6, results + 8
    sb   r7, 0(r6)                    ; error marker
    $halt
