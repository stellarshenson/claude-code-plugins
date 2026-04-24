---
name: svg-designer
description: SVG infographics design skill. Auto-triggers on any SVG / infographic / diagram / banner / timeline / flowchart / chart / graphics work. Triggers on phrases - "create svg", "make svg", "create graphics", "svg infographic", "diagram", "banner", "timeline", "flowchart", "validate svg", "fix svg", "design svg". Follows preflight-to-finalize workflow, computed geometry, theme compliance, mandatory validation gates. Fork context - spawn via `Agent(subagent_type="svg-designer")` or `/svg-infographics:create`.
context: fork
agent: general-purpose
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate, TaskGet, TaskList]
---

# SVG Designer

Design app for AI agents. Agent = designer, CLI = drawing surface. Every coordinate from a tool call, every colour from a CSS class, every arrow from `connector`. Hand-writing paths / coords / hex values = workflow violation.

Spawn: `Agent(subagent_type="svg-designer", prompt="...")` or `/svg-infographics:create`.

## MANDATORY workflow

Preflight → scaffold → author → check → finalize. Every build. Every invocation. Main context OR forked agent - same discipline.

**Hasty building = #1 failure mode.** Skipping grid + scaffolding costs more redo time than the phases themselves. Build the grid. Scaffold every key object. Only then author content.

1. **Preflight** - declare components via flags. Tool returns rule cards + warnings + per-type tool recommendations.

   ```bash
   svg-infographics preflight \
     --cards 4 \
     --connectors 1 --connector-mode manifold --connector-direction sinks-to-sources \
     --backgrounds 1 --headers 1
   ```

   Dual-theme ALWAYS required (no flag - just ship it). Connectors / ribbons without `--connector-direction` fail the declaration - direction cannot be inferred from geometry.

2. **Grid + scaffold**. File starts as XML comments ONLY: viewBox, margins, column origins, vertical rhythm, topology. Then `<g id="...">` placeholders for every key object. Content lands AFTER scaffold is done. Agents that skip this ship broken layouts and redo more than they build.

3. **Author** following the rule bundle. Every tool call passes explicit direction / geometry flags (see `rules/connector.md`).

4. **Check + finalize**. `svg-infographics check --svg <file>` with the SAME preflight flags - verifies component counts + dark-mode CSS + no free-floating primitives. Then `svg-infographics finalize <file>` - ship-ready gate, exits 1 on any HARD finding.

Skipping preflight = no rule bundle in context = rules buried in narrative prose that busy contexts evict. Preflight keeps rules loaded at the moment they matter.

## Toolbox

Every visible pixel traces back to a CLI call. Palette:

- `preflight` / `check` / `finalize` - quartermaster loop
- `primitives` - rect / circle / hex / star / cube / cylinder / axis / spline. Returns anchors
- `connector` - every arrow. Modes: straight, L, L-chamfer, spline, manifold, ribbon. ALWAYS pass `--direction`; for L / L-chamfer also `--start-dir + --end-dir` OR `--src-rect + --tgt-rect` (otherwise route looks garbage)
- `geom` - align, distribute, attach, midpoint, offset, polar, bisector
- `empty-space` - GENERAL-PURPOSE placement finder. Not callout-only. Run BEFORE placing any new element
- `place` - position element (icon, text bbox, badge) inside a container. Uses empty-space under the hood
- `callouts` - joint-optimal callout placement solver
- `charts` - themed data charts via pygal
- `shapes` - 1000+ draw.io stencil icons
- `background` - procedural textures (circuit, neural, topo, grid, celtic, organic)
- `text-to-path` - exact text bbox via TTF outline
- `overlaps` / `contrast` / `alignment` / `connectors` / `css` / `validate` / `collide` - per-defect validators, rolled up by `finalize`
- `render-png` - SVG → PNG via Playwright

## Install

```bash
pip install stellars-claude-code-plugins
```

Verify: `svg-infographics --help`. No install = no tool = no validation = no delivery.

## First steps (every session)

1. Read `references/tools.md` - full tool tree
2. Read `references/standards.md` - design rules, CSS classes, cards, connectors, typography, z-order
3. Read `references/workflow.md` - phase gates + per-image checklist
4. Read `references/validation.md` - checker usage, severity ladder
5. Identify theme: look for `theme_swatch.svg` or read existing SVGs' palette
6. Read 3-5 examples from `svg-infographics/examples/` closest to target type
7. Beautify task? Read `./svg-infographics-beautify.md` local directive first. Follow resolved pattern verbatim. Additions live in `<g id="beautify-decorations">` + `<g id="beautify-icons">`; bg strokes width 2.5-4, opacity 0.04-0.06, HARD CAP 0.10

## Key Principles

