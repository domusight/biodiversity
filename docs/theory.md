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

Fahrig (2013) argued that the amount of habitat in a local neighbourhood often explains species richness better than the shape and isolation of individual patches. The neighbourhood here is a circle of 250 m.

That radius is a single scale chosen inside the range where urban insects actually respond, not a dispersal kernel for one species. In one Central European city, flower-rich allotments and cemeteries were beneficial for most wild-bee groups at scales between 200 and 600 m, across radii from 50 to 1,500 m (Weber et al. 2023). 250 m sits inside that band. Mean flights of small solitary bees are about 60–120 m, and those authors suggest keeping flower strips and nesting sites within 150 m (Hofmann, Fleischmann and Renner 2020). Maximum foraging distances of most species run from a few hundred metres upward (Gathmann and Tscharntke 2002; Zurbuchen et al. 2010). Low-mobility garden invertebrates in Basel were related to sealed cover inside 200 m (Braschler et al. 2021). Plants often respond closer to the site than butterflies or birds, which respond further out (Concepción et al. 2015). A 250 m circle sits with the bees and the less mobile invertebrates. It will under-reach birds. The radius is a parameter because of that.

The score is the **mean distinctiveness** of every cell in that circle, not a simple green/not-green fraction. A circle of ancient woodland scores higher than a circle of the same size made of mown grass. Fahrig’s statement was about binary habitat. Weighting by distinctiveness is a deliberate extension, so that a tennis court and a meadow are not treated as the same “green”.

The grid passed to the model must extend at least one neighbourhood beyond the area being reported. Otherwise the cells on the boundary would be averaged with empty space and would look poorer than they are. The QGIS tool buffers the area by a context distance (1 km by default) before it scores, then writes only the original area.

## Connectivity

Isolation is scored as a decay with distance to the nearest **source** cell:

```
0.5 ^ (distance / 250 m)
```

A source is structural habitat, or land the user has marked with a designation layer (SSSI or Local Nature Reserve). At the source the score is 1. At 250 m it is 0.5. At 1 km it is about 0.06, which is why the default context buffer is 1 km: a source just outside a 250 m circle still needs to be visible to the calculation.

This is the shape of the incidence function used in metapopulation ecology (Hanski 1999). The 250 m half-distance is the same neighbourhood as the habitat-amount circle, for the reasons in that section. At four half-distances, 1 km, the function is about 0.06, which is why the context buffer defaults to 1 km. Birds, which respond at larger scales (Concepción et al. 2015), are outside this kernel. The half-distance is a parameter.

An SSSI or Local Nature Reserve is added as a source even where the land-cover layer has called the surface modified grass. Designation boundaries are drawn for a reason, and land cover often misses it. The reverse error also exists: a geological SSSI can include hard standing. The designation does not raise the distinctiveness of those cells. It only marks them as a source, and the log says so.

## Vegetation

Beninde and colleagues ranked vegetation structure just behind area and corridors. Satellites do not see shrub layers and dead wood. They do see a leaf-area signal. NDVI, (near infrared − red) / (near infrared + red), is the standard one (Pettorelli et al. 2005).

The index treats NDVI below 0.2 as no vegetation structure and NDVI of 0.8 or above as saturated. Between those values the score is linear. Carlson and Ripley (1997) scale vegetation cover between a bare-soil NDVI and a dense-canopy NDVI. For Sentinel-2 those ends are taken as 0.2 and 0.8. A byte image stretched to 0–255 is rejected, because it is not an index.

NDVI is a poor description of open water and wetland: clear water is near or below zero even when the habitat is valuable (Pettorelli et al. 2005). Those cells receive a fixed structure score of 0.55 instead of the satellite value. The 0.55 is the middle of the vegetation scale, so water is not read as bare ground. It is not a measured canopy value.

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

Distance to the nearest water or wetland cell decays with a 100 m half-distance. That is shorter than the 250 m terrestrial half-distance on purpose: a pond or a bank is a local effect, and Hill et al. (2017) is about the water body itself, not about a catchment. The 100 m figure is a modelling choice set below the terrestrial neighbourhood. It is not a measured aquatic dispersal distance. A cell of open water or wetland scores 1.

