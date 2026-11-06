#!/usr/bin/env python3
"""mda_e2e.py: end-to-end differential test of the whole RTL (mda_top: core, memories, loader ports) against the
independent eval simulator (tools/eval_model/mda_sim.py). Programs are assembled with the eval assembler, encoded with
tools/isa/isa_gen.py, loaded into the instruction memory through the loader port, and run on the elaborated SystemVerilog
(verif/svflat.py). Final registers, flags (Z N C ERR ERRC OVR) and the whole data memory are compared.

  python3 verif/mda_e2e.py directed
  python3 verif/mda_e2e.py fuzz [--count 100] [--first 1] [--mode plain|jrg|faults|mixed] [--len 40] [--cycles 800]

Run from anywhere; the repo root is the parent of verif/ (override with MDA_ROOT). Exit code 1 on any mismatch."""
import argparse, glob, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MDA_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
SRC = os.path.join(ROOT, 'src')
for p in (HERE, os.path.join(ROOT, 'tools', 'isa'), os.path.join(ROOT, 'tools', 'eval_model'), os.path.join(ROOT, 'tools')):
    if os.path.isdir(p): sys.path.insert(0, p)
from svflat import package_consts, package_types, parse_module, elaborate, Sim
from isa_gen import Isa
from mda_asm import assemble
from mda_sim import Sim as RefSim
isa = Isa(os.path.join(ROOT, 'tools', 'isa', 'isa.yaml')); enc = isa.encode
C = package_consts(os.path.join(SRC, 'mda_pkg.sv'), os.path.join(SRC, 'mda_isa_pkg.sv'))
T = package_types(C, os.path.join(SRC, 'mda_pkg.sv'), os.path.join(SRC, 'mda_isa_pkg.sv'))
def load_defs(rdir=None):
    defs = {}
    for f in glob.glob(os.path.join(rdir or SRC, 'mda_*.sv')):
        if 'pkg' in f: continue
        md = parse_module(f); defs[md.name] = md
    return defs

# ------------------------------------------------------------------ assembler output -> instruction words
RR = ('add','xor','and','or','cmp','cmpa','shl','shr'); RIA = ('addi','xori','shli','shri')
def encode_prog(prog):
    words = {}
    for addr, i in prog.mem.items():
        op = i['op']
        if op in RR:      words[addr] = enc(op, rd=i['rd'] or 0, rs1=i['rs1'], rs2=i['rs2'], wb=int(i['rd'] is not None))
        elif op in RIA:   words[addr] = enc(op, rd=i['rd'] or 0, rs1=i['rs1'], imm=i['imm'], wb=int(i['rd'] is not None))
        elif op in ('lb','lw'): words[addr] = enc(op, rd=i['rd'], rs1=i['rs1'], offset=i['imm'])
        elif op in ('sb','sw'): words[addr] = enc(op, rs1=i['rs1'], rs2=i['rs2'], offset=i['imm'])
        elif op in ('lbi','lui'): words[addr] = enc(op, rd=i['rd'], imm=i['imm'])
        elif op == 'lli':
            words[addr] = enc('lli', rd=i['rd'], imm=(i['imm'] >> 16) & 0xFF); words[addr + 1] = i['imm'] & 0xFFFF
        elif op == 'jmp': words[addr] = enc('jmp', rd=i['rd'], offset=i['off'])
        elif op == 'jnl': words[addr] = enc('jnl', offset=i['off'])
        elif op == 'jof': words[addr] = enc('jof_inv' if i['inv'] else 'jof', flag=i['flag'], offset=i['off'])
        elif op == 'joc':
            name, inv = {'all': ('joc_all', 0), 'notall': ('joc_all', 1), 'any': ('joc_any', 0), 'none': ('joc_any', 1)}[i['mode']]
            words[addr] = enc(name, rs1=i['rs1'], inv=inv, offset=i['off'])
        elif op == 'jrg': words[addr] = enc('jrg', rd=i['rd'], rs1=i['rs1'], imm=i['imm'])
        else: raise ValueError(op)
    return {a: (w[0] if isinstance(w, (list, tuple)) else w) & 0xFFFF for a, w in words.items()}

