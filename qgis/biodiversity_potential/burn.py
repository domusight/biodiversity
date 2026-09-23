# SPDX-License-Identifier: GPL-2.0-or-later
"""Rasterise project vectors onto the analysis grid.

This module is imported only from the QGIS algorithm. The numerical model
never imports it, so the tests can run without QGIS.
"""

import numpy as np
from osgeo import gdal, ogr, osr
from qgis.core import (
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProcessingException,
    QgsRectangle,
    QgsWkbTypes,
)

NODATA = -999


def snap_grid(extent, cell_size):
    """Align an extent to the cell size. Row 0 of the resulting grid is north."""
    if cell_size <= 0:
        raise QgsProcessingException("Cell size must be greater than zero.")
    xmin = np.floor(extent.xMinimum() / cell_size) * cell_size
    xmax = np.ceil(extent.xMaximum() / cell_size) * cell_size
    ymin = np.floor(extent.yMinimum() / cell_size) * cell_size
    ymax = np.ceil(extent.yMaximum() / cell_size) * cell_size
    width = int(round((xmax - xmin) / cell_size))
    height = int(round((ymax - ymin) / cell_size))
    if width < 1 or height < 1:
        raise QgsProcessingException("The area of interest has no area at this cell size.")
    if width * height > 4_000_000:
        raise QgsProcessingException(
            "The grid would be {0} by {1} cells. Use a larger cell size or a smaller area.".format(
                width, height
            )
        )
    return {
        "xmin": float(xmin),
        "ymin": float(ymin),
        "xmax": float(xmax),
        "ymax": float(ymax),
        "width": width,
        "height": height,
        "cell": float(cell_size),
    }


def grid_rectangle(grid):
    return QgsRectangle(grid["xmin"], grid["ymin"], grid["xmax"], grid["ymax"])


def empty_grid(grid):
    return np.full((grid["height"], grid["width"]), NODATA, dtype=np.int16)


def burn_layer(
    layer,
    grid,
    target_crs,
    context,
    code_for_feature,
    feedback,
    label,
    line_buffer_m=0.0,
    all_touched=False,
):
    """Rasterise ``layer`` to integer codes. Unmapped features are counted.

    ``code_for_feature(feature)`` returns ``(code, note)``. ``code`` is an int,
    or None to skip the feature. ``note`` is an optional string collected for
    the log (unrecognised class names).
    """
    if layer is None:
        return empty_grid(grid), []
    if not layer.isValid():
        raise QgsProcessingException("{0} is not a valid layer.".format(label))

    to_target = QgsCoordinateTransform(layer.crs(), target_crs, context.transformContext())
    to_source = QgsCoordinateTransform(target_crs, layer.crs(), context.transformContext())
    source_extent = to_source.transformBoundingBox(grid_rectangle(grid))
    source_extent.grow(grid["cell"] * 2.0)

    _warn_if_extent_is_short(layer, grid, target_crs, context, feedback, label)

    pairs = []
    notes = []
    seen_notes = set()
    feature_count = 0
    request = QgsFeatureRequest().setFilterRect(source_extent)
    for feature in layer.getFeatures(request):
        if feedback.isCanceled():
            raise QgsProcessingException("Cancelled.")
        decided = code_for_feature(feature)
        if decided is None:
            continue
        code, note = decided
        if note and note not in seen_notes:
            seen_notes.add(note)
            notes.append(note)
        if code is None:
            continue
        geometry = _prepared_geometry(feature.geometry(), to_target, line_buffer_m, grid["cell"])
        if geometry is None:
            continue
        pairs.append((_wkb_bytes(geometry), int(code)))
        feature_count += 1

    feedback.pushInfo("{0}: {1} features inside the context window.".format(label, feature_count))
    if feature_count == 0:
        feedback.pushWarning("{0} has no features in the context window.".format(label))
        return empty_grid(grid), notes

    array = _rasterize(pairs, grid, target_crs.toWkt(), all_touched)
    return array, notes


def burn_geometry(geometry, grid, crs_wkt, all_touched=False):
    """Rasterise one geometry already in the grid CRS. Burns the value 1."""
    return _rasterize([(_wkb_bytes(geometry), 1)], grid, crs_wkt, all_touched)


def sample_raster(layer, grid, target_crs):
    """Warp a single-band raster onto the grid. Nodata becomes NaN."""
    if layer is None or not layer.isValid():
        raise QgsProcessingException("The NDVI raster is not valid.")
    source = layer.source().split("|")[0]
    dataset = gdal.Warp(
        "",
        source,
        format="MEM",
        outputBounds=(grid["xmin"], grid["ymin"], grid["xmax"], grid["ymax"]),
        width=grid["width"],
        height=grid["height"],
        resampleAlg=gdal.GRA_Bilinear,
        dstSRS=target_crs.toWkt(),
    )
    if dataset is None:
        raise QgsProcessingException(
            "Could not read the NDVI raster. Use a single-band GeoTIFF of "
            "floating-point NDVI, (NIR - Red) / (NIR + Red)."
        )
    band = dataset.GetRasterBand(1)
    array = band.ReadAsArray().astype(float)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        array[np.isclose(array, nodata)] = np.nan
    dataset = None
    return array


