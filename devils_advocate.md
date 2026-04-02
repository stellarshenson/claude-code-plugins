# Devil's Advocate - Remaining Features Program

## The Devil

**Role**: Systems architect obsessed with design unity and minimal surface area
**Cares about**: (1) One canonical location for each piece of data, (2) No orphan files or parallel tracking mechanisms, (3) Every data structure should be self-describing, (4) Fewer moving parts = fewer bugs
**Style**: Pattern-driven. If two things store related data, they should be one thing. If a file has no schema, it's technical debt.
**Default bias**: Against adding files, against adding fields, against complexity. Prove it's necessary.
**Triggers**: Separate files tracking the same concern (context.yaml + context_ack.yaml), flat key-value when rich metadata is needed, "backward compat" used as excuse to keep two code paths
**Decision**: Approve the program or demand consolidation before implementation
**Source**: user-described persona

---

## Concern Catalogue

### 1. "context.yaml and context_ack.yaml are the same concern stored in two files"

**Likelihood: 8** | **Impact: 8** | **Risk: 64**

**Their take**: context.yaml stores `{phase: message}`. context_ack.yaml stores `{phase: [seen_by_phases]}`. These are TWO files about the SAME data entity - a context message. The ack file is a shadow copy that must stay in sync. If context.yaml is cleared but context_ack.yaml isn't, you get phantom acknowledgments. If a context message is updated, the ack data references stale content. This is the classic "data in two places" anti-pattern.

The architect demands: ONE file, ONE entry per context message, ALL metadata inline:
```yaml
RESEARCH:
  message: "focus on connector routing"
  created: "2026-04-02T14:00:00Z"
  acknowledged_by: [PLAN, IMPLEMENT]
  processed: false
```

**Reality**: The program already proposes this exact fix. But the CURRENT code (v0.8.51) has the split. The fix is planned but not implemented.

**Response**: This IS the top work item. Implement it first.

### 2. "The version check cache file is another orphan"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: `.auto-build-claw/.version_check` is a plain text file containing just a version string. No timestamp in the content - it uses file mtime for cache invalidation. This means: (1) copying the file preserves content but may reset mtime, (2) `_clean_artifacts_dir` could wipe it unless it's in the preserve list, (3) it's an invisible dot-file that's hard to discover.

Why not store the version check in a proper state structure? The artifacts directory already has `state.yaml` and `log.yaml` with structured data. A `.version_check` plain text file with no schema is a wart.

**Reality**: The version check is low-frequency (once per 24h) and non-critical (fails silently). A plain text file is the simplest thing that works. The mtime-based cache is elegant but fragile.

**Response**: Consider storing as `{latest_version: str, checked_at: ISO8601}` in YAML. Or accept the pragmatic plain-text file. Low priority.

### 3. "hypothesis_autowrite prompt says 'Write entries' not 'Append entries'"

**Likelihood: 8** | **Impact: 5** | **Risk: 40**

**Their take**: workflow.yaml ACTION::HYPOTHESIS_AUTOWRITE prompt says "Write entries to hypotheses.yaml in YAML list format." This is ambiguous - does "write" mean overwrite or append? A generative action (claude -p) receiving this prompt will interpret "write" as "create the file with these entries" - overwriting whatever was there. The _build_hypothesis_context loads prior hypotheses for the HYPOTHESIS phase, but if hypothesis_autowrite then overwrites the file, the accumulation is lost.

The architect demands: the prompt must say "Read existing hypotheses.yaml first. APPEND new entries, UPDATE existing entries by ID (matching by ID field). Do NOT remove entries unless their status is DONE or REMOVED."

**Reality**: The program identifies this as a work item. The current prompt IS ambiguous.

**Response**: Fix the prompt in workflow.yaml. One line change, high impact on hypothesis persistence.

### 4. "_clean_artifacts_dir preserves resources/ but not context_ack.yaml"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: `_CLEAN_PRESERVE` = `{"context.yaml"}` and `_CLEAN_PRESERVE_DIRS` = `{"resources"}`. But `context_ack.yaml` is NOT in the preserve set. Every `new --clean` wipes the acknowledgment tracking. This contradicts the purpose of tracking which phases have seen which context messages.

