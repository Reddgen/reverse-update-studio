# Start Here

## Install

1. Download `Reverse_Update_Studio_Windows_Portable_0.2.0.zip`.
2. Extract it anywhere.
3. Double-click **Setup.cmd**.
4. Choose **Y** to start.

Setup copies the app to:

```text
%LOCALAPPDATA%\ReverseUpdateStudio
```

It creates:

- Desktop → **Reverse Update Studio**
- Desktop → **Uninstall Reverse Update Studio**
- Start Menu → **Reverse Update Studio**
- Start Menu → **Uninstall Reverse Update Studio**

No admin rights, registry keys or `%TEMP%` writes are required.

## First launch

The dashboard should show:

```text
ready
Ghidra ready
REA ready
Python 3.12
```

If it does, the engine is installed correctly.

Open **Start here** in the app for the same tutorial.

## Path 1 — inspect a file

**Analyze → Inspect a file**

Supported:

- PE / EXE / DLL
- ELF
- Mach-O
- APK (classes, methods)
- IPA (container)
- JAR / class
- WebAssembly
- ZIP / archives

You get format, size, SHA-256, capabilities and structure.

## Path 2 — compare two Windows builds

**Analyze → Compare two builds**

```text
Build A: folder containing old EXE + PDB
Build B: folder containing new EXE + PDB
```

Press **Compare builds**.

Expected result:

```text
matched / changed / removed / added
```

Then scroll to **Changed functions**.

## Path 3 — open the source line

Set:

```text
Source root: C:\src\0ad
```

Use the folder that contains `source`, not `source` itself.

Click **Open** beside Source A or Source B.

- VS Code is used when installed.
- Otherwise the default editor opens.

## Path 4 — compare two APKs

**Analyze → Compare two APKs**

```text
APK A: old.apk
APK B: new.apk
```

APK Diff reports:

- matched methods
- identical methods
- changed methods
- removed
- added

The same APK twice must give **100% identical**.

## Path 5 — GameCube / PowerPC

**Analyze → Compare two GameCube builds**

Each side needs:

- an ELF
- a Ghidra function CSV

The same ELF twice is a valid control.

This is experimental. It is not a playable port.

## Jobs and exports

Every comparison produces:

- changed CSV
- full JSON

Open **Jobs** to see history. Results persist across restarts.

## Troubleshooting

| Problem | Fix |
|---|---|
| Dashboard says not ready | Reopen the desktop shortcut; wait 5 seconds |
| PDB missing | Put matching PDB next to each EXE |
| Open does nothing | Set Source root to the folder containing `source` |
| Port 8765 busy | Close the old window, reopen the shortcut |
| APK diff slow | Large APKs can take 1–3 minutes |
| Uninstall | Start Menu → Uninstall Reverse Update Studio |

## Remove

Use:

```text
Start Menu → Reverse Update Studio → Uninstall Reverse Update Studio
```

or:

```text
Desktop → Uninstall Reverse Update Studio
```

This removes the app, shortcuts and data.
