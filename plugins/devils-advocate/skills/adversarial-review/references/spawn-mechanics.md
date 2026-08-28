# Spawn mechanics - `claude -p` paths and gotchas

Subagent spawn is the default (see SKILL.md). `claude -p` is for what a subagent cannot do: genuinely deny tools in Mode 1, or pin a different model. Every gotcha below cost a wasted run.

## Mode 1 fallback - the only path that truly denies tools

```bash
# 1. Capture ONLY the implementation diff (exclude docs, lockfiles, golden
#    snapshots, generated files - they bloat the prompt and distract the reviewer).
git diff -- path/to/src/a.py path/to/src/b.tsx ... > /tmp/impl.diff

# 2. Build the prompt: no-tools instruction + adversarial framing + inline diff.
{ cat /tmp/review-prompt.txt; cat /tmp/impl.diff; } > /tmp/review-full.txt

# 3. Spawn. The flags matter (see Gotchas).
env -u CLAUDECODE claude -p "$(cat /tmp/review-full.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 1 \
  --no-session-persistence \
  > /tmp/review-result.txt 2>/dev/null < /dev/null
```

Returns well under a minute for a ~1k-line diff; `run_in_background: true` when large. Prompt template: `../examples/mode1-diff-prompt.txt` - fill `<change>`, context, focus bullets; append the diff inline.

## Mode 2 fallback - when the process boundary matters

```bash
# Write the audit prompt to a file first, then:
cd <repo-root>
env -u CLAUDECODE claude -p "$(cat /tmp/audit-prompt.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 50 \
  --no-session-persistence \
  > /tmp/audit-result.txt 2>/dev/null < /dev/null &
```

Prompt template: `../examples/mode2-audit-prompt.txt` - reviewer role + REPO/scope + CONTEXT + audited REQUIREMENTS + smell classes + strict VERDICT line.

## Gotchas

- **`env -u CLAUDECODE` mandatory** - with `CLAUDECODE` set the SDK enters degraded mode, hangs on file ops. Strip for every subprocess (same rule as the `acp` skill)
- **`< /dev/null` on every spawn** - without it the subprocess waits on stdin; result file holds only `Warning: no stdin data received...`, a silently empty review
- **Mode 1: forbid tools at the very top of the prompt** ("Do NOT use any tools... the COMPLETE diff is inline") - else the reviewer burns turns trying to `Read` referenced files, dies at `Error: Reached max turns` with EMPTY output. **Mode 2 is the opposite - it MUST use tools**; never paste the forbid-tools line into a Mode 2 prompt
- **Match `--max-turns` to the mode** - Mode 1 = 1; Mode 2 = ~50. Low cap in Mode 2 stops mid-investigation, no verdict
- **Mode 1: diff INLINE, never paths** - paths force tool use and leak repo layout instead of logic. Mode 2: no diff - it reads the tree; scope by instruction
- **Scope tightly** - Mode 1: 200-800 focused implementation lines get a sharp review, a 5k-line dump gets a vague one. Mode 2: name in/out-of-scope dirs so it skips vendored and generated code
- **`--no-session-persistence`** - else each one-shot call litters `~/.claude/projects/<slug>/` with an unresumable JSONL
- **`2>/dev/null`** - suppresses the harmless "no stdin data received" stderr that pollutes the result file
- **Soft-land a usage-policy refusal** - the model occasionally flags benign technical prose ("kill", "inject", "attack surface"). `grep -q "violate our Usage Policy" <result>` → retry once with `--model claude-sonnet-4-20250514`; still refused → surface to the user. One retry only

## Seed an adversary into a `claude -p` prompt

Prompt = mode mechanics + adversary body + target/scope. Adversary supplies WHO, WHAT-TO-HUNT, output shape; mode supplies tools-on/off, inline-diff-vs-repo, scope, `--max-turns`. Strip the YAML frontmatter (`body() { awk 'c>=2; /^---$/{c++}' "$1"; }`), paste the body in place of the mode prompt's generic role line. Runnable both-modes template: `../examples/seed-adversary.sh`.
