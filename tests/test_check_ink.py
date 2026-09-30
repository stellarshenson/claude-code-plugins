"""Overlap check from the rendered ink (svg_tools/check_ink.py).

The fixture plants one case of each HARD class, two near-misses and clean
cases that must stay silent; the regression corpus is the 12 shipped SVGs on
which the padded-box check reported 182 HARD overlaps (DEF-SVG-81).
ACC-SVG-164..173.
"""

from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from stellars_claude_code_plugins.svg_tools import check_ink
from stellars_claude_code_plugins.svg_tools.check_ink import (
    InkElement,
    candidate_pairs,
    gap,
    inspect,
    write_overlay,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "ink_overlaps.svg"
CORPUS = sorted((ROOT / ".resources" / "svg").glob("0[1-7]_*.svg")) + sorted(
    (ROOT / "plugins" / "svg-infographics" / "examples").glob("0[1-5]_*.svg")
)


@pytest.fixture(scope="module")
def result():
    return inspect(FIXTURE)


def _pairs(findings):
    return {(f.cls, frozenset((f.a.id, f.b.id))) for f in findings}


def _line_of(element_id):
    lines = FIXTURE.read_text().splitlines()
    return next(n for n, text in enumerate(lines, 1) if f'id="{element_id}"' in text)


def test_planted_overlaps_are_hard(result):
    """ACC-SVG-164..167: one finding per planted pair, each HARD."""
    assert _pairs(f for f in result.findings if f.hard) == {
        ("shapes-partly-overlap", frozenset(("fail-badge", "fail-pill"))),
        ("edge-crosses-text", frozenset(("fail-edge-pill", "fail-edge-text"))),
        ("text-on-text", frozenset(("fail-text-a", "fail-text-b"))),
        ("text-straddles-shape", frozenset(("fail-short-box", "fail-long-text"))),
    }


def test_near_misses_are_soft_with_the_gap(result):
    """ACC-SVG-168: text or an arrowhead under 3 px from an edge, not touching."""
    soft = [f for f in result.findings if not f.hard]
    assert _pairs(soft) == {
        ("clearance", frozenset(("near-arrowhead", "near-box"))),
        ("clearance", frozenset(("tight-text", "tight-box"))),
    }
    assert all(0 < f.gap < 3 for f in soft)


def test_clean_cases_are_silent(result):
    """ACC-SVG-169: label in its pill, chip in its card, connectors on their ends."""
    assert len(result.findings) == 6
    assert not [f for f in result.findings if "pass-" in f.a.id + f.b.id]


@pytest.mark.parametrize("svg", CORPUS, ids=[p.name for p in CORPUS])
def test_shipped_graphics_have_no_hard_overlap(svg):
    """ACC-SVG-169, DEF-SVG-81: the padded-box check flagged these 12 files."""
    assert [f.message() for f in inspect(svg).findings if f.hard] == []


def test_finding_names_both_elements_and_the_place(result):
    """ACC-SVG-170: ids, source lines and the overlap box in SVG units."""
    f = next(f for f in result.findings if f.cls == "shapes-partly-overlap")
    message = f.message()
    assert f"rect #fail-badge (line {_line_of('fail-badge')})" in message
    assert f"rect #fail-pill (line {_line_of('fail-pill')})" in message
    assert f.box == pytest.approx((380, 60, 500, 70), abs=1)


def test_overlay_marks_each_finding(result, tmp_path):
    """ACC-SVG-171: magenta boxes for HARD, orange for SOFT."""
    out = write_overlay(result, tmp_path / "overlay.png")
    pixels = np.asarray(Image.open(out))
    magenta = np.all(pixels == (230, 0, 170), axis=-1)
    orange = np.all(pixels == (240, 140, 0), axis=-1)
    assert magenta.sum() > 100 and orange.sum() > 100


def _element(index, box):
    return InkElement(index, 0, "rect", f"e{index}", "", "", "", box, True, True, False, False, [])


def test_collision_tree_returns_only_near_pairs():
    """ACC-SVG-172: boxes 2 units apart pair up, a far box pairs with nothing."""
    elements = [_element(0, (0, 0, 10, 10)), _element(1, (12, 0, 20, 10))]
    elements.append(_element(2, (100, 100, 110, 110)))
    assert candidate_pairs(elements, 3.0) == [(0, 1)]


def test_only_tree_pairs_get_the_exact_test(monkeypatch):
    """ACC-SVG-172: judge runs once per candidate pair and never otherwise."""
    judged = []
    real = check_ink.judge

    def counting(a, b, clearance, to_units):
        judged.append((a.index, b.index))
        return real(a, b, clearance, to_units)

    monkeypatch.setattr(check_ink, "judge", counting)
    run = inspect(FIXTURE)
    assert len(judged) == run.pairs == len(candidate_pairs(run.elements, 3.0))
    assert run.pairs < len(run.elements) * (len(run.elements) - 1) // 2


def test_gap_counts_empty_pixels_between_masks():
    """One empty device column between two masks is half an SVG unit at SCALE 2."""
    a, b = _element(0, (0, 0, 5, 5)), _element(1, (0, 0, 5, 5))
    a.origin, b.origin = (0, 0), (5, 0)
    a.fill = np.zeros((4, 4), bool)
    a.fill[:, 3] = True
    b.fill = np.zeros((4, 4), bool)
    b.fill[:, 0] = True
    assert gap(a, a.fill, b, b.fill, 6)[0] / check_ink.SCALE == 0.5


def test_finalize_reports_ink_findings():
    """ACC-SVG-173: finalize lists the ink findings and no padded-box pair."""
    from stellars_claude_code_plugins.svg_tools.finalize import finalize

    ink = ("[overlaps] shapes-", "[overlaps] edge-", "[overlaps] text-", "[overlaps] clearance")
    hard, soft = finalize(FIXTURE)
    assert len([f for f in hard if f.startswith(ink)]) == 4
    assert len([f for f in soft if f.startswith(ink)]) == 2
    assert not [f for f in hard + soft if "<->" in f]
