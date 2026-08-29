---
description: Hostile independent review by spawning fresh reviewer subagents - invokes the devils-advocate:adversarial-review skill, picking the adversary a data science project needs (data-scientist, architect, popular-science, ux-designer); find, fix, re-confirm clean
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, TaskCreate, TaskUpdate, Skill]
argument-hint: "what to review, e.g. 'the E12 experiments log before I trust it' or 'the architecture of the pipeline' or 'the article for a generalist reader'"
---

# Adversarial Review

Invoke the `datascience:adversarial-review` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
