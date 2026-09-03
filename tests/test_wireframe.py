"""Tests for the OBJ reader and the wireframe renderer.

Covers polygon-preserving parsing, negative face indices, the unique-edge set,
back-face culling at the default view, canvas fitting, the depth fade, the
orthographic camera and the CLI surface. No network: every mesh is written by
the test.
"""

import json
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pytest

from stellars_claude_code_plugins.svg_tools.obj_mesh import load_obj, parse_obj, unique_edges
from stellars_claude_code_plugins.svg_tools.wireframe_camera import view_space
from stellars_claude_code_plugins.svg_tools.wireframe_render import render_wireframe

TOOL = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "stellars_claude_code_plugins"
    / "svg_tools"
    / "wireframe.py"
)

# Unit cube, quad faces, wound counter-clockwise seen from outside.
CUBE = """# unit cube
v -1 -1 -1
v  1 -1 -1
v  1  1 -1
v -1  1 -1
v -1 -1  1
v  1 -1  1
v  1  1  1
v -1  1  1
vt 0 0
vn 0 0 1
f 5/1/1 6/1/1 7/1/1 8/1/1
f 1/1/1 4/1/1 3/1/1 2/1/1
f 2/1/1 3/1/1 7/1/1 6/1/1
f 1/1/1 5/1/1 8/1/1 4/1/1
f 4/1/1 8/1/1 7/1/1 3/1/1
f 1/1/1 2/1/1 6/1/1 5/1/1
"""

# One quad, addressed by negative (relative) indices.
NEGATIVE_QUAD = """
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
f -4 -3 -2 -1
"""

W = H = 400.0
OPACITY = re.compile(r'opacity="([\d.]+)"')


@pytest.fixture
def cube():
    return parse_obj(CUBE)


def test_parser_keeps_quads_and_drops_texture_and_normal_indices(cube):
    assert cube.vertices.shape == (8, 3)
    assert len(cube.faces) == 6
    assert {len(f) for f in cube.faces} == {4}
    assert cube.faces[0] == (4, 5, 6, 7)


def test_negative_face_indices_count_back_from_the_last_vertex():
    mesh = parse_obj(NEGATIVE_QUAD)
    assert mesh.faces == [(0, 1, 2, 3)]


def test_a_quad_contributes_four_edges_not_a_triangulated_six():
    assert len(unique_edges(parse_obj(NEGATIVE_QUAD).faces)) == 4


def test_a_cube_has_twelve_unique_edges(cube):
    assert len(unique_edges(cube.faces)) == 12


def test_load_obj_reads_from_disk(tmp_path):
    path = tmp_path / "cube.obj"
    path.write_text(CUBE, encoding="utf-8")
    assert len(load_obj(path).faces) == 6


@pytest.mark.parametrize("source", ["v 0 0 0\nv 1 0 0\n", "f 1 2 3\n"])
def test_a_mesh_without_vertices_or_faces_is_rejected(source):
    with pytest.raises(ValueError):
        parse_obj(source)


def test_wire_draws_every_edge_once(cube):
    result = render_wireframe(cube, "cube", style="wire", w=W, h=H)
    assert result.edge_count == 12
    assert len(result.elements) == 12
    assert {e.role for e in result.elements} == {"edge"}


def test_wire_drops_the_edges_seen_end_on(cube):
    # Looking straight down -Z, orthographic: the four Z edges project to points.
    result = render_wireframe(cube, "cube", style="wire", w=W, h=H, yaw=0, pitch=0, fov=0)
    assert result.edge_count == 8
    assert all(e.bbox[2] >= 0.5 or e.bbox[3] >= 0.5 for e in result.elements)


def test_hidden_shows_the_three_faces_of_a_cube_the_default_view_can_see(cube):
    result = render_wireframe(cube, "cube", style="hidden", w=W, h=H)
    assert result.face_count == 3
    assert all(e.kind == "polygon" for e in result.elements)


def test_elements_carry_no_stroke_or_fill_so_css_owns_them(cube):
    for style in ("wire", "hidden"):
        result = render_wireframe(cube, "cube", style=style, w=W, h=H)
        assert all("stroke=" not in e.svg for e in result.elements)
        assert all("fill=" not in e.svg for e in result.elements)


def test_the_drawing_fits_the_canvas_inside_the_fit_margin(cube):
    result = render_wireframe(cube, "cube", style="wire", w=W, h=H, fit=0.1)
    x, y, w, h = result.bbox
    assert x >= W * 0.1 - 1e-6 and x + w <= W * 0.9 + 1e-6
    assert y >= H * 0.1 - 1e-6 and y + h <= H * 0.9 + 1e-6
    # The fit is tight: one axis reaches its margin exactly.
    assert math.isclose(max(w / W, h / H), 0.8, abs_tol=1e-6)


