# Grounding optimisation archive

Complete record of the six-iteration autobuild cycle that optimised the
`stellars_claude_code_plugins.document_processing` grounding tool. Score
trajectory: baseline 69.3 -> final 0.0 (BENCHMARK.md composite) /
cross-validated mean accuracy 1.0 with overfit_gap 0 across three
held-out corpora.

## Contents

### Program-level documents

- **[OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)** - the full
  narrative: end-to-end process, per-iteration trajectory, what changed
  in the code, hypothesis verdicts, honest caveats.
- **[hypothesis.md](hypothesis.md)** - the H1-H11 hypothesis document
  authored before any code change. Claims, predicted effects, explicit
  falsifiers, non-goals. The source of truth for what the program tried
  to prove.
- **[PROGRAM.md](PROGRAM.md)** - autobuild program definition. Work
  items, acceptance criteria, dependencies, constraints, exit
  conditions.
- **[BENCHMARK.md](BENCHMARK.md)** - composite score formula + full
  iteration log from baseline through Iter 6.

### Analysis and review

- **[report.md](report.md)** - forensic write-up of the cycle by an
  independent subagent that read the session transcript and project
  artefacts (2300 words).
- **[lessons_learned.md](lessons_learned.md)** - mid-cycle
  observations about autobuild workflow choices (fast vs full), state
  survival across 500-error subagent deaths, and gaps in what
  orchestrator state records.
- **[calibration_cv.json](calibration_cv.json)** - final 3-fold
  cross-validation results: per-fold winners, per-corpus defaults
  performance, aggregate statistics. Mean test accuracy 1.0, std 0.0,
  overfit_gap 0.0.

### Corpus data

Under `data/`:

| File | Size | Purpose |
|---|---:|---|
| `liu2023.txt` | 64 KB | Liu 2023 "Lost in the Middle" source text (pdftotext) |
| `liu_claims.json` | 1.6 KB | 14 labelled claims (12 real + 2 fake: l13 RoPE-Mid, l14 H100 Meta) |
| `ye2024.txt` | 117 KB | Ye 2024 "Justice or Prejudice?" source text |
| `ye_claims.json` | 1.7 KB | 14 labelled claims (12 real + 2 fake: y13 SoberJudge, y14 Google Research TPU v5) |
| `han2024.txt` | 36 KB | Han 2024 "LLM Multi-Agent Systems" source text |
| `han_claims.json` | 1.5 KB | 14 labelled claims (12 real + 2 fake: h13 SwarmLLM, h14 BlockchainBench-v3) |

Each claim has an `id` (l01..l14, y01..y14, h01..h14) and a `claim`
string. Claims numbered 01-12 are real paraphrases (expected
CONFIRMED); claims 13-14 are fabrications (expected REJECTED).

## Reproducing

Everything needed is in the project proper:

```bash
# Install with semantic extras
make requirements

# Export HF token (models are on Hugging Face)
export HF_TOKEN=<your-hf-token>

# Single-run benchmark (same as CI)
uv run python scripts/bench_liu_accuracy.py
uv run python scripts/bench_agreement_gap.py
uv run python scripts/bench_numeric.py
uv run python scripts/bench_portability.py
uv run python scripts/validate.py \
    --liu-accuracy ... --agreement-gap-attainment ... \
    --numeric-recall ... --portability-pass ... --skill-rules-present ...

# 3-fold cross-validation (96 seconds)
uv run python scripts/calibrate_cv.py

# Grid sweep a subset of config fields (sweep spec example)
uv run python scripts/calibrate.py --sweep sweep.yaml
```

The three fixture text files in `data/` match what lives under
`/tmp/grounding-demo/` and `/tmp/holdout/` during benchmark runs. To
re-run the CV from a fresh clone, copy these files back to those
paths (see `scripts/calibrate_cv.py` for the expected locations).

## Caveats worth reading before trusting the numbers

From `OPTIMIZATION_SUMMARY.md`:

- All three corpora are English academic ML papers from 2023-2024.
- All fake claims follow the "specific invented entity" pattern.
- Ye and Han claim fixtures were authored by the same person who wrote
  the grounding fixes, so the held-out tests are not as adversarial as
  a fourth corpus authored by someone else would be.
- H3 (percentile-based model-portable thresholds) was FALSIFIED for
  models intrinsically weaker on the target corpus. The portability
  win came from H11 adaptive_gap + uniform "semantic" label, not from
  H3.
- H4, H5, H6 (BM25-guided semantic re-rank, chunk-boundary expansion,
  multilingual smoke test) are deferred.

Read `report.md` for an independent forensic account and
`OPTIMIZATION_SUMMARY.md` for the self-report.
