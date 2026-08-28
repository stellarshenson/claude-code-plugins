---
description: Fix issues in SVG infographics. Argument describes what to fix (layout / style / contrast / connectors / all). Dispatches the svg-designer builder - an in-session fork by default. Triggers - "fix svg", "fix layout", "fix style", "fix contrast", "fix connectors", "fix infographic".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, Skill, TaskCreate, TaskUpdate]
argument-hint: "SVG file path + optional intent (e.g. 'docs/fig.svg overlaps' or 'docs/*.svg style')"
---

# Fix SVG

## Toolchain gate (refuse only if the library is unavailable)

Before anything else run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Verify the CLI runs: `svg-infographics --help`. **The gate above blocks on both failures** - an absent library (`FATAL`) and a version mismatch (`STALE`) each exit non-zero. Neither is advisory: this command documents the current plugin's flags, so a mismatched CLI may reject them and anything it does produce is unverified. Report the line and stop. No fallback, no hand-built output.


Diagnose and fix issues in existing SVG infographics. Argument is free-text — user describes the file and what to fix.

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

MANDATORY: create tasks for diagnosis, each fix category, and validation re-run. The builder owns its own task list.

## Steps

1. **Classify intent** from argument. If ambiguous, ask user one clarifying question via `AskUserQuestion` before spawning
2. **Dispatch the builder.** Default: `Skill(skill="svg-infographics:svg-designer", args="<intent + file + instructions>")` - forks out-of-band, user keeps working. For several files at once, or when the user wants each fix visible and individually stoppable, dispatch one background `Agent` per file instead (see *Dispatch the builder* in `/svg-infographics:create` for both call shapes and the agent-type caveat)
3. **Builder follows the fix workflow** (see below). On completion, reports findings + fixes back to parent

## Builder fix workflow

The dispatched builder runs this workflow; the parent command does not execute these steps directly.

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

1. Run `svg-infographics connectors --svg <file>` + `svg-infographics collide --connectors-d '[...]'` (it takes the connector path `d` strings, not the file)
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

The `svg-designer` builder reads and applies:

- `references/standards.md` — grid layout, CSS-First rule, contrast rules, font opacity rule, connector modes
- `references/workflow.md` — 6-phase process (primarily Phase 6 validation + targeted Phase 3/4 re-do)
- `references/validation.md` — checker usage, severity ladder, justification rules

## Completion gate

A run ends in one of exactly two states, per finding: the file was **edited** so the checker no longer reports it, or the finding is **still present and carries a written justification comment adjacent to the element in the SVG**. Nothing else counts as finished.

Re-run the checkers and compare counts against the diagnosis. A count that did not move means no fix landed - keep working, do not report. Classifying a finding "Accepted" without writing the justification into the file is the same as leaving it unhandled, because the next run re-reports it and the reason is gone.

## Rules

- **Reporting is not fixing** — this command exists to change the file. A run that ends with findings, no edits and no written justifications has failed, whatever its summary said
- **Destructive** — modifies files in place. The builder backs up nothing; rely on git
- **No hand-coded paths** — every connector regenerated via tool
- **`--standoff 2`** on every connector call (project standard)
- **Unicode glyphs** — fix any `->` / `<-` / `...` / `--` / `x` / `*` inside `<text>` nodes to proper Unicode
- **Classify every finding** — no bulk dismissals
- **Re-run validators** after every fix cycle; report before/after counts
