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
  source/blender/blenloader_core
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
  intern/profile
  intern/guardedalloc/intern
  intern/eigen
  extern/rangetree
)
FLAGS=(-std=c++20 -O0 -g0 -DNDEBUG)
for dir in "${INC[@]}"; do
  if [[ -d "$ROOT/$dir" ]]; then
    FLAGS+=("-I$ROOT/$dir")
  fi
done

echo "::group::Verify Blender ResourceScope layout on wasm32"
em++ "${FLAGS[@]}" -fsyntax-only \
  "$ROOT/tools/blender_web/wasm/check-resource-scope-size.cc" \
  > "$OUT/resource-scope-wasm32.log" 2>&1 || { cat "$OUT/resource-scope-wasm32.log"; exit 1; }
echo "PASS: WASM32 ResourceScope layout"
echo "::endgroup::"

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

# Link selected Blender BMesh disk-cycle functions into a real WASM module.
# Compile original Blender source with function sections so unrelated
# desktop/BKE symbol references from *unused* functions can be removed.
echo "::group::Linking and running Blender BMesh disk kernel as WebAssembly"
em++ "${FLAGS[@]}" -O2 -ffunction-sections -fdata-sections \
  "$ROOT/source/blender/bmesh/intern/bmesh_structure.cc" \
  "$ROOT/tools/blender_web/wasm/bmesh_disk_bridge.cc" \
  -Wl,--gc-sections \
  -sWASM=1 -sMODULARIZE=1 -sEXPORT_ES6=1 -sENVIRONMENT=web,node \
  -sALLOW_MEMORY_GROWTH=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 \
  -sEXPORTED_FUNCTIONS='["_web_bmesh_square_vertex_degree","_web_bmesh_square_edge_exists","_web_bmesh_square_validate","_web_bmesh_after_edge_remove","_web_bmesh_after_vertex_relink"]' \
  -o "$OUT/bmesh_disk.mjs" > "$OUT/bmesh-disk-link.log" 2>&1 || {
    cat "$OUT/bmesh-disk-link.log"
    exit 1
  }
test -s "$OUT/bmesh_disk.wasm"
test -s "$OUT/bmesh_disk.mjs"
node "$ROOT/tools/blender_web/wasm/verify-bmesh-disk.mjs" "$OUT"
echo "::endgroup::"

echo "::group::Diagnostic only: resolve BMesh create/free linker dependencies"
if em++ "${FLAGS[@]}" -O2 -ffunction-sections -fdata-sections \
  "$ROOT/source/blender/bmesh/intern/bmesh_mesh.cc" \
  "$ROOT/tools/blender_web/wasm/bmesh_lifecycle_probe.cc" \
  -Wl,--gc-sections \
  -sWASM=1 -sMODULARIZE=1 -sEXPORT_ES6=1 -sENVIRONMENT=node \
  -sERROR_ON_UNDEFINED_SYMBOLS=1 \
  -sEXPORTED_FUNCTIONS='["_web_bmesh_lifecycle_probe"]' \
  -o "$OUT/bmesh_lifecycle_probe.mjs" > "$OUT/bmesh-lifecycle-link.log" 2>&1; then
    echo '{"link_success":true}' > "$OUT/lifecycle-probe-status.json"
    echo "BMesh lifecycle linked; execution requires explicit runtime validation."
else
    echo '{"link_success":false,"status":"dependency-discovery-only"}' > "$OUT/lifecycle-probe-status.json"
    echo "Expected at this stage: original Blender allocator/BKE/CustomData symbols missing."
    grep -E "(undefined symbol:|error:|wasm-ld:)" "$OUT/bmesh-lifecycle-link.log" | head -70 || true
fi
echo "::endgroup::"

# Escalation experiment: use REAL Blender implementations of allocator,
# BLI mempool, BKE CustomData, and BMesh iteration. A successful compilation
# does not mean that all linker symbols or runtime semantics are resolved.
echo "::group::Diagnostic: compile Blender-owned allocation and CustomData sources"
SUPPORT=(
  intern/guardedalloc/intern/mallocn.cc
  intern/guardedalloc/intern/mallocn_lockfree_impl.cc
  intern/guardedalloc/intern/mallocn_guarded_impl.cc
  intern/guardedalloc/intern/memory_usage.cc
  intern/guardedalloc/intern/leak_detector.cc
  intern/clog/clog.cc
  source/blender/blenlib/intern/BLI_mempool.cc
  source/blender/blenkernel/intern/customdata.cc
  source/blender/bmesh/intern/bmesh_iterators.cc
  source/blender/bmesh/intern/bmesh_operators.cc
  source/blender/blenlib/intern/math_vector.cc
  source/blender/blenlib/intern/index_mask.cc
  source/blender/blenlib/intern/listbase.cc
  source/blender/blenkernel/intern/mesh_normals.cc
  source/blender/blenkernel/intern/multires.cc
  source/blender/blenkernel/intern/customdata_file.cc
)
SUPPORT_OBJECTS=()
support_failed=0
for src in "${SUPPORT[@]}"; do
  base="${src##*/}"
  file="$OUT/dep_$base.o"
  if em++ "${FLAGS[@]}" -O2 -ffunction-sections -fdata-sections \
       -c "$ROOT/$src" -o "$file" > "$OUT/dep_$base.log" 2>&1; then
    echo "PASS: $src"
    SUPPORT_OBJECTS+=("$file")
  else
    echo "FAIL: $src (inspect uploaded dep_$base.log)"
    grep -E "fatal error:|error:" "$OUT/dep_$base.log" | head -10 || true
    support_failed=$((support_failed + 1))
  fi
