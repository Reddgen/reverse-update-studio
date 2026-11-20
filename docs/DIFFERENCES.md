# How This Is Different

One sentence:

> It is a **local release-diff workbench**: compare two compiled builds, match
> functions, point to source, mark unknown paths, and verify updates.

It is not a new matching algorithm. The difference is the **workflow and
accessibility**, not magic.

## vs source diff (`git diff`)

| | Source diff | This |
|---|---|---|
| Input | source text | compiled builds |
| Needs source | yes | no |
| Output | line changes | function changes |
| Source mapping | native | from PDB/debug info |
| APK/PPC | no | yes |

## vs Ghidra / IDA

| | Ghidra / IDA | This |
|---|---|---|
| Main use | interactive RE | automated release comparison |
| Learning curve | high | lower |
| Function diff | manual/plugin | built in |
| Source mapping | manual/plugin | built in |
| Deep decompilation | much deeper | uses Ghidra for PPC |

Ghidra and IDA are more powerful for deep analysis. This is narrower: compare
two releases and show what changed.

## vs BinDiff / Diaphora

| | BinDiff / Diaphora | This |
|---|---|---|
| Matching maturity | high | simpler |
| Platforms | IDA/Ghidra plugins | standalone local app |
| Source line | limited | PDB mapping |
| APK methods | no | yes |
| PPC CSV | no | yes |
| Path/puzzle IDs | no | yes |
| Update verification | no | yes |

BinDiff and Diaphora are better at advanced function matching. This is easier to
run and connects more of the workflow.

## vs VirusTotal

| | VirusTotal | This |
|---|---|---|
| Purpose | reputation/scanning | version comparison |
| Uploads files | yes | local by default |
| Shows changed functions | no | yes |

VirusTotal answers “is this known bad?” This answers “what changed between these
builds?”

## vs byte diff (`bsdiff`, `xdelta`, `radiff2`)

Those are byte-level diff/patch tools.

This is function-level:

```text
bsdiff:  bytes 1000–1200 changed
this:    CNetServerWorker::SetupUPnP changed, source line 267
```

The patch formats are still supported separately.

## vs APK diff tools

`jadx` and `apktool` focus on decompiled code and resources.

This compares **DEX methods** with normalized instructions:

- no Java source;
- no resource diff;
- method-level and faster.

## vs update frameworks (TUF and similar)

TUF is a mature update-security framework.

This has a small update engine:

- AES-256-GCM payload;
- Ed25519 manifest;
- chained apply/rollback;
- independent verification.

It is not a replacement for TUF in a large production system.

## What is different here

1. Local-first: files are not uploaded by default.
2. One UI for Windows PE/PDB, Android APK and GameCube/PPC.
3. Function → source line → **Open** in one flow.
4. Unknown paths get stable puzzle IDs and a priority score.
5. Update packages are verifiable in the same app.
6. CLI + browser + phone/tablet UI.
7. No scripting required for the common case.

## What is not different

- Matching uses standard ideas: symbols, code fingerprints, normalized
  instructions.
- Ghidra/IDA are deeper for interactive analysis.
- BinDiff/Diaphora are more mature at function matching.
- VirusTotal has a larger reputation database.
- TUF is more mature for update security.

## Who it is for

- People comparing public/open-source builds with PDBs.
- Maintainers checking release changes.
- Modders working within the EULA.
- Students learning binary structure.
- Security teams doing authorized triage.

## Who it is not for

- Unauthorized reverse engineering.
- DRM, anti-cheat or licence bypass.
- Malware development.
- Cheating.
- Redistribution of game ROMs or proprietary binaries.

See [ETHICS.md](ETHICS.md).

## Positioning

```text
Not “the best reverse-engineering tool.”
A practical local workbench for comparing releases
and following changes to source, paths and updates.
```

The difference is integration and accessibility.
