#!/usr/bin/env python3
"""Compare two PE/PDB builds at function level.

Reuses the existing PDB enumeration, fingerprint and compare engines, with
automatic x86/x64 selection. This is the engine behind Studio's Release Diff.
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / ".pylibs"))

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_64

import compare
import fingerprint


def find_pair(path: str, pdb_path: str | None = None):
    p = Path(path).expanduser().resolve()
    if p.is_dir():
        candidates = []
        for exe in p.glob("*.exe"):
            pdb = exe.with_suffix(".pdb")
            if pdb.exists():
                candidates.append(exe)
        if not candidates:
            raise ValueError(f"no .exe with a matching .pdb in {p}")
        preferred = [x for x in candidates if x.name.lower() == "pyrogenesis.exe"]
        exe = preferred[0] if preferred else max(candidates, key=lambda x: x.stat().st_size)
        pdb = exe.with_suffix(".pdb")
    else:
        exe = p
        pdb = Path(pdb_path).expanduser().resolve() if pdb_path else exe.with_suffix(".pdb")
    if not exe.exists():
        raise ValueError(f"executable not found: {exe}")
    if not pdb.exists():
        raise ValueError(f"PDB not found: {pdb}")
    return exe, pdb


def machine_mode(exe: Path):
    pe = pefile.PE(str(exe), fast_load=True)
    machine = pe.FILE_HEADER.Machine
    if machine == 0x14C:
        return CS_MODE_32, "x86"
    if machine == 0x8664:
        return CS_MODE_64, "x64"
    raise ValueError(f"unsupported PE machine 0x{machine:04x}; only x86/x64")


def build_fingerprints(label: str, exe: Path, pdb: Path, outdir: Path):
    mode, arch = machine_mode(exe)
    fingerprint.md = Cs(CS_ARCH_X86, mode)
    fingerprint.md.detail = True

    sym_path = outdir / f"symbols_{label}.json"
    fp_path = outdir / f"fingerprints_{label}.json"
    subprocess.run(
        [sys.executable, str(ROOT / "enum_pdb.py"), str(exe), str(sym_path), str(pdb.parent)],
        check=True, capture_output=True, text=True,
    )
    sym_data = json.loads(sym_path.read_text(encoding="utf-8"))
    meta = sym_data.get("meta", {})
    funcs = sym_data.get("functions", [])
    if meta.get("pdb_unmatched"):
        raise ValueError(f"PDB does not match {exe.name}: {pdb.name}")
    if not funcs:
        raise ValueError(f"no functions enumerated from {exe.name}")
    fingerprint.build(label, str(sym_path), str(exe), str(fp_path))
    data = json.loads(fp_path.read_text(encoding="utf-8"))
    return data["functions"], {
        "label": label,
        "arch": arch,
        "exe": str(exe),
        "pdb": str(pdb),
        "functions": len(funcs),
        "pdb_unmatched": bool(meta.get("pdb_unmatched")),
        "symbols": str(sym_path),
        "fingerprints": str(fp_path),
    }


def write_changed(result, path: Path):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name_a", "name_b", "rva_a", "rva_b", "size_a", "size_b",
                    "insn_a", "insn_b", "relation", "source_a", "source_b", "method", "confidence"])
        for x in result["pairs"]:
            if x["code_relation"] != "changed":
                continue
            w.writerow([x["name_a"], x["name_b"], x["rva_a"], x["rva_b"], x["size_a"], x["size_b"],
                        x["insn_a"], x["insn_b"], x["code_relation"], x.get("source_a", ""), x.get("source_b", ""),
                        x["match_method"], x["confidence"]])
        for x in result["removed"]:
            w.writerow([x["name"], "", x["rva"], "", x["size"], "", "", "", "removed", "", "", "", ""])
        for x in result["added"]:
            w.writerow(["", x["name"], "", x["rva"], "", x["size"], "", "", "added", "", "", "", ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="build A directory or exe")
    ap.add_argument("--b", required=True, help="build B directory or exe")
    ap.add_argument("--pdb-a")
    ap.add_argument("--pdb-b")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    exe_a, pdb_a = find_pair(args.a, args.pdb_a)
    exe_b, pdb_b = find_pair(args.b, args.pdb_b)

    A, meta_a = build_fingerprints(args.label_a, exe_a, pdb_a, outdir)
    B, meta_b = build_fingerprints(args.label_b, exe_b, pdb_b, outdir)
    result = compare.compare(A, B, args.label_a, args.label_b)

    result["builds"] = {"a": meta_a, "b": meta_b}
    result["inputs"] = {"a": str(exe_a), "b": str(exe_b), "pdb_a": str(pdb_a), "pdb_b": str(pdb_b)}
    json_path = outdir / "compare.json"
    pair_path = outdir / "pairs.csv"
    changed_path = outdir / "changed.csv"
    json_path.write_text(json.dumps(result), encoding="utf-8")
    compare.write_csv(result, str(pair_path))
    write_changed(result, changed_path)

    summary = dict(result["summary"])
    summary["builds"] = result["builds"]
    summary["outputs"] = {"compare": str(json_path), "pairs": str(pair_path), "changed": str(changed_path)}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
