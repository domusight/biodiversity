# Riverside Quarter (synthetic)

A made-up urban block, used to show what the index does to a neighbourhood and to lock that behaviour in the tests.

The shapes are invented. They are stored in British National Grid only so the grid has metre units. The origin, easting 440000 and northing 40000, lies in the English Channel south of the Isle of Wight. Do not overlay this file on a street map and read it as a survey.

The reported area is a circle of 250 m radius. The habitat grid extends further, so neighbourhood statistics at the edge of the circle are calculated from real surroundings rather than from empty margin. Cell size is 10 m. There are 1,976 cells inside the circle.

## The place

- An ancient wood of roughly 39 hectares occupies the north-east and continues outside the circle. A wetland clearing sits inside it, and a small pond sits on its southern edge.
- A public park with a copse and a belt of scattered trees lies to the west of the wood. Gardens back onto the wood.
- Allotments sit south of the wood, separate from it by a sealed gap so they remain their own patch.
- A playing field of worn amenity grass (NDVI 0.24) lies south of the park.
- Further south, a small group of gardens sits in otherwise sealed housing, away from the wood and the water.

NDVI is high in the wood (0.88) and the copse (0.80), moderate on allotments (0.64), and low on the playing field and the sealed surface (0.06). Water is slightly negative, and the index does not treat that as a failure of vegetation.

## The map

![Biodiversity potential, 0 to 100](output/preview_potential.png)

Dark green is the ancient wood and the wetland clearing. Mid green is the copse, the allotments, the pond and the tree belt. The park and the near gardens are lighter. The southern housing is pale. The same garden surface is visibly darker where it backs onto the wood than where it sits in the south.

![Habitat classes inside the circle](output/preview_habitat.png)

Grey is sealed. Pale green is amenity grass. Yellow-green is garden. Olive is allotment. The dark mass is ancient woodland, with teal wetland and blue water inside it. The small dark-green block in the park is the copse.

Both images are the 10 m cells enlarged so the pixels stay visible. They are not a smoothed surface.

Open `output/biodiversity_potential.asc` in QGIS for the same grid, styled by `biodiversity_potential.qml`. `output/habitat.asc` is the habitat codes. `output/summary.json` is the table below.

## Scores

Context components are shown after the permeability gate, which is how they enter the index. A sealed cell’s connectivity is a fifth of the distance decay.

| Place | Index | Class | Distinctiveness | Patch area | Habitat amount | Connectivity | Vegetation | Water | Heterogeneity | Interior |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Ancient wood, interior | 87.16 | 85–100 | 1.00 | 0.94 | 0.61 | 1.00 | 1.00 | 0.75 | 0.50 | 1.00 |
| Ancient wood, edge | 83.65 | 45–85 | 1.00 | 0.94 | 0.42 | 1.00 | 1.00 | 0.91 | 0.54 | 0.47 |
| Reedbed clearing | 79.68 | 45–85 | 0.75 | 0.94 | 0.61 | 1.00 | 0.55 | 1.00 | 0.54 | 1.00 |
| Pond | 59.87 | 45–85 | 0.50 | 0.29 | 0.50 | 1.00 | 0.55 | 1.00 | 0.54 | 1.00 |
| Copse in the park | 56.87 | 45–85 | 0.62 | 0.36 | 0.20 | 1.00 | 1.00 | 0.25 | 0.35 | 1.00 |
| Allotments | 55.36 | 45–85 | 0.45 | 0.40 | 0.30 | 1.00 | 0.73 | 0.45 | 0.41 | 1.00 |
| Street trees | 45.46 | 45–85 | 0.50 | 0.29 | 0.11 | 1.00 | 0.70 | 0.15 | 0.20 | 0.67 |
| Garden beside the wood | 40.25 | 10–45 | 0.35 | 0 | 0.47 | 0.90 | 0.33 | 0.66 | 0.54 | 0 |
| Park grassland | 24.74 | 10–45 | 0.25 | 0 | 0.13 | 0.64 | 0.43 | 0.17 | 0.24 | 0 |
| Garden in the south | 19.96 | 10–45 | 0.35 | 0 | 0.06 | 0.50 | 0.33 | 0.11 | 0.08 | 0 |
| Playing field | 16.78 | 10–45 | 0.25 | 0 | 0.12 | 0.46 | 0.07 | 0.19 | 0.24 | 0 |
| Sealed, beside the wood | 5.63 | 5–10 | 0 | 0 | 0.07 | 0.17 | 0 | 0.12 | 0.11 | 0 |
| Sealed, south | 2.56 | 0.5–3 | 0 | 0 | 0.01 | 0.12 | 0 | 0.03 | 0.03 | 0 |

Across the circle the index runs from 2.1 to 90.8, with a mean of 31.1.

A few readings that the tests refuse to let drift:

- The interior of the wood scores above its edge. Both share the same patch (area score 0.94, about 39 ha, under the 50 ha saturation point). The edge is lower because its neighbourhood contains more park and street, and because it is shallower.
- The reedbed shares that patch, which is why its area score matches the wood. It scores lower because its distinctiveness is 0.75 and its vegetation score is the fixed wetland value.
- The copse is a separate patch of about 0.8 ha (area score 0.36). Amenity grass does not join it to the ancient wood.
- The garden beside the wood scores 40. The same garden class in the south scores 20. The surface terms match. The neighbourhood terms do not.
- The sealed cell beside the wood scores 6, below both gardens. Permeability keeps the road from inheriting the wood.

Regenerate the files with `python3 examples/riverside_quarter/build_example.py` from the repository root.
