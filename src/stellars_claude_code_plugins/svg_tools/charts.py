"""SVG chart generation backed by pygal.

Exposes the `charts` subcommand of the `svg-infographics` CLI. Pygal produces
the native SVG; this module wraps it in a theme-aware CSS layer so callers
can pass palette colours directly and get dark-mode-friendly output via the
`prefers-color-scheme` media query.

The caller is responsible for providing the palette - typically the LLM
extracts colours from the relevant `theme_swatch.svg` and passes them on the
command line. No hardcoded themes are baked into the tool.

Chart types:
    line        Line chart over x-axis series
    bar         Vertical bar chart (categorical x-axis)
    hbar        Horizontal bar chart
    area        Stacked area chart
    radar       Multi-axis radar / spider chart
    dot         Dot-matrix chart (score grid)
    histogram   Histogram (pygal Histogram with bins)
    pie         Pie chart (categorical parts of a whole)

Palette arguments (all optional; sensible neutral defaults):
    --colors      Comma-separated list of series colours (hex)
    --fg-light    Foreground colour for light mode (hex)
    --fg-dark     Foreground colour for dark mode (hex)
    --grid-light  Grid/axis stroke colour for light mode
    --grid-dark   Grid/axis stroke colour for dark mode
    --bg-light    Plot background for light mode (usually transparent)
    --bg-dark     Plot background for dark mode (usually transparent)

Example (stellars-tech palette sourced from theme_swatch_0_stellars-tech.svg):
    svg-infographics charts bar --data "[('Q1',42),('Q2',55)]" \\
      --colors "#005f7a,#7a4a15,#0096d1,#d4a04a" \\
      --fg-light "#1a5a6e" --fg-dark "#b8e4f0" \\
      --grid-light "#7fb5c5" --grid-dark "#3a6d7a"
"""

from __future__ import annotations

import argparse
import ast
import re
import sys

# Neutral fallback palette - used only when the caller provides no colours.
# Keeping this small and neutral avoids any implicit brand baggage.
_DEFAULT_COLORS = ["#0284c7", "#7c3aed", "#059669", "#dc2626", "#f59e0b", "#0891b2"]
_DEFAULT_FG_LIGHT = "#1e3a5f"
_DEFAULT_FG_DARK = "#b8d4e8"
_DEFAULT_GRID_LIGHT = "#8aa4b8"
_DEFAULT_GRID_DARK = "#3d5568"

# Reference backgrounds used for contrast audits. Medium, GitHub, and most
# article surfaces use a near-white background in light mode and a near-black
# one in dark mode. The audit falls back to these when the caller passes
# `transparent` (which has no meaningful contrast on its own).
_AUDIT_BG_LIGHT = "#ffffff"
_AUDIT_BG_DARK = "#0b0b0b"
# Chart series contrast target. WCAG 2.1 gives 3:1 for UI components and
# 7:1 for AAA text, but for READABLE chart lines and legend swatches we
# want the stricter end - 7:1 minimum, 10:1 ideal. The stellars-tech
# palette naturally lands in this range (7-10:1) against #ffffff / #0b0b0b.
_MIN_CONTRAST = 7.0
_IDEAL_CONTRAST = 10.0


def _hex_to_rgb(hex_str):
    """Parse '#rrggbb' or '#rgb' into a (r, g, b) tuple of 0..1 floats.

    Returns ``None`` for non-hex tokens like ``"transparent"`` or named
    colours so the contrast audit can skip them cleanly.
    """
    if not isinstance(hex_str, str) or not hex_str.startswith("#"):
        return None
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
    except ValueError:
        return None
    return (r, g, b)


def _relative_luminance(rgb):
    """Return WCAG 2.1 relative luminance for an sRGB (r, g, b) tuple."""

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast_ratio(fg_hex, bg_hex):
    """Return the WCAG 2.1 contrast ratio between two hex colours.

    Returns ``None`` if either colour is non-hex (e.g. ``"transparent"``) so
    the caller can skip the contrast check without raising.
    """
    fg = _hex_to_rgb(fg_hex)
    bg = _hex_to_rgb(bg_hex)
    if fg is None or bg is None:
        return None
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _audit_palette(colors, bg_hex, mode_label):
    """Return a list of warning strings for any colour with contrast < 7:1.

    Target range is 7:1 minimum, 10:1 ideal. Anything below 7 gets flagged
    with a hint about which direction to move. ``mode_label`` is
    ``'light'`` or ``'dark'`` and drives the hint direction: light mode
    wants DARKER shades, dark mode wants BRIGHTER ones.

    ``colors`` is the list of series hexes (``colors_dark`` for dark mode).
    ``bg_hex`` is the background being drawn against; ``transparent`` is
    resolved to the canonical article background so the check still bites.
    """
    if not colors:
        return []
    warnings = []
    if not isinstance(bg_hex, str) or not bg_hex.startswith("#"):
        bg_hex = _AUDIT_BG_LIGHT if mode_label == "light" else _AUDIT_BG_DARK
    for i, col in enumerate(colors):
        ratio = _contrast_ratio(col, bg_hex)
        if ratio is None:
            continue
        if ratio < _MIN_CONTRAST:
            hint = (
                "too pale - use a darker shade"
                if mode_label == "light"
                else "too dark - use a brighter shade"
            )
            warnings.append(
                f"[{mode_label}] color-{i} {col} vs bg {bg_hex}: contrast {ratio:.2f}:1 "
                f"(< {_MIN_CONTRAST:.0f}:1 target, {_IDEAL_CONTRAST:.0f}:1 ideal) - {hint}"
            )
    return warnings


