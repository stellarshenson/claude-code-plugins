---
name: adversarial-review
description: Run a hostile, independent review by spawning fresh `claude -p` subprocesses that try to BREAK the work - real bugs and broken edge cases (diff mode) and systemic rot: slop, brittle architecture, hardcodings, config drift, broken SoC (architecture mode). Tuned for data-science projects with four pluggable adversaries, each also fully generalist - data-scientist (hypothesis rigor, leakage, metric validity; over an experiments log / notebook / pipeline), architect (project + pipeline architecture, hardcodings, SoC, security), popular-science (readability of the article / README for a generalist), ux-designer (notebook visuals, figures, dashboards). Multi-round - find, fix, re-confirm clean. Use before trusting an experiment's conclusions, publishing a writeup, shipping a notebook UI, or a risky commit. Triggers - "adversarial review", "red-team this", "review my experiment/hypotheses", "rigor review", "audit the architecture", "readability review", "review my README/article", "UX/notebook visuals review".
---

# Adversarial Review

Spawn fresh, context-free `claude -p` subprocesses as hostile reviewers. A second model with no attachment to the code catches what the author rationalises away. There are two complementary modes - run the one that fits the risk, or both:

- **Mode 1 - Diff bug-hunt.** No tools, inline diff, one turn, fast. Finds bugs, logic errors, security holes, broken edge cases IN a specific change.
- **Mode 2 - Architecture & quality audit.** Tools ON, whole-repo, many turns. Finds systemic rot a diff can't show: slop, brittle architecture, bad paradigms, hardcodings, config drift, broken separation of concerns. The finding is usually a RELATIONSHIP across files, invisible in any one hunk.

