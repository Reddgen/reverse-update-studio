"""Build function fingerprints for OpenRCT2 binaries using PDB symbols + Capstone."""
import json, hashlib, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.pylibs'))
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_GRP_JUMP, CS_GRP_CALL
from capstone.x86 import X86_OP_REG, X86_OP_IMM, X86_OP_MEM
from pdb_lines import LineIndex

BASE = 0x140000000

def clean_name(n):
    return n.rstrip('\x00')

class Image:
    def __init__(self, path):
        self.path = path
        self.pe = pefile.PE(path, fast_load=True)
        self.base = self.pe.OPTIONAL_HEADER.ImageBase
        self.size = self.pe.OPTIONAL_HEADER.SizeOfImage
        self.data = open(path, 'rb').read()
        self.sections = []
        for s in self.pe.sections:
            self.sections.append({
                'name': s.Name.decode('latin-1').rstrip('\x00'),
                'va': s.VirtualAddress,
                'vsize': s.Misc_VirtualSize,
                'raw_size': s.SizeOfRawData,
                'raw_ptr': s.PointerToRawData,
            })
        self.text = next(s for s in self.sections if s['name'] == '.text')

    def read(self, rva, size):
        for s in self.sections:
            if s['va'] <= rva and rva + size <= s['va'] + max(s['vsize'], s['raw_size']):
                off = s['raw_ptr'] + (rva - s['va'])
                return self.data[off:off+size]
        return None

md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True

def _tokens(code, start, stop, img):
    tokens = []
    count = 0
    for insn in md.disasm(code, start):
        if insn.address >= stop:
            break
        parts = [insn.mnemonic]
        for op in insn.operands:
            if op.type == X86_OP_REG:
                parts.append('r:' + insn.reg_name(op.reg))
            elif op.type == X86_OP_IMM:
                v = op.imm
                if insn.group(CS_GRP_JUMP) or insn.group(CS_GRP_CALL):
                    if start <= v < stop:
                        parts.append('j:%d' % (v - start))
                    else:
                        parts.append('j:ext')
                elif img.base <= v < img.base + img.size:
                    parts.append('i:addr')
                elif 0x1000 <= v < img.size:
                    # 32-bit image-relative address folded into an immediate.
                    parts.append('i:rva')
                elif v > 0xffffffff or v < -0x80000000:
                    parts.append('i:big')
                else:
                    parts.append('i:%d' % v)
            elif op.type == X86_OP_MEM:
                m = op.mem
                base = insn.reg_name(m.base) if m.base else ''
                idx = insn.reg_name(m.index) if m.index else ''
                if base == 'rip':
                    parts.append('m:rip:%d' % op.size)
                else:
                    # Large displacements in non-RIP addressing are virtually
                    # always references into image global tables; their
                    # absolute value shifts when the image is relaid out.
                    disp = m.disp if abs(m.disp) <= 0x10000 else 'G'
                    parts.append('m:%s:%s:%d:%s:%d' % (base, idx, m.scale, disp, op.size))
        tokens.append(' '.join(parts))
        count += 1
    return tokens, count

def _line_code_end(code, start, rva, size, line_max):
    """Advance from the last source line to the next terminal instruction."""
    if line_max is None:
        return None
    pos = line_max - rva
    if pos < 0 or pos >= size:
        return None
    base = start + pos
    remaining = code[pos:pos + 256]
    prev = None
    for insn in md.disasm(remaining, base):
        end = pos + (insn.address + insn.size - base)
        if insn.mnemonic in ('ret', 'retf', 'jmp', 'ljmp', 'ud2'):
            return end
        # int3 (and often a following nop) is the standard end-of-function
        # padding that precedes an embedded jump table.
        if insn.mnemonic == 'int3':
            return end
        if insn.mnemonic == 'nop' and prev in ('int3', 'call'):
            return end
        prev = insn.mnemonic
    return None

