# SPDX-License-Identifier: GPL-2.0-or-later
"""QGIS plugin entry point. The numerical model does not import this module."""

from qgis.core import QgsApplication

from .provider import BiodiversityPotentialProvider


class BiodiversityPotentialPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        self.provider = BiodiversityPotentialProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
