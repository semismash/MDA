#!/usr/bin/env python3
"""isa_gen.py: validate isa.yaml and generate the RTL package, doc tables, JSON tables and golden vectors.

  python3 isa_gen.py --check                     validate only (always run this after editing isa.yaml)
  python3 isa_gen.py --check --doc "Instruction Encoding.md"      also cross-check the examples against the doc table
  python3 isa_gen.py --out out/                  generate mda_isa_pkg.sv, isa_tables.md, isa_tables.json
  python3 isa_gen.py --out out/ --exhaustive out/golden_decode.csv   also write the classification of all 65,536 words

Requires PyYAML (pip install pyyaml). Plain Python 3 otherwise.
"""
import argparse
import hashlib
import itertools
import json
import os
import random
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
GROUPS = {'register_ops', 'immediate_ops', 'immediate_loading', 'jumps', 'memory', 'spatial', 'temporal_event', 'config_signal'}


class IsaError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    """YAML 1.1 reads bare y/n/yes/no/on/off as booleans. Only true/false are booleans here."""


StrictLoader.yaml_implicit_resolvers = {
    k: [(t, r) for t, r in v if t != 'tag:yaml.org,2002:bool'] for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}
StrictLoader.add_implicit_resolver('tag:yaml.org,2002:bool', re.compile(r'^(?:true|false)$'), list('tf'))


# ---------------------------------------------------------------------------------------------- bit helpers
def parse_range(s):
    s = str(s)
    if ':' in s:
        hi, lo = s.split(':')
        hi, lo = int(hi), int(lo)
    else:
        hi = lo = int(s)
    if not (0 <= lo <= hi <= 15):
        raise IsaError(f'bad bit range "{s}"')
    return (hi, lo)


def parse_ranges(lst):
    return [parse_range(x) for x in lst]


def width_of(ranges):
    return sum(hi - lo + 1 for hi, lo in ranges)


def mask_of(ranges):
    m = 0
    for hi, lo in ranges:
        m |= ((1 << (hi - lo + 1)) - 1) << lo
    return m


def get_bits(word, ranges):
    v = 0
    for hi, lo in ranges:
        w = hi - lo + 1
        v = (v << w) | ((word >> lo) & ((1 << w) - 1))
    return v


def put_bits(word, ranges, value):
    shift = width_of(ranges)
    for hi, lo in ranges:
        w = hi - lo + 1
        shift -= w
        word |= ((value >> shift) & ((1 << w) - 1)) << lo
    return word


# ---------------------------------------------------------------------------------------------- model
class Field:
    def __init__(self, name, spec):
        self.name = name
        self.ranges = parse_ranges(spec['bits'])
        self.width = width_of(self.ranges)
        self.signed = bool(spec.get('signed', False))
        self.addr_scale = int(spec.get('addr_scale', 1))
        self.bias = int(spec.get('bias', 0))

    def to_value(self, raw):
        if self.signed and raw >= 1 << (self.width - 1):
            raw -= 1 << self.width
        return raw + self.bias

    def to_raw(self, value):
        v = value - self.bias
        lo, hi = ((-(1 << (self.width - 1)), (1 << (self.width - 1)) - 1) if self.signed else (0, (1 << self.width) - 1))
        if not lo <= v <= hi:
            raise IsaError(f'{self.name}: {value} out of range')
        return v & ((1 << self.width) - 1)

    def value_range(self):
        lo, hi = ((-(1 << (self.width - 1)), (1 << (self.width - 1)) - 1) if self.signed else (0, (1 << self.width) - 1))
        return lo + self.bias, hi + self.bias


class Type:
    def __init__(self, name, spec):
        self.name = name
        self.opcode = int(spec['opcode'])
        self.funct = parse_range(spec['funct'])
        self.funct_w = self.funct[0] - self.funct[1] + 1
        self.regs = {r: parse_range(spec[r]) for r in ('rd', 'rs1', 'rs2', 'wb') if r in spec}
        self.unused = [int(x) for x in spec.get('unused_funct', [])]


