---
name: adversarial-review
description: Hostile, independent review - spawn fresh context-free `claude -p` subprocesses that try to BREAK a change. Two modes - diff bug-hunt (no tools, inline diff) and whole-repo audit (tools on - slop, brittle design, hardcodings, config drift, broken SoC). Expert adversaries seed the lens - architect, bug-hunter, qa-engineer, analyst, ux-designer, tui, data-scientist, methodologist, popular-science, devops, slop-hunter. Multi-round - find, fix, re-confirm. Use before a risky commit/merge, a UI or terminal-UI ship, a shell installer, trusting an experiment's verdicts or a green test suite, signing off a spec, or publishing docs. Triggers - "adversarial review", "red-team this", "find bugs in my change", "review before ship", "audit the architecture", "UX review", "TUI review", "shell review", "methodology review", "can this test fail", "review my tests", "readability review", "review my README/docs", "deployment review", "review my spec", "acceptance criteria review", "find gaps in the spec", "does the code match the spec", "hunt dead weight", "what can I delete", "is this over-engineered / bloated", "cut the bloat / slop", "find unnecessary code / tests / comments", "de-slop this", "check for fabricated citations".
---

# Adversarial Review

Spawn fresh, context-free `claude -p` subprocesses as hostile reviewers. A second model with no attachment to the code catches what the author rationalises away. Two complementary modes - run the one that fits the risk, or both:

- **Mode 1 - Diff bug-hunt.** No tools, inline diff, one turn, fast. Finds bugs, logic errors, security holes, broken edge cases IN a specific change
- **Mode 2 - Architecture & quality audit.** Tools ON, whole-repo, many turns. Finds systemic rot a diff cannot show - slop, brittle architecture, bad paradigms, hardcodings, config drift, broken separation of concerns. The finding is usually a RELATIONSHIP across files, invisible in any one hunk

A mode is the **HOW** (inline diff vs whole-repo, tools off/on). An **adversary** is the **WHO** - the expert lens the reviewer argues from. The default reviewer in the mode prompts is a generic hostile senior engineer; seed a specialist when the change has a specific risk surface. Modes and adversaries compose freely: any adversary runs in either mode.

Both are **multi-round**: a single pass finds, you fix, then you re-run to confirm the fix cleared it and did not open a new hole. One pass is a smoke test, not a verdict.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## When to use

- After a non-trivial feature or fix, before commit/merge
- A task/goal explicitly requires "survived adversarial review"
- Risky logic - auth, money, migrations, concurrency, data deletion, policy/permission resolution -> Mode 1 (+ Mode 2 if it touches structure)
- A change that adds config, env, labels, routes, new components, or crosses service/process boundaries -> Mode 2 (the hardcoding/SoC class of bug lives between files)
- Not for trivial mechanical edits (renames, dep bumps) - the spawn cost is not worth it

## The rounds protocol (this is the point - do not skip)

The "real deal" lesson: one pass is never the answer. A de-hardcode audit passed a `--max-turns 1` no-tools review clean, yet a tool-using whole-repo pass found a hardcoded label-key fallback duplicating a Dockerfile ENV - a silent-drift bug invisible in the diff. The fix then needed a SECOND pass to prove it was gone.

1. **Round 1 - find.** Run the reviewer (right mode). Capture findings
2. **Triage.** Confirm each finding against the code yourself - context-free reviewers raise false positives (they cannot see callers, types, invariants outside what they read). Keep the real ones
3. **Fix** the confirmed findings
4. **Round 2 - re-confirm.** Run the SAME review, PINNED to the fixes and the files they touched - never a fresh whole-repo sweep. Unpinned, a Mode 2 reviewer samples different ground each round, so "new findings" means it looked elsewhere, not that the tree regressed. It must come back clean; if your fix opened a hole, go back to step 2
5. **Loop until a full pass is clean.** Routine work is 2-3 rounds. Past 3, audit the last two remedies for radius instead of spawning another reviewer - round inflation is the symptom of oversized remedies (see **Remedy discipline**). For high-stakes work keep going until two consecutive passes are clean, or run a perspective-diverse panel. Never flip a "survived adversarial review" criterion to done on the strength of the round that still had findings - only on a clean confirming round

**Perspective-diverse panel (high stakes).** Instead of N identical reviewers, give each a distinct lens and run them concurrently - say, one on security, one on architecture/SoC, one on the riskiest invariant. Diversity catches failure modes redundancy cannot. Treat a finding as real when you confirm it, not by vote - but multiple lenses surface more to confirm.

**Cap the panel at 3** unless the user explicitly asks for more - say so when proposing one. Triage (step 2), not the spawn, is the bottleneck. Five lenses do not give five times the signal - they give a triage backlog you abandon half-done, which is how a real finding ships with the noise. Pick the 3 the target's risk surface actually has; run a second wave later if still uneasy.

