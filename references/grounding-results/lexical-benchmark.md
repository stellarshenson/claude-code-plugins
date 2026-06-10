# Lexical grounder on the cascade fixtures

Zero-shot run of the lexical verdict engine (the shipped default since v1.5.2: `calibration.mode: lexical`, `lexical_effort: high`) over the same Liu / Han / Ye fixtures the cascade was optimised on. The lexical manifolds were trained on private RAG + VitaminC data only - these corpora were never seen in training, so this measures transfer, not fit.

## Scoring

- **Fixtures** - `data/{liu,han,ye}_claims.json` + paired source texts; 14 claims per corpus, claims 01-12 expect CONFIRMED, 13-14 are fabrications and expect REJECTED
- **Verdict mapping** - CONFIRMED iff `match_type` in {exact, fuzzy, bm25, semantic}; REJECTED iff none/contradicted (same convention as the archived cascade benchmarks)
- **Metric** - per-corpus macro-F1 over the two classes (F1 of CONFIRMED and F1 of REJECTED, averaged - same metric as the lexical SOTA doc), accuracy shown for reference; headline = mean macro-F1 across the three corpora
- **Harness** - `scripts/bench_lexical.py` (core deps only, no extras; reads `data/` directly, no fixture setup)

## Results - 2026-06-10, v1.5.2, effort high

| corpus | macro-F1 | F1 confirmed | F1 rejected | accuracy | errors |
|---|---|---|---|---|---|
| liu | 0.7143 | 0.8571 | 0.5714 | 0.7857 | l08, l09, l10 false-rejected |
| han | 1.0000 | 1.0000 | 1.0000 | 1.0000 | - |
| ye | 0.7083 | 0.9167 | 0.5000 | 0.8571 | y08 false-rejected, y14 false-confirmed (fuzzy) |
| **mean** | **0.8075** | 0.9246 | 0.6905 | 0.8810 | |

- **Reference point** - the semantic cascade scores 1.0 on these fixtures (its own optimisation target; see `BENCHMARK.md`); with only 2 REJECTED claims per corpus the rejected-class F1 is coarse (one false-confirm halves it), so macro-F1 punishes errors here harder than accuracy does
- **Error shape** - misses concentrate on distant paraphrases (l09/l10 are the fixture's deliberately hard rephrase cases; l08/y08 similar) - exactly the irreducibly-semantic residual the triage flag exists for; fabrication detection holds 5/6
- **Run** - `uv run python references/grounding-results/scripts/bench_lexical.py` (stdout = mean macro-F1, stderr = table)

## Old grounder comparison - main v1.5.2 (`49db40c`), separate worktree

Same fixtures, same scoring, run from a clean checkout of `main` (the pre-fork grounder). Two configurations: lexical layers only (exact + fuzzy + BM25 + the adaptive_gap post-pass) and the full cascade with the e5-small embedding model (`semantic_threshold_percentile=0.02`, the archived configuration).

| grounder | engine | liu | han | ye | mean macro-F1 | mean accuracy |
|---|---|---|---|---|---|---|
| old (main) | lexical layers only | 1.0000 | 1.0000 | 0.7879 | **0.9293** | 0.9524 |
| old (main) | full cascade (+ e5-small) | 1.0000 | 1.0000 | 0.8133 | **0.9378** | 0.9762 |
| new (branch) | lexical manifold, effort high | 0.7143 | 1.0000 | 0.7083 | **0.8075** | 0.8810 |

Old-grounder error detail: lexical-only misses y07/y12 (false-rejected - fuzzy 0.51/0.54 and bm25 0.44/0.28 below thresholds); full cascade rescues both via semantic (0.88/0.89) but false-confirms the y14 fabrication (semantic 0.81 over the percentile threshold). On Liu, the old lexical-only run confirms l05/l08-l11 through the adaptive_gap post-pass labelling them `semantic` from the batch agreement-score distribution.

- **Read with the asymmetry in mind** - these fixtures were the old grounder's optimisation target (six tuning iterations to zero residual on this data, including the adaptive_gap mechanism that carries its Liu score); the new grounder is zero-shot here
- **Reverse benchmark** - on the new grounder's targets the old cascade fails: ~12% confirmation on the cross-lingual private RAG gold, no contradiction layer; the new grounder holds macro-F1 0.817 (private RAG) / 0.691 (VitaminC)
- **Net** - old cascade stronger on monolingual English paraphrase-heavy material when an embedding model is acceptable; new lexical tier wins on cross-lingual, contradiction-aware, CPU-only deployment. Missing 2x2 cell: old grounder scored on private RAG + VitaminC