# ------------------------------------------------------------------ random three-thread programs (forward jumps only, so they terminate)
import random
RR = ['add','xor','and','or','cmp','cmpa','shl','shr']; RIA = ['addi','xori','shli','shri']
BASE = {0: 0x000, 1: 0x100, 2: 0x200}
FLG = ['Z','N','C','ERR']
def gen_thread(t, rng, n=40, faults=True, fault_p=0.0, jrg_p=0.03):
    """items: ('ins', text, size) | ('label', name) | ('jf', kind, ...) resolved later. Forward jumps only, so every program terminates."""
    reg = lambda lo=0: rng.randrange(lo, 8)
    wr = lambda: rng.choice([0,1,2,3,4,5,6])             # r7 is the thread's base pointer, never a destination
    items = [('ins', f'lbi r7, {BASE[t] >> 4}', 1), ('ins', 'shli r7, r7, 4', 1)]   # r7 = base (0x00, 0x10<<4 = 0x100, 0x200)
    lab = 0; pending = []
    def new_label(dist): 
        nonlocal lab; lab += 1; pending.append([f'L{t}_{lab}', dist]); return f'L{t}_{lab}'
    for k in range(n):
        # place due labels
        for p in list(pending):
            if p[1] <= 0: items.append(('label', p[0])); pending.remove(p)
            else: p[1] -= 1
        if faults and rng.random() < fault_p:
            kind = rng.choice(['mis_lw','mis_sw','oob_sw','oob_lb','oob_sb'])
            if kind == 'mis_lw':   items += [('ins','addi r6, r7, 1',1), ('ins',f'lw r{wr()}, 0(r6)',1)]
            elif kind == 'mis_sw': items += [('ins','addi r6, r7, 2',1), ('ins',f'sw r{reg()}, 0(r6)',1)]
            elif kind == 'oob_sw': items += [('ins',f'lui r6, {rng.randrange(1,256)}',1), ('ins',f'sw r{reg()}, 0(r6)',1)]
            elif kind == 'oob_lb': items += [('ins',f'lui r6, {rng.randrange(1,256)}',1), ('ins',f'lb r{wr()}, 0(r6)',1)]
            else:                  items += [('ins',f'lui r6, {rng.randrange(1,256)}',1), ('ins',f'sb r{reg()}, 0(r6)',1)]
            continue
        if rng.random() < jrg_p:
            # jmp to the next instruction (link = address of the jrg), then a forward jrg from that link
            items += [('ins', 'jmp r5, LJ%d_%d' % (t, k), 1), ('label', 'LJ%d_%d' % (t, k)), ('jrg', rng.randrange(0, 7), rng.randrange(1, 5))]
            continue
        c = rng.random()
        if c < 0.22:   items.append(('ins', f"{rng.choice(RR)} {'@na' if rng.random()<0.2 else 'r%d'%wr()}, r{reg()}, r{reg()}", 1))
        elif c < 0.38: items.append(('ins', f"{rng.choice(RIA)} {'@na' if rng.random()<0.15 else 'r%d'%wr()}, r{reg()}, {rng.randrange(0,16) if False else 0}", 1)); i = items[-1]; op = i[1].split()[0]; imm = rng.randrange(-8, 8) if op in ('addi','xori') else rng.randrange(0, 16); items[-1] = ('ins', i[1].rsplit(',',1)[0] + f', {imm}', 1)
        elif c < 0.44: items.append(('ins', f'lbi r{wr()}, {rng.randrange(256)}', 1))
        elif c < 0.48: items.append(('ins', f'lui r{wr()}, {rng.randrange(256)}', 1))
        elif c < 0.53: items.append(('ins', f'lli r{wr()}, {rng.randrange(1<<24)}', 2))
        elif c < 0.63: items.append(('ins', f'sw r{reg()}, {rng.randrange(32)}(r7)', 1))
        elif c < 0.69: items.append(('ins', f'sb r{reg()}, {rng.randrange(32)}(r7)', 1))
        elif c < 0.77: items.append(('ins', f'lw r{wr()}, {rng.randrange(32)}(r7)', 1))
        elif c < 0.83: items.append(('ins', f'lb r{wr()}, {rng.randrange(32)}(r7)', 1))
        elif c < 0.90:
            f = rng.choice(FLG); items.append(('ins', f"jof {f}, {new_label(rng.randrange(1,5))}{', @inv' if rng.random()<0.5 else ''}", 1))
        elif c < 0.94:
            mode = rng.choice(['all','any','none','notall']); items.append(('ins', f'joc r{reg()}, @{mode}, {new_label(rng.randrange(1,5))}', 1))
        elif c < 0.96: items.append(('ins', f'jmp r{wr()}, {new_label(rng.randrange(1,4))}', 1))
        elif c < 0.97: items.append(('ins', f'jnl {new_label(rng.randrange(1,4))}', 1))
        elif faults and c < 0.985:
            kind = rng.choice(['mis_lw','mis_sw','oob_sw','oob_lb','oob_sb'])
            if kind == 'mis_lw':  items += [('ins','addi r6, r7, 1',1), ('ins',f'lw r{wr()}, 0(r6)',1)]
            elif kind == 'mis_sw': items += [('ins','addi r6, r7, 2',1), ('ins',f'sw r{reg()}, 0(r6)',1)]
            elif kind == 'oob_sw': items += [('ins',f'lui r6, {rng.randrange(1,256)}',1), ('ins',f'sw r{reg()}, 0(r6)',1)]
            elif kind == 'oob_lb': items += [('ins',f'lui r6, {rng.randrange(1,256)}',1), ('ins',f'lb r{wr()}, 0(r6)',1)]
            else:                  items += [('ins',f'lui r6, {rng.randrange(1,256)}',1), ('ins',f'sb r{reg()}, 0(r6)',1)]
        else: items.append(('ins', f'xori r{wr()}, r{reg()}, -1', 1))
    for p in pending: items.append(('label', p[0]))
    items.append(('ins', '$halt', 1))
    return items
