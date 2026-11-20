# Manual Translations

The application UI is currently **English only**. The manual can be translated
without changing the app.

| Language | Code | File | Status |
|---|---|---|---|
| English | `en` | [../../MANUAL.md](../../MANUAL.md) | complete |
| Spanish | `es` | `es.md` | wanted |
| French | `fr` | `fr.md` | wanted |
| Portuguese (Brazil) | `pt-BR` | `pt-BR.md` | wanted |
| German | `de` | `de.md` | wanted |
| Japanese | `ja` | `ja.md` | wanted |

The “wanted” list is a suggestion, not a commitment.

## Rules

- Translate meaning, not word-for-word.
- Keep commands, file names, buttons and menu names in English inside backticks.
- Do not translate code, paths, hashes or CLI flags.
- Keep warnings about DRM, malware, game data and authorisation.
- Label machine-assisted translations for review.
- Do not add legal claims that are not in the English text.

## Add a language

1. Copy [../../MANUAL.md](../../MANUAL.md) to `docs/manual/<code>.md`.
2. Add a header:

```markdown
> Translation: <language>. English is the authoritative version.
> Last synced with commit: <hash>
```

3. Translate.
4. Add the language to the table above.
5. Update [README.md](../../README.md) if it is reviewed.
6. Open a pull request.

## Terms that should usually stay English

```text
PE / PDB
ELF
Mach-O
APK / DEX
Ghidra
REA
LIEF
Capstone
PAK
sha256
CLI
API
PIN
```

See [GLOSSARY.md](GLOSSARY.md).
