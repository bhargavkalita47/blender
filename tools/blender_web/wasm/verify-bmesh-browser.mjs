// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// Execute original Blender BMesh topology and copied vertex/index arrays in
// actual Chromium and Firefox WebAssembly browser runtimes, not Node emulation.
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {readFile} from "node:fs/promises";
import {resolve} from "node:path";
import {chromium, firefox, webkit} from "playwright";

const out = resolve(process.argv[2] || "build/blender_web/bmesh_wasm");
const libraryRoot = resolve("tools/blender_web/wasm");
const paths = new Map([
  ["/", {path: null, type:"text/html"}],
  ["/bmesh_handles.mjs", {path: resolve(out,"bmesh_handles.mjs"), type:"text/javascript"}],
  ["/bmesh_handles.wasm", {path: resolve(out,"bmesh_handles.wasm"), type:"application/wasm"}],
  ["/mesh_buffers.mjs", {path: resolve(libraryRoot,"mesh_buffers.mjs"), type:"text/javascript"}],
]);
const server = createServer(async (req, res) => {
  const path = (req.url || "/").split("?")[0];
  const item = paths.get(path);
  if (!item) { res.writeHead(404); res.end(); return; }
  try {
    const body = item.path
      ? await readFile(item.path)
      : Buffer.from("<!doctype html><meta charset='utf-8'><title>Blender WASM browser test</title>");
    res.writeHead(200, {"content-type":item.type, "cache-control":"no-store",
      "cross-origin-resource-policy":"same-origin"});
    res.end(body);
  } catch (error) {
    res.writeHead(500); res.end(String(error));
  }
});
await new Promise((accept, reject) => {
  server.once("error", reject);
  server.listen(0, "127.0.0.1", accept);
});
const port = server.address().port;
const results = [];
try {
  for (const [name, engine] of [["chromium",chromium],["firefox",firefox],["webkit",webkit]]) {
    const browser = await engine.launch({headless:true});
    try {
      const page = await browser.newPage();
      const errors = [];
      page.on("pageerror", error => errors.push(String(error)));
      await page.goto(`http://127.0.0.1:${port}/`);
      const data = await page.evaluate(async () => {
        const {default:init} = await import("/bmesh_handles.mjs");
        const {copyMeshBuffers} = await import("/mesh_buffers.mjs");
        const wasm = await init();
        function ensure(condition, why) {
          if (!condition) throw new Error(why);
        }
        const baseline = wasm._web_mesh_memory_bytes();
        const handle = wasm._web_mesh_create_cube();
        ensure(handle > 0, "Could not create Blender cube");
        function snapshot(vertices, faces, topZ) {
          ensure(wasm._web_mesh_validate_topology(handle) === 0, "Invalid Blender BMesh topology");
          ensure(wasm._web_mesh_verts(handle) === vertices, "Wrong vertex count");
          ensure(wasm._web_mesh_faces(handle) === faces, "Wrong face count");
          ensure(wasm._web_mesh_top_z(handle) === topZ, "Wrong top cap Z");
          const mesh = copyMeshBuffers(wasm, handle);
          ensure(mesh.positions.length === vertices*3, "Wrong vertex buffer length");
          ensure(mesh.indices.length === faces*6, "Wrong triangulated index length");
          const maxZ = Math.max(...Array.from(mesh.positions).filter((_,i) => i%3 === 2));
          ensure(maxZ === topZ, "Position buffer does not reflect Blender extrusion");
          return {positions:Array.from(mesh.positions), indices:Array.from(mesh.indices)};
        }
        const initial = snapshot(8, 6, 1);
        ensure(wasm._web_mesh_extrude_top(handle, 1) === 0, "First BMO extrude failed");
        snapshot(12, 10, 2);
        ensure(wasm._web_mesh_extrude_top(handle, 0.5) === 0, "Second BMO extrude failed");
        const result = snapshot(16, 14, 2.5);
        ensure(wasm._web_mesh_destroy(handle) === 0, "Failed to destroy Blender BMesh");
        ensure(wasm._web_mesh_validate_topology(handle) === -1, "Stale handle accepted");
        ensure(wasm._web_mesh_memory_bytes() === baseline, "Leaked Blender allocated bytes");
        for(let i=0;i<50;i++) {
          const h = wasm._web_mesh_create_cube();
          ensure(h>0, "Repeated create failed");
          ensure(wasm._web_mesh_extrude_top(h,1)===0, "Repeated extrude failed");
          ensure(copyMeshBuffers(wasm,h).indices.length===60, "Repeated mesh export failed");
          ensure(wasm._web_mesh_destroy(h)===0, "Repeated destroy failed");
        }
        ensure(wasm._web_mesh_memory_bytes()===baseline, "50 browser edit cycles leaked memory");
        return {
          engine:"real Blender BMesh",
          initial_vertices: initial.positions.length/3,
          final_vertices: result.positions.length/3,
          final_indices: result.indices.length,
          final_geometry: result,
          stress_cycles:50,
          wasm_mem_baseline:baseline,
          wasm_mem_final:wasm._web_mesh_memory_bytes(),
          browser_webassembly: typeof WebAssembly === "object"
        };
      });
      assert.equal(errors.length, 0, `${name} page errors: ${errors.join(", ")}`);
      assert.equal(data.browser_webassembly, true);
      results.push({name, ...data});
      console.log(JSON.stringify({status:"pass",browser:name,
        initial_vertices:data.initial_vertices, final_vertices:data.final_vertices,
        final_indices:data.final_indices, stress_cycles:data.stress_cycles}));
    } finally { await browser.close(); }
  }
  for (const result of results.slice(1)) {
    assert.deepEqual(results[0].final_geometry, result.final_geometry,
      "All browser engines must receive identical Blender-owned mesh data");
  }
  console.log(JSON.stringify({status:"pass",stage:"Phase 1.3.3 browser compatibility",
    browsers:results.map(r=>r.name),geometry_identical:true}));
} finally {
  await new Promise((accept, reject) => server.close(err=>err?reject(err):accept()));
}
