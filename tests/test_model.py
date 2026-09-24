# SPDX-License-Identifier: GPL-2.0-or-later

import numpy as np
import pytest

from biodiversity_potential.components import species_area_score
from biodiversity_potential.habitats import Habitat
from biodiversity_potential.model import Weights, run_model


def _grid(*rows):
    return np.array(rows, dtype=np.int16)


def test_weights_sum_to_one_and_reject_nonsense():
    assert Weights().total() == pytest.approx(1.0)
    assert Weights(patch_area=2, habitat_amount=2).normalise().total() == pytest.approx(1.0)
    with pytest.raises(ValueError):
        Weights(patch_area=0, habitat_amount=0, connectivity=0, vegetation=0,
                distinctiveness=0, blue=0, heterogeneity=0, interior=0).normalise()


def test_species_area_saturates_at_the_beninde_reference():
    one_cell = species_area_score(np.array([100.0]), reference_ha=50, exponent=0.25)[0]
    one_hectare = species_area_score(np.array([10000.0]), reference_ha=50, exponent=0.25)[0]
    fifty = species_area_score(np.array([500000.0]), reference_ha=50, exponent=0.25)[0]
    huge = species_area_score(np.array([2_000_000.0]), reference_ha=50, exponent=0.25)[0]
    assert 0 < one_cell < one_hectare < fifty == pytest.approx(1.0)
    assert huge == pytest.approx(1.0)


def test_water_does_not_join_woods_but_allotments_do():
    wood = int(Habitat.WOODLAND)
    water = int(Habitat.OPEN_WATER)
    amenity = int(Habitat.AMENITY_GRASS)
    garden = int(Habitat.GARDEN)
    allotment = int(Habitat.ALLOTMENT)

    split = run_model(_grid([wood, water, wood]), config=_tiny())
    joined = run_model(_grid([wood, wood, wood]), config=_tiny())
    assert split.components["patch_area"][0, 0] < joined.components["patch_area"][0, 0]

    across_lawn = run_model(_grid([wood, amenity, wood]), config=_tiny())
    across_garden = run_model(_grid([wood, garden, wood]), config=_tiny())
    across_allotment = run_model(_grid([wood, allotment, wood]), config=_tiny())
    assert across_lawn.components["patch_area"][0, 0] == pytest.approx(
        split.components["patch_area"][0, 0]
    )
    assert across_garden.components["patch_area"][0, 0] == pytest.approx(
        split.components["patch_area"][0, 0]
    )
    assert across_allotment.components["patch_area"][0, 1] > across_garden.components["patch_area"][0, 1]


def test_open_water_is_not_punished_for_a_low_ndvi():
    water = _grid([int(Habitat.OPEN_WATER)])
    wood = _grid([int(Habitat.WOODLAND)])
    ndvi_water = np.array([[-0.1]])
    ndvi_wood = np.array([[-0.1]])
    config = _tiny()
    water_score = run_model(water, ndvi=ndvi_water, config=config)
    wood_score = run_model(wood, ndvi=ndvi_wood, config=config)
    assert water_score.components["vegetation"][0, 0] == pytest.approx(0.55)
    assert wood_score.components["vegetation"][0, 0] == pytest.approx(0.0)


def test_ndvi_digital_numbers_are_rejected():
    habitat = _grid([int(Habitat.WOODLAND)])
    with pytest.raises(ValueError, match="0-255"):
        run_model(habitat, ndvi=np.array([[180.0]]), config=_tiny())


def test_missing_ndvi_still_ranks_woodland_above_sealed():
    sealed = int(Habitat.SEALED)
    wood = int(Habitat.ANCIENT_WOODLAND)
    grid = np.full((7, 7), sealed, dtype=np.int16)
    grid[2:5, 2:5] = wood
    result = run_model(grid, ndvi=None, config=_tiny(radius=20))
    assert result.weights["vegetation"] == pytest.approx(0.0)
    assert sum(result.weights.values()) == pytest.approx(1.0)
    assert result.index[3, 3] > result.index[0, 0]
    assert 0 <= result.index[0, 0] <= 100
    assert result.index[3, 3] <= 100


def test_same_surface_scores_higher_beside_a_wood():
    sealed = int(Habitat.SEALED)
    garden = int(Habitat.GARDEN)
    wood = int(Habitat.ANCIENT_WOODLAND)
    near = np.full((9, 9), sealed, dtype=np.int16)
    near[4, 1] = garden
    near[3:6, 4:8] = wood
    far = np.full((9, 9), sealed, dtype=np.int16)
    far[4, 4] = garden
    config = _tiny(radius=30)
    near_score = run_model(near, config=config).index[4, 1]
    far_score = run_model(far, config=config).index[4, 4]
    assert near_score > far_score


def test_ancient_interior_beats_its_edge():
    sealed = int(Habitat.SEALED)
    wood = int(Habitat.ANCIENT_WOODLAND)
    grid = np.full((15, 15), sealed, dtype=np.int16)
    grid[2:13, 2:13] = wood
    result = run_model(grid, config=_tiny(radius=20, cell=10))
    assert result.components["interior"][7, 7] > result.components["interior"][2, 7]
    assert result.index[7, 7] > result.index[2, 7]


def test_uniform_sealed_heterogeneity_is_zero_in_the_interior():
    grid = np.full((9, 9), int(Habitat.SEALED), dtype=np.int16)
    result = run_model(grid, config=_tiny(radius=20))
    assert result.components["heterogeneity"][4, 4] == pytest.approx(0.0)


def test_sealed_context_is_gated_and_habitat_is_not():
    from biodiversity_potential.components import connectivity as raw_connectivity
    from biodiversity_potential.components import source_mask
    from biodiversity_potential.model import PERMEABILITY_IMPERVIOUS

    sealed = int(Habitat.SEALED)
    wood = int(Habitat.ANCIENT_WOODLAND)
    grid = np.full((5, 5), sealed, dtype=np.int16)
    grid[2, 4] = wood
    result = run_model(grid, config=_tiny())
    raw = raw_connectivity(source_mask(grid), cell_size_m=10, half_distance_m=250)
    assert result.components["connectivity"][2, 3] == pytest.approx(raw[2, 3] * PERMEABILITY_IMPERVIOUS)
    assert result.components["connectivity"][2, 4] == pytest.approx(1.0)


def test_report_mask_blanks_the_context():
    grid = np.full((5, 5), int(Habitat.AMENITY_GRASS), dtype=np.int16)
    mask = np.zeros((5, 5), dtype=bool)
    mask[2, 2] = True
    result = run_model(grid, report_mask=mask, config=_tiny())
    assert np.isnan(result.index[0, 0])
    assert np.isfinite(result.index[2, 2])


def _tiny(radius=10, cell=10):
    from biodiversity_potential.model import ModelConfig

    return ModelConfig(cell_size_m=cell, neighbourhood_radius_m=radius)
