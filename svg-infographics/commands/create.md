---
description: Create SVG infographic(s) following the full grid-first design workflow. Triggers - "create svg", "make svg", "create graphics", "make infographic", "create diagram", "make banner", "create timeline", "create flowchart".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "describe the infographic, e.g. 'card grid showing 4 platform modules' or 'timeline of project milestones'"
---

# Create SVG Infographic

Create one or more SVG infographics following the mandatory preflight → author → check → finalize workflow. Each image goes through all four stages sequentially — no batching.

Spawns `svg-designer` agent via fork context so user can continue working while agent designs. The agent MUST invoke `svg-infographics preflight` (declaring all components via flags) as its first action - this pulls the relevant rule cards into context before any `<rect>` is written. No authoring before preflight completes.

## Task Tracking

MANDATORY: create a task list at start showing all phases for each image. Update task status as you progress. Non-negotiable.

## Steps

1. **ASK the user**:
   - What infographic(s) to create? (type, content, purpose)
   - Target directory for output files?
   - Brand/theme? (existing swatch or new?)
   - Any specific style preferences?

2. **Theme check**: If no approved swatch exists for this brand, run `/svg-infographics:theme` first.

3. **Spawn `svg-designer` agent** via `Agent(subagent_type="svg-designer", prompt="Create <description> at <path>. Follow 6-phase workflow. Theme <swatch>.")`. Fork context runs out-of-band; user keeps working.

4. **Agent workflow** (runs in fork):
   - Preflight — call `svg-infographics preflight --cards N --connectors N --connector-mode X --connector-direction Y ...` with the full declared component set. Capture the returned rule bundle into the agent's context. No authoring begins until preflight returns.
   - Phase 1 — Research: read 3-5 relevant examples from `examples/`
   - Phase 2 — Invisible Grid: calculate with `svg-infographics primitives` for exact anchor coordinates. File contains ONLY XML comments (grid + topology)
   - Phase 3 — Scaffold: build structure from grid positions using primitives for shapes and `connector` for arrows. ALWAYS pass `--direction` (and for L / L-chamfer, also `--start-dir` + `--end-dir` or `--src-rect` + `--tgt-rect`) - otherwise the routing looks garbage.
   - Phase 4 — Content: add text (CSS classes only), icons (Lucide ISC), descriptions. Unicode glyphs only — no ASCII arrows
   - Phase 5 — Finishing: verify connectors match tool output, place callouts via `callouts`, write file description comment
   - Phase 6 — Check + Finalize: run `svg-infographics check --svg <file>` with the SAME flags used in preflight. Exit 0 = component counts match the declaration. Then `svg-infographics finalize <file>` for the ship-ready structural gate. Exit 1 on HARD finding = not shippable.

5. **For any smooth curve through waypoints** (decision boundaries, distributions, ROC/PR, sigmoid, trajectories, organic flow paths) the agent MUST use `svg-infographics primitives spline --points "..." --samples 200`. Hand-written `C`/`Q` bezier paths for data curves = workflow violation.

6. **Report**: created files, validation results, any remaining items.

## Skills applied

The spawned `svg-designer` agent reads and applies:

- `rules/<component>.md` — per-component rule cards (card, connector, ribbon, background, timeline, icon, callout). Pulled automatically by `svg-infographics preflight` based on declared component types.
- `references/tools.md` — full tool palette
- `references/standards.md` — design rules, grid layout, CSS classes, cards, arrows, typography, callouts, z-order
- `references/workflow.md` — 6-phase process with gate checks
- `references/validation.md` — checker tools and severity ladder
