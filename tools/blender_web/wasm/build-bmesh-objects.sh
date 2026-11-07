#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT="${1:-$ROOT/build/blender_web/bmesh_wasm}"
mkdir -p "$OUT"

command -v em++ >/dev/null 2>&1 || { echo "Activate emsdk before running" >&2; exit 127; }

# Resolve header directories deliberately: this is not a full Blender CMake build.
INC=(
  source/blender/bmesh
  source/blender/blenkernel
  source/blender/blenlib
  source/blender/makesdna
  source/blender/makesrna
  source/blender/depsgraph
  source/blender/geometry
  source/blender/functions
  source/blender/blentranslation
  source/blender/blenloader
  source/blender/imbuf
  source/blender/animrig
  source/blender/asset_system
  source/blender/gpu
  source/blender/draw
  source/blender/modifiers
  source/blender/nodes
  source/blender/render
  source/blender/windowmanager
  source/blender/editors/include
  intern/guardedalloc
  intern/clog
  intern/atomic
  intern/eigen
  extern/rangetree
)
FLAGS=(-std=c++20 -O0 -g0 -DNDEBUG)
for dir in "${INC[@]}"; do
  if [[ -d "$ROOT/$dir" ]]; then
    FLAGS+=("-I$ROOT/$dir")
  fi
done

SOURCES=(
  source/blender/bmesh/intern/bmesh_structure.cc
  source/blender/bmesh/intern/bmesh_core.cc
  source/blender/bmesh/intern/bmesh_construct.cc
  source/blender/bmesh/intern/bmesh_mesh.cc
)
printf 'Emscripten compiler: '; em++ --version | head -1
success=0
failed=0
for src in "${SOURCES[@]}"; do
  name="${src##*/}"
  echo "::group::Compiling genuine Blender $src"
  if em++ "${FLAGS[@]}" -c "$ROOT/$src" -o "$OUT/$name.o" > "$OUT/$name.log" 2>&1; then
    echo "PASS: $src"
    success=$((success + 1))
  else
    echo "FAIL: $src"
    cat "$OUT/$name.log"
    failed=$((failed + 1))
  fi
  echo "::endgroup::"
done

printf '{"compiler":"emscripten","compiled":%d,"failed":%d}\n' "$success" "$failed" > "$OUT/status.json"
cat "$OUT/status.json"
if ((failed != 0)); then
  exit 1
fi
