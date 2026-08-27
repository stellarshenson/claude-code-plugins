# Devil's Advocate - kg-builder-cli DESIGN.md

## The Devil

**Role**: Senior backend engineer with 15+ years building production data pipelines, reviewing a design document for implementation readiness
**Cares about**: implementation complexity, runtime predictability, maintenance burden, time-to-first-value
**Style**: data-driven, pragmatic, allergic to speculative architecture
**Default bias**: skeptical of agent-heavy designs, prefers deterministic pipelines, suspicious of LLM-in-the-loop for infrastructure decisions
**Triggers**: overengineering, optional features described as core, missing confidence/provenance on extracted data, vague error handling
**Decision**: approve for implementation, request simplification, or reject sections as premature

---

## Concern Catalogue

### 1. "Agents are overused - most ingestion steps should be deterministic pipelines"

**Likelihood: 5** | **Impact: 4** | **Risk: 20**

**Their take**: Every command spawns an agent. That is three agents for what should mostly be a deterministic pipeline with LLM steps injected at specific points. Agents introduce latency, unpredictability, and debugging difficulty. When extraction fails at chunk 47 of 200, I want a stack trace, not a conversation. The ingest pipeline should be code, not an agent deciding what to do next.

**Reality**: The Strands SDK agent model does provide tool orchestration, but the ingest pipeline's steps (parse -> chunk -> extract -> dedup -> resolve -> load) are sequential and deterministic. The agent adds value only for interactive schema inference and ontology review. For batch ingestion, the agent layer is overhead.

**Response**: The design should clarify that the agent orchestrates the pipeline but individual steps are deterministic functions. The agent's role in `kg ingest` is primarily for interactive initialization and schema inference - batch extraction and loading should be direct function calls, not agent-mediated tool invocations. Consider making the agent optional for non-interactive batch runs.

### 2. "Too many optional features presented as core architecture"

**Likelihood: 5** | **Impact: 3** | **Risk: 15**

**Their take**: Page nodes, Section nodes, TableElement, ImageElement, child chunks, OWL reasoning, semantic chunking, parent-child chunking, image description enrichment - these are all marked "optional" but described with the same depth and prominence as core features. A new contributor reading this document cannot tell what they need to implement for a working v1 versus what is future scope. The design reads like a feature catalogue, not an implementation blueprint.

**Reality**: These features are genuinely optional enrichments. The document does mark them as optional. But the presentation gives them equal weight to core functionality.

**Response**: The design should explicitly define a "Core Model" (Document, Chunk, Entity, FactNode, OntologyType, Source) versus "Extensions" (Page, Section, TableElement, ImageElement, child chunks). Each optional feature should be marked with a visual indicator and the document should include a phased implementation section.

### 3. "LLM normalization of arbitrary ontology formats is a silent corruption risk"

**Likelihood: 4** | **Impact: 4** | **Risk: 16**

**Their take**: You let an LLM convert markdown prose into an ontology schema. That is ontology hallucination. The LLM will invent types, misinterpret relationships, and produce schemas that look plausible but are wrong. JSON should be deterministic mapping, not LLM interpretation. Only truly unstructured formats (markdown, plain text) should use the LLM path. The design treats all non-YAML, non-OWL formats the same way, which hides the risk.

**Reality**: The normalization pipeline does use Pydantic validation and confidence scoring. The output is presented for interactive review. But the design does not distinguish between formats that could be parsed deterministically (JSON with known structure) and formats that genuinely need LLM interpretation.

**Response**: Split normalization into two tiers: deterministic parsing (JSON with recognizable ontology structure -> direct mapping) and LLM interpretation (markdown, plain text, unknown formats). Add a validation step that compares LLM-normalized output against the source to flag potential hallucinations.

### 4. "Schema inference conversation loop will produce unstable schemas"

**Likelihood: 3** | **Impact: 4** | **Risk: 12**

**Their take**: The schema inference loop (sample -> propose -> review -> refine -> confirm) depends on conversation state. If the user asks slightly different questions in two sessions, they get different schemas for the same data. The schema should be a deterministic artefact derived from data profiling, not a conversation outcome. The LLM should propose, the user should edit a YAML file, done. Conversation history should not be a dependency.

