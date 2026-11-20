#!/usr/bin/env python3
"""CLI for the path library, puzzle IDs and priority model."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / ".pylibs"))
from path_trace import PathTracer, train


def main():
    ap = argparse.ArgumentParser(prog="path_cli")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.add_argument("--db", required=True)
    p.add_argument("--library", default="")

    p = sub.add_parser("trace")
    p.add_argument("--db", required=True)
    p.add_argument("--nodes", required=True, help="comma-separated node labels")
    p.add_argument("--library", default="")
    p.add_argument("--model", default="")

    p = sub.add_parser("puzzles")
    p.add_argument("--db", required=True)

    p = sub.add_parser("traces")
    p.add_argument("--db", required=True)

    p = sub.add_parser("train")
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.command == "init":
        t = PathTracer(Path(args.db), Path(args.library) if args.library else None)
        print(json.dumps({"db": args.db, "library": args.library}, indent=2))
    elif args.command == "trace":
        t = PathTracer(Path(args.db), Path(args.library) if args.library else None,
                       Path(args.model) if args.model else None)
        nodes = [x.strip() for x in args.nodes.split(",") if x.strip()]
        print(json.dumps(t.trace(nodes), indent=2))
    elif args.command == "puzzles":
        t = PathTracer(Path(args.db))
        print(json.dumps(t.puzzles(), indent=2))
    elif args.command == "traces":
        t = PathTracer(Path(args.db))
        print(json.dumps(t.traces(), indent=2))
    elif args.command == "train":
        rows = [json.loads(x) for x in Path(args.data).read_text().splitlines() if x.strip()]
        model = train(rows)
        Path(args.out).write_text(json.dumps(model, indent=2))
        print(json.dumps(model, indent=2))


if __name__ == "__main__":
    main()
