#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Discover candidate source definitions for two concrete Blender modeling paths.

Scans the entire checked-out source/ and intern/ trees once. This finds text
occurrences and checks known provider files, NOT actual symbol linkage or
preprocessor-dependent compilation. See Phase 1.2 notes.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

# Key functions from the inspected cuboid and BMesh-extrusion call paths.
PROVIDERS = {
    "create_cuboid_mesh": "source/blender/geometry/intern/mesh_primitive_cuboid.cc",
    "calculate_uvs": "source/blender/geometry/intern/mesh_primitive_cuboid.cc",
    "BKE_mesh_new_nomain": "source/blender/blenkernel/intern/mesh.cc",
    "mesh_new_no_attributes": "source/blender/blenkernel/intern/mesh.cc",
    "mesh_ensure_required_data_layers": "source/blender/blenkernel/intern/mesh.cc",
    "mesh_smooth_set": "source/blender/blenkernel/intern/mesh.cc",
    "mesh_calc_edges": "source/blender/blenkernel/intern/mesh_calc_edges.cc",
    "BKE_libblock_alloc": "source/blender/blenkernel/intern/lib_id.cc",
    "BKE_libblock_init_empty": "source/blender/blenkernel/intern/lib_id.cc",
    "BM_mesh_create": "source/blender/bmesh/intern/bmesh_mesh.cc",
    "BM_mesh_free": "source/blender/bmesh/intern/bmesh_mesh.cc",
    "BM_face_create_quad_tri": "source/blender/bmesh/intern/bmesh_construct.cc",
    "BM_select_history_map_create": "source/blender/bmesh/intern/bmesh_marking.cc",
    "BMO_op_callf": "source/blender/bmesh/intern/bmesh_operators.cc",
    "BMO_slot_bool_get": "source/blender/bmesh/intern/bmesh_operators.cc",
    "BMO_slot_buffer_from_enabled_flag": "source/blender/bmesh/intern/bmesh_operators.cc",
    "bmo_extrude_discrete_faces_exec": "source/blender/bmesh/operators/bmo_extrude.cc",
}
EXTRA_SYMBOLS = {
    "BM_face_copy", "BM_elem_attrs_copy", "BMO_op_initf",
    "BMO_op_exec", "bmo_delete_context_exec",
}
EXT = {".cc", ".c", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".mm"}
PATTERN = re.compile(
    r"\b(" + "|".join(map(re.escape, sorted(PROVIDERS.keys() | EXTRA_SYMBOLS, key=len, reverse=True))) + r")\s*\("
)


def run(root: Path):
    matches = defaultdict(list)
    total_files = 0
    for base in (root / "source", root / "intern"):
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in EXT:
                continue
            total_files += 1
            rel = path.relative_to(root).as_posix()
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for idx, line in enumerate(lines, 1):
                for symbol in set(PATTERN.findall(line)):
                    matches[symbol].append({
                        "path": rel, "line": idx, "text": line.strip()[:220]
                    })
    checks = []
    for symbol, expected in sorted(PROVIDERS.items()):
        hits = [hit for hit in matches[symbol] if hit["path"] == expected]
        checks.append({
            "symbol": symbol, "expected_source": expected,
            "found_in_expected_source": bool(hits), "source_hits": hits[:15],
            "other_paths": sorted({hit["path"] for hit in matches[symbol] if hit["path"] != expected})[:25],
        })
    return {
        "status": "textual symbol occurrences; not linker-resolved",
        "scanned_source_files": total_files,
        "provider_checks": checks,
        "candidate_occurrences": {s: matches[s][:40] for s in sorted(matches)},
        "limitations": [
            "Text search also sees declarations and calls, not only definitions.",
            "Preprocessor flags, generated source and CMake include paths are not evaluated.",
            "The exact object-file/transitive linker closure must be established by a native compile/link.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("build/blender_web/symbol-candidates.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    report = run(root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failures = [c for c in report["provider_checks"] if not c["found_in_expected_source"]]
    print(f"Scanned {report['scanned_source_files']} source files; "
          f"{len(report['provider_checks'])} expected symbol providers; "
          f"{len(failures)} missing from expected sources")
    for check in failures:
        print(f"MISSING: {check['symbol']} in {check['expected_source']}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
