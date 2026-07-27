---
name: svg-designer
description: Grid-first SVG design workflow producing validated infographics - diagrams, banners, timelines, flowcharts, card grids, charts. Use when creating, fixing or validating any SVG graphic - scaffold a standard format, compute every coordinate via CLI tools, route connectors with direction gates, ship only on a clean finalize. Triggers - "create svg", "make svg", "create graphics", "svg infographic", "diagram", "banner", "timeline", "flowchart", "validate svg", "fix svg", "design svg". Fork context - invoke via `Skill(skill="svg-infographics:svg-designer")` or `/svg-infographics:create`.
context: fork
agent: general-purpose
model: sonnet
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, TaskCreate, TaskUpdate]
---

# SVG Designer

Design app for AI agents. Agent = designer, CLI = drawing surface. Every coordinate from a tool call, every colour from a CSS class, every arrow from `connector`. Hand-writing paths / coords / hex values = workflow violation.

## Workflow (mandatory, every build)

Preflight → scaffold → author → check → finalize. Skipping a phase is the #1 failure mode - hasty `<rect>`s cost more redo time than the phases themselves. Dual-theme always ships (no flag - just do it).

**Output path** - write every `--out` file into the exact directory named in your args, verbatim (`<output-dir>/<NN-name>.svg`). When given an absolute `<output-dir>`, use it as-is - never prepend the working directory, `cd` into a subdir first, or repeat the directory's own relative path inside itself (that nests `.../slug/slug/images_slug`).

1. **Preflight** - declare components via flags; tool returns the rule cards + warnings + tool recommendations THIS image needs. No authoring before it returns.

   ```bash
   svg-infographics preflight --cards 4 \
     --connectors 1 --connector-mode manifold --connector-direction sinks-to-sources \
     --backgrounds 1 --headers 1
   ```

   Connectors / ribbons without `--connector-direction` fail the declaration - direction cannot be inferred from geometry.

2. **Scaffold - via the tool, not by hand.** `svg-infographics scaffold --format <preset> --cols C --rows R --cards N --out <file>` generates the skeleton in one call: viewBox, 5px-snapped grid comments, topology stub, theme CSS + dark mode, hidden `guide-grid` + `grid-100/20/5` inspection layers, the five canonical layers, placeholder cards (`data-placeholder="true"`; doc-header gets slot anatomy instead). A fresh scaffold passes `finalize` with ZERO findings. Presets: `scaffold --list` (doc-stats / doc-timeline / doc-flow / doc-header / doc-grid / slide-16x9 / slide-4x3 / square). Re-theme the CSS against the approved swatch, then replace placeholders keeping the `card-N` ids.

3. **Author** following the rule bundle. Every tool call passes explicit direction / geometry flags (`rules/connector.md`). Run `svg-infographics map --svg <file>` before placing anything new.

4. **Check + finalize.** `svg-infographics check --svg <file>` with the SAME preflight flags (component counts, dark mode, layer discipline, free-floating primitives), then `svg-infographics finalize <file>` - ship gate, exit 1 on any HARD finding.

Resuming or unsure what remains? `svg-infographics workflow --svg <file>` infers the phase from the file and prints unmet gates + next actions - never redo a gate it reports as met.

## Toolbox

Every visible pixel traces back to a CLI call:

- `preflight` / `check` / `finalize` - quartermaster loop, all per-file
- `consistency --svg <f1> --svg <f2> …` - compares card anatomy (icons, slots, card primitives) across sibling SVGs. `finalize` runs this automatically when passed several files, so the deck close is one multi-file `finalize`; reach for the standalone command only to re-check a deck without re-running the per-file gates
- `scaffold` - format skeleton: grid, CSS, layers, placeholders (workflow step 2)
- `workflow` - phase inference + next actions from the file itself
- `map` - one-glance occupancy scan: ASCII grid, letter = topmost layer per cell (b/n/c/t/o), `.` = free, plus per-layer stats + largest free placement boxes. ONE call replaces several empty-space scans
- `primitives` - rect / circle / ellipse / diamond / hexagon / star / arc / cube / cuboid / cylinder / sphere / plane / pyramid / gear / cloud / document / speech / thought / spline / axis. Returns anchors. Discovery: `primitives` (bare), `--list`, `--caveman`
- `connector` - every arrow. Modes: straight, L, L-chamfer, spline, manifold, ribbon (see checklist below)
- `geom` - align, distribute, attach, midpoint, offset, polar, bisector
- `boolean` - union / intersection / difference / xor plus `buffer`, `cutout`, `outline` (`rules/shapes.md`)
- `empty-space` - general-purpose placement finder; `--layers nodes,content` (obstacles ONLY from these) or `--ignore-layers callouts`
- `place` - position an element inside a container (empty-space under the hood)
- `callouts` - joint-optimal callout placement solver
- `charts` - themed data charts via pygal
- `icons` - bundled icons + catalogue of every icon route (custom / Lucide / draw.io); `shapes` - 1000+ draw.io stencils
- `background` - procedural textures (circuit, neural, topo, grid, celtic, organic)
- `text-to-path` - exact text bbox via TTF outline
- `shaders` (beautify dimension 8) - 10 filter recipes: frosted-glass, water-ripple, iridescent, chromatic-aberration, embossed-metal, light-leak, bokeh, lens-flare, holographic-foil, paper-grain (`rules/shaders.md`)
- `overlaps` / `contrast` / `alignment` / `connectors` / `css` / `validate` / `collide` - per-defect validators, rolled up by `finalize`
- `render-png` - SVG → PNG via Playwright

## Toolchain gate (reinstall every session, refuse only if the library is unavailable - no asking)

Run BEFORE anything else, and ALWAYS upgrade. A stale-but-importable version is the exact failure this gate exists to prevent - an old CLI silently runs old validators (e.g. a pre-1.6.16 connector checker that mis-flags the full-canvas background plate as a card and floods edge-snap). An `import ... || install` guard never upgrades a version that already imports, so force the reinstall unconditionally:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && echo "STALE: library $LIB != plugin $PLUG - CLI may lack flags this skill uses; re-run the upgrade" || echo "toolkit $LIB"
```

Then verify the CLI runs: `svg-infographics --help`.

- **The upgrade always runs** - every session reinstalls to the latest so the validators match the current rules; never skip it because the package is already present, that is how a stale checker survives
- **The version compare is the real gate** - `--help` exits 0 on an ancient CLI, so a green `--help` proves nothing. Only `LIB == PLUG` proves the CLI carries the flags this skill documents. A `STALE:` line means treat every CLI failure as a version problem first
- **Refuse to start** only when the library is unavailable after the reinstall attempt - the import still fails, so `svg-infographics --help` still errors. Report the error and stop; there is no fallback, because every rule here assumes the CLI, and a hand-built SVG without the geometry tools and validators is exactly the defect class the toolchain prevents
- A failed *upgrade* is NOT a refusal condition - offline or PyPI unreachable while the CLI still imports means run at the installed version; the reinstall was attempted, which is what matters. An absent library is fatal, a stale one that could not reach PyPI is a hazard to report, not a stop

## First steps (every session)

Context is the budget - mandatory reads only:

1. `references/standards-core.md` - CSS classes, contrast, grid, structure, z-order (≤8KB)
2. `examples/INDEX.md` (geometry recipes per pattern) + ONE example closest to the target type
3. `svg-infographics preflight` declaring every component - the returned rule bundle is your component knowledge
4. Theme: `theme_swatch.svg` or an existing SVG's palette
5. On demand, not up front: `references/workflow.md` (phase gates + checklist), `references/validation.md` (unclear finalize finding), `references/tools.md` (which tool exists), `examples/concept_draft_deck.md` (concept-draft shape)
6. Beautify task? Read `./svg-infographics-beautify.md` local directive first; additions live in `<g id="beautify-decorations">` + `<g id="beautify-icons">`; bg strokes width 2.5-4, opacity 0.04-0.06, cap 0.10

## Key principles

1. **Tool first** - coords from `primitives`, arrows from `connector`, placement from `geom` / `callouts` / `empty-space` / `place`. Never eyeball
2. **Place via empty-space** - before dropping inside a container, `empty-space --edges-only --container-id <id>`. Text / strokes / outlines = obstacles, fills ≠ obstacles
3. **Symmetry by default** - corner elements equidistant from BOTH adjacent edges; connector standoff equal both ends; equal gaps between cards; equal margins around centred headers. Asymmetry must be intentional and justified against a specific visual rule. When in doubt: equal
4. **Theme first** - approve `theme_swatch.svg` before deliverables
5. **Group everything** - every visual unit = a `<g>`; topology comment declares relationships; no loose elements
6. **CSS classes only** - `<style>` + `prefers-color-scheme`; `class=`, never inline `fill=`
7. **File description comment** before `<svg>`: filename, shows, intent, theme
8. **Five named layers** - `background`, `nodes`, `connectors`, `content`, `callouts`; document order = render order
9. **Transparent backplate**; contrast via theme - no `#000000`, no `#ffffff`
10. **Unicode glyphs in `<text>`** - `→` not `->`, `←` not `<-`, `↔` not `<->`, `…` not `...`, `—` not `--`, `×` not `x`, `•` not `*`. ASCII arrow in any text node = FAIL
11. **Validate before delivery** - `finalize` runs every checker. No run = no ship
12. **MS Word scaling compat** - every SVG renders cleanly inserted + scaled in Word: common fonts only (Segoe UI / Arial / Calibri); stroke-width ≥ 0.5; no `filter` / `mask` / `foreignObject` / animation in the Word-targeted variant; light-mode fills stand alone (Word ignores dark `@media`); explicit `viewBox` + `preserveAspectRatio="xMidYMid meet"`; no textPath or >4-stop gradients. Exception: shader effects ship via the print-strip workflow - `<file>+_print.svg` (filters stripped) for Word, `<file>+.svg` for web (`rules/shaders.md`)

