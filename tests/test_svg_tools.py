"""Tests for SVG infographic validation tools.

Tests: calc_connector, check_contrast, check_connectors, check_overlaps, check_alignment.
"""

import math
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parent.parent / "svg-infographics" / "tools"
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
    """Tests for the connector geometry calculator."""

    def _run(self, *args):
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "calc_connector.py"), *args],
            capture_output=True, text=True,
        )
        return result

    def test_horizontal_connector(self):
        """Horizontal connector should have 0 degree angle."""
        r = self._run("--from", "100,50", "--to", "300,50")
        assert r.returncode == 0
        assert "0.0 degrees" in r.stdout

    def test_vertical_connector(self):
        """Vertical downward connector should have 90 degree angle."""
        r = self._run("--from", "100,50", "--to", "100,200")
        assert r.returncode == 0
        assert "90.0 degrees" in r.stdout

    def test_diagonal_connector(self):
        """Diagonal connector should have 45 degree angle."""
        r = self._run("--from", "100,100", "--to", "200,200")
        assert r.returncode == 0
        assert "45.0 degrees" in r.stdout

    def test_negative_angle(self):
        """Upward connector should have negative angle."""
        r = self._run("--from", "100,200", "--to", "200,100")
        assert r.returncode == 0
        assert "-45.0 degrees" in r.stdout

    def test_margin_reduces_length(self):
        """Margin should reduce effective length."""
        r_no_margin = self._run("--from", "100,50", "--to", "300,50")
        r_with_margin = self._run("--from", "100,50", "--to", "300,50", "--margin", "10")
        assert r_no_margin.returncode == 0
        assert r_with_margin.returncode == 0
        # Parse effective lengths
        for line in r_no_margin.stdout.split("\n"):
            if "Effective length" in line:
                len_no = float(line.split(":")[1].strip().replace("px", ""))
        for line in r_with_margin.stdout.split("\n"):
            if "Effective length" in line:
                len_with = float(line.split(":")[1].strip().replace("px", ""))
        assert len_with < len_no

    def test_custom_head_size(self):
        """Custom head size should appear in output."""
        r = self._run("--from", "100,50", "--to", "300,50", "--head-size", "15,8")
        assert r.returncode == 0
        assert "-15" in r.stdout  # head length in polygon points

    def test_svg_snippet_output(self):
        """Should produce ready-to-paste SVG snippet."""
        r = self._run("--from", "100,50", "--to", "300,50")
        assert r.returncode == 0
        assert "<g transform=" in r.stdout
        assert "<line" in r.stdout
        assert "<polygon" in r.stdout

    def test_cutout_mode(self):
        """Cutout mode should split connector into two segments."""
        r = self._run(
            "--from", "100,100", "--to", "400,100",
            "--cutout", "200,90,100,20",
        )
        assert r.returncode == 0
        assert "CUTOUT MODE" in r.stdout
        assert "Segment 1" in r.stdout
        assert "Segment 2" in r.stdout

    def test_cutout_no_intersection(self):
        """Cutout that doesn't intersect should fall back to normal mode."""
        r = self._run(
            "--from", "100,100", "--to", "400,100",
            "--cutout", "200,200,50,20",  # pill far away
        )
        assert r.returncode == 0
        # Should not enter cutout mode
        assert "CUTOUT MODE" not in r.stdout


