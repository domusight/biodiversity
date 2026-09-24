# SPDX-License-Identifier: GPL-2.0-or-later
"""Overlapping Sentinel tiles keep one value and fill each other's gaps."""

import numpy as np

from biodiversity_potential.mosaic import mosaic_first_valid


def test_overlap_keeps_the_first_value_and_fills_gaps():
    first = np.array([[0.8, np.nan], [0.2, np.nan]])
    second = np.array([[0.1, 0.6], [np.nan, 0.4]])
    merged = mosaic_first_valid([first, second])
    assert merged[0, 0] == 0.8
    assert merged[0, 1] == 0.6
    assert merged[1, 0] == 0.2
    assert merged[1, 1] == 0.4