def _make_pygal_style(fg_light, colors, background="transparent"):
    """Build a pygal Style using the light-mode colours. Dark-mode overrides
    are injected post-generation via a <style> block, so pygal itself only
    needs to know the light-mode foreground.
    """
    from pygal.style import Style

    return Style(
        background=background,
        plot_background=background,
        foreground=fg_light,
        foreground_strong=colors[0] if colors else fg_light,
        foreground_subtle=fg_light,
        opacity="1",
        opacity_hover="1",
        transition="0ms",
        colors=tuple(colors) if colors else tuple(_DEFAULT_COLORS),
        font_family="Segoe UI, Arial, sans-serif",
        label_font_size=10,
        major_label_font_size=10,
        value_font_size=9,
        title_font_size=14,
        legend_font_size=10,
    )


def _chart_class(chart_type):
    """Map chart_type to the pygal chart class."""
    import pygal

    mapping = {
        "line": pygal.Line,
        "bar": pygal.Bar,
        "hbar": pygal.HorizontalBar,
        "area": pygal.StackedLine,
        "radar": pygal.Radar,
        "dot": pygal.Dot,
        "histogram": pygal.Histogram,
        "pie": pygal.Pie,
    }
    if chart_type not in mapping:
        raise ValueError(f"unknown chart_type {chart_type!r}; choose one of {sorted(mapping)}")
    return mapping[chart_type]


def _dark_mode_override_style(fg_light, fg_dark, grid_light, grid_dark, bg_dark, colors_dark=None):
    """Generate an inline <style> block that swaps pygal's colour choices via
    the `prefers-color-scheme: dark` media query.

    When ``colors_dark`` is provided, per-series overrides are emitted for
    each ``.color-N`` class. The override is split by chart type to avoid
    clobbering the `.nofill` class on line/radar paths: line/radar/area/xy
    charts get STROKE-only overrides on paths (so the polygon interior stays
    transparent); pie charts get FILL on paths; bar/histogram charts get
    FILL on rects; markers and legend swatches get FILL.

    `!important` is used because pygal bakes the light-mode hexes directly
    into its inline `<style>` with high specificity.
    """
    series_css = ""
    if colors_dark:
        for i, color in enumerate(colors_dark):
            series_css += f"""
  /* series {i} */
  .line-graph .color-{i} path, .radar-graph .color-{i} path,
  .stackedline-graph .color-{i} path, .xy-graph .color-{i} path,
  .line-graph .color-{i} line, .radar-graph .color-{i} line {{
    stroke: {color} !important;
  }}
  .pie-graph .color-{i} path {{
    fill: {color} !important;
    stroke: {color} !important;
  }}
  .bar-graph .color-{i} rect, .histogram-graph .color-{i} rect,
  .horizontalbar-graph .color-{i} rect {{
    fill: {color} !important;
    stroke: {color} !important;
  }}
  .pygal-chart .color-{i} .dot,
  .pygal-chart .color-{i} circle.dot {{
    fill: {color} !important;
    stroke: {color} !important;
  }}
  .pygal-chart .legend .color-{i} rect,
  .pygal-chart .legend .color-{i} circle {{
    fill: {color} !important;
    stroke: {color} !important;
  }}
"""
    return f"""
@media (prefers-color-scheme: dark) {{
  .pygal-chart .axis line, .pygal-chart .axis path,
  .pygal-chart .axis .guide,
  .pygal-chart .guides line, .pygal-chart .guides path {{
    stroke: {grid_dark} !important;
  }}
  .pygal-chart .axis text, .pygal-chart .title,
  .pygal-chart .legends text, .pygal-chart text.no_data,
  .pygal-chart .tick, .pygal-chart .graph text {{
    fill: {fg_dark} !important;
  }}
  .pygal-chart .background, .pygal-chart .plot .background {{
    fill: {bg_dark} !important;
  }}
{series_css}}}
"""


