#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Execute Blender's ORIGINAL grid creation + translate operators for parity."""
import json
import pathlib
import sys

import bmesh
import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from native_reference import PINNED, snapshot

DELTA = (.5, -1.0, 2.0)


def main():
    value = bpy.app.build_hash
    build_hash = (value.decode("ascii") if isinstance(value, bytes) else str(value)).lower()
    assert tuple(bpy.app.version)[:2] == (5, 4)
    assert build_hash.startswith(PINNED[:12]), (
        "Official Blender binary does not match original pinned source")
    bm = bmesh.new()
    try:
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
        initial = snapshot(bm)
        assert [initial[k] for k in ("verts", "edges", "faces", "loops", "triangles")] == [
            4, 4, 1, 4, 2]
        assert initial["face_geometry"][0]["normal"] == [0, 0, 1]
        bmesh.ops.translate(bm, verts=list(bm.verts), vec=DELTA)
        translated = snapshot(bm)
        assert translated["verts"] == 4 and translated["faces"] == 1
        cases = {"plane":initial, "translated_plane":translated}
    finally:
        bm.free()
    result = {"status":"pass", "source_commit":PINNED, "blender_build_hash":build_hash,
              "reference":"original Blender bmesh.ops.create_grid and bmesh.ops.translate",
              "cases":cases}
    print("BLENDER_WEB_MODELING_OPS_ORIGINAL=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
