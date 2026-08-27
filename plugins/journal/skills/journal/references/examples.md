# Journal Entry Examples

Specimens for the four tiers `journal-tools check` enforces: Short (1-49 words, `[Short]` marker), Standard (50-150), Extended (150-400, `[Extended]` marker), and the over-400 case that belongs in a `docs/` article. Every specimen below produces exactly the validator result its heading says.

---

## Short entry (`[Short]`, under 50 words)

For a change with no WHY to preserve - a pin, a URL, a typo, a dead link. The marker tells the validator the brevity is deliberate.

```
3. **Task [Short] - Pin ruff to 0.6.9** (v0.1.8): lint step failed on a rule added in 0.7<br>
   **Result**: Pinned `ruff==0.6.9` in `pyproject.toml`; lint green again.
```

## Standard entry (50-150 words)

The default. One dense paragraph: problem -> finding -> fix -> verification, with file names and error text. Two shapes, a focused fix and a multi-file feature:

```
4. **Task - CI URL fixes** (v0.1.9): Fixed malformed GitHub URLs in package.json causing CI check-npm failure<br>
   **Result**: CI `check-release.yml` workflow failed at check-npm step with ValueError indicating repository.url doesn't match cloned repository. Found three malformed URLs in `package.json`: homepage had trailing `.git`, bugs.url had `.git/issues` path, and repository.url had duplicate `.git.git` suffix. Fixed all three URLs - homepage and bugs.url now use bare GitHub URLs without `.git`, repository.url uses single `.git` suffix. Build and tests pass.
```

```
6. **Task - CLI implementation** (v1.0.5): Created command-line tool for listing and culling resources from terminal<br>
   **Result**: Created `cli.py` with `jupyterlab_kernel_terminal_workspace_culler` command supporting two subcommands: `list` (displays all resources with idle times, culler settings, and terminal connection status) and `cull` (executes culling with optional `--dry-run` simulation). Added `--json` flag for machine-readable output. Implemented `JupyterClient` class for REST API communication with auto-detection of running Jupyter servers via `jupyter server list --json`. Token priority follows JupyterHub pattern: `JUPYTERHUB_API_TOKEN` -> `JPY_API_TOKEN` -> `JUPYTER_TOKEN` -> token from server list. Added `get_terminals_connection_status()` method to `culler.py` exposing terminal WebSocket connection status. Created `TerminalsConnectionHandler` in `routes.py` for `/terminals-connection` endpoint. CLI output shows culler settings first, then kernels with execution_state and idle time, terminals with connected/disconnected flag and idle time. Added entry point in `pyproject.toml` and `requests>=2.20.0` dependency. Updated `README.md` with CLI documentation section.
```

**Characteristics**: single paragraph; the trigger first; specific file names, error messages and numbers; every file modified named; dependencies added mentioned.

## Extended entry (`[Extended]`, 150-400 words)

For work that touches several areas in one session, an architectural decision, or a multi-iteration debug. Still ONE paragraph - the marker widens the word band, not the shape. Without the marker the validator warns at 150.

```
83. **Task [Extended] - Callout tool chain: cross-collision check, geom contains/rect-edge, empty-space speedup** (v1.0.12, plugins v1.3.1): svg-infographics callout workflow hardened with new validation tools, failure-mode detection, and 28x empty-space speedup<br>
    **Result**: Identified failure mode where the first callout placement pass did not check the leader path against shapes - the "auto-edge routing" leader sliced straight through Shape B - fixed by adding a leader-vs-hard-shapes intersection check that allows the origin shape but blocks transit through any other shape. Added a `CALLOUT CROSS-COLLISIONS` block to `check_overlaps` that parses `<g id="callout-*">` groups and pairwise-tests leader-vs-text-bbox, leader-vs-leader, and text-vs-text via shapely LineString/box intersection, wired into the CLI summary line. New `geom contains` subcommand in `calc_geometry.py` checks whether a point, bbox, line, polyline, or polygon sits inside an outer polygon, reporting both `contained` (shapely.covers) and `convex_safe` (convex hull also covered, catching concave notch re-entry) plus an `exit_segments` debug list. New `geom rect-edge` subcommand clips the ray from a rect centre toward an external point at the rect perimeter, used for callout leader-anchor computation by inflating the text bbox by the standoff and intersecting the target-ray. Performance optimisation in `calc_empty_space.find_empty_regions`: pre-split shapes into plain AABB tuples and shapely polygon geometries once up front, then run pure-Python AABB overlap in the quadtree hot path instead of constructing a shapely box per cell per shape - drops one empty-space call from 8815 ms to 318 ms, a 28x speedup, while the grid-search placement loop stays at ~335 ms and ~0.06 ms per candidate. `calc_empty_space` also gained `--tolerance` (default 20 px, the callout minimum) that shrinks each island inward via `shapely.buffer(-tolerance, join_style=2)`, and `--min-area` (default 500 px²) that drops slivers too small to fit a callout text bbox. Skill docs hardened: `svg-standards/SKILL.md` callout workflow grew from 5 to 7 steps with explicit pre-audit and post-audit `overlaps` gates, step 4 mandates `geom contains --polygon <island> --bbox <text-bbox>` with `contained=YES convex-safe=YES` as the pass condition, rule 6 added to placement rules requiring the leader anchor to come from `offset-rect` + `rect-edge` at a 3 px standoff, iterative-placement rule added (each placed callout's bbox must feed back into the obstacle list before the next placement), strand-bbox-tightness rule added to avoid over-erosion under the 20 px tolerance. `workflow/SKILL.md` tool inventory updated with the two new geom subcommands and the callout cross-collision block in `overlaps`. Rebuilt `docs/medium/images_article_02/06-manifold-showcase.svg` via the iterative tool chain, producing five clean callouts with leader lengths 22-68 px and zero cross-collisions. Tests: 517 passing (+17 across `TestCalloutCollision`, `TestGeometryContains`, `TestCalcEmptySpace`). Commit `c3d7650` pushed, PyPI `v1.0.12` published, marketplace bumped to v1.3.1.
```

