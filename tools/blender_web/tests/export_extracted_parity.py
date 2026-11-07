#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Capture identical geometry cases through the extracted native Blender core ABI."""
import ctypes
import json
import math
import pathlib
import sys

library = pathlib.Path(sys.argv[1]).resolve()
assert library.is_file(), f"Missing extracted Blender core: {library}"
core = ctypes.CDLL(str(library))
core.web_mesh_create_cube.restype = ctypes.c_int
core.web_mesh_destroy.argtypes = [ctypes.c_int]
core.web_mesh_extrude_top.argtypes = [ctypes.c_int, ctypes.c_float]
core.web_mesh_top_z.argtypes = [ctypes.c_int]
core.web_mesh_top_z.restype = ctypes.c_float
core.web_mesh_copy_positions.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_float),
                                          ctypes.c_int]
core.web_mesh_copy_triangles.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint32),
                                          ctypes.c_int]
for name in ("web_mesh_destroy", "web_mesh_extrude_top", "web_mesh_copy_positions",
             "web_mesh_copy_triangles"):
    getattr(core, name).restype = ctypes.c_int
for name in ("web_mesh_verts", "web_mesh_edges", "web_mesh_faces", "web_mesh_loops",
             "web_mesh_position_float_count", "web_mesh_triangle_index_count",
             "web_mesh_validate_topology"):
    getattr(core, name).argtypes = [ctypes.c_int]
    getattr(core, name).restype = ctypes.c_int
core.web_mesh_memory_bytes.restype = ctypes.c_int
core.web_mesh_live_count.restype = ctypes.c_int


def xyz(vector):
    return tuple(round(float(v), 6) for v in vector)


def canonical_loop(points):
    points = tuple(points)
    return min(points[n:] + points[:n] for n in range(len(points)))


def sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def face_record(points):
    a, b, c, d = points
    n1 = cross(sub(b, a), sub(c, a))
    n2 = cross(sub(c, a), sub(d, a))
    v = tuple(n1[i]+n2[i] for i in range(3))
    length = math.sqrt(sum(x*x for x in v))
    assert length > 1e-9, "Degenerate Blender quad in native export"
    area = (math.sqrt(sum(x*x for x in n1)) +
            math.sqrt(sum(x*x for x in n2))) / 2.0
    assert area > 0
    return {"loop": [list(p) for p in canonical_loop(points)],
            "normal": list(xyz(tuple(x/length for x in v))),
            "area": round(area, 6)}


def snapshot(handle):
    assert core.web_mesh_validate_topology(handle) == 0
    vertex_count = core.web_mesh_verts(handle)
    edge_count = core.web_mesh_edges(handle)
    face_count = core.web_mesh_faces(handle)
    loop_count = core.web_mesh_loops(handle)
    npos = core.web_mesh_position_float_count(handle)
    nidx = core.web_mesh_triangle_index_count(handle)
    assert npos == 3*vertex_count
    assert nidx == 6*face_count  # Quad-only Phase 2.2 native fixture.
    positions_buffer = (ctypes.c_float * npos)()
    indices_buffer = (ctypes.c_uint32 * nidx)()
    assert core.web_mesh_copy_positions(handle, positions_buffer, npos) == npos
    assert core.web_mesh_copy_triangles(handle, indices_buffer, nidx) == nidx
    verts = [xyz(positions_buffer[i:i+3]) for i in range(0, npos, 3)]
    positions = sorted(verts)
    indices = list(indices_buffer)
    assert all(0 <= i < vertex_count for i in indices), "Invalid native triangle index"
    edge_set = set()
    faces = []
    for i in range(0, nidx, 6):
        a, b, c, a2, c2, d = indices[i:i+6]
        assert a == a2 and c == c2, "Not expected quad-fan triangulation"
        assert len({a, b, c, d}) == 4
        points = [verts[k] for k in (a, b, c, d)]
        faces.append(face_record(points))
        for u, v in zip(points, points[1:] + points[:1]):
            edge_set.add(tuple(sorted((u, v))))
    assert len(edge_set) == edge_count
    faces.sort(key=lambda r: r["loop"])
    return {"verts": vertex_count, "edges": edge_count, "faces": face_count,
            "loops": loop_count, "triangles": nidx//3,
            "positions": [list(p) for p in positions],
            "edge_geometry": [[list(p) for p in edge] for edge in sorted(edge_set)],
            "face_geometry": faces,
            "surface_area": round(sum(f["area"] for f in faces), 6)}


def main():
    # Warm-up is intentionally excluded from the snapshot geometry cases.
    assert core.web_mesh_live_count() == 0
    baseline = core.web_mesh_memory_bytes()
    h = core.web_mesh_create_cube()
    assert h > 0
    try:
        cases = {"cube": snapshot(h)}
        assert core.web_mesh_top_z(h) == 1.0
        assert core.web_mesh_extrude_top(h, ctypes.c_float(1.0)) == 0
        cases["extrude_1"] = snapshot(h)
        assert core.web_mesh_top_z(h) == 2.0
        assert core.web_mesh_extrude_top(h, ctypes.c_float(.5)) == 0
        cases["extrude_2"] = snapshot(h)
        assert core.web_mesh_top_z(h) == 2.5
    finally:
        assert core.web_mesh_destroy(h) == 0
    assert core.web_mesh_live_count() == 0
    assert core.web_mesh_memory_bytes() == baseline
    result = {"status": "pass", "engine": "extracted Blender C++ native core",
              "cases": cases, "memory_baseline": baseline,
              "memory_final": core.web_mesh_memory_bytes(),
              "native_uv_parity_supported": False}
    print("BLENDER_WEB_EXTRACTED_REFERENCE=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
