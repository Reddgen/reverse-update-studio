#!/usr/bin/env python3
"""Compare two PowerPC fingerprint sets."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pair(a, b, method, relation):
    return {
        "name_a": a["name"], "name_b": b["name"],
        "address_a": a["address"], "address_b": b["address"],
        "size_a": a["size"], "size_b": b["size"],
        "insn_a": a["insn_count"], "insn_b": b["insn_count"],
        "code_sha_a": a["code_sha"], "code_sha_b": b["code_sha"],
        "norm_sha_a": a["norm_sha"], "norm_sha_b": b["norm_sha"],
        "method": method, "relation": relation,
    }


def compare(A, B):
    pairs, removed, added = [], [], []
    a_left, b_left = set(range(len(A))), set(range(len(B)))

    def match_by(key, method, relation):
        ga, gb = defaultdict(list), defaultdict(list)
        for i in a_left:
            ga[A[i][key]].append(i)
        for i in b_left:
            gb[B[i][key]].append(i)
        for h in set(ga) & set(gb):
            aa = sorted(ga[h], key=lambda i: A[i]["address"])
            bb = sorted(gb[h], key=lambda i: B[i]["address"])
            for x, y in zip(aa, bb):
                pairs.append(pair(A[x], B[y], method, relation))
                a_left.discard(x); b_left.discard(y)

    match_by("code_sha", "exact", "identical")
    match_by("norm_sha", "normalized", "relocated")
    match_by("name", "name", "changed" if False else "same-name")

    # Size and instruction-count fallback for renamed functions.
    ga, gb = defaultdict(list), defaultdict(list)
    for i in a_left:
        ga[(A[i]["size"], A[i]["insn_count"])].append(i)
    for i in b_left:
        gb[(B[i]["size"], B[i]["insn_count"])].append(i)
    for h in set(ga) & set(gb):
        aa = sorted(ga[h], key=lambda i: A[i]["address"])
        bb = sorted(gb[h], key=lambda i: B[i]["address"])
        for x, y in zip(aa, bb):
            pairs.append(pair(A[x], B[y], "shape", "similar" if A[x]["norm_sha"] != B[y]["norm_sha"] else "relocated"))
            a_left.discard(x); b_left.discard(y)

    removed = [A[i] for i in sorted(a_left, key=lambda i: A[i]["address"])]
    added = [B[i] for i in sorted(b_left, key=lambda i: B[i]["address"])]
    rel = defaultdict(int)
    for p in pairs:
        rel[p["relation"]] += 1
    summary = {
        "functions_a": len(A), "functions_b": len(B),
        "matched": len(pairs), "identical": rel["identical"],
        "relocated": rel["relocated"], "same_name": rel["same-name"],
        "similar": rel["similar"], "changed": rel["same-name"] + rel["similar"],
        "removed": len(removed), "added": len(added),
        "match_rate": round(100 * len(pairs) / max(1, len(A)), 2),
    }
    return {"summary": summary, "pairs": pairs, "removed": removed, "added": added}


def write_csv(result, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name_a", "name_b", "address_a", "address_b", "size_a", "size_b",
                    "insn_a", "insn_b", "relation", "method"])
        for p in result["pairs"]:
            w.writerow([p[k] for k in ["name_a", "name_b", "address_a", "address_b", "size_a", "size_b",
                                       "insn_a", "insn_b", "relation", "method"]])
        for x in result["removed"]:
            w.writerow([x["name"], "", x["address"], "", x["size"], "", x["insn_count"], "", "removed", ""])
        for x in result["added"]:
            w.writerow(["", x["name"], "", x["address"], "", x["size"], "", x["insn_count"], "added", ""])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    A = load(args.a)["functions"]
    B = load(args.b)["functions"]
    result = compare(A, B)
    Path(args.out).write_text(json.dumps(result), encoding="utf-8")
    write_csv(result, args.out.replace(".json", "_pairs.csv"))
    print(json.dumps(result["summary"], indent=2))
