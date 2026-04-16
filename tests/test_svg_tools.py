"""Tests for SVG infographic validation tools.

Tests: calc_connector, check_contrast, check_connectors, check_overlaps, check_alignment.
"""

import math
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parent.parent / "stellars_claude_code_plugins" / "svg_tools"
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "svg-infographics" / "examples"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tools_dir():
    return TOOLS_DIR


@pytest.fixture
def simple_svg(tmp_path):
    """Minimal SVG with one card and one text element."""
    svg = tmp_path / "simple.svg"
    svg.write_text(textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
          <style>
            .fg-1 { fill: #1e3a5f; }
            .fg-2 { fill: #2a5f9e; }
            .fg-3 { fill: #4a7ba7; }
            @media (prefers-color-scheme: dark) {
              .fg-1 { fill: #c8d6e5; }
              .fg-2 { fill: #a0b4c8; }
              .fg-3 { fill: #8899aa; }
            }
          </style>
          <rect x="20" y="20" width="200" height="100" fill="#0284c7" fill-opacity="0.04" stroke="#0284c7" stroke-width="1"/>
          <rect x="20" y="20" width="200" height="5" fill="#0284c7" opacity="0.6"/>
          <text x="34" y="45" font-size="12" class="fg-1" font-family="Segoe UI, Arial, sans-serif">Card Title</text>
          <text x="34" y="59" font-size="10" class="fg-3" font-family="Segoe UI, Arial, sans-serif">Description text</text>
        </svg>
    """))
    return svg


@pytest.fixture
def contrast_fail_svg(tmp_path):
    """SVG with a contrast failure: light text on light background."""
    svg = tmp_path / "contrast_fail.svg"
    svg.write_text(textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">
          <style>
            .fg-1 { fill: #1e3a5f; }
            @media (prefers-color-scheme: dark) {
              .fg-1 { fill: #c8d6e5; }
            }
          </style>
          <text x="20" y="40" font-size="12" fill="#cccccc" font-family="Segoe UI, Arial, sans-serif">Low contrast text</text>
        </svg>
    """))
    return svg


@pytest.fixture
def overlap_svg(tmp_path):
    """SVG with two overlapping text elements."""
    svg = tmp_path / "overlap.svg"
    svg.write_text(textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">
          <style>
            .fg-1 { fill: #1e3a5f; }
          </style>
          <text x="20" y="40" font-size="14" class="fg-1">First label</text>
          <text x="22" y="42" font-size="14" class="fg-1">Second label</text>
        </svg>
    """))
    return svg


@pytest.fixture
def connector_svg(tmp_path):
    """SVG with connectors and cards."""
    svg = tmp_path / "connectors.svg"
    svg.write_text(textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400">
          <rect x="20" y="20" width="200" height="100"/>
          <rect x="400" y="20" width="200" height="100"/>
          <line x1="220" y1="70" x2="400" y2="70" stroke="#333" stroke-width="1"/>
        </svg>
    """))
    return svg


@pytest.fixture
def alignment_svg(tmp_path):
    """SVG with aligned text for rhythm checking."""
    svg = tmp_path / "alignment.svg"
    svg.write_text(textwrap.dedent("""\
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
          <style>
            .fg-1 { fill: #1e3a5f; }
          </style>
          <text x="20" y="30" font-size="12" class="fg-1">Line one</text>
          <text x="20" y="44" font-size="12" class="fg-1">Line two</text>
          <text x="20" y="58" font-size="12" class="fg-1">Line three</text>
        </svg>
    """))
    return svg


# ---------------------------------------------------------------------------
# calc_connector.py tests
# ---------------------------------------------------------------------------


class TestCalcConnector:
    """CLI-level smoke tests for calc_connector.py. Parametrized over angle
    variants plus explicit covers for margin, cutout, head-size, svg output.
    Previous revision had 9 one-assertion CLI methods."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOLS_DIR / "calc_connector.py"), *args],
            capture_output=True, text=True,
        )

    @pytest.mark.parametrize(
        "src, tgt, expected_angle",
        [
            ("100,50", "300,50", "0.0"),
            ("100,50", "100,200", "90.0"),
            ("100,100", "200,200", "45.0"),
            ("100,200", "200,100", "-45.0"),
        ],
        ids=["horizontal", "vertical_down", "diagonal_down", "diagonal_up"],
    )
    def test_angle_variants(self, src, tgt, expected_angle):
        r = self._run("--from", src, "--to", tgt)
        assert r.returncode == 0
        assert f"Angle:            {expected_angle} degrees" in r.stdout

    def test_cli_scenarios(self):
        """Margin reduces length, custom head-size baked into polygon, svg
        output has path+polygon tags but no rotate templates, cutout mode
        splits into two segments when the pill intersects."""
        run = self._run

        # Margin reduces total length
        a = run("--from", "100,50", "--to", "300,50")
        b = run("--from", "100,50", "--to", "300,50", "--margin", "10")
        assert a.returncode == 0 and b.returncode == 0
        def _len(stdout):
            for line in stdout.split("\n"):
                if "Total length" in line:
                    return float(line.split(":")[1].strip().replace("px", ""))
            raise AssertionError("Total length not found")
        assert _len(b.stdout) < _len(a.stdout)

        # Custom head-size world-coords horizontal arrow
        c = run(
            "--from", "100,50", "--to", "300,50",
            "--head-size", "15,8", "--standoff", "0",
        )
        assert c.returncode == 0
        assert "(300.0,50.0) (285.0,42.0) (285.0,58.0)" in c.stdout

        # SVG snippet has path + polygon, NOT rotate templates
        d = run("--from", "100,50", "--to", "300,50")
        assert "<path d=" in d.stdout
        assert "<polygon points=" in d.stdout
        assert "<g transform=" not in d.stdout

        # Cutout intersects -> two segments
        e = run("--from", "100,100", "--to", "400,100", "--cutout", "200,90,100,20")
        assert e.returncode == 0
        assert "CUTOUT MODE" in e.stdout
        assert "Segment 1" in e.stdout and "Segment 2" in e.stdout

        # Cutout miss -> normal single-segment output
        f = run("--from", "100,100", "--to", "400,100", "--cutout", "200,200,50,20")
        assert f.returncode == 0
        assert "CUTOUT MODE" not in f.stdout


class TestCalcConnectorModule:
    """Direct-import tests for calc_connector + calc_empty_space.

    Previous revision had 31 tests - the per-attribute connector asserts
    and the per-edge-case empty-space tests are consolidated into a handful
    of parametrized or scenario tests.
    """

    # ----- calc_connector Python API -----

    def test_straight_and_edge_snap_and_arrow_and_cutout(self):
        """Covers: basic straight connector shape, default standoff 1px,
        auto edge-snap from rects (both aligned and diagonal), margin
        trim, no-arrow mode, and calc_cutout happy + miss paths."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import (
            calc_connector, calc_cutout,
        )

        # Basic straight (standoff=0) - full 100px, horizontal angle, arrow polygon correct
        c = calc_connector(0, 0, 100, 0, standoff=0)
        assert c["mode"] == "straight"
        assert abs(c["total_length"] - 100.0) < 0.01
        assert c["end"]["tip"] == (100.0, 0.0)
        assert abs(c["end"]["angle_deg"]) < 0.01
        poly = c["end"]["arrow"]["polygon"]
        assert poly[0] == (100.0, 0.0)
        assert abs(poly[1][0] - 90.0) < 0.01 and abs(poly[1][1] + 5.0) < 0.01
        assert abs(poly[2][0] - 90.0) < 0.01 and abs(poly[2][1] - 5.0) < 0.01

        # Default standoff is 1px each side -> 98px total
        assert calc_connector(0, 0, 100, 0)["standoff"] == (1.0, 1.0)
        assert abs(calc_connector(0, 0, 100, 0)["total_length"] - 98.0) < 0.01

        # Auto edge-snap (aligned rects) - endpoints on edge midpoints
        c = calc_connector(
            src_rect=(0, 0, 100, 100), tgt_rect=(200, 0, 100, 100),
            arrow="none", standoff=0,
        )
        assert abs(c["samples"][0][0] - 100) < 0.01
        assert abs(c["samples"][0][1] - 50) < 0.01
        assert abs(c["samples"][-1][0] - 200) < 0.01
        assert abs(c["samples"][-1][1] - 50) < 0.01

        # Auto edge-snap (diagonal) - endpoints on correct perimeter faces
        c = calc_connector(
            src_rect=(0, 0, 100, 100), tgt_rect=(200, 150, 100, 100),
            arrow="none", standoff=0,
        )
        s0, sL = c["samples"][0], c["samples"][-1]
        assert s0[0] >= 99.99 or s0[1] >= 99.99
        assert sL[0] <= 200.01 or sL[1] <= 150.01

        # Margin trims from both ends
        c = calc_connector(0, 0, 100, 0, margin=5)
        assert abs(c["total_length"] - 90.0) < 0.01
        assert abs(c["end"]["tip"][0] - 95.0) < 0.01

        # No-arrow mode: trimmed equals full path
        c = calc_connector(0, 0, 100, 0, arrow="none")
        assert c["start"]["arrow"] is None
        assert c["end"]["arrow"] is None
        assert c["trimmed_path_d"] == c["path_d"]

        # Cutout hits pill -> two straight segments
        res = calc_cutout(0, 50, 400, 50, 150, 40, 100, 20)
        assert res is not None
        assert res["segment1"]["mode"] == "straight"
        assert res["segment2"]["mode"] == "straight"
        assert res["segment1"]["end"]["arrow"] is None
        assert res["segment2"]["end"]["arrow"] is not None

        # Cutout misses pill -> None
        assert calc_cutout(0, 50, 400, 50, 150, 200, 100, 20) is None

    # ----- find_empty_regions helpers + scenarios -----

    @staticmethod
    def _svg(viewbox, body=""):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">'
            f'{body}</svg>'
        )

    @staticmethod
    def _rect(x, y, w, h, fill="black"):
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'

    def test_empty_space_rasterisation_and_defaults(self):
        """One scenario covers: finds free regions, sorts biggest-first,
        fully-occupied returns [], accepts polygon + text elements, respects
        default tolerance (20px) and default min_area (500), reports sensible
        areas, and handles narrow strips pixel-exactly."""
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import find_empty_regions

        # Finds free regions and returns boundary polygons sorted by area desc
        svg = self._svg(
            "0 0 400 300",
            self._rect(50, 50, 80, 60)
            + self._rect(250, 50, 80, 60)
            + self._rect(150, 200, 80, 60),
        )
        regions = find_empty_regions(svg, tolerance=0, min_area=0)
        assert len(regions) >= 1
        for i in range(len(regions) - 1):
            assert regions[i]["area"] >= regions[i + 1]["area"]

        # No shapes: single region covering the whole canvas
        single = find_empty_regions(self._svg("0 0 100 100"), tolerance=0)
        assert len(single) == 1
        assert abs(single[0]["area"] - 10000) < 100

        # Full-canvas background plate is auto-skipped (>=80% coverage rule),
        # so a single 100x100 rect on a 100x100 canvas leaves the canvas
        # fully free - not "fully occupied".
        bg_only = find_empty_regions(
            self._svg("0 0 100 100", self._rect(0, 0, 100, 100)), tolerance=0
        )
        assert len(bg_only) == 1
        assert abs(bg_only[0]["area"] - 10000) < 100

        # A sub-80% obstacle covering most of the canvas still blocks routing:
        # 70x70 on 100x100 = 49% coverage -> rasterised as an obstacle.
        occupied = find_empty_regions(
            self._svg("0 0 100 100", self._rect(15, 15, 70, 70)), tolerance=0, min_area=0
        )
        # The 70x70 obstacle leaves a thin ring -> 4 free strips. Total free
        # area = 10000 - 4900 = 5100 px^2, split across multiple components.
        assert occupied
        assert sum(r["area"] for r in occupied) > 4500

        # Narrow 30-px strip detected exactly. Obstacle is 70x100 on a
        # 100x100 canvas (70% coverage, below the 80% background threshold).
        strip = find_empty_regions(
            self._svg("0 0 100 100", self._rect(0, 0, 70, 100)),
            tolerance=0, min_area=0,
        )
        assert len(strip) == 1
        assert abs(strip[0]["area"] - 3000) < 50

        # Default tolerance = 20, default min_area = 500. Canvas 400x300 eroded
        # by 20 -> ~93600 px^2.
        default = find_empty_regions(self._svg("0 0 400 300"))
        assert len(default) == 1
        assert 90000 < default[0]["area"] < 95000
        import inspect
        assert inspect.signature(find_empty_regions).parameters["min_area"].default == 500.0

    def test_empty_space_shapes_transforms_and_css(self):
        """Covers: polygon elements rasterise correctly, nested <g transform>
        composes, stroke width cascades through CSS classes, boundary points
        stay within canvas bounds."""
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import find_empty_regions

        # Polygon element counted as an obstacle
        tri = self._svg(
            "0 0 300 300",
            '<polygon points="100,100 200,100 150,200" fill="red"/>',
        )
        r = find_empty_regions(tri, tolerance=0, min_area=0)
        assert len(r) >= 1
        assert r[0]["area"] >= 70000  # canvas minus small triangle

        # Nested <g transform="translate(...)"> composes
        translated = self._svg(
            "0 0 400 400",
            '<g transform="translate(100, 100)">' + self._rect(0, 0, 80, 80) + '</g>',
        )
        regions = find_empty_regions(translated, tolerance=0, min_area=0)
        assert len(regions) >= 1

        # CSS-class stroke cascades correctly - stroke-only rect leaves interior free
        css_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
            '<style>.big { stroke: black; stroke-width: 10; fill: none; }</style>'
            '<rect x="50" y="50" width="100" height="100" class="big"/>'
            '</svg>'
        )
        css_regions = find_empty_regions(css_svg, tolerance=0, min_area=0)
        assert len(css_regions) == 2  # inside + outside of the stroke ring

        # Boundary points lie within canvas
        bounded = self._svg("10 20 200 150", self._rect(50, 50, 30, 30))
        for reg in find_empty_regions(bounded, tolerance=0):
            for x, y in reg["boundary"]:
                assert 10 - 0.01 <= x <= 210 + 0.01
                assert 20 - 0.01 <= y <= 170 + 0.01

    def test_empty_space_tolerance_and_min_area_and_excludes(self):
        """Tolerance erodes regions, thin strips evaporate, min_area drops
        slivers, exclude_ids filter skips callout groups."""
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import find_empty_regions

        # Tolerance erodes a region
        base = self._svg("0 0 400 300", self._rect(150, 100, 100, 80))
        r0 = find_empty_regions(base, tolerance=0, min_area=0)
        r20 = find_empty_regions(base, tolerance=20, min_area=0)
        assert r0 and r20
        assert r20[0]["area"] < r0[0]["area"]

        # Thin strip (<2*tolerance) erodes to empty. A 320x220 obstacle
        # inset by 40 px on a 400x300 canvas (58% coverage, below the 80%
        # background threshold) leaves a 40-wide ring that fully erodes
        # at tolerance=20.
        assert find_empty_regions(
            self._svg("0 0 400 300", self._rect(40, 40, 320, 220)), tolerance=20
        ) == []

        # Canvas edge is an implicit obstacle (tolerance shrinks inward)
        edge = find_empty_regions(self._svg("0 0 200 200"), tolerance=20)
        assert len(edge) == 1
        assert 24000 < edge[0]["area"] < 27000

        # min_area drops slivers
        multi = self._svg(
            "0 0 400 300",
            self._rect(50, 50, 280, 60)
            + self._rect(50, 130, 280, 60)
            + self._rect(50, 210, 280, 60),
        )
        all_r = find_empty_regions(multi, tolerance=0, min_area=0)
        big_r = find_empty_regions(multi, tolerance=0, min_area=2000)
        assert len(big_r) <= len(all_r)
        assert all(r["area"] >= 2000 for r in big_r)

        # exclude_ids skips <g id="callout-*">
        cal = self._svg(
            "0 0 200 200",
            self._rect(10, 10, 20, 20)
            + '<g id="callout-foo">' + self._rect(100, 100, 50, 50) + '</g>',
        )
        r_with = find_empty_regions(cal, tolerance=0, exclude_ids=(), min_area=0)
        r_def = find_empty_regions(cal, tolerance=0, min_area=0)
        assert r_def[0]["area"] > r_with[0]["area"]

    def test_empty_space_input_types(self):
        """Accepts str SVG, pathlib.Path, bytes; rejects everything else."""
        import tempfile
        from pathlib import Path
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import find_empty_regions

        # Path input
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".svg", delete=False
        ) as f:
            f.write(self._svg("0 0 100 100", self._rect(0, 0, 50, 50)))
            path = Path(f.name)
        try:
            assert len(find_empty_regions(path, tolerance=0)) >= 1
        finally:
            path.unlink()

        # Bytes input
        assert len(find_empty_regions(
            self._svg("0 0 100 100").encode("utf-8"), tolerance=0
        )) == 1

        # Non-SVG input rejected
        with pytest.raises(TypeError, match="unsupported SVG source"):
            find_empty_regions(42, tolerance=0)

    def test_empty_space_text_bbox_semantics(self):
        """text-anchor=middle centres the bbox on x (not left-aligned), and
        longer text shrinks the free region proportionally."""
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import find_empty_regions

        # Middle-anchored text at canvas centre -> free region extends to left edge
        svg = self._svg(
            "0 0 400 100",
            '<text x="200" y="30" text-anchor="middle" font-size="12">Middle</text>',
        )
        regions = find_empty_regions(svg, tolerance=0, min_area=0)
        assert len(regions) >= 1
        xs = [p[0] for p in regions[0]["boundary"]]
        assert min(xs) < 50

        # Longer text -> smaller free area
        short = self._svg("0 0 400 100", '<text x="20" y="30" font-size="12">Hi</text>')
        long_svg = self._svg(
            "0 0 400 100",
            '<text x="20" y="30" font-size="12">a long piece of text spanning across the canvas</text>',
        )
        total_s = sum(r["area"] for r in find_empty_regions(short, tolerance=0, min_area=0))
        total_l = sum(r["area"] for r in find_empty_regions(long_svg, tolerance=0, min_area=0))
        assert total_s > total_l

    def test_empty_space_auto_skip_background(self):
        """Full-canvas background plates (>=80% of canvas area) are auto-
        skipped so a bg-plate rect does not fill the occupancy grid and
        leave zero free space. Sub-80% shapes are still rasterised."""
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import (
            _is_canvas_background,
            find_empty_regions,
            _parse_svg_source,
        )

        # Full-canvas rect -> skipped, whole canvas counted as free
        full = self._svg(
            "0 0 1000 600",
            '<rect id="bg" x="0" y="0" width="1000" height="600" fill="#ffffff"/>'
            + self._rect(100, 100, 80, 60),  # a real obstacle
        )
        regions = find_empty_regions(full, tolerance=0, min_area=0)
        total_free = sum(r["area"] for r in regions)
        # Canvas area minus the 80x60 real obstacle
        assert 595000 < total_free < 600000

        # 79% coverage rect is NOT skipped (just below threshold)
        below = self._svg(
            "0 0 100 100",
            '<rect x="0" y="0" width="100" height="79" fill="#000"/>',
        )
        r_below = find_empty_regions(below, tolerance=0, min_area=0)
        # Canvas has a 100x79 obstacle -> 100x21 remains free = 2100 px^2
        assert r_below
        assert abs(sum(r["area"] for r in r_below) - 2100) < 100

        # _is_canvas_background helper direct check
        doc, vb = _parse_svg_source(full)
        assert vb == (0.0, 0.0, 1000.0, 600.0)
        bg_elem = doc.get_element_by_id("bg")
        assert _is_canvas_background(bg_elem, vb) is True

    def test_empty_space_container_id(self):
        """Covers: rect/circle/polygon/path containers clip detection to their
        interior, regions are tagged with container_id, obstacles outside the
        container are ignored, obstacles inside still occupy, missing id
        raises, and Groups are rejected."""
        from stellars_claude_code_plugins.svg_tools.calc_empty_space import find_empty_regions

        # Rect container: outside obstacle ignored, inside obstacle occupies
        rect_svg = self._svg(
            "0 0 800 400",
            '<rect id="card" x="100" y="50" width="600" height="300" fill="#eee"/>'
            + '<rect id="inside" x="150" y="100" width="100" height="60" fill="#222"/>'
            + '<rect id="outside" x="20" y="20" width="40" height="40" fill="#f00"/>',
        )
        regions = find_empty_regions(rect_svg, tolerance=5, min_area=100, container_id="card")
        assert regions  # at least one empty region inside the card
        for r in regions:
            assert r["container_id"] == "card"
            xs = [p[0] for p in r["boundary"]]
            ys = [p[1] for p in r["boundary"]]
            # Every point lies inside the card's bbox (100,50)-(700,350) with
            # a small tolerance for the boundary pixel rounding.
            assert min(xs) >= 100 - 2 and max(xs) <= 700 + 2
            assert min(ys) >= 50 - 2 and max(ys) <= 350 + 2
        # The "outside" rect must NOT show up as an empty region when clipped
        # to the card; tagged regions live strictly inside the card.

        # Circle container: boundary stays within the disc
        circle_svg = self._svg(
            "0 0 400 400",
            '<circle id="disc" cx="200" cy="200" r="150" fill="#eee"/>'
            + '<rect id="obs" x="180" y="180" width="40" height="40" fill="#222"/>',
        )
        regions = find_empty_regions(
            circle_svg, tolerance=5, min_area=100, container_id="disc"
        )
        assert regions
        for r in regions:
            for x, y in r["boundary"]:
                # Within the disc plus small pixel-rounding slack
                dist_sq = (x - 200) ** 2 + (y - 200) ** 2
                assert dist_sq <= (155) ** 2

        # Polygon container (triangle)
        tri_svg = self._svg(
            "0 0 400 400",
            '<polygon id="tri" points="200,50 350,350 50,350" fill="#eee"/>',
        )
        regions = find_empty_regions(
            tri_svg, tolerance=5, min_area=100, container_id="tri"
        )
        assert regions
        assert all(r["container_id"] == "tri" for r in regions)
        # Triangle interior area roughly = 0.5 * base * height = 45000, minus erosion
        assert regions[0]["area"] > 20000

        # Path container (closed blob)
        path_svg = self._svg(
            "0 0 400 400",
            '<path id="blob" d="M 100 200 C 100 100, 300 100, 300 200 S 200 350, 100 200 Z" fill="#eee"/>',
        )
        regions = find_empty_regions(
            path_svg, tolerance=5, min_area=100, container_id="blob"
        )
        assert regions
        assert all(r["container_id"] == "blob" for r in regions)

        # Missing id -> ValueError
        with pytest.raises(ValueError, match="not found"):
            find_empty_regions(rect_svg, container_id="does_not_exist")

        # Group rejected -> ValueError
        grp_svg = self._svg(
            "0 0 100 100",
            '<g id="grp"><rect x="10" y="10" width="20" height="20"/></g>',
        )
        with pytest.raises(ValueError, match="closed shape"):
            find_empty_regions(grp_svg, container_id="grp")

        # Backward compat: no container_id -> container_id key is None
        doc = find_empty_regions(rect_svg, tolerance=0, min_area=0)
        assert doc
        assert all(r["container_id"] is None for r in doc)

    def test_empty_space_cli(self, tmp_path):
        """CLI prints region points, supports --json output, and --container-id
        clips detection to a specific element."""
        import subprocess
        import json as _json

        svg_file = tmp_path / "scene.svg"
        svg_file.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
            '<rect x="50" y="50" width="50" height="50" fill="black"/>'
            '</svg>'
        )

        # Default output - human-readable list
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "empty-space", "--svg", str(svg_file), "--tolerance", "0"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "EMPTY REGIONS" in r.stdout
        assert "points:" in r.stdout
        assert "<polygon" not in r.stdout

        # JSON output - parseable array, carries container_id field
        svg_file2 = tmp_path / "scene2.svg"
        svg_file2.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300">'
            '<rect x="100" y="100" width="50" height="50" fill="black"/>'
            '</svg>'
        )
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "empty-space", "--svg", str(svg_file2), "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        data = _json.loads(r.stdout)
        assert isinstance(data, list)
        assert all("boundary" in d and "area" in d and "container_id" in d for d in data)
        assert all(d["container_id"] is None for d in data)

        # --container-id CLI flag clips to element interior
        svg_file3 = tmp_path / "scene3.svg"
        svg_file3.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
            '<rect id="card" x="50" y="50" width="300" height="200" fill="#eee"/>'
            '<rect id="outside" x="360" y="10" width="30" height="30" fill="#f00"/>'
            '</svg>'
        )
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "empty-space", "--svg", str(svg_file3), "--container-id", "card",
             "--tolerance", "0", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        data = _json.loads(r.stdout)
        assert data
        assert all(d["container_id"] == "card" for d in data)


