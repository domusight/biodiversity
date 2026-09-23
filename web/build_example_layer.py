# SPDX-License-Identifier: GPL-2.0-or-later
"""Write the Leaflet image and index for the Riverside Quarter example.

Run from the repository root:

    python3 web/build_example_layer.py
"""

import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_ROOT, "examples", "riverside_quarter"))
sys.path.insert(0, os.path.join(_ROOT, "qgis"))

from images import POTENTIAL_STOPS, write_png  # noqa: E402
from osgb import bng_to_wgs84  # noqa: E402
from riverside import (  # noqa: E402
    CELL_M,
    ORIGIN_X,
    ORIGIN_Y,
    SAMPLES,
    SIZE_M,
    build,
    sample_table,
    score_landscape,
)

_DATA = os.path.join(_HERE, "data")
_SCALE = 8
_NODATA = -1

_PLACE_NAMES = {
    "ancient_interior": "Ancient wood, interior",
    "ancient_edge": "Ancient wood, edge",
    "reedbed": "Reedbed",
    "pond": "Pond",
    "copse": "Copse",
    "allotment": "Allotments",
    "verge": "Tree verge",
    "garden_near": "Garden beside the wood",
    "park": "Park grassland",
    "garden_far": "Garden in the housing",
    "playing_field": "Playing field",
    "sealed_between": "Sealed street beside the wood",
    "sealed_south": "Sealed street in the south",
}

# View centres for the city buttons. These are camera positions, not scores.
_CITY_VIEWS = (
    ("london", "London", 51.5074, -0.1278, 12),
    ("birmingham", "Birmingham", 52.4799, -1.9026, 12),
    ("manchester", "Manchester", 53.4794, -2.2453, 12),
    ("leeds", "Leeds", 53.7997, -1.5492, 12),
)


def colour_index(index, mask, scale=_SCALE):
    """RGBA image, row 0 north, transparent outside the area of interest."""
    image = np.zeros(index.shape + (4,), dtype=np.uint8)
    finite = np.isfinite(index) & mask
    flat = index[finite]
    painted = np.zeros((flat.size, 3), dtype=np.uint8)
    stops_x = [stop[0] for stop in POTENTIAL_STOPS]
    for channel in range(3):
        stops_y = [stop[1][channel] for stop in POTENTIAL_STOPS]
        painted[:, channel] = np.interp(flat, stops_x, stops_y).astype(np.uint8)
    image[finite, :3] = painted
    image[finite, 3] = 255
    if scale != 1:
        image = np.repeat(np.repeat(image, scale, axis=0), scale, axis=1)
    return image


def pack_index(index, mask):
    """Row-major scores rounded to 0.01. Nodata is -1. Row 0 is north."""
    packed = []
    height, width = index.shape
    for row in range(height):
        for column in range(width):
            if not mask[row, column] or not np.isfinite(index[row, column]):
                packed.append(_NODATA)
            else:
                packed.append(round(float(index[row, column]), 2))
    return packed


def sample_grid(values, width, height, easting, northing, origin_x=ORIGIN_X, origin_y=ORIGIN_Y, cell_m=CELL_M, size_m=SIZE_M):
    """Score at a British National Grid point, or None outside the index."""
    column = int(math.floor((easting - origin_x) / cell_m))
    row = int(math.floor((origin_y + size_m - northing) / cell_m))
    if column < 0 or row < 0 or column >= width or row >= height:
        return None
    value = values[row * width + column]
    if value < 0:
        return None
    return value


def _cell_centre(local_x, local_y):
    column = int(math.floor(local_x / CELL_M))
    row = int(math.floor((SIZE_M - local_y) / CELL_M))
    return (column + 0.5) * CELL_M, SIZE_M - (row + 0.5) * CELL_M


def _lat_lon(easting, northing):
    latitude, longitude = bng_to_wgs84(easting, northing)
    return [round(latitude, 8), round(longitude, 8)]


def example_layer():
    """Build the web layer in memory: image, index, and the manifest fields."""
    landscape = build()
    result = score_landscape(landscape)
    table = {row["name"]: row for row in sample_table(landscape, result)}
    values = pack_index(result.index, landscape["mask"])
    height, width = result.index.shape
    samples = []
    for key, _x, _y in SAMPLES:
        row = table[key]
        centre_x, centre_y = _cell_centre(row["local_x_m"], row["local_y_m"])
        easting = ORIGIN_X + centre_x
        northing = ORIGIN_Y + centre_y
        samples.append(
            {
                "id": key,
                "name": _PLACE_NAMES[key],
                "easting": easting,
                "northing": northing,
                "potential": sample_grid(values, width, height, easting, northing),
            }
        )
    lens = next(sample for sample in samples if sample["id"] == "ancient_interior")
    south_west = _lat_lon(ORIGIN_X, ORIGIN_Y)
    north_east = _lat_lon(ORIGIN_X + SIZE_M, ORIGIN_Y + SIZE_M)
    return {
        "rgba": colour_index(result.index, landscape["mask"], _SCALE),
        "scale": _SCALE,
        "width": width,
        "height": height,
        "values": values,
        "bounds": [south_west, north_east],
        "aoi_center": _lat_lon(ORIGIN_X + landscape["centre"][0], ORIGIN_Y + landscape["centre"][1]),
        "lens": [lens["easting"], lens["northing"]],
        "lens_wgs84": _lat_lon(lens["easting"], lens["northing"]),
        "radius_m": landscape["radius_m"],
        "samples": samples,
        "origin_easting": ORIGIN_X,
        "origin_northing": ORIGIN_Y,
        "cell_m": CELL_M,
        "size_m": SIZE_M,
    }


def manifest(layer):
    """JSON manifest consumed by web/map.js."""
    example_view = {
        "id": "riverside",
        "title": "Example",
        "lat": layer["lens_wgs84"][0],
        "lon": layer["lens_wgs84"][1],
        "zoom": 16,
    }
    places = [example_view]
    for key, title, lat, lon, zoom in _CITY_VIEWS:
        places.append({"id": key, "title": title, "lat": lat, "lon": lon, "zoom": zoom})
    return {
        "index_version": "0.1.0",
        "layer": {
            "id": "riverside-quarter",
            "title": "Riverside Quarter",
            "image": "data/riverside_potential.png",
            "index": "data/riverside_index.json",
            "bounds": layer["bounds"],
            "center": layer["lens_wgs84"],
            "zoom": 16,
            "aoi_center": layer["aoi_center"],
            "radius_m": layer["radius_m"],
            "lens": layer["lens_wgs84"],
            "samples": [
                {
                    "id": sample["id"],
                    "name": sample["name"],
                    "easting": sample["easting"],
                    "northing": sample["northing"],
                    "potential": sample["potential"],
                }
                for sample in layer["samples"]
            ],
        },
        "places": places,
    }


def main():
    os.makedirs(_DATA, exist_ok=True)
    layer = example_layer()
    write_png(os.path.join(_DATA, "riverside_potential.png"), layer["rgba"])
    index_path = os.path.join(_DATA, "riverside_index.json")
    with open(index_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "origin_easting": layer["origin_easting"],
                "origin_northing": layer["origin_northing"],
                "cell_m": layer["cell_m"],
                "size_m": layer["size_m"],
                "width": layer["width"],
                "height": layer["height"],
                "nodata": _NODATA,
                "values": layer["values"],
            },
            handle,
            separators=(",", ":"),
        )
        handle.write("\n")
    with open(os.path.join(_DATA, "layers.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest(layer), handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
