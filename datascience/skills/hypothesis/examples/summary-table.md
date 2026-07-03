# User-facing summary table

The pre-registration and finding tables the skill states back in the conversation. Two rules the format enforces:

- Always a markdown pipe table, one row per hypothesis - never `label: value` stanzas or `────`-separated blocks
- Rename the claim column for what the project tests (engine, model, method, reagent, personal skill); default to `Hypothesis under test (claim)` when there is no project-specific name
- Domain jargon is fine when each term rides with a plain companion a non-specialist gets; the prediction and falsifier keep exact numbers regardless

## Technical register - jargon carried with a plain companion

Pre-registration, stated back for sign-off before any run; Verdict blank (pending).

### Pre-registration - E30 (before execution)

| ID | Engine under test (claim) | Lever (one knob) | Prediction | Falsifier (acceptance bar) | Verdict |
|----|---------------------------|------------------|------------|-----------------------------|---------|
| E30-H106 | TurboMind (LMDeploy's optimized server) out-serves vLLM's int4 once many requests pile up at once | swap engine → TurboMind AWQ-int4 vs vLLM AWQ, batch 128, 7B model | TurboMind ≤ vLLM's ~2,957 honest tok/s - no real win | Refuted unless TurboMind ≥ 1.15× vLLM AWQ b128; killed-at-gate if it won't build on the sm_120 GPU | pending |
| E30-H107 | TurboMind's engine tricks push a single request past the speed ceiling every stack shares | LMDeploy batch-1 decode, 7B-int4, vs the stack-agnostic 213-226 tok/s band | lands inside the 213-226 tok/s band | Refuted unless batch-1 ≥ 250 tok/s; killed if it lands inside the band | pending |

Finding, same rows once results exist; Verdict filled with the number that justifies it.

### Finding - E30 (after execution)

| ID | Engine under test (claim) | Lever (one knob) | Prediction | Falsifier (acceptance bar) | Verdict |
|----|---------------------------|------------------|------------|-----------------------------|---------|
| E30-H106 | TurboMind (LMDeploy's optimized server) out-serves vLLM's int4 once many requests pile up at once | swap engine → TurboMind AWQ-int4 vs vLLM AWQ, batch 128, 7B model | TurboMind ≤ vLLM's ~2,957 honest tok/s - no real win | Refuted unless TurboMind ≥ 1.15× vLLM AWQ b128; killed-at-gate if it won't build on the sm_120 GPU | Refuted (0.98× vLLM, 2,910 tok/s) |
| E30-H107 | TurboMind's engine tricks push a single request past the speed ceiling every stack shares | LMDeploy batch-1 decode, 7B-int4, vs the stack-agnostic 213-226 tok/s band | lands inside the 213-226 tok/s band | Refuted unless batch-1 ≥ 250 tok/s; killed if it lands inside the band | Refuted (221 tok/s, inside band) |

## Plain register - named subject, no jargon needed

When the subject is a person or an everyday skill, the claim reads like a colleague's sentence and needs no gloss.

### Finding - E01 (after execution)

| ID | Hypothesis under test (claim) | Lever (one knob) | Prediction | Falsifier (acceptance bar) | Verdict |
|----|--------------------------------|------------------|------------|-----------------------------|---------|
| E01-H1 | Konrad explains a model so a non-technical listener actually understands it | plain-analogy explanation vs raw scikit-learn docstring, same model + listener | comprehension C ≥ 4/5 in ≤ 3 min; docstring baseline ~1/5 | Refuted unless mean C ≥ 4.0 and explanation ≤ 3 min (killed if docstring alone ≥ 4/5) | Kept (mean C=4.3) |
| E01-H2 | Konrad's debugging intuition reaches the fix faster than blind print() spam | hypothesis-first debugging vs print()-carpet-bomb, same bug set | median time S ≤ 0.5x baseline; 0 new regressions | Refuted unless median S ≤ 0.5x and 0 regressions introduced | Refuted (S=0.7×) |
| E01-H3 | Konrad's task-time estimates are actually calibrated, not optimistic | experience-anchored estimate vs flat '2 days' for everything, same tasks | hit rate E ≥ 60% within ±25%, bias within ±0.20; baseline E ≤ 20% | Refuted unless E ≥ 60% and bias within ±0.20 (bias guardrail catches optimism) | Refuted (E=41%) |
