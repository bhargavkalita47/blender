#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Regression for original Blender BMesh triangulation and triangle/UV corner maps.

The independently built native Blender core is invoked through its public C ABI.
The supplied geometry includes concave n-gons for which fan triangulation is
mathematically incorrect. No Python geometry is used to generate export values.
"""
import ctypes as C
import json
import math
import sys

assert __debug__, "Python assertions must be enabled"
lib = C.CDLL(sys.argv[1])
I = C.c_int
F = C.c_float
U = C.c_uint32
lib.web_mesh_create_polygon_xy.argtypes = [C.POINTER(F), I]
lib.web_mesh_create_polygon_xy.restype = I
lib.web_mesh_create_cube.restype = I
for name in ("destroy", "validate_topology", "position_float_count",
             "triangle_index_count", "uv_layer_ensure", "uv_float_count"):
    fn = getattr(lib, "web_mesh_" + name)
    fn.argtypes = [I]
    fn.restype = I
lib.web_mesh_copy_positions.argtypes = [I, C.POINTER(F), I]
lib.web_mesh_copy_triangles.argtypes = [I, C.POINTER(U), I]
lib.web_mesh_copy_triangle_corners.argtypes = [I, C.POINTER(U), I]
lib.web_mesh_copy_uvs.argtypes = [I, C.POINTER(F), I]
lib.web_mesh_set_uv.argtypes = [I, I, I, F, F]
lib.web_mesh_translate.argtypes = [I, F, F, F]
lib.web_mesh_named_uv_layer_count.argtypes = [I]
lib.web_mesh_uv_layer_ensure_named.argtypes = [I, C.c_char_p]
lib.web_mesh_set_uv_named.argtypes = [I, C.c_char_p, I, I, F, F]
lib.web_mesh_copy_uvs_named.argtypes = [I, C.c_char_p, C.POINTER(F), I]
lib.web_mesh_face_normal_float_count.argtypes = [I]
lib.web_mesh_copy_face_normals.argtypes = [I, C.POINTER(F), I]
lib.web_mesh_extrude_top.argtypes = [I, F]
lib.web_mesh_extrude_face_z.argtypes = [I, I, F]
lib.web_mesh_extrude_top.restype = I
lib.web_mesh_extrude_face_z.restype = I
lib.web_mesh_live_count.restype = I
lib.web_mesh_memory_bytes.restype = I


def new_polygon(points):
    xy = [coordinate for p in points for coordinate in p]
    array = (F * len(xy))(*xy)
    return lib.web_mesh_create_polygon_xy(array, len(points))


def checked_polygon(points):
    h = new_polygon(points)
    assert h > 0, (h, points)
    assert lib.web_mesh_validate_topology(h) == 0
    expected_area = abs(math.fsum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points)))) * .5
    p_count = lib.web_mesh_position_float_count(h)
    t_count = lib.web_mesh_triangle_index_count(h)
    assert p_count == len(points) * 3
    assert t_count == (len(points) - 2) * 3
    pos = (F * p_count)()
    tris = (U * t_count)()
    corners = (U * t_count)()
    assert lib.web_mesh_copy_positions(h, pos, p_count) == p_count
    assert lib.web_mesh_copy_triangles(h, tris, t_count) == t_count
    assert lib.web_mesh_copy_triangle_corners(h, corners, t_count) == t_count
    short = (U * (t_count - 1))()
    assert lib.web_mesh_copy_triangle_corners(h, short, t_count - 1) == -2
    assert lib.web_mesh_copy_triangles(h, short, t_count - 1) == -2

    areas = []
    for offset in range(0, t_count, 3):
        a, b, c = (int(tris[offset + j]) for j in range(3))
        p0, p1, p2 = ([pos[3 * k], pos[3 * k + 1]] for k in (a, b, c))
        areas.append(abs((p1[0] - p0[0]) * (p2[1] - p0[1])
                         - (p1[1] - p0[1]) * (p2[0] - p0[0])) / 2)
    assert math.isclose(math.fsum(areas), expected_area, rel_tol=1e-5, abs_tol=1e-5), (
        math.fsum(areas), expected_area)

    assert lib.web_mesh_uv_layer_ensure(h) == 0
    for i, _ in enumerate(points):
        assert lib.web_mesh_set_uv(h, 0, i, F(i / 128), F((i + 1) / 256)) == 0
    uv_count = lib.web_mesh_uv_float_count(h)
    assert uv_count == len(points) * 2
    uv = (F * uv_count)()
    assert lib.web_mesh_copy_uvs(h, uv, uv_count) == uv_count
    for tri_vertex, corner in zip(tris, corners):
        assert corner < len(points)
        assert math.isclose(pos[3 * tri_vertex], points[corner][0], abs_tol=1e-6)
        assert math.isclose(pos[3 * tri_vertex + 1], points[corner][1], abs_tol=1e-6)
        assert uv[2 * corner] == F(corner / 128).value
        assert uv[2 * corner + 1] == F((corner + 1) / 256).value

    assert lib.web_mesh_translate(h, F(.5), F(-1), F(2)) == 0
    after_corners = (U * t_count)()
    assert lib.web_mesh_copy_triangle_corners(h, after_corners, t_count) == t_count
    assert list(after_corners) == list(corners)
    after_uv = (F * uv_count)()
    assert lib.web_mesh_copy_uvs(h, after_uv, uv_count) == uv_count
    assert list(after_uv) == list(uv)
    assert lib.web_mesh_destroy(h) == 0
    assert lib.web_mesh_copy_triangle_corners(h, corners, t_count) == -1
    return expected_area


def main():
    assert lib.web_mesh_live_count() == 0
    cases = {
        "concave_pentagon": [(0, 0), (3, 0), (3, 3), (1.5, 1), (0, 3)],
        "reversed_concave": [(0, 3), (1.5, 1), (3, 3), (3, 0), (0, 0)],
        "triangle": [(0, 0), (2, 0), (1, 2)],
        "quad": [(-1, -1), (1, -1), (1, 1), (-1, 1)],
        "concave_octagon": [(0, 0), (3, 0), (3, 1), (2, 1),
                            (2, 2), (1, 2), (1, 3), (0, 3)],
    }
    # A full-size valid n-gon exercises bounded tessellation stack storage.
    cases["128_corners"] = [(math.cos(i * 2 * math.pi / 128),
                             math.sin(i * 2 * math.pi / 128)) for i in range(128)]
    area_results = {name: checked_polygon(p) for name, p in cases.items()}

    invalid = (
        [(0, 0), (1, 0), (2, 0)],
        [(0, 0), (1, 1), (0, 1), (1, 0)],
        [(0, 0), (1, 0), (1, 0), (0, 1)],
        [(0, 0), (1, math.nan), (0, 1)],
        [(0, 0), (1, math.inf), (0, 1)],
        [(0, 0), (1e7, 0), (0, 1)],
    )
    for p in invalid:
        assert new_polygon(p) == -4, p
    assert lib.web_mesh_create_polygon_xy(None, 4) == -4
    assert lib.web_mesh_create_polygon_xy(None, 129) == -4
    assert lib.web_mesh_live_count() == 0

    # Both faces sharing a cube vertex retain independent UV corners.
    h = lib.web_mesh_create_cube()
    assert h > 0
    # Invalid extrusions must be rejected before original Blender BMO runs.
    assert lib.web_mesh_extrude_top(h, F(math.nan)) == -2
    assert lib.web_mesh_extrude_top(h, F(math.inf)) == -2
    assert lib.web_mesh_extrude_top(h, F(3.4028235e38)) == -2
    assert lib.web_mesh_triangle_index_count(h) == 36
    assert lib.web_mesh_uv_layer_ensure(h) == 0
    for face in range(6):
        for corner in range(4):
            assert lib.web_mesh_set_uv(h, face, corner, F(face / 8),
                                       F(corner / 8)) == 0
    uv = (F * 48)()
    tris = (U * 36)()
    corners = (U * 36)()
    assert lib.web_mesh_copy_uvs(h, uv, 48) == 48
    assert lib.web_mesh_copy_triangles(h, tris, 36) == 36
    assert lib.web_mesh_copy_triangle_corners(h, corners, 36) == 36
    for corner in corners:
        assert corner < 24
        assert uv[2 * corner] == F((corner // 4) / 8).value
        assert uv[2 * corner + 1] == F((corner % 4) / 8).value
    assert lib.web_mesh_destroy(h) == 0

    # Named layers are real independent Blender CustomData blocks. The UVMap
    # default stays intact when new layers are added and independently edited.
    h = new_polygon(cases["concave_pentagon"])
    assert h > 0
    assert lib.web_mesh_uv_layer_ensure(h) == 0
    assert lib.web_mesh_named_uv_layer_count(h) == 1
    assert lib.web_mesh_set_uv(h, 0, 0, F(.25), F(.75)) == 0
    for name in (b"Lightmap", b"Detail"):
        assert lib.web_mesh_uv_layer_ensure_named(h, name) == 0
        assert lib.web_mesh_uv_layer_ensure_named(h, name) == 0
    assert lib.web_mesh_named_uv_layer_count(h) == 3
    assert lib.web_mesh_set_uv_named(h, b"Lightmap", 0, 0, F(.5), F(.125)) == 0
    assert lib.web_mesh_set_uv_named(h, b"Detail", 0, 0, F(.875), F(.625)) == 0
    base = (F * 10)()
    lightmap = (F * 10)()
    detail = (F * 10)()
    assert lib.web_mesh_copy_uvs(h, base, 10) == 10
    assert lib.web_mesh_copy_uvs_named(h, b"Lightmap", lightmap, 10) == 10
    assert lib.web_mesh_copy_uvs_named(h, b"Detail", detail, 10) == 10
    assert list(base[:2]) == [.25, .75]
    assert list(lightmap[:2]) == [.5, .125]
    assert list(detail[:2]) == [.875, .625]
    assert lib.web_mesh_copy_uvs_named(h, b"Detail", detail, 9) == -2
    assert lib.web_mesh_copy_uvs_named(h, b"Missing", detail, 10) == -3
    assert lib.web_mesh_uv_layer_ensure_named(h, b"bad name") == -4
    assert lib.web_mesh_uv_layer_ensure_named(h, b"") == -4
    assert lib.web_mesh_uv_layer_ensure_named(h, b"a" * 64) == -4
    for i in range(5):
        assert lib.web_mesh_uv_layer_ensure_named(h, f"Layer{i}".encode()) == 0
    assert lib.web_mesh_named_uv_layer_count(h) == 8
    assert lib.web_mesh_uv_layer_ensure_named(h, b"LayerOverflow") == -5
    assert lib.web_mesh_translate(h, F(.25), F(-.5), F(1.0)) == 0
    assert lib.web_mesh_copy_uvs_named(h, b"Detail", detail, 10) == 10
    assert list(detail[:2]) == [.875, .625]
    assert lib.web_mesh_face_normal_float_count(h) == 3
    normal = (F * 3)()
    assert lib.web_mesh_copy_face_normals(h, normal, 3) == 3
    assert abs(normal[0]) < 1e-6 and abs(normal[1]) < 1e-6
    assert math.isclose(normal[2], 1.0, abs_tol=1e-6)
    assert lib.web_mesh_copy_face_normals(h, normal, 2) == -2
    assert lib.web_mesh_destroy(h) == 0
    assert lib.web_mesh_copy_face_normals(h, normal, 3) == -1

    clockwise = new_polygon(cases["reversed_concave"])
    assert clockwise > 0
    assert lib.web_mesh_copy_face_normals(clockwise, normal, 3) == 3
    assert math.isclose(normal[2], -1.0, abs_tol=1e-6)
    assert lib.web_mesh_destroy(clockwise) == 0

    # Native GuardedAlloc baseline and object table capacity, including stale IDs.
    warmup = new_polygon(cases["concave_pentagon"])
    assert warmup > 0
    assert lib.web_mesh_uv_layer_ensure(warmup) == 0
    assert lib.web_mesh_destroy(warmup) == 0
    baseline = lib.web_mesh_memory_bytes()
    instances = [new_polygon(cases["concave_pentagon"]) for _ in range(16)]
    assert all(h > 0 for h in instances) and len(set(instances)) == 16
    assert new_polygon(cases["concave_pentagon"]) == -3
    for h in instances:
        assert lib.web_mesh_destroy(h) == 0
        assert lib.web_mesh_destroy(h) == -1
    assert lib.web_mesh_live_count() == 0
    for _ in range(200):
        h = new_polygon(cases["concave_pentagon"])
        assert h > 0
        assert lib.web_mesh_uv_layer_ensure(h) == 0
        assert lib.web_mesh_destroy(h) == 0
    assert lib.web_mesh_live_count() == 0
    assert lib.web_mesh_memory_bytes() == baseline

    print("BLENDER_WEB_TRIANGLE_UV_NATIVE=" + json.dumps({
        "status": "pass",
        "reference": "source-pinned original Blender BM_face_calc_tessellation",
        "concave_area_results": area_results,
        "triangle_corner_uv_seams": True,
        "bounded_named_uv_layers": True,
        "independent_uv_domains": True,
        "source_backed_face_normals": True,
        "extrusion_overflow_rejected_before_mutation": True,
        "invalid_geometry_rejected": True,
        "native_capacity_checked": 16,
        "lifecycle_cycles": 200,
        "guardedalloc_baseline_equal_final": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
