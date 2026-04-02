# Devil's Advocate - PROGRAM.md (Agent Lifecycle Architecture Fix)

## The Devil

**Role**: Senior backend engineer who has worked on the auto-build-claw codebase
**Cares about**: (1) Does this fix a real problem or is it aesthetic? (2) Will this break things? (3) Is the scope right?
**Style**: Evidence-first, skeptical of refactoring that changes structure without changing behavior
**Default bias**: If it works, the bar for rearranging it is high
**Triggers**: Semantic purity arguments, refactoring for its own sake, understated blast radius
**Decision**: Can block the work as unjustified churn
**Source**: User-described persona

---

## 1. Concern Catalogue

### 1. "This is a cosmetic refactoring disguised as a bug fix - nothing is broken"

**Likelihood: 8** | **Impact: 5** | **Risk: 40**

**Their take**: The PROGRAM.md says agents are "defined under gates.on_end" and calls this "wrong." But the codebase works. 142 tests pass. All 4 dry-runs pass. The orchestrator correctly injects agent instructions at START via `{agents_instructions}` and validates agent names at END via `--agents`. The YAML structure is a storage detail. Calling it "broken" in the heading ("Current Architecture (broken)") is dishonest framing to justify refactoring.

**Reality**: The PROGRAM.md itself concedes: "This dual use works mechanically but the YAML structure lies about when agents run." That's an aesthetic judgment, not a bug report. No user has filed an issue. No developer has been confused. The system has been through 19 iterations of development (journal entries 1-21) without this "lie" causing a single defect.

**Response**: The strongest counter-argument is onboarding cost - a new developer reading the YAML would assume agents run at end-time. But the PROGRAM.md doesn't mention onboarding or any concrete scenario where the current structure caused a real problem.

---

### 2. "The backward compatibility fallback contradicts the stated goal"

**Likelihood: 8** | **Impact: 5** | **Risk: 40**

**Their take**: The PROGRAM says the goal is to make the YAML "truthful" by moving agents to phase-level. But then it says: "Preserve backward compatibility: if a phase still has agents under on_end, the model should still load them (fallback)." So after this refactoring, the model.py code will support BOTH locations indefinitely. The YAML is no more "truthful" - it's now ambiguous. Two valid locations for the same data is worse than one "wrong" location because now a reader has to check both places.

**Reality**: The fallback already exists in `_build_agents_and_gates` (line 207-215 of model.py): `agent_list = section.get("agents", [])` reads phase-level first, then `if lifecycle == "on_end" and "agents" in subsection: agent_list = subsection["agents"]` overrides with on_end. The refactoring would flip the priority but keep the dual-path logic. The "truthfulness" argument is undermined by the dual-path.

**Response**: Either commit fully (remove the fallback, break old YAMLs) or don't do this at all. The middle ground makes the code more complex for zero behavioral change.

---

### 3. "The _build_phases function claim is wrong"

**Likelihood: 5** | **Impact: 3** | **Risk: 15**

**Their take**: The PROGRAM says: "The `_build_phases` function already skips `gates` key - must also skip `agents` key." But look at the actual code:

```python
def _build_phases(raw: dict) -> dict[str, Phase]:
    return {
        key: Phase(**{k: val[k] for k in Phase.__dataclass_fields__ if k in val and k != "gates"})
        ...
    }
```

It filters by `Phase.__dataclass_fields__` - only keys that match Phase dataclass field names get included. Since Phase has no `agents` field, a top-level `agents` key would be silently ignored anyway. The `k != "gates"` check is redundant caution for the `gates` key. Adding `agents` at phase level won't break `_build_phases` - it just gets ignored like any other unrecognized key. The PROGRAM's claim that you "must also skip" it implies it would break without the fix, which is false.

**Reality**: The current `_build_phases` logic filters by dataclass field intersection. An `agents` key at phase level would simply not match any Phase field and would be silently dropped. No code change needed in `_build_phases`.

**Response**: The PROGRAM overstates the complexity. But this is a minor factual error, not a showstopper.

---

### 4. "The scope enumeration is wrong - there are 7 phases with agents but the PROGRAM miscounts and misnames them"

**Likelihood: 5** | **Impact: 3** | **Risk: 15**

