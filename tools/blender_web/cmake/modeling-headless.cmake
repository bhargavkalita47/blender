# Blender for Web — reversible headless modeling baseline
# SPDX-FileCopyrightText: 2026 Blender for Web contributors
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Load with: cmake -S . -B build/web-modeling -C tools/blender_web/cmake/modeling-headless.cmake
#
# This is a *native diagnostic build profile*, NOT a standalone extracted core.
# It keeps Blender's original CMake target graph and does not guarantee
# all native GPU/GHOST/render-related library edges are gone.
# All options are real options declared by the pinned Blender 5.4 Alpha
# root CMakeLists.txt. Do not turn off GMP/Manifold/OpenSubdiv/UV by default:
# those support important modeling functionality.
#
# Never set these options in the upstream 'main' branch.

set(WITH_HEADLESS ON CACHE BOOL "Native headless modeling diagnostic" FORCE)
set(WITH_PYTHON ON CACHE BOOL "Keep Python for reference modeling tests" FORCE)

# Offline rendering / advanced render integration
set(WITH_CYCLES OFF CACHE BOOL "No Cycles in web core diagnostic" FORCE)
set(WITH_FREESTYLE OFF CACHE BOOL "No Freestyle rendering" FORCE)
set(WITH_HYDRA OFF CACHE BOOL "No Hydra rendering" FORCE)
set(WITH_OPENIMAGEDENOISE OFF CACHE BOOL "No offline denoise" FORCE)

# Simulations and animation-adjacent external integrations
set(WITH_MOD_FLUID OFF CACHE BOOL "No Mantaflow" FORCE)
set(WITH_MOD_OCEANSIM OFF CACHE BOOL "No ocean simulation" FORCE)
set(WITH_BULLET OFF CACHE BOOL "No Bullet physics" FORCE)
set(WITH_AUDASPACE OFF CACHE BOOL "No audio runtime" FORCE)
set(WITH_XR_OPENXR OFF CACHE BOOL "No XR" FORCE)
set(WITH_LIBMV OFF CACHE BOOL "No motion tracking" FORCE)

# Non-core interchange and media features; these can be reinstated selectively.
set(WITH_ALEMBIC OFF CACHE BOOL "Defer Alembic" FORCE)
set(WITH_USD OFF CACHE BOOL "Defer USD" FORCE)
set(WITH_MATERIALX OFF CACHE BOOL "Defer MaterialX" FORCE)
set(WITH_CODEC_FFMPEG OFF CACHE BOOL "No video codec" FORCE)
set(WITH_CODEC_SNDFILE OFF CACHE BOOL "No audio codec" FORCE)
set(WITH_IMAGE_CINEON OFF CACHE BOOL "No Cineon/DPX images" FORCE)
set(WITH_HARU OFF CACHE BOOL "No PDF export" FORCE)
set(WITH_POTRACE OFF CACHE BOOL "Defer Potrace" FORCE)
set(WITH_QUADRIFLOW OFF CACHE BOOL "Defer QuadriFlow remeshing" FORCE)

# Keep the following until their modeled use cases and link closure are tested:
# WITH_GMP, WITH_MANIFOLD, WITH_OPENSUBDIV, WITH_UV_SLIM,
# WITH_IMAGE_WEBP, WITH_IMAGE_OPENJPEG, and core DNA/RNA/BKE/BMesh.
