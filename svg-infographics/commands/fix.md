---
description: Fix issues in SVG infographics. Argument describes what to fix (layout / style / contrast / connectors / all). Spawns svg-designer agent via fork context. Triggers - "fix svg", "fix layout", "fix style", "fix contrast", "fix connectors", "fix infographic".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate]
argument-hint: "SVG file path + optional intent (e.g. 'docs/fig.svg overlaps' or 'docs/*.svg style')"
---

# Fix SVG

Diagnose and fix issues in existing SVG infographics. Argument is free-text — user describes the file and what to fix. Command classifies the intent and spawns the `svg-designer` agent via fork context so the user can continue working while the agent fixes.

## Argument parsing

Extract from the argument:

- **File(s)** — explicit path, glob, or directory
- **Intent** — what to fix. Categories below. If user says "fix svg" without intent, run full diagnostics and fix everything flagged

Common intents:

| Intent | What it fixes |
|--------|---------------|
| `layout` / `overlaps` / `alignment` | Element overlaps, alignment drift, spacing violations, grid snap, card padding, rhythm |
| `style` / `css` / `dark mode` | Inline fills on text, missing dark-mode overrides, forbidden colours (`#000000`/`#ffffff`), CSS class compliance |
| `contrast` / `wcag` | WCAG 2.1 failures, text contrast, object contrast vs background |
| `connectors` / `arrows` / `routing` | Dead ends, edge-snap issues, missing chamfers, hand-coded paths, `--standoff` drift |
| `geometry` / `baseline` | Geometry preservation vs original (beautify guard), `--baseline` compare |
| `all` / unspecified | Run every checker, classify findings, apply fixes across all categories |

## Task tracking

MANDATORY: create tasks for diagnosis, each fix category, and validation re-run. Spawned agent owns its own task list.

## Steps

1. **Classify intent** from argument. If ambiguous, ask user one clarifying question via `AskUserQuestion` before spawning
2. **Spawn `svg-designer` agent** via `Agent(subagent_type="svg-designer", prompt="<intent + file + instructions>")`. Fork context runs out-of-band; user keeps working
3. **Agent follows the fix workflow** (see below). On completion, reports findings + fixes back to parent

## Agent fix workflow

The spawned agent runs this workflow. Parent command does not execute these steps directly.

### Layout / overlaps / alignment intent

1. Read SVG + grid comment to understand intended layout
2. Run diagnostics:
   - `svg-infographics overlaps --svg <file>` — bounding box violations + container overflow
   - `svg-infographics alignment --svg <file>` — grid snap, rhythm, topology
   - `svg-infographics connectors --svg <file>` — connector quality
3. Apply fixes directly:
   - Reposition overlapping elements using grid coordinates
   - Fix vertical rhythm (consistent y-increments)
   - Fix horizontal alignment (shared x values)
   - Adjust card padding (10px+ from edges)
   - Recalculate arrow geometry with `svg-infographics connector --standoff 2`
   - Use `svg-infographics primitives <shape>` for exact anchor coordinates when repositioning
   - Update grid comment to match actual positions
4. Re-run validation to confirm resolution
5. Optional: `svg-infographics overlaps --inject-bounds` for visual bbox overlay, then `--strip-bounds` after verification
6. Report: fixes applied, before/after violation counts

### Style / css / dark mode intent

1. Identify target: read SVG file(s) to fix
2. Run diagnostics (one task per checker):
   - `svg-infographics css --svg <file>` — inline fills, forbidden colours, missing dark mode
   - `svg-infographics contrast --svg <file> --show-all` — FAIL + warn entries
   - `svg-infographics overlaps --svg <file>` — spacing violations
   - `svg-infographics alignment --svg <file>` — grid snap issues
3. Apply fixes directly:
   - Replace inline `fill="#hex"` on text with CSS classes (`class="fg-1"`)
   - Add missing `@media (prefers-color-scheme: dark)` overrides
   - Remove `opacity` from `<text>` elements
   - Replace `#000000` / `#ffffff` with theme colours
   - Fix `<tspan>` mixed styling → separate `<text>` elements
   - Add missing `font-family` attributes
   - Ensure transparent background (no full-viewport rect fill)
   - Fix ViewBox: remove `width`/`height` from `<svg>`, keep `viewBox`
4. Re-run validation to confirm resolution
5. Report: changes per file, before/after validation counts

### Contrast intent

Same as style intent, scoped to `svg-infographics contrast` findings only.

### Connectors intent

1. Run `svg-infographics connectors --svg <file>` + `svg-infographics collide --svg <file>`
2. Find hand-coded `<path d="M...">` arrows (greppable: `<path [^>]*d="M[^"]*" [^>]*arrow`)
3. Regenerate each via `svg-infographics connector --mode <m> --standoff 2` passing proper `--src-rect`/`--tgt-rect`/`--start-dir`/`--end-dir`
4. Replace hand-coded paths with `trimmed_path_d` + arrowhead polygons from tool output
5. Re-run connectors + collide checkers

### Geometry intent (beautify guard)

1. Run `svg-infographics validate <file> --baseline <original>` to detect dropped geometry
2. For each missing element, copy back from original into the `+` file (injection-only, preserve beautify decorations)
3. Re-run validate to confirm zero drops

### All / unspecified intent

Run every intent workflow in order: geometry → layout → connectors → style → contrast. Classify every finding (Fixed / Accepted / Checker limitation). Bulk dismissals prohibited.

## Skills applied

The spawned `svg-designer` agent reads and applies:

- `references/standards.md` — grid layout, CSS-First rule, contrast rules, font opacity rule, connector modes
- `references/workflow.md` — 6-phase process (primarily Phase 6 validation + targeted Phase 3/4 re-do)
- `references/validation.md` — checker usage, severity ladder, justification rules

## Rules

- **Destructive** — modifies files in place. Agent backs up nothing; rely on git
- **No hand-coded paths** — every connector regenerated via tool
- **`--standoff 2`** on every connector call (project standard)
- **Unicode glyphs** — fix any `->` / `<-` / `...` / `--` / `x` / `*` inside `<text>` nodes to proper Unicode
- **Classify every finding** — no bulk dismissals
- **Re-run validators** after every fix cycle; report before/after counts
