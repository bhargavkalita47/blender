/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Temporary one-shot Blender BMesh primitive construction check.
 * Geometry topology uses BM_vert_create and BM_face_create_verts from
 * original Blender bmesh_core.cc; no replacement topology algorithm.
 * The cube fixture is standard test input. Full cleanup and repeated
 * operations are gated separately by the proper lifecycle test.
 */
#include "bmesh.hh"

extern "C" int web_bmesh_make_cube_once()
{
  const blender::BMeshCreateParams params{false};
  blender::BMesh *bm = blender::BM_mesh_create(&blender::bm_mesh_allocsize_default, &params);
  if (!bm) {
    return -1;
  }

  constexpr float positions[8][3] = {
      {-1, -1, -1}, {1, -1, -1}, {1, 1, -1}, {-1, 1, -1},
      {-1, -1, 1},  {1, -1, 1},  {1, 1, 1},  {-1, 1, 1},
  };
  constexpr int quad[6][4] = {
      {0, 3, 2, 1}, {4, 5, 6, 7}, {0, 1, 5, 4},
      {1, 2, 6, 5}, {2, 3, 7, 6}, {3, 0, 4, 7},
  };
  blender::BMVert *v[8];
  for (int i = 0; i < 8; ++i) {
    v[i] = blender::BM_vert_create(bm, positions[i], nullptr, blender::BM_CREATE_NOP);
    if (!v[i]) {
      return -2;
    }
  }
  for (int i = 0; i < 6; ++i) {
    blender::BMVert *face_verts[4] = {
        v[quad[i][0]], v[quad[i][1]], v[quad[i][2]], v[quad[i][3]]};
    if (!blender::BM_face_create_verts(
            bm, face_verts, 4, nullptr, blender::BM_CREATE_NOP, true))
    {
      return -3;
    }
  }
  if (bm->totvert != 8 || bm->totedge != 12 || bm->totface != 6 || bm->totloop != 24) {
    return -4;
  }

  // This diagnostic creates only one cube and leaves the mesh to process
  // teardown. Production and stress tests MUST pair BM_mesh_create/free.
  return 8120624;
}
