# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Native Blender modeling reference, run with Blender's own Python.

Example:
  blender --background --factory-startup --threads 1 \
    --python tools/blender_web/tests/native_reference.py

This tests Blender's EXISTING BMesh behavior. It does not test an extracted
library, prove WASM compatibility, or replace sanitizer/memory testing.
"""

import hashlib
import json
import math
import sys

import bmesh
import bpy


def assert_mesh_is_finite_and_non_degenerate(bm):
    for vert in bm.verts:
        assert all(math.isfinite(float(coord)) for coord in vert.co), "non-finite coordinate"
    for face in bm.faces:
        assert face.calc_area() > 0.0, "zero-area face"


def snapshot(bm):
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.verts.index_update()
    bm.faces.index_update()

    positions = sorted(
        (round(float(v.co.x), 6), round(float(v.co.y), 6), round(float(v.co.z), 6))
        for v in bm.verts
    )
    payload = json.dumps(positions, separators=(",", ":"), sort_keys=True)
    return {
        "verts": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "triangulated_face_count": sum(len(face.verts) - 2 for face in bm.faces),
        "position_digest": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def test_bmesh_native():
    bm = bmesh.new()
    try:
        bmesh.ops.create_cube(bm, size=2.0)
        bm.normal_update()
        assert_mesh_is_finite_and_non_degenerate(bm)
        initial = snapshot(bm)
        assert (initial["verts"], initial["edges"], initial["faces"]) == (8, 12, 6), initial

        # Verify UV custom-data on the editable topology.
        layer = bm.loops.layers.uv.verify()
        for face in bm.faces:
            for loop in face.loops:
                loop[layer].uv = (
                    float(loop.vert.co.x) * 0.5 + 0.5,
                    float(loop.vert.co.y) * 0.5 + 0.5,
                )
        assert sum(len(face.loops) for face in bm.faces) == 24

        # Choose the upper face from actual normals, not an assumed face index.
        upper = max(bm.faces, key=lambda face: float(face.normal.z))
        assert upper.normal.z > 0.99
        result = bmesh.ops.extrude_discrete_faces(bm, faces=[upper])
        caps = result["faces"]
        assert len(caps) == 1, "expected a single extruded cap"
        for vertex in caps[0].verts:
            vertex.co.z += 1.0
        bm.normal_update()
        assert_mesh_is_finite_and_non_degenerate(bm)

        extruded = snapshot(bm)
        assert extruded["verts"] > initial["verts"], extruded
        assert extruded["faces"] > initial["faces"], extruded

        # Triangulation converts n-gons/quads into the representation
        # a browser renderer would typically consume.
        bmesh.ops.triangulate(
            bm,
            faces=list(bm.faces),
            quad_method="BEAUTY",
            ngon_method="BEAUTY",
        )
        bm.normal_update()
        assert_mesh_is_finite_and_non_degenerate(bm)
        triangulated = snapshot(bm)
        assert all(len(face.verts) == 3 for face in bm.faces)
        assert triangulated["faces"] == extruded["triangulated_face_count"]
        return {
            "initial_cube": initial,
            "extruded": extruded,
            "triangulated": triangulated,
            "uv_layer": True,
        }
    finally:
        bm.free()


def main():
    version = tuple(bpy.app.version)
    assert version[:2] == (5, 4), "Use pinned Blender 5.4 Alpha for this reference test"
    result = {"version": bpy.app.version_string, "bmesh": test_bmesh_native()}
    print("BLENDER_WEB_NATIVE_REFERENCE=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
