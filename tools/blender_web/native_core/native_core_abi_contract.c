/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 * Phase 2.2.5: a true C caller, independently compiled against public header.
 */
#include "blender_web_api.h"
#include <assert.h>
#include <stddef.h>

int main(void)
{
  assert(web_mesh_api_revision() == 1);
  assert(web_mesh_api_max_live_meshes() == 16);
  const uint32_t caps = web_mesh_api_capabilities();
  assert(caps & BLENDER_WEB_CAP_MESH_CORE);
  assert(caps & BLENDER_WEB_CAP_COMPONENT_SELECTION);
  assert(caps & BLENDER_WEB_CAP_INSET);
  assert(caps & BLENDER_WEB_CAP_SUBDIVIDE);
  assert(caps & BLENDER_WEB_CAP_LOOP_UV);
  assert(web_mesh_live_count() == 0);

  const int plane = web_mesh_create_plane();
  const int cube = web_mesh_create_cube();
  assert(plane > 0 && cube > 0 && plane != cube);
  assert(web_mesh_validate_topology(plane) == 0);
  assert(web_mesh_validate_topology(cube) == 0);

  assert(web_mesh_position_float_count(plane) == 12);
  assert(web_mesh_triangle_index_count(plane) == 6);
  float points[12] = {0};
  uint32_t indices[6] = {0};
  assert(web_mesh_copy_positions(plane, points, 12) == 12);
  assert(web_mesh_copy_triangles(plane, indices, 6) == 6);
  assert(web_mesh_copy_positions(plane, points, 11) < 0);
  for (size_t i = 0; i < 6; ++i) {
    assert(indices[i] < 4);
  }

  assert(web_mesh_uv_layer_ensure(plane) == 0);
  assert(web_mesh_uv_float_count(plane) == 8);
  assert(web_mesh_set_uv(plane, 0, 0, 0.25f, 0.75f) == 0);
  float uv[8] = {0};
  assert(web_mesh_copy_uvs(plane, uv, 8) == 8);
  assert(uv[0] == .25f && uv[1] == .75f);

  assert(web_mesh_live_count() == 2);
  assert(web_mesh_destroy(cube) == 0);
  assert(web_mesh_destroy(plane) == 0);
  assert(web_mesh_destroy(plane) < 0); /* stale token rejected */
  assert(web_mesh_position_float_count(plane) < 0);
  assert(web_mesh_live_count() == 0);
  return 0;
}
