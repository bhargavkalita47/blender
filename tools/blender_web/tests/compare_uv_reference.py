#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail CI unless extracted UV test matches the exact Blender reference."""
import json
import pathlib
import sys
from compare_reference_parity import PINNED,read_tag

def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: compare_uv_reference.py original.log native.log report.json")
    original=read_tag(sys.argv[1],"BLENDER_WEB_UV_ORIGINAL=")
    native=read_tag(sys.argv[2],"BLENDER_WEB_UV_NATIVE=")
    assert original["status"]==native["status"]=="pass"
    assert original["pinned_source_sha"]==PINNED
    assert original["blender_build_hash"].startswith(PINNED[:12])
    assert original["corner_count"]==native["corner_count"]==4
    assert original["corner_uvs_sorted"]==native["corner_uvs_sorted"],(
        original["corner_uvs_sorted"],native["corner_uvs_sorted"])
    for flag in ("supports_separate_face_corner_uvs",
                 "invalid_and_stale_handles_rejected",
                 "nonfinite_rejected_without_mutation","uv_layer_idempotent",
                 "translate_preserves_uv","no_net_tracked_memory"):
        assert native[flag] is True,flag
    assert native["lifecycle_cycles"]>=200
    report={"status":"pass","phase":"2.2.4 initial UV loop layer",
            "pinned_source_sha":PINNED,
            "pinned_build_hash":original["blender_build_hash"],
            "per_loop_uv_reference_parity":True,
            "uv_seam_and_lifetime_smoke":True,
            "not_yet_verified":["multiple UV layers","UV preservation after bevel/inset",
                                "triangle corner remapping","material attributes",
                                "general nonconvex n-gon triangulation"]}
    pathlib.Path(sys.argv[3]).write_text(json.dumps(report,indent=2)+"\n")
    print("BLENDER_WEB_UV_PARITY="+json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()