**Their take**: The PROGRAM lists: "FULL::RESEARCH (3 agents), FULL::HYPOTHESIS (4), PLAN (3), TEST (1 benchmark_evaluator), REVIEW (4), PLANNING::RESEARCH (3), PLANNING::PLAN (1 contrarian)". That's 7 phases, correct. But the PROGRAM's "Current Architecture" example shows agents as `gates.on_end.agents` and calls this wrong. Then the work items say "Move agents from gates.on_end to phase-level."

But here's the thing: the PROGRAM.md is describing a REVERSAL of work already done. Journal entry #16 explicitly says: "Moved agent definitions from phase-level into `gates.on_end` subsections across agents.yaml." So this refactoring is undoing a deliberate architectural decision made in the same project, by the same team, just a few iterations ago. What changed? Why was putting them in on_end the right call in entry #16 but wrong now?

**Reality**: This is accurate. Entry #16 moved agents INTO on_end. The current PROGRAM.md wants to move them OUT. The PROGRAM provides no explanation for why the prior decision was wrong. This is a red flag for thrashing.

**Response**: The PROGRAM should acknowledge it's reversing a prior decision and explain what was learned since then.

---

### 5. "The test fixture changes are understated - inline YAML in multiple test files is fragile"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: The PROGRAM lists fixture updates as "medium" priority and mentions conftest.py, test_model.py, and test_orchestrator.py. But the actual test codebase has YAML embedded inline in at least 6 places:
- `conftest.py` minimal_resources fixture (agents under on_end in ALPHA, BETA, GAMMA)
- `test_model.py` test_missing_workflow_description (agents under on_end)
- `test_model.py` test_non_fqn_workflow_name (agents under on_end)
- `test_model.py` test_duplicate_cli_name (agents under on_end)
- `test_model.py` test_undefined_action_reference (agents under on_end)
- `test_orchestrator.py` TestGenerativeActionDispatch (agents under on_end)

Each one is a separate inline YAML string that must be updated. Miss one and you get silent fallback to the old path (thanks to backward compat), which means the test appears to pass but isn't actually testing the new structure. This is exactly the kind of subtle breakage that code review won't catch because the tests still green.

**Reality**: The backward compatibility fallback means broken tests won't fail - they'll silently use the old path. This is insidious.

**Response**: Without a mechanism to WARN when the fallback path is used, you'll never know if your migration is complete. The PROGRAM should include: add a deprecation warning when agents are loaded from on_end instead of phase-level.

---

### 6. "The orchestrator constraint is dangerous - 'Do NOT change the orchestrator' when you're changing what feeds it"

**Likelihood: 3** | **Impact: 5** | **Risk: 15**

**Their take**: The constraints section says: "Do NOT change the orchestrator's agent instruction injection or end validation logic (they already work correctly)." But the PROGRAM also says: "Update _build_agents_and_gates in model.py." The model.py function is what feeds data to the orchestrator. If the model loads agents from a different YAML path, the orchestrator receives the same Agent objects - that's fine. But the constraint gives a false sense of safety. The real question is: does the orchestrator make ANY assumptions about where agents came from in the YAML? Looking at the code: `_resolve_agents` resolves to a key in `_MODEL.agents` dict. The dict keys are phase names like "FULL::RESEARCH". Those keys come from `_build_agents_and_gates` which currently derives them from the phase section key in the YAML. If you move agents to phase-level, the key derivation stays the same. So the constraint holds - but only by accident, not by design.

**Reality**: The orchestrator is genuinely decoupled from YAML structure via the Model object. The constraint is technically valid.

**Response**: But the PROGRAM should make this reasoning explicit rather than just asserting "they already work correctly."

---

### 7. "Auto-build-claw resources work item references a directory that doesn't exist"

**Likelihood: 8** | **Impact: 2** | **Risk: 16**

**Their take**: The PROGRAM says: "Update auto-build-claw resources - Scope: `auto-build-claw/skills/auto-build-claw/` (if any YAML references remain)." But glob search shows zero YAML files under any auto-build-claw path. Journal entry #19 confirms: "Removed old skill resources directory and redundant `orchestrate.py` entrypoint." This work item is dead. It's either stale (copied from an older version of the program) or the author didn't verify the current state before writing.

