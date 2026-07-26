---
description: Generate or update a theme swatch SVG for brand colour approval
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, TaskCreate, TaskUpdate]
argument-hint: "brand name or colour direction, e.g. 'corporate blue palette' or 'dark green tech theme'"
---

# Generate Theme Swatch

## Toolchain gate (refuse only if the library is unavailable)

Before anything else run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && echo "STALE: library $LIB != plugin $PLUG - CLI may lack flags this skill uses; re-run the upgrade" || echo "toolkit $LIB"
```

Verify the CLI runs: `svg-infographics --help`. **REFUSE to run this command** only when the library is unavailable - the import fails AND the install cannot fix it, so `--help` still errors. A failed *upgrade* (offline, PyPI unreachable) while the CLI still imports is not fatal - run at the installed version, but treat a `STALE:` line as a live hazard: this command documents the current plugin's flags and an older CLI can reject them. No fallback, no hand-built output.


Create a theme swatch SVG for user approval before producing infographic deliverables.

## Task Tracking

**MANDATORY**: Create tasks for gathering requirements, generating swatch, getting approval, and documenting palette.

## Skills to apply

- **`theme` skill** — theme structure, swatch template, colour naming, approval workflow
- **`svg-designer` skill, `references/standards.md`** — CSS classes, dark mode, contrast rules

## Steps

1. **ASK the user**:
   - Brand colours, hex values, or mood direction?
   - Reference materials or existing brand guidelines?
   - Any colour constraints or preferences?

2. **Read reference swatches** from `examples/`:
   - `theme_swatch_1_kolomolo.svg` (blue/violet)
   - `theme_swatch_3_meridian.svg` (blue)
   - `theme_swatch_5_optima_manufacturing.svg` (burgundy)

3. **Generate theme swatch SVG** with three sections:
   - Palette reference (transparent background)
   - Light background strip with all element types
   - Dark background strip with all element types
   - `=== COLOUR RULES ===` comment block

4. **Present to user** for approval:
   - Show fg-1 through fg-4 with sample text
   - Show accent-1 and accent-2 with strokes and fills
   - Show card backgrounds, track lines, coverage bars
   - Identify any dark-mode failures with "FAIL?"

5. **On approval**: Document palette in project's `CLAUDE.md` or `theme.md`

6. **On rejection**: Adjust based on feedback, regenerate, re-present
