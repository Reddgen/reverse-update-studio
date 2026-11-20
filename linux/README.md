# Reverse Update Studio — Linux

## Portable install (source-based)

This tarball is the Linux fallback until a real AppImage is built on a Linux host.

```bash
tar xzf Reverse_Update_Studio_Linux_x86_64.tar.gz
cd ReverseUpdateStudio
./install.sh
./run.sh
```

Requirements:

- Linux x86-64
- Python 3.10+
- `python3-venv`
- network access for Python packages on first install

The installer creates `.venv` and installs:

```text
capstone
pefile
lief
androguard
```

CLI:

```bash
~/.local/bin/reverse-update version
~/.local/bin/reverse-update doctor
~/.local/bin/reverse-update inspect file.apk
~/.local/bin/reverse-update path-trace --db ~/.local/share/ru/traces.sqlite \
  --nodes "LoadConfig,ResolvePath,ParseXML,ApplyConfig" \
  --library path_library.json --model path_model.json
```

## Optional engines

Python analysis works without Ghidra/REA.

For PPC/REA features, set:

```bash
export JAVA_HOME=/usr/lib/jvm/temurin-21
export GHIDRA_INSTALL_DIR=/opt/ghidra_12.1.4_PUBLIC
export RU_NODE=/usr/bin/node
```

The dashboard will show missing tools until these are set.

## AppImage

A Linux AppImage cannot be built on Windows. On a Linux host:

```bash
./linux/build_appimage.sh
```

That script requires:

- `appimagetool`
- `patchelf`
- `python3`

It builds a **source-based AppImage** that uses the system `python3` at runtime
and runs `studio/server.py`. It does not bundle Ghidra/JDK.

A fully self-contained AppImage needs bundled Linux Python, Node, Ghidra and
JDK; that build still has to be produced on Linux.

## Status

- Linux portable source package: built and inspected
- Linux shell scripts: syntax-checked with Git Bash
- AppImage: blocked on this host (no WSL, Docker, or Linux toolchain)
