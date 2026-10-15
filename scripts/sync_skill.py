#!/usr/bin/env python3
"""Copy the d3-designer skill from a d3 checkout into this plugin repository.

The d3 copy is the only copy that people edit. The plugin copy is generated.
Do not edit files in skills/ by hand.

The copy is byte for byte, with one change. The line "allowed-tools:" is
removed from the SKILL.md frontmatter. A plugin MCP server has tool names
like mcp__plugin_<plugin>_<server>__<tool>. The d3 value mcp__d3service__*
does not match them.

Usage:
  python scripts/sync_skill.py --d3 <d3 checkout>                 sync
  python scripts/sync_skill.py --d3 <d3 checkout> --check         no changes;
      exit 1 if a sync would change a file
  python scripts/sync_skill.py --verify-manifest                  no d3 needed;
      exit 1 if skills/ does not match skills-manifest.json

Exit codes: 0 good, 1 difference found, 2 error.
Python 3.9 or later. Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

SKILL_NAME = "d3-designer"
MANIFEST_NAME = "skills-manifest.json"
REMOVED_KEY = b"allowed-tools:"
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = (".pyc",)

_LINE = re.compile(rb"[^\n]*\n|[^\n]+")


class SyncError(Exception):
    """A problem that stops the sync. The message tells the user what to do."""


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def strip_allowed_tools(data):
    """Return SKILL.md bytes without the allowed-tools frontmatter line.

    Other bytes stay the same, including the line endings.
    """
    lines = _LINE.findall(data)
    if not lines or lines[0].rstrip(b"\r\n") != b"---":
        raise SyncError(
            "SKILL.md must start with a '---' frontmatter line. "
            "Fix the file in d3.")
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip(b"\r\n") == b"---":
            end = i
            break
    if end is None:
        raise SyncError(
            "SKILL.md frontmatter has no closing '---' line. "
            "Fix the file in d3.")
    hits = [i for i in range(1, end) if lines[i].startswith(REMOVED_KEY)]
    if len(hits) != 1:
        raise SyncError(
            "SKILL.md frontmatter must have exactly one 'allowed-tools:' "
            "line. Found %d. The sync cannot continue." % len(hits))
    i = hits[0]
    if i + 1 < end and lines[i + 1][:1] in (b" ", b"\t", b"-"):
        raise SyncError(
            "The 'allowed-tools:' value in SKILL.md goes over more than one "
            "line. The sync removes one line only. Change the sync script.")
    del lines[i]
    return b"".join(lines)


def list_files(root):
    """Return the sorted relative posix paths of all files under root."""
    found = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in names:
            if name.endswith(SKIP_SUFFIXES):
                continue
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            found.append(rel)
    return sorted(found)


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def d3_commit(d3):
    try:
        out = subprocess.run(
            ["git", "-C", d3, "rev-parse", "HEAD"],
            check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SyncError("Cannot read the d3 commit with git: %s" % exc)
    return out.stdout.decode("ascii").strip()


def manifest_bytes(files, commit, d3_skill_md_digest):
    """Make the manifest file content from a dict of {path: bytes}."""
    manifest = {
        "skill": SKILL_NAME,
        "d3_commit": commit,
        "skill_md_d3_sha256": d3_skill_md_digest,
        "files": [
            {"path": p, "size": len(files[p]), "sha256": sha256_hex(files[p])}
            for p in sorted(files)
        ],
    }
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return text.encode("utf-8")


def build_expected(d3):
    """Return (files, manifest) that a sync would write."""
    source = os.path.join(d3, "skills", SKILL_NAME)
    if not os.path.isdir(source):
        raise SyncError("Folder not found: %s" % source)
    files = {}
    for rel in list_files(source):
        files[rel] = read_bytes(os.path.join(source, *rel.split("/")))
    if "SKILL.md" not in files:
        raise SyncError("SKILL.md is missing in %s" % source)
    d3_digest = sha256_hex(files["SKILL.md"])
    files["SKILL.md"] = strip_allowed_tools(files["SKILL.md"])
    manifest = manifest_bytes(files, d3_commit(d3), d3_digest)
    return files, manifest


def read_plugin_files(repo):
    root = os.path.join(repo, "skills", SKILL_NAME)
    if not os.path.isdir(root):
        return {}
    return {rel: read_bytes(os.path.join(root, *rel.split("/")))
            for rel in list_files(root)}


def diff_files(expected, actual):
    """Return a list of text lines that describe the differences."""
    out = []
    for p in sorted(set(expected) | set(actual)):
        if p not in actual:
            out.append("missing in plugin: %s" % p)
        elif p not in expected:
            out.append("extra in plugin: %s" % p)
        elif expected[p] != actual[p]:
            out.append("different: %s" % p)
    return out


def write_tree(files, manifest, repo):
    """Write into a new folder, then swap it in. No in-place overwrite."""
    work = os.path.join(repo, ".sync-tmp-%d" % os.getpid())
    new_skill = os.path.join(work, SKILL_NAME)
    skills_dir = os.path.join(repo, "skills")
    target = os.path.join(skills_dir, SKILL_NAME)
    old = os.path.join(work, "old")
    try:
        os.makedirs(new_skill)
        for rel, data in files.items():
            path = os.path.join(new_skill, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
        new_manifest = os.path.join(work, MANIFEST_NAME)
        with open(new_manifest, "wb") as f:
            f.write(manifest)
        os.makedirs(skills_dir, exist_ok=True)
        moved_old = False
        if os.path.isdir(target):
            os.replace(target, old)
            moved_old = True
        try:
            os.replace(new_skill, target)
            os.replace(new_manifest, os.path.join(repo, MANIFEST_NAME))
        except OSError:
            # Put the old copy back. Do not leave the plugin with no skill.
            if moved_old and not os.path.isdir(target):
                os.replace(old, target)
            raise
    finally:
        shutil.rmtree(work, ignore_errors=True)


def do_sync(d3, repo, check):
    files, manifest = build_expected(d3)
    manifest_path = os.path.join(repo, MANIFEST_NAME)
    if check:
        problems = diff_files(files, read_plugin_files(repo))
        actual_manifest = (read_bytes(manifest_path)
                           if os.path.isfile(manifest_path) else None)
        if actual_manifest != manifest:
            problems.append("different: %s" % MANIFEST_NAME)
        for line in problems:
            print("FAIL " + line)
        if problems:
            print("The plugin copy is not what a sync writes. "
                  "Run scripts/sync_skill.py without --check.")
            return 1
        print("OK: the plugin copy matches a sync of the d3 copy.")
        return 0
    write_tree(files, manifest, repo)
    print("Synced %d files from %s" % (len(files), d3))
    return 0


def do_verify_manifest(repo):
    """Compare skills/ with skills-manifest.json. d3 is not needed."""
    manifest_path = os.path.join(repo, MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        print("FAIL %s does not exist" % MANIFEST_NAME)
        return 1
    try:
        manifest = json.loads(read_bytes(manifest_path).decode("utf-8"))
        listed = {f["path"]: f for f in manifest["files"]}
    except (ValueError, KeyError, TypeError) as exc:
        print("FAIL %s is not valid: %s" % (MANIFEST_NAME, exc))
        return 1
    actual = read_plugin_files(repo)
    problems = []
    for p in sorted(set(listed) | set(actual)):
        if p not in actual:
            problems.append("missing file: %s" % p)
        elif p not in listed:
            problems.append("file not in manifest: %s" % p)
        else:
            data = actual[p]
            if listed[p].get("size") != len(data):
                problems.append("size differs: %s" % p)
            elif listed[p].get("sha256") != sha256_hex(data):
                problems.append("digest differs: %s" % p)
    skill_md = actual.get("SKILL.md")
    if skill_md is not None:
        for line in _LINE.findall(skill_md):
            if line.startswith(REMOVED_KEY):
                problems.append("SKILL.md has an 'allowed-tools:' line")
                break
    for line in problems:
        print("FAIL " + line)
    if problems:
        return 1
    print("OK: %d files match %s." % (len(actual), MANIFEST_NAME))
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--d3", help="path to a d3 checkout")
    parser.add_argument("--repo", default=os.path.dirname(here),
                        help="plugin repository (default: this one)")
    parser.add_argument("--check", action="store_true",
                        help="change nothing; exit 1 if a sync would change")
    parser.add_argument("--verify-manifest", action="store_true",
                        help="compare skills/ with skills-manifest.json")
    args = parser.parse_args(argv)
    repo = os.path.abspath(args.repo)
    if args.verify_manifest:
        return do_verify_manifest(repo)
    if not args.d3:
        parser.error("--d3 is required")
    return do_sync(os.path.abspath(args.d3), repo, args.check)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SyncError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        sys.exit(2)
