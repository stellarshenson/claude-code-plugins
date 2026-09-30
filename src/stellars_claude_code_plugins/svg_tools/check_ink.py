"""Overlap check from rendered ink.

Chromium draws the elements and two elements collide only where their painted
pixels coincide: no estimated text widths, no padded boxes, no curve standing in
for its bounding rectangle. The browser's element boxes feed a collision tree
(shapely STRtree): only pairs whose boxes come within the clearance get the
pixel test, and only elements in such a pair are drawn. Elements whose boxes do
not intersect are drawn together in one screenshot and cut apart by their boxes.

Findings, HARD unless marked:

- ``shapes-partly-overlap`` - two shapes overlap and neither holds the other
- ``edge-crosses-text``     - a stroke or line is painted across text
- ``text-on-text``          - the glyphs of two texts overlap
- ``text-straddles-shape``  - text lies partly inside, partly outside a shape
- ``clearance`` (SOFT)      - text comes closer than the clearance to text, a
                              stroke or a line without touching, or an arrowhead
                              comes that close to a shape it does not point into
                              (touching it reports a gap of 0)

Element kinds come from geometry: text; lines are open strokes and small
triangles (arrowheads); shapes are closed outlines, judged by the region they
enclose whether filled or not. Left out by design: the backdrop (the
``background`` layer and full-canvas plates); a faint unstroked fill (a tint
band) against shapes and lines; shapes and lines inside one icon-sized group
(at most 100 units a side and 6400 square units),
which are parts of one drawing; shape overlaps shallower than 2 units, which
are shapes touching; plain lines against shapes (axes through markers,
gridlines behind bars) and lines against each other, which the connector and
collide checks own.
"""

from __future__ import annotations

import atexit
from dataclasses import dataclass, field
from io import BytesIO
import math
from pathlib import Path
import xml.parsers.expat

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_erosion, distance_transform_edt
from shapely import STRtree, box

SCALE = 2  # device pixels per SVG unit
ALPHA = 128  # alpha at or above this is ink
CLEARANCE = 3.0  # SVG units
REACH = 12  # SVG units searched beyond a line end for the shape it points into
CONTAIN = 0.99  # share of ink inside the other element that counts as fully inside
SPILL = 2.0  # SVG units a nested shape may stick out (an accent bar past a rounded corner)
TOUCH = 2.0  # SVG units: a shallower shape overlap is two shapes touching
ICON = (100, 6400)  # longest side and area, SVG units: a group this small is one drawing

