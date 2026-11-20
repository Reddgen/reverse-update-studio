"""Signed, AES-256-GCM encrypted update packages.

Package layout (zip):
  manifest.json   canonical metadata, Ed25519 signature
  payload.bin     AES-256-GCM ciphertext

The AES key is derived from a backend master key and the update id with
HKDF-SHA256.  The manifest is signed separately so encryption and authenticity
are independent checks.
"""
import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".pylibs"))

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

FORMAT = "reverse-update-package-v1"
HKDF_INFO = b"reverse-update-payload-v1"
MANIFEST = "manifest.json"
PAYLOAD = "payload.bin"


def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_master_key(path: Path) -> bytes:
    raw = Path(path).read_bytes()
    if len(raw) != 32:
        raise ValueError("master key must be exactly 32 bytes")
    return raw


def derive_key(master: bytes, update_id: str) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=update_id.encode("ascii"),
                info=HKDF_INFO).derive(master)


def make_keys(master_path: Path, private_path: Path, public_path: Path):
    master_path.parent.mkdir(parents=True, exist_ok=True)
    master_path.write_bytes(os.urandom(32))
    key = Ed25519PrivateKey.generate()
    private_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    public_path.write_bytes(key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    return {"master": str(master_path), "private": str(private_path), "public": str(public_path)}


def load_private(path: Path) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(Path(path).read_bytes(), password=None)


def load_public(path: Path) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(Path(path).read_bytes())


def public_b64(key: Ed25519PublicKey) -> str:
    return b64e(key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def verify_signature(manifest: dict, public_key: Ed25519PublicKey) -> None:
    sig = manifest.get("signature", {})
    if sig.get("alg") != "Ed25519":
        raise ValueError("unsupported signature algorithm")
    body = {k: v for k, v in manifest.items() if k != "signature"}
    try:
        public_key.verify(b64d(sig["sig"]), canonical(body))
    except Exception as e:
        raise ValueError(f"manifest signature invalid: {e}") from e


def create_package(payload_zip: Path, version: str, outdir: Path, master_key: Path,
                   private_key: Path, parent: str = "", channel: str = "stable") -> dict:
    payload = Path(payload_zip).read_bytes()
    update_id = uuid.uuid4().hex
    nonce = os.urandom(12)
    aad = f"{FORMAT}|{update_id}|{version}|{parent}".encode("utf-8")
    key = derive_key(load_master_key(master_key), update_id)
    cipher = AESGCM(key).encrypt(nonce, payload, aad)
    manifest = {
        "format": FORMAT,
        "update_id": update_id,
        "version": version,
        "parent": parent,
        "channel": channel,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "payload": {
            "name": Path(payload_zip).name,
            "size": len(payload),
            "sha256": sha256(payload),
            "cipher_sha256": sha256(cipher),
        },
        "crypto": {
            "alg": "AES-256-GCM",
            "nonce": b64e(nonce),
            "aad": aad.decode("utf-8"),
            "kdf": "HKDF-SHA256",
        },
        "signature": {
            "alg": "Ed25519",
            "public_key": public_b64(load_private(private_key).public_key()),
        },
    }
    body = {k: v for k, v in manifest.items() if k != "signature"}
    manifest["signature"]["sig"] = b64e(load_private(private_key).sign(canonical(body)))
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"update-{version}-{update_id}.rupkg"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, json.dumps(manifest, indent=2))
        z.writestr(PAYLOAD, cipher)
    return {"path": str(out), "manifest": manifest}


def read_package(path: Path):
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read(MANIFEST))
        cipher = z.read(PAYLOAD)
    return manifest, cipher


def verify_package(path: Path, public_key: Path, master_key: Path) -> dict:
    manifest, cipher = read_package(path)
    if manifest.get("format") != FORMAT:
        raise ValueError("unsupported package format")
    if sha256(cipher) != manifest["payload"]["cipher_sha256"]:
        raise ValueError("ciphertext hash mismatch")
    verify_signature(manifest, load_public(public_key))
    key = derive_key(load_master_key(master_key), manifest["update_id"])
    try:
        payload = AESGCM(key).decrypt(b64d(manifest["crypto"]["nonce"]), cipher,
                                      manifest["crypto"]["aad"].encode("utf-8"))
    except Exception as e:
        raise ValueError(f"AES-GCM authentication failed: {e}") from e
    if sha256(payload) != manifest["payload"]["sha256"]:
        raise ValueError("payload hash mismatch")
    return {"manifest": manifest, "payload": payload}


