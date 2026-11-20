#!/usr/bin/env python3
"""Run a two-build PowerPC diff: fingerprint A, fingerprint B, compare."""
import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(args):
    p = subprocess.run([sys.executable, "-u"] + [str(x) for x in args], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout)[-4000:])
    return p


def write_changed(compare_path: Path, out_path: Path):
    d = json.loads(compare_path.read_text(encoding="utf-8"))
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name_a", "name_b", "address_a", "address_b", "size_a", "size_b",
                    "insn_a", "insn_b", "relation", "method"])
        for p in d["pairs"]:
            if p["relation"] not in ("identical", "relocated"):
                w.writerow([p["name_a"], p["name_b"], p["address_a"], p["address_b"], p["size_a"], p["size_b"],
                            p["insn_a"], p["insn_b"], p["relation"], p["method"]])
        for x in d["removed"]:
            w.writerow([x["name"], "", x["address"], "", x["size"], "", x["insn_count"], "", "removed", ""])
        for x in d["added"]:
            w.writerow(["", x["name"], "", x["address"], "", x["size"], "", x["insn_count"], "added", ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf-a", required=True)
    ap.add_argument("--csv-a", required=True)
    ap.add_argument("--elf-b", required=True)
    ap.add_argument("--csv-b", required=True)
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    out = Path(args.outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    fp_a, fp_b = out / "ppc_a.json", out / "ppc_b.json"
    cmp = out / "compare.json"
    pairs = out / "pairs.csv"
    changed = out / "changed.csv"

    run([ROOT / "ppc_fingerprint.py", args.elf_a, args.csv_a, fp_a, "--label", args.label_a])
    run([ROOT / "ppc_fingerprint.py", args.elf_b, args.csv_b, fp_b, "--label", args.label_b])
    run([ROOT / "ppc_compare.py", fp_a, fp_b, "--out", cmp])
    shutil.copyfile(cmp.with_name("compare_pairs.csv"), pairs)
    write_changed(cmp, changed)

    payload = json.loads(cmp.read_text(encoding="utf-8"))
    result = {
        "summary": payload["summary"],
        "builds": {
            "a": {"label": args.label_a, "elf": args.elf_a, "csv": args.csv_a},
            "b": {"label": args.label_b, "elf": args.elf_b, "csv": args.csv_b},
        },
        "outputs": {"compare": str(cmp), "pairs": str(pairs), "changed": str(changed)},
    }
    (out / "result.json").write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