_ENUMERATE = """
([arrow, tint, side, area]) => {
  const svg = document.documentElement;
  const v = svg.viewBox && svg.viewBox.baseVal;
  const r0 = svg.getBoundingClientRect();
  const vb = v && v.width ? [v.x, v.y, v.width, v.height] : [0, 0, r0.width, r0.height];
  svg.setAttribute('width', vb[2]);
  svg.setAttribute('height', vb[3]);
  const leaf = 'text, rect, circle, ellipse, line, polyline, polygon, path, image, use';
  const template = 'defs, marker, clipPath, mask, pattern, symbol';
  const all = Array.from(svg.querySelectorAll('*'));
  const drawn = (el) => {
    if (getComputedStyle(el).visibility === 'hidden') return false;
    for (let a = el; a && a.nodeType === 1; a = a.parentNode)
      if (getComputedStyle(a).display === 'none') return false;
    return true;
  };
  const out = [];
  all.forEach((el, k) => {
    if (!el.matches(leaf) || el.closest(template) || el.parentNode.closest('text')) return;
    if (!drawn(el)) return;
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) return;
    const s = getComputedStyle(el);
    const sw = s.stroke !== 'none' ? parseFloat(s.strokeWidth) || 0 : 0;
    const marker = [s.markerStart, s.markerMid, s.markerEnd].some((m) => m && m !== 'none');
    const pad = 2 + sw / 2 + (marker ? 4 * sw + 8 : 0);
    let layer = '', group = '', drawing = -1, alpha = 1;
    for (let a = el; a && a !== svg; a = a.parentNode) alpha *= parseFloat(getComputedStyle(a).opacity);
    for (let a = el.parentNode; a && a !== svg; a = a.parentNode) {
      if (!group && a.id) group = a.id;
      // the outermost small group is the drawing this element belongs to; groups
      // only grow outward, so the walk keeps the last small one it meets
      const g = a.getBoundingClientRect();
      if (Math.max(g.width, g.height) <= side && g.width * g.height <= area) drawing = all.indexOf(a);
      if (a.parentNode === svg) layer = a.id || '';
    }
    const m = el.getScreenCTM();
    const pt = (x, y) => { const p = new DOMPoint(x, y).matrixTransform(m); return [p.x, p.y]; };
    const ends = [];
    let closed = !['line', 'polyline', 'path'].includes(el.tagName), isArrow = false;
    if (['path', 'line', 'polyline'].includes(el.tagName)) {
      const L = el.getTotalLength();
      if (L > 0) {
        const at = (d) => { const p = el.getPointAtLength(Math.max(0, Math.min(L, d))); return pt(p.x, p.y); };
        const a0 = at(0), a1 = at(1), b0 = at(L), b1 = at(L - 1);
        closed = el.tagName !== 'line' && (Math.hypot(a0[0] - b0[0], a0[1] - b0[1]) < 0.5
          || /[zZ]\\s*$/.test(el.getAttribute('d') || ''));
        if (!closed) {
          ends.push([a0[0], a0[1], a0[0] - a1[0], a0[1] - a1[1]]);
          ends.push([b0[0], b0[1], b0[0] - b1[0], b0[1] - b1[1]]);
        }
      }
    } else if (el.tagName === 'polygon' && el.points.numberOfItems === 3) {
      const p = [0, 1, 2].map((i) => { const q = el.points.getItem(i); return pt(q.x, q.y); });
      const side = (i, j) => Math.hypot(p[i][0] - p[j][0], p[i][1] - p[j][1]);
      isArrow = Math.max(side(0, 1), side(1, 2), side(0, 2)) <= arrow;
      // the tip is the apex: the corner whose two sides are closest in length
      let tip = null;
      for (let i = 0; i < 3; i++) {
        const [j, l] = [0, 1, 2].filter((x) => x !== i);
        const skew = Math.abs(side(i, j) - side(i, l));
        const mx = (p[j][0] + p[l][0]) / 2, my = (p[j][1] + p[l][1]) / 2;
        if (!tip || skew < tip[4]) tip = [p[i][0], p[i][1], p[i][0] - mx, p[i][1] - my, skew];
      }
      if (isArrow) ends.push(tip.slice(0, 4));
    }
    const hasFill = s.fill !== 'none' && el.tagName !== 'line';
    el.setAttribute('data-ink', String(k));
    out.push({
      index: k, tag: el.tagName, id: el.id || '', group, layer, drawing,
      text: el.tagName === 'text' ? el.textContent.replace(/\\s+/g, ' ').trim().slice(0, 48) : '',
      box: [r.left - pad, r.top - pad, r.right + pad, r.bottom + pad],
      stroke: sw > 0, closed, arrow: isArrow, ends,
      tint: el.tagName !== 'text' && sw === 0 && hasFill && parseFloat(s.fillOpacity) * alpha < tint,
    });
  });
  return {vb, elements: out};
}
"""

# One pass paints only the elements marked data-solo, each as that pass asks:
# `all` as authored, `region` the enclosed area in solid ink, `stroke` the
# stroke alone. Opacity and filters are lifted so faint fills and glows paint
# their true extent and nothing more.
_MASK_CSS = """
svg * { opacity: 1 !important; filter: none !important; }
[data-ink] { visibility: hidden !important; }
[data-ink][data-solo] { visibility: visible !important; }
[data-solo=all], [data-solo=all] * { fill-opacity: 1 !important; stroke-opacity: 1 !important; }
[data-solo=region] { fill: #000 !important; fill-opacity: 1 !important; stroke: none !important; }
[data-solo=stroke] { fill: none !important; stroke-opacity: 1 !important; }
"""

_ADD_STYLE = """
(css) => {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  s.textContent = css;
  document.documentElement.appendChild(s);
}
"""

_SOLO = """
([ks, pass]) => {
  document.querySelectorAll('[data-solo]').forEach((e) => e.removeAttribute('data-solo'));
  for (const k of ks) document.querySelector(`[data-ink="${k}"]`).setAttribute('data-solo', pass);
}
"""


