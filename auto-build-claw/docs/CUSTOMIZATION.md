# Customization Guide

The auto-build-claw engine is content-agnostic. All domain-specific behaviour lives in YAML. To adapt it for a different project, edit the YAML files - no Python changes needed.

## Changing Phase Templates

Edit `resources/phases.yaml`. Each phase has `start` (instructions) and `end` (exit criteria) templates with `{variable}` placeholders.

Available variables: `{objective}`, `{iteration}`, `{iteration_purpose}`, `{prior_context}`, `{plan_context}`, `{prior_hyp}`, `{CMD}`, `{benchmark_info}`, `{remaining}`, `{total}`, `{agents_instructions}`, `{spawn_instruction}`.

Example - changing RESEARCH to focus on a specific domain:

```yaml
FULL::RESEARCH:
  auto_actions:
    on_complete: []
  start: |
    ## Phase: RESEARCH

    **Objective**: {objective}
    **Iteration**: {iteration}

    Focus on database schema analysis and query performance.
    Read slow query logs, analyze indexes, check for N+1 patterns.
    ...
```

## Changing Agent Definitions

Edit `resources/agents.yaml`. Each `WORKFLOW::PHASE` section has `agents:` (list of agents) and `gates:` (readback + gatekeeper prompts).

To add an agent to a phase:
```yaml
FULL::RESEARCH:
  agents:
    - name: new_agent
      number: 4
      display_name: NEW AGENT
      prompt: |
        What this agent should do...
        **READ-ONLY**: Do NOT modify any files.
```

Agent numbers must be sequential (1, 2, 3...). The engine derives spawn instructions from the count.

## Adding a Workflow Type

Edit `resources/workflow.yaml`:

```yaml
review_only:
  description: "Review existing work without new implementation"
  phases:
    - name: RESEARCH
    - name: REVIEW
    - name: RECORD
    - name: NEXT
      skippable: true
```

Phase names must match keys in `phases.yaml` (bare or `WORKFLOW::PHASE` namespaced). Add `REVIEW_ONLY::RESEARCH` in `phases.yaml` for workflow-specific templates, or let the fallback use `FULL::RESEARCH`.

## Adding a Dependency Workflow

```yaml
analysis:
  description: "Deep analysis before implementation"
  dependency: true
  phases:
    - name: RESEARCH
    - name: HYPOTHESIS
    - name: RECORD

implementation:
  depends_on: analysis
  description: "Implementation with prior analysis"
  phases:
    - name: PLAN
    - name: IMPLEMENT
    - name: TEST
    - name: RECORD
```

Dependency workflows auto-chain before the parent. They cannot be invoked directly via `--type`.

## Adding Auto-Actions

Register the action handler in `orchestrate.py`:
```python
def _action_my_action(state: dict, phase: str):
    # do something after phase completes
    pass

_AUTO_ACTION_REGISTRY["my_action"] = _action_my_action
```

Add to `_KNOWN_AUTO_ACTIONS` in `model.py` for validation.

Declare on phases in `phases.yaml`:
```yaml
FULL::IMPLEMENT:
  auto_actions:
    on_complete: [my_action]
```

## Changing Display Text

Edit `resources/app.yaml`. Every user-facing string is a template with `{variable}` placeholders. The `messages:` section has ~120 keys covering all CLI output.

## Changing Gate Prompts

Each phase declares its own gate prompts under `gates:` in `agents.yaml`:

```yaml
FULL::RESEARCH:
  gates:
    readback:
      prompt: |
        Reply PASS or FAIL + one-line reason. No tools. No files.
        PHASE: {phase} | OBJECTIVE: {objective}
        INSTRUCTIONS: {instructions}
        UNDERSTANDING: {understanding}
        Must mention: spawning 3 separate agents AND read-only constraint.
    gatekeeper:
      prompt: |
        Reply PASS or FAIL + brief reason. No tools.
        PHASE: {phase}
        EXIT CRITERIA: {exit_criteria}
        EVIDENCE: {evidence}
        Check: 3 agents spawned separately, findings specific enough to act on.
```

## Validation

After any YAML change, run:
```bash
python orchestrate.py validate
```

This checks: workflow phases resolve, agent numbering is sequential, gate prompts have required variables, reject_to targets exist, auto_action names are registered, namespaced keys resolve correctly.

For a full execution preview:
```bash
python orchestrate.py new --type full --objective "test" --iterations 2 --dry-run
```