**Ask which adversary when the caller names none.** State the inferred target, list the fitting candidates with their lens, recommend one, wait. The wrong lens returns a fluent review of a risk the target does not have - worse than none, because it reads like assurance. Skip only when the prompt names the adversary, or one lens obviously fits.

## Remedy discipline

Oversized remedies turn a review into 1 fix → 2 defects → 3 fixes → 6 defects: every remedy is new review surface, so fixing wide pushes the branching factor above one. Correct findings do not help - the growth comes from the remedies. Observed: one remedy rewrote a true statement about `finalize` into a false one across three sites.

- **Conservative, surgical, strategic** - smallest impact radius that actually removes the defect, never the nearest symptom. Fewest files and call sites, no new public surface; stated at diff scale (this line, this assert, this clause); landing where the defect originates so it cannot return by another path. Small and shallow is not the goal; small and terminal is
- **Surface the opportunity, do not mandate the shape** - report that the defect *can* be fixed within that radius; the implementor chooses, weighing it against the rest of the system
- **Say when the small fix would paper over** - a narrow patch on a structural cause compounds debt. Advising wider needs evidence in the finding: the property the narrow fix cannot reach, the narrow fix you tried, why it failed. An untried alternative is not evidence; absent it the small fix stands
- **Only load-bearing findings block** - a false claim, a nonexistent command or flag, an instruction that cannot execute, a surviving mutant, a broken behaviour. Word count, structure, duplication and phrasing are `MINOR (taste)`: advisory, declined with a one-line reason, never re-litigated next round

## Mode 1 - Diff bug-hunt (no tools, inline diff)

```bash
# 1. Capture ONLY the implementation diff (exclude docs, lockfiles, golden
#    snapshots, generated files - they bloat the prompt and distract the reviewer).
git diff -- path/to/src/a.py path/to/src/b.tsx ... > /tmp/impl.diff

# 2. Build the prompt: a no-tools instruction + adversarial framing + the inline diff.
{ cat /tmp/review-prompt.txt; cat /tmp/impl.diff; } > /tmp/review-full.txt

# 3. Spawn the reviewer. The flags matter (see Gotchas).
env -u CLAUDECODE claude -p "$(cat /tmp/review-full.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 1 \
  --no-session-persistence \
  > /tmp/review-result.txt 2>/dev/null < /dev/null
```

Returns in well under a minute for a ~1k-line diff. Use `run_in_background: true` if the diff is large.

Prompt template: `examples/mode1-diff-prompt.txt` - no-tools instruction + hostile-reviewer framing + priority focus list + SHIP/DO-NOT-SHIP verdict. Fill `<change>`, the context, and the focus bullets; append the inline diff.

## Mode 2 - Architecture & quality audit (tools ON, whole-repo)

This is the mode that catches the bugs living BETWEEN files. The reviewer must read and grep the real tree, so tools are granted and turns are generous. Put the prompt in a file; pass it as the argument; redirect stdin from `/dev/null`.

```bash
# Write the audit prompt to a file first, then:
cd <repo-root>
env -u CLAUDECODE claude -p "$(cat /tmp/audit-prompt.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 50 \
  --no-session-persistence \
  > /tmp/audit-result.txt 2>/dev/null < /dev/null &
```

- **Tools ON is the whole difference.** Mode 1 forbids tools; Mode 2 REQUIRES them - the reviewer greps for a pattern across the repo, reads the call sites, and judges the relationship. Without tools it sees only what you paste, which is exactly where these bugs hide
- **`--max-turns 50`** (not 1). The reviewer needs to explore - grep, open several files, cross-check. Too low and it stops mid-investigation with no verdict
- **Run it in the background** - a whole-repo audit takes minutes, not seconds
- **Scope by instruction, not by diff.** Name the in-scope directories and the excluded ones (tests, vendored, generated) in the prompt, since it reads the live tree

Prompt template: `examples/mode2-audit-prompt.txt` - reviewer role + REPO/scope + CONTEXT + the operator's audited REQUIREMENTS + the smell classes it must hunt + strict VERDICT line. Fill scope, context and requirements; it reads the live tree itself.

**Name the smell classes explicitly** - a vague "review the architecture" gets a vague answer, so the template enumerates them (slop/over-engineering, brittle architecture, security, routing, separation of concerns, hardcodings & config drift, consistency) and demands file:line evidence per finding. `adversaries/architect.md` covers the same ground as ten sharper axes - seed it when the audit is architectural. Only executable use counts as a violation, never a comment/docstring literal.

## Adversaries - pluggable expert lenses

