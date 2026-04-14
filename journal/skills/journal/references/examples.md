# Journal Entry Examples

Examples of journal entries at different detail levels. Choose based on task complexity.

---

## Short Entry

For simple, focused changes - bug fixes, small features, configuration updates.

```
4. **Task - CI URL fixes** (v0.1.9): Fixed malformed GitHub URLs in package.json causing CI check-npm failure<br>
   **Result**: CI `check-release.yml` workflow failed at check-npm step with ValueError indicating repository.url doesn't match cloned repository. Found three malformed URLs in `package.json`: homepage had trailing `.git`, bugs.url had `.git/issues` path, and repository.url had duplicate `.git.git` suffix. Fixed all three URLs - homepage and bugs.url now use bare GitHub URLs without `.git`, repository.url uses single `.git` suffix. Build and tests pass.
```

**Characteristics**:
- ~80 words
- Single paragraph
- Problem -> finding -> fix -> verification
- Specific file names and error messages

---

## Normal Entry

For standard implementation tasks - new features, refactoring, multi-file changes.

```
6. **Task - CLI implementation** (v1.0.5): Created command-line tool for listing and culling resources from terminal<br>
   **Result**: Created `cli.py` with `jupyterlab_kernel_terminal_workspace_culler` command supporting two subcommands: `list` (displays all resources with idle times, culler settings, and terminal connection status) and `cull` (executes culling with optional `--dry-run` simulation). Added `--json` flag for machine-readable output. Implemented `JupyterClient` class for REST API communication with auto-detection of running Jupyter servers via `jupyter server list --json`. Token priority follows JupyterHub pattern: `JUPYTERHUB_API_TOKEN` -> `JPY_API_TOKEN` -> `JUPYTER_TOKEN` -> token from server list. Added `get_terminals_connection_status()` method to `culler.py` exposing terminal WebSocket connection status. Created `TerminalsConnectionHandler` in `routes.py` for `/terminals-connection` endpoint. CLI output shows culler settings first, then kernels with execution_state and idle time, terminals with connected/disconnected flag and idle time. Added entry point in `pyproject.toml` and `requests>=2.20.0` dependency. Updated `README.md` with CLI documentation section.
```

**Characteristics**:
- ~150-200 words
- Single dense paragraph
- Lists all files modified with specific changes
- Describes functionality and technical details
- Mentions dependencies added

### Multi-topic Normal Entry (problem -> fix -> tools -> perf -> docs -> release)

Use this shape when a single session touches several orthogonal areas and every change is worth recording. Keep it a single continuous paragraph despite the topic breadth - the reader should be able to scan by phrase, not by heading.

```
83. **Task - Callout tool chain: cross-collision check, geom contains/rect-edge, empty-space speedup** (v1.0.12, plugins v1.3.1): svg-infographics callout workflow hardened with new validation tools, failure-mode detection, and 28x empty-space speedup<br>
    **Result**: Identified failure mode where the first callout placement pass did not check the leader path against shapes - the "auto-edge routing" leader sliced straight through Shape B - fixed by adding a leader-vs-hard-shapes intersection check that allows the origin shape but blocks transit through any other shape. Added a `CALLOUT CROSS-COLLISIONS` block to `check_overlaps` that parses `<g id="callout-*">` groups and pairwise-tests leader-vs-text-bbox, leader-vs-leader, and text-vs-text via shapely LineString/box intersection, wired into the CLI summary line. New `geom contains` subcommand in `calc_geometry.py` checks whether a point, bbox, line, polyline, or polygon sits inside an outer polygon, reporting both `contained` (shapely.covers) and `convex_safe` (convex hull also covered, catching concave notch re-entry) plus an `exit_segments` debug list. New `geom rect-edge` subcommand clips the ray from a rect centre toward an external point at the rect perimeter, used for callout leader-anchor computation by inflating the text bbox by the standoff and intersecting the target-ray. Performance optimisation in `calc_empty_space.find_empty_regions`: pre-split shapes into plain AABB tuples and shapely polygon geometries once up front, then run pure-Python AABB overlap in the quadtree hot path instead of constructing a shapely box per cell per shape - drops one empty-space call from 8815 ms to 318 ms, a 28x speedup, while the grid-search placement loop stays at ~335 ms and ~0.06 ms per candidate. `calc_empty_space` also gained `--tolerance` (default 20 px, the callout minimum) that shrinks each island inward via `shapely.buffer(-tolerance, join_style=2)`, and `--min-area` (default 500 px²) that drops slivers too small to fit a callout text bbox. Skill docs hardened: `svg-standards/SKILL.md` callout workflow grew from 5 to 7 steps with explicit pre-audit and post-audit `overlaps` gates, step 4 mandates `geom contains --polygon <island> --bbox <text-bbox>` with `contained=YES convex-safe=YES` as the pass condition, rule 6 added to placement rules requiring the leader anchor to come from `offset-rect` + `rect-edge` at a 3 px standoff, iterative-placement rule added (each placed callout's bbox must feed back into the obstacle list before the next placement), strand-bbox-tightness rule added to avoid over-erosion under the 20 px tolerance. `workflow/SKILL.md` tool inventory updated with the two new geom subcommands and the callout cross-collision block in `overlaps`. Rebuilt `docs/medium/images_article_02/06-manifold-showcase.svg` via the iterative tool chain, producing five clean callouts with leader lengths 22-68 px and zero cross-collisions. Tests: 517 passing (+17 across `TestCalloutCollision`, `TestGeometryContains`, `TestCalcEmptySpace`). Commit `c3d7650` pushed, PyPI `v1.0.12` published, marketplace bumped to v1.3.1.
```