**Characteristics**: ~390 words, one paragraph; failure mode first, fix second; each topic separated by a period and a fresh clause, never a heading or a bullet; concrete numbers (`8815 ms -> 318 ms`, `28x`, `+17 tests`); file paths, functions, commit SHA and version in backticks; the release stamp at the end. When tempted to add headings, bullets or code blocks - resist.

## Over 400 words: extract an article

An entry past the Extended cap has outgrown the journal. `journal-tools check` warns even with the marker; run `/journal:article N` to move the depth into `docs/<slug>.md` and leave a Standard summary that links to it. The specimen below is the trigger case, kept so the warning is recognisable - not a shape to copy.

```
85. **Task - svg-infographics README capability rewrite + [fonts] extra cleanup** (plugins v1.3.2): Rewrote the svg-infographics README around five named capabilities and removed the stale `[fonts]` optional-dependency mention everywhere it leaked<br>
    **Result**: Previous README pass drifted into deep workflow documentation - a dedicated Callout Naming Convention section, a 7-step empty-space walkthrough, multi-paragraph design-principle bullet lists - content that belongs in skill files, not in a capability overview. User pushed back: README should be "what + where" not "how", scannable in 60 seconds, capability-centric. Rewrote the document around five foundational-first capabilities: Design Foundations (grid-first layout, shape primitives, theme/CSS/dark mode, typography, 6-phase mandatory workflow, geometry sketch-constraint toolkit), Connectors (five routing modes with canonical Sankey manifold and auto-edge routing), Callouts and Empty Space (the `callout-*` naming convention folded inline as prose rather than a dedicated section, SVG-native free-region detection, placement workflow), Charts (pygal with caller-provided palette and injected dark mode), and Validation (five checkers plus pairwise connector collision as a mandatory pre-delivery gate). Each capability runs 3-4 sentences covering what, why, and which tools back it, followed by a one-line "Reference:" pointer to the relevant `skills/*/SKILL.md`. Added five use cases (branded banner, annotate dense diagram, Sankey flow, port foreign SVG, place legend on populated canvas) showing how capabilities compose. Kept Commands, Skills, and Tool Inventory as reference tables at the bottom for agents that scan by grep. Separately removed the `[fonts]` optional-dependency drift: `fonttools` was already a core `pyproject.toml` dependency so the `pip install 'stellars-claude-code-plugins[fonts]'` guidance that appeared in the README, `skills/validation/SKILL.md` ("Eight tools" with a `[fonts]` install block), and `stellars_claude_code_plugins/svg_tools/text_to_path.py` (module docstring, `_require_fonttools` error message, CLI error message) was wrong - most users reach the package via Claude Code and expect every tool to work without extras. Rewrote the validation skill intro to say "Twelve tools shipped ... no optional extras required", updated the text_to_path module docstring to note fonttools is bundled with the core install, replaced both error messages with "core dependency - reinstall the package" guidance, and updated the corresponding pytest skip-reason in `tests/test_svg_tools.py`. Also tightened `skills/svg-standards/SKILL.md` Z-order layering to mandate five named top-level groups (`<g id="background">`, `nodes`, `connectors`, `content`, `callouts`) so callouts always live on their own layer, rewrote the callout construction workflow in telegram style (dropped articles and copulas, kept the 7-step structure with its pre/post audit gates), and added a Quick Reference bullet for the layer convention. Deleted three stale repo-root artifacts from a prior devils-advocate run (`devils_advocate.md`, `devils_advocate_program.md`, `fact_repository.md`) that had drifted out of scope. Tests: 524 passing (no new tests - pure docs/cleanup session; the number is the baseline from the prior release entry confirming nothing regressed). Plugin marketplace bumped v1.3.1 -> v1.3.2, PyPI `stellars-claude-code-plugins` unchanged.
```

## When to use each

| Tier | Use when |
|------|----------|
| Short | Pin, URL fix, typo, dead-link patch - nothing to explain |
| Standard | New feature, multi-file change, bug fix with a cause, standard implementation |
| Extended | Multi-area session, architectural decision with tradeoffs, debugging investigation |
| Article | The entry needs sections to be readable - the depth belongs in `docs/` |

**Default to Standard.** Short only when there is no WHY; Extended only when the rationale matters six months on.
