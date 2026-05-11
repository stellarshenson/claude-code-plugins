---
description: Export SVG to PNG with light/dark mode support via Playwright
allowed-tools: [Read, Bash, Glob, Grep]
argument-hint: "SVG file or glob, e.g. 'docs/images/01-diagram.svg' or 'docs/images/*.svg'"
---

# Export SVG to PNG

Render SVG files to PNG using `render-png` (Playwright-based). Natively evaluates `@media (prefers-color-scheme: dark)` CSS media queries.

## Pre-flight install (MANDATORY, no asking)

Before invoking `render-png`, always run:

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

No-op when the package is importable; auto-installs when missing or when a stale shim is on PATH but the package is uninstalled in the active Python.

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