**Characteristics**:
- ~400 words but still ONE paragraph - density over structure
- Failure mode stated first, fix second - never fix-first without the root cause
- Each topic separated by a period and a fresh clause, not a header
- Concrete numbers (`8815 ms -> 318 ms`, `28x`, `5 to 7 steps`, `22-68 px`, `+17 tests`)
- File paths, function names, commit SHA, PyPI version in backticks
- Terminal actions (commit pushed, version published) belong at the END as the release stamp
- When tempted to add headings, bullets, or code blocks - resist; this shape is the target

---

## Extended Entry

For complex refactoring or multi-component changes requiring clear per-layer breakdown.

```
8. **Task - Replace sessions with workspaces** (v1.0.18): Replaced session culling with workspace culling throughout the extension<br>
   **Result**: User clarified that "sessions" (kernel-notebook associations) were not the intended culling target - the extension should cull JupyterLab workspaces (auto-0, auto-k, default, etc.) instead. These are UI state files stored in `~/.jupyter/lab/workspaces/` created when users open multiple browser windows.

   **Design**: Workspaces are managed by `jupyterlab_server.workspaces_handler.WorkspacesManager` which reads JSON files from `~/.jupyter/lab/workspaces/`. Each workspace has metadata including `id`, `last_modified`, and `created` timestamps. Culling decision uses `last_modified` rather than access time since workspace files are only written when UI state changes. Default workspace is protected because it's the fallback when no workspace is specified - culling it would disrupt users without explicit workspace URLs. Workspace culling disabled by default (unlike kernels/terminals) because most users don't accumulate many workspaces and the 7-day timeout is long enough that manual cleanup is rarely needed.

   **Backend changes** (`culler.py`): Replaced all session references with workspace. Added `workspace_manager` property using `jupyterlab_server.workspaces_handler.WorkspacesManager` initialized with `~/.jupyter/lab/workspaces/` path. Added `list_workspaces()` method returning workspace id, last_modified, and created timestamps. Added `_cull_workspaces()` method that iterates workspaces, checks `last_modified` timestamp against timeout, and calls `ws_mgr.delete(workspace_id)`. Default workspace is protected and never culled. Renamed settings: `_session_cull_enabled` -> `_workspace_cull_enabled`, `_session_cull_idle_timeout` -> `_workspace_cull_idle_timeout`. Updated `_last_cull_result` to use `workspaces_culled` key.

   **Backend changes** (`routes.py`): Updated `CullResultHandler` to return `workspaces_culled` instead of `sessions_culled`. Added `WorkspacesHandler` class for GET `/workspaces` endpoint returning workspace list.

   **Schema changes** (`schema/plugin.json`): Renamed `sessionCullEnabled` -> `workspaceCullEnabled`, `sessionCullIdleTimeout` -> `workspaceCullIdleTimeout`. Updated descriptions to explain workspace culling behavior and note that default workspace is never culled.

   **CLI changes** (`cli.py`): Replaced `list_sessions()` with `list_workspaces()` calling extension's `/workspaces` endpoint. Updated output to show WORKSPACES section with protected indicator for default workspace. Removed session culling from CLI since workspace culling requires filesystem access handled by backend.

   **Frontend changes** (`src/index.ts`): Updated `pollCullResults()` to expect `workspaces_culled` instead of `sessions_culled`. Changed notification output from "Sessions" to "Workspaces". Updated plugin description.

   **Documentation changes** (`README.md`): Updated description to mention workspaces instead of sessions. Changed Features bullet from "Session culling" to "Workspace culling" explaining auto-named workspaces. Updated Default Settings table to show workspace culling disabled by default with 7-day timeout. Updated How Idle Detection Works section to explain workspace culling based on `last_modified` timestamp and that default workspace is protected.
```

**Characteristics**:
- ~350+ words
- Multiple labeled sections
- **Result**: Context and rationale for the change
- **Design**: Technical decisions, tradeoffs, and reasoning (why `last_modified`, why protect default, why disabled by default)
- **Component changes**: Grouped by file or layer (backend, routes, schema, CLI, frontend, docs)
- Used for multi-file refactoring where design rationale and per-component tracking aid future reference

---

## When to Use Each

| Entry Type | Use When |
|------------|----------|
| Short | Bug fix, config change, URL fix, typo fix, simple refactor |
| Normal | New feature, multi-file change, API addition, standard implementation |
| Extended | Multi-component refactoring, architectural change, design decisions with tradeoffs, debugging investigation |

**Default to Normal** - most tasks fit this level. Use Short for trivial fixes, Extended only when the investigation or architecture matters for future understanding.
