#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed Phase 2.2.3 parity for native plane and whole-mesh translate."""
import json
import pathlib
import sys

from compare_reference_parity import (
    PINNED, read_tag, vertices_match, assert_face_records, close,
)

STAGES = ("plane", "translated_plane")
COUNTS = ("verts", "edges", "faces", "loops", "triangles")


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: compare_modeling_ops.py official.log extracted.log report.json")
    original = read_tag(sys.argv[1], "BLENDER_WEB_MODELING_OPS_ORIGINAL=")
    extracted = read_tag(sys.argv[2], "BLENDER_WEB_MODELING_OPS_EXTRACTED=")
    assert original["status"] == extracted["status"] == "pass"
    assert original["source_commit"] == PINNED
    assert original["blender_build_hash"].lower().startswith(PINNED[:12])
    assert original["reference"].startswith("original Blender bmesh.ops.")
    assert extracted["scope"] == "Blender BMesh plane, whole-mesh translation"
    counts = {}
    for stage in STAGES:
        a, b = original["cases"][stage], extracted["cases"][stage]
        for key in COUNTS:
            assert a[key] == b[key], f"{stage}: {key} mismatch {a[key]} != {b[key]}"
        vertices_match(a["positions"], b["positions"], stage+".positions")
        assert len(a["edge_geometry"]) == len(b["edge_geometry"])
        for i, (edge_a, edge_b) in enumerate(zip(a["edge_geometry"], b["edge_geometry"])):
            vertices_match(edge_a, edge_b, f"{stage}.edge[{i}]")
        assert_face_records(a["face_geometry"], b["face_geometry"], stage)
        close(a["surface_area"], b["surface_area"], stage+".area")
        counts[stage] = {key:a[key] for key in COUNTS}
    assert extracted["invalid_float_rejection"] is True
    assert extracted["stale_handle_rejection"] is True
    assert extracted["simultaneous_mesh_isolation"] is True
    assert extracted["stress_cycles"] >= 1000
    assert extracted["memory_before"] == extracted["memory_after"]
    result = {"status":"pass", "milestone":"2.2.3 initial slice",
              "pinned_source_commit":PINNED,
              "reference_build_hash":original["blender_build_hash"],
              "geometry_stages":counts,
              "vertex_edge_face_winding_normal_area_parity":True,
              "boundary_radial_cycle_validation":True,
              "simultaneous_mesh_isolation":True,
              "invalid_parameter_and_stale_handle_rejection":True,
              "native_plane_create_translate_destroy_cycles":extracted["stress_cycles"],
              "native_memory_baseline_equal_final":True,
              "scope_limitation":"plane creation + full-mesh translation only; not 2.2.3 completion"}
    out = pathlib.Path(sys.argv[3])
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print("PHASE_2_2_3_INITIAL=" + json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    main()