@dataclass
class InkElement:
    """One drawn leaf element and its painted pixels."""

    index: int  # position among the <svg> root's descendants, document order
    line: int  # source line of the element's start tag
    tag: str
    id: str
    group: str  # nearest ancestor id
    layer: str  # id of the top-level group holding it
    text: str
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 in viewport units, padded for strokes
    has_stroke: bool
    closed: bool
    arrow: bool  # a small triangle: a connector's arrowhead
    tint: bool  # a faint unstroked fill
    ends: list[tuple[float, float, float, float]]  # x, y, dx, dy of each open end, outward
    drawing: int = -1  # outermost icon-sized group holding it, document index; -1 when none
    origin: tuple[int, int] = (0, 0)  # device pixel of the masks' top-left corner
    fill: np.ndarray | None = None  # text and arrowheads: all ink; shapes: the enclosed region
    stroke: np.ndarray | None = None
    targets: set[int] = field(default_factory=set)  # shapes a line end points into

    @property
    def kind(self) -> str:
        if self.tag == "text":
            return "text"
        return "line" if self.arrow or not self.closed else "shape"

    @property
    def passes(self) -> list[tuple[str, str]]:
        """(paint pass, mask slot) pairs this element needs."""
        if self.tag in ("text", "image", "use") or self.arrow:
            return [("all", "fill")]
        if self.kind == "line":
            return [("stroke", "stroke")]
        return [("region", "fill")] + ([("stroke", "stroke")] if self.has_stroke else [])

    @property
    def ink(self) -> np.ndarray | None:
        if self.fill is None or self.stroke is None:
            return self.fill if self.stroke is None else self.stroke
        return self.fill | self.stroke

    @property
    def edge(self) -> np.ndarray | None:
        """The stroke, or for an unstroked shape the outline of its region."""
        if self.stroke is not None or self.fill is None:
            return self.stroke
        return self.fill & ~binary_erosion(self.fill)

    def describe(self) -> str:
        if self.text:
            name = f'text "{self.text}"'
        elif self.id:
            name = f"{self.tag} #{self.id}"
        elif self.group:
            name = f"{self.tag} in #{self.group}"
        else:
            name = self.tag
        return f"{name} (line {self.line})"


@dataclass
class InkFinding:
    cls: str
    a: InkElement
    b: InkElement
    box: tuple[float, float, float, float]  # x0, y0, x1, y1 in SVG units
    gap: float | None = None  # clearance findings only

    @property
    def hard(self) -> bool:
        return self.cls != "clearance"

    def message(self) -> str:
        x0, y0, x1, y1 = self.box
        pair = f"{self.a.describe()} × {self.b.describe()}"
        if self.cls == "clearance":
            what = "touches" if self.gap == 0 else f"{self.gap:.1f} px apart"
            return f"clearance: {pair} {what} at x {x0:.0f}, y {y0:.0f}"
        return f"{self.cls}: {pair} at x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f}"


@dataclass
class InkResult:
    findings: list[InkFinding]
    elements: list[InkElement]
    viewbox: tuple[float, float, float, float]
    render: Image.Image  # the whole graphic, for the overlay
    pairs: int  # candidate pairs the collision tree returned


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

_session: dict = {}


def _page():
    """A fresh page on one browser shared by every call in the process."""
    if "browser" not in _session:
        from playwright.sync_api import sync_playwright

        _session["pw"] = sync_playwright().start()
        _session["browser"] = _session["pw"].chromium.launch(headless=True)
        atexit.register(_close)
    return _session["browser"].new_page(device_scale_factor=SCALE)


def _close() -> None:
    if "browser" in _session:
        _session.pop("browser").close()
        _session.pop("pw").stop()


def _source_lines(svg_path: Path) -> list[int]:
    """Start-tag line of every element in document order; index 0 is the root."""
    lines: list[int] = []
    parser = xml.parsers.expat.ParserCreate()
    parser.StartElementHandler = lambda *_: lines.append(parser.CurrentLineNumber)
    parser.Parse(svg_path.read_bytes(), True)
    return lines


def _backdrop(d: dict, vb) -> bool:
    """Background layer or a full-canvas plate: under everything by design, never a party."""
    x0, y0, x1, y1 = d["box"]
    return d["layer"] == "background" or (x0 <= 0 and y0 <= 0 and x1 >= vb[2] and y1 >= vb[3])


