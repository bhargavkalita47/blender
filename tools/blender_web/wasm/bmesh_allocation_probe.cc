/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Temporary one-shot memory-allocation feasibility test, not production.
 * Invokes Blender's actual BM_mesh_create plus the real GuardedAlloc,
 * BLI_mempool and BKE CustomData_reset implementation. The allocated
 * empty mesh is intentionally left for WASM process teardown. The
 * complete BM_mesh_free dependency chain is verified separately.
 * NEVER expose this interface to a long-running browser application.
 */

#include "bmesh.hh"

extern "C" int web_bmesh_create_one_empty_mesh()
{
  const blender::BMeshCreateParams params{false};
  blender::BMesh *bm = blender::BM_mesh_create(&blender::bm_mesh_allocsize_default, &params);
  if (!bm) {
    return -1;
  }
  if (!bm->vpool || !bm->epool || !bm->lpool || !bm->fpool) {
    return -2;
  }
  if (bm->totvert != 0 || bm->totedge != 0 || bm->totface != 0 || bm->totloop != 0) {
    return -3;
  }
  return 0;
}
