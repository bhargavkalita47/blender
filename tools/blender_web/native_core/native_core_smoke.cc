// SPDX-FileCopyrightText: 2026 Blender for Web contributors
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Independent NATIVE executable links only to the Phase 2.2 modeling library.
// It deliberately does not include Blender's process, window manager, or UI.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

extern "C" {
int web_mesh_create_cube();
int web_mesh_destroy(int);
int web_mesh_verts(int);
int web_mesh_edges(int);
int web_mesh_faces(int);
int web_mesh_loops(int);
float web_mesh_top_z(int);
int web_mesh_extrude_top(int, float);
int web_mesh_validate_topology(int);
int web_mesh_live_count();
int web_mesh_memory_bytes();
int web_mesh_position_float_count(int);
int web_mesh_triangle_index_count(int);
int web_mesh_copy_positions(int, float *, int);
int web_mesh_copy_triangles(int, std::uint32_t *, int);
}

static void check(bool pass, const char *message)
{
  if (!pass) {
    throw std::runtime_error(message);
  }
}

static void verify_mesh(int h, int vertices, int edges, int faces, int loops, float z)
{
  check(web_mesh_validate_topology(h) == 0, "Blender BMesh topology invalid");
  check(web_mesh_verts(h) == vertices, "vertex count mismatch");
  check(web_mesh_edges(h) == edges, "edge count mismatch");
  check(web_mesh_faces(h) == faces, "face count mismatch");
  check(web_mesh_loops(h) == loops, "loop count mismatch");
  check(web_mesh_top_z(h) == z, "top-face height mismatch");

  const int positions_count = web_mesh_position_float_count(h);
  const int index_count = web_mesh_triangle_index_count(h);
  check(positions_count == vertices * 3, "position buffer size mismatch");
  check(index_count == faces * 6, "triangle index size mismatch");
  std::vector<float> positions(positions_count);
  std::vector<std::uint32_t> indices(index_count);
  check(web_mesh_copy_positions(h, positions.data(), int(positions.size())) == positions_count,
        "position copy failed");
  check(web_mesh_copy_triangles(h, indices.data(), int(indices.size())) == index_count,
        "triangle copy failed");
  check(web_mesh_copy_positions(h, nullptr, positions_count) == -2,
        "null position buffer was not rejected");
  check(web_mesh_copy_triangles(h, nullptr, index_count) == -2,
        "null index buffer was not rejected");
  check(std::all_of(indices.begin(), indices.end(), [&](std::uint32_t i) {
          return i < std::uint32_t(vertices);
        }),
        "triangle index out of range");
  check(std::all_of(positions.begin(), positions.end(), [](float x) {
          return std::isfinite(x);
        }),
        "non-finite position detected");
}

static void cycle()
{
  int h = web_mesh_create_cube();
  check(h > 0, "create cube failed");
  verify_mesh(h, 8, 12, 6, 24, 1.0f);
  check(web_mesh_extrude_top(h, 1.0f) == 0, "first original Blender extrusion failed");
  verify_mesh(h, 12, 20, 10, 40, 2.0f);
  check(web_mesh_extrude_top(h, 0.5f) == 0, "second original Blender extrusion failed");
  verify_mesh(h, 16, 28, 14, 56, 2.5f);
  check(web_mesh_destroy(h) == 0, "destroy failed");
  check(web_mesh_destroy(h) == -1, "double free was not rejected");
  check(web_mesh_validate_topology(h) == -1, "stale handle accepted");
}

int main()
{
  try {
    check(web_mesh_live_count() == 0, "startup live mesh count nonzero");
    // Warm up the original Blender memory manager before recording baseline.
    for (int i = 0; i < 32; ++i) {
      cycle();
    }
    const int baseline = web_mesh_memory_bytes();
    for (int i = 0; i < 1000; ++i) {
      cycle();
      if ((i + 1) % 100 == 0) {
        check(web_mesh_memory_bytes() == baseline, "GuardedAlloc reported net leaked bytes");
      }
    }
    check(web_mesh_live_count() == 0, "mesh handle left live after stress");
    check(web_mesh_memory_bytes() == baseline, "Blender native memory not at baseline");
    std::cout << "{\"status\":\"pass\",\"phase\":\"2.2\",\"engine\":\"original Blender BMesh\","
              << "\"cycles\":1000,\"original_BMO_extrusions\":2000,"
              << "\"final_live_meshes\":0,\"memory_before\":" << baseline
              << ",\"memory_after\":" << web_mesh_memory_bytes() << "}\n";
    return 0;
  }
  catch (const std::exception &error) {
    std::cerr << "NATIVE_CORE_FAILURE: " << error.what() << "\n";
    return 1;
  }
}
