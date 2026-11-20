#!/usr/bin/env python3
"""Fingerprint PowerPC GameCube functions from an ELF plus a Ghidra CSV.

The CSV is the function boundary source; Capstone supplies the instructions.
No game code is executed.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT.parent / ".pylibs"))

import capstone
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN
from capstone.ppc import PPC_OP_REG, PPC_OP_IMM, PPC_OP_MEM

import isolate_code


def load_functions(csv_path: Path):
    funcs = []
    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].lower() == "address":
                continue
            if len(row) < 3:
                continue
            try:
                start = int(row[0], 16)
                size = int(row[2])
            except ValueError:
                continue
            if size <= 0:
                continue
            funcs.append({"address": start, "name": row[1].rstrip("\x00"), "size": size})
    funcs.sort(key=lambda x: x["address"])
    return funcs


def image_ranges(segs):
    return [(s["vaddr"], s["vaddr"] + s["size"]) for s in segs]


def in_image(value, ranges):
    return any(a <= value < b for a, b in ranges)


def tokens_for(code, start, size, ranges, md):
    tokens = []
    count = 0
    end = start + size
    for ins in md.disasm(code, start):
        if ins.address >= end:
            break
        parts = [ins.mnemonic]
        branch = ins.mnemonic.startswith("b") or ins.mnemonic.startswith("bc")
        for op in ins.operands:
            if op.type == PPC_OP_REG:
                parts.append("r:" + (ins.reg_name(op.reg) or str(op.reg)))
            elif op.type == PPC_OP_IMM:
                v = op.imm
                if branch:
                    if start <= v < end:
                        parts.append("j:%d" % (v - start))
                    else:
                        parts.append("j:ext")
                elif in_image(v, ranges):
                    parts.append("i:addr")
                else:
                    parts.append("i:%d" % v)
            elif op.type == PPC_OP_MEM:
                m = op.mem
                base = (ins.reg_name(m.base) or str(m.base)) if m.base else ""
                disp = m.disp if abs(m.disp) <= 0x10000 else "G"
                parts.append("m:%s:%s" % (base, disp))
        tokens.append(" ".join(parts))
        count += 1
        if count >= 2048:
            break
    return tokens, count


def fingerprint_function(b, seg, fn, ranges, md):
    start = fn["address"]
    size = min(fn["size"], 8192)
    seg = next((s for s in seg if s["vaddr"] <= start < s["vaddr"] + s["size"]), None)
    if seg is None:
        return None
    off = seg["off"] + (start - seg["vaddr"])
    code = b[off:off + size]
    if len(code) < 4:
        return None
    tokens, count = tokens_for(code, start, len(code), ranges, md)
    if not tokens:
        return None
    decoded = count * 4
    prefix = code[:decoded]
    norm = "codelen:%d|" % decoded + "|".join(tokens)
    return {
        "name": fn["name"],
        "address": start,
        "size": fn["size"],
        "insn_count": count,
        "decoded_bytes": decoded,
        "code_sha": hashlib.sha256(code).hexdigest(),
        "prefix_sha": hashlib.sha256(prefix).hexdigest(),
        "tail_sha": hashlib.sha256(code[decoded:]).hexdigest(),
        "norm_sha": hashlib.sha256(norm.encode()).hexdigest(),
        "tokens": tokens,
    }


def build(elf_path: Path, csv_path: Path, out_path: Path, label: str):
    b, machine, entry, segs = isolate_code.elf_segments(str(elf_path))
    if machine != 20:
        raise SystemExit(f"not a PowerPC ELF: e_machine={machine}")
    md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
    md.detail = True
    ranges = image_ranges(segs)
    funcs = load_functions(csv_path)
    out = []
    for i, fn in enumerate(funcs):
        fp = fingerprint_function(b, segs, fn, ranges, md)
        if fp:
            out.append(fp)
        if (i + 1) % 2000 == 0:
            print(f"{label} {i + 1}/{len(funcs)}", file=sys.stderr)
    out_path.write_text(json.dumps({"label": label, "elf": str(elf_path), "csv": str(csv_path), "functions": out}), encoding="utf-8")
    print(f"{label}: wrote {len(out)}/{len(funcs)} functions", file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("elf")
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--label", default="ppc")
    args = ap.parse_args()
    build(Path(args.elf), Path(args.csv), Path(args.out), args.label)
