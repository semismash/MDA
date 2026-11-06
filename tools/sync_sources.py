#!/usr/bin/env python3
"""sync_sources.py: write the source lists of info.yaml and test/Makefile from rtl.f.

  python3 tools/sync_sources.py            (run from the repo root)
  python3 tools/sync_sources.py --check    (exit 1 if either file is out of date, changes nothing)

The SystemVerilog sources of rtl.f are converted to one plain Verilog file by tools/gen_synth.py (sv2v), because Yosys's
front end cannot read them. So:

info.yaml    : the list under "source_files:": the generated src/mda_synth.v, then the asic-only files (the macro stubs)
test/Makefile: the PROJECT_SOURCES line: the generated file only (the simulation uses the macro models of test/)
"""
import argparse
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
GENERATED = 'mda_synth.v'


def read_list(path):
    files = []
    for line in open(path):
        raw = line.strip()
        if not raw or raw.startswith('#'):
            continue
        asic = '# asic-only' in raw
        name = raw.split('#')[0].strip()
        if not name.startswith('src/'):
            sys.exit(f'rtl.f: "{name}" must start with src/')
        files.append((name[len('src/'):], asic))
    return files


def new_info(text, files):
    lines = text.split('\n')
    out, i, done = [], 0, False
    while i < len(lines):
        out.append(lines[i])
        if re.match(r'^\s*source_files\s*:\s*$', lines[i]) and not done:
            indent = re.match(r'^(\s*)', lines[i + 1]).group(1) if i + 1 < len(lines) and lines[i + 1].strip().startswith('-') else '    '
            i += 1
            while i < len(lines) and lines[i].strip().startswith('-'):
                i += 1
            out.extend(f'{indent}- "{n}"' for n in [GENERATED] + [n for n, asic in files if asic])
            done = True
            continue
        i += 1
    if not done:
        sys.exit('info.yaml: no "source_files:" key found')
    return '\n'.join(out)


def new_make(text, files):
    names = [GENERATED]
    value = ' \\\n    '.join(names)
    pat = re.compile(r'^PROJECT_SOURCES[ \t]*=(?:[^\n]*\\\n)*[^\n]*$', re.M)
    if not pat.search(text):
        sys.exit('test/Makefile: no PROJECT_SOURCES line found')
    return pat.sub(lambda m: 'PROJECT_SOURCES = ' + value, text, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--root', default=ROOT)
    a = ap.parse_args()
    files = read_list(os.path.join(a.root, 'rtl.f'))
    stale = False
    for rel, fn in (('info.yaml', new_info), ('test/Makefile', new_make)):
        path = os.path.join(a.root, rel)
        old = open(path, newline='').read()
        nl = '\r\n' if '\r\n' in old else '\n'
        new = fn(old.replace('\r\n', '\n'), files).replace('\n', nl)
        if new != old:
            stale = True
            if a.check:
                print(f'{rel}: out of date')
            else:
                open(path, 'w', newline='').write(new)
                print(f'{rel}: updated')
        else:
            print(f'{rel}: up to date')
    if a.check and stale:
        sys.exit(1)


if __name__ == '__main__':
    main()