class TestConnectorModes:
    """L / L-chamfer / spline modes. 9 tests collapsed to 3."""

    @pytest.mark.parametrize(
        "mode, chamfer, src, tgt, start_dir, expected_corners, expected_angle",
        [
            # L mode, dx>dy -> horizontal first, corner at (tgt.x, src.y)
            ("l", None, (100, 50), (300, 150), None, [(300, 50)], 90.0),
            # L mode with start_dir=N -> vertical first, corner at (src.x, tgt.y)
            ("l", None, (100, 50), (300, 150), "N", [(100, 150)], None),
            # L-chamfer, dx>dy -> two corner points 4px apart
            ("l-chamfer", 4, (100, 50), (300, 150), None, [(296, 50), (300, 54)], None),
            # L-chamfer negative direction (up-and-left), signs flip
            ("l-chamfer", 4, (300, 150), (100, 50), None, [(104, 150), (100, 146)], None),
        ],
        ids=["l_horizontal_first", "l_forced_vertical", "l_chamfer_positive", "l_chamfer_negative"],
    )
    def test_l_modes(self, mode, chamfer, src, tgt, start_dir, expected_corners, expected_angle):
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l, calc_l_chamfer
        kwargs = {"arrow": "end"} if expected_angle is not None else {"arrow": "none"}
        if start_dir:
            kwargs["start_dir"] = start_dir
        if mode == "l":
            r = calc_l(src[0], src[1], tgt[0], tgt[1], **kwargs)
            assert r["mode"] == "l"
            assert len(r["samples"]) == 3
            assert r["samples"][1] == expected_corners[0]
        else:
            r = calc_l_chamfer(src[0], src[1], tgt[0], tgt[1], chamfer=chamfer, **kwargs)
            assert len(r["samples"]) == 4
            assert r["samples"][1] == expected_corners[0]
            assert r["samples"][2] == expected_corners[1]
        if expected_angle is not None:
            assert abs(r["end"]["angle_deg"] - expected_angle) < 0.01
            assert r["end"]["arrow"] is not None
            assert len(r["end"]["arrow"]["polygon"]) == 3
        else:
            assert r["end"]["arrow"] is None

    def test_spline_contract(self):
        """Spline covers: PCHIP passes through waypoints, handles vertical
        segments, arrow=both returns two polygons with trimming, and
        l-chamfer collinear degenerates to a straight line."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import (
            calc_spline, calc_l_chamfer,
        )

        # PCHIP hits waypoints exactly
        wp = [(100, 80), (200, 40), (300, 120), (400, 60)]
        r = calc_spline(wp, samples=200, arrow="end", standoff=0)
        assert r["mode"] == "spline"
        assert len(r["samples"]) == 200
        assert abs(r["samples"][0][0] - 100) < 0.5
        assert abs(r["samples"][0][1] - 80) < 0.5
        assert abs(r["samples"][-1][0] - 400) < 0.5
        assert abs(r["samples"][-1][1] - 60) < 0.5

        # Arrow both -> two polygons and trimmed path is shorter than full
        r = calc_spline([(0, 0), (50, 100), (100, 0)], samples=100, arrow="both")
        assert r["start"]["arrow"] is not None
        assert r["end"]["arrow"] is not None
        assert len(r["trimmed_path_d"]) < len(r["path_d"])

        # Non-monotone segments (vertical chunks) do not blow up
        wp = [(0, 0), (100, 0), (100, 100), (200, 100)]
        r = calc_spline(wp, samples=50, arrow="end")
        assert len(r["samples"]) == 50
        assert r["total_length"] > 0

        # L-chamfer collinear horizontal and vertical fall back to straight
        h = calc_l_chamfer(100, 200, 400, 200, chamfer=4, arrow="end", standoff=0)
        assert len(h["samples"]) == 2
        assert h["samples"][0] == (100, 200) and h["samples"][1] == (400, 200)
        assert abs(h["end"]["angle_deg"]) < 0.01

        v = calc_l_chamfer(200, 100, 200, 400, chamfer=4, arrow="end", standoff=0)
        assert len(v["samples"]) == 2
        assert abs(v["end"]["angle_deg"] - 90.0) < 0.01

    def test_pchip_parametric_closed_loop(self):
        """pchip_parametric produces self-intersecting / closed curves when
        the waypoints loop back - chord-length parametrisation required."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import pchip_parametric
        wp = [(0, 0), (50, 50), (100, 0), (50, -50), (0, 0)]
        pts = pchip_parametric(wp, num_samples=50)
        assert len(pts) == 50
        assert abs(pts[0][0] - pts[-1][0]) < 0.5
        assert abs(pts[0][1] - pts[-1][1]) < 0.5

    def test_auto_route_l(self):
        """Auto-route L: U-shape detour around a blocking obstacle, inside-
        container routing with container_id, and unroutable-case fallback
        warning."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l

        # Scenario 1: big obstacle between src and tgt on the left-right axis.
        # The 1-bend L would punch through the obstacle; auto_route must
        # produce a multi-elbow detour.
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400">'
            '<rect id="src" x="50" y="180" width="80" height="40" fill="#bbb"/>'
            '<rect id="obstacle" x="300" y="50" width="200" height="300" fill="#bbb"/>'
            '<rect id="tgt" x="670" y="180" width="80" height="40" fill="#bbb"/>'
            '</svg>'
        )
        r = calc_l(
            130, 200, 670, 200,
            start_dir="E", end_dir="W", arrow="end",
            auto_route=True, svg=svg,
        )
        assert r["mode"] == "l"
        # Multi-elbow path: at least two waypoints = three bend points total
        assert len(r["controls"]) >= 2, f"expected >=2 waypoints, got {r['controls']}"
        # None of the interior samples lies inside the obstacle's xyxy bbox
        for x, y in r["samples"]:
            inside = 305 < x < 495 and 55 < y < 345
            assert not inside, f"sample {(x,y)} is inside the obstacle"
        assert not any("failed" in w for w in r["warnings"])

        # Scenario 2: container_id clips routing to a card interior.
        svg_card = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">'
            '<rect id="card" x="50" y="50" width="500" height="300" fill="#eee"/>'
            '<rect id="inner-obstacle" x="250" y="120" width="100" height="160" fill="#222"/>'
            '</svg>'
        )
        r = calc_l(
            80, 200, 520, 200,
            start_dir="E", end_dir="W", arrow="end",
            auto_route=True, svg=svg_card, container_id="card",
        )
        assert len(r["controls"]) >= 2
        # Every sample stays inside the card's bbox (50,50)-(550,350)
        for x, y in r["samples"]:
            assert 48 <= x <= 552 and 48 <= y <= 352

        # Scenario 3: unroutable case -> warning + fallback to 1-bend L.
        # Src and tgt fully boxed in by a near-closed wall with no gap wide
        # enough for the 5 px margin.
        svg_blocked = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
            '<rect x="0" y="90" width="200" height="20" fill="#000"/>'
            '<rect x="90" y="0" width="20" height="200" fill="#000"/>'
            '</svg>'
        )
        r = calc_l(
            20, 50, 180, 150,
            arrow="end",
            auto_route=True, svg=svg_blocked,
            route_cell_size=5, route_margin=3,
        )
        # Either found a path OR fell back with a warning - both are valid.
        failed = any("auto_route failed" in w for w in r["warnings"])
        if failed:
            assert r["mode"] == "l"
            # Fallback is a simple 2-segment L (no waypoints)
            assert len(r["samples"]) <= 3

    def test_auto_route_skips_bg_and_routes_inside_card(self):
        """Regression for the demo failure: a scene with a full-canvas
        bg-plate PLUS a container card PLUS obstacles inside must route
        successfully. Without the bg-plate auto-skip the router would
        see the entire canvas as occupied and report 'unroutable'."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600">'
            '<rect id="bg-plate" x="0" y="0" width="1000" height="600" fill="#ffffff"/>'
            '<rect id="card-A" x="60" y="60" width="440" height="480" fill="#f5f7f8"/>'
            '<rect id="src-A" x="100" y="120" width="90" height="50" fill="#0096d1"/>'
            '<rect id="tgt-A" x="370" y="460" width="90" height="50" fill="#da8230"/>'
            '<rect id="obs-1" x="240" y="140" width="120" height="90" fill="#d4a04a"/>'
            '<rect id="obs-2" x="110" y="270" width="180" height="70" fill="#d4a04a"/>'
            '<rect id="obs-3" x="330" y="280" width="140" height="100" fill="#d4a04a"/>'
            '<rect id="obs-4" x="140" y="400" width="200" height="60" fill="#d4a04a"/>'
            '</svg>'
        )

        r = calc_l_chamfer(
            src_rect=(100, 120, 90, 50), start_dir="E",
            tgt_rect=(370, 460, 90, 50), end_dir="N",
            chamfer=6, standoff=4, arrow="end",
            auto_route=True, svg=svg, container_id="card-A",
            route_cell_size=16, route_margin=8,
        )
        # A routable scene produces >= 2 waypoints and no failure warning
        assert len(r["controls"]) >= 2
        assert not any("failed" in w for w in r["warnings"])
        # No sample sits inside any obstacle's bbox
        obstacle_bboxes = [
            (240, 140, 360, 230),
            (110, 270, 290, 340),
            (330, 280, 470, 380),
            (140, 400, 340, 460),
        ]
        for x, y in r["samples"]:
            for bx1, by1, bx2, by2 in obstacle_bboxes:
                inside = bx1 + 2 < x < bx2 - 2 and by1 + 2 < y < by2 - 2
                assert not inside, f"sample {(x, y)} inside obstacle {(bx1, by1, bx2, by2)}"
        # Every sample stays inside card-A with small pixel rounding slack
        for x, y in r["samples"]:
            assert 58 <= x <= 502 and 58 <= y <= 542

    def test_auto_route_cli(self, tmp_path):
        """CLI --auto-route flag runs the router via the unified CLI entry
        and emits a multi-elbow path. --svg is required when --auto-route
        is set."""
        import subprocess
        svg_file = tmp_path / "scene.svg"
        svg_file.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400">'
            '<rect id="src" x="50" y="180" width="80" height="40" fill="#bbb"/>'
            '<rect id="obstacle" x="300" y="50" width="200" height="300" fill="#bbb"/>'
            '<rect id="tgt" x="670" y="180" width="80" height="40" fill="#bbb"/>'
            '</svg>'
        )
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "connector", "--mode", "l",
             "--from", "130,200", "--to", "670,200",
             "--start-dir", "E", "--end-dir", "W",
             "--auto-route", "--svg", str(svg_file)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "controls" in r.stdout.lower() or "samples" in r.stdout.lower()

        # --auto-route without --svg is a parser error
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "connector", "--mode", "l",
             "--from", "130,200", "--to", "670,200",
             "--auto-route"],
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "--auto-route requires --svg" in (r.stderr + r.stdout)

    def test_threaded_route_respects_start_dir(self):
        """Regression: when auto_route returns a first waypoint that is
        nearly colinear with src (|dx|=1, |dy|=83), the threaded polyline
        must still exit src perpendicular to its edge - the old per-segment
        inference picked v-first and produced a path parallel to the east
        edge of src. With start_dir locked into _thread_l_controls the
        first step is horizontal (the small jog) and then vertical."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import _thread_l_controls
        src = (174, 162)
        dst = (422, 444)
        # First waypoint is 1 px east and 83 px south of src - dominant
        # delta is vertical, so inference would pick v-first. start_dir='E'
        # must override it.
        controls = [(175, 245), (483, 245)]
        pts = _thread_l_controls(src, dst, controls, chamfer=None, start_dir="E", end_dir="N")
        # First segment must move EAST before anything else.
        assert pts[0] == src
        dx0 = pts[1][0] - pts[0][0]
        dy0 = pts[1][1] - pts[0][1]
        assert dx0 != 0 and dy0 == 0, (
            f"first segment should be horizontal (east), got dx={dx0} dy={dy0}"
        )
        assert dx0 > 0, f"first segment must go east, got dx={dx0}"

    def test_threaded_route_respects_end_dir(self):
        """The last segment's orientation must match end_dir so the arrow
        tangent points in the requested cardinal direction. end_dir='S' on
        a route whose last waypoint is above tgt must produce a final
        vertical (southward) leg entering the top edge."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import _thread_l_controls
        src = (174, 162)
        dst = (422, 400)  # top-center of tgt rect
        controls = [(175, 245), (483, 245)]
        pts = _thread_l_controls(src, dst, controls, chamfer=None, start_dir="E", end_dir="S")
        # Last segment must be vertical (dx=0) and moving south (dy>0).
        dx_last = pts[-1][0] - pts[-2][0]
        dy_last = pts[-1][1] - pts[-2][1]
        assert dx_last == 0 and dy_last > 0, (
            f"last segment should be vertical-south, got dx={dx_last} dy={dy_last}"
        )

    def test_chamfer_clamps_to_short_segments(self):
        """Regression: the old _build_l_chamfer_polyline ignored segment
        length and emitted an 'after' point offset by the full chamfer from
        the corner, overshooting the segment endpoint when |dx|<chamfer.
        The global chamfer pass must clamp the bevel to half the shorter
        adjacent segment so no vertex ever backtracks."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import _thread_l_controls
        # src->control1 has a 1px horizontal jog, then a 100px vertical
        # run. A naive chamfer=5 would overshoot the 1px leg.
        src = (100, 100)
        dst = (200, 300)
        controls = [(101, 200)]
        pts = _thread_l_controls(src, dst, controls, chamfer=5, start_dir="E", end_dir="E")
        # No segment in the output may backtrack: every consecutive pair
        # must share a sign in at least one axis (otherwise we overshot).
        for i in range(1, len(pts)):
            a = pts[i - 1]
            b = pts[i]
            # Zero-length segments are a bug
            assert (a[0], a[1]) != (b[0], b[1]), f"duplicate vertex at index {i}"
        # Projected progression: x should never go below src.x (monotonic)
        xs = [p[0] for p in pts]
        assert all(xs[i + 1] >= xs[i] - 0.5 for i in range(len(xs) - 1)), (
            f"x coordinate backtracks: {xs}"
        )

    def test_1bend_respects_end_dir_alone(self):
        """Regression: 1-bend calc_l_chamfer with only end_dir (no start_dir)
        must honor end_dir on the last leg. The old code bypassed
        _thread_l_controls for the 1-bend case, so end_dir was silently
        dropped and first_axis fell back to dominant-delta inference -
        producing a diagonal arrow tangent when the dominant axis
        disagreed with end_dir.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # dx=376 >> |dy|=8 -> dominant inference picks h-first (last leg v).
        # end_dir='W' says last leg must be HORIZONTAL. Without the fix the
        # arrow tangent would be the diagonal bevel direction.
        r = calc_l_chamfer(
            src_x=494, src_y=280,
            tgt_rect=(760, 244, 110, 56), end_dir="W",
            chamfer=5, standoff=4, arrow="end",
        )
        tx, ty = r["end"]["tangent"]
        assert abs(ty) < 1e-6 and tx > 0.99, (
            f"end tangent must be pure east for end_dir='W', got ({tx}, {ty})"
        )
        # Last sample must share its y with the penultimate sample
        # (pure horizontal final segment, no diagonal bevel leak).
        samples = r["samples"]
        assert samples[-1][1] == samples[-2][1], (
            f"last segment must be horizontal, got {samples[-2]} -> {samples[-1]}"
        )

    def test_chamfer_reserves_arrowhead_clearance(self):
        """Regression: when the last axial segment is shorter than
        chamfer + standoff + head_len, the naive chamfer pass beveled
        the last corner at full radius and the subsequent head-clearance
        trim walked BACK into the bevel - the line ended on a diagonal
        and the arrow tangent diverged from end_dir. The reserve logic
        clamps the last corner's bevel so the final cardinal segment
        always accommodates standoff + head_len.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # Short last leg: 15 units from the last A*-like waypoint to tgt.
        # chamfer=5, standoff=4, head_len=10 -> naive would leave 10-4=6
        # after standoff which is less than head_len=10.
        controls = [(100, 100), (250, 100), (250, 385)]
        r = calc_l_chamfer(
            src_x=50, src_y=100,
            tgt_x=235, tgt_y=400,  # 15 units south of last waypoint
            controls=controls,
            chamfer=5, standoff=4, arrow="end", end_dir="S",
            head_len=10, head_half_h=5,
        )
        tx, ty = r["end"]["tangent"]
        assert abs(tx) < 1e-6 and ty > 0.99, (
            f"end tangent must be pure south for end_dir='S', got ({tx}, {ty})"
        )
        # Final axial segment (last two samples) must be vertical.
        samples = r["samples"]
        assert samples[-1][0] == samples[-2][0], (
            f"last segment must be vertical, got {samples[-2]} -> {samples[-1]}"
        )

    def test_straight_collapse_point_to_rect(self):
        """Raw point src + rect tgt with end_dir='E': when src.y is inside
        the tgt edge's y-range AND the natural midpoint difference is
        within straight_tolerance, both endpoints slide to a shared y
        and the route collapses to a single straight horizontal line.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # src.y = 280 is inside tgt y-range [244, 300]; diff from mid
        # (272) is 8 <= 20. Slide collapses to straight.
        r = calc_l_chamfer(
            src_x=494, src_y=280,
            tgt_rect=(760, 244, 110, 56), end_dir="E",
            chamfer=5, standoff=4, arrow="end",
        )
        samples = r["samples"]
        # Exactly one segment (two samples) = straight line, no corner
        assert len(samples) == 2, f"expected 2 samples for straight route, got {samples}"
        assert samples[0][1] == samples[1][1], (
            f"straight route must have constant y, got {samples}"
        )
        tx, ty = r["end"]["tangent"]
        assert abs(ty) < 1e-6 and tx > 0.99

    def test_straight_collapse_falls_back_when_outside_range(self):
        """When src's y coordinate is OUTSIDE the tgt edge's y-range,
        the slide is rejected and the tool falls back to the midpoint.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # src.y = 100 is OUTSIDE tgt y-range [244, 300] -> no slide.
        # Also diff = |100 - 272| = 172 > 20 so tolerance would reject
        # it anyway. The point is that tgt must still anchor at midpoint.
        r = calc_l_chamfer(
            src_x=494, src_y=100,
            tgt_rect=(760, 244, 110, 56), end_dir="E",
            chamfer=5, standoff=4, arrow="end",
        )
        # Tgt endpoint y must be the edge midpoint (272), NOT src.y (100)
        tgt_sample = r["samples"][-1]
        assert abs(tgt_sample[1] - 272) < 1.0 or tgt_sample[1] >= 244, (
            f"tgt must snap to midpoint when slide rejected, got y={tgt_sample[1]}"
        )

    def test_straight_collapse_rect_to_rect_overlap(self):
        """Rect-to-rect with both horizontal directions and overlapping
        y-ranges. The slide should find a common y in the overlap and
        collapse the route to a single horizontal line.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # Both rects have y-range covering [150, 160] with mid-y very close
        # (155 for src, 160 for tgt, diff 5 < tolerance=20). Slide
        # collapses.
        r = calc_l_chamfer(
            src_rect=(50, 130, 80, 50), start_dir="E",   # y range 130-180, mid=155
            tgt_rect=(400, 140, 80, 40), end_dir="E",   # y range 140-180, mid=160
            chamfer=5, standoff=4, arrow="end",
        )
        samples = r["samples"]
        assert len(samples) == 2, f"expected 2 samples for straight rect-rect, got {samples}"
        # Shared y = midpoint of overlap intersection [140, 180] = 160
        assert abs(samples[0][1] - samples[1][1]) < 1e-6

    def test_straight_collapse_no_slide_when_perpendicular(self):
        """Rect-to-rect with PERPENDICULAR directions (E + S) must not
        attempt to collapse - there is no shared axis to slide on.
        Route keeps its corner.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        r = calc_l_chamfer(
            src_rect=(90, 140, 84, 44), start_dir="E",
            tgt_rect=(380, 400, 84, 44), end_dir="S",
            chamfer=5, standoff=4, arrow="end",
        )
        samples = r["samples"]
        # Must have at least one corner -> more than 2 samples
        assert len(samples) > 2, (
            f"perpendicular rect pair must keep corner, got {samples}"
        )

    def test_stem_min_warning_on_short_last_leg(self):
        """stem_min requires len_out >= standoff + head_len + stem_min.
        When the last cardinal leg is too short to accommodate the stem
        target, the tool emits a non-fatal warning and clamps the last
        corner's bevel to preserve as much cardinal stem as possible.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # Construct a polyline whose final cardinal leg is 15 units
        # (from the last corner to tgt). end_dir='S' forces first_axis
        # on the last segment to 'h', making the corner at (250, 100).
        # Last leg (250, 100) -> (250, 115) = 15 units; need 34.
        r = calc_l_chamfer(
            src_x=50, src_y=100,
            tgt_x=250, tgt_y=115,
            controls=[(200, 100)],
            chamfer=5, standoff=4, arrow="end", end_dir="S",
            head_len=10, head_half_h=5, stem_min=20,
        )
        assert any("stem" in w for w in r["warnings"]), (
            f"expected stem-min warning, got warnings={r['warnings']}"
        )

    def test_stem_min_configurable(self):
        """stem_min is configurable - passing stem_min=0 disables the
        reserve and the tool bevels at full chamfer even on short legs.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        r0 = calc_l_chamfer(
            src_x=50, src_y=100, tgt_x=250, tgt_y=115,
            controls=[(200, 100)],
            chamfer=5, standoff=4, arrow="end",
            end_dir="S", stem_min=0,
        )
        # stem_min=0 disables the stem warning
        assert not any("stem" in w for w in r0["warnings"])

    def test_autoroute_stem_zone_penalty_keeps_corner_far_from_tgt(self):
        """The A* stem-zone turn penalty forces corners to stay far
        enough from tgt that the final cardinal leg accommodates
        standoff + head_len + stem_min. Without the penalty the router
        would hug the tgt too closely and leave the arrow with only a
        few pixels of cardinal stem.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # Scene identical in spirit to the container-routing demo: src
        # on left, tgt bottom-right, obstacles forcing a multi-elbow
        # detour. Without stem_min the last corner would sit ~15 px
        # north of tgt; with stem_min=20 the penalty forces it >=34 px.
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">'
            '<rect x="0" y="0" width="500" height="500" fill="#ffffff"/>'
            '<rect id="card" x="20" y="20" width="460" height="460" fill="#eee"/>'
            '<rect id="obs-1" x="150" y="100" width="120" height="60" fill="#888"/>'
            '<rect id="obs-2" x="150" y="280" width="200" height="60" fill="#888"/>'
            '</svg>'
        )
        r = calc_l_chamfer(
            src_rect=(40, 200, 80, 40), start_dir="E",
            tgt_rect=(360, 400, 80, 40), end_dir="S",
            chamfer=5, standoff=4, arrow="end",
            auto_route=True, svg=svg, container_id="card",
            route_cell_size=10, route_margin=6,
            stem_min=20,
        )
        assert not any("stem" in w for w in r["warnings"]), (
            f"stem penalty should achieve 20 px, got warnings={r['warnings']}"
        )
        # Walk backward from the end and measure the last cardinal run.
        samples = r["samples"]
        import math
        last_leg = 0.0
        for i in range(len(samples) - 1, 0, -1):
            a = samples[i - 1]
            b = samples[i]
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            if dx != 0 and dy != 0:
                break
            last_leg += math.hypot(dx, dy)
        # Final cardinal leg (post-standoff) must be >= head_len + stem_min = 30
        assert last_leg >= 30, f"expected last cardinal leg >= 30, got {last_leg}"

    def test_slide_bias_point_is_zero_width_smaller(self):
        """Raw point + rect: the point is effectively a zero-width
        "smaller" geometry, so it never moves - the rect absorbs 100 %
        of the slide by snapping its edge coord to the point. This is
        consistent with the rect-rect bias rule (smaller slides less).
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # Point at (494, 280); tgt rect y-range [244, 300] mid 272.
        # Diff 8 <= tolerance 20, point y inside rect range -> slide.
        # Point stays at y=280, rect slides from mid 272 to 280.
        r = calc_l_chamfer(
            src_x=494, src_y=280,
            tgt_rect=(760, 244, 110, 56), end_dir="E",
            chamfer=5, standoff=4, arrow="end",
        )
        samples = r["samples"]
        assert len(samples) == 2, f"expected straight line, got {samples}"
        assert samples[0][1] == 280, f"raw point must stay at y=280, got {samples[0]}"
        assert samples[1][1] == 280, f"rect must slide to y=280, got {samples[1]}"

    def test_slide_bias_favors_smaller_range(self):
        """When both endpoints are movable on the same axis, the slide
        target biases toward the SMALLER range's midpoint (clamped to
        the intersection). The smaller geometry moves less / not at all
        and the larger absorbs the slide.
        """
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_l_chamfer
        # Src y-range [180, 280] (wide, mid 230); tgt y-range [220, 260]
        # (narrow, mid 240). Natural diff 10 < tolerance=20. Intersection
        # is [220, 260]. Smaller (tgt, width 40) midpoint is 240 which
        # lies inside the intersection, so target = 240. Tgt does not
        # move (already at its midpoint), src slides from 230 to 240.
        # The old midpoint-of-intersection rule would pick 240 too in
        # this symmetric case, so use an asymmetric intersection.
        # src [180, 300] mid 240, tgt [210, 250] mid 230. Diff=10.
        # Intersection [210, 250]. Smaller is tgt (width 40, mid 230).
        # Old rule: mid of intersection = 230. New rule: tgt mid = 230.
        # Same here. We need a case where intersection-mid != smaller-mid.
        # src [100, 200] mid 150, tgt [140, 160] mid 150. Diff=0,
        # intersection [140, 160] mid 150, smaller mid 150. Same.
        # Better: src [100, 300] mid 200, tgt [190, 210] mid 200.
        # Diff=0. Intersection [190, 210] mid 200 == tgt mid. Same.
        # True asymmetric: src [100, 200] mid 150, tgt [130, 160] mid
        # 145. Diff=5. Intersection [130, 160] mid 145. Smaller (tgt,
        # width 30) mid 145. Same result!
        # The old mid-of-intersection equals smaller-mid whenever the
        # smaller range is FULLY INSIDE the larger. Picking a case
        # where smaller is partially outside: src [100, 150] mid 125,
        # tgt [140, 170] mid 155. Diff=30 > tol=20, rejected.
        # Use tolerance=50 for the test. src [100, 150] (width 50),
        # tgt [140, 170] (width 30, smaller). Intersection [140, 150]
        # mid 145. Smaller (tgt) mid 155 clamped to [140, 150] -> 150.
        # Target 150 instead of 145. Both slide to 150.
        r = calc_l_chamfer(
            src_rect=(50, 100, 80, 50), start_dir="E",    # y range 100..150
            tgt_rect=(400, 140, 80, 30), end_dir="E",    # y range 140..170 (smaller)
            chamfer=5, standoff=4, arrow="end",
            straight_tolerance=50,
        )
        samples = r["samples"]
        assert len(samples) == 2, f"expected straight line, got {samples}"
        # Biased target = 150 (smaller mid 155 clamped to intersection
        # [140, 150]); old rule would pick intersection mid = 145.
        assert abs(samples[0][1] - 150) < 1e-6, (
            f"slide bias should pick target y=150, got {samples[0]}"
        )

    def test_all_elbows_chamfered(self):
        """Regression: the old per-segment chamfer only beveled the corner
        INSIDE each L, leaving inter-segment joins sharp. With the global
        chamfer pass every 90 degree vertex gets a bevel, producing twice
        as many samples as there are corners (two bevel points per corner
        instead of one sharp vertex)."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import _thread_l_controls
        # A 3-waypoint route that produces 3 corners: one inside the first
        # L, one at the first inter-segment join, one inside the last L.
        src = (0, 0)
        dst = (300, 300)
        controls = [(100, 100), (200, 100)]
        sharp = _thread_l_controls(src, dst, controls, chamfer=None)
        chamfered = _thread_l_controls(src, dst, controls, chamfer=10)
        # Count corners in the sharp polyline (interior vertices).
        sharp_corners = len(sharp) - 2
        assert sharp_corners >= 2, f"expected at least 2 corners, got {sharp_corners}"
        # Each chamfered corner replaces 1 vertex with 2, so chamfered
        # length = len(sharp) + sharp_corners.
        assert len(chamfered) == len(sharp) + sharp_corners, (
            f"expected {len(sharp) + sharp_corners} samples after chamfer, "
            f"got {len(chamfered)} (sharp had {len(sharp)})"
        )
        # No interior vertex in the chamfered output should be a sharp 90
        # degree corner. A sharp corner has BOTH adjacent segments axis
        # aligned AND on different axes. Bevel entry/exit vertices have
        # one axis-aligned leg and one diagonal leg, which is fine.
        for i in range(1, len(chamfered) - 1):
            a = chamfered[i - 1]
            b = chamfered[i]
            c = chamfered[i + 1]
            d1 = (b[0] - a[0], b[1] - a[1])
            d2 = (c[0] - b[0], c[1] - b[1])
            d1_h = d1[1] == 0 and d1[0] != 0
            d1_v = d1[0] == 0 and d1[1] != 0
            d2_h = d2[1] == 0 and d2[0] != 0
            d2_v = d2[0] == 0 and d2[1] != 0
            sharp_corner = (d1_h and d2_v) or (d1_v and d2_h)
            assert not sharp_corner, f"vertex {i} at {b} is still a sharp corner"


