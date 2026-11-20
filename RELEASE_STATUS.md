# Release Status

## P0

| Item | Status | Evidence |
|---|---|---|
| 1. Code signing | **Dev signed; public blocked** | `Reverse Update Studio.exe` has `CN=Reverse Update Studio Dev`; CA cert not available |
| 2. Clean-profile test | **Passed on second PC** | Windows 10 Pro 19045, non-admin, 15/15 checks, upgrade data preserved |
| 3. Single installer | **Done** | `Setup.cmd` is canonical; legacy EXEs moved to `reports/legacy/` |
| 4. Staged install + rollback | **Done** | `.new` stage, verify, atomic swap, `.old` restore on failure, 11,438 files |

## P0 evidence

```text
clean install:        verified 11438 files on second PC
upgrade:              data/probe.txt preserved
failed stage:         previous install preserved, .new removed
uninstall:            target removed
signing:              UnknownError (untrusted dev root)
```

Second PC: Windows 10 Pro 19045, standard user, 2026-11-19.

## Linux

- AppImage: **blocked** â€” no WSL, Docker, or Linux toolchain on this host.
- Fallback: `Reverse_Update_Studio_Linux_x86_64.tar.gz`
  - `install.sh`
  - `run.sh`
  - `linux/build_appimage.sh`
- Shell syntax: pass
- CLI version from extracted source: pass

Run `build_appimage.sh` on a Linux host to produce the AppImage.

## Not P0, still open

- Production update payload and remote update endpoint
- CSV formula injection
- Upload/archive quotas
- CA-issued signing certificate
- Real full-app update rollback


