# SPDX-License-Identifier: GPL-2.0-or-later
"""The eight components of the biodiversity potential index.

Each function returns a float array on 0–1 (vegetation may also contain NaN
where the satellite value was missing). The equations are written out in
``docs/method.md``.
"""

import numpy as np

from .habitats import (
    DISTINCTIVENESS,
    HETEROGENEITY_DISTINCTIVENESS_MIN,
    STRUCTURAL_DISTINCTIVENESS_MIN,
    WATER_HABITATS,
    WATER_PATCH_HABITATS,
    Habitat,
)
from .spatial import (
    circular_offsets,
    circular_window_sum,
    distance_to_features,
    label_components,
)

# Undifferentiated canopy is not treated as saturated vegetation structure.
NDVI_LOW = 0.2
NDVI_HIGH = 0.8
WATER_VEGETATION_SCORE = 0.55

_DISTINCTIVENESS_TABLE = np.zeros(max(int(habitat) for habitat in Habitat) + 1, dtype=float)
for _habitat, _score in DISTINCTIVENESS.items():
    _DISTINCTIVENESS_TABLE[int(_habitat)] = _score

_FUNCTIONAL_IDS = tuple(
    int(habitat)
    for habitat, score in DISTINCTIVENESS.items()
    if score >= HETEROGENEITY_DISTINCTIVENESS_MIN and habitat != Habitat.UNKNOWN
)


def distinctiveness(codes):
    """Look up the distinctiveness of each habitat code."""
    codes = np.asarray(codes)
    _validate_codes(codes)
    return _DISTINCTIVENESS_TABLE[codes]


def species_area_score(area_m2, reference_ha, exponent):
    """Saturating species–area transform. ``reference_ha`` scores 1."""
    if reference_ha <= 0 or exponent <= 0:
        raise ValueError("Species-area reference area and exponent must be positive.")
    area_m2 = np.asarray(area_m2, dtype=float)
    score = np.zeros(area_m2.shape, dtype=float)
    positive = area_m2 > 0
    area_ha = area_m2[positive] / 10000.0
    score[positive] = np.minimum(1.0, (area_ha / float(reference_ha)) ** float(exponent))
    return score


def patch_area(codes, cell_size_m, reference_ha, exponent):
    """Species–area score of the patch a cell belongs to.

    Terrestrial structural habitat and open water are labelled separately, so a
    river does not join the woods on either bank into one patch.
    """
    codes = np.asarray(codes)
    score_lookup = distinctiveness(codes)
    structural = score_lookup >= STRUCTURAL_DISTINCTIVENESS_MIN
    water = np.isin(codes, [int(habitat) for habitat in WATER_PATCH_HABITATS])
    terrestrial = structural & ~water
    score = np.zeros(codes.shape, dtype=float)
    cell_area = float(cell_size_m) * float(cell_size_m)
    for mask in (terrestrial, water):
        labels = label_components(mask)
        if int(labels.max()) == 0:
            continue
        counts = np.bincount(labels.ravel())
        areas = counts.astype(float) * cell_area
        cell_areas = areas[labels]
        cell_areas[labels == 0] = 0.0
        score += species_area_score(cell_areas, reference_ha, exponent)
    return score


def habitat_amount(codes, radius_cells):
    """Mean distinctiveness inside the circular neighbourhood (Fahrig)."""
    return circular_window_sum(distinctiveness(codes), radius_cells) / _window_count(radius_cells)


def connectivity(source_mask, cell_size_m, half_distance_m):
    """Incidence-style decay with distance to the nearest source cell."""
    if half_distance_m <= 0:
        raise ValueError("Connectivity half-distance must be positive.")
    distance_m = distance_to_features(source_mask) * float(cell_size_m)
    return _decay(distance_m, half_distance_m)


def source_mask(codes, designation=None):
    """Structural habitat, plus any extra designation the caller supplies."""
    structural = distinctiveness(codes) >= STRUCTURAL_DISTINCTIVENESS_MIN
    if designation is None:
        return structural
    designation = np.asarray(designation, dtype=bool)
    if designation.shape != structural.shape:
        raise ValueError("Designation mask shape does not match the habitat grid.")
    return structural | designation


