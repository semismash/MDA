"""svflat: elaborating cycle simulator for the SystemVerilog subset used in MDA. Flattens the instance hierarchy into one
netlist of assigns / always_comb / always_ff items, orders the combinational items topologically, and simulates clock by clock."""
import os, re, random
from svmini import tokenize, Parser, ev, exe, M, package_consts, NBA, apply_nba

def package_types(consts, *paths):
    types = {}
    for p in paths:
        toks = tokenize(open(p).read()); i = 0
        while i < len(toks):
            if toks[i][1] == 'typedef':
                pr = Parser(toks); pr.i = i + 1; pr.ex('logic'); w = 1
                if pr.pk() == '[':
                    pr.nx(); hi = pr.expr(); pr.ex(':'); lo = pr.expr(); pr.ex(']')
                    w = abs(ev(hi, consts)[0] - ev(lo, consts)[0]) + 1
                types[pr.nx()[1]] = w; i = pr.i
            else: i += 1
    return types

class ModDef: pass

def parse_module(path):
    toks = tokenize(open(path).read()); i = 0
    while toks[i][1] != 'module': i += 1
    pr = Parser(toks); pr.i = i + 1
    md = ModDef(); md.name = pr.nx()[1]; md.params = []; md.ports = []; md.items = []; md.decls = []; md.localparams = []; md.insts = []
    if pr.pk() == '#':
        pr.nx(); pr.ex('(')
        while pr.pk() != ')':
            pr.ex('parameter')
            while pr.pk(1) != '=': pr.nx()
            pn = pr.nx()[1]; pr.ex('='); md.params.append((pn, pr.expr()))
            if pr.pk() == ',': pr.nx()
        pr.ex(')')
    pr.ex('(')
    while pr.pk() != ')':
        d = pr.nx()[1]; first = pr.nx()[1]; wspec = None
        if pr.pk() in (',', ')'): pname = first
        else:
            if pr.pk() == '[':
                pr.nx(); hi = pr.expr(); pr.ex(':'); lo = pr.expr(); pr.ex(']'); wspec = ('range', hi, lo)
            elif first not in ('logic', 'wire', 'reg'): wspec = ('type', first)
            pname = pr.nx()[1]
        md.ports.append((d, pname, wspec))
        if pr.pk() == ',': pr.nx()
    pr.ex(')'); pr.ex(';')
    while pr.pk() != 'endmodule':
        v = pr.pk()
        if v == 'assign':
            pr.nx(); tgt = pr.nx()[1]; pr.ex('='); md.items.append(('assign', tgt, pr.expr())); pr.ex(';')
        elif v == 'always_comb': pr.nx(); md.items.append(('comb', pr.stmt()))
        elif v == 'always_ff':
            pr.nx(); pr.ex('@'); pr.ex('(')
            while pr.pk() != ')': pr.nx()
            pr.nx(); md.items.append(('ff', pr.stmt()))
        elif v in ('localparam', 'parameter'):
            pr.nx()
            while True:
                while pr.pk(1) != '=': pr.nx()
                pn = pr.nx()[1]; pr.ex('='); md.localparams.append((pn, pr.expr()))
                if pr.pk() == ',': pr.nx(); continue
                break
            pr.ex(';')
        elif v == 'import':
            while pr.pk() != ';': pr.nx()
            pr.nx()
        elif v in ('generate', 'genvar'): raise NotImplementedError(v)
        elif pr.pk(1) == '#' or (pr.pk(2) == '(' and pr.pk(1) not in ('[',)):
            mod = pr.nx()[1]; params = {}
            if pr.pk() == '#':
                pr.nx(); pr.ex('(')
                while pr.pk() != ')':
                    pr.ex('.'); pn = pr.nx()[1]; pr.ex('('); params[pn] = pr.expr(); pr.ex(')')
                    if pr.pk() == ',': pr.nx()
                pr.ex(')')
            iname = pr.nx()[1]; pr.ex('('); conns = {}
            while pr.pk() != ')':
                pr.ex('.'); port = pr.nx()[1]; pr.ex('(')
                conns[port] = None if pr.pk() == ')' else pr.expr()
                pr.ex(')')
                if pr.pk() == ',': pr.nx()
            pr.ex(')'); pr.ex(';'); md.insts.append((mod, iname, params, conns))
        else:
            t0 = pr.nx()[1]; wspec = None
            if t0 in ('int', 'integer'): wspec = ('const', 32)
            elif t0 in ('logic', 'wire', 'reg'):
                if pr.pk() == '[':
                    pr.nx(); hi = pr.expr(); pr.ex(':'); lo = pr.expr(); pr.ex(']'); wspec = ('range', hi, lo)
            else: wspec = ('type', t0)
            while True:
                nm = pr.nx()[1]; dim = None
                if pr.pk() == '[':
                    pr.nx(); a = pr.expr(); pr.ex(':'); b = pr.expr(); pr.ex(']'); dim = (a, b)
                md.decls.append((nm, wspec, dim))
                if pr.pk() == '=':
                    pr.nx(); md.items.append(('assign', nm, pr.expr()))
                if pr.pk() == ',': pr.nx(); continue
                break
            pr.ex(';')
    return md

