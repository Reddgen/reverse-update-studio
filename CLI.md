# Reverse Update CLI

The CLI exposes the engine without the browser.

```text
reverse-update version
reverse-update doctor
reverse-update inspect FILE [FILE ...]
reverse-update serve --host 127.0.0.1 --port 8765
reverse-update diff --a BUILDA --b BUILDB --outdir OUT
reverse-update ppc-diff --elf-a A.elf --csv-a A.csv --elf-b B.elf --csv-b B.csv --outdir OUT
reverse-update apk-diff --a old.apk --b new.apk --outdir OUT
```

In the portable build use:

```text
reverse-update.cmd ...
```

or:

```text
runtime\python\python.exe cli.py ...
```

`doctor` shows tool readiness. `inspect` prints JSON with format details,
including APK DEX class/method counts when LIEF is available.
