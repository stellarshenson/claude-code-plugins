# SVG Infographic Standards - Core

Universal essentials only. Detailed component rules live in `rules/*.md`, served per declared component flag by `svg-infographics preflight`. Full tool inventory: `tools.md`. The agent is the designer, CLI tools are the application - every coordinate from a tool call, every colour from a CSS class, every arrow from the connector tool.

## Key Principles

1. **Tool first** - every coordinate from `primitives`, every arrow from `connector`, every placement from `geom`/`callouts`/`empty-space`. Never eyeball
2. **Place via empty-space** - before placing inside a container, run `empty-space --edges-only --container-id <id>`. Text/strokes/outlines = obstacles, fills = not. Role-shared elements aligned via `geom align`
3. **Theme first** - approve `theme_swatch.svg` before deliverables
4. **Grid first** - viewBox, margins, columns, rhythm as comments BEFORE content
5. **Group everything** - every visual unit = a `<g>`. Topology comment declares relationships. No loose elements
6. **CSS classes** - `<style>` + `prefers-color-scheme`. `class=`, never inline `fill=`
7. **File description comment** before `<svg>`: filename, shows, intent, theme
8. **Five named layers** - `background`, `nodes`, `connectors`, `content`, `callouts`
9. **Transparent background** - `fill="transparent"` on root rect
10. **Contrast via theme** - no `#000000`, no `#ffffff`
11. **Validate before delivery** - all six checkers (`overlaps`, `contrast`, `alignment`, `connectors`, `css`, `collide`). No run, no ship
12. **Read examples** - study `examples/` before each image
13. **Unicode glyphs in text** - see table below. ASCII arrow in any `<text>` node = FAIL
14. **Connector tool for every arrow** - hand-coded `<path d="M...">` for any routed line = FAIL. Not even "just 10 pixels"
15. **Task tracking** - TaskCreate/TaskUpdate throughout; prevents skipped steps
16. **Text after visuals** - compute label coords from placed geometry via `geom midpoint`/`attach`/`perpendicular`, never eyeball

## CSS Theme Classes and Dark Mode

- Theme-aware text: `<text class="fg-2">`. Text on saturated accent fills uses `on-fill` (light mode: dark fg-1 text; dark mode: pale tint)
- Inline `fill="#hex"` allowed only for structural shape fills, fixed swatch elements, decorative low-opacity imagery. Validate with `svg-infographics css`
- **Never opacity on text** - fonts render at full opacity; contrast via colour. Applies to `opacity`, `fill-opacity` on `<text>`, and parent `<g>` inheritance
- Opacity ONLY for: card background tints (`fill-opacity 0.04-0.06`), track lines (`0.3`), decorative bg imagery (`0.10-0.35`). Never on data bars, progress bars, legend chips, text, logos
- Dark-mode limits: `prefers-color-scheme` works in standalone/`<object>`/inline SVG; fails via `<img>` or markdown `![alt](path)`. Design light-primary; assume `#1e1e1e` dark bg

## Contrast Rules

| Background | Foreground |
|---|---|
| Transparent (doc bg) | fg-1 or fg-2 |
| bg-1 (accent at 0.04-0.08) | fg-1 headings, fg-3/fg-4 labels |
| bg-2 (accent at 0.3-0.6) | fg-1 or fg-2 |
| Full accent fill (0.8-1.0) | fg-4 or fg-1 (whichever contrasts) |
| Accent swatch chip | fg-1 label below, not on top |

Forbidden: `#000000` (invisible on dark), `#ffffff` (invisible on light), pure greys below `#404040` or above `#c0c0c0`, anything not in approved theme. Background always transparent (exception: banner gradient bars that ARE the design element).

Safe neutral palette (no brand defined): dark text `#1e3a5f`, primary `#0284c7`, secondary `#7c3aed`, tertiary `#059669`, muted `#6b7280`, subtle fills = accent + `fill-opacity 0.06`.

## Grid-Based Layout

Build order: 1 grid + guide lines → 2 placeholder rects → 3 structure (card paths, tracks, accent bars, dividers) → 4 content → 5 styling → 6 validation.

- **Vertical rhythm**: single step size (14px typical), rows on multiples: title y=14, row1 y=34 (title+20), then +14 per row
- **Guide grid**: first element after `<style>` = `<g id="guide-grid" display="none">`, hierarchical bisection grid-1 (viewBox edges) through grid-6 (1/32 points)
- **Grid comment** (MANDATORY) before content:

```xml
<!-- === GRID REFERENCE ===
  Panel origins: left x=20, right x=410
  Vertical rhythm (14px): y=14 title, y=34 row1, y=48 row2
=== -->
```

- **Topology comment** (MANDATORY) - declares relationships, NOT coordinates. Ops: `h-stack`/`v-stack` (adjacent), `h-align` (share x), `v-align` (share y), `h-spacing`/`v-spacing` (equal gaps), `contain`, `mirror`

```xml
<!-- TOPOLOGY:
  h-stack: card-a, card-b, card-c (gap=20)
  v-align: card-a.top = card-b.top = card-c.top
  contain: card-a > icon-a, label-a
-->
```

- **Grouping** (MANDATORY): every visual unit (card, icon+label, section, legend, decorative cluster) = its own `<g>`. Build at origin, position by one `transform="translate(x,y)"`; children in local coords. Nesting max 3 levels: layer > section > card
- **Transforms**: `translate` for position, `scale` for icon sizing (`scale(0.667)` = 16px from 24px Lucide), `rotate` rare. `translate(...) scale(...)` - translate first (parent coords)
- **Position via tools**: `geom align --edge top`, `geom distribute --axis h --mode gap` - returned positions = translate values. Group bbox after transforms lives in root coords; pass world-space rects to `geom`
- **Multi-card grids**: width per row = `(viewBox_w - 2*margin - (n-1)*gap) / n`. Gap 12px (timeline) or 20px (content). Card padding 16px left/right, 20px top from accent bar
- **Bounding boxes**: inner = rendered extent incl stroke; outer = inner + padding. Padding: text 12px from card edge, decorative icon/logo 6px edges + 4px from text, card 10px from neighbours/viewBox, accent bar 0px (flush)

## SVG Structure

File description comment before `<svg>`:

```xml
<!--
  filename.svg - Short role description
  Shows: visual elements in reading order
  Intent: purpose in document
  Theme: palette name, shade assignments
-->
```

- `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">` - `viewBox` only, never `width`/`height`
- Default width 1800. Sizes: 1800x200 stats, 1800x280 timelines, 1800x320 flows, 1800x400 headers, 1800x700 grids

### Typography

- `font-family="Segoe UI, Arial, sans-serif"` - system fonts only; the Word-safe set is Segoe UI / Arial / Calibri
- Sizes 7-28px. Progression: hero stats 18-28 > headings 12-14 > labels 10-11 > metadata 8-9
- `text-anchor="middle"` for centred, explicit `x` for left-aligned
- Never `<tspan>` for mixed styling - separate `<text>` elements

### Unicode glyphs in text

| Intent | Write | Don't write |
|---|---|---|
| arrows | `→` `←` `↑` `↓` `↔` `➜` | `->` `<-` `^` `v` `<->` `>` |
| em / en dash | `—` / `–` | `--`, `-` in ranges |
| ellipsis | `…` | `...` |
| multiplication | `×` | `x` |
| bullet / chevron | `•` / `›` | `*` / `>` |

XML comments differ: `--` breaks parsing. ASCII prose in comments, Unicode only in text nodes.

## Z-Order Layering (MANDATORY)

Document order = render order. Five named groups bottom-up; every drawable in exactly one layer, no stray top-level shapes:

```xml
<style>...</style>
<g id="background">...</g>   <!-- fills, grids, banners -->
<g id="nodes">...</g>        <!-- cards, circles, hexes -->
<g id="connectors">...</g>   <!-- arrows, strands, spines -->
<g id="content">...</g>      <!-- icons, labels, text -->
<g id="callouts">...</g>     <!-- callout groups - topmost -->
```

Every arrow inside `<g id="connectors">`, never at root. Every callout = child `<g id="callout-<name>">` inside the callouts layer. Track lines: cut real gaps at milestone nodes, never `fill="white"` knockouts.

## Markdown Integration

`![Description](path.svg)` - no HTML `<img>` unless width control needed.

## Creative Infographics

Organic forms (flowing paths, rings, orbital loops, funnels, constellations) follow the same theme swatch, CSS classes, transparent background. Low fill opacities (0.04-0.15). Topology ops: `flow:`, `orbit:`, `scatter:`, `radial:`. Decoration passes go through `/svg-infographics:beautify` (additive only, geometry-guarded - full rules in the beautify command doc and SKILL.md).
