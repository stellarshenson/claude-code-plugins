# Auto Build Claw

Autonomous iteration orchestrator for Claude Code. Breaks complex work into structured phases with multi-agent review, independent gates, and auditable state.

## Architecture

```
orchestrate.py          Pure execution engine (loads YAML, manages state, runs gates)
resources/
  workflow.yaml         Iteration types: full, gc, hotfix (+ planning dependency)
  phases.yaml           Phase start/end instruction templates with {variables}
  agents.yaml           Agent definitions per phase + gate prompts
  app.yaml              All display text, CLI help, messages (~120 keys)
  model.py              Typed dataclasses + load_model() + validate_model()
  fsm.py                Finite state machine (transitions, guards, actions)
```

The Python engine is content-agnostic. To build a different skill with the same orchestration pattern, edit only the YAML files.

## Writing Objectives and Benchmarks

### Objective

The `--objective` flag takes a text string that tells the orchestrating agent what to achieve. For complex objectives, reference a file:

```bash
orchestrate.py new --type full \
  --objective "Implement the program defined in PROGRAM.md (read .claude/skills/auto-build-claw/PROGRAM.md)" \
  --iterations 3
```

**PROGRAM.md pattern** (recommended for non-trivial work):

Create a `PROGRAM.md` in the skill directory (or project root) with:
- What needs to happen (numbered items with concrete requirements)
- Files to modify (table with file, action, purpose)
- Success criteria

The orchestrating agent reads this file and uses it as the full specification. This avoids cramming long objectives into CLI arguments and keeps the spec reviewable.

### Benchmark

The `--benchmark` flag is always a **generative instruction** - text that tells Claude what to evaluate. It is NOT a shell command.

```bash
orchestrate.py new --type full \
  --objective "..." \
  --benchmark "Read BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. Report remaining [ ] count as violation score."
```

The benchmark runs during the TEST phase only. Claude reads the referenced file, evaluates each checklist item by reading code, and updates the checkmarks.

### Writing a Generative Benchmark

When the work cannot be measured programmatically (no unit tests, no numeric scores), use a **living checklist** as the benchmark. This is the standard approach for generative work like architecture changes, workflow enforcement, and documentation improvements.

**Step 1**: Create `BENCHMARK.md` with categorised `[ ]` items:

```markdown
# Project Benchmark

Score = count of `[ ]` items. Goal: 0.

## 1. Category Name

- [ ] specific verifiable condition
- [ ] another condition with file/function reference
- [ ] measurable outcome (count, presence, absence)
```

**Step 2**: Reference it in `--benchmark`:

```bash
--benchmark "Read BENCHMARK.md and evaluate each [ ] item. For each: verify by reading code. Mark [x] if passing. Add new [ ] items if discovered. Report remaining [ ] count."
```

**Writing effective checklist items**:

- Each item must be **independently verifiable** by reading code (grep, file read, import check)
- Use specific language: "function X exists in file Y" not "code is well structured"
- Reference concrete artifacts: file paths, function names, YAML keys, CLI flags
- Include both presence checks ("X exists") and absence checks ("no hardcoded Y remains")
- Group by category so progress is trackable per area
- Items should be **pass/fail** - no subjective quality judgments

**Good items**:
```markdown
- [ ] `fsm.py` exists in `resources/`
- [ ] no `if iteration == 0` checks remain in `orchestrate.py`
- [ ] `--dry-run` flag exists on `new` command
- [ ] RESEARCH exit criteria require specific files with line numbers
```

**Bad items** (subjective, unmeasurable):
```markdown
- [ ] code quality is good
- [ ] architecture is clean
- [ ] documentation is comprehensive
```

**Score tracking**: The benchmark score (count of `[ ]`) is tracked across iterations. Lower is better. The forensicist agent in REVIEW uses the trend to identify what's improving and what's stuck.

### When You Have a Programmatic Benchmark

If the work produces measurable numeric output (test scores, error counts, performance metrics), you can still use the generative approach but instruct Claude to run a command as part of the evaluation:

```bash
--benchmark "Read BENCHMARK.md, evaluate each [ ] item, then run 'make test' and report pass/fail count. Total score = unchecked items + failing tests."
```

The generative instruction can include commands to run - Claude decides whether and how to execute them. The instruction is the interface, not the command.

### Common Programmatic Benchmark Metrics

For work that produces measurable outputs, typical metrics to track:

- **Execution time** - `time make build`, latency percentiles, cold start duration
- **Accuracy** - precision/recall/F1 for ML models, mAP for object detection, BLEU/ROUGE for NLP
- **Test coverage** - `pytest --cov` percentage, uncovered lines count
- **Error rate** - exception count, failure rate over N runs, retry frequency
- **Complexity** - cyclomatic complexity (`radon cc`), cognitive complexity, function length distribution
- **Code size** - lines of code delta, dependency count, binary size
- **Resource usage** - peak memory, GPU utilisation, token count for LLM calls
- **Conformance** - lint violations (`ruff`), type errors (`mypy`), security findings (`bandit`)
- **Benchmark suite** - domain-specific test harness with numeric score (e.g., SVG quality score, routing accuracy)

### Generative vs Programmatic Benchmarks

| Aspect | Generative (checklist) | Programmatic (command) |
|--------|----------------------|----------------------|
| **Evaluator** | Claude reads and judges | Script outputs numeric score |
| **Format** | Markdown `[ ]` items in BENCHMARK.md | Shell command with stdout |
| **Score** | Count of unchecked `[ ]` items | Numeric value from stdout |
| **Best for** | Architecture, workflow, docs, config | Tests, perf, accuracy, coverage |
| **Example objective** | "Implement FSM-driven orchestrator" | "Improve model mAP to 0.85" |
| **Example benchmark** | `"Read BENCHMARK.md, evaluate [ ] items"` | `"Run pytest --tb=short, count failures"` |
| **Example item** | `[ ] no hardcoded text in orchestrate.py` | `mAP >= 0.85` (from `make eval`) |
| **Tracks progress** | Items flip `[ ]` -> `[x]` across iterations | Score improves numerically |
| **Discovers new work** | Claude adds new `[ ]` items as discovered | N/A - fixed test suite |
| **Subjectivity** | Low if items are specific, high if vague | Zero - pass/fail numeric |

**Hybrid approach** - combine both in a single `--benchmark` instruction:

```bash
--benchmark "Read BENCHMARK.md, evaluate each [ ] item. Then run 'make test && make lint'. Score = unchecked items + test failures + lint errors."
```

These can be combined with the generative checklist. The `--benchmark` instruction tells Claude to run the measurement command and incorporate the result into the overall score:

```bash
--benchmark "Read BENCHMARK.md, evaluate each [ ] item. Then run 'make benchmark' and record the numeric score. Total violations = unchecked items + (benchmark_score > threshold ? 1 : 0)."
```