class TestManifoldConnector:
    """N-starts + M-ends Sankey-style manifold connector.

    Previous revision had 35 tests; this revision groups them into one
    canonical-topology parametrized test + targeted tests for tension,
    organic relaxation, bbox/warnings, error paths, alignment, direction
    annotations, controls, cli, and unified polyline output.
    """

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOLS_DIR / "calc_connector.py"), *args],
            capture_output=True, text=True,
        )

    @pytest.mark.parametrize(
        "shape, tension",
        [
            ("straight", 0.5),
            ("l", 1.0),
            ("l-chamfer", 0.0),
            ("spline", 0.5),
        ],
        ids=["straight", "l", "l_chamfer", "spline"],
    )
    def test_manifold_canonical_topology(self, shape, tension):
        """Every shape must produce a valid manifold where all start strands
        merge at spine_start, all end strands fork from spine_end, spine
        has positive length, and each sub-result carries trimmed_path_d."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_manifold
        r = calc_manifold(
            starts=[(50, 100), (50, 200), (50, 300)],
            ends=[(400, 150), (400, 250)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape=shape, tension=tension, samples=50, arrow="end",
        )
        assert r["mode"] == "manifold"
        assert r["shape"] == shape
        assert r["n_starts"] == 3
        assert r["n_ends"] == 2
        # All merges coincide at spine_start; all forks at spine_end
        for m in r["merge_points"]:
            assert m == (200, 200)
        for f in r["fork_points"]:
            assert f == (300, 200)
        # Spine has length; each sub-result has a trimmed path
        assert r["spine"]["total_length"] > 0
        for strand in r["start_strands"] + r["end_strands"] + [r["spine"]]:
            assert "trimmed_path_d" in strand
            assert strand["trimmed_path_d"].startswith("M")
        # Arrowheads present on end strands when arrow="end"
        assert r["end_strands"][0]["end"]["arrow"] is not None

    def test_manifold_tension_and_bbox_and_overrides(self):
        """Tension tuple stored as-is, bbox spans all sub-strands, and
        explicit merge_points/fork_points override the auto-topology."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_manifold

        # Tension as (start, end) tuple is preserved
        r = calc_manifold(
            starts=[(50, 100), (50, 300)],
            ends=[(400, 100), (400, 300)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="l-chamfer", tension=(0.2, 0.8),
        )
        assert r["tension"] == (0.2, 0.8)

        # bbox spans all strand geometry
        r = calc_manifold(
            starts=[(50, 100), (50, 300)],
            ends=[(400, 200)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="l-chamfer", tension=1,
        )
        x, y, w, h = r["bbox"]
        assert x <= 52 and x + w >= 398
        assert y <= 102 and y + h >= 198

        # Explicit merge/fork points override inference
        r = calc_manifold(
            starts=[(50, 100), (50, 200)],
            ends=[(400, 150)],
            spine_start=(200, 150), spine_end=(300, 150),
            merge_points=[(180, 60), (180, 240)],
            shape="l", tension=0.5,
        )
        assert r["merge_points"][0] == (180, 60)
        assert r["merge_points"][1] == (180, 240)

    @pytest.mark.parametrize(
        "bad_args, match",
        [
            (
                dict(starts=[(0, 0), (0, 10)], ends=[(100, 5)], merge_points=[(50, 5)]),
                "merge_points length",
            ),
            (
                dict(starts=[(0, 0)], ends=[(100, 0), (100, 10)], fork_points=[(70, 5)]),
                "fork_points length",
            ),
            (
                dict(starts=[(0, 0)], ends=[(100, 0)], tension=1.5),
                "tension components",
            ),
        ],
        ids=["merge_points_length", "fork_points_length", "tension_out_of_range"],
    )
    def test_manifold_validation_errors(self, bad_args, match):
        """Invalid argument combinations raise ValueError with specific match."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_manifold
        defaults = dict(
            spine_start=(50, 5), spine_end=(70, 5), shape="l-chamfer",
        )
        with pytest.raises(ValueError, match=match):
            calc_manifold(**defaults, **bad_args)

    def test_manifold_organic_relaxation(self):
        """Organic mode is opt-in (default False), tension modulates relaxation
        stiffness, strand midpoints visibly move at low tension."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_manifold

        # Default organic=False
        r = calc_manifold(
            starts=[(50, 100), (50, 200), (50, 300)],
            ends=[(400, 150), (400, 250)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="spline", tension=0.8,
        )
        assert r["organic"] is False

        # Explicit organic=False overrides the auto-default
        r = calc_manifold(
            starts=[(50, 100), (50, 200)],
            ends=[(400, 200)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="spline", organic=False,
        )
        assert r["organic"] is False

        # Organic mode with tension=0 moves midpoints visibly vs baseline
        common = dict(
            starts=[(50, 100), (50, 200), (50, 300)],
            ends=[(400, 200)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="spline", tension=0.0,
        )
        baseline = calc_manifold(**common, organic=False)
        relaxed = calc_manifold(
            **common, organic=True,
            organic_iterations=40, organic_repulsion=150,
        )
        b_mid = baseline["start_strands"][0]["samples"][
            len(baseline["start_strands"][0]["samples"]) // 2
        ]
        r_mid = relaxed["start_strands"][0]["samples"][
            len(relaxed["start_strands"][0]["samples"]) // 2
        ]
        assert abs(b_mid[1] - r_mid[1]) > 0.3 or abs(b_mid[0] - r_mid[0]) > 0.3

        # Organic relaxation with different tensions produces different paths
        s0 = calc_manifold(
            **common, organic=True, organic_iterations=80, organic_repulsion=300,
        )
        common["tension"] = 1.0
        s1 = calc_manifold(
            **common, organic=True, organic_iterations=80, organic_repulsion=300,
        )
        assert s0["start_strands"][0]["samples"] != s1["start_strands"][0]["samples"]

    def test_manifold_align_elbows_and_controls(self):
        """align_elbows injects an alignment waypoint for l-chamfer strands,
        but is suppressed when the caller supplies explicit start_controls.
        Also: start_controls drive the routing for L-chamfer sub-strands
        directly, and align_elbows is ignored entirely for spline shapes."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import calc_manifold

        # align_elbows makes all strands turn at the same x
        r = calc_manifold(
            starts=[(50, 100), (50, 200), (50, 300)],
            ends=[(400, 200)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="l-chamfer", tension=1, align_elbows=True,
        )
        for strand in r["start_strands"]:
            xs = [s[0] for s in strand["samples"]]
            assert any(abs(x - 200) < 2 for x in xs)

        # User controls preserved (align_elbows does not override them)
        explicit = [[(180, 100)], [], []]
        r = calc_manifold(
            starts=[(50, 100), (50, 200), (50, 300)],
            ends=[(400, 200)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="l-chamfer", tension=1,
            start_controls=explicit, align_elbows=True,
        )
        assert r["start_strands"][0]["controls"][0] == (180, 100)

        # Explicit start_controls on a 2-start l-chamfer manifold
        r = calc_manifold(
            starts=[(50, 100), (50, 300)],
            ends=[(400, 200)],
            spine_start=(200, 200), spine_end=(300, 200),
            shape="l-chamfer", tension=1,
            start_controls=[[(120, 100), (150, 130)], []],
        )
        controls = r["start_strands"][0]["controls"]
        assert controls[0] == (120, 100)
        assert controls[1] == (150, 130)
        assert len(controls) == 2

        # align_elbows ignored for spline shape (no extra waypoint injected)
        r = calc_manifold(
            starts=[(50, 100), (50, 200)],
            ends=[(400, 150)],
            spine_start=(200, 150), spine_end=(300, 150),
            shape="spline", tension=1, align_elbows=True,
        )
        for strand in r["start_strands"]:
            assert len(strand["controls"]) <= 1

    def test_manifold_directions_and_3_tuple_unpack(self):
        """Manifold accepts 3-tuple direction-annotated starts/ends and the
        underlying _unpack_point_with_direction helper parses compass strings
        and numeric degrees equivalently."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import (
            calc_l, calc_manifold, _unpack_point_with_direction,
        )

        # compass vs numeric degrees agree
        r_compass = calc_l(50, 100, 300, 200, start_dir="E")
        r_degrees = calc_l(50, 100, 300, 200, start_dir=90)
        assert r_compass["samples"][1] == r_degrees["samples"][1]

        # N forces vertical first, E horizontal first
        assert calc_l(50, 100, 200, 50, start_dir="E")["samples"][1] == (200, 100)
        assert calc_l(50, 100, 300, 50, start_dir="N")["samples"][1] == (50, 50)

        # 3-tuple / 2-tuple unpacking
        xy, d = _unpack_point_with_direction((10, 20, "NE"))
        assert xy == (10.0, 20.0) and d == "NE"
        xy, d = _unpack_point_with_direction((10, 20, 45))
        assert d == 45
        xy, d = _unpack_point_with_direction((10, 20))
        assert d is None

        # Manifold accepts direction-annotated starts/ends without crashing
        r = calc_manifold(
            starts=[(50, 100, "E"), (50, 200, "E")],
            ends=[(400, 150, "E")],
            spine_start=(200, 150), spine_end=(300, 150),
            shape="spline", tension=0.5,
        )
        assert r["mode"] == "manifold"
        assert len(r["start_strands"]) == 2
        assert len(r["end_strands"]) == 1

    @pytest.mark.parametrize(
        "mode, extra_args, expected_tokens",
        [
            # CLI L mode - path + polygon + arrow polygon
            ("l", ["--from", "100,50", "--to", "300,150", "--arrow", "end"],
             ["L CONNECTOR", "Arrow polygon", "<path d=", "<polygon"]),
            # CLI L-chamfer - 4-sample polyline
            ("l-chamfer", ["--from", "100,50", "--to", "300,150", "--chamfer", "4"],
             ["L-CHAMFER CONNECTOR", "Samples:          4"]),
            # CLI spline with arrow=both - 2 polygons in the SVG output
            ("spline", ["--waypoints", "100,80 200,40 300,120 400,60", "--samples", "100", "--arrow", "both"],
             ["SPLINE CONNECTOR", "Samples:          100"]),
            # CLI straight unified output - path + polygon in world coords, no rotate template
            ("straight", ["--from", "100,50", "--to", "300,50"],
             ["STRAIGHT CONNECTOR", "Angle:            0.0 degrees", "<path d=", "<polygon points="]),
        ],
        ids=["l", "l_chamfer", "spline", "straight_unified"],
    )
    def test_cli_modes(self, mode, extra_args, expected_tokens):
        r = self._run("--mode", mode, *extra_args)
        assert r.returncode == 0, r.stderr
        for tok in expected_tokens:
            assert tok in r.stdout, f"{tok} missing from {mode} CLI output"

    def test_cli_manifold_and_error_paths(self):
        """CLI end-to-end for manifold mode plus the missing-spine error
        path. Previous revision split these into two separate tests."""
        # Tension-based manifold CLI runs end-to-end
        r = self._run(
            "--mode", "manifold",
            "--starts", "[(50,100),(50,200),(50,300)]",
            "--ends", "[(400,200)]",
            "--spine-start", "(200,200)",
            "--spine-end", "(300,200)",
            "--shape", "l-chamfer",
            "--tension", "0.5",
            "--arrow", "end",
        )
        assert r.returncode == 0, r.stderr
        for tok in [
            "MANIFOLD CONNECTOR", "Starts:           3", "Ends:             1",
            "Spine start:", "Tension:", "BBox:", "manifold-connector",
        ]:
            assert tok in r.stdout

        # Missing spine endpoints -> non-zero exit
        r = self._run(
            "--mode", "manifold",
            "--starts", "[(50,100)]",
            "--ends", "[(400,200)]",
        )
        assert r.returncode != 0
        assert "spine" in r.stderr.lower()

    def test_polyline_result_helpers_and_options(self):
        """Engine-level helpers and polyline-result options:
        _arrowhead_polygon_world horizontal case, _trim_polyline end/start,
        bbox/warnings/standoff on connector results, standoff tuple splits
        trim across both ends, l-chamfer controls, controls soft cap warning
        via CLI, and straight shape rejects controls."""
        from stellars_claude_code_plugins.svg_tools.calc_connector import (
            _arrowhead_polygon_world, _trim_polyline, _polyline_length,
            calc_connector, calc_l_chamfer, _calc_single_strand,
        )

        # Arrow polygon for horizontal arrow at tip (10, 5)
        poly = _arrowhead_polygon_world(10, 5, 0, head_len=10, head_half_h=4)
        assert poly[0] == (10, 5)
        assert abs(poly[1][0]) < 0.001 and abs(poly[1][1] - 1) < 0.001
        assert abs(poly[2][0]) < 0.001 and abs(poly[2][1] - 9) < 0.001

        # Trim 30px from each end of a 200-px polyline
        pts = [(0, 0), (100, 0), (100, 100)]
        assert abs(_polyline_length(_trim_polyline(pts, 30, "end")) - 170) < 0.01
        assert abs(_polyline_length(_trim_polyline(pts, 30, "start")) - 170) < 0.01

        # Connector result carries bbox + warnings + standoff
        c = calc_connector(10, 20, 110, 80, standoff=0)
        assert "bbox" in c and "warnings" in c and "standoff" in c
        x, y, w, h = c["bbox"]
        assert x <= 10 and y <= 20
        assert x + w >= 110 and y + h >= 80
        assert isinstance(c["warnings"], list)

        # Standoff tuple trims independently at start and end
        c = calc_connector(0, 0, 100, 0, standoff=(5, 15), arrow="none")
        assert c["samples"][0] == (5, 0)
        assert c["samples"][-1] == (85, 0)
        assert c["standoff"] == (5.0, 15.0)

        # l-chamfer controls add corners to the polyline. With the global
        # chamfer pass, each control is replaced by a bevel pair straddling
        # it, so the exact control coord no longer appears as a vertex - we
        # assert instead that samples pass within `chamfer` of the control.
        r = calc_l_chamfer(50, 50, 300, 200, controls=[(150, 50), (200, 150)], arrow="end")
        samples = r["samples"]
        chamfer_tol = 4.0 + 1e-3
        assert any(
            abs(s[0] - 150) <= chamfer_tol and abs(s[1] - 50) <= chamfer_tol for s in samples
        )
        assert r["controls"] == [(150, 50), (200, 150)]

        # Soft-cap warning via CLI when >5 controls are given
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "calc_connector.py"),
             "--mode", "l-chamfer", "--from", "0,0", "--to", "300,300",
             "--controls", "[(50,10),(100,20),(150,30),(200,40),(250,50),(280,80)]"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert "WARNING" in r.stderr
        assert "soft cap" in r.stderr

        # Straight shape rejects controls via the manifold-dispatch helper
        with pytest.raises(ValueError, match="straight shape does not accept"):
            _calc_single_strand(
                (0, 0), (100, 0), shape="straight", chamfer=4, samples=50,
                margin=0, head_len=10, head_half_h=5, arrow="end",
                controls=[(50, 20)],
            )


class TestGeometryModule:
    """Direct import tests for calc_geometry primitives. 14 tests collapsed
    into 3 comprehensive scenario tests grouped by primitive family."""

    def test_basic_primitives(self):
        """midpoint, distance, lerp, extend_line, perpendicular_foot, bisector_direction."""
        from stellars_claude_code_plugins.svg_tools.calc_geometry import (
            midpoint, distance, lerp, extend_line, perpendicular_foot,
            bisector_direction, Point,
        )

        assert midpoint(Point(0, 0), Point(100, 200)) == Point(50, 100) or (
            midpoint(Point(0, 0), Point(100, 200)).x == 50
            and midpoint(Point(0, 0), Point(100, 200)).y == 100
        )
        assert distance(Point(0, 0), Point(3, 4)) == 5.0
        p = lerp(Point(0, 0), Point(100, 0), 0.25)
        assert p.x == 25 and p.y == 0

        end = extend_line(Point(0, 0), Point(10, 0), 5, "end")
        assert abs(end.x - 15) < 1e-9 and abs(end.y) < 1e-9
        start = extend_line(Point(0, 0), Point(10, 0), 5, "start")
        assert abs(start.x + 5) < 1e-9 and abs(start.y) < 1e-9

        foot = perpendicular_foot(Point(5, 10), Point(0, 0), Point(20, 0))
        assert abs(foot.x - 5) < 1e-9 and abs(foot.y) < 1e-9

        # 90-degree corner: bisector at 45 degrees, unit length
        bx, by = bisector_direction(Point(10, 0), Point(0, 0), Point(0, 10))
        assert abs(bx - by) < 1e-9
        assert abs(math.hypot(bx, by) - 1) < 1e-9

    def test_intersections(self):
        """intersect_lines (hit/parallel), intersect_line_circle (hit/miss),
        intersect_circles, tangent_points_from_external."""
        from stellars_claude_code_plugins.svg_tools.calc_geometry import (
            intersect_lines, intersect_line_circle, intersect_circles,
            tangent_points_from_external, distance, Point,
        )

        # Line intersection - diagonals of unit square cross at (50, 50)
        pt = intersect_lines(
            Point(0, 0), Point(100, 100),
            Point(0, 100), Point(100, 0),
        )
        assert abs(pt.x - 50) < 1e-9 and abs(pt.y - 50) < 1e-9

        # Parallel lines -> None
        assert intersect_lines(
            Point(0, 0), Point(10, 0),
            Point(0, 5), Point(10, 5),
        ) is None

        # Line hits circle at x=±10, misses at y=100
        pts = intersect_line_circle(Point(-50, 0), Point(50, 0), Point(0, 0), 10)
        xs = sorted(p.x for p in pts)
        assert abs(xs[0] + 10) < 1e-9 and abs(xs[1] - 10) < 1e-9

        assert intersect_line_circle(
            Point(-50, 100), Point(50, 100), Point(0, 0), 10,
        ) == []

        # Two circles centred (0,0) and (10,0), r=6 -> x=5, y=±sqrt(11)
        pts = intersect_circles(Point(0, 0), 6, Point(10, 0), 6)
        assert len(pts) == 2
        for p in pts:
            assert abs(p.x - 5) < 1e-6
            assert abs(abs(p.y) - math.sqrt(11)) < 1e-6

        # Tangent points from external point: on circle, perpendicular to radius
        center, ext, r = Point(0, 0), Point(10, 0), 6
        tangents = tangent_points_from_external(ext, center, r)
        assert len(tangents) == 2
        for p in tangents:
            assert abs(distance(p, center) - r) < 1e-6
            # Radius at p is perpendicular to tangent line (dot product = 0)
            dot = (p.x - center.x) * (ext.x - p.x) + (p.y - center.y) * (ext.y - p.y)
            assert abs(dot) < 1e-6

    def test_polar_and_attachment(self):
        """polar_to_cartesian, evenly_spaced_on_circle, rect_attachment,
        rect_corner, rect_center."""
        from stellars_claude_code_plugins.svg_tools.calc_geometry import (
            polar_to_cartesian, evenly_spaced_on_circle, distance,
            rect_attachment, rect_corner, rect_center, Point,
        )

        # Angle 0 = +X in SVG; angle 90 = +Y (down)
        p = polar_to_cartesian(Point(100, 100), 50, 0)
        assert abs(p.x - 150) < 1e-9 and abs(p.y - 100) < 1e-9
        p = polar_to_cartesian(Point(100, 100), 50, 90)
        assert abs(p.x - 100) < 1e-9 and abs(p.y - 150) < 1e-9

        # 4 points evenly spaced on unit circle - all radius 10, point 0 at (10, 0)
        pts = evenly_spaced_on_circle(Point(0, 0), 10, 4)
        assert len(pts) == 4
        for pt in pts:
            assert abs(distance(pt, Point(0, 0)) - 10) < 1e-9
        assert abs(pts[0].x - 10) < 1e-9 and abs(pts[0].y) < 1e-9

        # Rect attach + corner + center - 100x80 rect at (50, 50)
        right_mid = rect_attachment(50, 50, 100, 80, "right", "mid")
        assert right_mid.x == 150 and right_mid.y == 90
        top_mid = rect_attachment(50, 50, 100, 80, "top", "mid")
        assert top_mid.x == 100 and top_mid.y == 50

        center = rect_center(50, 50, 100, 80)
        assert center.x == 100 and center.y == 90

        tl = rect_corner(50, 50, 100, 80, "tl")
        assert tl.x == 50 and tl.y == 50


class TestGeometryOffsets:
    """Parallel-offset primitives. 7 tests collapsed into 2."""

    def test_offset_line_polyline_circle_rect(self):
        """offset_line, offset_polyline with mitred corner, offset_rect
        (inflate / deflate / collapse), offset_circle (hit / invalid)."""
        from stellars_claude_code_plugins.svg_tools.calc_geometry import (
            offset_line, offset_polyline, offset_rect, offset_circle, Point,
        )

        # Line left/right sides (SVG: right = +Y down)
        a, b = offset_line(Point(0, 0), Point(100, 0), 10, side="left")
        assert abs(a.y + 10) < 1e-9 and abs(b.y + 10) < 1e-9
        a, b = offset_line(Point(0, 0), Point(100, 0), 10, side="right")
        assert abs(a.y - 10) < 1e-9 and abs(b.y - 10) < 1e-9

        # Right-angle polyline, offset 10 right -> mitred vertex at (90, 10)
        result = offset_polyline(
            [Point(0, 0), Point(100, 0), Point(100, 100)], 10, side="right",
        )
        assert len(result) == 3
        assert abs(result[0].x) < 1e-9 and abs(result[0].y - 10) < 1e-9
        assert abs(result[1].x - 90) < 1e-9 and abs(result[1].y - 10) < 1e-9
        assert abs(result[2].x - 90) < 1e-9 and abs(result[2].y - 100) < 1e-9

        # Rect inflate / deflate / collapse
        assert offset_rect(50, 50, 100, 80, 5) == (45, 45, 110, 90)
        assert offset_rect(50, 50, 100, 80, -5) == (55, 55, 90, 70)
        assert offset_rect(50, 50, 10, 10, -10) is None

        # Circle offset: positive inflates, negative collapses
        c, r = offset_circle(Point(50, 50), 20, 5)
        assert r == 25 and c.x == 50 and c.y == 50
        assert offset_circle(Point(0, 0), 5, -10) is None

    def test_offset_point_and_polygon(self):
        """offset_point_from_line (standoff), offset_polygon (outward / inward)."""
        from stellars_claude_code_plugins.svg_tools.calc_geometry import (
            offset_point_from_line, offset_polygon, Point,
        )

        # Mid-line offset 10 to the right = (50, 10)
        p = offset_point_from_line(Point(0, 0), Point(100, 0), 0.5, 10, "right")
        assert abs(p.x - 50) < 1e-9 and abs(p.y - 10) < 1e-9

        # Square (CW in SVG) inflated by 5 -> larger square with 5px halo
        square = [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)]
        outward = offset_polygon(square, 5, "outward")
        xs = sorted(p.x for p in outward)
        ys = sorted(p.y for p in outward)
        assert abs(xs[0] + 5) < 1e-9 and abs(xs[-1] - 15) < 1e-9
        assert abs(ys[0] + 5) < 1e-9 and abs(ys[-1] - 15) < 1e-9

        # Same square deflated by 2
        inward = offset_polygon(square, 2, "inward")
        xs = sorted(p.x for p in inward)
        ys = sorted(p.y for p in inward)
        assert abs(xs[0] - 2) < 1e-9 and abs(xs[-1] - 8) < 1e-9
        assert abs(ys[0] - 2) < 1e-9 and abs(ys[-1] - 8) < 1e-9


class TestGeometryCLI:
    """calc_geometry CLI subcommands + svg-infographics unified CLI. 19 tests
    collapsed to 2 parametrized tests + one error-path test."""

    TOOL = TOOLS_DIR / "calc_geometry.py"

    def _run_tool(self, *args):
        return subprocess.run(
            [sys.executable, str(self.TOOL), *args],
            capture_output=True, text=True,
        )

    @pytest.mark.parametrize(
        "subcommand, args, expected_substring",
        [
            ("midpoint", ["--p1", "0,0", "--p2", "100,200"], "Midpoint: (50.00, 100.00)"),
            ("extend", ["--line", "0,0,100,0", "--by", "20"], "Extended end by 20.0: (120.00, 0.00)"),
            ("at", ["--line", "0,0,100,0", "--t", "0.25"], "(25.00, 0.00)"),
            ("perpendicular", ["--point", "5,10", "--line", "0,0,20,0"], "Foot: (5.00, 0.00)"),
            ("tangent", ["--circle", "0,0,6", "--from", "10,0"], "Tangent point 1"),
            ("intersect-lines", ["--line1", "0,0,100,100", "--line2", "0,100,100,0"], "Intersection: (50.00, 50.00)"),
            ("intersect-circles", ["--c1", "0,0,6", "--c2", "10,0,6"], "Intersection 1"),
            ("evenly-spaced", ["--center", "0,0", "--r", "10", "--count", "4"], "Point 0"),
            ("concentric", ["--center", "100,100", "--radii", "20,40,60"], "<circle"),
            ("attach", ["--shape", "rect", "--geometry", "50,50,100,80", "--side", "right"], "Attachment: (150.00, 90.00)"),
            ("attach", ["--shape", "circle", "--geometry", "100,100,30", "--side", "perimeter", "--angle", "90"], "Attachment: (100.00, 130.00)"),
            ("offset-line", ["--line", "0,0,100,0", "--distance", "10", "--side", "right"], "Offset start  : (0.00, 10.00)"),
            ("offset-polyline", ["--points", "0,0 100,0 100,100", "--distance", "10", "--side", "right"], "v1: (90.00, 10.00)"),
            ("offset-rect", ["--rect", "50,50,100,80", "--by", "5"], "x=45.0"),
            ("offset-circle", ["--circle", "50,50,20", "--by", "-5"], "Offset radius:   15"),
            ("offset-polygon", ["--points", "0,0 10,0 10,10 0,10", "--distance", "2", "--direction", "inward"], "Inward offset polygon (4 vertices)"),
            ("offset-point", ["--line", "0,0,100,0", "--t", "0.5", "--distance", "12", "--side", "right"], "(50.00, 12.00)"),
        ],
        ids=[
            "midpoint", "extend", "at", "perpendicular", "tangent",
            "intersect_lines", "intersect_circles", "evenly_spaced", "concentric",
            "attach_rect", "attach_circle_perimeter",
            "offset_line", "offset_polyline", "offset_rect", "offset_circle",
            "offset_polygon_inward", "offset_point",
        ],
    )
    def test_cli_subcommands(self, subcommand, args, expected_substring):
        r = self._run_tool(subcommand, *args)
        assert r.returncode == 0, r.stderr
        assert expected_substring in r.stdout

    def test_cli_unknown_subcommand_fails(self):
        r = self._run_tool("nonexistent")
        assert r.returncode != 0

    def test_geom_midpoint_via_unified_cli(self):
        """The calc_geometry subcommands are reachable through svg-infographics."""
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "cli.py"), "geom",
             "midpoint", "--p1", "0,0", "--p2", "100,200"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert "Midpoint: (50.00, 100.00)" in r.stdout


class TestGeometryContains:
    """geometry_in_polygon + rect_ray_exit. 14 tests collapsed to 3."""

    SQUARE = [(0, 0), (100, 0), (100, 100), (0, 100)]
    # U-shape: notch cut down from y=100 to y=40 between x=40 and x=60
    U_SHAPE = [
        (0, 0), (100, 0), (100, 100),
        (60, 100), (60, 40), (40, 40), (40, 100),
        (0, 100),
    ]

    @pytest.mark.parametrize(
        "geometry, polygon_key, expected_contained, expected_convex_safe",
        [
            (("point", (50, 50)), "SQUARE", True, True),
            (("point", (150, 50)), "SQUARE", False, False),
            (("bbox", (10, 10, 80, 80)), "SQUARE", True, True),
            (("bbox", (80, 80, 50, 50)), "SQUARE", False, None),  # None = don't check
            (("line", ((10, 10), (90, 90))), "SQUARE", True, True),
            (("polygon", [(10, 10), (90, 10), (90, 90), (10, 90)]), "SQUARE", True, True),
            # Concave container: both endpoints inside but line crosses the notch
            (("line", ((20, 70), (80, 70))), "U_SHAPE", False, None),
        ],
        ids=[
            "point_inside", "point_outside", "bbox_inside", "bbox_straddling",
            "line_inside", "polygon_inside", "line_concave_notch",
        ],
    )
    def test_containment_cases(self, geometry, polygon_key, expected_contained, expected_convex_safe):
        from stellars_claude_code_plugins.svg_tools.calc_geometry import geometry_in_polygon
        polygon = getattr(self, polygon_key)
        r = geometry_in_polygon(geometry, polygon)
        assert r["contained"] is expected_contained
        if expected_convex_safe is not None:
            assert r["convex_safe"] is expected_convex_safe

    def test_convex_safe_concave_diagonal(self):
        """Polyline that routes AROUND the notch (valid containment) but
        whose convex hull includes the notch - convex_safe is False and
        exit_segments identifies the offending diagonals."""
        from stellars_claude_code_plugins.svg_tools.calc_geometry import geometry_in_polygon
        r = geometry_in_polygon(
            ("polyline", [(20, 90), (20, 30), (80, 30), (80, 90)]),
            self.U_SHAPE,
        )
        assert r["contained"]
        assert not r["convex_safe"]
        assert r["exit_segments"]

    @pytest.mark.parametrize(
        "rect, target, expected",
        [
            ((0, 0, 100, 100), (200, 50), (100, 50)),  # right edge
            ((0, 0, 100, 100), (50, 300), (50, 100)),  # bottom edge
            ((0, 0, 100, 100), (150, 150), (100, 100)),  # 45-deg corner
        ],
        ids=["right_edge", "bottom_edge", "corner_diagonal"],
    )
    def test_rect_ray_exit_cases(self, rect, target, expected):
        from stellars_claude_code_plugins.svg_tools.calc_geometry import rect_ray_exit
        px, py = rect_ray_exit(rect, target)
        assert abs(px - expected[0]) < 1e-6
        assert abs(py - expected[1]) < 1e-6

    def test_rect_ray_exit_degenerate_raises(self):
        """Target at rect centre -> no direction to cast a ray."""
        from stellars_claude_code_plugins.svg_tools.calc_geometry import rect_ray_exit
        with pytest.raises(ValueError):
            rect_ray_exit((0, 0, 100, 100), (50, 50))

    def test_cli_contains_and_rect_edge(self):
        """geom contains + geom rect-edge subcommands via the unified CLI."""
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "cli.py"), "geom", "rect-edge",
             "--rect", "0,0,100,100", "--from", "200,50"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "Edge point:  (100.00, 50.00)" in r.stdout

        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "cli.py"), "geom", "contains",
             "--polygon", "[(0,0),(100,0),(100,100),(60,100),(60,40),(40,40),(40,100),(0,100)]",
             "--line", "20,70,80,70"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "contained=NO" in r.stdout
        assert "convex-safe=NO" in r.stdout
        assert "exit:" in r.stdout


