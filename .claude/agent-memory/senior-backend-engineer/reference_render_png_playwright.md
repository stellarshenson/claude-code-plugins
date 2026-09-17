---
name: reference-render-png-playwright
description: render-png needs a playwright-build-matched chromium that is wiped between sessions; reinstall before any visual verification
metadata:
  type: reference
---

`render-png` (src/stellars_claude_code_plugins/svg_tools/render_png.py) drives Playwright
Chromium only - there is no cairosvg or rsvg fallback path.

`PLAYWRIGHT_BROWSERS_PATH` is `/galaxalab/ms-playwright`. That directory holds a *newer*
chromium build than the repo venv's playwright pin expects, and the matching build gets
removed between sessions, so the first render of a session fails with
"Executable doesn't exist at .../chromium_headless_shell-<N>".

Fix, ~90s, before any render work:

```
uv run --extra dev playwright install chromium-headless-shell
```

**Why:** visual verification in this repo is mandatory (see the user's
`feedback_playwright_mandatory` note), so a dead renderer blocks the whole task.
**How to apply:** run it once at the start of any task that renders SVG to PNG, rather than
waiting for the first failure.
