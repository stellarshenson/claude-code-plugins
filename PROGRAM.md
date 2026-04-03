# Program: Fix Real Gaps (Not Prompt Theater)

## Objective

Fix the actually broken subsystems in the orchestrator that were previously "fixed" with prompt text changes but have no code enforcement. The prior iteration scored 0 on the benchmark by checking template text presence, not runtime behavior. This program addresses the real gaps.

## Critical Design Problem: RESEARCH and HYPOTHESIS ROI

RESEARCH and HYPOTHESIS phases consume massive resources - multiple agent spawns, gatekeeper evaluations, subprocess calls - but produce almost nothing that persists. Phase outputs vanish due to the path doubling bug. Even when they do persist, the content is shallow because there's no code enforcement on quality.

The ROI of these expensive phases must be visible:
- Rich outputs MUST survive in phase directories as reusable artifacts
- RESEARCH output must be rich enough that a new session can pick up from it without re-reading the codebase
- HYPOTHESIS output must contain self-contained action plans (not just "do X"), with predictions that can be verified after implementation
- Both must be validated programmatically before the phase completes - not by LLM judgment

## What Actually Works (leave alone)

- `_load_hypotheses` notes validation - crashes on plain strings and invalid statuses
- `{phase_dir}` in `_build_context` - template variable resolves correctly
- `_KNOWN_VARS` updated - validation passes
- `_clean_artifacts_dir` conditional preserve - fresh new cleans, --continue preserves
- `_check_lifecycle_compliance` blocks acknowledged at NEXT boundary
- `--record-instructions` CLI flag stored in state and resolved in templates
- RECORD template conditional on code changes

## What's Broken

### Readback subprocess polluted by CLAUDE.md and plan mode

The `claude -p` readback subprocess reads the project's `.claude/CLAUDE.md` and Claude Code's internal state. When CLAUDE.md contains git commit policies ("Never create git commits without explicit user approval"), the readback evaluator treats these as higher priority than the orchestrator's RECORD phase instructions. It fails with "plan mode is active" or "CLAUDE.md prohibits automatic git commits."

Forensic evidence from cp-simulations: 7 consecutive RECORD readback failures all citing plan mode or CLAUDE.md git policy. The state.yaml correctly showed RECORD/pending but the subprocess was influenced by external context.

**Design principle: CLAUDE.md always wins.** The project's CLAUDE.md represents the user's explicit policies. If CLAUDE.md says "no automatic git commits", the orchestrator must respect that - it cannot override the user's own rules.

The fix is NOT to suppress CLAUDE.md. Instead:
1. The readback prompt must acknowledge that CLAUDE.md policies override phase instructions. Add to readback prompt: "If the project CLAUDE.md restricts actions mentioned in the phase instructions (e.g. git commits require user approval), the understanding should reflect those restrictions. The agent adapting to CLAUDE.md is CORRECT behavior, not a readback failure."
2. The RECORD template itself must be compatible with CLAUDE.md restrictions. The current template says "commit and push" but CLAUDE.md may forbid this. The template should say: "If CLAUDE.md or project policy restricts git operations, follow those restrictions. Record iteration summary regardless."
3. The readback for RECORD should only require "iteration summary mentioned" - git operations are conditional on both code changes AND project policy.

### Rate limit errors treated as readback failures

Forensic evidence: IMPLEMENT readback failed with `"You've hit your limit · resets 9pm (Europe/Warsaw)"`. The `_claude_evaluate` function treats any non-PASS first line as FAIL. API rate limits, timeouts, and network errors are transient - they should be retried, not treated as a readback failure that the agent has to fix.

Fix: detect rate limit and transient error patterns in `_claude_evaluate` output. If the response contains "hit your limit", "rate limit", "timeout", "network error" etc., return a special result that triggers automatic retry (up to 3 attempts with backoff) instead of FAIL.

### Output file path doubling

When `{phase_dir}` resolves to an absolute path in the template (e.g. `/home/user/project/.auto-build-claw/phase_06_review`), the agent passes that entire string as `--output-file "/home/user/project/.auto-build-claw/phase_06_review/review.md"`. The code in `_validate_end_inputs` then checks `is_absolute()` - this IS absolute so it uses it as-is. But the file doesn't exist there because the agent wrote it to the phase_dir directly.

The real problem: the agent writes the file to `{phase_dir}/review.md` (correct location), then passes `{phase_dir}/review.md` as `--output-file`. The orchestrator reads from that path - this should work. But we saw it fail with doubled path `phase_06_review/.auto-build-claw/phase_06_review/review.md`. Investigate the exact failure mode and fix.

