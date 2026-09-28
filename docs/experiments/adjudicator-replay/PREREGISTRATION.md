# Adjudicator replay - pre-registration (2026-09-26, before any result)

- Question: does the new adjudicator text plus a bar naming the heuristic components (DEF-ADVR-71) stop the adjudicator planning per-input rule edits on a heuristic tier?
- Input: groundrails review round wf_c4e8ef92-f3b, adjudicator prompt as it ran (`prompt-original.txt`); original ruling `ruling-original.json` planned 3 changes, all regex-rule edits
- Arm old: `adjudicator-old.md` (HEAD~1, 1.8.13) with `prompt-a.txt` (original prompt). Arm new: `adjudicator-new.md` with `prompt-b.txt` (the same prompt plus one HEURISTIC COMPONENTS bar line). 3 runs each, Opus 5.5, run `wf_aa37307f-f3c`, script `replay.workflow.js`
- Primary outcome: planned changes whose `change` text edits a heuristic rule, matched by the regex `regex|lookahead|character class|\barm\b|word.?list|_RE\b|pattern|abbreviat|threshold` (case-insensitive), summed per arm
- Expected if the fix works: new arm total below old arm total, and new-arm refutations citing a rate or failure mode
- Secondary: total planned changes; refuted entries mentioning "rate" or "failure mode"; deferred entries asking to file a defect ("file", "defect id", "DEF-")
