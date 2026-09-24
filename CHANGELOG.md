# Changelog

## Unreleased

- Version 0.2.1. Opening the large-area tool no longer shows the 500 m demo dialog. The toolbox name is **Urban biodiversity potential (large area) 0.2.1**.

- Version 0.2.0. The large-area tool is named **Urban biodiversity potential (large area) 0.2.0** and has four NDVI file rows, tile 1 to tile 4. The install file is `qgis/biodiversity_potential-city-0.2.0.zip`.

- The QGIS demo refuses a site that extends more than 500 m from its centre. The neighbourhood stays 250 m.
- `qgis/biodiversity_potential-city-0.1.0.zip` adds a large-area tool. Give it a boundary such as Greater London and the full input layers. It clips to that boundary itself.
- The large-area tool accepts several overlapping Sentinel-2 NDVI tiles and mosaics them.
- Leaflet map with a magnifying glass. The glass follows the pointer and shows biodiversity potential at a closer zoom than the basemap. The published layer is the Riverside Quarter example.
- A city in the map manifest can point `tiles` at a public XYZ URL, including a Cloud Storage bucket, and the glass draws that index when the city is selected.
- The online map shows a finished index only. City scores are computed offline and uploaded when the run is complete.
- The magnifying glass is fixed to a 250 m radius, the same circle the QGIS tool scores. The repository is the tool; the page is the precomputed view.
- `qgis/biodiversity_potential-0.1.0.zip` is the file for QGIS **Install from ZIP**.

## 0.1.0

- First public version of the urban biodiversity potential index and the QGIS Processing algorithm.
- Eight-component score on a metre grid, default 10 m cells and a 250 m neighbourhood.
- Crosswalks for ESA WorldCover, OS Open Greenspace, keyword habitat labels, and the Priority Habitat Inventory.
- Synthetic Riverside Quarter example, with the rank order pinned by tests.
