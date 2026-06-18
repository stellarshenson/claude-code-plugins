# WMD Document-Distance Experiments - raising tier contrast

Experiments log for widening the gold/adversarial gap of the source-free Statement Mover's Distance (SMD) from `../wmd-docdistance-solution-sota.md`. Batch E01 ran five pre-registered levers in [`notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb`](../../notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb): one promoted (E01-H2 anisotropy removal), four refuted.

- **Branch / artefacts** - baseline `notebooks/04-kj-wmd-document-distance.ipynb`; E01 execution [`notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb`](../../notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb); design `../wmd-docdistance-solution-sota.md`
- **Data** - `data/interim/exec-summaries/ibm-ai-adoption/` (one source article, eleven summaries)

## Problem overview

Eleven executive summaries of one IBM AI-adoption article, three quality tiers, scored against the reference gold (`exec-summary-gold-opus-4-8`).

- **Tiers** - 7 gold (faithful, shared rules), 2 adv1 (information loss - numbers stripped), 2 adv2 (information noise - bloat, fabricated forecasts)
- **Size** - summaries segment to ~12 statements, the source article to 70; clouds small, exact OT is cheap
- **Baseline** - perfect ordinality (`0 / 24` violations), boundary margin only `+0.79` closeness points, contrast ratio `1.27x`
- **Core difficulty** - mmBERT embeddings are anisotropic; cosines bunch at 0.7-0.9, so the `√(2 − 2cos)` cost matrix is compressed and tiers sit close
- **Not tested** - generalisation beyond one article and one degradation design; a controlled probe, not a benchmark

## Executive summary

Five levers, one promoted (E01-H2 anisotropy removal), five variants refuted. The baseline exact SMD already orders every tier without error (`d' = 2.70`, `V = 0/24`) at 0.08 ms/pair, and no lever manufactures separation the embedding geometry does not already support.

| hypothesis | lever | mechanism | predicted | result | verdict |
|---|---|---|---|---|---|
| E01-H1 | weights | salience-weighted transport | margin up, `R` up | `V = 1`, margin negative, `R` 1.29 | Refuted |
| E01-H1b | weights | numeric-density fallback | margin up, `V = 0` | `V = 1`, margin negative, `R` 1.31 | Refuted |
| E01-H2 | embedding geometry | anisotropy removal (all-but-the-top) | dynamic range ≥ 1.5x | `DR` 3.2x, margin up, `V = 0` | **Promoted** |
| E01-H3 | cost function | angular distance `arccos` | margin up, metric kept | `d'` flat (2.72), margin down | Refuted (null) |
| E01-H4 | OT formulation | unbalanced residual | widest margin (≥ +0.040) | worse than baseline, ~120x slower | Refuted |
| E01-H5 | aggregation | tail-aware plan statistic | margin up | `V = 3`, margin sharply negative | Refuted |

**Baseline performance** (notebook 04, SMD against the reference gold)

| measure | value |
|---|---|
| mean gold → ref | 0.332 |
| mean adversarial → ref | 0.423 |
| reference contrast ratio `R` | 1.27x |
| all-pairs contrast (gold-adv / gold-gold) | 1.15x |
| boundary margin `M` | +0.79 closeness pts (+0.012 SMD) |
| dynamic range `DR` (std of → ref) | 0.057 |
| separation `d'` | 2.70 |
| ordinality violations `V` | 0 / 24 |
| gold closeness band | 73-82% |
| adversarial closeness band | 68-72% |

## Methodology and metrics

Each lever rebuilds the distance to the reference gold over all eleven summaries, recomputes the metrics, and compares to the baseline row.

- **Boundary margin** - `min(gold closeness) − max(adversarial closeness)`, closeness points on the 0-1 scale; comparable across methods, baseline `+0.79`, must stay `> 0`
- **Contrast ratio `R`** - `mean(adv → ref) / mean(gold → ref)`, scale-free, baseline `1.27x`
- **Dynamic range `DR`** - std of the ten `→ ref` distances, resolution proxy, baseline `0.057`
- **Separation `d'`** - `(mean adv − mean gold) / pooled std`, scale-free effect size, baseline `2.70`
- **Ordinality violations `V`** - count of (gold, adversarial) pairs ranked wrong, hard guardrail, must stay `0 / 24`
- **Metric guardrail** - a hypothesis claiming to be a metric must keep the triangle inequality; non-metric variants are flagged as discriminative scores

## Setup

