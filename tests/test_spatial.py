# SPDX-License-Identifier: GPL-2.0-or-later

import numpy as np

from biodiversity_potential.spatial import (
    circular_offsets,
    circular_window_sum,
    distance_to_features,
    label_components,
)


def test_distance_matches_brute_force():
    rng = np.random.default_rng(4)
    features = rng.random((9, 12)) > 0.8
    features[3, 5] = True
    got = distance_to_features(features)
    rows, columns = np.where(features)
    expected = np.empty(features.shape, dtype=float)
    for row in range(features.shape[0]):
        for column in range(features.shape[1]):
            expected[row, column] = np.min(
                np.hypot(rows - row, columns - column)
            )
    np.testing.assert_allclose(got, expected, atol=1e-6)


def test_distance_without_features_does_not_crash():
    distance = distance_to_features(np.zeros((4, 4), dtype=bool))
    assert distance.shape == (4, 4)
    assert np.all(distance > 0)


def test_eight_connected_diagonal_is_one_patch():
    mask = np.array(
        [
            [True, False],
            [False, True],
        ]
    )
    labels = label_components(mask)
    assert len(set(labels.ravel()) - {0}) == 1


def test_gap_splits_components_and_u_shape_joins_them():
    split = np.array([[True, False, True]])
    assert len(set(label_components(split).ravel()) - {0}) == 2

    joined = np.array(
        [
            [True, True, True],
            [True, False, True],
            [False, False, True],
        ]
    )
    assert len(set(label_components(joined).ravel()) - {0}) == 1


def test_circular_mean_of_a_constant_interior_is_the_constant():
    values = np.full((11, 11), 3.0)
    total = circular_window_sum(values, radius_cells=2)
    mean = total / len(circular_offsets(2))
    assert mean[5, 5] == 3.0
    assert mean[0, 0] < 3.0


def test_circular_sum_matches_brute_force():
    rng = np.random.default_rng(9)
    values = rng.normal(size=(8, 7))
    radius = 1.5
    offsets = circular_offsets(radius)
    got = circular_window_sum(values, radius)
    expected = np.zeros_like(values)
    height, width = values.shape
    for d_row, d_column in offsets:
        for row in range(height):
            for column in range(width):
                near_row = row + d_row
                near_column = column + d_column
                if 0 <= near_row < height and 0 <= near_column < width:
                    expected[row, column] += values[near_row, near_column]
    np.testing.assert_allclose(got, expected)
