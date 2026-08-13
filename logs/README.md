# Logs

Background job logs for this repo.

- `round8-diagnostics.log` - Round 8 mechanism diagnostic gates (A1 extraction verb-gate rejection by language, A2 multi-sentence error concentration, H-C negation asymmetry); produced by `experiments/grounding/mechanisms.py`
- `round8-a1-eval.log` - A1 head-to-head extraction evaluation (shipped vs gate-only vs SaT+gate over 639 answer docs); produced by `experiments/grounding/mechanisms.py --eval-a1`
- `round8-notebook-exec.log` - nbconvert execution of notebook 04 (H13-H16 record)
- `round8-goldv2-*.log` - gold v2 rebuild stages (units / judge haiku / judge sonnet / build / bench); produced by `experiments/grounding/gold_v2.py`
- `round9-audit.log` - Round 9 Stage 1: per-feature + per-language AUC on the non-EN gold-v2 slice, MT firing fraction; `round9.py audit`
- `round9-eval.log` - Round 9 Stage 3: shipped baseline vs retrained (5-fold OOF) slice metrics + LOLO held-out TNR; `round9.py eval`
- `round9-threshold.log` - Round 9 operating-point diagnostic: non-EN threshold sweep on OOF probabilities + LOLO at fixed non-EN thresholds; `round9.py threshold`
- `round9-retrain.log` - Round 9 Stage 2: retrain all tiers on gold v2, write experiment-copy config; `round9.py retrain`
- `round9-shipcal.log` - Round 9 ship calibration: chosen HIGH english/non-english thresholds + no-regression guard (shipped vs recalibrated on gold v2 EN/non-EN, VitaminC, held-out articles) + VitaminC up-weight recovery sweep; `round9.py shipcal`
- `round10-translate.log` - Round 10: `claude -p` Haiku translation of 120 English negatives into 9 languages (per-language counts only); `synth_mt.py translate`
- `round10-verify.log` - Round 10: `claude -p` Sonnet fidelity verification of the translations (faithful counts per language); `synth_mt.py verify`
- `round10-synthcal.log` - Round 10 integration eval: shipped vs retrain vs retrain+synthetic on the real gold v2 non-EN slice at the global threshold + LOLO; `round9.py synthcal`
- `round11-select.log` - Round 11 batch 2: select the next 120 fresh English negatives (counts only); `SYNTH_BATCH=2 synth_mt.py select`
- `round11-translate.log` - Round 11 batch 2: `claude -p` Haiku translation into 9 languages (per-language counts only); `synth_mt.py translate`
- `round11-verify.log` - Round 11 batch 2: `claude -p` Sonnet fidelity verification (faithful counts per language); `synth_mt.py verify`
- `round11-build.log` - Round 11: merge all batches into `synthetic_mt.parquet` (per-language row counts only); `synth_mt.py build`
- `round11-synthcal.log` - Round 11 integration eval over the doubled 2,119-row synthetic set (de bridge off); `round9.py synthcal`
- `round11-synthcal-de.log` - Round 11 re-eval after installing `translate-de_en` (de bridge active, 0 skips); `round9.py synthcal`
- `ci-watch-a2e3b62.log` - GitHub Actions poll for the cascade-consolidation commit a2e3b62 (30s cadence until the Build run completed success)
