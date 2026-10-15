"""d3.pyi stub lookup tool.

Parses d3.pyi using the ast module and resolves inheritance chains to give
a flat view of all properties and methods available on a class.

Stub source, in this order:
    1. --stub PATH, or the D3_PYI_PATH environment variable: a d3.pyi file
       that you give. Use this for a stub that matches your build.
    2. The public stub from developer.disguise.one. The script downloads it to
       a cache folder and refreshes it when it is older than 1 day. The public
       stub can be older than your build.
The cache folder is "d3-designer-skill" in the local application data folder
(LOCALAPPDATA), or in ~/.cache when LOCALAPPDATA is not set.
Set D3_PYI_CACHE_DIR to use a different cache folder.

Usage:
    python d3-pyi-lookup.py ClassName
    python d3-pyi-lookup.py Class1,Class2,...
    python d3-pyi-lookup.py --no-inherited ClassName
    python d3-pyi-lookup.py --doc ClassName.methodName
    python d3-pyi-lookup.py --search <keyword>
    python d3-pyi-lookup.py --stub PATH ClassName
    python d3-pyi-lookup.py --help
"""

import ast
import io
import os
import socket
import sys
import time
import urllib.request

# Ensure UTF-8 output on Windows (avoid cp1252 UnicodeEncodeError)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from collections import Counter, OrderedDict

D3_PYI_URL = "https://developer.disguise.one/assets/d3.pyi"
MAX_AGE_SECONDS = 86400  # 1 day


def default_cache_dir():
    """Folder for the downloaded stub. It is always writable by the user."""
    override = os.environ.get("D3_PYI_CACHE_DIR")
    if override:
        return override
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "d3-designer-skill")


CACHE_DIR = default_cache_dir()
CACHE_FILE = os.path.join(CACHE_DIR, "d3.pyi")

# Classes whose members are omitted with --no-inherited.
# These base properties are documented in SKILL.md Core Workflow.
WELL_KNOWN_BASES = {"Resource", "Module"}


def ensure_stub(stub_path=None):
    """Return the path of a d3.pyi file.

    Use the given stub (or D3_PYI_PATH) when set. Otherwise download the public
    stub if it is missing or older than MAX_AGE_SECONDS.
    """
    stub_path = stub_path or os.environ.get("D3_PYI_PATH")
    if stub_path:
        if not os.path.isfile(stub_path):
            print(f"Error: stub file not found: {stub_path}", file=sys.stderr)
            sys.exit(1)
        return stub_path
    os.makedirs(CACHE_DIR, exist_ok=True)
    need_download = True
    if os.path.exists(CACHE_FILE):
        age = time.time() - os.path.getmtime(CACHE_FILE)
        if age < MAX_AGE_SECONDS:
            need_download = False
    if need_download:
        print("Downloading the public d3.pyi (it can be older than your build)...", file=sys.stderr)
        # Force IPv4: disguise.one publishes AAAA records that time out on
        # networks without IPv6, causing urllib to hang for ~42s.
        _orig_getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = lambda *args, **kwargs: _orig_getaddrinfo(
            args[0], args[1], socket.AF_INET, *args[3:], **kwargs
        )
        try:
            urllib.request.urlretrieve(D3_PYI_URL, CACHE_FILE)
        finally:
            socket.getaddrinfo = _orig_getaddrinfo
        print("Done.", file=sys.stderr)
    return CACHE_FILE


def parse_stub(path):
    """Parse d3.pyi and return a dict of class name -> ClassInfo."""
    with open(path, encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)

    classes = {}
    _collect_classes(tree.body, "", classes)
    return classes


def _collect_classes(body, prefix, classes):
    """Recursively collect class definitions, handling nested classes."""
    for node in body:
        if isinstance(node, ast.ClassDef):
            name = f"{prefix}{node.name}" if prefix else node.name
            classes[name] = node
            # Also index by short name if no collision
            if node.name not in classes:
                classes[node.name] = node
            _collect_classes(node.body, f"{name}.", classes)


def get_bases(cls_node):
    """Get base class names from a ClassDef node."""
    bases = []
    for base in cls_node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(ast.unparse(base))
        elif isinstance(base, ast.Constant):
            bases.append(str(base.value))
    return bases


