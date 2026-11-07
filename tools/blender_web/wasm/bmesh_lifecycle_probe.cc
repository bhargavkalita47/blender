/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Diagnostic ONLY: request the actual Blender BM_mesh_create/free entry
 * points. This is not a mock allocator or stub CustomData implementation.
 */

#include "bmesh.hh"
#include "MEM_guardedalloc.h"

extern "C" int web_bmesh_lifecycle_probe()
{
  const blender::BMeshCreateParams params{false};
  blender::BMesh *bm = blender::BM_mesh_create(&blender::bm_mesh_allocsize_default, &params);
  if (!bm) {
    return -1;
  }
  const int total = bm->totvert + bm->totedge + bm->totface + bm->totloop;
  blender::BM_mesh_free(bm);
  return total;
}

/* True lifecycle regression: allocate AND free real Blender BMesh instances. */
extern "C" int web_bmesh_lifecycle_stress(int iterations)
{
  if (iterations <= 0 || iterations > 10000) {
    return -1;
  }
  if (web_bmesh_lifecycle_probe() != 0) {
    return -2;
  }
  const size_t initial_bytes = MEM_get_memory_in_use();
  for (int i = 0; i < iterations; i++) {
    if (web_bmesh_lifecycle_probe() != 0) {
      return -3;
    }
  }
  const size_t final_bytes = MEM_get_memory_in_use();
  // Allocator accounting excludes unused free capacity in the WASM linear heap.
  return final_bytes == initial_bytes ? 0 : -4;
}
