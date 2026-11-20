# Reverse Update Studio

Local-first binary release analysis for Windows builds, APKs and PowerPC ELF
files. Compare two releases, find changed functions, map them to source lines,
and trace unknown paths.

## Why this exists

A personal project by **Reddgen** — a regular tinkerer and music maker who
wanted to make release changes visible without a lab or a large team. Read
[How this started](ORIGIN.md).

Music: [yelledbox.com](https://yelledbox.com)
## What it does

- **PE/PDB Release Diff** â€” compare two Windows builds; matched, changed,
  removed, added functions.
- **Source mapping** â€” PDB file/line plus optional *Open in editor*.
- **APK Diff** â€” compare DEX classes/methods with normalized instructions.
- **PPC Diff** â€” GameCube ELF + Ghidra CSV comparison.
- **Inspect** â€” PE, ELF, Mach-O, APK, IPA, JAR, WASM, ZIP.
- **Trace** â€” match a path against a library; unknown runs get deterministic
  puzzle IDs and a priority score.
- **Updates** â€” AES-256-GCM payloads, Ed25519 manifests, chained apply/rollback.

It does **not** run games, emulate consoles, or turn a game into a native app.

## Download

Releases: https://github.com/Reddgen/reverse-update-studio/releases/tag/v0.2.0

| Platform | File |
|---|---|
| Windows | `Reverse_Update_Studio_Windows_Portable_0.2.0.zip` |
| Linux | `Reverse_Update_Studio-x86_64.AppImage` |
| Source | `Reverse_Update_Studio_Source_v0.2.0.zip` |

Verify with the accompanying `.sha256` files.
## Windows

Download the portable ZIP from Releases, extract it and run:

```text
Setup.cmd
```

Setup is per-user and installs to:

```text
%LOCALAPPDATA%\ReverseUpdateStudio
```

It creates Desktop and Start Menu entries and an uninstaller.

The current release is development-signed only. Windows may show an unknown
publisher warning. See [SIGNING.md](SIGNING.md).

## Run from source

Requirements:

- Python 3.10+
- `pip install -r studio/requirements.txt`

```bash
python cli.py version
python cli.py doctor
python cli.py serve --port 8765 --open
```

Then open:

```text
http://127.0.0.1:8765/
```

## CLI

```text
reverse-update inspect file.apk
reverse-update diff --a BUILDA --b BUILDB --outdir OUT
reverse-update ppc-diff --elf-a A.elf --csv-a A.csv --elf-b B.elf --csv-b B.csv --outdir OUT
reverse-update apk-diff --a old.apk --b new.apk --outdir OUT
reverse-update path-trace --db traces.sqlite --nodes "LoadConfig,ResolvePath"
reverse-update update-verify --package update.rupkg --public pub.pem --master master.key
reverse-update update-apply --package update.rupkg --target install --public pub.pem --master master.key
reverse-update update-rollback --target install
```

## Linux

A source-based tarball and AppImage build script are in
[linux/](linux/). The AppImage must be built on Linux:

```bash
./linux/build_appimage.sh
```

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The APK smoke test needs a real APK:

```bash
python tests/smoke.py --base http://127.0.0.1:8765 --apk-a app.apk --apk-b app.apk
```

## Documentation

- [Full step-by-step manual](MANUAL.md)\n- [Manual translations](docs/manual/README.md)\n- [Tutorial](TUTORIAL.md)
- [CLI](CLI.md)
- [Format support](FORMAT_SUPPORT.md)
- [Update system](UPDATE_SYSTEM.md)
- [Path tracing](PATH_TRACE.md)
- [Signing](SIGNING.md)\n- [SignPath application notes](SIGNPATH.md)
- [Release status](RELEASE_STATUS.md)\n- [Acknowledgements](ACKNOWLEDGEMENTS.md)\n- [Acceptable use and ethics](ETHICS.md)

## Security

- Binds to `127.0.0.1` by default.
- LAN mode requires a PIN.
- No files are uploaded unless you use the Upload button.
- Update payloads are encrypted and manifests are signed.
- Do not use the demo keys from old packages in production.

Report security issues privately before opening a public issue.

## Support

If this project saves you time:

https://buymeacoffee.com/yelledbox

Donations are optional. They do not buy priority support or change the MIT
license.
## License

MIT for original code. See [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

No game data, ROMs, ISOs, PDBs, or proprietary binaries are included.







