/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 * Phase 2.2.5: a true C caller, independently compiled against public header.
 */
#include "blender_web_api.h"
#include <assert.h>
#include <stddef.h>
#include <math.h>
#if defined(NDEBUG)
#  error "Release-mode ABI smoke assertions must stay enabled"
#endif

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
  assert(caps & BLENDER_WEB_CAP_TRIANGLE_CORNERS);
  assert(caps & BLENDER_WEB_CAP_PLANAR_NGON);
  assert(caps & BLENDER_WEB_CAP_NAMED_UV);
  assert(caps & BLENDER_WEB_CAP_FACE_NORMALS);
  assert(caps & BLENDER_WEB_CAP_BOUNDARY_COLLAPSE);
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
  assert(web_mesh_face_normal_float_count(plane) == 3);
  float plane_normal[3] = {0};
  assert(web_mesh_copy_face_normals(plane, plane_normal, 3) == 3);
  assert(plane_normal[0] == 0.f && plane_normal[1] == 0.f);
  assert(fabsf(plane_normal[2] - 1.f) < 1e-6f);
  assert(web_mesh_copy_face_normals(plane, plane_normal, 2) == -2);
  assert(web_mesh_named_uv_layer_count(plane) == 1);
  assert(web_mesh_uv_layer_ensure_named(plane, "Detail") == 0);
  assert(web_mesh_uv_layer_ensure_named(plane, "Detail") == 0);
  assert(web_mesh_named_uv_layer_count(plane) == 2);
  assert(web_mesh_set_uv_named(plane, "Detail", 0, 0, .5f, .125f) == 0);
  float detail[8] = {0};
  assert(web_mesh_copy_uvs_named(plane, "Detail", detail, 8) == 8);
  assert(detail[0] == .5f && detail[1] == .125f);
  assert(web_mesh_copy_uvs(plane, uv, 8) == 8);
  assert(uv[0] == .25f && uv[1] == .75f);
  assert(web_mesh_uv_layer_ensure_named(plane, "bad name") == -4);
  assert(web_mesh_set_uv_named(plane, "missing", 0, 0, 0.f, 0.f) == -3);


  /* A concave pentagon cannot be triangulated correctly by a naive fan.
   * Blender's BMesh tessellation must preserve its six-unit polygon area.
   */
  const float concave_xy[10] = {0.f, 0.f, 3.f, 0.f, 3.f, 3.f,
                                1.5f, 1.f, 0.f, 3.f};
  const int ngon = web_mesh_create_polygon_xy(concave_xy, 5);
  assert(ngon > 0);
  assert(web_mesh_validate_topology(ngon) == 0);
  assert(web_mesh_position_float_count(ngon) == 15);
  assert(web_mesh_triangle_index_count(ngon) == 9);
  float poly_points[15];
  uint32_t poly_triangles[9], poly_corners[9];
  assert(web_mesh_copy_positions(ngon, poly_points, 15) == 15);
  assert(web_mesh_copy_triangles(ngon, poly_triangles, 9) == 9);
  assert(web_mesh_copy_triangle_corners(ngon, poly_corners, 9) == 9);
  assert(web_mesh_copy_triangle_corners(ngon, poly_corners, 8) == -2);
  float total_area = 0.f;
  for (size_t i = 0; i < 9; i += 3) {
    for (size_t j = 0; j < 3; ++j) {
      assert(poly_triangles[i + j] < 5);
      assert(poly_corners[i + j] < 5);
      /* Loop index maps to the original BMesh face corner, not a UV
       * borrowed from some unrelated face sharing the vertex. */
      const uint32_t vertex_index = poly_triangles[i + j];
      const uint32_t corner_index = poly_corners[i + j];
      assert(poly_points[3 * vertex_index] == concave_xy[2 * corner_index]);
      assert(poly_points[3 * vertex_index + 1] == concave_xy[2 * corner_index + 1]);
    }
    const uint32_t a = poly_triangles[i], b = poly_triangles[i + 1],
                   c = poly_triangles[i + 2];
    const float ax = poly_points[3 * b] - poly_points[3 * a];
    const float ay = poly_points[3 * b + 1] - poly_points[3 * a + 1];
    const float bx = poly_points[3 * c] - poly_points[3 * a];
    const float by = poly_points[3 * c + 1] - poly_points[3 * a + 1];
    total_area += .5f * fabsf(ax * by - ay * bx);
  }
  assert(fabsf(total_area - 6.f) < 1e-4f);
  assert(web_mesh_uv_layer_ensure(ngon) == 0);
  for (int i = 0; i < 5; ++i) {
    assert(web_mesh_set_uv(ngon, 0, i, i / 8.f, i / 16.f) == 0);
  }
  float poly_uv[10];
  assert(web_mesh_copy_uvs(ngon, poly_uv, 10) == 10);
  for (int i = 0; i < 9; ++i) {
    const int c = poly_corners[i];
    assert(poly_uv[2 * c] == c / 8.f);
    assert(poly_uv[2 * c + 1] == c / 16.f);
  }
  const float degenerate[6] = {0.f, 0.f, 1.f, 0.f, 2.f, 0.f};
  const float crossing[8] = {0.f, 0.f, 2.f, 2.f, 0.f, 2.f, 2.f, 0.f};
  const float invalid[6] = {0.f, 0.f, NAN, 0.f, 0.f, 1.f};
  assert(web_mesh_create_polygon_xy(degenerate, 3) == -4);
  assert(web_mesh_create_polygon_xy(crossing, 4) == -4);
  assert(web_mesh_create_polygon_xy(invalid, 3) == -4);
  assert(web_mesh_create_polygon_xy(NULL, 5) == -4);
  assert(web_mesh_create_polygon_xy(concave_xy, 129) == -4);
  assert(web_mesh_dissolve_boundary_vertex(cube, 0) == -4);
  assert(web_mesh_dissolve_boundary_vertex(ngon, -1) == -2);
  assert(web_mesh_dissolve_boundary_vertex(ngon, 3) == 0);
  assert(web_mesh_validate_topology(ngon) == 0);
  assert(web_mesh_position_float_count(ngon) == 12);
  assert(web_mesh_triangle_index_count(ngon) == 6);
  assert(web_mesh_collapse_boundary_edge(cube, 0) == -4);
  int collapsing = web_mesh_create_plane();
  assert(collapsing > 0);
  assert(web_mesh_collapse_boundary_edge(collapsing, -1) == -2);
  assert(web_mesh_collapse_boundary_edge(collapsing, 0) == 0);
  assert(web_mesh_validate_topology(collapsing) == 0);
  assert(web_mesh_position_float_count(collapsing) == 9);
  assert(web_mesh_triangle_index_count(collapsing) == 3);
  assert(web_mesh_destroy(collapsing) == 0);
  assert(web_mesh_live_count() == 3);
  assert(web_mesh_destroy(ngon) == 0);
  assert(web_mesh_destroy(cube) == 0);
  assert(web_mesh_destroy(plane) == 0);
  assert(web_mesh_destroy(plane) < 0); /* stale token rejected */
  assert(web_mesh_position_float_count(plane) < 0);
  assert(web_mesh_live_count() == 0);
  return 0;
}
