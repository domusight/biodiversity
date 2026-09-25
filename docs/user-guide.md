# User guide

## Install

The install file is `qgis/biodiversity_potential-0.3.1.zip`. The toolbox name ends in **0.3.1**. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**, choose that file, then turn on **Biodiversity potential**.

Download the zip itself. On GitHub, open the file and use **Download raw file**. A page saved from the browser is HTML, and QGIS then reports that the file is not a zip. The zip begins with the characters `PK`.

The zip contains one folder, `biodiversity_potential`, with `metadata.txt` inside it. That is the layout QGIS expects. Rebuild it with `make plugin-zip` after a plugin change.

You can also copy the folder `qgis/biodiversity_potential` itself, not the whole repository, into the QGIS profile plugins directory.

- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`

Restart QGIS. In **Plugins → Manage and Install Plugins**, turn on **Biodiversity potential**. In the Processing toolbox, open **Biodiversity potential → Urban ecology → Urban biodiversity potential 0.3.1**.

QGIS 3.28 or later. The area of interest must be in a projected CRS with metre units. For English open data that is British National Grid, EPSG:27700.

## Run

1. Put the area in as a polygon, or as a point. Points are buffered by the radius, default 250 m. A polygon can be a neighbourhood or a city boundary. There is no size cap.
2. Add whatever of the following you have. One habitat layer is the minimum. The useful set is a wall-to-wall base, OS Open Greenspace, woodland polygons, surface water lines, surface water area, tidal water, the Priority Habitat Inventory, and Ancient Woodland. Narrow streams are OS Open Map Local `SurfaceWater_Line`.
3. Optionally add up to four Sentinel-2 NDVI rasters. See `docs/data-sources.md` for how to calculate NDVI.
4. Run. The log prints the weights, the number of features used, any class names the crosswalk did not recognise, and, when the area fits in one tile, the count of cells in each legend class.

The tool reads features that meet the area plus a context buffer (1 km by default), scores the area, and writes only the area of interest. A large polygon is split into tiles. You do not need to clip national layers first. If an input falls short of the context, the log warns you: the gap is left unrecorded and the edge of the data will score low.

### Basic parameters

| Parameter | Default | Meaning |
| --- | --- | --- |
| Buffer radius for points | 250 m | Ignored when the area is already a polygon. |
| Cell size | 10 m | Matches Sentinel-2 and WorldCover. |
| Neighbourhood radius | 250 m | Circle used for habitat amount and heterogeneity. |
| Base classification | ESA WorldCover | Or keyword labels, habitat codes, greenspace functions, priority-habitat names. |
| Greenspace function field | choose `function` | OS Open Greenspace. |
| Assumed width of water lines | 8 m | Buffer for `SurfaceWater_Line`. Narrower lines are thickened to about one cell so they are not missed. |
| NDVI tiles 1–4 | optional | Float index, about −1 to 1. One raster per row. |

### Advanced parameters

Context buffer, the two half-distances, the interior distance, the 50 ha reference, the species-area exponent, the eight weights, and two switches: treat unrecorded land as sealed, and whether SSSI and Local Nature Reserve polygons count as connectivity sources. Weights that do not sum to 1 are rescaled, and the log shows the values used.

## Read the layer

The layer is 0–100. The style file is copied beside the GeoTIFF and applied when QGIS loads the result.

| Colour, pale green to dark green | Index |
| --- | --- |
| `#edf8e9` | 0–0.5 |
| `#c7e9c0` | 0.5–3 |
| `#a1d99b` | 3–5 |
| `#74c476` | 5–10 |
| `#41ab5d` | 10–45 |
| `#238b45` | 45–85 |
| `#005a32` | 85–100 |

Dark green is where several of the strong components coincide: a large, distinctive, well-vegetated patch. Pale is sealed or unrecorded land, including where that land sits near better habitat. A sealed cell keeps only a fifth of the neighbourhood score, so a road does not turn dark green because a wood is next to it.

Turn on the optional component raster to see which term produced a score. The bands are distinctiveness, patch area, habitat amount, connectivity, vegetation, blue, heterogeneity, interior. They are 0–1, and the four neighbourhood bands are already multiplied by surface permeability.

The optional cell polygons carry the same numbers as attributes, for the identify tool. Leave them off on anything larger than a neighbourhood. Above 250,000 cells they are skipped.

## One tool, any size

The same tool scores a point buffer and a city polygon. Give it the boundary, for example Greater London, and the full national or regional layers. Leave them unclipped. Put OS Open Map Local `SurfaceWater_Line` in **Surface water lines**. The tool reads only the features that meet the boundary plus the context buffer, scores the boundary in tiles, and writes one raster.

Component rasters and cell polygons are written when the area fits in one tile. A city run writes the index only, and the log says so.

Sentinel-2 tiles overlap on purpose. Calculate NDVI for each tile. The tool has four rows, **Sentinel-2 NDVI tile 1** through **tile 4**. Each row is a normal raster input with a file browser. Put one tile on each row. Where two tiles cover the same ground, the first value is kept. A later tile fills only the cells that are still empty.

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

The same example can be rebuilt for the Leaflet map in `web/`. From the repository root, `python3 -m http.server -d web 8765`, then open `http://127.0.0.1:8765/`. See `web/README.md`. The public site opens on the precomputed London index.
