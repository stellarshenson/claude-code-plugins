# SVG Validation and Verification

Twelve tools shipped in `stellars-claude-code-plugins` pip package. Install once, use via `svg-infographics` CLI. No optional extras.

The CLI is the deterministic floor of the validation split - construction, geometry, colour arithmetic, roster honesty, and nothing more. Legibility, semantic fit and aesthetic quality are generative judgments made by the validator process; the full split lives in `docs/acc-crit-claude-code-plugins.md` (repo root). A CLI PASS alone is never a ship decision.

## Stop-and-think warning-ack gate (MANDATORY)

Every **producer** tool in svg-tools (generates an artefact - SVG snippet, coordinates, layout, render) blocks its primary output whenever any warning fires. Output resumes only after the caller acknowledges each warning with a deterministic token and terse reasoning. This is not optional and there is no bulk override.

**Gate matrix** (Release D):

| Tool | Gated? | Warnings blocked |
|---|---|---|
| `calc_connector` (straight / L / L-chamfer / spline / manifold) | YES | direction omission, L-routing underconstrained, stem-length, stem/head ratio, manifold spine-offset, T-junction hints, FLOW REVERSED, TWIST, soft-cap controls |
| `charts` | YES | palette contrast findings (light + dark modes vs background) |
| `drawio_shapes` | YES | indexer warnings (file not found, parse errors, unrecognised root tag) |
| `empty-space` | YES | tolerance-below-20px warning |
| `finalize` | YES | every HARD + SOFT finding surfaced from sub-validators |
| `check_*` validators (overlaps, contrast, alignment, connectors, css, svg_valid) | NO | findings are the primary output; exit code signals severity |
| `primitives`, `place`, `text-to-path`, `gen_backgrounds` | NO | only emit hard-error messages before `sys.exit(1)` or pure-info lines |

**Contract** (identical across every gated tool):

1. Run the tool. Any warning makes it exit 2 with a `BLOCKED` block listing one deterministic token per warning.
2. Token format: `W-xxxxxxxx` (8 hex chars), computed as `sha256(canonical_argv, warning_text)[:8]`. Same input + same warning text = same token across reruns.
3. Fix the input (preferred) OR rerun with `--ack-warning TOKEN=reason` once per warning. No bulk override - one flag per warning, one reason per warning.
4. Acked: tool prints an audit summary of `[TOKEN] warning / reason: ...` pairs on stderr, then proceeds to output.
5. Input or warning text changes -> token changes -> a stale ack no longer matches -> gate blocks again. You cannot silently pass a different defect by reusing an old ack.

**Reasoning MUST be terse.** One short clause that names the constraint. Good: `'card column locked'`, `'T-junction middle, desired visual'`, `'palette anchored on brand spec'`. Bad: `'known issue'`, `'I know what I'm doing'`, `'see ticket'`, `'geometry constrained'` (too vague - which constraint?). Bad reasons fail review; a stack of vague acks is a signal the input needs rework.

**Fixing the input is ALWAYS preferred over acking.** The gate is there to force a deliberate choice, not to be bypassed. If every build ends with a long `--ack-warning` list, the layout or declaration is wrong - rework it instead.

**Token discovery workflow** (the common path):

```bash
# 1. Build naturally; gate fires with tokens listed
svg-infographics connector --mode manifold --starts "[...]" ...
# ...
# BLOCKED: 3 unacknowledged warning(s).
#   [W-11a21a1f]  CONSIDER: starts strand 2 at (560,205) is 5.0px off spine...
#   [W-aca14b8c]  CONSIDER (snap rule): odd starts (3); middle off-axis...
#   [W-03c26fa7]  CONSIDER (snap rule): end stem 8.0px (< stem_min=20.0)...

# 2. Decide per-warning. Rerun with per-ack flags (terse reasons).
svg-infographics connector --mode manifold --starts "[...]" ... \
    --ack-warning W-11a21a1f='card stroke width, snapping would collide' \
    --ack-warning W-aca14b8c='spine locked to target geometry' \
    --ack-warning W-03c26fa7='hex edge fixed; short stem accepted'
# SVG output released; stderr shows audit trail.
```