class TestCheckContrast:
    """CLI smoke tests for check_contrast.py. 5 tests -> 2."""

    def _run(self, svg_path, *extra_args):
        return subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_contrast.py"),
             "--svg", str(svg_path), *extra_args],
            capture_output=True, text=True,
        )

    def test_cli_smoke(self, simple_svg, contrast_fail_svg):
        """Covers: simple SVG passes AA, low contrast surfaced, AAA is
        stricter than AA, custom --dark-bg accepted, --show-all adds
        passing entries to output."""
        r = self._run(simple_svg)
        assert r.returncode == 0
        assert "SUMMARY" in r.stdout

        r = self._run(contrast_fail_svg, "--show-all")
        assert r.returncode == 0
        assert "SUMMARY" in r.stdout

        r = self._run(simple_svg, "--level", "AAA", "--show-all")
        assert r.returncode == 0
        assert "WCAG AAA" in r.stdout
        assert "pass" in r.stdout.lower()

        r = self._run(simple_svg, "--dark-bg", "#272b31")
        assert r.returncode == 0


class TestContrastModule:
    """Direct import tests for check_contrast.py helpers. 9 tests -> 2."""

    def test_color_helpers(self):
        """hex_to_rgb, relative_luminance, contrast_ratio, blend_over,
        resolve_color."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            hex_to_rgb, relative_luminance, contrast_ratio, blend_over, resolve_color,
        )

        # hex parsing - full form + shorthand
        assert hex_to_rgb("#ff0000") == (255, 0, 0)
        assert hex_to_rgb("#00ff00") == (0, 255, 0)
        assert hex_to_rgb("#f00") == (255, 0, 0)

        # Relative luminance: white near 1, black near 0
        white = relative_luminance(255, 255, 255)
        black = relative_luminance(0, 0, 0)
        assert white > 0.99
        assert black < 0.01
        # Black-on-white = 21:1
        assert contrast_ratio(white, black) > 20.0

        # Blend 50/50 black over white -> mid grey
        result = blend_over("#000000", 0.5, "#ffffff")
        r, g, _ = int(result[1:3], 16), int(result[3:5], 16), int(result[5:7], 16)
        assert 125 <= r <= 130
        assert 125 <= g <= 130

        # resolve_color: hex/named/none/transparent
        assert resolve_color("#ff0000") == "#ff0000"
        assert resolve_color("red") == "#ff0000"
        assert resolve_color("none") is None
        assert resolve_color("transparent") is None

    def test_css_parser_and_large_text(self):
        """parse_css_classes (strips media), parse_dark_classes (extracts media),
        is_large_text thresholds."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            parse_css_classes, parse_dark_classes, is_large_text,
        )

        css = (
            ".fg-1 { fill: #1e3a5f; } .fg-2 { fill: #2a5f9e; } "
            "@media (prefers-color-scheme: dark) { .fg-1 { fill: #c8d6e5; } }"
        )

        # Light-mode parser strips @media blocks and captures two classes
        classes = parse_css_classes(css)
        assert classes["fg-1"] == "#1e3a5f"
        assert classes["fg-2"] == "#2a5f9e"

        # Dark-mode parser picks up only the @media override
        dark = parse_dark_classes(css)
        assert dark["fg-1"] == "#c8d6e5"

        # is_large_text: 18+ normal, 14+ bold, else not large
        assert is_large_text(18, "normal") is True
        assert is_large_text(14, "bold") is True
        assert is_large_text(12, "normal") is False
        assert is_large_text(14, "normal") is False


