# SPDX-License-Identifier: GPL-2.0-or-later
"""City tiles cover the boundary and do not overlap."""

from biodiversity_potential.tiles import core_window, plan_cores


def test_cores_cover_a_city_without_overlap_or_gaps():
    cores = plan_cores(0, 0, 30_000, 20_000, cell=10, context_m=1000)
    assert len(cores) > 1
    covered = 0.0
    for core in cores:
        covered += (core["xmax"] - core["xmin"]) * (core["ymax"] - core["ymin"])
        assert core["xmax"] - core["xmin"] > 0
        assert core["ymax"] - core["ymin"] > 0
    assert covered == 30_000 * 20_000


def test_core_window_is_north_up():
    grid = {"xmin": 0.0, "ymax": 100.0}
    column, row, width, height = core_window(
        grid, {"xmin": 40.0, "ymin": 20.0, "xmax": 70.0, "ymax": 50.0}, 10
    )
    assert (column, row, width, height) == (4, 5, 3, 3)
