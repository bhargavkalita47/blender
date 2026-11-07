#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Conservative, reproducible source-level Blender dependency inventory.

Run from a complete checkout:
  python3 tools/blender_web/dependencies/audit_static.py \
    --root . --out build/blender_web/dependency-audit.json

No third-party packages are needed. This is deliberately a STATIC scanner,
not a CMake interpreter, compiler, linker, or a proof of runtime reachability.
Ambiguous and unresolved includes are reported rather than guessed.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

CM_CALL = re.compile(
    r"\b(set|list|blender_add_lib|target_link_libraries|add_dependencies|if|elseif|else|endif)\s*\(",
    re.IGNORECASE,
)
INCLUDE = re.compile(r'^\s*#\s*include\s*([<"])([^>"]+)[>"]', re.MULTILINE)
CPP_SUFFIXES = {".h", ".hh", ".hpp", ".hxx", ".c", ".cc", ".cpp", ".cxx", ".mm"}
SEEDS = [
    "source/blender/geometry/intern/mesh_primitive_cuboid.cc",
    "source/blender/bmesh/operators/bmo_extrude.cc",
]


def cmake_commands(source: str):
    """Yield (command, argument text, line) for balanced CMake calls.

    Handles nested parentheses and quotes, but not all CMake generator
    expressions or bracket-quoted strings. Conditions are preserved as
    source expressions, not evaluated.
    """
    for match in CM_CALL.finditer(source):
        start = match.end()
        depth, quoted, escaped = 1, False, False
        i = start
        while i < len(source) and depth:
            ch = source[i]
            if escaped:
                escaped = False
            elif ch == "\\" and quoted:
                escaped = True
            elif ch == '"':
                quoted = not quoted
            elif not quoted and ch == "(":
                depth += 1
            elif not quoted and ch == ")":
                depth -= 1
            i += 1
        if depth == 0:
            yield match.group(1).lower(), source[start : i - 1], source.count("\n", 0, match.start()) + 1


def atoms(s: str):
    s = re.sub(r"(?m)^\s*#.*$", "", s)
    return [part.strip('"') for part in re.findall(r'"(?:\\.|[^"\\])*"|[^\s]+', s)]


def target_of(token: str) -> str:
    if token.startswith("bf::dependencies::"):
        return ""
    if token.startswith("bf::"):
        return "bf_" + token[4:].replace("::", "_")
    if token.startswith("bf_"):
        return token
    return ""


def collect_cmake(root: Path):
    declared = {}
    edges = []
    build_order = []
    for path in sorted(root.rglob("CMakeLists.txt")):
        if ".git" in path.parts or "build" in path.parts:
            continue
        if "extern" in path.parts or "lib" in path.parts:
            # Not needed for internal Blender target SCCs, still documented separately.
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        lib_args = []
        qualifiers = []
        conds = []
        rel = path.relative_to(root).as_posix()
        for command, body, line in cmake_commands(source):
            values = atoms(body)
            if command == "if":
                conds.append(" ".join(values))
            elif command == "elseif":
                if conds:
                    conds[-1] = "elseif " + " ".join(values)
            elif command == "else":
                if conds:
                    conds[-1] = "else(" + conds[-1] + ")"
            elif command == "endif":
                if conds:
                    conds.pop()
            elif command == "set" and values and values[0] == "LIB":
                lib_args = [(x, " && ".join(conds), line) for x in values[1:]]
            elif command == "list" and len(values) > 2 and values[:2] == ["APPEND", "LIB"]:
                lib_args.extend((x, " && ".join(conds), line) for x in values[2:])
            elif command == "blender_add_lib" and values:
                owner = values[0]
                declared[owner] = rel
                for token, condition, source_line in lib_args:
                    dep = target_of(token)
                    if dep and dep != owner:
                        edges.append(dict(src=owner, dst=dep, condition=condition,
                                          path=rel, line=source_line, kind="link"))
            elif command == "target_link_libraries" and len(values) > 1:
                owner = values[0]
                for token in values[1:]:
                    dep = target_of(token)
                    if dep and dep != owner:
                        edges.append(dict(src=owner, dst=dep, condition=" && ".join(conds),
                                          path=rel, line=line, kind="link"))
            elif command == "add_dependencies" and len(values) > 1:
                owner = values[0]
                for token in values[1:]:
                    build_order.append(dict(src=owner, dst=token, condition=" && ".join(conds),
                                            path=rel, line=line, kind="build-order"))
    # Keep only unique declared library edges for structural analysis,
    # while retaining all raw records with provenance.
    adjacency = {name: set() for name in declared}
    for e in edges:
        if e["src"] in adjacency and e["dst"] in adjacency:
            adjacency[e["src"]].add(e["dst"])
    return declared, edges, build_order, adjacency


