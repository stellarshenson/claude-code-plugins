"""Turn a projected mesh into unstyled SVG wireframe elements.

Two styles:

* ``wire`` - every unique edge once, its opacity falling with depth so the far
  side of the model reads lighter;
* ``hidden`` - back faces culled with a Newell normal, the rest painted far to
  near as polygons, so nearer faces occlude the edges behind them once the
  caller's CSS gives the polygons a fill.

Colour is the caller's: elements carry geometry, opacity and ``stroke-width``,
never a ``stroke`` or a ``fill``. The camera lives in :mod:`wireframe_camera`.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from stellars_claude_code_plugins.svg_tools.gen_backgrounds import BackgroundElement
from stellars_claude_code_plugins.svg_tools.obj_mesh import Mesh, unique_edges
from stellars_claude_code_plugins.svg_tools.wireframe_camera import (
    depth_from_camera,
    fit_to_canvas,
    view_space,
)

STYLES = ("wire", "hidden")

DEFAULT_YAW = 35.0
DEFAULT_PITCH = 20.0
DEFAULT_FOV = 25.0
DEFAULT_FIT = 0.06
DEFAULT_STROKE_WIDTH = 0.8

# Depth fade of the `wire` style, nearest edge to furthest.
_NEAR_OPACITY = 0.95
_FAR_OPACITY = 0.18
# An edge seen end-on projects to a point. Below half a pixel it draws nothing,
# and the `connectors` gate reads a line that short as a zero-length defect.
_MIN_EDGE_PX = 0.5


@dataclass
class WireframeResult:
    """A rendered wireframe: elements plus the counts and bounds of the drawing.

    Attributes:
        model: Slug or file stem the drawing came from.
        style: ``wire`` or ``hidden``.
        elements: Unstyled SVG elements, in paint order.
        bbox: ``(x, y, w, h)`` of the fitted drawing inside the canvas.
        edge_count: Edges drawn (``wire`` only).
        face_count: Faces drawn after culling (``hidden`` only).
    """

    model: str
    style: str
    elements: list[BackgroundElement]
    bbox: tuple[float, float, float, float]
    edge_count: int
    face_count: int


def _wire_elements(
    mesh: Mesh, points: np.ndarray, depth: np.ndarray, stroke_width: float
) -> list[BackgroundElement]:
    """One faded line per unique edge, nearest edges most opaque; end-on edges dropped."""
    edges = unique_edges(mesh.faces)
    midpoints = np.array([(depth[a] + depth[b]) / 2 for a, b in edges])
    low, high = midpoints.min(), midpoints.max()
    span = max(high - low, 1e-9)
    elements = []
    for (a, b), mid in zip(edges, midpoints):
        alpha = _NEAR_OPACITY - (_NEAR_OPACITY - _FAR_OPACITY) * (mid - low) / span
        (x1, y1), (x2, y2) = points[a], points[b]
        if math.hypot(x2 - x1, y2 - y1) < _MIN_EDGE_PX:
            continue
        elements.append(
            BackgroundElement(
                "line",
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke-width="{stroke_width:.2f}" opacity="{alpha:.3f}"/>',
                "edge",
                (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)),
            )
        )
    return elements


def _newell_normal(polygon: np.ndarray) -> np.ndarray:
    """Normal of a polygon by Newell's method - stable for non-planar quads."""
    nxt = np.roll(polygon, -1, axis=0)
    return np.array(
        [
            float(((polygon[:, 1] - nxt[:, 1]) * (polygon[:, 2] + nxt[:, 2])).sum()),
            float(((polygon[:, 2] - nxt[:, 2]) * (polygon[:, 0] + nxt[:, 0])).sum()),
            float(((polygon[:, 0] - nxt[:, 0]) * (polygon[:, 1] + nxt[:, 1])).sum()),
        ]
    )


def _visible_faces(mesh: Mesh, rotated: np.ndarray, distance: float) -> list[tuple[int, ...]]:
    """Front-facing faces, sorted far to near - the painter's algorithm order.

    Args:
        mesh: The mesh being drawn.
        rotated: ``(N, 3)`` camera-space vertex positions.
        distance: Camera distance, ``inf`` for orthographic.

    Returns:
        list[tuple[int, ...]]: Faces that turn toward the camera, furthest first.
    """
    orthographic = math.isinf(distance)
    eye = np.array([0.0, 0.0, 1.0])
    visible = []
    for face in mesh.faces:
        polygon = rotated[list(face)]
        centroid = polygon.mean(axis=0)
        towards_eye = eye if orthographic else np.array([0.0, 0.0, distance]) - centroid
        if float(_newell_normal(polygon) @ towards_eye) <= 0:
            continue
        away = -centroid[2] if orthographic else float(np.linalg.norm(towards_eye))
        visible.append((away, face))
    visible.sort(key=lambda item: -item[0])
    return [face for _, face in visible]


def _hidden_elements(
    faces: list[tuple[int, ...]], points: np.ndarray, stroke_width: float
) -> list[BackgroundElement]:
    """One polygon per visible face, in the order given; fill and stroke are CSS's."""
    elements = []
    for face in faces:
        polygon = points[list(face)]
        coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in polygon)
        low, high = polygon.min(axis=0), polygon.max(axis=0)
        elements.append(
            BackgroundElement(
                "polygon",
                f'<polygon points="{coordinates}" stroke-width="{stroke_width:.2f}"/>',
                "face",
                (float(low[0]), float(low[1]), float(high[0] - low[0]), float(high[1] - low[1])),
            )
        )
    return elements


def render_wireframe(
    mesh: Mesh,
    model: str,
    style: str = "wire",
    w: float = 400,
    h: float = 400,
    yaw: float = DEFAULT_YAW,
    pitch: float = DEFAULT_PITCH,
    roll: float = 0.0,
    fov: float = DEFAULT_FOV,
    fit: float = DEFAULT_FIT,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
) -> WireframeResult:
    """Render a mesh as SVG wireframe elements fitted to a canvas.

    Args:
        mesh: Parsed OBJ mesh.
        model: Slug or file stem, reported back on the result.
        style: ``wire`` (every edge, depth-faded) or ``hidden`` (painted faces).
        w: Canvas width.
        h: Canvas height.
        yaw: Degrees about the model's up axis.
        pitch: Degrees about the screen-horizontal axis.
        roll: Degrees about the view axis.
        fov: Field of view in degrees; ``0`` is orthographic.
        fit: Margin as a fraction of each canvas side.
        stroke_width: Stroke width on every element.

    Returns:
        WireframeResult: Elements in paint order plus bounds and counts.

    Raises:
        ValueError: Unknown style, or a fov or fit out of range.
    """
    if style not in STYLES:
        raise ValueError(f"Unknown style {style!r}. Choose from: {', '.join(STYLES)}")
    projected, rotated, distance = view_space(mesh.vertices, yaw, pitch, roll, fov)
    points, bbox = fit_to_canvas(projected, w, h, fit)
    if style == "wire":
        elements = _wire_elements(mesh, points, depth_from_camera(rotated, distance), stroke_width)
        edge_count, face_count = len(elements), 0
    else:
        faces = _visible_faces(mesh, rotated, distance)
        elements = _hidden_elements(faces, points, stroke_width)
        edge_count, face_count = 0, len(elements)
    return WireframeResult(model, style, elements, bbox, edge_count, face_count)
