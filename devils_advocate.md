# Devil's Advocate - Agent Lifecycle Architecture

## The Devil

**Role**: Workflow architect responsible for orchestrator FSM consistency
**Cares about**: (1) Harmony between YAML definitions and runtime behavior, (2) Consistency with established FSM patterns (entry/execution/exit), (3) Correctness of metadata consumed by the engine
**Style**: Meticulous, pattern-driven. Evaluates against formal FSM lifecycle model. Notices any semantic mismatch between what a key NAME says and what the code DOES with the data under it.
**Default bias**: If the YAML says `on_end` but the data is used during execution, the YAML is lying. Lying metadata is worse than missing metadata.
**Triggers**: Inconsistency between naming and behavior. Backward-compat hacks that preserve wrong structure. Half-measures that move data without fixing the model.
**Decision**: Approve/reject the program's design and scope
**Source**: user-described persona

---

## 1. "The program moves agents but doesn't fix the model's lifecycle semantics"

**Likelihood: 8** | **Impact: 8** | **Risk: 64**

**Their take**: Moving agents from `gates.on_end.agents` to a phase-level `agents` key is cosmetic if the model still treats them the same way. The `_build_agents_and_gates` function name says "agents AND gates" - it processes both from the same raw dict. After this change, agents will come from a different YAML location but the model dataclass `Model.agents` is still a flat `dict[str, list[Agent]]` with no lifecycle annotation. The engine has no concept of "execution" as a lifecycle point. You're moving furniture without renovating the room.

A proper FSM lifecycle has three distinct data channels:
- `on_start` -> entry actions/gates
- `execution` -> work performed during the phase
- `on_end` -> exit actions/gates

The program proposes agents at phase level, but that's neither `on_start`, `execution`, nor `on_end`. It's "somewhere". The model should have `Model.execution_agents` separate from `Model.gates`, not just `Model.agents` accessed the same way from a different YAML key.

**Reality**: The program does move agents to a semantically better location (phase-level rather than inside gates.on_end). The orchestrator already uses agents in two distinct ways: instructions at START, validation at END. This dual use is the actual semantic truth - agents span the phase.

**Response**: The program should either (a) add an explicit `execution` lifecycle section to the YAML and model, or (b) acknowledge that phase-level is the correct semantic location because agents span the full phase. Option (b) is simpler and honest. But the program should state WHY phase-level is correct, not just that on_end is wrong.

---

## 2. "The gate_type_sets will lose agent information"

**Likelihood: 5** | **Impact: 8** | **Risk: 40**

**Their take**: Currently `_build_agents_and_gates` populates `gate_type_sets["end"]` with gate types found under `on_end`. Since agents are ALSO under `on_end`, the function processes them in the same loop. When agents move to phase level, they're no longer iterated in the gate lifecycle loop. Does any downstream code depend on agents being discovered alongside end-gate types?

Looking at model.py line 225: `gate_type_sets.get(bucket, set()).add(gate_type)` - this adds the gate TYPE name (like "gatekeeper") not the agent names. Agents are filtered out at line 217: `if gate_type == "agents": continue`. So agents are explicitly SKIPPED from gate type discovery. The concern is unfounded.

Wait - but `gate_type == "agents"` is the filter that prevents agents from being treated as a gate type. If agents move to phase level, this filter becomes dead code. Dead code is a maintenance trap.

**Reality**: The `if gate_type == "agents": continue` filter at line 217 exists precisely because agents are co-located with gates under `on_end`. Moving agents to phase level makes this filter unnecessary. The program should note this dead code for removal.

**Response**: Add to program: remove the `if gate_type == "agents": continue` filter after agents move, since no non-gate data will exist under `gates.on_end`.

---

## 3. "The program doesn't address the on_end agents backward compat correctly"

**Likelihood: 8** | **Impact: 5** | **Risk: 40**

**Their take**: The program says "Preserve backward compatibility: if a phase still has agents under on_end, the model should still load them (fallback)." But model.py line 214-215 currently makes `on_end.agents` the PRIMARY source, overriding phase-level. The program says agents should be at phase level as PRIMARY. So the priority must REVERSE:

