---
description: Create SVG infographic(s) following the full grid-first design workflow. Triggers - "create svg", "make svg", "create graphics", "make infographic", "create diagram", "make banner", "create timeline", "create flowchart".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "describe the infographic, e.g. 'card grid showing 4 platform modules' or 'timeline of project milestones'"
---

# Create SVG Infographic

## Toolchain gate (refuse only if the library is unavailable)

Before anything else run:

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

Verify the CLI runs: `svg-infographics --help`. **REFUSE to run this command** only when the library is unavailable - the import fails AND the install cannot fix it, so `--help` still errors. A failed *upgrade* (offline, PyPI unreachable) while the CLI still imports is fine - run at the installed version; the plugin and library ship at the same version, so any installed library is a compatible one. No fallback, no hand-built output.


Create one or more SVG infographics following the mandatory draft → preflight → scaffold → author → check → finalize workflow.

**Deck batching**: sibling images for one document are ONE deck. Invoke the `svg-infographics:svg-designer` skill ONCE per deck of up to ~5 images - the skill fork builds them sequentially (theme, recipes and rule cards loaded once, not per image) and closes with a cross-file `consistency` check. One invocation per image multiplies ~100KB of context per fork for nothing. More than ~5 images → split into multiple decks.

The agent MUST invoke `svg-infographics preflight` (declaring all components via flags) as its first action per image - this pulls the relevant rule cards into context before any `<rect>` is written. No authoring before preflight completes.

## Task Tracking

MANDATORY: create a task list at start showing all phases for each image. Update task status as you progress. Non-negotiable.

## Steps

1. **ASK the user** (one AskUserQuestion round):
   - What infographic(s) to create? (type, content, purpose)
   - **Drafting mode** - MANDATORY question, two options:
     - **Draft approval (interactive)**: the concept draft is presented to the user as text and generation waits for their approval / edits
     - **End-to-end (headless)**: the AI proceeds from draft to finished SVGs without stopping
   - Output folder: `images_<context>` (visible) or `.images_<context>` (hidden)? `<context>` = the document/article slug. Default to visible `images_<context>` unless the user picks hidden
   - Brand/theme? (existing swatch or new?)
   - Any specific style preferences?
   - **Model**: the `svg-infographics:svg-designer` skill runs on its own configured model (**sonnet**); the `Skill` call takes no model override, so a different model means editing the skill's frontmatter

2. **Concept draft** (ALWAYS written, both modes): one plain-text ```svg-infographics``` fenced content spec per image, following `examples/concept_draft_deck.md` - canvas + format preset, theme, every band, the CONCRETE facts each band carries (real numbers, not lorem), per-image data sources, open questions for the reviewer. The draft is the spec the builder consumes; headless mode skips the approval, not the draft.
   - **Interactive mode**: present the draft(s) to the user, apply their edits, do NOT generate until they approve
   - **Headless mode**: save the draft(s) next to the images (`<context>_concept_draft.md`) and proceed

3. **Theme check**: If no approved swatch exists for this brand, run `/svg-infographics:theme` first.

4. **Invoke the `svg-infographics:svg-designer` SKILL once per deck** - via the `Skill` tool, NOT `Agent` / `subagent_type`: there is no `svg-designer` agent, it is a `context: fork` skill and only the `Skill` tool resolves it. Call `Skill(skill="svg-infographics:svg-designer", args="Create <deck description, all images> at <path> from the approved concept draft: <draft>. Follow the workflow per image, sequentially. Theme <swatch>. Close with the deck consistency check.")`. The skill forks and runs out-of-band on its own model (sonnet); user keeps working. The approved draft goes INTO the args - the builder builds what the draft says, not its own interpretation.

5. **Agent workflow** (runs in fork, per image):
   - Preflight — call `svg-infographics preflight --cards N --connectors N --connector-mode X --connector-direction Y ...` with the full declared component set. Capture the returned rule bundle into the agent's context. No authoring begins until preflight returns.
   - Research — read `examples/INDEX.md` (geometry recipes) + ONE closest example. Not 3-5
   - Scaffold — `svg-infographics scaffold --format <preset> --cols C --rows R --cards N --title "..." --out <file>` generates the skeleton: viewBox, 5px-snapped grid comments, theme CSS + dark mode, guide grid, the five canonical layers, placeholder cards. Do NOT hand-type any of that. Re-theme the CSS block against the approved swatch, then replace placeholders (keep the `card-N` ids, drop `data-placeholder`)
   - Author — structure from grid positions using `primitives` for shapes and `connector` for arrows. ALWAYS pass `--direction` (and for L / L-chamfer, also `--start-dir` + `--end-dir` with `--src-rect` + `--tgt-rect`) - the route gates verify axis AND sign on both ends and block card-piercing routes. Run `svg-infographics map --svg <file>` before placing anything new - one scan shows per-layer occupancy and the largest free boxes; use `empty-space --layers/--ignore-layers` for targeted placement
   - Content — text (CSS classes only), icons (Lucide ISC, corner slots placed via `place --ref-id accent-bar`), descriptions. Unicode glyphs only — no ASCII arrows
   - Finishing — verify connectors match tool output, place callouts via `callouts`, fill in the file description comment
   - Check + Finalize (batch-fix) — `svg-infographics workflow --svg <file>` tells you which gates are already met (never redo a met gate), then `svg-infographics check --svg <file>` with the SAME flags used in preflight, then `svg-infographics finalize <file>` ONCE - it runs ALL validators including the visual-geometry layer. Fix everything it reports in one pass, re-run once, cap 3 iterations. Then ONE high-quality `render-png --mode both` readback against the 6-item checklist in workflow.md - the PNG is the only render artifact; no browser sessions, no screenshot loops
   - Deck close — `svg-infographics finalize <all files>` in one call (cross-file consistency runs automatically on multi-file invocations)

6. **For any smooth curve through waypoints** (decision boundaries, distributions, ROC/PR, sigmoid, trajectories, organic flow paths) the agent MUST use `svg-infographics primitives spline --points "..." --samples 200`. Hand-written `C`/`Q` bezier paths for data curves = workflow violation.

7. **Report**: created files, validation results, any remaining items. Interactive mode: note where the approved draft deviated and why, if it did.

## Skills applied

The `svg-infographics:svg-designer` skill fork reads and applies:

- `rules/<component>.md` — per-component rule cards (card, connector, ribbon, background, timeline, icon, callout, shapes). Pulled automatically by `svg-infographics preflight` based on declared component types - the detailed design rules live here.
- `references/standards-core.md` — the essentials: CSS classes, contrast, grid, structure, z-order
- `examples/INDEX.md` — geometry recipes per pattern, plus the one closest example
- `examples/concept_draft_deck.md` — the concept-draft reference (what a good draft carries)
- `references/workflow.md` — phase process with gate checks (read at build start)
- `references/validation.md` / `references/tools.md` — on demand
