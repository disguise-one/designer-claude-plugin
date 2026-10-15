"""Unit tests for the compare function in verify_against_d3service.py."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import verify_against_d3service as v  # noqa: E402

MANIFEST = {
    "skill_md_d3_sha256": "aa",
    "files": [
        {"path": "SKILL.md", "size": 10, "sha256": "bb"},
        {"path": "references/a.md", "size": 5, "sha256": "cc"},
    ],
}


def served(size=5, digest="sha256:CC"):
    return {"references/a.md": {"size": size, "digest": digest}}


class CompareTests(unittest.TestCase):
    def oks(self, served_files, skill_md):
        return [ok for ok, _ in v.compare(MANIFEST, served_files, skill_md)]

    def test_all_pass(self):
        self.assertEqual(self.oks(served(), "aa"), [True, True])

    def test_skill_md_uses_d3_digest(self):
        self.assertEqual(self.oks(served(), "bb"), [False, True])

    def test_no_skill_md_digest_is_skipped(self):
        lines = v.compare(MANIFEST, served(), None)
        self.assertTrue(lines[0][1].startswith("SKIP"))
        self.assertEqual(self.oks(served(), None), [True, True])

    def test_size_differs(self):
        self.assertEqual(self.oks(served(size=6), "aa"), [True, False])

    def test_digest_differs(self):
        self.assertEqual(self.oks(served(digest="sha256:dd"), "aa"),
                         [True, False])

    def test_missing_and_extra_files(self):
        self.assertEqual(self.oks({}, "aa"), [True, False])
        extra = served()
        extra["x.md"] = {"size": 1, "digest": "sha256:ee"}
        self.assertEqual(self.oks(extra, "aa"), [True, True, False])


if __name__ == "__main__":
    unittest.main()
