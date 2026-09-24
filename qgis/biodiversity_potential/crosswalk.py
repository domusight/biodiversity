# SPDX-License-Identifier: GPL-2.0-or-later
"""Translate open-data class labels into :class:`Habitat` codes.

Unrecognised greenspace functions and keyword labels return ``None`` so the
caller can leave the underlying class in place and report the gap. Priority
Habitat Inventory polygons are already a biodiversity designation: an
unrecognised name still becomes priority habitat, and the caller can warn that
the name was not in the specific list.
"""

import numpy as np

from .habitats import Habitat


def normalise_label(value):
    """Case-fold a class label and treat hyphens and underscores as spaces."""
    text = str(value).strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(text.split())


# OS Open Greenspace FunctionValue code list. Matching is case-insensitive.
# https://docs.os.uk/os-downloads/products/land-and-terrain-portfolio/os-open-greenspace
OS_GREENSPACE_FUNCTION = {
    "allotments or community growing spaces": Habitat.ALLOTMENT,
    "bowling green": Habitat.AMENITY_GRASS,
    "cemetery": Habitat.SCATTERED_TREES,
    "golf course": Habitat.AMENITY_GRASS,
    "other sports facility": Habitat.AMENITY_GRASS,
    "play space": Habitat.AMENITY_GRASS,
    "playing field": Habitat.AMENITY_GRASS,
    "public park or garden": Habitat.AMENITY_GRASS,
    "religious grounds": Habitat.SCATTERED_TREES,
    "tennis court": Habitat.SEALED,
}

# First match wins. Hyphens have already been turned into spaces.
KEYWORD_RULES = (
    ("ancient woodland", Habitat.ANCIENT_WOODLAND),
    ("blanket bog", Habitat.IRREPLACEABLE),
    ("limestone pavement", Habitat.IRREPLACEABLE),
    ("wood pasture", Habitat.PRIORITY_HABITAT),
    ("parkland", Habitat.PRIORITY_HABITAT),
    ("allotment", Habitat.ALLOTMENT),
    ("reedbed", Habitat.WETLAND),
    ("reed bed", Habitat.WETLAND),
    ("wetland", Habitat.WETLAND),
    ("saltmarsh", Habitat.WETLAND),
    ("salt marsh", Habitat.WETLAND),
    ("mudflat", Habitat.WETLAND),
    ("marsh", Habitat.WETLAND),
    ("fen", Habitat.WETLAND),
    ("bog", Habitat.IRREPLACEABLE),
    ("pond", Habitat.OPEN_WATER),
    ("lake", Habitat.OPEN_WATER),
    ("canal", Habitat.OPEN_WATER),
    ("river", Habitat.OPEN_WATER),
    ("water", Habitat.OPEN_WATER),
    ("broadleaf", Habitat.WOODLAND),
    ("broadleaved", Habitat.WOODLAND),
    ("conifer", Habitat.WOODLAND),
    ("woodland", Habitat.WOODLAND),
    ("forest", Habitat.WOODLAND),
    ("scrub", Habitat.SCRUB),
    ("shrub", Habitat.SCRUB),
    ("street tree", Habitat.SCATTERED_TREES),
    ("scattered tree", Habitat.SCATTERED_TREES),
    ("trees", Habitat.SCATTERED_TREES),
    ("tree", Habitat.SCATTERED_TREES),
    ("semi natural", Habitat.SEMI_NATURAL_GRASS),
    ("meadow", Habitat.SEMI_NATURAL_GRASS),
    ("heath", Habitat.PRIORITY_HABITAT),
    ("public park", Habitat.AMENITY_GRASS),
    ("playing field", Habitat.AMENITY_GRASS),
    ("amenity", Habitat.AMENITY_GRASS),
    ("golf", Habitat.AMENITY_GRASS),
    ("park", Habitat.AMENITY_GRASS),
    ("pasture", Habitat.AMENITY_GRASS),
    ("garden", Habitat.GARDEN),
    ("arable", Habitat.CROP),
    ("crop", Habitat.CROP),
    ("cultivated", Habitat.CROP),
    ("bare", Habitat.BARE),
    ("building", Habitat.SEALED),
    ("built up", Habitat.SEALED),
    ("road", Habitat.SEALED),
    ("rail", Habitat.SEALED),
    ("pavement", Habitat.SEALED),
    ("sealed", Habitat.SEALED),
    ("manmade", Habitat.SEALED),
)

