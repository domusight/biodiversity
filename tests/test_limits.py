# SPDX-License-Identifier: GPL-2.0-or-later
"""The demo tool accepts a neighbourhood and refuses a city."""

import math

from biodiversity_potential.limits import DEMO_RADIUS_M, farthest_from_point, within_demo_radius


def _circle(radius, segments=64):
    xs = []
    ys = []
    for step in range(segments):
        angle = 2.0 * math.pi * step / segments
        xs.append(radius * math.cos(angle))
        ys.append(radius * math.sin(angle))
    return xs, ys


def test_five_hundred_metres_is_accepted():
    xs, ys = _circle(DEMO_RADIUS_M)
    assert within_demo_radius(xs, ys, 0.0, 0.0)
    assert abs(farthest_from_point(xs, ys, 0.0, 0.0) - DEMO_RADIUS_M) < 1e-6


def test_a_city_scale_polygon_is_refused():
    xs, ys = _circle(20_000.0)
    assert not within_demo_radius(xs, ys, 0.0, 0.0)


def test_two_sites_far_apart_are_refused():
    assert not within_demo_radius([0.0, 5_000.0], [0.0, 0.0], 2_500.0, 0.0)