Adversaries live in `adversaries/*.md`, one self-contained persona prompt per expert, written to be pasted straight into a spawn as the reviewer's role + methodology + output contract. Each file's `lens:` frontmatter is the authoritative one-line summary; the table below is only the index.

### Signal standard (every adversary)

Every adversary emits the SAME two-axis signal, so a panel reads uniformly:

- **VERDICT** (first line, always) - `VERDICT: SHIP (<n> findings)` or `VERDICT: DO-NOT-SHIP (<n> findings)`, plus a half-sentence why
- **SEVERITY** (per finding) - exactly `[CRITICAL|MAJOR|MINOR]`; taste / subjective notes use MINOR tagged `(taste)`
- **REMEDY** (per finding) - the fix with the smallest impact radius, at diff scale, naming what it touches and what it leaves alone. A wider remedy (delete, restructure, replace) is an opportunity to state with evidence, never a mandate - the implementor chooses. Per **Remedy discipline** above
- **Coupling** - `DO-NOT-SHIP` iff any finding is CRITICAL; otherwise `SHIP`

Canonical contract: `references/authoring-an-adversary.md`.

| Adversary | Catches | Mode |
| --- | --- | --- |
| `architect` | architecture, consistency, hardcodings & config drift, SoC, leaky abstractions, advertised-surface-vs-reality; over-engineering, gold-plating & dead weight as the primary axis, under a proportionality rule binding its own fixes | 2 |
| `bug-hunter` | runtime bugs in shell/installers/startup - quoting, `set -e`, fresh-vs-restart asymmetry, cross-platform parity, secrets hygiene, lifecycle races | 2 |
| `qa-engineer` | test STRATEGY - risk-based coverage, the confidence ladder (progressive tiers), can-each-test-fail, regression pinning, test slop to DELETE, harness fitness & reinvented wheels | 2 |
| `ux-designer` | friction & intent, visual hierarchy, focus management, motion comfort & afterimages, accessibility, desktop/mobile parity, edge states | 2 |
| `tui` | Textual/Rich internals - chrome duplication, mis-wired widgets, key propagation, focus & highlight, truecolor, headless-render verification | 2 |
| `data-scientist` | hypothesis formulation, refutation protocol, self-contained reproducibility (re-run from the doc alone), test power, data-prep & leakage, metric validity, sensitivity, blindspots | 2 |
| `methodologist` | scientific-METHOD integrity - can the test fail, does the verdict ladder span outcomes, pre-registration honoured, can the control move, is the criterion exercised | 2 |
| `popular-science` | readability for a curious generalist - jargon, unsourced claims, false vagueness, buried lede, pace, the visuals (judged against best-in-class article figures), the ending (arc-back, conclusions, next steps), simplification that broke the truth. Reviews against the shared craft canon in the `datascience` plugin | 1 |
| `devops` | containers & deploy - Dockerfile hygiene, layer cache, secrets in layers, root/privileged runtime, PID-1 signals, probes, pipeline gate integrity, env drift | 2 |
| `analyst` | specs & acceptance criteria - coverage gaps, missing edge-case fanout, unverifiable/ambiguous criteria, sibling features diverging with no stated reason (silos), spec-vs-code widows & orphans, gold plating to cut | 2 |
| `slop-hunter` | dead weight / project bloat - dead code, speculative & single-use abstractions (YAGNI), vanity & duplicate tests, comment & doc over-prose, unused deps/config; plus AI-slop tells & fabrication. Remedy = delete, gated by a load-bearing check | 2 |

**Boundaries** (so a panel does not return one finding three times):

- `tui` judges what the framework actually does; `ux-designer` judges what the user perceives
- `qa-engineer` judges the suite (why it would never have caught the bug); `bug-hunter` finds the bug itself; `methodologist` judges an experiment's verdict ladder, never a software suite
- `devops` owns the image and the pipeline; `bug-hunter` owns the script that runs inside them
- `analyst` judges whether the RIGHT thing is specified and whether the code matches the spec (widows, orphans, drift); `qa-engineer` judges whether the suite would catch a break; `architect` judges the code's internal consistency. Spec says nothing about it → `analyst`; spec says it, tests miss it → `qa-engineer`; code contradicts its own conventions → `architect`
- `analyst` (axis 5) challenges two *specs* diverging without reason; `architect` (axis 1) challenges two *implementations* diverging; `ux-designer` challenges what the divergence feels like to the user
- `architect` (axis 8), `qa-engineer` (axis 7) and `analyst` (axis 8) all carry a first-class slop axis - architect cuts code and docs, qa-engineer cuts tests, analyst cuts gold-plated criteria. `architect` alone is also bound by proportionality on its OWN recommendations: it may not prescribe a fix bigger than the defect, and never adds speculative structure
- `slop-hunter` is the dedicated cross-cutting bloat lens - "can this be DELETED?" across code, tests, comments, docs and dependencies, gated by a load-bearing check. It differs by REMEDY and SCOPE: `slop-hunter` runs an exhaustive delete pass over the whole tree, load-bearing check first; `architect` judges whether a *design* is proportionate to its problem - cutting the layer, knob or generalisation that no requirement demands, and unifying drift - so reach for `architect` when the question is "is this structure justified?" and `slop-hunter` when it is "what can go?"; `qa-engineer` judges whether the suite would catch a break (a missing test) and overlaps only when a test pays no rent; `popular-science` judges whether a lay reader finishes the prose, not whether it is padded. Fabrication (a fake citation, a hallucinated API) is `slop-hunter`'s alone. The per-adversary slop axes above stay domain-scoped; `slop-hunter` is the whole-project delete pass

