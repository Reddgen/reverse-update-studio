#!/usr/bin/env python3
"""Generate bundle-manifest.json for a portable install tree."""
import argparse
import hashlib
import json
from pathlib import Path

SKIP_DIRS = {"data", "__pycache__", "work"}
SKIP_NAMES = {"bundle-manifest.json"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--version", default="0.2.0")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    base = Path(args.base).resolve()
    out = Path(args.out) if args.out else base / "bundle-manifest.json"
    files = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(base)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.name in SKIP_NAMES:
            continue
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        files.append({"path": rel.as_posix(), "size": p.stat().st_size, "sha256": h.hexdigest()})
    payload = {"version": args.version, "files": files}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"{out} {len(files)} files {out.stat().st_size} bytes")


if __name__ == "__main__":
    main()
