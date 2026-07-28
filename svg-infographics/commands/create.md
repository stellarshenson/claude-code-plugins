---
description: Create SVG infographic(s) following the full grid-first design workflow. Triggers - "create svg", "make svg", "create graphics", "make infographic", "create diagram", "make banner", "create timeline", "create flowchart".
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate]
argument-hint: "describe the infographic, e.g. 'card grid showing 4 platform modules' or 'timeline of project milestones'"
---

# Create SVG Infographic

## Toolchain gate

Run first:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Verify CLI: `svg-infographics --help`. **The gate above blocks on both failures** - an absent library (`FATAL`) and a version mismatch (`STALE`) each exit non-zero. Neither is advisory: this command documents the current plugin's flags, so a mismatched CLI may reject them and anything it does produce is unverified. Report the line and stop. No fallback, no hand-built output.

Workflow: draft → preflight → scaffold → author → check → finalize.

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
   - **Execution plane** (MANDATORY - ask, never assume; step 4 has the mechanics). Recommend the fork at ≤5 images, agents above that:
     - **In-session fork** - cheapest, but opaque: the fork IS a subagent, yet it never appears in the agent list, so an individual build cannot be watched or stopped
     - **Background agents** - each appears by name and is individually stoppable, at the cost of every agent reloading theme + rule cards

2. **Concept draft** (ALWAYS written, both modes): one ```svg-infographics``` fenced spec per image, per `examples/concept_draft_deck.md` - canvas + format preset, theme, every band, CONCRETE facts per band (real numbers, not lorem), per-image data sources, open questions. Draft = the spec the builder consumes; headless skips approval, not the draft.
   - **Interactive**: present draft(s), apply edits, do NOT generate until approved
   - **Headless**: save draft(s) into `<output-dir>` as `<context>_concept_draft.md`, proceed

3. **Theme check**: no approved swatch for this brand → run `/svg-infographics:theme` first.

4. **Dispatch the builder** per the execution plane chosen in step 1.

   Common to both - pass the absolute `<output-dir>` from step 1 verbatim; the builder writes files DIRECTLY into it as `<output-dir>/<NN-name>.svg` and must NOT prepend cwd or re-derive the folder (nests the doc path inside itself; observed bug `.../next_best_site/next_best_site/.images_next_best_site`). The approved draft goes INTO the brief - the builder builds the draft, not its own interpretation.

   **4a. In-session fork** - ONE `Skill` call per deck; sibling images for one document are ONE deck, capped at 5. Above 5, split into multiple decks and make one call each - one call per image would waste ~100KB context per fork. `Agent` / `subagent_type="svg-designer"` does NOT work: no such agent type exists, only `Skill` resolves a `context: fork` skill.
   `Skill(skill="svg-infographics:svg-designer", args="Create <deck description, all images> into the absolute directory <output-dir> - write files there verbatim, do NOT nest or re-derive the path - from the approved concept draft: <draft>. Follow the workflow per image, sequentially. Theme <swatch>. Close with the deck consistency check.")`

   **4b. Background agents** - ONE `Agent` per graphic, all dispatched in a single message so they run concurrently. Name each agent for the graphic it owns so the agent list is readable.
   An `Agent` prompt is literal text - no shell runs on it, so `${CLAUDE_PLUGIN_ROOT}` would reach the agent unexpanded and its `Read` would fail. Resolve the skill path ONCE before dispatching (`echo "${CLAUDE_PLUGIN_ROOT}/skills/svg-designer/SKILL.md"`) and paste the resulting absolute path into every prompt.
   Tradeoff to accept knowingly: a `general-purpose` agent reads the skill as a document, so it does NOT inherit the frontmatter - the `allowed-tools` narrowing does not apply.
   `Agent(subagent_type="general-purpose", model="sonnet", description="<NN> <graphic name>", prompt="Read <resolved-skill-path> and follow its workflow. Ignore its frontmatter - YOU are the builder, do not re-dispatch or fork. Build EXACTLY ONE graphic: <this image's spec from the draft>. Write it to the absolute path <output-dir>/<NN-name>.svg - that exact path, do NOT nest or re-derive it. Theme <swatch>. Run the full per-image workflow including preflight, check and finalize.")`
   Each agent finalized only its own file, so run the deck close YOURSELF once all have returned: `svg-infographics finalize <all files>` in one call - cross-file consistency is automatic on multi-file (it rides the visual layer, so `--no-visual` suppresses it).

5. **Builder workflow** (per image, both planes):
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