def safe_extract_zip(data: bytes, target: Path):
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as z:
        for info in z.infolist():
            name = info.filename
            p = (target / name).resolve()
            if not str(p).startswith(str(target.resolve()) + os.sep) and p != target.resolve():
                raise ValueError(f"unsafe path in payload: {name}")
            if info.is_dir():
                p.mkdir(parents=True, exist_ok=True)
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, p.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def apply_package(path: Path, target: Path, public_key: Path, master_key: Path,
                  allow_downgrade: bool = False) -> dict:
    verified = verify_package(path, public_key, master_key)
    m = verified["manifest"]
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    state_path = target / "update-state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"version": "0", "update_id": ""}
    if m["parent"] and m["parent"] != state.get("update_id"):
        raise ValueError(f"parent mismatch: package expects {m['parent']}, installed {state.get('update_id')}")
    if not allow_downgrade and m["version"] == state.get("version"):
        raise ValueError("version already installed")
    staging = target / ".update-staging"
    if staging.exists():
        shutil.rmtree(staging)
    safe_extract_zip(verified["payload"], staging)
    backup_rel = Path(".update-backups") / m["update_id"]
    backup_root = target / backup_rel
    if backup_root.exists():
        shutil.rmtree(backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)
    created, overwritten = [], []
    previous_state = dict(state)
    try:
        for p in staging.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(staging)
            if rel.parts and rel.parts[0].startswith(".update-"):
                continue  # reserved control paths
            dst = target / rel
            if dst.exists():
                bdst = backup_root / rel
                bdst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bdst)
                overwritten.append(rel.as_posix())
            else:
                created.append(rel.as_posix())
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
        shutil.rmtree(staging)
        state = {"version": m["version"], "update_id": m["update_id"],
                 "installed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "parent": m["parent"], "channel": m["channel"],
                 "rollback": {"backup": backup_rel.as_posix(),
                              "created": created, "overwritten": overwritten,
                              "previous_state": previous_state}}
        tmp = state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        os.replace(tmp, state_path)
    except Exception:
        # Best-effort restore of files copied before the failure.
        for rel in overwritten:
            b = backup_root / rel
            if b.exists():
                d = target / rel
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(b, d)
        for rel in created:
            d = target / rel
            if d.exists():
                d.unlink()
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"ok": True, "state": state, "manifest": m}


def rollback_package(target: Path) -> dict:
    """Restore the state and files captured before the last applied update."""
    target = Path(target)
    state_path = target / "update-state.json"
    if not state_path.exists():
        raise ValueError("no update-state.json in target")
    state = json.loads(state_path.read_text())
    rb = state.get("rollback")
    if not rb:
        raise ValueError("no rollback snapshot for this update")
    backup_root = target / rb["backup"]
    if not backup_root.exists():
        raise ValueError(f"rollback backup missing: {backup_root}")
    for rel in rb.get("overwritten", []):
        src = backup_root / rel
        if not src.exists():
            raise ValueError(f"backup file missing: {rel}")
    for rel in rb.get("overwritten", []):
        src = backup_root / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for rel in rb.get("created", []):
        p = target / rel
        if p.exists():
            p.unlink()
    # Remove directories that became empty after deleting created files.
    for rel in sorted(rb.get("created", []), key=lambda x: x.count("/"), reverse=True):
        d = (target / rel).parent
        while d != target and d.exists():
            try:
                d.rmdir()
            except OSError:
                break
            d = d.parent
    previous = dict(rb.get("previous_state", {"version": "0", "update_id": ""}))
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(previous, indent=2))
    os.replace(tmp, state_path)
    return {"ok": True, "state": previous, "rolled_back_update": state.get("update_id")}


def inspect_package(path: Path) -> dict:
    manifest, cipher = read_package(path)
    return {
        "update_id": manifest.get("update_id"),
        "version": manifest.get("version"),
        "parent": manifest.get("parent"),
        "channel": manifest.get("channel"),
        "payload_size": manifest.get("payload", {}).get("size"),
        "cipher_size": len(cipher),
        "signature_alg": manifest.get("signature", {}).get("alg"),
        "crypto": manifest.get("crypto", {}).get("alg"),
    }
