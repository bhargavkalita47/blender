#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Negative regression: extrusion must reject non-finite Z without mutation."""
import ctypes
import math
from export_extracted_parity import core, snapshot

core.web_mesh_api_version_major.restype = ctypes.c_int
core.web_mesh_api_version_minor.restype = ctypes.c_int
core.web_mesh_max_live_meshes.restype = ctypes.c_int
core.web_mesh_extrude_top.argtypes = [ctypes.c_int, ctypes.c_float]
core.web_mesh_extrude_top.restype = ctypes.c_int
core.web_mesh_extrude_face_z.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_float]
core.web_mesh_extrude_face_z.restype = ctypes.c_int

assert core.web_mesh_api_version_major() == 0
assert core.web_mesh_api_version_minor() >= 1
assert core.web_mesh_max_live_meshes() == 16
assert core.web_mesh_live_count() == 0
for _ in range(16):
    warmup = core.web_mesh_create_cube()
    assert warmup > 0
    assert core.web_mesh_destroy(warmup) == 0
baseline = core.web_mesh_memory_bytes()
h = core.web_mesh_create_cube()
assert h > 0
try:
    original = snapshot(h)
    for value in (math.nan, math.inf, -math.inf):
        assert core.web_mesh_extrude_top(h, value) == -2
        assert snapshot(h) == original
        assert core.web_mesh_validate_topology(h) == 0
        assert core.web_mesh_extrude_face_z(h, 0, value) == -2
        assert snapshot(h) == original
        assert core.web_mesh_validate_topology(h) == 0
finally:
    assert core.web_mesh_destroy(h) == 0
assert core.web_mesh_live_count() == 0
assert core.web_mesh_memory_bytes() == baseline
print("BLENDER_WEB_EXTRUSION_GUARDS=pass")
