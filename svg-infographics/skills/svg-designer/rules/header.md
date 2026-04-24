**Header rule card** - rules when preflight declares `--headers N`.

Header = banner, title strip, cover row. Sits at the top of the SVG and introduces the content below. One header per SVG in 99% of cases; multi-header layouts are the exception and count each band separately.

## 20% rule (MANDATORY)

Decorative graphics in the header take AT MOST 20% of the viewBox's horizontal width. Title + subtitle + metadata get the remaining 80%+.

Why: the header's job is to tell the reader what this image is about. Oversized logos, embroidery, icon clusters steal the breathing room that the TITLE needs to land. Measured: every decorative element's bbox width / viewBox width <= 0.20.

Violations: floating logo the size of a quarter of the width, decorative embroidery eating 40% of the horizontal band, icon cluster that makes the title feel squeezed.

Remediation: shrink the decorative element, or move it to a corner where its footprint counts separately from the title zone.

## Typography discipline

- Title: 13-16pt bold, letter-spacing 0.4-0.8. Class `.fg-1`. One line only - if it wraps, the title is too long, not the header too narrow.
- Subtitle / tagline (optional): 10-12pt, italic or regular, class `.fg-2` or `.fg-3`. One line.
- Metadata strap (date, version, author; optional): 8-9pt, class `.fg-3`, right-aligned.

## Alignment

- Title text-anchor: `middle` when the header is symmetric, `start` with margin when left-aligned. Pick one per SVG - mixing across a set of images reads as chaos.
- Decorative element goes LEFT of title (corner badge) or RIGHT (trailing flourish). Never centre-behind the title - that's a busy-background anti-pattern.

## Z-order

Header `<g>` is the FIRST content group after `<g id="background">`. Title text sits ABOVE the decorative element if any z-order conflict arises.

## ID convention (MANDATORY for check)

Every header `<g>` MUST use one of:
- `id="header"` (canonical, single-header layouts)
- `id="header-<slug>"` (multi-header variants)
- `class` containing `"header"`

`check` counts headers by scanning for these; no convention = not counted = failed declaration.

## When to use a header vs a title text alone

If the SVG is showing ONE thing (metric card, single hero image), a plain `<text>` title at the top is sufficient - no header component declared. Reserve `--headers 1` for actual banner rows with decorative elements, tagline, metadata strap, or distinguishing background treatment.