def get_inheritance_chain(classes, name):
    """Get the inheritance chain for a class, excluding the class itself."""
    chain = []
    seen = {name}
    current = name
    while True:
        node = classes.get(current)
        if node is None:
            break
        bases = get_bases(node)
        if not bases:
            break
        parent = bases[0]  # single inheritance
        if parent in seen:
            break
        seen.add(parent)
        if parent in classes:
            chain.append(parent)
        current = parent
    return chain


def extract_members(cls_node):
    """Extract properties and methods from a single class node."""
    properties = OrderedDict()
    methods = []
    static_methods = []

    # First pass: collect property names and setter names
    setter_names = set()
    for node in cls_node.body:
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Attribute) and dec.attr == "setter":
                    setter_names.add(node.name)

    # Second pass: collect members
    for node in cls_node.body:
        if not isinstance(node, ast.FunctionDef):
            continue

        name = node.name
        if name.startswith("_"):
            continue

        is_property = any(
            (isinstance(d, ast.Name) and d.id == "property")
            for d in node.decorator_list
        )
        is_setter = any(
            (isinstance(d, ast.Attribute) and d.attr == "setter")
            for d in node.decorator_list
        )
        is_static = any(
            (isinstance(d, ast.Name) and d.id == "staticmethod")
            for d in node.decorator_list
        )
        is_overload = any(
            (isinstance(d, ast.Name) and d.id == "overload")
            for d in node.decorator_list
        )

        if is_setter:
            continue  # handled via setter_names set

        if is_property:
            ret_type = ast.unparse(node.returns) if node.returns else "Any"
            rw = "rw" if name in setter_names else "ro"
            doc = _get_docstring_oneliner(node)
            properties[name] = (ret_type, rw, doc)
        elif is_static:
            sig = _format_signature(node, skip_self=False)
            static_methods.append(sig)
        elif is_overload:
            sig = _format_signature(node, skip_self=True)
            methods.append(sig)
        else:
            sig = _format_signature(node, skip_self=True)
            methods.append(sig)

    return properties, methods, static_methods


def _format_signature(func_node, skip_self=True):
    """Format a function signature as 'name(params) -> RetType'."""
    params = []
    for arg in func_node.args.args:
        if skip_self and arg.arg == "self":
            continue
        if arg.annotation:
            params.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
        else:
            params.append(arg.arg)

    # Handle defaults
    defaults = func_node.args.defaults
    if defaults:
        n_defaults = len(defaults)
        n_params = len(params)
        for i, default in enumerate(defaults):
            param_idx = n_params - n_defaults + i
            if 0 <= param_idx < n_params:
                params[param_idx] += f" = {ast.unparse(default)}"

    ret = ast.unparse(func_node.returns) if func_node.returns else "None"
    return f"{func_node.name}({', '.join(params)}) -> {ret}"


def _get_docstring_oneliner(node):
    """Extract first line of docstring if present."""
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        doc = node.body[0].value.value.strip()
        first_line = doc.split("\n")[0].strip()
        if first_line:
            return first_line
    return None


def _get_docstring_full(node):
    """Extract full docstring if present."""
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)):
        return node.body[0].value.value.strip()
    return None


def _find_method_node(cls_node, method_name):
    """Find a FunctionDef by name in a class body."""
    for node in cls_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    return None


def _print_members(name, all_props, all_methods, all_statics, omitted_bases=None):
    """Print formatted member listings."""
    if all_props:
        print("Properties:")
        current_source = None
        for source, pname, ptype, rw, doc in all_props:
            if source != name and source != current_source:
                current_source = source
                print(f"  # inherited from {source}")
            line = f"  {pname}: {ptype} [{rw}]"
            if doc:
                line += f"  -- {doc}"
            print(line)

    if all_methods:
        if all_props:
            print()
        print("Methods:")
        current_source = None
        for source, sig in all_methods:
            if source != name and source != current_source:
                current_source = source
                print(f"  # inherited from {source}")
            print(f"  {sig}")

    if all_statics:
        if all_methods or all_props:
            print()
        print("Static Methods:")
        current_source = None
        for source, sig in all_statics:
            if source != name and source != current_source:
                current_source = source
                print(f"  # inherited from {source}")
            print(f"  {sig}")

    if omitted_bases:
        print()
        bases_str = ", ".join(omitted_bases)
        print(f"  # {bases_str} base properties omitted — see SKILL.md Common Patterns")


