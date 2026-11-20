#!/usr/bin/env python3
"""Isolate executable code from a game binary and produce a function-candidate map.

Supported inputs:
  .dol / GameCube .iso  -> DOL -> ELF32 BE PPC
  .elf                 -> ELF32/ELF64
  .exe / .dll          -> PE x86/x64

This is static isolation, not execution and not source recovery.
"""
import argparse
import csv
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dol_to_elf
import rea_bridge

sys.path.insert(0, r'C:\Users\Windows 11 PRO\Documents\deepseek-harness\default-workspace\.pylibs')

def capstone_for(machine, bits, endian):
    import capstone
    if machine == 20:  # EM_PPC
        return capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN), 'ppc32-be'
    if machine == 62:  # EM_X86_64
        return capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64), 'x86-64'
    if machine == 3:   # EM_386
        return capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32), 'x86'
    raise ValueError(f'unsupported ELF machine {machine}')

def elf_segments(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF':
        raise ValueError('not ELF')
    cls, data = b[4], b[5]
    endian = '>' if data == 2 else '<'
    if cls != 1:
        raise ValueError('only ELF32 supported by this isolator')
    e_machine, e_entry, e_phoff, e_phnum = struct.unpack_from(endian + 'H', b, 18)[0], struct.unpack_from(endian + 'I', b, 24)[0], struct.unpack_from(endian + 'I', b, 28)[0], struct.unpack_from(endian + 'H', b, 44)[0]
    segs = []
    for i in range(e_phnum):
        t, o, v, pa, fs, ms, fl, al = struct.unpack_from(endian + 'IIIIIIII', b, e_phoff + i * 32)
        if t == 1 and (fl & 1):
            segs.append({'vaddr': v, 'off': o, 'size': fs, 'flags': fl})
    return b, e_machine, e_entry, segs

def pe_segments(path):
    import pefile
    pe = pefile.PE(path, fast_load=True)
    machine = pe.FILE_HEADER.Machine
    image_base = pe.OPTIONAL_HEADER.ImageBase
    entry = image_base + pe.OPTIONAL_HEADER.AddressOfEntryPoint
    segs = []
    for s in pe.sections:
        if s.Characteristics & 0x20000000 or s.Name.rstrip(b'\0').lower() == b'.text':
            off = s.PointerToRawData
            size = s.SizeOfRawData
            if size:
                segs.append({'vaddr': image_base + s.VirtualAddress, 'off': off, 'size': size, 'name': s.Name.rstrip(b'\0').decode('latin-1', 'replace')})
    return open(path, 'rb').read(), machine, entry, segs

def find_candidates(insns, arch, ranges):
    starts = []
    def in_code(addr):
        return any(lo <= addr < hi for lo, hi in ranges)
    if arch == 'ppc32-be':
        for i, ins in enumerate(insns):
            if ins.mnemonic == 'bl' and ins.op_str.startswith('0x'):
                try:
                    target = int(ins.op_str, 16)
                    if in_code(target):
                        starts.append(target)
                except ValueError:
                    pass
            if ins.mnemonic == 'stwu' and ins.op_str.startswith('r1, -') and ins.op_str.endswith('(r1)'):
                window = insns[i + 1:i + 4]
                before = insns[max(0, i - 2):i]
                if any(x.mnemonic in ('mflr', 'stw') for x in window) or any(x.mnemonic == 'mflr' for x in before):
                    starts.append(ins.address)
    else:
        for ins in insns:
            if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
                try:
                    target = int(ins.op_str, 16)
                    if in_code(target):
                        starts.append(target)
                except ValueError:
                    pass
        for i, ins in enumerate(insns):
            if ins.mnemonic == 'push' and ins.op_str == 'rbp':
                window = insns[i + 1:i + 4]
                if any(x.mnemonic == 'mov' and x.op_str.replace(' ', '') == 'rbp,rsp' for x in window):
                    starts.append(ins.address)
    return sorted(set(starts))

def isolate(input_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    low = input_path.lower()
    source = input_path
    if low.endswith('.dol') or (low.endswith('.iso') and not low.endswith('.nkit.iso')):
        prep = rea_bridge.prepare(input_path, out_dir)
        source = prep['prepared']
        kind = prep['kind']
    elif low.endswith('.exe') or low.endswith('.dll'):
        kind = 'pe'
    elif low.endswith('.elf'):
        kind = 'elf'
    else:
        raise ValueError('unsupported input')
    if kind == 'pe':
        b, machine, entry, segs = pe_segments(source)
        arch = {0x8664: 'x86-64', 0x14c: 'x86'}.get(machine)
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64 if machine == 0x8664 else capstone.CS_MODE_32)
    else:
        b, machine, entry, segs = elf_segments(source)
        md, arch = capstone_for(machine, 32, True)
    md.skipdata = True
    total = 0
    candidates = []
    code_bytes = 0
    ranges = [(s['vaddr'], s['vaddr'] + s['size']) for s in segs]
    for s in segs:
        code = b[s['off']:s['off'] + s['size']]
        code_bytes += len(code)
        insns = list(md.disasm(code, s['vaddr']))
        total += len(insns)
        candidates.extend(find_candidates(insns, arch, ranges))
    candidates = sorted(set(candidates))
    rows = []
    for i, addr in enumerate(candidates):
        end = candidates[i + 1] if i + 1 < len(candidates) else addr + 4
        rows.append({'address': f'0x{addr:x}', 'approx_size': max(0, end - addr)})
    csv_path = os.path.join(out_dir, os.path.splitext(os.path.basename(input_path))[0] + '.functions.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['address', 'approx_size'])
        w.writeheader(); w.writerows(rows)
    return {
        'input': os.path.abspath(input_path), 'kind': kind, 'architecture': arch,
        'entry': f'0x{entry:x}', 'code_segments': len(segs), 'code_bytes': code_bytes,
        'instructions': total, 'candidate_functions': len(candidates),
        'functions_csv': os.path.abspath(csv_path),
        'note': 'candidate functions use call-target + prologue heuristics; they are not symbol-confirmed',
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('--out', default='isolated')
    a = ap.parse_args()
    try:
        print(json.dumps(isolate(a.input, a.out), indent=2))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
