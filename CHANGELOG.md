# Changelog

## Unreleased

- Leaflet map with a magnifying glass. The glass follows the pointer and shows biodiversity potential at a closer zoom than the basemap. The published layer is the Riverside Quarter example.
- A city in the map manifest can point `tiles` at a public XYZ URL, including a Cloud Storage bucket, and the glass draws that index when the city is selected.
- The online map shows a finished index only. City scores are computed offline and uploaded when the run is complete.

## 0.1.0

- First public version of the urban biodiversity potential index and the QGIS Processing algorithm.
- Eight-component score on a metre grid, default 10 m cells and a 250 m neighbourhood.
- Crosswalks for ESA WorldCover, OS Open Greenspace, keyword habitat labels, and the Priority Habitat Inventory.
- Synthetic Riverside Quarter example, with the rank order pinned by tests.
