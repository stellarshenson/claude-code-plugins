"""Custom icon library: bundled, plugin-original icons + a catalogue.

The plugin ships its OWN small set of hand-tuned icons that are not in
Lucide or the draw.io stencil libraries. Each lives here as a 24-grid,
stroke-based ``<g>`` body so it pastes in next to Lucide icons with the
same scale + stroke convention (``fill="none" stroke=... stroke-width=2``).

This is ADDITIVE to the two big external sources:

- **Lucide** (1000+, ISC) - paste the path verbatim from lucide.dev, embed
  in ``<g transform="translate(x,y) scale(s)" fill="none" stroke=...>``.
- **draw.io stencils** (1000+) - ``svg-infographics shapes ...`` (downloaded
  on demand, cached).

The catalogue command lists THIS bundled set plus pointers to the two
external sources so an agent sees every icon route in one place.

CLI usage::

    svg-infographics icons list [--category CAT] [--caveman]
    svg-infographics icons search QUERY
    svg-infographics icons render NAME [--size 24] [--at X,Y] [--stroke HEX]
"""

from __future__ import annotations

import argparse
import sys

# ---------------------------------------------------------------------------
# Bundled icon library. Each entry:
#   category  - grouping slug
#   keywords  - search terms (name is always searchable too)
#   source    - provenance / licence note for the emitted comment
#   body      - 24-grid child markup, stroke-based (fill="none" on the group)
# Add new icons here; the catalogue + search + render pick them up for free.
# ---------------------------------------------------------------------------
ICON_LIBRARY: dict[str, dict] = {
    "brain-circuit": {
        "category": "ai",
        "keywords": [
            "brain",
            "circuit",
            "ai",
            "ml",
            "machine learning",
            "neural",
            "intelligence",
            "model",
            "cognition",
            "inference",
        ],
        "source": "stellars custom (original, ISC-compatible)",
        "body": (
            '<path d="M12 4c-4 0-5 2-5 4-2 .5-3 2-3 4s1 3.5 3 4c0 2 2 4 5 4"/>'
            '<line x1="12" y1="4" x2="12" y2="20"/>'
            '<path d="M12 8h4.4"/>'
            '<path d="M12 11.5h2.5"/>'
            '<path d="M12 15h3.9"/>'
            '<circle cx="18" cy="8" r="1.6"/>'
            '<circle cx="17.5" cy="15" r="1.6"/>'
        ),
    },
}

# Caveman-soft one-liners for `icons list --caveman`. Drop articles + copulas;
# keep the meaning. Mirror this whenever an icon lands in ICON_LIBRARY.
CAVEMAN_KEYWORDS: dict[str, str] = {
    "brain-circuit": "brain + circuit nodes. AI / ML / model",
}

_GRID = 24  # every bundled icon authored on a 0..24 box


def list_icons(category: str | None = None) -> list[str]:
    """Names in the bundled library, optionally filtered by category."""
    names = sorted(ICON_LIBRARY)
    if category:
        names = [n for n in names if ICON_LIBRARY[n]["category"] == category]
    return names


def search_icons(query: str) -> list[str]:
    """Names whose name or keywords contain ``query`` (case-insensitive)."""
    q = query.lower().strip()
    hits = []
    for name, meta in sorted(ICON_LIBRARY.items()):
        haystack = " ".join([name, *meta["keywords"]]).lower()
        if q in haystack:
            hits.append(name)
    return hits


def render_icon(
    name: str,
    size: float = 24.0,
    at: tuple[float, float] = (0.0, 0.0),
    stroke: str = "currentColor",
    stroke_width: float = 2.0,
) -> str:
    """Return a paste-ready ``<g>`` for ``name`` at ``size`` px, anchored at ``at``.

    Matches the Lucide embed convention used across the examples:
    ``fill="none" stroke=... stroke-width=2`` with round caps, scaled from the
    24-grid by ``size / 24``. Pass ``--stroke`` the theme stroke hex from your
    swatch (the examples bake a concrete hex, not a class, for stroke icons).
    """
    if name not in ICON_LIBRARY:
        raise KeyError(name)
    meta = ICON_LIBRARY[name]
    s = size / _GRID
    x, y = at
    return (
        f"<!-- Icon: {name} ({meta['source']}) -->\n"
        f'<g transform="translate({x:g}, {y:g}) scale({s:g})" '
        f'fill="none" stroke="{stroke}" stroke-width="{stroke_width:g}" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f"{meta['body']}</g>"
    )


