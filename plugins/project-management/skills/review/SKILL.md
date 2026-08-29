---
name: review
description: Hostile independent review of the acceptance-criteria or defects document - spawns the devils-advocate adversary the discipline calls for (analyst on criteria, qa-engineer on defects); find, fix through pm-tools, re-confirm clean
allowed-tools: [Read, Write, Bash, Agent, TaskCreate, TaskUpdate, Skill]
---

# Review

Read the `project-management` skill first for the document's own rules, then invoke the `devils-advocate:adversarial-review` skill - the single source of truth for the two modes, the rounds protocol, the spawn mechanics and the adversary personas in `adversaries/<name>.md`. Do NOT duplicate either here. This skill is only the project-management entry point into it.

Requires the `devils-advocate` plugin installed - the skill and its adversaries live there. For any other target, `/devils-advocate:adversarial-review` is the same skill with the full roster up front.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Adversary per discipline - fixed, not inferred

| Target                        | Adversary      | Lens |
|-------------------------------|----------------|------|
| `docs/acc-crit*.md`           | `analyst`      | coverage gaps, unverifiable criteria, silos, spec-vs-code drift |
| `docs/defects*.md`            | `qa-engineer`  | risk-based coverage, can-each-test-fail, triage honesty, regression tests that keep a fix fixed |

Both documents in one ask: spawn both, one lens each, in a single message so they run concurrently. This is the one review where the adversary is not asked for - the discipline picks it. A named adversary from the user overrides the table.

## What to do

1. Read the `project-management` skill, then invoke the `devils-advocate:adversarial-review` skill
2. **`TaskCreate` the review before spawning**, `TaskUpdate` it each round; `completed` only on a clean confirming round. One task per review, not per lens
3. **Spawn the `devils-advocate:adversarial-reviewer` subagent** - one per document, naming the adversary from the table and the file in its prompt. Write the prompt as if for a process that knows nothing but what you typed: the file, the discipline's rules that bind it (ids permanent, three states, severity mandatory on a defect, importance mandatory on a criterion, the log append-only), and what is locked. Never your own reasoning about the items - that is the thing under review
4. **Mode 2** (tools ON) is the default here - the document is read whole, and the reviewer needs the code to test a criterion's claim against reality
5. **Triage every finding against the document yourself.** Correctness findings (a criterion that cannot be verified, a defect with no repro, a severity or importance that does not match the item, a dangling relation) get fixed. Taste findings (wording, ordering, "this could be leaner") get a stated reason for declining, not an edit
6. **Fix through `pm-tools`, never by hand** - lock each item before you write to it (`pm-tools lock FILE --id ID --author @xx`) and unlock when you leave it, then `edit` to amend, `log` to record what the review found, `reject` with a reason for an item the review killed. The review is itself an event worth logging on the items it touched
7. **Re-confirm** - per the rounds protocol in the adversarial-review skill: never call it clean on the round that still had findings, and the criterion or defect flips to done only on a clean confirming round. A round run past that bar manufactures defects
8. **Gate** - `pm-tools check docs --strict` after the fixes
