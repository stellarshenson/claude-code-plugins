# Authoring an adversary

The file IS the plugin - no registry, no wiring. Drop `adversaries/<name>.md` and reference it by path when you spawn. `architect.md` and `ux-designer.md` are the reference implementations; the `agent-prompting-psychological` skill explains the rationale for the tagged sections.

## Frontmatter

- `name` - lowercase-hyphen, matches the filename
- `lens` - ONE line, what it catches. This is the source of truth the SKILL.md roster table indexes; write it to be read there
- `default-mode` - `1` (inline diff, no tools) or `2` (whole-repo, tools ON)

## Body - tagged sections, in this order

| Tag | Contents |
| --- | --- |
| `<PERSONA>` | who they are, why pedantic HERE - concrete war stories beat adjectives |
| `<STAKES>` | what ONE missed defect costs in the field |
| `<INCENTIVE>` | rewarded for real defects, penalised for noise and taste |
| `<CHALLENGE>` | assume it is flawed and prove it; what to default to flagging |
| `<METHODOLOGY>` | the numbered axes to sweep - the expert's real value |
| `<CONSTRAINTS>` | critique-only, cite file:line, separate fact from judgement, terse |
| `<OUTPUT FORMAT>` | `VERDICT: SHIP`/`DO-NOT-SHIP` first line + severity-ordered `[CRITICAL|MAJOR|MINOR]` findings, each carrying its minimal REMEDY, + "what's already good" (see Signal standard below) |
| `<QUALITY CONTROL>` | self-check before returning |
| `<TASK>` | one generic line; the caller fills the actual target |

## Signal standard (mandatory, every adversary)

Two orthogonal axes, identical for every adversary and both mode templates. This is the lock: every adversary's `<OUTPUT FORMAT>` MUST emit the verdict as its first line and use ONLY these three severity labels.

**VERDICT** - the one-line ship signal, the FIRST line of every review. Exactly two values:

- `VERDICT: SHIP` - no CRITICAL findings; the artifact is good to ship / publish / trust (MAJOR/MINOR may remain, to be fixed, but none blocks)
- `VERDICT: DO-NOT-SHIP` - at least one CRITICAL or MAJOR finding

Always carry a finding count and a half-sentence why: `VERDICT: SHIP (0 findings) - <half sentence>` or `VERDICT: DO-NOT-SHIP (2 findings) - <half sentence>`.

**SEVERITY** - the per-finding label, exactly three tiers: `[CRITICAL|MAJOR|MINOR]`

- `CRITICAL` - ship-blocking on its own; its presence forces DO-NOT-SHIP. MUST be load-bearing: a false claim, a nonexistent command or flag, an instruction that cannot execute, a guard with a surviving mutant, a behaviour that breaks. Taste never reaches CRITICAL, whatever its surface area
- `MAJOR` - serious and ship-blocking: it forces DO-NOT-SHIP exactly as CRITICAL does, and differs only in standing alone being repairable within the round rather than sinking the design
- `MINOR` - minor; fix when convenient. Taste / subjective observations go here, tagged with a leading `(taste)` - e.g. `[MINOR] (taste) prefer userId`

**MATERIALITY** - the per-finding line, set before the severity: who is harmed, doing what the product is for, on which in-universe input - or `NONE`, which fixes the severity at `MINOR` (out of bar). The rule lives in `agents/adversarial-reviewer.md`; every adversary's `<OUTPUT FORMAT>` carries the line beside the remedy.

**REMEDY** - the per-finding fix with the smallest impact radius (fewest files, fewest call sites, no new public surface), stated at diff scale: this line, this assert, this clause, plus what it leaves alone and what it could break. Three personas satisfy this through an equivalent gate rather than this wording, and are not counter-examples: `architect` (its proportionality rule and "name what the fix adds" clause), `slop-hunter` (its load-bearing check before any deletion), `popular-science` (single-word remedies, no radius to bound). The failure modes and the evidence bar: `remedy-discipline.md`.

**COUPLING** (the only link between the axes) - `VERDICT` = `DO-NOT-SHIP` if and only if any finding is `CRITICAL` or `MAJOR`; otherwise `SHIP`. The verdict is a pure function of the severity mix - a caller (or `review-tools findings`) recomputes it from the findings and flags a report whose verdict line disagrees, so never let prose judgement leak into the verdict: put it in the severities.

## What makes an adversary earn its slot

- **METHODOLOGY is the heart** - the axes THIS expert hunts that a generalist misses. Generic axes ("check for bugs") make the adversary worthless; it must encode what only this expert knows to look at
- **Make findings falsifiable** - demand the concrete artefact per finding (the file:line, the mutation that stays green, the missing branch, the standard tool that replaces the hand-rolled one). "Use a library" is not a finding
- **Cut as well as add where the lens allows** - a reviewer that only ever demands MORE is a ratchet. `architect` (axis 8) and `qa-engineer` (axis 7) both carry a first-class slop axis whose fix is deletion
- **Name the boundary** - if a sibling adversary is adjacent, say what each owns (see Boundaries between lenses below), so a panel does not return the same finding three times
- **Severity discipline** - `<QUALITY CONTROL>` must force a re-check that no CRITICAL/MAJOR is mere style, and must permit a clean verdict rather than manufactured severity

## Boundaries between lenses

So a panel does not return one finding three times:

- `tui` judges what the framework does; `ux-designer` what the user perceives
- `bug-hunter` finds the bug; `qa-engineer` judges why the suite missed it; `methodologist` judges an experiment's verdict ladder, never a software suite
- `devops` owns image and pipeline; `bug-hunter` owns the script inside them
- Spec says nothing about it → `analyst`; spec says it, tests miss it → `qa-engineer`; code contradicts its own conventions → `architect`. Two *specs* diverging → `analyst`; two *implementations* → `architect`; how the divergence feels → `ux-designer`
- The instruction layer as an instrument (instruction files, skills, agent prompts, tool descriptions, workflow graphs, loops) → `ai-engineer`; the code it steers → `architect`; spec against code → `analyst`; the product's own test suite → `qa-engineer`. On deletion the two split by readership: `slop-hunter` cuts what nothing reads, `ai-engineer` cuts what the agent reads and does not need
- Slop: `architect` judges whether a *design* is proportionate ("is this structure justified?"); `slop-hunter` runs the exhaustive whole-tree delete pass ("what can go?"), load-bearing check first; `qa-engineer` cuts only tests paying no rent. On a diff, a hunk no requirement reaches is `slop-hunter`'s (a fact: revert); a construct a requirement reaches but that is bigger than needed is `architect`'s proportionality call (a judgement). Fabrication (fake citation, hallucinated API or package, a fake pass, an unverified verification claim) is `slop-hunter`'s alone

## Register

Voice is free - `data-scientist` is a caveman-voiced method-shaman, `popular-science` a magazine editor with a blue pencil. A distinctive register sharpens the lens; it must never soften the output contract.

## After adding one

1. Add a row to the SKILL.md roster table - short "catches" clause plus mode, NOT a restatement of the lens
2. Add its primary trigger phrases to the SKILL.md `description` (the only discovery signal), keeping it under 1024 chars
3. If it is adjacent to an existing adversary, add the demarcation to Boundaries between lenses above
