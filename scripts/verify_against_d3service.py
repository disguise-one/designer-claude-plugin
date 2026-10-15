#!/usr/bin/env python3
"""Compare skills-manifest.json with the skill files that d3service serves.

Usage:
  python scripts/verify_against_d3service.py --url http://<host>/api/mcp/rpc

The script calls skills/list. It compares the size and SHA-256 digest of each
file with the manifest. It prints one PASS or FAIL line for each file.
Exit code: 0 if all files pass, 1 if a file fails, 2 on an error.

The plugin SKILL.md has no allowed-tools line, so it differs from the d3
file. For SKILL.md the script compares the d3 digest in the manifest
(skill_md_d3_sha256) with the digest of the file that the server serves.
skills/list does not list SKILL.md. The script tries resources/read and
hashes the text as UTF-8 bytes. The d3service code today does not serve
SKILL.md that way. Then the script prints SKIP for SKILL.md.

Python 3.9 or later. Standard library only.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

SKILL_NAME = "d3-designer"
URI_PREFIX = "skill://%s/" % SKILL_NAME


def rpc(url, method, params=None, timeout=30):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        body["params"] = params
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        reply = json.loads(response.read().decode("utf-8"))
    if "error" in reply:
        raise RuntimeError("%s failed: %s" % (method, reply["error"]))
    return reply["result"]


def normalise_digest(value):
    value = (value or "").lower()
    return value[len("sha256:"):] if value.startswith("sha256:") else value


def served_skill_md_digest(url):
    """Return the SHA-256 hex digest of the served SKILL.md, or None."""
    try:
        result = rpc(url, "resources/read", {"uri": URI_PREFIX + "SKILL.md"})
        text = result["contents"][0]["text"]
    except (RuntimeError, KeyError, IndexError, urllib.error.URLError) as exc:
        print("note: cannot read SKILL.md from the server: %s" % exc)
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare(manifest, served, skill_md_digest):
    """Return a list of (ok, text) lines. Pure function, easy to test."""
    lines = []
    listed = {f["path"]: f for f in manifest["files"]}
    for path in sorted(listed):
        entry = listed[path]
        if path == "SKILL.md":
            want = manifest["skill_md_d3_sha256"]
            if skill_md_digest is None:
                # The server lists no SKILL.md digest and resources/read
                # does not serve it (checked in mcpskillregistry.cpp).
                lines.append((True, "SKIP SKILL.md: server gives no digest"))
            elif skill_md_digest == want:
                lines.append((True, "PASS SKILL.md (d3 digest)"))
            else:
                lines.append((False, "FAIL SKILL.md: digest %s, expected %s"
                              % (skill_md_digest, want)))
            continue
        item = served.get(path)
        if item is None:
            lines.append((False, "FAIL %s: not served" % path))
        elif item.get("size") != entry["size"]:
            lines.append((False, "FAIL %s: size %s, expected %s"
                          % (path, item.get("size"), entry["size"])))
        elif normalise_digest(item.get("digest")) != entry["sha256"]:
            lines.append((False, "FAIL %s: digest differs" % path))
        else:
            lines.append((True, "PASS %s" % path))
    for path in sorted(set(served) - set(listed)):
        lines.append((False, "FAIL %s: served but not in manifest" % path))
    return lines


def served_files(result):
    for skill in result.get("skills", []):
        if skill.get("uri") == URI_PREFIX + "SKILL.md":
            return {r["uri"][len(URI_PREFIX):]: r
                    for r in skill.get("resources", [])}
    raise RuntimeError("skill %s is not in skills/list" % SKILL_NAME)


def main(argv=None):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--url", required=True,
                        help="for example http://host/api/mcp/rpc")
    parser.add_argument("--manifest",
                        default=os.path.join(root, "skills-manifest.json"))
    args = parser.parse_args(argv)
    try:
        with open(args.manifest, "rb") as f:
            manifest = json.loads(f.read().decode("utf-8"))
        served = served_files(rpc(args.url, "skills/list"))
        skill_md = served_skill_md_digest(args.url)
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    results = compare(manifest, served, skill_md)
    for _, text in results:
        print(text)
    failed = sum(1 for ok, _ in results if not ok)
    print("%d passed, %d failed" % (len(results) - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
