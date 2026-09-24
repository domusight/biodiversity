# SPDX-License-Identifier: GPL-2.0-or-later
"""Underground and culverted centrelines are not open water."""

from biodiversity_potential.water import is_hidden_centreline


def test_fictitious_open_rivers_links_are_hidden():
    assert is_hidden_centreline({"fictitious": True, "form": "inlandRiver"})
    assert is_hidden_centreline({"fictitious": "true"})
    assert is_hidden_centreline({"fictitiou": 1})


def test_a_surface_river_is_kept():
    assert not is_hidden_centreline({"fictitious": False, "form": "inlandRiver"})
    assert not is_hidden_centreline({"form": "canal"})


def test_level_and_containment_words_hide_a_line():
    assert is_hidden_centreline({"level": "underground"})
    assert is_hidden_centreline({"physicalcontainment": "In Culvert"})
    assert is_hidden_centreline({"physicallevel": "Below ground"})
    assert not is_hidden_centreline({"level": "on ground"})