class Instr:
    def __init__(self, spec, types):
        self.spec = spec
        self.name = spec['name']
        self.mnemonic = spec['mnemonic']
        self.type = types[spec['type']]
        self.funct = int(spec['funct'])
        self.fields = {k: Field(k, v) for k, v in (spec.get('fields') or {}).items()}
        self.reserved = parse_ranges(spec.get('reserved', []))
        self.illegal_values = {k: [int(x) for x in v] for k, v in (spec.get('illegal_values') or {}).items()}
        self.stage = spec['stage']
        self.group = spec['group']

    def mask_used(self):
        return mask_of([self.type.funct]) | 0b111 | sum(0 for _ in ()) | 0

    def coverage(self):
        """bit -> list of owners, to prove that every bit is used exactly once."""
        own = {}

        def claim(rs, label):
            for hi, lo in rs:
                for b in range(lo, hi + 1):
                    own.setdefault(b, []).append(label)
        claim([(2, 0)], 'opcode')
        claim([self.type.funct], 'funct')
        for r, rng in self.type.regs.items():
            claim([rng], r)
        for f in self.fields.values():
            claim(f.ranges, 'field:' + f.name)
        claim(self.reserved, 'reserved')
        return own


class Isa:
    def __init__(self, path):
        self.path = path
        raw = open(path, 'rb').read()
        self.sha = hashlib.sha256(raw).hexdigest()
        self.y = yaml.load(raw, Loader=StrictLoader)
        self.types = {n: Type(n, s) for n, s in self.y['types'].items()}
        self.instrs = [Instr(s, self.types) for s in self.y['instructions']]
        self.by_name = {i.name: i for i in self.instrs}
        self.by_tf = {(i.type.name, i.funct): i for i in self.instrs}
        self.by_opc = {t.opcode: t for t in self.types.values()}

    # ------------------------------------------------------------------ codec
    def decode(self, word):
        t = self.by_opc[word & 7]
        funct = get_bits(word, [t.funct])
        if funct in t.unused:
            return {'legal': False, 'reason': 'unused_funct', 'type': t.name, 'funct': funct}
        ins = self.by_tf[(t.name, funct)]
        d = {'legal': True, 'reason': '', 'name': ins.name, 'mnemonic': ins.mnemonic, 'type': t.name, 'funct': funct, 'stage': ins.stage}
        for r, rng in t.regs.items():
            d[r] = get_bits(word, [rng])
        for rng in ins.reserved:
            if get_bits(word, [rng]) != 0:
                return {'legal': False, 'reason': 'reserved_bits', 'type': t.name, 'funct': funct, 'name': ins.name}
        fields = {}
        for fname, f in ins.fields.items():
            raw = get_bits(word, f.ranges)
            if raw in ins.illegal_values.get(fname, []):
                return {'legal': False, 'reason': 'reserved_value', 'type': t.name, 'funct': funct, 'name': ins.name}
            fields[fname] = f.to_value(raw)
        d['fields'] = fields
        return d

    def encode(self, name, **ops):
        ins = self.by_name[name]
        t = ins.type
        w = ins.type.opcode
        w = put_bits(w, [t.funct], ins.funct)
        known = set(ins.fields) | set(t.regs)
        for k in ops:
            if k not in known:
                raise IsaError(f'{name}: unknown operand "{k}"')
        for r, rng in t.regs.items():
            v = ops.get(r, 1 if r == 'wb' else 0)
            lim = 1 if r == 'wb' else 7
            if not 0 <= v <= lim:
                raise IsaError(f'{name}: {r}={v} out of range')
            w = put_bits(w, [rng], v)
        for fname, f in ins.fields.items():
            w = put_bits(w, f.ranges, f.to_raw(ops.get(fname, 0)))
        return w

    # ------------------------------------------------------------------ analytic count of legal words
    def legal_count(self, ins):
        n = 1
        for r, rng in ins.type.regs.items():
            n *= 1 << width_of([rng])
        for fname, f in ins.fields.items():
            n *= (1 << f.width) - len(ins.illegal_values.get(fname, []))
        return n