## Connector checklist (quick)

- L / L-chamfer: ALWAYS pass `--src-rect` + `--tgt-rect` AND `--start-dir` + `--end-dir`; every call passes `--direction` (forward / reverse / both / none; manifold: sources-to-sinks / sinks-to-sources / both / none). Hand-coded `<path d="M...">` for any routed line = FAIL, not even "just 10 pixels"
- Direction gates verify axis AND sign on BOTH ends plus interior piercing (`ROUTE-AXIS-MISMATCH[-END]`, `ROUTE-DIR-REVERSED[-END]`, `ROUTE-THROUGH-SOURCE/TARGET`). Blocked = a 1-bend route cannot satisfy that pair: add a `--controls` waypoint, use `--auto-route`, or change the direction. Never ack these to force a wrong-face arrival
- `--standoff 2` project standard (tool default 1px too tight)
- Obstacles present: `--auto-route --svg scene.svg` (optionally `--route-ignore-layers callouts,content`); container scope: `--container-id ID`
- Manifold: `--auto-tune` (escalates tension until strand crossings clear in one call); `--stem-min 20` guarantees a clean cardinal stem behind arrowheads

## Warning-ack gate (stop and think)

Producer tools block output on exit 2 whenever any warning fires; output resumes only with `--ack-warning TOKEN=reason` per warning - one flag, one terse reason each, no bulk override. Tokens hash the warning text, so fixing other flags keeps outstanding tokens valid. Fixing the input ALWAYS beats acking; a stack of acks means the input needs rework. Reasons like "known issue" fail review - name the constraint ("card column locked"). Full gate matrix: `references/validation.md`; per-tool specifics in each rule card.

## Alignment checklist (quick)

- Same row: `geom align --rects "[...]" --edge top`
- Equal gaps: `geom distribute --rects "[...]" --axis h --mode gap`
- Sequential: `geom stack --rects "[...]" --axis v --gap 12`
- Centre: `geom align --edge h-center` then `--edge v-center`

## Rendering

After build / modify: `render-png input.svg output.png --mode both --width 3000` → `.light.png` + `.dark.png`, transparent backgrounds, honours `prefers-color-scheme` natively. Options: `--mode light|dark|both`, `--width N`, `--bg "#hex"`.

## Task tracking

Create tasks at start (one per phase), update as you progress - prevents skipped steps.

## References

- `references/standards-core.md` - essentials (read first)
- `references/workflow.md` - phase gates + per-image checklist
- `references/validation.md` - checker usage, severity ladder, ack rules
- `references/tools.md` - full tool palette tree
- `rules/<component>.md` - served by `preflight` per declared type
- `svg-infographics/examples/` - production references + `concept_draft_deck.md`
