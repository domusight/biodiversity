# Map

A Leaflet map with a [magnifying glass](https://github.com/bbecquet/Leaflet.MagnifyingGlass). The glass follows the pointer and shows biodiversity potential at a closer zoom than the basemap around it. Scroll the wheel to change the scale. The lens stays on the pointer, so the index underneath is what gets larger.

The layer on the page is the synthetic [Riverside Quarter](../examples/riverside_quarter/README.md) example. It is drawn in the English Channel on purpose. London, Birmingham, Manchester and Leeds are camera positions. Their index layers are not in this folder yet. A later layer can be an image overlay with bounds, like the example, or XYZ tiles: add it to the glass in `map.js` the same way `riverside_potential.png` is added, and extend `data/layers.json`.

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

## Publishing

`.github/workflows/pages.yml` deploys this folder with GitHub Actions when `main` is pushed. In the repository settings, set Pages to **GitHub Actions**. The site is then `https://domusight.github.io/biodiversity/`.

Basemap tiles are requested from CARTO (light map, © OpenStreetMap contributors © CARTO) and Esri (satellite). The index itself is computed in this repository. It is a neighbourhood screen, separate from the Statutory Biodiversity Metric and from species records.

Leaflet 1.9.4 is BSD-2-Clause. Leaflet.MagnifyingGlass is MIT. Both sit in `vendor/` with their licences.
