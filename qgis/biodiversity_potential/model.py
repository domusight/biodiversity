# SPDX-License-Identifier: GPL-2.0-or-later
"""Combine the components into a 0–100 biodiversity potential index."""

from dataclasses import dataclass, fields

import numpy as np

from .components import (
    blue_infrastructure,
    connectivity,
    distinctiveness,
    habitat_amount,
    heterogeneity,
    interior,
    patch_area,
    source_mask,
    vegetation,
    water_mask_from_codes,
)

# Beninde, Veith and Hochkirch (2015): patch area and corridors first, then
# vegetation structure, with local habitat ahead of broader landscape context.
# These are a transparent reading of that ranking, not a fitted regression.
DEFAULT_WEIGHTS = {
    "patch_area": 0.22,
    "habitat_amount": 0.18,
    "connectivity": 0.16,
    "vegetation": 0.14,
    "distinctiveness": 0.14,
    "blue": 0.08,
    "heterogeneity": 0.05,
    "interior": 0.03,
}

COMPONENT_ORDER = (
    "distinctiveness",
    "patch_area",
    "habitat_amount",
    "connectivity",
    "vegetation",
    "blue",
    "heterogeneity",
    "interior",
)

# Landscape context is down-weighted on surfaces that species can barely use.
# Impervious land keeps a trace of its surroundings, so a road by a wood still
# reads above a road in an estate, but it cannot outscore a garden.
CONTEXT_COMPONENTS = ("habitat_amount", "connectivity", "blue", "heterogeneity")
PERMEABILITY_IMPERVIOUS = 0.2
PERMEABILITY_MODIFIED = 0.7
FULL_PERMEABILITY_FROM = 0.35


@dataclass(frozen=True)
class Weights:
    """Component weights. ``normalise`` rescales them to sum to 1."""

    patch_area: float = DEFAULT_WEIGHTS["patch_area"]
    habitat_amount: float = DEFAULT_WEIGHTS["habitat_amount"]
    connectivity: float = DEFAULT_WEIGHTS["connectivity"]
    vegetation: float = DEFAULT_WEIGHTS["vegetation"]
    distinctiveness: float = DEFAULT_WEIGHTS["distinctiveness"]
    blue: float = DEFAULT_WEIGHTS["blue"]
    heterogeneity: float = DEFAULT_WEIGHTS["heterogeneity"]
    interior: float = DEFAULT_WEIGHTS["interior"]

    def as_dict(self):
        return {item.name: float(getattr(self, item.name)) for item in fields(self)}

    def total(self):
        return float(sum(self.as_dict().values()))

    def normalise(self):
        values = self.as_dict()
        total = sum(values.values())
        if total <= 0:
            raise ValueError("At least one component weight must be positive.")
        if any(value < 0 for value in values.values()):
            raise ValueError("Component weights cannot be negative.")
        scaled = {name: value / total for name, value in values.items()}
        return Weights(**scaled)


@dataclass(frozen=True)
class ModelConfig:
    """Spatial constants. Defaults are the published reading in ``docs/method.md``."""

    cell_size_m: float = 10.0
    neighbourhood_radius_m: float = 250.0
    patch_reference_ha: float = 50.0
    species_area_z: float = 0.25
    connectivity_half_distance_m: float = 250.0
    blue_half_distance_m: float = 100.0
    interior_saturation_m: float = 30.0
    weights: Weights = None

    def resolved_weights(self):
        weights = DEFAULT_WEIGHT_OBJECT if self.weights is None else self.weights
        return weights.normalise()


DEFAULT_WEIGHT_OBJECT = Weights()


@dataclass
class Result:
    """``index`` is 0–100. Component arrays are 0–1. Nodata is NaN."""

    index: np.ndarray
    components: dict
    weights: dict
    config: ModelConfig


def run_model(
    habitat,
    ndvi=None,
    designation=None,
    report_mask=None,
    config=None,
):
    """Score every cell, then mask the result to the area of interest.

    ``habitat`` must already include the context around the area of interest
    (neighbourhood radius, and ideally the wider patch and source context).
    ``report_mask`` is True on cells that should appear in the output. Other
    cells are set to NaN after they have been used as context.
    """
    config = config or ModelConfig()
    _validate_config(config)
    habitat = np.asarray(habitat)
    if habitat.ndim != 2:
        raise ValueError("Habitat grid must be a 2-D array.")
    weights = config.resolved_weights()
    if ndvi is None:
        dropped = weights.as_dict()
        dropped["vegetation"] = 0.0
        weights = Weights(**dropped).normalise()
    radius_cells = float(config.neighbourhood_radius_m) / float(config.cell_size_m)

    sources = source_mask(habitat, designation)
    water = water_mask_from_codes(habitat)
    vegetation_score = vegetation(habitat, ndvi, water)

    surface = distinctiveness(habitat)
    gate = np.ones(habitat.shape, dtype=float)
    gate[surface < FULL_PERMEABILITY_FROM] = PERMEABILITY_MODIFIED
    gate[surface <= 0] = PERMEABILITY_IMPERVIOUS
    components = {
        "distinctiveness": surface,
        "patch_area": patch_area(
            habitat,
            config.cell_size_m,
            config.patch_reference_ha,
            config.species_area_z,
        ),
        "habitat_amount": habitat_amount(habitat, radius_cells) * gate,
        "connectivity": connectivity(
            sources, config.cell_size_m, config.connectivity_half_distance_m
        )
        * gate,
        "vegetation": vegetation_score,
        "blue": blue_infrastructure(water, config.cell_size_m, config.blue_half_distance_m)
        * gate,
        "heterogeneity": heterogeneity(habitat, radius_cells) * gate,
        "interior": interior(habitat, config.cell_size_m, config.interior_saturation_m),
    }
    index = _composite(components, weights) * 100.0

    if report_mask is not None:
        report_mask = np.asarray(report_mask, dtype=bool)
        if report_mask.shape != habitat.shape:
            raise ValueError("Report mask shape does not match the habitat grid.")
        index = np.where(report_mask, index, np.nan)
        for name, layer in list(components.items()):
            if layer is None:
                continue
            components[name] = np.where(report_mask, layer, np.nan)

    return Result(
        index=index,
        components=components,
        weights=weights.as_dict(),
        config=config,
    )


def _composite(components, weights):
    shape = components["distinctiveness"].shape
    total = np.zeros(shape, dtype=float)
    weight_sum = np.zeros(shape, dtype=float)
    for name in COMPONENT_ORDER:
        layer = components[name]
        weight = float(getattr(weights, name))
        if layer is None or weight == 0:
            continue
        valid = np.ones(shape, dtype=bool) if name != "vegetation" else ~np.isnan(layer)
        values = np.where(valid, layer, 0.0)
        total += values * weight
        weight_sum += np.where(valid, weight, 0.0)
    if np.any(weight_sum <= 0):
        raise ValueError("No component weights left to score a cell.")
    return total / weight_sum


def _validate_config(config):
    if config.cell_size_m <= 0:
        raise ValueError("Cell size must be positive.")
    if config.neighbourhood_radius_m <= 0:
        raise ValueError("Neighbourhood radius must be positive.")
    if config.neighbourhood_radius_m + 1.0e-6 < config.cell_size_m:
        raise ValueError("Neighbourhood radius must be at least one cell.")