**Reality**: No YAML files exist at `auto-build-claw/skills/auto-build-claw/`. The work item is a no-op.

**Response**: Remove the work item. It signals sloppiness.

---

### 8. "No rollback plan for a pure-refactoring change"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: The exit conditions include "make test passes with 0 failures" and "orchestrate validate passes." But there's no discussion of what happens if the refactoring is halfway done and something unexpected breaks. With backward compatibility, the half-migrated state is the most dangerous: some phases using new location, some using old, and the fallback silently covering up inconsistencies. The PROGRAM should define a "revert to git HEAD" escape hatch and a specific commit strategy (atomic single commit vs incremental).

**Reality**: The backward compat fallback makes partial migration safe in terms of runtime behavior, but semantically incoherent. A half-migrated YAML is worse than the "wrong" original.

**Response**: Define whether this is a single atomic change or incremental migration, and what "abort" looks like.

---

## 2. Fact Verification

| PROGRAM.md Claim | Verified? | Evidence |
|---|---|---|
| "Agents defined under `gates.on_end` alongside the gatekeeper" | **TRUE** | phases.yaml lines 156-198, 288-336, 417-494, 629-661, 731-798, 962-1002, 1063-1082 all show `agents:` under `on_end:` |
| "Their instructions are injected into the START template via `{agents_instructions}`" | **TRUE** | orchestrator.py line 449: `ctx["agents_instructions"] = _build_agent_instructions(agent_phase_key, ctx)` runs during `_build_context` which feeds START template |
| "Their names are validated on END via `--agents` flag" | **TRUE** | orchestrator.py line 1671: `_validate_end_inputs` checks `PHASE_AGENTS.get(required_key, [])` |
| "7 phases with agents under gates.on_end" | **TRUE** | FULL::RESEARCH(3), FULL::HYPOTHESIS(4), PLAN(3), TEST(1), REVIEW(4), PLANNING::RESEARCH(3), PLANNING::PLAN(1) = 7 phases |
| "The `_build_phases` function already skips `gates` key - must also skip `agents` key" | **MISLEADING** | `_build_phases` filters by `Phase.__dataclass_fields__` intersection, not by explicit skip. The `k != "gates"` is present but `agents` would be silently ignored anyway because Phase has no `agents` field. No code change needed in `_build_phases`. |
| "Tests passing: 142" | **TRUE** | `pytest --co -q` reports 142 tests collected |
| "Auto-build-claw skill resources directory has YAML references" | **FALSE** | Glob finds zero YAML files under any `auto-build-claw/` path. Resources were moved to module in journal entry #19. |
| "model.py currently extracts agents from `on_end` subsection" | **TRUE** | model.py line 214: `if lifecycle == "on_end" and "agents" in subsection: agent_list = subsection["agents"]` |
| "model.py has phase-level fallback" | **TRUE** | model.py line 207: `agent_list = section.get("agents", [])` reads phase-level first, then on_end overrides |

---

## 3. Blind Spots

**3.1 - No mention of GC::PLAN sharing agents with PLAN**

GC::PLAN (lines 1086-1153) has NO agents defined under on_end - only a gatekeeper. But its `end` template references `{agents_instructions}` and `{spawn_instruction_plan}` and expects agents named "architect,critic,guardian." These resolve via `_resolve_agents` which falls through from `GC::PLAN` to bare `PLAN` (which has those agents). If agents move to phase-level in PLAN, the resolution chain must still work for GC::PLAN. The PROGRAM doesn't mention this cross-phase agent sharing at all.

**3.2 - No deprecation warning for fallback path**

If backward compatibility is preserved, there's no mechanism to detect stale YAML still using the old location. Tests will pass silently via fallback. The PROGRAM should mandate a log warning when agents are loaded from on_end rather than phase-level.

**3.3 - IMPLEMENT and RECORD and NEXT have no agents but have on_end**

The PROGRAM focuses on the 7 phases WITH agents but doesn't discuss IMPLEMENT (line 555), RECORD (line 843), NEXT (line 909), and GC::PLAN (line 1143) which have `on_end` with only a gatekeeper and no agents. These phases are unaffected by the change but should be explicitly called out as "no change needed" to show completeness.