**Reality**: The design does save the confirmed schema to `.kg-builder/schemas/` as a static file. But the interactive refinement loop means the same data can produce different schemas depending on conversation flow. Agent memory mitigates this by checking for prior sessions, but memory is advisory.

**Response**: Clarify that the conversation produces a static schema file which becomes the sole authority. Once saved, the schema is configuration, not conversation. Re-inference produces a fresh proposal compared against the existing schema, not a continuation of the previous conversation.

### 5. "Missing confidence model for extracted triples"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: This is the biggest gap. Entities, relationships, and facts are extracted with no confidence score. The normalization metadata stores `normalized_score` for resolution, but the extraction itself produces no confidence signal. Every triple looks equally trustworthy regardless of whether it came from a clear statement or an LLM inference from ambiguous text. Downstream reasoning, query ranking, and graph pruning all need confidence scores. Without them the graph is a flat assertion layer with no way to distinguish reliable facts from noise.

**Reality**: The design includes `normalized_score` for entity resolution and `confidence` for ontology normalization, but not for extracted entities or relationships. FactNodes store `embedding` but not `confidence`. The extraction output format (Section 19) has no confidence field on entities or relationships.

**Response**: Add `confidence` field to entities, relationships, and facts in the extraction output format. Confidence should reflect extraction certainty - derived from LLM self-assessment, cross-chunk corroboration (entity appears in multiple chunks), and ontology coverage (entity matches a known type vs NEW_ prefix). Store `extraction_model` on all extracted elements for provenance.

### 6. "Entity resolution lacks Levenshtein distance details and similarity matrix"

**Likelihood: 4** | **Impact: 3** | **Risk: 12**

**Their take**: The resolution pipeline mentions "Levenshtein ratio" in passing but does not specify thresholds, distance metrics, or how candidates are selected for pairwise comparison. For large entity sets, pairwise comparison is O(n^2). The design needs a similarity matrix approach with blocking strategies to make this tractable. Without it, resolution will either be too slow (comparing everything) or too lossy (arbitrary cutoffs).

**Reality**: The SpaCy+fuzzy pre-filter step mentions "token overlap and Levenshtein ratio" but provides no thresholds, no blocking strategy, and no description of how the similarity matrix is constructed or pruned. The embedding step says "pairwise within each type group" but does not address the O(n^2) scaling problem.

**Response**: Specify Levenshtein ratio thresholds (e.g., 0.85 for name matching), describe type-based blocking (only compare entities within the same type group), and add a similarity matrix construction step with configurable cutoff. For large entity sets, use approximate nearest neighbor (ANN) indexing on embeddings rather than brute-force pairwise comparison.

### 7. "No concurrency model for LLM calls"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: The config has `concurrency: 4` but the design never describes how parallel LLM calls are managed. Are chunks extracted in parallel? How are results merged? What about rate limiting across parallel calls? If four extraction calls modify the ontology buffer simultaneously, what is the synchronization model?

**Reality**: The design mentions `concurrency` as a config option and "parallel LLM requests" but does not describe the concurrency model. The ontology buffer is described as an in-memory structure that receives feedback after each document, but the interaction between parallel extraction and sequential buffer updates is not specified.

**Response**: Clarify that concurrency applies to chunk extraction within a single document - multiple chunks are extracted in parallel, but buffer feedback happens after all chunks from a document are collected. Documents are processed sequentially to maintain buffer consistency.

### 8. "Post-load OWL reasoning is a complexity trap"

**Likelihood: 3** | **Impact: 2** | **Risk: 6**

**Their take**: The HermiT reasoner pipeline (export to RDF -> load into owlready2 -> reason -> import inferred triples) is a full round-trip through two different graph representations. This is fragile, slow, and adds a heavy dependency. The Cypher-based alternative is simpler and covers the most common case (subclass propagation). The full reasoning pipeline should be removed from v1 and replaced entirely by the Cypher approach.

**Reality**: The design already presents the Cypher-based approach as an alternative. Post-load reasoning is optional and off by default.

**Response**: Mark the full HermiT pipeline as a future extension. Keep the Cypher-based subclass propagation as the v1 approach. This removes the n10s dependency and the RDF export complexity.

### 9. "No data volume estimates or performance characteristics"

**Likelihood: 4** | **Impact: 3** | **Risk: 12**

