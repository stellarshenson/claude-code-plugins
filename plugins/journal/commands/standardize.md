---
description: Standardize oversized / mis-marked journal entries via the ACP repair loop. For each offender, the shipped prompt YAML drives a focused `claude -p` subprocess that decides Extended vs Condense vs Drop-marker; the CLI applies the verdict. Triggers - "standardize journal", "fix journal entry tiers", "repair journal".
allowed-tools: [Read, Write, Edit, Bash, Glob]
argument-hint: "(optional) <journal-path>  -- default .claude/JOURNAL.md"
---

# Standardize Journal Entries

The `journal-tools check` validator flags three failure modes:

- **Standard over target** - body > 150 words, no `[Extended]` marker → either depth is real (add marker) or body is inflated (condense).
- **Extended over max** - body > 400 words even with `[Extended]` marker → condense, marker can stay. (Alternative when the depth is worth preserving: `/journal:article N` extracts the body into `docs/<slug>.md` and slims the entry to a summary + link.)
- **Spurious marker** - `[Extended]` present but body < 150 words → marker is false advertising → drop it.

This command repairs all three via the ACP companion-process pattern: a shipped prompt YAML at `src/stellars_claude_code_plugins/journal/prompts/standardize.yaml` defines the per-entry rubric, the CLI renders it for one entry at a time, a fresh `claude -p` subprocess returns a structured decision, the CLI applies it. Run after a `journal-tools check` reports warnings; never inline-edit oversized entries by hand.

## Pre-flight install (MANDATORY, no asking)

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

The upgrade always runs - a stale-but-importable install is exactly the failure this gate prevents, and the reinstall also repairs a stale shim on PATH whose package is uninstalled in the active Python. Never skip.

## Procedure

Default journal path is `.claude/JOURNAL.md` unless an argument is passed.

### Happy path — one CLI call

```bash
journal-tools standardize .claude/JOURNAL.md --all
```

`--all` walks every flagged entry in order:

- `drop_marker` candidates apply immediately (no subprocess).
- `decide` / `condense` candidates spawn one focused `claude -p` subprocess each, with the CLAUDECODE env var stripped, stderr suppressed, the `--no-session-persistence` flag set (so the subprocess does NOT leave a JSONL file under `~/.claude/projects/<slug>/` per entry), and a sonnet-4 retry on usage-policy refusal.
- Each decision is parsed via the YAML grammar and applied through the existing `--apply` write path.
- Unparseable / refused / timed-out subprocess responses skip the entry with a `SKIP ...` log line and continue; nothing crashes mid-sweep.
- After the loop, `check_journal` runs once. On a fully clean validator exit (zero errors AND zero warnings) the CLI writes a `<!-- standardize-clean: YYYY-MM-DD -->` comment near the journal top for forensics. Any remaining warnings or errors are surfaced for follow-up.

This is the only command you need for 99% of runs. Everything below is the manual procedure for debugging individual entries — useful when `--all` skipped an entry and you want to inspect the subprocess prompt or step through one decision at a time interactively.

## Debugging one entry

The manual `--list` / `--prompt N` / `--apply N` walk, for when `--all` logged a `SKIP` and you want to see the prompt or step through one decision: `skills/journal/references/standardize-manual.md`.

## Rules

- ALL subprocess calls MUST use `env -u CLAUDECODE` (or set `env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"}` in Python). Without this the SDK hangs on file ops. Reference: `acp` skill, "Critical: Strip CLAUDECODE Env Var".
- Soft landing on usage-policy refusal. Default model occasionally flags benign technical bodies (long file-path lists, words like FAIL / kill / inject as plain prose). Retry once with `--model claude-sonnet-4-20250514` before surfacing the entry to the user. Trigger: `grep -q "violate our Usage Policy"` on the decision file. One retry only - if Sonnet 4 also refuses, report the entry and skip; do not chain further model swaps. `--all` already enforces this contract in code.
- One subprocess per entry per `--all` run. If a subprocess produced a non-compliant body (e.g. condensed but still >150 without marker), do NOT manually retry inside the same session — re-run `journal-tools standardize --all` and the candidate either re-fires or settles. The rubric is deterministic enough that two manual retries chasing the same entry usually means the body needs human review, not another model spin.
- Subprocess calls MUST add `--no-session-persistence`. The standardize decisions are one-shot and never resumed; persisting their session JSONL files accumulates one extra file per entry under `~/.claude/projects/<slug>/`. `--all` adds the flag automatically; the manual procedure block below also carries it.
- ONE subprocess per entry. Do not bundle multiple entries into a single `claude -p` prompt - it defeats the focused-decision principle and lets the subprocess drift across boundaries.
- Subprocess `--max-turns 3` cap. The task is a single decision; more turns means the subprocess is wandering.
- Never edit `JOURNAL.md` directly during standardize - only via `journal-tools standardize --apply`. The CLI handles the structural rewrite (preserving indentation, joining body onto a single Result line, dropping the marker when condense pushes back into Standard).
- Numbering is preserved. The standardize flow never touches entry numbers; if you need renumbering, that is `journal-tools sort`, run BEFORE standardize.
- The shipped `prompts/standardize.yaml` is the single source of truth for the decision rubric. Bump the YAML's `version:` field on breaking changes and the CLI refuses unknown versions - no silent prompt drift between wheel + slash command versions.
