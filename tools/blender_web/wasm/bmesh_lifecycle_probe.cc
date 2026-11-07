/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Diagnostic ONLY: request the actual Blender BM_mesh_create/free entry
 * points. This is not a mock allocator or stub CustomData implementation.
 */

#include "bmesh.hh"

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
