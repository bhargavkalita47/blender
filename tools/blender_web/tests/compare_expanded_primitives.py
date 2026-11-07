#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare bounded grid/cylinder/UV-sphere topology with pinned Blender 5.4."""
import json
import math
import pathlib
import sys

from compare_reference_parity import PINNED, read_tag

SHAPES=("grid_3x2","cylinder_8","uv_sphere_8x4")
COUNTS=("verts","edges","faces","loops","triangles")
EPS=2e-4


def compare_positions(label,a,b):
    assert len(a)==len(b),(label,len(a),len(b))
    diffs=[]
    for i,(pa,pb) in enumerate(zip(a,b)):
        assert len(pa)==len(pb)==3
        for j,(x,y) in enumerate(zip(pa,pb)):
            assert math.isfinite(float(x)) and math.isfinite(float(y)),label
            if abs(float(x)-float(y))>EPS:
                diffs.append([i,j,x,y])
    if diffs:
        raise AssertionError(f"{label}: {len(diffs)} coordinate mismatches, first={diffs[:10]}")


def main():
    if len(sys.argv)!=4:raise SystemExit("original.log expanded.log report.json")
    original=read_tag(sys.argv[1],"BLENDER_WEB_EXPANDED_ORIGINAL=")
    extracted=read_tag(sys.argv[2],"BLENDER_WEB_EXPANDED_NATIVE=")
    assert original["status"]==extracted["status"]=="pass"
    assert original["pinned_source_sha"]==PINNED
    assert original["blender_build_hash"].startswith(PINNED[:12])
    passed={}
    for name in SHAPES:
        a=original["shapes"][name]
        b=extracted["reference_cases"][name]
        for k in COUNTS:
            assert a[k]==b[k],f"{name} mismatch {k}: pinned={a[k]}, extracted={b[k]}"
        compare_positions(name,a["positions"],b["positions"])
        passed[name]={k:a[k] for k in COUNTS}
    poke_original=original["shapes"]["poked_plane"]
    poke_extracted=extracted["poked_plane"]
    for key in COUNTS:
        assert poke_original[key] == poke_extracted[key], (
            "Blender BMO poke mismatch: "+key)
    compare_positions("poked_plane",poke_original["positions"],poke_extracted["positions"])
    assert extracted["original_blender_bmo_poke"] is True
    passed["poked_plane"]={key:poke_original[key] for key in COUNTS}
    inset_original=original["shapes"]["inset_plane"]
    inset_extracted=extracted["inset_plane"]
    for key in COUNTS:
        assert inset_original[key] == inset_extracted[key], (
            "Blender BMO inset mismatch: "+key)
    compare_positions("inset_plane",inset_original["positions"],inset_extracted["positions"])
    assert extracted["original_blender_bmo_inset"] is True
    passed["inset_plane"]={key:inset_original[key] for key in COUNTS}
    extrude_original=original["shapes"]["extruded_plane"]
    extrude_extracted=extracted["extruded_plane"]
    for key in COUNTS:
        assert extrude_original[key] == extrude_extracted[key], (
            "Blender general BMO extrusion mismatch: "+key)
    compare_positions("extruded_plane",extrude_original["positions"],
                      extrude_extracted["positions"])
    assert extracted["general_face_extrusion"] is True
    assert extracted["edge_face_selection"] is True
    assert extracted["vertex_edge_face_deletion"] is True
    passed["extruded_plane"]={key:extrude_original[key] for key in COUNTS}
    assert extracted["vertex_selection_transforms"]
    assert extracted["face_deletion"]
    assert extracted["multi_mesh_independence"]
    assert extracted["invalid_parameters_rejected"]
    assert extracted["tracked_allocations_before"]==extracted["tracked_allocations_after"]
    report={"status":"pass","phase":"2.2.3 primitive/selected-edit expansion",
            "pinned_blender_commit":PINNED,
            "pinned_reference_hash":original["blender_build_hash"],
            "shapes":passed,"position_tolerance":EPS,
            "original_blender_element_constructors":True,
            "selection_transform_and_delete_smoke":True,
            "original_blender_poke_parity":True,
            "original_blender_inset_parity":True,
            "original_blender_general_face_extrusion_parity":True,
            "native_primitive_cycles":extracted["new_primitive_lifecycle_cycles"],
            "native_no_net_tracked_allocation":True,
            "does_not_verify":"inset/bevel/subdivide operator parity, materials or UVs"}
    pathlib.Path(sys.argv[3]).write_text(json.dumps(report,indent=2)+"\n")
    print("BLENDER_WEB_EXPANDED_PARITY="+json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