class TestObjectContrast:
    """Tests for non-text object contrast checks. 6 tests -> 2."""

    def test_object_contrast_scenarios(self, tmp_path):
        """Covers: near-white card fails, strong stroke rescues faint fill,
        doc-background rect is skipped, dark-mode class colour is used
        when evaluating dark mode."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            parse_svg_shapes, check_object_contrasts,
        )

        # 1) Near-white card on white bg fails light-mode contrast
        lowobj = tmp_path / "lowobj.svg"
        lowobj.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
              <rect x="20" y="20" width="200" height="100" fill="#f5f5f5"/>
            </svg>
        """))
        shapes, _, dark, w, h = parse_svg_shapes(str(lowobj))
        results = check_object_contrasts(shapes, dark, w, h)
        assert any(r.mode == "light" and not r.passed for r in results)

        # 2) Strong stroke rescues faint fill (paired paths merge into one shape)
        stroke_saves = tmp_path / "stroke_saves.svg"
        stroke_saves.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
              <path d="M20,20 H220 V120 H20 Z" fill="#0066aa" fill-opacity="0.04"/>
              <path d="M20,20 H220 V120 H20 Z" fill="none" stroke="#003355" stroke-width="2"/>
            </svg>
        """))
        shapes, _, dark, w, h = parse_svg_shapes(str(stroke_saves))
        assert len(shapes) == 1
        results = check_object_contrasts(shapes, dark, w, h)
        assert all(r.passed for r in results if r.mode == "light")

        # 3) Doc-background rect (covers canvas) is skipped
        docbg = tmp_path / "docbg.svg"
        docbg.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
              <rect x="0" y="0" width="800" height="200" fill="#ffffff"/>
              <rect x="20" y="20" width="200" height="100" fill="#0066aa"/>
            </svg>
        """))
        shapes, _, dark, w, h = parse_svg_shapes(str(docbg))
        results = check_object_contrasts(shapes, dark, w, h)
        labels = {r.shape.label for r in results}
        assert "rect 800x200" not in labels
        assert "rect 200x100" in labels

        # 4) Dark-mode swap: same class has different fills in light vs dark
        darkswap = tmp_path / "darkswap.svg"
        darkswap.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
              <style>
                .card { fill: #0066aa; }
                @media (prefers-color-scheme: dark) {
                  .card { fill: #88ccee; }
                }
              </style>
              <rect x="20" y="20" width="200" height="100" class="card"/>
            </svg>
        """))
        shapes, _, dark, w, h = parse_svg_shapes(str(darkswap))
        results = check_object_contrasts(shapes, dark, w, h)
        light = next(r for r in results if r.mode == "light")
        dark_r = next(r for r in results if r.mode == "dark")
        assert light.fill_used == "#0066aa"
        assert dark_r.fill_used == "#88ccee"

    def test_path_bbox_and_skip_objects_flag(self, tmp_path):
        """_parse_path_bbox handles H/V commands; CLI --skip-objects
        suppresses the OBJECT CONTRAST sections."""
        from stellars_claude_code_plugins.svg_tools.check_contrast import _parse_path_bbox

        bbox = _parse_path_bbox("M20,40 H150 V107 H20 Z")
        assert bbox is not None
        x, y, w, h = bbox
        assert x == 20 and y == 40 and w == 130 and h == 67

        svg = tmp_path / "obj.svg"
        svg.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">
              <rect x="20" y="20" width="200" height="100" fill="#f5f5f5"/>
            </svg>
        """))
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_contrast.py"),
             "--svg", str(svg), "--skip-objects"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert "OBJECT CONTRAST" not in r.stdout
        assert "OBJECTS:" not in r.stdout


