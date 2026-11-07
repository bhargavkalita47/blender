/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * EXPERIMENTAL Phase 2.2.5 C interface. Revision 1 is NOT a promise of ABI
 * stability across releases. Function symbols, opaque handles and copied
 * buffers deliberately do not expose Blender internal object layouts.
 */
#ifndef BLENDER_WEB_EXPERIMENTAL_API_H
#define BLENDER_WEB_EXPERIMENTAL_API_H
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
  BLENDER_WEB_CAP_MESH_CORE = 1u << 0,
  BLENDER_WEB_CAP_COMPONENT_SELECTION = 1u << 1,
  BLENDER_WEB_CAP_INSET = 1u << 2,
  BLENDER_WEB_CAP_SUBDIVIDE = 1u << 3,
  BLENDER_WEB_CAP_LOOP_UV = 1u << 4,
  BLENDER_WEB_CAP_TRIANGLE_CORNERS = 1u << 5,
  BLENDER_WEB_CAP_PLANAR_NGON = 1u << 6,
  BLENDER_WEB_CAP_NAMED_UV = 1u << 7,
  BLENDER_WEB_CAP_FACE_NORMALS = 1u << 8,
  BLENDER_WEB_CAP_BOUNDARY_COLLAPSE = 1u << 9
};

/* ABI discovery (experimental). A caller MUST test capability bits before
 * invoking feature-specific operations. All calls are currently single-thread
 * only; no C++ exceptions are allowed across this boundary.
 */
int web_mesh_api_revision(void);
uint32_t web_mesh_api_capabilities(void);
int web_mesh_api_max_live_meshes(void);

/* Creation returns a positive generation-tagged opaque integer handle.
 * A negative value is an error, never a pointer. The current table is
 * process-global; max live instances is intentionally small.
 */
int web_mesh_create_cube(void);
int web_mesh_create_plane(void);
int web_mesh_create_grid(int x_segments, int y_segments);
int web_mesh_create_cylinder(int segments);
int web_mesh_create_uv_sphere(int segments, int rings);
/* Optional: BLENDER_WEB_CAP_PLANAR_NGON. XY coordinates must describe a
 * simple, non-self-intersecting polygon; each point is x,y in packed order.
 * Valid length: 3..128, finite coordinates with absolute value <= 1e6.
 * Errors: -4 invalid input, -3 mesh table full, -2 BMesh allocation failure.
 */
int web_mesh_create_polygon_xy(const float *xy, int vertex_count);
int web_mesh_destroy(int handle);
int web_mesh_live_count(void);
int web_mesh_memory_bytes(void);

/* Snapshot export copies into caller-owned memory, and never lends Blender
 * pointers. Call count first; any change to topology invalidates old counts.
 * Return is written float/index count or a negative failure code.
 */
int web_mesh_position_float_count(int handle);
int web_mesh_triangle_index_count(int handle);
int web_mesh_copy_positions(int handle, float *out, int float_capacity);
int web_mesh_copy_triangles(int handle, uint32_t *out, int index_capacity);
/* Optional: BLENDER_WEB_CAP_TRIANGLE_CORNERS. One corner index per triangle
 * vertex, in exactly the same triangle order as copy_triangles. This index
 * addresses the face-major BMLoop array returned by copy_uvs, as pairs of
 * floats; it is NOT a vertex index. Counts match triangle_index_count.
 * The implementation uses original Blender BMesh tessellation, including
 * for concave n-gons. Caller owns all output buffers; topology mutations
 * invalidate prior snapshots and capacities.
 */
int web_mesh_copy_triangle_corners(int handle, uint32_t *out, int index_capacity);
/* Optional: BLENDER_WEB_CAP_FACE_NORMALS. Returns xyz per BMesh face in
 * face enumeration order (one normal per face; NOT smooth loop normals).
 * Normals are recomputed from original Blender BMesh geometry on export.
 */
int web_mesh_face_normal_float_count(int handle);
int web_mesh_copy_face_normals(int handle, float *out, int float_capacity);
int web_mesh_validate_topology(int handle);
int web_mesh_translate(int handle, float dx, float dy, float dz);
/* Optional: BLENDER_WEB_CAP_BOUNDARY_COLLAPSE. Source-backed BMesh
 * BM_vert_dissolve/BM_edge_collapse restricted to a single simple polygon
 * with one boundary loop. Enumeration indices are invalidated after edits;
 * -4 means unsupported topology, -2 invalid index, -1 invalid mesh token.
 * This is not a general Blender dissolve/merge tool.
 */
int web_mesh_dissolve_boundary_vertex(int handle, int vertex_index);
int web_mesh_collapse_boundary_edge(int handle, int edge_index);

/* Optional: BLENDER_WEB_CAP_LOOP_UV. Copy is ordered by BMesh face traversal
 * then winding-order corners, not by vertex and not by arbitrary triangles.
 * Consumers pair this with web_mesh_copy_triangle_corners, never with
 * vertex indices directly: shared 3D vertices may have different UV seams.
 */
int web_mesh_uv_layer_ensure(int handle);
int web_mesh_uv_float_count(int handle);
int web_mesh_set_uv(int handle, int face_index, int corner_index, float u, float v);
int web_mesh_copy_uvs(int handle, float *out, int float_capacity);
/* Optional: BLENDER_WEB_CAP_NAMED_UV. Up to 8 independent UV layers.
 * Names must be ASCII alphanumeric, underscore or hyphen, length 1..63;
 * no pointers or storage references are retained by the engine.
 * Return values are function-specific; invalid name: -4; no named layer
 * when writing/copying: -3; exhausted layer quota: -5.
 */
int web_mesh_named_uv_layer_count(int handle);
int web_mesh_uv_layer_ensure_named(int handle, const char *name);
int web_mesh_set_uv_named(int handle, const char *name, int face_index,
                          int corner_index, float u, float v);
int web_mesh_copy_uvs_named(int handle, const char *name, float *out,
                            int float_capacity);

#ifdef __cplusplus
}
#endif
#endif /* BLENDER_WEB_EXPERIMENTAL_API_H */
