#!/usr/bin/env python3
"""Tests for path matching, puzzle IDs and priority scoring."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / ".pylibs"))
from path_trace import PathTracer, train, label, score


class PathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = self.tmp / "traces.sqlite"
        self.lib = self.tmp / "library.json"
        self.lib.write_text("""{"paths":[
          {"id":"lib_cfg","name":"Config","sequence":["LoadConfig","ResolvePath","ParseXML","ApplyConfig"],"confidence":0.95},
          {"id":"lib_save","name":"Save","sequence":["Serialize","WriteFile","Flush"],"confidence":0.9}
        ]}""")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_match_and_puzzle(self):
        t = PathTracer(self.db, self.lib)
        r = t.trace(["LoadConfig", "ResolvePath", "ParseXML", "ApplyConfig", "UnknownA", "UnknownB", "Serialize", "WriteFile", "Flush"])
        self.assertEqual(len(r["matches"]), 2)
        self.assertEqual(len(r["puzzles"]), 1)
        self.assertTrue(r["puzzles"][0]["id"].startswith("pz_"))
        self.assertGreaterEqual(r["priority"], 0.0)
        self.assertLessEqual(r["priority"], 1.0)

    def test_puzzle_id_stable_and_reused(self):
        t = PathTracer(self.db, self.lib)
        a = t.trace(["UnknownA", "UnknownB"])["puzzles"][0]
        b = t.trace(["UnknownA", "UnknownB"])["puzzles"][0]
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(b["occurrences"], 2)

    def test_train(self):
        rows = [
            {"features": {"novelty": 0.0, "coverage": 1.0, "library_hits": 2, "reuse": 1, "unknown_count": 0}, "label": 0.05},
            {"features": {"novelty": 0.9, "coverage": 0.1, "library_hits": 0, "reuse": 1, "unknown_count": 8}, "label": 0.95},
            {"features": {"novelty": 0.5, "coverage": 0.5, "library_hits": 1, "reuse": 5, "unknown_count": 4}, "label": 0.8},
        ]
        model = train(rows, iterations=800, lr=0.15)
        self.assertIn("weights", model)
        high = score({"novelty": 0.9, "coverage": 0.1, "library_hits": 0, "reuse": 1, "unknown_count": 8}, model)
        low = score({"novelty": 0.0, "coverage": 1.0, "library_hits": 2, "reuse": 1, "unknown_count": 0}, model)
        self.assertGreater(high, low)
        self.assertIn(label(high), {"high", "critical", "medium"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