**Their take**: The design never states what scale it targets. Is this for 10 documents or 10,000? 1,000 entities or 1,000,000? The batch size of 500 and concurrency of 4 suggest small-to-medium scale, but the entity resolution pipeline with embedding similarity suggests larger ambitions. Without scale targets, I cannot evaluate whether the architecture is appropriate.

**Reality**: No performance targets, scale estimates, or benchmarking strategy are mentioned anywhere in the document.

**Response**: Add a "Scale and Performance" subsection with target ranges (e.g., "designed for 10-10,000 documents, 1,000-100,000 entities per graph") and note where architecture decisions change at different scales.

### 10. "The module structure lists 30+ files but has no interface contracts"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: Section 16 lists files and describes what each module does, but there are no function signatures, no data flow types, no interface contracts. What does `buffer.py` expose? What data structure does `extraction/unstructured.py` pass to `loading/loader.py`? Without these, the module structure is a file listing, not a design.

**Reality**: The section describes interface boundaries in prose ("loading/ depends only on config/ for connection details, receives entities and relationships as data structures") but does not define the data structures or function signatures.

**Response**: Add key interface types - at minimum the data structures passed between major modules (extraction output -> loader input, buffer state -> prompt constructor, config -> all modules). Pydantic models for these interfaces would make the design implementable.

---

## Scorecard - v1 (DESIGN.md, 1852 lines, commit 79991e0)

| # | Concern | Risk | Score | Residual | How addressed |
|---|---------|------|-------|----------|---------------|
| 1 | Agent overuse | 20 | 40% | 12.0 | Section 2 describes agents as command-level orchestrators but does not distinguish interactive vs batch modes. No mention of deterministic pipeline fallback |
| 2 | Optional features as core | 15 | 45% | 8.3 | Individual features marked "optional" in prose but no consolidated core vs extensions distinction |
| 3 | LLM normalization risk | 16 | 55% | 7.2 | Section 5.2 mentions Pydantic validation, confidence scoring, and interactive review. Does not distinguish deterministic vs LLM parsing paths for different formats |
| 4 | Schema inference instability | 12 | 60% | 4.8 | Section 7.3 saves schema to static file, memory checks for prior sessions. Does not explicitly state schema-as-configuration principle |
| 5 | Missing confidence model | 25 | 15% | 21.3 | Only `normalized_score` for resolution. No confidence on extracted entities, relationships, or facts. Extraction output format (Section 19) has no confidence field |
| 6 | Missing Levenshtein/similarity matrix details | 12 | 25% | 9.0 | Section 6.7 mentions "Levenshtein ratio" once. No thresholds, no blocking strategy, no similarity matrix, no ANN for embeddings |
| 7 | No concurrency model | 9 | 20% | 7.2 | `concurrency: 4` in config, "parallel LLM requests" mentioned. No synchronization model for buffer updates during parallel extraction |
| 8 | OWL reasoning complexity | 6 | 70% | 1.8 | Marked optional, off by default, Cypher alternative provided. Still presented with full implementation detail |
| 9 | No scale targets | 12 | 5% | 11.4 | No performance targets, volume estimates, or benchmarking strategy anywhere in the document |
| 10 | Module structure lacks interfaces | 9 | 35% | 5.9 | Prose descriptions of boundaries but no data types, function signatures, or interface contracts |

**v1 document score (total residual risk)**: 88.9 (lower = better, max 136)

---

## Scorecard - v2 (DESIGN_v02.md, 1951 lines)

**Corrections applied**: #5a evidence spans, #5b source frequency, #3 three-tier normalization, #1 interactive/autonomous mode with batch logging, TUI harness

