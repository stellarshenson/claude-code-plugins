"""Camera for the wireframe renderer: rotate, project, fit.

The camera looks down -Z at a mesh centred on the origin, so ``yaw`` turns the
model about its up axis, ``pitch`` tips it toward the viewer and ``roll`` spins
the picture plane. ``fov`` sets how close the camera sits: wide is close and
strongly perspective, ``0`` puts it at infinity for an orthographic view.

Nothing here knows about SVG - it returns plain arrays of points and depths.
"""

from __future__ import annotations

import math

import numpy as np


def rotation_matrix(yaw: float, pitch: float, roll: float) -> np.ndarray:
    """Rotation applied to the model, in degrees, as yaw then pitch then roll.

    Args:
        yaw: Turn about the model's up axis (Y).
        pitch: Tip about the screen-horizontal axis (X).
        roll: Spin about the view axis (Z).

    Returns:
        np.ndarray: A ``(3, 3)`` rotation matrix.
    """
    a, b, c = (math.radians(v) for v in (yaw, pitch, roll))
    ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return rz @ rx @ ry


def camera_distance(radius: float, fov: float) -> float:
    """Distance from the model centre that frames a sphere of ``radius`` at ``fov``.

    Args:
        radius: Bounding-sphere radius of the centred model.
        fov: Field of view in degrees; ``0`` means orthographic.

    Returns:
        float: Camera distance, or ``inf`` for an orthographic camera.

    Raises:
        ValueError: ``fov`` is negative or 180 degrees or wider.
    """
    if fov < 0 or fov >= 180:
        raise ValueError(f"fov {fov} out of range - use 0 <= fov < 180.")
    if fov == 0:
        return math.inf
    return radius / math.sin(math.radians(fov) / 2)


def view_space(
    vertices: np.ndarray, yaw: float, pitch: float, roll: float, fov: float
) -> tuple[np.ndarray, np.ndarray, float]:
    """Rotate vertices into camera space and project them onto the picture plane.

    The model is centred on the origin first, so the view does not depend on
    where the mesh sits in its own coordinates. Screen Y is flipped, because SVG
    counts it downward.

    Args:
        vertices: ``(N, 3)`` model-space positions.
        yaw: Degrees about the up axis.
        pitch: Degrees about the screen-horizontal axis.
        roll: Degrees about the view axis.
        fov: Field of view in degrees; ``0`` is orthographic.

    Returns:
        tuple: ``(points, rotated, distance)`` - the ``(N, 2)`` projected points,
        the ``(N, 3)`` camera-space positions and the camera distance.

    Raises:
        ValueError: ``fov`` is out of range.
    """
    centred = vertices - (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    rotated = centred @ rotation_matrix(yaw, pitch, roll).T
    radius = float(np.linalg.norm(rotated, axis=1).max()) or 1.0
    distance = camera_distance(radius, fov)
    if math.isinf(distance):
        points = rotated[:, :2].copy()
    else:
        points = rotated[:, :2] * (distance / (distance - rotated[:, 2]))[:, None]
    points[:, 1] *= -1
    return points, rotated, distance


def depth_from_camera(rotated: np.ndarray, distance: float) -> np.ndarray:
    """Per-vertex distance from the camera; larger is further away.

    Args:
        rotated: ``(N, 3)`` camera-space positions.
        distance: Camera distance, ``inf`` for orthographic.

    Returns:
        np.ndarray: ``(N,)`` depths, on an arbitrary but monotone scale.
    """
    if math.isinf(distance):
        return -rotated[:, 2]
    return distance - rotated[:, 2]


def fit_to_canvas(
    points: np.ndarray, w: float, h: float, fit: float
) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    """Scale and centre projected points inside a canvas, keeping the aspect ratio.

    Args:
        points: ``(N, 2)`` projected points.
        w: Canvas width.
        h: Canvas height.
        fit: Margin as a fraction of each canvas side, ``0 <= fit < 0.5``.

    Returns:
        tuple: ``(fitted, bbox)`` - the placed ``(N, 2)`` points and the
        ``(x, y, w, h)`` bounds of the drawing.

    Raises:
        ValueError: ``fit`` leaves no room to draw in.
    """
    if not 0 <= fit < 0.5:
        raise ValueError(f"fit {fit} out of range - use 0 <= fit < 0.5.")
    low, high = points.min(axis=0), points.max(axis=0)
    span = np.maximum(high - low, 1e-9)
    scale = min(w * (1 - 2 * fit) / span[0], h * (1 - 2 * fit) / span[1])
    drawn = span * scale
    origin = np.array([(w - drawn[0]) / 2, (h - drawn[1]) / 2])
    fitted = (points - low) * scale + origin
    return fitted, (float(origin[0]), float(origin[1]), float(drawn[0]), float(drawn[1]))