done
echo "::endgroup::"

# BM_mesh_create/free does not itself need selection-marking translation units.
# BMesh marking has a separate wasm32 enum-char narrowing problem to address
# when selection/extended editing is part of the chosen runtime closure.

echo "::group::Diagnostic: attempt genuine BM_mesh_create/free linkage"
# Compile this source independently of whether all optional providers compile.
# Both the full lifecycle probe and the narrower allocation probe consume it.
em++ "${FLAGS[@]}" -O2 -ffunction-sections -fdata-sections \
  -c "$ROOT/source/blender/bmesh/intern/bmesh_mesh.cc" \
  -o "$OUT/bmesh_mesh_lifecycle.o" > "$OUT/lifecycle-mesh-compile.log" 2>&1 || {
    cat "$OUT/lifecycle-mesh-compile.log"
    exit 1
  }
if em++ "${FLAGS[@]}" -O2 -ffunction-sections -fdata-sections \
    "$OUT/bmesh_mesh_lifecycle.o" "${SUPPORT_OBJECTS[@]}" \
    "$ROOT/tools/blender_web/wasm/bmesh_lifecycle_probe.cc" \
    -Wl,--gc-sections -Wl,--error-limit=0 \
    -sWASM=1 -sMODULARIZE=1 -sEXPORT_ES6=1 -sENVIRONMENT=node \
    -sERROR_ON_UNDEFINED_SYMBOLS=1 \
    -sEXPORTED_FUNCTIONS='["_web_bmesh_lifecycle_probe"]' \
    -o "$OUT/bmesh_lifecycle_full.mjs" > "$OUT/lifecycle-full-link.log" 2>&1; then
  printf '{"compile_support_failures":%d,"link_success":true}\n' "$support_failed" > "$OUT/lifecycle-expanded-status.json"
  echo "BM_mesh_create/free link succeeded (runtime test still required)."
else
  printf '{"compile_support_failures":%d,"link_success":false}\n' "$support_failed" > "$OUT/lifecycle-expanded-status.json"
  grep "undefined symbol:" "$OUT/lifecycle-full-link.log" | sed 's/^.*undefined symbol: //' | sort -u | head -75 || true
fi
echo "::endgroup::"

# Second escalation: isolate BM_mesh_create alone. Uses original Blender
# allocator/BLI/BKE implementations and GC-sections to eliminate unreferenced
# Blender desktop/lifecycle code. Not a replacement for proper BM_mesh_free.
if [[ -f "$OUT/dep_customdata.cc.o" ]]; then
  echo "::group::Diagnostic: create one empty BMesh via actual Blender code in WASM"
  if em++ "${FLAGS[@]}" -O2 -ffunction-sections -fdata-sections \
    "$OUT/bmesh_mesh_lifecycle.o" \
    "$OUT/dep_mallocn.cc.o" \
    "$OUT/dep_mallocn_lockfree_impl.cc.o" \
    "$OUT/dep_memory_usage.cc.o" \
    "$OUT/dep_clog.cc.o" \
    "$OUT/dep_BLI_mempool.cc.o" \
    "$OUT/dep_customdata.cc.o" \
    "$ROOT/tools/blender_web/wasm/bmesh_allocation_probe.cc" \
    -Wl,--gc-sections -Wl,--error-limit=0 \
    -sWASM=1 -sMODULARIZE=1 -sEXPORT_ES6=1 -sENVIRONMENT=node \
    -sERROR_ON_UNDEFINED_SYMBOLS=1 \
    -sEXPORTED_FUNCTIONS='["_web_bmesh_create_one_empty_mesh"]' \
    -o "$OUT/bmesh_alloc.mjs" > "$OUT/bmesh-alloc-link.log" 2>&1; then
      if node "$ROOT/tools/blender_web/wasm/verify-bmesh-allocation.mjs" "$OUT" > "$OUT/bmesh-alloc-run.log" 2>&1; then
        echo '{"link_success":true,"runtime_success":true}' > "$OUT/allocation-probe-status.json"
        cat "$OUT/bmesh-alloc-run.log"
      else
        echo '{"link_success":true,"runtime_success":false}' > "$OUT/allocation-probe-status.json"
        cat "$OUT/bmesh-alloc-run.log"
      fi
  else
      echo '{"link_success":false,"runtime_success":false}' > "$OUT/allocation-probe-status.json"
      grep -E "undefined symbol:|error:" "$OUT/bmesh-alloc-link.log" | head -35 || true
  fi
  echo "::endgroup::"
fi
