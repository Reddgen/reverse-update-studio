#!/usr/bin/env python3
"""Verify a portable install against bundle-manifest.json."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    args = ap.parse_args()
    base = Path(args.base).resolve()
    mf = base / "bundle-manifest.json"
    if not mf.exists():
        print(f"manifest missing: {mf}")
        sys.exit(1)
    payload = json.loads(mf.read_text(encoding="utf-8"))
    bad = []
    for item in payload.get("files", []):
        p = base / item["path"]
        if not p.is_file():
            bad.append(f"missing {item['path']}")
        elif p.stat().st_size != item["size"] or sha(p) != item["sha256"]:
            bad.append(f"changed {item['path']}")
    if bad:
        print(f"{len(bad)} problem(s):")
        for b in bad[:20]:
            print(" ", b)
        sys.exit(1)
    print(f"verified {len(payload.get('files', []))} files")


if __name__ == "__main__":
    main()