# ---------------------------------------------------------------------------
# Collision tree
# ---------------------------------------------------------------------------


def candidate_pairs(elements: list[InkElement], clearance: float) -> list[tuple[int, int]]:
    """Index pairs whose boxes lie within ``clearance`` of each other."""
    if len(elements) < 2:
        return []
    boxes = [box(*e.box) for e in elements]
    left, right = STRtree(boxes).query(boxes, predicate="dwithin", distance=clearance)
    return sorted({(int(i), int(j)) for i, j in zip(left, right) if i < j})


def _batches(elements: list[InkElement], picks: list[int]) -> list[list[int]]:
    """Split ``picks`` into groups whose boxes never intersect, so each group is one render."""
    boxes = [box(*elements[k].box) for k in picks]
    left, right = STRtree(boxes).query(boxes, predicate="intersects")
    clash: dict[int, set[int]] = {}
    for i, j in zip(left, right):
        if i != j:
            clash.setdefault(int(i), set()).add(int(j))
    colour: dict[int, int] = {}
    for i in range(len(picks)):
        taken = {colour[n] for n in clash.get(i, ()) if n in colour}
        colour[i] = next(c for c in range(len(picks) + 1) if c not in taken)
    groups: dict[int, list[int]] = {}
    for i, c in colour.items():
        groups.setdefault(c, []).append(picks[i])
    return list(groups.values())


# ---------------------------------------------------------------------------
# Pixel tests
# ---------------------------------------------------------------------------


