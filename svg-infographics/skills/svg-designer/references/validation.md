# SVG Validation and Verification

Twelve tools shipped in `stellars-claude-code-plugins` pip package. Install once, use via `svg-infographics` CLI. No optional extras.

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



```bash
pip install stellars-claude-code-plugins
svg-infographics --help
```

Task tracking MANDATORY: TaskCreate/TaskUpdate when running validation. One task per checker run + fix cycle.

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
5. **XML malformation** — broken parse (e.g. `--` in comment). Hard fail

### Justifying a hard fail

Intentional hard fail? Add XML comment adjacent documenting reason:

```xml
<!-- Hard-fail justified: "4.5:1" label sits ON the WCAG threshold line by design,
     communicating the boundary visually. Not a layout bug. -->
<line class="target-quad-stroke" x1="430" y1="246" x2="430" y2="294"/>
<text class="accent-2 metric-unit" x="432" y="248">4.5:1</text>
```

No justification = no ship.

## Default-Bad rule (fail-first)

All violations assumed real defects until individually defended. Resolve each:

- **Fixed** — repositioned, re-run confirms
- **Accepted** — specific reason not a defect
- **Checker limitation** — manual computation proves compliance

Bulk dismissals prohibited. Examine every finding individually.

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

CSS compliance: all colours CSS-controlled, no inline fills on text, no forbidden colours (`#000000`/`#ffffff`), dark-mode overrides present.

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

See `standards.md` "Arrow Construction" for full modes + flags.

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

- [ ] `validate` — XML + baseline clean
- [ ] `overlaps` — all violations reviewed
- [ ] `contrast` — zero FAIL in production
- [ ] `alignment` — topology passes
- [ ] `connectors` — no dangling / zero-length
- [ ] `css` — no inline fills, no forbidden colours, dark mode verified
- [ ] `collide` — no connector crossings (when manifold present)
- [ ] Browser visual check via Playwright

## Multi-agent validation workflow

1. **Generator** creates/edits SVG
2. **Checker agents** run all validators in parallel (3+ concurrent)
3. **Generator** classifies findings, writes `verification_checklist.md`
4. **Critic agent** (separate context, fail-first) reviews every classification
5. **Fixer** addresses rejections, re-runs checkers
6. **Verifier** confirms with Playwright screenshots (light + dark)

## Browser visual verification

Playwright blocks `file://` URLs. Serve via HTTP:

1. `python3 -m http.server 8768` from images directory
2. HTML wrapper: `<body style="background:#1e1e1e"><img src="http://localhost:8768/file.svg" width="900"></body>`
3. Serve wrapper on different port, navigate Playwright
4. Screenshot dark + light modes
5. Check: text overlap, contrast failures, bar misalignment, asymmetric padding

## Generative failure investigation

Generate `verification_checklist.md` per failure:

```markdown
- [ ] `<filename>` | `"<text>"` | <ratio/overlap%> | <mode>
  - **Root cause**: <description>
  - **Fix**: <specific action>
```