- **Fixtures** - `data/interim/exec-summaries/ibm-ai-adoption/summaries/*.md` (11), reference `exec-summary-gold-opus-4-8`
- **Pipeline** - `sat-3l-sm` segmenter → mmBERT (mean-pooled, L2-normalized) → SMD via POT `ot.emd2`
- **Dependencies** - `wtpsplit`, `transformers`, `torch`, `ot` (POT) in the conda base kernel; GPU RTX 5000 Ada
- **Reproducibility** - fixed seed; deterministic across runs apart from minor GPU non-determinism in the encoder
- **Execution vehicle** - [`notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb`](../../notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb); each hypothesis is one toggle over the nb04 baseline

## E01 - experiment batch 1

Five independent levers, pre-registered before any run, one toggle each over the nb04 baseline, executed in [`notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb`](../../notebooks/experiments/E01-kj-wmd-contrast-hypotheses.ipynb). Composable, but tested one at a time to isolate effect.

### E01-H1 Salience-weighted transport

- **Hypothesis** - because quantified claims carry the article's signal and uniform weights dilute them, salience-weighting (IDF × numeric) will lift the boundary margin and `R ≥ 1.40` while holding `0/24` violations
- **Lever** - transport weights (baseline uniform `1/n`)
- **Mechanism** - weight each statement by salience (corpus IDF × numeric-content boost, renormalized) so quantified claims dominate and filler is discounted
- **Prediction** - adv1 (drops claims) and adv2 (pads filler) pay more; margin up, `R ≥ 1.40`
- **Acceptance bar** - margin up, `V = 0`
- **Result** - `V = 1`, margin `−0.23`, `d'` 2.47, `R` 1.292; numeric fallback E01-H1b same failure (`V = 1`, margin `−0.16`, `R` 1.309)
- **Verdict** - Refuted; up-weighting numbers pulls the number-retaining adv2 tier into the gold band and breaks ordering, fallback confirms the mechanism not IDF noise

### E01-H2 Embedding anisotropy removal

- **Hypothesis** - because mmBERT embeddings are anisotropic and statement cosines are compressed, subtracting the dominant principal component will raise distance dynamic range ≥ 1.5x while preserving `0/24` ordinality violations
- **Lever** - embedding geometry
- **Mechanism** - mean-center the statement embeddings, subtract the top 1-3 principal components (all-but-the-top), re-L2-normalize, then cost
- **Prediction** - cost matrix de-compresses, `DR ≥ 1.5x`, margin widens
- **Acceptance bar** - `DR ≥ 1.5x` baseline and `V = 0`, swept `k ∈ {1,2,3}`
- **Result** (k=1) - `DR` 0.180 = 3.2x baseline, margin `+0.92` (up from +0.79), `V = 0`, `d'` slips to 2.34, latency ~2x
- **Verdict** - Promoted; clears the `DR ≥ 1.5x` bar and widens the margin at `V = 0`, the only lever to do so; caveat - it spreads the gold band too, so `d'` drops (resolution, not a sharper boundary)

### E01-H3 Sharpened ground cost - angular distance

- **Hypothesis** - because `arccos` expands the high-cosine region where statements bunch, the angular ground cost will widen the boundary margin while keeping the metric property and `0/24` violations
- **Lever** - ground cost function
- **Mechanism** - replace `√(2 − 2cos)` with angular distance `arccos(cos) / π`, a true metric that expands the high-cosine region
- **Prediction** - more spread among near-duplicate statements, margin up, metric preserved
- **Acceptance bar** - margin up, `V = 0`, triangle inequality intact
- **Result** - `V = 0`, `d'` 2.72 (baseline 2.70), margin `+0.37` (down from +0.79), metric kept
- **Verdict** - Refuted (null); `arccos` is near-affine to `√(2 − 2cos)` at these cosines, so the ranking barely moves - a valid metric, a no-op for separation

### E01-H4 Unbalanced / partial transport residual

- **Hypothesis** - because balanced OT force-matches every statement and hides omissions and additions, unbalanced OT with a folded residual will widen the margin most (`≥ +0.040`) while holding `0/24` violations
- **Lever** - OT formulation
- **Mechanism** - unbalanced OT (marginal-relaxation `reg_m`) with the unmatched residual folded into the score (`+ √2 · residual`)
- **Prediction** - residual loads the adversarial tiers hardest, the widest margin of the five (`≥ +0.040`)
- **Acceptance bar** - margin up, `V = 0`, sweep `reg_m`
- **Result** (reg_m=2.0) - `V = 0`, margin `+0.68` (below baseline +0.79), `d'` 2.57, non-metric, ~9.4 ms/pair (~120x exact SMD)
- **Verdict** - Refuted; the boldest prediction lands worse than baseline, drops the metric property, costs two orders of magnitude more latency; both tiers share enough content that the residual does not concentrate

