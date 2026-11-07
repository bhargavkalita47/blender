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
#if defined(BLENDER_WEB_NATIVE_UV)
#  include "BKE_customdata.hh"
#  include "DNA_customdata_types.h"
#endif
#include "bmesh.hh"

#include <cstdint>
#include <cmath>
#include <limits>
#include <vector>
#include <algorithm>

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

// The primitive adapters construct topology ONLY with original Blender
// BM_vert_create/BM_face_create_verts. Parameters are deliberately bounded.
int create_extended_primitive(int kind, int segments, int rings)
{
  if ((kind == 1 && (segments < 1 || segments > 32 || rings < 1 || rings > 32)) ||
      (kind == 2 && (segments < 3 || segments > 64)) ||
      (kind == 3 && (segments < 3 || segments > 64 || rings < 3 || rings > 32))) {
    return -4;
  }
  unsigned index = kCapacity;
  for (unsigned i = 0; i < kCapacity; ++i) {
    if (!slots[i].mesh) { index = i; break; }
  }
  if (index == kCapacity) return -3;
  const blender::BMeshCreateParams params{true};
  blender::BMesh *bm = blender::BM_mesh_create(&blender::bm_mesh_allocsize_default, &params);
  if (!bm) return -2;
  bool ok = true;
  blender::BMFace *cap = nullptr;
  const auto vertex = [&](float x, float y, float z) {
    const float co[3] = {x, y, z};
    return blender::BM_vert_create(bm, co, nullptr, blender::BM_CREATE_NOP);
  };
  const auto face = [&](std::vector<blender::BMVert *> &v) -> blender::BMFace * {
    if (v.size() < 3) return nullptr;
    return blender::BM_face_create_verts(
        bm, v.data(), int(v.size()), nullptr, blender::BM_CREATE_NOP, true);
  };
  constexpr double pi = 3.1415926535897932384626433832795;
  if (kind == 1) {
    // Regular 2x2 XY grid with X/Y segment counts.
    std::vector<blender::BMVert *> v;
    v.reserve(size_t(segments + 1) * size_t(rings + 1));
    for (int y = 0; y <= rings && ok; ++y) {
      for (int x = 0; x <= segments && ok; ++x) {
        auto *p = vertex(float(2.0 * x / segments - 1.0),
                         float(2.0 * y / rings - 1.0), 0.0f);
        ok = p != nullptr;
        v.push_back(p);
      }
    }
    for (int y = 0; y < rings && ok; ++y) {
      for (int x = 0; x < segments && ok; ++x) {
        const int a = y * (segments + 1) + x;
        std::vector<blender::BMVert *> q = {
            v[a], v[a + 1], v[a + segments + 2], v[a + segments + 1]};
        ok = face(q) != nullptr;
      }
    }
  }
  else if (kind == 2) {
    // Cylinder radius=1, z=[-1,+1], closed by convex n-gon caps.
    std::vector<blender::BMVert *> bottom, top;
    bottom.reserve(segments);
    top.reserve(segments);
    for (int i = 0; i < segments && ok; ++i) {
      double phi = 2.0 * pi * i / segments;
      float x = float(std::cos(phi)), y = float(std::sin(phi));
      auto *b = vertex(x, y, -1.0f), *t = vertex(x, y, 1.0f);
      ok = b != nullptr && t != nullptr;
      bottom.push_back(b);
      top.push_back(t);
    }
    for (int i = 0; i < segments && ok; ++i) {
      const int j = (i + 1) % segments;
      std::vector<blender::BMVert *> q = {bottom[i], bottom[j], top[j], top[i]};
      ok = face(q) != nullptr;
    }
    if (ok) {
      std::vector<blender::BMVert *> bottom_rev(bottom.rbegin(), bottom.rend());
      ok = face(bottom_rev) != nullptr;
    }
    if (ok) cap = face(top);
    ok = ok && cap;
  }
  else if (kind == 3) {
    // UV sphere longitude segments and latitude intervals.
    blender::BMVert *north = vertex(0.0f, 0.0f, 1.0f);
    ok = north != nullptr;
    std::vector<std::vector<blender::BMVert *>> levels;
    for (int j = 1; j < rings && ok; ++j) {
      const double theta = pi * j / rings;
      const double radius = std::sin(theta), z = std::cos(theta);
      std::vector<blender::BMVert *> ring;
      for (int i = 0; i < segments && ok; ++i) {
        const double phi = 2.0 * pi * i / segments;
        auto *p = vertex(float(radius * std::cos(phi)),
                         float(radius * std::sin(phi)), float(z));
        ok = p != nullptr;
        ring.push_back(p);
      }
      levels.push_back(std::move(ring));
    }
    blender::BMVert *south = ok ? vertex(0.0f, 0.0f, -1.0f) : nullptr;
    ok = ok && south;
    for (int i = 0; i < segments && ok; ++i) {
      int next = (i + 1) % segments;
      std::vector<blender::BMVert *> tri = {
          north, levels.front()[i], levels.front()[next]};
      ok = face(tri) != nullptr;
    }
    for (int j = 0; j + 1 < int(levels.size()) && ok; ++j) {
      for (int i = 0; i < segments && ok; ++i) {
        int next = (i + 1) % segments;
        std::vector<blender::BMVert *> q = {
            levels[j][i], levels[j + 1][i],
            levels[j + 1][next], levels[j][next]};
        ok = face(q) != nullptr;
      }
    }
    for (int i = 0; i < segments && ok; ++i) {
      int next = (i + 1) % segments;
      std::vector<blender::BMVert *> tri = {
          south, levels.back()[next], levels.back()[i]};
      ok = face(tri) != nullptr;
    }
  }
  if (!ok) {
    blender::BM_mesh_free(bm);
    return -2;
  }
  slots[index].mesh = bm;
  slots[index].top_face = cap;
  return make_handle(index);
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

int web_mesh_create_plane()
{
  // Phase 2.2.3: an open XY quad, using genuine Blender BMesh element creation.
  // Unlike a cube this has boundary edges, which the validator must recognize.
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
  constexpr float positions[4][3] = {
      {-1.0f, -1.0f, 0.0f}, {1.0f, -1.0f, 0.0f},
      {1.0f, 1.0f, 0.0f}, {-1.0f, 1.0f, 0.0f},
  };
  blender::BMVert *verts[4]{};
  bool ok = true;
  for (int i = 0; i < 4; ++i) {
    verts[i] = blender::BM_vert_create(bm, positions[i], nullptr, blender::BM_CREATE_NOP);
    if (!verts[i]) {
      ok = false;
      break;
    }
  }
  if (ok) {
    ok = blender::BM_face_create_verts(
             bm, verts, 4, nullptr, blender::BM_CREATE_NOP, true) != nullptr;
  }
  if (!ok || bm->totvert != 4 || bm->totedge != 4 || bm->totface != 1 ||
      bm->totloop != 4) {
    blender::BM_mesh_free(bm);
    return -2;
  }
  slots[index].mesh = bm;
  slots[index].top_face = nullptr;  // Closed-cube top-cap extrusion is not available.
  return make_handle(index);
}

int web_mesh_create_grid(int x_segments, int y_segments)
{
  return create_extended_primitive(1, x_segments, y_segments);
}

int web_mesh_create_cylinder(int segments)
{
  return create_extended_primitive(2, segments, 0);
}

int web_mesh_create_uv_sphere(int segments, int rings)
{
  return create_extended_primitive(3, segments, rings);
}

int web_mesh_translate(int handle, float dx, float dy, float dz)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) {
    return -1;
  }
  const float delta[3] = {dx, dy, dz};
  for (const float component : delta) {
    if (!std::isfinite(component)) {
      return -2;
    }
  }
  // Validate the entire operation first so a float overflow cannot leave
  // half of a BMesh translated. Geometry storage is original Blender BMVert.
  blender::BMIter iter;
  blender::BMVert *vert = nullptr;
  BM_ITER_MESH (vert, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
    for (int axis = 0; axis < 3; ++axis) {
      const double value = double(vert->co[axis]) + double(delta[axis]);
      if (!std::isfinite(value) || std::abs(value) >
                                       double(std::numeric_limits<float>::max())) {
        return -3;
      }
    }
  }
  BM_ITER_MESH (vert, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
    for (int axis = 0; axis < 3; ++axis) {
      vert->co[axis] += delta[axis];
    }
  }
  return 0;
}

