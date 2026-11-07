/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Create, validate, and destroy a Blender cube with the original BMesh
 * constructors and allocator. Repetitions exercise mesh lifecycle with
 * topology rather than just empty mesh allocation.
 */
#include "bmesh.hh"
#include "MEM_guardedalloc.h"

namespace {

int create_cube_and_free()
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
      blender::BM_mesh_free(bm);
      return -2;
    }
  }
  for (int i = 0; i < 6; ++i) {
    blender::BMVert *face_verts[4] = {
        v[quad[i][0]], v[quad[i][1]], v[quad[i][2]], v[quad[i][3]]};
    if (!blender::BM_face_create_verts(
            bm, face_verts, 4, nullptr, blender::BM_CREATE_NOP, true))
    {
      blender::BM_mesh_free(bm);
      return -3;
    }
  }
  if (bm->totvert != 8 || bm->totedge != 12 || bm->totface != 6 || bm->totloop != 24) {
    blender::BM_mesh_free(bm);
    return -4;
  }

  blender::BM_mesh_free(bm);
  return 8120624;
}

}  // namespace

extern "C" int web_bmesh_make_cube_once()
{
  return create_cube_and_free();
}

extern "C" int web_bmesh_cube_stress(int iterations)
{
  if (iterations < 1 || iterations > 1000) {
    return -1;
  }
  if (create_cube_and_free() != 8120624) {
    return -2;
  }
  const size_t before = MEM_get_memory_in_use();
  for (int i = 0; i < iterations; ++i) {
    if (create_cube_and_free() != 8120624) {
      return -3;
    }
  }
  return MEM_get_memory_in_use() == before ? 0 : -4;
}
