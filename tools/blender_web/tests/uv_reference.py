#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reference BMLoop UV data using official source-pinned Blender 5.4 Alpha."""
import bmesh
import bpy
import json

PINNED="67e5a5f874cf37e2a114cebd24f219d8c44a16ad"

def main():
    h=bpy.app.build_hash
    h=h.decode("ascii") if isinstance(h,bytes) else str(h)
    assert tuple(bpy.app.version)[:2]==(5,4)
    assert h.lower().startswith(PINNED[:12]),(h,PINNED)
    bm=bmesh.new()
    try:
        bmesh.ops.create_grid(bm,x_segments=1,y_segments=1,size=1.0,calc_uvs=False)
        layer=bm.loops.layers.uv.new("UVMap")
        for face in bm.faces:
            for loop in face.loops:
                loop[layer].uv=((loop.vert.co.x+1.)/2.,(loop.vert.co.y+1.)/2.)
        uvs=sorted([[float(x) for x in loop[layer].uv]
                    for face in bm.faces for loop in face.loops])
        assert len(uvs)==4
        assert len(bm.verts)==4 and len(bm.edges)==4 and len(bm.faces)==1
        print("BLENDER_WEB_UV_ORIGINAL="+json.dumps({
            "status":"pass","pinned_source_sha":PINNED,
            "blender_build_hash":h.lower(),"corner_uvs_sorted":uvs,
            "corner_count":len(uvs),"uv_storage":"Blender BMLoop CustomData"
        },sort_keys=True))
    finally:
        bm.free()
if __name__=="__main__":
    main()
