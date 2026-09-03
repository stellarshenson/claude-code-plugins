"""Tests for the dotsea background generator in gen_backgrounds.py.

Covers registration, determinism, the depth fade, the horizon and canvas
clips, density ordering, the connection mesh, the honeycomb variant, the
swell, the direction frames and the CLI surface.
"""

import collections
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys

import pytest

from stellars_claude_code_plugins.svg_tools.gen_backgrounds import (
    BG_TYPES,
    generate_background,
)

TOOL = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "stellars_claude_code_plugins"
    / "svg_tools"
    / "gen_backgrounds.py"
)

W, H = 1280.0, 720.0
SEED = 7

CIRCLE = re.compile(r'<circle cx="([-\d.]+)" cy="([-\d.]+)" r="([\d.]+)" opacity="([\d.]+)"/>')
POLYGON = re.compile(r'<polygon points="([^"]+)" opacity="([\d.]+)"/>')
OPACITY = re.compile(r'opacity="([\d.]+)"')

# Screen depth of a point - 0 on the near edge, growing toward the horizon.
DEPTH = {
    "up": lambda x, y: H - y,
    "down": lambda x, y: y,
    "right": lambda x, y: x,
    "left": lambda x, y: W - x,
    "radial": lambda x, y: math.hypot(x - W / 2, y - H / 2),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def field(**kwargs):
    """Generate a dotsea field on a 1280x720 canvas receding upward."""
    return generate_background(
        "dotsea", **{"w": W, "h": H, "direction": "up", "seed": SEED, **kwargs}
    )


def circles(result):
    """(cx, cy, radius, opacity) for every circle marker in a result."""
    return [tuple(float(v) for v in m) for m in CIRCLE.findall(result.svg)]


def centres(result, shape):
    """(cx, cy) for every marker, averaging the six vertices of a hexagon."""
    if shape == "dot":
        return [(m[0], m[1]) for m in circles(result)]
    out = []
    for points, _ in POLYGON.findall(result.svg):
        xy = [[float(v) for v in point.split(",")] for point in points.split()]
        out.append((sum(p[0] for p in xy) / 6, sum(p[1] for p in xy) / 6))
    return out


def adjacent_row_offset(result, shape):
    """Median lateral gap from a row's markers to the next row's, in row spacings.

    Only markers near the canvas centre count, where the column convergence
    between neighbouring rows is negligible. Needs ``waviness=0`` so that a row
    shares one exact y and can be recovered from the rendered coordinates.
    """
    rows = collections.defaultdict(list)
    for x, y in centres(result, shape):
        rows[round(y, 1)].append(x)

    offsets = []
    ordered = sorted(rows, reverse=True)
    for near, far in zip(ordered, ordered[1:]):
        here = sorted(x for x in rows[near] if abs(x - W / 2) < 120)
        there = [x for x in rows[far] if abs(x - W / 2) < 120]
        spacing = statistics.median(b - a for a, b in zip(here, here[1:]))
        offsets += [min(abs(x - t) for t in there) / spacing for x in here]
    return statistics.median(offsets)


def top_edge_spread(result, bands=16):
    """Vertical spread of the field's far edge across the canvas width."""
    tops = collections.defaultdict(list)
    for x, y, _, _ in circles(result):
        tops[min(int(x * bands / W), bands - 1)].append(y)
    edge = [min(v) for v in tops.values()]
    return max(edge) - min(edge)


def cli(*args):
    """Run gen_backgrounds.py as the CLI does."""
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Registration and determinism
# ---------------------------------------------------------------------------


def test_dotsea_is_registered():
    assert "dotsea" in BG_TYPES
    assert generate_background("dotsea", w=W, h=H).bg_type == "dotsea"


def test_default_field_is_dots_only():
    result = field()
    assert len(result.elements) > 1000
    assert {e.role for e in result.elements} == {"dot"}
    assert {e.kind for e in result.elements} == {"circle"}


def test_same_seed_reproduces_the_field():
    assert field().svg == field().svg
    assert field(seed=SEED + 1).svg != field().svg


# ---------------------------------------------------------------------------
# Depth fade
# ---------------------------------------------------------------------------


def test_opacity_falls_with_depth():
    marks = circles(field())
    bands = collections.defaultdict(list)
    for _, y, _, alpha in marks:
        bands[int((H - y) // 72)].append(alpha)

    means = [statistics.mean(bands[k]) for k in sorted(bands)]
    assert len(means) >= 4
    assert means == sorted(means, reverse=True)
    assert means[0] > 2 * means[-1]

    nearest = max(marks, key=lambda m: m[1])
    farthest = min(marks, key=lambda m: m[1])
    assert nearest[3] > farthest[3]


@pytest.mark.parametrize("cap", [0.35, 0.6, 0.9])
def test_no_marker_is_more_opaque_than_the_cap(cap):
    alphas = [m[3] for m in circles(field(opacity=cap))]
    assert max(alphas) == pytest.approx(cap, abs=0.001)
    assert min(alphas) < cap / 2


def test_a_lower_fade_rate_carries_dots_further():
    def reach(rate):
        return H - min(m[1] for m in circles(field(fade_rate=rate)))

    assert reach(0.5) > reach(2.0)
    assert reach(1.0) > reach(2.0)


# ---------------------------------------------------------------------------
# Horizon, canvas and density
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("horizon", [0.3, 0.5, 0.8])
def test_markers_stay_inside_the_horizon_and_the_canvas(horizon):
    marks = circles(field(horizon=horizon))
    vanish = H * (1 - horizon)
    assert min(m[1] for m in marks) >= vanish - 0.05
    assert min(m[1] for m in marks) < vanish + 0.1 * H
    assert max(m[1] for m in marks) <= H
    assert min(m[0] for m in marks) >= 0
    assert max(m[0] for m in marks) <= W


def test_density_presets_order_the_field():
    sparse, medium, dense = (len(field(density=d).elements) for d in ("sparse", "medium", "dense"))
    assert sparse < medium < dense
    assert dense > 3 * sparse


# ---------------------------------------------------------------------------
# Connection mesh
# ---------------------------------------------------------------------------


def test_connections_add_fainter_mesh_lines():
    plain = field()
    meshed = field(connections=True)
    lines = [e for e in meshed.elements if e.role == "connection"]

    assert not [e for e in plain.elements if e.role == "connection"]
    assert len(lines) > len(plain.elements)
    assert {e.kind for e in lines} == {"line"}
    assert len([e for e in meshed.elements if e.role == "dot"]) == len(plain.elements)

    line_alpha = [float(OPACITY.search(e.svg).group(1)) for e in lines]
    dot_alpha = [m[3] for m in circles(meshed)]
    assert max(line_alpha) < max(dot_alpha)
    assert statistics.mean(line_alpha) < statistics.mean(dot_alpha)


# ---------------------------------------------------------------------------
# Hexagon variant
# ---------------------------------------------------------------------------


def test_hex_markers_are_six_sided_polygons():
    result = field(shape="hex")
    assert {e.role for e in result.elements} == {"hex"}
    assert {e.kind for e in result.elements} == {"polygon"}
    assert {len(points.split()) for points, _ in POLYGON.findall(result.svg)} == {6}


def test_hex_rows_alternate_by_half_a_spacing():
    square = adjacent_row_offset(field(waviness=0), "dot")
    honeycomb = adjacent_row_offset(field(shape="hex", waviness=0), "hex")
    assert square < 0.15
    assert honeycomb > 0.35


LINE = re.compile(r'x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"')


def mesh_degrees(result):
    """Mesh lines meeting at each marker, keyed by the marker's line endpoint."""
    degree = collections.Counter()
    for e in result.elements:
        if e.role == "connection":
            x1, y1, x2, y2 = (float(v) for v in LINE.search(e.svg).groups())
            degree[(x1, y1)] += 1
            degree[(x2, y2)] += 1
    return degree


def test_hex_mesh_traces_hexagon_outlines_not_triangles():
    """Hex markers sit at honeycomb vertices, so three lines meet at each - a
    triangular mesh would put six at every interior marker, a square grid four."""
    honeycomb = mesh_degrees(field(shape="hex", connections=True))
    square = mesh_degrees(field(connections=True))
    assert max(honeycomb.values()) == 3
    assert max(square.values()) == 4
    assert len(centres(field(shape="hex", connections=True), "hex")) == len(
        centres(field(shape="hex"), "hex")
    ), "the honeycomb is the hex lattice itself, not a connections-only thinning"


# ---------------------------------------------------------------------------
# Swell
# ---------------------------------------------------------------------------


def test_waviness_zero_gives_straight_rows():
    rows = collections.Counter(m[1] for m in circles(field(waviness=0)))
    assert len(rows) < 80
    assert max(rows.values()) > 80
    assert top_edge_spread(field(waviness=0)) == 0.0


def test_rough_heaves_the_rows_more_than_calm():
    calm = top_edge_spread(field(waviness="calm"))
    moderate = top_edge_spread(field(waviness="moderate"))
    rough = top_edge_spread(field(waviness="rough"))
    assert 0 < calm < moderate < rough
    assert rough > 3 * calm


# ---------------------------------------------------------------------------
# Direction frames
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("direction", sorted(DEPTH))
def test_largest_markers_sit_on_the_near_edge(direction):
    depth = DEPTH[direction]
    marks = circles(field(direction=direction))
    biggest, smallest = max(m[2] for m in marks), min(m[2] for m in marks)

    near = statistics.mean(depth(m[0], m[1]) for m in marks if m[2] == biggest)
    far = statistics.mean(depth(m[0], m[1]) for m in marks if m[2] == smallest)
    assert near < 0.15 * max(W, H)
    assert far > 2 * near


# ---------------------------------------------------------------------------
# Option validation and CLI
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"shape": "star"},
        {"horizon": 0.0},
        {"horizon": 1.5},
        {"fade_rate": 0.0},
        {"opacity": 0.0},
        {"opacity": 1.5},
        {"waviness": "banana"},
        {"waviness": 2.0},
    ],
)
def test_out_of_range_options_raise(kwargs):
    with pytest.raises(ValueError):
        field(**kwargs)


