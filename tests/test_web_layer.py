# SPDX-License-Identifier: GPL-2.0-or-later
"""The Leaflet layer is the same index as the worked example."""

import json
import math
import os
import shutil
import struct
import subprocess
import zlib

import numpy as np
import pytest

from build_example_layer import attach_tiles, example_layer, sample_grid
from osgb import bng_to_wgs84, wgs84_to_bng

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DATA = os.path.join(_ROOT, "web", "data")


def test_channel_corner_matches_the_proj_helmert_pipeline():
    latitude, longitude = bng_to_wgs84(440000, 40000)
    assert latitude == pytest.approx(50.25863584, abs=1e-7)
    assert longitude == pytest.approx(-1.44021075, abs=1e-7)


def test_trafalgar_square_matches_the_proj_helmert_pipeline():
    latitude, longitude = bng_to_wgs84(530030, 180380)
    assert latitude == pytest.approx(51.50739886, abs=1e-7)
    assert longitude == pytest.approx(-0.12778198, abs=1e-7)


def test_wgs84_round_trip_is_within_a_millimetre():
    for easting, northing in ((440900, 40900), (441125, 40935), (530030, 180380)):
        latitude, longitude = bng_to_wgs84(easting, northing)
        back_e, back_n = wgs84_to_bng(latitude, longitude)
        assert back_e == pytest.approx(easting, abs=0.001)
        assert back_n == pytest.approx(northing, abs=0.001)


def test_named_places_keep_the_published_scores():
    layer = example_layer()
    expected = {
        "ancient_interior": 87.16,
        "ancient_edge": 83.65,
        "reedbed": 79.68,
        "pond": 59.87,
        "copse": 56.87,
        "allotment": 55.36,
        "verge": 45.46,
        "garden_near": 40.25,
        "park": 24.74,
        "garden_far": 19.96,
        "playing_field": 16.78,
        "sealed_between": 5.63,
        "sealed_south": 2.56,
    }
    by_id = {sample["id"]: sample for sample in layer["samples"]}
    assert set(by_id) == set(expected)
    for key, score in expected.items():
        sample = by_id[key]
        assert sample["potential"] == score
        assert sample_grid(layer["values"], layer["width"], layer["height"], sample["easting"], sample["northing"]) == score


def test_published_files_match_the_model():
    layer = example_layer()
    with open(os.path.join(_DATA, "layers.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    published = manifest["layer"]
    assert published["bounds"] == layer["bounds"]
    assert published["lens"] == layer["lens_wgs84"]
    assert published["radius_m"] == 250
    with open(os.path.join(_DATA, "riverside_index.json"), encoding="utf-8") as handle:
        index = json.load(handle)
    assert index["values"] == layer["values"]
    png = _read_png(os.path.join(_DATA, "riverside_potential.png"))
    assert png.shape == layer["rgba"].shape
    assert np.array_equal(png, layer["rgba"])


def test_city_tile_urls_survive_a_rebuild():
    places = [
        {"id": "riverside", "title": "Example"},
        {"id": "london", "title": "London"},
    ]
    previous = [
        {
            "id": "london",
            "tiles": "https://storage.googleapis.com/example-bucket/london/{z}/{x}/{y}.png",
        },
        {"id": "birmingham", "title": "Birmingham"},
    ]
    attach_tiles(places, previous)
    assert places[1]["tiles"] == previous[0]["tiles"]
    assert "tiles" not in places[0]


def test_javascript_transform_matches_python():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = r"""
const osgb = require("./web/osgb.js");
const points = [[440000, 40000], [440900, 40900], [441125, 40935], [530030, 180380]];
for (const [e, n] of points) {
  const [lat, lon] = osgb.bngToWgs84(e, n);
  const [e2, n2] = osgb.wgs84ToBng(lat, lon);
  process.stdout.write([e, n, lat, lon, e2, n2].join(",") + "\n");
}
"""
    completed = subprocess.run([node, "-e", script], cwd=_ROOT, check=True, capture_output=True, text=True)
    for line in completed.stdout.splitlines():
        easting, northing, latitude, longitude, back_e, back_n = [float(part) for part in line.split(",")]
        py_lat, py_lon = bng_to_wgs84(easting, northing)
        assert latitude == pytest.approx(py_lat, abs=1e-9)
        assert longitude == pytest.approx(py_lon, abs=1e-9)
        assert back_e == pytest.approx(easting, abs=0.001)
        assert math.isfinite(back_n)


def _read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    width = height = color_type = None
    idat = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, _bit, color_type = struct.unpack(">IIBB", chunk[:10])
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break
        pos += 12 + length
    assert color_type == 6
    raw = zlib.decompress(idat)
    channels = 4
    stride = width * channels
    rows = []
    cursor = 0
    for _ in range(height):
        assert raw[cursor] == 0
        cursor += 1
        rows.append(raw[cursor:cursor + stride])
        cursor += stride
    image = np.frombuffer(b"".join(rows), dtype=np.uint8).reshape((height, width, channels))
    return image