def _inject_dark_mode_css(svg_text, dark_css):
    """Inject the dark-mode override <style> into the pygal SVG's <defs>."""

    # Pygal emits a <defs><style> block. Append to its style content.
    def _augment_style(m):
        return m.group(0) + dark_css

    # Match the first </style> tag inside <defs>
    new_text = re.sub(r"(</style>)", lambda m: dark_css + m.group(1), svg_text, count=1)
    return new_text


def generate_chart(
    chart_type,
    data,
    labels=None,
    title=None,
    colors=None,
    colors_dark=None,
    fg_light=_DEFAULT_FG_LIGHT,
    fg_dark=_DEFAULT_FG_DARK,
    grid_light=_DEFAULT_GRID_LIGHT,
    grid_dark=_DEFAULT_GRID_DARK,
    bg_light="transparent",
    bg_dark="transparent",
    x_title=None,
    y_title=None,
    show_legend=True,
    width=600,
    height=360,
):
    """Generate an SVG chart with dark-mode CSS overrides baked in.

    Palette arguments are explicit and required to come from the caller;
    no theme dict lives in the tool. When palette values are omitted, a
    neutral fallback palette is used.

    The function audits both palettes for readability: every series colour
    is measured against the matching background for WCAG 2.1 contrast, and
    any pair below 3:1 generates a warning. Warnings are ATTACHED to the
    returned bytes via a ``warnings`` attribute (list of strings) so the
    CLI and downstream callers can surface them. Chart rendering proceeds
    regardless - the audit is advisory, not blocking.

    Returns the SVG as bytes suitable for writing to a .svg file.
    """
    colors = colors or list(_DEFAULT_COLORS)
    if colors_dark is None:
        colors_dark = list(colors)

    # Contrast audit - warn but do not block.
    audit_warnings = []
    audit_warnings.extend(_audit_palette(colors, bg_light, "light"))
    audit_warnings.extend(_audit_palette(colors_dark, bg_dark, "dark"))

    ChartClass = _chart_class(chart_type)
    style = _make_pygal_style(fg_light, colors, background=bg_light)
    chart = ChartClass(
        style=style,
        width=width,
        height=height,
        show_legend=show_legend,
        title=title,
        x_title=x_title,
        y_title=y_title,
    )

    if labels is not None:
        chart.x_labels = labels

    if not data:
        raise ValueError("data must not be empty")
    if isinstance(data[0], tuple) and len(data[0]) == 2 and isinstance(data[0][1], (list, tuple)):
        for name, values in data:
            chart.add(name, values)
    elif isinstance(data[0], tuple) and len(data[0]) == 2 and isinstance(data[0][0], str):
        for label, value in data:
            chart.add(label, value)
    else:
        chart.add(title or "series", data)

    svg_bytes = chart.render()
    # Inject dark-mode CSS overrides into pygal's existing style block
    svg_text = svg_bytes.decode("utf-8")
    dark_css = _dark_mode_override_style(
        fg_light, fg_dark, grid_light, grid_dark, bg_dark, colors_dark
    )
    svg_text = _inject_dark_mode_css(svg_text, dark_css)

    # Attach audit metadata to the returned bytes so the CLI + callers can
    # surface the palette summary and contrast warnings. `bytes` is
    # immutable, so we return a subclass instance with extra attributes.
    class _ChartBytes(bytes):
        pass

    out = _ChartBytes(svg_text.encode("utf-8"))
    out.palette_light = list(colors)
    out.palette_dark = list(colors_dark)
    out.bg_light = bg_light
    out.bg_dark = bg_dark
    out.contrast_warnings = audit_warnings
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_literal(s):
    """Parse a Python-literal string with ast.literal_eval."""
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError) as exc:
        raise argparse.ArgumentTypeError(f"invalid Python literal: {exc}")


