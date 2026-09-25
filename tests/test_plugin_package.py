# SPDX-License-Identifier: GPL-2.0-or-later
"""The QGIS modules must at least be valid Python, without importing QGIS."""

import ast
import os
import zipfile
import xml.etree.ElementTree as ET

_PLUGIN = os.path.join(os.path.dirname(__file__), "..", "qgis", "biodiversity_potential")
_ZIP = os.path.join(os.path.dirname(__file__), "..", "qgis", "biodiversity_potential-0.3.1.zip")


def test_plugin_sources_parse():
    found = False
    for name in os.listdir(_PLUGIN):
        if not name.endswith(".py"):
            continue
        found = True
        path = os.path.join(_PLUGIN, name)
        with open(path, encoding="utf-8") as handle:
            ast.parse(handle.read(), filename=path)
    assert found


def test_metadata_has_the_processing_provider_flag():
    keys = {}
    path = os.path.join(_PLUGIN, "metadata.txt")
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if "=" in line and not line.startswith("["):
                key, value = line.split("=", 1)
                keys[key.strip()] = value.strip()
    for required in (
        "name",
        "qgisMinimumVersion",
        "description",
        "version",
        "author",
        "hasProcessingProvider",
    ):
        assert keys.get(required)
    assert keys["hasProcessingProvider"] == "yes"
    assert keys["version"] == "0.3.1"


def test_install_zip_is_one_tool():
    with zipfile.ZipFile(_ZIP) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        algorithm = archive.read("biodiversity_potential/algorithm.py").decode("utf-8")
        provider = archive.read("biodiversity_potential/provider.py").decode("utf-8")
    assert "biodiversity_potential/metadata.txt" in names
    assert "__pycache__" not in "".join(names)
    tops = {name.split("/")[0] for name in names}
    assert tops == {"biodiversity_potential"}
    assert "biodiversity_potential/large.py" not in names
    assert "biodiversity_potential/water.py" not in names
    assert "biodiversity_potential/limits.py" not in names
    assert "def createInstance" in algorithm
    assert "return BiodiversityPotentialAlgorithm()" in algorithm
    assert 'return self.tr("Urban biodiversity potential {0}".format(__version__))' in algorithm
    assert "https://github.com/domusight/biodiversity/blob/main/docs/user-guide.md" in algorithm
    assert "def helpUrl" in algorithm
    assert "LargeAreaAlgorithm" not in provider
    assert "addAlgorithm(BiodiversityPotentialAlgorithm())" in provider


def test_style_file_is_xml_and_covers_the_index_range():
    path = os.path.join(_PLUGIN, "style", "biodiversity_potential.qml")
    tree = ET.parse(path)
    values = [item.get("value") for item in tree.iter("item")]
    assert "0.5" in values
    assert "100" in values
