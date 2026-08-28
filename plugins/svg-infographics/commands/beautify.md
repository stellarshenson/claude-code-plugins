---
description: Enhance existing SVGs with glow, icons, decorations, colour variation, abstract shapes at configurable intensity (low/medium/high/absurd)
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "path(s) + level, e.g. 'docs/images/*.svg medium' or 'banner.svg high'"
---

# Add Life

## Toolchain gate (refuse only if the library is unavailable)

Before anything else run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Verify the CLI runs: `svg-infographics --help`. **The gate above blocks on both failures** - an absent library (`FATAL`) and a version mismatch (`STALE`) each exit non-zero. Neither is advisory: this command documents the current plugin's flags, so a mismatched CLI may reject them and anything it does produce is unverified. Report the line and stop. No fallback, no hand-built output.


Decoration pass on existing SVG. NOT a redesign - additive overlays, filters, fills. Positions, text, connectors stay unchanged.

## HARD RULE (absolute, non-negotiable)

**UNDER NO CIRCUMSTANCES CHANGE GEOMETRY unless the user explicitly asks for it.**

No paths may be moved, resized, rewritten, or deleted. No `<g>` structure may be restructured. No `<line>`, `<path>`, `<rect>`, `<circle>`, `<polygon>`, or connector may be altered, removed, or replaced with a "better" version. No spine, trunk, strand, arrow, or axis line may be touched. No card shape, manifold, workflow arrow, or grid line may be tweaked.

If a decoration would require modifying an existing element, DO NOT add it. Decorations live in a SEPARATE `<g id="beautify-decorations">` group added BELOW the original `<g id="content">` and `<g id="connectors">` in the DOM. The original DOM stays byte-for-byte identical below the style block.

Post-pass verification: after writing the output file, count `<path>`, `<line>`, `<rect>`, `<circle>`, `<polygon>` elements in the original and in the output. Every original element tag count must be preserved (output ≥ original for each tag). If any count dropped, **fix it in place** - copy the missing elements back from the original into the output file. Do NOT revert the whole pass; just restore the missing geometry and keep the valid decorations.

If the user explicitly requests a geometry change ("widen the spine", "move the fork 20px east"), that's allowed and scoped to what they asked for, nothing else.

**Input**: SVG file(s) + intensity level (low / medium / high / absurd). Default: medium.

**MANDATORY**: This command follows the svg-infographics skill and workflow. All placement uses tools (`empty-space`, `geom align`), all colours use CSS classes with dark mode, all elements respect topology and grouping. Read `svg-designer/references/standards.md` principles - they apply here.

## Local directive file (user's project)

`./svg-infographics-beautify.md` at the CURRENT project root. LOCAL to the user's project. NOT shipped with the plugin. Stores the user's ANSWERS to the questionnaire and their custom standing-directive overrides, not the questionnaire itself.

- Questionnaire = static, defined in this command (below).
- User's answers = stored in the local directive file under "Resolved pattern".
- History = local append-only log in the directive file.

### Directive file template (generated on first run, minimal)

```markdown
# svg-infographics-beautify directive (project-local)

## Standing directive overrides (optional; defaults in the command)

(Leave empty to use shipped defaults; or list overrides here.)

## Creative brief (rewritten each run, free-text from user)

(empty)

## Resolved pattern (rewritten by the command each run)

(empty)

## History (append-only)

(empty)
```

### Shipped standing directives (apply unless overridden in local file)

1. **Additive only.** Never move/resize/restyle existing content. ALL beautify additions live in `<g id="beautify-decorations">` (background + shape decorations) and `<g id="beautify-icons">` (per-item glyphs). Nothing goes outside these two groups.
2. **Original untouched.** Output to `+` variant or user-chosen suffix.
3. **Colour in-family.** Teal → cyan/blue-teal OK; teal → green FORBIDDEN. Amber → ochre/copper OK; amber → red FORBIDDEN.
4. **Background strokes: thick + ghost-transparent.** Default `stroke-width: 2.5-4` with `opacity: 0.04-0.06`. Atmospheric, not line-art. Reduce stroke width only if it would visibly overpower content at 3x render; never exceed opacity 0.08. HARD CAP opacity 0.10.
5. **Icon per item** when questionnaire = `per-item`.
6. **Icons = multi-stroke glyphs.** Lucide/Feather style.
7. **Placement validated.** `empty-space --edges-only` before every decoration. `geom align` for role-shared.
8. **Validation HARD gates.** `validate` → 0 errors; `overlaps` container-overflow → 0; `contrast` → WCAG AA preserved.
9. **Dark-mode override per new class.**
10. **Doc comment.** `<!-- beautify: <level> ... -->` block near top.
11. **Size budget.** Low < 15KB. Medium < 50KB. High < 100KB.
12. **No PNG rasterisation.** SVG only.
13. **Push the hue harder.** Wide in-family hue range (up to ~25°), saturation + lightness part of the toolkit, per-card variants, focal stronger than neighbours.

