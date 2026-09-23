# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic urban block used to show the index.

The shapes are invented. They are placed on British National Grid only so the
grid has metre units. The origin sits in the English Channel, south of the
Isle of Wight, so the example cannot be mistaken for a survey of a real town.
"""

import numpy as np

from biodiversity_potential.habitats import Habitat
from biodiversity_potential.model import ModelConfig, run_model

ORIGIN_X = 440000.0
ORIGIN_Y = 40000.0
SIZE_M = 1800.0
CELL_M = 10.0
CENTRE = (900.0, 900.0)
AOI_RADIUS_M = 250.0

# Later polygons overwrite earlier ones. The order matches the plugin:
# urban surfaces, then woody cover, then water, then priority habitat, then
# ancient woodland.
# Boxes are (xmin, ymin, xmax, ymax) in local metres, y increasing north.
# Edges sit on the 10 m grid. A cell is included when its centre falls inside,
# so two boxes that meet on a grid line do not share a cell.
POLYGONS = (
    ("far_gardens", Habitat.GARDEN, 0.40, (700, 680, 820, 760)),
    ("playing_field", Habitat.AMENITY_GRASS, 0.24, (720, 760, 980, 860)),
    ("park", Habitat.AMENITY_GRASS, 0.46, (720, 900, 900, 1100)),
    ("verge", Habitat.SCATTERED_TREES, 0.62, (720, 960, 752, 1080)),
    ("copse", Habitat.WOODLAND, 0.80, (760, 960, 850, 1050)),
    ("near_gardens", Habitat.GARDEN, 0.40, (900, 960, 980, 1120)),
    ("allotments", Habitat.ALLOTMENT, 0.64, (1020, 760, 1160, 850)),
    ("ancient_wood", Habitat.ANCIENT_WOODLAND, 0.88, (980, 860, 1600, 1500)),
    ("reedbed", Habitat.WETLAND, 0.60, (1000, 960, 1100, 1060)),
    ("pond", Habitat.OPEN_WATER, -0.05, (1000, 900, 1060, 960)),
)

SAMPLES = (
    ("ancient_interior", 1120, 940),
    ("ancient_edge", 995, 900),
    ("reedbed", 1040, 1000),
    ("pond", 1030, 930),
    ("copse", 800, 1000),
    ("allotment", 1080, 800),
    ("park", 800, 1080),
    ("garden_near", 940, 1040),
    ("garden_far", 750, 720),
    ("playing_field", 850, 800),
    ("verge", 735, 1000),
    ("sealed_between", 930, 900),
    ("sealed_south", 860, 680),
)


def build():
    """Return the habitat grid, NDVI, area-of-interest mask, and georeferencing."""
    count = int(SIZE_M / CELL_M)
    habitat = np.full((count, count), int(Habitat.SEALED), dtype=np.int16)
    ndvi = np.full((count, count), 0.06, dtype=float)
    for _name, habitat_code, ndvi_value, box in POLYGONS:
        _burn_rectangle(habitat, ndvi, box, int(habitat_code), ndvi_value)

    columns = (np.arange(count) + 0.5) * CELL_M
    rows = SIZE_M - (np.arange(count) + 0.5) * CELL_M
    xx, yy = np.meshgrid(columns, rows)
    mask = np.hypot(xx - CENTRE[0], yy - CENTRE[1]) <= AOI_RADIUS_M
    return {
        "habitat": habitat,
        "ndvi": ndvi,
        "mask": mask,
        "origin_x": ORIGIN_X,
        "origin_y": ORIGIN_Y,
        "size_m": SIZE_M,
        "cell_m": CELL_M,
        "centre": CENTRE,
        "radius_m": AOI_RADIUS_M,
    }


def score_landscape(landscape=None, config=None):
    """Run the index on the synthetic block."""
    landscape = landscape or build()
    config = config or ModelConfig(
        cell_size_m=landscape["cell_m"],
        neighbourhood_radius_m=AOI_RADIUS_M,
    )
    result = run_model(
        landscape["habitat"],
        ndvi=landscape["ndvi"],
        report_mask=landscape["mask"],
        config=config,
    )
    return result


def sample_table(landscape, result):
    """One row per named place, read from the cell containing that point."""
    rows = []
    for name, x_local, y_local in SAMPLES:
        row, column = _cell_index(x_local, y_local)
        habitat_code = int(landscape["habitat"][row, column])
        rows.append(
            {
                "name": name,
                "local_x_m": x_local,
                "local_y_m": y_local,
                "easting": ORIGIN_X + x_local,
                "northing": ORIGIN_Y + y_local,
                "inside_aoi": bool(landscape["mask"][row, column]),
                "habitat_code": habitat_code,
                "habitat": Habitat(habitat_code).name.lower(),
                "ndvi": round(float(landscape["ndvi"][row, column]), 3),
                "potential": _round(result.index[row, column]),
                "components": {
                    key: _round(result.components[key][row, column])
                    for key in result.components
                },
            }
        )
    return rows


def _cell_index(x_local, y_local):
    column = int(np.floor(x_local / CELL_M))
    row = int(np.floor((SIZE_M - y_local) / CELL_M))
    return row, column


def _burn_rectangle(habitat, ndvi, box, code, ndvi_value):
    x0, y0, x1, y1 = box
    count = habitat.shape[0]
    columns = (np.arange(count) + 0.5) * CELL_M
    rows = SIZE_M - (np.arange(count) + 0.5) * CELL_M
    column_inside = (columns >= x0) & (columns < x1)
    row_inside = (rows >= y0) & (rows < y1)
    habitat[np.ix_(row_inside, column_inside)] = code
    ndvi[np.ix_(row_inside, column_inside)] = ndvi_value


def _round(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return round(float(value), 2)