// Phase 2.2.3 element editing: vertex indices are enumeration-order IDs.
// They are deliberately NOT persistent across topology mutation.
int web_mesh_select_vertex(int handle, int index, int selected)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (index < 0 || index >= slot->mesh->totvert || (selected != 0 && selected != 1)) {
    return -2;
  }
  blender::BMIter iter;
  blender::BMVert *vert = nullptr;
  int i = 0;
  BM_ITER_MESH (vert, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
    if (i++ == index) {
      blender::BM_vert_select_set(slot->mesh, vert, selected != 0);
      return 0;
    }
  }
  return -3;
}

int web_mesh_selected_vert_count(int handle);
#if defined(BLENDER_WEB_NATIVE_SUBDIVIDE)
int web_mesh_subdivide_all_edges(int handle, int cuts)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (cuts < 1 || cuts > 2 || slot->mesh->totedge > 2048 ||
      slot->mesh->totedge <= 0) return -2;
  const int before_verts = slot->mesh->totvert;
  blender::BMOperator op;
  blender::BMO_op_init(slot->mesh, &op, blender::BMO_FLAG_DEFAULTS, "subdivide_edges");
  blender::BMO_slot_buffer_from_all(
      slot->mesh, &op, op.slots_in, "edges", blender::BM_EDGE);
  blender::BMO_slot_int_set(op.slots_in, "cuts", cuts);
  blender::BMO_slot_bool_set(op.slots_in, "use_grid_fill", true);
  // Default geometry interpolation/quad corner mode follows original Blender.
  slot->top_face = nullptr;
  blender::BMO_op_exec(slot->mesh, &op);
  blender::BMO_op_finish(slot->mesh, &op);
  return slot->mesh->totvert > before_verts ? 0 : -3;
}
#endif

