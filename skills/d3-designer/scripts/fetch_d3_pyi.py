#!/usr/bin/env python3
"""Fetch the current disguise d3 Python API type stub for this skill."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_URL = "https://developer.disguise.one/assets/d3.pyi"


def default_output():
    """Same cache file that d3-pyi-lookup.py reads. The folder is writable by the user."""
    folder = os.environ.get("D3_PYI_CACHE_DIR")
    if not folder:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
        folder = os.path.join(base, "d3-designer-skill")
    return os.path.join(folder, "d3.pyi")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the current d3.pyi type stub.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Stub URL to download.")
    parser.add_argument(
        "--output",
        default=default_output(),
        help="Output path for the downloaded stub.",
    )
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    request = Request(args.url, headers={"User-Agent": "d3-designer-skill/1.0"})
    with urlopen(request, timeout=30) as response:
        data = response.read()

    if not data.strip().startswith((b"import ", b"from ", b"class ", b"def ", b"#")):
        raise RuntimeError(f"Downloaded content from {args.url} does not look like a Python stub")

    output.write_bytes(data)
    print(f"Wrote {len(data)} bytes to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