def resolve(items):
    addr = []; a = 0
    for it in items:
        addr.append(a)
        a += {'ins': it[2] if it[0] == 'ins' else 0, 'label': 0, 'jrg': 1}[it[0]]
    out = []
    for i, it in enumerate(items):
        if it[0] != 'jrg': out.append(it); continue
        rd, k = it[1], it[2]
        later = [j for j in range(i + 1, len(items)) if items[j][0] in ('ins', 'jrg')]
        tgt = addr[later[min(k, len(later)) - 1]] if later else addr[i] + 1
        out.append(('ins', f'jrg r{rd}, r5, {tgt - addr[i]}', 1))
    return out
def render(items):
    items = resolve(items)
    out = []
    for it in items: out.append(f"{it[1]}:" if it[0] == 'label' else '    ' + it[1])
    return '\n'.join(out)
def gen_program(seed, n=40, faults=True, fault_p=0.0, jrg_p=0.03):
    rng = random.Random(seed)
    src = ".mda\n.text\n"
    for t in range(3):
        fp = rng.choice([0.0, 0.0, 0.03, 0.25]) if fault_p == 'mixed' else fault_p       # mixed: each thread gets its own fault rate
        src += f".entry{t}\n" + render(gen_thread(t, rng, n, faults, fp, jrg_p)) + "\n"
    return src

