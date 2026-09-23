# Method

The implementation is `qgis/biodiversity_potential/model.py` and `components.py`. This note is the same calculation in words. If the two disagree, the code and the tests are the source of record.

## Grid

- Projected coordinates in metres. For England, British National Grid (EPSG:27700).
- Cell size 10 m by default.
- The reported area is the polygon supplied, or a buffer around points. The default point buffer is 250 m.
- The calculated grid is that area expanded by the context buffer, at least the neighbourhood radius and 1 km by default.
- Row 0 is north.

Only cells inside the reported area are written. Cells outside it are used as context and then set to nodata.

## Habitat surface

Integer habitat codes are defined in `habitats.py`. Layers are combined in the order in `docs/theory.md`. A cell below zero in a layer is nodata and does not overwrite.

Distinctiveness `D` is looked up from the code. Structural habitat is `D ≥ 0.40`, excluding open water from the terrestrial patch layer. Open water and priority water form their own patches.

## Components

Each component is on 0–1.

**Distinctiveness.** `D` as tabulated in `docs/theory.md`.

**Patch area.** Let `A` be the area in hectares of the 8-connected patch containing the cell, or 0 if the cell is not structural habitat.

```
P = 0                         if A = 0
P = min(1, (A / 50) ^ 0.25)   otherwise
```

`50` and `0.25` are parameters (`patch reference` and `species-area exponent`).

**Habitat amount.** Mean of `D` inside a circle of radius `R` (default 250 m). Cells beyond the array are treated as zero, which is why the reported area must sit a full radius inside the array.

**Connectivity.** Euclidean distance `d` in metres to the nearest source cell. Sources are structural habitat, plus SSSI and Local Nature Reserve cells when those options are on.

```
C_raw = 0.5 ^ (d / 250)
```

**Vegetation.** From NDVI `N`, if a raster was supplied:

```
V = 0                      if N ≤ 0.2
V = 1                      if N ≥ 0.8
V = (N - 0.2) / 0.6        otherwise
```

Open water, priority water and wetland use `V = 0.55` instead. Missing NDVI pixels are omitted for that cell and the weights are rescaled. If there is no NDVI raster at all, the vegetation weight is removed and the remaining weights are rescaled once.

Values outside about −1.5 to 1.5 raise an error. The usual cause is an 8-bit image.

**Blue infrastructure.** Distance `w` to the nearest water or wetland cell.

```
B_raw = 0.5 ^ (w / 100)
```

**Heterogeneity.** In the same circle, let `p_k` be the share of each functional class (`D ≥ 0.35`) and let one further class hold every other cell. With `S` the number of those classes including the remainder,

```
H = − Σ p_k ln p_k
E_raw = H / ln S
```

A single class gives 0.

**Interior.** For a cell in a patch, depth in metres to the nearest cell outside that patch (terrestrial and water patches measured separately):

```
I = min(1, depth / 30)
```

Cells that are not structural habitat score 0.

## Permeability gate

Context components are multiplied by a surface factor `g` before they are weighted.

```
g = 0.2    if D = 0
g = 0.7    if 0 < D < 0.35
g = 1      if D ≥ 0.35
```

```
habitat amount  = (mean D) × g
connectivity    = C_raw × g
blue            = B_raw × g
heterogeneity   = E_raw × g
```

## Index

```
score = 100 × Σ (weight_k × component_k) / Σ weight_k
```

The default weights are 0.22, 0.18, 0.16, 0.14, 0.14, 0.08, 0.05, 0.03 in the order patch area, habitat amount, connectivity, vegetation, distinctiveness, blue, heterogeneity, interior. They sum to 1. Any other set is rescaled to 1 and the rescaling is written to the log.

The denominator drops a component only when its weight is zero or, for vegetation, when the value is missing.

## Legend

The colour ramp is fixed, so two places can be compared. The breaks are round numbers on the 0–100 index, not quantiles of one site.

| Index | Class |
| --- | --- |
| 0–15 | Low |
| 15–30 | Limited |
| 30–45 | Moderate |
| 45–65 | High |
| 65–100 | Very high |

On the synthetic example these breaks separate sealed streets, amenity grassland, gardens, allotments and the ancient wood. A site with no semi-natural habitat will sit in the lower classes. That is the finding, not a reason to stretch the ramp.

## Outputs

- **Biodiversity potential.** One-band float32 GeoTIFF, 0–100, nodata −9999, with the style file applied.
- **Component scores.** Optional eight-band GeoTIFF, bands in the component order above, each 0–1 after the permeability gate.
- **Cell polygons.** Optional, for a small area. Attribute `potential` plus the components and the habitat name. Above 250,000 cells the tool keeps the raster and skips the polygons.

## Worked checks

On the synthetic Riverside Quarter site (`examples/riverside_quarter`):

- The ancient-woodland patch scores 0.94 for area. That is `(about 39 ha / 50) ^ 0.25`. The reference of 50 ha is not reached, so the component has not saturated.
- The copse is about 0.8 ha and scores 0.36.
- A garden against the wood scores 40. The same garden class in the southern housing scores 20.
- A sealed cell against the wood scores 6. A sealed cell in the south scores 3. Both stay below the gardens.
- Reversing any of those inequalities fails `tests/test_riverside.py`.
