---
description: Hostile independent review of the acceptance-criteria or defects document - spawns the devils-advocate adversary the discipline calls for (analyst on criteria, qa-engineer on defects); find, fix through pm-tools, re-confirm clean
allowed-tools: [Read, Write, Bash, Agent, TaskCreate, TaskUpdate, Skill]
argument-hint: "what to review, e.g. 'the acc-crit doc before the sprint starts' or 'the defects list - is anything untestable or mis-triaged'"
---

# Review

Invoke the `project-management:review` skill and follow it exactly. It owns the whole procedure; this command only routes into it.

Pass the remainder of this invocation through unchanged as the skill's arguments.
