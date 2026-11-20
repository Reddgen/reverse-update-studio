#!/usr/bin/env python3
"""Static structure scan for GameCube PowerPC ELF.

Borrows the legitimate part of ReClass/IDA workflow:
- find pointer tables (vtables, function tables) in data;
- find direct call targets;
- find prologues;
- rank function candidates by multiple independent evidence sources.

No runtime memory editing, no cheat functionality.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dol_to_elf
import rea_bridge

sys.path.insert(0, r'C:\Users\Windows 11 PRO\Documents\deepseek-harness\default-workspace\.pylibs')

def parse_elf(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF' or b[4] != 1 or b[5] != 2:
        raise ValueError('need ELF32 big-endian')
    e_machine = struct.unpack_from('>H', b, 18)[0]
    if e_machine != 20:
        raise ValueError('need EM_PPC')
    e_entry = struct.unpack_from('>I', b, 24)[0]
    e_phoff = struct.unpack_from('>I', b, 28)[0]
    e_phnum = struct.unpack_from('>H', b, 44)[0]
    segs = []
    for i in range(e_phnum):
        t, o, v, pa, fs, ms, fl, al = struct.unpack_from('>IIIIIIII', b, e_phoff + i * 32)
        if t == 1:
            segs.append({'off': o, 'vaddr': v, 'filesz': fs, 'memsz': ms, 'flags': fl})
    return b, e_entry, segs

def in_ranges(addr, ranges):
    return any(lo <= addr < hi for lo, hi in ranges)

def find_tables(b, segs, code_ranges):
    tables = []
    for s in segs:
        if s['flags'] & 1 or s['filesz'] < 8:
            continue
        data = b[s['off']:s['off'] + s['filesz']]
        cur = []
        for i in range(0, len(data) - 3, 4):
            val = struct.unpack_from('>I', data, i)[0]
            if in_ranges(val, code_ranges):
                cur.append((s['vaddr'] + i, val))
            else:
                if len(cur) >= 2:
                    tables.append(cur)
                cur = []
        if len(cur) >= 2:
            tables.append(cur)
    return tables

def scan_calls(b, segs, code_ranges):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    md.skipdata = True
    edges = []
    prologues = set()
    for s in segs:
        if not (s['flags'] & 1):
            continue
        code = b[s['off']:s['off'] + s['filesz']]
        insns = list(md.disasm(code, s['vaddr']))
        for i, ins in enumerate(insns):
            if ins.mnemonic == 'bl' and ins.op_str.startswith('0x'):
                try:
                    t = int(ins.op_str, 16)
                    if in_ranges(t, code_ranges):
                        edges.append((ins.address, t))
                except ValueError:
                    pass
            if ins.mnemonic == 'stwu' and ins.op_str.startswith('r1, -') and ins.op_str.endswith('(r1)'):
                window = insns[i + 1:i + 4]
                before = insns[max(0, i - 2):i]
                if any(x.mnemonic in ('mflr', 'stw') for x in window) or any(x.mnemonic == 'mflr' for x in before):
                    prologues.add(ins.address)
    return edges, prologues

def score_functions(entry, tables, edges, prologues):
    vt_count = {}
    for table in tables:
        for _, target in table:
            vt_count[target] = vt_count.get(target, 0) + 1
    incoming = {}
    for _, target in edges:
        incoming[target] = incoming.get(target, 0) + 1
    candidates = set([entry]) | set(vt_count) | set(incoming) | set(prologues)
    rows = []
    for addr in sorted(candidates):
        score = 0
        evidence = []
        if addr == entry:
            score += 50; evidence.append('entry')
        if vt_count.get(addr):
            score += min(32, 8 * vt_count[addr]); evidence.append(f'vtable_slots={vt_count[addr]}')
        if incoming.get(addr):
            score += min(30, 3 * incoming[addr]); evidence.append(f'incoming_calls={incoming[addr]}')
        if addr in prologues:
            score += 5; evidence.append('prologue')
        rows.append({'address': f'0x{addr:x}', 'score': score, 'evidence': evidence})
    rows.sort(key=lambda r: (-r['score'], int(r['address'], 16)))
    return rows

def scan(path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    low = path.lower()
    source = path
    if low.endswith('.dol') or (low.endswith('.iso') and not low.endswith('.nkit.iso')):
        prep = rea_bridge.prepare(path, out_dir)
        source = prep['prepared']
    b, entry, segs = parse_elf(source)
    code_ranges = [(s['vaddr'], s['vaddr'] + s['filesz']) for s in segs if s['flags'] & 1 and s['filesz']]
    tables = find_tables(b, segs, code_ranges)
    edges, prologues = scan_calls(b, segs, code_ranges)
    rows = score_functions(entry, tables, edges, prologues)
    high = [r for r in rows if r['score'] >= 15]
    return {
        'input': os.path.abspath(path), 'prepared': os.path.abspath(source),
        'entry': f'0x{entry:x}', 'pointer_tables': len(tables),
        'pointer_table_targets': len({t for table in tables for _, t in table}),
        'direct_calls': len(edges), 'prologues': len(prologues),
        'candidates': len(rows), 'high_confidence': len(high),
        'top': rows[:20],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('--out', default='structure_scan')
    a = ap.parse_args()
    try:
        print(json.dumps(scan(a.input, a.out), indent=2))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
