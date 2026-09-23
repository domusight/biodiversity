# SPDX-License-Identifier: GPL-2.0-or-later
"""Array operations used by the index: distance, patches, circular windows.

The distance transform is the separable algorithm of Felzenszwalb and
Huttenlocher (2012). It is implemented here so the library does not require
SciPy, which a QGIS install does not always have.
"""

import numpy as np


def distance_to_features(features):
    """Euclidean distance, in cells, from every cell to the nearest True cell.

    An image with no True cells returns the diagonal length of the image, which
    is far enough that a connectivity decay of a few hundred metres becomes zero.
    """
    features = np.asarray(features, dtype=bool)
    height, width = features.shape
    if not features.any():
        # Nothing in the context window counts as a source. A short diagonal
        # would pretend a source sat just outside the grid.
        return np.full((height, width), 1.0e6)

    # A finite sentinel keeps the parabola intersection defined on empty columns.
    sentinel = 1.0e12
    squared = np.where(features, 0.0, sentinel)
    along_columns = np.empty_like(squared)
    for column in range(width):
        along_columns[:, column] = _squared_distance_1d(squared[:, column])
    out = np.empty_like(squared)
    for row in range(height):
        out[row, :] = _squared_distance_1d(along_columns[row, :])
    return np.sqrt(out)


def _squared_distance_1d(values):
    """Squared Euclidean distance transform of a 1-D sampled function."""
    count = int(values.shape[0])
    sites = np.zeros(count, dtype=np.int32)
    boundaries = np.empty(count + 1, dtype=float)
    site_count = 0
    sites[0] = 0
    boundaries[0] = -np.inf
    boundaries[1] = np.inf
    for query in range(1, count):
        intersection = _parabola_intersection(values, query, int(sites[site_count]))
        while intersection <= boundaries[site_count]:
            site_count -= 1
            intersection = _parabola_intersection(values, query, int(sites[site_count]))
        site_count += 1
        sites[site_count] = query
        boundaries[site_count] = intersection
        boundaries[site_count + 1] = np.inf

    out = np.empty(count, dtype=float)
    site_count = 0
    for query in range(count):
        while boundaries[site_count + 1] < query:
            site_count += 1
        delta = query - int(sites[site_count])
        out[query] = (delta * delta) + values[int(sites[site_count])]
    return out


def _parabola_intersection(values, query, site):
    return (
        (values[query] + query * query) - (values[site] + site * site)
    ) / (2.0 * query - 2.0 * site)


def label_components(mask):
    """Label 8-connected True cells. Background is 0. Labels start at 1."""
    mask = np.asarray(mask, dtype=bool)
    height, width = mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    parent = [0]

    def find(label):
        while parent[label] != label:
            parent[label] = parent[parent[label]]
            label = parent[label]
        return label

    def union(left, right):
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    next_label = 1
    for row in range(height):
        for column in range(width):
            if not mask[row, column]:
                continue
            neighbours = []
            for d_row, d_column in ((-1, -1), (-1, 0), (-1, 1), (0, -1)):
                near_row = row + d_row
                near_column = column + d_column
                if near_row < 0 or near_column < 0 or near_column >= width:
                    continue
                neighbour = int(labels[near_row, near_column])
                if neighbour:
                    neighbours.append(neighbour)
            if not neighbours:
                parent.append(next_label)
                labels[row, column] = next_label
                next_label += 1
                continue
            root = find(neighbours[0])
            for neighbour in neighbours[1:]:
                union(root, neighbour)
            labels[row, column] = root

    dense = {}
    out = np.zeros_like(labels)
    next_dense = 1
    for row in range(height):
        for column in range(width):
            label = int(labels[row, column])
            if label == 0:
                continue
            root = find(label)
            if root not in dense:
                dense[root] = next_dense
                next_dense += 1
            out[row, column] = dense[root]
    return out


def circular_offsets(radius_cells):
    """Cell offsets whose centre lies inside a circle of the given radius."""
    if radius_cells < 0:
        raise ValueError("Neighbourhood radius cannot be negative.")
    limit = int(np.ceil(radius_cells))
    squared_limit = float(radius_cells) * float(radius_cells) + 1.0e-9
    offsets = []
    for d_row in range(-limit, limit + 1):
        for d_column in range(-limit, limit + 1):
            if (d_row * d_row + d_column * d_column) <= squared_limit:
                offsets.append((d_row, d_column))
    if not offsets:
        offsets.append((0, 0))
    return offsets


def circular_window_sum(values, radius_cells):
    """Sum of ``values`` inside a circle, with zeros beyond the array edge.

    Dividing by ``len(circular_offsets(...))`` is the mean over the full
    window. Cells closer than one radius to the array edge are diluted by that
    zero padding. Callers therefore score only an area of interest inset by the
    neighbourhood radius, and pass a grid that already contains that buffer.
    """
    values = np.asarray(values, dtype=float)
    offsets = circular_offsets(radius_cells)
    pad = int(np.ceil(radius_cells))
    padded = np.pad(values, pad, mode="constant", constant_values=0.0)
    height, width = values.shape
    total = np.zeros((height, width), dtype=float)
    for d_row, d_column in offsets:
        total += padded[
            pad + d_row : pad + d_row + height,
            pad + d_column : pad + d_column + width,
        ]
    return total
