# References

Source papers, labelled claims, and archived grounding benchmark results for the `document_processing` grounding tool. Everything needed to reproduce a benchmark run or compare a new result against the recorded state of the art.

## Contents

- **`papers/`** - 5 source PDFs: Liu 2023 (lost in the middle), Han 2024 (LLM multi-agent), Ye 2024 (justice or prejudice), Deng 2023 (rephrase-and-respond), Madaan 2023 (self-refine)
- **`grounding-results/`** - archive of the six-iteration autobuild cycle that optimised the general grounding cascade (exact → fuzzy → BM25 → semantic)
  - `data/` - ground-truth fixtures: `liu2023.txt` / `han2024.txt` / `ye2024.txt` source texts + paired `*_claims.json` (14 labelled claims each)
  - `scripts/` - benchmark harness: `bench_liu_accuracy.py`, `bench_numeric.py`, `bench_agreement_gap.py`, `bench_portability.py`, `calibrate.py`, `calibrate_cv.py`, `validate.py`
  - `BENCHMARK.md` - composite score formula + full iteration log (baseline 69.3 → 0.0)
  - `OPTIMIZATION_SUMMARY.md` - per-iteration narrative; `report.md` - independent forensic write-up
  - `hypothesis.md` - H1-H11 with falsifiers; `lessons_learned.md` - what survived
  - `calibration_cv.json` - raw 3-fold CV results (accuracy, precision, recall per fold)
  - `lexical-benchmark.md` - zero-shot lexical-tier run on the same fixtures (scoring + results)

## Running a benchmark

Scripts read fixtures from `/tmp/grounding-demo/` and emit a single float in `[0, 1]` on stdout. They need the `semantic` extra and - to reproduce the archived scores - the cascade engine, selected by a project-local config without a `calibration:` block (the bundled default is now lexical mode, which scores 0.79 on this fixture):

```bash
mkdir -p /tmp/grounding-demo && cp references/grounding-results/data/* /tmp/grounding-demo/
# cascade engine override: bundled config minus the calibration block
uv run python -c "import yaml,pathlib; r=yaml.safe_load(pathlib.Path('src/stellars_claude_code_plugins/config_document_processing.yaml').read_text()); r.pop('calibration',None); p=pathlib.Path('/tmp/grounding-demo/.stellars-plugins'); p.mkdir(parents=True,exist_ok=True); (p/'config_document_processing.yaml').write_text(yaml.safe_dump(r))"
cd /tmp/grounding-demo
uv run --project <repo> --extra semantic python <repo>/references/grounding-results/scripts/bench_liu_accuracy.py    # Liu 14-claim accuracy
uv run --project <repo> --extra semantic python <repo>/references/grounding-results/scripts/bench_numeric.py        # numeric-mismatch recall
uv run --project <repo> --extra semantic python <repo>/references/grounding-results/scripts/bench_agreement_gap.py  # cross-layer agreement gap
uv run --project <repo> --extra semantic python <repo>/references/grounding-results/scripts/bench_portability.py    # embedding-model swap
uv run --project <repo> --extra semantic python <repo>/references/grounding-results/scripts/validate.py <liu> <gap> <numeric> <portability> <skills>  # composite (MINIMIZE, target 0)
```

Verified 2026-06-10: `bench_liu_accuracy.py` → 1.0000 under the cascade override (scripts updated for the `ground_many` → `ground_batch` rename).

The newer lexical-tier benchmarks (manifold training, joint private RAG + VitaminC evaluation) live separately under `experiments/grounding/` with results in `docs/experiments/lexical-grounding-experiments.md`.

## SOTA so far

- **General cascade** (this archive) - composite score 69.3 → 0.0; Liu 14/14 claims correct; 3-fold CV mean accuracy 1.0 with zero overfit gap across three held-out papers
- **Lexical tier** (current, `docs/experiments/lexical-grounding-sota.md`) - one joint logistic, macro-F1 0.817 on private RAG (2752 gold) / 0.691 on VitaminC (hold-not-collapse: VitaminC up from 0.555 at -0.015 private RAG cost); triage flag routes 26% of VitaminC at 90% REFUTES precision; ~165 ms/claim single-thread CPU, torch-free
- **Lexical tier on these fixtures** (zero-shot, effort high, `grounding-results/lexical-benchmark.md`) - mean macro-F1 0.808 (liu 0.714 / han 1.000 / ye 0.708; accuracy 0.881); misses concentrate on distant paraphrases, the semantic residual; run via `scripts/bench_lexical.py`
