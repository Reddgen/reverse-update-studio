#!/usr/bin/env python3
"""Extract compare-chain constants from x86/PPC code.

Use for CTF binaries, your own programs, and interoperability analysis.
Do not use to bypass DRM, licensing or anti-cheat.
"""
import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rea_bridge

sys.path.insert(0, r'C:\Users\Windows 11 PRO\Documents\deepseek-harness\default-workspace\.pylibs')

def elf_segments(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF':
        raise ValueError('not ELF')
    cls, data = b[4], b[5]
    endian = '>' if data == 2 else '<'
    e_machine = struct.unpack_from(endian + 'H', b, 18)[0]
    e_phoff = struct.unpack_from(endian + ('I' if cls == 1 else 'Q'), b, 28 if cls == 1 else 32)[0]
    e_phnum = struct.unpack_from(endian + 'H', b, 44 if cls == 1 else 56)[0]
    segs = []
    for i in range(e_phnum):
        base = e_phoff + i * (32 if cls == 1 else 56)
        if cls == 1:
            t, o, v, pa, fs, ms, fl, al = struct.unpack_from(endian + 'IIIIIIII', b, base)
        else:
            t, fl, o, v, pa, fs, ms, al = struct.unpack_from(endian + 'IIQQQQQQ', b, base)
        if t == 1 and (fl & 1):
            segs.append({'off': o, 'vaddr': v, 'size': fs})
    return b, e_machine, segs

def pe_segments(path):
    import pefile
    pe = pefile.PE(path, fast_load=True)
    b = open(path, 'rb').read()
    segs = []
    for s in pe.sections:
        if s.Characteristics & 0x20000000:
            segs.append({'off': s.PointerToRawData, 'vaddr': pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress, 'size': s.SizeOfRawData})
    return b, pe.FILE_HEADER.Machine, segs

def immediate(op_str):
    # last 0x... token
    toks = [t.strip(' ,') for t in op_str.split()]
    for t in reversed(toks):
        if t.startswith('0x'):
            try:
                return int(t, 16)
            except ValueError:
                pass
    return None

def scan(path):
    low = path.lower()
    source = path
    if low.endswith('.dol') or (low.endswith('.iso') and not low.endswith('.nkit.iso')):
        prep = rea_bridge.prepare(path, os.path.dirname(os.path.abspath(__file__)) + '/test/constants')
        source = prep['prepared']
    if low.endswith(('.exe', '.dll')):
        b, machine, segs = pe_segments(source)
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64 if machine == 0x8664 else capstone.CS_MODE_32)
        arch = 'x86-64' if machine == 0x8664 else 'x86'
    else:
        b, machine, segs = elf_segments(source)
        import capstone
        if machine == 20:
            md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
            arch = 'ppc32-be'
        elif machine == 62:
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
            arch = 'x86-64'
        else:
            raise ValueError(f'unsupported machine {machine}')
    md.skipdata = True
    hits = []
    for s in segs:
        code = b[s['off']:s['off'] + s['size']]
        for ins in md.disasm(code, s['vaddr']):
            if arch.startswith('x86') and ins.mnemonic == 'cmp':
                val = immediate(ins.op_str)
                if val is not None and 0 <= val <= 0xff and ('al' in ins.op_str or 'byte ptr' in ins.op_str):
                    hits.append((ins.address, val, ins.op_str))
            elif arch == 'ppc32-be' and ins.mnemonic in ('cmpwi', 'cmpdi', 'cmpi', 'cmplwi', 'cmpldi'):
                val = immediate(ins.op_str)
                if val is not None and 0 <= val <= 0xff:
                    hits.append((ins.address, val, ins.op_str))
    hits.sort()
    groups = []
    cur = []
    last = None
    for addr, val, text in hits:
        if last is not None and addr - last > 0x200:
            if len(cur) >= 4:
                groups.append(cur)
            cur = []
        cur.append((addr, val, text)); last = addr
    if len(cur) >= 4:
        groups.append(cur)
    out = []
    for g in groups:
        chars = ''.join(chr(v) for _, v, _ in g if 0x20 <= v <= 0x7e)
        out.append({
            'start': f'0x{g[0][0]:x}', 'end': f'0x{g[-1][0]:x}',
            'count': len(g), 'string': chars,
            'chars': [{'addr': f'0x{a:x}', 'value': v} for a, v, _ in g],
        })
    return {'input': os.path.abspath(path), 'prepared': os.path.abspath(source),
            'architecture': arch, 'compare_hits': len(hits), 'groups': out}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    a = ap.parse_args()
    try:
        print(json.dumps(scan(a.input), indent=2))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
