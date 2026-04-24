"""draw.io shape library: index, search, catalogue, and render as SVG snippets.

Stencil XML files are NOT bundled with the package. They are downloaded on
demand from URLs or loaded from local paths, then cached at
``~/.cache/svg-infographics/drawio-stencils/``.

The module works with an empty cache - returns empty results and suggests
running ``shapes index --source <URL>`` to populate.

Supported library formats:
    Format B - stencil XML: <shapes><shape name="...">...</shape></shapes>
    Format A - mxlibrary JSON: <mxlibrary>[{"xml":"...","title":"..."}]</mxlibrary>

CLI usage:
    svg-infographics shapes index --source URL_OR_PATH
    svg-infographics shapes index --refresh
    svg-infographics shapes search QUERY [--limit N] [--library LIB]
    svg-infographics shapes catalogue [--category CAT] [--columns N]
    svg-infographics shapes render NAME [--width W] [--height H]
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from stellars_claude_code_plugins.svg_tools._warning_gate import (
    add_ack_warning_arg,
    enforce_warning_acks,
)

# Module-level accumulator for warning-ack gate. Indexing / render helpers
# deep in the call stack append here instead of printing to stderr; the
# CLI dispatch calls enforce_warning_acks once at the end so all warnings
# surface together with their tokens.
_PENDING_WARNINGS: list[str] = []

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_DIR = Path(os.path.expanduser("~/.cache/svg-infographics/drawio-stencils"))
INDEX_FILE = CACHE_DIR / "_index.json"

DRAWIO_STENCILS_BASE = (
    "https://raw.githubusercontent.com/jgraph/drawio/dev/src/main/webapp/stencils"
)
DEFAULT_SOURCE_URL = f"{DRAWIO_STENCILS_BASE}/basic.xml"

_INDEX_VERSION = 2

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


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DrawioShape:
    """A single shape extracted from a draw.io stencil or library file."""

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
        return {
            "name": self.name,
            "category": self.category,
            "library": self.library,
            "width": self.width,
            "height": self.height,
            "svg_snippet": self.svg_snippet,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DrawioShape:
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
    """Searchable index of draw.io shapes with persistent cache."""

    shapes: list[DrawioShape] = field(default_factory=list)
    categories: dict[str, list[int]] = field(default_factory=dict)
    sources: dict[str, dict] = field(default_factory=dict)

    def search(self, query: str, limit: int = 10, library: str | None = None) -> list[DrawioShape]:
        """Case-insensitive substring search across name and category.

        Scoring: exact > prefix > all-words > substring > partial-word.
        """
        q = query.lower()
        words = q.split()
        scored: list[tuple[int, int, DrawioShape]] = []
        for idx, shape in enumerate(self.shapes):
            if library and shape.category != library:
                continue
            name_lower = shape.name.lower()
            score = 0
            if q == name_lower:
                score = 100
            elif name_lower.startswith(q):
                score = 80
            elif all(w in name_lower for w in words):
                score = 60
            elif q in name_lower or q in shape.category.lower():
                score = 40
            elif any(w in name_lower for w in words):
                score = 20
            if score > 0:
                scored.append((score, idx, shape))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [s[2] for s in scored[:limit]]

    def list_categories(self) -> list[str]:
        return sorted(self.categories.keys())

    def by_category(self, category: str) -> list[DrawioShape]:
        indices = self.categories.get(category, [])
        return [self.shapes[i] for i in indices]

    def save(self, path: str | Path) -> None:
        """Save index as JSON for fast reload."""
        import json as _json

        data = {
            "version": 1,
            "shape_count": len(self.shapes),
            "categories": self.list_categories(),
            "shapes": [
                {
                    "name": s.name,
                    "category": s.category,
                    "library": s.library,
                    "width": s.width,
                    "height": s.height,
                    "svg_snippet": s.svg_snippet,
                }
                for s in self.shapes
            ],
        }
        Path(path).write_text(_json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ShapeIndex":
        """Load pre-built index from JSON."""
        import json as _json

        data = _json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("version", 0) != 1:
            raise ValueError(f"Unsupported index version: {data.get('version')}")
        index = cls()
        for i, s in enumerate(data.get("shapes", [])):
            shape = DrawioShape(
                name=s["name"],
                category=s["category"],
                library=s["library"],
                width=s["width"],
                height=s["height"],
                svg_snippet=s["svg_snippet"],
            )
            index.shapes.append(shape)
            index.categories.setdefault(shape.category, []).append(i)
        return index


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def _ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _download_to_cache(url: str) -> Path:
    """Download a URL to the cache directory. Return local path."""
    _ensure_cache_dir()
    filename = url.rsplit("/", 1)[-1]
    if not filename.endswith(".xml"):
        filename += ".xml"
    dest = CACHE_DIR / filename
    print(f"Downloading {url} ...", file=sys.stderr)
    try:
        urllib.request.urlretrieve(url, str(dest))
        print(f"Saved to {dest} ({dest.stat().st_size:,} bytes)", file=sys.stderr)
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        if dest.exists():
            dest.unlink()
        raise
    return dest


def _resolve_source(source: str) -> Path:
    """Resolve source to a local path. Downloads if URL."""
    if source.startswith("http"):
        return _download_to_cache(source)
    p = Path(source).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Source not found: {source}")
    return p


def _load_index() -> ShapeIndex:
    """Load index from cache. Returns empty index if missing."""
    if not INDEX_FILE.exists():
        return ShapeIndex()
    try:
        raw = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        if raw.get("version") != _INDEX_VERSION:
            return ShapeIndex()
        shapes = [DrawioShape.from_dict(d) for d in raw.get("shapes", [])]
        categories: dict[str, list[int]] = {}
        for idx, shape in enumerate(shapes):
            categories.setdefault(shape.category, []).append(idx)
        index = ShapeIndex(
            shapes=shapes,
            categories=categories,
            sources=raw.get("sources", {}),
        )
        return index
    except (json.JSONDecodeError, KeyError, OSError):
        return ShapeIndex()


def _save_index(index: ShapeIndex) -> None:
    """Save index to cache directory."""
    _ensure_cache_dir()
    data = {
        "version": _INDEX_VERSION,
        "shape_count": len(index.shapes),
        "categories": index.list_categories(),
        "sources": index.sources,
        "shapes": [s.to_dict() for s in index.shapes],
    }
    INDEX_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Anchor helper
# ---------------------------------------------------------------------------


def _anchors_from_bbox(x: float, y: float, w: float, h: float) -> dict[str, tuple[float, float]]:
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
    """Convert mxGraph stencil drawing commands to SVG path d string.

    Stencil coordinates are in absolute units matching the shape's w/h
    declaration, NOT normalised 0..1. No scaling needed.
    """
    parts: list[str] = []

    for el in stencil_el.iter():
        tag = el.tag
        if tag == "move":
            parts.append(f"M {float(el.get('x', 0)):.3f} {float(el.get('y', 0)):.3f}")
        elif tag == "line":
            parts.append(f"L {float(el.get('x', 0)):.3f} {float(el.get('y', 0)):.3f}")
        elif tag == "quad":
            parts.append(
                f"Q {float(el.get('x1', 0)):.3f} {float(el.get('y1', 0)):.3f}"
                f" {float(el.get('x2', 0)):.3f} {float(el.get('y2', 0)):.3f}"
            )
        elif tag == "curve":
            parts.append(
                f"C {float(el.get('x1', 0)):.3f} {float(el.get('y1', 0)):.3f}"
                f" {float(el.get('x2', 0)):.3f} {float(el.get('y2', 0)):.3f}"
                f" {float(el.get('x3', 0)):.3f} {float(el.get('y3', 0)):.3f}"
            )
        elif tag == "close":
            parts.append("Z")
        elif tag == "ellipse":
            ex = float(el.get("x", 0))
            ey = float(el.get("y", 0))
            ew = float(el.get("w", w))
            eh = float(el.get("h", h))
            rx, ry = ew / 2, eh / 2
            cx, cy = ex + rx, ey + ry
            parts.append(
                f"M {cx - rx:.3f} {cy:.3f}"
                f" A {rx:.3f} {ry:.3f} 0 1 0 {cx + rx:.3f} {cy:.3f}"
                f" A {rx:.3f} {ry:.3f} 0 1 0 {cx - rx:.3f} {cy:.3f} Z"
            )
        elif tag == "rect":
            rx_el = float(el.get("x", 0))
            ry_el = float(el.get("y", 0))
            rw = float(el.get("w", w))
            rh = float(el.get("h", h))
            parts.append(
                f"M {rx_el:.3f} {ry_el:.3f}"
                f" L {rx_el + rw:.3f} {ry_el:.3f}"
                f" L {rx_el + rw:.3f} {ry_el + rh:.3f}"
                f" L {rx_el:.3f} {ry_el + rh:.3f} Z"
            )

    return " ".join(parts)


def _stencil_to_svg_snippet(shape_el: ET.Element, w: float, h: float) -> str:
    """Convert a stencil <shape> element to a paste-ready <g> snippet."""
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
    """Parse a single mxlibrary JSON entry into a DrawioShape."""
    title = entry.get("title") or entry.get("label") or ""
    if not title:
        xml_raw = entry.get("xml", "")
        try:
            decoded = urllib.parse.unquote(xml_raw)
            root = ET.fromstring(decoded)
            title = root.get("label") or root.get("value") or ""
        except Exception:
            pass
    if not title:
        return None

    w = float(entry.get("w", 80))
    h = float(entry.get("h", 60))
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
    """Extract SVG snippet from URL-encoded mxGraph XML."""
    placeholder = f'<g><rect width="{w}" height="{h}" fill="none" stroke="currentColor"/></g>'
    if not xml_raw:
        return placeholder
    try:
        decoded = urllib.parse.unquote(xml_raw)
        root = ET.fromstring(decoded)
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
    """Parse a draw.io .xml library file into a list of shapes.

    Handles Format A (mxlibrary JSON array) and Format B (stencil XML).
    """
    path = Path(xml_path)
    if not path.exists():
        _PENDING_WARNINGS.append(f"{path} not found, skipping.")
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        _PENDING_WARNINGS.append(f"{path} XML parse error ({exc}), skipping.")
        return []

    library = path.name
    category = path.stem.lower().replace("-", "_").replace(" ", "_")

    if root.tag == "mxlibrary":
        return _parse_format_a(root.text or "", library, category)

    if root.tag == "shapes":
        # Use the name attribute as category if available
        lib_name = root.get("name", "")
        if lib_name:
            category = lib_name
        return _parse_format_b(root, library, category)

    nested = root.find("shapes")
    if nested is not None:
        return _parse_format_b(nested, library, category)

    _PENDING_WARNINGS.append(f"{path} has unrecognised root tag <{root.tag}>, skipping.")
    return []


def _parse_format_a(json_text: str, library: str, category: str) -> list[DrawioShape]:
    try:
        entries = json.loads(json_text.strip())
    except json.JSONDecodeError as exc:
        _PENDING_WARNINGS.append(f"mxlibrary JSON parse error ({exc}), skipping.")
        return []
    shapes: list[DrawioShape] = []
    for entry in entries:
        shape = _parse_mxlibrary_entry(entry, library, category)
        if shape is not None:
            shapes.append(shape)
    return shapes


def _parse_format_b(shapes_el: ET.Element, library: str, category: str) -> list[DrawioShape]:
    shapes: list[DrawioShape] = []
    for shape_el in shapes_el.findall("shape"):
        name = shape_el.get("name", "").strip()
        if not name:
            continue
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
# Index operations
# ---------------------------------------------------------------------------


def build_index(source_dirs: list[str | Path]) -> ShapeIndex:
    """Scan directories/files/URLs for .xml libraries and build a searchable index.

    Compatibility wrapper that iterates sources and delegates to
    ``index_source`` for each. Used by tests and callers that pass
    multiple sources at once.
    """
    index = ShapeIndex()
    for source in source_dirs:
        resolved = _resolve_source(str(source))
        if resolved.is_dir():
            for xml_file in sorted(resolved.rglob("*.xml")):
                for shape in parse_drawio_library(xml_file):
                    idx = len(index.shapes)
                    index.shapes.append(shape)
                    index.categories.setdefault(shape.category, []).append(idx)
        elif resolved.is_file():
            for shape in parse_drawio_library(resolved):
                idx = len(index.shapes)
                index.shapes.append(shape)
                index.categories.setdefault(shape.category, []).append(idx)
        else:
            _PENDING_WARNINGS.append(f"{resolved} not found, skipping.")
    return index


def index_source(source: str) -> ShapeIndex:
    """Index a stencil library from URL or local path.

    If source starts with http -> download to cache first.
    If local path -> parse directly (no copy to cache).
    Merges with existing index.
    """
    local_path = _resolve_source(source)
    shapes = parse_drawio_library(local_path)

    if not shapes:
        print(f"No shapes found in {source}", file=sys.stderr)
        return _load_index()

    index = _load_index()

    # Remove existing shapes from same library to avoid duplicates
    old_lib = local_path.name
    index.shapes = [s for s in index.shapes if s.library != old_lib]

    # Rebuild categories
    index.categories = {}
    for idx, shape in enumerate(index.shapes):
        index.categories.setdefault(shape.category, []).append(idx)

    # Add new shapes
    for shape in shapes:
        idx = len(index.shapes)
        index.shapes.append(shape)
        index.categories.setdefault(shape.category, []).append(idx)

    # Track source for refresh
    index.sources[local_path.name] = {
        "source": source,
        "filename": local_path.name,
        "category": shapes[0].category,
        "shape_count": len(shapes),
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_index(index)
    print(
        f"Indexed {len(shapes)} shapes from '{shapes[0].category}' ({local_path.name})",
        file=sys.stderr,
    )
    return index


def refresh_index() -> ShapeIndex:
    """Re-download all indexed libraries from their original sources."""
    index = _load_index()
    if not index.sources:
        print("No libraries indexed. Run: shapes index --source <URL>", file=sys.stderr)
        return index

    sources = [info["source"] for info in index.sources.values()]

    # Clear and rebuild
    new_index = ShapeIndex()
    _save_index(new_index)

    for source in sources:
        new_index = index_source(source)

    return new_index


def _no_index_hint() -> None:
    """Print a helpful message when no index exists."""
    print("No shapes indexed.", file=sys.stderr)
    print(
        f"\nTo get started, index a draw.io stencil library:\n"
        f"  svg-infographics shapes index --source {DEFAULT_SOURCE_URL}\n"
        f"\nOther libraries available at:\n"
        f"  {DRAWIO_STENCILS_BASE}/\n"
        f"  e.g. flowchart.xml, networks.xml, bpmn.xml, floorplan.xml",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Shape renderer
# ---------------------------------------------------------------------------


def render_shape(shape: DrawioShape, x: float, y: float, w: float, h: float) -> dict:
    """Scale a draw.io shape to target dimensions.

    Returns dict with svg, anchors, bbox matching calc_primitives contract.
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
    """Render a visual SVG grid catalogue of shapes with labels."""
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
        label = shape.name[:14] + "..." if len(shape.name) > 14 else shape.name
        label_el = (
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" '
            f'font-size="9" text-anchor="middle" class="cat-label">{label}</text>'
        )

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
    if args.refresh:
        idx = refresh_index()
        total = len(idx.shapes)
        libs = len(idx.sources)
        print(f"Refreshed {libs} libraries, {total} shapes total.")
        return

    if not args.source:
        print(
            "Usage: svg-infographics shapes index --source <URL or path>",
            file=sys.stderr,
        )
        print(f"\nDefault: --source {DEFAULT_SOURCE_URL}", file=sys.stderr)
        sys.exit(1)

    idx = index_source(args.source)
    print(f"{len(idx.sources)} libraries indexed, {len(idx.shapes)} shapes total.")


