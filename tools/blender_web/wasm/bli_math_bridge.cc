/* SPDX-FileCopyrightText: 2026 Blender for Web contributors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Phase 1.3.1: small C ABI exposing existing Blender BLI math functions.
 * The math algorithms remain in source/blender/blenlib/intern/math_base.cc.
 * This adapter does NOT implement geometry, BMesh or scene logic.
 */

#include "BLI_math_base_c.hh"

extern "C" {

int web_bli_pow_i(const int base, const int exp)
{
  // Guard invalid negative exponents. Callers must avoid signed int overflow.
  if (exp < 0 || exp > 30) {
    return -1;
  }
  return blender::pow_i(base, exp);
}

double web_bli_double_round(const double value, const int digits)
{
  return blender::double_round(value, digits);
}

float web_bli_floor_power_of_10(const float value)
{
  if (value < 0.0f) {
    return -1.0f;
  }
  return blender::floor_power_of_10(value);
}

float web_bli_ceil_power_of_10(const float value)
{
  if (value < 0.0f) {
    return -1.0f;
  }
  return blender::ceil_power_of_10(value);
}

} // extern "C"
