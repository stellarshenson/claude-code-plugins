# Lexical grounder on the cascade fixtures

Zero-shot run of the lexical verdict engine (the shipped default since v1.5.2: `calibration.mode: lexical`, `lexical_effort: high`) over the same Liu / Han / Ye fixtures the cascade was optimised on. The lexical manifolds were trained on private RAG + VitaminC data only - these corpora were never seen in training, so this measures transfer, not fit.

## Scoring

- **Fixtures** - `data/{liu,han,ye}_claims.json` + paired source texts; 14 claims per corpus, claims 01-12 expect CONFIRMED, 13-14 are fabrications and expect REJECTED
- **Verdict mapping** - CONFIRMED iff `match_type` in {exact, fuzzy, bm25, semantic}; REJECTED iff none/contradicted (same convention as the archived cascade benchmarks)
- **Metric** - per-corpus accuracy = correct / 14, plus confirmed-recall (over 12) and rejected-recall (over 2); headline = mean accuracy across the three corpora
- **Harness** - `scripts/bench_lexical.py` (core deps only, no extras; reads `data/` directly, no fixture setup)

## Results - 2026-06-10, v1.5.2, effort high

| corpus | accuracy | confirmed recall | rejected recall | errors |
|---|---|---|---|---|
| liu | 0.7857 | 0.7500 | 1.0000 | l08, l09, l10 false-rejected |
| han | 1.0000 | 1.0000 | 1.0000 | - |
| ye | 0.8571 | 0.9167 | 0.5000 | y08 false-rejected, y14 false-confirmed (fuzzy) |
| **mean** | **0.8810** | 0.8889 | 0.8333 | |

- **Reference point** - the semantic cascade scores 1.0 on these fixtures (its own optimisation target; see `BENCHMARK.md`), so the lexical tier gives up 0.12 here in exchange for CPU-only, torch-free, ~165 ms/claim and no embedding model
- **Error shape** - misses concentrate on distant paraphrases (l09/l10 are the fixture's deliberately hard rephrase cases; l08/y08 similar) - exactly the irreducibly-semantic residual the triage flag exists for; fabrication detection holds 5/6
- **Run** - `uv run python references/grounding-results/scripts/bench_lexical.py` (stdout = mean accuracy, stderr = table)