Current: phase-level (fallback) < on_end (primary)
Target: phase-level (primary) > on_end (fallback)

The program doesn't explicitly state this priority reversal. An implementer reading "fallback" might keep on_end as primary and phase-level as fallback, which is the CURRENT behavior and changes nothing.

**Reality**: The program's constraint says "if a phase still has agents under on_end, the model should still load them (fallback)" - this IS stating on_end as fallback. But it doesn't say "phase-level is primary". The ambiguity is real.

**Response**: Make explicit in program: "Phase-level `agents` key is the PRIMARY source. `gates.on_end.agents` is the FALLBACK for backward compatibility only. Reverse the current priority in `_build_agents_and_gates`."

---

## 4. "The YAML structure still has semantic inconsistency in agent roles"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: Not all agents serve the same purpose. Execution agents (researcher, contrarian) do work. The benchmark_evaluator agent edits a file. The guardian agent has a standalone_session mode (runs as subprocess). The plan review agents (architect, critic, guardian) review at phase END, not during execution. Moving all of them to the same phase-level `agents` key says "these are all execution agents" but guardian runs as a gate-like isolated process, and plan reviewers run at end-time.

In FULL::PLAN, the agents (architect, critic, guardian) are documented to "review the plan" - this happens AFTER the plan is written, at the END of the phase. They are genuinely on_end agents, not execution agents. Moving them to phase level is semantically WRONG for these agents.

In FULL::REVIEW, ALL agents (critic, architect, guardian, forensicist) ARE the entire phase execution - they do the review work. These ARE execution agents.

In FULL::RESEARCH, agents (researcher, architect, product_manager) run during execution. Execution agents.

In FULL::HYPOTHESIS, agents (contrarian, optimist, pessimist, scientist) run during execution. Execution agents.

The program treats all agents as execution agents. Some are. Some aren't.

**Reality**: The orchestrator doesn't distinguish between "runs during execution" and "runs at end" - it injects all agent instructions into the START template and validates all agents on END. The distinction exists in the phase instructions text but not in the model. The program could address this by adding a `role` field (execution/review) or accepting that all agents span the phase.

**Response**: Either add a `role` or `lifecycle_point` field to Agent dataclass to distinguish execution agents from review agents, or explicitly document that the phase-level `agents` key represents "all agents that participate in this phase, regardless of when they run." The latter is simpler and honest.

---

## 5. "The _build_phases exclusion list is growing without a pattern"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: `_build_phases` currently excludes `gates` key with `k != "gates"`. After this change it must also exclude `agents`. Then next time someone adds another metadata key, they'll need to remember to exclude it. This is the "growing exclusion list" anti-pattern. A better approach: define WHICH keys _build_phases INCLUDES rather than which it excludes.

**Reality**: Phase dataclass fields are well-defined (start, end, reject_to, auto_actions, auto_verify, etc.). Using an inclusion list (`k in Phase.__dataclass_fields__`) is already the pattern - the exclusion is only for non-dataclass keys. Adding one more exclusion is manageable.

**Response**: Low priority. Note in program that `_PHASE_RESERVED_KEYS` or the `_build_phases` filter should be the single exclusion point.

---

## 6. "The program doesn't mention the {agents_instructions} template variable contract"

**Likelihood: 3** | **Impact: 5** | **Risk: 15**

**Their take**: The template variable `{agents_instructions}` is populated by `_build_agent_instructions` which reads from `_MODEL.agents`. Phase templates reference this variable in their START section (e.g., FULL::RESEARCH start template has `{agents_instructions}`). This contract - agents defined somewhere, rendered into START template - is the actual architectural invariant. The program should state this invariant explicitly and verify it survives the move.

**Reality**: The program's constraint says "Do NOT change the orchestrator's agent instruction injection or end validation logic" - implying this contract is preserved. But it doesn't NAME the contract. An implementer could accidentally break the `_resolve_agents` -> `_build_agent_instructions` -> `{agents_instructions}` chain.

