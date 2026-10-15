"""Unit tests for sync_skill.py.

Each test uses a small fake d3 checkout in a temporary folder.
Run: python -m unittest discover -s scripts
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sync_skill  # noqa: E402

ALLOWED = b"allowed-tools: Bash, Read, mcp__d3service__*"


def skill_md(eol):
    lines = [
        b"---",
        b"name: d3-designer",
        b"description: >",
        b"  Test skill.",
        ALLOWED,
        b"---",
        b"",
        b"# Title",
        b"Body text.",
    ]
    return eol.join(lines) + eol


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Base(unittest.TestCase):
    eol = b"\r\n"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sync_skill_test_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.d3 = os.path.join(self.tmp, "d3")
        self.repo = os.path.join(self.tmp, "plugin")
        os.makedirs(self.repo)
        self.skill_dir = os.path.join(self.d3, "skills", "d3-designer")
        self.write_d3("SKILL.md", skill_md(self.eol))
        self.write_d3("references/a.md", b"Line one\r\nLine two\n")
        self.write_d3("scripts/run.ps1", b"Write-Host 'hi'\r\n")
        self.write_d3("references/data.bin", bytes(range(256)))
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com",
                 "commit", "-q", "-m", "init")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", self.d3] + list(args),
            check=True, capture_output=True).stdout.decode().strip()

    def write_d3(self, rel, data):
        path = os.path.join(self.skill_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def plugin_path(self, rel):
        return os.path.join(self.repo, "skills", "d3-designer",
                            *rel.split("/"))

    def read_plugin(self, rel):
        with open(self.plugin_path(rel), "rb") as f:
            return f.read()

    def run_main(self, *extra):
        args = ["--d3", self.d3, "--repo", self.repo] + list(extra)
        return sync_skill.main(args)

    def manifest(self):
        with open(os.path.join(self.repo, "skills-manifest.json"), "rb") as f:
            return json.loads(f.read().decode("utf-8"))


class SyncTests(Base):
    def test_allowed_tools_line_is_removed(self):
        self.assertEqual(self.run_main(), 0)
        self.assertNotIn(b"allowed-tools", self.read_plugin("SKILL.md"))

    def test_only_that_line_changes(self):
        self.run_main()
        expected = skill_md(self.eol).replace(ALLOWED + self.eol, b"")
        self.assertEqual(self.read_plugin("SKILL.md"), expected)

    def test_lf_line_ending_is_kept(self):
        self.write_d3("SKILL.md", skill_md(b"\n"))
        self.run_main()
        expected = skill_md(b"\n").replace(ALLOWED + b"\n", b"")
        self.assertEqual(self.read_plugin("SKILL.md"), expected)

    def test_other_files_are_byte_identical(self):
        self.run_main()
        self.assertEqual(self.read_plugin("references/a.md"),
                         b"Line one\r\nLine two\n")
        self.assertEqual(self.read_plugin("references/data.bin"),
                         bytes(range(256)))
        self.assertEqual(self.read_plugin("scripts/run.ps1"),
                         b"Write-Host 'hi'\r\n")

    def test_file_removed_in_d3_is_removed_in_plugin(self):
        self.run_main()
        self.assertTrue(os.path.exists(self.plugin_path("references/a.md")))
        os.remove(os.path.join(self.skill_dir, "references", "a.md"))
        self.run_main()
        self.assertFalse(os.path.exists(self.plugin_path("references/a.md")))
        paths = [f["path"] for f in self.manifest()["files"]]
        self.assertNotIn("references/a.md", paths)

    def test_no_temporary_folder_is_left(self):
        self.run_main()
        self.assertEqual(sorted(os.listdir(self.repo)),
                         ["skills", "skills-manifest.json"])

    def test_manifest_content(self):
        self.run_main()
        m = self.manifest()
        self.assertEqual(m["d3_commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(m["skill_md_d3_sha256"], sha(skill_md(self.eol)))
        by_path = {f["path"]: f for f in m["files"]}
        self.assertEqual(sorted(by_path), [
            "SKILL.md", "references/a.md", "references/data.bin",
            "scripts/run.ps1"])
        plugin_md = self.read_plugin("SKILL.md")
        self.assertEqual(by_path["SKILL.md"]["size"], len(plugin_md))
        self.assertEqual(by_path["SKILL.md"]["sha256"], sha(plugin_md))

    def test_missing_line_is_an_error(self):
        self.write_d3("SKILL.md", skill_md(self.eol).replace(
            ALLOWED + self.eol, b""))
        with self.assertRaises(sync_skill.SyncError) as ctx:
            self.run_main()
        self.assertIn("allowed-tools", str(ctx.exception))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "skills")))

    def test_bad_frontmatter_is_an_error(self):
        self.write_d3("SKILL.md", b"# No frontmatter\n" + ALLOWED + b"\n")
        with self.assertRaises(sync_skill.SyncError):
            self.run_main()

    def test_line_after_frontmatter_is_not_removed(self):
        data = skill_md(self.eol).replace(ALLOWED + self.eol, b"") + \
            ALLOWED + self.eol
        self.write_d3("SKILL.md", data)
        with self.assertRaises(sync_skill.SyncError):
            self.run_main()

    def test_two_lines_is_an_error(self):
        data = skill_md(self.eol).replace(
            ALLOWED + self.eol, ALLOWED + self.eol + ALLOWED + self.eol)
        self.write_d3("SKILL.md", data)
        with self.assertRaises(sync_skill.SyncError):
            self.run_main()

    def test_continuation_line_is_an_error(self):
        data = skill_md(self.eol).replace(
            ALLOWED + self.eol, ALLOWED + self.eol + b"  more" + self.eol)
        self.write_d3("SKILL.md", data)
        with self.assertRaises(sync_skill.SyncError):
            self.run_main()

    def test_yaml_list_after_the_key_is_an_error(self):
        data = skill_md(self.eol).replace(
            ALLOWED + self.eol,
            b"allowed-tools:" + self.eol + b"- Bash" + self.eol)
        self.write_d3("SKILL.md", data)
        with self.assertRaises(sync_skill.SyncError):
            self.run_main()

    def test_missing_d3_skill_is_an_error(self):
        shutil.rmtree(self.skill_dir)
        with self.assertRaises(sync_skill.SyncError):
            self.run_main()

    def test_failed_swap_keeps_the_old_copy(self):
        self.run_main()
        before = self.read_plugin("SKILL.md")
        self.write_d3("references/a.md", b"changed\r\n")
        real_replace = os.replace
        calls = []

        def fail_second(src, dst):
            calls.append((src, dst))
            if len(calls) == 2:
                raise OSError("simulated failure")
            return real_replace(src, dst)

        os.replace = fail_second
        try:
            with self.assertRaises(OSError):
                self.run_main()
        finally:
            os.replace = real_replace
        self.assertEqual(before, self.read_plugin("SKILL.md"))
        self.assertEqual(b"Line one\r\nLine two\n",
                         self.read_plugin("references/a.md"))


class CheckTests(Base):
    def test_check_passes_right_after_sync(self):
        self.run_main()
        self.assertEqual(self.run_main("--check"), 0)

    def test_check_fails_after_hand_edit(self):
        self.run_main()
        with open(self.plugin_path("references/a.md"), "ab") as f:
            f.write(b"edit\n")
        self.assertEqual(self.run_main("--check"), 1)

    def test_check_fails_for_extra_file(self):
        self.run_main()
        with open(self.plugin_path("extra.md"), "wb") as f:
            f.write(b"x")
        self.assertEqual(self.run_main("--check"), 1)

    def test_check_fails_when_manifest_changed(self):
        self.run_main()
        path = os.path.join(self.repo, "skills-manifest.json")
        with open(path, "ab") as f:
            f.write(b" ")
        self.assertEqual(self.run_main("--check"), 1)

    def test_check_fails_when_d3_changed(self):
        self.run_main()
        self.write_d3("references/a.md", b"new\n")
        self.assertEqual(self.run_main("--check"), 1)

    def test_check_changes_nothing(self):
        self.run_main()
        with open(self.plugin_path("references/a.md"), "ab") as f:
            f.write(b"edit\n")
        before = self.read_plugin("references/a.md")
        self.run_main("--check")
        self.assertEqual(self.read_plugin("references/a.md"), before)


class VerifyManifestTests(Base):
    def verify(self):
        return sync_skill.main(["--repo", self.repo, "--verify-manifest"])

    def test_passes_after_sync(self):
        self.run_main()
        self.assertEqual(self.verify(), 0)

    def test_fails_after_hand_edit(self):
        self.run_main()
        with open(self.plugin_path("references/a.md"), "ab") as f:
            f.write(b"edit\n")
        self.assertEqual(self.verify(), 1)

    def test_fails_for_extra_file(self):
        self.run_main()
        with open(self.plugin_path("extra.md"), "wb") as f:
            f.write(b"x")
        self.assertEqual(self.verify(), 1)

    def test_fails_for_missing_file(self):
        self.run_main()
        os.remove(self.plugin_path("references/a.md"))
        self.assertEqual(self.verify(), 1)

    def test_fails_when_allowed_tools_is_back(self):
        self.run_main()
        with open(self.plugin_path("SKILL.md"), "wb") as f:
            f.write(skill_md(self.eol))
        self.assertEqual(self.verify(), 1)

    def test_fails_without_manifest(self):
        self.run_main()
        os.remove(os.path.join(self.repo, "skills-manifest.json"))
        self.assertEqual(self.verify(), 1)


if __name__ == "__main__":
    unittest.main()
