// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// Phase 1.3.2 opaque integer handle API / Blender BMO WASM end-to-end test.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {resolve} from "node:path";
import {pathToFileURL} from "node:url";

const dir=resolve(process.argv[2]||"build/blender_web/bmesh_wasm");
const bytes=await readFile(resolve(dir,"bmesh_handles.wasm"));
assert.equal(bytes.subarray(0,4).toString("hex"),"0061736d");
const {default:instantiate}=await import(pathToFileURL(resolve(dir,"bmesh_handles.mjs")).href);
const wasm=await instantiate();
assert.equal(wasm._web_mesh_live_count(),0);
assert.equal(wasm._web_mesh_destroy(1),-1,"Unknown mesh handle must be rejected");
assert.equal(wasm._web_mesh_verts(-1),-1);

const h=wasm._web_mesh_create_cube();
assert.ok(h>0,"Should return opaque positive mesh handle");
assert.equal(wasm._web_mesh_verts(h),8);
assert.equal(wasm._web_mesh_edges(h),12);
assert.equal(wasm._web_mesh_faces(h),6);
assert.equal(wasm._web_mesh_loops(h),24);
assert.equal(wasm._web_mesh_top_z(h),1);
assert.equal(wasm._web_mesh_validate_topology(h),0,"Initial cube must be a closed manifold");
assert.equal(wasm._web_mesh_extrude_top(h,1),0);
assert.equal(wasm._web_mesh_verts(h),12);
assert.equal(wasm._web_mesh_edges(h),20);
assert.equal(wasm._web_mesh_faces(h),10);
assert.equal(wasm._web_mesh_loops(h),40);
assert.equal(wasm._web_mesh_top_z(h),2);
assert.equal(wasm._web_mesh_validate_topology(h),0,"Extruded cube must have correct loops and radial links");
assert.equal(wasm._web_mesh_extrude_top(h,0.5),0);
assert.equal(wasm._web_mesh_verts(h),16);
assert.equal(wasm._web_mesh_edges(h),28);
assert.equal(wasm._web_mesh_faces(h),14);
assert.equal(wasm._web_mesh_loops(h),56);
assert.equal(wasm._web_mesh_top_z(h),2.5);
assert.equal(wasm._web_mesh_validate_topology(h),0,"Second extrusion must preserve manifold topology");
assert.equal(wasm._web_mesh_destroy(h),0);
assert.equal(wasm._web_mesh_destroy(h),-1,"Stale handle must not free twice");
assert.equal(wasm._web_mesh_faces(h),-1,"Stale handle must be invalid");
assert.equal(wasm._web_mesh_extrude_top(h,1),-1);
assert.equal(wasm._web_mesh_validate_topology(h),-1);
assert.equal(wasm._web_mesh_live_count(),0);

// Handle generations: reuse a slot must not validate old handles.
const h2=wasm._web_mesh_create_cube();
assert.ok(h2>0&&h2!==h,"Reused slot must get a new handle generation");
assert.equal(wasm._web_mesh_faces(h),-1);
assert.equal(wasm._web_mesh_destroy(h2),0);

// A bounded set of concurrent meshes.
const handles=[];
for(let i=0;i<16;i++){
  const id=wasm._web_mesh_create_cube();
  assert.ok(id>0);
  handles.push(id);
}
assert.equal(wasm._web_mesh_live_count(),16);
assert.equal(wasm._web_mesh_create_cube(),-3,"Capacity guard must work");
for(const id of handles){ assert.equal(wasm._web_mesh_destroy(id),0); }
assert.equal(wasm._web_mesh_live_count(),0);

// Warmup can legitimately populate global caches; compare after warmup.
const baseline=wasm._web_mesh_memory_bytes();
for(let i=0;i<1000;i++){
  const id=wasm._web_mesh_create_cube();
  assert.ok(id>0);
  assert.equal(wasm._web_mesh_extrude_top(id,1),0);
  assert.equal(wasm._web_mesh_extrude_top(id,0.5),0);
  assert.equal(wasm._web_mesh_validate_topology(id),0,"Stress iteration topology must be valid");
  assert.equal(wasm._web_mesh_destroy(id),0);
}
assert.equal(wasm._web_mesh_live_count(),0);
const memoryAfter=wasm._web_mesh_memory_bytes();
assert.equal(memoryAfter,baseline,
  "Blender GuardedAlloc should have no net bytes after 1000 full mesh/edit/free cycles");
console.log(JSON.stringify({
  status:"pass",stage:"Blender BMesh opaque-handle WASM editing",
  wasm_bytes:bytes.length,stress_cycles:1000,
  BMO_extrusions:2000,stale_handles_rejected:true,
  concurrent_meshes:16,
  allocator_baseline_bytes:baseline,allocator_final_bytes:memoryAfter
}));
