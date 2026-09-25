# SPDX-License-Identifier: GPL-2.0-or-later
"""Biodiversity potential index, and the QGIS plugin entry point."""

__version__ = "0.3.0"


def classFactory(iface):  # QGIS calls this when the plugin loads.
    from .plugin import BiodiversityPotentialPlugin

    return BiodiversityPotentialPlugin(iface)
