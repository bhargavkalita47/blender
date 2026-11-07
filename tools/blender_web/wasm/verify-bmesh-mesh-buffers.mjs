// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {resolve} from "node:path";
import {pathToFileURL} from "node:url";
import {copyMeshBuffers} from "./mesh_buffers.mjs";

const dir = resolve(process.argv[2] || "build/blender_web/bmesh_wasm");
const bin = await readFile(resolve(dir, "bmesh_handles.wasm"));
assert.equal(bin.subarray(0,4).toString("hex"), "0061736d");
const {default: init} = await import(pathToFileURL(resolve(dir, "bmesh_handles.mjs")).href);
const wasm = await init();
const before = wasm._web_mesh_memory_bytes();
const handle = wasm._web_mesh_create_cube();
assert.ok(handle > 0);

function verifyMesh(expectedVertices, expectedTriangles, zMax) {
  assert.equal(wasm._web_mesh_validate_topology(handle), 0);
  const {positions, indices} = copyMeshBuffers(wasm, handle);
  assert.equal(positions.length, expectedVertices * 3);
  assert.equal(indices.length, expectedTriangles * 3);
  assert.ok(indices.every(x => x < expectedVertices));
  assert.equal(Math.max(...positions.filter((_, i) => i % 3 === 2)), zMax);
  assert.equal(Math.min(...positions.filter((_, i) => i % 3 === 2)), -1);
  assert.equal(wasm._web_mesh_copy_positions(handle, 0, positions.length), -2);
  assert.equal(wasm._web_mesh_copy_triangles(handle, 0, indices.length), -2);
  const ptr = wasm._malloc(4);
  assert.ok(ptr > 0);
  try {
    assert.equal(wasm._web_mesh_copy_positions(handle, ptr, 1), -2);
    assert.equal(wasm._web_mesh_copy_triangles(handle, ptr, 1), -2);
  } finally { wasm._free(ptr); }
}
verifyMesh(8, 12, 1);
assert.equal(wasm._web_mesh_extrude_top(handle, 1), 0);
verifyMesh(12, 20, 2);
assert.equal(wasm._web_mesh_extrude_top(handle, 0.5), 0);
verifyMesh(16, 28, 2.5);
assert.equal(wasm._web_mesh_destroy(handle), 0);
assert.throws(() => copyMeshBuffers(wasm, handle), /invalid mesh/);
assert.equal(wasm._web_mesh_memory_bytes(), before);
console.log(JSON.stringify({status:"pass",step:"Phase 1.3.3 buffer transfer Node",
  vertices:16,triangle_indices:84,wasm_bytes:bin.length,allocations_return_to_baseline:true}));