# ---------------------------------------------------------------------------------------------- checks
def check(isa, doc=None, asm_path=None, verbose=True):
    problems = []
    say = print if verbose else (lambda *a, **k: None)

    # 1. every funct slot of every type is assigned exactly once, and opcodes are unique
    opcodes = [t.opcode for t in isa.types.values()]
    if sorted(opcodes) != list(range(8)):
        problems.append('opcodes are not exactly 0..7')
    for t in isa.types.values():
        slots = {}
        for i in isa.instrs:
            if i.type is t:
                slots.setdefault(i.funct, []).append(i.name)
        for u in t.unused:
            slots.setdefault(u, []).append('<unused>')
        for f in range(1 << t.funct_w):
            if len(slots.get(f, [])) != 1:
                problems.append(f'type {t.name}: funct {f} is assigned {len(slots.get(f, []))} times: {slots.get(f)}')
    names = [i.name for i in isa.instrs]
    if len(set(names)) != len(names):
        problems.append('duplicate instruction names')
    say(f'[1] funct slots: {len(isa.instrs)} encodings over {len(isa.types)} types, every slot assigned once')

    # 2. every bit of every encoding is used exactly once (catches typos in bit ranges)
    for i in isa.instrs:
        own = i.coverage()
        for b in range(16):
            n = len(own.get(b, []))
            if n != 1:
                problems.append(f'{i.name}: bit {b} is claimed {n} times {own.get(b)}')
        for fname, f in i.fields.items():
            if f.width > 16:
                problems.append(f'{i.name}.{fname}: wider than 16')
    say('[2] bit coverage: every bit of every encoding is claimed exactly once')

    # 3. semantic sanity
    for i in isa.instrs:
        s = i.spec
        if i.group not in GROUPS:
            problems.append(f'{i.name}: bad group {i.group}')
        if i.stage not in ('A', 'B'):
            problems.append(f'{i.name}: bad stage')
        for r in s.get('src', []):
            if r not in i.type.regs:
                problems.append(f'{i.name}: source register {r} not in type {i.type.name}')
        if s.get('dst') == 'rd' and 'rd' not in i.type.regs:
            problems.append(f'{i.name}: writes rd but type has none')
        if s.get('dst_when') == 'wb' and 'wb' not in i.type.regs:
            problems.append(f'{i.name}: dst_when wb but type has no WB bit')
        for fl in s.get('flags', []):
            if fl not in isa.y['flags']:
                problems.append(f'{i.name}: unknown flag {fl}')
        for fname in i.illegal_values:
            if fname not in i.fields:
                problems.append(f'{i.name}: illegal_values names unknown field {fname}')
    n_mn = len({i.mnemonic for i in isa.instrs})
    if n_mn != isa.y['isa']['mnemonics'] or len(isa.instrs) != isa.y['isa']['encodings']:
        problems.append(f'counts: {n_mn} mnemonics / {len(isa.instrs)} encodings, expected {isa.y["isa"]["mnemonics"]} / {isa.y["isa"]["encodings"]}')
    say(f'[3] semantics: {n_mn} mnemonics, {len(isa.instrs)} encodings (spec: 35 and 37)')

    # 4. worked examples: encode must give the doc's word, decode must give the operands back
    ok = 0
    for ex in isa.y['examples']:
        try:
            w = isa.encode(ex['name'], **ex['ops'])
        except IsaError as e:
            problems.append(f'example "{ex["asm"]}": {e}')
            continue
        if w != ex['word']:
            problems.append(f'example "{ex["asm"]}": encodes to 0x{w:04X}, doc says 0x{ex["word"]:04X}')
            continue
        d = isa.decode(w)
        if not d['legal'] or d['name'] != ex['name']:
            problems.append(f'example "{ex["asm"]}": decodes to {d}')
            continue
        for k, v in ex['ops'].items():
            got = d['fields'].get(k, d.get(k))
            if got != v:
                problems.append(f'example "{ex["asm"]}": decoded {k}={got}, expected {v}')
        ok += 1
    say(f'[4] worked examples: {ok}/{len(isa.y["examples"])} encode to the documented word and decode back')

    # 5. independent facts from the doc text: legality (and the decoded instruction) of specific words
    nsp = 0
    for sw in isa.y.get('special_words', []):
        d = isa.decode(sw['word'])
        nsp += 1
        if bool(d['legal']) != bool(sw['legal']):
            problems.append(f'word 0x{sw["word"]:04X} ({sw["why"]}): legal={d["legal"]}, expected {sw["legal"]}')
        elif sw['legal'] and sw.get('name') and d['name'] != sw['name']:
            problems.append(f'word 0x{sw["word"]:04X} ({sw["why"]}): decodes to {d["name"]}, expected {sw["name"]}')
    say(f'[5] doc-derived special words: {nsp} checked (reserved fields, unused funct codes, run-time-fault cases)')

    # 6. exhaustive: every word classifies, legal words round-trip, counts match the analytic count
    legal = {i.name: 0 for i in isa.instrs}
    reasons = {}
    for w in range(1 << 16):
        d = isa.decode(w)
        if d['legal']:
            legal[d['name']] += 1
            args = dict(d['fields'])
            for r in d['type'].split() and isa.types[d['type']].regs:
                args[r] = d[r]
            if isa.encode(d['name'], **args) != w:
                problems.append(f'round trip fails for 0x{w:04X}')
                break
        else:
            reasons[d['reason']] = reasons.get(d['reason'], 0) + 1
    for i in isa.instrs:
        if legal[i.name] != isa.legal_count(i):
            problems.append(f'{i.name}: {legal[i.name]} legal words counted, {isa.legal_count(i)} expected')
    total_legal = sum(legal.values())
    say(f'[6] exhaustive: {total_legal} legal words, {65536 - total_legal} illegal {reasons}; counts match the analytic count; all legal words round-trip')

    # 7. random round trips on operands (including range limits)
    rnd = random.Random(1)
    for i in isa.instrs:
        for _ in range(300):
            ops = {}
            for r, rng in i.type.regs.items():
                ops[r] = rnd.randint(0, 1 if r == 'wb' else 7)
            for fname, f in i.fields.items():
                lo, hi = f.value_range()
                v = rnd.choice([lo, hi, rnd.randint(lo, hi)])
                while (v - f.bias) & ((1 << f.width) - 1) in i.illegal_values.get(fname, []):
                    v = rnd.randint(lo, hi)
                ops[fname] = v
            w = isa.encode(i.name, **ops)
            d = isa.decode(w)
            if not d['legal'] or d['name'] != i.name:
                problems.append(f'{i.name}: random operands {ops} do not decode back (0x{w:04X})')
                break
    say('[7] random operand round trips incl. range limits: done')

    # 8. optional: compare the examples with the doc table itself, so a transcription slip here cannot hide
    if doc:
        text = open(doc, encoding='utf-8').read()
        rows = re.findall(r'\|`([^`|]*(?:\\\|[^`|]*)*)`\|`0x([0-9A-Fa-f]{4})`\|`([01]{16})`\|', text)
        doc_words = [int(w, 16) for _, w, _ in rows]
        for _, w, b in rows:
            if int(b, 2) != int(w, 16):
                problems.append(f'doc row 0x{w}: binary column disagrees with the hex word')
        yaml_words = [e['word'] for e in isa.y['examples']]
        if sorted(doc_words) != sorted(yaml_words):
            only_doc = sorted(set(doc_words) - set(yaml_words))
            only_yaml = sorted(set(yaml_words) - set(doc_words))
            problems.append(f'examples differ from the doc: only in doc {[hex(x) for x in only_doc]}, only in yaml {[hex(x) for x in only_yaml]}')
        say(f'[8] doc cross-check: the doc table has {len(rows)} rows, isa.yaml has {len(yaml_words)} examples'
            + (' (same words)' if sorted(doc_words) == sorted(yaml_words) else ' (MISMATCH)'))

    # 9. optional: value ranges against the evaluation assembler
    if asm_path:
        sys.path.insert(0, os.path.dirname(os.path.abspath(asm_path)))
        import importlib
        asm = importlib.import_module(os.path.splitext(os.path.basename(asm_path))[0])
        pick = ('imm', 'offset', 'shift', 'count')
        bad = []
        cmp_n = 0
        for mn, (lo, hi) in asm.RANGES.items():
            ins = isa.by_name.get(mn)
            if ins is None or mn == 'lli':
                continue
            fn = next((p for p in pick if p in ins.fields), None)
            if fn is None:
                continue
            f = ins.fields[fn]
            rlo, rhi = f.value_range()
            cmp_n += 1
            if (rlo, rhi) != (lo, hi):
                bad.append(f'{mn}: yaml {rlo}..{rhi}, assembler {lo}..{hi}')
        for b in bad:
            problems.append('range mismatch ' + b)
        say(f'[9] ranges vs {os.path.basename(asm_path)}: {cmp_n} compared, {len(bad)} mismatches')

    return problems