# ------------------------------------------------------------------ elaboration
def rn(n, pre, consts):
    if n is None: return None
    t = n[0]
    if t == 'num': return n
    if t == 'id':
        if n[1] in consts: v, w = consts[n[1]]; return ('num', v, w)
        return ('id', pre + n[1])
    if t == 'sel': return ('sel', pre + n[1], rn(n[2], pre, consts), rn(n[3], pre, consts))
    if t == 'un' or t == 'red': return (t, n[1], rn(n[2], pre, consts))
    if t == 'bin': return ('bin', n[1], rn(n[2], pre, consts), rn(n[3], pre, consts))
    if t == '?': return ('?', rn(n[1], pre, consts), rn(n[2], pre, consts), rn(n[3], pre, consts))
    if t == 'cat': return ('cat', [rn(x, pre, consts) for x in n[1]])
    if t == 'rep': return ('rep', rn(n[1], pre, consts), rn(n[2], pre, consts))
    if t == 'call': return ('call', n[1], [rn(x, pre, consts) for x in n[2]])
    if t == 'block': return ('block', [rn(x, pre, consts) for x in n[1]])
    if t == 'if': return ('if', rn(n[1], pre, consts), rn(n[2], pre, consts), rn(n[3], pre, consts))
    if t == 'case': return ('case', rn(n[1], pre, consts), [([rn(l, pre, consts) for l in ls], rn(b, pre, consts)) for ls, b in n[2]], rn(n[3], pre, consts))
    if t == 'for': return ('for', pre + n[1], rn(n[2], pre, consts), rn(n[3], pre, consts), pre + n[4], rn(n[5], pre, consts), rn(n[6], pre, consts))
    if t == 'assign_cat': return ('assign_cat', [pre + x for x in n[1]], rn(n[2], pre, consts))
    if t in ('assign_idx', 'nba_idx'): return (t, pre + n[1], rn(n[2], pre, consts), rn(n[3], pre, consts))
    if t in ('assign', 'nba'): return (t, pre + n[1], rn(n[2], pre, consts))
    raise ValueError(t)

def reads_writes(n, R, W):
    if n is None: return
    t = n[0]
    if t == 'num': return
    if t == 'id': R.add(n[1]); return
    if t == 'sel': R.add(n[1]); reads_writes(n[2], R, W); reads_writes(n[3], R, W); return
    if t in ('un', 'red'): reads_writes(n[2], R, W); return
    if t == 'bin': reads_writes(n[2], R, W); reads_writes(n[3], R, W); return
    if t == '?': [reads_writes(x, R, W) for x in n[1:]]; return
    if t == 'cat': [reads_writes(x, R, W) for x in n[1]]; return
    if t == 'rep': reads_writes(n[1], R, W); reads_writes(n[2], R, W); return
    if t == 'call': [reads_writes(x, R, W) for x in n[2]]; return
    if t == 'block': [reads_writes(x, R, W) for x in n[1]]; return
    if t == 'if': [reads_writes(x, R, W) for x in n[1:]]; return
    if t == 'case':
        reads_writes(n[1], R, W)
        for ls, b in n[2]: [reads_writes(l, R, W) for l in ls]; reads_writes(b, R, W)
        reads_writes(n[3], R, W); return
    if t == 'for': W.add(n[1]); [reads_writes(x, R, W) for x in (n[2], n[3], n[5], n[6])]; return
    if t == 'assign_cat': W.update(n[1]); reads_writes(n[2], R, W); return
    if t in ('assign_idx', 'nba_idx'): W.add(n[1]); reads_writes(n[2], R, W); reads_writes(n[3], R, W); return
    if t in ('assign', 'nba'): W.add(n[1]); reads_writes(n[2], R, W); return
    raise ValueError(t)

class Flat: pass

