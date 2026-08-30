---
name: validate
description: Run the consolidated SVG validation gate (finalize - all checkers in one call) on one or more files. Triggers - "validate svg", "check svg", "audit svg", "validate infographic".
allowed-tools: [Read, Bash, Glob, Grep, Skill, TaskCreate, TaskUpdate]
---

# Validate SVG Infographics

## Toolchain gate (refuse only if the library is unavailable)

Before anything else run:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

**Run the CLI without touching the caller's project.** The gate above puts it on PATH, so the bare command name is the whole invocation. `uv run` instead resolves whatever project the working directory sits in and writes `uv.lock` and `.venv` into it, so if you reach for uv pass `--no-project` (`uv run --no-project <cli> ...`) - it skips project discovery, leaves the tree untouched and still finds the same PATH binary. `--no-sync` and `--frozen` are not substitutes; both still create `.venv`.

Verify the CLI runs: `svg-infographics --help`. **The gate above blocks on both failures** - an absent library (`FATAL`) and a version mismatch (`STALE`) each exit non-zero. Neither is advisory: this command documents the current plugin's flags, so a mismatched CLI may reject them and anything it does produce is unverified. Report the line and stop. No fallback, no hand-built output.


Run the consolidated validation gate on SVG files and report findings.

## Task Tracking

Create ONE task per finalize run (not per checker - finalize runs all checkers internally).

## Steps

1. **Identify targets**: glob for SVG files in the specified path

2. **Run the consolidated gate** - one call for the whole set:

   ```bash
   svg-infographics finalize <file1> [<file2> …]        # all checkers, HARD/SOFT tiers
   svg-infographics finalize <file1> --json             # machine-readable report
   ```

   finalize runs validate, overlaps, connectors, contrast, collide, alignment
   and css internally. Do NOT invoke the seven checkers separately - drill
   into a single checker (`svg-infographics overlaps --svg <file>` etc.) only
   when a specific finding needs more detail.

3. **Batch-fix protocol**: fix ALL findings in one editing pass, re-run
   finalize ONCE. Hard cap 3 iterations; report residuals and stop.

4. **Classify findings**:
   - HARD findings: real defects until individually defended (Fixed / Accepted / Checker limitation)
   - SOFT findings: fix what is cheap, acknowledge remaining layers with `--ack-class SOFT-<LAYER>='reason'`

5. **Generate `verification_checklist.md`** (if issues found):
   ```markdown
   - [ ] `<filename>` | `"<text>"` | <ratio/overlap%> | <mode>
     - **Root cause**: <description>
     - **Fix**: <specific action>
   ```

6. **Report summary**: files checked, hard/soft counts per file, top issues to fix

## Skill applied

The `svg-infographics:svg-designer` skill (fork context) reads `references/validation.md` for checker usage, severity ladder (HARD FAIL / SOFT / HINT), justification rules, pre-delivery checklist. For heavy validation work across many files, invoke it via the `Skill` tool (NOT `Agent` / `subagent_type`): `Skill(skill="svg-infographics:svg-designer", args="Validate <paths>. Run finalize, batch-fix, classify findings.")` to keep main session responsive.