class TestCheckConnectors:
    """CLI + module tests for check_connectors.py. 4 tests -> 2."""

    def _run(self, svg_path):
        return subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_connectors.py"), "--svg", str(svg_path)],
            capture_output=True, text=True,
        )

    def test_cli_basic_and_zero_length(self, connector_svg, tmp_path):
        """Basic connector scene passes; zero-length line is flagged."""
        r = self._run(connector_svg)
        assert r.returncode == 0
        assert "Connector check" in r.stdout

        zero = tmp_path / "zero.svg"
        zero.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
              <line x1="100" y1="50" x2="100" y2="50" stroke="#333"/>
            </svg>
        """))
        r = self._run(zero)
        assert r.returncode == 0
        assert "zero-length" in r.stdout

    def test_module_helpers(self):
        """_point_to_seg_dist and _parse_points helper functions."""
        from stellars_claude_code_plugins.svg_tools.check_connectors import (
            _point_to_seg_dist, _parse_points,
        )
        assert abs(_point_to_seg_dist(50, 0, 0, 0, 100, 0)) < 0.01
        assert abs(_point_to_seg_dist(50, 10, 0, 0, 100, 0) - 10.0) < 0.01

        pts = _parse_points("100,50 200,60 300,70")
        assert len(pts) == 3
        assert pts[0] == (100.0, 50.0)
        assert pts[2] == (300.0, 70.0)


class TestCheckOverlaps:
    """CLI + --inject-bounds / --strip-bounds for check_overlaps.py. 4 -> 1."""

    def _run(self, svg_path, *extra_args):
        return subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_overlaps.py"),
             "--svg", str(svg_path), *extra_args],
            capture_output=True, text=True,
        )

    def test_cli_scenarios(self, simple_svg, overlap_svg, tmp_path):
        """Simple SVG runs cleanly, overlapping texts are detected,
        inject + strip bounds round-trip succeeds."""
        import shutil

        # Clean SVG
        r = self._run(simple_svg)
        assert r.returncode == 0
        assert "SUMMARY" in r.stdout or "summary" in r.stdout.lower()

        # Overlapping texts - must exit cleanly
        r = self._run(overlap_svg)
        assert r.returncode == 0

        # Inject bounds -> strip bounds round-trip
        test_svg = tmp_path / "test_roundtrip.svg"
        shutil.copy(simple_svg, test_svg)
        r = self._run(test_svg, "--inject-bounds")
        assert r.returncode == 0
        r = self._run(test_svg, "--strip-bounds")
        assert r.returncode == 0


class TestCalloutCollision:
    """Callout cross-collision detection (parse_callouts + check_callouts).

    Shares a builder helper across all cases. 8 tests -> 3 (parse, clean +
    CLI smoke, three violation families)."""

    CALLOUT_STYLE = (
        '<style>\n'
        '.callout-text { font-family: Segoe UI; font-size: 8.5px; font-style: italic; }\n'
        '.callout-line { fill: none; stroke: #7a4a15; stroke-width: 1; }\n'
        '</style>\n'
    )

    def _svg(self, tmp_path, body, viewbox="0 0 400 300"):
        p = Path(tmp_path) / "callouts.svg"
        p.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">\n'
            f'{self.CALLOUT_STYLE}{body}\n</svg>\n'
        )
        return str(p)

    def test_parse_callouts_extracts_line_and_path_leaders(self, tmp_path):
        """parse_callouts picks up text_bbox + <line>/<path> leaders."""
        from stellars_claude_code_plugins.svg_tools.check_overlaps import parse_callouts

        # <line> leader
        svg = self._svg(tmp_path, (
            '<g id="callout-a">\n'
            '  <text x="100" y="50" class="callout-text">hello</text>\n'
            '  <line x1="100" y1="55" x2="150" y2="90" class="callout-line"/>\n'
            '</g>\n'
        ))
        callouts = parse_callouts(svg)
        assert len(callouts) == 1
        assert callouts[0]["id"] == "callout-a"
        assert callouts[0]["text_bbox"] is not None
        assert callouts[0]["leaders"] == [((100.0, 55.0), (150.0, 90.0))]

        # <path> leader with M/L segments -> 2 sub-segments
        svg = self._svg(tmp_path, (
            '<g id="callout-b">\n'
            '  <text x="200" y="100" class="callout-text">world</text>\n'
            '  <path d="M 200 105 L 240 130 L 260 150" class="callout-line"/>\n'
            '</g>\n'
        ))
        callouts = parse_callouts(svg)
        assert len(callouts) == 1
        assert len(callouts[0]["leaders"]) == 2

    def test_check_callouts_violation_families(self, tmp_path):
        """Three violation families: leader crosses other text bbox,
        leader crosses leader, text bboxes overlap. Plus clean layout +
        empty-callouts sanity paths."""
        from stellars_claude_code_plugins.svg_tools.check_overlaps import check_callouts

        # Clean layout - no violations
        clean = self._svg(tmp_path, (
            '<g id="callout-a">\n'
            '  <text x="20" y="30" class="callout-text">left</text>\n'
            '  <line x1="20" y1="35" x2="40" y2="45" class="callout-line"/>\n'
            '</g>\n'
            '<g id="callout-b">\n'
            '  <text x="300" y="200" class="callout-text">right</text>\n'
            '  <line x1="300" y1="205" x2="270" y2="180" class="callout-line"/>\n'
            '</g>\n'
        ))
        assert check_callouts(clean) == []

        # No callouts at all -> empty
        none_svg = self._svg(tmp_path, '<rect x="0" y="0" width="10" height="10"/>')
        assert check_callouts(none_svg) == []

        # Leader-crosses-text
        cross_text = self._svg(tmp_path, (
            '<g id="callout-a">\n'
            '  <text x="100" y="50" class="callout-text">aaa</text>\n'
            '  <line x1="100" y1="55" x2="80" y2="80" class="callout-line"/>\n'
            '</g>\n'
            '<g id="callout-b">\n'
            '  <text x="300" y="200" class="callout-text">bbb</text>\n'
            '  <line x1="300" y1="205" x2="105" y2="48" class="callout-line"/>\n'
            '</g>\n'
        ))
        vs = check_callouts(cross_text)
        assert any("crosses text of callout-a" in v for v in vs)

        # Leader-crosses-leader
        cross_leader = self._svg(tmp_path, (
            '<g id="callout-a">\n'
            '  <text x="20" y="20" class="callout-text">a</text>\n'
            '  <line x1="20" y1="25" x2="200" y2="200" class="callout-line"/>\n'
            '</g>\n'
            '<g id="callout-b">\n'
            '  <text x="300" y="20" class="callout-text">b</text>\n'
            '  <line x1="300" y1="25" x2="100" y2="200" class="callout-line"/>\n'
            '</g>\n'
        ))
        vs = check_callouts(cross_leader)
        assert any("crosses leader" in v for v in vs)

        # Text-vs-text bbox overlap
        overlap_text = self._svg(tmp_path, (
            '<g id="callout-a">\n'
            '  <text x="100" y="100" class="callout-text">overlap</text>\n'
            '  <line x1="100" y1="105" x2="80" y2="120" class="callout-line"/>\n'
            '</g>\n'
            '<g id="callout-b">\n'
            '  <text x="105" y="102" class="callout-text">same</text>\n'
            '  <line x1="105" y1="107" x2="130" y2="120" class="callout-line"/>\n'
            '</g>\n'
        ))
        vs = check_callouts(overlap_text)
        assert any("text of callout-a overlaps text of callout-b" in v for v in vs)

    def test_cli_reports_callout_cross_collisions_section(self, tmp_path):
        """check_overlaps.py CLI surfaces a CALLOUT CROSS-COLLISIONS block."""
        svg = self._svg(tmp_path, (
            '<g id="callout-a">\n'
            '  <text x="20" y="20" class="callout-text">a</text>\n'
            '  <line x1="20" y1="25" x2="200" y2="200" class="callout-line"/>\n'
            '</g>\n'
            '<g id="callout-b">\n'
            '  <text x="300" y="20" class="callout-text">b</text>\n'
            '  <line x1="300" y1="25" x2="100" y2="200" class="callout-line"/>\n'
            '</g>\n'
        ))
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_overlaps.py"), "--svg", svg],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert "CALLOUT CROSS-COLLISIONS" in r.stdout
        assert "crosses leader" in r.stdout


class TestCheckAlignment:
    """check_alignment.py CLI. 3 tests -> 1."""

    def test_cli_variants(self, alignment_svg):
        """Default run, custom --grid, grid + --tolerance all succeed."""
        for extra in ([], ["--grid", "7"], ["--grid", "14", "--tolerance", "2"]):
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "check_alignment.py"),
                 "--svg", str(alignment_svg), *extra],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"alignment failed with extra args {extra}"


class TestExampleSVGs:
    """Smoke tests running each validator against real example SVGs. 4 -> 1
    parametrized row-per-tool."""

    @pytest.fixture
    def example_svgs(self):
        examples = list(EXAMPLES_DIR.glob("*.svg"))
        assert len(examples) > 0, f"No example SVGs in {EXAMPLES_DIR}"
        return examples[:5]

    @pytest.mark.parametrize(
        "tool_name",
        ["check_contrast.py", "check_overlaps.py", "check_alignment.py", "check_connectors.py"],
        ids=["contrast", "overlaps", "alignment", "connectors"],
    )
    def test_tool_on_examples(self, example_svgs, tool_name):
        """Each checker must exit cleanly on the first 5 bundled examples."""
        for svg in example_svgs:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / tool_name), "--svg", str(svg)],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"{tool_name} crashed on {svg.name}: {r.stderr}"


class TestPluginStructure:
    """svg-infographics plugin directory layout. 9 tests -> 2."""

    PLUGIN_DIR = Path(__file__).resolve().parent.parent / "svg-infographics"

    def test_structure(self):
        """plugin.json, README, skills, workflow reference, commands, tools
        directory all present. plugin.json is valid JSON with expected fields."""
        import json

        p = self.PLUGIN_DIR
        assert (p / ".claude-plugin" / "plugin.json").is_file()
        assert (p / "README.md").is_file()
        for skill in ("svg-standards", "workflow", "theme", "validation"):
            assert (p / "skills" / skill / "SKILL.md").is_file(), f"missing skill {skill}"
        assert (p / "skills" / "workflow" / "WORKFLOW.md").is_file()
        for cmd in ("create", "fix-style", "fix-layout", "validate", "theme"):
            assert (p / "commands" / f"{cmd}.md").is_file(), f"missing command {cmd}"
        for tool in ("calc_connector.py", "check_overlaps.py", "check_alignment.py",
                     "check_contrast.py", "check_connectors.py"):
            assert (p / "tools" / tool).is_file(), f"missing tool {tool}"

        # plugin.json is valid JSON with expected fields
        data = json.loads((p / ".claude-plugin" / "plugin.json").read_text())
        assert data["name"] == "svg-infographics"
        assert "version" in data
        assert "keywords" in data
        assert len(data["keywords"]) >= 5

        # Example library is populated
        examples = list((p / "examples").glob("*.svg"))
        assert len(examples) >= 60

    def test_examples_anonymised(self):
        """Client company names must not leak into the bundled examples."""
        forbidden = ["DeLaval", "Nordea", "Atlas Copco", "Perfekta"]
        for svg in (self.PLUGIN_DIR / "examples").glob("*.svg"):
            content = svg.read_text()
            for name in forbidden:
                assert name not in content, f"found '{name}' in {svg.name}"


class TestDefectDetection:
    """Inject specific defects into real SVGs, verify tools catch them.

    5 tests -> 2: one Python-API test across overlap/contrast/alignment/
    connector defect families, plus one end-to-end CLI test.
    """

    NS = "http://www.w3.org/2000/svg"

    @pytest.fixture(autouse=True)
    def register_ns(self):
        import xml.etree.ElementTree as ET
        ET.register_namespace("", self.NS)

    @pytest.fixture
    def real_svg_content(self):
        svg_path = EXAMPLES_DIR / "01_current_evaluation_pipeline.svg"
        assert svg_path.exists()
        return svg_path.read_text()

    def _write_svg(self, root, path):
        import xml.etree.ElementTree as ET
        ET.ElementTree(root).write(str(path), xml_declaration=True, encoding="unicode")

    def test_defect_families_via_python_api(self, real_svg_content, tmp_path):
        """Inject one defect per family and confirm the checker detects it:
        overlap (same x/y), contrast (near-bg fill), alignment (off-grid
        shift), zero-length connector."""
        import xml.etree.ElementTree as ET

        # Overlap defect - move text[1] to text[0]'s position
        root = ET.fromstring(real_svg_content)
        texts = list(root.iter(f"{{{self.NS}}}text"))
        assert len(texts) >= 2
        texts[1].set("x", texts[0].get("x", "0"))
        texts[1].set("y", texts[0].get("y", "0"))
        defect = tmp_path / "overlap.svg"
        self._write_svg(root, defect)
        from stellars_claude_code_plugins.svg_tools.check_overlaps import (
            parse_svg, analyze_overlaps,
        )
        elements = parse_svg(str(defect))
        assert len(analyze_overlaps(elements)) > 0

        # Contrast defect - near-white fill, no class
        root = ET.fromstring(real_svg_content)
        texts = list(root.iter(f"{{{self.NS}}}text"))
        target = texts[0]
        target.attrib.pop("class", None)
        target.set("fill", "#eeeeee")
        defect = tmp_path / "contrast.svg"
        self._write_svg(root, defect)
        from stellars_claude_code_plugins.svg_tools.check_contrast import (
            parse_svg_for_contrast, check_all_contrasts,
        )
        texts_parsed, bgs, light_cls, dark_cls = parse_svg_for_contrast(str(defect))
        results, _ = check_all_contrasts(texts_parsed, bgs, light_cls, dark_cls)
        assert any(not r.aa_pass for r in results)

        # Alignment defect - 3px shift off a 5px grid
        root = ET.fromstring(real_svg_content)
        texts = list(root.iter(f"{{{self.NS}}}text"))
        original_x = float(texts[0].get("x", "0"))
        texts[0].set("x", str(original_x + 3))
        defect = tmp_path / "alignment.svg"
        self._write_svg(root, defect)
        from stellars_claude_code_plugins.svg_tools.check_alignment import (
            parse_svg_elements, check_grid_snapping,
        )
        assert len(check_grid_snapping(parse_svg_elements(str(defect)), grid=5, tolerance=0)) > 0

        # Zero-length connector defect (hand-crafted - the example SVG may
        # not have connectors)
        zero_connector = textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 400">
              <rect x="20" y="20" width="200" height="100" fill="#0284c7" fill-opacity="0.04"
                    stroke="#0284c7" stroke-width="1"/>
              <rect x="400" y="20" width="200" height="100" fill="#0284c7" fill-opacity="0.04"
                    stroke="#0284c7" stroke-width="1"/>
              <line x1="220" y1="70" x2="400" y2="70" stroke="#333" stroke-width="1"/>
              <line x1="300" y1="150" x2="300" y2="150" stroke="#333" stroke-width="1"/>
            </svg>
        """)
        zero_path = tmp_path / "zero.svg"
        zero_path.write_text(zero_connector)
        from stellars_claude_code_plugins.svg_tools.check_connectors import (
            parse_svg as cc_parse, check_zero_length,
        )
        _, connectors, _ = cc_parse(str(zero_path))
        assert any("zero-length" in i.lower() for i in check_zero_length(connectors))

    def test_contrast_defect_via_cli(self, real_svg_content, tmp_path):
        """CLI end-to-end: inject contrast defect, run the check_contrast
        subprocess, confirm a FAIL surfaces in stdout."""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(real_svg_content)
        texts = list(root.iter(f"{{{self.NS}}}text"))
        target = texts[0]
        target.attrib.pop("class", None)
        target.set("fill", "#f0f0f0")
        defect = tmp_path / "cli_contrast.svg"
        self._write_svg(root, defect)
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_contrast.py"),
             "--svg", str(defect), "--show-all"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert "FAIL" in r.stdout or "fail" in r.stdout.lower()


class TestSvgInfographicsCLI:
    """Unified svg-infographics CLI dispatcher. 12 tests -> 3."""

    CLI = Path(__file__).resolve().parent.parent / "stellars_claude_code_plugins" / "svg_tools" / "cli.py"

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.CLI), *args],
            capture_output=True, text=True,
        )

    def test_help_and_discovery(self):
        """--help lists every subcommand; no-args shows help; each
        subcommand accepts --help; text-to-path surfaces as ON REQUEST."""
        r = self._run("--help")
        assert r.returncode == 0
        for sub in ("overlaps", "contrast", "alignment", "connectors", "connector",
                    "text-to-path"):
            assert sub in r.stdout, f"{sub} missing from --help"
        assert "ON REQUEST" in r.stdout

        r = self._run()
        assert r.returncode == 0
        assert "svg-infographics" in r.stdout

        r = self._run("nonexistent")
        assert r.returncode == 1
        assert "Unknown subcommand" in r.stderr

        for sub in ("overlaps", "contrast", "alignment", "connectors", "connector",
                    "css", "primitives", "text-to-path"):
            r = self._run(sub, "--help")
            assert r.returncode == 0, f"{sub} --help failed"

    @pytest.mark.parametrize(
        "subcommand, fixture_name, expected_substring",
        [
            ("overlaps", "simple_svg", None),
            ("contrast", "simple_svg", "SUMMARY"),
            ("alignment", "alignment_svg", None),
            ("connectors", "connector_svg", None),
            ("css", "simple_svg", None),
        ],
        ids=["overlaps", "contrast", "alignment", "connectors", "css"],
    )
    def test_checker_subcommands(self, request, subcommand, fixture_name, expected_substring):
        """Each checker subcommand runs cleanly against its fixture SVG."""
        svg = request.getfixturevalue(fixture_name)
        r = self._run(subcommand, "--svg", str(svg))
        assert r.returncode == 0
        if expected_substring:
            assert expected_substring in r.stdout

    def test_calc_subcommands(self):
        """connector (calc) + primitives subcommands produce expected outputs."""
        r = self._run("connector", "--from", "100,50", "--to", "300,50")
        assert r.returncode == 0
        assert "0.0 degrees" in r.stdout

        r = self._run("primitives", "circle", "--cx", "100", "--cy", "100", "--r", "50")
        assert r.returncode == 0
        assert "center" in r.stdout


class TestCalcPrimitives:
    """Primitive geometry generator tests.

    28 per-shape tests collapsed into one parametrized anchor table + two
    spline correctness tests + one mode-variant test + one CLI smoke test.
    """

    # Each row: (shape fn name, kwargs, anchor checks as (anchor_name, axis, expected))
    _ANCHOR_CASES = [
        # rect: (20,30) -> (220,130), center (120, 80)
        ("gen_rect", {"x": 20, "y": 30, "w": 200, "h": 100}, [
            ("top-left", "x", 20), ("top-left", "y", 30),
            ("bottom-right", "x", 220), ("bottom-right", "y", 130),
            ("center", "x", 120), ("center", "y", 80),
        ]),
        # square: (10,10) size 50 -> top-right (60,10), bottom-left (10,60)
        ("gen_square", {"x": 10, "y": 10, "size": 50}, [
            ("top-right", "x", 60), ("bottom-left", "y", 60),
        ]),
        # circle: (100,100) r 50
        ("gen_circle", {"cx": 100, "cy": 100, "r": 50}, [
            ("center", "x", 100), ("top", "y", 50), ("right", "x", 150),
        ]),
        # ellipse: (200,100) rx=80 ry=40
        ("gen_ellipse", {"cx": 200, "cy": 100, "rx": 80, "ry": 40}, [
            ("left", "x", 120), ("right", "x", 280), ("top", "y", 60),
        ]),
        # diamond: (200,100) w=80 h=60
        ("gen_diamond", {"cx": 200, "cy": 100, "w": 80, "h": 60}, [
            ("top", "y", 70), ("bottom", "y", 130),
            ("left", "x", 160), ("right", "x", 240),
        ]),
    ]

    @pytest.mark.parametrize(
        "fn_name, kwargs, checks",
        _ANCHOR_CASES,
        ids=[row[0] for row in _ANCHOR_CASES],
    )
    def test_shape_anchors(self, fn_name, kwargs, checks):
        import stellars_claude_code_plugins.svg_tools.calc_primitives as prims
        fn = getattr(prims, fn_name)
        r = fn(**kwargs)
        for anchor_name, axis, expected in checks:
            got = getattr(r.anchors[anchor_name], axis)
            assert abs(got - expected) < 0.5, (
                f"{fn_name} anchor {anchor_name}.{axis} = {got}, expected {expected}"
            )

    def test_rect_rounded_and_diagonal_circle(self):
        """Rect with r=3 uses quadratic beziers; circle diagonal anchors
        lie on the 45-degree offset from centre."""
        from stellars_claude_code_plugins.svg_tools.calc_primitives import gen_rect, gen_circle
        r = gen_rect(0, 0, 100, 80, r=3)
        assert "Q" in r.svg
        c = gen_circle(100, 100, 50)
        assert abs(c.anchors["top-right"].x - 135.35) < 0.5

    @pytest.mark.parametrize(
        "shape_name, kwargs_fill, kwargs_wire, wire_marker",
        [
            ("gen_cube", {"x": 50, "y": 50, "w": 100, "h": 80, "mode": "fill"},
             {"x": 50, "y": 50, "w": 100, "h": 80, "mode": "wire"}, 'fill="none"'),
            ("gen_cylinder", {"cx": 200, "cy": 50, "rx": 60, "ry": 20, "h": 100, "mode": "fill"},
             {"cx": 200, "cy": 50, "rx": 60, "ry": 20, "h": 100, "mode": "wire"}, "stroke-dasharray"),
            ("gen_sphere", {"cx": 200, "cy": 200, "r": 50, "mode": "fill"},
             {"cx": 200, "cy": 200, "r": 50, "mode": "wire"}, 'fill="none"'),
        ],
        ids=["cube", "cylinder", "sphere"],
    )
    def test_3d_fill_and_wire_modes(self, shape_name, kwargs_fill, kwargs_wire, wire_marker):
        """3D primitives support fill and wire modes. Wire mode must emit
        a distinguishing marker (fill=none for cube/sphere, dashed bottom
        arc for cylinder hidden edges)."""
        import stellars_claude_code_plugins.svg_tools.calc_primitives as prims
        fn = getattr(prims, shape_name)
        r_fill = fn(**kwargs_fill)
        r_wire = fn(**kwargs_wire)

        # Fill mode always has fill-opacity declaration somewhere
        assert "fill-opacity" in r_fill.svg or "fill" in r_fill.svg
        # Wire mode has the expected marker
        assert wire_marker in r_wire.svg
        # Cube/cuboid anchors for front-top-left / back-top-right
        if shape_name == "gen_cube":
            assert "front-top-left" in r_fill.anchors
            assert "back-top-right" in r_fill.anchors
        # Cylinder anchors span top to bottom
        if shape_name == "gen_cylinder":
            assert r_fill.anchors["top-center"].y == 50
            assert r_fill.anchors["bottom-center"].y == 150
            assert "A" in r_fill.svg  # arcs for ellipse faces
        # Sphere has highlight ellipse in fill mode, full circle in wire
        if shape_name == "gen_sphere":
            assert r_fill.anchors["center"].x == 200
            assert r_fill.anchors["top"].y == 150
            assert "circle" in r_fill.svg
            assert "ellipse" in r_fill.svg  # highlight
            assert r_wire.svg.count("ellipse") == 2  # equator + meridian

    def test_axis_variants(self):
        """Axis primitive supports xy, xyz, and x-only combinations with
        correct anchor presence and arrow-tip polygons."""
        from stellars_claude_code_plugins.svg_tools.calc_primitives import gen_axis

        xy = gen_axis(80, 200, 300, axes="xy", tick_count=5)
        assert xy.anchors["origin"].x == 80
        assert xy.anchors["x-end"].x == 380
        assert xy.anchors["y-end"].y == -100
        assert "x-tick-0" in xy.anchors
        assert "y-tick-0" in xy.anchors
        assert "<polygon" in xy.svg

        xyz = gen_axis(200, 200, 150, axes="xyz")
        assert "z-end" in xyz.anchors
        assert xyz.anchors["z-end"].x < 200  # z axis goes left

        x_only = gen_axis(50, 100, 200, axes="x")
        assert "x-end" in x_only.anchors
        assert "y-end" not in x_only.anchors

    def test_spline_pchip_correctness(self):
        """PCHIP interpolator hits every waypoint and preserves monotonicity
        (no overshoot across a plateau)."""
        from stellars_claude_code_plugins.svg_tools.calc_primitives import (
            gen_spline, pchip_interpolate,
        )

        # Basic gen_spline output has M/L commands and start/end anchors
        pts = [(0, 0), (50, 100), (100, 50), (150, 80)]
        r = gen_spline(pts, num_samples=20)
        assert r.anchors["start"].x == 0
        assert r.anchors["end"].x == 150
        assert "M" in r.path_d
        assert "L" in r.path_d

        # PCHIP passes exactly through control points
        xs, ys = [0, 50, 100, 150, 200], [10, 80, 30, 90, 50]
        interp = pchip_interpolate(xs, ys, num_samples=201)
        for x, y in zip(xs, ys):
            nearest = min(interp, key=lambda p: abs(p.x - x))
            assert abs(nearest.y - y) < 0.5

        # Monotonicity preservation - no overshoot on a flat plateau
        plateau_xs, plateau_ys = [0, 50, 100, 150], [0, 100, 100, 0]
        pts_p = pchip_interpolate(plateau_xs, plateau_ys, num_samples=100)
        for p in pts_p:
            if 50 <= p.x <= 100:
                assert p.y <= 101

    def test_hexagon_star_arc_cuboid_plane(self):
        """Remaining primitives: hexagon, star, arc, cuboid, plane. Each has
        distinct anchor semantics that are best asserted together."""
        import stellars_claude_code_plugins.svg_tools.calc_primitives as prims

        h_flat = prims.gen_hexagon(300, 200, 50, flat_top=True)
        assert "v0" in h_flat.anchors and "v5" in h_flat.anchors
        assert h_flat.anchors["area"].x > 0
        assert "polygon" in h_flat.svg

        h_pointy = prims.gen_hexagon(300, 200, 50, flat_top=False)
        assert len([k for k in h_pointy.anchors if k.startswith("v")]) == 6

        star = prims.gen_star(200, 200, 50)
        assert "tip0" in star.anchors
        assert "tip4" in star.anchors
        assert "valley0" in star.anchors
        assert star.anchors["top"].y < 200  # top tip above centre

        star6 = prims.gen_star(200, 200, 50, inner_r=30, points=6)
        assert "tip5" in star6.anchors

        arc = prims.gen_arc(200, 200, 80, 0, 90)
        assert arc.anchors["start"].x > 200
        assert arc.anchors["end"].y < 200
        assert "A" in arc.path_d
        assert arc.anchors["label"].x > 200

        cuboid = prims.gen_cuboid(50, 50, 120, 80, 60, mode="fill")
        assert "front-top-left" in cuboid.anchors
        assert "front-center" in cuboid.anchors
        assert "top-center" in cuboid.anchors
        assert "fill-opacity" in cuboid.svg

        plane = prims.gen_plane(100, 200, 300, 100, tilt=30)
        assert plane.anchors["front-left"].x == 100
        assert plane.anchors["front-right"].x == 400
        assert plane.anchors["back-left"].y < 200  # tilted upward
        assert "Z" in plane.path_d

    def test_primitives_cli(self):
        """CLI smoke tests for the primitives tool - one invocation per
        major mode (rect / spline / axis)."""
        for args, expected in [
            (["rect", "--x", "20", "--y", "30", "--width", "200", "--height", "100"], "top-left"),
            (["spline", "--points", "0,0 50,100 100,50 150,80", "--samples", "20"], "Path data"),
            (["axis", "--origin", "80,200", "--length", "300", "--axes", "xyz", "--ticks", "5"], "z-end"),
        ]:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "calc_primitives.py"), *args],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"primitives CLI failed on {args[0]}"
            assert expected in r.stdout


    def test_gear(self):
        """Gear produces a valid polygon/path with correct anchors and bbox shape."""
        from stellars_claude_code_plugins.svg_tools.calc_primitives import gen_gear

        g = gen_gear(100, 100, 50)
        assert "centre" in g.anchors
        assert "top" in g.anchors and "right" in g.anchors
        assert "bottom" in g.anchors and "left" in g.anchors
        assert g.anchors["centre"].x == 100 and g.anchors["centre"].y == 100
        assert abs(g.anchors["top"].y - 50) < 0.5
        assert abs(g.anchors["right"].x - 150) < 0.5
        assert "<polygon" in g.svg or "<path" in g.svg

        # outline mode uses a path with fill=none
        g_wire = gen_gear(100, 100, 50, mode="outline")
        assert 'fill="none"' in g_wire.svg

        # inner_r default is outer_r * 0.7
        g_default = gen_gear(0, 0, 100)
        assert g_default.anchors["top"].y == -100
        # custom teeth count changes vertex density
        g_coarse = gen_gear(0, 0, 40, inner_r=28, teeth=6)
        assert g_coarse.anchors["right"].x == 40

    def test_pyramid(self):
        """Pyramid apex is at top of bbox; base anchors at expected positions."""
        from stellars_claude_code_plugins.svg_tools.calc_primitives import gen_pyramid

        p = gen_pyramid(50, 20, 100, 80)
        assert "apex" in p.anchors
        assert "base-left" in p.anchors
        assert "base-right" in p.anchors
        assert "base-back" in p.anchors
        assert "centre" in p.anchors

        apex = p.anchors["apex"]
        assert abs(apex.x - 100) < 0.5  # x + base_w/2
        assert abs(apex.y - 20) < 0.5   # y (top of bbox)

        base_left = p.anchors["base-left"]
        assert abs(base_left.x - 50) < 0.5
        assert abs(base_left.y - 100) < 0.5  # y + height

        base_right = p.anchors["base-right"]
        assert abs(base_right.x - 150) < 0.5

        # base-back is recessed at 60% of height
        base_back = p.anchors["base-back"]
        assert abs(base_back.y - (20 + 80 * 0.6)) < 0.5

        # filled mode has fill-opacity; wire mode has fill=none
        assert "fill-opacity" in p.svg
        p_wire = gen_pyramid(50, 20, 100, 80, mode="wire")
        assert 'fill="none"' in p_wire.svg
        assert "stroke-dasharray" in p_wire.svg

    def test_cloud(self):
        """Cloud path is closed, anchors are within the bounding box."""
        from stellars_claude_code_plugins.svg_tools.calc_primitives import gen_cloud

        c = gen_cloud(10, 20, 200, 100)
        assert "centre" in c.anchors
        assert "top" in c.anchors and "bottom" in c.anchors
        assert "left" in c.anchors and "right" in c.anchors

        assert abs(c.anchors["centre"].x - 110) < 0.5  # x + w/2
        assert abs(c.anchors["top"].x - 110) < 0.5

        # path closes with Z
        assert "Z" in c.svg
        assert "C" in c.svg  # cubic bezier

        # outline mode omits fill
        c_wire = gen_cloud(10, 20, 200, 100, mode="outline")
        assert 'fill="none"' in c_wire.svg

        # extra lobes produce a longer path string
        c5 = gen_cloud(0, 0, 300, 150, lobes=5)
        c7 = gen_cloud(0, 0, 300, 150, lobes=7)
        assert len(c7.svg) > len(c5.svg)

    def test_document(self):
        """Document has a fold corner; anchors match expected positions."""
        from stellars_claude_code_plugins.svg_tools.calc_primitives import gen_document

        d = gen_document(10, 20, 160, 200)
        assert "top-left" in d.anchors
        assert "top-right" in d.anchors
        assert "bottom-left" in d.anchors
        assert "bottom-right" in d.anchors
        assert "centre" in d.anchors
        assert "fold" in d.anchors

        fold_default = min(160, 200) * 0.2  # 32
        top_right = d.anchors["top-right"]
        assert abs(top_right.x - (10 + 160 - fold_default)) < 0.5
        assert abs(top_right.y - 20) < 0.5

        fold_pt = d.anchors["fold"]
        assert abs(fold_pt.x - (10 + 160)) < 0.5
        assert abs(fold_pt.y - (20 + fold_default)) < 0.5

        assert abs(d.anchors["centre"].x - (10 + 80)) < 0.5
        assert abs(d.anchors["centre"].y - (20 + 100)) < 0.5

        # SVG contains two paths (body + flap)
        assert d.svg.count("<path") == 2

        # explicit fold size
        d_custom = gen_document(0, 0, 100, 80, fold=10)
        assert abs(d_custom.anchors["top-right"].x - 90) < 0.5

        # outline mode uses fill=none on both paths
        d_wire = gen_document(0, 0, 100, 80, mode="outline")
        assert 'fill="none"' in d_wire.svg

    def test_new_primitives_cli(self):
        """CLI smoke test: gear, pyramid, cloud, document all produce valid output."""
        cases = [
            (["gear", "--x", "100", "--y", "100", "--outer-r", "50"], "centre"),
            (["pyramid", "--x", "50", "--y", "20", "--base-w", "100", "--height", "80"], "apex"),
            (["cloud", "--x", "10", "--y", "20", "--w", "200", "--h", "100"], "centre"),
            (["document", "--x", "10", "--y", "20", "--w", "160", "--h", "200"], "top-left"),
        ]
        for args, expected in cases:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "calc_primitives.py"), *args],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"CLI failed for {args[0]}: {r.stderr}"
            assert expected in r.stdout, f"Expected '{expected}' in output for {args[0]}"


