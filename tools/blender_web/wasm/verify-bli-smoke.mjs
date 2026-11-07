// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Phase 1.3.1: evaluate functions implemented by Blender's actual
// source/blender/blenlib/intern/math_base.cc inside an Emscripten WASM module.

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const outDir = resolve(process.argv[2] || "build/blender_web/wasm");
const wasmPath = resolve(outDir, "bli_smoke.wasm");
const jsPath = resolve(outDir, "bli_smoke.mjs");

const magic = await readFile(wasmPath);
assert.equal(magic.subarray(0, 4).toString("hex"), "0061736d",
  "Output must contain a genuine WebAssembly binary");
assert.ok(magic.length > 128, "WASM output unexpectedly small");

const { default: createBlenderBli } = await import(pathToFileURL(jsPath).href);
assert.equal(typeof createBlenderBli, "function", "Expected modularized JS factory");
const instance = await createBlenderBli();

for (const symbol of [
  "_web_bli_pow_i",
  "_web_bli_double_round",
  "_web_bli_floor_power_of_10",
  "_web_bli_ceil_power_of_10",
]) {
  assert.equal(typeof instance[symbol], "function", "Missing WASM binding: " + symbol);
}

assert.equal(instance._web_bli_pow_i(2, 10), 1024);
assert.equal(instance._web_bli_pow_i(-2, 3), -8);
assert.equal(instance._web_bli_pow_i(5, 0), 1);
assert.equal(instance._web_bli_pow_i(2, -1), -1); // adapter guard

// Blender's double_round uses ties-to-even (banker's rounding).
assert.equal(instance._web_bli_double_round(2.5, 0), 2);
assert.equal(instance._web_bli_double_round(3.5, 0), 4);
assert.equal(instance._web_bli_double_round(-2.5, 0), -2);

const near = (actual, expected, epsilon = 1e-5) => {
  assert.ok(Math.abs(actual - expected) <= epsilon,
    "Expected " + expected + ", got " + actual);
};
near(instance._web_bli_double_round(123.456, 2), 123.46);
near(instance._web_bli_floor_power_of_10(78), 10);
near(instance._web_bli_ceil_power_of_10(78), 100);
near(instance._web_bli_floor_power_of_10(0), 0);
near(instance._web_bli_ceil_power_of_10(0), 0);

console.log(JSON.stringify({
  status: "pass",
  test: "blender-bli-wasm-phase-1.3.1",
  source: "source/blender/blenlib/intern/math_base.cc",
  wasmBytes: magic.length,
  node: process.version,
  assertions: 13,
}));
