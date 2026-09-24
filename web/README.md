# Map

A Leaflet map with a [magnifying glass](https://github.com/bbecquet/Leaflet.MagnifyingGlass). The glass follows the pointer and shows a finished biodiversity-potential index inside a 250 m radius, the same circle the QGIS tool scores. Scroll the map and the lens stays at that scale.

The repository gives the tool away. This page invites people to view precomputed maps. Riverside Quarter is the worked example. London, Birmingham, Manchester and Leeds are filled in after those indexes are computed offline and uploaded.

The layer on the page is the synthetic [Riverside Quarter](../examples/riverside_quarter/README.md) example. It is drawn in the English Channel on purpose. London, Birmingham, Manchester and Leeds are camera positions. Their index layers are not in this folder yet. A public XYZ tile URL on a place in `data/layers.json` is drawn in the glass when that city is selected.

## Preview

From the repository root:

```
python3 -m http.server -d web 8765
```

Open `http://127.0.0.1:8765/`. Fetching the index needs HTTP. Opening the file directly will not load it.

Regenerate the image and the index after a model change:

```
python3 web/build_example_layer.py
```

`tests/test_web_layer.py` checks that the published grid still matches the named scores.

## City tiles on Google Cloud

The page displays a finished index. Scoring happens offline, in QGIS or with the Python model, and the coloured raster is uploaded when that run is complete. Nothing is calculated in the browser, and the site does not call Earth Engine.

The HTML stays in this repository. The city rasters are too large to commit, so the finished tiles belong in a Cloud Storage bucket with public read on the tile objects. No API key goes in the page. The light map and the Sentinel-2 cloudless basemap stay on their own servers.

Object names:

```
london/{z}/{x}/{y}.png
birmingham/{z}/{x}/{y}.png
manchester/{z}/{x}/{y}.png
leeds/{z}/{x}/{y}.png
```

Set `tiles` on that city in `data/layers.json`:

```json
"tiles": "https://storage.googleapis.com/BUCKET/london/{z}/{x}/{y}.png"
```

Choosing the city then puts those finished tiles in the magnifying glass. Rebuilding the example keeps a `tiles` URL that is already in the file. The bucket can use uniform access and grant `allUsers` the Storage Object Viewer role on the tile objects. The glass loads them as images.

OS Open Greenspace, OS Open Rivers, Natural England inventories, and any Sentinel-2 NDVI are inputs to the offline run. They are not fetched when someone opens the map.

## Publishing

`.github/workflows/pages.yml` deploys this folder with GitHub Actions when `main` is pushed. In the repository settings, set Pages to **GitHub Actions**. The site is then `https://domusight.github.io/biodiversity/`.

Basemap tiles are requested from CARTO (light map, © OpenStreetMap contributors © CARTO) and from EOX Sentinel-2 cloudless (satellite, contains modified Copernicus Sentinel data). The index itself is computed in this repository. It is a neighbourhood screen, separate from the Statutory Biodiversity Metric and from species records.

Leaflet 1.9.4 is BSD-2-Clause. Leaflet.MagnifyingGlass is MIT. Both sit in `vendor/` with their licences.
