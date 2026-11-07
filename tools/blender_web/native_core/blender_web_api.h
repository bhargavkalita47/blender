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
  BLENDER_WEB_CAP_LOOP_UV = 1u << 4
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
int web_mesh_validate_topology(int handle);
int web_mesh_translate(int handle, float dx, float dy, float dz);

/* Optional: BLENDER_WEB_CAP_LOOP_UV. Copy is ordered by BMesh face traversal
 * then winding-order corners, not by vertex and not by arbitrary triangles.
 * UI consumers must NOT pair this with triangulated vertex indices without
 * a future explicit triangle-corner remapping API.
 */
int web_mesh_uv_layer_ensure(int handle);
int web_mesh_uv_float_count(int handle);
int web_mesh_set_uv(int handle, int face_index, int corner_index, float u, float v);
int web_mesh_copy_uvs(int handle, float *out, int float_capacity);

#ifdef __cplusplus
}
#endif
#endif /* BLENDER_WEB_EXPERIMENTAL_API_H */
