# Update System

## What a package is

```text
update-<version>-<id>.rupkg   (ZIP)
├─ manifest.json
└─ payload.bin                AES-256-GCM ciphertext
```

Each package is independently verified:

1. `payload.bin` SHA-256 matches the manifest.
2. Manifest Ed25519 signature is valid against a trusted public key.
3. AES-256-GCM authentication succeeds.
4. Decrypted ZIP SHA-256 matches the manifest.
5. `parent` update id matches the installed chain.

Encryption and authenticity are separate checks. AES alone is not a signature.

## Keys

```text
update_cli.py keygen --dir keys
```

Produces:

```text
keys/master.key             32-byte AES master key (backend only)
keys/signing-private.pem    Ed25519 private key (backend only)
keys/signing-public.pem     trust anchor (publish this)
```

Per-package key:

```text
HKDF-SHA256(master, salt=update_id, info="reverse-update-payload-v1")
```

## Create

```text
python update_cli.py create ^
  --payload payload.zip ^
  --version 0.2.1 ^
  --parent "" ^
  --channel stable ^
  --out dist ^
  --master keys/master.key ^
  --private keys/signing-private.pem
```

The payload is a ZIP of files to overlay.

## Verify

```text
python update_cli.py verify dist/update-0.2.1-*.rupkg ^
  --public keys/signing-public.pem ^
  --master keys/master.key
```

## Apply

```text
python update_cli.py apply dist/update-0.2.1-*.rupkg ^
  --target install ^
  --public keys/signing-public.pem ^
  --master keys/master.key
```

Writes:

```text
install/update-state.json
```

State contains `version`, `update_id`, `parent`, `channel`, `installed_at`.

## Chain

```text
0.2.1 -> 0.2.2 -> 0.2.3
```

Each package's `parent` must equal the installed `update_id`.

## Rollback

Before each apply the engine snapshots every file it will overwrite and records
files it creates.

```text
python update_cli.py rollback --target install
```

Rollback:

- restores overwritten files from `.update-backups/<update_id>/`;
- deletes files created by the update;
- restores the previous `update-state.json`;
- can be repeated one step at a time back down the chain.

Tested: `0.2.3 → 0.2.2 → 0.2.1 → 0`.

## Tamper behavior

| Attack | Result |
|---|---|
| Flip ciphertext byte | `ciphertext hash mismatch` |
| Edit manifest | `manifest signature invalid` |
| Wrong master key | `AES-GCM authentication failed` |
| Wrong parent | `parent mismatch` |
| Wrong public key | `manifest signature invalid` |

## Demo

`updates_demo/` contains three packages and a **demo** key pair. The demo master
key is public; never use it for real releases.

## Production requirements

- Keep the master key and Ed25519 private key off the client.
- Verify in a separate process from apply.
- Stop the app before replacing its files.
- Keep a rollback snapshot.
- Add code signing for the installer itself.
- Add a channel/version policy before enabling automatic apply.
