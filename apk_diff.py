#!/usr/bin/env python3
"""Method-level diff for Android APK/DEX files using LIEF."""
import argparse
import csv
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / ".pylibs"))

logging.disable(logging.CRITICAL)
try:
    from androguard.core.dex import DEX
except ImportError as e:
    raise SystemExit("androguard is required: pip install androguard") from e


def _dex_paths(path: Path, workdir: Path):
    if path.suffix.lower() != ".apk" and not zipfile.is_zipfile(path):
        return [path]
    out = []
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith(".dex"))
        for i, name in enumerate(names):
            data = z.read(name)
            p = workdir / f"classes_{i}.dex"
            p.write_bytes(data)
            out.append(p)
    return out


def _flag_names(flags):
    return str(flags or "")


def _norm_output(name, out):
    out = str(out or "")
    # Branch and payload offsets shift when unrelated methods change size.
    if name.startswith(("goto", "if-", "packed-switch", "sparse-switch", "fill-array-data")):
        out = re.sub(r"[+-]?0x[0-9a-fA-F]+", "<off>", out)
    return out


def load_methods(path: Path, workdir: Path):
    methods = []
    for dex in _dex_paths(path, workdir):
        d = DEX(dex.read_bytes())
        for cls in d.get_classes():
            cname = str(cls.get_name())
            for m in cls.get_methods():
                try:
                    ins = list(m.get_instructions())
                except Exception:
                    ins = []
                norm = "\n".join(f"{i.get_name()} {_norm_output(i.get_name(), i.get_output())}" for i in ins)
                key = (cname, str(m.get_name()), str(m.get_descriptor()))
                methods.append({
                    "key": key,
                    "class": cname,
                    "name": str(m.get_name()),
                    "prototype": str(m.get_descriptor()),
                    "dex": dex.name,
                    "access": _flag_names(m.get_access_flags_string()),
                    "code_offset": int(getattr(m, "code_off", 0) or 0),
                    "code_sha": hashlib.sha256(norm.encode("utf-8")).hexdigest(),
                    "code_bytes": len(norm.encode("utf-8")),
                })
    return methods


def compare(A, B):
    from collections import defaultdict
    ga, gb = defaultdict(list), defaultdict(list)
    for m in A:
        ga[m["key"]].append(m)
    for m in B:
        gb[m["key"]].append(m)

    identical = changed = 0
    pairs, removed, added = [], [], []
    for key in ga.keys() & gb.keys():
        al, bl = list(ga[key]), list(gb[key])
        # Exact code + access matches first, preserving duplicates.
        buckets = defaultdict(list)
        for b in bl:
            buckets[(b["code_sha"], b["access"])].append(b)
        left_a = []
        for a in al:
            bucket = buckets.get((a["code_sha"], a["access"]))
            if bucket:
                bucket.pop()
                identical += 1
            else:
                left_a.append(a)
        left_b = [b for bucket in buckets.values() for b in bucket]
        # Pair remaining same-key methods as changed.
        for a, b in zip(left_a, left_b):
            changed += 1
            pairs.append({"relation": "changed", "a": a, "b": b})
        removed.extend(left_a[len(left_b):])
        added.extend(left_b[len(left_a):])

    for key in ga.keys() - gb.keys():
        removed.extend(ga[key])
    for key in gb.keys() - ga.keys():
        added.extend(gb[key])

    summary = {
        "methods_a": len(A), "methods_b": len(B),
        "matched": identical + changed, "identical": identical, "changed": changed,
        "removed": len(removed), "added": len(added),
        "match_rate": round(100 * (identical + changed) / max(1, len(A)), 2),
    }
    return {"summary": summary, "pairs": pairs, "removed": removed, "added": added}


def write_csv(result, path: Path):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["class", "method", "prototype", "relation", "code_a", "code_b",
                    "access_a", "access_b", "dex_a", "dex_b"])
        for p in result["pairs"]:
            a, b = p["a"], p["b"]
            w.writerow([a["class"], a["name"], a["prototype"], p["relation"],
                        a["code_bytes"], b["code_bytes"], a["access"], b["access"], a["dex"], b["dex"]])
        for a in result["removed"]:
            w.writerow([a["class"], a["name"], a["prototype"], "removed", a["code_bytes"], "", a["access"], "", a["dex"], ""])
        for b in result["added"]:
            w.writerow([b["class"], b["name"], b["prototype"], "added", "", b["code_bytes"], "", b["access"], "", b["dex"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    work = Path(args.outdir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        A = load_methods(Path(args.a), tmp)
        B = load_methods(Path(args.b), tmp)
    result = compare(A, B)
    result["builds"] = {"a": {"label": args.label_a, "path": args.a},
                        "b": {"label": args.label_b, "path": args.b}}
    cmp = work / "compare.json"
    csvp = work / "changed.csv"
    cmp.write_text(json.dumps(result), encoding="utf-8")
    write_csv(result, csvp)
    result["outputs"] = {"compare": str(cmp), "changed": str(csvp)}
    (work / "result.json").write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
