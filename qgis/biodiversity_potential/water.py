# SPDX-License-Identifier: GPL-2.0-or-later
"""Decide which river centrelines are on the surface.

OS Open Rivers ``fictitious`` means the link is a straight line with no
intermediate vertices. It does not mean the water is underground. Narrow
visible streams belong on OS Open Map Local ``SurfaceWater_Line``, which
only draws water that was surveyed on the surface.
"""

_FICTITIOUS_FIELDS = ("fictitious", "fictitiou")
_LEVEL_FIELDS = (
    "level",
    "physicallevel",
    "physical_level",
    "physicalcontainment",
    "physical_containment",
)
_HIDDEN_WORDS = (
    "underground",
    "culvert",
    "tunnel",
    "subterranean",
    "below ground",
    "belowground",
)


OPEN_RIVERS_NOTE = (
    "OS Open Rivers fictitious means a straight line, not a culvert, so those "
    "links were kept. Leave River centrelines empty when Surface water lines "
    "is set. Open Rivers also draws network links that are not visible water. "
    "Narrow streams are OS Open Map Local SurfaceWater_Line."
)


def is_fictitious_geometry(attributes):
    """True when Open Rivers has marked the link as a straight-line geometry."""
    return any(_is_true(attributes.get(name)) for name in _FICTITIOUS_FIELDS)


def is_hidden_centreline(attributes):
    """True when a centreline is described as underground, culverted, or in a tunnel.

    ``attributes`` maps a lower-case field name to its value. A straight-line
    ``fictitious`` flag is not this test. Only a level or containment field
    that says underground, culvert, or tunnel is excluded.
    """
    for name in _LEVEL_FIELDS:
        if name not in attributes or attributes[name] is None:
            continue
        text = str(attributes[name]).lower().replace("_", " ")
        if any(word in text for word in _HIDDEN_WORDS):
            return True
    return False


def _is_true(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "t", "yes", "y")
