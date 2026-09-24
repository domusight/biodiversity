# Why the map is built this way

The tool answers one question: **in this small piece of town, where does the land offer more biodiversity potential, and where does it offer less?**

It answers with a 0–100 index on a 10 m grid. The default area is a circle of 250 m radius, about 20 hectares. That is the scale of a park, a housing block, or a development site. It is large enough for a wood, a pond and the streets around them to sit in the same view, and small enough that a person can go and look.

The index is a screening layer. A high cell is a place the published urban-ecology literature would expect to matter. A low cell is a place that literature would expect to matter little, until the surface or its surroundings change. The number is not a species count.

## The literature the weights follow

Beninde, Veith and Hochkirch (2015) reviewed studies of biodiversity *inside* cities, across many taxa. The strongest positive effects were **patch area** and **corridors**. **Vegetation structure** came next. Local habitat character mattered more than the broad urban-to-rural gradient. They also reported that sites larger than about **50 hectares** are what it takes to hold on to area-sensitive species.

That ranking is the backbone of the index. The weights are not a regression fitted to those papers. Beninde and colleagues published effect sizes, not a recipe for a map. The weights are an explicit translation of their order into a sum that a planner can inspect and change:

| Component | Weight | What it carries from the literature |
| --- | ---: | --- |
| Patch area | 0.22 | Species–area relationship; the strongest intra-urban effect in Beninde et al. |
| Local habitat amount | 0.18 | Fahrig’s habitat-amount hypothesis; local habitat ahead of a vague landscape label |
| Connectivity | 0.16 | Corridors and isolation, the other strong effect in Beninde et al. |
| Vegetation | 0.14 | Vegetation structure, the next effect in that meta-analysis |
| Distinctiveness | 0.14 | Which habitat the surface actually is, using the UK distinctiveness bands |
| Blue infrastructure | 0.08 | Urban ponds and wetlands, disproportionately rich for their size |
| Heterogeneity | 0.05 | Mixed habitat structure, a real but taxon-dependent effect |
| Interior | 0.03 | Edge depth, kept small because most urban patches are edge |

The eight weights sum to 1. If a Sentinel-2 NDVI raster is not supplied, the vegetation weight is shared across the other seven so the index still sums to 100.

Lepczyk and colleagues (2017) asked the questions a green-space map ought to be able to face: how large is the space, how connected is it, and how varied is the habitat inside it. The components line up with those questions.

## Patch area

The species–area relationship (Arrhenius 1921; the island-biogeography framing of MacArthur and Wilson 1967) says a larger habitat patch holds more species, with a declining slope. Preston’s canonical exponent is often near 0.25. Urban habitat islands sit in a similar range.

A cell that falls in structural habitat takes the area of its whole 8-connected patch. The score is

```
min(1, (area in hectares / 50) ^ 0.25)
```

Fifty hectares is the Beninde threshold, used here as the area where this component **saturates**, not as a claim that a smaller patch is worthless. One hectare still scores about 0.45. The curve is in `docs/method.md`.

Structural habitat starts at distinctiveness 0.40. That includes allotments, scrub, woodland, wetland and water. It excludes sealed land, amenity grassland and private gardens.

Two further rules keep the area honest:

- **Open water is patched on its own.** A river must not glue the woods on either bank into one giant patch.
- **Amenity grassland does not bridge patches.** A mown park is poor habitat for most of the taxa in the urban reviews. Letting lawns join every copse would paint playing fields as large habitat islands. The lawn still counts, at a discount, in habitat amount.

Allotments do form patches. They are mapped as whole sites in OS Open Greenspace, and Speak, Mizgajski and Borysiak (2015) found higher spontaneous plant richness on allotments than in the parks they compared them with.

Gardens do not form patches. A garden polygon usually follows a property boundary. Treating that as a habitat island would make the map describe the cadastre. Goddard, Dougill and Benton (2010) make the more useful point: gardens matter as a **matrix**, collectively, not as a set of little islands. They enter habitat amount and heterogeneity instead.

## Habitat amount

Fahrig (2013) argued that the amount of habitat in a local neighbourhood often explains species richness better than the shape and isolation of individual patches. The neighbourhood here is a circle, 250 m by default, the same radius as the area of interest.

The score is the **mean distinctiveness** of every cell in that circle, not a simple green/not-green fraction. A circle of ancient woodland scores higher than a circle of the same size made of mown grass. Fahrig’s statement was about binary habitat. Weighting by distinctiveness is a deliberate extension, so that a tennis court and a meadow are not treated as the same “green”.

The grid passed to the model must extend at least one neighbourhood beyond the area being reported. Otherwise the cells on the boundary would be averaged with empty space and would look poorer than they are. The QGIS tool buffers the area by a context distance (1 km by default) before it scores, then writes only the original area.

