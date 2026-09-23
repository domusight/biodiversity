# SPDX-License-Identifier: GPL-2.0-or-later

import numpy as np

from biodiversity_potential.crosswalk import (
    combine_habitat_layers,
    map_priority_habitat,
    map_value,
)
from biodiversity_potential.habitats import Habitat


def test_greenspace_functions_are_case_insensitive():
    assert map_value("Public Park Or Garden", "os_greenspace") is Habitat.AMENITY_GRASS
    assert map_value("allotments or community growing spaces", "os_greenspace") is Habitat.ALLOTMENT
    assert map_value("Tennis Court", "os_greenspace") is Habitat.SEALED
    assert map_value("Cemetery", "os_greenspace") is Habitat.SCATTERED_TREES
    assert map_value("not a real function", "os_greenspace") is None


def test_worldcover_urban_reading_of_grassland():
    assert map_value(10, "esa_worldcover") is Habitat.WOODLAND
    assert map_value("30", "esa_worldcover") is Habitat.AMENITY_GRASS
    assert map_value(50, "esa_worldcover") is Habitat.SEALED
    assert map_value(80, "esa_worldcover") is Habitat.OPEN_WATER
    assert map_value(90, "esa_worldcover") is Habitat.WETLAND
    assert map_value(999, "esa_worldcover") is None


def test_keyword_order_keeps_semi_natural_grass_out_of_amenity():
    assert map_value("Semi-natural grassland", "keyword") is Habitat.SEMI_NATURAL_GRASS
    assert map_value("Amenity grassland", "keyword") is Habitat.AMENITY_GRASS
    assert map_value("street trees", "keyword") is Habitat.SCATTERED_TREES
    assert map_value("Building", "keyword") is Habitat.SEALED


def test_priority_habitat_defaults_and_specific_names():
    habitat, specific = map_priority_habitat("Lowland mixed deciduous woodland")
    assert habitat is Habitat.PRIORITY_HABITAT
    assert specific is False

    habitat, specific = map_priority_habitat("Blanket bog")
    assert habitat is Habitat.IRREPLACEABLE
    assert specific is True

    habitat, specific = map_priority_habitat("Reedbeds")
    assert habitat is Habitat.WETLAND

    habitat, specific = map_priority_habitat("Ponds")
    assert habitat is Habitat.PRIORITY_WATER

    assert map_priority_habitat("") == (None, False)
    assert map_value("Ponds", "priority_habitat") is Habitat.PRIORITY_WATER


def test_habitat_code_accepts_names_and_numbers():
    assert map_value(Habitat.ANCIENT_WOODLAND, "habitat_code") is Habitat.ANCIENT_WOODLAND
    assert map_value("ancient woodland", "habitat_code") is Habitat.ANCIENT_WOODLAND


def test_later_layer_overwrites_and_nodata_does_not():
    base = np.array([[int(Habitat.SEALED), int(Habitat.SEALED)]])
    overlay = np.array([[int(Habitat.WOODLAND), -999]])
    combined = combine_habitat_layers([base, overlay])
    assert combined[0, 0] == Habitat.WOODLAND
    assert combined[0, 1] == Habitat.SEALED