### Questionnaire (MANDATORY every run — use `AskUserQuestion`)

Ask the user via the `AskUserQuestion` tool so they see the nice tab-based multiple-choice UI and can either click an option or chat their own answer. Ask in batches (up to 4 questions per `AskUserQuestion` call) to keep the UI compact. User answers override the defaults; "default" / empty answer uses the Default column.

**Batch 0 (FIRST, before the structured questions): free-text creative brief.**

Ask ONE open-ended question before any structured option: "Describe in your own words what this beautifying pass is about, the mood or theme you want, and anything else the agent should know." Use `AskUserQuestion` with the "free-text" input mode (the user types a paragraph, no multiple-choice options).

Capture the answer verbatim into the local directive file's **Creative brief** section (a new section above "Resolved pattern"). Sub-agents read the Creative brief and use it to pick domain-appropriate icons, bg textures, embroidery motifs, and to break ties when the structured answers leave room (e.g. the user said "cyberpunk HUD atmosphere" → embroidery theme = cyberpunk HUD, glow palette = dual with a cooler cool-end, etc).

If the user skips the free-text brief (empty answer), note in the brief "no user brief provided; infer from SVG content".

**Batch 1: scope + intensity**

| Question | Options | Default |
|----------|---------|---------|
| Target files | list of paths or glob | current article folder |
| Output suffix | `+` / `_live` / in-place | `+` |
| Intensity | `low` / `medium` / `high` / `absurd` | `medium` |

**Batch 2: structure dimensions**

| Question | Options | Default |
|----------|---------|---------|
| Colour variation | `off` / `subtle` / `moderate` / `free` | `moderate` |
| Shapes | `off` / `subtle` / `moderate` / `bold` | `moderate` |
| Icons mode | `per-item` / `per-header` / `off` | `per-item` |
| Icon library | `lucide` / `feather` / `custom` | `lucide` |

**Batch 3: decoration dimensions**