### Seed an adversary into a spawn

Build the prompt as **mode mechanics + adversary body + target/scope**. The adversary supplies WHO, WHAT-TO-HUNT and the output shape; the mode supplies tools-on/off, inline-diff-vs-repo, scope and `--max-turns`. Strip the adversary's YAML frontmatter (`body() { awk 'c>=2; /^---$/{c++}' "$1"; }`) and paste the body in place of the mode prompt's generic role line.

Runnable both-modes template: `examples/seed-adversary.sh`.

Pick the mode by where the defect would live, not by the adversary: a UX afterimage bug shows in a CSS/animation diff (Mode 1) OR across the component tree (Mode 2); the architect's drift bugs almost always need Mode 2. For high stakes run several adversaries concurrently as the perspective-diverse panel above - one lens each.

### Add your own expert

The file IS the plugin - no registry, no wiring. Drop `adversaries/<name>.md` with `name`/`lens`/`default-mode` frontmatter over the tagged body, then add a row to the table above and its triggers to the `description`.

Full authoring contract, section by section: `references/authoring-an-adversary.md`.

## Gotchas (lessons learned - each cost a wasted run)

- **`env -u CLAUDECODE` is mandatory.** With `CLAUDECODE` set the SDK enters degraded mode and hangs on file ops. Strip it for every subprocess (same rule as the `acp` skill)
- **`< /dev/null` on every spawn.** Without it the subprocess waits on stdin and the result file contains only `Warning: no stdin data received...` - a silently empty review. This exact failure wasted a real run
- **Mode 1 only: forbid tools at the very top of the prompt** ("Do NOT use any tools... the COMPLETE diff is inline"). Otherwise the reviewer burns its turns trying to `Read` referenced files and dies with `Error: Reached max turns` and EMPTY output. **Mode 2 is the opposite - it MUST use tools**; never paste the forbid-tools line into a Mode 2 prompt
- **Match `--max-turns` to the mode.** Mode 1 = 1 (with the no-tools instruction it answers in one turn). Mode 2 = ~50 (it needs to explore). A low cap in Mode 2 stops it mid-investigation with no verdict
- **Mode 1: diff INLINE, never as paths.** Paths force tool use and leak repo layout instead of logic. Mode 2: no diff - it reads the tree itself; scope it by instruction
- **Scope tightly.** Mode 1: 200-800 focused implementation lines get a sharp review; a 5k-line dump gets a vague one. Mode 2: name the in/out-of-scope dirs so it does not audit vendored or generated code
- **`--no-session-persistence`** so the one-shot call does not litter `~/.claude/projects/<slug>/` with an unresumable JSONL per run
- **`2>/dev/null`** suppresses the harmless "no stdin data received" stderr that otherwise pollutes the result file
- **Soft-land on a usage-policy refusal.** The default model occasionally flags benign technical prose (words like "kill", "inject", "attack surface"). If `grep -q "violate our Usage Policy" <result>`, retry once with `--model claude-sonnet-4-20250514`; if it also refuses, surface to the user. One retry only

## After the review

- Triage, fix, re-confirm per the rounds protocol - flip a "review clean" criterion to done only on a clean confirming round. For each dismissed finding, know why it is wrong (caller guards it, type forbids it, a test covers it, env always provides it)
- A `DO-NOT-SHIP` verdict on a confirmed real (CRITICAL) issue blocks the ship; one driven only by false positives or style nits does not - say which, do not wave it away
- **Shrink the remedy before applying it** - a confirmed finding does not license the reviewer's proposed fix. If a round's CRITICALs trace to the previous round's fixes, the loop is generating its own work: shrink the last remedy rather than adding another
- Record what the review caught and how you fixed it (acc-crit log, journal) - the cross-file findings are the ones future-you reintroduces
