"""Minimal Wavefront OBJ reader for wireframe rendering.

Reads only what a wireframe needs: ``v`` positions and ``f`` faces. Texture and
normal indices in ``v/vt/vn`` face tokens are discarded, and every other
statement (``vt``, ``vn``, ``o``, ``g``, ``s``, ``usemtl``, ...) is ignored.

Faces are kept as the polygons the file declares. The Base Mesh assets are quad
topology, and triangulating them would draw a diagonal across every quad.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Mesh:
    """A polygon soup: vertex positions plus faces that index them.

    Attributes:
        vertices: ``(N, 3)`` float array of positions.
        faces: One tuple of zero-based vertex indices per face, any length >= 3.
    """

    vertices: np.ndarray
    faces: list[tuple[int, ...]]


def _face_indices(tokens: list[str], vertex_count: int) -> tuple[int, ...]:
    """Convert ``f`` tokens to zero-based indices, resolving negative references.

    Args:
        tokens: Face tokens such as ``["23/1/1", "92/2/1", "114/3/2"]``.
        vertex_count: Vertices read so far - the base a negative index counts back from.

    Returns:
        tuple[int, ...]: Zero-based vertex indices.
    """
    indices = []
    for token in tokens:
        number = int(token.split("/", 1)[0])
        indices.append(vertex_count + number if number < 0 else number - 1)
    return tuple(indices)


def parse_obj(text: str) -> Mesh:
    """Parse OBJ source into a mesh.

    Args:
        text: Contents of an OBJ file.

    Returns:
        Mesh: Vertices and faces, polygons kept intact.

    Raises:
        ValueError: The source declares no vertices or no faces.
    """
    positions: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            positions.append((float(fields[1]), float(fields[2]), float(fields[3])))
        elif fields[0] == "f" and len(fields) >= 4:
            faces.append(_face_indices(fields[1:], len(positions)))
    if not positions:
        raise ValueError("OBJ has no vertices")
    if not faces:
        raise ValueError("OBJ has no faces")
    return Mesh(vertices=np.asarray(positions, dtype=float), faces=faces)


def load_obj(path: str | Path) -> Mesh:
    """Read an OBJ file from disk.

    Args:
        path: Path to a ``.obj`` file.

    Returns:
        Mesh: The parsed mesh.

    Raises:
        FileNotFoundError: The path does not exist.
        ValueError: The file declares no vertices or no faces.
    """
    return parse_obj(Path(path).read_text(encoding="utf-8", errors="replace"))


def unique_edges(faces: list[tuple[int, ...]]) -> list[tuple[int, int]]:
    """Every polygon edge once, orientation-independent, in first-seen order.

    Args:
        faces: Faces as zero-based vertex index tuples.

    Returns:
        list[tuple[int, int]]: Edges as ``(low, high)`` index pairs.
    """
    seen: dict[tuple[int, int], None] = {}
    for face in faces:
        for start, end in zip(face, face[1:] + face[:1]):
            if start != end:
                seen.setdefault((min(start, end), max(start, end)))
    return list(seen)
