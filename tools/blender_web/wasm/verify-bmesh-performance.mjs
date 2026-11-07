// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// Phase 1.3.4 reproducible stress/performance benchmark for the actual
// Blender BMesh WASM implementation. This is not a whole-app benchmark.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {performance} from "node:perf_hooks";
import {resolve} from "node:path";
import {pathToFileURL} from "node:url";
import {copyMeshBuffers} from "./mesh_buffers.mjs";

const output = resolve(process.argv[2] || "build/blender_web/bmesh_wasm");
const iterations = Number(process.argv[3] || "2000");
assert.ok(Number.isInteger(iterations) && iterations >= 100 && iterations <= 20000,
  "Require 100..20000 full mesh edit/export/free cycles");
const bytes = await readFile(resolve(output,"bmesh_handles.wasm"));
assert.equal(bytes.subarray(0,4).toString("hex"),"0061736d");
const {default:init} = await import(pathToFileURL(resolve(output,"bmesh_handles.mjs")).href);
const initBegin = performance.now();
const wasm = await init();
const initMs = performance.now() - initBegin;

function cycle() {
  const id = wasm._web_mesh_create_cube();
  assert.ok(id > 0, "Blender BMesh constructor failed");
  assert.equal(wasm._web_mesh_validate_topology(id), 0);
  assert.equal(wasm._web_mesh_extrude_top(id, 1), 0, "First original Blender extrude failed");
  assert.equal(wasm._web_mesh_extrude_top(id, 0.5), 0, "Second original Blender extrude failed");
  assert.equal(wasm._web_mesh_validate_topology(id), 0, "Mesh topology corrupted");
  const {positions, indices} = copyMeshBuffers(wasm, id);
  assert.equal(positions.length, 48);
  assert.equal(indices.length, 84);
  assert.equal(wasm._web_mesh_destroy(id), 0);
  assert.equal(wasm._web_mesh_destroy(id), -1, "Stale handle not invalidated");
}
// Warmup before memory baselines; caches should be initialized.
for(let i=0;i<50;i++)cycle();
const memoryBaseline = wasm._web_mesh_memory_bytes();
const heapBaseline = wasm.HEAPF32.buffer.byteLength;
const durations=[];
let maxAllocatorBytes = memoryBaseline;
const totalBegin = performance.now();
for(let i=0;i<iterations;i++) {
  const begin = performance.now();
  cycle();
  durations.push(performance.now()-begin);
  if ((i + 1) % 100 === 0) {
    const n = wasm._web_mesh_memory_bytes();
    maxAllocatorBytes = Math.max(maxAllocatorBytes,n);
    assert.equal(n, memoryBaseline, "Tracked Blender allocation leak after completed cycles");
  }
}
const elapsedMs = performance.now()-totalBegin;
assert.equal(wasm._web_mesh_live_count(),0);
assert.equal(wasm._web_mesh_memory_bytes(),memoryBaseline);
const heapAfter = wasm.HEAPF32.buffer.byteLength;
assert.ok(heapAfter <= Math.max(heapBaseline, 64*1024*1024),
  "Excessive WASM linear-memory growth during small fixed geometry stress test");
assert.ok(elapsedMs < 90000, "2000 small BMesh create/edit/export/free operations too slow");
durations.sort((a,b)=>a-b);
const p95Ms = durations[Math.ceil(durations.length*.95)-1];
const out = {
  status:"pass",stage:"Phase 1.3.4 WASM BMesh stress and performance",
  wasm_bytes:bytes.length,iterations,
  emscripten_module_init_ms:Number(initMs.toFixed(3)),
  elapsed_ms:Number(elapsedMs.toFixed(3)),
  operations_per_second:Number((iterations*1000/elapsedMs).toFixed(2)),
  p95_cycle_ms:Number(p95Ms.toFixed(3)),
  bmesh_original_extrusions:iterations*2,
  memory_before_bytes:memoryBaseline,
  memory_after_bytes:wasm._web_mesh_memory_bytes(),
  peak_sampled_allocator_bytes:maxAllocatorBytes,
  wasm_heap_start_bytes:heapBaseline,
  wasm_heap_finish_bytes:heapAfter
};
console.log(JSON.stringify(out));