# Specific Priority Habitat Inventory names. Anything else in that scheme still
# maps to priority habitat, because membership of the inventory is the signal.
PRIORITY_RULES = (
    ("limestone pavement", Habitat.IRREPLACEABLE),
    ("blanket bog", Habitat.IRREPLACEABLE),
    ("raised bog", Habitat.IRREPLACEABLE),
    ("bog", Habitat.IRREPLACEABLE),
    ("ancient woodland", Habitat.ANCIENT_WOODLAND),
    ("ancient wood", Habitat.ANCIENT_WOODLAND),
    ("pond", Habitat.PRIORITY_WATER),
    ("lake", Habitat.PRIORITY_WATER),
    ("lagoon", Habitat.PRIORITY_WATER),
    ("river", Habitat.PRIORITY_WATER),
    ("reed", Habitat.WETLAND),
    ("fen", Habitat.WETLAND),
    ("marsh", Habitat.WETLAND),
    ("mudflat", Habitat.WETLAND),
    ("saltmarsh", Habitat.WETLAND),
    ("salt marsh", Habitat.WETLAND),
    ("swamp", Habitat.WETLAND),
)

# ESA WorldCover v200 class codes. Grassland (30) is read as modified grass:
# in towns the class is mostly amenity and pasture, and real semi-natural
# grassland should arrive later from the Priority Habitat Inventory.
ESA_WORLDCOVER_V200 = {
    10: Habitat.WOODLAND,
    20: Habitat.SCRUB,
    30: Habitat.AMENITY_GRASS,
    40: Habitat.CROP,
    50: Habitat.SEALED,
    60: Habitat.BARE,
    70: Habitat.BARE,
    80: Habitat.OPEN_WATER,
    90: Habitat.WETLAND,
    95: Habitat.WETLAND,
    100: Habitat.SEMI_NATURAL_GRASS,
}

SCHEME_ESA = "esa_worldcover"
SCHEME_KEYWORD = "keyword"
SCHEME_HABITAT = "habitat_code"
SCHEME_GREENSPACE = "os_greenspace"
SCHEME_PRIORITY = "priority_habitat"

_HABITAT_NAMES = {}
for _habitat in Habitat:
    _HABITAT_NAMES[_habitat.name.lower().replace("_", " ")] = _habitat
    _HABITAT_NAMES[normalise_label(_habitat.name)] = _habitat


def map_value(value, scheme):
    """Map one attribute value to a habitat, or ``None`` if it should not burn.

    For ``priority_habitat``, the return is ``(habitat, specific)`` via
    :func:`map_priority_habitat` instead. This function returns only the habitat
    for that scheme, defaulting unrecognised names to priority habitat.
    """
    if value is None:
        return None
    if scheme == SCHEME_PRIORITY:
        habitat, _specific = map_priority_habitat(value)
        return habitat
    if scheme == SCHEME_ESA:
        return _map_esa(value)
    if scheme == SCHEME_GREENSPACE:
        return _map_greenspace(value)
    if scheme == SCHEME_HABITAT:
        return _map_habitat_code(value)
    if scheme == SCHEME_KEYWORD:
        return _map_keyword(value)
    raise ValueError("Unknown classification scheme: {}".format(scheme))


def map_priority_habitat(value):
    """Return ``(habitat, specific)`` for a Priority Habitat Inventory name.

    ``specific`` is False when the name fell through to the default priority
    class. Empty values return ``(None, False)``.
    """
    if value is None:
        return None, False
    label = normalise_label(value)
    if label in ("", "none", "null", "nan"):
        return None, False
    for needle, habitat in PRIORITY_RULES:
        if needle in label:
            return habitat, True
    return Habitat.PRIORITY_HABITAT, False


def _map_esa(value):
    code = _as_int(value)
    if code is None:
        return None
    return ESA_WORLDCOVER_V200.get(code)


def _map_greenspace(value):
    label = normalise_label(value)
    if not label:
        return None
    return OS_GREENSPACE_FUNCTION.get(label)


def _map_keyword(value):
    label = normalise_label(value)
    if not label:
        return None
    for needle, habitat in KEYWORD_RULES:
        if needle in label:
            return habitat
    return None


def _map_habitat_code(value):
    code = _as_int(value)
    if code is not None:
        try:
            return Habitat(code)
        except ValueError:
            return None
    label = normalise_label(value)
    return _HABITAT_NAMES.get(label)


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def combine_habitat_layers(layers):
    """Burn habitat layers in precedence order. Later layers overwrite.

    Each layer is an integer array. Cells below zero are nodata and do not
    overwrite. The result starts as ``Habitat.UNKNOWN``.
    """
    if not layers:
        raise ValueError("At least one habitat layer is required.")
    arrays = [np.asarray(layer) for layer in layers]
    shape = arrays[0].shape
    out = np.full(shape, int(Habitat.UNKNOWN), dtype=np.int16)
    for layer in arrays:
        if layer.shape != shape:
            raise ValueError("Habitat layers must share a shape.")
        present = layer >= 0
        out[present] = layer[present]
    return out