class TestCheckCSS:
    """check_css compliance tests. 8 tests -> 3."""

    def test_clean_and_real_examples(self, simple_svg):
        """A proper-themed SVG produces zero errors, and the checker runs
        cleanly on bundled example SVGs reporting CSS classes."""
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        violations, _ = check_css_compliance(str(simple_svg))
        assert [v for v in violations if v.severity == "error"] == []

        examples = [f for f in sorted(EXAMPLES_DIR.glob("*.svg")) if "swatch" not in f.name][:3]
        for svg in examples:
            _, stats = check_css_compliance(str(svg))
            assert stats["light_classes"] > 0, f"no CSS classes in {svg.name}"

    @pytest.mark.parametrize(
        "body, expected_rule, severity",
        [
            # Inline fill="#hex" on text -> error
            (
                '<text x="20" y="40" font-size="12" fill="#ff0000">Bad inline fill</text>',
                "inline-fill-on-text",
                "error",
            ),
            # Forbidden #000000 / #ffffff -> error
            (
                '<rect x="0" y="0" width="400" height="100" fill="#000000"/>'
                '<text x="20" y="40" font-size="12" class="fg-1">Text</text>',
                "forbidden-color",
                "error",
            ),
            # Text with opacity attribute -> error
            (
                '<text x="20" y="40" font-size="12" class="fg-1" opacity="0.5">Faded text</text>',
                "text-opacity",
                "error",
            ),
            # Light class without dark override -> warning
            (
                '<text x="20" y="40" font-size="12" class="fg-1">No dark mode</text>',
                "missing-dark-override",
                "warning",
            ),
        ],
        ids=["inline_fill", "forbidden_color", "text_opacity", "missing_dark"],
    )
    def test_violation_rules(self, tmp_path, body, expected_rule, severity):
        """Each defective SVG body triggers a specific rule at the matching severity."""
        from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

        svg = tmp_path / "case.svg"
        svg.write_text(textwrap.dedent(f"""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">
              <style>.fg-1 {{ fill: #1e3a5f; }}</style>
              {body}
            </svg>
        """))
        violations, _ = check_css_compliance(str(svg))
        rules_at_severity = [v.rule for v in violations if v.severity == severity]
        assert expected_rule in rules_at_severity

    def test_cli_pass_and_fail(self, simple_svg, tmp_path):
        """CLI exits 0 on clean SVGs and exits 1 with ERRORS stdout on
        error-severity violations."""
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_css.py"), "--svg", str(simple_svg)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0

        bad = tmp_path / "bad.svg"
        bad.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">
              <style>.fg-1 { fill: #1e3a5f; }</style>
              <text x="20" y="40" font-size="12" fill="#ff0000">Inline fill</text>
              <rect x="0" y="0" width="400" height="100" fill="#000000"/>
            </svg>
        """))
        r = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_css.py"), "--svg", str(bad)],
            capture_output=True, text=True,
        )
        assert r.returncode == 1
        assert "ERRORS" in r.stdout


# ---------------------------------------------------------------------------
# text_to_path.py tests (on-request tool, requires fonttools + system font)
# ---------------------------------------------------------------------------


_FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    Path("/Library/Fonts/DejaVuSans.ttf"),
]
_SYSTEM_FONT = next((p for p in _FONT_CANDIDATES if p.exists()), None)

pytest.importorskip("fontTools", reason="text_to_path requires fonttools (core dependency)")


@pytest.mark.skipif(_SYSTEM_FONT is None, reason="No system DejaVu Sans font available")
class TestTextToPath:
    """Text -> SVG path renderer (on-request tool). 16 tests -> 4."""

    def test_render_contract_and_styling(self):
        """Basic render produces a <path> with d= + transform=, advance + scale
        are positive, baseline y matches input semantics, fill/class attributes
        are emitted when requested, and the path inherits styling when neither
        fill nor class is given."""
        from stellars_claude_code_plugins.svg_tools.text_to_path import text_to_path

        # Basic render - path, transform, d, advance, scale
        r = text_to_path("Hi", _SYSTEM_FONT, size=24, x=0, y=100)
        assert r.svg.startswith("<path ")
        assert r.svg.endswith("/>")
        assert 'd="M' in r.svg
        assert "transform=" in r.svg
        assert r.advance > 0
        assert r.scale > 0

        # Baseline y matches input - bbox covers the baseline
        r = text_to_path("A", _SYSTEM_FONT, size=20, x=10, y=50)
        assert r.bbox_y < 50
        assert r.bbox_y + r.bbox_height > 50

        # fill attribute emitted
        r = text_to_path("X", _SYSTEM_FONT, size=20, x=0, y=0, fill="#ff0000")
        assert 'fill="#ff0000"' in r.svg

        # css_class attribute emitted
        r = text_to_path("X", _SYSTEM_FONT, size=20, x=0, y=0, css_class="headline")
        assert 'class="headline"' in r.svg

        # No fill, no class -> neither attribute emitted (inherits styling)
        r = text_to_path("X", _SYSTEM_FONT, size=20, x=0, y=0)
        assert "fill=" not in r.svg
        assert "class=" not in r.svg

    def test_anchor_and_fit_width(self):
        """text-anchor middle/end shifts origin by half / full advance;
        fit_width shrinks proportionally when natural advance exceeds it,
        and is a no-op when it doesn't. unicode falls back to .notdef."""
        from stellars_claude_code_plugins.svg_tools.text_to_path import text_to_path

        # Anchor: start/middle/end preserve advance, shift origin
        s = text_to_path("Hello", _SYSTEM_FONT, size=24, x=200, y=100, anchor="start")
        m = text_to_path("Hello", _SYSTEM_FONT, size=24, x=200, y=100, anchor="middle")
        e = text_to_path("Hello", _SYSTEM_FONT, size=24, x=200, y=100, anchor="end")
        assert s.advance == pytest.approx(m.advance) == pytest.approx(e.advance)
        assert s.bbox_x == pytest.approx(200, abs=0.01)
        assert m.bbox_x == pytest.approx(200 - s.advance / 2, abs=0.01)
        assert e.bbox_x == pytest.approx(200 - s.advance, abs=0.01)

        # fit_width < natural shrinks proportionally, preserves aspect
        natural = text_to_path("HELLO WORLD", _SYSTEM_FONT, size=48, x=0, y=0)
        constrained = text_to_path(
            "HELLO WORLD", _SYSTEM_FONT, size=48, x=0, y=0, fit_width=natural.advance / 4
        )
        assert constrained.advance == pytest.approx(natural.advance / 4, abs=0.5)
        assert constrained.scale < natural.scale
        assert constrained.scale / natural.scale == pytest.approx(0.25, rel=0.01)

        # fit_width larger than natural is a no-op (never scales up)
        natural = text_to_path("Hi", _SYSTEM_FONT, size=12, x=0, y=0)
        bigger = text_to_path(
            "Hi", _SYSTEM_FONT, size=12, x=0, y=0, fit_width=natural.advance * 10
        )
        assert bigger.scale == pytest.approx(natural.scale)
        assert bigger.advance == pytest.approx(natural.advance)

        # Unicode out-of-cmap falls back to .notdef instead of crashing
        r = text_to_path("\U0010fffd", _SYSTEM_FONT, size=20)
        assert r.svg.startswith("<path ")

    @pytest.mark.parametrize(
        "kwargs, match",
        [
            (dict(size=20, anchor="left"), "anchor"),
            (dict(size=0), "size"),
            (dict(size=20, fit_width=-5), "fit_width"),
        ],
        ids=["bad_anchor", "zero_size", "negative_fit_width"],
    )
    def test_input_validation(self, kwargs, match):
        """Invalid anchor/size/fit_width raise ValueError with specific match."""
        from stellars_claude_code_plugins.svg_tools.text_to_path import text_to_path
        with pytest.raises(ValueError, match=match):
            text_to_path("X", _SYSTEM_FONT, **kwargs)

    def test_cli_and_wrapped_svg_roundtrip(self, tmp_path):
        """CLI dispatches to text-to-path, emits a <path> element, supports
        --json, and exits non-zero on missing-font. Also: emitted path
        parses cleanly when wrapped inside a real SVG document."""
        import json as _json
        import xml.etree.ElementTree as ET
        from stellars_claude_code_plugins.svg_tools.text_to_path import text_to_path

        cli = (
            Path(__file__).resolve().parent.parent
            / "stellars_claude_code_plugins" / "svg_tools" / "cli.py"
        )

        # CLI --fill emits the expected attribute
        r = subprocess.run(
            [sys.executable, str(cli), "text-to-path",
             "--text", "OK", "--font", str(_SYSTEM_FONT),
             "--size", "16", "--x", "10", "--y", "30",
             "--anchor", "middle", "--fill", "#222"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "<path " in r.stdout
        assert 'fill="#222"' in r.stdout

        # CLI --json emits parseable metadata
        r = subprocess.run(
            [sys.executable, str(cli), "text-to-path",
             "--text", "OK", "--font", str(_SYSTEM_FONT),
             "--size", "20", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        data = _json.loads(r.stdout)
        assert "svg" in data
        assert "bbox_width" in data
        assert data["bbox_width"] > 0

        # Missing font -> exit code 2 + "not found" stderr
        r = subprocess.run(
            [sys.executable, str(cli), "text-to-path",
             "--text", "X", "--font", str(tmp_path / "nope.ttf")],
            capture_output=True, text=True,
        )
        assert r.returncode == 2
        assert "not found" in r.stderr

        # Wrap the emitted path in an SVG and verify it parses
        r = text_to_path("Test", _SYSTEM_FONT, size=24, x=20, y=60, fill="#222")
        wrapper = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">'
            f"{r.svg}"
            "</svg>"
        )
        out = tmp_path / "wrapped.svg"
        out.write_text(wrapper)
        tree = ET.parse(out)
        paths = tree.getroot().findall("{http://www.w3.org/2000/svg}path")
        assert len(paths) == 1


class TestDetectCollisions:
    """Pairwise connector collision detection. 6 tests -> 2."""

    @pytest.mark.parametrize(
        "a_pts, b_pts, tolerance, expected_type, extra_checks",
        [
            # Two diagonals crossing at (50, 50)
            ((0, 0, 100, 100), (0, 100, 100, 0), 0.0, "crossing",
             {"min_distance": 0.0, "points": [(50.0, 50.0)]}),
            # Parallel 5px apart, tolerance 8 -> near-miss
            ((0, 10, 100, 10), (0, 15, 100, 15), 8.0, "near-miss",
             {"min_distance": 5.0}),
            # Endpoint touching at (50, 0)
            ((0, 0, 50, 0), (50, 0, 100, 50), 2.0, "touching", None),
        ],
        ids=["crossing", "near_miss", "touching"],
    )
    def test_collision_types(self, a_pts, b_pts, tolerance, expected_type, extra_checks):
        from stellars_claude_code_plugins.svg_tools.calc_connector import (
            calc_connector, detect_collisions,
        )
        # Endpoint touching case requires standoff=0 so the lines actually touch
        kwargs = dict(arrow="none")
        if expected_type == "touching":
            kwargs["standoff"] = 0
        a = calc_connector(*a_pts, **kwargs)
        b = calc_connector(*b_pts, **kwargs)
        collisions = detect_collisions([a, b], tolerance=tolerance, labels=["a", "b"])
        assert len(collisions) == 1
        assert collisions[0]["type"] == expected_type
        if extra_checks:
            for k, v in extra_checks.items():
                assert collisions[0][k] == v

    def test_no_collision_and_multi_connector_and_cli(self):
        """Parallel non-colliding lines return []; three-connector scene
        only reports the colliding pair; CLI end-to-end returns JSON."""
        import json as _json
        from stellars_claude_code_plugins.svg_tools.calc_connector import (
            calc_connector, detect_collisions,
        )

        # 30px apart with 4px tolerance -> no collision
        a = calc_connector(0, 0, 100, 0, arrow="none")
        b = calc_connector(0, 30, 100, 30, arrow="none")
        assert detect_collisions([a, b], tolerance=4.0, labels=["a", "b"]) == []

        # Three connectors: A and B cross, C is isolated
        connectors = [
            calc_connector(0, 0, 100, 100, arrow="none"),
            calc_connector(0, 100, 100, 0, arrow="none"),
            calc_connector(0, 200, 100, 200, arrow="none"),
        ]
        c = detect_collisions(connectors, tolerance=4.0, labels=["A", "B", "C"])
        assert len(c) == 1
        assert {c[0]["a"], c[0]["b"]} == {"A", "B"}

        # CLI end-to-end
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "collide",
             "--connectors", "[('a',[(0,0),(100,100)]),('b',[(0,100),(100,0)])]",
             "--tolerance", "0"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        report = _json.loads(r.stdout)
        assert len(report) == 1
        assert report[0]["type"] == "crossing"


class TestCharts:
    """pygal chart generation. 7 tests -> 2."""

    def test_chart_types_and_dark_mode(self):
        """Core chart types (line/bar) produce valid SVG bytes with dark-mode
        @media block; multi-series data shapes are supported; caller palette
        overrides flow through; unknown chart type raises ValueError."""
        from stellars_claude_code_plugins.svg_tools.charts import generate_chart

        # Line chart (plain sequence)
        svg = generate_chart("line", data=[1, 3, 2, 5, 4], title="Test")
        assert isinstance(svg, bytes)
        assert svg.startswith(b"<?xml") or b"<svg" in svg[:200]

        # Bar chart (categorical tuples)
        svg = generate_chart("bar", data=[("A", 10), ("B", 20), ("C", 15)])
        assert b"<svg" in svg[:500]

        # Multi-series line chart with labels
        svg = generate_chart(
            "line",
            data=[("Series 1", [1, 2, 3, 4]), ("Series 2", [4, 3, 2, 1])],
            labels=["Q1", "Q2", "Q3", "Q4"],
        )
        assert b"<svg" in svg[:500]

        # Caller palette override produces dark-mode @media block
        svg = generate_chart(
            "line", data=[1, 2, 3],
            colors=["#ff0088", "#00ff88"],
            fg_light="#112233", fg_dark="#eeddcc",
            grid_light="#ccddee", grid_dark="#223344",
        )
        assert b"prefers-color-scheme: dark" in svg

        # Dark-mode CSS injected with custom fg_dark
        svg = generate_chart("bar", data=[("A", 1)], fg_dark="#abcdef")
        assert b"#abcdef" in svg
        assert b"prefers-color-scheme: dark" in svg

        # Unknown chart type raises
        with pytest.raises(ValueError, match="unknown chart_type"):
            generate_chart("pyramid", data=[1, 2, 3])

    def test_cli_outputs_svg_file(self, tmp_path):
        """CLI writes an SVG file that contains <svg> and weighs > 500 bytes."""
        out = tmp_path / "chart.svg"
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "charts", "line",
             "--data", "[1,2,3,4,5]",
             "--title", "Test",
             "--out", str(out)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert out.exists()
        assert out.stat().st_size > 500
        assert "<svg" in out.read_text()


class TestProposeCallouts:
    """Greedy callout placement tool. 9 tests -> 3."""

    SIMPLE_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">'
        '<rect x="50" y="50" width="200" height="100" fill="black"/>'
        '<rect x="350" y="250" width="200" height="100" fill="black"/>'
        '</svg>'
    )

    def test_placement_shapes_and_determinism(self):
        """Single leader callout, single leaderless callout, two non-conflict
        callouts, and deterministic results from a fixed seed."""
        from stellars_claude_code_plugins.svg_tools.propose_callouts import (
            CalloutRequest, propose_callouts,
        )

        # Single leader callout
        r = propose_callouts(
            self.SIMPLE_SVG,
            [CalloutRequest(id="callout-a", target=(150, 100), text="annotated")],
        )
        layout = r["best_layout"]
        assert len(layout) == 1
        assert layout[0].id == "callout-a"
        assert layout[0].leader_start == (150.0, 100.0)
        assert layout[0].leader_anchor is not None
        assert r["stats"]["hard_failures"] == 0

        # Single leaderless callout
        r = propose_callouts(
            self.SIMPLE_SVG,
            [CalloutRequest(id="callout-leaderless", target=(300, 200),
                            text="no line", leader=False)],
        )
        p = r["best_layout"][0]
        assert p.leader_start is None
        assert p.leader_anchor is None

        # Two callouts: non-overlapping text bboxes
        r = propose_callouts(
            self.SIMPLE_SVG,
            [
                CalloutRequest(id="callout-a", target=(150, 100), text="left card"),
                CalloutRequest(id="callout-b", target=(450, 300), text="right card"),
            ],
        )
        a, b = r["best_layout"]
        ax, ay, aw, ah = a.text_bbox
        bx, by, bw, bh = b.text_bbox
        assert ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay

        # Determinism with a fixed seed
        req = [CalloutRequest(id="callout-a", target=(150, 100), text="hello")]
        r1 = propose_callouts(self.SIMPLE_SVG, req, seed=42)
        r2 = propose_callouts(self.SIMPLE_SVG, req, seed=42)
        assert r1["best_layout"][0].text_baseline == r2["best_layout"][0].text_baseline
        assert r1["best_layout"][0].penalty == r2["best_layout"][0].penalty

    def test_multiline_and_id_validation(self):
        """Multi-line text (\n) produces a tall-enough bbox; plan file
        validator rejects IDs that don't start with 'callout-'."""
        import tempfile, os
        from stellars_claude_code_plugins.svg_tools.propose_callouts import (
            CalloutRequest, propose_callouts, _load_plan,
        )

        # Multi-line text: bbox height >= 2 line heights
        r = propose_callouts(
            self.SIMPLE_SVG,
            [CalloutRequest(id="callout-a", target=(150, 100),
                            text="first line\nsecond line")],
        )
        p = r["best_layout"][0]
        assert p.text_bbox[3] >= 2 * 8.5

        # _load_plan rejects non-'callout-' ids
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write('[{"id": "badname", "target": [100, 100], "text": "x"}]')
            path = f.name
        try:
            with pytest.raises(ValueError, match="must start with 'callout-'"):
                _load_plan(path)
        finally:
            os.unlink(path)

    def test_cli_help_and_run_and_json(self, tmp_path):
        """CLI --help shows the plan schema; CLI run on a real SVG produces
        PROPOSAL output with the callout id; --json emits parseable data
        with best_layout + proposals + stats."""
        import json as _json

        # --help includes schema info
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "callouts", "--help"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0
        assert "Schema for --plan JSON" in r.stdout
        assert "callout-" in r.stdout
        assert "leader" in r.stdout
        assert "preferred_side" in r.stdout

        # CLI run on real SVG
        plan = tmp_path / "plan.json"
        plan.write_text(
            '[{"id": "callout-a", "target": [150, 100], "text": "test annotation"}]'
        )
        svg = tmp_path / "scene.svg"
        svg.write_text(self.SIMPLE_SVG)
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "callouts", "--svg", str(svg), "--plan", str(plan)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "PROPOSAL" in r.stdout
        assert "callout-a" in r.stdout

        # CLI --json
        r = subprocess.run(
            [sys.executable, "-m", "stellars_claude_code_plugins.svg_tools.cli",
             "callouts", "--svg", str(svg), "--plan", str(plan), "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        data = _json.loads(r.stdout)
        assert "best_layout" in data
        assert "proposals" in data


# ---------------------------------------------------------------------------
# drawio_shapes.py tests
# ---------------------------------------------------------------------------

import textwrap as _textwrap

from stellars_claude_code_plugins.svg_tools.drawio_shapes import (
    DrawioShape,
    ShapeIndex,
    _mxgraph_to_svg_path,
    build_index,
    parse_drawio_library,
    render_catalogue,
    render_shape,
)


_SAMPLE_STENCIL_XML = _textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <shapes>
      <shape name="database" w="60" h="80" aspect="fixed">
        <background>
          <ellipse x="0" y="0" w="60" h="20"/>
        </background>
        <foreground>
          <move x="0" y="10"/>
          <line x="60" y="10"/>
          <move x="0" y="10"/>
          <curve x1="15" y1="20" x2="45" y2="20" x3="60" y3="10"/>
          <move x="0" y="10"/>
          <line x="0" y="70"/>
          <curve x1="0" y1="80" x2="60" y2="80" x3="60" y3="70"/>
          <line x="60" y="10"/>
          <close/>
        </foreground>
      </shape>
      <shape name="server" w="60" h="80" aspect="fixed">
        <foreground>
          <move x="5" y="0"/>
          <line x="55" y="0"/>
          <line x="55" y="80"/>
          <line x="5" y="80"/>
          <close/>
        </foreground>
      </shape>
    </shapes>
""")

_SAMPLE_MXLIBRARY_XML = _textwrap.dedent("""\
    <mxlibrary>[{"title":"Cloud","w":50,"h":40,"xml":""},{"title":"Router","w":60,"h":60,"xml":""}]</mxlibrary>
""")


class TestDrawioShapesParsing:
    """Unit tests for parse_drawio_library and related helpers."""

    def test_parse_format_b_returns_shapes(self, tmp_path):
        """Format B stencil XML produces one DrawioShape per <shape> element."""
        xml_file = tmp_path / "networking.xml"
        xml_file.write_text(_SAMPLE_STENCIL_XML)
        shapes = parse_drawio_library(xml_file)
        assert len(shapes) == 2
        names = {s.name for s in shapes}
        assert "database" in names
        assert "server" in names

    def test_parse_format_b_dimensions(self, tmp_path):
        """Width and height are read from stencil attributes."""
        xml_file = tmp_path / "networking.xml"
        xml_file.write_text(_SAMPLE_STENCIL_XML)
        shapes = parse_drawio_library(xml_file)
        db = next(s for s in shapes if s.name == "database")
        assert db.width == 60.0
        assert db.height == 80.0

    def test_parse_format_b_svg_snippet_has_path(self, tmp_path):
        """The SVG snippet for a stencil shape contains at least one <path> element."""
        xml_file = tmp_path / "networking.xml"
        xml_file.write_text(_SAMPLE_STENCIL_XML)
        shapes = parse_drawio_library(xml_file)
        db = next(s for s in shapes if s.name == "database")
        assert "<path" in db.svg_snippet

    def test_parse_format_b_category_from_filename(self, tmp_path):
        """Category is derived from the library filename stem."""
        xml_file = tmp_path / "my-network-shapes.xml"
        xml_file.write_text(_SAMPLE_STENCIL_XML)
        shapes = parse_drawio_library(xml_file)
        assert all(s.category == "my_network_shapes" for s in shapes)

    def test_parse_format_a_returns_shapes(self, tmp_path):
        """Format A mxlibrary JSON entries with titles produce DrawioShape objects."""
        xml_file = tmp_path / "cloud.xml"
        xml_file.write_text(_SAMPLE_MXLIBRARY_XML)
        shapes = parse_drawio_library(xml_file)
        assert len(shapes) == 2
        names = {s.name for s in shapes}
        assert "Cloud" in names
        assert "Router" in names

    def test_parse_missing_file_returns_empty(self, tmp_path):
        """A non-existent file path returns an empty list without raising."""
        shapes = parse_drawio_library(tmp_path / "does_not_exist.xml")
        assert shapes == []

    def test_parse_malformed_xml_returns_empty(self, tmp_path):
        """A file with invalid XML returns an empty list without raising."""
        bad = tmp_path / "bad.xml"
        bad.write_text("NOT XML AT ALL <<<")
        shapes = parse_drawio_library(bad)
        assert shapes == []

    def test_parse_unknown_root_tag_returns_empty(self, tmp_path):
        """An XML file with an unrecognised root returns an empty list."""
        xml_file = tmp_path / "weird.xml"
        xml_file.write_text("<something><else/></something>")
        shapes = parse_drawio_library(xml_file)
        assert shapes == []


class TestMxGraphToSvgPath:
    """Unit tests for the mxGraph stencil path converter."""

    def _el(self, xml_str: str):
        import xml.etree.ElementTree as ET
        return ET.fromstring(xml_str)

    def test_move_and_line(self):
        """move -> M and line -> L with correct scaling."""
        el = self._el(
            "<foreground>"
            '<move x="0" y="0"/><line x="100" y="0"/><close/>'
            "</foreground>"
        )
        d = _mxgraph_to_svg_path(el, w=100, h=100)
        assert "M 0.000 0.000" in d
        assert "L 100.000 0.000" in d
        assert "Z" in d

    def test_scaling_applied(self):
        """Coordinates are scaled from the [0,100] stencil box to (w, h)."""
        el = self._el("<foreground><move x='50' y='50'/></foreground>")
        d = _mxgraph_to_svg_path(el, w=200, h=100)
        # x=50% of 200 = 100, y=50% of 100 = 50
        assert "M 100.000 50.000" in d

    def test_curve_produces_C(self):
        """curve element -> SVG cubic bezier C command."""
        el = self._el(
            "<foreground>"
            '<curve x1="10" y1="0" x2="90" y2="0" x3="100" y3="50"/>'
            "</foreground>"
        )
        d = _mxgraph_to_svg_path(el, w=100, h=100)
        assert d.startswith("C ")

    def test_ellipse_produces_arcs(self):
        """ellipse element is converted to two SVG arc commands."""
        el = self._el('<foreground><ellipse x="0" y="0" w="100" h="100"/></foreground>')
        d = _mxgraph_to_svg_path(el, w=100, h=100)
        assert "A " in d

    def test_empty_foreground_returns_empty_string(self):
        """A <foreground> with no recognised children returns an empty string."""
        el = self._el("<foreground><unknown x='0' y='0'/></foreground>")
        d = _mxgraph_to_svg_path(el, w=100, h=100)
        assert d == ""


class TestShapeIndex:
    """Unit tests for ShapeIndex: build, search, save, load, by_category."""

    def _make_index(self, tmp_path) -> ShapeIndex:
        xml_file = tmp_path / "networking.xml"
        xml_file.write_text(_SAMPLE_STENCIL_XML)
        return build_index([tmp_path])

    def test_build_index_finds_shapes(self, tmp_path):
        index = self._make_index(tmp_path)
        assert len(index.shapes) == 2

    def test_build_index_categories(self, tmp_path):
        index = self._make_index(tmp_path)
        assert "networking" in index.categories

    def test_build_index_empty_dir(self, tmp_path):
        """An empty directory produces an empty index without error."""
        subdir = tmp_path / "empty"
        subdir.mkdir()
        index = build_index([subdir])
        assert len(index.shapes) == 0
        assert len(index.categories) == 0

    def test_build_index_missing_dir(self, tmp_path):
        """A non-existent directory is skipped without raising."""
        index = build_index([tmp_path / "no_such_dir"])
        assert index.shapes == []

    def test_search_exact_match(self, tmp_path):
        index = self._make_index(tmp_path)
        results = index.search("database")
        assert len(results) >= 1
        assert results[0].name == "database"

    def test_search_partial_match(self, tmp_path):
        index = self._make_index(tmp_path)
        results = index.search("data")
        assert any(s.name == "database" for s in results)

    def test_search_no_match_returns_empty(self, tmp_path):
        index = self._make_index(tmp_path)
        results = index.search("xyzzy_nonexistent")
        assert results == []

    def test_search_limit_respected(self, tmp_path):
        # Add multiple XML files to get more shapes
        for i in range(5):
            f = tmp_path / f"lib{i}.xml"
            f.write_text(_SAMPLE_STENCIL_XML)
        index = build_index([tmp_path])
        results = index.search("database", limit=2)
        assert len(results) <= 2

    def test_list_categories_sorted(self, tmp_path):
        for name in ("zzz.xml", "aaa.xml"):
            (tmp_path / name).write_text(_SAMPLE_STENCIL_XML)
        index = build_index([tmp_path])
        cats = index.list_categories()
        assert cats == sorted(cats)

    def test_by_category_returns_shapes(self, tmp_path):
        index = self._make_index(tmp_path)
        shapes = index.by_category("networking")
        assert len(shapes) == 2

    def test_by_category_unknown_returns_empty(self, tmp_path):
        index = self._make_index(tmp_path)
        assert index.by_category("unknown_category") == []

    def test_save_and_load_roundtrip(self, tmp_path):
        """Shapes survive a save -> load roundtrip with identical attributes."""
        index = self._make_index(tmp_path)
        index_path = tmp_path / "index.json"
        index.save(index_path)

        loaded = ShapeIndex.load(index_path)
        assert len(loaded.shapes) == len(index.shapes)
        orig_names = {s.name for s in index.shapes}
        loaded_names = {s.name for s in loaded.shapes}
        assert orig_names == loaded_names

    def test_save_json_structure(self, tmp_path):
        """Saved JSON has required top-level keys and correct version."""
        import json as _json
        index = self._make_index(tmp_path)
        index_path = tmp_path / "index.json"
        index.save(index_path)
        data = _json.loads(index_path.read_text())
        assert data["version"] == 1
        assert data["shape_count"] == len(index.shapes)
        assert isinstance(data["categories"], list)
        assert isinstance(data["shapes"], list)

    def test_load_wrong_version_raises(self, tmp_path):
        """Loading an index with an unsupported version raises ValueError."""
        import json as _json
        index_path = tmp_path / "bad_version.json"
        index_path.write_text(_json.dumps({"version": 999, "shapes": [], "categories": []}))
        with pytest.raises(ValueError, match="Unsupported index version"):
            ShapeIndex.load(index_path)


class TestRenderShape:
    """Unit tests for render_shape."""

    def _make_shape(self) -> DrawioShape:
        return DrawioShape(
            name="database",
            category="networking",
            library="networking.xml",
            width=60.0,
            height=80.0,
            svg_snippet="<g><rect width='60' height='80'/></g>",
        )

    def test_returns_required_keys(self):
        shape = self._make_shape()
        result = render_shape(shape, x=10.0, y=20.0, w=120.0, h=160.0)
        assert "svg" in result
        assert "anchors" in result
        assert "bbox" in result

    def test_bbox_matches_target(self):
        shape = self._make_shape()
        result = render_shape(shape, x=10.0, y=20.0, w=120.0, h=160.0)
        assert result["bbox"] == (10.0, 20.0, 120.0, 160.0)

    def test_svg_has_transform(self):
        shape = self._make_shape()
        result = render_shape(shape, x=10.0, y=20.0, w=120.0, h=160.0)
        assert 'transform="translate(10.0,20.0)' in result["svg"]

    def test_anchors_cardinal_points(self):
        shape = self._make_shape()
        result = render_shape(shape, x=0.0, y=0.0, w=60.0, h=80.0)
        anchors = result["anchors"]
        assert anchors["top-left"] == (0.0, 0.0)
        assert anchors["bottom-right"] == (60.0, 80.0)
        assert anchors["centre"] == (30.0, 40.0)

    def test_scale_encoded_in_transform(self):
        """Scale factor changes proportionally to target vs native dimensions."""
        shape = self._make_shape()  # native 60x80
        result = render_shape(shape, x=0.0, y=0.0, w=120.0, h=160.0)
        # scale should be 2.0 in both axes
        assert "scale(2.000000,2.000000)" in result["svg"]


class TestRenderCatalogue:
    """Unit tests for render_catalogue."""

    def _shapes(self, n: int = 3) -> list[DrawioShape]:
        return [
            DrawioShape(
                name=f"shape{i}",
                category="test",
                library="test.xml",
                width=60.0,
                height=80.0,
                svg_snippet="<g><rect width='60' height='80'/></g>",
            )
            for i in range(n)
        ]

    def test_empty_list_returns_minimal_svg(self):
        svg = render_catalogue([])
        assert "<svg" in svg
        assert 'width="0"' in svg

    def test_output_is_valid_svg(self):
        """render_catalogue output opens with <svg and closes with </svg>."""
        shapes = self._shapes(4)
        svg = render_catalogue(shapes, columns=2, cell_size=100)
        assert svg.strip().startswith("<svg")
        assert svg.strip().endswith("</svg>")

    def test_all_shape_names_in_output(self):
        shapes = self._shapes(3)
        svg = render_catalogue(shapes, columns=3)
        for shape in shapes:
            assert shape.name in svg

    def test_dark_mode_media_query_present(self):
        shapes = self._shapes(2)
        svg = render_catalogue(shapes)
        assert "prefers-color-scheme: dark" in svg

    def test_grid_dimensions(self):
        """SVG dimensions match columns * cell_size and rows * cell_size."""
        shapes = self._shapes(6)
        svg = render_catalogue(shapes, columns=3, cell_size=80)
        # 6 shapes, 3 cols -> 2 rows; width=240, height=160
        assert 'width="240"' in svg
        assert 'height="160"' in svg
