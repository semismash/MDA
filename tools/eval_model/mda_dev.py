#!/usr/bin/env python3
"""External device models (the 'other end' of each protocol) and bus analyzers."""
import bisect

CYC_NS = 20.0   # 50 MHz


class Device:
    pins = []
    pullup_pins = []

    def drive_pin(self, pin, t, sim):
        return None

    def tick(self, t, sim):
        pass


class Schedule(Device):
    """Open-loop drivers: per pin a sorted list of (time, level)."""

    def __init__(self):
        self.ch = {}

    def add(self, pin, t, v):
        self.ch.setdefault(pin, []).append((t, v))

    def finalize(self):
        self.times = {}
        for p, l in self.ch.items():
            l.sort(key=lambda x: x[0])
            self.times[p] = [x[0] for x in l]

    def drive_pin(self, pin, t, sim):
        l = self.ch.get(pin)
        if not l:
            return None
        i = bisect.bisect_right(self.times[pin], t) - 1
        return l[i][1] if i >= 0 else self.init.get(pin)


# ------------------------------------------------------------------ UART
class UartSender(Schedule):
    """Drives the DUT's RX pin with 8N1 frames. baud_div may be fractional (to inject baud error)."""

    def __init__(self, pin, data, baud_div, start=2000, gap_bits=0.0):
        super().__init__()
        self.pins = [pin]
        self.init = {pin: 1}
        self.add(pin, 0, 1)
        t = float(start)
        self.frames = []
        for b in data:
            bits = [0] + [(b >> i) & 1 for i in range(8)] + [1]
            self.frames.append((int(round(t)), b))
            for k, v in enumerate(bits):
                self.add(pin, int(round(t + k * baud_div)), v)
            t += (10 + gap_bits) * baud_div
        self.end = int(t)
        self.finalize()


def uart_decode(sim, pin, div, t0=0, t1=None):
    """Decode 8N1 frames on a pin. Returns [(start_cycle, byte, stop_ok)]."""
    h = sim.hist[pin]
    t1 = t1 or sim.t
    out = []
    t = t0 + 1
    while t < t1 - 1:
        if h[t - 1] == 1 and h[t] == 0:
            s = t
            byte = 0
            for i in range(8):
                byte |= h[int(s + div * (1.5 + i))] << i
            stop = h[int(s + div * 9.5)]
            out.append((s, byte, bool(stop)))
            t = int(s + div * 9.5)
        else:
            t += 1
    return out


def bit_widths(sim, pin, t0, t1):
    """Widths (cycles) of every low/high run on a pin, for exactness checks."""
    e = sim.edges(pin, t0, t1)
    return [e[i + 1][0] - e[i][0] for i in range(len(e) - 1)]


# ------------------------------------------------------------------ SPI
class SpiFlashSlave(Device):
    """SPI mode 0 slave for the DUT master tests. Command 0x9F returns the JEDEC ID."""

    def __init__(self, cs, sck, mosi, miso, tco=1, ident=(0xEF, 0x40, 0x18)):
        self.cs, self.sck, self.mosi, self.miso = cs, sck, mosi, miso
        self.pins = [cs, sck, mosi, miso]
        self.tco = tco
        self.ident = ident
        self.val = 0
        self.pend = []
        self.bitn = 0
        self.byten = 0
        self.sh = 0
        self.rx = []
        self.frames = []
        self.cur = []

    def drive_pin(self, pin, t, sim):
        return self.val if pin == self.miso else None

    def out_byte(self):
        if self.byten == 0:
            return 0
        cmd = self.cur[0] if self.cur else None
        if cmd == 0x9F:
            return self.ident[self.byten - 1] if self.byten - 1 < len(self.ident) else 0xFF
        return 0xFF

    def tick(self, t, sim):
        h = sim.hist
        if t < 2:
            return
        cs, pcs = h[self.cs][t], h[self.cs][t - 1]
        sck, psck = h[self.sck][t], h[self.sck][t - 1]
        if pcs == 1 and cs == 0:
            self.bitn = self.byten = 0
            self.cur = []
            self.pend.append((t + self.tco - 1, (self.out_byte() >> 7) & 1))
        if pcs == 0 and cs == 1:
            if self.cur or self.bitn:
                self.frames.append(list(self.cur))
            self.pend.append((t + 1, 0))
        if cs == 0:
            if psck == 0 and sck == 1:
                self.sh = ((self.sh << 1) | h[self.mosi][t]) & 255
                self.bitn += 1
                if self.bitn == 8:
                    self.cur.append(self.sh)
                    self.bitn = 0
                    self.byten += 1
                    self._last_full = t
            if psck == 1 and sck == 0:
                self.pend.append((t + self.tco - 1, (self.out_byte() >> (7 - self.bitn)) & 1))
        while self.pend and self.pend[0][0] <= t:
            self.val = self.pend.pop(0)[1]


