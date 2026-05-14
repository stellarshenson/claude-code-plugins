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

## Standard document header patterns

Two canonical patterns. Both share the same skeleton: a **text column** on the left (title + subtitle stack + meta strap + version stamp), a **decorative motif column** on the right (max 20% of viewBox width per the rule above), and a **bottom-flush gradient accent bar** (10px tall, full width, opacity 0.6). Both ship with light + dark mode CSS via `@media (prefers-color-scheme: dark)`. Use them as starting points; do not hand-author a header from scratch.

### Pattern A — document section header (compact, 800×130)

For a section header sitting above a structured document body. Single brand colour pair (e.g. teal/orange). Decorative motif carries no information — abstract metaphor for the document's content (chronology bars + icon glyphs, layered slices, etc.).

Reference: [`examples/header-doc-banner-example.svg`](../../../examples/header-doc-banner-example.svg).

Anatomy:
- viewBox `0 0 800 130`, left/right margin 40px
- text column at `x=40`: title (20px bold, `.fg-1`, y=36) → subtitle (14px semi-bold, `.fg-2`, y=58) → meta1 (11px, `.fg-3`, y=80) → meta2 (10px, `.fg-4`, y=98)
- **version stamp** in meta2 alongside date range and reference: e.g. `Period: YYYY - YYYY  |  Reference: <id>  |  v<N>`
- decorative motif column at `x=640..760` (15% of width, well under the 20% cap)
- bottom accent gradient bar at `y=120, h=10`, `linearGradient` from primary colour (60% offset) to accent colour (100%), `opacity=0.6`

### Pattern B — cover banner (taller, 800×170, with glyph cluster)

For the cover of a whitepaper / proposal / report. Multi-stop **brand gradient bar** (rainbow) at the bottom, **decorative 2×2 glyph cluster** on the right with aura rings + circuit traces + cardinal accent dots. Allows two subtitle lines (primary value proposition + publisher / context) and a credits line with the version stamp.

Reference: [`examples/header-cover-banner-example.svg`](../../../examples/header-cover-banner-example.svg).

Anatomy:
- viewBox `0 0 800 170`, left/right margin 40px
- text column at `x=40`: title (28px bold, `.fg-1`, y=54) → subtitle (15px semi-bold, `.fg-2`, y=82) → subtitle-2 (12px, `.fg-3`, y=100) → credits (10px, `.credits`, y=140 — bottom-anchored)
- **version stamp** in the credits line: e.g. `Prepared by <author>  •  <topic>  •  <domain>  |  v<N>`
- glyph cluster centred at `(712.5, 68)`:
  - 4 Lucide icons (ISC license) on a 2×2 grid with 55px horizontal × 50px vertical pitch — centres `(685,43)`, `(740,43)`, `(685,93)`, `(740,93)` — each `transform="translate(...) scale(0.72)"`
  - two concentric aura rings (`r=46` dense dash, `r=56` sparse dash, `.aura-ring`)
  - diamond circuit-trace polyline visiting all 4 glyph centres through the cluster centre (dashed, 35% opacity)
  - small node dot (`r=1.4`) at each glyph centre + central hex hub (circumradius 4)
  - 4 cardinal accent dots at `r=56` from centre (`r=1.2`, brand-colour rotation)
- bottom rainbow gradient bar at `y=160, h=10`, 6 stops at offsets `0 / 0.18 / 0.37 / 0.58 / 0.79 / 1.0`, `opacity=0.6`

## Version stamp placement (MANDATORY when document is versioned)

If the underlying document carries a version (versioned report, iterating proposal, dated brief), the header MUST show it. Two placements, pick by pattern:

- **Pattern A**: rightmost cell of meta2, separated by ` | `. Format: `v<N>` or `v<MAJOR>.<MINOR>`. Lives in `.fg-4` (smallest text class).
- **Pattern B**: rightmost cell of the credits line, separated by ` | `. Same format.

Never hide the version in an XML comment or stuff it into the title — the version is reader-facing metadata, not authorship trivia. Skipping it on a v2+ document leaves the reader unable to tell which iteration they're looking at.

## Decorative-graphics rules of thumb (across both patterns)

- Carries no information — pure metaphor for the document's domain. Reader should be able to ignore it without losing meaning.
- Lives in its own `<g>` (`#decorative-motif` or `#cluster-accents` + 4 glyph `<g>` siblings).
- Sub-element opacity ≤ 0.85 (cluster icons), ≤ 0.45 (texture / bars beneath icons), ≤ 0.75 (aura rings). Layered transparency reads as decoration, not signal.
- Two colour rotation max: one primary brand colour + one accent. Multi-stop rainbow gradients live ONLY in the bottom accent bar, never in the motif itself.
- Glyph half-extent post-scale should fit comfortably inside the grid pitch (e.g. `~11px` glyph in 27.5px half-cell = safe). Tight glyphs read as clutter; aim for ~40-60% cell fill.
