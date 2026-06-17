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