int web_mesh_delete_face(int handle, int index);

int web_mesh_select_element(int handle, int kind, int index, int selected)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (kind < 1 || kind > 3 || (selected != 0 && selected != 1) || index < 0)
    return -2;
  blender::BMIter iter;
  int i = 0;
  if (kind == 1) return web_mesh_select_vertex(handle, index, selected);
  if (kind == 2) {
    blender::BMEdge *edge = nullptr;
    BM_ITER_MESH (edge, &iter, slot->mesh, blender::BM_EDGES_OF_MESH) {
      if (i++ == index) {
        blender::BM_edge_select_set(slot->mesh, edge, selected != 0);
        return 0;
      }
    }
  }
  else {
    blender::BMFace *face = nullptr;
    BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
      if (i++ == index) {
        blender::BM_face_select_set(slot->mesh, face, selected != 0);
        return 0;
      }
    }
  }
  return -2;
}

int web_mesh_selected_element_count(int handle, int kind)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (kind < 1 || kind > 3) return -2;
  blender::BMIter iter;
  int count = 0;
  if (kind == 1) return web_mesh_selected_vert_count(handle);
  if (kind == 2) {
    blender::BMEdge *edge = nullptr;
    BM_ITER_MESH (edge, &iter, slot->mesh, blender::BM_EDGES_OF_MESH) {
      if (BM_elem_flag_test(edge, blender::BM_ELEM_SELECT)) ++count;
    }
  }
  else {
    blender::BMFace *face = nullptr;
    BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
      if (BM_elem_flag_test(face, blender::BM_ELEM_SELECT)) ++count;
    }
  }
  return count;
}

