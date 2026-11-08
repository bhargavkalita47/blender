/* SPDX-FileCopyrightText: 2001-2002 NaN Holding BV. All rights reserved.
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/* Pinned Blender 5.4 Alpha helper extracted verbatim from
 * source/blender/blenkernel/intern/curve.cc at 67e5a5f874cf37e2a114cebd24f219d8c44a16ad.
 * This standalone translation unit avoids linking the entire curve implementation
 * into the Blender for Web native modeling core.
 */
#include "BKE_curve.hh"
#include "BLI_utildefines.hh"

namespace blender {

void BKE_curve_forward_diff_bezier(
    float q0, float q1, float q2, float q3, float *p, int it, int stride)
{
  float rt0, rt1, rt2, rt3, f;
  int a;

  f = float(it);
  rt0 = q0;
  rt1 = 3.0f * (q1 - q0) / f;
  f *= f;
  rt2 = 3.0f * (q0 - 2.0f * q1 + q2) / f;
  f *= it;
  rt3 = (q3 - q0 + 3.0f * (q1 - q2)) / f;

  q0 = rt0;
  q1 = rt1 + rt2 + rt3;
  q2 = 2 * rt2 + 6 * rt3;
  q3 = 6 * rt3;

  for (a = 0; a <= it; a++) {
    *p = q0;
    p = static_cast<float *> POINTER_OFFSET(p, stride);
    q0 += q1;
    q1 += q2;
    q2 += q3;
  }
}

}  // namespace blender
