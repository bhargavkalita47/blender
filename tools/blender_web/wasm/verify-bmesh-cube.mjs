// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// Creates and destroys real Blender cube topology with repeated WASM operations.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const dir = resolve(process.argv[2] || "build/blender_web/bmesh_wasm");
const bytes = await readFile(resolve(dir, "bmesh_cube.wasm"));
assert.equal(bytes.subarray(0, 4).toString("hex"), "0061736d");
const {default: instantiate} = await import(pathToFileURL(resolve(dir, "bmesh_cube.mjs")).href);
const wasm = await instantiate();
assert.equal(wasm._web_bmesh_make_cube_once(), 8120624,
  "Original Blender BM_vert_create + BM_face_create_verts must create a cube");
assert.equal(wasm._web_bmesh_cube_stress(0),-1);
assert.equal(wasm._web_bmesh_cube_stress(1000),0,
  "1000 Blender cube create/free cycles must preserve GuardedAlloc accounting");
console.log(JSON.stringify({
  status:"pass",stage:"Blender BMesh cube construction",
  topology:{vertices:8,edges:12,faces:6,loops:24},
  wasm_bytes:bytes.length,
  lifecycle_stress_repetitions:1000,
  memory_check:"GuardedAlloc memory in use returns to baseline"
}));
