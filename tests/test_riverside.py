# SPDX-License-Identifier: GPL-2.0-or-later
"""The worked example has to keep telling the same ecological story."""

import numpy as np
import pytest

from biodiversity_potential.habitats import Habitat
from riverside import SAMPLES, build, sample_table, score_landscape

EXPECTED_HABITAT = {
    "ancient_interior": Habitat.ANCIENT_WOODLAND,
    "ancient_edge": Habitat.ANCIENT_WOODLAND,
    "reedbed": Habitat.WETLAND,
    "copse": Habitat.WOODLAND,
    "allotment": Habitat.ALLOTMENT,
    "park": Habitat.AMENITY_GRASS,
    "garden_near": Habitat.GARDEN,
    "garden_far": Habitat.GARDEN,
    "playing_field": Habitat.AMENITY_GRASS,
    "pond": Habitat.OPEN_WATER,
    "verge": Habitat.SCATTERED_TREES,
    "sealed_between": Habitat.SEALED,
    "sealed_south": Habitat.SEALED,
}


def test_sample_points_land_in_the_habitats_they_name():
    landscape = build()
    result = score_landscape(landscape)
    rows = {row["name"]: row for row in sample_table(landscape, result)}
    assert set(rows) == {name for name, _x, _y in SAMPLES}
    for name, habitat in EXPECTED_HABITAT.items():
        assert rows[name]["inside_aoi"], name
        assert rows[name]["habitat_code"] == int(habitat), name
        assert rows[name]["potential"] is not None


def test_the_map_ranks_places_in_the_order_the_theory_predicts():
    rows = {row["name"]: row for row in sample_table(build(), score_landscape())}

    def potential(name):
        return rows[name]["potential"]

    assert potential("ancient_interior") > potential("ancient_edge")
    assert potential("ancient_edge") > potential("copse")
    assert potential("copse") > potential("park")
    assert potential("allotment") > potential("playing_field")
    assert potential("playing_field") > potential("sealed_south")
    assert potential("garden_near") > potential("garden_far")
    assert potential("garden_far") > potential("sealed_between")
    assert potential("reedbed") > potential("park")
    assert potential("sealed_between") > potential("sealed_south")
    assert rows["pond"]["components"]["blue"] > rows["park"]["components"]["blue"]
    assert rows["ancient_interior"]["components"]["interior"] > rows["ancient_edge"]["components"]["interior"]
    scored = [potential(name) for name in rows]
    assert min(scored) >= 0
    assert max(scored) <= 100


def test_scores_are_stable():
    """Pinned so a silent change to the index is visible in review."""
    rows = {row["name"]: row["potential"] for row in sample_table(build(), score_landscape())}
    assert rows == {
        "ancient_interior": 87.16,
        "ancient_edge": 83.65,
        "reedbed": 79.68,
        "pond": 59.87,
        "copse": 56.87,
        "allotment": 55.36,
        "park": 24.74,
        "garden_near": 40.25,
        "garden_far": 19.96,
        "playing_field": 16.78,
        "verge": 45.46,
        "sealed_between": 5.63,
        "sealed_south": 2.56,
    }
