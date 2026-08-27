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
- `VERDICT: DO-NOT-SHIP` - at least one CRITICAL finding

Always carry a finding count and a half-sentence why: `VERDICT: SHIP (0 findings) - <half sentence>` or `VERDICT: DO-NOT-SHIP (2 findings) - <half sentence>`.

**SEVERITY** - the per-finding label, exactly three tiers: `[CRITICAL|MAJOR|MINOR]`

- `CRITICAL` - ship-blocking on its own; its presence forces DO-NOT-SHIP. MUST be load-bearing: a false claim, a nonexistent command or flag, an instruction that cannot execute, a guard with a surviving mutant, a behaviour that breaks. Taste never reaches CRITICAL, whatever its surface area
- `MAJOR` - serious, fix before ship, but does not block by itself
- `MINOR` - minor; fix when convenient. Taste / subjective observations go here, tagged with a leading `(taste)` - e.g. `[MINOR] (taste) prefer userId`

**REMEDY** - the per-finding fix with the smallest impact radius (fewest files, fewest call sites, no new public surface), stated at diff scale: this line, this assert, this clause, plus what it leaves alone and what it could break. Three personas satisfy this through an equivalent gate rather than this wording, and are not counter-examples: `architect` (its proportionality rule and "name what the fix adds" clause), `slop-hunter` (its load-bearing check before any deletion), `popular-science` (single-word remedies, no radius to bound). State a wider remedy - delete, restructure, replace - as an opportunity with its evidence, never as a mandate; the implementor weighs it against the rest of the system. A remedy larger than the defect and unjustified is itself a defect; a reflexive narrow patch over a structural cause compounds debt. Both failure modes and the evidence bar: **Remedy discipline** in SKILL.md.

**COUPLING** (the only link between the axes) - `VERDICT` = `DO-NOT-SHIP` if and only if any finding is `CRITICAL`; otherwise `SHIP`.

## What makes an adversary earn its slot

- **METHODOLOGY is the heart** - the axes THIS expert hunts that a generalist misses. Generic axes ("check for bugs") make the adversary worthless; it must encode what only this expert knows to look at
- **Make findings falsifiable** - demand the concrete artefact per finding (the file:line, the mutation that stays green, the missing branch, the standard tool that replaces the hand-rolled one). "Use a library" is not a finding
- **Cut as well as add where the lens allows** - a reviewer that only ever demands MORE is a ratchet. `architect` (axis 8) and `qa-engineer` (axis 7) both carry a first-class slop axis whose fix is deletion
- **Name the boundary** - if a sibling adversary is adjacent, say what each owns (see the boundaries note in SKILL.md), so a panel does not return the same finding three times
- **Severity discipline** - `<QUALITY CONTROL>` must force a re-check that no CRITICAL/MAJOR is mere style, and must permit a clean verdict rather than manufactured severity

## Register

Voice is free - `data-scientist` is a caveman-voiced method-shaman, `popular-science` a magazine editor with a blue pencil. A distinctive register sharpens the lens; it must never soften the output contract.

## After adding one

1. Add a row to the SKILL.md roster table - short "catches" clause plus mode, NOT a restatement of the lens
2. Add its primary trigger phrases to the SKILL.md `description` (the only discovery signal), keeping it under 1024 chars
3. If it is adjacent to an existing adversary, add the demarcation to the boundaries note
