#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Blender-5.4 original BMesh creation operators, pinned-build reference."""
import json
import math
import sys
import pathlib

import bmesh
import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from native_reference import PINNED, xyz


def capture(name, call):
    bm = bmesh.new()
    try:
        call(bm)
        positions = sorted(xyz(v.co) for v in bm.verts)
        # Original Blender operator, face winding and edge topology remain authoritative.
        return {
            "name":name, "verts":len(bm.verts), "edges":len(bm.edges),
            "faces":len(bm.faces), "loops":sum(len(f.loops) for f in bm.faces),
            "triangles":sum(len(f.verts)-2 for f in bm.faces),
            "positions":[list(p) for p in positions],
            "bbox_min":[min(p[i] for p in positions) for i in range(3)],
            "bbox_max":[max(p[i] for p in positions) for i in range(3)]
        }
    finally:
        bm.free()


def main():
    build_hash=bpy.app.build_hash
    if isinstance(build_hash,bytes):
        build_hash=build_hash.decode("ascii")
    assert tuple(bpy.app.version)[:2] == (5, 4)
    assert str(build_hash).lower().startswith(PINNED[:12])
    results = {}
    results["grid_3x2"] = capture(
        "grid_3x2",
        lambda bm: bmesh.ops.create_grid(
            bm, x_segments=3, y_segments=2, size=1.0, calc_uvs=False))
    results["cylinder_8"] = capture(
        "cylinder_8",
        lambda bm: bmesh.ops.create_cone(
            bm, cap_ends=True, cap_tris=False, segments=8,
            radius1=1.0, radius2=1.0, depth=2.0, calc_uvs=False))
    results["uv_sphere_8x4"] = capture(
        "uv_sphere_8x4",
        lambda bm: bmesh.ops.create_uvsphere(
            bm, u_segments=8, v_segments=4, radius=1.0, calc_uvs=False))
    def poke_plane(bm):
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
        bmesh.ops.poke(bm, faces=list(bm.faces), offset=0.0,
                       center_mode="MEAN_WEIGHTED", use_relative_offset=False)
    results["poked_plane"] = capture("poked_plane", poke_plane)
    result = {"status":"pass","blender_build_hash":str(build_hash).lower(),
              "pinned_source_sha":PINNED,"shapes":results}
    print("BLENDER_WEB_EXPANDED_ORIGINAL=" + json.dumps(result,sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
