#!/usr/bin/env bash
# Seed an adversary persona into a review spawn.
#
# Prompt = mode mechanics + adversary body + target/scope.
#   - the ADVERSARY supplies WHO, WHAT-TO-HUNT, and the output shape
#   - the MODE supplies tools-on/off, inline-diff-vs-repo, scope, and --max-turns
# Strip the adversary's YAML frontmatter; paste the body in place of the mode
# prompt's generic "You are a hostile senior reviewer" role line.

ADV=~/.claude/skills/adversarial-review/adversaries/architect.md
body() { awk 'c>=2; /^---$/{c++}' "$1"; }   # everything below the frontmatter

# --- Mode 2 (tools ON, whole-repo) ---------------------------------------
{
  echo "Use ripgrep and read files directly to investigate the LIVE tree - do not guess. Do not modify anything."
  echo "REPO: $(pwd)"
  echo "IN SCOPE: <dirs/files>   OUT OF SCOPE: tests/, generated/, vendored/"
  echo "CONTEXT: <2-5 sentences - the change/feature, its architecture, the rules it must hold>"
  body "$ADV"
} > /tmp/audit-prompt.txt

cd <repo-root>
env -u CLAUDECODE claude -p "$(cat /tmp/audit-prompt.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 50 \
  --no-session-persistence \
  > /tmp/audit-result.txt 2>/dev/null < /dev/null &

# --- Mode 1 (no tools, inline diff) --------------------------------------
# Capture ONLY the implementation diff - exclude docs, lockfiles, golden
# snapshots, generated files; they bloat the prompt and distract the reviewer.
git diff -- path/to/src/a.py path/to/src/b.tsx > /tmp/impl.diff

{
  echo "IMPORTANT: Do NOT use any tools. Do NOT read files. The COMPLETE unified diff is inline below - analyze ONLY what is shown."
  body "$ADV"
  echo; echo "Here is the unified diff:"; echo
  cat /tmp/impl.diff
} > /tmp/review-full.txt

env -u CLAUDECODE claude -p "$(cat /tmp/review-full.txt)" \
  --output-format text \
  --dangerously-skip-permissions \
  --max-turns 1 \
  --no-session-persistence \
  > /tmp/review-result.txt 2>/dev/null < /dev/null
