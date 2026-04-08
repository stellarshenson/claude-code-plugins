# Devil's Advocate - kg-builder-cli DESIGN.md

## The Devil

**Role**: Senior backend engineer with 15+ years building production data pipelines, reviewing a design document for implementation readiness
**Cares about**: implementation complexity, runtime predictability, maintenance burden, time-to-first-value
**Style**: data-driven, pragmatic, allergic to speculative architecture
**Default bias**: skeptical of agent-heavy designs, prefers deterministic pipelines, suspicious of LLM-in-the-loop for infrastructure decisions
**Triggers**: overengineering, optional features described as core, missing confidence/provenance on extracted data, vague error handling
**Decision**: approve for implementation, request simplification, or reject sections as premature

---

## Concern Catalogue (2 of 10 shown)

### 1. "Agents are overused - most ingestion steps should be deterministic pipelines"

**Likelihood: 5** | **Impact: 4** | **Risk: 20**

**Their take**: Every command spawns an agent. That is three agents for what should mostly be a deterministic pipeline with LLM steps injected at specific points. Agents introduce latency, unpredictability, and debugging difficulty. When extraction fails at chunk 47 of 200, I want a stack trace, not a conversation.

**Reality**: The agent model does provide tool orchestration, but the ingest pipeline's steps (parse -> chunk -> extract -> dedup -> resolve -> load) are sequential and deterministic. The agent adds value only for interactive schema inference and ontology review.

**Response**: Clarify that the agent orchestrates the pipeline but individual steps are deterministic functions. Consider making the agent optional for non-interactive batch runs.

### 5. "Missing confidence model for extracted triples"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: This is the biggest gap. Entities, relationships, and facts are extracted with no confidence score. Every triple looks equally trustworthy regardless of whether it came from a clear statement or an LLM inference from ambiguous text. Downstream reasoning, query ranking, and graph pruning all need confidence scores.

**Reality**: The design includes `normalized_score` for entity resolution and `confidence` for ontology normalization, but not for extracted entities or relationships.

**Response**: Add `confidence` field to entities, relationships, and facts. Confidence should reflect extraction certainty - derived from LLM self-assessment, cross-chunk corroboration, and ontology coverage.

---

## Score Trajectory (6 iterations)

| Version | Score | Delta | Key correction |
|---------|-------|-------|----------------|
| v1 | 88.9 | - | Baseline evaluation |
| v2 | 27.8 | -61.1 | Confidence model, three-tier normalization, interactive/batch modes |
| v3 | 22.6 | -5.2 | Module interfaces with Pydantic contracts |
| v4 | 20.4 | -2.2 | Schema-as-configuration, lockfile, versioning |
| v5 | 17.8 | -2.6 | Reference benchmark dataset, measurement methodology |
| v6 | 15.5 | -2.3 | All features core (removed optional distinction) |

**Total risk**: 136. **Final residual**: 15.5 (11.4% of total - below 15% threshold).
