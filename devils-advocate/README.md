# devils-advocate

Critical document analysis plugin for Claude Code. Systematically critiques documents from the perspective of their toughest audience using structured pushback scenarios, risk scoring, and iterative improvement.

## Skills

| Skill | Description |
|-------|-------------|
| `devils-advocate:setup` | Build devil persona + harvest fact repository |
| `devils-advocate:evaluate` | Generate concern catalogue + baseline scorecard |
| `devils-advocate:iterate` | Apply corrections, re-score, produce versioned copy |
| `devils-advocate:run` | Full workflow end-to-end (setup -> evaluate -> iterate until done) |

## Workflow

```
/devils-advocate:setup       # 1. Build persona, harvest facts
/devils-advocate:evaluate    # 2. Generate concerns + baseline scorecard
/devils-advocate:iterate     # 3. Apply corrections, re-score (repeat)
```

Or run everything at once:

```
/devils-advocate:run          # Full workflow
```

## Artefacts

- `devils_advocate.md` - persona, concerns, scorecards (accumulated across iterations)
- `fact_repository.md` - verified claims with sources
- `<name>_v<NN>_<score>.md` - versioned corrections with embedded scorecard

## Scoring

- **Risk** = Likelihood x Impact (Fibonacci scale 1-8, max 64)
- **Score** = 0-100% per concern (how well addressed)
- **Residual** = Risk x (1 - Score)
- **Document score** = sum of residuals (minimise)
