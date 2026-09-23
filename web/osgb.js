/* British National Grid (EPSG:27700) <-> WGS84.
   Same Helmert pipeline as web/osgb.py. Display accuracy, not OSTN15. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.OSGB = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  var A_AIRY = 6377563.396;
  var RF_AIRY = 299.3249646;
  var B_AIRY = A_AIRY * (1 - 1 / RF_AIRY);
  var A_WGS = 6378137.0;
  var RF_WGS = 298.257223563;
  var B_WGS = A_WGS * (1 - 1 / RF_WGS);
  var F0 = 0.9996012717;
  var LAT0 = 49 * Math.PI / 180;
  var LON0 = -2 * Math.PI / 180;
  var N0 = -100000;
  var E0 = 400000;
  var TX = 446.448;
  var TY = -125.157;
  var TZ = 542.06;
  var RX = (0.15 / 3600) * Math.PI / 180;
  var RY = (0.247 / 3600) * Math.PI / 180;
  var RZ = (0.842 / 3600) * Math.PI / 180;
  var S = -20.489e-6;

  function bngToOsgb36(easting, northing) {
    var a = A_AIRY;
    var b = B_AIRY;
    var e2 = 1 - (b * b) / (a * a);
    var n = (a - b) / (a + b);
    var n2 = n * n;
    var n3 = n2 * n;
    var lat = LAT0;
    var meridian = 0;
    var i;
    for (i = 0; i < 30; i += 1) {
      lat = (northing - N0 - meridian) / (a * F0) + lat;
      var dlat = lat - LAT0;
      var slat = lat + LAT0;
      meridian = b * F0 * (
        (1 + n + (5 / 4) * n2 + (5 / 4) * n3) * dlat
        - (3 * n + 3 * n2 + (21 / 8) * n3) * Math.sin(dlat) * Math.cos(slat)
        + ((15 / 8) * n2 + (15 / 8) * n3) * Math.sin(2 * dlat) * Math.cos(2 * slat)
        - (35 / 24) * n3 * Math.sin(3 * dlat) * Math.cos(3 * slat)
      );
      if (Math.abs(northing - N0 - meridian) < 1e-8) {
        break;
      }
    }
    var sinLat = Math.sin(lat);
    var cosLat = Math.cos(lat);
    var nu = a * F0 / Math.sqrt(1 - e2 * sinLat * sinLat);
    var rho = a * F0 * (1 - e2) / Math.pow(1 - e2 * sinLat * sinLat, 1.5);
    var eta2 = nu / rho - 1;
    var tanLat = Math.tan(lat);
    var tan2 = tanLat * tanLat;
    var tan4 = tan2 * tan2;
    var tan6 = tan4 * tan2;
    var sec = 1 / cosLat;
    var nu3 = nu * nu * nu;
    var nu5 = nu3 * nu * nu;
    var nu7 = nu5 * nu * nu;
    var vii = tanLat / (2 * rho * nu);
    var viii = tanLat / (24 * rho * nu3) * (5 + 3 * tan2 + eta2 - 9 * tan2 * eta2);
    var ix = tanLat / (720 * rho * nu5) * (61 + 90 * tan2 + 45 * tan4);
    var x = sec / nu;
    var xi = sec / (6 * nu3) * (nu / rho + 2 * tan2);
    var xii = sec / (120 * nu5) * (5 + 28 * tan2 + 24 * tan4);
    var xiia = sec / (5040 * nu7) * (61 + 662 * tan2 + 1320 * tan4 + 720 * tan6);
    var de = easting - E0;
    var de2 = de * de;
    var de3 = de2 * de;
    var de4 = de2 * de2;
    var de5 = de3 * de2;
    var de6 = de4 * de2;
    var de7 = de5 * de2;
    lat = lat - vii * de2 + viii * de4 - ix * de6;
    var lon = LON0 + x * de - xi * de3 + xii * de5 - xiia * de7;
    return [lat * 180 / Math.PI, lon * 180 / Math.PI];
  }

  function geodeticToEcef(latitude, longitude, semiMajor, semiMinor) {
    var lat = latitude * Math.PI / 180;
    var lon = longitude * Math.PI / 180;
    var e2 = 1 - (semiMinor * semiMinor) / (semiMajor * semiMajor);
    var sinLat = Math.sin(lat);
    var cosLat = Math.cos(lat);
    var nu = semiMajor / Math.sqrt(1 - e2 * sinLat * sinLat);
    return [
      nu * cosLat * Math.cos(lon),
      nu * cosLat * Math.sin(lon),
      nu * (1 - e2) * sinLat
    ];
  }

  function ecefToGeodetic(x, y, z, semiMajor, semiMinor) {
    var e2 = 1 - (semiMinor * semiMinor) / (semiMajor * semiMajor);
    var lon = Math.atan2(y, x);
    var p = Math.hypot(x, y);
    var lat = Math.atan2(z, p * (1 - e2));
    var i;
    for (i = 0; i < 10; i += 1) {
      var sinLat = Math.sin(lat);
      var nu = semiMajor / Math.sqrt(1 - e2 * sinLat * sinLat);
      lat = Math.atan2(z + e2 * nu * sinLat, p);
    }
    return [lat * 180 / Math.PI, lon * 180 / Math.PI];
  }

  function helmert(x, y, z) {
    var scale = 1 + S;
    return [
      TX + scale * (x - RZ * y + RY * z),
      TY + scale * (RZ * x + y - RX * z),
      TZ + scale * (-RY * x + RX * y + z)
    ];
  }

  function bngToWgs84(easting, northing) {
    var osgb = bngToOsgb36(easting, northing);
    var ecef = geodeticToEcef(osgb[0], osgb[1], A_AIRY, B_AIRY);
    var shifted = helmert(ecef[0], ecef[1], ecef[2]);
    return ecefToGeodetic(shifted[0], shifted[1], shifted[2], A_WGS, B_WGS);
  }

  function wgs84ToBng(latitude, longitude) {
    var lat0 = latitude * Math.PI / 180;
    var lon0 = longitude * Math.PI / 180;
    var easting = E0 + (lon0 - LON0) * A_AIRY * Math.cos(lat0);
    var northing = N0 + (lat0 - LAT0) * A_AIRY;
    var i;
    for (i = 0; i < 8; i += 1) {
      var hat = bngToWgs84(easting, northing);
      var dlat = latitude - hat[0];
      var dlon = longitude - hat[1];
      if (Math.abs(dlat) < 1e-11 && Math.abs(dlon) < 1e-11) {
        break;
      }
      var step = 1;
      var east = bngToWgs84(easting + step, northing);
      var north = bngToWgs84(easting, northing + step);
      var j11 = (east[0] - hat[0]) / step;
      var j21 = (east[1] - hat[1]) / step;
      var j12 = (north[0] - hat[0]) / step;
      var j22 = (north[1] - hat[1]) / step;
      var det = j11 * j22 - j12 * j21;
      easting += (dlat * j22 - dlon * j12) / det;
      northing += (j11 * dlon - j21 * dlat) / det;
    }
    return [easting, northing];
  }

  return {
    bngToWgs84: bngToWgs84,
    wgs84ToBng: wgs84ToBng
  };
});
