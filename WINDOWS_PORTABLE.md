# Windows Portable Build

## v0.2.1

| File | Size | SHA-256 |
|---|---:|---|
| `Reverse_Update_Studio_Windows_Portable_0.2.1.zip` | 549,065,214 | `39e59bd540b0cc173e3c9419a28064186ff1a793aefc5af9f3d1fa8b4ad6b885` |

No Lite package is published for v0.2.1.

## Install

1. Extract the ZIP.
2. Run **Setup.cmd**.
3. Choose **Y**.

The shortcut launches `Reverse Update Studio.exe`, which starts `Launch.cmd`.
The fallback is `Launch.cmd` directly.

## What is inside

- `studio/` server and browser UI
- `runtime/python` with Capstone, pefile, LIEF, androguard
- `runtime/node`
- Ghidra 12.1.4
- Temurin JDK 21
- REA 6.5.0
- CLI, tools, tests
- `LICENSES/` and third-party notices
- `MANUAL.md`, `TUTORIAL.md` and technical docs

## Verify

Each package contains `bundle-manifest.json`. Setup verifies it during staging.

```powershell
Get-FileHash .\Reverse_Update_Studio_Windows_Portable_0.2.1.zip -Algorithm SHA256
```

Expected:

```text
39e59bd540b0cc173e3c9419a28064186ff1a793aefc5af9f3d1fa8b4ad6b885
```

## Known gaps

- Launcher unsigned.
- No CA/SignPath signature yet.
- Full-app update payload not tested.
- GameCube/PPC is experimental.
