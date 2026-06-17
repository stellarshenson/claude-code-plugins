# Logs

Background job logs for this repo.

- `round8-diagnostics.log` - Round 8 mechanism diagnostic gates (A1 extraction verb-gate rejection by language, A2 multi-sentence error concentration, H-C negation asymmetry); produced by `experiments/grounding/mechanisms.py`
- `round8-a1-eval.log` - A1 head-to-head extraction evaluation (shipped vs gate-only vs SaT+gate over 639 answer docs); produced by `experiments/grounding/mechanisms.py --eval-a1`
- `round8-notebook-exec.log` - nbconvert execution of notebook 04 (H13-H16 record)
- `round8-goldv2-*.log` - gold v2 rebuild stages (units / judge haiku / judge sonnet / build / bench); produced by `experiments/grounding/gold_v2.py`
