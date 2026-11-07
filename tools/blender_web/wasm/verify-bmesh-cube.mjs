// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// One-shot primitive test, not a lifetime-safe production API.
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
console.log(JSON.stringify({
  status:"pass",stage:"Blender BMesh cube construction",
  topology:{vertices:8,edges:12,faces:6,loops:24},
  wasm_bytes:bytes.length,
  caveat:"one-shot; teardown required before repeated usage"
}));
