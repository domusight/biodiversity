# SPDX-License-Identifier: GPL-2.0-or-later
"""The QGIS modules must at least be valid Python, without importing QGIS."""

import ast
import os
import xml.etree.ElementTree as ET

_PLUGIN = os.path.join(os.path.dirname(__file__), "..", "qgis", "biodiversity_potential")


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
    assert keys["qgisMinimumVersion"] >= "3.28"


def test_style_file_is_xml_and_covers_the_index_range():
    path = os.path.join(_PLUGIN, "style", "biodiversity_potential.qml")
    tree = ET.parse(path)
    values = [item.get("value") for item in tree.iter("item")]
    assert "0" in values
    assert "100" in values
