# Data sources

Everything the tool needs is open, apart from a garden or site survey the user already holds. Layers should be in British National Grid, or in another projected metre CRS that matches the area of interest. The tool reprojects inputs onto the area’s CRS. It will not run a longitude/latitude area, because a radius in degrees is not 250 m.

Clip to a county or a few kilometres around the site if you can. The algorithm only reads features that meet the context window, so a national file works, more slowly.

Absence in these inventories is not evidence that habitat is absent. The Priority Habitat Inventory and the Ancient Woodland Inventory are incomplete relative to the ground, and OS Open Greenspace does not map private gardens.

## Land cover and green space

| Dataset | Use in the tool | Licence and where to get it |
| --- | --- | --- |
| ESA WorldCover 10 m v200 | Base land cover. Class 10 woodland, 20 scrub, 30 amenity grass (an urban reading of the grassland class), 40 cultivated, 50 sealed, 80 water, 90 wetland. | CC BY 4.0. [esa-worldcover.org](https://esa-worldcover.org/). Cite Zanaga et al. (2022), doi:10.5281/zenodo.7254221. |
| OS Open Zoomstack | Woodland and surface water as overlays. Buildings can be a keyword base if you accept that everything else stays unrecorded. | Open Government Licence. [OS Data Hub](https://osdatahub.os.uk/downloads/open/OpenZoomstack). |
| OS Open Greenspace | Public parks, playing fields, allotments, cemeteries, religious grounds, golf courses, play space, sports facilities, tennis courts. Field `function`. | Open Government Licence. [OS Data Hub](https://osdatahub.os.uk/downloads/open/OpenGreenspace). Code list: [FunctionValue](https://docs.os.uk/os-downloads/products/land-and-terrain-portfolio/os-open-greenspace/os-open-greenspace-technical-specification/code-lists/functionvalue). |
| OS Open Rivers | River centrelines. Buffered by the assumed width, default 8 m. | Open Government Licence. [OS Data Hub](https://osdatahub.os.uk/downloads/open/OpenRivers). |
| National Forest Inventory | Optional woodland overlay. Keyword scheme. | Open Government Licence. Forestry Commission / Forestry England open data. |

OS Open Greenspace describes access and function, not botanical quality. A public park becomes amenity grassland. A woodland overlay or the Priority Habitat Inventory has to promote the parts of that park that are actually wood or priority habitat. Tennis courts become sealed. Cemeteries and religious grounds become scattered trees: a moderate score, standing in for the less intensive management and older trees often found there. Golf courses become amenity grassland, which undervalues roughs the product does not separate.

## Designations and priority habitat (England)

| Dataset | Use | Where |
| --- | --- | --- |
| Priority Habitats Inventory (England) | Overwrites with high distinctiveness. Name field is often `Main_Habit`. | [data.gov.uk catalogue](https://www.data.gov.uk/dataset/4b6ddab7-6c0f-4407-946e-d6499f19fcde/priority-habitats-inventory-england). GeoPackage from the Defra Data Services Platform. Open Government Licence. © Natural England. Contains OS data © Crown copyright. |
| Ancient Woodland (England) | Very high distinctiveness. | [data.gov.uk](https://ckan.publishing.service.gov.uk/dataset/ancient-woodland-england). Where a county is in the revised inventory, use the revised polygons for that county. The tool does not choose between them. |
| Sites of Special Scientific Interest (England) | Connectivity source. Does not change the habitat class. | [data.gov.uk](https://www.data.gov.uk/dataset/5b632bd7-9838-4ef2-9101-ea9384421b0d/sites-of-special-scientific-interest-england3). |
| Local Nature Reserves (England) | Optional connectivity source. Quality varies. | Natural England open data, same family of downloads. |

These designation layers cover England. OS OpenData covers Great Britain. A Welsh or Scottish study can use the same model with NRW ancient woodland or NatureScot sites if the class names are mapped, or if the keyword overlay is extended in `crosswalk.py`. The plugin does not ship those crosswalks.

## Satellite vegetation

Sentinel-2 L2A, 10 m bands, growing season, a scene with little cloud. NDVI is

```
(B08 - B04) / (B08 + B04)
```

B08 is near infrared, B04 is red. Write a float32 GeoTIFF. Nodata should be a numeric nodata value, not a colour stretch.

In QGIS, the raster calculator does the same thing. From GDAL:

```
gdal_calc.py -A B08.tif -B B04.tif --outfile=ndvi.tif \
  --calc="(A-B)/(A+B)" --type=Float32 --NoDataValue=-9999 --hideNoData
```

Copernicus Browser is a practical place to pick a scene: [browser.dataspace.copernicus.eu](https://browser.dataspace.copernicus.eu/).

The raster must be true NDVI, roughly −1 to 1. An 8-bit preview will be rejected.

NDVI is optional. Without it, vegetation drops out and the other weights are rescaled. The map is then entirely a reading of the habitat layers and their arrangement.

## What not to expect from the open layers

- Private gardens, green roofs, street trees under a 10 m canopy, and garden ponds are mostly missing.
- WorldCover grassland in a city is treated as modified grass on purpose. Run the Priority Habitat Inventory as well, or semi-natural grassland will be undervalued.
- A wood in Zoomstack or WorldCover is not ancient and is not automatically priority habitat.
- River width is not surveyed. Prefer surface-water polygons where you have them.

Attribute OS data as “Contains OS data © Crown copyright and database right [year]”. Attribute Natural England layers as required on the download page, including the OS acknowledgement those layers carry.
