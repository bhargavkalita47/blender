/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Blender's original BMesh vertex/face constructors and *original*
 * discrete-face extrusion operator, through the unmodified BMO engine.
 * Only the operator registration TABLE is compile-time reduced to the
 * original delete+extrude entries for this WASM feasibility experiment.
 */

#include "MEM_guardedalloc.h"
#include "bmesh.hh"

namespace {

int cube_extrude_once()
{
  const blender::BMeshCreateParams params{true};
  blender::BMesh *bm = blender::BM_mesh_create(&blender::bm_mesh_allocsize_default, &params);
  if (!bm) {
    return -1;
  }
  constexpr float xyz[8][3] = {
      {-1, -1, -1}, {1, -1, -1}, {1, 1, -1}, {-1, 1, -1},
      {-1, -1, 1}, {1, -1, 1}, {1, 1, 1}, {-1, 1, 1},
  };
  constexpr int quads[6][4] = {
      {0, 3, 2, 1}, {4, 5, 6, 7}, {0, 1, 5, 4},
      {1, 2, 6, 5}, {2, 3, 7, 6}, {3, 0, 4, 7},
  };
  blender::BMVert *v[8]{};
  blender::BMFace *faces[6]{};
  for (int i = 0; i < 8; ++i) {
    v[i] = blender::BM_vert_create(bm, xyz[i], nullptr, blender::BM_CREATE_NOP);
    if (!v[i]) {
      blender::BM_mesh_free(bm);
      return -2;
    }
  }
  for (int i = 0; i < 6; ++i) {
    blender::BMVert *quad[4] = {
        v[quads[i][0]], v[quads[i][1]], v[quads[i][2]], v[quads[i][3]]};
    faces[i] = blender::BM_face_create_verts(
        bm, quad, 4, nullptr, blender::BM_CREATE_NOP, true);
    if (!faces[i]) {
      blender::BM_mesh_free(bm);
      return -3;
    }
  }
  if (bm->totvert != 8 || bm->totedge != 12 || bm->totface != 6 || bm->totloop != 24) {
    blender::BM_mesh_free(bm);
    return -4;
  }

  blender::BMOperator op;
  blender::BMO_op_init(bm, &op, blender::BMO_FLAG_DEFAULTS, "extrude_discrete_faces");
  blender::BMO_slot_buffer_from_single(
      &op, blender::BMO_slot_get(op.slots_in, "faces"), &faces[1]->head);
  blender::BMO_op_exec(bm, &op);

  blender::BMOIter iter;
  blender::BMFace *cap = nullptr;
  int caps = 0;
  int moved_verts = 0;
  BMO_ITER (cap, &iter, op.slots_out, "faces.out", blender::BM_FACE) {
    ++caps;
    blender::BMLoop *loop = BM_FACE_FIRST_LOOP(cap);
    blender::BMLoop *first = loop;
    do {
      loop->v->co[2] += 1.0f;
      ++moved_verts;
      loop = loop->next;
    } while (loop != first);
  }
  blender::BMO_op_finish(bm, &op);

  const bool valid = caps == 1 && moved_verts == 4 &&
                     bm->totvert == 12 && bm->totedge == 20 &&
                     bm->totface == 10 && bm->totloop == 40;
  blender::BM_mesh_free(bm);
  return valid ? 0 : -5;
}

} // namespace

extern "C" int web_bmesh_extrude_cube_once()
{
  return cube_extrude_once();
}

extern "C" int web_bmesh_extrude_cube_stress(int count)
{
  if (count < 1 || count > 1000) {
    return -1;
  }
  const int warmup = cube_extrude_once();
  if (warmup != 0) {
    return warmup;
  }
  const size_t initial_bytes = MEM_get_memory_in_use();
  for (int i = 0; i < count; ++i) {
    const int result = cube_extrude_once();
    if (result != 0) {
      return result;
    }
  }
  return MEM_get_memory_in_use() == initial_bytes ? 0 : -6;
}
