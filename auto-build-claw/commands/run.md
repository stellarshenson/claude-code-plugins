---
description: Run the auto-build-claw orchestrator for structured improvement cycles
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "new --type full --objective \"...\" --iterations N [--benchmark \"...\"] | start | end | status | skip | reject | add-iteration | validate"
---

# Auto Build Claw - Run Orchestrator

Load and execute the auto-build-claw skill for autonomous iteration orchestration.

## Usage

```bash
/auto-build-claw:run new --type full --objective "improve X" --iterations 3
/auto-build-claw:run start --understanding "brief summary"
/auto-build-claw:run end --evidence "what was done" --agents "a,b,c" --output-file "path"
/auto-build-claw:run status
/auto-build-claw:run skip --reason "why" [--force]
/auto-build-claw:run reject --reason "what needs fixing"
/auto-build-claw:run add-iteration --count N [--objective "updated objective"]
/auto-build-claw:run validate
```

When invoked, load the auto-build-claw skill and pass the arguments to the orchestrator.