| # | Concern | Risk | v1 Score | v2 Score | v2 Residual | How addressed in v2 |
|---|---------|------|----------|----------|-------------|---------------------|
| 1 | Agent overuse | 20 | 40% | 90% | 2.0 | Section 2 rewritten with "Interactive vs Autonomous Agent Mode". Explicit `--batch` flag added to `kg ingest`. All activities annotated as interactive checkpoints vs direct execution. Batch decision logging to `.kg-builder/runs/`. Agent always present in both modes - no bypassing |
| 2 | Optional features as core | 15 | 45% | 80% | 3.0 | Section 8 already has "Core vs Extension Node Types" from v1 corrections. v2 unchanged - still well addressed |
| 3 | LLM normalization risk | 16 | 55% | 90% | 1.6 | Section 5.2 rewritten as "Three-Tier Normalization Pipeline". Tier 1: programmatic parse via py-repl for structured formats (up to 3 retries). Tier 2: LLM-assisted repair for specific validation failures only. Tier 3: full LLM interpretation (fallback). JSON row in 5.1 table updated. Diagnostic output after every tier with interactive confirm |
| 4 | Schema inference instability | 12 | 60% | 60% | 4.8 | Unchanged from v1. Schema saved to static file, memory checks for prior sessions |
| 5 | Missing confidence model | 25 | 85% | 92% | 2.0 | v1 already added `confidence` and `extraction_model` to extraction output. v2 adds `evidence_span` (character offsets) and `source_count`/`document_count` (cross-chunk/document corroboration) as config options. Prose explains trade-offs (latency, prompt size). Both default false for opt-in complexity |
| 6 | Missing Levenshtein/similarity matrix details | 12 | 85% | 85% | 1.8 | v1 corrections already addressed. Type-based blocking, Levenshtein ratio 0.85 threshold, similarity matrix, ANN for large sets |
| 7 | No concurrency model | 9 | 80% | 80% | 1.8 | v1 corrections already addressed. Intra-document parallel, inter-document sequential, buffer feedback at document boundary |
| 8 | OWL reasoning complexity | 6 | 70% | 70% | 1.8 | Unchanged from v1. Still optional, off by default, Cypher alternative provided |
| 9 | No scale targets | 12 | 70% | 70% | 3.6 | v1 corrections already addressed. Scale targets in Section 2 |
| 10 | Module structure lacks interfaces | 9 | 35% | 40% | 5.4 | Minor improvement: `tui/` subpackage added with 3 modules. Interface contracts still described in prose without function signatures |

**v2 document score (total residual risk)**: 27.8 (lower = better, max 136)

**Score change**: 88.9 -> 27.8 (improvement of 61.1)

**Top gaps** (highest residual risk):
1. **#10 - Module structure lacks interfaces** (residual 5.4) - still prose descriptions without function signatures or data types
2. **#4 - Schema inference instability** (residual 4.8) - no explicit schema-as-configuration principle, conversation dependency not addressed
3. **#9 - No scale targets** (residual 3.6) - targets present but no benchmarking strategy or performance test plan
4. **#2 - Optional features as core** (residual 3.0) - core vs extensions defined but no phased implementation roadmap
5. **#1 - Agent overuse** (residual 2.0) - well addressed, minor gap: no example of batch run report format

---

## Scorecard - v3 (DESIGN_v03_23.md, 2161 lines)

**Correction applied**: #10 module structure rewrite with shared `types/` module, interface contracts, dependency graph

| # | Concern | Risk | v2 Score | v3 Score | v3 Residual | How addressed in v3 |
|---|---------|------|----------|----------|-------------|---------------------|
| 1 | Agent overuse | 20 | 90% | 90% | 2.0 | Unchanged from v2 |
| 2 | Optional features as core | 15 | 80% | 80% | 3.0 | Unchanged from v2 |
| 3 | LLM normalization risk | 16 | 90% | 90% | 1.6 | Unchanged from v2 |
| 4 | Schema inference instability | 12 | 60% | 60% | 4.8 | Unchanged from v2 |
| 5 | Missing confidence model | 25 | 92% | 92% | 2.0 | Unchanged from v2 |
| 6 | Levenshtein/similarity details | 12 | 85% | 85% | 1.8 | Unchanged from v2 |
| 7 | No concurrency model | 9 | 80% | 80% | 1.8 | Unchanged from v2 |
| 8 | OWL reasoning complexity | 6 | 70% | 70% | 1.8 | Unchanged from v2 |
| 9 | No scale targets | 12 | 70% | 70% | 3.6 | Unchanged from v2 |
| 10 | Module structure lacks interfaces | 9 | 40% | 82% | 1.6 | Section 16 fully rewritten. New `types/` module with 10 Pydantic contract files (config, document, extraction, ontology, resolution, loading, query, pipeline, migration). Mermaid dependency graph showing module relationships. Interface contracts table listing 12 boundary crossings with named types and key fields. Every submodule annotated with accepts/returns types. Dependency rules per module. Frozen `OntologyState` snapshot pattern prevents extraction/ontology circular coupling |

