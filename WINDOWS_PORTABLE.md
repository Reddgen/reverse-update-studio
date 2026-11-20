# Windows Portable Build

Two portable packages:

| Package | Contents | Size |
|---|---|---:|
| `Reverse_Update_Studio_Windows_Portable_0.2.0.zip` | full: Ghidra + JDK 21 + REA + Studio | 665,806,494 bytes |
| `Reverse_Update_Studio_Windows_Portable_Lite_0.2.0.zip` | Lite: Studio + embedded Python + Node, no Ghidra/REA | 130,581,479 bytes |

Full SHA-256: `85fc960afa891c194fb964f19d1419d471bfb6b1b95d4d7e7005401fb09e77c9`

Lite SHA-256: `087a2a872c98266495a41cc3c902cff7f6b13e0fff1a0cb5a07f197fdca14523`

The full package is the one with the GameCube Ghidra workflow ready out of the box.

Extract it and double-click:

```text
Reverse Update Studio.exe
```

or, if the launcher is blocked:

```text
start.cmd
```

## What is inside

- embedded Python 3.12.10 with Capstone, pefile and LIEF;
- embedded Node.js 24 for the patch CLI;
- **Ghidra 12.1.4 + Temurin JDK 21.0.13**;
- **REA 6.5.0** and its Node dependencies;
- Studio server and responsive UI;
- **persistent job history across restarts**;
- **source file/line mapping** for PE/PDB diffs;
- **Source Root + Open in VS Code** for changed functions;
- **Trace** view with path library, puzzle IDs and priority;
- **signed/encrypted update package CLI**;
- **format probe**: ELF, Mach-O, APK, IPA, JAR, WASM and archives;
- **APK method diff** with normalized DEX instructions;
- **native Browse dialog** for Windows path fields;
- optional **PIN gate** for LAN mode;
- PE/PDB Release Diff;
- PPC/ELF Diff and function Inspector;
- bundled tools, sample Ghidra CSV and top-20 pseudocode;
- no game files, no Python installation required.

## Data

Jobs and uploads are stored in `data\` inside the extracted folder.

## Tested

- embedded Python imports Capstone and pefile;
- `studio/server.py` starts under the bundled runtime;
- bundled Ghidra headless: **12,152 Metroid functions**;
- PPC self-control through the bundled server: **12,142 matched, 0 changed**;
- Node and REA are detected;
- the launcher starts the server and opens the Studio window in Edge app mode.

## Not included

- code signing (SmartScreen may warn);
- Android/iOS installers;
- game data.

## Limits

The bundle is a local web app in a portable desktop shell. It is not a native
port and does not execute game binaries.