int web_mesh_selected_vert_count(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  blender::BMIter iter;
  blender::BMVert *vert = nullptr;
  int count = 0;
  BM_ITER_MESH (vert, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
    if (BM_elem_flag_test(vert, blender::BM_ELEM_SELECT)) ++count;
  }
  return count;
}

int web_mesh_transform_selected(int handle, int kind, float a, float b, float c)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (kind < 1 || kind > 3 || !std::isfinite(a) || !std::isfinite(b) ||
      !std::isfinite(c)) return -2;
  if (kind == 2 && a <= 0.0f) return -2; // positive uniform scale
  const double cosine = std::cos(double(a)), sine = std::sin(double(a));
  const auto transform = [&](const blender::BMVert *v, double p[3]) {
    const double x = v->co[0], y = v->co[1], z = v->co[2];
    if (kind == 1) {
      p[0] = x + a; p[1] = y + b; p[2] = z + c;
    }
    else if (kind == 2) {
      p[0] = x * a; p[1] = y * a; p[2] = z * a;
    }
    else {
      p[0] = x * cosine - y * sine;
      p[1] = x * sine + y * cosine;
      p[2] = z;
    }
  };
  blender::BMIter iter;
  blender::BMVert *vert = nullptr;
  BM_ITER_MESH (vert, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
    if (!BM_elem_flag_test(vert, blender::BM_ELEM_SELECT)) continue;
    double p[3]{};
    transform(vert, p);
    for (double value : p) {
      if (!std::isfinite(value) ||
          std::abs(value) > double(std::numeric_limits<float>::max())) return -3;
    }
  }
  BM_ITER_MESH (vert, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
    if (!BM_elem_flag_test(vert, blender::BM_ELEM_SELECT)) continue;
    double p[3]{};
    transform(vert, p);
    for (int i = 0; i < 3; ++i) vert->co[i] = float(p[i]);
  }
  return 0;
}

#if defined(BLENDER_WEB_NATIVE_POKE)
int web_mesh_poke_face(int handle, int index)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (index < 0 || index >= slot->mesh->totface) return -2;
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int i = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    if (i++ != index) continue;
    const int old_verts = slot->mesh->totvert;
    const int old_faces = slot->mesh->totface;
    const int old_face_length = face->len;
    blender::BMOperator op;
    blender::BMO_op_init(slot->mesh, &op, blender::BMO_FLAG_DEFAULTS, "poke");
    blender::BMO_slot_buffer_from_single(
        &op, blender::BMO_slot_get(op.slots_in, "faces"), &face->head);
    // Default center_mode 0: original Blender weighted-median poke.
    slot->top_face = nullptr; // Poke deletes the original face.
    blender::BMO_op_exec(slot->mesh, &op);
    blender::BMO_op_finish(slot->mesh, &op);
    return slot->mesh->totvert == old_verts + 1 &&
                   slot->mesh->totface == old_faces + old_face_length - 1 ?
               0 : -3;
  }
  return -3;
}
#endif

