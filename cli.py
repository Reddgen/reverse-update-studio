#!/usr/bin/env python3
"""Reverse Update command-line interface."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT.parent / ".pylibs"))
sys.path.insert(0, str(ROOT / "studio"))


def cmd_version(_args):
    import server
    print(server.APP_VERSION)


def cmd_doctor(_args):
    import server
    payload = server.status_payload()
    print(json.dumps(payload, indent=2))


def cmd_inspect(args):
    from format_probe import probe_file
    out = []
    for raw in args.files:
        p = Path(raw).expanduser().resolve()
        if not p.exists():
            out.append({"path": str(p), "error": "file not found"})
            continue
        out.append({"path": str(p), **probe_file(p)})
    print(json.dumps(out, indent=2))


def cmd_serve(args):
    import server
    argv = ["server.py", "--host", args.host, "--port", str(args.port)]
    if args.pin:
        argv += ["--pin", args.pin]
    for root in args.allow_root:
        argv += ["--allow-root", root]
    if args.open:
        argv.append("--open")
    sys.argv = argv
    server.main()


def cmd_diff(args):
    import release_diff
    sys.argv = ["release_diff.py", "--a", args.a, "--b", args.b,
                "--label-a", args.label_a, "--label-b", args.label_b,
                "--outdir", args.outdir]
    release_diff.main()


def cmd_ppc_diff(args):
    import ppc_diff
    sys.argv = ["ppc_diff.py", "--elf-a", args.elf_a, "--csv-a", args.csv_a,
                "--elf-b", args.elf_b, "--csv-b", args.csv_b,
                "--label-a", args.label_a, "--label-b", args.label_b,
                "--outdir", args.outdir]
    ppc_diff.main()


def cmd_apk_diff(args):
    import apk_diff
    sys.argv = ["apk_diff.py", "--a", args.a, "--b", args.b,
                "--label-a", args.label_a, "--label-b", args.label_b,
                "--outdir", args.outdir]
    apk_diff.main()




def cmd_update_verify(args):
    import update_format as uf
    uf.verify_package(Path(args.package), Path(args.public), Path(args.master))
    print(json.dumps({"ok": True, **uf.inspect_package(Path(args.package))}, indent=2))


def cmd_update_apply(args):
    import update_format as uf
    r = uf.apply_package(Path(args.package), Path(args.target), Path(args.public), Path(args.master))
    print(json.dumps({"ok": r["ok"], "state": r["state"]}, indent=2))


def cmd_update_rollback(args):
    import update_format as uf
    r = uf.rollback_package(Path(args.target))
    print(json.dumps({"ok": r["ok"], "state": r["state"], "rolled_back_update": r["rolled_back_update"]}, indent=2))


def cmd_path_trace(args):
    from path_trace import PathTracer
    t = PathTracer(Path(args.db), Path(args.library) if args.library else None,
                   Path(args.model) if args.model else None)
    nodes = [x.strip() for x in args.nodes.split(",") if x.strip()]
    print(json.dumps(t.trace(nodes), indent=2))


def main():
    ap = argparse.ArgumentParser(prog="reverse-update", description="Reverse Update Studio CLI")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("version")
    p.set_defaults(func=cmd_version)

    p = sub.add_parser("doctor", help="show runtime/tool status")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("inspect", help="inspect one or more files")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("serve", help="start the Studio server")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--pin", default="")
    p.add_argument("--allow-root", action="append", default=[])
    p.add_argument("--open", action="store_true")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("diff", help="compare two PE/PDB builds")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--label-a", default="A")
    p.add_argument("--label-b", default="B")
    p.add_argument("--outdir", required=True)
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("ppc-diff", help="compare two GameCube ELF + Ghidra CSV sets")
    p.add_argument("--elf-a", required=True)
    p.add_argument("--csv-a", required=True)
    p.add_argument("--elf-b", required=True)
    p.add_argument("--csv-b", required=True)
    p.add_argument("--label-a", default="A")
    p.add_argument("--label-b", default="B")
    p.add_argument("--outdir", required=True)
    p.set_defaults(func=cmd_ppc_diff)

    p = sub.add_parser("apk-diff", help="compare two APK/DEX method sets")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)
    p.add_argument("--label-a", default="A")
    p.add_argument("--label-b", default="B")
    p.add_argument("--outdir", required=True)
    p.set_defaults(func=cmd_apk_diff)

    p = sub.add_parser("update-verify", help="verify an encrypted update package")
    p.add_argument("--package", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--master", required=True)
    p.set_defaults(func=cmd_update_verify)

    p = sub.add_parser("update-apply", help="verify and apply an update package")
    p.add_argument("--package", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--master", required=True)
    p.set_defaults(func=cmd_update_apply)

    p = sub.add_parser("update-rollback", help="roll back the last applied update")
    p.add_argument("--target", required=True)
    p.set_defaults(func=cmd_update_rollback)

    p = sub.add_parser("path-trace", help="trace a node path and score it")
    p.add_argument("--db", required=True)
    p.add_argument("--nodes", required=True)
    p.add_argument("--library", default="")
    p.add_argument("--model", default="")
    p.set_defaults(func=cmd_path_trace)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