### Agent execution mode is a no-op

`_run_auto_actions` for `execution: agent` just prints the resolved prompt to stdout wrapped in `--- AUTO-ACTION (agent): ... ---` markers. This relies on the main conversation agent noticing the printed text and acting on it. In practice, I had to manually write `hypotheses.yaml` because the print was ignored.

**Decision: Option 2 - bake into template with gatekeeper enforcement.**

The fix: remove `execution: agent` auto-actions entirely. Instead, inject the hypothesis extraction instructions directly into the HYPOTHESIS END template. The agent already has the debate output in context when ending the phase. The template tells the agent: "Before calling end, write hypotheses to `{artifacts_dir}/hypotheses.yaml` in the required format." The gatekeeper then verifies: (1) hypotheses.yaml exists, (2) it has valid entries matching the debate output, (3) entries have correct format (identifier-keyed dict with required fields). This is deterministic enforcement, not hope.

Also remove the `execution` field from `ActionDef` since it's no longer needed - all generative auto-actions become either template instructions (agent does it) or `_claude_evaluate` standalone calls. The `execution: agent` concept was wrong - printing to stdout is not execution.

### Context acknowledgment notes have no code verification

Phase templates tell agents to write rich acknowledgment notes via `orchestrate context --note`. But nothing in code verifies they actually did it. The gatekeeper checks are subjective LLM judgment.

Fix: after phase end, programmatically check that each acknowledged context/failure entry has at least one note added during this phase. If an entry was "acknowledged" at phase start but has no new notes by phase end, that's a compliance violation.

### Research output depth has no code enforcement

The RESEARCH gatekeeper prompt lists structural checks (4 sections, code references) but the gatekeeper is a `claude -p` subprocess making a subjective call. Nothing in code verifies the output actually contains these sections.

Fix: after RESEARCH phase end, programmatically scan the output file for required section headers AND minimum content depth. Checks:
1. Required sections present: "Current State", "Gap Analysis", "File Inventory", "Risk Assessment" (case-insensitive header scan)
2. Minimum output length: >= 500 characters total (shallow outputs are physically short)
3. Code references present: at least 3 file paths (pattern: contains `/` or `.py` or `.yaml` or `.md`)
4. Each section has content (not just a header with nothing under it): >= 50 chars between section headers

Fail the phase programmatically before the gatekeeper runs. Same pattern as `_check_lifecycle_compliance` - hard code gate, not LLM-dependent.

### Hypothesis format has no code enforcement

Same pattern as research - the gatekeeper prompt checks for format fields but it's LLM-judged.

Fix: after HYPOTHESIS phase end, programmatically validate hypotheses.yaml entries for richness. Each entry must have:
1. `hypothesis` field: >= 20 chars (a real problem statement, not "fix X")
2. `prediction` field: >= 10 chars AND contains a number or comparison word (from/to/increase/decrease/reduce)
3. `evidence` field: >= 10 chars (actual data points, not empty)
4. `stars` field: int 1-5
5. `status` field: valid value
6. `notes` field: list of dicts (already enforced by _load_hypotheses)

Fail programmatically if ANY entry fails richness checks. Error message names the entry and the failing field with its actual length vs minimum.

## Work Items

### Broken code

- **Rate limit errors treated as failures** (critical)
  - Scope: `orchestrator.py` `_claude_evaluate`
  - Root cause: `_claude_evaluate` treats any non-PASS first line as FAIL. API rate limits are transient, not a readback judgment
  - Fix: detect "hit your limit", "rate limit", "timeout" patterns in output. Retry up to 3 times with exponential backoff (5s, 15s, 45s). Only FAIL after all retries exhausted
  - Acceptance: rate limit response triggers retry, not immediate FAIL
  - Predict: zero phase failures caused by transient API errors
  - Outcome: orchestrator survives rate limit periods without losing progress

- **Readback must respect CLAUDE.md policies** (critical)
  - Scope: phases.yaml RECORD readback prompt, RECORD template
  - Root cause: readback subprocess reads CLAUDE.md and correctly identifies git policy conflicts, but treats the agent's compliance with CLAUDE.md as a readback failure instead of correct behavior
  - Fix: (1) RECORD readback prompt acknowledges CLAUDE.md overrides - agent adapting to project policy is PASS, not FAIL. (2) RECORD template itself is compatible with CLAUDE.md restrictions (git operations conditional on project policy). (3) Readback only requires "iteration summary" - git is conditional
  - Acceptance: RECORD readback passes when agent says "write summary, respect CLAUDE.md git policy"
  - Predict: zero readback failures caused by CLAUDE.md git policy
  - Outcome: orchestrator works harmoniously with project-level policies

