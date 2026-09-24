# SPDX-License-Identifier: GPL-2.0-or-later
"""Write the synthetic Riverside Quarter grid, preview and score table.

Run from the repository root:

    python3 examples/riverside_quarter/build_example.py
"""

import json
import os
import shutil
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_ROOT, "qgis"))

from images import habitat_rgb, potential_rgb, write_icon, write_png  # noqa: E402
from riverside import build, sample_table, score_landscape  # noqa: E402

_OUTPUT = os.path.join(_HERE, "output")
_STYLE = os.path.join(_ROOT, "qgis", "biodiversity_potential", "style", "biodiversity_potential.qml")
_ICON = os.path.join(_ROOT, "qgis", "biodiversity_potential", "icon.png")

_BNG_WKT = (
    'PROJCS["OSGB 1936 / British National Grid",'
    'GEOGCS["OSGB 1936",DATUM["OSGB_1936",'
    'SPHEROID["Airy 1830",6377563.396,299.3249646]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["latitude_of_origin",49],'
    'PARAMETER["central_meridian",-2],'
    'PARAMETER["scale_factor",0.9996012717],'
    'PARAMETER["false_easting",400000],'
    'PARAMETER["false_northing",-100000],'
    'UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH],'
    'AUTHORITY["EPSG","27700"]]'
)


def main():
    os.makedirs(_OUTPUT, exist_ok=True)
    landscape = build()
    result = score_landscape(landscape)
    samples = sample_table(landscape, result)
    _write_asc(
        os.path.join(_OUTPUT, "biodiversity_potential.asc"),
        result.index,
        landscape,
        nodata=-9999,
    )
    _write_asc(
        os.path.join(_OUTPUT, "habitat.asc"),
        np.where(landscape["mask"], landscape["habitat"], -9999),
        landscape,
        nodata=-9999,
        integer=True,
    )
    prj = os.path.join(_OUTPUT, "biodiversity_potential.prj")
    with open(prj, "w", encoding="utf-8") as handle:
        handle.write(_BNG_WKT)
    shutil.copyfile(prj, os.path.join(_OUTPUT, "habitat.prj"))
    if os.path.isfile(_STYLE):
        shutil.copyfile(_STYLE, os.path.join(_OUTPUT, "biodiversity_potential.qml"))
    write_png(
        os.path.join(_OUTPUT, "preview_potential.png"),
        potential_rgb(result.index, landscape["mask"], scale=8),
    )
    write_png(
        os.path.join(_OUTPUT, "preview_habitat.png"),
        habitat_rgb(landscape["habitat"], landscape["mask"], scale=8),
    )
    write_icon(_ICON)
    scored = result.index[np.isfinite(result.index)]
    summary = {
        "note": (
            "Synthetic Riverside Quarter. Coordinates are British National Grid "
            "so the grid has metre units. The origin is in the English Channel "
            "and the shapes are not a survey of a real place."
        ),
        "origin_easting": landscape["origin_x"],
        "origin_northing": landscape["origin_y"],
        "cell_m": landscape["cell_m"],
        "aoi_radius_m": landscape["radius_m"],
        "neighbourhood_radius_m": landscape["radius_m"],
        "weights": result.weights,
        "cells": int(scored.size),
        "minimum": round(float(scored.min()), 2),
        "mean": round(float(scored.mean()), 2),
        "maximum": round(float(scored.max()), 2),
        "samples": samples,
    }
    with open(os.path.join(_OUTPUT, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    print("Wrote {0}".format(_OUTPUT))
    for row in samples:
        print("{0:20} {1:6}".format(row["name"], row["potential"]))


def _write_asc(path, array, landscape, nodata, integer=False):
    height, width = array.shape
    header = (
        "ncols {width}\n"
        "nrows {height}\n"
        "xllcorner {xmin}\n"
        "yllcorner {ymin}\n"
        "cellsize {cell}\n"
        "NODATA_value {nodata}\n"
    ).format(
        width=width,
        height=height,
        xmin=landscape["origin_x"],
        ymin=landscape["origin_y"],
        cell=landscape["cell_m"],
        nodata=int(nodata),
    )
    lines = [header]
    for row in array:
        if integer:
            cells = [str(int(nodata)) if not np.isfinite(value) or value < 0 else str(int(value)) for value in row]
        else:
            cells = []
            for value in row:
                if not np.isfinite(value):
                    cells.append(str(int(nodata)))
                else:
                    cells.append("{0:.2f}".format(float(value)))
        lines.append(" ".join(cells) + "\n")
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


if __name__ == "__main__":
    main()