def elaborate(defs, top, pkg_consts, types, top_overrides=None):
    fl = Flat(); fl.items = []; fl.widths = {}; fl.arrays = {}; fl.top_ports = {}
    def wid(wspec, consts):
        if wspec is None: return 1
        if wspec[0] == 'range': return abs(ev(wspec[1], consts)[0] - ev(wspec[2], consts)[0]) + 1
        if wspec[0] == 'type': return types[wspec[1]]
        return wspec[1]
    def go(mname, pre, overrides):
        md = defs[mname]; consts = dict(pkg_consts)
        for pn, pe in md.params: consts[pn] = overrides[pn] if pn in overrides else ev(pe, consts)
        for pn, pe in md.localparams: consts[pn] = ev(pe, consts)
        for d, pn, ws in md.ports: fl.widths[pre + pn] = wid(ws, consts)
        for nm, ws, dim in md.decls:
            w = wid(ws, consts)
            if dim is not None:
                depth = abs(ev(dim[0], consts)[0] - ev(dim[1], consts)[0]) + 1; fl.arrays[pre + nm] = (depth, w)
            fl.widths[pre + nm] = w
        for kind, *rest in md.items:
            node = (rest[0],) if kind in ('comb', 'ff') else (kind, rest[0], rest[1])
            node = rn(rest[0], pre, consts) if kind in ('comb', 'ff') else rn(('assign', rest[0], rest[1]), pre, consts)
            fl.items.append((kind, node))
        for mod, iname, params, conns in md.insts:
            child = defs[mod]; cpre = pre + iname + '__'
            ov = {pn: ev(pe, consts) for pn, pe in params.items()}
            go(mod, cpre, ov)
            pdir = {pn: d for d, pn, ws in child.ports}
            for port, e in conns.items():
                if e is None: continue
                if pdir[port] == 'input': fl.items.append(('assign', ('assign', cpre + port, rn(e, pre, consts))))
                else:
                    assert e[0] == 'id', (mod, port, e)
                    fl.items.append(('assign', ('assign', pre + e[1], ('id', cpre + port))))
    go(top, '', top_overrides or {})
    for d, pn, ws in defs[top].ports: fl.top_ports[pn] = d
    return fl

class Sim:
    def __init__(s, fl, rng=None):
        s.fl = fl; rng = rng or random.Random(0)
        s.comb = []; s.ff = []
        for kind, node in fl.items:
            R, W = set(), set(); reads_writes(node, R, W)
            (s.ff if kind == 'ff' else s.comb).append((node, R, W))
        s.ffw = set()
        for node, R, W in s.ff: s.ffw |= W
        # topological order of the combinational items; reading a register (written by ff) is not a dependency
        writer = {}
        for idx, (node, R, W) in enumerate(s.comb):
            for x in W:
                assert x not in writer, f'multiple combinational drivers: {x}'
                writer[x] = idx
        deps = [set() for _ in s.comb]
        for idx, (node, R, W) in enumerate(s.comb):
            for x in R - W:
                if x in writer and writer[x] != idx: deps[idx].add(writer[x])
        order, state = [], [0] * len(s.comb)
        sys_limit = __import__('sys').getrecursionlimit(); __import__('sys').setrecursionlimit(100000)
        def visit(i, stack):
            if state[i] == 2: return
            assert state[i] != 1, f'combinational loop through {[s.comb[j][2] for j in stack[-6:]]}'
            state[i] = 1
            for d in deps[i]: visit(d, stack + [i])
            state[i] = 2; order.append(i)
        for i in range(len(s.comb)): visit(i, [])
        s.order = [s.comb[i][0] for i in order]
        s.env = {}
        for nm, w in fl.widths.items():
            if nm in fl.arrays:
                depth, ew = fl.arrays[nm]; s.env[nm] = ([rng.getrandbits(ew) for _ in range(depth)], ew)
            else: s.env[nm] = (rng.getrandbits(w) if nm in s.ffw else 0, w)
        s.loopvars = set()
    def set_inputs(s, inputs):
        for k, v in inputs.items(): s.env[k] = (v & M(s.fl.widths[k]), s.fl.widths[k])
    def eval_comb(s):
        for node in s.order: exe(node, s.env, s.fl.widths)
    def get(s, name): return s.env[name][0]
    def peek(s, inputs):
        s.set_inputs(inputs); s.eval_comb()
    def step(s, inputs):
        s.set_inputs(inputs); s.eval_comb()
        NBA.clear()
        for node, R, W in s.ff: exe(node, s.env, s.fl.widths)
        apply_nba(s.env, NBA); NBA.clear()
        s.eval_comb()
