#!/usr/bin/env python3
"""Convert a GameCube/Wii DOL executable to ELF32 big-endian PowerPC.

This is a bridge for analysis tools that accept ELF32 EM_PPC (for example
REA's Ghidra PowerPC lane). It does not execute the DOL and does not recover
symbols.
"""
import json
import os
import struct
import sys

PT_LOAD = 1
PF_X = 1
PF_W = 2
PF_R = 4
SHT_PROGBITS = 1
SHT_NOBITS = 8
SHT_STRTAB = 3
SHF_WRITE = 1
SHF_ALLOC = 2
SHF_EXECINSTR = 4

def align_up(v, a):
    return (v + a - 1) & ~(a - 1)

def parse_dol(path):
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) < 0x100:
        raise ValueError('DOL shorter than 0x100 header')
    text_off = struct.unpack_from('>7I', data, 0x00)
    data_off = struct.unpack_from('>11I', data, 0x1C)
    text_addr = struct.unpack_from('>7I', data, 0x48)
    data_addr = struct.unpack_from('>11I', data, 0x64)
    text_size = struct.unpack_from('>7I', data, 0x90)
    data_size = struct.unpack_from('>11I', data, 0xAC)
    bss_addr, bss_size, entry = struct.unpack_from('>III', data, 0xD8)
    sections = []
    for i in range(7):
        if text_size[i]:
            sections.append({'name': f'.text{i}', 'off': text_off[i], 'addr': text_addr[i],
                             'size': text_size[i], 'flags': PF_R | PF_X, 'sh_flags': SHF_ALLOC | SHF_EXECINSTR,
                             'kind': 'text'})
    for i in range(11):
        if data_size[i]:
            sections.append({'name': f'.data{i}', 'off': data_off[i], 'addr': data_addr[i],
                             'size': data_size[i], 'flags': PF_R | PF_W, 'sh_flags': SHF_ALLOC | SHF_WRITE,
                             'kind': 'data'})
    for s in sections:
        if s['off'] + s['size'] > len(data):
            raise ValueError(f"{s['name']} extends past EOF: {s['off']:#x}+{s['size']:#x} > {len(data):#x}")
    return {'data': data, 'sections': sections, 'bss_addr': bss_addr, 'bss_size': bss_size,
            'entry': entry, 'file_size': len(data)}

def overlap(a, b):
    return a['addr'] < b['addr'] + b['size'] and b['addr'] < a['addr'] + a['size']