Install and version check: the toolchain gate in `SKILL.md`. A green `--help` proves nothing; only the version compare does.

Task tracking MANDATORY: TaskCreate/TaskUpdate when running validation. One task per checker run + fix cycle.

## The checklist (`finalize --checklist`)

Findings tell you what is wrong. They cannot tell you what was never looked at, and an aspect nobody checks reads exactly like one that passed - that is how a 17-file deck shipped with a dark-mode block nobody had measured for whether it changed anything.

`finalize --checklist` prints a per-aspect roster on **stderr**, one block per file, ahead of the findings. The findings go to stderr too while the ack gate is holding output, so `2>/dev/null` discards both. The `--json` report is on stdout, but it appears only once every warning is acked - until then the gate withholds it and exits 2, so a bare `| jq` gets nothing.

Four states, and the differences between them are the whole point:

- **PASS** - the layer ran, the subject exists in the file, nothing was found
- **FAIL** - a finding carries this row's rule, counted per tier in the row note (`4 HARD`, or `1 HARD, 3 SOFT` when mixed)
- **NA** - the layer ran and the file holds nothing to judge; the note names the missing input. A row is gated on *every* input its checker consumes, so `endpoints snap to edges` reads `NA (no card-rule <rect>)` rather than passing on a card-relative property with nothing to relate to. Each note names the RULE the layer applies, never the contents of the file - a note that claimed "no card `<rect>`s" was falsified by any file full of small ones. The three that need their rule spelled out:
  - `card-rule <rect>` - a `<rect>` whose class contains `card` or `box`, **or** which exceeds 50x50 in *both* axes. Two 90x40 node rects match neither, so the connector layer has no edge to snap to and says so
  - `canvas-covering <rect>` - a `<rect>` covering at least 92% of the canvas from within 4% of its origin, opaque once `fill-opacity`, `opacity`, any ancestor `opacity`, `rgba()` alpha and a gradient's stops are all accounted for (over 0.1), and none of: a `slot` placeholder, `data-placeholder="true"`, a `filter` (the house `paper-grain` overlay is an opaque full-bleed rect painted last on purpose), a `<pattern>` fill (the scaffold's guide grid), or anything inside `<defs>`/`<symbol>`/`<marker>`/`<pattern>`/`<mask>`/`<clipPath>`, whose contents paint where they are REFERENCED rather than in place. The LAST such rect in document order wins - that is the one on top. **Rects only**: a ground drawn as a `<path>` reads NA rather than being guessed at, because a path's `d` cannot be boxed reliably without walking every command
  - `light/dark pair to compare` - one selector the light sheet paints AND the dark block redeclares, with both values readable as colours. A dark block that redeclares only selectors the light sheet never paints has nothing to measure