OS Open Map Local draws inland water in two layers. `SurfaceWater_Area` is water wide enough to be a polygon. `SurfaceWater_Line` is the inland water that was not wide enough, which is where the missing streams are. The tool buffers those lines by an assumed width (8 m by default) and thickens them to at least about one cell, so a stream is not lost between the sample points of a 10 m grid. That width is an assumption. The area polygons are painted afterwards, so a river that widens keeps its surveyed shape.

`TidalWater` is the tidal polygon, up to the Normal Tidal Limit.

OS Open Rivers is a connected network, not a map of visible water. Its `fictitious` flag means the link was drawn as a straight line. It does not mean a culvert. The open product has no field that separates a surface stream from a link through a culvert, so those centrelines should be left empty once `SurfaceWater_Line` is used. A centreline whose level or containment says underground, culvert, or tunnel is still left out.

## Heterogeneity

MacArthur and MacArthur (1961) showed that the variety of foliage layers helps explain bird diversity. Tews and colleagues (2004) reviewed the wider pattern: habitat heterogeneity often raises animal diversity, and it does so through keystone structures, not through variety for its own sake. It can also fail for habitat specialists.

The component is Shannon evenness, in Pielou’s form (Pielou 1966), of the functional classes in the neighbourhood (everything of distinctiveness 0.35 or above, plus one class for everything else), divided by the logarithm of the number of classes in the scheme. A pure wood scores 0. A wood with water and scrub scores higher. Sealed land and amenity grass sit in the “everything else” class, so a mosaic of roofs and roads does not look diverse. The 0.35 threshold is the garden score, so a garden counts as habitat structure and a lawn does not (Goddard, Dougill and Benton 2010).

The weight is kept at 0.05 because the effect is real and easy to overstate.

## Interior

Edge effects are well described, and the distance they reach is variable (Ries et al. 2004; Harper et al. 2005). Harper and colleagues found that the depth of edge influence in temperate forest is often on the order of tens of metres, and that it is not one number. The score here is the distance from a habitat cell to the edge of its patch, divided by 30 m and capped at 1. Thirty metres is the short end of that range, chosen because most town woods never develop a deep core. The weight is 0.03. On the example site the difference between the middle of the wood and its edge is a few points on the 0–100 index. The habitat-amount difference at the edge, where the neighbourhood starts to include the park and the streets, is the larger of the two.

## The permeability gate

A weighted sum will let a strong neighbourhood rescue a hostile surface. A sealed cell beside an ancient wood would otherwise outscore a garden in nearby housing, because connectivity and habitat amount would transfer the wood’s context onto the road. McKinney (2002, 2008) treats impervious cover as the consistent negative driver, so the index should do the same.

The four context components — habitat amount, connectivity, water and heterogeneity — are multiplied by a permeability that depends on the surface. McKinney (2002, 2008) supplies the direction of the gate, not the two factors. The factors are set so that a sealed cell cannot overtake a garden: 0.2 leaves a trace of the neighbourhood, and 0.7 discounts modified grass. They are not fitted coefficients.

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
| 5 | Surface water lines, then surface water area, then tidal water | Open water. Lines are the narrow streams. Areas overwrite them where the water is wide enough to be a polygon. Tidal water runs up to the Normal Tidal Limit, which is the Thames through London. |
| 6 | Priority Habitat Inventory | High distinctiveness. Bogs and limestone pavement are treated as irreplaceable. Ponds and lakes become priority water. Names the list does not recognise still score as priority habitat, and the log says so. |
| 7 | Ancient woodland | Very high distinctiveness. Where a county has a revised Ancient Woodland Inventory, that revision should be used for the county. |

SSSI and Local Nature Reserve polygons do not paint a habitat class. They add connectivity sources.

Private gardens are largely absent from these layers. OS Open Greenspace is publicly accessible land. Davies and colleagues (2009) estimated on the order of 430,000 hectares of domestic garden in Britain. If a garden layer is available it can be passed as a keyword overlay (`garden`). Without it, the index will understate the matrix Goddard and colleagues described, and the unrecorded or sealed class will show that gap.

## What the index will not do

It will not produce a species list. It has no records of birds, plants or invertebrates.

It will not replace a field condition assessment. The Statutory Biodiversity Metric’s condition scores, strategic-significance scores and trading rules are a different instrument. The distinctiveness *bands* are used here because they are the public language for habitat quality in England. The rest of that metric is not implemented, and this index must not be entered into a Biodiversity Net Gain calculation.

It will not see a green roof, a garden pond or a veteran tree unless a layer the user supplies contains them. At 10 m, a single tree is smaller than a cell unless the canopy closes it.

