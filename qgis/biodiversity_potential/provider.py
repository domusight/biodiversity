# SPDX-License-Identifier: GPL-2.0-or-later
"""Processing provider registered by the plugin."""

import os

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

from .algorithm import BiodiversityPotentialAlgorithm


class BiodiversityPotentialProvider(QgsProcessingProvider):
    def id(self):
        return "biodiversitypotential"

    def name(self):
        return "Biodiversity potential"

    def longName(self):
        return self.name()

    def icon(self):
        path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.isfile(path):
            return QIcon(path)
        return super().icon()

    def loadAlgorithms(self):
        self.addAlgorithm(BiodiversityPotentialAlgorithm())