def test_the_drawing_is_centred_on_the_canvas(cube):
    x, y, w, h = render_wireframe(cube, "cube", style="wire", w=640, h=360).bbox
    assert math.isclose(x + w / 2, 320.0, abs_tol=1e-6)
    assert math.isclose(y + h / 2, 180.0, abs_tol=1e-6)


def test_wire_opacity_falls_with_depth(cube):
    result = render_wireframe(cube, "cube", style="wire", w=W, h=H)
    opacities = [float(OPACITY.search(e.svg).group(1)) for e in result.elements]
    _, rotated, distance = view_space(cube.vertices, 35.0, 20.0, 0.0, 25.0)
    depth = [
        (distance - rotated[a, 2] + distance - rotated[b, 2]) / 2
        for a, b in unique_edges(cube.faces)
    ]
    by_depth = [o for _, o in sorted(zip(depth, opacities))]
    assert by_depth == sorted(by_depth, reverse=True)
    assert max(opacities) > min(opacities)


@pytest.mark.parametrize("angles", [(70.0, 20.0, 0.0), (35.0, 55.0, 0.0), (35.0, 20.0, 30.0)])
def test_yaw_pitch_and_roll_each_change_the_drawing(cube, angles):
    default = render_wireframe(cube, "cube", style="wire", w=W, h=H)
    yaw, pitch, roll = angles
    turned = render_wireframe(
        cube, "cube", style="wire", w=W, h=H, yaw=yaw, pitch=pitch, roll=roll
    )
    assert [e.svg for e in turned.elements] != [e.svg for e in default.elements]


def _parallel_edge_angles(mesh, fov):
    """Screen angles of the four cube edges that run along the X axis."""
    points, _, _ = view_space(mesh.vertices, 35.0, 20.0, 0.0, fov)
    angles = []
    for a, b in unique_edges(mesh.faces):
        delta = mesh.vertices[b] - mesh.vertices[a]
        if abs(delta[0]) > 0 and np.allclose(delta[1:], 0):
            dx, dy = points[b] - points[a]
            angles.append(math.atan2(dy, dx) % math.pi)
    assert len(angles) == 4
    return angles


def test_fov_zero_is_orthographic_and_keeps_parallel_edges_parallel(cube):
    angles = _parallel_edge_angles(cube, fov=0.0)
    assert max(angles) - min(angles) < 1e-9


def test_a_wide_fov_makes_parallel_edges_converge(cube):
    angles = _parallel_edge_angles(cube, fov=60.0)
    assert max(angles) - min(angles) > 1e-3


@pytest.mark.parametrize("kwargs", [{"style": "solid"}, {"fov": 180.0}, {"fit": 0.6}])
def test_out_of_range_options_raise(cube, kwargs):
    with pytest.raises(ValueError):
        render_wireframe(cube, "cube", **kwargs)


@pytest.fixture
def cube_file(tmp_path):
    path = tmp_path / "testcube.obj"
    path.write_text(CUBE, encoding="utf-8")
    return path


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def test_cli_fragment_is_a_placeable_group(cube_file):
    result = _run("--model", str(cube_file))
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('<g class="wireframe" data-model="testcube" data-bbox="')
    assert result.stdout.count("<line") == 12


def test_cli_preview_wraps_the_drawing_in_a_full_svg(cube_file):
    result = _run("--model", str(cube_file), "--preview", "--style", "hidden")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("<svg xmlns=")
    assert result.stdout.count("<polygon") == 3


def test_cli_json_reports_the_drawing_metadata(cube_file):
    result = _run("--model", str(cube_file), "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["model"] == "testcube"
    assert data["style"] == "wire"
    assert data["edge_count"] == 12 and data["face_count"] == 0
    assert len(data["bbox"]) == 4


def test_cli_names_mesh_fetch_when_the_model_cannot_be_resolved():
    result = _run("--model", "no-such-asset-slug")
    assert result.returncode == 1
    assert "mesh fetch no-such-asset-slug" in result.stderr


def test_cli_gives_no_fetch_hint_for_a_missing_obj_file(tmp_path):
    result = _run("--model", str(tmp_path / "missing.obj"))
    assert result.returncode == 1
    assert "missing.obj" in result.stderr
    assert "mesh fetch" not in result.stderr