def vegetation(codes, ndvi, water_mask):
    """Scale NDVI to 0–1. Water and wetland keep a fixed structure score."""
    if ndvi is None:
        return None
    ndvi = np.asarray(ndvi, dtype=float)
    if ndvi.shape != np.asarray(codes).shape:
        raise ValueError("NDVI shape does not match the habitat grid.")
    _validate_ndvi(ndvi)
    score = (ndvi - NDVI_LOW) / (NDVI_HIGH - NDVI_LOW)
    score = np.clip(score, 0.0, 1.0)
    score = np.where(np.isnan(ndvi), np.nan, score)
    if water_mask is not None:
        score = np.where(np.asarray(water_mask, dtype=bool), WATER_VEGETATION_SCORE, score)
    return score


def water_mask_from_codes(codes, extra=None):
    """Open water, priority water, and wetland, plus an optional extra mask."""
    mask = np.isin(np.asarray(codes), [int(habitat) for habitat in WATER_HABITATS])
    if extra is not None:
        extra = np.asarray(extra, dtype=bool)
        if extra.shape != mask.shape:
            raise ValueError("Water mask shape does not match the habitat grid.")
        mask = mask | extra
    return mask


def blue_infrastructure(water_mask, cell_size_m, half_distance_m):
    """Decay with distance to the nearest water or wetland cell."""
    if half_distance_m <= 0:
        raise ValueError("Blue-infrastructure half-distance must be positive.")
    distance_m = distance_to_features(water_mask) * float(cell_size_m)
    return _decay(distance_m, half_distance_m)


def heterogeneity(codes, radius_cells):
    """Shannon evenness of functional classes, plus one 'other' class.

    Evenness is divided by ln(S), where S is fixed for the classification, so
    windows can be compared. Sealed and amenity surfaces sit in 'other'.
    """
    codes = np.asarray(codes)
    _validate_codes(codes)
    window = _window_count(radius_cells)
    class_count = len(_FUNCTIONAL_IDS) + 1
    entropy = np.zeros(codes.shape, dtype=float)
    functional_total = np.zeros(codes.shape, dtype=float)
    shares = []
    for habitat_id in _FUNCTIONAL_IDS:
        count = circular_window_sum(codes == habitat_id, radius_cells)
        functional_total += count
        shares.append(count)
    shares.append(window - functional_total)
    for count in shares:
        proportion = count / window
        present = proportion > 0
        entropy[present] -= proportion[present] * np.log(proportion[present])
    return entropy / np.log(class_count)


def interior(codes, cell_size_m, saturation_m):
    """Depth within a patch, saturating at ``saturation_m`` metres."""
    if saturation_m <= 0:
        raise ValueError("Interior saturation distance must be positive.")
    codes = np.asarray(codes)
    structural = distinctiveness(codes) >= STRUCTURAL_DISTINCTIVENESS_MIN
    water = np.isin(codes, [int(habitat) for habitat in WATER_PATCH_HABITATS])
    score = np.zeros(codes.shape, dtype=float)
    for mask in (structural & ~water, water):
        if not mask.any():
            continue
        depth_m = distance_to_features(~mask) * float(cell_size_m)
        depth_score = np.clip(depth_m / float(saturation_m), 0.0, 1.0)
        score = np.maximum(score, np.where(mask, depth_score, 0.0))
    return score


def _decay(distance_m, half_distance_m):
    return np.exp(-np.asarray(distance_m, dtype=float) * np.log(2.0) / float(half_distance_m))


def _window_count(radius_cells):
    return float(len(circular_offsets(radius_cells)))


def _validate_codes(codes):
    allowed_max = _DISTINCTIVENESS_TABLE.shape[0] - 1
    if codes.size and (int(codes.min()) < 0 or int(codes.max()) > allowed_max):
        raise ValueError("Habitat grid contains a code that is not in the classification.")


def _validate_ndvi(ndvi):
    finite = ndvi[np.isfinite(ndvi)]
    if finite.size == 0:
        raise ValueError("NDVI raster has no finite values.")
    low = float(finite.min())
    high = float(finite.max())
    if low < -1.5 or high > 1.5:
        raise ValueError(
            "NDVI values run from {:.1f} to {:.1f}. This tool expects a "
            "floating-point index (NIR - Red) / (NIR + Red), roughly between "
            "-1 and 1. A 0-255 image still needs that calculation.".format(low, high)
        )
