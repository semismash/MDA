#!/usr/bin/env python3
"""check_names.py: consistency checks between src/mda_pkg.sv, src/mda_isa_pkg.sv and tools/isa/isa.yaml.

Usage:
    python3 tools/isa/check_names.py --pkg src/mda_pkg.sv --isa-pkg src/mda_isa_pkg.sv --yaml tools/isa/isa.yaml

Checks:
    1. The two packages declare no common identifier, so both can be imported with a wildcard.
    2. The ALU codes in mda_pkg equal the RR and RI-A funct codes in isa.yaml (the funct pass-through
       documented in mda_pkg.sv).
    3. mda_pkg declares every name required by the Stage A modules.
    4. Every ALU_* code fits in the width of the AluOp type, and the codes are distinct.

Exit status is 0 when all checks pass and 1 otherwise.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from isa_gen import Isa   # noqa: E402

REQUIRED_NAMES = [
    'NUM_THREADS', 'DATA_WIDTH', 'INSTR_WIDTH', 'REG_ADDR_WIDTH', 'NUM_REGS', 'FLAGS_WIDTH',
    'IMEM_ADDR_WIDTH', 'IMEM_SIZE_HALFWORDS', 'DMEM_ADDR_WIDTH', 'DMEM_SIZE_WORDS', 'DMEM_SIZE_BYTES',
    'DMEM_BYTE_ADDR_WIDTH',
    'Word', 'Instruction', 'PcAddr', 'RegAddr', 'ThreadSel', 'Flags', 'DmemWordAddr', 'Cause',
    'NOP_INSTR', 'ILLEGAL_INSTR',
    'AluOp', 'ALU_ADD', 'ALU_XOR', 'ALU_SHL', 'ALU_SHR', 'ALU_CMP', 'ALU_CMPA', 'ALU_AND', 'ALU_OR',
    'BrType', 'BR_NONE', 'BR_JMP', 'BR_JRG', 'BR_JNL', 'BR_JOF', 'BR_JOC',
    'MemOp', 'MEM_NONE', 'MEM_LOAD', 'MEM_STORE',
    'COND_ANY', 'COND_ALL',
]


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def declared(text):
    """Map identifier -> (kind, statement) for every localparam and typedef in a package."""
    names = {}
    for stmt in strip_comments(text).split(';'):
        s = stmt.strip()
        if s.startswith('localparam'):
            for m in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*', s):
                names[m.group(1)] = ('localparam', s)
        elif s.startswith('typedef'):
            m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*$', s)
            if m:
                names[m.group(1)] = ('typedef', s)
    return names


def const_value(stmt):
    m = re.search(r"=\s*(?:\d+')?[dD]?(\d+)\s*$", stmt.strip())
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pkg', required=True)
    ap.add_argument('--isa-pkg', required=True)
    ap.add_argument('--yaml', required=True)
    args = ap.parse_args()

    pkg = declared(open(args.pkg).read())
    isa_pkg = declared(open(args.isa_pkg).read())
    problems = []

    common = sorted(set(pkg) & set(isa_pkg))
    if common:
        problems.append(f'identifiers declared in both packages: {common}')
    print(f'[1] names: mda_pkg declares {len(pkg)}, mda_isa_pkg declares {len(isa_pkg)}, common: {len(common)}')

    isa = Isa(args.yaml)
    checked = 0
    for ins in isa.instrs:
        alu = ins.spec.get('alu')
        if alu in ('add', 'xor', 'shl', 'shr', 'cmp', 'cmpa', 'and', 'or') and ins.type.name in ('RR', 'RI-A'):
            key = 'ALU_' + alu.upper()
            if key not in pkg:
                problems.append(f'{key} is missing from mda_pkg')
                continue
            value = const_value(pkg[key][1])
            if value != ins.funct:
                problems.append(f'{key} = {value}, but {ins.name} ({ins.type.name}) has funct {ins.funct}: '
                                'the funct pass-through would be wrong')
            checked += 1
    print(f'[2] ALU codes against funct codes: {checked} instructions checked')

    missing = [n for n in REQUIRED_NAMES if n not in pkg]
    if missing:
        problems.append(f'mda_pkg is missing {missing}')
    print(f'[3] required names present: {len(REQUIRED_NAMES) - len(missing)}/{len(REQUIRED_NAMES)}')

    m = re.search(r'\[(\d+):0\]\s*AluOp\s*$', pkg['AluOp'][1]) if 'AluOp' in pkg else None
    alu_codes = {k: const_value(v[1]) for k, v in pkg.items() if k.startswith('ALU_')}
    if m is None:
        problems.append('could not read the AluOp width')
    else:
        width = int(m.group(1)) + 1
        too_big = {k: v for k, v in alu_codes.items() if v is None or v >= (1 << width)}
        if too_big:
            problems.append(f'ALU codes do not fit in AluOp ({width} bits): {too_big}')
        if len(set(alu_codes.values())) != len(alu_codes):
            problems.append(f'duplicate ALU codes: {alu_codes}')
        print(f'[4] ALU codes: {len(alu_codes)} codes, AluOp is {width} bits, all fit and are distinct')

    for p in problems:
        print('PROBLEM:', p)
    if problems:
        sys.exit(1)
    print('mda_pkg: all checks passed')


if __name__ == '__main__':
    main()