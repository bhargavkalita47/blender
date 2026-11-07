#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Phase 2.2.4 first slice: original Blender BMLoop UV data, not vertex UVs."""
import ctypes
import json
import math
from export_extracted_parity import core

core.web_mesh_uv_layer_ensure.argtypes=[ctypes.c_int]
core.web_mesh_uv_layer_ensure.restype=ctypes.c_int
core.web_mesh_uv_float_count.argtypes=[ctypes.c_int]
core.web_mesh_uv_float_count.restype=ctypes.c_int
core.web_mesh_set_uv.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,
                               ctypes.c_float,ctypes.c_float]
core.web_mesh_set_uv.restype=ctypes.c_int
core.web_mesh_copy_uvs.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_float),ctypes.c_int]
core.web_mesh_copy_uvs.restype=ctypes.c_int
core.web_mesh_translate.argtypes=[ctypes.c_int,ctypes.c_float,ctypes.c_float,ctypes.c_float]
core.web_mesh_translate.restype=ctypes.c_int

PLANE_UVS=((0.,0.),(1.,0.),(1.,1.),(0.,1.))

def read_uv(handle):
    count=core.web_mesh_uv_float_count(handle)
    assert count>=0 and count%2==0,count
    array=(ctypes.c_float*count)()
    assert core.web_mesh_copy_uvs(handle,array,count)==count
    return [[float(array[i]),float(array[i+1])] for i in range(0,count,2)]

def main():
    assert core.web_mesh_live_count()==0
    warmup=core.web_mesh_create_plane()
    assert warmup>0 and core.web_mesh_uv_layer_ensure(warmup)==0
    assert core.web_mesh_destroy(warmup)==0
    baseline=core.web_mesh_memory_bytes()

    plane=core.web_mesh_create_plane()
    cube=core.web_mesh_create_cube()
    assert plane>0 and cube>0 and plane!=cube
    try:
        assert core.web_mesh_uv_float_count(plane)==-2
        assert core.web_mesh_uv_layer_ensure(plane)==0
        assert core.web_mesh_uv_layer_ensure(plane)==0  # Idempotent.
        assert core.web_mesh_uv_float_count(plane)==8
        for corner,(u,v) in enumerate(PLANE_UVS):
            assert core.web_mesh_set_uv(plane,0,corner,u,v)==0
        expected=[list(p) for p in PLANE_UVS]
        assert read_uv(plane)==expected
        assert core.web_mesh_set_uv(plane,0,4,0,0)==-2
        assert core.web_mesh_set_uv(plane,1,0,0,0)==-2
        assert core.web_mesh_set_uv(plane,0,0,math.nan,0)==-4
        assert core.web_mesh_set_uv(plane,0,0,0,math.inf)==-4
        assert read_uv(plane)==expected
        small=(ctypes.c_float*7)()
        assert core.web_mesh_copy_uvs(plane,small,7)==-3
        assert core.web_mesh_translate(plane,1.,2.,3.)==0
        assert read_uv(plane)==expected  # UV remains independent of world coordinates.

        # Shared 3D vertices may have different UVs on adjacent face corners.
        assert core.web_mesh_uv_float_count(cube)==-2
        assert core.web_mesh_set_uv(cube,0,0,0.,0.)==-3
        assert core.web_mesh_uv_layer_ensure(cube)==0
        assert core.web_mesh_uv_float_count(cube)==48
        for face in range(6):
            for corner in range(4):
                assert core.web_mesh_set_uv(cube,face,corner,
                                            face/8.,corner/8.)==0
        seam=read_uv(cube)
        assert len(seam)==24
        assert len({p[0] for p in seam})==6
        assert core.web_mesh_validate_topology(plane)==0
        assert core.web_mesh_validate_topology(cube)==0
    finally:
        assert core.web_mesh_destroy(plane)==0
        assert core.web_mesh_destroy(cube)==0

    assert core.web_mesh_uv_float_count(plane)==-1
    assert core.web_mesh_set_uv(plane,0,0,0.,0.)==-1
    assert core.web_mesh_uv_layer_ensure(plane)==-1
    assert core.web_mesh_live_count()==0
    assert core.web_mesh_memory_bytes()==baseline
    for i in range(200):
        h=core.web_mesh_create_plane()
        assert h>0
        assert core.web_mesh_uv_layer_ensure(h)==0
        assert core.web_mesh_set_uv(h,0,0,0.25,0.75)==0
        assert core.web_mesh_destroy(h)==0
        if (i+1)%50==0:
            assert core.web_mesh_memory_bytes()==baseline
    assert core.web_mesh_live_count()==0
    assert core.web_mesh_memory_bytes()==baseline

    print("BLENDER_WEB_UV_NATIVE="+json.dumps({
        "status":"pass","corner_uvs_sorted":sorted(expected),
        "corner_count":4,"independent_cube_corner_count":24,
        "supports_separate_face_corner_uvs":True,
        "invalid_and_stale_handles_rejected":True,
        "nonfinite_rejected_without_mutation":True,
        "uv_layer_idempotent":True,
        "translate_preserves_uv":True,
        "lifecycle_cycles":200,
        "no_net_tracked_memory":True
    },sort_keys=True))

if __name__=="__main__":
    main()
