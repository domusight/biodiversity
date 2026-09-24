# SPDX-License-Identifier: GPL-2.0-or-later
"""Decide which river centrelines are on the surface."""

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


def is_hidden_centreline(attributes):
    """True when a centreline is underground, culverted, or a network connector.

    ``attributes`` maps a lower-case field name to its value. OS Open Rivers
    marks those links ``fictitious``. A level or containment field that says
    underground, culvert, or tunnel is the same exclusion.
    """
    for name in _FICTITIOUS_FIELDS:
        if name in attributes and _is_true(attributes[name]):
            return True
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
