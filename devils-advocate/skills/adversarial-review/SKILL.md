---
name: adversarial-review
description: Hostile, independent review - spawn fresh context-free `claude -p` subprocesses that try to BREAK a change. Two modes - diff bug-hunt (no tools, inline diff - bugs, logic errors, security holes, edge cases) and whole-repo audit (tools on - slop, brittle design, hardcodings, config drift, broken SoC). Expert adversaries seed the lens - architect, bug-hunter, qa-engineer, ux-designer, tui, data-scientist, methodologist, popular-science, devops. Multi-round - find, fix, re-confirm. Use before a risky commit/merge, a UI or terminal-UI ship, a shell installer, trusting an experiment's verdicts or a green test suite, or publishing docs. Triggers - "adversarial review", "red-team this", "find bugs in my change", "review before ship", "audit the architecture", "consistency sweep", "UX review", "TUI review", "shell review", "installer review", "methodology review", "can this test fail", "QA review", "test review", "review my tests", "readability review", "review my README/docs", "docker review", "deployment review".
---

# Adversarial Review

Spawn fresh, context-free `claude -p` subprocesses as hostile reviewers. A second model with no attachment to the code catches what the author rationalises away. Two complementary modes - run the one that fits the risk, or both:

- **Mode 1 - Diff bug-hunt.** No tools, inline diff, one turn, fast. Finds bugs, logic errors, security holes, broken edge cases IN a specific change
- **Mode 2 - Architecture & quality audit.** Tools ON, whole-repo, many turns. Finds systemic rot a diff cannot show - slop, brittle architecture, bad paradigms, hardcodings, config drift, broken separation of concerns. The finding is usually a RELATIONSHIP across files, invisible in any one hunk

A mode is the **HOW** (inline diff vs whole-repo, tools off/on). An **adversary** is the **WHO** - the expert lens the reviewer argues from. The default reviewer in the mode prompts is a generic hostile senior engineer; seed a specialist when the change has a specific risk surface. Modes and adversaries compose freely: any adversary runs in either mode.

Both are **multi-round**: a single pass finds, you fix, then you re-run to confirm the fix cleared it and did not open a new hole. One pass is a smoke test, not a verdict.

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
4. **Round 2 - re-confirm.** Run the SAME review on the fixed tree. It must come back clean. If it finds something new (your fix opened a hole, or it explored further), go back to step 2
5. **Loop until a full pass is clean.** Routine work is usually 2 rounds. For high-stakes work keep going until two consecutive passes are clean, or run a perspective-diverse panel. Never flip a "survived adversarial review" criterion to done on the strength of the round that still had findings - only on a clean confirming round

**Perspective-diverse panel (high stakes).** Instead of N identical reviewers, give each a distinct lens and run them concurrently - one on security, one on architecture/SoC, one on hardcodings/drift, one on the riskiest invariant. Diversity catches failure modes redundancy cannot. Treat a finding as real when you confirm it, not by vote - but multiple lenses surface more to confirm.

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

| Adversary | Catches | Mode |
| --- | --- | --- |
| `architect` | architecture, consistency, hardcodings & config drift, SoC, leaky abstractions, advertised-surface-vs-reality, over-engineering & doc slop | 2 |
| `bug-hunter` | runtime bugs in shell/installers/startup - quoting, `set -e`, fresh-vs-restart asymmetry, cross-platform parity, secrets hygiene, lifecycle races | 2 |
| `qa-engineer` | test STRATEGY - risk-based coverage, the confidence ladder (progressive tiers), can-each-test-fail, regression pinning, test slop to DELETE, harness fitness & reinvented wheels | 2 |
| `ux-designer` | friction & intent, visual hierarchy, focus management, motion comfort & afterimages, accessibility, desktop/mobile parity, edge states | 2 |
| `tui` | Textual/Rich internals - chrome duplication, mis-wired widgets, key propagation, focus & highlight, truecolor, headless-render verification | 2 |
| `data-scientist` | hypothesis formulation, refutation protocol, self-contained reproducibility (re-run from the doc alone), test power, data-prep & leakage, metric validity, sensitivity, blindspots | 2 |
| `methodologist` | scientific-METHOD integrity - can the test fail, does the verdict ladder span outcomes, pre-registration honoured, can the control move, is the criterion exercised | 2 |
| `popular-science` | readability for a curious generalist - jargon, unsourced claims, false vagueness, buried lede, pace, the visuals (judged against best-in-class article figures), the ending (arc-back, conclusions, next steps), simplification that broke the truth. Reviews against the shared craft canon in the `datascience` plugin | 1 |
| `devops` | containers & deploy - Dockerfile hygiene, layer cache, secrets in layers, root/privileged runtime, PID-1 signals, probes, pipeline gate integrity, env drift | 2 |

**Boundaries** (so a panel does not return one finding three times):

- `tui` judges what the framework actually does; `ux-designer` judges what the user perceives
- `qa-engineer` judges the suite (why it would never have caught the bug); `bug-hunter` finds the bug itself; `methodologist` judges an experiment's verdict ladder, never a software suite
- `devops` owns the image and the pipeline; `bug-hunter` owns the script that runs inside them
- `architect` (axis 8) and `qa-engineer` (axis 7) both carry a first-class slop axis - architect cuts code and docs, qa-engineer cuts tests

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
- A `DO-NOT-SHIP` / `VIOLATIONS FOUND` verdict on a confirmed real issue blocks the ship; one driven only by false positives or style nits does not - say which, do not wave it away
- Record what the review caught and how you fixed it (acc-crit log, journal) - the cross-file findings are the ones future-you reintroduces
