// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// The real Blender BMesh constructor and destructor, via WebAssembly.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {resolve} from "node:path";
import {pathToFileURL} from "node:url";
const out=resolve(process.argv[2]||"build/blender_web/bmesh_wasm");
const binary=await readFile(resolve(out,"bmesh_lifecycle_full.wasm"));
assert.equal(binary.subarray(0,4).toString("hex"),"0061736d");
const {default:create}=await import(pathToFileURL(resolve(out,"bmesh_lifecycle_full.mjs")).href);
const wasm=await create();
assert.equal(wasm._web_bmesh_lifecycle_probe(),0,"Expected empty BMesh create/free");
assert.equal(wasm._web_bmesh_lifecycle_stress(0),-1,"Reject invalid iteration count");
assert.equal(wasm._web_bmesh_lifecycle_stress(1),0,"Single alloc/free");
assert.equal(wasm._web_bmesh_lifecycle_stress(100),0,"100 alloc/free");
assert.equal(wasm._web_bmesh_lifecycle_stress(1000),0,"1000 alloc/free memory accounting");
console.log(JSON.stringify({status:"pass",stage:"BMesh allocate/free",
  iterations:1000,wasm_bytes:binary.length,method:"GuardedAlloc accounted memory stable"}));