#if defined(BLENDER_WEB_NATIVE_INSET)
int web_mesh_inset_face(int handle, int index, float thickness)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (index < 0 || index >= slot->mesh->totface ||
      !std::isfinite(thickness) || thickness <= 0.0f || thickness >= 0.5f)
    return -2;
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int i = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    if (i++ != index) continue;
    if (face->len != 4) return -4;
    // The isolated BMesh primitive constructor does not populate cached face
    // normals; inset uses those normals for edge tangent offsets.
    blender::BM_face_normal_update(face);
    const int old_faces = slot->mesh->totface;
    const int old_verts = slot->mesh->totvert;
    blender::BMOperator op;
    blender::BMO_op_init(slot->mesh, &op, blender::BMO_FLAG_DEFAULTS, "inset_individual");
    blender::BMO_slot_buffer_from_single(
        &op, blender::BMO_slot_get(op.slots_in, "faces"), &face->head);
    blender::BMO_slot_float_set(op.slots_in, "thickness", thickness);
    blender::BMO_slot_float_set(op.slots_in, "depth", 0.0f);
    blender::BMO_slot_bool_set(op.slots_in, "use_even_offset", true);
    slot->top_face = nullptr;
    blender::BMO_op_exec(slot->mesh, &op);
    blender::BMO_op_finish(slot->mesh, &op);
    return slot->mesh->totface == old_faces + 4 &&
                   slot->mesh->totvert == old_verts + 4 ? 0 : -3;
  }
  return -3;
}
#endif

// Delete vertices, edges or faces using the original Blender BMesh kernels.
// Element indices are snapshot-order only and invalid after topology edits.
int web_mesh_delete_element(int handle, int kind, int index)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (kind < 1 || kind > 3 || index < 0) return -2;
  if (kind == 3) return web_mesh_delete_face(handle, index);
  blender::BMIter iter;
  int i = 0;
  if (kind == 1) {
    blender::BMVert *vert = nullptr;
    BM_ITER_MESH (vert, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
      if (i++ == index) {
        slot->top_face = nullptr;
        blender::BM_vert_kill(slot->mesh, vert);
        return 0;
      }
    }
  }
  else {
    blender::BMEdge *edge = nullptr;
    BM_ITER_MESH (edge, &iter, slot->mesh, blender::BM_EDGES_OF_MESH) {
      if (i++ == index) {
        slot->top_face = nullptr;
        blender::BM_edge_kill(slot->mesh, edge);
        return 0;
      }
    }
  }
  return -2;
}

int web_mesh_delete_face(int handle, int index)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (index < 0 || index >= slot->mesh->totface) return -2;
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int i = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    if (i++ == index) {
      // Always clear this convenience pointer before invalidating any face.
      slot->top_face = nullptr;
      blender::BM_face_kill_loose(slot->mesh, face);
      return 0;
    }
  }
  return -3;
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

// Original Blender discrete-face extrusion for any face, including open
// planes and convex n-gon caps. Displacement is along global Z in this bounded
// adapter; a face-local normal transform needs extra orientation state.
int web_mesh_extrude_face_z(int handle, int face_index, float distance)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (face_index < 0 || face_index >= slot->mesh->totface ||
      !std::isfinite(distance)) return -2;
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int i = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    if (i++ != face_index) continue;
    blender::BMOperator op;
    blender::BMO_op_init(slot->mesh, &op, blender::BMO_FLAG_DEFAULTS, "extrude_discrete_faces");
    blender::BMO_slot_buffer_from_single(
        &op, blender::BMO_slot_get(op.slots_in, "faces"), &face->head);
    blender::BMO_op_exec(slot->mesh, &op);
    blender::BMOIter output;
    blender::BMFace *cap = nullptr;
    blender::BMFace *new_top = nullptr;
    unsigned caps = 0;
    BMO_ITER (cap, &output, op.slots_out, "faces.out", blender::BM_FACE) {
      ++caps;
      new_top = cap;
      blender::BMLoop *loop = BM_FACE_FIRST_LOOP(cap);
      blender::BMLoop *first = loop;
      do {
        loop->v->co[2] += distance;
        loop = loop->next;
      } while (loop != first);
    }
    blender::BMO_op_finish(slot->mesh, &op);
    if (caps != 1 || !new_top) {
      slot->top_face = nullptr;
      return -3;
    }
    slot->top_face = new_top;
    return 0;
  }
  return -3;
}

/* Check linked BMesh face loops, edge endpoints and radial adjacency.
 * This validates actual Blender topology after each modeling operation. */
