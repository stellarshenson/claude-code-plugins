# Research - Iteration 23: Occam Directive + Gatekeeper Context

## Architect agents (4 locations in phases.yaml)
1. FULL::RESEARCH L156-165
2. PLAN L401-412
3. REVIEW L752-762
4. PLANNING::RESEARCH L999-1008

Note: GC::PLAN and PLANNING::PLAN don't have dedicated architect agents.

## Gatekeeper prompts (11 phase gates in phases.yaml)
FULL::RESEARCH L197, FULL::HYPOTHESIS L339, PLAN L500, IMPLEMENT L576, TEST L669, REVIEW L816, RECORD L875, NEXT L944, PLANNING::RESEARCH L1032, PLANNING::PLAN L1116, GC::PLAN L1189

## Context injection
- cmd_start L1688-1702 injects context messages into phase instructions
- Agent spawn instructions generated dynamically by _build_spawn_instruction (L376-397)
- Agent instructions built by _build_agent_instructions (L300-328)