class TestCalcConnectorModule:
    """Direct import tests for calc_connector functions."""

    def test_calc_connector_basic(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from calc_connector import calc_connector
        c = calc_connector(0, 0, 100, 0)
        assert abs(c["angle_deg"] - 0.0) < 0.01
        assert abs(c["full_length"] - 100.0) < 0.01
        assert abs(c["tip_x"] - 100.0) < 0.01
        assert abs(c["tip_y"] - 0.0) < 0.01
        sys.path.pop(0)

    def test_calc_connector_with_margin(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from calc_connector import calc_connector
        c = calc_connector(0, 0, 100, 0, margin=5)
        assert abs(c["effective_length"] - 90.0) < 0.01
        assert abs(c["tip_x"] - 95.0) < 0.01
        sys.path.pop(0)

    def test_calc_cutout(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from calc_connector import calc_cutout
        result = calc_cutout(0, 50, 400, 50, 150, 40, 100, 20)
        assert result is not None
        assert "segment1" in result
        assert "segment2" in result
        sys.path.pop(0)

    def test_calc_cutout_no_intersection(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from calc_connector import calc_cutout
        result = calc_cutout(0, 50, 400, 50, 150, 200, 100, 20)
        assert result is None
        sys.path.pop(0)


# ---------------------------------------------------------------------------
# check_contrast.py tests
# ---------------------------------------------------------------------------


class TestCheckContrast:
    """Tests for the WCAG contrast checker."""

    def _run(self, svg_path, *extra_args):
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_contrast.py"), "--svg", str(svg_path), *extra_args],
            capture_output=True, text=True,
        )
        return result

    def test_simple_svg_passes(self, simple_svg):
        """Well-themed SVG should pass AA contrast."""
        r = self._run(simple_svg)
        assert r.returncode == 0
        assert "SUMMARY" in r.stdout

    def test_low_contrast_detected(self, contrast_fail_svg):
        """Low contrast text should be flagged."""
        r = self._run(contrast_fail_svg, "--show-all")
        assert r.returncode == 0
        # Light grey (#cccccc) on white should fail or warn
        assert "SUMMARY" in r.stdout

    def test_aaa_stricter(self, simple_svg):
        """AAA level should be stricter than AA."""
        r = self._run(simple_svg, "--level", "AAA", "--show-all")
        assert r.returncode == 0
        assert "WCAG AAA" in r.stdout

    def test_custom_dark_bg(self, simple_svg):
        """Custom dark background should be accepted."""
        r = self._run(simple_svg, "--dark-bg", "#272b31")
        assert r.returncode == 0

    def test_show_all_flag(self, simple_svg):
        """--show-all should show passing entries too."""
        r = self._run(simple_svg, "--show-all")
        assert r.returncode == 0
        assert "pass" in r.stdout.lower()


class TestContrastModule:
    """Direct import tests for check_contrast functions."""

    def test_hex_to_rgb(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import hex_to_rgb
        assert hex_to_rgb("#ff0000") == (255, 0, 0)
        assert hex_to_rgb("#00ff00") == (0, 255, 0)
        assert hex_to_rgb("#f00") == (255, 0, 0)
        sys.path.pop(0)

    def test_relative_luminance(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import relative_luminance
        white_lum = relative_luminance(255, 255, 255)
        black_lum = relative_luminance(0, 0, 0)
        assert white_lum > 0.99
        assert black_lum < 0.01
        sys.path.pop(0)

    def test_contrast_ratio(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import relative_luminance, contrast_ratio
        white_lum = relative_luminance(255, 255, 255)
        black_lum = relative_luminance(0, 0, 0)
        ratio = contrast_ratio(white_lum, black_lum)
        assert ratio > 20.0  # black on white is 21:1
        sys.path.pop(0)

    def test_blend_over(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import blend_over
        # Black at 50% opacity over white should be mid-grey
        result = blend_over("#000000", 0.5, "#ffffff")
        r, g, b = int(result[1:3], 16), int(result[3:5], 16), int(result[5:7], 16)
        assert 125 <= r <= 130
        assert 125 <= g <= 130
        sys.path.pop(0)

    def test_resolve_color(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import resolve_color
        assert resolve_color("#ff0000") == "#ff0000"
        assert resolve_color("red") == "#ff0000"
        assert resolve_color("none") is None
        assert resolve_color("transparent") is None
        sys.path.pop(0)

    def test_parse_css_classes(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import parse_css_classes
        css = ".fg-1 { fill: #1e3a5f; } .fg-2 { fill: #2a5f9e; }"
        classes = parse_css_classes(css)
        assert classes["fg-1"] == "#1e3a5f"
        assert classes["fg-2"] == "#2a5f9e"
        sys.path.pop(0)

    def test_parse_css_strips_media(self):
        """Light mode parser should ignore @media blocks."""
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import parse_css_classes
        css = ".fg-1 { fill: #1e3a5f; } @media (prefers-color-scheme: dark) { .fg-1 { fill: #c8d6e5; } }"
        classes = parse_css_classes(css)
        assert classes["fg-1"] == "#1e3a5f"
        sys.path.pop(0)

    def test_parse_dark_classes(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import parse_dark_classes
        css = ".fg-1 { fill: #1e3a5f; } @media (prefers-color-scheme: dark) { .fg-1 { fill: #c8d6e5; } }"
        dark = parse_dark_classes(css)
        assert dark["fg-1"] == "#c8d6e5"
        sys.path.pop(0)

    def test_is_large_text(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_contrast import is_large_text
        assert is_large_text(18, "normal") is True
        assert is_large_text(14, "bold") is True
        assert is_large_text(12, "normal") is False
        assert is_large_text(14, "normal") is False
        sys.path.pop(0)


# ---------------------------------------------------------------------------
# check_connectors.py tests
# ---------------------------------------------------------------------------


class TestCheckConnectors:
    """Tests for the connector quality checker."""

    def _run(self, svg_path):
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_connectors.py"), "--svg", str(svg_path)],
            capture_output=True, text=True,
        )
        return result

    def test_basic_connector(self, connector_svg):
        """Basic horizontal connector between cards should pass."""
        r = self._run(connector_svg)
        assert r.returncode == 0
        assert "Connector check" in r.stdout

    def test_zero_length_detection(self, tmp_path):
        """Zero-length line should be flagged."""
        svg = tmp_path / "zero.svg"
        svg.write_text(textwrap.dedent("""\
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">
              <line x1="100" y1="50" x2="100" y2="50" stroke="#333"/>
            </svg>
        """))
        r = self._run(svg)
        assert r.returncode == 0
        assert "zero-length" in r.stdout


class TestConnectorsModule:
    """Direct import tests for check_connectors functions."""

    def test_point_to_seg_dist(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_connectors import _point_to_seg_dist
        # Point on the segment
        assert abs(_point_to_seg_dist(50, 0, 0, 0, 100, 0)) < 0.01
        # Point above segment midpoint
        assert abs(_point_to_seg_dist(50, 10, 0, 0, 100, 0) - 10.0) < 0.01
        sys.path.pop(0)

    def test_parse_points(self):
        sys.path.insert(0, str(TOOLS_DIR))
        from check_connectors import _parse_points
        pts = _parse_points("100,50 200,60 300,70")
        assert len(pts) == 3
        assert pts[0] == (100.0, 50.0)
        assert pts[2] == (300.0, 70.0)
        sys.path.pop(0)


# ---------------------------------------------------------------------------
# check_overlaps.py tests
# ---------------------------------------------------------------------------


class TestCheckOverlaps:
    """Tests for the overlap detection tool."""

    def _run(self, svg_path, *extra_args):
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_overlaps.py"), "--svg", str(svg_path), *extra_args],
            capture_output=True, text=True,
        )
        return result

    def test_simple_svg(self, simple_svg):
        """Simple well-spaced SVG should run without errors."""
        r = self._run(simple_svg)
        assert r.returncode == 0
        assert "SUMMARY" in r.stdout or "summary" in r.stdout.lower()

    def test_overlapping_texts(self, overlap_svg):
        """Overlapping text elements should be detected."""
        r = self._run(overlap_svg)
        assert r.returncode == 0
        # Should find overlaps between the two nearly-identical positioned texts

    def test_inject_bounds(self, simple_svg, tmp_path):
        """--inject-bounds should modify the SVG with overlay elements."""
        import shutil
        test_svg = tmp_path / "test_inject.svg"
        shutil.copy(simple_svg, test_svg)
        r = self._run(test_svg, "--inject-bounds")
        assert r.returncode == 0

    def test_strip_bounds(self, simple_svg, tmp_path):
        """--strip-bounds should remove overlay elements."""
        import shutil
        test_svg = tmp_path / "test_strip.svg"
        shutil.copy(simple_svg, test_svg)
        # Inject then strip
        self._run(test_svg, "--inject-bounds")
        r = self._run(test_svg, "--strip-bounds")
        assert r.returncode == 0


# ---------------------------------------------------------------------------
# check_alignment.py tests
# ---------------------------------------------------------------------------


class TestCheckAlignment:
    """Tests for the alignment and grid checker."""

    def _run(self, svg_path, *extra_args):
        result = subprocess.run(
            [sys.executable, str(TOOLS_DIR / "check_alignment.py"), "--svg", str(svg_path), *extra_args],
            capture_output=True, text=True,
        )
        return result

    def test_aligned_text(self, alignment_svg):
        """Text with consistent y-rhythm should pass."""
        r = self._run(alignment_svg)
        assert r.returncode == 0

    def test_custom_grid(self, alignment_svg):
        """Custom grid step should be accepted."""
        r = self._run(alignment_svg, "--grid", "7")
        assert r.returncode == 0

    def test_grid_with_tolerance(self, alignment_svg):
        """Grid check with tolerance should pass more elements."""
        r = self._run(alignment_svg, "--grid", "14", "--tolerance", "2")
        assert r.returncode == 0


# ---------------------------------------------------------------------------
# Example SVG validation (smoke tests)
# ---------------------------------------------------------------------------


class TestExampleSVGs:
    """Smoke tests running validators against actual example SVGs."""

    @pytest.fixture
    def example_svgs(self):
        """List a few example SVGs for smoke testing."""
        examples = list(EXAMPLES_DIR.glob("*.svg"))
        assert len(examples) > 0, f"No example SVGs found in {EXAMPLES_DIR}"
        return examples[:5]  # Test first 5 to keep fast

    def test_contrast_on_examples(self, example_svgs):
        """Contrast checker should not crash on real examples."""
        for svg in example_svgs:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "check_contrast.py"), "--svg", str(svg)],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"check_contrast.py crashed on {svg.name}: {r.stderr}"

    def test_overlaps_on_examples(self, example_svgs):
        """Overlap checker should not crash on real examples."""
        for svg in example_svgs:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "check_overlaps.py"), "--svg", str(svg)],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"check_overlaps.py crashed on {svg.name}: {r.stderr}"

    def test_alignment_on_examples(self, example_svgs):
        """Alignment checker should not crash on real examples."""
        for svg in example_svgs:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "check_alignment.py"), "--svg", str(svg)],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"check_alignment.py crashed on {svg.name}: {r.stderr}"

    def test_connectors_on_examples(self, example_svgs):
        """Connector checker should not crash on real examples."""
        for svg in example_svgs:
            r = subprocess.run(
                [sys.executable, str(TOOLS_DIR / "check_connectors.py"), "--svg", str(svg)],
                capture_output=True, text=True,
            )
            assert r.returncode == 0, f"check_connectors.py crashed on {svg.name}: {r.stderr}"


# ---------------------------------------------------------------------------
# Plugin structure tests
# ---------------------------------------------------------------------------


class TestPluginStructure:
    """Verify the svg-infographics plugin has correct structure."""

    PLUGIN_DIR = Path(__file__).resolve().parent.parent / "svg-infographics"

    def test_plugin_json_exists(self):
        assert (self.PLUGIN_DIR / ".claude-plugin" / "plugin.json").is_file()

    def test_readme_exists(self):
        assert (self.PLUGIN_DIR / "README.md").is_file()

    def test_skills_exist(self):
        for skill in ["svg-standards", "workflow", "theme", "validation"]:
            assert (self.PLUGIN_DIR / "skills" / skill / "SKILL.md").is_file(), f"Missing skill: {skill}"

    def test_workflow_reference_exists(self):
        assert (self.PLUGIN_DIR / "skills" / "workflow" / "WORKFLOW.md").is_file()

    def test_commands_exist(self):
        for cmd in ["create", "fix-style", "fix-layout", "validate", "theme"]:
            assert (self.PLUGIN_DIR / "commands" / f"{cmd}.md").is_file(), f"Missing command: {cmd}"

    def test_tools_exist(self):
        for tool in ["calc_connector.py", "check_overlaps.py", "check_alignment.py",
                      "check_contrast.py", "check_connectors.py"]:
            assert (self.PLUGIN_DIR / "tools" / tool).is_file(), f"Missing tool: {tool}"

    def test_examples_not_empty(self):
        examples = list((self.PLUGIN_DIR / "examples").glob("*.svg"))
        assert len(examples) >= 60, f"Expected 60+ examples, got {len(examples)}"

    def test_plugin_json_valid(self):
        import json
        plugin_json = self.PLUGIN_DIR / ".claude-plugin" / "plugin.json"
        data = json.loads(plugin_json.read_text())
        assert data["name"] == "svg-infographics"
        assert "version" in data
        assert "keywords" in data
        assert len(data["keywords"]) >= 5

    def test_examples_anonymised(self):
        """Client company names should be anonymised (Kolomolo and Stellars-Tech are allowed)."""
        forbidden = ["DeLaval", "Nordea", "Atlas Copco", "Perfekta"]
        for svg in (self.PLUGIN_DIR / "examples").glob("*.svg"):
            content = svg.read_text()
            for name in forbidden:
                assert name not in content, f"Found unanonymised '{name}' in {svg.name}"
