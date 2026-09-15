# methodologist research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Test can fail
- [SEP Karl Popper](https://plato.stanford.edu/entries/popper/) - corroboration counts only from risky prediction that could have failed

## Verdict ladder completeness
- [Lakens, Scheel, Isager 2018](https://doi.org/10.1177/2515245918770963) - REFUTED needs equivalence test against SESOI; p>.05 alone inconclusive

## Pre-registration adherence
- [Nosek et al. 2018](https://doi.org/10.1073/pnas.1708274114) - plan fixed before outcomes; else postdiction passed off as prediction
- [Claesen et al. 2021](https://doi.org/10.1098/rsos.211037): "Two out of 27 preregistered studies contained no deviations from the preregistration plan". Rule: preregistered label does not mean plan followed (1 of 27 disclosed all deviations, 9 disclosed none; deviations in sample size, exclusions, analysis); diff plan against code, every deviation stated in main text. Tell: n, exclusion filter or test in code absent from plan, no deviation note.

## Control adequacy
- [J. Cognition Registered Reports guidelines](https://journalofcognition.org/about/registered-reports) - pre-specify outcome-neutral checks: positive controls, no floor/ceiling effects

## Metric reference consistency
- [Lipton, Steinhardt 2018](https://arxiv.org/abs/1807.03341) - ablate each change; gains often from tuning, not claimed change

## Criterion actually exercised
- [Chicco, Jurman 2020](https://doi.org/10.1186/s12864-019-6413-7): "A potential problem with MCC lies in the fact that MCC is undefined when a whole row or column of M is zero, as it happens in the previously cited case of the trivial majority classifier". Rule: authors fill the gap - majority classifier MCC 0; all samples one class and all correct MCC +1; bar met on one-class set = arithmetic, both classes must be observed. Tell: MCC 1 or 6/6 where every ground-truth label is same class.

## Appropriate method choice
- [Nieuwenhuis et al. 2011](https://doi.org/10.1038/nn.2886) - two effects differ only via interaction test, not sig vs non-sig
- [Weissgerber et al. 2015](https://doi.org/10.1371/journal.pbio.1002128) - many distributions give same mean bar; show full data at small n

Unsourced: static threshold on path-dependent (hysteretic) phenomenon; grid coverage behind "zero everywhere" claims
