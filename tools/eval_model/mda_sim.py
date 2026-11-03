#!/usr/bin/env python3
"""Cycle-level MDA simulator (evaluation model, NOT the reference model).

Written from the spec docs to run firmware and measure it. Every place where the spec does not pin a
behaviour down is marked ASSUMPTION and collected in the evaluation doc.
Time unit: one clock cycle. Thread t executes at cycles 3k+t. Instruction effects (pin writes, engine
launch) take effect at the next cycle. Readable pin level = pad value 2 cycles ago (2-flop synchronizer).
"""
import heapq
from mda_asm import assemble, FLAG

M32 = 0xFFFFFFFF
F = FLAG
BIT = {k: 1 << v for k, v in FLAG.items()}


class Pin:
    def __init__(self, n, owner):
        self.n = n
        self.owner = owner
        self.reset()

    def reset(self):
        self.outsrc = 0
        self.od = 0
        self.idle = 0
        self.din = self.cin = self.gate = 0
        self.mode = 0
        self.ev = 0          # sticky event bit (edge modes)
        self.dval = 1 if False else 0


class Engine:
    def __init__(self):
        self.div = 1
        self.msb = 0
        self.duplex = 0
        self.cpha = 0
        self.busy = False
        self.tl = []         # heap of (cycle, seq, kind, value)
        self.seq = 0
        self.dout = 0
        self.clkout = 0
        self.x = None        # active transfer

    def push(self, cycle, kind, val=None):
        self.seq += 1
        heapq.heappush(self.tl, (cycle, self.seq, kind, val))


class Thread:
    def __init__(self, tid):
        self.tid = tid
        self.regs = [0] * 8
        self.pc = 0
        self.flags = BIT['OSR_EMPTY']
        self.next_exec = tid
        self.isr = 0
        self.osr = 0
        self.eng = Engine()
        self.tmr_exp = None
        self.pending = []     # (apply_cycle, set_mask)
        self.n_exec = 0
        self.n_wait = 0
        self.n_dl = 0
        self.alive = True
        self.trace = []
        self.last_fault = None


