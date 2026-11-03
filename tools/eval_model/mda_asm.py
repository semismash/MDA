#!/usr/bin/env python3
"""MDA assembler (checker subset) for the protocol evaluation.

Implements the 35 instructions plus the pseudo-instructions used by the firmware, label
resolution in halfword units (lli = 2), immediate range checks from Assembly.md, and simple
.equ / .entryN / .data support. It does not emit binary. It exists to (a) reject firmware that
breaks the ISA ranges and (b) feed the cycle-level simulator with exact slot costs.
"""
import re


class AsmError(Exception):
    pass


ABI = {'rsp': 0, 'rad': 1, 'ra0': 2, 'ra1': 3, 'rt0': 4, 'rt1': 5, 'rs0': 6, 'rs1': 7}
FLAG = dict(Z=0, N=1, C=2, ERR=3, ERRC0=4, ERRC1=5, ERRC2=6, ISR_RDY=7, OSR_EMPTY=8,
            MSG_N=9, MSG_P=10, PE=11, OVR=12, TMR=13)
TARGET = dict(PIN=0, WATCH=1, ENG_DIV=2, ENG_CTL=3, ENG_ABORT=4, TMR=5)

# Helper constants for cfg values (packing from I-O_Interface.md). The assembler proposes these.
CONSTS = dict(
    SRC_DIRECT=1 << 8, SRC_DATA=2 << 8, SRC_CLK=3 << 8,
    ROLE_DIN=1 << 10, ROLE_CIN=1 << 11, ROLE_GATE=1 << 12, OD=1 << 13, IDLE1=1 << 14,
    OWN_NEXT=1 << 15, OWN_PREV=2 << 15,
    W_OFF=0, W_LOW=1 << 5, W_HIGH=2 << 5, W_POS=5 << 5, W_NEG=6 << 5, W_ANY=7 << 5,
    ENG_MSB=1, ENG_DUPLEX=2, ENG_CPHA=4,
)
for _k, _v in FLAG.items():
    CONSTS['M_' + _k] = 1 << _v

RANGES = {
    'addi': (-8, 7), 'xori': (-8, 7), 'shli': (0, 15), 'shri': (0, 15),
    'lbi': (0, 255), 'lui': (0, 255), 'lli': (0, (1 << 24) - 1),
    'lb': (0, 31), 'sb': (0, 31), 'lw': (0, 31), 'sw': (0, 31),
    'jrg': (-16, 15), 'jmp': (-128, 127), 'jof': (-32, 31), 'joc': (-32, 31), 'jnl': (-512, 511),
    'pull': (0, 31), 'push': (0, 31), 'inp': (1, 32), 'outp': (1, 32), 'dl': (0, 1023), 'dlrg': (0, 127),
}