| Question | Options | Default |
|----------|---------|---------|
| Embroidery | `off` / `sparse` / `moderate` / `dense` | `moderate` |
| Abstract graphics | `off` / `sparse` / `moderate` / `rich` | `moderate` |
| Bg texture theme | `none` / `circuit` / `neural` / `topo` / `grid` / `organic` / `constellation` | match article domain |
| Bg opacity cap | `0.05` / `0.08` / `0.10` | `0.10` (directive #4 cap) |

**Batch 4: glow + validation**

| Question | Options | Default |
|----------|---------|---------|
| Glow mode | `off` / `focal-only` / `connectors+titles` / `everywhere` | `connectors+titles` |
| Glow palette | `cool` / `warm` / `dual` | `dual` |
| Validation strictness | `strict` / `strict-errors-only` | `strict-errors-only` |

**Batch 5: shader effects** (dimension 8 — opt-in)

| Question | Options | Default |
|----------|---------|---------|
| Shader mode | `off` / `subtle` / `moderate` / `wild` | `off` |
| Shader theme | `none` / `frosted-glass` / `water-ripple` / `iridescent` / `chromatic-aberration` / `embossed-metal` / `light-leak` / `bokeh` / `lens-flare` / `holographic-foil` / `paper-grain` / `auto` | `auto` (creative brief decides) |
| Print compat | `strip-on-export` / `preserve-effects` | `strip-on-export` |
| Animation | `off` / `subtle` | `off` |

If shader mode is `off` (default), skip Batch 5 entirely — no other Batch-5 questions are asked. When `shader mode != off`, the agent reads `skills/svg-designer/rules/shaders.md` and picks the SVG filter recipe(s) matching the chosen theme (or composes from the creative brief when `theme=auto`). When `print compat = strip-on-export`, beautify writes BOTH `<file>+.svg` (with filters) and `<file>+_print.svg` (filters stripped) per file. Animation default `off` because SMIL filter animations break print rasterisers entirely; `subtle` opts in to one-element water-ripple `seed` animation only.

The questionnaire now totals 18 questions across 5 batches. `AskUserQuestion` still batches at up to 4 per call.

If the user's initial command invocation volunteered any answers inline (e.g. "medium intensity, icons per item, circuit texture, water-ripple shader"), pre-fill those into the `AskUserQuestion` defaults so the user only confirms the rest.

Workflow:
1. If `./svg-infographics-beautify.md` missing: generate the minimal template above.
2. Read it. Apply any standing-directive overrides from the local file on top of the shipped defaults.
3. Walk the 18-question questionnaire (Batch 5 skipped when shader mode = off). Collect answers.
4. Rewrite the local file's "Resolved pattern" section with the answers.
5. Append history entry when done.
6. Sub-agents told: "Read `./svg-infographics-beautify.md` and apply the Resolved pattern."

Questionnaire asked every run. Resolved pattern rewrites. Directive overrides persist across runs.

## Before touching

1. Read target SVG completely
2. Read XML comment block - understand intent and theme
3. Identify theme swatch (CSS classes, palette, dark-mode overrides)
4. Reference `svg-infographics/skills/svg-designer/references/standards.md` for palette and placement rules
5. Run `empty-space --svg <file> --edges-only --tolerance 8 --min-area 100` to map available space

**Never break layout.** Enhancements = additive only.

## Eight dimensions

### 1. Colour variation

Be creative with colour per card / pillar / phase / tool-tile. Every repeating element gets its own hue variant on body + stroke + accent bar. Hue, saturation, lightness all in play. In-family only (teal → cyan/blue-teal OK, teal → green FORBIDDEN; amber → ochre/copper OK, amber → red FORBIDDEN). Rhythm, not coded categories.

Apply to BOTH fills AND strokes. Introduce `card-body-1 / -2 / -3 ...` classes with `@media (prefers-color-scheme: dark)` overrides.

| Level | Character |
|-------|-----------|
| **low** | Per-card opacity + tiny hue shifts on accents |
| **medium** | Per-card body + stroke + accent-bar hue variants. Focal card a stronger variant |
| **high** | Multi-stop gradients, several variants per card, colour-coded groups within family |
| **absurd** | Iridescent overlays, every element its own shade |

### 2. Shape and creative elements

Visual hierarchy, depth cues, compositional interest.

| Level | Character |
|-------|-----------|
| **low** | Gentle. Rounded corners, thin accent bars, slight size variation |
| **medium** | Layered. Card shadows for depth, decorative dividers, staggered elements |
| **high** | Bold. Overlapping edges, isometric hints, background plates, corner brackets |
| **absurd** | Experimental. Irregular polygons, translucent layers, perspective distortion |

### 3. Icons and symbols

Detailed multi-stroke iconic glyphs reinforcing element meaning. NOT simple silhouettes - each icon should be a small but complete drawing with visible internal detail.

| Level | Character |
|-------|-----------|
| **low** | Few. Geometric icons in key headers, monochrome |
| **medium** | Contextual. Icons per section, mixed stroke weights and fill/outline |
| **high** | Comprehensive. Unique icon per card, accent-coloured, badge icons at junctions |
| **absurd** | Pervasive. Icon patterns as backgrounds, floating particles, inline glyphs on labels |

### 4. Decorative embroidery

Futuristic flourishes, tech-line accents, ornamental detail. Choose a domain theme from the embroidery gallery that matches SVG content.

**Domain themes**: electronics/circuit, AI/neural, cyberpunk HUD, sci-fi abstract, decorative flourishes, science/math

**Organic circuitry**: faded circuit-trace paths that grow organically across the background - branching lines with node dots at intersections, like PCB traces or neural dendrites. Low opacity, placed in the background layer behind all content. Density scales with level.

| Level | Character |
|-------|-----------|
| **low** | Sparse. Corner marks on focal cards, dash accents. One or two faded organic circuit traces in background |
| **medium** | Textured. Tech-line fragments, angular bracket decorations, micro geometric patterns. Several organic circuit branches |
| **high** | Intricate. Pattern fills, alternating motifs, filigree corners. Organic circuitry network spanning background |
| **absurd** | Dense. Full textile overlays, woven backgrounds, themed border systems. Dense organic circuitry everywhere |

### 5. Abstract graphics

Non-representational shapes creating visual energy.

| Level | Character |
|-------|-----------|
| **low** | Minimal. Few accent particles in whitespace, one subtle background sweep |
| **medium** | Atmospheric. Scattered particles with varied opacity, background arcs, ring fragments |
| **high** | Energetic. Particle clouds, wave undulations, constellation lines, radial bursts |
| **absurd** | Dense. Particle fields, ribbon paths, voronoi outlines, orbital rings, fractal branching |

### 6. Background texture

Faded organic patterns behind content adding visual depth. Low opacity, background layer only.

**Texture themes** (ask user which fits):
- Circuit / PCB traces - branching paths with node dots at intersections
- Neural / dendritic - organic branching like neurons or root systems
- Geographic / topographic - contour lines, map-like undulations
- Grid / technical - faded engineering grid, coordinate markers
- Organic / natural - flowing curves, leaf veins, water ripples
- None - skip this dimension

| Level | Character |
|-------|-----------|
| **low** | One or two faded traces, very sparse |
| **medium** | Several branching paths, subtle network |
| **high** | Full background network, clearly visible texture |
| **absurd** | Dense texture covering entire background |

### 7. Glow effects

Luminous highlights via SVG filters. Apply selectively where it reinforces visual hierarchy.

| Level | Character |
|-------|-----------|
| **low** | Restrained. Glow on one or two focal elements only |
| **medium** | Warm. Dual-tone glow on connectors and key borders, title halos |
| **high** | Dramatic. Multi-layer glow, connectors and accent bars, background radial glow |
| **absurd** | Full bloom. Everything glows, neon double-glow, light leak edges |

### 8. Shader effects

Shader-style atmospheric treatments via native SVG filter primitives — no JavaScript, no Canvas. Ten canonical recipes cover frosted-glass cards, water-ripple distortion ("blurred by water"), iridescent oil-slick sheen, chromatic-aberration lens fringe, embossed-metal bumpmaps, light-leak corner glow, bokeh background dots, anamorphic lens-flare streaks, holographic-foil sheen, and paper-grain canvas texture. Pick from the recipe file - sub-agents paste the chosen `<defs>` block verbatim then apply `filter="url(#name)"` on the target element. Do NOT invent filter chains - noise-based effects need specific parameter ranges to look right.

| Level | Character |
|-------|-----------|
| **low** | One effect on one focal element (frosted-glass on title card) |
| **medium** | 2-3 effects, focal + decorative (frosted cards + paper-grain overlay) |
| **high** | Multi-effect (frosted cards + water-ripple background + iridescent accents) |
| **absurd** | Everything (chromatic-aberration titles + water-ripple background + holographic cards + light-leak corners + bokeh + lens-flare) |

**Default OFF.** Most infographics don't need shader effects - they add file size and break print rasterisers (Word / LibreOffice drop SVG filters entirely). Opt-in via questionnaire Batch 5. When `shader mode != off` AND `print compat = strip-on-export` (the default), beautify produces TWO files: `<file>+.svg` with filters and `<file>+_print.svg` with all `<filter>` defs and `filter=` attributes stripped. The article skill picks the print variant for Word delivery, the live variant for web.

**Recipe file**: `skills/svg-designer/rules/shaders.md` — 10 canonical SVG filter chains with copy-paste-ready `<defs>` blocks, level guidance, anti-patterns, and 5 worked combination examples (underwater report card, premium proposal, vintage photo article, blueprint diagram, holographic banner). Read this BEFORE writing any filter.

**Compatible combinations** (2-3 effects compose well; >3 stops rendering correctly):
- water-ripple + frosted-glass + bokeh = "submerged" theme
- holographic-foil + paper-grain + chromatic-aberration = "premium proposal" theme
- light-leak + paper-grain + embossed-metal = "vintage photo" theme

## Documentation comment

**MANDATORY**: append an `<!-- beautify -->` XML comment block inside the SVG (after the existing file description comment) documenting what was done:

```xml
<!-- beautify: medium
  colour: 4 derived shades, gradient fills on section headers
  shapes: card shadows at 0.06 opacity, accent bars 3px
  icons: 6 contextual icons (grid, connector, palette, align, check, chart)
  embroidery: dot backgrounds 8px spacing, decorative end-caps on dividers
  abstract: 15 accent particles, 2 background arcs
  glow: cool accent-1 stdDev=3 on connectors, warm accent-2 stdDev=2 on focal cards
  shaders: frosted-glass on card bodies, paper-grain overlay alpha 0.05 (print variant emitted as `<file>+_print.svg`)
-->
```

This comment allows future agents to understand what decorations were applied, at what level, and whether to preserve or replace them during rework.

## Rules

1. `<defs>` block after `<style>` for filters, gradients, patterns
2. Every new colour/gradient MUST have `@media (prefers-color-scheme: dark)` override
3. Decorations render BELOW content in DOM
4. Filter regions tight (`filterUnits="userSpaceOnUse"`). Max 3 blur passes per chain
5. Size targets: <50KB medium, <100KB high. Absurd unlimited
6. Text stays legible. Decoration interferes with contrast = reduce or remove
7. Run `overlaps` + `contrast` validators after. Broken validation = broken embroidery
8. **Shader effects require print-strip**. When `shader mode != off` AND `print compat = strip-on-export`, produce TWO files per source: `<file>+.svg` (filters applied) AND `<file>+_print.svg` (every `<filter>` def removed from `<defs>` and every `filter="url(#...)"` attribute stripped from elements). The article skill picks the print variant for Word delivery, the live variant for web. When `print compat = preserve-effects`, only the live variant is produced and the user accepts that Word will render filters flat (i.e. without effect)
9. **Shader perf budget**. Max 3 filter primitives per chain. Max 4 distinct named filters per SVG. `filterUnits="userSpaceOnUse"` MANDATORY with explicit `x` / `y` / `width` / `height` regions — never `objectBoundingBox` on shader filters, the region calculation gets the noise-based effects wrong and produces invisible output. SMIL animation off by default; opt-in via Batch 5 `animation: subtle` and only for ONE element

## Workflow

### Step 1: Read directive file

Read `svg-infographics-beautify.md` FULLY. Standing-directive overrides, the creative brief, the resolved-pattern slot this run will populate, and the history live there; the questionnaire and the dimension reference are in this command.

### Step 2: Read target SVG + theme

For each file passed in arguments, read the SVG completely. Parse the XML comment block to absorb intent and theme. Identify the CSS theme classes, the palette, and the dark-mode overrides.

### Step 3: Run the mandatory questionnaire

Walk the user through all 18 questions in the Questionnaire section above (Batch 5 skipped when shader mode = off). Use `AskUserQuestion` if available, otherwise present them as a numbered list and wait for all answers. Do NOT shortcut, do NOT use previous runs' answers. Every run re-asks. This is the guard against silent drift.

Defaults are allowed - the user may answer "default" to accept the Default column for any question. "Skip" marks a dimension as off for this run. Custom values are copied verbatim.

If the user volunteered any of these answers inline in their command invocation (e.g. they said "medium intensity, icons per item, circuit texture"), pre-fill those answers in the questionnaire and only ask about the remaining ones. But still SHOW the full questionnaire so the user sees every decision being made.

### Step 4: Rewrite the Resolved pattern

After all 18 answers are collected, rewrite the **Resolved pattern** section in `svg-infographics-beautify.md` with the current run's concrete choices. Timestamp the update. This becomes the single source of truth that sub-agents will read.

### Step 5: Apply (delegated to sub-agents for multi-file runs)

For a single file: apply the eight dimensions per the resolved pattern directly. One task per dimension.

For multiple files: dispatch one builder per file (or per 2 files) - see *Dispatch the builder* in `/svg-infographics:create` for both call shapes and the agent-type caveat. Every builder's prompt starts with:

> Read `svg-infographics-beautify.md` first. Follow every standing directive and the resolved pattern in that file.

Then list the specific file(s) and any per-file domain targeting (icon picks, texture theme) that vary between files.

**Placement rules (MANDATORY)**:

1. **Empty-space first**: before placing ANY element (icon, flourish, particle), run `empty-space --svg <file> --edges-only --tolerance 8 --min-area 100` to find safe zones. For placement inside a specific card, add `--container-id <card-id>`. Only place within detected free regions
2. **Topology alignment**: elements sharing a role across containers (e.g. icons across cards, corner marks across sections) MUST be aligned via `geom align`. Icons in a row of cards share the same y. Corner marks at the same relative position in each card
3. **Group decorations**: all beautify elements go into a dedicated `<g id="beautify-decorations">` group. Icons into `<g id="beautify-icons">`. Maintain the five-layer structure
4. **Overlap validation**: run `overlaps` checker after placement. Any decoration that violates padding/margin/spacing rules gets repositioned or removed

### Step 6: Verify

For each modified file:
1. `svg-infographics validate <file>` - zero XML errors.
2. `svg-infographics overlaps --svg <file>` - zero container-overflow warnings (text escaping parent = hard fail per validation skill).
3. `svg-infographics contrast --svg <file>` - WCAG AA preserved.
4. Fix or revert any hard-fail violation before declaring done.

**Do NOT rasterise to PNG.** The `medium-article` skill was updated to embed SVGs directly - per-SVG PNGs are no longer produced for article assets.

### Step 7: Log the run

Append a one-line history entry to the directive file's History section:

```
# <YYYY-MM-DD HH:MM> - <files> - <level> - <OK | FAIL: reason>
```

### Step 8: Report

Report to the user:
- Files produced (paths with + suffix or equivalent)
- Per-dimension summary (what was added)
- Validator results
- Final file sizes