# ------------------------------------------------------------------ directed program
PROG = """
.mda
.text
; ---------------------------------------------------------------- thread 0: loop, flags, constants, call and return
.entry0
    lbi  r1, 0
    lbi  r2, 10
loop0:
    add  r1, r1, r2
    addi r2, r2, -1
    jof  Z, loop0, @inv
    lbi  r4, 0
    sw   r1, 0(r4)
    lli  r5, 0xABCDEF
    sw   r5, 1(r4)
    lw   r6, 1(r4)
    shli r7, r6, 4
    cmpa r3, r1, r2
    xori r3, r3, -1
    sw   r3, 2(r4)
    jmp  r6, sub0
    sw   r7, 3(r4)
    lb   r2, 4(r4)
    add  r1, r1, r2
    lbi  r5, 5
    joc  r5, @all, hit0
    lbi  r6, 1
    jnl  end0
hit0:
    lbi  r6, 2
end0:
    sw   r6, 4(r4)
    $halt
sub0:
    addi r7, r7, 3
    jrg  r5, r6, 0
; ---------------------------------------------------------------- thread 1: byte and word memory access, misaligned and out-of-bounds faults
.entry1
    lbi  r1, 64
    lli  r3, 0x123456
    sw   r3, 0(r1)
    lbi  r2, 0x7F
    sb   r2, 4(r1)
    xori r2, r2, -1
    sb   r2, 5(r1)
    lbi  r2, 0x55
    sb   r2, 6(r1)
    sb   r2, 7(r1)
    lw   r5, 1(r1)
    lb   r6, 1(r1)
    lb   r4, 2(r1)
    addi r1, r1, 2
    lw   r7, 0(r1)
    cmp  r3, r5, r6
    lbi  r1, 0
    lui  r1, 128
    sw   r2, 0(r1)
    lw   r2, 0(r1)
    $halt
; ---------------------------------------------------------------- thread 2: out-of-bounds first, logic and shifts, carry, signed and unsigned compare
.entry2
    lbi  r1, 0
    lui  r1, 1
    lbi  r6, 99
    sb   r6, 0(r1)
    lbi  r1, 128
    lbi  r2, 0xF0
    lbi  r3, 0x3C
    xor  r4, r2, r3
    and  r5, r2, r3
    or   r6, r2, r3
    shl  r7, r2, r3
    sw   r4, 0(r1)
    sw   r5, 1(r1)
    sw   r6, 2(r1)
    sw   r7, 3(r1)
    shr  r7, r7, r3
    shri r5, r6, 3
    shli r4, r6, 15
    lli  r2, 0xFFFFFF
    shli r2, r2, 8
    add  r2, r2, r2
    jof  C, carry2
    lbi  r6, 0
    jnl  e2
carry2:
    lbi  r6, 1
e2:
    sw   r6, 4(r1)
    cmp  r3, r2, r4
    cmpa @na, r2, r4
    jof  N, neg2
    lbi  r7, 1
    jnl  end2
neg2:
    lbi  r7, 2
end2:
    sw   r7, 5(r1)
    $halt
"""

# ------------------------------------------------------------------ run the RTL
IDLE = dict(rst_n=1, go=0, entry_pc0=0, entry_pc1=0, entry_pc2=0, imem_ld_we=0, imem_ld_addr=0, imem_ld_data=0, dmem_ld_we=0, dmem_ld_addr=0, dmem_ld_data=0)
def run_rtl(src, cycles, defs=None, seed=1):
    defs = defs or load_defs(); prog = assemble(src); words = encode_prog(prog)
    fl = elaborate(defs, 'mda_top', C, T); sim = Sim(fl, random.Random(seed))
    for _ in range(3): sim.step({**IDLE, 'rst_n': 0})
    for a, wd in sorted(words.items()): sim.step({**IDLE, 'imem_ld_we': 1, 'imem_ld_addr': a, 'imem_ld_data': wd})
    for a in range(256): sim.step({**IDLE, 'dmem_ld_we': 1, 'dmem_ld_addr': a, 'dmem_ld_data': 0})
    init_regs = [list(sim.env[f'u_core__u_regbank__u_bank{t}__register_file'][0]) for t in range(3)]
    ent = {f'entry_pc{t}': (prog.entry.get(t) or 0) for t in range(3)}
    sim.step({**IDLE, 'go': 1, **ent})
    for _ in range(cycles): sim.step(dict(IDLE))
    regs = [list(sim.env[f'u_core__u_regbank__u_bank{t}__register_file'][0]) for t in range(3)]
    flags = [sim.get(f'u_core__u_ex__u_flags{t}__flag_reg') for t in range(3)]
    dm = bytearray()
    for wd in sim.env['u_dmem__u_sram__mem'][0]: dm += wd.to_bytes(4, 'little')
    return dict(init_regs=init_regs, regs=regs, flags=flags, dmem=bytes(dm))