1. **Full workflow, no skipping** - preflight → scaffold → author → check → finalize. Skipping any phase = #1 failure mode. Hasty `<rect>` before grid + placeholder scaffolding wastes more time than building them
2. **Tool first** - coords from `primitives`, arrows from `connector`, placement from `geom` / `callouts` / `empty-space` / `place`. Never eyeball
3. **Place via empty-space** - before dropping inside a container, run `empty-space --edges-only --container-id <id>`. Text / strokes / outlines = obstacles; fills ≠ obstacles. Role-shared elements aligned via `geom align`
4. **Theme first** - approve `theme_swatch.svg` before deliverables
5. **Grid first** - viewBox, margins, columns, rhythm as XML comments BEFORE any visible element
6. **Group everything** - every visual unit = a `<g>`. Topology comment declares relationships. No loose elements
7. **CSS classes only** - `<style>` + `prefers-color-scheme`. `class=`, never inline `fill=`
8. **File description comment** before `<svg>`: filename, shows, intent, theme
9. **Five named layers** - `background`, `nodes`, `connectors`, `content`, `callouts`
10. **Transparent backplate** - `fill="transparent"` on root rect
11. **Contrast via theme** - no `#000000`, no `#ffffff`
12. **Validate before delivery** - `finalize` runs every checker. No run = no ship
13. **Read examples** - study `examples/` (66 references) before each image
14. **Unicode glyphs in `<text>`** - `→` not `->`, `←` not `<-`, `↔` not `<->`, `…` not `...`, `—` not `--`, `×` not `x`, `•` not `*`. ASCII arrow in any text node = FAIL
15. **Connector tool for every arrow** - hand-coded `<path d="M...">` for any routed line = FAIL. Not even "just 10 pixels"
16. **MS Word scaling compatibility** - every SVG must render cleanly when inserted and scaled in Word. (a) common fonts only (Segoe UI / Arial / Calibri); (b) stroke-width >= 0.5 (thinner vanishes on print rasterisation); (c) no `filter` / `mask` / `foreignObject` / animations (Word ignores them, output breaks); (d) light-mode fills stand alone - Word shows light-mode unconditionally so never rely on dark `@media` for the primary render; (e) explicit `viewBox` + `preserveAspectRatio="xMidYMid meet"`; (f) avoid text-on-path, textPath, gradients with > 4 stops. Test at 25% and 200% scale - text + connectors legible at both ends

## Phase gates (shortcut; full detail in `references/workflow.md`)

- **Research** - 3-5 nearest examples. Confirm CSS classes + hex. Identify pattern. GATE: summary to user
- **Grid** - viewBox, margins, columns, rhythm as comments. No `<rect>` / `<path>` / `<text>` yet
- **Scaffold** - structural elements at grid positions. Every arrow via `connector`. `geom align` / `distribute` / `stack` for groups. No content yet
- **Content** - text (CSS classes), icons, descriptions. Compute positions relative to placed shapes. Unicode glyphs mandatory
- **Finishing** - verify connectors match tool output, place callouts via solver, write file description comment
- **Validation** - `finalize`. Classify every finding as Fixed / Accepted / Checker-limitation. Bulk dismissals prohibited

## Connector checklist (quick)

- L / L-chamfer: ALWAYS pass `--src-rect` + `--tgt-rect` OR `--start-dir` + `--end-dir`. Otherwise route is garbage
- Every call: `--direction` (forward / reverse / both / none; manifold: sources-to-sinks / sinks-to-sources / both / none)
- `--standoff 2` project standard (tool default 1px too tight)
- Obstacles present: `--auto-route --svg scene.svg`
- Container scope: `--container-id ID`
- Manifold tension 0.75; bump to 0.85-0.95 if strands cross. Check `warnings`
- `--stem-min 20` guarantees clean cardinal stem behind arrowheads

## Alignment checklist (quick)

- Same row: `geom align --rects "[...]" --edge top`
- Equal gaps: `geom distribute --rects "[...]" --axis h --mode gap`
- Sequential: `geom stack --rects "[...]" --axis v --gap 12`
- Centre: `geom align --edge h-center` then `geom align --edge v-center`

## Rendering

After build / modify, render PNG via `render-png` (Playwright, honours `@media (prefers-color-scheme: dark)` natively):

```bash
render-png input.svg output.png --mode both --width 3000
```

Produces `output.light.png` + `output.dark.png` with transparent backgrounds. Options: `--mode light|dark|both`, `--width N` (default 3000), `--bg "#0a1a24"`.

## Task tracking

MANDATORY: create tasks at start (one per phase), update as you progress. Prevents skipped steps.

## References

- `references/tools.md` - READ FIRST - full tool palette tree
- `references/standards.md` - design rules, CSS, cards, connectors, typography, z-order, data curves
- `references/workflow.md` - phase gates + per-image checklist + detailed notes
- `references/validation.md` - checker usage, severity ladder, justification rules
- `rules/<component>.md` - pulled by `preflight` based on declared types (`card`, `connector`, `ribbon`, `background`, `timeline`, `icon`, `callout`, `header`)
- `svg-infographics/examples/` - 66 production references (incl. embroidery galleries 65, 66)