def lookup_classes(classes, names, no_inherited=False):
    """Look up one or more classes with shared-ancestor deduplication.

    When multiple classes share a common ancestor (e.g. both inherit from Module),
    that ancestor's members are shown once under a shared section rather than
    repeated for each class. For a single class, prints it directly.
    """
    # Resolve all classes and their chains
    resolved = []  # [(name, chain)]
    for name in names:
        name = name.strip()
        if name not in classes:
            print(f"Class '{name}' not found.")
            print(f"\nDid you mean one of these?")
            search_classes(classes, name)
            print()
            continue
        chain = get_inheritance_chain(classes, name)
        resolved.append((name, chain))

    if not resolved:
        return

    # For a single class, simpler output (no ## headers)
    if len(resolved) == 1:
        name, chain = resolved[0]
        chain_str = " -> ".join(chain) if chain else "(no parent)"
        print(f"{name} ({chain_str})")
        print()

        # Determine which ancestors to include
        omitted_bases = []
        if no_inherited:
            display_chain = []
            for parent in chain:
                if parent in WELL_KNOWN_BASES:
                    omitted_bases.append(parent)
                else:
                    display_chain.append(parent)
        else:
            display_chain = chain

        all_levels = [(name, classes[name])] + [
            (parent, classes[parent]) for parent in display_chain
        ]

        all_props = []
        all_methods = []
        all_statics = []
        for cls_name, cls_node in all_levels:
            props, methods, statics = extract_members(cls_node)
            for pn, (pt, rw, doc) in props.items():
                all_props.append((cls_name, pn, pt, rw, doc))
            for sig in methods:
                all_methods.append((cls_name, sig))
            for sig in statics:
                all_statics.append((cls_name, sig))

        _print_members(name, all_props, all_methods, all_statics,
                       omitted_bases=omitted_bases if no_inherited else None)
        return

    # Multi-class: find shared ancestors for deduplication
    ancestor_counts = Counter()
    for name, chain in resolved:
        for parent in chain:
            if no_inherited and parent in WELL_KNOWN_BASES:
                continue
            ancestor_counts[parent] += 1

    shared_ancestors = {a for a, count in ancestor_counts.items() if count >= 2}

    # Print shared ancestors first (deduplicated)
    printed_shared = set()
    for ancestor in shared_ancestors:
        if ancestor in printed_shared or ancestor not in classes:
            continue
        printed_shared.add(ancestor)
        ancestor_chain = get_inheritance_chain(classes, ancestor)
        chain_str = " -> ".join(ancestor_chain) if ancestor_chain else "(no parent)"
        print(f"## {ancestor} ({chain_str})  [shared base]")
        print()

        props, methods, statics = extract_members(classes[ancestor])
        all_props = [(ancestor, pn, pt, rw, doc) for pn, (pt, rw, doc) in props.items()]
        all_methods = [(ancestor, sig) for sig in methods]
        all_statics = [(ancestor, sig) for sig in statics]
        _print_members(ancestor, all_props, all_methods, all_statics)
        print()

    # Print each requested class, excluding shared ancestor members
    omitted_bases_all = set()
    for name, chain in resolved:
        chain_str = " -> ".join(chain) if chain else "(no parent)"
        print(f"## {name} ({chain_str})")
        print()

        levels = [(name, classes[name])]
        for parent in chain:
            if parent in shared_ancestors:
                continue
            if no_inherited and parent in WELL_KNOWN_BASES:
                omitted_bases_all.add(parent)
                continue
            if parent in classes:
                levels.append((parent, classes[parent]))

        all_props = []
        all_methods = []
        all_statics = []
        for cls_name, cls_node in levels:
            props, methods, statics = extract_members(cls_node)
            for pn, (pt, rw, doc) in props.items():
                all_props.append((cls_name, pn, pt, rw, doc))
            for sig in methods:
                all_methods.append((cls_name, sig))
            for sig in statics:
                all_statics.append((cls_name, sig))

        _print_members(name, all_props, all_methods, all_statics)
        print()

    if no_inherited and omitted_bases_all:
        bases_str = ", ".join(sorted(omitted_bases_all))
        print(f"# {bases_str} base properties omitted — see SKILL.md Common Patterns")