def _print_catalogue(category: str | None = None, caveman: bool = False) -> None:
    names = list_icons(category)
    if caveman:
        print("custom icons (plugin-own). list + render via `icons`:")
        for name in names:
            print(f"  {name:<16} {CAVEMAN_KEYWORDS.get(name, '')}")
        print()
        print("more icons:")
        print("  lucide   1000+. paste path from lucide.dev. keep `d` verbatim")
        print("  drawio   1000+. `svg-infographics shapes ...`")
        return

    print("Custom icon library (bundled with the plugin)")
    print("Plugin-original icons - additive to Lucide + draw.io. Render a")
    print("paste-ready <g> with `svg-infographics icons render <name>`.")
    print()
    if not names:
        print("  (no icons in this category)")
    else:
        print(f"  {'NAME':<16} {'CATEGORY':<10} KEYWORDS")
        for name in names:
            meta = ICON_LIBRARY[name]
            kw = ", ".join(meta["keywords"][:5])
            print(f"  {name:<16} {meta['category']:<10} {kw}")
    print()
    print("Other icon sources (not bundled - pull on demand):")
    print("  Lucide  (ISC, 1000+)  paste the path verbatim from lucide.dev;")
    print("                        embed in <g ... fill=none stroke=...>. Keep")
    print("                        the path `d` data unchanged - size + colour")
    print("                        come from transform + stroke, never a rewrite.")
    print("  draw.io (1000+)       svg-infographics shapes search/render ...")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics icons",
        description=(
            "Bundled custom icon library + catalogue of every icon route "
            "(custom / Lucide / draw.io)."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_list = sub.add_parser("list", help="catalogue the bundled custom icons")
    p_list.add_argument("--category", help="filter by category slug (e.g. ai)")
    p_list.add_argument("--caveman", action="store_true", help="ultra-terse catalogue")

    p_search = sub.add_parser("search", help="search bundled icons by name/keyword")
    p_search.add_argument("query", help="search term")

    p_render = sub.add_parser("render", help="emit a paste-ready <g> for one icon")
    p_render.add_argument("name", help="icon name (see `icons list`)")
    p_render.add_argument(
        "--size", type=float, default=24.0, help="target size in px (default 24)"
    )
    p_render.add_argument("--at", default="0,0", help="top-left anchor 'x,y' (default 0,0)")
    p_render.add_argument(
        "--stroke",
        default="currentColor",
        help="stroke colour - pass the theme stroke hex from your swatch",
    )
    p_render.add_argument(
        "--stroke-width", type=float, default=2.0, help="stroke width (default 2)"
    )

    args = parser.parse_args()

    if args.action == "list":
        _print_catalogue(category=args.category, caveman=args.caveman)
        return 0

    if args.action == "search":
        hits = search_icons(args.query)
        if not hits:
            print(f"No bundled icon matches '{args.query}'.")
            print("Try Lucide (lucide.dev) or `svg-infographics shapes search`.")
            return 0
        for name in hits:
            kw = ", ".join(ICON_LIBRARY[name]["keywords"][:5])
            print(f"  {name:<16} {kw}")
        return 0

    if args.action == "render":
        try:
            x_str, y_str = args.at.split(",")
            at = (float(x_str), float(y_str))
        except ValueError:
            print(f"Bad --at '{args.at}', expected 'x,y'.", file=sys.stderr)
            return 1
        try:
            print(
                render_icon(
                    args.name,
                    size=args.size,
                    at=at,
                    stroke=args.stroke,
                    stroke_width=args.stroke_width,
                )
            )
        except KeyError:
            print(f"Unknown icon '{args.name}'.", file=sys.stderr)
            print("Run `svg-infographics icons list` for available names.", file=sys.stderr)
            return 1
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