def test_cli_accepts_a_waviness_preset():
    result = cli(
        "--type", "dotsea", "--w", "400", "--h", "240", "--seed", "3", "--waviness", "calm"
    )
    assert result.returncode == 0
    assert result.stdout.count("<circle") > 100


def test_cli_rejects_garbage_waviness():
    result = cli("--type", "dotsea", "--w", "400", "--h", "240", "--waviness", "banana")
    assert result.returncode != 0
    assert "waviness" in result.stderr.lower()


def test_cli_defaults_dotsea_to_up_without_moving_other_types():
    base = ["--type", "dotsea", "--w", "400", "--h", "240", "--seed", "3"]
    assert cli(*base).stdout == cli(*base, "--direction", "up").stdout
    assert cli(*base).stdout != cli(*base, "--direction", "down").stdout

    grid = ["--type", "grid", "--w", "400", "--h", "240", "--seed", "3"]
    assert cli(*grid).stdout == cli(*grid, "--direction", "right").stdout


@pytest.mark.parametrize("shape, tag", [("dot", "<circle"), ("hex", "<polygon")])
def test_cli_preview_puts_markers_in_the_node_group(shape, tag):
    result = cli(
        "--type",
        "dotsea",
        "--w",
        "400",
        "--h",
        "240",
        "--seed",
        "3",
        "--preview",
        "--shape",
        shape,
    )
    assert result.returncode == 0
    nodes = result.stdout.split('<g class="bg-nodes"')[1].split("</g>")[0]
    assert nodes.count(tag) > 100
