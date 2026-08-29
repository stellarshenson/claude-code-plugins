# The rounds protocol (manual fallback - only without the Workflow tool)

Lesson on record: a de-hardcode audit passed a no-tools review clean, yet a whole-repo pass found a hardcoded label-key fallback duplicating a Dockerfile ENV - and the fix needed a SECOND pass to prove it gone.

1. **Round 1 - find.** Run the reviewer, capture findings
2. **Triage.** Confirm each finding against the code yourself - context-free reviewers raise false positives. Keep the real ones
3. **Fix** the confirmed findings
4. **Round 2 - re-confirm.** SAME review, PINNED to the fixes and touched files - never a fresh sweep (unpinned Mode 2 samples different ground each round, so "new findings" means it looked elsewhere). Two jobs, demand both in the prompt: reproduce each closed finding (a reviewer accepting the author's account cannot catch a fix wrong in a new way), and attack what the fix broke. Seed with fix-round shapes - partial conversion, borrowed defaults, sibling left behind, Nth weaker copy - and the question under them all: what did the old code fail at, and who silently relied on that failure? Full recipe: `regression-patterns.md`
5. **Loop until a full pass is clean.** Routine = 2-3 rounds. Past 3, adjudicate before spawning another reviewer - round inflation is the symptom of oversized remedies. High stakes: two consecutive clean passes. Never flip a "survived review" criterion on the round that still had findings

**Perspective-diverse panel (high stakes)** - one distinct lens each, concurrent; diversity catches what redundancy cannot. A finding is real when you confirm it, not by vote. **Cap the panel at 3** unless the user asks for more - triage, not the spawn, is the bottleneck; five lenses buy a half-abandoned backlog, which is how a real finding ships with the noise.

**Caller named no adversary → ASK.** State the inferred target, list fitting candidates, recommend one, wait. The wrong lens returns a fluent review of a risk the target does not have - worse than none, because it reads like assurance.