class Sim:
    def __init__(self, src_or_prog, dmem=4096, ncycles=400000, trace=False, comp=0, init_random=None):
        self.comp = comp   # ASSUMPTION switch: delay engine sample strobes by `comp` cycles (synchronizer compensation)
        self.prog = assemble(src_or_prog) if isinstance(src_or_prog, str) else src_or_prog
        self.dmem = bytearray(dmem)
        self._rng = None
        if init_random is not None:
            import random
            self._rng = random.Random(init_random)
            self.dmem = bytearray(self._rng.getrandbits(8) for _ in range(dmem))
        for a, v in self.prog.data.items():
            self.dmem[a] = v
        self.N = ncycles
        self.th = [Thread(i) for i in range(3)]
        if self._rng is not None:
            for th in self.th:
                th.regs = [self._rng.getrandbits(32) for _ in range(8)]
        self.pins = [Pin(n, n % 3) for n in range(24)]
        for t in range(3):
            e = self.prog.entry.get(t)
            if e is None:
                self.th[t].alive = False
            else:
                self.th[t].pc = e
        self.hist = [bytearray(ncycles + 8) for _ in range(24)]
        self.pullups = set()
        self.devices = []
        self.active = set()
        self.t = 0
        self.trace_on = trace
        self.faults = []
        self.log = []
        self._evq = []

    # ---------------------------------------------------------------- helpers
    def add_device(self, dev):
        self.devices.append(dev)
        for p in dev.pins:
            self.active.add(p)
        for p in getattr(dev, 'pullup_pins', []):
            self.pullups.add(p)
            self.active.add(p)

    def rd(self, pin, back, t):
        i = t - back
        if i < 0:
            return 1 if pin in self.pullups else 0
        return self.hist[pin][i]

    def view(self, th, t):
        v = th.flags
        for p in self.pins:
            if p.owner == th.tid and self.pin_event(p, t):
                v |= BIT['PE']
                break
        return v

    def pin_event(self, p, t):
        if p.mode in (1, 2):
            lvl = self.rd(p.n, 2, t)
            return (lvl == 0) if p.mode == 1 else (lvl == 1)
        return bool(p.ev)

    def set_flags(self, th, mask, delay=0):
        th.pending.append((self.t + delay, mask))

    def fault(self, th, cause):
        self.faults.append((self.t, th.tid, cause))
        th.last_fault = cause
        if th.flags & BIT['ERR']:
            th.flags |= BIT['OVR']
        else:
            th.flags |= BIT['ERR'] | (BIT['ERRC0'] if cause & 1 else 0) | (BIT['ERRC1'] if cause & 2 else 0) | (BIT['ERRC2'] if cause & 4 else 0)

    # ---------------------------------------------------------------- pad drive
    def dut_drive(self, pin):
        p = self.pins[pin]
        th = self.th[p.owner]
        if p.outsrc == 0:
            return 0 if 8 <= pin <= 15 else None
        if p.outsrc == 1:
            v = p.dval
        elif p.outsrc == 2:
            v = th.eng.dout
        else:
            v = th.eng.clkout
        if p.od and v == 1:
            return None
        return v

    # ---------------------------------------------------------------- engine
    def eng_pins(self, th):
        d = dict(dout=None, clkout=None, din=None, cin=None, gate=None)
        for p in self.pins:
            if p.owner != th.tid:
                continue
            if p.outsrc == 2:
                d['dout'] = p
            if p.outsrc == 3:
                d['clkout'] = p
            if p.din:
                d['din'] = p
            if p.cin:
                d['cin'] = p
            if p.gate:
                d['gate'] = p
        return d

    def bit_out(self, th, i):
        e = th.eng
        return (th.osr >> (31 - i)) & 1 if e.msb else (th.osr >> i) & 1

    def launch(self, th, t, rx, tx, n):
        e = th.eng
        pp = self.eng_pins(th)
        if e.busy or (pp['dout'] is None and pp['din'] is None):
            self.fault(th, 4)
            return
        if e.duplex:
            rx = tx = True
        t0 = t + 1
        if rx:
            if th.flags & BIT['ISR_RDY']:
                th.flags |= BIT['OVR']
            th.flags &= ~BIT['ISR_RDY']
            th.isr = 0
        e.busy = True
        e.x = dict(n=n, rx=rx, tx=tx, i=0, si=0, t0=t0, pp=pp, slave=pp['cin'] is not None)
        x = e.x
        idle_d = pp['dout'].idle if pp['dout'] else 0
        if x['slave']:
            if tx:
                e.push(t0, 'd', self.bit_out(th, 0))
            return
        D = e.div
        S = self.comp
        if pp['clkout'] is None:                    # UART-like, paced by the divider
            for i in range(n):
                if tx:
                    e.push(t0 + D * i, 'd', self.bit_out(th, i))
                if rx:
                    e.push(t0 + D * (i + 1) + S, 's', i)
            e.push(t0 + D * n + S, 'done')
        else:                                       # clock-out (SPI master)
            cp = pp['clkout']
            lead = 1 - cp.idle
            for i in range(n):
                if e.cpha == 0:
                    if tx:
                        e.push(t0 + 2 * D * i, 'd', self.bit_out(th, i))
                    e.push(t0 + D + 2 * D * i, 'c', lead)
                    if rx:
                        e.push(t0 + D + 2 * D * i + S, 's', i)
                    e.push(t0 + 2 * D * (i + 1), 'c', cp.idle)
                else:
                    e.push(t0 + D + 2 * D * i, 'c', lead)
                    if tx:
                        e.push(t0 + D + 2 * D * i, 'd', self.bit_out(th, i))
                    e.push(t0 + 2 * D * (i + 1), 'c', cp.idle)
                    if rx:
                        e.push(t0 + 2 * D * (i + 1) + S, 's', i)
            e.push(t0 + 2 * D * n + S, 'done')

    def eng_finish(self, th, t, x):
        e = th.eng
        pp = x['pp']
        e.busy = False
        e.x = None
        e.dout = pp['dout'].idle if pp['dout'] else 0
        e.clkout = pp['clkout'].idle if pp['clkout'] else 0
        m = 0
        if x['rx']:
            m |= BIT['ISR_RDY']
        if x['tx']:
            m |= BIT['OSR_EMPTY']
            if e.msb:
                th.osr = (th.osr << x['n']) & M32
            else:
                th.osr >>= x['n']
        self.set_flags(th, m)

    def sample(self, th, x, t):
        din = x['pp']['din']
        bit = self.rd(din.n, 2, t) if din else 1
        e = th.eng
        if e.msb:
            th.isr = ((th.isr << 1) | bit) & M32
        else:
            th.isr = (th.isr >> 1) | (bit << 31)

    def eng_advance(self, th, t):
        e = th.eng
        while e.tl and e.tl[0][0] <= t:
            c, _, kind, val = heapq.heappop(e.tl)
            x = e.x
            if kind == 'd':
                e.dout = val
            elif kind == 'c':
                e.clkout = val
            elif kind == 's' and x:
                self.sample(th, x, c)
            elif kind == 'done' and x:
                self.eng_finish(th, c, x)

    def eng_react(self, th, t):
        e = th.eng
        x = e.x
        if not x or not x['slave'] or t < 3:
            return
        pp = x['pp']
        if t < x['t0']:
            return
        if pp['gate'] is not None and self.rd(pp['gate'].n, 2, t) != 0:
            return
        c = pp['cin'].n
        cur, prev = self.rd(c, 2, t), self.rd(c, 3, t)
        if cur == prev:
            return
        idle = pp['cin'].idle
        leading = (cur != idle)
        if e.cpha:
            raise NotImplementedError('slave CPHA=1 not modelled')
        if leading:
            if x['rx']:
                self.sample(th, x, t)
        else:
            x['i'] += 1
            if x['i'] >= x['n']:
                e.push(t + 1, 'done')
                if pp['dout']:
                    pass
            elif x['tx']:
                e.push(t + 1, 'd', self.bit_out(th, x['i']))

    # ---------------------------------------------------------------- watchers / timers
    def hw_step(self, t):
        if t >= 3:
            for p in self.pins:
                if p.mode in (5, 6, 7):
                    cur, prev = self.rd(p.n, 2, t), self.rd(p.n, 3, t)
                    hit = (cur and not prev and p.mode in (5, 7)) or (prev and not cur and p.mode in (6, 7))
                    if hit:
                        if p.ev:
                            self.set_flags(self.th[p.owner], BIT['OVR'])
                        self._evq.append(p)      # event bit is set at the END of this cycle (visible from the next one)
        for th in self.th:
            if th.tmr_exp is not None and t >= th.tmr_exp:
                self.set_flags(th, BIT['TMR'])
                th.tmr_exp = None
            self.eng_react(th, t)

    # ---------------------------------------------------------------- CPU
    def alu_flags(self, th, res, c=None):
        th.flags &= ~(BIT['Z'] | BIT['N'])
        if res & M32 == 0:
            th.flags |= BIT['Z']
        if res & 0x80000000:
            th.flags |= BIT['N']
        if c is not None:
            th.flags = (th.flags & ~BIT['C']) | (BIT['C'] if c else 0)

    def wr(self, th, rd, v):
        if rd is not None:
            th.regs[rd] = v & M32

    def exec(self, th, t):
        ins = self.prog.mem.get(th.pc)
        if ins is None:
            self.fault(th, 6)
            th.pc += 1
            th.next_exec = t + 3
            return
        op = ins['op']
        r = th.regs
        nxt = th.pc + ins['size']
        step = 3 * ins['size']
        th.n_exec += 1
        if self.trace_on:
            th.trace.append((t, th.pc, ins['text']))
        if op in ('add', 'xor', 'and', 'or', 'cmp', 'cmpa', 'shl', 'shr'):
            a, b = r[ins['rs1']], r[ins['rs2']]
            if op == 'add':
                s = a + b
                self.wr(th, ins['rd'], s)
                self.alu_flags(th, s, c=s > M32)
            elif op == 'xor':
                self.wr(th, ins['rd'], a ^ b)
                self.alu_flags(th, a ^ b)
            elif op == 'and':
                self.wr(th, ins['rd'], a & b)
                self.alu_flags(th, a & b)
            elif op == 'or':
                self.wr(th, ins['rd'], a | b)
                self.alu_flags(th, a | b)
            elif op in ('cmp', 'cmpa'):
                if op == 'cmpa':
                    sa = a - (1 << 32) if a & 0x80000000 else a
                    sb = b - (1 << 32) if b & 0x80000000 else b
                    less = sa < sb
                else:
                    less = a < b
                self.wr(th, ins['rd'], 1 if less else 0)
                th.flags &= ~(BIT['Z'] | BIT['N'])
                if less:
                    th.flags |= BIT['N']
                if a == b:
                    th.flags |= BIT['Z']
            else:
                sh = b & 31
                self.shift(th, ins, a, sh, op == 'shl')
        elif op in ('addi', 'xori', 'shli', 'shri'):
            a = r[ins['rs1']]
            im = ins['imm']
            if op == 'addi':
                s = a + (im & M32)
                self.wr(th, ins['rd'], s)
                self.alu_flags(th, s, c=s > M32)
            elif op == 'xori':
                v = a ^ (im & M32)
                self.wr(th, ins['rd'], v)
                self.alu_flags(th, v)
            else:
                self.shift(th, ins, a, im, op == 'shli')
        elif op == 'lbi':
            self.wr(th, ins['rd'], ins['imm'])
        elif op == 'lli':
            self.wr(th, ins['rd'], ins['imm'])
        elif op == 'lui':
            self.wr(th, ins['rd'], (r[ins['rd']] & 0xFFFFFF) | (ins['imm'] << 24))
        elif op == 'jmp':
            self.wr(th, ins['rd'], nxt)
            nxt = ins['addr'] + 1 + ins['off']
        elif op == 'jrg':
            tgt = r[ins['rs1']] + ins['imm']
            self.wr(th, ins['rd'], nxt)
            nxt = tgt
        elif op == 'jnl':
            nxt = ins['addr'] + 1 + ins['off']
        elif op == 'jof':
            v = self.view(th, t)
            cond = bool(v & (1 << ins['flag']))
            if cond != ins['inv']:
                nxt = ins['addr'] + 1 + ins['off']
        elif op == 'joc':
            v = self.view(th, t) & 0xFFFF
            m = r[ins['rs1']] & 0xFFFF
            sel = v & m
            md = ins['mode']
            cond = {'all': sel == m, 'any': sel != 0, 'none': sel == 0, 'notall': sel != m}[md]
            if cond:
                nxt = ins['addr'] + 1 + ins['off']
        elif op in ('lb', 'lw', 'sb', 'sw'):
            w = op in ('lw', 'sw')
            a = r[ins['rs1']] + ins['imm'] * (4 if w else 1)
            ok = True
            if w and a % 4:
                self.fault(th, 0)
                ok = False
            elif a < 0 or a + (4 if w else 1) > len(self.dmem):
                self.fault(th, 1)
                ok = False
            if op in ('lb', 'lw'):
                v = 0
                if ok:
                    v = int.from_bytes(self.dmem[a:a + (4 if w else 1)], 'little')
                self.wr(th, ins['rd'], v)
            elif ok:
                v = r[ins['rs2']]
                self.dmem[a:a + (4 if w else 1)] = (v & (M32 if w else 255)).to_bytes(4 if w else 1, 'little')
        elif op == 'pull':
            self.wr(th, ins['rd'], th.isr >> ins['imm'])
            th.flags &= ~BIT['ISR_RDY']
        elif op == 'push':
            if not th.flags & BIT['OSR_EMPTY']:
                th.flags |= BIT['OVR']
            th.osr = (r[ins['rs1']] << ins['imm']) & M32
            th.flags &= ~BIT['OSR_EMPTY']
        elif op in ('inp', 'outp'):
            self.launch(th, t, op == 'inp', op == 'outp', ins['imm'])
        elif op == 'rpin':
            self.do_rpin(th, ins, t)
        elif op == 'wpin':
            p = self.pins[ins['pin']]
            if p.owner != th.tid or p.outsrc != 1:
                self.fault(th, 3)
            else:
                p.dval = r[ins['rs1']] & 1
        elif op == 'dl' or op == 'dlrg':
            n = ins['imm'] if op == 'dl' else (r[ins['rs1']] + ins['imm']) & M32
            k = max(1, (n + 2) // 3)
            step = 3 * k
            th.n_dl += k - 1
        elif op == 'waitev':
            m = r[ins['rs1']] & 0xFFFF
            if m == 0:
                self.fault(th, 5)
            else:
                v = self.view(th, t) & 0xFFFF
                sel = v & m
                al, cl = ins['all_'], ins['clear']
                cond = (sel == m) if (al and not cl) else (sel != 0) if (not al and not cl) else (sel == 0) if (al and cl) else (sel != m)
                if cond:
                    if ins['consume'] and not cl:
                        th.flags &= ~(sel & (BIT['MSG_N'] | BIT['MSG_P'] | BIT['TMR']))
                else:
                    nxt = th.pc
                    th.n_exec -= 1
                    th.n_wait += 1
        elif op == 'cfg':
            self.do_cfg(th, ins, t)
        elif op == 'flg':
            self.do_flg(th, ins, t)
        else:
            raise RuntimeError(f'op {op} not implemented')
        th.pc = nxt
        th.next_exec = t + step

    def shift(self, th, ins, a, sh, left):
        if sh == 0:
            res = a
            c = None
        elif left:
            res = (a << sh) & M32
            c = (a >> (32 - sh)) & 1
        else:
            res = a >> sh
            c = (a >> (sh - 1)) & 1
        self.wr(th, ins['rd'], res)
        self.alu_flags(th, res, c=c)

    def do_rpin(self, th, ins, t):
        m = ins['mode']
        if m in ('pend', 'pend_clr'):
            v = 0
            for p in self.pins:
                if p.owner == th.tid and self.pin_event(p, t):
                    v |= 1 << p.n
                    if m == 'pend_clr':
                        p.ev = 0
            self.wr(th, ins['rd'], v)
            return
        p = self.pins[ins['pin']]
        if m == 'level':
            if 8 <= p.n <= 15:
                self.fault(th, 3)
                self.wr(th, ins['rd'], 0)
            else:
                self.wr(th, ins['rd'], self.rd(p.n, 2, t))
        else:
            if p.owner != th.tid:
                self.fault(th, 3)
                self.wr(th, ins['rd'], 0)
            else:
                self.wr(th, ins['rd'], 1 if self.pin_event(p, t) else 0)
                if m == 'event_clr':
                    p.ev = 0

    def do_cfg(self, th, ins, t):
        v = th.regs[ins['rs1']]
        tg = ins['target_id']
        e = th.eng
        if tg == 0:
            pn = v & 31
            if pn > 23 or self.pins[pn].owner != th.tid:
                return self.fault(th, 2)
            mode, outsrc = (v >> 5) & 7, (v >> 8) & 3
            din, cin, gate = (v >> 10) & 1, (v >> 11) & 1, (v >> 12) & 1
            od, idle, own = (v >> 13) & 1, (v >> 14) & 1, (v >> 15) & 3
            if v >> 17 or own == 3 or mode == 3:
                return self.fault(th, 2)
            if (pn <= 7 and outsrc) or (8 <= pn <= 15 and (din or cin or gate)):
                return self.fault(th, 2)
            p = self.pins[pn]
            if own:
                if e.busy:
                    return self.fault(th, 2)
                p.reset()
                p.owner = (th.tid + 1) % 3 if own == 1 else (th.tid - 1) % 3
                return
            p.mode, p.outsrc, p.din, p.cin, p.gate, p.od, p.idle = mode, outsrc, din, cin, gate, od, idle
            p.ev = 0
            if outsrc == 2:
                e.dout = idle
            if outsrc == 3:
                e.clkout = idle
            if outsrc == 1:
                p.dval = idle      # ASSUMPTION: idle level = initial level of a direct-driven pin
            self.active.add(pn)
        elif tg == 1:
            pn = v & 31
            mode = (v >> 5) & 7
            if pn > 23 or self.pins[pn].owner != th.tid or (v >> 8) or mode == 3:
                return self.fault(th, 2)
            self.pins[pn].mode = mode
            self.pins[pn].ev = 0
        elif tg == 2:
            if e.busy or (v & 0xFFFF) == 0 or v >> 16:
                return self.fault(th, 2)
            e.div = v & 0xFFFF
        elif tg == 3:
            if e.busy or v >> 3:
                return self.fault(th, 2)
            e.msb, e.duplex, e.cpha = v & 1, (v >> 1) & 1, (v >> 2) & 1
        elif tg == 4:
            if e.busy:
                x = e.x
                e.tl.clear()
                e.busy = False
                e.x = None
                pp = x['pp']
                e.dout = pp['dout'].idle if pp['dout'] else 0
                e.clkout = pp['clkout'].idle if pp['clkout'] else 0
            th.flags |= BIT['OSR_EMPTY']
        elif tg == 5:
            th.flags &= ~BIT['TMR']
            th.pending = [(c, m & ~BIT['TMR']) for c, m in th.pending]
            th.tmr_exp = None if v == 0 else t + 1 + v

    def do_flg(self, th, ins, t):
        for k in ins['kws']:
            if k == 'ack_err':
                th.flags &= ~(BIT['ERR'] | BIT['ERRC0'] | BIT['ERRC1'] | BIT['ERRC2'])
            elif k == 'ack_ovr':
                th.flags &= ~BIT['OVR']
            elif k == 'ack_msgn':
                th.flags &= ~BIT['MSG_N']
            elif k == 'ack_msgp':
                th.flags &= ~BIT['MSG_P']
            elif k in ('ring_next', 'ring_prev'):
                nx = (th.tid + 1) % 3 if k == 'ring_next' else (th.tid - 1) % 3
                tgt = self.th[nx]
                bit = BIT['MSG_P'] if k == 'ring_next' else BIT['MSG_N']
                if tgt.flags & bit:
                    th.flags |= BIT['OVR']
                # ASSUMPTION (Threading.md): MSG_P visible after 1 cycle, MSG_N after 2.
                tgt.pending.append((t + (1 if k == 'ring_next' else 2), bit))

    # ---------------------------------------------------------------- main loop
    def run(self, until=None, ncycles=None):
        N = ncycles or self.N
        for t in range(self.t, N):
            self.t = t
            # 0. engine timelines advance first, so an event scheduled for cycle c shows on the pad in cycle c
            for th in self.th:
                self.eng_advance(th, t)
            # 1. pad resolution
            for pin in self.active:
                d = self.dut_drive(pin)
                a0 = d == 0
                a1 = d == 1
                for dev in self.devices:
                    if pin in dev.pins:
                        v = dev.drive_pin(pin, t, self)
                        if v == 0:
                            a0 = True
                        elif v == 1:
                            a1 = True
                self.hist[pin][t] = 0 if a0 else (1 if (a1 or pin in self.pullups) else 0)
            # 2. hardware step (watchers, timers, slave-mode engines)
            self.hw_step(t)
            # 3. CPU
            for th in self.th:
                if th.alive and th.next_exec == t:
                    self.exec(th, t)
            # 4. apply pending flag sets and pin events (visible from t+1; set wins over a clear in the same cycle)
            for p in self._evq:
                p.ev = 1
            self._evq.clear()
            for th in self.th:
                if th.pending:
                    keep = []
                    for c, m in th.pending:
                        if c <= t:
                            th.flags |= m
                        else:
                            keep.append((c, m))
                    th.pending = keep
            for dev in self.devices:
                dev.tick(t, self)
            if until and until(self, t):
                break
        self.t += 1
        return self

    # ---------------------------------------------------------------- analysis
    def edges(self, pin, t0=0, t1=None):
        h = self.hist[pin]
        t1 = t1 or self.t
        out = []
        prev = h[t0]
        for t in range(t0 + 1, t1):
            if h[t] != prev:
                out.append((t, h[t]))
                prev = h[t]
        return out