def build_elf(dol, skip_bss_overlap=True):
    sections = sorted(dol['sections'], key=lambda s: (s['addr'], s['off']))
    bss = {'name': '.bss', 'addr': dol['bss_addr'], 'size': dol['bss_size'],
           'flags': PF_R | PF_W, 'sh_flags': SHF_ALLOC | SHF_WRITE, 'kind': 'bss', 'off': 0}
    bss_skipped = False
    if bss['size']:
        if any(overlap(bss, s) for s in sections):
            bss_skipped = True
            bss = None
        else:
            sections.append(bss)
    # ELF header + program headers
    phnum = len(sections)
    phoff = 52
    data_start = align_up(phoff + phnum * 32, 0x1000)
    out = bytearray(data_start)
    # e_ident + ELF header
    e_ident = bytearray(16)
    e_ident[0:4] = b'\x7fELF'
    e_ident[4] = 1      # 32-bit
    e_ident[5] = 2      # big-endian
    e_ident[6] = 1      # EV_CURRENT
    e_ident[7] = 0      # SysV
    out[0:16] = e_ident
    struct.pack_into('>HHIIIIIHHHHHH', out, 16,
                     2,      # ET_EXEC
                     20,     # EM_PPC
                     1,      # EV_CURRENT
                     dol['entry'],
                     phoff,  # e_phoff
                     0,      # e_shoff (filled later)
                     0,      # e_flags: no EF_PPC_EMB
                     52,     # e_ehsize
                     32,     # e_phentsize
                     phnum,
                     40,     # e_shentsize
                     0,      # e_shnum (filled later)
                     0)      # e_shstrndx (filled later)
    phdrs = []
    file_cursor = data_start
    shstr = bytearray(b'\0')
    sh_name_offsets = {}
    section_defs = []
    for s in sections:
        if s['kind'] == 'bss':
            off = file_cursor
            filesz = 0
            memsz = s['size']
        else:
            # Keep p_offset congruent to p_vaddr modulo 0x20.
            off = align_up(file_cursor, 0x20)
            while (off & 0x1f) != (s['addr'] & 0x1f):
                off += 0x20
            out.extend(b'\0' * (off - len(out)))
            out.extend(dol['data'][s['off']:s['off'] + s['size']])
            filesz = s['size']
            memsz = s['size']
            file_cursor = off + filesz
        p_type = PT_LOAD
        p_flags = s['flags']
        p_align = 1 if s['kind'] == 'bss' else 0x20
        phdrs.append(struct.pack('>IIIIIIII', p_type, off, s['addr'], s['addr'],
                                 filesz, memsz, p_flags, p_align))
        if s['name'] not in sh_name_offsets:
            sh_name_offsets[s['name']] = len(shstr)
            shstr.extend(s['name'].encode('ascii') + b'\0')
        sh_type = SHT_NOBITS if s['kind'] == 'bss' else SHT_PROGBITS
        section_defs.append({'name': s['name'], 'type': sh_type, 'flags': s['sh_flags'],
                             'addr': s['addr'], 'off': off, 'size': s['size']})
    # shstrtab section data
    sh_name_offsets['.shstrtab'] = len(shstr)
    shstr.extend(b'.shstrtab\0')
    shstr_off = align_up(len(out), 4)
    out.extend(b'\0' * (shstr_off - len(out)))
    out.extend(shstr)
    # section headers
    shoff = align_up(len(out), 4)
    out.extend(b'\0' * (shoff - len(out)))
    shstr_index = len(section_defs) + 1
    shdrs = [b'\0' * 40]
    for s in section_defs:
        shdrs.append(struct.pack('>IIIIIIIIII', sh_name_offsets[s['name']], s['type'], s['flags'],
                                 s['addr'], s['off'], s['size'], 0, 0, 0x20, 0))
    shdrs.append(struct.pack('>IIIIIIIIII', sh_name_offsets.get('.shstrtab', 0), SHT_STRTAB, 0,
                             0, shstr_off, len(shstr), 0, 0, 1, 0))
    out.extend(b''.join(shdrs))
    struct.pack_into('>I', out, 32, shoff)
    struct.pack_into('>H', out, 48, len(shdrs))
    struct.pack_into('>H', out, 50, shstr_index)
    # write actual program headers
    out[phoff:phoff + phnum * 32] = b''.join(phdrs)
    return bytes(out), bss_skipped

def validate_elf(path):
    with open(path, 'rb') as f:
        b = f.read()
    assert b[:4] == b'\x7fELF', 'bad magic'
    assert b[4] == 1 and b[5] == 2, 'not ELF32 BE'
    e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = struct.unpack_from('>HHIIIIIHHHHHH', b, 16)
    assert e_type == 2 and e_machine == 20 and e_flags == 0, 'not ET_EXEC EM_PPC flags=0'
    segs = []
    for i in range(e_phnum):
        p_type, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = struct.unpack_from('>IIIIIIII', b, e_phoff + i * 32)
        assert p_type == 1, 'not PT_LOAD'
        assert p_off + p_filesz <= len(b), 'segment past EOF'
        assert (p_off % p_align) == (p_vaddr % p_align), 'p_offset/p_vaddr misaligned'
        segs.append({'off': p_off, 'vaddr': p_vaddr, 'filesz': p_filesz, 'memsz': p_memsz, 'flags': p_flags})
    assert any(s['vaddr'] <= e_entry < s['vaddr'] + s['memsz'] for s in segs), 'entry outside segments'
    return {'type': e_type, 'machine': e_machine, 'entry': e_entry, 'phnum': e_phnum,
            'shnum': e_shnum, 'size': len(b), 'segments': segs}

def main():
    if len(sys.argv) < 3:
        print('usage: dol_to_elf.py <input.dol> <output.elf>', file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    dol = parse_dol(src)
    elf, bss_skipped = build_elf(dol)
    with open(dst, 'wb') as f:
        f.write(elf)
    report = validate_elf(dst)
    report.update({'input': src, 'output': dst, 'dol_bytes': dol['file_size'],
                   'sections': len(dol['sections']), 'bss_skipped': bss_skipped,
                   'bss_addr': dol['bss_addr'], 'bss_size': dol['bss_size']})
    print(json.dumps(report, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
