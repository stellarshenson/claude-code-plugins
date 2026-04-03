# devils-advocate

Critical document analysis plugin for Claude Code. Systematically critiques documents from the perspective of their toughest audience using structured pushback scenarios, risk scoring, and iterative improvement.

## Skills

- **devils-advocate** - Build devil persona, generate concern catalogue with Fibonacci risk scoring, evaluate with scorecard, iterate corrections until residual risk minimized

## How it works

1. Define the toughest reader (persona with role, biases, triggers)
2. Harvest facts into `fact_repository.md`
3. Generate concerns scored by likelihood x impact (1-64 range)
4. Evaluate document with scorecard (0-100% per concern)
5. Propose options for high-residual concerns
6. Iterate versioned corrections until residual risk acceptable

## Trigger phrases

- "devil's advocate on this document"
- "critique this" / "scorecard"
- "how will they attack this?"
- "stress-test this for [audience]"

## Artefacts

- `devils_advocate.md` - persona, concerns, scorecard, recommendations
- `fact_repository.md` - verified claims with sources
- `<name>_v<NN>_<score>.md` - versioned corrections with embedded scorecard
