# SPDX-License-Identifier: GPL-2.0-or-later
"""Habitat classes and the distinctiveness scores applied to them.

Distinctiveness follows the band scores of the Statutory Biodiversity Metric
(very low 0, low 2, medium 4, high 6, very high 8), divided by 8 so the
component sits on 0–1. Two urban classes the Metric does not really represent,
private gardens and allotments, are placed between the low and medium bands.
The reasons are set out in ``docs/theory.md``.
"""

from enum import IntEnum


class Habitat(IntEnum):
    """Integer codes stored in the habitat grid.

    ``UNKNOWN`` is unrecorded land, not a finding that the surface is sealed.
    """

    UNKNOWN = 0
    SEALED = 1
    BARE = 2
    CROP = 3
    AMENITY_GRASS = 4
    GARDEN = 5
    ALLOTMENT = 6
    SCATTERED_TREES = 7
    SCRUB = 8
    SEMI_NATURAL_GRASS = 9
    OPEN_WATER = 10
    WOODLAND = 11
    WETLAND = 12
    PRIORITY_HABITAT = 13
    ANCIENT_WOODLAND = 14
    PRIORITY_WATER = 15
    IRREPLACEABLE = 16


# Metric band / 8, except garden (0.35) and allotment (0.45): see theory.md.
DISTINCTIVENESS = {
    Habitat.UNKNOWN: 0.0,
    Habitat.SEALED: 0.0,
    Habitat.BARE: 0.0,
    Habitat.CROP: 0.25,
    Habitat.AMENITY_GRASS: 0.25,
    Habitat.GARDEN: 0.35,
    Habitat.ALLOTMENT: 0.45,
    Habitat.SCATTERED_TREES: 0.50,
    Habitat.SCRUB: 0.50,
    Habitat.SEMI_NATURAL_GRASS: 0.50,
    Habitat.OPEN_WATER: 0.50,
    Habitat.WOODLAND: 0.625,
    Habitat.WETLAND: 0.75,
    Habitat.PRIORITY_HABITAT: 0.75,
    Habitat.ANCIENT_WOODLAND: 1.0,
    Habitat.PRIORITY_WATER: 0.75,
    Habitat.IRREPLACEABLE: 1.0,
}

# Gardens contribute to matrix quality but are not treated as patches: mapped
# garden polygons are an artefact of property boundaries. Allotments are mapped
# as whole sites in OS Open Greenspace, so they are allowed to form patches.
STRUCTURAL_DISTINCTIVENESS_MIN = 0.40

# Included in the heterogeneity count. Gardens count; sealed and amenity do not.
HETEROGENEITY_DISTINCTIVENESS_MIN = 0.35

# Open water is habitat, but it must not glue two terrestrial patches together.
WATER_PATCH_HABITATS = frozenset(
    {
        Habitat.OPEN_WATER,
        Habitat.PRIORITY_WATER,
    }
)

# NDVI is not a useful structure measure on these surfaces, or on the water mask.
WATER_HABITATS = frozenset(
    {
        Habitat.OPEN_WATER,
        Habitat.PRIORITY_WATER,
        Habitat.WETLAND,
    }
)

LABELS = {
    Habitat.UNKNOWN: "Unrecorded",
    Habitat.SEALED: "Sealed surface",
    Habitat.BARE: "Bare ground",
    Habitat.CROP: "Cultivated land",
    Habitat.AMENITY_GRASS: "Amenity grassland",
    Habitat.GARDEN: "Garden",
    Habitat.ALLOTMENT: "Allotment",
    Habitat.SCATTERED_TREES: "Scattered trees",
    Habitat.SCRUB: "Scrub",
    Habitat.SEMI_NATURAL_GRASS: "Semi-natural grassland",
    Habitat.OPEN_WATER: "Open water",
    Habitat.WOODLAND: "Woodland",
    Habitat.WETLAND: "Wetland",
    Habitat.PRIORITY_HABITAT: "Priority habitat",
    Habitat.ANCIENT_WOODLAND: "Ancient woodland",
    Habitat.PRIORITY_WATER: "Priority pond or lake",
    Habitat.IRREPLACEABLE: "Irreplaceable habitat",
}


def label(code):
    """Human-readable name for a habitat code."""
    try:
        return LABELS[Habitat(int(code))]
    except (ValueError, KeyError):
        return "Unrecognised ({})".format(code)
