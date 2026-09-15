# data-scientist research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Pre-registration and HARKing
- [Nosek et al. preregistration 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5856500/) - hypothesis and analysis fixed before outcome data; deviations disclosed with reason

## Power and uncertainty
- [Miller error bars for evals 2024](https://arxiv.org/html/2411.00640) - CLT SE; clustered SE (>3X naive possible); paired differences; power analysis
- [Bates, Hastie, Tibshirani CV 2023](https://arxiv.org/abs/2104.00673): "standard confidence intervals for prediction error derived from cross-validation may have coverage far below the desired level". Rule: CV estimates average error over training sets, not this fitted model; fold-SE interval too narrow; nested CV for variance. Tell: "0.84 ± 0.01 (5-fold)" presented as interval of shipped model.

## Leakage and split hygiene
- [Kapoor, Narayanan leakage 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10499856/) - 8 types incl. full-data preprocessing, duplicates, temporal, non-independent samples

## Metric validity
- [Saito, Rehmsmeier PR vs ROC 2015](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432) - imbalanced data: PR plot shows positive-prediction reliability, ROC hides it
- [McDermott et al. AUROC vs AUPRC 2024](https://arxiv.org/abs/2401.06091): "AUPRC is not generally superior in cases of class imbalance". Rule: class ratio alone never justifies AUPRC; AUPRC favours gains in high-prevalence subgroups. Tell: metric switched to AUPRC citing imbalance only, no subgroup breakdown; finding demanding AUPRC for that reason.

## Robustness across seeds, splits
- [Bouthillier et al. benchmark variance 2021](https://ar5iv.labs.arxiv.org/html/2103.03098): "Bootstrapping data stands out as the most important source of variance." Rule: randomize split, init, augmentation, full HPO per run; decide on P(A>B) ≥ 0.75, not mean gap. Tell: N seeds on one fixed split, HPO run once, "A beats B" from mean.
- [Lipton, Steinhardt troubling trends 2018](https://arxiv.org/abs/1807.03341) - ablate to locate gain; gains often from tuning, not claimed change

## Similarity-score overclaim
- [Steck et al. cosine similarity 2024](https://arxiv.org/abs/2403.05440) - cosine on learned embeddings can be arbitrary, regularization-driven, non-unique

## Reproducibility and reporting
- [REFORMS checklist 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11092361/) - 32 items: code, compute, uncertainty method, justified baselines, leakage, generalizability

Unsourced: refute/confirm protocol (kill-gate before build, two-sided accept)
