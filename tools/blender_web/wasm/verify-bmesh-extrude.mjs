// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// Verifies Blender's original BMesh discrete-face extrusion operator in WASM.
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {resolve} from "node:path";
import {pathToFileURL} from "node:url";

const dir=resolve(process.argv[2]||"build/blender_web/bmesh_wasm");
const bytes=await readFile(resolve(dir,"bmesh_extrude.wasm"));
assert.equal(bytes.subarray(0,4).toString("hex"),"0061736d");
const {default:instantiate}=await import(pathToFileURL(resolve(dir,"bmesh_extrude.mjs")).href);
const wasm=await instantiate();
assert.equal(wasm._web_bmesh_extrude_cube_once(),0,
  "Original BMesh extrusion must generate 12 vertices, 20 edges, 10 faces, 40 loops");
assert.equal(wasm._web_bmesh_extrude_cube_stress(0),-1);
assert.equal(wasm._web_bmesh_extrude_cube_stress(1),0);
assert.equal(wasm._web_bmesh_extrude_cube_stress(100),0);
console.log(JSON.stringify({status:"pass",stage:"Original Blender BMO discrete-face extrusion",
  expected:{vertices:12,edges:20,faces:10,loops:40},
  successful_repeated_extrusions:100,wasm_bytes:bytes.length,
  memory_check:"GuardedAlloc returns to baseline after allocation/extrusion/free"}));