def doc_lookup(classes, spec):
    """Look up full docstring for ClassName.methodName or ClassName.propertyName."""
    parts = spec.split(".", 1)
    if len(parts) != 2:
        print("Usage: --doc ClassName.memberName")
        return

    cls_name, member_name = parts
    if cls_name not in classes:
        print(f"Class '{cls_name}' not found.")
        return

    # Search the class and its inheritance chain
    chain = [cls_name] + get_inheritance_chain(classes, cls_name)
    for ancestor in chain:
        node = classes.get(ancestor)
        if node is None:
            continue
        method_node = _find_method_node(node, member_name)
        if method_node:
            doc = _get_docstring_full(method_node)
            sig = _format_signature(method_node, skip_self=True)
            source_note = f"  (defined in {ancestor})" if ancestor != cls_name else ""
            print(f"{cls_name}.{member_name}{source_note}")
            print(f"  {sig}")
            if doc:
                print()
                for line in doc.split("\n"):
                    print(f"  {line}")
            else:
                print("  (no docstring)")
            return

    print(f"Member '{member_name}' not found on {cls_name} or its ancestors.")


def search_classes(classes, keyword):
    """Search for classes by keyword (case-insensitive substring match)."""
    keyword_lower = keyword.lower()
    # Deduplicate: only show canonical entries (avoid duplicates from short-name indexing)
    seen_ids = set()
    matches = []
    for name, node in sorted(classes.items()):
        if id(node) in seen_ids:
            continue
        if keyword_lower in name.lower():
            seen_ids.add(id(node))
            bases = get_bases(node)
            parent = bases[0] if bases else ""
            matches.append((name, parent))

    if not matches:
        print(f"No classes matching '{keyword}'.")
        return

    if len(matches) <= 3:
        # Few results — show full interface directly
        print(f'Classes matching "{keyword}" ({len(matches)} found) — showing full interface:\n')
        lookup_classes(classes, [name for name, _ in matches], no_inherited=False)
    else:
        print(f'Classes matching "{keyword}":')
        for name, parent in matches:
            if parent:
                print(f"  {name}({parent})")
            else:
                print(f"  {name}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python d3-pyi-lookup.py ClassName")
        print("  python d3-pyi-lookup.py Class1,Class2,... --search keyword")
        print("  python d3-pyi-lookup.py --no-inherited ClassName")
        print("  python d3-pyi-lookup.py --doc ClassName.methodName")
        print("  python d3-pyi-lookup.py --search <keyword>")
        print("  python d3-pyi-lookup.py --stub PATH ClassName")
        print("  python d3-pyi-lookup.py --help")
        sys.exit(1)

    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        print(__doc__)
        sys.exit(0)

    # Parse flags
    stub_path = None
    if "--stub" in args:
        idx = args.index("--stub")
        if idx + 1 >= len(args):
            print("Usage: python d3-pyi-lookup.py --stub PATH ...", file=sys.stderr)
            sys.exit(1)
        stub_path = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    pyi_path = ensure_stub(stub_path)
    classes = parse_stub(pyi_path)

    no_inherited = False
    if "--no-inherited" in args:
        no_inherited = True
        args.remove("--no-inherited")

    # Extract --search keyword (can appear alongside named classes)
    search_keyword = None
    if "--search" in args:
        idx = args.index("--search")
        if idx + 1 < len(args):
            search_keyword = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print("Usage: python d3-pyi-lookup.py --search <keyword>")
            sys.exit(1)

    if not args and not search_keyword:
        print("Error: no command or class name provided.")
        sys.exit(1)

    if args and args[0] == "--doc":
        if len(args) < 2:
            print("Usage: python d3-pyi-lookup.py --doc ClassName.methodName")
            sys.exit(1)
        doc_lookup(classes, args[1])
        return

    # Named class lookups
    if args:
        names = args[0].split(",")
        lookup_classes(classes, names, no_inherited=no_inherited)

    # Search (standalone or after named lookups)
    if search_keyword:
        if args:
            print("\n---\n")
        search_classes(classes, search_keyword)


if __name__ == "__main__":
    main()