def _crop(e: InkElement, mask: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    """``mask`` of ``e`` placed in the device-pixel window [x0, x1) x [y0, y1)."""
    out = np.zeros((y1 - y0, x1 - x0), bool)
    ox, oy = e.origin
    h, w = mask.shape
    sx0, sy0, sx1, sy1 = max(x0, ox), max(y0, oy), min(x1, ox + w), min(y1, oy + h)
    if sx0 < sx1 and sy0 < sy1:
        out[sy0 - y0 : sy1 - y0, sx0 - x0 : sx1 - x0] = mask[
            sy0 - oy : sy1 - oy, sx0 - ox : sx1 - ox
        ]
    return out


def _window(a: InkElement, ma, b: InkElement, mb, grow: int = 0):
    ax, ay = a.origin
    bx, by = b.origin
    x0, y0 = max(ax, bx) - grow, max(ay, by) - grow
    x1 = min(ax + ma.shape[1], bx + mb.shape[1]) + grow
    y1 = min(ay + ma.shape[0], by + mb.shape[0]) + grow
    return (x0, y0, x1, y1) if x0 < x1 and y0 < y1 else None


def overlap(a: InkElement, ma, b: InkElement, mb):
    """Shared pixels of mask ``ma`` of ``a`` and ``mb`` of ``b``.

    Returns ``(box, share_a, share_b)`` with the box in device pixels, or None.
    """
    if ma is None or mb is None:
        return None
    w = _window(a, ma, b, mb)
    if w is None:
        return None
    both = _crop(a, ma, *w) & _crop(b, mb, *w)
    if not both.any():
        return None
    ys, xs = np.nonzero(both)
    n = int(both.sum())
    x0, y0 = w[0], w[1]
    return (
        (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1),
        n / int(ma.sum()),
        n / int(mb.sum()),
    )


def gap(a: InkElement, ma, b: InkElement, mb, limit: float):
    """Empty device pixels between the masks, when fewer than ``limit``.

    Returns ``(pixels, (x, y))`` with the closest point of ``ma``, or None.
    """
    if ma is None or mb is None:
        return None
    w = _window(a, ma, b, mb, grow=math.ceil(limit) + 2)
    if w is None:
        return None
    ca, cb = _crop(a, ma, *w), _crop(b, mb, *w)
    if not ca.any() or not cb.any():
        return None
    dist = distance_transform_edt(~cb)
    d = dist[ca].min()
    if d - 1 >= limit:
        return None
    ys, xs = np.nonzero(ca & (dist == d))
    return max(0.0, d - 1), (w[0] + xs[0], w[1] + ys[0])


def _spill(small: InkElement, big: InkElement) -> float:
    """Thickness, in SVG units, of the part of ``small``'s region outside ``big``'s."""
    h, w = small.fill.shape
    ox, oy = small.origin
    out = small.fill & ~_crop(big, big.fill, ox, oy, ox + w, oy + h)
    return 2 * float(distance_transform_edt(out).max()) / SCALE


def _entry(sh: InkElement, x: float, y: float, ux: float, uy: float) -> int | None:
    """First half-unit step along the ray from (x, y) that lands in ``sh``'s region."""
    ox, oy = sh.origin
    h, w = sh.fill.shape
    for step in range(2 * REACH + 1):
        px = int((x + ux * step / 2) * SCALE) - ox
        py = int((y + uy * step / 2) * SCALE) - oy
        if 0 <= px < w and 0 <= py < h and sh.fill[py, px]:
            return step
    return None


def _mark_targets(elements: list[InkElement], pairs: list[tuple[int, int]]) -> None:
    """Record, per line end, the first shape the end points into."""
    near: dict[int, list[InkElement]] = {}
    for i, j in pairs:
        for ln, sh in ((elements[i], elements[j]), (elements[j], elements[i])):
            if ln.kind == "line" and sh.kind == "shape" and sh.fill is not None:
                near.setdefault(ln.index, []).append(sh)
    for ln in elements:
        for x, y, dx, dy in ln.ends:
            n = math.hypot(dx, dy) or 1.0
            hits = [(_entry(sh, x, y, dx / n, dy / n), sh) for sh in near.get(ln.index, [])]
            hits = [(step, sh) for step, sh in hits if step is not None]
            if hits:
                first = min(step for step, _ in hits)
                ln.targets |= {sh.index for step, sh in hits if step == first}


def _one_drawing(a: InkElement, b: InkElement) -> bool:
    """Both parts of the same icon-sized group."""
    return a.drawing >= 0 and a.drawing == b.drawing


def judge(a: InkElement, b: InkElement, clearance: float, to_units) -> InkFinding | None:
    """The finding for one candidate pair, or None."""
    limit = clearance * SCALE

    def hit(cls, first, second, found):
        return InkFinding(cls, first, second, to_units(found[0]))

    def near(first, m1, second, m2):
        g = gap(first, m1, second, m2, limit)
        if g is None:
            return None
        (x, y) = g[1]
        return InkFinding("clearance", first, second, to_units((x, y, x + 1, y + 1)), g[0] / SCALE)

    kinds = {a.kind, b.kind}
    if kinds == {"text"}:
        found = overlap(a, a.fill, b, b.fill)
        return hit("text-on-text", a, b, found) if found else near(a, a.fill, b, b.fill)
    if kinds == {"text", "line"}:
        t, ln = (a, b) if a.kind == "text" else (b, a)
        found = overlap(t, t.fill, ln, ln.ink)
        return hit("edge-crosses-text", ln, t, found) if found else near(t, t.fill, ln, ln.ink)
    if kinds == {"text", "shape"}:
        t, s = (a, b) if a.kind == "text" else (b, a)
        found = overlap(t, t.fill, s, s.stroke)
        if found:
            return hit("edge-crosses-text", s, t, found)
        found = overlap(t, t.fill, s, s.fill)
        if found and found[1] < CONTAIN:
            return hit("text-straddles-shape", s, t, found)
        return near(t, t.fill, s, s.edge)
    if a.tint or b.tint or _one_drawing(a, b):
        return None
    if kinds == {"shape"}:
        found = overlap(a, a.fill, b, b.fill)
        if not found or max(found[1], found[2]) >= CONTAIN:
            return None
        x0, y0, x1, y1 = found[0]
        if min(x1 - x0, y1 - y0) < TOUCH * SCALE:
            return None  # touching, not overlapping
        small, big, share = (a, b, found[1]) if found[1] >= found[2] else (b, a, found[2])
        if share >= 0.9 and _spill(small, big) <= SPILL:
            return None  # nested, with a thin spill past a rounded corner
        return hit("shapes-partly-overlap", a, b, found)
    if kinds == {"line", "shape"}:
        ln, s = (a, b) if a.kind == "line" else (b, a)
        if not ln.arrow or s.index in ln.targets:
            return None  # plain lines through shapes: axes, gridlines, the connector checks
        found = overlap(ln, ln.ink, s, s.ink)
        if found:
            return InkFinding("clearance", ln, s, to_units(found[0]), 0.0)
        return near(ln, ln.ink, s, s.edge)
    return None  # line with line: the collide check


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def inspect(svg_path: str | Path, clearance: float = CLEARANCE) -> InkResult:
    """Draw ``svg_path`` and judge every candidate pair the collision tree returns."""
    svg_path = Path(svg_path)
    lines = _source_lines(svg_path)
    page = _page()
    try:
        page.goto(svg_path.resolve().as_uri())
        data = page.evaluate(_ENUMERATE, [24, 0.2, *ICON])
        vb = tuple(data["vb"])
        width, height = math.ceil(vb[2]), math.ceil(vb[3])
        page.set_viewport_size({"width": width, "height": height})
        render = Image.open(BytesIO(page.screenshot(omit_background=True))).convert("RGBA")
        elements = [
            InkElement(
                index=d["index"],
                line=lines[d["index"] + 1],
                tag=d["tag"],
                id=d["id"],
                group=d["group"],
                layer=d["layer"],
                text=d["text"],
                box=tuple(d["box"]),
                has_stroke=d["stroke"],
                closed=d["closed"],
                arrow=d["arrow"],
                tint=d["tint"],
                ends=[tuple(e) for e in d["ends"]],
                drawing=d["drawing"],
            )
            for d in data["elements"]
            if not _backdrop(d, vb)
        ]
        pairs = candidate_pairs(elements, clearance)
        page.evaluate(_ADD_STYLE, _MASK_CSS)
        drawn = sorted({i for pair in pairs for i in pair})
        for e in (elements[k] for k in drawn):
            # snapped to whole device pixels so every mask shares one pixel grid
            x0, y0 = (math.floor(max(0.0, c) * SCALE) for c in e.box[:2])
            e.origin = (x0, y0)
        by_index = {e.index: e for e in elements}
        for paint in ("all", "region", "stroke"):
            picks = [k for k in drawn if any(p == paint for p, _ in elements[k].passes)]
            for batch in _batches(elements, picks) if picks else []:
                page.evaluate(_SOLO, [[elements[k].index for k in batch], paint])
                shot = np.asarray(Image.open(BytesIO(page.screenshot(omit_background=True))))
                alpha = shot[:, :, 3] >= ALPHA
                for k in batch:
                    e = elements[k]
                    x0, y0 = e.origin
                    x1 = math.ceil(min(width, e.box[2]) * SCALE)
                    y1 = math.ceil(min(height, e.box[3]) * SCALE)
                    if x1 <= x0 or y1 <= y0:
                        continue
                    ink = alpha[y0:y1, x0:x1]
                    slot = dict(e.passes)[paint]
                    setattr(by_index[e.index], slot, ink.copy() if ink.any() else None)
        page.evaluate(_SOLO, [[], ""])
    finally:
        page.close()

    def to_units(b):
        x0, y0, x1, y1 = b
        return (x0 / SCALE + vb[0], y0 / SCALE + vb[1], x1 / SCALE + vb[0], y1 / SCALE + vb[1])

    _mark_targets(elements, pairs)
    findings = []
    for i, j in pairs:
        f = judge(elements[i], elements[j], clearance, to_units)
        if f:
            findings.append(f)
    findings.sort(key=lambda f: (not f.hard, f.box[1], f.box[0]))
    return InkResult(findings, elements, vb, render, len(pairs))


def write_overlay(result: InkResult, out_path: str | Path) -> Path:
    """The graphic on white with a numbered box on each finding: HARD magenta, SOFT orange."""
    img = Image.new("RGBA", result.render.size, (255, 255, 255, 255))
    img.alpha_composite(result.render)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=11 * SCALE)
    vx, vy = result.viewbox[0], result.viewbox[1]
    for n, f in enumerate(result.findings, 1):
        colour = (230, 0, 170, 255) if f.hard else (240, 140, 0, 255)
        x0, y0, x1, y1 = ((c - o) * SCALE for c, o in zip(f.box, (vx, vy, vx, vy)))
        draw.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], outline=colour, width=SCALE + 1)
        draw.text((x1 + 6, y0 - 6 - 11 * SCALE), str(n), fill=colour, font=font)
    out_path = Path(out_path)
    img.convert("RGB").save(out_path)
    return out_path
