# Format Support

## Function-level diff

| Format | Inspect | Function diff | Notes |
|---|---|---|---|
| PE / EXE / DLL + PDB | yes | **yes** | Release Diff |
| GameCube PPC ELF + Ghidra CSV | yes | **yes, experimental** | PPC Diff |
| Linux ELF x86-64 | yes | no | needs DWARF/symbol diff adapter |
| Mach-O | yes | no | inspect only |
| APK / DEX | container + **class/method inventory** | **yes — normalized DEX method diff** | LIEF + androguard |
| IPA | container only | no | Mach-O inside not parsed |
| Java JAR / class | container + class count | no | needs class-file adapter |
| WebAssembly | sections | no | inspect only |
| ZIP / archives | entries | no | container |
| Patches | IPS/UPS/BPS/PPF/xdelta | not applicable | patch apply/create |

## Inspection details

### ELF
- class, endian, type, machine, entry
- program/section counts
- section names
- symtab / dynsym / debug-info / build-id flags

### Mach-O
- 32/64-bit, CPU, load command count
- segments
- symbol count
- UUID

### APK
- entry count
- DEX file count
- native library count and ABIs
- manifest presence

### IPA
- ZIP entry count
- Payload/app entry counts

### Java JAR
- entry count
- class-file count

### APK method diff
- compares class, method name and prototype
- normalizes register and pool references with androguard instructions
- removes branch/payload offsets that shift between builds
- reports identical, changed, removed and added methods

### WebAssembly
- version and section IDs

## Limits

- Format recognition is not the same as function-level comparison.
- APK/IPA are archives; code analysis requires DEX/Mach-O adapters.
- ELF x86-64 diff needs symbols or DWARF plus an x86 fingerprint adapter.
- Mach-O has symbols in some builds, but no matcher is wired yet.
- No execution of targets.

