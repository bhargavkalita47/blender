/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Phase 1.3.2: link and execute genuine BMesh disk-cycle implementation.
 * This is a temporary algorithm-level fixture, not a production mesh/scene API.
 * Topology algorithms are compiled from Blender's unmodified bmesh_structure.cc.
 */

#include "bmesh_class.hh"
#include "intern/bmesh_structure.hh"

// This original Blender function is intentionally private (defined in
// bmesh_structure.cc). Declare it locally only for this source-level test.
namespace blender {
int bmesh_disk_count(const BMVert *v);
}

namespace {

struct SquareWire {
  blender::BMVert verts[4]{};
  blender::BMEdge edges[4]{};

  SquareWire()
  {
    for (int i = 0; i < 4; i++) {
      edges[i].v1 = &verts[i];
      edges[i].v2 = &verts[(i + 1) % 4];
      blender::bmesh_disk_edge_append(&edges[i], edges[i].v1);
      blender::bmesh_disk_edge_append(&edges[i], edges[i].v2);
    }
  }
};

}  // namespace

extern "C" {

/* Returns valence, or -1 for out-of-range vertex. */
int web_bmesh_square_vertex_degree(int vertex)
{
  if (vertex < 0 || vertex >= 4) {
    return -1;
  }
  SquareWire wire;
  return blender::bmesh_disk_count(&wire.verts[vertex]);
}

/* Check whether two vertices really share a Blender disk edge. */
int web_bmesh_square_edge_exists(int vertex_a, int vertex_b)
{
  if (vertex_a < 0 || vertex_a >= 4 || vertex_b < 0 || vertex_b >= 4) {
    return -1;
  }
  SquareWire wire;
  return blender::bmesh_disk_edge_exists(&wire.verts[vertex_a],
                                          &wire.verts[vertex_b]) ? 1 : 0;
}

/* Verifies the disk cycle for all four vertices. */
int web_bmesh_square_validate()
{
  SquareWire wire;
  for (int i = 0; i < 4; ++i) {
    if (!blender::bmesh_disk_validate(2, wire.verts[i].e, &wire.verts[i])) {
      return i + 1;
    }
  }
  return 0;
}

/* Remove one edge from both of its endpoints and return their summed degree. */
int web_bmesh_after_edge_remove()
{
  SquareWire wire;
  blender::bmesh_disk_edge_remove(&wire.edges[0], &wire.verts[0]);
  blender::bmesh_disk_edge_remove(&wire.edges[0], &wire.verts[1]);
  if (blender::bmesh_disk_count(&wire.verts[0]) != 1 ||
      blender::bmesh_disk_count(&wire.verts[1]) != 1 ||
      blender::bmesh_disk_count(&wire.verts[2]) != 2 ||
      blender::bmesh_disk_count(&wire.verts[3]) != 2)
  {
    return -1;
  }
  return blender::bmesh_disk_count(&wire.verts[0]) +
         blender::bmesh_disk_count(&wire.verts[1]) +
         blender::bmesh_disk_count(&wire.verts[2]) +
         blender::bmesh_disk_count(&wire.verts[3]);
}

/* Reconnect the edge from vertex 1 to vertex 2 through Blender's own implementation. */
int web_bmesh_after_vertex_relink()
{
  SquareWire wire;
  blender::bmesh_disk_vert_replace(&wire.edges[0], &wire.verts[2], &wire.verts[1]);
  if (blender::bmesh_disk_count(&wire.verts[0]) != 2 ||
      blender::bmesh_disk_count(&wire.verts[1]) != 1 ||
      blender::bmesh_disk_count(&wire.verts[2]) != 3 ||
      blender::bmesh_disk_count(&wire.verts[3]) != 2)
  {
    return -1;
  }
  if (blender::bmesh_disk_edge_exists(&wire.verts[0], &wire.verts[1]) != nullptr ||
      blender::bmesh_disk_edge_exists(&wire.verts[0], &wire.verts[2]) != &wire.edges[0]) {
    return -2;
  }
  return blender::bmesh_disk_count(&wire.verts[2]);
}

}  // extern "C"
