# Remedy discipline

Oversized remedies turn a review into 1 fix → 2 defects → 3 fixes → 6 defects: every remedy is new review surface, so fixing wide pushes the branching factor above one. The growth comes from the remedies, not the findings.

- **Conservative, surgical, strategic** - smallest impact radius that removes the defect at its origin, stated at diff scale. Small and shallow is not the goal; small and terminal is
- **Surface the opportunity, never mandate the shape** - the implementor chooses
- **No unmeasured machinery** - a remedy adding a cap, guard, knob or normalisation pass must name the input that makes it necessary and the measurement showing the unguarded cost; absent both, measure-first or delete-the-need, never the guard. On record: three size ceilings added as remedies fed three rounds of findings about their own bounds before a benchmark showed removing all of them cost 1.4 s on a deliberately pathological input - 235 lines deleted
- **Say when the small fix would paper over** - advising wider needs evidence: the property the narrow fix cannot reach, the narrow fix tried, why it failed. Untried alternative is not evidence
- **Materiality first** - a remedy answers a finding that harms a user on the product's primary path with an in-universe input; a true defect on an input the product is not for gets a `NONE` materiality line and no remedy. A remedy that adds a new pass, plugin, branch, helper or data shape is named NEW MECHANISM and enters a plan only for a material CRITICAL/MAJOR
- **Only load-bearing findings block** - false claim, nonexistent command/flag, unexecutable instruction, surviving mutant, broken behaviour. Word count, structure, duplication, phrasing = `MINOR (taste)`: advisory, declined with one line, never re-litigated