### E01-H5 Tail-aware aggregation

- **Hypothesis** - because a few badly-matched statements are averaged away by the mean, a p90 tail of matched cost will sharpen tier separation while holding `0/24` violations
- **Lever** - aggregation of the transport plan
- **Mechanism** - report the cost-weighted p90 of matched cost instead of the mean, surfacing the few badly-matched statements the mean averages away
- **Prediction** - the tail separates the tiers more sharply
- **Acceptance bar** - margin up, `V = 0`
- **Result** - `V = 3`, margin `−1.39`, `d'` 1.79 (baseline 2.70), the worst performer
- **Verdict** - Refuted; at ~12 statements the p90 tail is dominated by one or two noisy alignments and reorders the tiers - the mean is the right aggregator

### Results table (E01)

| hypothesis | V | margin (clos pts) | d' | R | DR | metric | ms/pair | verdict |
|---|---|---|---|---|---|---|---|---|
| baseline (SMD mean) | 0/24 | +0.79 | 2.70 | 1.273 | 0.057 | yes | 0.08 | reference |
| E01-H1 salience (IDF×num) | 1/24 | −0.23 | 2.47 | 1.292 | 0.060 | yes | 0.08 | Refuted |
| E01-H1b numeric proxy | 1/24 | −0.16 | 2.44 | 1.309 | 0.063 | yes | 0.08 | Refuted |
| E01-H2 anisotropy (k=1) | 0/24 | +0.92 | 2.34 | 1.256 | 0.180 | yes | 0.17 | **Promoted** |
| E01-H3 angular cost | 0/24 | +0.37 | 2.72 | 1.275 | 0.018 | yes | 0.10 | Refuted (null) |
| E01-H4 unbalanced (reg_m 2) | 0/24 | +0.68 | 2.57 | 1.253 | 0.067 | no | 9.4 | Refuted |
| E01-H5 tail (p90) | 3/24 | −1.39 | 1.79 | 1.123 | 0.048 | no | 0.06 | Refuted |

### Benchmarks (E01)

Latency per document-pair, exact baseline SMD = 1x, measured on the RTX 5000 Ada over the ten non-reference summaries.

- **baseline exact SMD** - 0.08 ms/pair, the reference
- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair, same solver, weights are free
- **E01-H3 angular** - 0.10 ms/pair, only the cost matrix changes
- **E01-H2 anisotropy** - 0.17 ms/pair (~2x), one extra SVD on the pooled embeddings
- **E01-H5 tail** - 0.06 ms/pair, cheapest, reuses the balanced plan
- **E01-H4 unbalanced** - 9.4 ms/pair (~120x), the majorization-minimization solver dominates

## Lessons learned

- **Baseline near the ceiling for ordering** - perfect ordinality and `d' = 2.70` leave little room; resolution (dynamic range), not the normalized boundary, is the axis with room
- **Anisotropy is the bottleneck** - the one lever that helps removes a single common principal component, de-bunches the cosines, triples dynamic range
- **Number-aware weighting is self-defeating on number-heavy sources** - both the faithful and the info-noise tiers carry the article's percentages, so up-weighting numbers pulls adversarial summaries toward gold
- **A wider mean gap is not a wider boundary** - E01-H1 raises `R` while the boundary margin turns negative; `V` catches what `R` hides
- **Heavier machinery did not pay** - unbalanced OT (non-metric, ~120x) and tail aggregation (noise at ~12 statements) both underperform the cheap exact mean

## Conclusions

- **Ships** - baseline exact SMD: metric, 0.08 ms/pair, perfect ordinality
- **Optional** - anisotropy removal (k=1) as a resolution pre-pass, ~2x latency, `d'` caveat noted
- **Thin margin is intrinsic** - all eleven summaries describe one article and share its content, so the boundary is genuinely narrow

## Next steps

- **Batch E02 (only the survivor)** - sweep the anisotropy `k` further, test a gentle numeric weight tuned to preserve `V` stacked on anisotropy removal; nothing else is worth compounding
- **Cross-fixture check** - the result holds on one article; re-run on a second source before trusting the anisotropy gain
- **Refuted, do not revisit** - salience / numeric weighting (breaks ordinality on number-heavy sources), angular cost (null), unbalanced residual (worse, slow, non-metric), tail aggregation (noise at this statement count)