int web_mesh_validate_topology(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) {
    return -1;
  }
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int counted_faces = 0;
  int counted_loops = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    ++counted_faces;
    if (!face->l_first || face->len < 3 || face->len > 128) {
      return -2;
    }
    blender::BMLoop *loop = BM_FACE_FIRST_LOOP(face);
    for (int n = 0; n < face->len; ++n) {
      if (!loop || !loop->next || !loop->prev || !loop->v || !loop->e ||
          loop->f != face || loop->next->prev != loop || loop->prev->next != loop) {
        return -3;
      }
      const blender::BMVert *v1 = loop->v;
      const blender::BMVert *v2 = loop->next->v;
      if (!((loop->e->v1 == v1 && loop->e->v2 == v2) ||
            (loop->e->v1 == v2 && loop->e->v2 == v1))) {
        return -4;
      }
      if (!loop->radial_next || !loop->radial_prev ||
          loop->radial_next->radial_prev != loop ||
          loop->radial_prev->radial_next != loop) {
        return -5;
      }
      // A plane has one radial loop per boundary edge; cube edges have two.
      // Reject non-manifold >2 radial cycles until their behavior is specified.
      if (loop->radial_next == loop) {
        if (loop->radial_prev != loop) {
          return -5;
        }
      }
      else if (loop->radial_next->radial_next != loop ||
               loop->radial_prev != loop->radial_next) {
        return -5;
      }
      ++counted_loops;
      loop = loop->next;
    }
    if (loop != BM_FACE_FIRST_LOOP(face)) {
      return -6;
    }
  }
  return counted_faces == slot->mesh->totface && counted_loops == slot->mesh->totloop ? 0 : -7;
}

/* Phase 1.3.3: COPY current Blender mesh coordinates and triangulated face
 * indices into caller-owned linear memory. Never expose BMVert/BMFace pointers.
 * Current scope is the closed, quad-only primitive/extrude fixture; future
 * general polygon triangulation belongs to the actual Blender mesh pipeline.
 * Return values: >=0 number of values written; -1 invalid handle;
 * -2 null/insufficient output buffer; -3 non-quad face or integer overflow.
 */
int web_mesh_position_float_count(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) {
    return -1;
  }
  if (slot->mesh->totvert > 715827882) {
    return -3;
  }
  return slot->mesh->totvert * 3;
}

int web_mesh_triangle_index_count(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) {
    return -1;
  }
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int64_t triangle_count = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    if (face->len < 3 || face->len > 128) {
      return -3;
    }
    triangle_count += (face->len - 2);
    if (triangle_count > std::numeric_limits<int>::max() / 3) {
      return -3;
    }
  }
  return int(triangle_count * 3);
}

int web_mesh_copy_positions(int handle, float *out, int float_capacity)
{
  const int n = web_mesh_position_float_count(handle);
  if (n < 0) {
    return n;
  }
  if (out == nullptr || float_capacity < n) {
    return -2;
  }
  MeshSlot *slot = get_slot(handle);
  blender::BMIter iter;
  blender::BMVert *vertex = nullptr;
  int i = 0;
  BM_ITER_MESH (vertex, &iter, slot->mesh, blender::BM_VERTS_OF_MESH) {
    out[i++] = vertex->co[0];
    out[i++] = vertex->co[1];
    out[i++] = vertex->co[2];
  }
  return i == n ? i : -3;
}

