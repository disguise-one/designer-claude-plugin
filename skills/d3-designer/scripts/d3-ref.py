"""Combined reference + API lookup for d3-designer skill.

Reads reference files and runs pyi-lookup for specified classes and search
terms — all in a single tool call. The agent specifies which classes to
look up; this script does NOT auto-extract class names from references.

Usage:
    python d3-ref.py stage-projection,layers-modules
    python d3-ref.py stage-projection --classes LedScreen,Parallel --search radar
    python d3-ref.py --classes Track --doc Track.addNewLayer
    python d3-ref.py --classes Track --inherited
    python d3-ref.py --list
    python d3-ref.py --stub PATH --classes Track
    python d3-ref.py --help

References are short names (without path or .md extension).
--stub PATH (or the D3_PYI_PATH environment variable) selects a d3.pyi file
that matches your build. Without it, d3-pyi-lookup.py uses the public stub,
which can be older than your build. See d3-pyi-lookup.py for the cache folder.
"""

import io
import os
import subprocess
import sys

# Ensure UTF-8 output on Windows (avoid cp1252 UnicodeEncodeError on arrow chars etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(SCRIPT_DIR, "..", "references")
PYI_LOOKUP = os.path.join(SCRIPT_DIR, "d3-pyi-lookup.py")


def read_reference(name):
    """Read a reference file by short name. Returns (filename, content) or None."""
    name = name.strip()
    path = os.path.join(REF_DIR, name + ".md")
    if not os.path.exists(path):
        # Fuzzy match: ignore dashes/underscores
        target = name.lower().replace("-", "").replace("_", "")
        for f in os.listdir(REF_DIR):
            if f.endswith(".md") and f[:-3].lower().replace("-", "").replace("_", "") == target:
                path = os.path.join(REF_DIR, f)
                break
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return (os.path.basename(path), f.read())


def run_pyi_lookup(class_names, search_keyword=None, inherited=False, doc_spec=None, stub=None):
    """Run d3-pyi-lookup.py and return its output."""
    cmd = [sys.executable, PYI_LOOKUP]
    if stub:
        cmd.extend(["--stub", stub])

    if doc_spec:
        cmd.extend(["--doc", doc_spec])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout

    if class_names:
        if not inherited:
            cmd.append("--no-inherited")
        cmd.append(",".join(class_names))
    if search_keyword:
        cmd.extend(["--search", search_keyword])
    if not class_names and not search_keyword:
        return ""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python d3-ref.py ref1,ref2 [--classes Class1,Class2] [--search keyword]")
        print("       python d3-ref.py --classes Class --doc Class.method")
        print("       python d3-ref.py --classes Class --inherited")
        print("       python d3-ref.py --list")
        print("       python d3-ref.py --help")
        print("\nReads reference files and looks up API classes in one call.")
        sys.exit(1)

    if args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    if args[0] == "--list":
        print("Available references:")
        for f in sorted(os.listdir(REF_DIR)):
            if f.endswith(".md"):
                print(f"  {f[:-3]}")
        sys.exit(0)

    # Parse arguments
    ref_names = []
    explicit_classes = []
    search_keyword = None
    inherited = False
    doc_spec = None
    stub = None

    i = 0
    while i < len(args):
        if args[i] in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif args[i] == "--stub" and i + 1 < len(args):
            stub = args[i + 1]
            i += 2
        elif args[i] == "--classes" and i + 1 < len(args):
            explicit_classes.extend(args[i + 1].split(","))
            i += 2
        elif args[i] == "--search" and i + 1 < len(args):
            search_keyword = args[i + 1]
            i += 2
        elif args[i] == "--doc" and i + 1 < len(args):
            doc_spec = args[i + 1]
            i += 2
        elif args[i] == "--inherited":
            inherited = True
            i += 1
        elif args[i] in ("--classes", "--search", "--doc", "--stub"):
            print(f"Error: {args[i]} requires a value.", file=sys.stderr)
            sys.exit(1)
        elif not args[i].startswith("--"):
            ref_names.extend(args[i].split(","))
            i += 1
        else:
            print(f"Error: Unknown flag '{args[i]}'.", file=sys.stderr)
            sys.exit(1)

    # Read and print references
    for name in ref_names:
        result = read_reference(name)
        if result:
            filename, content = result
            print(f"{'=' * 60}")
            print(f"REFERENCE: {filename}")
            print(f"{'=' * 60}\n")
            print(content)
            print()
        else:
            print(f"WARNING: Reference '{name}' not found.\n")

    # Run pyi lookups
    if explicit_classes or search_keyword or doc_spec:
        mode = "--doc" if doc_spec else ("--inherited" if inherited else "--no-inherited")
        print(f"{'=' * 60}")
        print(f"API LOOKUP ({mode})")
        if explicit_classes:
            print(f"  Classes: {', '.join(explicit_classes)}")
        if search_keyword:
            print(f"  Search: {search_keyword}")
        if doc_spec:
            print(f"  Doc: {doc_spec}")
        print(f"{'=' * 60}\n")

        output = run_pyi_lookup(explicit_classes, search_keyword, inherited, doc_spec, stub)
        if output:
            print(output)


if __name__ == "__main__":
    main()
