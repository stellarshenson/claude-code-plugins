# Regression patterns a fix round introduces

Observed across a real multi-round loop where a duplicated CSS resolver was consolidated onto a shared one. Every round closed its findings and shipped new defects of the SAME shape. These are the shapes. Seed them into a confirming round's prompt so the reviewer attacks the repair, not the original defect.

## The governing mechanism

**Strengthening a resolver removes the accidental filtering its weakness provided.**

The weak version failed on hard inputs and returned nothing. Downstream code treated "returned nothing" as "skip this". That skip was never written down - it was a side effect. Replace the resolver with one that succeeds on those inputs, and every guard that was accidentally satisfied becomes load-bearing and absent.

Concretely: background election read `fill` off the presentation attribute, so class-painted decorations resolved to `None` and were skipped. Resolving them through the cascade admitted them - at their untransformed coordinates, because the transform filter had never needed to be explicit. 17 false findings on shipped files, in a fix whose whole purpose was removing false findings.

Ask of any consolidation: **what did the old code fail at, and who was silently relying on that failure?**

## The six shapes

- **Partial conversion** - one caller of the shared mechanism is converted, its siblings are not. The converted half changes the inputs the unconverted half consumes, so the mixture is worse than either alone. Text fill went through the cascade while background fill, object fill, stroke, opacity and font-size did not; each produced a false verdict the un-converted code alone would not have. **Enumerate every read of the same document in the changed file, not just the one named in the finding.**

- **Half-converted record** - a struct gains a resolved value for one mode and keeps a single field consumed for both. `Background.fill` held the light plate and was scored against dark-mode text. Dormant while the field was rarely populated; universal the moment resolution started working. **For every field added for one theme/mode/branch, find the consumer that reads the old field in the other.**

- **Borrowed defaults** - rewriting adjacent lines silently replaces a specification's initial value with whatever local is in scope. `stroke-opacity` defaulted to the fill's opacity, `stroke-width` to `0.0`; the spec says `1` for both. 149 shapes lost their stroke entirely, 226 blended a solid border at a 6% wash. **Check every default touched in the diff against the specification, not against the surrounding code.**

- **Sibling property left behind** - a property and its modifier are meaningless apart. `fill` resolved through the cascade while `fill-opacity` was read from the attribute, so a documented 4%-wash plate scored as solid. **A resolved paint needs its resolved alpha; a resolved font needs its resolved size.**

- **Nth weaker copy** - the fix introduces a new local helper that re-implements a shared one with fewer cases, in the same change that consolidates two copies into one. `_cascade_opacity` covered two of the four terms the existing `_resolved_opacity` already handles, ignoring both the paint-carried alpha and every ancestor's opacity. **Grep the package for the question the new helper answers before accepting it** - and check the justification you write for the replacement, because a comment claiming the shared helper does something it does not is the next reader's trap.

- **Channel with no consumer** - the fix replaces a wrong answer with an honest signal, and emits it into a channel nothing reads. A fabricated black used to produce a (correct-by-accident) failure; refusing to guess produced silence, and the gate printed PASS over text nobody measured. **Trace the new signal to the thing that decides the exit code. A loud wrong answer is safer than a silent right one.**

## Prompting a confirming round

First, freeze the reviewed state. Hash the files under review (`md5sum`), write the hashes into the reviewer prompt, and require the reviewer to re-hash before starting and again before returning, reporting both pairs. A round over a moving tree reviews nothing: two of the source campaign's first three rounds were partly invalidated by edits landing mid-review, and every round after the freeze returned findings with reproductions against a known state. It is the one process change that measurably improved signal; cost is one command per round.

State plainly what was changed and why, then require both halves:

1. **Verify each closed finding by reproducing it** - not by reading the diff. A reviewer that accepts the author's account of a fix cannot catch a fix that is wrong in a new way.
2. **Attack what the fix broke** - name the six shapes above and ask which apply. Ask specifically: what did the old code fail at, and who relied on that failure?

Require the reviewer to say which previous findings are closed, with evidence. A round that only lists new findings gives no signal about convergence, and the loop cannot be stopped on "two consecutive clean verdicts" if nobody says what got clean.

## Stopping

Findings that are correctness defects with a reproduction get fixed. Findings that are taste get declined with the reason stated. A round whose findings are all taste is a clean round. Two consecutive clean rounds ends the loop - continuing past that rewrites prose that was not broken and the next round flags the rewrite.