def write_geotiff(path, array, grid, crs_wkt, nodata, descriptions):
    """Write a one-band or multi-band float32 GeoTIFF. Row 0 is north."""
    data = np.asarray(array, dtype=np.float32)
    if data.ndim == 2:
        data = data[np.newaxis, ...]
    bands, height, width = data.shape
    if (height, width) != (grid["height"], grid["width"]):
        raise QgsProcessingException("Output array does not match the analysis grid.")
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(
        path,
        width,
        height,
        bands,
        gdal.GDT_Float32,
        options=["COMPRESS=DEFLATE", "TILED=YES", "PREDICTOR=3"],
    )
    if dataset is None:
        raise QgsProcessingException("Could not create {0}.".format(path))
    dataset.SetGeoTransform((grid["xmin"], grid["cell"], 0.0, grid["ymax"], 0.0, -grid["cell"]))
    dataset.SetProjection(crs_wkt)
    for index in range(bands):
        band = dataset.GetRasterBand(index + 1)
        band.WriteArray(np.where(np.isnan(data[index]), nodata, data[index]))
        band.SetNoDataValue(float(nodata))
        if descriptions and index < len(descriptions):
            band.SetDescription(descriptions[index])
        band.FlushCache()
    dataset.FlushCache()
    dataset = None


def _prepared_geometry(geometry, transform, line_buffer_m, cell_size):
    if geometry is None or geometry.isEmpty():
        return None
    geometry = QgsGeometry(geometry)
    if not geometry.isGeosValid():
        geometry = geometry.makeValid()
    if geometry.isEmpty():
        return None
    try:
        geometry.transform(transform)
    except Exception as error:
        raise QgsProcessingException("Could not reproject a feature: {0}".format(error))
    geometry_type = QgsWkbTypes.geometryType(geometry.wkbType())
    if geometry_type == QgsWkbTypes.PointGeometry:
        return None
    if geometry_type == QgsWkbTypes.LineGeometry:
        radius = max(float(line_buffer_m), float(cell_size) * 0.6)
        geometry = geometry.buffer(radius, 8)
    if geometry is None or geometry.isEmpty():
        return None
    return geometry


def _rasterize(pairs, grid, crs_wkt, all_touched):
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromWkt(crs_wkt)
    spatial_reference.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    memory = ogr.GetDriverByName("Memory").CreateDataSource("burn")
    vector = memory.CreateLayer("burn", spatial_reference, ogr.wkbUnknown)
    field = ogr.FieldDefn("code", ogr.OFTInteger)
    vector.CreateField(field)
    definition = vector.GetLayerDefn()
    for wkb, code in pairs:
        feature = ogr.Feature(definition)
        feature.SetField("code", int(code))
        feature.SetGeometry(ogr.CreateGeometryFromWkb(wkb))
        vector.CreateFeature(feature)
        feature = None

    raster = gdal.GetDriverByName("MEM").Create("", grid["width"], grid["height"], 1, gdal.GDT_Int16)
    raster.SetGeoTransform((grid["xmin"], grid["cell"], 0.0, grid["ymax"], 0.0, -grid["cell"]))
    raster.SetProjection(crs_wkt)
    band = raster.GetRasterBand(1)
    band.Fill(NODATA)
    band.SetNoDataValue(NODATA)
    options = ["ATTRIBUTE=code"]
    if all_touched:
        options.append("ALL_TOUCHED=TRUE")
    result = gdal.RasterizeLayer(raster, [1], vector, options=options)
    if result not in (0, None):
        raise QgsProcessingException("Rasterising a layer failed (GDAL code {0}).".format(result))
    array = band.ReadAsArray()
    raster = None
    memory = None
    return array


def _warn_if_extent_is_short(layer, grid, target_crs, context, feedback, label):
    extent = QgsRectangle(layer.extent())
    if not layer.crs() == target_crs:
        transform = QgsCoordinateTransform(layer.crs(), target_crs, context.transformContext())
        extent = transform.transformBoundingBox(extent)
    if not extent.contains(grid_rectangle(grid)):
        feedback.pushWarning(
            "{0} does not cover the whole context window. Gaps are left unrecorded, "
            "which lowers the score at the edge of the data.".format(label)
        )


def _wkb_bytes(geometry):
    raw = geometry.asWkb()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    data = raw.data()
    return bytes(data)
