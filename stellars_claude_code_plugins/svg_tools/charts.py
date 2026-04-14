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
        raise ValueError(
            f"unknown chart_type {chart_type!r}; choose one of {sorted(mapping)}"
        )
    return mapping[chart_type]


def _dark_mode_override_style(fg_light, fg_dark, grid_light, grid_dark, bg_dark):
    """Generate an inline <style> block that swaps pygal's colour choices via
    the `prefers-color-scheme: dark` media query.

    Pygal exposes hooks via `.axis line`, `.axis path`, `.axis text`, `.title`,
    `.legends text`, `.tick`, and the generic `.graph` element. Each selector
    gets a dark-mode override. `!important` is used because pygal emits
    inline fill/stroke attributes on some elements that would otherwise win.
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
}}
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

    Returns the SVG as bytes suitable for writing to a .svg file.
    """
    colors = colors or list(_DEFAULT_COLORS)
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
    if (
        isinstance(data[0], tuple)
        and len(data[0]) == 2
        and isinstance(data[0][1], (list, tuple))
    ):
        for name, values in data:
            chart.add(name, values)
    elif (
        isinstance(data[0], tuple)
        and len(data[0]) == 2
        and isinstance(data[0][0], str)
    ):
        for label, value in data:
            chart.add(label, value)
    else:
        chart.add(title or "series", data)

    svg_bytes = chart.render()
    # Inject dark-mode CSS overrides into pygal's existing style block
    svg_text = svg_bytes.decode("utf-8")
    dark_css = _dark_mode_override_style(fg_light, fg_dark, grid_light, grid_dark, bg_dark)
    svg_text = _inject_dark_mode_css(svg_text, dark_css)
    return svg_text.encode("utf-8")


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
        help="Comma-separated hex series colours, e.g. '#005f7a,#7a4a15,#0096d1'",
    )
    parser.add_argument("--fg-light", dest="fg_light", default=_DEFAULT_FG_LIGHT,
                        help="Foreground colour for light mode (hex)")
    parser.add_argument("--fg-dark", dest="fg_dark", default=_DEFAULT_FG_DARK,
                        help="Foreground colour for dark mode (hex)")
    parser.add_argument("--grid-light", dest="grid_light", default=_DEFAULT_GRID_LIGHT,
                        help="Grid/axis stroke colour for light mode (hex)")
    parser.add_argument("--grid-dark", dest="grid_dark", default=_DEFAULT_GRID_DARK,
                        help="Grid/axis stroke colour for dark mode (hex)")
    parser.add_argument("--bg-light", dest="bg_light", default="transparent",
                        help="Plot background for light mode (usually transparent)")
    parser.add_argument("--bg-dark", dest="bg_dark", default="transparent",
                        help="Plot background for dark mode (usually transparent)")

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

    if args.out:
        with open(args.out, "wb") as f:
            f.write(svg_bytes)
        print(f"wrote {args.out} ({len(svg_bytes)} bytes)", file=sys.stderr)
    else:
        sys.stdout.buffer.write(svg_bytes)


if __name__ == "__main__":
    main()