# ---------------------------------------------------------------------------------------------- generators
def sv_name(s):
    return s.replace('-', '').upper()


def gen_pkg(isa):
    L = []
    a = L.append
    a(f'// GENERATED by tools/isa/isa_gen.py from tools/isa/isa.yaml (sha256 {isa.sha[:16]}). DO NOT EDIT BY HAND.')
    a('// Re-run the generator after changing isa.yaml, and copy the result to src/mda_isa_pkg.sv.')
    a('package mda_isa_pkg;')
    a('')
    a('  // ---- fixed field positions (the same in every type that has the field)')
    a('  localparam int OPC_HI = 2,  OPC_LO = 0;')
    a('  localparam int RD_HI  = 15, RD_LO  = 13;')
    a('  localparam int RS1_HI = 12, RS1_LO = 10;')
    a('  localparam int RS2_HI = 9,  RS2_LO = 7;')
    a('')
    a('  // ---- types')
    a('  typedef logic [2:0] OpCode;     // opcode, instruction word bits [2:0]')
    a('  typedef logic [2:0] Funct3;     // 3-bit funct field (RR, NX and RX types, instr[5:3])')
    a('  typedef logic [1:0] Funct2;     // 2-bit funct field (RI-A, RI-Z, SX, DI-L and DI-Z types, instr[4:3])')
    a('  typedef logic [2:0] RpinMode;   // rpin mode field, instr[7:5]')
    a('  typedef logic [2:0] CfgTarget;  // cfg target field, instr[8:6]')
    a('')
    a('  // ---- opcodes (instruction word bits [2:0])')
    for t in sorted(isa.types.values(), key=lambda x: x.opcode):
        a(f"  localparam OpCode OPC_{sv_name(t.name)} = 3'd{t.opcode};")
    a('')
    a('  // ---- funct codes. RR, NX and RX use word bits [5:3]; the other types use bits [4:3]')
    for t in sorted(isa.types.values(), key=lambda x: x.opcode):
        hi, lo = t.funct
        a(f'  // {t.name}: funct = instr[{hi}:{lo}]')
        for i in sorted([i for i in isa.instrs if i.type is t], key=lambda x: x.funct):
            a(f"  localparam Funct{t.funct_w} FN_{sv_name(t.name)}_{i.name.upper()} = {t.funct_w}'d{i.funct};")
        for u in t.unused:
            a(f"  localparam Funct{t.funct_w} FN_{sv_name(t.name)}_UNUSED{u} = {t.funct_w}'d{u};   // illegal")
    a('')
    a('  // ---- reserved-field masks: an instruction is illegal if (instr & RSV_x) != 0')
    for i in isa.instrs:
        if i.reserved:
            a(f"  localparam logic [15:0] RSV_{i.name.upper()} = 16'h{mask_of(i.reserved):04X};")
    a('')
    a('  // ---- illegal field values')
    a(f"  localparam int RPIN_MODE_MAX_LEGAL = {max(isa.y['rpin_modes'].values())};   // rpin modes above this are illegal words")
    a('')
    a('  // ---- rpin modes, cfg targets (targets 6 and 7 are a bad cfg at run time, not illegal words)')
    for k, v in isa.y['rpin_modes'].items():
        a(f"  localparam RpinMode RPIN_{k} = 3'd{v};")
    for k, v in isa.y['cfg_targets'].items():
        a(f"  localparam CfgTarget CFG_TGT_{k} = 3'd{v};")
    a('')
    a('  // ---- flag indices (Events.md)')
    for k, v in isa.y['flags'].items():
        a(f"  localparam int FLAG_{k} = {v};")
    a('')
    a('  // ---- fault causes (Events.md)')
    for k, v in isa.y['fault_causes'].items():
        a(f"  localparam logic [2:0] CAUSE_{k} = 3'd{v};")
    a('')
    a('endpackage')
    return '\n'.join(L) + '\n'


