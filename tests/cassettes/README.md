# claude -p cassettes

Real recorded `claude -p` responses for the test suite. CI replays these without ever needing the `claude` binary.

## Layout

```
tests/cassettes/
└── claude_p/
    └── <hash>.json   # SHA-256(prompt)[:12] as the filename
```

Each cassette ships `stdout`, `stderr`, `returncode`, the prompt preview, and the exact subprocess args used at record time. Replay matches on the prompt hash only - args are stored for debugging.

## How replay works

1. A test renders the same prompt the production code would render (via `render_standardize_prompt`, hand-crafted PASS/FAIL question, etc.).
2. The test installs `tests/_claude_cassette.py::ClaudePCassette` over `module.subprocess.run` (or uses the `claude_p_cassette` fixture from `conftest.py`).
3. The cassette layer hashes the prompt, finds `<hash>.json`, returns a `SimpleNamespace` shaped like `subprocess.CompletedProcess`.
4. The production code parses the response unchanged - same path as a real spawn.

## How to (re-)record

```bash
uv run python tests/record_claude_cassettes.py
```

Requires the `claude` binary on PATH. The script overwrites existing cassettes - that's intentional, since cassettes are tied to specific prompt text. If you change a prompt template, you must re-record any cassette derived from it (the hash will change anyway, so the test will start asking for a new file).

To add a scenario: add a `record_<scenario>` function in `tests/record_claude_cassettes.py`, call it from `main()`, run the script once, commit the new JSON.

## When replay fails

If a test raises `RuntimeError: claude -p cassette missing for prompt hash <hash>`, the prompt has changed (or the test is brand-new) and there is no cassette for it yet. Re-record locally, commit the new file, push.

`pytest --record-cassettes` is also wired into `conftest.py` for tests that use the `claude_p_cassette` fixture - on a miss, the fixture will shell out to the real `claude` binary and persist the response.

## Hash collisions

SHA-256 truncated to 12 hex chars gives 48 bits of entropy. Collision risk is negligible for the handful of cassettes the suite needs. If you ever see two cassettes claim the same hash, treat it as a bug in this layer, not as legitimate file traffic.