def tarjan(adjacency):
    index = 0
    stack = []
    visiting = set()
    indices, lowlinks = {}, {}
    groups = []

    def visit(node):
        nonlocal index
        indices[node] = lowlinks[node] = index
        index += 1
        stack.append(node)
        visiting.add(node)
        for other in sorted(adjacency[node]):
            if other not in indices:
                visit(other)
                lowlinks[node] = min(lowlinks[node], lowlinks[other])
            elif other in visiting:
                lowlinks[node] = min(lowlinks[node], indices[other])
        if lowlinks[node] == indices[node]:
            group = []
            while True:
                current = stack.pop()
                visiting.remove(current)
                group.append(current)
                if current == node:
                    break
            groups.append(sorted(group))

    for name in sorted(adjacency):
        if name not in indices:
            visit(name)
    return sorted(groups, key=lambda group: (-len(group), group))


def header_index(root):
    by_name = defaultdict(list)
    for base in (root / "source", root / "intern"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in CPP_SUFFIXES:
                by_name[path.name].append(path)
    return by_name


def include_resolution(current: Path, requested: str, index):
    # A relative include is preferred; then an indexed unique include.
    direct = current.parent / requested
    if direct.is_file():
        return direct, []
    candidates = index.get(Path(requested).name, [])
    matches = [p for p in candidates if p.as_posix().endswith(requested)]
    if len(matches) == 1:
        return matches[0], []
    if len(matches) > 1:
        return None, matches
    if len(candidates) == 1 and "/" not in requested:
        return candidates[0], []
    return None, candidates


def collect_source_closure(root, index, seed):
    initial = root / seed
    if not initial.is_file():
        return {"error": "seed missing", "seed": seed}
    pending = [initial]
    visited = set()
    ambiguous = []
    unresolved = []
    external = set()
    include_edges = []
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        data = current.read_text(encoding="utf-8", errors="replace")
        for kind, name in INCLUDE.findall(data):
            if kind == "<":
                external.add(name)
                continue
            resolved, alternatives = include_resolution(current, name, index)
            source = current.relative_to(root).as_posix()
            if resolved is None:
                record = {"source": source, "include": name}
                if alternatives:
                    record["candidates"] = [p.relative_to(root).as_posix() for p in alternatives]
                    ambiguous.append(record)
                else:
                    unresolved.append(record)
            else:
                target = resolved.relative_to(root).as_posix()
                include_edges.append((source, target))
                if resolved not in visited:
                    pending.append(resolved)
    return {
        "seed": seed,
        "files": sorted(p.relative_to(root).as_posix() for p in visited),
        "include_edges": sorted(set(include_edges)),
        "external_includes": sorted(external),
        "ambiguous": ambiguous,
        "unresolved": unresolved,
        "limitations": [
            "No compile preprocessor configuration; conditional includes may be included.",
            "Header include resolution is filename/path based, not compiler -I ordered.",
            "This traces headers, not undefined symbols, required .cc objects, or runtime calls.",
            "Generated headers can appear unresolved until a native CMake configure/build.",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("build/blender_web/dependency-audit.json"))
    ap.add_argument("--seed", action="append", default=[])
    args = ap.parse_args()
    root = args.root.resolve()
    declared, edges, order, adjacency = collect_cmake(root)
    index = header_index(root)
    seeds = args.seed or SEEDS
    report = {
        "status": "static inventory only; no configured native build or linker proof",
        "declared_internal_targets": declared,
        "link_edges": edges,
        "build_order_edges": order,
        "sccs": tarjan(adjacency),
        "seed_closures": [collect_source_closure(root, index, seed) for seed in seeds],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Targets: {len(declared)}; link records: {len(edges)}; "
          f"SCCs: {len(report['sccs'])}; source seeds: {len(seeds)}")
    print(f"Report: {args.out}")
    print("WARNING: this is not a compiled/link-resolved dependency closure")


if __name__ == "__main__":
    main()