def field_str(f):
    parts = ','.join(f'{hi}:{lo}' if hi != lo else str(hi) for hi, lo in f.ranges)
    lo, hi = f.value_range()
    kind = 'signed' if f.signed else 'unsigned'
    extra = (f', address x{f.addr_scale}' if f.addr_scale != 1 else '') + (f', +{f.bias}' if f.bias else '')
    return f'`{f.name}` [{parts}] {kind}{extra} ({lo} to {hi})'


def gen_md(isa):
    L = []
    a = L.append
    a(f'<!-- GENERATED from isa.yaml (sha256 {isa.sha[:16]}) by isa_gen.py. Do not edit by hand. -->')
    a('# MDA instruction encoding tables (generated)')
    a('')
    a('Bit ranges are instruction-word bits. A field with several ranges is their concatenation, MSB first.')
    a('')
    for t in sorted(isa.types.values(), key=lambda x: x.opcode):
        ins = sorted([i for i in isa.instrs if i.type is t], key=lambda x: x.funct)
        regs = ', '.join(f'{r} [{h}:{l}]' if h != l else f'{r} [{h}]' for r, (h, l) in t.regs.items()) or 'no registers'
        a(f'## {t.name} (opcode `{t.opcode:03b}`, funct [{t.funct[0]}:{t.funct[1]}])')
        a('')
        a(f'Registers: {regs}.' + (f' Unused funct codes (illegal): {", ".join(map(str, t.unused))}.' if t.unused else ''))
        a('')
        a('| Instruction | Funct | Stage | Fields | Reserved (must be 0) | Flags set | Notes |')
        a('|---|---|---|---|---|---|---|')
        for i in ins:
            flds = '; '.join(field_str(f) for f in i.fields.values()) or '-'
            rsv = ', '.join(f'[{h}:{l}]' if h != l else f'[{h}]' for h, l in i.reserved) or '-'
            fl = ','.join(i.spec.get('flags', [])) or '-'
            note = i.spec.get('note', '')
            if i.illegal_values:
                note += ' Illegal values: ' + ', '.join(f'{k}={v}' for k, v in i.illegal_values.items()) + '.'
            f_s = format(i.funct, f'0{t.funct_w}b')
            a(f'| `{i.mnemonic}`{" (" + i.name + ")" if i.name != i.mnemonic else ""} | `{f_s}` | {i.stage} | {flds} | {rsv} | {fl} | {note.strip()} |')
        a('')
    return '\n'.join(L) + '\n'