**v3 document score (total residual risk)**: 22.6 (lower = better, max 136)

**Score change**: 27.8 -> 22.6 (improvement of 5.2)

**Top gaps** (highest residual risk):
1. **#4 - Schema inference instability** (residual 4.8) - no explicit schema-as-configuration principle
2. **#9 - No scale targets** (residual 3.6) - targets present but no benchmarking strategy
3. **#2 - Optional features as core** (residual 3.0) - no phased implementation roadmap
4. **#1 - Agent overuse** (residual 2.0) - no batch run report format example
5. **#5 - Confidence model** (residual 2.0) - well addressed

---

## Scorecard - v4 (DESIGN_v04_20.md)

**Correction applied**: #4 schema inference stability - schema-as-configuration principle, lockfile, deterministic baseline, schema versioning with SchemaVersion nodes, CREATED_UNDER linking, schema recovery via `kg init`

| # | Concern | Risk | v3 Score | v4 Score | v4 Residual | How addressed in v4 |
|---|---------|------|----------|----------|-------------|---------------------|
| 1 | Agent overuse | 20 | 90% | 90% | 2.0 | Unchanged from v3 |
| 2 | Optional features as core | 15 | 80% | 80% | 3.0 | Unchanged from v3 |
| 3 | LLM normalization risk | 16 | 90% | 90% | 1.6 | Unchanged from v3 |
| 4 | Schema inference instability | 12 | 60% | 90% | 1.2 | Section 7.3 fully rewritten. Schema-as-configuration principle: conversation is UX convenience, saved file is sole authority. Lockfile at `.kg-builder/schema.lock` with PID and timestamp prevents concurrent mutation. Deterministic field profile baseline (`<source>.profile.yml`) from py-repl ensures reproducible starting point. Schema versioning: every confirmed schema gets integer version, materialized as `SchemaVersion` node in Neo4J with version, source, timestamp, hash. Entities linked via `CREATED_UNDER` relationship. Schema recovery via `kg init` introspects graph to reconstruct `.kg-builder/` when missing. Section 8 graph structure updated with SchemaVersion node. `kg ingest` initialization updated with three scenarios (fresh, recovery, validation) |
| 5 | Missing confidence model | 25 | 92% | 92% | 2.0 | Unchanged from v3 |
| 6 | Levenshtein/similarity details | 12 | 85% | 85% | 1.8 | Unchanged from v3 |
| 7 | No concurrency model | 9 | 80% | 80% | 1.8 | Unchanged from v3 |
| 8 | OWL reasoning complexity | 6 | 70% | 70% | 1.8 | Unchanged from v3 |
| 9 | No scale targets | 12 | 70% | 70% | 3.6 | Unchanged from v3 |
| 10 | Module structure lacks interfaces | 9 | 82% | 82% | 1.6 | Unchanged from v3 |

**v4 document score (total residual risk)**: 20.4 (lower = better, max 136)

**Score change**: 22.6 -> 20.4 (improvement of 2.2)

**Top gaps** (highest residual risk):
1. **#9 - No scale targets** (residual 3.6) - targets present but no benchmarking strategy
2. **#2 - Optional features as core** (residual 3.0) - no phased implementation roadmap
3. **#1 - Agent overuse** (residual 2.0) - no batch run report format example
4. **#5 - Confidence model** (residual 2.0) - well addressed
5. **#6 - Levenshtein/similarity** (residual 1.8) - well addressed

---

## Scorecard - v5 (DESIGN_v05_18.md)

**Correction applied**: #9 reference benchmark dataset and measurement methodology

