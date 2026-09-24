# SPDX-License-Identifier: GPL-2.0-or-later
"""Processing algorithm: urban biodiversity potential for a small area."""

import os
import shutil

import numpy as np
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
    QgsRectangle,
    QgsUnitTypes,
    QgsWkbTypes,
)

from .burn import burn_geometry, burn_layer, sample_rasters, snap_grid, write_geotiff
from .crosswalk import SCHEME_ESA, SCHEME_KEYWORD, SCHEME_PRIORITY, combine_habitat_layers, map_priority_habitat, map_value
from .habitats import Habitat, label
from .limits import DEMO_RADIUS_M, farthest_from_point, within_demo_radius
from .model import COMPONENT_ORDER, Weights, ModelConfig, run_model

_STYLE = os.path.join(os.path.dirname(__file__), "style", "biodiversity_potential.qml")
_OUTPUT_NODATA = -9999.0
_SCHEME_LABELS = [
    "ESA WorldCover class code",
    "Keyword labels",
    "Habitat code or name",
    "OS Open Greenspace function",
    "Priority habitat name",
]
_SCHEME_KEYS = [
    SCHEME_ESA,
    SCHEME_KEYWORD,
    "habitat_code",
    "os_greenspace",
    SCHEME_PRIORITY,
]
_BANDS = (
    (0.0, 15.0, "Low"),
    (15.0, 30.0, "Limited"),
    (30.0, 45.0, "Moderate"),
    (45.0, 65.0, "High"),
    (65.0, 100.01, "Very high"),
)


class _ApplyStyle(QgsProcessingLayerPostProcessorInterface):
    def __init__(self, qml_path):
        super().__init__()
        self._qml_path = qml_path

    def postProcessLayer(self, layer, context, feedback):
        if layer is None or not layer.isValid():
            return
        layer.loadNamedStyle(self._qml_path)
        layer.triggerRepaint()