FLAGMASK = 0x107F      # Z N C ERR ERRC[2:0] and OVR; the event flags belong to Stage B
def compare(src, cycles, defs=None):
    r = run_rtl(src, cycles, defs=defs)
    s = RefSim(src, dmem=1024, ncycles=cycles)
    for t in range(3): s.th[t].regs = list(r['init_regs'][t])      # RTL registers are not reset: both sides start from the same values
    s.run(ncycles=cycles); bad = []
    for t in range(3):
        if s.prog.entry.get(t) is None: continue
        for i in range(8):
            if r['regs'][t][i] != s.th[t].regs[i] & 0xFFFFFFFF: bad.append(f"thread {t} r{i}: rtl {r['regs'][t][i]:#x} ref {s.th[t].regs[i] & 0xFFFFFFFF:#x}")
        if (r['flags'][t] & FLAGMASK) != (s.th[t].flags & FLAGMASK): bad.append(f"thread {t} flags: rtl {r['flags'][t] & FLAGMASK:#06x} ref {s.th[t].flags & FLAGMASK:#06x}")
    ref_mem = bytes(s.dmem[:1024])
    if r['dmem'] != ref_mem:
        diff = [i for i in range(1024) if r['dmem'][i] != ref_mem[i]]
        bad.append(f"data memory differs at {len(diff)} bytes, first: " + ", ".join(f"[{i:#x}] rtl {r['dmem'][i]:#04x} ref {ref_mem[i]:#04x}" for i in diff[:6]))
    return bad

def fuzz(seeds, n=40, cycles=800, mode='mixed', defs=None):
    kw = dict(plain=dict(), jrg=dict(jrg_p=0.12), faults=dict(fault_p=0.2), mixed=dict(fault_p='mixed', jrg_p=0.05))[mode]
    defs = defs or load_defs(); fails = []; t0 = time.time()
    for sd in seeds:
        try: bad = compare(gen_program(sd, n, True, **kw), cycles, defs)
        except Exception as e: bad = [f"EXCEPTION {type(e).__name__}: {e}"]
        if bad:
            fails.append(sd); print(f"seed {sd}: {len(bad)} mismatches", *bad[:4], sep="\n    ")
    print(f"{len(seeds)} random three-thread programs (mode {mode}, {n} items per thread, {cycles} cycles): {len(seeds) - len(fails)} match, {len(fails)} mismatch | {time.time() - t0:.0f}s")
    return fails

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['directed', 'fuzz'])
    ap.add_argument('--count', type=int, default=100); ap.add_argument('--first', type=int, default=1)
    ap.add_argument('--mode', default='mixed', choices=['plain', 'jrg', 'faults', 'mixed']); ap.add_argument('--len', type=int, default=40); ap.add_argument('--cycles', type=int, default=800)
    a = ap.parse_args()
    if a.cmd == 'directed':
        bad = compare(PROG, 900)
        print("directed three-thread program, 900 cycles:", "MATCH (registers, flags, data memory)" if not bad else f"{len(bad)} MISMATCHES"); [print("   ", b) for b in bad]
        sys.exit(1 if bad else 0)
    fails = fuzz(range(a.first, a.first + a.count), a.len, a.cycles, a.mode); sys.exit(1 if fails else 0)