## Connectivity

Isolation is scored as a decay with distance to the nearest **source** cell:

```
0.5 ^ (distance / 250 m)
```

A source is structural habitat, or land the user has marked with a designation layer (SSSI or Local Nature Reserve). At the source the score is 1. At 250 m it is 0.5. At 1 km it is about 0.06, which is why the default context buffer is 1 km: a source just outside a 250 m circle still needs to be visible to the calculation.

This is the shape of the incidence function used in metapopulation ecology (Hanski 1999). The 250 m half-distance is a neighbourhood scale for many urban plants and invertebrates, not a measured dispersal kernel for a named species. Birds move further. The half-distance is an advanced parameter because of that.

An SSSI or Local Nature Reserve is added as a source even where the land-cover layer has called the surface modified grass. Designation boundaries are drawn for a reason, and land cover often misses it. The reverse error also exists: a geological SSSI can include hard standing. The designation does not raise the distinctiveness of those cells. It only marks them as a source, and the log says so.

## Vegetation

Beninde and colleagues ranked vegetation structure just behind area and corridors. Satellites do not see shrub layers and dead wood. They do see a leaf-area signal. NDVI, (near infrared − red) / (near infrared + red), is the standard one (Pettorelli et al. 2005).

The index treats NDVI below 0.2 as no vegetation structure and NDVI of 0.8 or above as saturated. Between those values the score is linear. A byte image stretched to 0–255 is rejected, because it is not an index.

NDVI is a poor description of open water and wetland: clear water is near or below zero even when the habitat is valuable. Those cells receive a fixed structure score of 0.55 instead of the satellite value.

NDVI also cannot tell a rye-grass playing field from a meadow if both are green, and it saturates in closed canopy. Distinctiveness, from the habitat map, is what separates those cases. The two components are both in the sum for that reason.

## Distinctiveness

The surface itself has to count. The bands follow the Statutory Biodiversity Metric used in England: very low 0, low 2, medium 4, high 6, very high 8. Dividing by 8 puts them on 0–1.

| Surface | Score | Reading |
| --- | ---: | --- |
| Sealed, bare, unrecorded | 0 | Very low, or no data |
| Cultivated land, amenity grassland | 0.25 | Low (Metric score 2) |
| Garden | 0.35 | Between low and medium |
| Allotment | 0.45 | Between low and medium, above gardens |
| Scattered trees, scrub, semi-natural grass, open water | 0.50 | Medium (Metric score 4) |
| Woodland of unknown quality | 0.625 | Between medium and high |
| Wetland, priority habitat, priority pond | 0.75 | High (Metric score 6) |
| Ancient woodland, blanket bog, limestone pavement | 1 | Very high (Metric score 8) |

Gardens and allotments are the two departures from the Metric bands. The Metric folds most domestic land into developed land. Urban ecology does not (Davies et al. 2009; Goddard et al. 2010; Speak et al. 2015). The scores sit between the low and medium bands so they can move the index without pretending a garden is a priority habitat.

Undifferentiated woodland, the class produced by ESA WorldCover tree cover or an OS woodland polygon, stays at 0.625. Plantation and semi-natural broadleaf look the same in those layers. Ancient woodland and the Priority Habitat Inventory are what promote a wood to the top of the scale. That stops every urban tree clump from being treated as an irreplaceable habitat.

Unrecorded land scores 0 and is labelled unrecorded. It is a data gap. There is an option to treat it as sealed, for a study where the inputs really do cover every surface. The default is to leave the gap visible.

## Water

Hill and colleagues (2017) compared 240 urban ponds with 782 ponds outside towns and found the urban ponds held a similar richness of aquatic invertebrates, with more varied communities, not a poorer copy of the rural set. A neighbourhood index that ignored water would miss that.

Distance to the nearest water or wetland cell decays with a 100 m half-distance, shorter than the terrestrial half-distance, because the effect of a pond or a river bank is local. A cell of open water or wetland scores 1.

OS Open Rivers is a centreline. The tool buffers it by an assumed width (8 m by default) and thickens it to at least about one cell, so a stream is not lost between the sample points of a 10 m grid. That width is an assumption. Links marked fictitious, or described as underground, a culvert, or a tunnel, are left out. OS Open Map Local `SurfaceWater_Area` and `TidalWater` are the polygons to use.

## Heterogeneity

MacArthur and MacArthur (1961) showed that the variety of foliage layers helps explain bird diversity. Tews and colleagues (2004) reviewed the wider pattern: habitat heterogeneity often raises animal diversity, and it does so through keystone structures, not through variety for its own sake. It can also fail for habitat specialists.

