"""draw.io shape library indexing, searching, and catalogue generation.

Integrates draw.io's open-source SVG stencil libraries as a second-tier shape
source for the svg-infographics plugin. Works without any draw.io files present
(returns empty index with a helpful message).

Supported library formats:
    Format B  - stencil XML: <shapes><shape name="..." ...><foreground>...</foreground></shape>
    Format A  - mxlibrary JSON: <mxlibrary>[{"xml":"...","title":"...","w":80,"h":60}]</mxlibrary>
                (initial release: title + dimensions parsed; SVG extracted when base64 present)

mxGraph path syntax differs from SVG. The ``_mxgraph_to_svg_path`` converter
handles the key differences: move/line/curve/close -> M/L/C/Z.

Index JSON format (version 1):
    {
      "version": 1,
      "shape_count": N,
      "categories": ["aws", "azure", ...],
      "shapes": [{"name": ..., "category": ..., "library": ...,
                  "width": ..., "height": ..., "svg_snippet": ...}]
    }

CLI usage:
    svg-infographics shapes index --source ./drawio-libs/ --output shapes-index.json
    svg-infographics shapes search "database" --index shapes-index.json --limit 5
    svg-infographics shapes catalogue --index shapes-index.json --category general --output cat.svg
    svg-infographics shapes render --index shapes-index.json --name "database" --x 100 --y 200 --w 80 --h 60
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import urllib.parse
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

_INDEX_VERSION = 1

# Stellars-tech palette for catalogue dark-mode support
_PALETTE = {
    "bg_light": "#f4f8fb",
    "bg_dark": "#0d1117",
    "card_light": "#ffffff",
    "card_dark": "#161b22",
    "fg_light": "#1a5a6e",
    "fg_dark": "#b8e4f0",
    "stroke_light": "#0096d1",
    "stroke_dark": "#005f7a",
    "accent": "#0096d1",
}


@dataclass
class DrawioShape:
    """A single shape extracted from a draw.io stencil or library file.

    Attributes:
        name: Display name of the shape.
        category: Logical group (usually the library filename stem).
        library: Source filename (basename only).
        width: Default render width in px.
        height: Default render height in px.
        svg_snippet: Paste-ready ``<g>`` element at original size.
        anchor_points: Nine cardinal anchor points keyed by label, derived
            from the default bounding box (top-left origin).
    """

    name: str
    category: str
    library: str
    width: float
    height: float
    svg_snippet: str
    anchor_points: dict[str, tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.anchor_points:
            self.anchor_points = _anchors_from_bbox(0.0, 0.0, self.width, self.height)

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict (anchor_points omitted for compactness)."""
        return {
            "name": self.name,
            "category": self.category,
            "library": self.library,
            "width": self.width,
            "height": self.height,
            "svg_snippet": self.svg_snippet,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DrawioShape":
        """Deserialise from an index JSON dict."""
        return cls(
            name=d["name"],
            category=d["category"],
            library=d["library"],
            width=float(d["width"]),
            height=float(d["height"]),
            svg_snippet=d["svg_snippet"],
        )


@dataclass
class ShapeIndex:
    """Searchable index of draw.io shapes.

    Attributes:
        shapes: Flat list of all parsed shapes.
        categories: Maps category name -> list of shape indices into ``shapes``.
    """

    shapes: list[DrawioShape] = field(default_factory=list)
    categories: dict[str, list[int]] = field(default_factory=dict)

    def search(self, query: str, limit: int = 10) -> list[DrawioShape]:
        """Case-insensitive substring search across name and category.

        Args:
            query: Search term (partial match, case-insensitive).
            limit: Maximum number of results to return.

        Returns:
            Matching shapes, name-exact matches first, then category matches.
        """
        q = query.lower()
        exact: list[DrawioShape] = []
        partial: list[DrawioShape] = []
        for shape in self.shapes:
            name_lower = shape.name.lower()
            if q == name_lower:
                exact.append(shape)
            elif q in name_lower or q in shape.category.lower():
                partial.append(shape)
        return (exact + partial)[:limit]

    def list_categories(self) -> list[str]:
        """Return sorted list of all category names."""
        return sorted(self.categories.keys())

    def by_category(self, category: str) -> list[DrawioShape]:
        """Return all shapes belonging to ``category``.

        Args:
            category: Exact category name (case-sensitive).

        Returns:
            Matching shapes, empty list if category is unknown.
        """
        indices = self.categories.get(category, [])
        return [self.shapes[i] for i in indices]

    def save(self, path: str | Path) -> None:
        """Serialise the index to JSON at ``path``.

        Args:
            path: Destination file path.
        """
        data = {
            "version": _INDEX_VERSION,
            "shape_count": len(self.shapes),
            "categories": self.list_categories(),
            "shapes": [s.to_dict() for s in self.shapes],
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ShapeIndex":
        """Load a pre-built index from JSON.

        Args:
            path: Path to the index file produced by ``save``.

        Returns:
            A populated ``ShapeIndex``.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            ValueError: If the JSON is malformed or version is unsupported.
        """
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("version") != _INDEX_VERSION:
            raise ValueError(
                f"Unsupported index version {raw.get('version')!r}. Expected {_INDEX_VERSION}."
            )
        shapes = [DrawioShape.from_dict(d) for d in raw.get("shapes", [])]
        categories: dict[str, list[int]] = {}
        for idx, shape in enumerate(shapes):
            categories.setdefault(shape.category, []).append(idx)
        return cls(shapes=shapes, categories=categories)


# ---------------------------------------------------------------------------
# Anchor helper
# ---------------------------------------------------------------------------


def _anchors_from_bbox(x: float, y: float, w: float, h: float) -> dict[str, tuple[float, float]]:
    """Derive nine cardinal anchor points from a bounding box.

    Args:
        x: Left edge of the box.
        y: Top edge of the box.
        w: Box width.
        h: Box height.

    Returns:
        Dict keyed by ``top-left``, ``top``, ``top-right``, ``right``,
        ``bottom-right``, ``bottom``, ``bottom-left``, ``left``, ``centre``.
    """
    cx, cy = x + w / 2, y + h / 2
    return {
        "top-left": (x, y),
        "top": (cx, y),
        "top-right": (x + w, y),
        "right": (x + w, cy),
        "bottom-right": (x + w, y + h),
        "bottom": (cx, y + h),
        "bottom-left": (x, y + h),
        "left": (x, cy),
        "centre": (cx, cy),
    }


# ---------------------------------------------------------------------------
# mxGraph stencil path converter
# ---------------------------------------------------------------------------


def _mxgraph_to_svg_path(stencil_el: ET.Element, w: float, h: float) -> str:
    """Convert an mxGraph stencil ``<foreground>`` element to an SVG path ``d`` string.

    mxGraph stencil coordinates are normalised to a [0,1] unit box; we scale
    them to (w, h). Command mapping:

    +-----------+---------+
    | mxGraph   | SVG     |
    +===========+=========+
    | move      | M       |
    | line      | L       |
    | quad      | Q       |
    | curve     | C       |
    | close     | Z       |
    +-----------+---------+

    Unrecognised elements are silently skipped so that partial stencils still
    produce usable paths.

    Args:
        stencil_el: The ``<foreground>`` (or ``<background>``) XML element.
        w: Target width used to scale normalised coordinates.
        h: Target height used to scale normalised coordinates.

    Returns:
        SVG path ``d`` attribute string, empty string if no path data found.
    """
    parts: list[str] = []

    def sx(v: str) -> float:
        return float(v) * w / 100

    def sy(v: str) -> float:
        return float(v) * h / 100

    for el in stencil_el.iter():
        tag = el.tag
        if tag == "move":
            parts.append(f"M {sx(el.get('x', '0')):.3f} {sy(el.get('y', '0')):.3f}")
        elif tag == "line":
            parts.append(f"L {sx(el.get('x', '0')):.3f} {sy(el.get('y', '0')):.3f}")
        elif tag == "quad":
            parts.append(
                f"Q {sx(el.get('x1', '0')):.3f} {sy(el.get('y1', '0')):.3f}"
                f" {sx(el.get('x2', '0')):.3f} {sy(el.get('y2', '0')):.3f}"
            )
        elif tag == "curve":
            parts.append(
                f"C {sx(el.get('x1', '0')):.3f} {sy(el.get('y1', '0')):.3f}"
                f" {sx(el.get('x2', '0')):.3f} {sy(el.get('y2', '0')):.3f}"
                f" {sx(el.get('x3', '0')):.3f} {sy(el.get('y3', '0')):.3f}"
            )
        elif tag == "close":
            parts.append("Z")
        elif tag == "ellipse":
            cx = sx(el.get("x", "50")) + sx(el.get("w", "50")) / 2
            cy = sy(el.get("y", "50")) + sy(el.get("h", "50")) / 2
            rx = sx(el.get("w", "50")) / 2
            ry = sy(el.get("h", "50")) / 2
            # Approximate ellipse via two arcs
            parts.append(
                f"M {cx - rx:.3f} {cy:.3f}"
                f" A {rx:.3f} {ry:.3f} 0 1 0 {cx + rx:.3f} {cy:.3f}"
                f" A {rx:.3f} {ry:.3f} 0 1 0 {cx - rx:.3f} {cy:.3f} Z"
            )
        elif tag == "rect":
            rx_el = sx(el.get("x", "0"))
            ry_el = sy(el.get("y", "0"))
            rw = sx(el.get("w", "100"))
            rh = sy(el.get("h", "100"))
            parts.append(
                f"M {rx_el:.3f} {ry_el:.3f}"
                f" L {rx_el + rw:.3f} {ry_el:.3f}"
                f" L {rx_el + rw:.3f} {ry_el + rh:.3f}"
                f" L {rx_el:.3f} {ry_el + rh:.3f} Z"
            )
        # arc, roundrect and other structural elements are skipped

    return " ".join(parts)


def _stencil_to_svg_snippet(shape_el: ET.Element, w: float, h: float) -> str:
    """Convert a stencil ``<shape>`` element to a paste-ready ``<g>`` snippet.

    Args:
        shape_el: The ``<shape>`` XML element from a Format B library.
        w: Default width from the shape definition.
        h: Default height from the shape definition.

    Returns:
        An SVG ``<g>`` string with stroke/fill classes applied.
    """
    paths: list[str] = []
    for section in ("background", "foreground"):
        section_el = shape_el.find(section)
        if section_el is not None:
            d = _mxgraph_to_svg_path(section_el, w, h)
            if d:
                fill = "none" if section == "foreground" else "currentColor"
                paths.append(
                    f'<path d="{d}" fill="{fill}" stroke="currentColor"'
                    f' stroke-width="1" fill-opacity="0.12"/>'
                )
    inner = (
        "\n  ".join(paths)
        if paths
        else f'<rect width="{w}" height="{h}" fill="none" stroke="currentColor"/>'
    )
    return f"<g>\n  {inner}\n</g>"


# ---------------------------------------------------------------------------
# Format A: mxlibrary JSON inside <mxlibrary>
# ---------------------------------------------------------------------------


def _parse_mxlibrary_entry(entry: dict, library: str, category: str) -> DrawioShape | None:
    """Parse a single mxlibrary JSON entry into a DrawioShape.

    Extracts title, width, height, and attempts to decode embedded SVG from
    the ``xml`` field when it is base64-encoded. Falls back to a placeholder
    ``<g>`` when no decodable SVG is present.

    Args:
        entry: One dict from the mxlibrary JSON array.
        library: Source filename (basename).
        category: Category derived from the library filename stem.

    Returns:
        A ``DrawioShape`` or ``None`` if the entry lacks a usable title.
    """
    title = entry.get("title") or entry.get("label") or ""
    if not title:
        # Attempt to extract name from the encoded xml
        xml_raw = entry.get("xml", "")
        try:
            decoded = urllib.parse.unquote(xml_raw)
            root = ET.fromstring(decoded)
            title = root.get("label") or root.get("value") or root.find(".//@label") or ""
        except Exception:
            pass
    if not title:
        return None

    w = float(entry.get("w", 80))
    h = float(entry.get("h", 60))

    # Try to extract embedded SVG from the xml field
    svg_snippet = _extract_svg_from_mxlibrary_xml(entry.get("xml", ""), w, h)

    return DrawioShape(
        name=title,
        category=category,
        library=library,
        width=w,
        height=h,
        svg_snippet=svg_snippet,
    )


def _extract_svg_from_mxlibrary_xml(xml_raw: str, w: float, h: float) -> str:
    """Attempt to extract an SVG snippet from a URL-encoded mxGraph XML string.

    Args:
        xml_raw: URL-encoded mxGraph XML from the mxlibrary ``xml`` field.
        w: Default shape width (used as fallback rect dimensions).
        h: Default shape height.

    Returns:
        A ``<g>`` SVG string, either extracted or a plain placeholder rect.
    """
    placeholder = f'<g><rect width="{w}" height="{h}" fill="none" stroke="currentColor"/></g>'
    if not xml_raw:
        return placeholder
    try:
        decoded = urllib.parse.unquote(xml_raw)
        root = ET.fromstring(decoded)
        # Look for an embedded <svg> element or style="shape=..."
        svg_el = root.find(".//{http://www.w3.org/2000/svg}svg") or root.find(".//svg")
        if svg_el is not None:
            inner = ET.tostring(svg_el, encoding="unicode")
            return f"<g>{inner}</g>"
    except Exception:
        pass
    return placeholder


# ---------------------------------------------------------------------------
# Public parser
# ---------------------------------------------------------------------------


def parse_drawio_library(xml_path: str | Path) -> list[DrawioShape]:
    """Parse a draw.io ``.xml`` library file into a list of shapes.

    Handles Format A (mxlibrary JSON array) and Format B (stencil XML).
    Returns an empty list and prints a warning when the file cannot be parsed.

    Args:
        xml_path: Path to the draw.io XML library file.

    Returns:
        List of ``DrawioShape`` instances, possibly empty.
    """
    path = Path(xml_path)
    if not path.exists():
        print(f"Warning: {path} not found, skipping.", file=sys.stderr)
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        print(f"Warning: {path} XML parse error ({exc}), skipping.", file=sys.stderr)
        return []

    library = path.name
    category = path.stem.lower().replace("-", "_").replace(" ", "_")

    # Format A: <mxlibrary>[...]</mxlibrary>
    if root.tag == "mxlibrary":
        return _parse_format_a(root.text or "", library, category)

    # Format B: <shapes><shape .../></shapes>
    if root.tag == "shapes":
        return _parse_format_b(root, library, category)

    # Some stencil files have a root wrapper with nested <shapes>
    nested = root.find("shapes")
    if nested is not None:
        return _parse_format_b(nested, library, category)

    print(
        f"Warning: {path} has unrecognised root tag <{root.tag}>, skipping.",
        file=sys.stderr,
    )
    return []


def _parse_format_a(json_text: str, library: str, category: str) -> list[DrawioShape]:
    """Parse Format A mxlibrary JSON content.

    Args:
        json_text: The text content of the ``<mxlibrary>`` element.
        library: Source filename.
        category: Derived category name.

    Returns:
        List of shapes, possibly empty.
    """
    try:
        entries = json.loads(json_text.strip())
    except json.JSONDecodeError as exc:
        print(f"Warning: mxlibrary JSON parse error ({exc}), skipping.", file=sys.stderr)
        return []

    shapes: list[DrawioShape] = []
    for entry in entries:
        shape = _parse_mxlibrary_entry(entry, library, category)
        if shape is not None:
            shapes.append(shape)
    return shapes


def _parse_format_b(shapes_el: ET.Element, library: str, category: str) -> list[DrawioShape]:
    """Parse Format B stencil XML content.

    Args:
        shapes_el: The ``<shapes>`` XML element.
        library: Source filename.
        category: Derived category name.

    Returns:
        List of shapes.
    """
    shapes: list[DrawioShape] = []
    for shape_el in shapes_el.findall("shape"):
        name = shape_el.get("name", "").strip()
        if not name:
            continue
        # draw.io stencil name often uses path notation: "group/name"
        display_name = name.split("/")[-1].replace("_", " ").replace("-", " ")
        w = float(shape_el.get("w", 100))
        h = float(shape_el.get("h", 100))
        svg_snippet = _stencil_to_svg_snippet(shape_el, w, h)
        shapes.append(
            DrawioShape(
                name=display_name,
                category=category,
                library=library,
                width=w,
                height=h,
                svg_snippet=svg_snippet,
            )
        )
    return shapes


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------


DEFAULT_STENCIL_URL = (
    "https://raw.githubusercontent.com/jgraph/drawio/master/src/main/webapp/stencils/general.xml"
)

CACHE_DIR = Path.home() / ".cache" / "svg-infographics" / "drawio-stencils"


def _resolve_source(source: str | Path) -> Path:
    """Resolve a source to a local path. URLs are downloaded and cached."""
    source_str = str(source)
    if source_str.startswith("http://") or source_str.startswith("https://"):
        import urllib.request

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        filename = source_str.rsplit("/", 1)[-1]
        cached = CACHE_DIR / filename
        if not cached.exists():
            print(f"Downloading {source_str} -> {cached}", file=sys.stderr)
            urllib.request.urlretrieve(source_str, cached)
        return cached
    return Path(source)


def build_index(source_dirs: list[str | Path]) -> ShapeIndex:
    """Scan directories/files/URLs for ``.xml`` library files and build a searchable index.

    Each source can be a directory (walked recursively), a single XML file,
    or a URL (downloaded to ``~/.cache/svg-infographics/drawio-stencils/``
    on first use, then parsed from cache). Non-existent directories are
    skipped with a warning.

    Args:
        source_dirs: List of directory paths, file paths, or URLs.

    Returns:
        A ``ShapeIndex`` with all parsed shapes.
    """
    index = ShapeIndex()
    for source in source_dirs:
        resolved = _resolve_source(source)
        if resolved.is_file():
            for shape in parse_drawio_library(resolved):
                idx = len(index.shapes)
                index.shapes.append(shape)
                index.categories.setdefault(shape.category, []).append(idx)
        elif resolved.is_dir():
            for xml_file in sorted(resolved.rglob("*.xml")):
                for shape in parse_drawio_library(xml_file):
                    idx = len(index.shapes)
                    index.shapes.append(shape)
                    index.categories.setdefault(shape.category, []).append(idx)
        else:
            print(f"Warning: {resolved} not found, skipping.", file=sys.stderr)
    return index


# ---------------------------------------------------------------------------
# Shape renderer
# ---------------------------------------------------------------------------


def render_shape(shape: DrawioShape, x: float, y: float, w: float, h: float) -> dict:
    """Scale a draw.io shape to target dimensions.

    Wraps the shape's SVG snippet in a ``<g transform="...">`` that translates
    to (x, y) and scales from the shape's native dimensions to (w, h). The
    returned dict matches the ``calc_primitives`` contract so it can be used
    interchangeably with native primitives.

    Args:
        shape: The shape to render.
        x: Target x position (top-left).
        y: Target y position (top-left).
        w: Target width in px.
        h: Target height in px.

    Returns:
        Dict with keys ``svg`` (str), ``anchors`` (dict), ``bbox`` (4-tuple).
    """
    sx = w / shape.width if shape.width else 1.0
    sy = h / shape.height if shape.height else 1.0
    transform = f"translate({x},{y}) scale({sx:.6f},{sy:.6f})"
    svg = f'<g transform="{transform}">\n{shape.svg_snippet}\n</g>'
    anchors = _anchors_from_bbox(x, y, w, h)
    return {"svg": svg, "anchors": anchors, "bbox": (x, y, w, h)}


# ---------------------------------------------------------------------------
# Catalogue renderer
# ---------------------------------------------------------------------------


def render_catalogue(
    shapes: list[DrawioShape],
    columns: int = 8,
    cell_size: int = 100,
) -> str:
    """Render a visual SVG grid catalogue of shapes with labels.

    Each cell contains the shape scaled to fit a square, with the shape name
    below. Uses the stellars-tech palette with dark-mode support via
    ``prefers-color-scheme``.

    Args:
        shapes: Shapes to include in the catalogue.
        columns: Number of columns in the grid.
        cell_size: Width and height of each grid cell in px.

    Returns:
        Complete SVG document as a string.
    """
    if not shapes:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"></svg>'

    rows = (len(shapes) + columns - 1) // columns
    label_height = 20
    padding = 8
    shape_area = cell_size - 2 * padding - label_height
    total_w = columns * cell_size
    total_h = rows * cell_size

    cells: list[str] = []
    for idx, shape in enumerate(shapes):
        col = idx % columns
        row = idx // columns
        cx = col * cell_size
        cy = row * cell_size

        # Scale shape into the cell's shape area
        scale_x = shape_area / shape.width if shape.width else 1.0
        scale_y = shape_area / shape.height if shape.height else 1.0
        scale = min(scale_x, scale_y)
        scaled_w = shape.width * scale
        scaled_h = shape.height * scale
        offset_x = cx + padding + (shape_area - scaled_w) / 2
        offset_y = cy + padding + (shape_area - scaled_h) / 2

        transform = f"translate({offset_x:.2f},{offset_y:.2f}) scale({scale:.6f},{scale:.6f})"
        shape_svg = f'<g transform="{transform}">{shape.svg_snippet}</g>'

        label_x = cx + cell_size / 2
        label_y = cy + cell_size - 4
        label = shape.name[:14] + "…" if len(shape.name) > 14 else shape.name
        label_el = (
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" '
            f'font-size="9" text-anchor="middle" class="cat-label">{label}</text>'
        )

        # Cell border
        border = (
            f'<rect x="{cx}" y="{cy}" width="{cell_size}" height="{cell_size}" class="cat-cell"/>'
        )

        cells.append(f"<!-- {shape.name} -->\n{border}\n{shape_svg}\n{label_el}")

    p = _PALETTE
    css = f"""
    <style>
      .cat-cell {{
        fill: {p["card_light"]}; stroke: {p["stroke_light"]}; stroke-width: 0.5;
      }}
      .cat-label {{
        fill: {p["fg_light"]}; font-family: 'Segoe UI', Arial, sans-serif;
      }}
      .cat-shape-stroke {{ stroke: {p["stroke_light"]}; }}
      @media (prefers-color-scheme: dark) {{
        .cat-cell {{ fill: {p["card_dark"]}; stroke: {p["stroke_dark"]}; }}
        .cat-label {{ fill: {p["fg_dark"]}; }}
        .cat-shape-stroke {{ stroke: {p["stroke_dark"]}; }}
      }}
    </style>""".strip()

    grid_content = "\n".join(cells)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}">\n'
        f"{css}\n"
        f'<rect width="{total_w}" height="{total_h}" class="cat-cell"/>\n'
        f"{grid_content}\n"
        f"</svg>"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_index(args: argparse.Namespace) -> None:
    sources = [Path(s) for s in args.source]
    index = build_index(sources)
    output = Path(args.output)
    index.save(output)
    print(f"Indexed {len(index.shapes)} shapes across {len(index.categories)} categories.")
    print(f"Saved to {output}")


def _cmd_search(args: argparse.Namespace) -> None:
    if not Path(args.index).exists():
        print(f"Index file not found: {args.index}", file=sys.stderr)
        sys.exit(1)
    index = ShapeIndex.load(args.index)
    results = index.search(args.query, limit=args.limit)
    if not results:
        print("No shapes found.")
        return
    for shape in results:
        print(f"{shape.category}/{shape.name}  ({shape.width}x{shape.height})  [{shape.library}]")


def _cmd_catalogue(args: argparse.Namespace) -> None:
    if not Path(args.index).exists():
        print(f"Index file not found: {args.index}", file=sys.stderr)
        sys.exit(1)
    index = ShapeIndex.load(args.index)
    shapes = index.by_category(args.category) if args.category else index.shapes
    if not shapes:
        category_hint = f" in category {args.category!r}" if args.category else ""
        print(f"No shapes found{category_hint}.")
        return
    svg = render_catalogue(shapes, columns=args.columns, cell_size=args.cell_size)
    output = Path(args.output)
    output.write_text(svg, encoding="utf-8")
    print(f"Catalogue written to {output}  ({len(shapes)} shapes)")


def _cmd_render(args: argparse.Namespace) -> None:
    if not Path(args.index).exists():
        print(f"Index file not found: {args.index}", file=sys.stderr)
        sys.exit(1)
    index = ShapeIndex.load(args.index)
    results = index.search(args.name, limit=1)
    if not results:
        print(f"Shape {args.name!r} not found.", file=sys.stderr)
        sys.exit(1)
    shape = results[0]
    result = render_shape(shape, x=args.x, y=args.y, w=args.w, h=args.h)
    print("SVG snippet:")
    print(result["svg"])
    print("\nAnchors:")
    for label, (ax, ay) in result["anchors"].items():
        print(f"  {label:<14} ({ax:.1f}, {ay:.1f})")
    print(
        f"\nBBox: x={result['bbox'][0]}, y={result['bbox'][1]}, "
        f"w={result['bbox'][2]}, h={result['bbox'][3]}"
    )


def main() -> None:
    """Entry point for the ``shapes`` subcommand of ``svg-infographics``."""
    parser = argparse.ArgumentParser(
        prog="svg-infographics shapes",
        description="draw.io shape library indexing, searching, and catalogue generation.",
    )
    sub = parser.add_subparsers(dest="subcmd", required=True)

    # index
    p_index = sub.add_parser("index", help="Scan directories and build a shape index JSON.")
    p_index.add_argument(
        "--source",
        nargs="+",
        required=True,
        help="One or more directories containing draw.io .xml library files.",
    )
    p_index.add_argument("--output", required=True, help="Output path for the JSON index.")

    # search
    p_search = sub.add_parser("search", help="Search shapes by name or category.")
    p_search.add_argument("query", help="Search term (partial match, case-insensitive).")
    p_search.add_argument("--index", required=True, help="Path to the shapes-index.json file.")
    p_search.add_argument("--limit", type=int, default=10, help="Maximum results (default 10).")

    # catalogue
    p_cat = sub.add_parser("catalogue", help="Render a visual SVG grid of shapes.")
    p_cat.add_argument("--index", required=True, help="Path to the shapes-index.json file.")
    p_cat.add_argument("--category", default="", help="Filter to a single category (optional).")
    p_cat.add_argument("--output", required=True, help="Output path for the SVG catalogue.")
    p_cat.add_argument("--columns", type=int, default=8, help="Grid columns (default 8).")
    p_cat.add_argument(
        "--cell-size", dest="cell_size", type=int, default=100, help="Cell px (default 100)."
    )

    # render
    p_render = sub.add_parser("render", help="Render a single shape at target position/size.")
    p_render.add_argument("--index", required=True, help="Path to the shapes-index.json file.")
    p_render.add_argument(
        "--name", required=True, help="Shape name (partial match, first hit used)."
    )
    p_render.add_argument("--x", type=float, default=0.0, help="Target x position.")
    p_render.add_argument("--y", type=float, default=0.0, help="Target y position.")
    p_render.add_argument("--w", type=float, default=80.0, help="Target width.")
    p_render.add_argument("--h", type=float, default=60.0, help="Target height.")

    args = parser.parse_args()
    dispatch = {
        "index": _cmd_index,
        "search": _cmd_search,
        "catalogue": _cmd_catalogue,
        "render": _cmd_render,
    }
    dispatch[args.subcmd](args)


if __name__ == "__main__":
    main()
