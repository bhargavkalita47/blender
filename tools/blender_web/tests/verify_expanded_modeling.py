#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Phase 2.2.3: validate new native Blender BMesh primitives/editing and lifecycle."""
import ctypes
import json
import math

from export_extracted_parity import core, xyz

core.web_mesh_create_grid.argtypes = [ctypes.c_int, ctypes.c_int]
core.web_mesh_create_grid.restype = ctypes.c_int
core.web_mesh_create_cylinder.argtypes = [ctypes.c_int]
core.web_mesh_create_cylinder.restype = ctypes.c_int
core.web_mesh_create_uv_sphere.argtypes = [ctypes.c_int, ctypes.c_int]
core.web_mesh_create_uv_sphere.restype = ctypes.c_int
core.web_mesh_select_vertex.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
core.web_mesh_select_vertex.restype = ctypes.c_int
core.web_mesh_selected_vert_count.argtypes = [ctypes.c_int]
core.web_mesh_selected_vert_count.restype = ctypes.c_int
core.web_mesh_transform_selected.argtypes = [ctypes.c_int, ctypes.c_int,
                                              ctypes.c_float, ctypes.c_float, ctypes.c_float]
core.web_mesh_transform_selected.restype = ctypes.c_int
core.web_mesh_delete_face.argtypes = [ctypes.c_int, ctypes.c_int]
core.web_mesh_delete_face.restype = ctypes.c_int

FIXTURES = [
    ("grid_3x2", lambda: core.web_mesh_create_grid(3, 2), (12, 17, 6, 24, 12)),
    ("cylinder_8", lambda: core.web_mesh_create_cylinder(8), (16, 24, 10, 48, 28)),
    ("uv_sphere_8x4", lambda: core.web_mesh_create_uv_sphere(8, 4), (26, 56, 32, 112, 48)),
]


def snapshot(handle):
    assert core.web_mesh_validate_topology(handle) == 0, "BMesh radial and face topology failed"
    values = [getattr(core, f"web_mesh_{key}")(handle)
              for key in ("verts", "edges", "faces", "loops")]
    pcount = core.web_mesh_position_float_count(handle)
    icount = core.web_mesh_triangle_index_count(handle)
    assert pcount == 3 * values[0] and icount >= 0
    assert icount % 3 == 0
    pos = (ctypes.c_float * pcount)()
    idx = (ctypes.c_uint32 * icount)()
    assert core.web_mesh_copy_positions(handle, pos, pcount) == pcount
    assert core.web_mesh_copy_triangles(handle, idx, icount) == icount
    assert all(0 <= n < values[0] for n in idx)
    positions = sorted(xyz(pos[i:i+3]) for i in range(0, pcount, 3))
    assert all(math.isfinite(x) for p in positions for x in p)
    return {"verts":values[0], "edges":values[1], "faces":values[2], "loops":values[3],
            "triangles":icount//3, "positions":[list(p) for p in positions]}


def main():
    for fn, args in ((core.web_mesh_create_grid, (0, 2)),
                     (core.web_mesh_create_grid, (100, 2)),
                     (core.web_mesh_create_cylinder, (2,)),
                     (core.web_mesh_create_cylinder, (70,)),
                     (core.web_mesh_create_uv_sphere, (8, 2)),
                     (core.web_mesh_create_uv_sphere, (8, 40))):
        assert fn(*args) == -4
    assert core.web_mesh_live_count() == 0
    for name, factory, expected in FIXTURES:
        h = factory()
        assert h > 0, (name,h)
        try:
            counts = snapshot(h)
            assert tuple(counts[k] for k in ("verts","edges","faces","loops","triangles")) == expected, (name,counts)
        finally:
            assert core.web_mesh_destroy(h) == 0
            assert core.web_mesh_destroy(h) == -1
    # Selection and transforms live on actual BMVert flags/co, not JS-local state.
    grid = core.web_mesh_create_grid(2, 2)
    cube = core.web_mesh_create_cube()
    assert grid > 0 and cube > 0 and grid != cube
    try:
        before = snapshot(grid)
        cube_before = snapshot(cube)
        assert core.web_mesh_select_vertex(grid, 0, 1) == 0
        assert core.web_mesh_select_vertex(grid, 9, 1) == -2
        assert core.web_mesh_selected_vert_count(grid) == 1
        assert core.web_mesh_transform_selected(grid, 1, .25, 0, 0) == 0
        changed = snapshot(grid)
        assert changed["positions"] != before["positions"]
        assert core.web_mesh_selected_vert_count(grid) == 1
        assert core.web_mesh_transform_selected(grid, 1, math.nan, 0, 0) == -2
        assert snapshot(grid) == changed, "Non-finite translation mutated mesh"
        assert core.web_mesh_transform_selected(grid, 2, 1.25, 0, 0) == 0
        assert core.web_mesh_transform_selected(grid, 3, .1, 0, 0) == 0
        assert core.web_mesh_validate_topology(grid) == 0
        assert core.web_mesh_select_vertex(grid, 0, 0) == 0
        assert core.web_mesh_selected_vert_count(grid) == 0
        assert snapshot(cube) == cube_before
        assert core.web_mesh_delete_face(grid, -1) == -2
    finally:
        assert core.web_mesh_destroy(grid) == 0
        assert core.web_mesh_destroy(cube) == 0

    plane = core.web_mesh_create_plane()
    assert plane > 0
    assert core.web_mesh_delete_face(plane, 0) == 0
    assert [getattr(core,f"web_mesh_{key}")(plane)
            for key in ("verts","edges","faces","loops")] == [0,0,0,0]
    assert core.web_mesh_validate_topology(plane) == 0
    assert core.web_mesh_destroy(plane) == 0
    assert core.web_mesh_delete_face(plane, 0) == -1
    # GuardedAlloc baseline after warm-up; all three shapes are independently freed.
    for _, fn, _ in FIXTURES:
        h=fn()
        assert h>0
        assert core.web_mesh_destroy(h)==0
    baseline = core.web_mesh_memory_bytes()
    for n in range(200):
        for _, fn, _ in FIXTURES:
            h = fn()
            assert h > 0
            assert core.web_mesh_validate_topology(h) == 0
            assert core.web_mesh_destroy(h) == 0
        if (n+1)%50==0:
            assert core.web_mesh_live_count()==0
            assert core.web_mesh_memory_bytes()==baseline
    assert core.web_mesh_memory_bytes()==baseline
    print("BLENDER_WEB_EXPANDED_NATIVE=" + json.dumps({
        "status":"pass", "fixtures":{name:list(expected) for name,_,expected in FIXTURES},
        "new_primitive_lifecycle_cycles":600, "vertex_selection_transforms":True,
        "face_deletion":True, "multi_mesh_independence":True,
        "invalid_parameters_rejected":True, "tracked_allocations_before":baseline,
        "tracked_allocations_after":core.web_mesh_memory_bytes()
    },sort_keys=True))


if __name__=="__main__":
    main()
