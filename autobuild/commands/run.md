---
description: Run the autobuild orchestrator for structured improvement cycles
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "describe what you want to build or improve"
---

# Autobuild - Run Orchestrator

Load and execute the autobuild skill for autonomous iteration orchestration.

## Startup Sequence

When the user asks to run an improvement cycle, execute these skills IN ORDER before starting the orchestrator:

1. **program-writer** - Generate PROGRAM.md from user's objective. Ask clarifying questions about scope, constraints, exit conditions. Do NOT proceed until user approves the program.

2. **benchmark-writer** - Generate BENCHMARK.md from the approved PROGRAM.md. Define score formula, direction (minimize/maximize), checklist sections, evaluation instructions. Do NOT proceed until user approves the benchmark.

3. **autobuild** - ASK the user which workflow to execute:
   - `full` - Feature work, improvements, research-driven changes
   - `gc` - Cleanup, dead code removal, refactoring
   - `hotfix` - Targeted bug fix, minimal ceremony

   Then ASK iteration count (or 0 for run-until-complete). Then start:
   ```bash
   orchestrate new --type <chosen> \
     --objective "Implement the program defined in PROGRAM.md (read PROGRAM.md)" \
     --iterations <chosen> \
     --benchmark "Read BENCHMARK.md and evaluate each [ ] item. Mark [x] if passing. EDIT the file. UPDATE Score Tracking table. Report composite score."
   ```

**MANDATORY**: Do NOT skip steps 1 and 2. Do NOT start the orchestrator without an approved PROGRAM.md and BENCHMARK.md. The user must see and approve both documents before any work begins.

**NEVER write BENCHMARK.md directly with the Write tool.** Always invoke the benchmark-writer skill. The skill has safety rules that prevent exit conditions from leaking into the benchmark. Writing BENCHMARK.md manually bypasses these rules - this is the #1 cause of malformed benchmarks.

## Direct Usage

If PROGRAM.md and BENCHMARK.md already exist, skip to step 3:

```bash
/autobuild:run new --type full --objective "..." --iterations N [--benchmark "..."]
/autobuild:run start --understanding "brief summary"
/autobuild:run end --evidence "what was done" --agents "a,b,c" --output-file "path"
/autobuild:run status
/autobuild:run skip --reason "why" [--force]
/autobuild:run reject --reason "what needs fixing"
/autobuild:run add-iteration --count N [--objective "updated objective"]
/autobuild:run validate
```

**MANDATORY**: ALL work MUST go through the orchestrator. No code changes outside IMPLEMENT phase. No commits outside RECORD phase. No benchmark evaluation outside TEST phase. No exceptions.
