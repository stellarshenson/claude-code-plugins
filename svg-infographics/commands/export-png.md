---
description: Export SVG to PNG with light/dark mode support via Playwright
allowed-tools: [Read, Bash, Glob, Grep]
argument-hint: "SVG file or glob, e.g. 'docs/images/01-diagram.svg' or 'docs/images/*.svg'"
---

# Export SVG to PNG

## Toolchain gate (refuse only if the library is unavailable)

Before anything else run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && echo "STALE: library $LIB != plugin $PLUG - CLI may lack flags this skill uses; re-run the upgrade" || echo "toolkit $LIB"
```

Verify the CLI runs: `svg-infographics --help`. **REFUSE to run this command** only when the library is unavailable - the import fails AND the install cannot fix it, so `--help` still errors. A failed *upgrade* (offline, PyPI unreachable) while the CLI still imports is not fatal - run at the installed version, but treat a `STALE:` line as a live hazard: this command documents the current plugin's flags and an older CLI can reject them. No fallback, no hand-built output.


Render SVG files to PNG using `render-png` (Playwright-based). Natively evaluates `@media (prefers-color-scheme: dark)` CSS media queries.

## Pre-flight install (MANDATORY, no asking)

Before invoking `render-png`, always run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && echo "STALE: library $LIB != plugin $PLUG - CLI may lack flags this skill uses; re-run the upgrade" || echo "toolkit $LIB"
```

The upgrade always runs - a stale-but-importable install is exactly the failure this gate prevents, and the reinstall also repairs a stale shim on PATH whose package is uninstalled in the active Python.

## Steps

1. **Identify targets**: Glob for SVG files matching the argument

2. **Render each SVG**:
   ```bash
   render-png <file>.svg <file>.png --mode both --width 3000
   ```
   Creates `<file>.light.png` and `<file>.dark.png` with transparent backgrounds.

3. **Options** (pass through from user request):
   - `--mode light|dark|both` (default: both)
   - `--width N` (default: 3000)
   - `--bg "#hex"` (default: transparent)

4. **Report**: list rendered files with dimensions and sizes
