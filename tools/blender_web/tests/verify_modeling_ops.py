#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independent native BMesh API regression for Phase 2.2.3 initial operations."""
import ctypes
import json
import math
import sys

from export_extracted_parity import core, snapshot

core.web_mesh_create_plane.restype = ctypes.c_int
core.web_mesh_translate.argtypes = [ctypes.c_int, ctypes.c_float,
                                    ctypes.c_float, ctypes.c_float]
core.web_mesh_translate.restype = ctypes.c_int

DELTA = (.5, -1.0, 2.0)


def check_plane(mesh, translation=(0.0, 0.0, 0.0)):
    assert [mesh[k] for k in ("verts", "edges", "faces", "loops", "triangles")] == [
        4, 4, 1, 4, 2]
    expected = sorted([[x + translation[0], y + translation[1], translation[2]]
                       for x in (-1.0, 1.0) for y in (-1.0, 1.0)])
    assert mesh["positions"] == expected, (mesh["positions"], expected)
    assert mesh["surface_area"] == 4
    assert mesh["face_geometry"][0]["normal"] == [0.0, 0.0, 1.0]


def check_unsafe_arguments(plane, original):
    for v in (math.nan, math.inf, -math.inf):
        assert core.web_mesh_translate(plane, ctypes.c_float(v), 0, 0) == -2
        assert snapshot(plane) == original, "Invalid translation modified mesh"
    assert core.web_mesh_translate(-1, 0, 0, 0) == -1
    assert core.web_mesh_extrude_top(plane, 1) == -1, (
        "Cube-specific top-cap extrusion should not silently operate on open plane")


def main():
    assert core.web_mesh_live_count() == 0
    # Allocator cache warmup precedes the measured baseline.
    for _ in range(16):
        h = core.web_mesh_create_plane()
        assert h > 0
        assert core.web_mesh_destroy(h) == 0
    baseline = core.web_mesh_memory_bytes()
    plane = core.web_mesh_create_plane()
    cube = core.web_mesh_create_cube()
    assert plane > 0 and cube > 0 and plane != cube
    cases = {}
    try:
        cases["plane"] = snapshot(plane)
        check_plane(cases["plane"])
        cube_before = snapshot(cube)
        check_unsafe_arguments(plane, cases["plane"])
        assert core.web_mesh_translate(plane, *DELTA) == 0
        cases["translated_plane"] = snapshot(plane)
        check_plane(cases["translated_plane"], DELTA)
        assert snapshot(cube) == cube_before, "Translating one mesh modified another"
        # Reversed translation restores original exact positions and normals.
        assert core.web_mesh_translate(plane, *(-v for v in DELTA)) == 0
        assert snapshot(plane) == cases["plane"]
    finally:
        assert core.web_mesh_destroy(cube) == 0
        assert core.web_mesh_destroy(plane) == 0
    assert core.web_mesh_translate(plane, 0, 0, 1) == -1
    assert core.web_mesh_validate_topology(plane) == -1
    assert core.web_mesh_live_count() == 0
    assert core.web_mesh_memory_bytes() == baseline
    for cycle in range(1000):
        h = core.web_mesh_create_plane()
        assert h > 0
        assert core.web_mesh_validate_topology(h) == 0
        assert core.web_mesh_translate(h, *DELTA) == 0
        assert core.web_mesh_destroy(h) == 0
        if (cycle + 1) % 100 == 0:
            assert core.web_mesh_memory_bytes() == baseline
    assert core.web_mesh_live_count() == 0
    assert core.web_mesh_memory_bytes() == baseline
    result = {"status":"pass", "scope":"Blender BMesh plane, whole-mesh translation",
              "cases":cases, "simultaneous_mesh_isolation":True,
              "invalid_float_rejection":True,
              "stale_handle_rejection":True,
              "stress_cycles":1000,
              "memory_before":baseline, "memory_after":core.web_mesh_memory_bytes()}
    print("BLENDER_WEB_MODELING_OPS_EXTRACTED=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
