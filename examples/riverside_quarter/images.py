# SPDX-License-Identifier: GPL-2.0-or-later
"""Small PNG writer so the example map can be previewed without extra libraries."""

import struct
import zlib

import numpy as np

from biodiversity_potential.habitats import Habitat

POTENTIAL_STOPS = (
    (0.5, (237, 248, 233)),
    (3.0, (199, 233, 192)),
    (5.0, (161, 217, 155)),
    (10.0, (116, 196, 118)),
    (45.0, (65, 171, 93)),
    (85.0, (35, 139, 69)),
    (100.01, (0, 90, 50)),
)

HABITAT_COLORS = {
    Habitat.UNKNOWN: (217, 217, 217),
    Habitat.SEALED: (186, 186, 186),
    Habitat.BARE: (200, 184, 154),
    Habitat.CROP: (230, 211, 106),
    Habitat.AMENITY_GRASS: (197, 224, 155),
    Habitat.GARDEN: (143, 191, 106),
    Habitat.ALLOTMENT: (110, 160, 46),
    Habitat.SCATTERED_TREES: (62, 140, 74),
    Habitat.SCRUB: (107, 143, 113),
    Habitat.SEMI_NATURAL_GRASS: (125, 207, 106),
    Habitat.OPEN_WATER: (76, 120, 200),
    Habitat.WOODLAND: (46, 122, 72),
    Habitat.WETLAND: (58, 160, 160),
    Habitat.PRIORITY_HABITAT: (14, 122, 74),
    Habitat.ANCIENT_WOODLAND: (12, 59, 46),
    Habitat.PRIORITY_WATER: (29, 78, 137),
    Habitat.IRREPLACEABLE: (8, 48, 38),
}


def write_png(path, rgb):
    """Write an 8-bit RGB or RGBA image.

    ``rgb`` is a uint8 array of shape (height, width, 3) or (height, width, 4).
    Row 0 is the top of the file.
    """
    rgb = np.asarray(rgb, dtype=np.uint8)
    height, width, channels = rgb.shape
    if channels not in (3, 4):
        raise ValueError("Expected an RGB or RGBA image.")
    color_type = 2 if channels == 3 else 6
    raw = b"".join(b"\x00" + rgb[row].tobytes() for row in range(height))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as handle:
        handle.write(png)


def potential_rgb(index, mask, scale=8):
    """Colour the area-of-interest circle. Cells outside it are white."""
    colours = np.full(index.shape + (3,), 255, dtype=np.uint8)
    finite = np.isfinite(index) & mask
    flat = index[finite]
    painted = np.zeros((flat.size, 3), dtype=np.uint8)
    for value, colour in POTENTIAL_STOPS:
        painted[flat < value] = colour
        flat = np.where(flat < value, np.inf, flat)
    colours[finite] = painted
    cropped, _bounds = _crop_to_mask(colours, mask, pad=1)
    return _zoom(cropped, scale)


def habitat_rgb(habitat, mask, scale=6):
    """Colour habitat classes inside the area of interest."""
    colours = np.full(habitat.shape + (3,), 255, dtype=np.uint8)
    for code, colour in HABITAT_COLORS.items():
        colours[(habitat == int(code)) & mask] = colour
    cropped, _bounds = _crop_to_mask(colours, mask, pad=1)
    return _zoom(cropped, scale)


def write_icon(path):
    """A 64 px mark: a neighbourhood circle, darker where potential is higher."""
    size = 64
    image = np.full((size, size, 3), (244, 241, 234), dtype=np.uint8)
    centre = (size - 1) / 2.0
    radius = 26.0
    yy, xx = np.mgrid[0:size, 0:size]
    distance = np.hypot(xx - centre, yy - centre)
    inside = distance <= radius
    # A simple field, high toward the upper right, so the icon reads as a map.
    field = np.clip((xx + (size - yy)) / (2 * size), 0, 1)
    for channel in range(3):
        stops_y = [stop[1][channel] for stop in POTENTIAL_STOPS]
        image[:, :, channel] = np.where(
            inside,
            np.interp(field * 100.0, [stop[0] for stop in POTENTIAL_STOPS], stops_y),
            image[:, :, channel],
        ).astype(np.uint8)
    ring = (distance <= radius) & (distance >= radius - 1.5)
    image[ring] = (12, 59, 46)
    write_png(path, image)


def _crop_to_mask(colours, mask, pad):
    rows, columns = np.where(mask)
    row0 = max(0, int(rows.min()) - pad)
    row1 = min(colours.shape[0], int(rows.max()) + pad + 1)
    column0 = max(0, int(columns.min()) - pad)
    column1 = min(colours.shape[1], int(columns.max()) + pad + 1)
    return colours[row0:row1, column0:column1], (row0, row1, column0, column1)


def _zoom(image, factor):
    if factor == 1:
        return image
    return np.repeat(np.repeat(image, factor, axis=0), factor, axis=1)
