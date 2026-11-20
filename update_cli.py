#!/usr/bin/env python3
"""CLI for signed, AES-256-GCM encrypted update packages."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_format as uf


def main():
    ap = argparse.ArgumentParser(prog="update_cli")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("keygen")
    p.add_argument("--dir", required=True)

    p = sub.add_parser("create")
    p.add_argument("--payload", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--parent", default="")
    p.add_argument("--channel", default="stable")
    p.add_argument("--out", required=True)
    p.add_argument("--master", required=True)
    p.add_argument("--private", required=True)

    p = sub.add_parser("inspect")
    p.add_argument("package")

    p = sub.add_parser("verify")
    p.add_argument("package")
    p.add_argument("--public", required=True)
    p.add_argument("--master", required=True)

    p = sub.add_parser("rollback")
    p.add_argument("--target", required=True)

    p = sub.add_parser("apply")
    p.add_argument("package")
    p.add_argument("--target", required=True)
    p.add_argument("--public", required=True)
    p.add_argument("--master", required=True)
    p.add_argument("--allow-downgrade", action="store_true")

    args = ap.parse_args()
    if args.command == "keygen":
        d = Path(args.dir)
        out = uf.make_keys(d / "master.key", d / "signing-private.pem", d / "signing-public.pem")
        print(json.dumps(out, indent=2))
    elif args.command == "create":
        r = uf.create_package(Path(args.payload), args.version, Path(args.out),
                              Path(args.master), Path(args.private), args.parent, args.channel)
        print(json.dumps({"package": r["path"], **uf.inspect_package(Path(r["path"]))}, indent=2))
    elif args.command == "inspect":
        print(json.dumps(uf.inspect_package(Path(args.package)), indent=2))
    elif args.command == "verify":
        r = uf.verify_package(Path(args.package), Path(args.public), Path(args.master))
        print(json.dumps({"ok": True, **uf.inspect_package(Path(args.package))}, indent=2))
    elif args.command == "rollback":
        r = uf.rollback_package(Path(args.target))
        print(json.dumps({"ok": r["ok"], "state": r["state"], "rolled_back_update": r["rolled_back_update"]}, indent=2))
    elif args.command == "apply":
        r = uf.apply_package(Path(args.package), Path(args.target), Path(args.public),
                             Path(args.master), args.allow_downgrade)
        print(json.dumps({"ok": r["ok"], "state": r["state"]}, indent=2))


if __name__ == "__main__":
    main()
