---
description: Create SVG infographic(s) following the full grid-first design workflow. Triggers - "create svg", "make svg", "create graphics", "make infographic", "create diagram", "make banner", "create timeline", "create flowchart".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "describe the infographic, e.g. 'card grid showing 4 platform modules' or 'timeline of project milestones'"
---

# Create SVG Infographic

## Toolchain gate

Run first:

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

Verify CLI: `svg-infographics --help`. REFUSE only if library unavailable - import fails AND install cannot fix it, so `--help` still errors. Failed *upgrade* (offline, PyPI unreachable) while CLI still imports = fine; plugin + library ship same version, so any installed library is compatible. No fallback, no hand-built output.

Workflow: draft → preflight → scaffold → author → check → finalize.

**Deck batching**: sibling images for one document = ONE deck. Invoke the `svg-infographics:svg-designer` skill ONCE per deck of ≤5 images - fork builds them sequentially (theme + recipes + rule cards loaded once, not per image), closes with a cross-file `consistency` check. One invoke per image wastes ~100KB context per fork. >5 images → split into decks.

**Preflight first**: builder runs `svg-infographics preflight` (all components via flags) as its first action per image - pulls the rule cards before any `<rect>`. No authoring before preflight returns.

## Task tracking

MANDATORY: task list at start, all phases per image. Update status as you go.

## Steps

1. **Ask user** (one AskUserQuestion round):
   - What infographic(s)? (type, content, purpose)
   - **Draft mode** (MANDATORY, two options):
     - **Interactive**: present draft as text, wait for approval/edits before generating
     - **Headless**: proceed draft → finished SVGs, no stop
   - **Output dir `<output-dir>`**: `images_<context>` (visible) or `.images_<context>` (hidden)? `<context>` = document basename slug ONLY (e.g. `next_best_site`), never a path. Folder is a SIBLING of the document - directly inside the document's own directory. Resolve `<output-dir>` to ONE absolute path now (`<dir-of-document>/images_<context>`); an absolute path cannot nest under itself. Default visible unless user picks hidden
   - Brand/theme? (existing swatch or new)
   - Style preferences?
   - **Model**: skill runs on its own model (**sonnet**); the `Skill` call takes no model override - different model = edit the skill frontmatter

2. **Concept draft** (ALWAYS written, both modes): one ```svg-infographics``` fenced spec per image, per `examples/concept_draft_deck.md` - canvas + format preset, theme, every band, CONCRETE facts per band (real numbers, not lorem), per-image data sources, open questions. Draft = the spec the builder consumes; headless skips approval, not the draft.
   - **Interactive**: present draft(s), apply edits, do NOT generate until approved
   - **Headless**: save draft(s) into `<output-dir>` as `<context>_concept_draft.md`, proceed

3. **Theme check**: no approved swatch for this brand → run `/svg-infographics:theme` first.

4. **Invoke the `svg-infographics:svg-designer` SKILL once per deck** - the `Skill` tool, NOT `Agent` / `subagent_type` (no `svg-designer` agent exists; it is a `context: fork` skill, only `Skill` resolves it). Pass the absolute `<output-dir>` from step 1 verbatim; builder writes files DIRECTLY into it as `<output-dir>/<NN-name>.svg` - must NOT prepend cwd or re-derive the folder (nests the doc path inside itself; observed bug `.../next_best_site/next_best_site/.images_next_best_site`). Call:
   `Skill(skill="svg-infographics:svg-designer", args="Create <deck description, all images> into the absolute directory <output-dir> - write files there verbatim, do NOT nest or re-derive the path - from the approved concept draft: <draft>. Follow the workflow per image, sequentially. Theme <swatch>. Close with the deck consistency check.")`
   Fork runs out-of-band; user keeps working. Approved draft goes INTO the args - builder builds the draft, not its own interpretation.

5. **Builder workflow** (fork, per image):
   - **Preflight** - `svg-infographics preflight --cards N --connectors N --connector-mode X --connector-direction Y ...`, full declared component set. Capture the rule bundle. No authoring before it returns.
   - **Research** - read `examples/INDEX.md` (geometry recipes) + ONE closest example. Not 3-5.
   - **Scaffold** - `svg-infographics scaffold --format <preset> --cols C --rows R --cards N --title "..." --out <file>`: viewBox, 5px-snapped grid comments, theme CSS + dark mode, guide grid, five canonical layers, placeholder cards. Do NOT hand-type. Re-theme the CSS to the approved swatch, replace placeholders (keep `card-N` ids, drop `data-placeholder`).
   - **Author** - structure from grid positions: `primitives` for shapes, `connector` for arrows. ALWAYS pass `--direction` (L / L-chamfer also `--start-dir` + `--end-dir` + `--src-rect` + `--tgt-rect`) - route gates verify axis + sign on both ends, block card-piercing routes. Run `svg-infographics map --svg <file>` before placing new; `empty-space --layers/--ignore-layers` for targeted placement.
   - **Content** - text (CSS classes only), icons (Lucide ISC, corner slots via `place --ref-id accent-bar`), descriptions. Unicode glyphs only, no ASCII arrows.
   - **Finishing** - verify connectors match tool output, place callouts via `callouts`, fill the file description comment.
   - **Check + finalize** - `svg-infographics workflow --svg <file>` (which gates already met - never redo), then `svg-infographics check --svg <file>` with the SAME preflight flags, then `svg-infographics finalize <file>` ONCE (all validators + visual-geometry). Fix all in one pass, re-run once, cap 3. Then ONE `render-png --mode both` readback vs the 6-item checklist in workflow.md - the PNG is the only render artifact; no browser, no screenshot loops.
   - **Deck close** - `svg-infographics finalize <all files>` in one call (cross-file consistency auto on multi-file).

6. **Smooth curve through waypoints** (decision boundaries, distributions, ROC/PR, sigmoid, trajectories, organic flow) → `svg-infographics primitives spline --points "..." --samples 200`. Hand-written `C` / `Q` bezier for data curves = violation.

7. **Report**: created files, validation results, remaining items. Interactive: note where the draft deviated and why.

## Skills applied

Builder reads + applies:

- `rules/<component>.md` - per-component rule cards (card, connector, ribbon, background, timeline, icon, callout, shapes). Pulled by `preflight` from declared component types.
- `references/standards-core.md` - essentials: CSS classes, contrast, grid, structure, z-order
- `examples/INDEX.md` - geometry recipes per pattern + the one closest example
- `examples/concept_draft_deck.md` - concept-draft reference (what a good draft carries)
- `references/workflow.md` - phase process + gate checks (read at build start)
- `references/validation.md` / `references/tools.md` - on demand
