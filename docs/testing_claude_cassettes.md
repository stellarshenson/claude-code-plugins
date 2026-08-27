# Testing code that spawns `claude -p`

CI cannot run the `claude` binary. Tests that exercise subprocess spawn paths (the standardize ACP loop, the autobuild gatekeeper/readback gates, the devils-advocate standalone scorer, the toolchain-gate comprehension pair) need to replay real recorded responses instead of either hand-crafted synthetic strings or live binary calls. This doc captures how that layer is built, when to re-record, and where to read the contracts.

## The cassette layer in three pieces

- **`tests/_claude_cassette.py`** — the `ClaudePCassette` callable. Drop-in replacement for `subprocess.run`. Extracts the prompt from the args (the value following `-p`/`--print`), hashes it with SHA-256 (12-char prefix), looks up `tests/cassettes/claude_p/<hash>.json`, returns a `SimpleNamespace` shaped like `subprocess.CompletedProcess`. Default mode is REPLAY: missing cassettes raise `RuntimeError`, tests fail loudly.
- **`tests/conftest.py`** — registers the `--record-cassettes` pytest CLI flag and exposes the `claude_p_cassette` fixture. The fixture returns a `ClaudePCassette` instance pre-configured for the current mode.
- **`tests/record_claude_cassettes.py`** — the manual-invocation recording script. NOT a pytest test (filename intentionally lacks the `test_` prefix). Run with `uv run python tests/record_claude_cassettes.py` when you need to record or re-record. Requires the `claude` binary on PATH.

Cassettes live in `tests/cassettes/claude_p/<hash>.json` and ship with the repo. Each cassette records `stdout`, `stderr`, `returncode`, a 200-char prompt preview, and the exact subprocess args used at record time. Replay matches on the prompt hash only; the args are debug detail.

## When to use a cassette vs a synthetic mock

Synthetic mocks (the `monkeypatch.setattr(module.subprocess, "run", lambda args, **kw: SimpleNamespace(stdout="DECISION: EXTENDED\n", ...))` pattern) are correct for **structural** tests — verifying that the spawn args include `--no-session-persistence`, that a refusal triggers the sonnet-4 retry, that a timeout returns `None`. These tests don't need realism; they need to nail down the control flow.

Cassettes are correct for **realism** tests — verifying that the parser actually handles real claude output. Format drift in the binary (stderr leaks, JSON envelope changes, model-swap retry text, the literal "API Error: ... violate our Usage Policy" string the soft-landing code grep-matches on) would silently break a synthetic-mock test because the mock is hand-crafted. A cassette would expose the drift the first time it lands.

The current realism tests are in `tests/test_claude_cassette_realism.py`. They render the same prompts the production code would render (via `render_standardize_prompt`, hand-crafted PASS/FAIL question, etc.), install the cassette layer, and assert on the parsed output.

## Re-recording

```bash
uv run python tests/record_claude_cassettes.py
```

This overwrites existing cassettes. The script is idempotent on prompt content — if a prompt has not changed, the new cassette will land under the same hash and replace the old file with a fresh response. If a prompt HAS changed, the new cassette lands under a new hash and the old file becomes orphaned (delete it by hand or run `rm tests/cassettes/claude_p/*.json` before re-recording).

Adding a new scenario:

1. Append a `record_<scenario>` function to `tests/record_claude_cassettes.py` that builds the prompt and calls `spawn(prompt, model=...)`.
2. Add the call to `main()` so the next recording run picks it up.
3. Run the script once.
4. Add a corresponding test in `tests/test_claude_cassette_realism.py` that asserts against the recorded response.
5. Commit the new JSON file alongside the test.

## Model choice at record time

The standardize prompts trigger the default-model usage-policy refusal (`"violate our Usage Policy"`) on benign technical content — this is exactly the soft-landing case the slash command + CLI handle in production. For RECORDING, pass `model="claude-sonnet-4-20250514"` to `spawn()` so the cassette captures a parseable response. The retry logic itself is tested via synthetic mocks in `test_journal_tools.py::TestSpawnSubprocessSoftLanding`, which mocks the refusal text directly without needing a recorded refusal cassette.

The orchestrator's `_claude_evaluate` PASS/FAIL prompts do not hit the refusal — record those with default model.

## Why cassettes are content-addressed

A test renders a prompt, hashes it, looks up the cassette. If a prompt template changes (a typo fix, a rubric clarification, a new placeholder), the hash changes, the lookup misses, the test fails loudly with `cassette missing for prompt hash <new_hash>`. This forces a deliberate re-record instead of silently letting a stale response paper over a real change.

**Freeze the quoted artefact in `_cassette_prompts.py`; guard it with a static test that reads the live file.** A frozen prompt plus a recorded reply is `constant == constant` and would pass even if the artefact were gutted - so the pairing is mandatory, not the freezing optional. Reading the artefact live instead looks stronger but couples the cassette hash to prose: rewording one bullet misses the cassette and fails CI, which has no `claude` binary to re-record with. The toolchain-gate pair uses the frozen `GATE_FENCE` / `GATE_BULLETS`, while `test_shipped_gate_still_carries_its_normative_lines` reads `plugins/svg-infographics/skills/svg-designer/SKILL.md` and asserts the shipped commands and rules still match the snapshot. Changing either fails loudly and names the re-record command; tidying the prose around them is free.

The cassette filename is the entire identity. There is no test-name → cassette mapping, no separate registry, no human-friendly aliasing. If you want to find which test consumes which cassette, grep the prompt preview in the JSON files.

## When a test raises `cassette missing for prompt hash <hash>`

Either the prompt is new (add a record function in the recording script and run it) or the prompt drifted from what was originally recorded (intentional: re-record; unintentional: revert the prompt to the version that matches the cassette).

`pytest --record-cassettes` is the inline form — on a miss, the fixture will shell out to the real `claude` binary and persist the response. Use this when you're iterating on tests locally and don't want to leave the test runner.

## Hash collisions

SHA-256 truncated to 12 hex chars gives 48 bits of entropy. The suite has on the order of 10 cassettes; collision risk is negligible. If two cassettes claim the same hash, treat it as a bug in `tests/_claude_cassette.py` rather than expected behaviour.