class SpiMaster(Schedule):
    """SPI mode 0 master for the DUT slave tests. half = SCLK half period in cycles."""

    def __init__(self, cs, sck, mosi, miso, frames, half, start=2000, cs_setup=20, cs_hold=20, gap=0, idle=200):
        super().__init__()
        self.cs, self.sck, self.mosi, self.miso = cs, sck, mosi, miso
        self.pins = [cs, sck, mosi]
        self.half = half
        self.init = {cs: 1, sck: 0, mosi: 0}
        for p, v in self.init.items():
            self.add(p, 0, v)
        t = start
        self.samples = []        # per frame: list of cycle times of MISO sampling
        self.frames = frames
        self.spans = []
        for fr in frames:
            self.add(cs, t, 0)
            fs = t
            t += cs_setup
            smp = []
            for bi, b in enumerate(fr):
                for k in range(7, -1, -1):
                    self.add(mosi, t, (b >> k) & 1)
                    self.add(sck, t + half, 1)
                    smp.append(t + half)
                    self.add(sck, t + 2 * half, 0)
                    t += 2 * half
                t += gap
            t += cs_hold
            self.add(cs, t, 1)
            self.spans.append((fs, t))
            self.samples.append(smp)
            t += idle
        self.end = t
        self.finalize()

    def results(self, sim):
        out = []
        for smp in self.samples:
            bits = [sim.hist[self.miso][s] for s in smp]
            out.append([sum(bits[i * 8 + j] << (7 - j) for j in range(8)) for i in range(len(bits) // 8)])
        return out


# ------------------------------------------------------------------ I2C
class I2cEeprom(Device):
    """I2C slave (7-bit addr) with a 256-byte register file; used with the DUT master. Optional clock stretching."""

    def __init__(self, scl, sda, addr=0x50, stretch=0):
        self.scl, self.sda = scl, sda
        self.pins = [scl, sda]
        self.pullup_pins = [scl, sda]
        self.addr = addr
        self.stretch = stretch
        self.sda_drv = None
        self.scl_drv = None
        self.hold_until = -1
        self.mem = [0] * 256
        self.ptr = 0
        self.state = 'idle'
        self.bitn = 0
        self.sh = 0
        self.mode = 'addr'
        self.rw = 0
        self.first = True
        self.log = []
        self.out = 0
        self.nack_seen = False

    def drive_pin(self, pin, t, sim):
        if pin == self.sda:
            return self.sda_drv
        return self.scl_drv

    def tick(self, t, sim):
        h = sim.hist
        if self.scl_drv == 0 and t >= self.hold_until:
            self.scl_drv = None
        if t < 2:
            return
        scl, pscl = h[self.scl][t], h[self.scl][t - 1]
        sda, psda = h[self.sda][t], h[self.sda][t - 1]
        if scl == 1 and pscl == 1 and psda == 1 and sda == 0:       # START
            self.state = 'run'
            self.bitn = 0
            self.mode = 'addr'
            self.sda_drv = None
            self.log.append((t, 'START'))
            return
        if scl == 1 and pscl == 1 and psda == 0 and sda == 1:       # STOP
            self.state = 'idle'
            self.sda_drv = None
            self.log.append((t, 'STOP'))
            return
        if self.state != 'run':
            return
        if pscl == 0 and scl == 1:                                   # rising
            if self.bitn < 8:
                self.sh = ((self.sh << 1) | sda) & 255
                self.bitn += 1
            else:
                self.bitn = 9
                self.ackbit = sda                                    # master's ACK for reads
        elif pscl == 1 and scl == 0:                                 # falling
            if self.bitn == 8:
                if self.mode == 'addr':
                    if (self.sh >> 1) == self.addr:
                        self.rw = self.sh & 1
                        self.sda_drv = 0
                        self.log.append((t, 'ADDR', self.sh))
                    else:
                        self.state = 'idle'
                elif self.mode == 'w':
                    self.sda_drv = 0
                    self.log.append((t, 'WDATA', self.sh))
                    if self.first:
                        self.ptr = self.sh
                        self.first = False
                    else:
                        self.mem[self.ptr] = self.sh
                        self.ptr = (self.ptr + 1) & 255
                else:
                    self.sda_drv = None
                if self.stretch and self.sda_drv == 0:
                    self.scl_drv = 0
                    self.hold_until = t + self.stretch
            elif self.bitn == 9:
                if self.mode == 'addr':
                    self.mode = 'r' if self.rw else 'w'
                    self.first = True
                    if self.rw:
                        self.out = self.mem[self.ptr]
                        self.sda_drv = None if (self.out >> 7) & 1 else 0
                    else:
                        self.sda_drv = None
                elif self.mode == 'r':
                    if self.ackbit == 0:
                        self.ptr = (self.ptr + 1) & 255
                        self.out = self.mem[self.ptr]
                        self.sda_drv = None if (self.out >> 7) & 1 else 0
                    else:
                        self.sda_drv = None
                        self.state = 'idle'
                else:
                    self.sda_drv = None
                self.bitn = 0
            elif self.mode == 'r' and 1 <= self.bitn < 8:
                self.sda_drv = None if (self.out >> (7 - self.bitn)) & 1 else 0
            else:
                if self.mode != 'r':
                    self.sda_drv = None


class I2cMaster(Device):
    """Closed-loop I2C master (generator based) for the DUT slave tests. Times are in cycles."""

    def __init__(self, scl, sda, script, tlow=70, thigh=55, tsusta=35, thdsta=35, tsusto=35, tbuf=70,
                 tsudat=8, thddat=8, start=3000):
        self.scl, self.sda = scl, sda
        self.pins = [scl, sda]
        self.pullup_pins = [scl, sda]
        self.script = script
        self.p = dict(tlow=tlow, thigh=thigh, tsusta=tsusta, thdsta=thdsta, tsusto=tsusto, tbuf=tbuf,
                      tsudat=tsudat, thddat=thddat)
        self.scl_drv = None
        self.sda_drv = None
        self.start = start
        self.gen = self._run()
        self.wait = 0
        self.now = 0
        self.sim = None
        self.acks = []
        self.reads = []
        self.stretch_seen = 0
        self.late = 0          # bits where the slave's SDA was not yet valid when SCL was released (setup violation)
        self.done = False

    def drive_pin(self, pin, t, sim):
        return self.scl_drv if pin == self.scl else self.sda_drv

    def tick(self, t, sim):
        self.now = t
        self.sim = sim
        if self.wait > 0:
            self.wait -= 1
            return
        try:
            while True:
                n = next(self.gen)
                if n > 0:
                    self.wait = n - 1
                    return
        except StopIteration:
            self.done = True

    def _sda(self, v):
        self.sda_drv = None if v else 0

    def _scl_release_wait(self):
        self.scl_drv = None
        yield 1
        n = 0
        while self.sim.hist[self.scl][self.now] == 0:
            n += 1
            yield 1
        self.stretch_seen = max(self.stretch_seen, n)

    def _bit(self, v, sample=False):
        p = self.p
        self._sda(v)
        yield p['tsudat']
        pre = self.sim.hist[self.sda][self.now]
        yield from self._scl_release_wait()
        yield p['thigh'] - 1
        s = self.sim.hist[self.sda][self.now]
        if pre != s:
            self.late += 1
        yield 1
        self.scl_drv = 0
        yield p['thddat']
        return s

    def _run(self):
        p = self.p
        yield self.start
        for op in self.script:
            k = op[0]
            if k == 'start':
                self._sda(1)
                self.scl_drv = None
                yield p['tbuf']
                self._sda(0)
                yield p['thdsta']
                self.scl_drv = 0
                yield max(1, p['tlow'] - p['tsudat'] - 1)       # honour tLOW before the first data bit
            elif k == 'rstart':
                self._sda(1)
                yield p['tsudat']
                yield from self._scl_release_wait()
                yield p['tsusta']
                self._sda(0)
                yield p['thdsta']
                self.scl_drv = 0
                yield max(1, p['tlow'] - p['tsudat'] - 1)
            elif k == 'wr':
                for i in range(7, -1, -1):
                    yield from self._bit((op[1] >> i) & 1)
                    yield p['tlow'] - p['thddat'] - p['tsudat'] - 1 if p['tlow'] > p['thddat'] + p['tsudat'] + 1 else 1
                a = yield from self._bit(1)
                self.acks.append(a)
                yield p['tlow'] - p['thddat'] - p['tsudat'] - 1
            elif k == 'rd':
                v = 0
                for i in range(8):
                    s = yield from self._bit(1)
                    v = (v << 1) | s
                    yield p['tlow'] - p['thddat'] - p['tsudat'] - 1
                self.reads.append(v)
                yield from self._bit(op[1])           # ACK=0 / NACK=1 driven by master
                yield p['tlow'] - p['thddat'] - p['tsudat'] - 1
            elif k == 'stop':
                self._sda(0)
                yield p['tsudat']
                yield from self._scl_release_wait()
                yield p['tsusto']
                self._sda(1)
                yield p['tbuf']
            elif k == 'wait':
                yield op[1]
        self.done = True
        while True:
            yield 1000


def i2c_analyze(sim, scl, sda, t0=0, t1=None):
    """Measure I2C bus timing (in ns) from the pad history. Returns dict of min/max values."""
    hs, hd = sim.hist[scl], sim.hist[sda]
    t1 = t1 or sim.t
    ev = []
    for t in range(t0 + 1, t1):
        if hs[t] != hs[t - 1]:
            ev.append((t, 'scl', hs[t]))
        if hd[t] != hd[t - 1]:
            ev.append((t, 'sda', hd[t]))
    ev.sort(key=lambda e: e[0])
    m = {k: [] for k in ('tLOW', 'tHIGH', 'tSU_STA', 'tHD_STA', 'tSU_STO', 'tBUF', 'tSU_DAT', 'tHD_DAT', 'period')}
    last = dict(scl_r=None, scl_f=None, sda_c=None, start=None, stop=None)
    scl_v, sda_v = hs[t0], hd[t0]
    prev_scl_rise = None
    for t, w, v in ev:
        if w == 'scl':
            if v == 1:
                if last['scl_f'] is not None:
                    m['tLOW'].append(t - last['scl_f'])
                if last['sda_c'] is not None and last['sda_c'] > (last['scl_f'] or -1):
                    m['tSU_DAT'].append(t - last['sda_c'])
                if prev_scl_rise is not None and t - prev_scl_rise < 1000:
                    m['period'].append(t - prev_scl_rise)
                prev_scl_rise = t
                last['scl_r'] = t
            else:
                if last['scl_r'] is not None:
                    m['tHIGH'].append(t - last['scl_r'])
                if last['start'] is not None and last['start'] > (last['scl_f'] or -1):
                    m['tHD_STA'].append(t - last['start'])
                last['scl_f'] = t
            scl_v = v
        else:
            if scl_v == 1:
                if v == 0:      # START or repeated START
                    if last['scl_r'] is not None and last['stop'] is None or True:
                        if last['stop'] is not None and last['stop'] > (last['start'] or -1):
                            m['tBUF'].append(t - last['stop'])
                        elif last['scl_r'] is not None:
                            m['tSU_STA'].append(t - last['scl_r'])
                    last['start'] = t
                else:           # STOP
                    if last['scl_r'] is not None:
                        m['tSU_STO'].append(t - last['scl_r'])
                    last['stop'] = t
            else:
                if last['scl_f'] is not None:
                    m['tHD_DAT'].append(t - last['scl_f'])
                last['sda_c'] = t
            sda_v = v
    res = {}
    for k, l in m.items():
        if l:
            res[k] = (min(l) * CYC_NS, max(l) * CYC_NS, len(l))
    return res