- **SKIP** - the layer produced no verdict. Six causes, and the note distinguishes them: a layer that never executed because an earlier one aborted the pipeline (`not run` - malformed XML and a crashed parser both do this), a crashed checker that reports one diagnostic and nothing else (`checker crashed`, with the exception printed under the block), a probe that could not read the file well enough to say whether the row even has a subject (`inventory unavailable` - which is not the same as having none), geometry the connector parser declined to read (`connectors the parser skipped` - named connectors or arrowheads under a `transform`; the arrows exist, this layer cannot see them, and the overlaps layer names them by coordinate), the renderer failing on this file (`renderer unavailable` - per file, so a sibling's bad XML no longer costs this file its layer), and `--no-visual` switching the render layer off

Rows sit in the group they belong to, with one exception: `other <layer> findings` catch-alls live in a trailing `other` group, so a catch-all can never render underneath a named `PASS` row that contradicts it.

```
CHECKLIST  01-four-situations.svg
  structure
    [PASS] xml well-formed
    [PASS] no element overlaps
  theme
    [PASS] dark block present
    ...
  contrast
    [FAIL] text meets WCAG AA  (2 HARD)
  connectors
    [PASS] no zero-length segments
    [ NA ] endpoints snap to edges  (no card-rule <rect>)
    ...
    [FAIL] head continues its stroke  (4 HARD)
    [PASS] labels clear the route
    [PASS] routes do not cross
  layout
    [FAIL] alignment and rhythm  (3 SOFT)
  render
    [SKIP] rendered geometry  (--no-visual)
  other
    [FAIL] other connectors findings  (1 SOFT)

  24 aspects: 15 PASS  4 FAIL  4 NA  1 SKIP
  4 failing rows: 2 with hard findings, 2 soft-only
```

(`...` marks rows elided here; the real block always prints all of them. A block with a `SKIP` the operator did not ask for gains one more line naming the cause, e.g. `7 unjudged (7 checker crashed) - these are not passes`.)

Gating several files at once adds a final `deck` block for the cross-file consistency checks, which belong to no single file and so appear in no per-file roster. It carries the same four states: `NA (no cards to compare across files)` when no file holds an element the checker reads as a card, since both of its comparisons then have zero subjects and an empty result is not agreement. Its findings are classed `SOFT-CONSISTENCY`, so one `--ack-class SOFT-CONSISTENCY=<reason>` covers the block.

A `SKIP` you did not ask for is not a pass and not a clean bill - it is the absence of a verdict, and on a file that should have exercised that layer it is the first thing to chase. An `other <layer> findings` row catches anything no named row claims, so the roster can never be quieter than the findings printed beneath it.

The gate's verdict line answers to the roster on every branch. Zero findings or only-acked SOFT findings beside an unasked SKIP prints `NOT VERIFIED - ... N not judged (<count> <cause>)` and exits 1; the HARD path prints the same NOT VERIFIED lines after the batch-fix protocol, so the editing pass is planned against the unjudged aspects too instead of meeting them a re-run later. A fully judged file on an acked run prints `OK - findings acked, all aspects judged.` - uniform and mixed runs alike. A SKIP the operator asked for (`--no-visual`) stays shippable with exit 0. `--json` carries the per-file `skipped` map of aspect to cause plus `totals` on both branches; a cause starting with `--` names an asked-for skip, and `totals` of `{"hard": 0, "soft": 0}` with exit 1 is a reachable state (findings clean, aspects unjudged), so a consumer reads the exit code, not totals alone.

## Failure severity ladder

Three severities. Only HARD FAIL blocks delivery.

| Severity | Prefix | Meaning | Ship rule |
|---|---|---|---|
| HARD FAIL | `WARNING:` / `ERROR:` | Broken geometry / illegal state. Requires written justification in SVG comment to ship | BLOCK by default |
| SOFT WARNING | `CONSIDER (snap rule):` | Aesthetic degradation, avoidable with small adjustment | Fix when convenient |
| HINT | `HINT:` | Rule auto-applied, FYI (e.g. T-junction chamfer dropped) | No action |

### Hard-fail classes

Geometry defects where rendered output is visually broken:

1. **Text-on-edge overlap** — text glyph bbox crosses a stroke (axis, card border, divider). Unreadable where crossed. Hard fail unless justified
2. **Edge-on-edge overlap** — two strokes crossing wrongly (axis through card border, connector through unrelated divider). Routing bug. Hard fail unless justified
3. **Text-outside-container** — text extends past parent rectangle. Layout overflow. Hard fail
4. **Connector-through-content** — connector mid-segment crosses content group. Hard fail
5. **Arrowhead off its own line** (`[arrowhead-axis]`) — head axis more than 10 degrees off the chord from its connector's endpoint to the tip. Reads as a bent flag rather than an arrow. Hard fail
6. **XML malformation** — broken parse (e.g. `--` in comment). Hard fail

### Justifying a hard fail

Intentional hard fail? Add XML comment adjacent documenting reason:

```xml
<!-- Hard-fail justified: "4.5:1" label sits ON the WCAG threshold line by design,
     communicating the boundary visually. Not a layout bug. -->
<line class="target-quad-stroke" x1="430" y1="246" x2="430" y2="294"/>
<text class="accent-2 metric-unit" x="432" y="248">4.5:1</text>
```

No justification = no ship.

## Default-Bad rule (HARD findings only)

HARD findings are assumed real defects until individually defended. Resolve each:

- **Fixed** — repositioned, re-run confirms
- **Accepted** — specific reason not a defect
- **Checker limitation** — manual computation proves compliance

SOFT findings (alignment, css, collide, connector style nudges) do NOT need
per-finding defence: fix what is cheap in the batch-fix pass, then
acknowledge a whole remaining layer with one reasoned
`--ack-class SOFT-<LAYER>='reason'` on `finalize`. Per-token acks stay
mandatory for HARD findings - a class ack never silences a HARD finding.

Why the split: forcing an individual written defence of 50+ stylistic
notices is what trained agents to acknowledge reflexively - and a reflexive
ack is how a REAL flagged overlap shipped to a client deck.

## Tool: validate

XML well-formedness + structural sanity + geometry preservation.

```bash
svg-infographics validate <file>                            # XML + viewBox + empty paths
svg-infographics validate <file> --baseline <original>     # + geometry signature compare (beautify)
```

Catches: unbalanced tags, `--` in comments (#1 cause of broken SVGs), stray ampersands, missing viewBox, empty `<path d>`, removed geometry between original + modified.

Exit 0 = clean. 1 = errors.

## Tool: overlaps

Parses all visual elements, computes bboxes (text with font metrics, paths, rotated arrows, circles, rects), reports ALL overlaps.

Classifications: `violation` (fix), `sibling` (adjacent), `label-on-fill` (intentional), `contained` (child in parent).

```bash
svg-infographics overlaps --svg <file>
svg-infographics overlaps --svg <file> --ignore "21x23,24x25"   # skip reviewed pairs
svg-infographics overlaps --svg <file> --inject-bounds           # bbox overlay
svg-infographics overlaps --svg <file> --strip-bounds            # remove overlay
```

Also checks **container overflow** (text escaping parent rect, including under compound transforms) and **callout cross-collisions** (leader-vs-text, leader-vs-leader, text-vs-text across `callout-*` groups).

Verification cycle: `--strip-bounds` → fix → run → `--inject-bounds` → visual check → repeat → `--strip-bounds` (final, mandatory before ship).

## Tool: contrast

WCAG 2.1 contrast. Resolves CSS classes, alpha-blends backgrounds, checks AA (4.5:1 normal, 3.0:1 large) + AAA.

```bash
svg-infographics contrast --svg <file>                     # AA default
svg-infographics contrast --svg <file> --level AAA         # stricter
svg-infographics contrast --svg <file> --show-all          # include passing
svg-infographics contrast --svg <file> --dark-bg "#272b31"
```

Checks text AND objects (cards too faint) in both light + dark modes.

## Tool: alignment

Grid snapping, vertical rhythm, x-alignment, rect alignment, legend consistency, topology.

```bash
svg-infographics alignment --svg <file>                    # 5px grid default
svg-infographics alignment --svg <file> --grid 10 --tolerance 1
```

## Tool: connectors

Connector quality: zero-length segments, edge-snap, L-routing, label clearance, dangling endpoints.

```bash
svg-infographics connectors --svg <file>
```

## Tool: css

CSS compliance: all colours CSS-controlled, no inline fills on text, no forbidden colours (`#000000`/`#ffffff`), dark-mode overrides present *and effective*.

Three theme rules, and two of them go past presence to measurement - a dark block that exists and does nothing passes every presence check:

- `inert-dark-mode` - most overrides move luminance less than 32/255, so the file renders the same in both themes. A few deliberately theme-invariant colours (text on an accent that does not itself invert) are fine; a majority of them is not
- `unthemed-background` - the ground fails either half of the inversion test: its dark value must move at least 96/255 in brightness **and** land below mid-grey. `#d0d0d0 → #787878` crosses mid-grey but only moves 88, so it still fails. The two values are read through the full cascade - id beats class beats element beats presentation attribute, equal specificity decided by source order - and the dark value is the light winner *unless a dark declaration of equal-or-higher specificity displaces it*, because `@media` adds declarations rather than replacing the sheet. So `#bg-plate { fill: light }` with `.plate { fill: dark }` in the dark block does NOT invert: the id rule keeps winning under the query. A plate painted by a presentation `fill` (which no media query can reach, whatever its value - including `url(#gradient)`) measures identical in both themes and fails here, with the remedy naming the attribute
- `missing-dark-block` - no `@media (prefers-color-scheme: dark)` block at all
- `missing-dark-override` - a rule paints (`fill` or `stroke` set to something other than `none`/`transparent`, above the 0.1 composite threshold) and the dark block either never names it or names it without repainting that property. Judged per property and for **every selector shape** - `text { fill: … }` and `#plate { fill: … }` go unthemed exactly as a class does
- `forbidden-color` - `#000`/`#fff` in any rule, any presentation attribute, or any inline `style="fill:…"`. `<mask>` and `<clipPath>` contents are exempt (white there is an alpha value); `<defs>` is **not** - a `<marker>`, `<symbol>`, `<pattern>` or gradient stop inside it paints wherever it is referenced

```bash
svg-infographics css --svg <file>                          # check
svg-infographics css --svg <file> --strict                 # warnings as errors
```

## Tool: collide

Pairwise collision over a set of connectors. Tolerance-aware (buffered shapely intersection). Reports crossing / near-miss / touching with coords + min distance.

```bash
svg-infographics collide --svg <file>
```

## Tool: connector (generative, not a validator)

**Every arrow / routed line from this tool. Hand-coded `<path d="M…">` = hard FAIL.** Computes angle, stem coordinates, arrowhead points, SVG snippet.

**Project standard: `--standoff 2`** on every call. Tool default 1px is too tight for production — pass `2` explicitly unless layout demands otherwise.

```bash
# Straight
svg-infographics connector --from 520,55 --to 590,135 --standoff 2 --arrow end

# With cutout (splits into two segments)
svg-infographics connector --from 353,122 --to 200,84 --standoff 2 --cutout 236,90,78,13

# L-route between rects (CANONICAL)
svg-infographics connector --mode l-chamfer \
  --src-rect "70,90,60,40"  --start-dir E \
  --tgt-rect "370,160,60,40" --end-dir S \
  --chamfer 4 --standoff 2 --arrow end
```

See `rules/connector.md` "Connector tool reference" for full modes + flags.

## Tool: primitives (generative)

Exact anchors for precise placement.

```bash
# 2D
svg-infographics primitives rect --x 20 --y 30 --width 200 --height 100 --radius 3
svg-infographics primitives circle --cx 400 --cy 200 --r 50
svg-infographics primitives hexagon --cx 300 --cy 200 --r 40
svg-infographics primitives diamond --cx 200 --cy 100 --width 80 --height 60
svg-infographics primitives arc --cx 200 --cy 200 --r 80 --start 0 --end 90

# 3D isometric
svg-infographics primitives cube --x 50 --y 50 --width 100 --height 80 --mode fill
svg-infographics primitives cylinder --cx 200 --cy 50 --rx 60 --ry 20 --height 100
svg-infographics primitives sphere --cx 300 --cy 200 --r 50

# Curves + layout
svg-infographics primitives spline --points "80,200 150,80 300,120 450,60" --samples 200
svg-infographics primitives axis --origin 80,200 --length 300 --axes xyz --ticks 5
```

Each returns named anchors (center, top-left, vertices, tips) for precise positioning.

## Tool: text-to-path (ON REQUEST ONLY)

Converts text rendered in TTF/OTF font into SVG `<path>` outlines. **Do NOT run by default.** Use only when user explicitly asks for:

- Custom font without renderer having it installed
- Print/hand-off SVGs identical across renderers
- Headline/label needing deterministic bbox without `textLength` distortion
- Branding marks (logos, wordmarks) that must never reflow

Tradeoffs caller accepts: no longer editable as text, file size 5-20× larger, `.ttf` / `.otf` required.

```bash
svg-infographics text-to-path --text "Hello" --font ./Inter.ttf --size 24 --x 100 --y 200

# Centered, fit to width
svg-infographics text-to-path --text "Quarterly Results" \
  --font ./InterDisplay-SemiBold.ttf --size 32 \
  --x 450 --y 80 --anchor middle --fit-width 300 --fill "#1e3a5f"

# CSS class instead of inline fill
svg-infographics text-to-path --text "TITLE" --font ./Inter.ttf \
  --size 28 --x 20 --y 60 --class headline-fg

# JSON output for scripted composition
svg-infographics text-to-path --text "Hi" --font ./Inter.ttf --size 24 --json
```

Prints `<path>` on stdout, bbox + scale on stderr.

`--x`/`--y` are baseline origin. `--anchor` mirrors `text-anchor` (`start`|`middle`|`end`). `--fit-width` uniformly scales path down (aspect preserved) when natural advance exceeds width.

## Pre-delivery checklist

### Structure

- [ ] File description comment before `<svg>`
- [ ] Transparent background
- [ ] ViewBox set, no `width`/`height` on `<svg>`
- [ ] `<style>` with `@media (prefers-color-scheme: dark)`
- [ ] Guide grid present
- [ ] Grid comment after `<style>`
- [ ] No `#000000`, no `#ffffff`

### Text

- [ ] All `<text>` use CSS classes, no inline `fill=`
- [ ] No opacity on text
- [ ] System fonts, 7px minimum
- [ ] Text within parent shapes
- [ ] Unicode glyphs only (`→` not `->`, `…` not `...`, `×` not `x`)

### Layout

- [ ] Z-order: background → nodes → connectors → content → callouts
- [ ] Card fills at 0.04-0.08 opacity
- [ ] 10px+ padding from edges
- [ ] Uniform spacing, consistent alignment
- [ ] All children within parent boundaries

### Automated

Do not re-list the machine-checkable rows by hand - `finalize --checklist` owns them, and a second copy here drifts out of step with the checkers. Run it and read the roster:

- [ ] `finalize --checklist` — every row `PASS` or `NA`; no `FAIL`, and no `SKIP` you did not ask for
- [ ] `render-png --mode both` readback - one pass, both modes; no browser or screenshot loops (`workflow.md` Phase 6)

The manual boxes above stay manual: they cover intent (transparent background, guide grid, z-order, unicode glyphs, 7px minimum, card fill opacity) that no checker decides.

## Troubleshooting (moved from standards.md)

- **Text invisible in dark mode**: use CSS class, not inline fill
- **Overlapping elements**: re-verify against grid comment, run `overlaps`
- **Arrows wrong direction**: rerun `connector` with correct `--from`/`--to`; paste `trimmed_path_d` and arrowhead polygons
- **Colours off-theme**: check every hex against swatch, run `contrast`
- **CSS compliance errors**: run `css --svg file.svg`
- **Imprecise coordinates**: use `primitives <shape>` for exact anchors
- **Wrong size in markdown**: remove `width`/`height` from `<svg>`, use `viewBox` only
