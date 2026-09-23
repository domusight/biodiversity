# User guide

## Install

The plugin is the folder `qgis/biodiversity_potential`. Copy that folder, not the whole repository, into the QGIS profile plugins directory.

- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`

Restart QGIS. In **Plugins → Manage and Install Plugins**, turn on **Biodiversity potential**. In the Processing toolbox, open **Biodiversity potential → Urban ecology → Urban biodiversity potential**.

QGIS 3.28 or later. The area of interest must be in a projected CRS with metre units. For English open data that is British National Grid, EPSG:27700.

## Run

1. Put the area in as a polygon, or as a point. Points are buffered by the radius, default 250 m.
2. Add whatever of the following you have. One habitat layer is the minimum. The useful set is a wall-to-wall base, OS Open Greenspace, a woodland overlay, surface water or rivers, the Priority Habitat Inventory, and Ancient Woodland.
3. Optionally add a single-band NDVI raster. See `docs/data-sources.md` for how to calculate it.
4. Run. The log prints the weights, the number of features used, any class names the crosswalk did not recognise, and the count of cells in each legend class.

The tool builds a grid over the area plus a context buffer (1 km by default), scores every cell, and writes the area of interest. Input layers should cover that wider window. If one of them falls short, the log warns you: the gap is left unrecorded and the edge of the data will score low.

### Basic parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| Buffer radius for points | 250 m | Ignored when the area is already a polygon. |
| Cell size | 10 m | Matches Sentinel-2 and WorldCover. |
| Neighbourhood radius | 250 m | Circle used for habitat amount and heterogeneity. |
| Base classification | ESA WorldCover | Or keyword labels, habitat codes, greenspace functions, priority-habitat names. |
| Greenspace function field | choose `function` | OS Open Greenspace. |
| Assumed river width | 8 m | Centreline buffer. Narrower lines are thickened to about one cell so they are not missed. |
| NDVI | optional | Float index, about −1 to 1. |

### Advanced parameters

Context buffer, the two half-distances, the interior distance, the 50 ha reference, the species-area exponent, the eight weights, and two switches: treat unrecorded land as sealed, and whether SSSI and Local Nature Reserve polygons count as connectivity sources. Weights that do not sum to 1 are rescaled, and the log shows the values used.

## Read the layer

The layer is 0–100. The style file is copied beside the GeoTIFF and applied when QGIS loads the result.

| Colour, from pale to dark green | Index | Class |
| --- | --- | --- |
| Pale | 0–15 | Low |
| | 15–30 | Limited |
| | 30–45 | Moderate |
| | 45–65 | High |
| Dark | 65–100 | Very high |

Dark green is where several of the strong components coincide: a large, distinctive, well-vegetated patch. Pale is sealed or unrecorded land, including where that land sits near better habitat. A sealed cell keeps only a fifth of the neighbourhood score, so a road does not turn dark green because a wood is next to it.

Turn on the optional component raster to see which term produced a score. The bands are distinctiveness, patch area, habitat amount, connectivity, vegetation, blue, heterogeneity, interior. They are 0–1, and the four neighbourhood bands are already multiplied by surface permeability.

The optional cell polygons carry the same numbers as attributes, for the identify tool. Leave them off on anything larger than a neighbourhood. Above 250,000 cells they are skipped.

## Prepare a repeatable project

Keep the inputs in one GeoPackage per theme, in EPSG:27700, clipped to the site plus at least 1 km. Name the class fields in a way you will recognise next year (`function`, `Main_Habit`). Record the Sentinel-2 scene date next to the NDVI file. The index will move if you swap a winter scene for a July scene, and that movement is phenology, not a gain in habitat.

## Tests and the example

From the repository root, with NumPy and pytest installed:

```
python3 -m pytest
python3 examples/riverside_quarter/build_example.py
```

The tests cover the distance transform, the crosswalk, the index, and the rank order on the synthetic site. They do not start QGIS. The Processing algorithm is ordinary PyQGIS and GDAL and is meant to be run from the toolbox.

The synthetic site and its grid are described in `examples/riverside_quarter/README.md`.
