# SPDX-License-Identifier: GPL-2.0-or-later
"""Split a large extent into cores that fit in memory, each with context."""

import math


def plan_cores(xmin, ymin, xmax, ymax, cell, context_m, max_cells=1_500_000):
    """Return core rectangles aligned to ``cell``.

    Each core, expanded by ``context_m`` on every side, stays within
    ``max_cells``. The cores cover ``xmin, ymin, xmax, ymax`` without overlap.
    """
    if cell <= 0:
        raise ValueError("Cell size must be greater than zero.")
    if xmax <= xmin or ymax <= ymin:
        raise ValueError("The area has no extent.")
    context_cells = int(math.ceil(float(context_m) / float(cell)))
    side = int(math.floor(math.sqrt(max_cells))) - (2 * context_cells)
    if side < 1:
        raise ValueError("The context buffer is too large for one tile.")
    step = side * float(cell)
    cores = []
    x_coord = float(xmin)
    while x_coord < float(xmax) - 1e-6:
        y_coord = float(ymin)
        core_width = min(step, float(xmax) - x_coord)
        while y_coord < float(ymax) - 1e-6:
            core_height = min(step, float(ymax) - y_coord)
            cores.append({
                "xmin": x_coord,
                "ymin": y_coord,
                "xmax": x_coord + core_width,
                "ymax": y_coord + core_height,
            })
            y_coord += core_height
        x_coord += core_width
    return cores


def core_window(grid, core, cell):
    """Pixel column, row, width and height of ``core`` inside ``grid``.

    Row 0 is the north edge of ``grid``.
    """
    column = int(round((core["xmin"] - grid["xmin"]) / cell))
    row = int(round((grid["ymax"] - core["ymax"]) / cell))
    width = int(round((core["xmax"] - core["xmin"]) / cell))
    height = int(round((core["ymax"] - core["ymin"]) / cell))
    return column, row, width, height
