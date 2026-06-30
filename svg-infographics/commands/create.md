---
description: Create SVG infographic(s) following the full grid-first design workflow. Triggers - "create svg", "make svg", "create graphics", "make infographic", "create diagram", "make banner", "create timeline", "create flowchart".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "describe the infographic, e.g. 'card grid showing 4 platform modules' or 'timeline of project milestones'"
---

# Create SVG Infographic

Create one or more SVG infographics following the mandatory preflight → author → check → finalize workflow.

**Deck batching**: sibling images for one document are ONE deck. Spawn ONE `svg-designer` agent per deck of up to ~5 images - the agent builds them sequentially inside one fork (theme, recipes and rule cards loaded once, not per image) and closes with a cross-file `consistency` check. Spawning one agent per image multiplies ~100KB of context per spawn for nothing. More than ~5 images → split into multiple decks.

The agent MUST invoke `svg-infographics preflight` (declaring all components via flags) as its first action per image - this pulls the relevant rule cards into context before any `<rect>` is written. No authoring before preflight completes.

## Task Tracking

MANDATORY: create a task list at start showing all phases for each image. Update task status as you progress. Non-negotiable.

## Steps

1. **ASK the user**:
   - What infographic(s) to create? (type, content, purpose)
   - Output folder: `images_<context>` (visible) or `.images_<context>` (hidden)? `<context>` = the document/article slug. Default to visible `images_<context>` unless the user picks hidden
   - Brand/theme? (existing swatch or new?)
   - Any specific style preferences?
   - **Model** for the svg-designer agent(s): default **sonnet** - only ask when the user raised quality or cost, then offer sonnet / opus / haiku

2. **Theme check**: If no approved swatch exists for this brand, run `/svg-infographics:theme` first.

3. **Spawn ONE `svg-designer` agent per deck** via `Agent(subagent_type="svg-designer", model="<choice, default sonnet>", prompt="Create <deck description, all images> at <path>. Follow 6-phase workflow per image, sequentially. Theme <swatch>. Close with the deck consistency check.")`. Fork context runs out-of-band; user keeps working.

4. **Agent workflow** (runs in fork, per image):
   - Preflight — call `svg-infographics preflight --cards N --connectors N --connector-mode X --connector-direction Y ...` with the full declared component set. Capture the returned rule bundle into the agent's context. No authoring begins until preflight returns.
   - Phase 1 — Research: read `examples/INDEX.md` (geometry recipes) + ONE closest example. Not 3-5
   - Phase 2 — Invisible Grid: calculate with `svg-infographics primitives` for exact anchor coordinates. File contains ONLY XML comments (grid + topology)
   - Phase 3 — Scaffold: build structure from grid positions using primitives for shapes and `connector` for arrows. ALWAYS pass `--direction` (and for L / L-chamfer, also `--start-dir` + `--end-dir` or `--src-rect` + `--tgt-rect`) - otherwise the routing looks garbage.
   - Phase 4 — Content: add text (CSS classes only), icons (Lucide ISC, corner slots placed via `place --ref-id accent-bar`), descriptions. Unicode glyphs only — no ASCII arrows
   - Phase 5 — Finishing: verify connectors match tool output, place callouts via `callouts`, write file description comment
   - Phase 6 — Check + Finalize (batch-fix): run `svg-infographics check --svg <file>` with the SAME flags used in preflight, then `svg-infographics finalize <file>` ONCE - it runs ALL validators including the visual-geometry layer. Fix everything it reports in one pass, re-run once, cap 3 iterations. Then ONE high-quality `render-png --mode both` readback against the 6-item checklist in workflow.md - the PNG is the only render artifact; no browser sessions, no screenshot loops
   - Deck close — `svg-infographics finalize <all files>` in one call (cross-file consistency runs automatically on multi-file invocations)

5. **For any smooth curve through waypoints** (decision boundaries, distributions, ROC/PR, sigmoid, trajectories, organic flow paths) the agent MUST use `svg-infographics primitives spline --points "..." --samples 200`. Hand-written `C`/`Q` bezier paths for data curves = workflow violation.

6. **Report**: created files, validation results, any remaining items.

## Skills applied

The spawned `svg-designer` agent reads and applies:

- `rules/<component>.md` — per-component rule cards (card, connector, ribbon, background, timeline, icon, callout, shapes). Pulled automatically by `svg-infographics preflight` based on declared component types - the detailed design rules live here.
- `references/standards-core.md` — the essentials: CSS classes, contrast, grid, structure, z-order
- `examples/INDEX.md` — geometry recipes per pattern, plus the one closest example
- `references/workflow.md` — 6-phase process with gate checks (read at build start)
- `references/validation.md` / `references/tools.md` — on demand