**3.4 - No discussion of how validate_model agent-name validation works post-move**

`validate_model` (model.py lines 625-643) checks that gates referencing `{required_agents}` have agents defined for that phase. The resolution uses `agent_keys = set(model.agents.keys())`. Moving agents from on_end to phase-level changes WHERE agents are extracted in `_build_agents_and_gates` but not the resulting dict key (still `phase_key`). But the PROGRAM doesn't verify this reasoning - it just says "should still work."

**3.5 - No performance or memory consideration**

Adding a phase-level `agents` key means `_build_agents_and_gates` must now handle two locations. The function is already O(phases * gates) - doubling the extraction logic has no meaningful performance impact, but the PROGRAM doesn't acknowledge this analysis even briefly.

---

## 4. Contradictions

**4.1 - "Fix" vs "works mechanically"**

The PROGRAM title says "Architecture Fix" and the current architecture is labelled "(broken)." But the objective section says "This dual use works mechanically." These are contradictory. Either it's broken (doesn't work) or it works but is semantically misleading. The language inflation from "misleading" to "broken" is itself misleading.

**4.2 - "Truthful YAML" vs "backward compatibility"**

The goal is to make YAML truthful about agent lifecycle. But the backward compat requirement means the model.py code will accept agents in EITHER location. The YAML schema is now MORE ambiguous than before, not less.

**4.3 - "Do NOT change orchestrator" vs "Update validate_model"**

`validate_model` is in model.py but is called FROM the orchestrator's validate command flow. The constraint says "Do NOT change the orchestrator's agent instruction injection or end validation logic" - validate_model IS validation logic. This is a definitional boundary that isn't clear.

**4.4 - Work item says "fall back to on_end for backward compat" but exit condition says "no agents under gates.on_end"**

The baseline metrics table says target is "0" agents under gates.on_end. But the work item for model.py says "fall back to `on_end` for backward compat." If the target is 0 agents under on_end, the fallback will never trigger in the production YAML. It exists only for hypothetical external users who customized their YAML. If there are no external users (this is a single-user plugin system), the fallback is dead code from day one.

---

## 5. Execution Risk

**5.1 - Highest risk: Silent test passes via fallback (Risk: 25)**

The backward compatibility fallback in model.py means that if ANY test fixture or inline YAML is missed during migration, the tests will still pass because agents load from on_end as before. The refactoring could be declared "complete" while some test paths never exercise the new code. Only way to catch this: temporarily REMOVE the fallback, run tests, then add it back. The PROGRAM doesn't describe this verification step.

**5.2 - Second highest risk: GC::PLAN agent resolution (Risk: 20)**

GC::PLAN borrows agents from PLAN via the resolution chain. If the resolution logic changes (phase-level lookup priority changes), GC::PLAN could silently lose its agents. The PROGRAM doesn't mention GC::PLAN at all despite it being present in phases.yaml.

**5.3 - Thrashing risk (Risk: 15)**

This is the third structural reorganization of agent placement in the codebase: (1) originally phase-level, (2) moved to on_end in journal entry #16, (3) now proposed back to phase-level. Without documenting why the on_end decision was wrong, there's no guardrail against moving them back again in iteration N+1.

---

## Summary Assessment

**Is this worth doing?** The devil says: probably not. The current architecture works, passes all tests, and has been stable through 19 development iterations. The "semantic mismatch" is a valid observation but fixing it introduces more complexity (dual-path loading, silent fallback, migration verification burden) than it removes. The PROGRAM conflates "misleading structure" with "broken architecture" to justify the work.

**If you do it anyway**: (1) Remove the fallback entirely - commit to one location. (2) Add a deprecation warning if you keep the fallback. (3) Acknowledge this reverses journal entry #16 and explain what changed. (4) Add GC::PLAN to the scope analysis. (5) Remove the dead auto-build-claw work item. (6) Define atomic vs incremental migration strategy.

**Total catalogue risk**: 175 (across 8 concerns)
**Highest individual risks**: Concerns #1 and #2 at 40 each (cosmetic refactoring + contradictory fallback)