int web_mesh_copy_triangles(int handle, std::uint32_t *out, int index_capacity)
{
  const int n = web_mesh_triangle_index_count(handle);
  if (n < 0) {
    return n;
  }
  if (out == nullptr || index_capacity < n) {
    return -2;
  }
  MeshSlot *slot = get_slot(handle);
  blender::BM_mesh_elem_index_ensure(slot->mesh, blender::BM_VERT);
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int i = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    // Convex-face fan triangulation for transfer only. True Blender
    // n-gon triangulation and UV-corner triangulation belong to Phase 2.2.4.
    blender::BMLoop *first = BM_FACE_FIRST_LOOP(face);
    blender::BMLoop *loop = first->next;
    const std::uint32_t v0 = std::uint32_t(blender::BM_elem_index_get(first->v));
    for (int corner = 1; corner < face->len - 1; ++corner) {
      out[i++] = v0;
      out[i++] = std::uint32_t(blender::BM_elem_index_get(loop->v));
      out[i++] = std::uint32_t(blender::BM_elem_index_get(loop->next->v));
      loop = loop->next;
    }
  }
  return i == n ? i : -3;
}


#if defined(BLENDER_WEB_NATIVE_UV)
/* Phase 2.2.4 UV experiment. UVs belong to BMLoop (face corners), NOT
 * BMVert: one vertex may have distinct coordinates on a UV seam.
 * Every accessor uses the existing generation-checked opaque mesh handle.
 */
int web_mesh_uv_layer_ensure(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  blender::BMesh *bm = slot->mesh;
  if (blender::CustomData_get_offset(&bm->ldata, CD_PROP_FLOAT2) == -1) {
    blender::BM_data_layer_add(bm, &bm->ldata, CD_PROP_FLOAT2);
  }
  return blender::CustomData_get_offset(&bm->ldata, CD_PROP_FLOAT2) >= 0 ? 0 : -2;
}

int web_mesh_uv_float_count(int handle)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (blender::CustomData_get_offset(&slot->mesh->ldata, CD_PROP_FLOAT2) < 0) return -2;
  if (slot->mesh->totloop > std::numeric_limits<int>::max() / 2) return -3;
  return slot->mesh->totloop * 2;
}

int web_mesh_set_uv(int handle, int face_index, int corner_index, float u, float v)
{
  MeshSlot *slot = get_slot(handle);
  if (!slot) return -1;
  if (!std::isfinite(u) || !std::isfinite(v)) return -4;
  blender::BMesh *bm = slot->mesh;
  if (face_index < 0 || face_index >= bm->totface || corner_index < 0) return -2;
  const int offset = blender::CustomData_get_offset(&bm->ldata, CD_PROP_FLOAT2);
  if (offset < 0) return -3;
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int i = 0;
  BM_ITER_MESH (face, &iter, bm, blender::BM_FACES_OF_MESH) {
    if (i++ != face_index) continue;
    if (corner_index >= face->len) return -2;
    blender::BMLoop *loop = BM_FACE_FIRST_LOOP(face);
    for (int corner = 0; corner < corner_index; ++corner) loop = loop->next;
    float (*uv)[2] = BM_ELEM_CD_GET_FLOAT2_P(loop, offset);
    (*uv)[0] = u;
    (*uv)[1] = v;
    return 0;
  }
  return -2;
}

int web_mesh_copy_uvs(int handle, float *out, int float_capacity)
{
  const int count = web_mesh_uv_float_count(handle);
  if (count < 0) return count;
  if (count == 0) return 0;
  if (!out || float_capacity < count) return -3;
  MeshSlot *slot = get_slot(handle);
  const int offset = blender::CustomData_get_offset(&slot->mesh->ldata, CD_PROP_FLOAT2);
  blender::BMIter iter;
  blender::BMFace *face = nullptr;
  int n = 0;
  BM_ITER_MESH (face, &iter, slot->mesh, blender::BM_FACES_OF_MESH) {
    const blender::BMLoop *loop = BM_FACE_FIRST_LOOP(face);
    for (int corner = 0; corner < face->len; ++corner, loop = loop->next) {
      const float (*uv)[2] = BM_ELEM_CD_GET_FLOAT2_P(loop, offset);
      out[n++] = (*uv)[0];
      out[n++] = (*uv)[1];
    }
  }
  return n == count ? n : -4;
}
#endif  // BLENDER_WEB_NATIVE_UV

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
