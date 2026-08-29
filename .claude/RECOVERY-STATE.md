# Recovery State

Written by `/brace`. The newest BRACE section is the one to act on. Read it before anything else after a restart.

## BRACE 2026-08-29T14:00Z

### HORIZON

**SERVER RESTART** (assumed - the Star Colonel did not state one, so the stricter reading was taken). Nothing was detached and nothing needs reattaching: this session ran no experiments, no training, no servers. Everything of value is on disk in the working tree. If it was in fact SESSION-ONLY, nothing changes - there was no surviving compute either way.

### FIRST ACTION

`cd /home/lab/workspace/private/ai-assistants/claude-code-plugins && git log --oneline -1 && git status --short && uv run pytest -q | tail -1`

Expect commit `b98429d` (v1.7.9) plus roughly 30 modified/untracked files, suite 1058 passed + 1 skipped. Then relaunch the two stopped workflows below. Nothing is broken; the work is uncommitted, not lost.

### Stopped workflows - relaunch these

Both were halted by the brace, not by failure. A workflow is session-bound: `resumeFromRunId` works **only inside the session that created it**, so after a restart the agent cache is gone and each relaunches from its script path plus its args, verbatim.

**Before relaunching either, read its `journal.jsonl`** - one JSON line per completed agent, each carrying that agent's full return value. Those results are already paid for; feeding them into the relaunch instead of re-running the phase is the difference between minutes and a million tokens.

| Run | Purpose | Phase reached | Salvage |
| --- | --- | --- | --- |
| `wf_c71f1553-f5d` | ACC-REVIEW-74 - the agentic-engineering canon | wrote the file, in Verify (8 agents started, 7 returned) | `references/agentic-engineering-canon.md` is written, 206 lines, ~115 links. UNVERIFIED - the link audit and the usefulness audit had not returned |
| `wf_386e1a9d-fb8` | ACC-REVIEW-75/76 - graphify knowledge refresh | Research (3 started, 1 returned) | nothing written yet - `references/code-graph-instrument.md` does not exist and `~/.claude/skills/graphify/SKILL.md` is untouched (mtime Jul 31) |

Script paths (persisted, survive a restart):

- `/home/lab/.claude/projects/-home-lab-workspace-private-ai-assistants-claude-code-plugins/3301e203-050c-47c3-8443-9d0a2d7fd5e4/workflows/scripts/agentic-engineering-canon-wf_c71f1553-f5d.js`
- `/home/lab/.claude/projects/-home-lab-workspace-private-ai-assistants-claude-code-plugins/3301e203-050c-47c3-8443-9d0a2d7fd5e4/workflows/scripts/graphify-knowledge-refresh-wf_386e1a9d-fb8.js`

Args, verbatim (NOT stored with the script - a relaunch without them is dead):

- canon: `{"repo": "/home/lab/workspace/private/ai-assistants/claude-code-plugins"}`
- graphify: `{"repo": "/home/lab/workspace/private/ai-assistants/claude-code-plugins", "version": "0.8.18", "today": "2026-08-29"}`

Transcript dirs (the journals live here):

- `/home/lab/.claude/projects/-home-lab-workspace-private-ai-assistants-claude-code-plugins/3301e203-050c-47c3-8443-9d0a2d7fd5e4/subagents/workflows/wf_c71f1553-f5d/journal.jsonl`
- `.../subagents/workflows/wf_386e1a9d-fb8/journal.jsonl`

The graphify run re-reads the CLI surface itself; `graphify --version` was 0.8.18 at brace time - check it again rather than trusting that number.

### Tree difference the stops produced

None. `git status --porcelain` was byte-identical before and after both `TaskStop` calls (29 lines each time), so no workflow was mid-write. Everything uncommitted is intended work.

### Valid on disk - uncommitted, all gated green

Suite **1058 passed + 1 skipped**, `ruff check .` clean, `pm-tools check docs` 0 errors, `journal-tools check` OK, at brace time. HEAD is `b98429d` (v1.7.9, shipped to PyPI and the marketplace).

- **devils-advocate loop restructure** (ACC-REVIEW-61/62/63, closed): invariants stated once in `references/loop-spec.md` with pointers elsewhere; adjudicator and reviewer method in `agents/*.md` with the workflow script passing data only; `SKILL.md` 3793 → 2196 words with `references/manual-rounds.md` and `references/remedy-discipline.md` split out
- **Instrument-as-data paradigm** (ACC-REVIEW-72, closed): no pinned tool command surface anywhere in the plugin; `test_instrument_threaded_as_data_never_prescribed` fails if one returns
- **pm-tools soft lock** (ACC-PMLOCK-64..71, all closed): `lock` / `unlock`, the `- lock:` line, warn-never-refuse, auto-expiry, pick-up notice, TRANSFER call-out, `--locked` / `--locked-by`, the `lock` field and the `Worked on` count, plus docs in eight plugin files
- **`adversaries/ai-engineer.md`** (ACC-REVIEW-73, open): 110 lines, 13 axes, repaired against its verifier's five substantive findings; wired into `SKILL.md`, `README.md` and `commands/adversarial-review.md`
- **`references/agentic-engineering-canon.md`** (ACC-REVIEW-74, open): written, unverified - see the stopped run above
- **`CHANGELOG.md`**: new file, seeded with 1.7.7 / 1.7.8 / 1.7.9 and an Unreleased section

### Outside the project tree

`~/.claude/commands/brace.md` and `~/.claude/commands/brace-resume.md` were edited this session (workflow halt step; `/brace resume` dispatch). They are in the home dotfiles repo, not this one - commit them there separately.

### Pending recordings and decisions

1. Journal entries for today's post-release work - none written since entry 344 (v1.7.9). Use `/journal:update`, never an inline edit
2. `CHANGELOG.md` Unreleased section describes work in flight - reconcile it to what actually landed
3. ACC-REVIEW-73 and 74 stay open until the canon is verified and the adversary is exercised on a real target
4. `ACC-REVIEW-61/62/63` carry log lines saying they were closed prematurely on my own spot-check, then repaired after a relaunched verifier found a vacuous guardrail. A fresh verifier for them was planned and never launched
5. Known gap, logged not fixed: the adversarial-review `SKILL.md` description is 1314 chars against the authoring contract's 1024 cap (pre-existing at 1224)
6. **Release v1.7.10 is NOT approved.** Roughly 30 files are uncommitted. Commit, push and release each need the Star Colonel's explicit word, per instance

### Standing rules this session established

- A workflow agent that dies (credit exhaustion, API error) is **relaunched**, never counted as passed; my own spot-check is interim evidence, never the verdict
- Instruments are passed to agents as data - what exists, where. Never a command: a written invocation pins an API that moves
