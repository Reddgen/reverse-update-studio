# Contributing

Thanks for taking a look. This is a small project; clear reports and small
patches are more useful than large rewrites.

## Before you open a PR

- Search existing issues.
- For a security problem, follow [SECURITY.md](SECURITY.md), not a public issue.
- Do not attach game ROMs, ISOs, proprietary PDBs or personal data.
- Keep third-party binaries out of the repo.

## Development

```bash
python -m pip install -r studio/requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
```

Optional checks:

```bash
python cli.py version
python cli.py doctor
bash -n linux/install.sh
bash -n linux/build_appimage.sh
```

## Pull requests

- Keep the change focused.
- Add or update tests when behavior changes.
- Update docs/manual text when UI or CLI changes.
- Preserve third-party notices and license files.
- Do not add a dependency without its license and reason.

## Translations

See [docs/manual/README.md](docs/manual/README.md). Keep UI labels and CLI
commands in English inside backticks.

## Commit style

Short imperative subject, for example:

```text
Fix APK duplicate-method matching
Add Linux AppImage build
Document update rollback
```

## Code of conduct

Be direct, be kind, assume good faith. Harassment, doxxing, malware, piracy and
unauthorised access are not welcome.