def _cmd_search(args: argparse.Namespace) -> None:
    index = _load_index()
    if not index.shapes:
        _no_index_hint()
        sys.exit(1)

    results = index.search(args.query, limit=args.limit, library=args.library)
    if not results:
        print(f"No shapes matching '{args.query}'.")
        return

    print(f"Found {len(results)} shapes matching '{args.query}':\n")
    for shape in results:
        print(
            f"  {shape.category}/{shape.name:<30} {shape.width}x{shape.height}  [{shape.library}]"
        )


def _cmd_catalogue(args: argparse.Namespace) -> None:
    index = _load_index()
    if not index.shapes:
        _no_index_hint()
        sys.exit(1)

    shapes = index.by_category(args.category) if args.category else index.shapes
    if not shapes:
        hint = f" in category {args.category!r}" if args.category else ""
        print(f"No shapes found{hint}.")
        return

    svg = render_catalogue(shapes, columns=args.columns, cell_size=args.cell_size)

    if args.output:
        Path(args.output).write_text(svg, encoding="utf-8")
        print(f"Catalogue written to {args.output}  ({len(shapes)} shapes)")
    else:
        print(svg)


def _cmd_render(args: argparse.Namespace) -> None:
    index = _load_index()
    if not index.shapes:
        _no_index_hint()
        sys.exit(1)

    results = index.search(args.name, limit=1, library=args.library)
    if not results:
        # Try broader search for suggestions
        broader = index.search(args.name, limit=5)
        if broader:
            print(f"Shape '{args.name}' not found. Did you mean:", file=sys.stderr)
            for s in broader:
                print(f"  {s.category}/{s.name}", file=sys.stderr)
        else:
            print(f"Shape '{args.name}' not found.", file=sys.stderr)
        sys.exit(1)

    shape = results[0]
    w = args.width or shape.width
    h = args.height or shape.height
    result = render_shape(shape, x=args.x, y=args.y, w=w, h=h)

    if args.json:
        output = {
            "name": shape.name,
            "category": shape.category,
            "library": shape.library,
            "original_size": {"w": shape.width, "h": shape.height},
            "svg": result["svg"],
            "anchors": {k: list(v) for k, v in result["anchors"].items()},
            "bbox": list(result["bbox"]),
        }
        print(json.dumps(output, indent=2))
    else:
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
        description=(
            "draw.io stencil library: index, search, catalogue, render. "
            "Downloads on demand, caches at ~/.cache/svg-infographics/drawio-stencils/."
        ),
    )
    sub = parser.add_subparsers(dest="subcmd")

    # index
    p_index = sub.add_parser(
        "index",
        help="Index a stencil library from URL or local path. Downloads if URL.",
    )
    p_index.add_argument(
        "--source",
        help=(f"URL or local path to a stencil XML file. Default: {DEFAULT_SOURCE_URL}"),
    )
    p_index.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download and re-index all previously indexed libraries.",
    )

    # search
    p_search = sub.add_parser("search", help="Search indexed shapes by name pattern.")
    p_search.add_argument("query", help="Shape name or pattern to search for.")
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default 20).")
    p_search.add_argument("--library", help="Restrict search to a specific library/category.")

    # catalogue
    p_cat = sub.add_parser("catalogue", help="List or render a visual SVG grid of shapes.")
    p_cat.add_argument("--category", default="", help="Filter to a single category.")
    p_cat.add_argument(
        "--output", help="Output path for SVG catalogue (prints to stdout if omitted)."
    )
    p_cat.add_argument("--columns", type=int, default=8, help="Grid columns (default 8).")
    p_cat.add_argument(
        "--cell-size", dest="cell_size", type=int, default=100, help="Cell px (default 100)."
    )

    # render
    p_render = sub.add_parser("render", help="Render a single shape as SVG snippet.")
    p_render.add_argument("name", help="Shape name (partial match, first hit used).")
    p_render.add_argument("--x", type=float, default=0.0, help="Target x position.")
    p_render.add_argument("--y", type=float, default=0.0, help="Target y position.")
    p_render.add_argument("--width", type=float, help="Target width in px.")
    p_render.add_argument("--height", type=float, help="Target height in px.")
    p_render.add_argument("--library", help="Restrict to a specific library/category.")
    p_render.add_argument("--json", action="store_true", help="Output as JSON with metadata.")

    # Add --ack-warning to every subparser so the flag is discoverable
    # from any subcommand. The stop-and-think gate fires after dispatch
    # once per invocation - stdout is buffered during dispatch so the
    # gate can block primary output when warnings fire.
    for sp in (p_index, p_search, p_cat, p_render):
        add_ack_warning_arg(sp)

    args = parser.parse_args()

    dispatch = {
        "index": _cmd_index,
        "search": _cmd_search,
        "catalogue": _cmd_catalogue,
        "render": _cmd_render,
    }

    if args.subcmd in dispatch:
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dispatch[args.subcmd](args)
        enforce_warning_acks(
            [f"drawio-shapes: {w}" for w in _PENDING_WARNINGS],
            sys.argv[1:],
            getattr(args, "ack_warning", []) or [],
        )
        # Gate passed (or no warnings) - release buffered stdout.
        sys.stdout.write(buf.getvalue())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
