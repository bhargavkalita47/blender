/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Compile this both natively (x86-64) and for wasm32. The check ensures
 * the two-pointer resource layout remains compact across pointer widths.
 */
#include "BLI_resource_scope.hh"

static_assert(sizeof(blender::ResourceScope) == sizeof(void *) * 2);
