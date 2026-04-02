# Hypotheses - Iteration 23: Occam Directive + Gatekeeper Context

## H1: Occam directive as YAML anchor will ensure consistency across 4 architect agents
- **Root cause**: 4 separate architect prompts with no shared directive. Adding same text to each risks drift.
- **Prediction**: Using a YAML anchor `&occam_directive` defined once and referenced via `*occam_directive` ensures all 4 architects get identical wording. grep -i "occam" phases.yaml will return >= 5 matches (1 anchor definition + 4 references).
- **Evidence**: phases.yaml already uses YAML anchors for guardian checklist (`&guardian_checklist`/`*guardian_checklist`).
- **Stars**: 5

## H2: Gatekeeper context check should be conditional on active context existing
- **Root cause**: S8 requires gatekeepers to verify context was considered in evidence. But not all iterations have context messages - adding unconditional context checks would fail phases with no context.
- **Prediction**: Adding "IF context messages are active, evidence MUST reference them" to gatekeeper prompts will satisfy S8 without false failures on contextless iterations. The check is conditional: only triggered when context.yaml has entries.
- **Evidence**: cmd_start already filters active context at L1692. Gatekeeper prompts at 11 locations don't mention context at all.
- **Stars**: 4

## H3: Agent spawn instructions should include context acknowledgment directive
- **Root cause**: S8 item "Agent spawn instructions include directive to acknowledge context". Currently _build_agent_instructions at L300-328 generates agent prompts but no context directive.
- **Prediction**: Adding a context acknowledgment line to the agent instruction template (in _build_agent_instructions or in the phase template) will satisfy S8. But this is in orchestrator.py, not phases.yaml. Since this iteration focuses on phases.yaml, we should add the directive to the phase template's execution section instead.
- **Evidence**: The user guidance instruction at L1701 already says "MUST be considered by every agent" but individual agent prompts don't explicitly reference it.
- **Stars**: 3
