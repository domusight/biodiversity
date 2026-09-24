# SPDX-License-Identifier: GPL-2.0-or-later
"""Large-area tool. The public demo does not include this module."""

from qgis.core import QgsGeometry, QgsProcessingException, QgsRectangle

from .algorithm import BiodiversityPotentialAlgorithm, _OUTPUT_NODATA
from .burn import create_geotiff, snap_grid, write_array_window
from .tiles import core_window, plan_cores


class LargeAreaAlgorithm(BiodiversityPotentialAlgorithm):
    """Score a city from its boundary. National layers are read, not pre-clipped."""

    enforces_demo_limit = False
    multiple_ndvi = True

    def createInstance(self):
        return LargeAreaAlgorithm()

    def name(self):
        return "urban_biodiversity_potential_large"

    def displayName(self):
        return self.tr("Urban biodiversity potential (large area) 0.2.5")

    def shortHelpString(self):
        return self.tr(
            "Scores a whole city or district from a boundary polygon, such as "
            "Greater London. Supply the full input layers. The tool reads only "
            "the features that meet the boundary plus the context buffer, so "
            "you do not clip the files yourself. Version 0.2.5 has four NDVI "
            "rows, tile 1 to tile 4. Each row has the same file browser as the "
            "other layers. Add one overlapping Sentinel-2 NDVI raster to each "
            "row. Where the tiles cover the same ground, one value is kept and "
            "the others fill any gaps. Narrow streams are Surface water lines, "
            "OS Open Map Local SurfaceWater_Line. Leave River centrelines empty. "
            "The result is one raster of the boundary. "
            "The public demo is a separate tool and stops at 500 m."
        )

    def processAlgorithm(self, parameters, context, feedback):
        aoi_layer = self.parameterAsVectorLayer(parameters, self.AOI, context)
        if aoi_layer is None:
            raise QgsProcessingException("Choose a boundary polygon.")
        target_crs = aoi_layer.crs()
        self._require_metres(target_crs)

        cell = self.parameterAsDouble(parameters, self.CELL, context)
        neighbourhood = self.parameterAsDouble(parameters, self.NEIGHBOURHOOD, context)
        context_buffer = self.parameterAsDouble(parameters, self.CONTEXT, context)
        if context_buffer < neighbourhood:
            feedback.pushWarning(
                "The context buffer was smaller than the neighbourhood radius, so it was raised to match."
            )
            context_buffer = neighbourhood

        aoi = self._aoi_geometry(aoi_layer, self.parameterAsDouble(parameters, self.RADIUS, context))
        box = aoi.boundingBox()
        full = snap_grid(box, cell, max_cells=None)
        cores = plan_cores(
            full["xmin"], full["ymin"], full["xmax"], full["ymax"],
            cell, context_buffer,
        )
        feedback.pushInfo(
            "Boundary grid {0} by {1} cells at {2:.0f} m, scored in {3} tiles. "
            "Each tile reads inputs only inside that tile plus {4:.0f} m of context.".format(
                full["width"], full["height"], cell, len(cores), context_buffer
            )
        )

        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        dataset = create_geotiff(
            output_path, full, target_crs.toWkt(), _OUTPUT_NODATA,
            "Biodiversity potential (0-100)",
        )
        try:
            for index, core in enumerate(cores, start=1):
                if feedback.isCanceled():
                    raise QgsProcessingException("Cancelled.")
                core_rect = QgsRectangle(core["xmin"], core["ymin"], core["xmax"], core["ymax"])
                if not QgsGeometry.fromRect(core_rect).intersects(aoi):
                    feedback.setProgress(int(100 * index / len(cores)))
                    continue
                analysis = snap_grid(
                    QgsRectangle(
                        core["xmin"] - context_buffer,
                        core["ymin"] - context_buffer,
                        core["xmax"] + context_buffer,
                        core["ymax"] + context_buffer,
                    ),
                    cell,
                )
                feedback.pushInfo(
                    "Tile {0} of {1}.".format(index, len(cores))
                )
                result, _habitat, _mask = self._score_window(
                    parameters, context, feedback, aoi, analysis, target_crs,
                    cell, neighbourhood, allow_empty=True,
                )
                if result is None:
                    feedback.setProgress(int(100 * index / len(cores)))
                    continue
                column, row, width, height = core_window(analysis, core, cell)
                destination_column, destination_row, _width, _height = core_window(full, core, cell)
                write_array_window(
                    dataset,
                    full,
                    result.index[row:row + height, column:column + width],
                    _OUTPUT_NODATA,
                    destination_column,
                    destination_row,
                )
                feedback.setProgress(int(100 * index / len(cores)))
        finally:
            dataset.FlushCache()
            dataset = None

        self._attach_style(output_path, context)
        return {self.OUTPUT: output_path}
