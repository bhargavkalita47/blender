#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the native Phase 2.2 experimental engine did not pull desktop code."""
import json
import pathlib
import re
import subprocess
import sys

build = pathlib.Path(sys.argv[1]).resolve()
root = pathlib.Path(__file__).resolve().parents[3]
commands_file = build / "compile_commands.json"
library = build / "libblender_web_native_core.so"
assert commands_file.is_file(), "Missing compile_commands.json"
assert library.is_file(), "Native BMesh shared library not linked"
commands = json.loads(commands_file.read_text())
sources = [pathlib.Path(x["file"]).resolve() for x in commands]
source_relative = []
for path in sources:
    try:
        source_relative.append(path.relative_to(root).as_posix())
    except ValueError:
        raise AssertionError(f"Unrecognized source path outside repo: {path}")
must_include = [
    "source/blender/bmesh/intern/bmesh_mesh.cc",
    "source/blender/bmesh/operators/bmo_poke.cc",
    "source/blender/bmesh/intern/bmesh_interp.cc",
    "source/blender/bmesh/operators/bmo_inset.cc",
    "source/blender/bmesh/intern/bmesh_mods.cc",
    "source/blender/bmesh/operators/bmo_subdivide.cc",
    "source/blender/bmesh/intern/bmesh_structure.cc",
    "source/blender/blenkernel/intern/customdata.cc",
    "intern/guardedalloc/intern/mallocn.cc",
    "tools/blender_web/wasm/bmesh_handle_api.cc",
    "tools/blender_web/native_core/native_core_smoke.cc",
]
missing = sorted(set(must_include) - set(source_relative))
assert not missing, f"Missing original Blender translation units: {missing}"
# 53 original source files + 1 ABI bridge + 1 smoke executable, after
# adding the original BLI/translation implementations required by BMO edits.
assert len(sources) == 55, f"Expected 53 original Blender sources + bridge + smoke, got {len(sources)}"
forbidden_prefixes = (
    "source/blender/draw/",
    "source/blender/gpu/",
    "source/blender/render/",
    "source/blender/windowmanager/",
    "source/blender/creator/",
    "source/blender/editors/",
    "intern/ghost/",
    "intern/cycles/",
)
bad_sources = [s for s in source_relative if s.startswith(forbidden_prefixes)]
assert not bad_sources, f"Desktop source compiled into minimal native target: {bad_sources}"

link_undefined = subprocess.run(
    ["nm", "-D", "--undefined-only", "-C", str(library)],
    capture_output=True, text=True, check=True).stdout
prohibited_symbols = re.findall(
    r"(?m)^.*(?:\bGHOST_|\bGPU_|\bDRW_|\bWM_|\bRE_Render|\bBLF_).*",
    link_undefined)
assert not prohibited_symbols, f"Unexpected native UI/GPU unresolved symbols: {prohibited_symbols[:10]}"

dyn = subprocess.run(["readelf", "-d", str(library)],
                     capture_output=True, text=True, check=True).stdout
dependencies = sorted(set(re.findall(r"Shared library: \[(.*?)\]", dyn)))
for forbidden in ("libOpenColorIO", "libOpenImageIO", "libGL.so", "libEGL",
                  "libvulkan", "libX11", "libGHOST", "libblender_draw", "libCycles"):
    assert not any(forbidden in d for d in dependencies), (
        f"Unexpected native-renderer dependency: {dependencies}")

defined = subprocess.run(["nm", "-D", "--defined-only", str(library)],
                         capture_output=True, text=True, check=True).stdout
for symbol in ("web_mesh_create_cube", "web_mesh_extrude_top",
               "web_mesh_destroy", "web_mesh_copy_positions",
               "web_mesh_copy_triangles", "web_mesh_validate_topology"):
    assert re.search(rf"\b{symbol}\b", defined), f"Missing exported API {symbol}"

report = {
    "status": "pass",
    "scope": "isolated original Blender BMesh experimental native core",
    "original_blender_translation_units": len(sources) - 2,
    "abi_bridge_translation_units": 1,
    "native_test_translation_units": 1,
    "native_desktop_sources": bad_sources,
    "unexpected_native_window_renderer_symbols": prohibited_symbols,
    "direct_dynamic_libraries": dependencies,
    "upstream_blender_cmake_configured": False,
    "native_reference_parity_verified": False,
    "sources": sorted(source_relative),
}
(build / "isolation-report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "sources"}, indent=2))