**Response**: Add to program: "The agent instruction injection chain must be preserved: `_resolve_agents(phase)` resolves the agent key -> `_build_agent_instructions(key)` renders agent prompts -> `{agents_instructions}` template variable populated in START context. This chain must work identically after the move."

---

## 7. "validate_model agent checks will reference wrong YAML location in error messages"

**Likelihood: 5** | **Impact: 3** | **Risk: 15**

**Their take**: validate_model currently reports errors like `"[phases.yaml] '{phase_key}.{agent.name}': missing '{f}'."`. After the move, agents are no longer under gates - they're at phase level. The error messages should reflect this. But more importantly, the validate_model function iterates `model.agents` which is populated by `_build_agents_and_gates`. If the extraction changes, does validation still work?

**Reality**: The program mentions this: "Agent validation messages should reference phase-level agents, not gates.on_end." The concern is acknowledged but the validation logic itself may need structural changes if agents are no longer co-discovered with gates.

**Response**: The program covers this. Low residual.

---

## Scorecard

| # | Concern | Risk | Score | Residual | Reasoning |
|---|---------|------|-------|----------|-----------|
| 1 | Model lifecycle semantics | 64 | 40% | 38.4 | Program moves agents to phase-level but doesn't add `execution` lifecycle to model. Says "agents at phase level" which is better than on_end but doesn't name WHY. No Model.execution_agents distinction. |
| 2 | gate_type_sets dead code | 40 | 60% | 16.0 | Program doesn't mention removing `if gate_type == "agents": continue` dead code after move. Partial coverage. |
| 3 | Backward compat priority reversal | 40 | 30% | 28.0 | Program says "fallback" but doesn't explicitly state the priority REVERSAL needed in _build_agents_and_gates. Ambiguous. |
| 4 | Agent role inconsistency | 25 | 35% | 16.3 | Program treats all agents as execution agents. PLAN review agents are genuinely end-of-phase. No role distinction proposed. |
| 5 | Growing exclusion list | 9 | 70% | 2.7 | Minor. Program mentions _build_phases needs update. |
| 6 | Template variable contract | 15 | 50% | 7.5 | Program says "don't change injection logic" but doesn't name the specific chain to preserve. |
| 7 | Error message locations | 15 | 80% | 3.0 | Program explicitly mentions this. Well covered. |

**Document score**: 111.9 (total residual risk)
**Total absolute risk**: 208
**Residual %**: 53.8%

**Top gaps**:
1. Model lifecycle semantics (38.4) - the fundamental design question: move agents vs add execution lifecycle
2. Backward compat priority reversal (28.0) - ambiguous instruction will produce wrong implementation
3. gate_type_sets dead code (16.0) - dead code trap after move
4. Agent role inconsistency (16.3) - PLAN review agents are genuinely end-of-phase agents

---

## Biggest gaps - options

### Concern #1: Model lifecycle semantics (residual: 38.4)

**Option A**: Add `execution` key to YAML and `execution_agents` to Model
- Expected effect: #1 +50%, #4 +30% (net: large improvement)
- Risk: significant model change, many files touched

**Option B**: Keep phase-level `agents` and document that agents span the full phase
- Expected effect: #1 +25%, #4 +15%
- Risk: none - documentation only

**Option C**: Add `agents` key parallel to `gates` with its own lifecycle subsections (`execution`, `review`)
- Expected effect: #1 +40%, #4 +50%
- Risk: over-engineering for 19 agents across 7 phases

**Recommendation**: Option B. The orchestrator already treats agents as phase-spanning (instructions at start, validation at end). Making the YAML match this reality is the honest fix. Option A/C add complexity without changing behavior.

### Concern #3: Backward compat priority reversal (residual: 28.0)

**Option A**: Explicitly state "phase-level primary, on_end fallback" in program
- Expected effect: #3 +60%
- Straightforward text fix

**Recommendation**: Option A. One sentence fixes the ambiguity.