Once context.yaml becomes rich (with acknowledged_by inline), this concern vanishes - there's only one file to preserve and it's already preserved.

**Reality**: This is another reason to consolidate into context.yaml. The separate file creates a preservation gap.

**Response**: Consolidating into context.yaml (concern #1) fixes this automatically.

### 5. "Three separate data files with no schema versioning"

**Likelihood: 3** | **Impact: 5** | **Risk: 15**

**Their take**: context.yaml, hypotheses.yaml, and .version_check all have implicit schemas with no version marker. When the format changes (like context.yaml gaining rich entries), the code does format detection inline (`if isinstance(entry, str): migrate`). Each format migration is ad-hoc code in the function that reads the file. With 3 files and growing, this becomes unmaintainable.

The architect wants: a `schema_version` field at the top of each YAML file, and a centralized migration registry.

**Reality**: Over-engineering for 3 files. The inline migration (`isinstance` check) is simple and obvious. A schema registry adds complexity without proportional benefit.

**Response**: Accept inline migration for now. Note for future if file count grows beyond 5.

### 6. "cmd_status has grown into a god function"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: `cmd_status` now displays: iteration info, phase progress, agents recorded, AND context messages with acknowledgment. Each new feature adds another display block to the same function. The function is becoming a dashboard renderer that knows about every subsystem.

**Reality**: Status is supposed to show everything. That's its job. The blocks are independent and don't interact.

**Response**: Low priority. Monitor but don't refactor yet.

---

## Scorecard v01 (PROGRAM.md as-is)

| # | Concern | Risk | Score | Residual | Reasoning |
|---|---------|------|-------|----------|-----------|
| 1 | Context split into 2 files | 64 | 80% | 12.8 | Program explicitly proposes rich context entries with acknowledged_by inline. Remove context_ack.yaml. Well covered. Residual: hasn't been implemented yet. |
| 2 | Version check orphan file | 25 | 40% | 15.0 | Program doesn't address .version_check format. Stays as plain text with mtime cache. Minor wart but not addressed. |
| 3 | Hypothesis autowrite ambiguity | 40 | 85% | 6.0 | Program has explicit work item to fix prompt to say append/update. Well covered. |
| 4 | context_ack.yaml not preserved | 25 | 90% | 2.5 | Consolidation (concern #1) eliminates this automatically. Program addresses root cause. |
| 5 | No schema versioning | 15 | 30% | 10.5 | Program doesn't mention schema versioning. Relies on inline isinstance checks. Pragmatic but unaddressed. |
| 6 | cmd_status growing | 9 | 50% | 4.5 | Program adds more to status (timestamps, processed flag) without mentioning extraction. Minor. |

**Document score**: 51.3 (total residual risk)
**Total absolute risk**: 178
**Residual %**: 28.8%

**Top gaps**:
1. Version check file format (15.0) - plain text with mtime, no schema
2. Context file consolidation (12.8) - planned but not yet done
3. No schema versioning (10.5) - inline migration only
4. Hypothesis prompt (6.0) - work item exists, needs execution
5. cmd_status growth (4.5) - monitoring, not blocking

---

## Options for Top Gaps

### Concern #2: Version check file (residual 15.0)

**Option A**: Convert to YAML `{latest: "0.8.51", checked_at: "2026-04-02T14:00:00Z"}`
- Expected effect: #2 +40%, #5 +10% (schema more explicit)

**Option B**: Keep plain text, add to _CLEAN_PRESERVE
- Expected effect: #2 +20% (preserved but still schemeless)

**Recommendation**: Option A - 2 lines of code, makes the file self-describing.

### Concern #5: Schema versioning (residual 10.5)

**Option A**: Add `_schema_version: 1` to each YAML file
- Expected effect: #5 +50% but adds complexity everywhere

**Option B**: Accept inline migration, document the format in docstrings
- Expected effect: #5 +20%, zero code change

**Recommendation**: Option B - inline migration is the right choice at this scale.