def tokenize(img, rva, size, with_tokens=False, line_max=None):
    code = img.read(rva, size)
    if code is None:
        return None
    start = img.base + rva
    end = start + size
    decoded = 0
    last_terminal_end = None
    terminal_mnemonics = {'ret', 'retf', 'jmp', 'ljmp', 'ud2'}
    for insn in md.disasm(code, start):
        if insn.address >= end:
            break
        decoded += insn.size
        if insn.mnemonic in terminal_mnemonics:
            last_terminal_end = decoded
    # Switch tables are frequently emitted after the final return/jump and are
    # part of the PDB function extent. Exclude that embedded data from the
    # instruction fingerprint and hash it separately. The PDB line table is the
    # strongest signal: data tables carry no source line records.
    line_end = _line_code_end(code, start, rva, size, line_max)
    if line_end is not None and line_end >= max(decoded * 0.25, 8):
        code_end = line_end
    elif decoded < size and last_terminal_end and last_terminal_end < size:
        code_end = last_terminal_end
    else:
        code_end = min(decoded, size)
    code_prefix = code[:code_end]
    if code_prefix:
        tokens, insn_count = _tokens(code_prefix, start, start + code_end, img)
    else:
        tokens, insn_count = [], 0
    norm = 'codelen:%d|' % code_end + '|'.join(tokens)
    res = {
        'code_sha': hashlib.sha256(code).hexdigest(),
        'prefix_sha': hashlib.sha256(code_prefix).hexdigest(),
        'tail_sha': hashlib.sha256(code[code_end:]).hexdigest(),
        'norm_sha': hashlib.sha256(norm.encode()).hexdigest(),
        'insn_count': insn_count,
        'decoded_bytes': code_end,
        'raw_decoded_bytes': decoded,
        'code_bytes': code_end,
        'truncated': code_end < size,
        'first_sha': hashlib.sha256(code[:16]).hexdigest(),
    }
    if with_tokens:
        res['tokens'] = tokens
    return res

def fingerprint(img, rva, size, line_max=None):
    return tokenize(img, rva, size, line_max=line_max)

def build(ver, sym_json, exe_path, out_path):
    img = Image(exe_path)
    lines = LineIndex(exe_path)
    syms = json.load(open(sym_json, encoding='utf-8'))['functions']
    out = []
    t0 = time.time()
    bad = 0
    for i, s in enumerate(syms):
        name = clean_name(s['name'])
        rva, size = s['rva'], s['size']
        fp = fingerprint(img, rva, size, lines.max_in(rva, size))
        if fp is None:
            bad += 1
            continue
        rec = {
            'name': name,
            'rva': rva,
            'size': size,
            'flags': s['flags'],
        }
        src = lines.source_at(rva, size)
        if src:
            rec['source'] = src
        rec.update(fp)
        out.append(rec)
        if (i + 1) % 5000 == 0:
            print(ver, i + 1, '%.1fs' % (time.time() - t0), file=sys.stderr)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'version': ver, 'exe': exe_path, 'functions': out}, f)
    lines.close()
    print(ver, 'wrote', len(out), 'bad', bad, 'in %.1fs' % (time.time() - t0), file=sys.stderr)

if __name__ == '__main__':
    d = os.path.dirname(os.path.abspath(__file__))
    jobs = [
        ('v0.5.5', f'{d}/reports/symbols_v055.json', f'{d}/extracted/v0.5.5/openrct2.exe', f'{d}/reports/fingerprints_v055.json'),
        ('v0.5.6', f'{d}/reports/symbols_v056.json', f'{d}/extracted/v0.5.6/openrct2.exe', f'{d}/reports/fingerprints_v056.json'),
        ('v0.5.7', f'{d}/reports/symbols_v057.json', f'{d}/extracted/v0.5.7/openrct2.exe', f'{d}/reports/fingerprints_v057.json'),
    ]
    for job in jobs:
        build(*job)