class BiodiversityPotentialAlgorithm(QgsProcessingAlgorithm):
    enforces_demo_limit = True
    multiple_ndvi = False
    """Score biodiversity potential on a metre grid inside a small area."""

    AOI = "AOI"
    RADIUS = "RADIUS"
    CELL = "CELL"
    NEIGHBOURHOOD = "NEIGHBOURHOOD"
    BASE = "BASE"
    BASE_FIELD = "BASE_FIELD"
    BASE_SCHEME = "BASE_SCHEME"
    GREENSPACE = "GREENSPACE"
    GREENSPACE_FIELD = "GREENSPACE_FIELD"
    OVERLAY = "OVERLAY"
    OVERLAY_FIELD = "OVERLAY_FIELD"
    OVERLAY_SCHEME = "OVERLAY_SCHEME"
    RIVERS = "RIVERS"
    RIVER_WIDTH = "RIVER_WIDTH"
    SURFACE_WATER = "SURFACE_WATER"
    PRIORITY = "PRIORITY"
    PRIORITY_FIELD = "PRIORITY_FIELD"
    ANCIENT = "ANCIENT"
    SSSI = "SSSI"
    LNR = "LNR"
    NDVI = "NDVI"
    OUTPUT = "OUTPUT"
    OUTPUT_COMPONENTS = "OUTPUT_COMPONENTS"
    OUTPUT_CELLS = "OUTPUT_CELLS"
    CONTEXT = "CONTEXT"
    CONNECTIVITY_HALF = "CONNECTIVITY_HALF"
    BLUE_HALF = "BLUE_HALF"
    INTERIOR_M = "INTERIOR_M"
    REFERENCE_HA = "REFERENCE_HA"
    SPECIES_Z = "SPECIES_Z"
    UNRECORDED_AS_SEALED = "UNRECORDED_AS_SEALED"
    USE_SSSI = "USE_SSSI"
    USE_LNR = "USE_LNR"

    def tr(self, text):
        return QCoreApplication.translate("BiodiversityPotential", text)

    def createInstance(self):
        return BiodiversityPotentialAlgorithm()

    def name(self):
        return "urban_biodiversity_potential"

    def displayName(self):
        return self.tr("Urban biodiversity potential")

    def group(self):
        return self.tr("Urban ecology")

    def groupId(self):
        return "urbanecology"

    def shortHelpString(self):
        return self.tr(
            "Scores the biodiversity potential of each 10 m cell in a small area. "
            "This demo accepts a site within 500 m of its centre. "
            "Each cell still looks 250 m around itself. The score is a 0–100 index built from "
            "patch area, local habitat amount, connectivity, vegetation, "
            "distinctiveness, water, heterogeneity and interior habitat.\n\n"
            "It is a screening map for where potential sits. It is not a species "
            "survey, and it is not the Statutory Biodiversity Metric. Give it "
            "British National Grid layers: a wall-to-wall land cover such as ESA "
            "WorldCover, OS Open Greenspace, OS Open Rivers or Zoomstack surface "
            "water, the Priority Habitat Inventory, Ancient Woodland, and an "
            "optional Sentinel-2 NDVI raster. The tool buffers the area itself so "
            "edge cells can see the surrounding landscape; input layers should "
            "cover that wider context.\n\n"
            "The reasoning, equations and data catalogue are in the project documentation: "
            "https://github.com/domusight/biodiversity"
        )

    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.AOI,
                self.tr("Area of interest (polygon, or points to buffer)"),
                types=[QgsProcessing.TypeVectorPolygon, QgsProcessing.TypeVectorPoint],
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RADIUS,
                self.tr("Buffer radius for points (metres)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=250.0,
                minValue=10.0,
                maxValue=DEMO_RADIUS_M,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CELL,
                self.tr("Cell size (metres)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=2.0,
                maxValue=50.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NEIGHBOURHOOD,
                self.tr("Neighbourhood radius (metres)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=250.0,
                minValue=10.0,
                maxValue=DEMO_RADIUS_M,
            )
        )
        self._add_layer(self.BASE, "Base land cover (wall to wall)")
        self._add_field(self.BASE_FIELD, "Base class field", self.BASE)
        self._add_scheme(self.BASE_SCHEME, "Base classification", default=0)
        self._add_layer(self.GREENSPACE, "OS Open Greenspace")
        self._add_field(self.GREENSPACE_FIELD, "Greenspace function field", self.GREENSPACE)
        self._add_layer(self.OVERLAY, "Local habitat overlay (woodland, UKHab, Phase 1)")
        self._add_field(self.OVERLAY_FIELD, "Overlay class field", self.OVERLAY)
        self._add_scheme(self.OVERLAY_SCHEME, "Overlay classification", default=1)
        self._add_layer(self.RIVERS, "River centrelines (OS Open Rivers)")
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RIVER_WIDTH,
                self.tr("Assumed river width (metres)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=8.0,
                minValue=1.0,
            )
        )
        self._add_layer(self.SURFACE_WATER, "Surface water polygons")
        self._add_layer(self.PRIORITY, "Priority Habitat Inventory")
        self._add_field(self.PRIORITY_FIELD, "Priority habitat name field", self.PRIORITY)
        self._add_layer(self.ANCIENT, "Ancient woodland")
        self._add_layer(self.SSSI, "Sites of Special Scientific Interest")
        self._add_layer(self.LNR, "Local Nature Reserves")
        if self.multiple_ndvi:
            self.addParameter(
                QgsProcessingParameterMultipleLayers(
                    self.NDVI,
                    self.tr("Sentinel-2 NDVI tiles (select every overlapping tile)"),
                    layerType=QgsProcessing.TypeRaster,
                    optional=True,
                )
            )
        else:
            self.addParameter(
                QgsProcessingParameterRasterLayer(
                    self.NDVI,
                    self.tr("Sentinel-2 NDVI (optional, floating point, about -1 to 1)"),
                    optional=True,
                )
            )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, self.tr("Biodiversity potential"))
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_COMPONENTS,
                self.tr("Component scores (optional)"),
                optional=True,
                createByDefault=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_CELLS,
                self.tr("Cell polygons (optional, for small areas)"),
                type=QgsProcessing.TypeVectorPolygon,
                optional=True,
                createByDefault=False,
            )
        )
        self._advanced_number(self.CONTEXT, "Context buffer beyond the area (metres)", 1000.0, 0.0)
        self._advanced_number(self.CONNECTIVITY_HALF, "Connectivity half-distance (metres)", 250.0, 10.0)
        self._advanced_number(self.BLUE_HALF, "Water half-distance (metres)", 100.0, 10.0)
        self._advanced_number(self.INTERIOR_M, "Interior saturation distance (metres)", 30.0, 5.0)
        self._advanced_number(self.REFERENCE_HA, "Patch-area reference (hectares)", 50.0, 1.0)
        self._advanced_number(self.SPECIES_Z, "Species-area exponent", 0.25, 0.05)
        self._advanced_bool(self.UNRECORDED_AS_SEALED, "Treat unrecorded land as sealed surface", False)
        self._advanced_bool(self.USE_SSSI, "Treat SSSI land as a connectivity source", True)
        self._advanced_bool(self.USE_LNR, "Treat Local Nature Reserves as a connectivity source", True)
        for key, title, default in (
            ("patch_area", "Weight: patch area", 0.22),
            ("habitat_amount", "Weight: habitat amount", 0.18),
            ("connectivity", "Weight: connectivity", 0.16),
            ("vegetation", "Weight: vegetation", 0.14),
            ("distinctiveness", "Weight: distinctiveness", 0.14),
            ("blue", "Weight: blue infrastructure", 0.08),
            ("heterogeneity", "Weight: heterogeneity", 0.05),
            ("interior", "Weight: interior habitat", 0.03),
        ):
            self._advanced_number("W_" + key.upper(), title, default, 0.0)

    def processAlgorithm(self, parameters, context, feedback):
        aoi_layer = self.parameterAsVectorLayer(parameters, self.AOI, context)
        if aoi_layer is None:
            raise QgsProcessingException("Choose an area of interest.")
        target_crs = aoi_layer.crs()
        self._require_metres(target_crs)

        cell = self.parameterAsDouble(parameters, self.CELL, context)
        neighbourhood = self.parameterAsDouble(parameters, self.NEIGHBOURHOOD, context)
        if self.enforces_demo_limit and neighbourhood > DEMO_RADIUS_M:
            raise QgsProcessingException(self._demo_limit_message(neighbourhood))
        context_buffer = self.parameterAsDouble(parameters, self.CONTEXT, context)
        if context_buffer < neighbourhood:
            feedback.pushWarning(
                "The context buffer was smaller than the neighbourhood radius, so it was raised to match."
            )
            context_buffer = neighbourhood

        radius = self.parameterAsDouble(parameters, self.RADIUS, context)
        if self.enforces_demo_limit and radius > DEMO_RADIUS_M:
            raise QgsProcessingException(self._demo_limit_message(radius))
        aoi = self._aoi_geometry(aoi_layer, radius)
        if self.enforces_demo_limit:
            self._require_demo_extent(aoi)
        buffered = QgsGeometry(aoi).buffer(context_buffer, 24)
        grid = snap_grid(buffered.boundingBox(), cell)
        feedback.pushInfo(
            "Analysis grid {0} by {1} cells at {2:.0f} m. "
            "Only the area of interest is written out; the rest is context.".format(
                grid["width"], grid["height"], cell
            )
        )
        feedback.setProgress(8)

        result, habitat, aoi_mask = self._score_window(
            parameters, context, feedback, aoi, grid, target_crs, cell, neighbourhood
        )
        self._log_summary(feedback, result, habitat, aoi_mask)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        index = result.index.astype(float)
        write_geotiff(
            output_path, index, grid, target_crs.toWkt(), _OUTPUT_NODATA,
            ["Biodiversity potential (0-100)"],
        )
        self._attach_style(output_path, context)
        results = {self.OUTPUT: output_path}

        components_path = self._optional_path(parameters, self.OUTPUT_COMPONENTS, context)
        if components_path:
            stack = []
            for name in COMPONENT_ORDER:
                layer = result.components[name]
                if layer is None:
                    layer = np.full(index.shape, np.nan)
                stack.append(layer)
            write_geotiff(
                components_path,
                np.stack(stack),
                grid,
                target_crs.toWkt(),
                _OUTPUT_NODATA,
                list(COMPONENT_ORDER),
            )
            results[self.OUTPUT_COMPONENTS] = components_path

        cell_id = self._write_cells(
            parameters, context, feedback, grid, target_crs, habitat, result, aoi_mask
        )
        if cell_id is not None:
            results[self.OUTPUT_CELLS] = cell_id

        feedback.setProgress(100)
        return results

    def _score_window(self, parameters, context, feedback, aoi, grid, target_crs, cell, neighbourhood, allow_empty=False):
            layers = []
            notes = []
            base = self.parameterAsVectorLayer(parameters, self.BASE, context)
            if base is not None:
                layers.append(
                    self._burn_classified(
                        base, grid, target_crs, context, feedback,
                        self.BASE_FIELD, self.BASE_SCHEME, parameters, "Base land cover", False,
                    )
                )
            greenspace = self.parameterAsVectorLayer(parameters, self.GREENSPACE, context)
            if greenspace is not None:
                layers.append(
                    self._burn_fixed_scheme(
                        greenspace, grid, target_crs, context, feedback,
                        self.GREENSPACE_FIELD, parameters, "os_greenspace", "OS Open Greenspace", False,
                    )
                )
            overlay = self.parameterAsVectorLayer(parameters, self.OVERLAY, context)
            if overlay is not None:
                layers.append(
                    self._burn_classified(
                        overlay, grid, target_crs, context, feedback,
                        self.OVERLAY_FIELD, self.OVERLAY_SCHEME, parameters, "Habitat overlay", False,
                    )
                )
            water = self.parameterAsVectorLayer(parameters, self.SURFACE_WATER, context)
            if water is not None:
                layers.append(
                    self._burn_constant(
                        water, grid, target_crs, context, feedback,
                        int(Habitat.OPEN_WATER), "Surface water", True, 0.0,
                    )
                )
            rivers = self.parameterAsVectorLayer(parameters, self.RIVERS, context)
            if rivers is not None:
                width = self.parameterAsDouble(parameters, self.RIVER_WIDTH, context)
                layers.append(
                    self._burn_constant(
                        rivers, grid, target_crs, context, feedback,
                        int(Habitat.OPEN_WATER), "Rivers", True, width / 2.0,
                    )
                )
            priority = self.parameterAsVectorLayer(parameters, self.PRIORITY, context)
            if priority is not None:
                layers.append(
                    self._burn_priority(priority, grid, target_crs, context, feedback, parameters)
                )
            ancient = self.parameterAsVectorLayer(parameters, self.ANCIENT, context)
            if ancient is not None:
                layers.append(
                    self._burn_constant(
                        ancient, grid, target_crs, context, feedback,
                        int(Habitat.ANCIENT_WOODLAND), "Ancient woodland", False, 0.0,
                    )
                )
            if not layers:
                raise QgsProcessingException(
                    "Add at least one habitat layer: land cover, greenspace, an overlay, "
                    "water, priority habitat, or ancient woodland."
                )
            feedback.setProgress(35)

            habitat_arrays = []
            for array, layer_notes in layers:
                habitat_arrays.append(array)
                notes.extend(layer_notes)
            for note in notes[:12]:
                feedback.pushWarning(note)
            if len(notes) > 12:
                feedback.pushWarning("{0} further classification notes were omitted.".format(len(notes) - 12))

            habitat = combine_habitat_layers(habitat_arrays)
            if self.parameterAsBool(parameters, self.UNRECORDED_AS_SEALED, context):
                habitat = np.array(habitat, copy=True)
                habitat[habitat == int(Habitat.UNKNOWN)] = int(Habitat.SEALED)
                feedback.pushInfo("Unrecorded cells were reclassed as sealed surface.")

            designation = self._designation_mask(parameters, context, grid, target_crs, feedback)
            aoi_mask = self._mask_from_geometry(aoi, grid, target_crs)
            if not aoi_mask.any():
                if allow_empty:
                    return None, None, None
                raise QgsProcessingException(
                    "No cells fall inside the area of interest. Check the radius and cell size."
                )

            ndvi = sample_rasters(self._ndvi_layers(parameters, context), grid, target_crs)

            weights = self._weights(parameters, context, feedback)
            config = ModelConfig(
                cell_size_m=cell,
                neighbourhood_radius_m=neighbourhood,
                patch_reference_ha=self.parameterAsDouble(parameters, self.REFERENCE_HA, context),
                species_area_z=self.parameterAsDouble(parameters, self.SPECIES_Z, context),
                connectivity_half_distance_m=self.parameterAsDouble(parameters, self.CONNECTIVITY_HALF, context),
                blue_half_distance_m=self.parameterAsDouble(parameters, self.BLUE_HALF, context),
                interior_saturation_m=self.parameterAsDouble(parameters, self.INTERIOR_M, context),
                weights=weights,
            )
            feedback.setProgress(45)
            try:
                result = run_model(
                    habitat,
                    ndvi=ndvi,
                    designation=designation,
                    report_mask=aoi_mask,
                    config=config,
                )
            except ValueError as error:
                raise QgsProcessingException(str(error))
            feedback.setProgress(75)
            return result, habitat, aoi_mask

    def _aoi_geometry(self, layer, radius):
        parts = []
        for feature in layer.getFeatures():
            if feature.hasGeometry() and not feature.geometry().isEmpty():
                parts.append(QgsGeometry(feature.geometry()))
        if not parts:
            raise QgsProcessingException("The area of interest has no geometries.")
        merged = QgsGeometry.unaryUnion(parts)
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            merged = merged.buffer(radius, 32)
        elif layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            raise QgsProcessingException("The area of interest must be points or polygons.")
        if merged is None or merged.isEmpty() or merged.area() <= 0:
            raise QgsProcessingException("The area of interest has no area.")
        return merged

    def _ndvi_layers(self, parameters, context):
        if self.multiple_ndvi:
            return [
                layer for layer in self.parameterAsLayerList(parameters, self.NDVI, context)
                if layer is not None
            ]
        single = self.parameterAsRasterLayer(parameters, self.NDVI, context)
        if single is None:
            return []
        return [single]

    def _require_demo_extent(self, geometry):
        centroid = geometry.centroid().asPoint()
        xs = []
        ys = []
        for vertex in geometry.vertices():
            xs.append(vertex.x())
            ys.append(vertex.y())
        if not within_demo_radius(xs, ys, centroid.x(), centroid.y()):
            reached = farthest_from_point(xs, ys, centroid.x(), centroid.y())
            raise QgsProcessingException(self._demo_limit_message(reached))

    def _demo_limit_message(self, reached_m):
        return (
            "This demo scores a site within {0:.0f} m of its centre. "
            "This one reaches {1:.0f} m. For a city boundary, use "
            "Urban biodiversity potential (large area)."
        ).format(DEMO_RADIUS_M, reached_m)

    def _require_metres(self, crs):
        if not isinstance(crs, QgsCoordinateReferenceSystem) or not crs.isValid():
            raise QgsProcessingException("The area of interest has no coordinate reference system.")
        if crs.mapUnits() != QgsUnitTypes.DistanceMeters:
            raise QgsProcessingException(
                "The area of interest must use a projected CRS in metres, "
                "such as British National Grid (EPSG:27700). A longitude/latitude "
                "layer cannot support a 250 m radius."
            )

    def _burn_classified(self, layer, grid, crs, context, feedback, field_name, scheme_name, parameters, label_text, all_touched):
        field = self._require_field(layer, parameters, field_name, context, label_text)
        scheme = _SCHEME_KEYS[self.parameterAsEnum(parameters, scheme_name, context)]
        return self._burn_with_field(layer, grid, crs, context, feedback, field, scheme, label_text, all_touched, 0.0)

    def _burn_fixed_scheme(self, layer, grid, crs, context, feedback, field_name, parameters, scheme, label_text, all_touched):
        field = self._require_field(layer, parameters, field_name, context, label_text)
        return self._burn_with_field(layer, grid, crs, context, feedback, field, scheme, label_text, all_touched, 0.0)

    def _burn_with_field(self, layer, grid, crs, context, feedback, field, scheme, label_text, all_touched, line_buffer):
        notes = []

        def code_for_feature(feature):
            value = feature[field]
            if scheme == SCHEME_PRIORITY:
                habitat, specific = map_priority_habitat(value)
                if habitat is None:
                    return None, None
                note = None
                if not specific and value not in (None, ""):
                    note = "Priority habitat name '{0}' used the default high-distinctiveness class.".format(value)
                return int(habitat), note
            habitat = map_value(value, scheme)
            if habitat is None:
                if value in (None, ""):
                    return None, None
                return None, "{0}: '{1}' is not in the {2} crosswalk, so those features were left unchanged.".format(
                    label_text, value, scheme
                )
            return int(habitat), None

        array, burn_notes = burn_layer(
            layer, grid, crs, context, code_for_feature, feedback, label_text,
            line_buffer_m=line_buffer, all_touched=all_touched,
        )
        notes.extend(burn_notes)
        return array, notes

    def _burn_priority(self, layer, grid, crs, context, feedback, parameters):
        return self._burn_fixed_scheme(
            layer, grid, crs, context, feedback,
            self.PRIORITY_FIELD, parameters, SCHEME_PRIORITY, "Priority Habitat Inventory", False,
        )

    def _burn_constant(self, layer, grid, crs, context, feedback, code, label_text, all_touched, line_buffer):
        def code_for_feature(_feature):
            return code, None

        return burn_layer(
            layer, grid, crs, context, code_for_feature, feedback, label_text,
            line_buffer_m=line_buffer, all_touched=all_touched,
        )

    def _designation_mask(self, parameters, context, grid, crs, feedback):
        mask = np.zeros((grid["height"], grid["width"]), dtype=bool)
        jobs = []
        if self.parameterAsBool(parameters, self.USE_SSSI, context):
            jobs.append((self.SSSI, "SSSI"))
        if self.parameterAsBool(parameters, self.USE_LNR, context):
            jobs.append((self.LNR, "Local Nature Reserve"))
        for name, label_text in jobs:
            layer = self.parameterAsVectorLayer(parameters, name, context)
            if layer is None:
                continue
            array, _notes = self._burn_constant(
                layer, grid, crs, context, feedback, 1, label_text, True, 0.0
            )
            mask |= array == 1
        if not mask.any():
            return None
        return mask

    def _mask_from_geometry(self, geometry, grid, crs):
        array = burn_geometry(geometry, grid, crs.toWkt(), all_touched=False)
        return array == 1

    def _weights(self, parameters, context, feedback):
        raw = {}
        for key in (
            "patch_area", "habitat_amount", "connectivity", "vegetation",
            "distinctiveness", "blue", "heterogeneity", "interior",
        ):
            raw[key] = self.parameterAsDouble(parameters, "W_" + key.upper(), context)
        weights = Weights(**raw)
        total = weights.total()
        normalised = weights.normalise()
        if abs(total - 1.0) > 1.0e-6:
            feedback.pushInfo("Component weights summed to {0:.3f} and were rescaled to 1.".format(total))
        feedback.pushInfo("Weights: " + ", ".join(
            "{0} {1:.3f}".format(name, value) for name, value in normalised.as_dict().items()
        ))
        return normalised

    def _log_summary(self, feedback, result, habitat, mask):
        scored = result.index[np.isfinite(result.index)]
        feedback.pushInfo(
            "Scored {0} cells. Minimum {1:.1f}, mean {2:.1f}, maximum {3:.1f}.".format(
                scored.size, float(scored.min()), float(scored.mean()), float(scored.max())
            )
        )
        for low, high, name in _BANDS:
            count = int(np.sum((scored >= low) & (scored < high)))
            feedback.pushInfo("  {0}: {1} cells".format(name, count))
        codes, counts = np.unique(habitat[mask], return_counts=True)
        feedback.pushInfo("Habitat inside the area of interest:")
        for code, count in zip(codes, counts):
            feedback.pushInfo("  {0}: {1} cells".format(label(int(code)), int(count)))
        feedback.pushInfo(
            "This is biodiversity potential, not a record of species and not a "
            "Biodiversity Net Gain calculation."
        )

    def _attach_style(self, output_path, context):
        if not os.path.isfile(_STYLE):
            return
        if output_path and not str(output_path).startswith("memory:"):
            sidecar = os.path.splitext(output_path)[0] + ".qml"
            try:
                shutil.copyfile(_STYLE, sidecar)
            except OSError:
                pass
        if context.willLoadLayerOnCompletion(output_path):
            self._style_processor = _ApplyStyle(_STYLE)
            details = context.layerToLoadOnCompletionDetails(output_path)
            details.name = self.tr("Biodiversity potential")
            details.setPostProcessor(self._style_processor)

    def _optional_path(self, parameters, name, context):
        if not _value_set(parameters.get(name)):
            return None
        path = self.parameterAsOutputLayer(parameters, name, context)
        if not path:
            return None
        return path

    def _write_cells(self, parameters, context, feedback, grid, crs, habitat, result, mask):
        if not _value_set(parameters.get(self.OUTPUT_CELLS)):
            return None
        count = int(mask.sum())
        if count > 250_000:
            feedback.pushWarning(
                "Skipping cell polygons: {0} cells is too many. Use the raster, or a coarser cell size.".format(count)
            )
            return None
        fields = QgsFields()
        fields.append(QgsField("potential", QVariant.Double))
        for name in COMPONENT_ORDER:
            fields.append(QgsField(_FIELD_NAMES[name], QVariant.Double))
        fields.append(QgsField("habitat", QVariant.String))
        fields.append(QgsField("hab_code", QVariant.Int))
        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT_CELLS, context, fields, QgsWkbTypes.Polygon, crs
        )
        if sink is None:
            return None
        rows, columns = np.where(mask)
        for index, (row, column) in enumerate(zip(rows, columns)):
            if index % 2000 == 0 and feedback.isCanceled():
                raise QgsProcessingException("Cancelled.")
            feature = QgsFeature(fields)
            xmin = grid["xmin"] + column * grid["cell"]
            ymax = grid["ymax"] - row * grid["cell"]
            feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(
                xmin, ymax - grid["cell"], xmin + grid["cell"], ymax
            )))
            attributes = [float(result.index[row, column])]
            for name in COMPONENT_ORDER:
                layer = result.components[name]
                value = np.nan if layer is None else float(layer[row, column])
                attributes.append(None if np.isnan(value) else round(value, 4))
            attributes.append(label(int(habitat[row, column])))
            attributes.append(int(habitat[row, column]))
            feature.setAttributes(attributes)
            sink.addFeature(feature)
        return dest_id

    def _require_field(self, layer, parameters, name, context, label_text):
        field = self.parameterAsString(parameters, name, context).strip()
        if not field:
            raise QgsProcessingException("Choose the class field for {0}.".format(label_text))
        if layer.fields().lookupField(field) < 0:
            available = ", ".join(layer.fields().names()) or "(none)"
            raise QgsProcessingException(
                "{0} has no field named '{1}'. Fields on that layer: {2}.".format(
                    label_text, field, available
                )
            )
        return field

    def _add_layer(self, name, title):
        self.addParameter(
            QgsProcessingParameterVectorLayer(name, self.tr(title), optional=True)
        )

    def _add_field(self, name, title, parent):
        self.addParameter(
            QgsProcessingParameterField(
                name,
                self.tr(title),
                parentLayerParameterName=parent,
                optional=True,
            )
        )

    def _add_scheme(self, name, title, default):
        self.addParameter(
            QgsProcessingParameterEnum(
                name,
                self.tr(title),
                options=_SCHEME_LABELS,
                defaultValue=default,
                optional=True,
            )
        )

    def _advanced_number(self, name, title, default, minimum):
        parameter = QgsProcessingParameterNumber(
            name,
            self.tr(title),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=default,
            minValue=minimum,
        )
        parameter.setFlags(parameter.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(parameter)

    def _advanced_bool(self, name, title, default):
        parameter = QgsProcessingParameterBoolean(name, self.tr(title), defaultValue=default)
        parameter.setFlags(parameter.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(parameter)


_FIELD_NAMES = {
    "distinctiveness": "distinct",
    "patch_area": "patch",
    "habitat_amount": "hab_amount",
    "connectivity": "connect",
    "vegetation": "vegetation",
    "blue": "blue",
    "heterogeneity": "heterogen",
    "interior": "interior",
}


def _value_set(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True
