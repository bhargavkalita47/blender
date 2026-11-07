# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reference geometry emitted by the *actual pinned Blender executable*.

Run using official Blender 5.4 Alpha built from pinned source SHA, never system
Python or a different Blender release. The comparison runner checks build_hash
and refuses to accept any unmatching Blender binary.
"""
import json
import math
import os
import sys

import bmesh
import bpy

PINNED = "67e5a5f874cf37e2a114cebd24f219d8c44a16ad"


def xyz(vector):
    return tuple(round(float(v), 6) for v in vector)


def canonical_loop(points):
    points = tuple(points)
    assert len(points) >= 3
    # A cyclic rotation leaves face winding intact; reversal does not.
    return min(points[n:] + points[:n] for n in range(len(points)))


def face_record(points, normal, area):
    return {"loop": [list(p) for p in canonical_loop(points)],
            "normal": list(xyz(normal)), "area": round(float(area), 6)}


def snapshot(bm):
    bm.normal_update()
    for v in bm.verts:
        assert all(math.isfinite(float(x)) for x in v.co)
    for face in bm.faces:
        assert face.calc_area() > 0.0, "degenerate face"
    positions = sorted(xyz(v.co) for v in bm.verts)
    edges = sorted(tuple(sorted((xyz(e.verts[0].co), xyz(e.verts[1].co))))
                   for e in bm.edges)
    faces = sorted((face_record([xyz(loop.vert.co) for loop in face.loops],
                                face.normal, face.calc_area()) for face in bm.faces),
                   key=lambda r: r["loop"])
    return {
        "verts": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "loops": sum(len(f.loops) for f in bm.faces),
        "triangles": sum(len(f.loops) - 2 for f in bm.faces),
        "positions": [list(p) for p in positions],
        "edge_geometry": [[list(p) for p in edge] for edge in edges],
        "face_geometry": faces,
        "surface_area": round(sum(f.calc_area() for f in bm.faces), 6),
    }


def move_extruded_cap(bm, face, amount):
    result = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
    caps = result["faces"]
    assert len(caps) == 1, "Expected one Blender BMO extruded top cap"
    for v in caps[0].verts:
        v.co.z += amount
    bm.normal_update()
    return caps[0]


def test_mesh():
    bm = bmesh.new()
    try:
        bmesh.ops.create_cube(bm, size=2.0)
        bm.normal_update()
        initial = snapshot(bm)
        assert (initial["verts"], initial["edges"], initial["faces"], initial["loops"]) == (
            8, 12, 6, 24)

        # This is a Blender reference UV sanity gate, NOT a parity claim for the
        # reduced core; native UV layer transfer belongs to Phase 2.2.4.
        layer = bm.loops.layers.uv.verify()
        for face in bm.faces:
            for loop in face.loops:
                loop[layer].uv = (float(loop.vert.co.x) * .5 + .5,
                                  float(loop.vert.co.y) * .5 + .5)
        assert sum(len(face.loops) for face in bm.faces) == 24
        upper = max(bm.faces, key=lambda face: float(face.normal.z))
        assert upper.normal.z > .99
        top = move_extruded_cap(bm, upper, 1.0)
        after1 = snapshot(bm)
        assert (after1["verts"], after1["edges"], after1["faces"], after1["loops"]) == (
            12, 20, 10, 40)
        move_extruded_cap(bm, top, .5)
        after2 = snapshot(bm)
        assert (after2["verts"], after2["edges"], after2["faces"], after2["loops"]) == (
            16, 28, 14, 56)

        bmesh.ops.triangulate(bm, faces=list(bm.faces),
                              quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.normal_update()
        triangulated = snapshot(bm)
        assert triangulated["faces"] == 28
        assert all(len(face.verts) == 3 for face in bm.faces)
        return {"cube": initial, "extrude_1": after1, "extrude_2": after2,
                "triangulated": triangulated, "native_reference_uv_layer": True}
    finally:
        bm.free()


def main():
    build_hash = bpy.app.build_hash
    if isinstance(build_hash, bytes):
        build_hash = build_hash.decode("ascii", errors="replace")
    build_hash = str(build_hash).lower()
    assert tuple(bpy.app.version)[:2] == (5, 4), "Not Blender 5.4"
    assert build_hash.startswith(PINNED[:12]), (
        "Reference is not built from the pinned Blender commit: " + build_hash)
    result = {"status": "pass", "reference": "official Blender 5.4 Alpha",
              "pinned_source_commit": PINNED,
              "blender_build_hash": build_hash,
              "blender_version": bpy.app.version_string,
              "reference_cases": test_mesh()}
    print("BLENDER_WEB_NATIVE_REFERENCE=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