def _parse_color_list(s):
    """Parse a comma-separated list of hex colours."""
    return [c.strip() for c in s.split(",") if c.strip()]


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics charts",
        description="Render a themed SVG chart via pygal with dark-mode CSS overrides.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "chart_type",
        choices=["line", "bar", "hbar", "area", "radar", "dot", "histogram", "pie"],
        help="chart variant to render",
    )
    parser.add_argument(
        "--data",
        type=_parse_literal,
        required=True,
        help='Python-literal data: [1,2,3] or [("A",5),("B",8)] or [("Series",[1,2,3])]',
    )
    parser.add_argument(
        "--labels",
        type=_parse_literal,
        default=None,
        help='Python-literal list of x-axis labels: ["Q1","Q2","Q3","Q4"]',
    )
    parser.add_argument("--title", default=None, help="chart title")
    parser.add_argument("--x-title", dest="x_title", default=None, help="x-axis title")
    parser.add_argument("--y-title", dest="y_title", default=None, help="y-axis title")

    # Palette - provided by the caller, not the tool
    parser.add_argument(
        "--colors",
        type=_parse_color_list,
        default=None,
        help="Comma-separated hex series colours for LIGHT mode, e.g. '#005f7a,#7a4a15,#0096d1'",
    )
    parser.add_argument(
        "--colors-dark",
        dest="colors_dark",
        type=_parse_color_list,
        default=None,
        help="Comma-separated hex series colours for DARK mode. Must be brighter "
        "than --colors so plot lines and fills stay visible on dark backgrounds. "
        "Falls back to --colors when omitted. Length should match --colors.",
    )
    parser.add_argument(
        "--fg-light",
        dest="fg_light",
        default=_DEFAULT_FG_LIGHT,
        help="Foreground colour for light mode (hex)",
    )
    parser.add_argument(
        "--fg-dark",
        dest="fg_dark",
        default=_DEFAULT_FG_DARK,
        help="Foreground colour for dark mode (hex)",
    )
    parser.add_argument(
        "--grid-light",
        dest="grid_light",
        default=_DEFAULT_GRID_LIGHT,
        help="Grid/axis stroke colour for light mode (hex)",
    )
    parser.add_argument(
        "--grid-dark",
        dest="grid_dark",
        default=_DEFAULT_GRID_DARK,
        help="Grid/axis stroke colour for dark mode (hex)",
    )
    parser.add_argument(
        "--bg-light",
        dest="bg_light",
        default="transparent",
        help="Plot background for light mode (usually transparent)",
    )
    parser.add_argument(
        "--bg-dark",
        dest="bg_dark",
        default="transparent",
        help="Plot background for dark mode (usually transparent)",
    )

    parser.add_argument("--width", type=int, default=600, help="pixel width (default 600)")
    parser.add_argument("--height", type=int, default=360, help="pixel height (default 360)")
    parser.add_argument(
        "--no-legend", dest="show_legend", action="store_false", help="hide the legend"
    )
    parser.add_argument("--out", default=None, help="write SVG to this file (default stdout)")
    args = parser.parse_args()

    svg_bytes = generate_chart(
        chart_type=args.chart_type,
        data=args.data,
        labels=args.labels,
        title=args.title,
        colors=args.colors,
        colors_dark=args.colors_dark,
        fg_light=args.fg_light,
        fg_dark=args.fg_dark,
        grid_light=args.grid_light,
        grid_dark=args.grid_dark,
        bg_light=args.bg_light,
        bg_dark=args.bg_dark,
        x_title=args.x_title,
        y_title=args.y_title,
        show_legend=args.show_legend,
        width=args.width,
        height=args.height,
    )

    # Print palette summary + contrast audit to stderr so callers can see
    # exactly what colours are baked into the SVG and which (if any) fail
    # the 3:1 contrast target for their respective background.
    pal_light = getattr(svg_bytes, "palette_light", [])
    pal_dark = getattr(svg_bytes, "palette_dark", [])
    warnings = getattr(svg_bytes, "contrast_warnings", [])
    bg_l = getattr(svg_bytes, "bg_light", args.bg_light)
    bg_d = getattr(svg_bytes, "bg_dark", args.bg_dark)
    print(f"[charts] light palette ({len(pal_light)}): {', '.join(pal_light)}", file=sys.stderr)
    print(f"[charts] dark palette  ({len(pal_dark)}): {', '.join(pal_dark)}", file=sys.stderr)
    print(f"[charts] light bg: {bg_l}   dark bg: {bg_d}", file=sys.stderr)
    if warnings:
        print(
            f"[charts] CONTRAST WARNINGS ({len(warnings)}) - fix these before shipping:",
            file=sys.stderr,
        )
        for w in warnings:
            print(f"  ! {w}", file=sys.stderr)
    else:
        print(
            "[charts] contrast audit: all series >= 7:1 in both modes (target 7-10:1)",
            file=sys.stderr,
        )

    if args.out:
        with open(args.out, "wb") as f:
            f.write(svg_bytes)
        print(f"wrote {args.out} ({len(svg_bytes)} bytes)", file=sys.stderr)
    else:
        sys.stdout.buffer.write(svg_bytes)


if __name__ == "__main__":
    main()
