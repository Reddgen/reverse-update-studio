# Windows Install

## Supported path

Use the portable ZIP plus **Setup.cmd**. There is no supported Inno Setup EXE in
this release.

1. Download `Reverse_Update_Studio_Windows_Portable_0.2.1.zip`.
2. Verify its SHA-256.
3. Extract it.
4. Double-click **Setup.cmd**.
5. Choose **Y**.

Setup:

- copies to `%LOCALAPPDATA%\ReverseUpdateStudio`;
- preserves `data\` on upgrade;
- creates Desktop and Start Menu shortcuts;
- points the app shortcut at `Reverse Update Studio.exe`;
- creates an Uninstall shortcut;
- requires no admin rights or registry keys.

Shortcuts:

```text
Desktop\Reverse Update Studio
Desktop\Uninstall Reverse Update Studio
Start Menu\Reverse Update Studio\
```

Uninstall:

```text
Start Menu -> Reverse Update Studio -> Uninstall Reverse Update Studio
```

## Package

| File | Size | SHA-256 |
|---|---:|---|
| `Reverse_Update_Studio_Windows_Portable_0.2.1.zip` | 549,065,214 | `39e59bd540b0cc173e3c9419a28064186ff1a793aefc5af9f3d1fa8b4ad6b885` |

## Signing

The launcher is **not CA-signed**. A development self-signed certificate can be
used for testing, but Windows will warn.

See [SIGNING.md](SIGNING.md).

## Contents

- Studio server and browser UI
- Python 3.12 with Capstone, pefile, LIEF, androguard
- Node.js 24
- Ghidra 12.1.4 and Temurin JDK 21
- REA 6.5.0
- CLI, tools, tests and docs
- `LICENSES/`, `THIRD_PARTY_NOTICES.md`, `ACKNOWLEDGEMENTS.md`, `ETHICS.md`
- `MANUAL.md`, tutorial and format/update/path docs

No game ROMs, ISOs, PDBs or proprietary binaries are included.

## Removing the legacy EXEs

Older Inno Setup EXEs were moved out of the release. They are not part of the
v0.2.1 download.
