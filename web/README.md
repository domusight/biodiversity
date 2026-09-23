# Map

A Leaflet map with a [magnifying glass](https://github.com/bbecquet/Leaflet.MagnifyingGlass). The glass follows the pointer and shows biodiversity potential at a closer zoom than the basemap around it. Scroll the wheel to change the scale. The lens stays on the pointer, so the index underneath is what gets larger.

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

The HTML stays in this repository. The city rasters are too large to commit, so they belong in a Cloud Storage bucket with public read on the tile objects. No API key goes in the page. The light map and the Sentinel-2 cloudless basemap stay on their own servers.

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

Choosing the city then puts those tiles in the magnifying glass. Rebuilding the example keeps a `tiles` URL that is already in the file. The bucket can use uniform access and grant `allUsers` the Storage Object Viewer role on the tile objects. The glass loads them as images.

Sentinel-2 NDVI for those cities can be built in Earth Engine on the same Google account. OS Open Greenspace, OS Open Rivers, and the Natural England inventories still come from their own downloads.

## Publishing

`.github/workflows/pages.yml` deploys this folder with GitHub Actions when `main` is pushed. In the repository settings, set Pages to **GitHub Actions**. The site is then `https://domusight.github.io/biodiversity/`.

Basemap tiles are requested from CARTO (light map, © OpenStreetMap contributors © CARTO) and from EOX Sentinel-2 cloudless (satellite, contains modified Copernicus Sentinel data). The index itself is computed in this repository. It is a neighbourhood screen, separate from the Statutory Biodiversity Metric and from species records.

Leaflet 1.9.4 is BSD-2-Clause. Leaflet.MagnifyingGlass is MIT. Both sit in `vendor/` with their licences.