def gen_json(isa):
    out = {'sha256': isa.sha, 'types': {}, 'instructions': {}}
    for t in isa.types.values():
        out['types'][t.name] = {'opcode': t.opcode, 'funct': list(t.funct), 'regs': {k: list(v) for k, v in t.regs.items()}, 'unused_funct': t.unused}
    for i in isa.instrs:
        d = {k: v for k, v in i.spec.items() if k not in ('fields',)}
        d['funct_bits'] = list(i.type.funct)
        d['opcode'] = i.type.opcode
        d['fields'] = {k: {'bits': [list(r) for r in f.ranges], 'width': f.width, 'signed': f.signed, 'addr_scale': f.addr_scale, 'bias': f.bias,
                           'range': list(f.value_range())} for k, f in i.fields.items()}
        d['reserved'] = [list(r) for r in i.reserved]
        out['instructions'][i.name] = d
    return json.dumps(out, indent=1)


def gen_exhaustive(isa, path):
    with open(path, 'w', newline='') as fh:
        fh.write('word,legal,reason,name,type,funct,rd,rs1,rs2,wb,fields\n')
        for w in range(1 << 16):
            d = isa.decode(w)
            if d['legal']:
                fs = ';'.join(f'{k}={v}' for k, v in d['fields'].items())
                fh.write(f"0x{w:04X},1,,{d['name']},{d['type']},{d['funct']},{d.get('rd', '')},{d.get('rs1', '')},{d.get('rs2', '')},{d.get('wb', '')},{fs}\n")
            else:
                fh.write(f"0x{w:04X},0,{d['reason']},{d.get('name', '')},{d['type']},{d['funct']},,,,,\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--yaml', default=os.path.join(HERE, 'isa.yaml'))
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--doc')
    ap.add_argument('--asm')
    ap.add_argument('--out')
    ap.add_argument('--exhaustive')
    a = ap.parse_args()
    isa = Isa(a.yaml)
    problems = check(isa, doc=a.doc, asm_path=a.asm)
    if problems:
        print('\nPROBLEMS:')
        for p in problems:
            print('  -', p)
        sys.exit(1)
    print('\nisa.yaml: all checks passed')
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        open(os.path.join(a.out, 'mda_isa_pkg.sv'), 'w', newline='\n').write(gen_pkg(isa))
        open(os.path.join(a.out, 'isa_tables.md'), 'w', newline='\n', encoding='utf-8').write(gen_md(isa))
        open(os.path.join(a.out, 'isa_tables.json'), 'w', newline='\n').write(gen_json(isa))
        print(f'wrote mda_isa_pkg.sv, isa_tables.md, isa_tables.json to {a.out}')
    if a.exhaustive:
        gen_exhaustive(isa, a.exhaustive)
        print(f'wrote {a.exhaustive}')


if __name__ == '__main__':
    main()