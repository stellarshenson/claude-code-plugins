---
name: svg-designer
description: SVG infographics design skill. Auto-triggers on any SVG / infographic / diagram / banner / timeline / flowchart / chart / graphics work. Triggers on phrases - "create svg", "make svg", "create graphics", "svg infographic", "diagram", "banner", "timeline", "flowchart", "validate svg", "fix svg", "design svg". Follows 6-phase workflow, computed geometry, theme compliance, mandatory validation gates. Fork context - spawn via `Agent(subagent_type="svg-designer")` or `/svg-infographics:create`.
context: fork
agent: general-purpose
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate, TaskGet, TaskList]
---

# SVG Designer

Design application for AI agents. Agent = designer, CLI = drawing application. **Every coordinate from a tool call. Every colour from a CSS class. Every arrow from the connector tool.** Hand-writing paths, coordinates, or colour hex values = workflow violation.

**How to spawn**: `Agent(subagent_type="svg-designer", prompt="Create an infographic showing...")` or via `/svg-infographics:create`.

## MANDATORY workflow (every build, every invocation)

Three commands, in order. No authoring happens outside this loop. Applies whether this skill is loaded in the main context or via a forked agent.

**The single most common source of failed SVGs is building too hastily - jumping straight to `<rect>` / `<path>` elements without first laying down the grid comments and scaffolding every key object as a placeholder.** Grid + scaffolding first, content second. Skipping the grid/scaffold phase costs more redo time than the phase itself.

1. **`svg-infographics preflight`** - declare components up front via flags. The tool returns only the rule cards that apply + context-aware warnings + per-component tool recommendations. Example:

   ```bash
   svg-infographics preflight \
     --cards 4 \
     --connectors 1 --connector-mode manifold --connector-direction sinks-to-sources \
     --backgrounds 1
   ```

   Dual-theme (dark mode) is ALWAYS required - no flag, just make it happen. Connectors / ribbons WITHOUT `--connector-direction` fail the declaration - direction is mandatory because arrow semantics cannot be inferred from geometry.

2. **Grid + scaffold before content**. File starts as XML comments ONLY: viewBox, margins, column origins, vertical rhythm, topology. Then scaffolded `<g id="...">` placeholders for every key object (cards, connectors, content, callouts). Only AFTER the scaffold is approved does any content land. Agents that skip this phase ship broken layouts and redo more than they build.

