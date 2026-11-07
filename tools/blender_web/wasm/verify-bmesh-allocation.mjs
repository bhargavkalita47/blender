// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// One-shot allocation-only experiment. A deliberately unfreed empty mesh
// is reclaimed when the Node/WASM process terminates. NOT a browser API.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const dir = resolve(process.argv[2] || "build/blender_web/bmesh_wasm");
const bytes = await readFile(resolve(dir, "bmesh_alloc.wasm"));
assert.equal(bytes.subarray(0, 4).toString("hex"), "0061736d");
const { default: instantiate } = await import(pathToFileURL(resolve(dir, "bmesh_alloc.mjs")).href);
const module = await instantiate();
assert.equal(module._web_bmesh_create_one_empty_mesh(), 0);
console.log(JSON.stringify({ status: "pass", stage: "BMesh empty allocation", bytes: bytes.length,
  includes: ["BM_mesh_create", "MEM_guardedalloc", "BLI_mempool", "CustomData_reset"],
  warning: "one-shot diagnostic; intentionally not a lifetime-safe API" }));