A mode is the **HOW** (inline diff vs whole-repo, tools off/on). An **adversary** is the **WHO** - the expert lens the reviewer argues from. The default reviewer in the mode prompts is a generic hostile senior engineer; seed a specialist (architect, ux-designer, or one you add) when the change has a specific risk surface. See [Adversaries](#adversaries---pluggable-expert-lenses). Modes and adversaries compose freely: any adversary can run in either mode.

Both are **multi-round**: a single pass finds, you fix, then you re-run to confirm the fix actually cleared it (and didn't open a new hole). One pass is a smoke test, not a verdict.

## In a data science project (generalist lenses, DS surfaces)

The four shipped adversaries stay fully general; in a data science project they map onto its surfaces - run each where its risk lives, and on any generalist target too:

- **data-scientist** → the experiments log, a notebook, the data-prep pipeline, a metric / eval design - before trusting a conclusion (hypothesis rigor, refutation protocol, test power, leakage, metric validity)
- **architect** → the project + pipeline architecture, config, and repo structure (consistency, hardcodings, config drift, separation of concerns, security)
- **popular-science** → the article, story, or README that reports the work - before publishing for non-specialists (jargon, unsourced claims, the hook, the payoff, the visuals judged against best-in-class figures, an ending that closes with conclusions and next steps). A visuals pass needs Mode 2 (tools on) so the reviewer can render and view the figures
- **ux-designer** → notebook visuals, figures, and dashboards (hierarchy, attention, colour / contrast, accessibility)

## When to use

- After a non-trivial feature or fix, before commit/merge
- A task/goal explicitly requires "survived adversarial review"
- Risky logic: auth, money, migrations, concurrency, data deletion, policy/permission resolution -> Mode 1 (+ Mode 2 if it touches structure)
- A change that adds config, env, labels, routes, new components, or crosses service/process boundaries -> Mode 2 (the hardcoding/SoC class of bug lives between files)
- Not for trivial mechanical edits (renames, dep bumps) - the spawn cost isn't worth it

## The rounds protocol (this is the point - do not skip)

The "real deal" lesson: one pass is never the answer. A de-hardcode audit passed `--max-turns 1` no-tools review clean, yet a tool-using whole-repo pass found a hardcoded label-key fallback duplicating a Dockerfile ENV - a silent-drift bug invisible in the diff. The fix then needed a SECOND pass to prove it was gone.

1. **Round 1 - find.** Run the reviewer (right mode). Capture findings.
2. **Triage.** Confirm each finding against the code yourself - context-free reviewers raise false positives (they can't see callers, types, invariants outside what they read). Keep the real ones.
3. **Fix** the confirmed findings.
4. **Round 2 - re-confirm.** Run the SAME review again on the fixed tree. It must come back clean. If it finds something new (your fix opened a hole, or it explored further this time), go back to step 2.
5. **Loop until a full pass is clean.** For routine work that is usually 2 rounds. For high-stakes or "be thorough / learn from the real deal" work, keep going until two consecutive passes are clean, or run a perspective-diverse panel (below). Never flip a "survived adversarial review" / "review clean" criterion to done on the strength of the round that still had findings - only on a clean confirming round.

**Perspective-diverse panel (high stakes).** Instead of N identical reviewers, give each a distinct lens and run them concurrently: one on security, one on architecture/SoC, one on hardcodings/drift, one on the riskiest invariant. Diversity catches failure modes redundancy can't. Treat a finding as real when you confirm it, not by vote - but multiple lenses surface more to confirm.

## Mode 1 - Diff bug-hunt (no tools, inline diff)

```bash
# 1. Capture ONLY the implementation diff (exclude docs, lockfiles, golden snapshots,
#    generated files - they bloat the prompt and distract the reviewer).
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

Returns in well under a minute for a ~1k-line diff. Run `run_in_background: true` if the diff is large.

### Mode 1 prompt

```
IMPORTANT: Do NOT use any tools. Do NOT read files. The COMPLETE unified diff is
provided inline below - analyze ONLY what is shown and respond directly in your
first and only message.

You are a hostile senior reviewer doing an adversarial review of <change>. Your job
is to BREAK this code: find real bugs, logic errors, security holes, broken edge
cases and design flaws. Be skeptical and specific. Do NOT praise. Do NOT restate
what the code does. If you find nothing real, say so plainly rather than inventing nits.

<2-5 sentences of context: what the change is meant to do, the invariants it must hold>

Focus your scrutiny on, in priority order:
- <the riskiest function / the trickiest invariant>
- <auth / permission / data-loss path>
- <state, effect deps, stale closures, concurrency>

Output a numbered list. For each finding: SEVERITY (CRITICAL/HIGH/MEDIUM/LOW), the
file, the precise problem, and why it's wrong. End with a one-line verdict: SHIP or
DO-NOT-SHIP.

Here is the unified diff:

<inline diff>
```

## Mode 2 - Architecture & quality audit (tools ON, whole-repo)

This is the mode that catches the bugs living BETWEEN files. The reviewer must read and grep the real tree, so tools are granted (`--dangerously-skip-permissions`) and turns are generous. Put the prompt in a file; pass it as the argument; redirect stdin from `/dev/null`.

```bash
# Write the audit prompt to a file first (it's long - see below), then:
cd <repo-root>
env -u CLAUDECODE claude -p "$(cat /tmp/audit-prompt.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 50 \
  --no-session-persistence \
  > /tmp/audit-result.txt 2>/dev/null < /dev/null &
```

- **Tools ON is the whole difference.** Mode 1 forbids tools; Mode 2 REQUIRES them - the reviewer greps for a pattern across the repo, reads the call sites, and judges the relationship. Without tools it can only see what you paste, which is exactly where these bugs hide.
- **`--max-turns 50`** (not 1). The reviewer needs to explore: grep, open several files, cross-check. Too low and it stops mid-investigation with no verdict.
- **Run it in the background** - a whole-repo audit takes minutes, not seconds.
- **Scope by instruction, not by diff.** Tell it which directories are in scope and which to exclude (tests, vendored code, generated files) in the prompt, since it's reading the live tree.

### The smell checklist (Mode 2 hunts for these)

Tell the reviewer to hunt each class explicitly - a vague "review the architecture" gets a vague answer. Demand file:line evidence per finding.

- **Slop / over-engineering** - code, config, flags, abstractions, error handling, fallbacks, or files beyond what the task needed; speculative "flexibility"; defensive checks for impossible states; a 200-line solution to a 50-line problem. Flag anything that doesn't trace to a real requirement.
- **Brittle architecture** - load-bearing assumptions that break on rename/restart/scale; ordering or timing dependencies (works only because X happens before Y); shared mutable state; a change that "works" only in the current wiring and silently breaks if a caller moves.
- **Security paradigms** - secrets/tokens in code or logs; auth/permission checks that can be bypassed, are missing on a path, or are duplicated inconsistently; trust of client-supplied identity; least-privilege violations (a component granted more reach than its job needs); injection/escaping gaps.
- **Routing** - overlapping/ambiguous routes, wrong precedence (longest-prefix vs generic), routes that leak across tenants/users, handlers mounted under the wrong prefix, missing auth on a route, redirects that can be open-redirected.
- **Component definitions & separation of concerns** - a module doing two jobs; business logic in a handler/view; config logic in business code; a layer reaching past its neighbour (UI calling the DB, a hook embedding policy); leaky abstractions; duplicated responsibility that will drift.
- **Hardcodings & config drift** - literal values (keys, hosts, paths, names, ports, label keys) embedded in logic that should come from one source; the SAME default written in two places (e.g. a code fallback AND a Dockerfile/compose ENV) - a silent-drift bug even when the values currently match; a "default" that fires silently instead of failing loud on misconfiguration; missing validation that required config is actually provided.
- **Consistency** - the change follows one pattern here and a different one three files over; an invariant enforced in one path but not its twin.

### Mode 2 prompt skeleton

```
You are an adversarial architecture reviewer. Your ONLY job is to FIND VIOLATIONS,
not to be agreeable. Be skeptical, specific, and exhaustive. Use ripgrep and read
files directly to investigate the LIVE tree - do not guess. Do not modify anything.

REPO: <root>
IN SCOPE: <dirs/files>   OUT OF SCOPE: tests/, generated/, vendored/

CONTEXT: <2-5 sentences - what the change/feature is, the architecture it lives in,
the invariants and design rules it must hold>

REQUIREMENTS BEING AUDITED (the operator's actual intent, stated precisely):
1. <e.g. no resource KEY hardcoded in logic - all from env, single source of truth>
2. <e.g. the validator must fail hard when required config is missing/inconsistent>

Hunt for every class below; for EACH, grep the repo and read the call sites:
- Slop / over-engineering (anything beyond the requirement)
- Brittle architecture (rename/restart/ordering/shared-state assumptions)
- Security (secrets, bypassable or missing auth, least-privilege, injection)
- Routing (precedence, leakage, wrong prefix, missing auth)
- Component definition & separation of concerns (a module doing two jobs, logic in
  the wrong layer, duplicated responsibility that will drift)
- Hardcodings & config drift (literals in logic; same default in two places; silent
  fallback instead of fail-loud; missing "is it provided" validation)
- Consistency (same thing done two ways; invariant enforced on one path not its twin)

A literal that only APPEARS in a comment/docstring is NOT a violation - only executable
use counts. Distinguish a single legitimate config-module default from a duplicated one.

OUTPUT (strict):
- A bullet list of every VIOLATION: file:line, the class, the precise problem, why it's
  wrong, and the blast radius. No praise. No restating. If a candidate is benign, omit it.
- For each audited requirement, a short MET / NOT-MET assessment with evidence.
- End with EXACTLY ONE final line:
    VERDICT: NO VIOLATIONS FOUND
    VERDICT: VIOLATIONS FOUND (<n>)
```

## Adversaries - pluggable expert lenses

Adversaries live in `adversaries/*.md`, one self-contained persona prompt per expert, written to be pasted straight into a spawn as the reviewer's role + methodology + output contract. Shipped:

- **architect** (`adversaries/architect.md`) - architecture, consistency, hardcodings & config-drift, separation of concerns, leaky abstractions, security & routing smells. Built for Mode 2 (whole-repo, tools ON); use to UNIFY a convention across the tree.
- **ux-designer** (`adversaries/ux-designer.md`) - friction & intent, visual hierarchy, attention-without-alarm, focus management, motion comfort & retinal afterimages, accessibility, desktop/mobile parity, edge states. Reads component/CSS/screens; run before shipping user-facing UI.
- **data-scientist** (`adversaries/data-scientist.md`) - hypothesis formulation, refutation/confirmation protocol, test power & confidence, data-prep & leakage regime, metric validity, sensitivity, blindspots. Caveman-voiced, rigorous old method-shaman. Built for Mode 2 (whole-repo, tools ON); run over an experiments log, notebook, data-prep pipeline or metric/eval design before trusting its conclusions.
- **popular-science** (`adversaries/popular-science.md`) - readability for a curious educated generalist: jargon & unexplained notation, names dropped without context, unsourced empirical claims (every fact needs a `(Author et al., year)` or an honest "our model finds"), false vagueness (name the real technique - nine coupled differential equations, the reparameterisation trick - with a reference, not a hand-wave), story-vs-list both ways (argument-as-bullets AND a genuine enumeration hidden in prose), the hook & buried lede, concreteness, register & condescension, pace/length/paragraphing (break the wall of text into shorter paragraphs), the visuals (judged as a constructive critic against best-in-class article figures - legibility, honest ink, caption, hierarchy - advising svg-infographics:svg-designer for a rebuild), the payoff and an ending that arcs back to the opening and closes with conclusions and, where applicable, next steps, and simplification that broke the truth. Voiced as a veteran magazine editor with a blue pencil. Default Mode 1 (paste the doc inline, no tools) for a pure-prose read; use Mode 2 (tools on) when it must render and view the figures. Run over a README, story/design doc, article or explainer before publishing for non-specialist readers.

Each file is `name` / `lens` / `default-mode` frontmatter over a tagged body (`<PERSONA> <STAKES> <INCENTIVE> <CHALLENGE> <METHODOLOGY> <CONSTRAINTS> <OUTPUT FORMAT> <QUALITY CONTROL> <TASK>`). The METHODOLOGY is the heart - the axes THIS expert hunts that a generalist misses.

### Seed an adversary into a spawn

Build the prompt as **mode mechanics + adversary body + target/scope**. The adversary supplies WHO, WHAT-TO-HUNT, and the output shape; the mode supplies tools-on/off, inline-diff-vs-repo, scope, and `--max-turns`. Strip the adversary's YAML frontmatter and paste the body in place of the generic "You are a hostile senior reviewer" role line of the mode prompt.

```bash
ADV=adversaries/architect.md   # relative to this skill's directory
body() { awk 'c>=2; /^---$/{c++}' "$1"; }   # everything below the frontmatter

# --- Mode 2 (tools ON, whole-repo): architect sweep ---
{
  echo "Use ripgrep and read files directly to investigate the LIVE tree - do not guess. Do not modify anything."
  echo "REPO: $(pwd)"
  echo "IN SCOPE: <dirs/files>   OUT OF SCOPE: tests/, generated/, vendored/"
  echo "CONTEXT: <2-5 sentences - the change/feature, its architecture, the rules it must hold>"
  body "$ADV"
} > /tmp/audit-prompt.txt
# then spawn exactly as the Mode 2 block above (env -u CLAUDECODE ... --max-turns 50 ... &)
```

For **Mode 1** with an adversary, prepend the no-tools line, append the inline diff, use `--max-turns 1`:

```bash
{
  echo "IMPORTANT: Do NOT use any tools. Do NOT read files. The COMPLETE unified diff is inline below - analyze ONLY what is shown."
  body "$ADV"
  echo; echo "Here is the unified diff:"; echo
  cat /tmp/impl.diff
} > /tmp/review-full.txt
```

**popular-science adversary - append the shared craft canon.** Its review standard lives in one file, shared with the `datascience:popular-science` writer skill so critique and craft never drift: `../popular-science/references/craft-canon.md` (relative to this skill). Its target is usually a prose doc, not a diff, so build the Mode 1 prompt as no-tools line + adversary body + the doc + the canon:

```bash
{
  echo "IMPORTANT: Do NOT use any tools. Do NOT read files. The article and the craft canon are inline below - analyze ONLY what is shown."
  body adversaries/popular-science.md
  echo; echo "=== CRAFT CANON (your review standard) ==="; echo
  cat ../popular-science/references/craft-canon.md
  echo; echo "=== ARTICLE UNDER REVIEW ==="; echo
  cat /path/to/article.md
} > /tmp/review-full.txt
```

In Mode 2 (tools on, needed to render and judge figures) the reviewer reads that canon file directly - do not paste it. Editing the standard means editing that one file; both the writer and this adversary inherit it.

Pick the mode by where the defect would live, not by the adversary: a UX afterimage bug shows in a CSS/animation diff (Mode 1) OR across the component tree (Mode 2); the architect's drift bugs almost always need Mode 2. For high stakes, run several adversaries concurrently as the perspective-diverse panel above - one lens each.

### Add your own expert

The file IS the plugin - no registry, no wiring. Drop `adversaries/<name>.md` with the same shape and reference it by path when you spawn:

- Frontmatter: `name`, `lens` (one line - what it catches), `default-mode` (`1` or `2`)
- Body, tagged in this order: `<PERSONA>` who they are and why pedantic here; `<STAKES>` what one missed defect costs in the field; `<INCENTIVE>` rewarded for real defects, penalised for noise/taste; `<CHALLENGE>` assume it's flawed and prove it; `<METHODOLOGY>` the numbered axes to sweep - the expert's real value, make these specific not generic; `<CONSTRAINTS>` critique-only, cite file:line/element, separate fact from taste/judgement, terse; `<OUTPUT FORMAT>` one-line verdict + severity-ordered findings (`[BLOCKER|MAJOR|MINOR|...]`) + a short "what's already good"; `<QUALITY CONTROL>` self-check before returning; `<TASK>` one generic line, the caller fills the actual target.

`architect.md` and `ux-designer.md` are the reference implementations; the `agent-prompting-psychological` skill explains the rationale for the tagged sections.

## Gotchas (lessons learned - each cost a wasted run)

- **`env -u CLAUDECODE` is mandatory.** With `CLAUDECODE` set the SDK enters degraded mode and hangs on file ops. Strip it for every subprocess. (Same rule as the `acp` skill.)
- **`< /dev/null` on every spawn.** Without it the subprocess waits on stdin and you get a result file containing only `Warning: no stdin data received...` and nothing else - a silently empty review. (This exact failure wasted a real run.)
- **Mode 1 only: forbid tools at the very top of the prompt** ("Do NOT use any tools... the COMPLETE diff is inline"). Otherwise the reviewer burns its turns trying to `Read` referenced files and dies with `Error: Reached max turns` and EMPTY output. **Mode 2 is the opposite - it MUST use tools**; don't paste the forbid-tools line into a Mode 2 prompt.
- **Match `--max-turns` to the mode.** Mode 1 = 1 (with the no-tools instruction it answers in one turn). Mode 2 = ~50 (it needs to explore). A low cap in Mode 2 stops it mid-investigation with no verdict.
- **Mode 1: diff INLINE, never as paths.** Paths force tool use and leak repo layout instead of logic. Mode 2: no diff - it reads the tree itself; scope it by instruction.
- **Scope tightly.** Mode 1: 200-800 focused implementation lines get a sharp review; a 5k-line dump gets a vague one. Mode 2: name the in/out-of-scope dirs so it doesn't audit vendored or generated code.
- **`--no-session-persistence`** so the one-shot call doesn't litter `~/.claude/projects/<slug>/` with an unresumable JSONL per run.
- **`2>/dev/null`** suppresses the harmless "no stdin data received" stderr that otherwise pollutes the result file.
- **Soft-land on a usage-policy refusal.** The default model occasionally flags benign technical prose (words like "kill", "inject", "attack surface"). If `grep -q "violate our Usage Policy" <result>`, retry once with `--model claude-sonnet-4-20250514`; if it also refuses, surface to the user. One retry only.

## After the review

- Triage every finding against the code yourself - confirm before fixing. For each dismissed finding, be able to say why it's wrong (the caller guards it, the type forbids it, a test covers it, the env always provides it).
- Fix the real ones, then run the **re-confirm round** (protocol step 4). Do not flip a "review clean" / "survived adversarial review" criterion to done until a confirming round comes back clean.
- A `DO-NOT-SHIP` / `VIOLATIONS FOUND` verdict on a confirmed real issue blocks the ship; a verdict driven only by false positives or style nits does not - but say which, don't wave it away.
- Record what the review caught and how you fixed it (acc-crit log, journal) - the cross-file findings are the ones future-you will reintroduce.