def split_ops(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(':
            depth += 1
        if ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            out.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


class Prog:
    def __init__(self):
        self.mem = {}        # halfword address -> instruction dict
        self.entry = {}      # thread -> address
        self.labels = {}
        self.data = {}       # byte address -> value
        self.listing = []    # (addr, size, text)
        self.size = 0


def assemble(text, name='<src>'):
    syms = dict(CONSTS)
    labels = {}
    items = []       # (kind, dict) in order
    section = '.text'
    addr = 0
    daddr = 0
    entry = {}
    data = {}
    pend_labels = []

    def err(ln, msg):
        raise AsmError(f'{name}:{ln}: {msg}')

    def ev(expr, ln, allow_fwd=False):
        env = dict(syms)
        env.update(labels)
        try:
            return int(eval(expr, {'__builtins__': {}}, env))
        except NameError:
            if allow_fwd:
                return None
            err(ln, f'undefined symbol in "{expr}"')
        except Exception as e:  # noqa
            err(ln, f'bad expression "{expr}": {e}')

    def reg(tok, ln):
        t = tok.strip()
        if t in ABI:
            return ABI[t]
        m = re.fullmatch(r'r([0-7])', t)
        if not m:
            err(ln, f'bad register "{tok}"')
        return int(m.group(1))

    def emit(ln, text_, **kw):
        nonlocal addr
        ins = dict(kw)
        ins['ln'] = ln
        ins['text'] = text_
        ins['addr'] = addr
        ins['size'] = 2 if kw['op'] == 'lli' else 1
        for l in pend_labels:
            labels[l] = addr
        pend_labels.clear()
        items.append(ins)
        addr += ins['size']
        return ins

    for ln, raw in enumerate(text.splitlines(), 1):
        line = re.split(r';|//', raw)[0].strip()
        if not line:
            continue
        while True:
            m = re.match(r'([A-Za-z_][A-Za-z0-9_]*):\s*(.*)', line)
            if not m:
                break
            if section == '.text':
                pend_labels.append(m.group(1))
            else:
                labels[m.group(1)] = daddr
            line = m.group(2)
        if not line:
            continue
        mn, _, rest = line.partition(' ')
        mn = mn.strip()
        ops = split_ops(rest)
        if mn.startswith('.'):
            if mn == '.mda':
                continue
            if mn in ('.text', '.data', '.rodata', '.bss'):
                section = '.text' if mn == '.text' else '.data'
                continue
            if mn == '.equ' or mn == '.set':
                syms[ops[0]] = ev(ops[1], ln)
                continue
            if mn in ('.entry0', '.entry1', '.entry2'):
                for l in pend_labels:
                    labels[l] = addr
                pend_labels.clear()
                entry[int(mn[-1])] = addr
                continue
            if mn in ('.word', '.int'):
                for o in ops:
                    v = ev(o, ln)
                    for b in range(4):
                        data[daddr + b] = (v >> (8 * b)) & 255
                    daddr += 4
                continue
            if mn == '.byte':
                for o in ops:
                    data[daddr] = ev(o, ln) & 255
                    daddr += 1
                continue
            if mn in ('.asciz', '.ascii', '.string'):
                s = rest.strip()[1:-1].encode().decode('unicode_escape')
                for ch in s:
                    data[daddr] = ord(ch)
                    daddr += 1
                if mn != '.ascii':
                    data[daddr] = 0
                    daddr += 1
                continue
            if mn in ('.align', '.balign'):
                a = ev(ops[0], ln)
                daddr = (daddr + a - 1) // a * a
                continue
            if mn in ('.skip', '.space'):
                daddr += ev(ops[0], ln)
                continue
            err(ln, f'unknown directive {mn}')
        if section != '.text':
            err(ln, 'instructions are only allowed in .text')

        def R(i):
            return reg(ops[i], ln)

        def wb(i=0):
            if ops[i].strip() == '@na':
                return None
            return reg(ops[i], ln)

        def mem(tok):
            m = re.fullmatch(r'(.*)\((\w+)\)', tok.strip())
            if not m:
                err(ln, f'bad memory operand "{tok}"')
            return m.group(1).strip() or '0', reg(m.group(2), ln)

        txt = line
        if mn in ('add', 'xor', 'and', 'or', 'cmp', 'cmpa', 'shl', 'shr'):
            emit(ln, txt, op=mn, rd=wb(), rs1=R(1), rs2=R(2))
        elif mn in ('addi', 'xori', 'shli', 'shri'):
            emit(ln, txt, op=mn, rd=wb(), rs1=R(1), imm=ops[2])
        elif mn in ('lbi', 'lli', 'lui'):
            emit(ln, txt, op=mn, rd=R(0), imm=ops[1])
        elif mn == 'jmp':
            emit(ln, txt, op='jmp', rd=R(0), target=ops[1])
        elif mn == 'jrg':
            emit(ln, txt, op='jrg', rd=R(0), rs1=R(1), imm=ops[2])
        elif mn == 'jnl':
            emit(ln, txt, op='jnl', target=ops[0])
        elif mn == 'jof':
            inv = '@inv' in ops
            o = [x for x in ops if x not in ('@inv', '@noinv')]
            emit(ln, txt, op='jof', flag=FLAG[o[0]], inv=inv, target=o[1])
        elif mn == 'joc':
            mode = ops[1].lstrip('@')
            if mode not in ('all', 'any', 'none', 'notall'):
                err(ln, 'bad joc mode')
            emit(ln, txt, op='joc', rs1=R(0), mode=mode, target=ops[2])
        elif mn in ('lb', 'lw'):
            off, rs = mem(ops[1])
            emit(ln, txt, op=mn, rd=R(0), rs1=rs, imm=off)
        elif mn in ('sb', 'sw'):
            off, rs = mem(ops[1])
            emit(ln, txt, op=mn, rs2=R(0), rs1=rs, imm=off)
        elif mn == 'pull':
            emit(ln, txt, op='pull', rd=R(0), imm=ops[1])
        elif mn == 'push':
            emit(ln, txt, op='push', rs1=R(0), imm=ops[1])
        elif mn in ('inp', 'outp'):
            emit(ln, txt, op=mn, imm=ops[0])
        elif mn == 'rpin':
            mode = ops[-1].lstrip('@')
            if mode in ('pend', 'pend_clr'):
                emit(ln, txt, op='rpin', rd=R(0), pin=None, mode=mode)
            else:
                emit(ln, txt, op='rpin', rd=R(0), pin=ops[1], mode=mode)
        elif mn == 'wpin':
            emit(ln, txt, op='wpin', rs1=R(0), pin=ops[1])
        elif mn == 'dl':
            emit(ln, txt, op='dl', imm=ops[0])
        elif mn == 'dlrg':
            emit(ln, txt, op='dlrg', rs1=R(0), imm=ops[1])
        elif mn == 'waitev':
            kw = [x.lstrip('@') for x in ops[1:]]
            emit(ln, txt, op='waitev', rs1=R(0), all_='all' in kw, clear='clear' in kw, consume='consume' in kw)
        elif mn == 'cfg':
            t = ops[0].lstrip('#')
            if t not in TARGET:
                err(ln, f'bad cfg target {t}')
            emit(ln, txt, op='cfg', target_id=TARGET[t], rs1=R(1))
        elif mn == 'flg':
            emit(ln, txt, op='flg', kws=[x.lstrip('@') for x in ops])
        # ---------------- pseudo-instructions ----------------
        elif mn == '$nop':
            emit(ln, txt, op='jnl', target=None, off=0)
        elif mn == '$mv':
            emit(ln, txt, op='addi', rd=R(0), rs1=R(1), imm='0')
        elif mn == '$not':
            emit(ln, txt, op='xori', rd=R(0), rs1=R(1), imm='-1')
        elif mn == '$li':
            v = ev(ops[1], ln, allow_fwd=True)
            if v is not None and 0 <= v <= 255:
                emit(ln, txt, op='lbi', rd=R(0), imm=ops[1])
            elif v is not None and (v < 0 or v >= (1 << 24)):
                v &= 0xFFFFFFFF
                emit(ln, txt, op='lli', rd=R(0), imm=str(v & 0xFFFFFF))
                emit(ln, txt, op='lui', rd=R(0), imm=str(v >> 24))
            else:
                emit(ln, txt, op='lli', rd=R(0), imm=ops[1])
        elif mn == '$call':
            emit(ln, txt, op='jmp', rd=1, target=ops[0])
        elif mn == '$ret':
            emit(ln, txt, op='jrg', rd=1, rs1=1, imm='0')
        elif mn == '$halt':
            emit(ln, txt, op='jnl', target=None, off=-1)
        elif mn == '$park':
            rt = R(0)
            emit(ln, txt, op='lli', rd=rt, imm='M_MSG_N|M_MSG_P')
            lab = f'__park{ln}'
            pend_labels.append(lab)
            emit(ln, txt, op='waitev', rs1=rt, all_=False, clear=False, consume=True)
            emit(ln, txt, op='jnl', target=lab)
        elif mn in ('$beq', '$bne', '$bltu', '$bgeu', '$bgtu', '$bleu', '$blt', '$bge', '$bgt', '$ble'):
            signed = mn in ('$blt', '$bge', '$bgt', '$ble')
            cmpop = 'cmpa' if signed else 'cmp'
            base = mn.replace('$b', '$bx')[3:]
            a, b_ = R(0), R(1)
            swap = base in ('gtu', 'leu', 'gt', 'le')
            if swap:
                a, b_ = b_, a
            emit(ln, txt, op=cmpop, rd=None, rs1=a, rs2=b_)
            if base in ('eq', 'ne'):
                emit(ln, txt, op='jof', flag=FLAG['Z'], inv=(base == 'ne'), target=ops[2])
            else:
                inv = base in ('geu', 'leu', 'ge', 'le')
                emit(ln, txt, op='jof', flag=FLAG['N'], inv=inv, target=ops[2])
        elif mn in ('$beqz', '$bnez'):
            emit(ln, txt, op='addi', rd=None, rs1=R(0), imm='0')
            emit(ln, txt, op='jof', flag=FLAG['Z'], inv=(mn == '$bnez'), target=ops[1])
        elif mn == '$sub':
            rd, a, b_ = R(0), R(1), R(2)
            if rd == a == b_:
                emit(ln, txt, op='xor', rd=rd, rs1=rd, rs2=rd)
            elif rd != b_:
                emit(ln, txt, op='xori', rd=rd, rs1=a, imm='-1')
                emit(ln, txt, op='add', rd=rd, rs1=rd, rs2=b_)
                emit(ln, txt, op='xori', rd=rd, rs1=rd, imm='-1')
            else:
                emit(ln, txt, op='xori', rd=rd, rs1=rd, imm='-1')
                emit(ln, txt, op='add', rd=rd, rs1=rd, rs2=a)
                emit(ln, txt, op='addi', rd=rd, rs1=rd, imm='1')
        elif mn in ('$jof', '$joc'):
            err(ln, 'far-capable $jof/$joc not implemented in the checker, use jof/joc')
        else:
            err(ln, f'unknown mnemonic {mn}')

    for l in pend_labels:
        labels[l] = addr

    # ---- pass 2: resolve immediates, targets, ranges
    prog = Prog()
    prog.labels = labels
    prog.entry = entry
    prog.data = data
    prog.size = addr
    for ins in items:
        ln = ins['ln']
        op = ins['op']
        if 'target' in ins and ins['target'] is not None:
            tgt = ev(ins['target'], ln)
            ins['off'] = tgt - (ins['addr'] + 1)
        if 'off' in ins:
            lo, hi = RANGES[op]
            if not lo <= ins['off'] <= hi:
                err(ln, f'{op} offset {ins["off"]} out of range {lo}..{hi} ("{ins["text"]}")')
        if 'imm' in ins and isinstance(ins['imm'], str):
            v = ev(ins['imm'], ln)
            ins['imm'] = v
            if op in RANGES:
                lo, hi = RANGES[op]
                if not lo <= v <= hi:
                    err(ln, f'{op} immediate {v} out of range {lo}..{hi} ("{ins["text"]}")')
        if 'pin' in ins and ins['pin'] is not None:
            p = ins['pin'].lstrip('#')
            ins['pin'] = ev(p, ln)
            if not 0 <= ins['pin'] <= 23:
                err(ln, 'pin out of range')
        prog.mem[ins['addr']] = ins
        prog.listing.append((ins['addr'], ins['size'], ins['text']))
    for t in range(3):
        if t not in entry:
            entry[t] = None
    return prog
