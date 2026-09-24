# SPDX-License-Identifier: GPL-2.0-or-later
"""Only centrelines described as underground are left out of open water."""

from biodiversity_potential.water import is_fictitious_geometry, is_hidden_centreline


def test_a_straight_open_rivers_link_is_kept():
    # fictitious means a straight-line geometry, not a culvert.
    assert is_fictitious_geometry({"fictitious": True, "form": "inlandRiver"})
    assert not is_hidden_centreline({"fictitious": True, "form": "inlandRiver"})
    assert not is_hidden_centreline({"fictitious": "true"})
    assert not is_hidden_centreline({"fictitiou": 1})


def test_a_surface_river_is_kept():
    assert not is_hidden_centreline({"fictitious": False, "form": "inlandRiver"})
    assert not is_fictitious_geometry({"fictitious": False})
    assert not is_hidden_centreline({"form": "canal"})


def test_level_and_containment_words_hide_a_line():
    assert is_hidden_centreline({"level": "underground"})
    assert is_hidden_centreline({"physicalcontainment": "In Culvert"})
    assert is_hidden_centreline({"physicallevel": "Below ground"})
    assert not is_hidden_centreline({"level": "on ground"})
