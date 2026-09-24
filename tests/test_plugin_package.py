# SPDX-License-Identifier: GPL-2.0-or-later
"""The QGIS modules must at least be valid Python, without importing QGIS."""

import ast
import os
import zipfile
import xml.etree.ElementTree as ET

_PLUGIN = os.path.join(os.path.dirname(__file__), "..", "qgis", "biodiversity_potential")
_ZIP = os.path.join(os.path.dirname(__file__), "..", "qgis", "biodiversity_potential-0.2.1.zip")
_CITY_ZIP = os.path.join(os.path.dirname(__file__), "..", "qgis", "biodiversity_potential-city-0.2.1.zip")


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
    assert keys["version"] == "0.2.1"


def test_install_zip_has_one_plugin_folder():
    with zipfile.ZipFile(_ZIP) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
    assert "biodiversity_potential/metadata.txt" in names
    assert "__pycache__" not in "".join(names)
    tops = {name.split("/")[0] for name in names}
    assert tops == {"biodiversity_potential"}
    assert "biodiversity_potential/large.py" not in names


def test_large_tool_opens_as_itself():
    with zipfile.ZipFile(_CITY_ZIP) as archive:
        source = archive.read("biodiversity_potential/large.py").decode("utf-8")
    assert "def createInstance" in source
    assert "return LargeAreaAlgorithm()" in source


def test_city_zip_adds_the_large_area_tool():
    with zipfile.ZipFile(_CITY_ZIP) as archive:
        names = archive.namelist()
    assert "biodiversity_potential/large.py" in names
    assert "biodiversity_potential/metadata.txt" in names


def test_style_file_is_xml_and_covers_the_index_range():
    path = os.path.join(_PLUGIN, "style", "biodiversity_potential.qml")
    tree = ET.parse(path)
    values = [item.get("value") for item in tree.iter("item")]
    assert "0" in values
    assert "100" in values
