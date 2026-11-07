/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Phase 1.3.2 test-facing C ABI for genuine Blender BMesh.
 * Opaque integer handles protect callers from raw C++ / WASM pointers.
 * Geometry and extrusion are delegated to ORIGINAL Blender BMesh sources.
 *
 * Capacity and the primitive are deliberately bounded for feasibility.
 * Not a production scene manager or generalized mesh editing API.
 */
#include "MEM_guardedalloc.h"
#include "bmesh.hh"

#include <cstdint>

namespace {

constexpr unsigned kCapacity = 16;
constexpr unsigned kGenerationLimit = 0x007FFFFFu;

struct MeshSlot {
  blender::BMesh *mesh = nullptr;
  blender::BMFace *top_face = nullptr;
  unsigned generation = 1;
};

MeshSlot slots[kCapacity];

int make_handle(unsigned slot)
{
  return int((slots[slot].generation << 8) | (slot + 1));
}

MeshSlot *get_slot(int handle)
{
  if (handle <= 0) {
    return nullptr;
  }
  const unsigned token = unsigned(handle);
  const unsigned offset = token & 0xFF;
  const unsigned generation = token >> 8;
  if (offset < 1 || offset > kCapacity) {
    return nullptr;
  }
  MeshSlot *slot = &slots[offset - 1];
  return slot->mesh && slot->generation == generation ? slot : nullptr;
}

bool create_cube(blender::BMesh *bm, blender::BMFace **top)
{
  constexpr float positions[8][3] = {
      {-1, -1, -1}, {1, -1, -1}, {1, 1, -1}, {-1, 1, -1},
      {-1, -1, 1},  {1, -1, 1},  {1, 1, 1},  {-1, 1, 1},
  };
  constexpr int quads[6][4] = {
      {0, 3, 2, 1}, {4, 5, 6, 7}, {0, 1, 5, 4},
      {1, 2, 6, 5}, {2, 3, 7, 6}, {3, 0, 4, 7},
  };
  blender::BMVert *verts[8]{};
  blender::BMFace *faces[6]{};
  for (int i = 0; i < 8; ++i) {
    verts[i] = blender::BM_vert_create(bm, positions[i], nullptr, blender::BM_CREATE_NOP);
    if (!verts[i]) {
      return false;
    }
  }
  for (int i = 0; i < 6; ++i) {
    blender::BMVert *quad[4] = {verts[quads[i][0]], verts[quads[i][1]],
                               verts[quads[i][2]], verts[quads[i][3]]};
    faces[i] = blender::BM_face_create_verts(
        bm, quad, 4, nullptr, blender::BM_CREATE_NOP, true);
    if (!faces[i]) {
      return false;
    }
  }
  *top = faces[1];
  return bm->totvert == 8 && bm->totedge == 12 && bm->totface == 6 && bm->totloop == 24;
}

}  // namespace

extern "C" {

int web_mesh_create_cube()
{
  unsigned index = kCapacity;
  for (unsigned i = 0; i < kCapacity; ++i) {
    if (slots[i].mesh == nullptr) {
      index = i;
      break;
    }
  }
  if (index == kCapacity) {
    return -3;
  }
  const blender::BMeshCreateParams params{true};
  blender::BMesh *bm = blender::BM_mesh_create(&blender::bm_mesh_allocsize_default, &params);
  if (!bm) {
    return -2;
  }
  blender::BMFace *top = nullptr;
  if (!create_cube(bm, &top)) {
    blender::BM_mesh_free(bm);
    return -2;
  }
  slots[index].mesh = bm;
  slots[index].top_face = top;
  return make_handle(index);
}

int web_mesh_destroy(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) {
    return -1;
  }
  blender::BM_mesh_free(slot->mesh);
  slot->mesh = nullptr;
  slot->top_face = nullptr;
  slot->generation = slot->generation == kGenerationLimit ? 1 : slot->generation + 1;
  return 0;
}

int web_mesh_verts(int handle)
{
  MeshSlot *slot = get_slot(handle);
  return slot ? slot->mesh->totvert : -1;
}

int web_mesh_edges(int handle)
{
  MeshSlot *slot = get_slot(handle);
  return slot ? slot->mesh->totedge : -1;
}

int web_mesh_faces(int handle)
{
  MeshSlot *slot = get_slot(handle);
  return slot ? slot->mesh->totface : -1;
}

int web_mesh_loops(int handle)
{
  MeshSlot *slot = get_slot(handle);
  return slot ? slot->mesh->totloop : -1;
}

float web_mesh_top_z(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot || !slot->top_face) {
    return -99999.0f;
  }
  blender::BMLoop *loop = BM_FACE_FIRST_LOOP(slot->top_face);
  blender::BMLoop *first = loop;
  float sum = 0.0f;
  unsigned n = 0;
  do {
    sum += loop->v->co[2];
    ++n;
    loop = loop->next;
  } while (loop != first);
  return n ? sum / n : -99999.0f;
}

int web_mesh_extrude_top(int handle, float delta_z)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot || !slot->top_face) {
    return -1;
  }
  blender::BMOperator op;
  blender::BMO_op_init(slot->mesh, &op, blender::BMO_FLAG_DEFAULTS, "extrude_discrete_faces");
  blender::BMO_slot_buffer_from_single(
      &op, blender::BMO_slot_get(op.slots_in, "faces"), &slot->top_face->head);
  blender::BMO_op_exec(slot->mesh, &op);
  blender::BMOIter iter;
  blender::BMFace *cap = nullptr;
  blender::BMFace *new_top = nullptr;
  unsigned caps = 0;
  BMO_ITER (cap, &iter, op.slots_out, "faces.out", blender::BM_FACE) {
    ++caps;
    new_top = cap;
    blender::BMLoop *loop = BM_FACE_FIRST_LOOP(cap);
    blender::BMLoop *first = loop;
    do {
      loop->v->co[2] += delta_z;
      loop = loop->next;
    } while (loop != first);
  }
  blender::BMO_op_finish(slot->mesh, &op);
  if (caps != 1 || !new_top) {
    slot->top_face = nullptr;
    return -2;
  }
  slot->top_face = new_top;
  return 0;
}

int web_mesh_live_count()
{
  int count = 0;
  for (const MeshSlot &slot : slots) {
    if (slot.mesh) {
      ++count;
    }
  }
  return count;
}

int web_mesh_memory_bytes()
{
  // Test fixtures run with small memory sizes that fit signed 32-bit.
  return int(MEM_get_memory_in_use());
}

}  // extern "C"