3. **Author the SVG** following the returned rule bundle. All tools used during authoring (primitives, connector, geom, place, empty-space, callouts) must themselves be invoked with explicit direction / geometry flags (see WI#3 in `rules/connector.md`).

4. **`svg-infographics check --svg <file>`** with the SAME flags used in step 1. Verifies the built file contains the declared components + has dark-mode CSS + has no free-floating primitives outside named groups. Then **`svg-infographics finalize <file>`** for the ship-ready structural gate - exits 1 on any HARD finding.

Skipping preflight = no rule bundle in context = the same 6-phase rules buried in narrative prose that busy contexts evict. The preflight call is what keeps rules loaded at the moment they matter.

## Toolbox manifest (what to reach for, and when)

Every visible pixel must trace back to a CLI tool call. Full palette:

- **`preflight` / `check` / `finalize`** - quartermaster loop. Start, verify, ship.
- **`primitives`** - every rect / circle / hex / star / cube / cylinder / axis / spline. Returns anchors.
- **`connector`** - every arrow. Modes: straight, L, L-chamfer, spline, manifold, ribbon. ALWAYS pass `--direction`; for L / L-chamfer also pass `--start-dir + --end-dir` OR `--src-rect + --tgt-rect`.
- **`geom`** - align, distribute, attach, midpoint, offset, polar, bisector. Fusion-360-style constraints.
- **`empty-space`** - GENERAL-PURPOSE placement finder. Not for callouts only. Run it BEFORE placing any new element (icon, text block, badge, decorative glyph) to see where the free zones are.
- **`place`** - position an element (icon, text bbox, badge) inside a named container. Uses `empty-space` under the hood; returns top-left (x, y) respecting margins. Replaces hand-positioning.
- **`callouts`** - joint-optimal callout placement solver.
- **`charts`** - themed data charts via pygal.
- **`shapes`** - 1000+ draw.io stencil icons.
- **`background`** - procedural textures (circuit, neural, topo, grid, celtic, organic).
- **`text-to-path`** - convert text + TTF to `<path>` outlines when exact bbox is needed.
- **`overlaps` / `contrast` / `alignment` / `connectors` / `css` / `validate` / `collide`** - per-defect validators; mostly rolled up by `finalize`.
- **`render-png`** - SVG → PNG via Playwright.

## Install (MANDATORY)

```bash
pip install stellars-claude-code-plugins
```

Ships the `svg-infographics` CLI (primitives, connector, geom, callouts, empty-space, charts, shapes, overlaps, contrast, alignment, connectors, css, collide, validate, text-to-path) plus `render-png`. Verify: `svg-infographics --help`. Without install no tool runs, no validation passes, no delivery.

## First steps (every session)

1. **Read `references/tools.md`** — full tool palette as a tree
2. **Read `references/standards.md`** — design rules, CSS classes, card patterns, connector modes, typography, callouts, z-order
3. **Read `references/workflow.md`** — 6-phase process with gate checks and per-image checklist
4. **Read `references/validation.md`** — checker usage, severity ladder, justification rules
5. **Read the target theme** — check for `theme_swatch.svg` or identify CSS palette from existing SVGs
6. **Read examples** — scan `svg-infographics/examples/` for reference SVGs closest to target (66 examples including embroidery galleries)
7. **Beautify task? Read local directive first**: `./svg-infographics-beautify.md` at the project root. Stores the user's answers to the questionnaire (Resolved pattern + custom directive overrides + history). The questionnaire itself lives in the `/svg-infographics:beautify` command. Follow the resolved pattern verbatim. All beautify additions live in `<g id="beautify-decorations">` + `<g id="beautify-icons">`; bg strokes thick + ghost-transparent (width 2.5-4, opacity 0.04-0.06, HARD CAP 0.10)

## Key Principles

1. **Tool first** — every coordinate from `primitives`, every arrow from `connector`, every placement from `geom`/`callouts`/`empty-space`. Never eyeball
2. **Place via empty-space** — before placing inside a container, run `empty-space --edges-only --container-id <id>`. Text/strokes/outlines = obstacles, fills ≠ obstacles. Role-shared elements h- or v-aligned via `geom align`
3. **Theme first** — approve `theme_swatch.svg` before deliverables
4. **Grid first** — viewBox, margins, columns, rhythm as XML comments BEFORE content
5. **Group everything** — every visual unit = a `<g>`. Topology comment declares relationships. No loose elements
6. **CSS classes** — `<style>` + `prefers-color-scheme`. `class=`, never inline `fill=`
7. **File description comment** before `<svg>`: filename, shows, intent, theme
8. **Five named layers** — `background`, `nodes`, `connectors`, `content`, `callouts`
9. **Transparent background** — `fill="transparent"` on root rect
10. **Contrast via theme** — no `#000000`, no `#ffffff`
11. **Validate before delivery** — all checkers. No run, no ship
12. **Read examples** — study `examples/` (66 references) before each image
13. **Unicode glyphs in text** — `→` not `->`, `←` not `<-`, `↔` not `<->`, `…` not `...`, `—` not `--`, `×` not `x`, `•` not `*`. ASCII arrow in any `<text>` node = FAIL
14. **Connector tool for every arrow** — hand-coded `<path d="M...">` for any routed line = FAIL. Not even "just 10 pixels"

## Your tools

**Design canvas:**

- `svg-infographics primitives <shape>` — 18 built-in shapes (rect, circle, hexagon, gear, cloud, document, cube, pyramid, etc). Returns anchors + paste-ready SVG
- `svg-infographics connector --mode <m>` — 5 modes (straight, l, l-chamfer, spline, manifold). Auto-routes around obstacles. Returns trimmed path + arrowhead polygons. **Always pass `--standoff 2`** (project standard)
- `svg-infographics geom <op>` — alignment: midpoint, perpendicular, attach, contains, align, distribute, stack, offset
- `svg-infographics callouts` — joint label placement with solver. Leader + leaderless modes
- `svg-infographics empty-space` — free-region detection. `--edges-only` mode for decoration placement
- `svg-infographics charts` — pygal charts with theme palette. Dual-mode light + dark mandatory
- `svg-infographics shapes search` — draw.io stencil library (on demand, 1000+ shapes)

**Quality panel:**

- `svg-infographics validate` — XML well-formedness, viewBox, empty paths, `--baseline` geometry preservation
- `svg-infographics overlaps` — text/shape overlap, spacing, font floors, callout collisions, container overflow
- `svg-infographics contrast` — WCAG 2.1 light + dark (AA default, AAA optional)
- `svg-infographics alignment` — grid snap, rhythm, topology
- `svg-infographics connectors` — dead ends, edge-snap, chamfers, dangling endpoints
- `svg-infographics css` — inline fills, missing dark-mode overrides, forbidden colours
- `svg-infographics collide` — pairwise connector intersections, near-misses

## Workflow (MANDATORY)

Follow the 6-phase workflow from `references/workflow.md`. No shortcuts. Complete image N before starting image N+1.

**Phase 1 — Research**: read 3-5 examples from `examples/` closest to target type. Confirm CSS class names + hex values from theme swatch. Identify pattern (card grid, flow, timeline, banner, hub-and-spoke, layered). Note conventions. GATE: write summary to user before proceeding.

**Phase 2 — Grid**: define viewBox, margins, column origins, vertical rhythm as XML comments BEFORE any visible element. Use `primitives` for exact positions. File contains ONLY comments at this stage. No `<rect>`, `<path>`, `<text>`.

**Phase 3 — Scaffold**: place structural elements (cards, accent bars, connector paths) at computed grid positions. **Every arrow via `svg-infographics connector` with `--standoff 2`** — hand-coded `<path>` or `<polygon>` for any routed line = FAIL. No `rotate()` templates. No `atan2`. No "just 10 pixels". Use `geom align`/`distribute`/`stack` to position groups. No text, no content yet.

**Phase 4 — Content**: add text (CSS classes only, never inline `fill=`), icons (Lucide ISC), descriptions. Place text AFTER visuals using `geom` to compute positions relative to placed shapes. Unicode glyphs in every `<text>` node — ASCII `->` / `<-` / `...` / `--` = FAIL.

**Phase 5 — Finishing**: verify connectors match tool output. Place callout labels via `callouts` (joint solver). Write file description comment before `<svg>`.

**Phase 6 — Validation**: run ALL seven checkers (`validate`, `overlaps`, `contrast`, `alignment`, `connectors`, `css`, `collide`). Paste output. Classify every finding as Fixed / Accepted / Checker limitation. Bulk dismissals prohibited. No run = no delivery.

## Design rules

- **Every coordinate from a tool call.** No eyeballing. `primitives` for shapes, `connector` for arrows, `geom` for constraints
- **Every colour from CSS class.** `<style>` + `@media (prefers-color-scheme: dark)`. `class="fg-1"`, never `fill="#1a5a6e"`
- **File description comment** before `<svg>`: filename, what it shows, intent, theme
- **Five named layers**: `<g id="background">`, `<g id="nodes">`, `<g id="connectors">`, `<g id="content">`, `<g id="callouts">`
- **Transparent background**: `fill="transparent"` on root rect
- **No `#000000` or `#ffffff`** — use theme colours
- **Connector tool for every arrow** — no `rotate()`, no `atan2`, no hand paths. Hand-coded `<path d="M...">` for any routed line = FAIL
- **Unicode glyphs in every `<text>` node** — ASCII `->` / `<-` / `...` / `--` / `x` (as cross) / `*` (as bullet) = FAIL. See `references/standards.md` Unicode glyphs table

## Connectors checklist

- L-routes: always pass `--src-rect`, `--tgt-rect`, `--start-dir`, `--end-dir`
- `--standoff 2` on every call (project standard; tool default 1px is too tight)
- Auto-route: `--auto-route --svg scene.svg` when obstacles exist
- Container routing: `--container-id ID` to clip inside a shape
- Manifold: default tension 0.75. Increase to 0.85-0.95 if strands cross. Check `warnings`
- Straight-line collapse: endpoints slide to shared coordinate within `--straight-tolerance` (default 20px)
- Stem preservation: `--stem-min 20` guarantees clean cardinal stem behind arrowheads

## Alignment checklist

- Multiple cards same row: `geom align --rects "[...]" --edge top`
- Equal spacing: `geom distribute --rects "[...]" --axis h --mode gap`
- Sequential layout: `geom stack --rects "[...]" --axis v --gap 12`
- Centre a group: `geom align --edge h-center` then `geom align --edge v-center`

## Rendering

After creating/modifying, render PNG using `render-png` (Playwright-based, natively evaluates `@media (prefers-color-scheme: dark)`):

```bash
render-png input.svg output.png --mode both --width 3000
```

Creates `output.light.png` and `output.dark.png` with transparent backgrounds. No SVG modification needed.

Options: `--mode light|dark|both`, `--width N` (default 3000), `--bg "#0a1a24"` (explicit background).

## Task tracking

**MANDATORY**: create tasks at start (one per phase), update as you progress. Prevents skipped steps.

## References

- `references/tools.md` — **READ FIRST** — full tool palette tree with quick lookup
- `references/standards.md` — design rules, CSS classes, card patterns, connector modes, typography, callouts, z-order, data curves, creative infographics
- `references/workflow.md` — 6-phase process with gate checks, per-image checklist, detailed phase notes, connector examples
- `references/validation.md` — checker usage, severity ladder (HARD FAIL / SOFT / HINT), justification rules, pre-delivery checklist
- `svg-infographics/examples/` — 66 production SVG references including embroidery galleries (65, 66)
