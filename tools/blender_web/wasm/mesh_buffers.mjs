// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
// Copies Blender-owned BMesh geometry into independent JS typed arrays.
// The transient WASM byte offsets here are ONLY caller-owned scratch buffers;
// BMesh C++ pointers never leave the C ABI.
export function copyMeshBuffers(wasm, handle) {
  const floatCount = wasm._web_mesh_position_float_count(handle);
  const indexCount = wasm._web_mesh_triangle_index_count(handle);
  if (floatCount < 0 || indexCount < 0 || floatCount % 3 !== 0 || indexCount % 3 !== 0) {
    throw new Error(`Unsupported or invalid mesh: position=${floatCount}, indices=${indexCount}`);
  }
  if (floatCount === 0 || indexCount === 0) {
    return {positions: new Float32Array(0), indices: new Uint32Array(0)};
  }
  const pBytes = floatCount * Float32Array.BYTES_PER_ELEMENT;
  const iBytes = indexCount * Uint32Array.BYTES_PER_ELEMENT;
  if (!Number.isSafeInteger(pBytes) || !Number.isSafeInteger(iBytes)) {
    throw new Error("Mesh exceeds safe JavaScript allocation bounds");
  }
  const positionPtr = wasm._malloc(pBytes);
  if (!positionPtr) throw new Error("Cannot allocate WASM position buffer");
  let indexPtr = 0;
  try {
    indexPtr = wasm._malloc(iBytes);
    if (!indexPtr) throw new Error("Cannot allocate WASM index buffer");
    const pWritten = wasm._web_mesh_copy_positions(handle, positionPtr, floatCount);
    const iWritten = wasm._web_mesh_copy_triangles(handle, indexPtr, indexCount);
    if (pWritten !== floatCount || iWritten !== indexCount) {
      throw new Error(`Mesh copy changed during snapshot: ${pWritten}/${iWritten}`);
    }
    // Read HEAP views only after both mallocs; memory growth can detach earlier views.
    const positions = Float32Array.from(wasm.HEAPF32.subarray(
      positionPtr >>> 2, (positionPtr >>> 2) + floatCount));
    const indices = Uint32Array.from(wasm.HEAPU32.subarray(
      indexPtr >>> 2, (indexPtr >>> 2) + indexCount));
    const vertexCount = floatCount / 3;
    for (const i of indices) {
      if (i >= vertexCount) throw new Error("Blender mesh index is outside vertex buffer");
    }
    for (const v of positions) {
      if (!Number.isFinite(v)) throw new Error("Blender vertex contains a non-finite coordinate");
    }
    return {positions, indices};
  } finally {
    if (indexPtr) wasm._free(indexPtr);
    wasm._free(positionPtr);
  }
}
