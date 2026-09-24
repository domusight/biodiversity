# SPDX-License-Identifier: GPL-2.0-or-later
"""Size limits for the proof-of-concept QGIS tool."""

import math

# The installed tool scores one neighbourhood-scale site. A city is the same
# index, run offline and published as tiles. It is not a second model.
DEMO_RADIUS_M = 500.0
# One metre absorbs the segment vertices of a circular buffer.
DEMO_RADIUS_TOLERANCE_M = 1.0


def farthest_from_point(xs, ys, origin_x, origin_y):
    """Return the greatest distance from ``origin`` to any vertex, in metres."""
    if len(xs) == 0:
        raise ValueError("The area has no vertices.")
    furthest = 0.0
    for x_coord, y_coord in zip(xs, ys):
        distance = math.hypot(x_coord - origin_x, y_coord - origin_y)
        if distance > furthest:
            furthest = distance
    return furthest


def within_demo_radius(xs, ys, origin_x, origin_y, limit_m=DEMO_RADIUS_M):
    """True when every vertex lies within ``limit_m`` of the origin."""
    return farthest_from_point(xs, ys, origin_x, origin_y) <= limit_m + DEMO_RADIUS_TOLERANCE_M
