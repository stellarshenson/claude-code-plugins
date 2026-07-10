"""Regression tests: a full-canvas background plate is never a card.

The failure this guards against: the connector checker treated the full-canvas
backplate as a card, so every connector endpoint registered as "Npx inside a
card" and flooded edge-snap with HARD false positives (observed as a stale
checker flagging 18 phantom edge-snap findings on a clean five-stage flow).

A backplate is excluded four ways so no fill style slips through: the canonical
``<g id="background">`` layer, an id/class marker, a transparent/none fill, and
full-canvas geometry regardless of fill (a solid or gradient full-bleed banner
plate is still a backplate, not a card).
"""

import xml.etree.ElementTree as ET

from stellars_claude_code_plugins.svg_tools.check_connectors import (
    _is_background_rect,
    _is_card_element,
    check_edge_snap,
    parse_svg,
)


def _rect(**attrs):
    return ET.Element("rect", {k: str(v) for k, v in attrs.items()})


class TestBackplateNotACard:
    def test_transparent_full_canvas_excluded(self):
        el = _rect(x=0, y=0, width=1000, height=360, fill="transparent")
        assert _is_background_rect(el, 1000, 360) is True
        assert _is_card_element(el, 1000, 360) is False

    def test_solid_hex_full_canvas_excluded_by_geometry(self):
        # The legitimate full-bleed banner plate the old fill-only guard missed.
        el = _rect(x=0, y=0, width=1000, height=360, fill="#0e1a2b")
        assert _is_background_rect(el, 1000, 360) is True
        assert _is_card_element(el, 1000, 360) is False

    def test_gradient_full_canvas_excluded_by_geometry(self):
        el = _rect(x=0, y=0, width=1000, height=360, fill="url(#bg)")
        assert _is_background_rect(el, 1000, 360) is True
        assert _is_card_element(el, 1000, 360) is False

    def test_fill_opacity_zero_excluded(self):
        el = _rect(x=0, y=0, width=1000, height=360, fill="#000", **{"fill-opacity": 0})
        assert _is_background_rect(el, 1000, 360) is True

    def test_id_marker_excluded_regardless_of_size(self):
        el = _rect(x=10, y=10, width=200, height=120, fill="#123456", id="backplate")
        assert _is_background_rect(el, 1000, 360) is True

    def test_genuine_card_still_detected(self):
        # No over-exclusion: a real stage box is still a card.
        el = _rect(x=40, y=150, width=170, height=100, fill="#123456")
        assert _is_background_rect(el, 1000, 360) is False
        assert _is_card_element(el, 1000, 360) is True


_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 360">
  <g id="background">
    <rect x="0" y="0" width="1000" height="360" fill="{bg_fill}"/>
  </g>
  <g id="nodes">
    <rect id="card-1" x="40" y="150" width="170" height="100" fill="#123456"/>
    <rect id="card-2" x="790" y="150" width="170" height="100" fill="#123456"/>
  </g>
  <g id="connectors">
    <path d="M 210 200 L 790 200" fill="none" stroke="#fff"/>
  </g>
</svg>"""


class TestEdgeSnapNoBackplateFalsePositives:
    def _run(self, tmp_path, bg_fill):
        svg = tmp_path / "flow.svg"
        svg.write_text(_SVG.format(bg_fill=bg_fill), encoding="utf-8")
        cards, connectors, _labels, _arrows = parse_svg(str(svg))
        return cards, check_edge_snap(connectors, cards)

    def test_transparent_backplate_no_edge_snap(self, tmp_path):
        cards, snaps = self._run(tmp_path, "transparent")
        labels = {c.label for c in cards}
        assert labels == {"card-1", "card-2"}  # backplate excluded
        assert snaps == []  # endpoints sit on real card edges, nothing "inside" the plate

    def test_solid_backplate_no_edge_snap(self, tmp_path):
        cards, snaps = self._run(tmp_path, "#0e1a2b")
        assert {c.label for c in cards} == {"card-1", "card-2"}
        assert snaps == []

    def test_gradient_backplate_no_edge_snap(self, tmp_path):
        cards, snaps = self._run(tmp_path, "url(#bg)")
        assert {c.label for c in cards} == {"card-1", "card-2"}
        assert snaps == []