Patch area is censored at the edge of the context window. A wood that runs for kilometres outside a 1 km buffer is measured only as far as that buffer. The area is then a lower bound. For a 250 m site and a 1 km buffer this rarely binds. It will bind for a strategic map of a whole district, which is a different job.

The weights are a reading of the literature, shared so they can be argued with. The order follows Beninde, Veith and Hochkirch (2015). The eight numbers are not estimated from a survey. Where a city has one, the advanced weight parameters are there to be changed, and the log records the weights actually used.

## Where each number comes from

A number in the model is either taken from a cited result or set as a modelling choice and said to be one. The equations are in `docs/method.md`.

| Decision | Value | Source |
| --- | --- | --- |
| Cell size | 10 m | Sentinel-2 bands (Drusch et al. 2012) and WorldCover (Zanaga et al. 2022). |
| Neighbourhood radius | 250 m | Flower-rich allotments and cemeteries benefited most wild-bee groups at scales between 200 and 600 m (Weber et al. 2023). Garden invertebrates in Basel were scored inside 200 m (Braschler et al. 2021). Plants respond closer in, and birds further out (Concepción et al. 2015). |
| Connectivity half-distance | 250 m | Same neighbourhood. The decay is Hanski’s incidence function (1999). Mean bee flights are shorter and maxima are longer (Gathmann and Tscharntke 2002; Hofmann, Fleischmann and Renner 2020; Zurbuchen et al. 2010). |
| Context buffer | 1 km | Four connectivity half-distances. The kernel there is about 0.06. |
| Patch-area reference | 50 ha | Beninde, Veith and Hochkirch (2015): area-sensitive urban species were retained above about this size. Used as the saturation point of the curve. |
| Species–area exponent | 0.25 | Preston (1962), in the range reviewed from Arrhenius (1921) and MacArthur and Wilson (1967). |
| Water half-distance | 100 m | Modelling choice, set below the 250 m terrestrial half-distance. Hill et al. (2017) is the reason water is scored. |
| Interior saturation | 30 m | Short end of temperate forest edge depths, which are variable and often tens of metres (Harper et al. 2005; Ries et al. 2004). |
| NDVI bare end | 0.2 | Bare-soil end of the vegetation-fraction scale (Carlson and Ripley 1997), applied to Sentinel-2. |
| NDVI closed-canopy end | 0.8 | Dense-canopy end of that same scale. |
| Water vegetation score | 0.55 | Modelling choice. NDVI on clear water is near or below zero (Pettorelli et al. 2005), so water is given the middle of the vegetation scale. |
| Permeability, sealed | 0.2 | Modelling choice. McKinney (2002, 2008) supplies the direction. The factor keeps a trace and stops a road beside a wood outscoring a garden. |
| Permeability, modified grass | 0.7 | Modelling choice, same gate. |
| Structural habitat | distinctiveness ≥ 0.40 | Above gardens (0.35) and below allotments (0.45), so lawns and property parcels do not form patches (Goddard, Dougill and Benton 2010) and allotments do (Speak, Mizgajski and Borysiak 2015). |
| Heterogeneity classes | distinctiveness ≥ 0.35 | The garden score. A garden counts as structure; amenity grass does not. |
| Distinctiveness bands | 0, 2, 4, 6, 8, divided by 8 | Statutory Biodiversity Metric (Natural England 2023). Gardens and allotments are placed between the low and medium bands (Davies et al. 2009; Goddard, Dougill and Benton 2010; Speak, Mizgajski and Borysiak 2015). Undifferentiated woodland is placed at 0.625, between medium and high, because the open layers do not separate plantation from semi-natural wood. |
| Water-line width | 8 m | Modelling choice, about one cell. `SurfaceWater_Line` has no width. A centreline described as underground, a culvert, or a tunnel is excluded. |
| Component weights | 0.22, 0.18, 0.16, 0.14, 0.14, 0.08, 0.05, 0.03 | Order from Beninde, Veith and Hochkirch (2015). The values are a translation of that order, not a fitted model. |
| Legend breaks | 0.5, 3, 5, 10, 45, 85 | Display bands on a green scale. Each band is one colour. Not quantiles, and not part of the score. |
| Public demo site cap | 500 m from the site centre | A product limit, so the public tool stays a neighbourhood demonstration. It is not an ecological radius. The neighbourhood stays 250 m. |
