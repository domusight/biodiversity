# SPDX-License-Identifier: GPL-2.0-or-later
"""British National Grid to WGS84 for the web map.

This is the transverse Mercator on Airy 1830 followed by the Helmert
datum shift PROJ uses for EPSG:27700 when the OSTN15 grid is not applied
(pipeline: tmerc + helmert position vector, rx=0.15, ry=0.247, rz=0.842,
s=-20.489 ppm). It is a display transform. A surveyed coordinate should
use OSTN15. The worked example lies in the English Channel, outside the
land area of that grid, and this closed-form shift is the one that places
it.
"""

import math

# Airy 1830, as used by PROJ.
_A_AIRY = 6377563.396
_RF_AIRY = 299.3249646
_B_AIRY = _A_AIRY * (1.0 - 1.0 / _RF_AIRY)

# WGS84.
_A_WGS = 6378137.0
_RF_WGS = 298.257223563
_B_WGS = _A_WGS * (1.0 - 1.0 / _RF_WGS)

_F0 = 0.9996012717
_LAT0 = math.radians(49.0)
_LON0 = math.radians(-2.0)
_N0 = -100000.0
_E0 = 400000.0

# OSGB36 -> WGS84, position-vector convention, matching PROJ's EPSG:27700
# ballpark/Helmert pipeline (arc-seconds, parts per million).
_TX, _TY, _TZ = 446.448, -125.157, 542.06
_RX = math.radians(0.15 / 3600.0)
_RY = math.radians(0.247 / 3600.0)
_RZ = math.radians(0.842 / 3600.0)
_S = -20.489e-6


def bng_to_wgs84(easting, northing):
    """Return latitude, longitude in degrees."""
    lat_os, lon_os = _bng_to_osgb36(easting, northing)
    return _osgb36_to_wgs84(lat_os, lon_os)


def wgs84_to_bng(latitude, longitude):
    """Return easting, northing in metres. Inverse of ``bng_to_wgs84``."""
    lat0 = math.radians(latitude)
    lon0 = math.radians(longitude)
    easting = _E0 + (lon0 - _LON0) * _A_AIRY * math.cos(lat0)
    northing = _N0 + (lat0 - _LAT0) * _A_AIRY
    for _ in range(8):
        lat_hat, lon_hat = bng_to_wgs84(easting, northing)
        dlat = latitude - lat_hat
        dlon = longitude - lon_hat
        if abs(dlat) < 1e-11 and abs(dlon) < 1e-11:
            break
        step = 1.0
        lat_e, lon_e = bng_to_wgs84(easting + step, northing)
        lat_n, lon_n = bng_to_wgs84(easting, northing + step)
        j11 = (lat_e - lat_hat) / step
        j21 = (lon_e - lon_hat) / step
        j12 = (lat_n - lat_hat) / step
        j22 = (lon_n - lon_hat) / step
        det = j11 * j22 - j12 * j21
        easting += (dlat * j22 - dlon * j12) / det
        northing += (j11 * dlon - j21 * dlat) / det
    return easting, northing


def _bng_to_osgb36(easting, northing):
    """Inverse transverse Mercator. Returns OSGB36 latitude and longitude in degrees."""
    a = _A_AIRY
    b = _B_AIRY
    e2 = 1.0 - (b * b) / (a * a)
    n = (a - b) / (a + b)
    n2 = n * n
    n3 = n2 * n

    lat = _LAT0
    meridian = 0.0
    for _ in range(30):
        lat = (northing - _N0 - meridian) / (a * _F0) + lat
        dlat = lat - _LAT0
        slat = lat + _LAT0
        meridian = b * _F0 * (
            (1 + n + (5.0 / 4.0) * n2 + (5.0 / 4.0) * n3) * dlat
            - (3 * n + 3 * n2 + (21.0 / 8.0) * n3) * math.sin(dlat) * math.cos(slat)
            + ((15.0 / 8.0) * n2 + (15.0 / 8.0) * n3) * math.sin(2 * dlat) * math.cos(2 * slat)
            - (35.0 / 24.0) * n3 * math.sin(3 * dlat) * math.cos(3 * slat)
        )
        if abs(northing - _N0 - meridian) < 1e-8:
            break

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    nu = a * _F0 / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    rho = a * _F0 * (1.0 - e2) / (1.0 - e2 * sin_lat * sin_lat) ** 1.5
    eta2 = nu / rho - 1.0
    tan_lat = math.tan(lat)
    tan2 = tan_lat * tan_lat
    tan4 = tan2 * tan2
    tan6 = tan4 * tan2
    sec = 1.0 / cos_lat
    nu3 = nu * nu * nu
    nu5 = nu3 * nu * nu
    nu7 = nu5 * nu * nu
    vii = tan_lat / (2 * rho * nu)
    viii = tan_lat / (24 * rho * nu3) * (5 + 3 * tan2 + eta2 - 9 * tan2 * eta2)
    ix = tan_lat / (720 * rho * nu5) * (61 + 90 * tan2 + 45 * tan4)
    x = sec / nu
    xi = sec / (6 * nu3) * (nu / rho + 2 * tan2)
    xii = sec / (120 * nu5) * (5 + 28 * tan2 + 24 * tan4)
    xiia = sec / (5040 * nu7) * (61 + 662 * tan2 + 1320 * tan4 + 720 * tan6)
    de = easting - _E0
    de2 = de * de
    de3 = de2 * de
    de4 = de2 * de2
    de5 = de3 * de2
    de6 = de4 * de2
    de7 = de5 * de2
    lat = lat - vii * de2 + viii * de4 - ix * de6
    lon = _LON0 + x * de - xi * de3 + xii * de5 - xiia * de7
    return math.degrees(lat), math.degrees(lon)


def _osgb36_to_wgs84(latitude, longitude):
    x, y, z = _geodetic_to_ecef(latitude, longitude, _A_AIRY, _B_AIRY)
    x, y, z = _helmert(x, y, z)
    return _ecef_to_geodetic(x, y, z, _A_WGS, _B_WGS)


def _geodetic_to_ecef(latitude, longitude, semi_major, semi_minor):
    lat = math.radians(latitude)
    lon = math.radians(longitude)
    e2 = 1.0 - (semi_minor * semi_minor) / (semi_major * semi_major)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    nu = semi_major / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    return (
        nu * cos_lat * math.cos(lon),
        nu * cos_lat * math.sin(lon),
        nu * (1.0 - e2) * sin_lat,
    )


def _ecef_to_geodetic(x, y, z, semi_major, semi_minor):
    e2 = 1.0 - (semi_minor * semi_minor) / (semi_major * semi_major)
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    lat = math.atan2(z, p * (1.0 - e2))
    for _ in range(10):
        sin_lat = math.sin(lat)
        nu = semi_major / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
        lat = math.atan2(z + e2 * nu * sin_lat, p)
    return math.degrees(lat), math.degrees(lon)


def _helmert(x, y, z):
    scale = 1.0 + _S
    return (
        _TX + scale * (x - _RZ * y + _RY * z),
        _TY + scale * (_RZ * x + y - _RX * z),
        _TZ + scale * (-_RY * x + _RX * y + z),
    )
