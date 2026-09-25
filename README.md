# Biodiversity potential

A QGIS tool that maps where biodiversity potential is higher and lower. The study area is a point plus a radius, by default 250 m, or a polygon of any size.

The result is a 0–100 raster. Darker green is higher potential. It is a screening layer built from published urban ecology and from open data: Ordnance Survey Open Greenspace and Open Map Local, Natural England’s Priority Habitat Inventory, Ancient Woodland, SSSI and Local Nature Reserves, ESA WorldCover, and optional Sentinel-2 NDVI. Narrow streams are Open Map Local `SurfaceWater_Line`. The reasoning is written out in [docs/theory.md](docs/theory.md). The equations are in [docs/method.md](docs/method.md).

This is a landscape screen for a neighbourhood. Statutory Biodiversity Net Gain calculations remain the Statutory Biodiversity Metric plus a field condition assessment. This index does not implement that metric’s condition scores or trading rules, and it does not record species.

## What the map shows

The picture below is a synthetic site, [Riverside Quarter](examples/riverside_quarter/README.md), invented so the method can be seen and tested. The coordinates sit in the English Channel on purpose. It is not a survey of a real town.

![Biodiversity potential on the synthetic site. Dark green is the ancient wood. Pale cells are sealed land.](examples/riverside_quarter/output/preview_potential.png)

![Habitat classes that produced the score.](examples/riverside_quarter/output/preview_habitat.png)

| Place | Index | Class |
| --- | ---: | --- |
| Ancient wood, interior | 87 | 85–100 |
| Ancient wood, edge | 84 | 45–85 |
| Reedbed in the wood | 80 | 45–85 |
| Pond | 60 | 45–85 |
| Copse in the park | 57 | 45–85 |
| Allotments | 55 | 45–85 |
| Garden beside the wood | 40 | 10–45 |
| Park grassland | 25 | 10–45 |
| Garden in the southern housing | 20 | 10–45 |
| Playing field | 17 | 10–45 |
| Sealed street beside the wood | 6 | 5–10 |
| Sealed street in the south | 3 | 0.5–3 |

The same garden scores 40 beside the wood and 20 in the housing. The street beside the wood stays at 6. Patch size, habitat quality and vegetation do the heavy lifting. Neighbourhood context moves a surface up or down, and a permeability gate stops sealed land from inheriting the score of the habitat next to it.

The full component table, and the checks that keep these ranks stable, are in the [example notes](examples/riverside_quarter/README.md).

## The map

Each cell is scored from a 250 m neighbourhood. A point uses the radius you set. A polygon, including a city boundary such as Greater London, uses the same index and is scored in tiles. Give the tool the boundary and the full input layers. It clips them itself.

[web/index.html](web/index.html) is the public map. The green overlay is a finished index. The page does not score anything while someone looks at it. London is the published city layer. Birmingham, Manchester and Leeds are camera positions until their indexes are uploaded. Details are in [web/README.md](web/README.md).

```
python3 -m http.server -d web 8765
```

Then open `http://127.0.0.1:8765/`. Details are in [web/README.md](web/README.md).

## How the score is made

Eight components, weighted in the order reported by Beninde, Veith and Hochkirch (2015): patch area and connectivity first, then vegetation structure, with local habitat ahead of a broad landscape label.

| Component | Weight | Measured from |
| --- | ---: | --- |
| Patch area | 0.22 | Species–area curve, saturating at 50 hectares |
| Habitat amount | 0.18 | Mean distinctiveness within 250 m |
| Connectivity | 0.16 | Distance to structural habitat or a designation |
| Vegetation | 0.14 | Sentinel-2 NDVI, with water handled separately |
| Distinctiveness | 0.14 | Statutory Biodiversity Metric bands, plus gardens and allotments |
| Blue infrastructure | 0.08 | Distance to water and wetland |
| Heterogeneity | 0.05 | Mix of habitat classes in the neighbourhood |
| Interior | 0.03 | Depth inside a patch, saturating at 30 m |

Distinctiveness follows the Metric bands (0, 2, 4, 6, 8, divided by 8). Gardens and allotments sit between the low and medium bands because that literature treats them as matrix and as sites, which the Metric’s developed-land class does not. Details, citations and the choices that could have gone another way are in [docs/theory.md](docs/theory.md).

## Run it in QGIS

Install `qgis/biodiversity_potential-0.3.0.zip` with **Plugins → Manage and Install Plugins → Install from ZIP**, then enable **Biodiversity potential** and open **Urban biodiversity potential 0.3.0** in the Processing toolbox. The area must be in a metre CRS, normally EPSG:27700.

The steps, the parameters, and how to build a floating-point NDVI from Sentinel-2 are in [docs/user-guide.md](docs/user-guide.md). Dataset links and licences are in [docs/data-sources.md](docs/data-sources.md).

```
python3 -m pytest
python3 examples/riverside_quarter/build_example.py
```

The tests cover the model. They do not launch QGIS. NumPy is the only runtime dependency of the library. QGIS supplies GDAL when the toolbox algorithm runs.

## Layout

```
qgis/biodiversity_potential/    QGIS plugin and the Python model
docs/                           theory, method, data, user guide, references
examples/riverside_quarter/     synthetic site, grid, and preview
web/                            Leaflet map of precomputed indexes
tests/                          model, crosswalk, example ranks, plugin package
```

The model (`model.py`, `components.py`, `habitats.py`, `crosswalk.py`, `spatial.py`) does not import QGIS, so it can be tested on its own. `algorithm.py` is the Processing tool that turns OS and Natural England layers into the grids the model scores.

## Licence

GPL-2.0-or-later, the usual licence for a QGIS plugin. OS OpenData and Natural England open data stay under the Open Government Licence when you use them; they are not redistributed here. ESA WorldCover is CC BY 4.0.

Cite the method with [CITATION.cff](CITATION.cff). Cite Beninde, Veith and Hochkirch (2015) if you quote the weighting rationale, and the dataset citations in [docs/references.md](docs/references.md) for any map you publish.
