# Windows Install

## Recommended: Setup.cmd

The reliable install path is the portable ZIP plus **Setup.cmd**:

1. Download `Reverse_Update_Studio_Windows_Portable_0.2.0.zip`.
2. Extract it.
3. Double-click **Setup.cmd**.
4. Choose **Y** to start.

Setup:

- copies to `%LOCALAPPDATA%\ReverseUpdateStudio`;
- preserves `data\` on upgrade;
- creates Desktop and Start Menu shortcuts;
- creates an Uninstall shortcut;
- needs no admin rights, registry keys or `%TEMP%` writes.

Shortcuts:

```text
Desktop\Reverse Update Studio
Desktop\Uninstall Reverse Update Studio
Start Menu\Reverse Update Studio\
```

Uninstall:

```text
Start Menu â†’ Reverse Update Studio â†’ Uninstall Reverse Update Studio
```

## Single supported installer

`Setup.cmd` inside the portable ZIP is the **only supported installer**.

The old Inno Setup EXEs were moved to `reports/legacy/`. They are not part of the
recommended release because silent install depends on Start Menu and `HKCU`
uninstall-key access that this locked-down profile denies.

| Package | Contents | Size |
|---|---|---:|
| `Reverse_Update_Studio_Windows_Portable_0.2.0.zip` | full + Setup.cmd | 548,994,674 |
| `Reverse_Update_Studio_Windows_Portable_Lite_0.2.0.zip` | Lite + Setup.cmd | 73,927,120 |

## Signing

The launcher and package can be Authenticode-signed with
`tools/sign_release.ps1`. Without a CA-issued certificate the signature is a
development signature only; Windows will still warn.

Full portable SHA-256: `66f25843b3cb894d744df1baf5a735ac88f456cf5acdcc36b0131bcb0fef1fb5`

Lite portable SHA-256: `04c1b48101bd6f1c42810f42a3e40ee16a1213127ef8e9435b24384988b1fcd6`

## What gets installed

The full package installs the same tree as the full portable ZIP:

- `runtime\python` with Capstone, pefile, LIEF and androguard;
- `runtime\node`;
- Ghidra 12.1.4 + Temurin JDK 21.0.13;
- REA 6.5.0;
- Studio server, UI, CLI and tools.

Data is written under the install folder in `data\`.

## Build sources

- `Setup.cmd`, `Uninstall.cmd`, `Launch.cmd`
- `tools/install_shortcuts.ps1`
- Inno scripts: `build/ReverseUpdateStudio.iss`, `build/ReverseUpdateStudioLite.iss`

## Not included

- Code signing certificate. Packages are unsigned; SmartScreen may warn.
- Game files.
- Android/iOS packages.




