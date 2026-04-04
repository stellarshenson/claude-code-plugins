# devils-advocate

Critical document analysis plugin for Claude Code. Systematically critiques documents from the perspective of their toughest audience using structured pushback scenarios, risk scoring, and iterative improvement.

Unlike qualitative tools like [grill-me](https://github.com/mattpocock/skills/tree/main/grill-me) (Socratic interview producing shared understanding) or [Devil's Advocate Protocol](https://mcpmarket.com/tools/skills/devil-s-advocate-protocol) (one-shot adversarial reasoning), this plugin takes a semi-data-science approach: a custom persona is built for each scenario - inferred from existing conversations, emails, or meeting transcripts, or described manually (role, biases, triggers, priorities - not a generic critic), every concern gets a Fibonacci risk score (1-64), each iteration produces a measurable residual, and the score trajectory (89 -> 34 -> 12) shows convergence. Versioned files with embedded scorecards create an audit trail. The math decides priority, not gut feel.

## Skills

| Skill | Description |
|-------|-------------|
| `devils-advocate:setup` | Build devil persona + harvest fact repository |
| `devils-advocate:evaluate` | Generate concern catalogue + baseline scorecard |
| `devils-advocate:improve` | Ask user how to address concerns (suggestions / auto-apply / planning mode) |
| `devils-advocate:iterate` | Re-score after changes, update scorecard, create versioned files |
| `devils-advocate:run` | Full workflow: setup -> evaluate -> improve/iterate loop |

## Workflow

```
/devils-advocate:run          # Full workflow with improvement loop
```

Or step by step:

```
/devils-advocate:setup       # 1. Build persona, harvest facts
/devils-advocate:evaluate    # 2. Generate concerns + baseline scorecard
/devils-advocate:improve     # 3. Decide how to address (user/auto/planning)
/devils-advocate:iterate     # 4. Re-score, update scorecard (repeat 3-4)
```

## Improvement loop

The `improve -> iterate` cycle repeats until residual risk is acceptable:

1. **Improve** asks: your suggestions, auto-apply, or planning mode?
2. AI applies changes -> creates versioned file `<name>_v<NN>_<score>.md`
3. **Iterate** re-scores all concerns against the new text
4. Check: stop if residual < 10% of total, or stagnation, or user accepts

If the user edits the document outside Claude, run `iterate` directly - it re-scores the current state and updates `devils_advocate.md` without creating a versioned copy.

## Artefacts

- `devils_advocate.md` - persona, concerns, scorecards (accumulated across iterations)
- `fact_repository.md` - verified claims with sources
- `<name>_v<NN>_<score>.md` - versioned corrections with embedded scorecard (AI changes only)

## Scoring

- **Risk** = Likelihood x Impact (Fibonacci scale 1-8, max 64)
- **Score** = 0-100% per concern (how well addressed)
- **Residual** = Risk x (1 - Score)
- **Document score** = sum of residuals (minimise)
