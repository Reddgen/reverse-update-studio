#!/usr/bin/env python3
"""Prepare a game executable for REA's native analysis lanes.

Supported:
  .dol                 -> ELF32 BE PowerPC
  GameCube .iso        -> extract the DOL -> ELF32 BE PowerPC
  .elf                 -> pass through after validation
  PE (.exe/.dll)       -> pass through for REA's Windows PE lane

Unsupported:
  .nkit.iso, .rvz, .xex, .pirs, PS3 SCE/EBOOT, PSP PRX/EBOOT
"""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dol_to_elf

GAMECUBE_MAGIC = b'\xc2\x33\x9f\x3d'

def gc_dol_bytes(iso_path):
    with open(iso_path, 'rb') as f:
        f.seek(0x1c)
        if f.read(4) != GAMECUBE_MAGIC:
            raise ValueError('not a GameCube disc image (magic missing)')
        f.seek(0x420)
        dol_off = struct.unpack('>I', f.read(4))[0]
        size = os.path.getsize(iso_path)
        if not dol_off or dol_off >= size:
            raise ValueError('invalid DOL offset in boot header')
        f.seek(dol_off)
        hdr = f.read(0x100)
        text_off = struct.unpack_from('>7I', hdr, 0x00)
        data_off = struct.unpack_from('>11I', hdr, 0x1C)
        text_size = struct.unpack_from('>7I', hdr, 0x90)
        data_size = struct.unpack_from('>11I', hdr, 0xAC)
        end = 0x100
        for off, sz in zip(text_off, text_size):
            if sz:
                end = max(end, off + sz)
        for off, sz in zip(data_off, data_size):
            if sz:
                end = max(end, off + sz)
        if end > size:
            raise ValueError('DOL extends past ISO EOF')
        f.seek(dol_off)
        return f.read(end)

def prepare(input_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.basename(input_path)
    low = name.lower()
    result = {'input': os.path.abspath(input_path), 'kind': None, 'prepared': None, 'notes': []}
    if low.endswith('.dol'):
        result['kind'] = 'gamecube-dol'
        dol_path = input_path
    elif low.endswith('.iso') and not low.endswith('.nkit.iso'):
        result['kind'] = 'gamecube-iso'
        dol_path = os.path.join(out_dir, name + '.dol')
        with open(dol_path, 'wb') as f:
            f.write(gc_dol_bytes(input_path))
        result['notes'].append('extracted main DOL from GameCube ISO')
    elif low.endswith('.elf'):
        result['kind'] = 'elf'
        dol_to_elf.validate_elf(input_path)
        result['prepared'] = os.path.abspath(input_path)
        result['rea_command'] = f'rea analyze "{result["prepared"]}" --provider ghidra --json'
        return result
    elif low.endswith(('.exe', '.dll')):
        result['kind'] = 'pe'
        result['prepared'] = os.path.abspath(input_path)
        result['rea_command'] = f'rea analyze "{result["prepared"]}" --provider ghidra --json'
        result['notes'].append('pass-through; REA Windows Ghidra lane')
        return result
    else:
        raise ValueError('unsupported input; need .dol, GameCube .iso, .elf or PE')

    dol = dol_to_elf.parse_dol(dol_path)
    elf, bss_skipped = dol_to_elf.build_elf(dol)
    out_elf = os.path.join(out_dir, os.path.splitext(name)[0] + '.elf')
    with open(out_elf, 'wb') as f:
        f.write(elf)
    report = dol_to_elf.validate_elf(out_elf)
    result.update({
        'prepared': os.path.abspath(out_elf),
        'dol_bytes': dol['file_size'],
        'sections': len(dol['sections']),
        'bss_skipped': bss_skipped,
        'entry': hex(report['entry']),
        'segments': report['phnum'],
        'rea_command': f'rea analyze "{os.path.abspath(out_elf)}" --provider ghidra --json',
    })
    if bss_skipped:
        result['notes'].append('BSS omitted because it overlaps loaded data in this DOL; code/data analysis is unaffected')
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('--out', default='rea_bridge_out')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--run', action='store_true', help='run rea analyze if rea is on PATH')
    a = ap.parse_args()
    try:
        result = prepare(a.input, a.out)
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}), file=sys.stderr)
        return 2
    if a.run:
        rea = shutil.which('rea')
        if not rea:
            result['run'] = {'ok': False, 'error': 'rea not installed/on PATH'}
        else:
            p = subprocess.run([rea, 'analyze', result['prepared'], '--provider', 'ghidra', '--json'],
                               capture_output=True, text=True)
            result['run'] = {'ok': p.returncode == 0, 'returncode': p.returncode,
                             'stdout_tail': p.stdout[-4000:], 'stderr_tail': p.stderr[-2000:]}
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
