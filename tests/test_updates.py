#!/usr/bin/env python3
"""Automated tests for encrypted, signed update packages."""
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / ".pylibs"))
import update_format as uf


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.keys = self.tmp / "keys"
        self.keys.mkdir()
        uf.make_keys(self.keys / "master.key", self.keys / "private.pem", self.keys / "public.pem")
        self.pkgs = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_pkg(self, version, parent=""):
        payload = self.tmp / f"payload-{version}.zip"
        with zipfile.ZipFile(payload, "w") as z:
            z.writestr("VERSION.txt", version)
        r = uf.create_package(payload, version, self.tmp / "dist",
                              self.keys / "master.key", self.keys / "private.pem", parent)
        self.pkgs.append(Path(r["path"]))
        return r["manifest"]

    def test_chain_verify_apply(self):
        parent = ""
        for v in ("1.0.1", "1.0.2", "1.0.3"):
            m = self.make_pkg(v, parent)
            parent = m["update_id"]
        for p in self.pkgs:
            uf.verify_package(p, self.keys / "public.pem", self.keys / "master.key")
        target = self.tmp / "target"
        for p in self.pkgs:
            uf.apply_package(p, target, self.keys / "public.pem", self.keys / "master.key")
        self.assertEqual((target / "VERSION.txt").read_text(), "1.0.3")
        state = json.loads((target / "update-state.json").read_text())
        self.assertEqual(state["version"], "1.0.3")
        uf.rollback_package(target)
        self.assertEqual((target / "VERSION.txt").read_text(), "1.0.2")
        uf.rollback_package(target)
        self.assertEqual((target / "VERSION.txt").read_text(), "1.0.1")
        uf.rollback_package(target)
        self.assertFalse((target / "VERSION.txt").exists())
        self.assertEqual(json.loads((target / "update-state.json").read_text())["version"], "0")

    def test_tampered_ciphertext(self):
        self.make_pkg("2.0.0")
        p = self.pkgs[0]
        with zipfile.ZipFile(p) as z:
            manifest = z.read("manifest.json")
            cipher = bytearray(z.read("payload.bin"))
        cipher[0] ^= 1
        bad = self.tmp / "bad.rupkg"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("manifest.json", manifest)
            z.writestr("payload.bin", bytes(cipher))
        with self.assertRaises(ValueError):
            uf.verify_package(bad, self.keys / "public.pem", self.keys / "master.key")

    def test_tampered_manifest(self):
        self.make_pkg("3.0.0")
        p = self.pkgs[0]
        with zipfile.ZipFile(p) as z:
            manifest = json.loads(z.read("manifest.json"))
            cipher = z.read("payload.bin")
        manifest["version"] = "9.9.9"
        bad = self.tmp / "bad2.rupkg"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("manifest.json", json.dumps(manifest))
            z.writestr("payload.bin", cipher)
        with self.assertRaises(ValueError):
            uf.verify_package(bad, self.keys / "public.pem", self.keys / "master.key")

    def test_wrong_master_key(self):
        self.make_pkg("4.0.0")
        wrong = self.tmp / "wrong.key"
        wrong.write_bytes(b"0" * 32)
        with self.assertRaises(ValueError):
            uf.verify_package(self.pkgs[0], self.keys / "public.pem", wrong)


if __name__ == "__main__":
    unittest.main(verbosity=2)
