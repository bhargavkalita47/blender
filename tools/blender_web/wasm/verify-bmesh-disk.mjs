// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const out = resolve(process.argv[2] || "build/blender_web/bmesh_wasm");
const wasm = await readFile(resolve(out, "bmesh_disk.wasm"));
assert.equal(wasm.subarray(0, 4).toString("hex"), "0061736d");
assert.ok(wasm.length > 128);

const { default: instantiate } = await import(pathToFileURL(resolve(out, "bmesh_disk.mjs")).href);
const module = await instantiate();
for (let i = 0; i < 4; i++) {
  assert.equal(module._web_bmesh_square_vertex_degree(i), 2, "Square adjacency vertex " + i);
}
assert.equal(module._web_bmesh_square_vertex_degree(-1), -1);
assert.equal(module._web_bmesh_square_vertex_degree(4), -1);
for (const [a, b] of [[0, 1], [1, 2], [2, 3], [3, 0]]) {
  assert.equal(module._web_bmesh_square_edge_exists(a, b), 1, "Expected original square edge");
}
for (const [a, b] of [[0, 2], [1, 3]]) {
  assert.equal(module._web_bmesh_square_edge_exists(a, b), 0, "Diagonal edge must be absent");
}
assert.equal(module._web_bmesh_square_edge_exists(-1, 0), -1);
assert.equal(module._web_bmesh_square_validate(), 0, "BMesh disk validation");
assert.equal(module._web_bmesh_after_edge_remove(), 6, "BMesh edge removal");
assert.equal(module._web_bmesh_after_vertex_relink(), 3, "BMesh vertex relink");

// Recreate and mutate the topology repeatedly to catch state leakage/traps.
for (let i = 0; i < 1000; ++i) {
  assert.equal(module._web_bmesh_square_validate(), 0);
  assert.equal(module._web_bmesh_after_edge_remove(), 6);
  assert.equal(module._web_bmesh_after_vertex_relink(), 3);
}
console.log(JSON.stringify({
  status: "pass",
  stage: "Blender real BMesh disk adjacency via Emscripten",
  source: "source/blender/bmesh/intern/bmesh_structure.cc",
  wasm_bytes: wasm.length,
  runtime: process.version,
  stress_repetitions: 1000,
}));