| # | Concern | Risk | v4 Score | v5 Score | v5 Residual | How addressed in v5 |
|---|---------|------|----------|----------|-------------|---------------------|
| 1 | Agent overuse | 20 | 90% | 90% | 2.0 | Unchanged from v4 |
| 2 | Optional features as core | 15 | 80% | 80% | 3.0 | Unchanged from v4 |
| 3 | LLM normalization risk | 16 | 90% | 90% | 1.6 | Unchanged from v4 |
| 4 | Schema inference instability | 12 | 90% | 90% | 1.2 | Unchanged from v4 |
| 5 | Missing confidence model | 25 | 92% | 92% | 2.0 | Unchanged from v4 |
| 6 | Levenshtein/similarity details | 12 | 85% | 85% | 1.8 | Unchanged from v4 |
| 7 | No concurrency model | 9 | 80% | 80% | 1.8 | Unchanged from v4 |
| 8 | OWL reasoning complexity | 6 | 70% | 70% | 1.8 | Unchanged from v4 |
| 9 | No scale targets | 12 | 70% | 92% | 0.96 | Section 2 expanded with "Reference Benchmark Dataset" subsection. 23 CPAP PDF documents (~63MB) from `data/external/cpap-datasheets-and-manuals.zip` as the standard evaluation corpus - datasheets, brochures, user manuals, clinical guides, product catalogues. Six performance metrics per pipeline stage (parse, chunk, extract, dedup/resolve, load, end-to-end) with wall time, throughput, token consumption, and memory. Five quality metrics: entity coverage (spot-check against curated list), relationship accuracy (50-sample true positive rate), duplicate rate, ontology coherence, confidence distribution analysis. `--benchmark` flag enables extended instrumentation. Results persisted to `.kg-builder/runs/`. Baseline quality profile established on first run, subsequent runs detect regressions |
| 10 | Module structure lacks interfaces | 9 | 82% | 82% | 1.6 | Unchanged from v4 |

**v5 document score (total residual risk)**: 17.8 (lower = better, max 136)

**Score change**: 20.4 -> 17.8 (improvement of 2.6)

**Top gaps** (highest residual risk):
1. **#2 - Optional features as core** (residual 3.0) - no phased implementation roadmap
2. **#1 - Agent overuse** (residual 2.0) - no batch run report format example
3. **#5 - Confidence model** (residual 2.0) - well addressed
4. **#6 - Levenshtein/similarity** (residual 1.8) - well addressed
5. **#8 - OWL reasoning** (residual 1.8) - well addressed

---

## Scorecard - v6 (DESIGN_v06_16.md)

**Corrections applied**: #2 removed core/extension distinction - all features are core. #1 batch report format deferred to runtime iteration (intentional design decision, not a gap)

| # | Concern | Risk | v5 Score | v6 Score | v6 Residual | How addressed in v6 |
|---|---------|------|----------|----------|-------------|---------------------|
| 1 | Agent overuse | 20 | 90% | 90% | 2.0 | Unchanged. Batch report format intentionally deferred to runtime iteration - the system will generate reports and the format will be refined based on actual output |
| 2 | All features are core | 15 | 80% | 95% | 0.75 | Core/extension distinction removed entirely. Section 8 "Core vs Extension Node Types" rewritten as "Node Types" - all 12 node types are part of the core model. Removed "optional" markers from graph structure diagram (Page, Section, TableElement, ImageElement, child Chunk). Removed "optional" qualifiers from narrative sections on image description, table/image elements, chunk linking, section detection. No phased roadmap needed because everything ships together |
| 3 | LLM normalization risk | 16 | 90% | 90% | 1.6 | Unchanged from v5 |
| 4 | Schema inference instability | 12 | 90% | 90% | 1.2 | Unchanged from v5 |
| 5 | Missing confidence model | 25 | 92% | 92% | 2.0 | Unchanged from v5 |
| 6 | Levenshtein/similarity details | 12 | 85% | 85% | 1.8 | Unchanged from v5 |
| 7 | No concurrency model | 9 | 80% | 80% | 1.8 | Unchanged from v5 |
| 8 | OWL reasoning complexity | 6 | 70% | 70% | 1.8 | Unchanged from v5 |
| 9 | No scale targets | 12 | 92% | 92% | 0.96 | Unchanged from v5 |
| 10 | Module structure lacks interfaces | 9 | 82% | 82% | 1.6 | Unchanged from v5 |

**v6 document score (total residual risk)**: 15.5 (lower = better, max 136)

**Score change**: 17.8 -> 15.5 (improvement of 2.3)

**Top gaps** (highest residual risk):
1. **#1 - Agent overuse** (residual 2.0) - batch report format deferred to runtime
2. **#5 - Confidence model** (residual 2.0) - well addressed
3. **#6 - Levenshtein/similarity** (residual 1.8) - well addressed
4. **#7 - Concurrency model** (residual 1.8) - well addressed
5. **#8 - OWL reasoning** (residual 1.8) - well addressed
