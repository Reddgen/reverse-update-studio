# Changelog

## 0.2.0 — 2026-11-19

### Added

- PE/PDB Release Diff with source file/line mapping.
- Source Root and Open-in-editor flow.
- APK method diff with normalized DEX instructions.
- PPC ELF + Ghidra CSV comparison.
- Format inspection for ELF, Mach-O, APK, IPA, JAR, WASM and archives.
- Trace view, path library, stable puzzle IDs and priority model.
- AES-256-GCM + Ed25519 update packages with chained apply and rollback.
- `reverse-update` CLI.
- Windows portable install (`Setup.cmd`), staged copy, verification and rollback.
- Desktop and Start Menu shortcuts; Uninstall entry.
- Start here tutorial and full manual.
- Linux source tarball and AppImage build workflow.
- MIT license, third-party notices and license texts.
- CI on Windows and Ubuntu; Windows launcher workflow.

### Known gaps

- CA/SignPath signing not complete.
- Windows release ZIP is not signed.
- AppImage runtime untested on real Linux.
- APK native `.so` diff not implemented.
- ELF x86-64 and Mach-O diff not implemented.
- Upload/archive quotas and CSV formula-injection guard not implemented.
- Full-app update payload not tested.
- Keep-data uninstall path untested.

## 0.1.0 — earlier

- Initial local web UI and analysis experiments.
- OpenRCT2 and 0 A.D. benchmark work.
- GameCube/PPC matcher prototype.
