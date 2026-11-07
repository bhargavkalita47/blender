# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Phase 2.2 EXPERIMENT: native independently linked subset of genuine Blender
# BMesh, BLI and BKE. Not part of Blender's native app CMake target graph.
# This is a bounded source-level proof, not a production general editor.
cmake_minimum_required(VERSION 3.25)
project(BlenderWebNativeCore VERSION 0.1 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(BLENDER_WEB_SANITIZE "Build extracted Blender BMesh with ASan and UBSan" OFF)
if(BLENDER_WEB_SANITIZE)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR "Sanitizers require GCC or Clang")
  endif()
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer -O1)
  add_link_options(-fsanitize=address,undefined)
endif()

get_filename_component(BLENDER_WEB_SOURCE_ROOT "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
if(NOT EXISTS "${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/bmesh.hh")
  message(FATAL_ERROR "Expected full Blender source checkout at ${BLENDER_WEB_SOURCE_ROOT}")
endif()

# An explicit, auditable manifest derived from the *passing* Phase 1.3 BMesh
# source build. Never glob Blender's entire target tree into this target.
set(BLENDER_WEB_NATIVE_SOURCES
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_structure.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_core.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_construct.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_query.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_mesh.cc
  ${BLENDER_WEB_SOURCE_ROOT}/intern/guardedalloc/intern/mallocn.cc
  ${BLENDER_WEB_SOURCE_ROOT}/intern/guardedalloc/intern/mallocn_lockfree_impl.cc
  ${BLENDER_WEB_SOURCE_ROOT}/intern/guardedalloc/intern/mallocn_guarded_impl.cc
  ${BLENDER_WEB_SOURCE_ROOT}/intern/guardedalloc/intern/memory_usage.cc
  ${BLENDER_WEB_SOURCE_ROOT}/intern/guardedalloc/intern/leak_detector.cc
  ${BLENDER_WEB_SOURCE_ROOT}/intern/clog/clog.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/BLI_mempool.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenkernel/intern/customdata.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_iterators.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_operators.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/math_vector.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/math_rotation_c.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/BLI_memarena.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/task_range.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/index_mask.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/listbase.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenkernel/intern/mesh_normals.cc
  # Used by Blender BMesh kernel winding reversal during boundary collapse.
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenkernel/intern/mesh_evaluate.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenkernel/intern/multires.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenkernel/intern/customdata_file.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_delete.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_marking.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_mesh_normals.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_opdefines.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/operators/bmo_dupe.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/operators/bmo_extrude.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/operators/bmo_poke.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_interp.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/operators/bmo_inset.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_mods.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/operators/bmo_subdivide.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/BLI_assert.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/BLI_ghash.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/string.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/task_iterator.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/math_matrix_c.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh/intern/bmesh_polygon.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/BLI_ghash_utils.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/task_pool.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/task_scheduler.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/math_geom.cc
  # Original Blender BLI concave polygon triangulation used by BM_face_calc_tessellation.
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/polyfill_2d.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/threads.cc
  # Original Blender providers required by expanded BMO inset/subdivide:
  # UTF-8 names, Blender translation (internationalization disabled in
  # this isolated target), BLI RNG/stack, and legacy procedural noise.
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/string_ref.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/string_utf8.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/string_utils.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/rand.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/stack.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib/intern/noise_c.cc
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blentranslation/intern/blt_translation.cc
  ${BLENDER_WEB_SOURCE_ROOT}/tools/blender_web/wasm/bmesh_handle_api.cc
)
set(BLENDER_WEB_NATIVE_INCLUDES
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/bmesh
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenkernel
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenlib
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/makesdna
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/makesrna
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/depsgraph
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/geometry
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/functions
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blentranslation
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenloader
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/blenloader_core
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/imbuf
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/animrig
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/asset_system
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/gpu
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/draw
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/modifiers
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/nodes
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/render
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/windowmanager
  ${BLENDER_WEB_SOURCE_ROOT}/source/blender/editors/include
  ${BLENDER_WEB_SOURCE_ROOT}/intern/guardedalloc
  ${BLENDER_WEB_SOURCE_ROOT}/intern/clog
  ${BLENDER_WEB_SOURCE_ROOT}/intern/atomic
  ${BLENDER_WEB_SOURCE_ROOT}/intern/profile
  ${BLENDER_WEB_SOURCE_ROOT}/intern/guardedalloc/intern
  ${BLENDER_WEB_SOURCE_ROOT}/intern/eigen
  ${BLENDER_WEB_SOURCE_ROOT}/extern/rangetree
  ${BLENDER_WEB_SOURCE_ROOT}/extern/wcwidth
)

# FMT_HEADER_ONLY allows the original BLI dependency to use native fmt headers
# without linking the full Blender external dependency bundle.
find_path(FMT_INCLUDE_DIR fmt/format.h REQUIRED)
find_package(Threads REQUIRED)

add_library(blender_web_native_core SHARED ${BLENDER_WEB_NATIVE_SOURCES})
# Do not export the full native BKE/BLI surface. Restrict the dynamic symbol
# roots to our bounded C ABI bridge so --gc-sections can discard unrelated
# desktop-side functions and their dependencies.
set_target_properties(blender_web_native_core PROPERTIES
  CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN YES)
set_source_files_properties(
  "${BLENDER_WEB_SOURCE_ROOT}/tools/blender_web/wasm/bmesh_handle_api.cc"
  PROPERTIES COMPILE_OPTIONS "-fvisibility=default")
target_include_directories(blender_web_native_core PRIVATE
  ${BLENDER_WEB_NATIVE_INCLUDES} ${FMT_INCLUDE_DIR})
target_compile_definitions(blender_web_native_core PRIVATE
  NDEBUG FMT_HEADER_ONLY BLENDER_WEB_MINIMAL_BMO BLENDER_WEB_NATIVE_POKE BLENDER_WEB_NATIVE_INSET BLENDER_WEB_NATIVE_SUBDIVIDE BLENDER_WEB_NATIVE_UV BLENDER_WEB_NATIVE_CORE_ABI)
# Required by existing Blender bit-7 flag enums in the current source build.
# DNA serialization semantics must be validated before general native parity.
target_compile_options(blender_web_native_core PRIVATE
  -funsigned-char -ffunction-sections -fdata-sections)
target_link_libraries(blender_web_native_core PRIVATE Threads::Threads ${CMAKE_DL_LIBS})
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  target_link_options(blender_web_native_core PRIVATE
    "-Wl,--no-undefined" "-Wl,--gc-sections")
endif()

add_executable(blender_web_native_smoke
  "${CMAKE_CURRENT_LIST_DIR}/native_core_smoke.cc")
target_link_libraries(blender_web_native_smoke PRIVATE blender_web_native_core)
# Release builds otherwise define NDEBUG and silently remove all smoke asserts.
target_compile_options(blender_web_native_smoke PRIVATE -UNDEBUG)

enable_testing()
add_test(NAME blender_web_native_bmesh COMMAND blender_web_native_smoke)
# Phase 2.2.5 independent true C consumer of the C++-linked Blender BMesh
# library, with only the explicitly declared opaque public interface.
add_executable(blender_web_native_contract
  "${CMAKE_CURRENT_LIST_DIR}/native_core_abi_contract.c")
target_include_directories(blender_web_native_contract PRIVATE
  "${CMAKE_CURRENT_LIST_DIR}")
target_link_libraries(blender_web_native_contract PRIVATE blender_web_native_core)
target_compile_options(blender_web_native_contract PRIVATE -UNDEBUG)
add_test(NAME blender_web_native_contract COMMAND blender_web_native_contract)
set_tests_properties(blender_web_native_contract PROPERTIES TIMEOUT 45)

set_tests_properties(blender_web_native_bmesh PROPERTIES TIMEOUT 45)

message(STATUS "Blender Web native-core experimental source count: 56")
message(STATUS "Original Blender source root: ${BLENDER_WEB_SOURCE_ROOT}")
message(STATUS "This standalone CMake project does NOT run the upstream Blender CMake configuration")
