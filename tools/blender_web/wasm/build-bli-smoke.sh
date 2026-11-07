#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
output="${1:-$root/build/blender_web/wasm}"
mkdir -p "$output"

if ! command -v em++ >/dev/null 2>&1; then
  echo "Emscripten em++ not found. Source emsdk_env.sh first." >&2
  exit 127
fi

echo "Using Emscripten:"
em++ --version | head -n 1
echo "Compiling actual Blender BLI math_base.cc into WebAssembly"

em++ -std=c++20 -O2 -DNDEBUG \
  -I"$root/source/blender/blenlib" \
  "$root/source/blender/blenlib/intern/math_base.cc" \
  "$root/tools/blender_web/wasm/bli_math_bridge.cc" \
  -sWASM=1 \
  -sMODULARIZE=1 \
  -sEXPORT_ES6=1 \
  -sENVIRONMENT=web,node \
  -sALLOW_MEMORY_GROWTH=1 \
  -sEXPORTED_FUNCTIONS='["_web_bli_pow_i","_web_bli_double_round","_web_bli_floor_power_of_10","_web_bli_ceil_power_of_10"]' \
  -o "$output/bli_smoke.mjs"

test -s "$output/bli_smoke.wasm"
test -s "$output/bli_smoke.mjs"
echo "Built $output/bli_smoke.wasm and bli_smoke.mjs"