The component is Shannon evenness of the functional classes in the neighbourhood (everything of distinctiveness 0.35 or above, plus one class for everything else), divided by the logarithm of the number of classes in the scheme. A pure wood scores 0. A wood with water and scrub scores higher. Sealed land and amenity grass sit in the “everything else” class, so a mosaic of roofs and roads does not look diverse.

The weight is kept at 0.05 because the effect is real and easy to overstate.

## Interior

Edge effects are well described (Ries et al. 2004). The score is the distance from a habitat cell to the edge of its patch, divided by 30 m and capped at 1. Thirty metres is a short urban edge depth. Most town patches never develop a core, and the component is there so that a large wood can show one. The weight is 0.03. On the example site the difference between the middle of the wood and its edge is a few points on the 0–100 index. The habitat-amount difference at the edge, where the neighbourhood starts to include the park and the streets, is the larger of the two.

## The permeability gate

A weighted sum will let a strong neighbourhood rescue a hostile surface. A sealed cell beside an ancient wood would otherwise outscore a garden in nearby housing, because connectivity and habitat amount would transfer the wood’s context onto the road. McKinney (2002, 2008) treats impervious cover as the consistent negative driver, so the index should do the same.

The four context components — habitat amount, connectivity, water and heterogeneity — are multiplied by a permeability that depends on the surface:

| Surface | Distinctiveness | Permeability |
| --- | --- | --- |
| Sealed, bare, unrecorded | 0 | 0.2 |
| Cultivated land, amenity grassland | 0.25 | 0.7 |
| Garden and everything richer | 0.35 and above | 1 |

A road beside a wood still scores above a road in an estate, because a fifth of the context remains and the map can show where a sealed surface sits in a living neighbourhood. It cannot overtake a garden. Distinctiveness, vegetation, patch area and interior are properties of the surface and are not gated.

The component rasters store the values **after** this gate, so they are the numbers that entered the index.

## What each dataset is doing

The model never sees a file format. It sees a habitat grid, an optional NDVI grid, and an optional designation mask. The QGIS tool builds those from open data. Later layers overwrite earlier ones.

| Order | Dataset | Role |
| --- | --- | --- |
| 1 | Wall-to-wall land cover, often ESA WorldCover | Fills every cell. In towns, WorldCover grassland is read as amenity grass, because the class mixes pasture and lawns. Priority habitat later corrects real meadows. |
| 2 | OS Open Greenspace | Re-labels public parks, allotments, cemeteries and tennis courts. A park is amenity grass until a woodland polygon says otherwise. |
| 3 | Woodland polygons | OS Open Map Local `Woodland`, or any polygon layer of ordinary woods. Ancient woodland still overwrites these. |
| 4 | Local habitat overlay | A Phase 1 or UKHab export, where it is more detailed than the woodland polygons. |
| 5 | Surface water area, then tidal water, then river centrelines | Open water. Surface water is inland. Tidal water runs up to the Normal Tidal Limit, which is the Thames through London. |
| 6 | Priority Habitat Inventory | High distinctiveness. Bogs and limestone pavement are treated as irreplaceable. Ponds and lakes become priority water. Names the list does not recognise still score as priority habitat, and the log says so. |
| 7 | Ancient woodland | Very high distinctiveness. Where a county has a revised Ancient Woodland Inventory, that revision should be used for the county. |

SSSI and Local Nature Reserve polygons do not paint a habitat class. They add connectivity sources.

Private gardens are largely absent from these layers. OS Open Greenspace is publicly accessible land. Davies and colleagues (2009) estimated on the order of 430,000 hectares of domestic garden in Britain. If a garden layer is available it can be passed as a keyword overlay (`garden`). Without it, the index will understate the matrix Goddard and colleagues described, and the unrecorded or sealed class will show that gap.

## What the index will not do

It will not produce a species list. It has no records of birds, plants or invertebrates.

It will not replace a field condition assessment. The Statutory Biodiversity Metric’s condition scores, strategic-significance scores and trading rules are a different instrument. The distinctiveness *bands* are used here because they are the public language for habitat quality in England. The rest of that metric is not implemented, and this index must not be entered into a Biodiversity Net Gain calculation.

It will not see a green roof, a garden pond or a veteran tree unless a layer the user supplies contains them. At 10 m, a single tree is smaller than a cell unless the canopy closes it.

Patch area is censored at the edge of the context window. A wood that runs for kilometres outside a 1 km buffer is measured only as far as that buffer. The area is then a lower bound. For a 250 m site and a 1 km buffer this rarely binds. It will bind for a strategic map of a whole district, which is a different job.

The weights are a reading of the literature, shared so they can be argued with. They are not calibrated to a local survey. Where a city has one, the advanced weight parameters are there to be changed, and the log records the weights actually used.
