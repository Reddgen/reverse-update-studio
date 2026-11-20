# Third-Party Notices and Credits

Reverse Update Studio's original integration code is licensed under MIT.
The project depends on and/or redistributes the components below under their
own licenses.

Full license texts are in [LICENSES/](LICENSES/). This file is a notice, not
legal advice.

## Runtime components

| Component | Version | License | Upstream |
|---|---|---|---|
| Python | 3.12.10 | PSF License | https://www.python.org/ |
| Node.js | 24.19.0 | MIT | https://nodejs.org/ |
| Ghidra | 12.1.4 | Apache-2.0 | https://github.com/NationalSecurityAgency/ghidra |
| Eclipse Temurin JDK | 21.0.13 | GPL-2.0 + Classpath Exception | https://adoptium.net/ |
| REA (`rea-agents`) | 6.5.0 | MIT | https://github.com/morluto/rea |
| RomPatcher.js | upstream | MIT | https://github.com/marcrobledo/RomPatcher.js |

## Python packages

| Package | License | Upstream |
|---|---|---|
| capstone | BSD-3-Clause | https://github.com/capstone-engine/capstone |
| pefile | MIT | https://github.com/erocarrera/pefile |
| LIEF | Apache-2.0 | https://github.com/lief-project/LIEF |
| androguard | Apache-2.0 | https://github.com/androguard/androguard |
| cryptography | Apache-2.0 / BSD | https://github.com/pyca/cryptography |

Transitive Python dependencies carry their own licenses. Before shipping a
full portable bundle, generate a complete inventory, for example with
`pip-licenses`, and keep the package metadata.

## Build-only tools

These are used to build packages but are not part of the application runtime:

| Tool | License | Upstream |
|---|---|---|
| 7-Zip | LGPL | https://www.7-zip.org/ |
| Inno Setup | Inno Setup License | https://jrsoftware.org/isinfo.php |

## Testing acknowledgements

The project was validated against public builds. These projects and their
developers deserve credit for the software used as test material:

- **OpenRCT2** — https://github.com/OpenRCT2/OpenRCT2
- **0 A.D.** — https://play0ad.com/ and https://gitea.wildfiregames.com/0ad/0ad
- **Ghidra** — function extraction and decompiler workflow
- **Metroid Prime** — GameCube/PPC control experiments

No game ROMs, ISOs, executables, PDBs, or proprietary game data are included in
this repository or its source release.

## Research references

The packaging and remote-access design was informed by publicly documented
tools such as T3 Code and LIEF. No code from T3 Code is included. LIEF is a
runtime dependency and is credited above.

## Trademarks

Ghidra, Node.js, Python, Eclipse Temurin, and other names are trademarks of
their respective owners. Use here is descriptive and does not imply endorsement.

## Original code

The MIT license applies only to original code in this repository. It does not
relicense any third-party component, trademark, or game asset.
