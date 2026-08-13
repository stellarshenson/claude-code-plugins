"""Visual-geometry checks over element bbox data.

Pure functions over the JSON produced by ``render_inspect`` (static
parse, transforms applied, heuristic text extents). Each check targets a
failure-mode class that shipped past the structural validators in
production and was only caught by a human eyeballing a render:

- ``check_text_collisions``  - text vs icon / accent-bar overlap (real glyph widths)
- ``check_corner_padding``   - icon/badge/digit corner padding asymmetric or
                               inconsistent across sibling cards
- ``check_label_centering``  - middle-anchored label not centred in its container
- ``check_canvas_balance``   - dead canvas band on one side / lopsided margins
- ``check_slot_parity``      - card in a grid missing a slot its siblings have
- ``check_cross_file_consistency`` - sibling SVGs in a deck with diverging
                               card anatomy (icons present in one file, absent
                               in another; mixed rect/path card bodies)

No browser needed here - testable on synthetic bbox JSON.

CLI (cross-file deck check):
    svg-infographics consistency --svg a.svg --svg b.svg
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------


def _idents(el: dict) -> str:
    return " ".join([el.get("id") or "", el.get("parent") or "", *el.get("classes", [])]).lower()


def _has_role(el: dict, *needles: str) -> bool:
    ident = _idents(el)
    return any(n in ident for n in needles)


def _bbox(el: dict) -> tuple[float, float, float, float]:
    x, y, w, h = el["bbox"]
    return x, y, w, h


def _intersect(a: dict, b: dict, pad: float = 0.0) -> bool:
    ax, ay, aw, ah = _bbox(a)
    bx, by, bw, bh = _bbox(b)
    return not (
        ax + aw + pad <= bx or bx + bw + pad <= ax or ay + ah + pad <= by or by + bh + pad <= ay
    )


def _contains(outer: dict, inner: dict, tol: float = 1.0) -> bool:
    ox, oy, ow, oh = _bbox(outer)
    ix, iy, iw, ih = _bbox(inner)
    return (
        ix >= ox - tol and iy >= oy - tol and ix + iw <= ox + ow + tol and iy + ih <= oy + oh + tol
    )


def _is_background(el: dict, view_box: list[float]) -> bool:
    if _has_role(el, "background", "backplate", "bg-"):
        return True
    _, _, vw, vh = view_box
    _, _, w, h = _bbox(el)
    return vw > 0 and vh > 0 and w >= 0.95 * vw and h >= 0.95 * vh


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_text_collisions(data: dict, pad: float = 1.0) -> list[str]:
    """Text vs icon-group / accent-bar overlap using rendered extents."""
    findings = []
    texts = [el for el in data["elements"] if el["tag"] == "text"]
    icons = [el for el in data["elements"] if el["tag"] == "g" and _has_role(el, "icon")]
    accents = [el for el in data["elements"] if el["tag"] == "rect" and _has_role(el, "accent")]
    for t in texts:
        t_ident = _idents(t)
        for icon in icons:
            # text inside its own icon group is icon artwork, not a collision
            if icon.get("id") and icon["id"] == t.get("parent"):
                continue
            if _intersect(t, icon, pad=pad):
                findings.append(
                    f'[visual] text "{(t.get("text") or "")[:40]}" collides with '
                    f"icon {icon.get('id') or icon.get('classes')}"
                )
        for bar in accents:
            if "accent" in t_ident:
                continue
            if _intersect(t, bar, pad=pad):
                findings.append(
                    f'[visual] text "{(t.get("text") or "")[:40]}" collides with '
                    f"accent bar {bar.get('id') or bar.get('classes')}"
                )
    return findings


def _corner_distances(card: dict, el: dict) -> tuple[float, float] | None:
    """(dx, dy) to the corner the element hugs, or None if not corner-placed."""
    cx, cy, cw, ch = _bbox(card)
    ex, ey, ew, eh = _bbox(el)
    dx = min(ex - cx, (cx + cw) - (ex + ew))
    dy = min(ey - cy, (cy + ch) - (ey + eh))
    # Corner-placed = close to one horizontal AND one vertical edge.
    if dx < 0 or dy < 0 or dx > 25 or dy > 25:
        return None
    return dx, dy


def check_corner_padding(data: dict, tol: float = 2.0) -> list[str]:
    """Corner elements (icon/badge/digit) must sit equidistant from their two
    nearest card edges, and consistently so across sibling cards."""
    findings = []
    cards = [
        el for el in data["elements"] if el["tag"] in ("rect", "path") and _has_role(el, "card")
    ]

    def _own_role(el: dict) -> bool:
        # Match on the element's OWN id/classes only - children of an icon
        # group inherit the role via parent and would double-count.
        own = " ".join([el.get("id") or "", *el.get("classes", [])]).lower()
        return any(n in own for n in ("icon", "badge", "digit"))

    corner_els = [el for el in data["elements"] if _own_role(el) and el["tag"] != "text"]
    per_role_pads: dict[str, list[tuple[str, float]]] = {}
    for el in corner_els:
        host = next((c for c in cards if _contains(c, el, tol=2.0)), None)
        if host is None:
            continue
        dists = _corner_distances(host, el)
        if dists is None:
            continue
        dx, dy = dists
        label = el.get("id") or el.get("parent") or "/".join(el.get("classes", []))
        if abs(dx - dy) > tol:
            findings.append(
                f"[visual] {label}: uneven corner padding in "
                f"{host.get('id') or 'card'} ({dx:.1f}px vs {dy:.1f}px)"
            )
        role = (
            "icon" if _has_role(el, "icon") else ("badge" if _has_role(el, "badge") else "digit")
        )
        per_role_pads.setdefault(role, []).append((label, (dx + dy) / 2))
    for role, pads in per_role_pads.items():
        if len(pads) < 2:
            continue
        values = [p for _, p in pads]
        if max(values) - min(values) > tol:
            detail = ", ".join(f"{lbl}={v:.1f}px" for lbl, v in pads)
            findings.append(f"[visual] {role} corner padding inconsistent across cards: {detail}")
    return findings


def check_label_centering(data: dict, tol: float = 2.0) -> list[str]:
    """A middle-anchored text inside a container must be horizontally centred."""
    findings = []
    containers = [
        el
        for el in data["elements"]
        if el["tag"] in ("rect", "path") and not _is_background(el, data["viewBox"])
    ]
    for t in (el for el in data["elements"] if el["tag"] == "text"):
        if t.get("anchor") != "middle":
            continue
        hosts = [c for c in containers if _contains(c, t, tol=1.0)]
        if not hosts:
            continue
        host = min(hosts, key=lambda c: c["bbox"][2] * c["bbox"][3])
        hx, _, hw, _ = _bbox(host)
        tx, _, tw, _ = _bbox(t)
        off = abs((tx + tw / 2) - (hx + hw / 2))
        if off > tol:
            findings.append(
                f'[visual] label "{(t.get("text") or "")[:40]}" off-centre by '
                f"{off:.1f}px in {host.get('id') or 'container'}"
            )
    return findings


def check_canvas_balance(data: dict, dead_frac: float = 0.10, ratio: float = 2.5) -> list[str]:
    """Flag one-sided dead canvas: a margin band that is both > dead_frac of
    the canvas and > ratio x the opposite margin."""
    vx, vy, vw, vh = data["viewBox"]
    content = [el for el in data["elements"] if not _is_background(el, data["viewBox"])]
    if not content or vw <= 0 or vh <= 0:
        return []
    x1 = min(el["bbox"][0] for el in content)
    y1 = min(el["bbox"][1] for el in content)
    x2 = max(el["bbox"][0] + el["bbox"][2] for el in content)
    y2 = max(el["bbox"][1] + el["bbox"][3] for el in content)
    margins = {
        "left": x1 - vx,
        "right": (vx + vw) - x2,
        "top": y1 - vy,
        "bottom": (vy + vh) - y2,
    }
    findings = []
    for side, opposite, extent in (
        ("left", "right", vw),
        ("right", "left", vw),
        ("top", "bottom", vh),
        ("bottom", "top", vh),
    ):
        m, om = margins[side], margins[opposite]
        if m > dead_frac * extent and m > ratio * max(om, 1.0):
            findings.append(
                f"[visual] {m:.0f}px dead canvas on the {side} "
                f"({opposite} margin {om:.0f}px) - rebalance the layout"
            )
    return findings


def check_slot_parity(data: dict, min_cards: int = 3) -> list[str]:
    """Cards in a grid must carry the same slot types: a class present in
    most sibling cards but missing from one is a parity break."""
    cards = [
        el for el in data["elements"] if el["tag"] in ("rect", "path") and _has_role(el, "card")
    ]
    # Group cards of near-identical size (a grid).
    groups: list[list[dict]] = []
    for card in cards:
        _, _, w, h = _bbox(card)
        for g in groups:
            _, _, gw, gh = _bbox(g[0])
            if abs(w - gw) <= 5 and abs(h - gh) <= 5:
                g.append(card)
                break
        else:
            groups.append([card])
    findings = []
    for group in groups:
        if len(group) < min_cards:
            continue
        slots_per_card: list[set[str]] = []
        for card in group:
            slots = set()
            for el in data["elements"]:
                if el is card or not _contains(card, el, tol=2.0):
                    continue
                for cls in el.get("classes", []):
                    slots.add(cls)
                if el["tag"] == "g" and _has_role(el, "icon"):
                    slots.add("icon")
            slots_per_card.append(slots)
        n = len(group)
        common = {s for slots in slots_per_card for s in slots}
        for slot in sorted(common):
            holders = sum(1 for slots in slots_per_card if slot in slots)
            if holders >= max(2, n - 1) and holders < n:
                missing = [
                    group[i].get("id") or f"card#{i}"
                    for i, slots in enumerate(slots_per_card)
                    if slot not in slots
                ]
                findings.append(
                    f"[visual] slot parity: {holders}/{n} cards carry '{slot}' - "
                    f"missing in {', '.join(missing)}"
                )
    return findings


def check_visual(data: dict) -> tuple[list[str], list[str]]:
    """Run all single-file visual checks.

    Returns ``(hard, soft)``. Collisions and corner padding are HARD when
    the data came from the real renderer; with the static fallback every
    finding degrades to SOFT (heuristic text widths cannot prove a
    collision).
    """
    hard = check_text_collisions(data) + check_corner_padding(data)
    soft = check_label_centering(data) + check_canvas_balance(data) + check_slot_parity(data)
    if data.get("backend") != "chromium":
        soft = hard + soft
        hard = []
    return hard, soft


# ---------------------------------------------------------------------------
# Cross-file consistency (deck check)
# ---------------------------------------------------------------------------


def _card_body_styles(svg_path: Path) -> set[str]:
    """How card bodies are drawn in a file: rect-with-rx vs path."""
    styles = set()
    try:
        root = ET.fromstring(Path(svg_path).read_text(encoding="utf-8"))
    except ET.ParseError:
        return styles
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        ident = f"{el.get('id', '')} {el.get('class', '')}".lower()
        if "card" not in ident:
            continue
        if tag == "rect":
            styles.add("rect-rx" if el.get("rx") not in (None, "0") else "rect")
        elif tag == "path":
            styles.add("path")
    return styles


def consistency_subjects(datas: list[dict]) -> int:
    """How many files ``check_cross_file_consistency`` can actually compare.

    It returns no findings in two very different states: the deck agrees, and
    neither of its two comparisons had a subject because no file holds an
    element it reads as a card. Without this count the caller cannot tell them
    apart, and the roster announced a 7-file deck mutually consistent on zero
    cards and zero body styles.
    """
    n = 0
    for d in datas:
        cards = any(
            el["tag"] in ("rect", "path") and _has_role(el, "card") for el in d["elements"]
        )
        if cards or _card_body_styles(Path(d["file"])):
            n += 1
    return n


def check_cross_file_consistency(datas: list[dict]) -> list[str]:
    """Sibling SVGs in one deck must share card anatomy: icon presence and
    card body construction must not diverge between files."""
    findings = []
    if len(datas) < 2:
        return findings

    def card_icon_share(data: dict) -> float | None:
        cards = [
            el
            for el in data["elements"]
            if el["tag"] in ("rect", "path") and _has_role(el, "card")
        ]
        if not cards:
            return None
        icons = [el for el in data["elements"] if el["tag"] == "g" and _has_role(el, "icon")]
        with_icon = sum(1 for c in cards if any(_contains(c, i, tol=2.0) for i in icons))
        return with_icon / len(cards)

    shares = {Path(d["file"]).name: card_icon_share(d) for d in datas}
    present = {k: v for k, v in shares.items() if v is not None}
    if present:
        haves = [k for k, v in present.items() if v >= 0.5]
        havenots = [k for k, v in present.items() if v < 0.5]
        if haves and havenots:
            findings.append(
                f"[consistency] card icons present in {', '.join(haves)} but "
                f"missing in {', '.join(havenots)} - same deck, same anatomy"
            )

    styles = {Path(d["file"]).name: _card_body_styles(Path(d["file"])) for d in datas}
    styles = {k: v for k, v in styles.items() if v}
    all_styles = set().union(*styles.values()) if styles else set()
    if len(all_styles) > 1:
        detail = "; ".join(f"{k}: {', '.join(sorted(v))}" for k, v in sorted(styles.items()))
        findings.append(
            f"[consistency] mixed card body construction across the deck ({detail}) - "
            "house style is one card primitive per deck"
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics consistency",
        description=(
            "Cross-file deck check: compares card anatomy (icons, slots, "
            "card primitives) across sibling SVGs and reports divergence."
        ),
    )
    parser.add_argument("--svg", action="append", required=True, help="SVG file (repeatable)")
    args = parser.parse_args(argv)
    paths = [Path(p) for p in args.svg]
    for p in paths:
        if not p.is_file():
            print(f"ERROR: svg not found: {p}", file=sys.stderr)
            return 2
    if len(paths) < 2:
        print("consistency: need at least two --svg files to compare", file=sys.stderr)
        return 2

    from stellars_claude_code_plugins.svg_tools.render_inspect import extract_bboxes

    datas = list(extract_bboxes(paths).values())
    findings = check_cross_file_consistency(datas)
    if not findings:
        print(f"consistency: {len(paths)} files - OK, no anatomy divergence")
        return 0
    for f in findings:
        print(f)
    return 1


if __name__ == "__main__":
    sys.exit(main())