- **Output file path doubling** (high)
  - Scope: `orchestrator.py` `_validate_end_inputs`
  - Acceptance: `--output-file` with absolute path to existing file works without doubling. Test reproduces the doubling and verifies fix

- **Hypothesis persistence via template + gatekeeper** (high)
  - Scope: phases.yaml HYPOTHESIS end template, HYPOTHESIS gatekeeper, `orchestrator.py` `_run_auto_actions`, `model.py` ActionDef
  - Remove `execution: agent` auto-action mechanism (stdout print is not execution)
  - Remove `execution` field from ActionDef - revert to just `type: programmatic | generative` where generative always uses `_claude_evaluate`
  - Move hypothesis extraction into HYPOTHESIS END template: agent writes `{artifacts_dir}/hypotheses.yaml` before calling `orchestrate end`
  - HYPOTHESIS gatekeeper programmatically checks: (1) hypotheses.yaml exists, (2) `_load_hypotheses()` succeeds (valid format), (3) at least one entry exists, (4) each entry has ALL required fields non-empty: hypothesis (>= 20 chars), prediction (>= 10 chars), evidence (>= 10 chars), stars (int 1-5). Empty or stub fields like `prediction: ""` or `evidence: "TBD"` must fail
  - `_check_lifecycle_compliance` for HYPOTHESIS phase: verify hypotheses.yaml is non-empty AND entries pass richness check
  - Acceptance: after HYPOTHESIS phase end, hypotheses.yaml contains structured entries without manual intervention
  - Predict: hypotheses.yaml non-empty after HYPOTHESIS phase completes
  - Outcome: hypothesis catalogue accumulates across iterations automatically

### Missing enforcement

- **Context/failure note verification** (medium)
  - Scope: `orchestrator.py` `_check_lifecycle_compliance` or new compliance check in `cmd_end`
  - Acceptance: phase end fails if acknowledged entries gained no new notes during the phase. Test covers this
  - Predict: agents who ignore context acknowledgment get blocked
  - Outcome: audit trail is guaranteed, not hoped for

- **Research output structural validation** (medium)
  - Scope: `orchestrator.py` `cmd_end` or new validation function
  - Acceptance: RESEARCH phase end fails programmatically if output lacks required sections. Test covers this
  - Predict: shallow "X is missing" research outputs get rejected by code, not LLM
  - Outcome: research outputs are always rich enough for session restart

- **Hypothesis format structural validation** (medium)
  - Scope: `orchestrator.py` `cmd_end` or new validation function
  - Acceptance: HYPOTHESIS phase end fails programmatically if selected hypotheses lack required fields. Test covers this
  - Predict: thin hypotheses get rejected by code
  - Outcome: hypothesis entries are always self-contained action plans

### Plan output quality (gatekeeper checklist, not code)

Unlike RESEARCH (structural sections) and HYPOTHESIS (field richness), PLAN quality is inherently generative - whether a root cause is correct or acceptance criteria are realistic requires LLM judgment. A programmatic validator would be prompt theater.

The fix is a rigorous PLAN gatekeeper checklist. The gatekeeper already runs - it just needs teeth. Update the PLAN gatekeeper prompt with an explicit checklist that must ALL pass:
- [ ] Plan names specific files to modify (not "update the module")
- [ ] Each change has a root cause identified
- [ ] Each change has acceptance criteria that can be verified
- [ ] Risk assessment present (what could go wrong)
- [ ] Predictions with metrics (from X to Y)
- [ ] Dependencies between changes identified (ordering)
- FAIL if ANY item is missing or vague

The "explore 2-3 alternatives, have contrarian challenge, select with justification" instruction exists in PLANNING::PLAN (work breakdown) but NOT in the shared PLAN phase used by FULL workflow. This planning rigor must be in ALL plan phases - the same depth that EnterPlanMode provides (explore alternatives, agent review, justified selection) without requiring interactive mode.

## Exit Conditions

- All work items implemented
- make test >= 236
- make lint clean
- Output file path works with absolute paths (no doubling)
- Hypotheses.yaml populated automatically after HYPOTHESIS phase (no manual intervention)
- Acknowledged entries without new notes blocked at phase end
- Research and hypothesis outputs validated structurally by code

## Constraints

- No backward compatibility for old state files
- Occam's razor: simplest fix that actually enforces
- Programmatic checks run BEFORE gatekeeper (same pattern as _check_lifecycle_compliance)
- Agent execution mode approach must be decided with user before implementation
