/* Ground scale of the magnifying glass. The QGIS tool scores a 250 m radius. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.Lens = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  var RADIUS_M = 250;
  var METRES_PER_PIXEL_AT_ZOOM_0 = 156543.03392804097;

  function zoomForRadius(latitude, pixelRadius, radiusM) {
    var radius = radiusM === undefined ? RADIUS_M : radiusM;
    var metresPerPixel = (radius * 2) / (pixelRadius * 2);
    var zoom = Math.log2(
      (METRES_PER_PIXEL_AT_ZOOM_0 * Math.cos(latitude * Math.PI / 180)) / metresPerPixel
    );
    return zoom;
  }

  return {
    RADIUS_M: RADIUS_M,
    zoomForRadius: zoomForRadius
  };
});
