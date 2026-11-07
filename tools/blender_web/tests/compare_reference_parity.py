#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Strict geometry parity: pinned Blender executable versus extracted native core.

This is NOT a UV data-layer equivalence test (Phase 2.2.4). The limited
extracted API triangulates only quads using a fan; native Blender can choose a
different diagonal, so triangulation parity is compared by oriented planar
surface coverage, area and triangle count, not raw triangle index order.
"""
import json
import math
import pathlib
import sys

PINNED = "67e5a5f874cf37e2a114cebd24f219d8c44a16ad"
COUNTS = ("verts", "edges", "faces", "loops", "triangles")
STAGES = ("cube", "extrude_1", "extrude_2")
EPS = 0.0001


def read_tag(path, tag):
    lines = pathlib.Path(path).read_text(errors="replace").splitlines()
    found = [line.split(tag, 1)[1] for line in lines if tag in line]
    assert len(found) == 1, f"Expected one {tag} line in {path}, got {len(found)}"
    # Blender prints its process banner directly after the Python script's
    # final stdout line on some headless builds (no separating newline).
    # Decode exactly one JSON value; do not mistake the Blender banner for
    # a second JSON document or a geometry failure.
    result, _ = json.JSONDecoder().raw_decode(found[0])
    return result


def close(a, b, where, eps=EPS):
    assert math.isfinite(float(a)) and math.isfinite(float(b)), (
        f"{where}: non-finite comparison")
    assert abs(float(a) - float(b)) <= eps, f"{where}: {a} != {b}"


def vertices_match(a, b, where):
    assert len(a) == len(b), f"{where}: size {len(a)} != {len(b)}"
    for i, (u, v) in enumerate(zip(a, b)):
        assert len(u) == len(v), f"{where}/{i}: coordinate arity"
        for axis, (x, y) in enumerate(zip(u, v)):
            close(x, y, f"{where}/{i}/{axis}")


def assert_face_records(ref, got, stage):
    assert len(ref) == len(got), f"{stage}: mismatched faces"
    for i, (a, b) in enumerate(zip(ref, got)):
        vertices_match(a["loop"], b["loop"], f"{stage}.face[{i}].loop")
        vertices_match([a["normal"]], [b["normal"]], f"{stage}.face[{i}].normal")
        close(a["area"], b["area"], f"{stage}.face[{i}].area")


def plane_coverage(faces):
    """Covers surfaces by directed plane, independent of quad split diagonal."""
    acc = {}
    for face in faces:
        n = tuple(0.0 if abs(float(x)) < 1e-6 else round(float(x), 4)
                  for x in face["normal"])
        p = face["loop"][0]
        height = round(sum(n[i] * p[i] for i in range(3)), 4)
        k = (n, height)
        acc[k] = acc.get(k, 0.0) + float(face["area"])
    return {str(k): round(v, 5) for k, v in sorted(acc.items())}


def compare_stages(ref, got):
    for stage in STAGES:
        a = ref[stage]
        b = got[stage]
        for key in COUNTS:
            assert a[key] == b[key], f"{stage}/{key}: {a[key]} vs {b[key]}"
        vertices_match(a["positions"], b["positions"], f"{stage}.positions")
        for i, (edge_a, edge_b) in enumerate(
                zip(a["edge_geometry"], b["edge_geometry"])):
            vertices_match(edge_a, edge_b, f"{stage}.edge[{i}]")
        assert len(a["edge_geometry"]) == len(b["edge_geometry"]), (
            f"{stage}: edge geometry count mismatch")
        assert_face_records(a["face_geometry"], b["face_geometry"], stage)
        close(a["surface_area"], b["surface_area"], f"{stage}.total_area")
    return {stage: {key: ref[stage][key] for key in COUNTS}
            for stage in STAGES}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: compare_reference_parity.py pinned_blender.log "
                         "extracted_core.log report.json")
    official = read_tag(sys.argv[1], "BLENDER_WEB_NATIVE_REFERENCE=")
    extracted = read_tag(sys.argv[2], "BLENDER_WEB_EXTRACTED_REFERENCE=")
    assert official["status"] == extracted["status"] == "pass"
    assert official["pinned_source_commit"] == PINNED
    assert official["blender_build_hash"].lower().startswith(PINNED[:12])
    assert extracted["engine"] == "extracted Blender C++ native core"
    a = official["reference_cases"]
    b = extracted["cases"]
    counts = compare_stages(a, b)
    # Native reference triangulates with Blender's own BEAUTY method.
    # Our quad-fan tessellation can choose a different diagonal but must
    # preserve all oriented face planes and the exact surface area.
    triangles = a["triangulated"]
    assert triangles["faces"] == triangles["triangles"] == b["extrude_2"]["triangles"] == 28
    assert triangles["verts"] == b["extrude_2"]["verts"]
    assert triangles["positions"] == b["extrude_2"]["positions"]
    close(triangles["surface_area"], b["extrude_2"]["surface_area"],
          "triangulated surface area")
    reference_planes = plane_coverage(triangles["face_geometry"])
    extracted_planes = plane_coverage(b["extrude_2"]["face_geometry"])
    assert reference_planes == extracted_planes, (
        "Triangulated surface coverage mismatch: " +
        repr({"original": reference_planes, "extracted": extracted_planes}))
    assert extracted["memory_baseline"] == extracted["memory_final"]
    report = {
        "status": "pass", "milestone": "2.2.2",
        "reference": "Official Blender 5.4 Alpha running source-pinned BMesh Python API",
        "pinned_git_sha": PINNED,
        "reference_build_hash": official["blender_build_hash"],
        "extracted": "Independently linked native original Blender BMesh shared library",
        "coordinate_tolerance": EPS,
        "geometry_parity": counts,
        "face_winding_normal_area_parity": True,
        "canonical_mesh_edges_parity": True,
        "triangles_after_two_extrusions": 28,
        "triangulated_oriented_plane_surface_parity": True,
        "native_memory_baseline_equal_final": True,
        "uv_reference_layer_verified": bool(a.get("native_reference_uv_layer")),
        "uv_parity_with_extracted_core": False,
        "scope": "cube and two Blender discrete-face extrusions; UV/other operators deferred",
    }
    path = pathlib.Path(sys.argv[3])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("PHASE_2_2_2_PARITY=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
