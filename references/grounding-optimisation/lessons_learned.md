# Autobuild — Lessons Learned

Captured during the grounding-improvements program (PROGRAM.md + BENCHMARK.md,
baseline score 69.3, target 5.0). Use these notes when planning future
autobuild cycles or extending the plugin itself.

## Workflow choice

The `fast` workflow omits the `RESEARCH` and `HYPOTHESIS` phases from the
`full` workflow:

```
fast:  PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> (NEXT)
full:  RESEARCH -> HYPOTHESIS -> PLAN -> IMPLEMENT -> TEST -> REVIEW -> RECORD -> (NEXT)
```

For hypothesis-driven programs (like this one, with H1-H10 and explicit
falsifiers) `full` is the right workflow. `HYPOTHESIS` runs four agents
(contrarian, optimist, pessimist, scientist) and is exactly the
pre-implementation critique we needed. `fast` was a mistake given the program
shape - worth revisiting the decision when the next program is opened.

Workflow can't be switched mid-cycle. The decision is per-cycle.

## State survival

The `orchestrate` CLI persists phase state to disk, not memory. When the first
subagent died on a 500 API error mid-TEST, nothing was lost: `orchestrate
status` still reported `Iteration 1 / TEST in_progress / PLAN ok / IMPLEMENT
ok`, and a fresh subagent resumed cleanly without re-doing 32 minutes of
PLAN+IMPLEMENT work.

Design takeaway: state is the source of truth, agents are replaceable workers.
Any future tooling wrapped around autobuild should preserve this property.

## Gaps in what state records

The current orchestrator records which agents ran per phase and the phase
transitions. It does NOT record:

- **Per-work-item attribution** — composite score moved, but which of H1/H2/H3
  delivered? Current log can't say.
- **Predicted vs measured deltas** — each hypothesis had a prediction ("gap
  widens from 0.02 to >= 0.10"); TEST produced the actual number. Nothing
  pairs them.
- **Falsifier verdicts** — hypotheses had explicit falsifiers. Nothing records
  whether each one fired, didn't fire, or wasn't tested.
- **Phase timing** — we don't know if the 32-minute run was PLAN:20 /
  IMPLEMENT:10 / TEST:2 or the inverse.
- **Agent disagreements** — PLAN records that `architect, critic, guardian`
  all ran, but not whether critic pushed back or what the objection was.
- **Iteration scope** — which work items the planner picked up for this
  iteration is only visible in PLAN agent output, not in a structured field.

Adding even a minimal JSON sidecar with `{iteration, work_items_picked,
predicted_deltas, measured_deltas, falsifier_verdicts, phase_timings}` per
iteration would pay off for post-hoc analysis and for critic agents in later
iterations.

## Iteration log granularity

The BENCHMARK.md Iteration Log is one row per iteration with five component
values and a composite score. That's enough to detect plateau but not enough
to diagnose why a score moved. Consider either:

- A **wider** Iteration Log with one column per work item touched this round,
  or
- A **second table** (Work Items Log) keyed by hypothesis ID with the row
  fired for each iteration where that item was touched.

Either way, the composite score should not be the only scoreboard - per-
hypothesis visibility is needed to argue about what's working.

## Hypothesis document as first-class artefact

`docs/grounding_improvements_hypothesis.md` captures predicted effects,
falsifiers, and non-goals. It should be referenced by both PROGRAM.md and
BENCHMARK.md, and the TEST phase should explicitly read it and report "H1
falsifier: NOT FIRED (gap 0.14 >= 0.05 threshold)" for each hypothesis it
touched.

Future program-writer invocations: if the user says "this is hypothesis-
driven", default to writing the hypothesis doc FIRST, then PROGRAM.md
referencing it, then BENCHMARK.md referencing both.

## Bench scripts as IMPLEMENT output

Bench scripts (`scripts/bench_*.py`) were listed in BENCHMARK.md as
prerequisites but created inside IMPLEMENT phase of Iteration 1. This worked
but blurred the phase contract - TEST needs its tools to exist before it
starts. Two alternatives next time:

1. **Create all bench scripts during PLAN** so TEST has its instruments ready
   from Iteration 1 onward, or
2. **Explicitly allow IMPLEMENT to build measurement infrastructure** and
   mark those scripts as build artefacts of Iteration 1 rather than pre-
   existing tools.

Option 1 is cleaner. benchmark-writer skill could gain a "scaffold the bench
scripts as empty stubs" step.

## Commit / git policy interaction

Per user policy, the subagent cannot commit, push, tag, or publish without
explicit per-session approval. The autobuild RECORD phase nominally wants
commits. Current behaviour: the subagent writes files, RECORD passes, but
nothing is committed. This is correct but worth making explicit in the
orchestrator prompt so future runs don't surprise the user.

Recommendation: extend the orchestrator subagent prompt with a standing rule
"RECORD phase writes artefacts to disk; commits are a separate user-approved
step".

## Resume protocol after subagent death

Works cleanly as-is:

1. `orchestrate status` identifies the current phase.
2. If a phase is `in_progress`, the new subagent picks up mid-phase - no
   restart needed.
3. Code changes from previous IMPLEMENT are on disk already.
4. New subagent just needs the same original context (PROGRAM.md path,
   BENCHMARK.md path, exit conditions, constraints) plus the "resume from X"
   instruction.

Keep the resume prompt explicit: cite the orchestrator state fields verbatim
so the new subagent doesn't second-guess.

## Exit conditions that actually worked

The PROGRAM.md exit condition set - stagnation OR scope complete OR effective
optimum - is right. Stagnation at "no improvement for 2 consecutive
iterations" is the primary gate; the score target (5.0) is the floor for a
heuristic detection feature, not a hard requirement.

One refinement: "no improvement" should probably be "no improvement beyond
noise tolerance" - a 0.2-point score flicker due to a non-deterministic
embedding call shouldn't count as progress. Add a tolerance band (e.g. delta
must be >= 1.0) in future benchmarks.

## Things that were right first time

- Putting the score formula in `scripts/validate.py` as a callable CLI -
  trivial to re-check from the shell, trivial to pipe into `jq`, trivial to
  embed in CI later.
- `--baseline` / `--target` shortcuts on validate.py - they made the three
  reference points (69.3 / 5.0 / 0.0) inspectable without memorising the
  component values.
- Keeping heavy deps (torch, faiss) in the `[semantic]` extra - means the
  portability bench can swap embedding models without forcing a re-install.
- Writing the hypothesis doc before the PROGRAM - the predicted effects and
  falsifiers fed directly into the BENCHMARK metric targets.

## Checklist for next program

Before `orchestrate new`:

- [ ] Is this hypothesis-driven? If yes, use `full` not `fast`.
- [ ] Is there a hypothesis doc? If yes, reference it from PROGRAM.md.
- [ ] Are bench scripts scaffolded (even as stubs)? If no, do that before
      Iteration 1.
- [ ] Does BENCHMARK.md's Iteration Log have per-work-item columns, or only
      composite score?
- [ ] Is the exit condition's "no improvement" defined with a tolerance band?
- [ ] Has the user explicitly approved commits during RECORD, or is RECORD
      write-only this cycle?
