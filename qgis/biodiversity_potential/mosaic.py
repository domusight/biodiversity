# SPDX-License-Identifier: GPL-2.0-or-later
"""Combine overlapping rasters. The first finite value is kept."""

import numpy as np


def mosaic_first_valid(arrays):
    """Stack arrays that share a shape.

    Sentinel tiles overlap on purpose. Where two tiles both have a value, the
    first is kept. A later tile fills only the cells the earlier tiles left empty.
    """
    combined = None
    for array in arrays:
        data = np.asarray(array, dtype=float)
        if combined is None:
            combined = np.array(data, copy=True)
            continue
        if data.shape != combined.shape:
            raise ValueError("Overlapping rasters must share a shape.")
        missing = ~np.isfinite(combined)
        combined[missing] = data[missing]
    if combined is None:
        raise ValueError("At least one raster is required.")
    return combined
