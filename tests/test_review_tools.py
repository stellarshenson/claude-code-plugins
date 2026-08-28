"""review-tools: the dossier, the cost profile and the findings merge.

Each fixture is the smallest input that exercises a decision the tool makes:
a loop-built subcommand only `--help` can see, a script name in prose that is
not a command, a transcript whose thinking and tool_use share one message id,
two lenses citing the same file twenty lines apart.
"""

from __future__ import annotations

import json
from pathlib import Path
import textwrap

import pytest

from stellars_claude_code_plugins.review.review_tools import (
    build_dossier,
    cost_of,
    main,
    merge_findings,
    parse_report,
    render_dossier,
)

# --- dossier fixtures ------------------------------------------------------


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text(
        textwrap.dedent(
            '''
            """Module docstring is not a literal."""
            import argparse
            import subprocess
            import sys

            TOKEN = "shared-token"
            LIMIT = 800


            class Runner:
                def go(self):
                    return 1

                def stop(self):
                    return 2


            def main(argv=None):
                p = argparse.ArgumentParser(prog="mytool")
                sub = p.add_subparsers(dest="cmd", required=True)
                r = sub.add_parser("run")
                r.add_argument("--force", action="store_true")
                r.add_argument("--n", default=3, help="not a literal either")
                for name in ("fly",):
                    sub.add_parser(name)
                p.parse_args(argv)
                try:
                    subprocess.run(["true"])
                except Exception:
                    pass
                with open("out.txt", "w") as fh:
                    fh.write(TOKEN)
                return 0


            if __name__ == "__main__":
                sys.exit(main())
            '''
        )
    )
    (pkg / "b.py").write_text(
        'LIMIT = 800\nOTHER = "shared-token"\n\n\ndef helper():\n    return 42\n'
    )
    docs = tmp_path / "plugins"
    docs.mkdir()
    (docs / "skill.md").write_text(
        "Run `mytool run --force` then `mytool soar`. The mytool console prints a table.\n\n"
        "```bash\npython -m pkg.a run\n```\n"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "0"\n\n[project.scripts]\nmytool = "pkg.a:main"\n'
    )
    (tmp_path / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "a_main",
                        "label": "main()",
                        "source_file": "pkg/a.py",
                        "source_location": "L16",
                    },
                    {
                        "id": "b_helper",
                        "label": "helper()",
                        "source_file": "pkg/b.py",
                        "source_location": "L5",
                    },
                ],
                "links": [
                    {
                        "relation": "calls",
                        "source": "a_main",
                        "target": "b_helper",
                        "source_file": "pkg/a.py",
                        "source_location": "L20",
                    },
                    {"relation": "contains", "source": "a_main", "target": "b_helper"},
                ],
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def dossier(root: Path, **kw) -> dict:
    return build_dossier(
        [root / "pkg"], root, root / "pyproject.toml", root / "plugins", root / "graph.json", **kw
    )


# --- dossier ---------------------------------------------------------------


def test_inventory_and_compact_symbol_index(tree: Path):
    d = dossier(tree, run_help=False)
    assert [r["file"] for r in d["inventory"]] == ["pkg/__init__.py", "pkg/a.py", "pkg/b.py"]
    assert "Runner:L11{go:L12,stop:L15}" in d["symbols"]["pkg/a.py"]
    assert "main:L19" in d["symbols"]["pkg/a.py"]


def test_cli_surface_reads_flags_and_help_finds_the_loop_built_subcommand(tree: Path):
    ast_only = dossier(tree, run_help=False)
    run = ast_only["surface"]["pkg/a.py"]["run"]
    assert [names for names, _, _ in run] == ["--force", "--n"]
    assert run[0][1] == {"action": "'store_true'"}
    assert run[1][1] == {"default": "3"}
    check = ast_only["surface_check"][0]
    assert check["source"] == "ast" and check["defined"] == ["run"]

    live = dossier(tree)["surface_check"][0]
    assert live["source"] == "--help"
    assert live["defined"] == ["fly", "run"]


def test_advertised_surface_counts_code_spans_not_prose(tree: Path):
    check = dossier(tree)["surface_check"][0]
    assert check["advertised_undefined"] == ["soar"]  # in a code span, no parser
    assert "console" not in check["advertised_undefined"]  # prose after the script name
    assert check["defined_unadvertised"] == ["fly"]
    assert dossier(tree, run_help=False)["module_refs"] == {"pkg.a": 1}


def test_risky_primitives_and_literals_shared_across_modules(tree: Path):
    d = dossier(tree, run_help=False)
    hits = d["risky"]["pkg/a.py"]
    assert [ln for ln, _ in hits["subprocess"]] == [29]  # the call, not the import
    assert [ln for ln, _ in hits["broad-except"]] == [30]
    assert [ln for ln, _ in hits["write"]] == [32]
    assert [ln for ln, _ in hits["exit"]] == [38]
    shared = {v: fs for v, fs in d["shared_literals"]}
    assert set(shared) == {"shared-token", 800}
    assert shared["shared-token"] == {"pkg/a.py": [7], "pkg/b.py": [2]}


def test_graph_callers_come_from_calls_edges_only(tree: Path):
    d = dossier(tree, run_help=False)
    assert d["callers"] == [("helper()", "pkg/b.py:L5", ["main() (pkg/a.py:L20)"])]
    missing = build_dossier([tree / "pkg"], tree, None, None, tree / "nope.json", run_help=False)
    assert missing["callers"] == [] and "not found" in missing["graph_note"]


def test_dossier_renders_every_section_and_writes_out(tree: Path, capsys: pytest.CaptureFixture):
    text = render_dossier(dossier(tree, run_help=False))
    for head in (
        "## Inventory",
        "## Symbols",
        "## CLI surface",
        "## Advertised surface vs parser",
        "## Risky primitives",
        "## Literals shared",
        "## Most-called symbols",
    ):
        assert head in text
    out = tree / "dossier.md"
    assert (
        main(
            [
                "dossier",
                "pkg",
                "--plugins",
                "plugins",
                "--graph",
                "graph.json",
                "--no-help",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert "3 files" in capsys.readouterr().out
    assert out.read_text().startswith("# Review dossier")
    assert main(["dossier", "pkg", "--no-help", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["inventory"][1]["symbols"] == 2


# --- cost ------------------------------------------------------------------


def _event(
    role: str,
    content: list,
    mid: str | None = None,
    usage: dict | None = None,
    ts: str = "2026-08-28T08:00:00Z",
) -> str:
    msg = {"role": role, "content": content}
    if mid:
        msg["id"] = mid
    if usage:
        msg["usage"] = usage
    return json.dumps({"timestamp": ts, "message": msg})


def test_cost_deduplicates_turns_by_message_id(tmp_path: Path):
    usage1 = {
        "input_tokens": 10,
        "cache_read_input_tokens": 1000,
        "cache_creation_input_tokens": 100,
        "output_tokens": 50,
    }
    usage2 = {
        "input_tokens": 10,
        "cache_read_input_tokens": 2000,
        "cache_creation_input_tokens": 100,
        "output_tokens": 500,
    }
    lines = [
        _event(
            "assistant",
            [{"type": "thinking", "thinking": "..."}],
            "m1",
            usage1,
            "2026-08-28T08:00:00Z",
        ),
        _event(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "Bash",
                    "input": {"command": "cd /repo && grep -n foo a.py"},
                },
                {
                    "type": "tool_use",
                    "id": "t2",
                    "name": "Read",
                    "input": {"file_path": "/repo/a.py"},
                },
            ],
            "m1",
            usage1,
            "2026-08-28T08:00:05Z",
        ),
        _event(
            "user",
            [
                {"type": "tool_result", "tool_use_id": "t1", "content": "a.py:1:foo"},
                {
                    "type": "tool_result",
                    "tool_use_id": "t2",
                    "content": [{"type": "text", "text": "x" * 500}],
                },
            ],
        ),
        _event(
            "assistant",
            [
                {
                    "type": "tool_use",
                    "id": "t3",
                    "name": "Read",
                    "input": {"file_path": "/repo/a.py"},
                }
            ],
            "m2",
            usage2,
            "2026-08-28T08:01:00Z",
        ),
        _event("user", [{"type": "tool_result", "tool_use_id": "t3", "content": "x" * 500}]),
        _event(
            "assistant",
            [{"type": "text", "text": "VERDICT: SHIP"}],
            "m3",
            usage2,
            "2026-08-28T08:02:00Z",
        ),
    ]
    path = tmp_path / "agent-x.jsonl"
    path.write_text("\n".join(lines) + "\n")
    r = cost_of(path)
    assert r["events"] == 4 and r["turns"] == 3
    assert r["cache_read"] == 1000 + 2000 + 2000  # m1 counted once, not per event
    assert r["output_tokens"] == 50 + 500 + 500
    assert r["tool_calls"] == {"Read": 2, "Bash": 1}
    assert r["tool_turns"] == 2 and r["multi_tool_turns"] == 1
    assert r["rereads"] == 1 and r["distinct_targets"] == 1
    assert r["tiny_results"] == 1
    assert r["bash_verbs"] == {"grep": 1}
    assert r["wall_min"] == 2.0
    assert r["context_max"] == 2110


def test_cost_cli_renders_a_table(tmp_path: Path, capsys: pytest.CaptureFixture):
    path = tmp_path / "t.jsonl"
    path.write_text(
        _event(
            "assistant", [{"type": "text", "text": "done"}], "m1", {"cache_read_input_tokens": 5}
        )
        + "\n"
    )
    assert main(["cost", str(path)]) == 0
    out = capsys.readouterr().out
    assert "| `t.jsonl` | 1 |" in out and "Cache read is the bill" in out


# --- findings --------------------------------------------------------------

ARCHITECT = """VERDICT: DO-NOT-SHIP (2 findings) - one break.

## Inconsistencies / defects

- **[CRITICAL] Resources archived on every run** - `src/pkg/orchestrator.py:3610-3616` byte-compares
  and `:3636` renames. REMEDY: delete the loop.
- **[MINOR (taste)] Two table renderers** - `pm_tools.py:657` and hand-rolled tables. REMEDY: leave.
"""

BUG_HUNTER = """VERDICT: SHIP (2 findings) - nothing blocks.

- [MAJOR] orchestrator.py:3596 - `_detect_stale_resources` reverts any edit; see `app.yaml:326`. REMEDY: record a hash.
- [MINOR] `render_png.py:25` misreads `viewBox="0,0,8,6"`.
"""


def test_parse_report_reads_both_bullet_shapes():
    rep = parse_report(ARCHITECT, "architect")
    assert rep["verdict"] == {"verdict": "DO-NOT-SHIP", "count": 2}
    first, second = rep["findings"]
    assert first["severity"] == "CRITICAL" and first["title"] == "Resources archived on every run"
    assert (first["file"], first["line"]) == ("src/pkg/orchestrator.py", 3610)
    assert "renames" in first["text"]  # continuation line kept
    assert second["taste"] is True and second["severity"] == "MINOR"
    plain = parse_report(BUG_HUNTER, "bug-hunter")["findings"][0]
    assert plain["title"].startswith("orchestrator.py:3596")
    assert (plain["file"], plain["line"]) == ("orchestrator.py", 3596)


def test_merge_joins_lenses_on_the_same_file_within_a_few_lines():
    rows = merge_findings(
        [parse_report(ARCHITECT, "architect"), parse_report(BUG_HUNTER, "bug-hunter")]
    )
    assert len(rows) == 3
    top = rows[0]
    assert top["severity"] == "CRITICAL" and top["lenses"] == ["architect", "bug-hunter"]
    assert len(top["texts"]) == 2
    assert [r["severity"] for r in rows] == ["CRITICAL", "MINOR", "MINOR"]
    assert rows[1]["taste"] is False and rows[2]["taste"] is True  # taste sorts last within a tier


def test_findings_cli_table_and_full_text(tmp_path: Path, capsys: pytest.CaptureFixture):
    (tmp_path / "architect.md").write_text(ARCHITECT)
    (tmp_path / "bug-hunter.md").write_text(BUG_HUNTER)
    assert main(["findings", str(tmp_path / "architect.md"), str(tmp_path / "bug-hunter.md")]) == 0
    out = capsys.readouterr().out
    assert "| architect | DO-NOT-SHIP | 2 | 2 | 1 | 0 | 1 |" in out
    assert "## Findings (3 after merge)" in out
    assert "| architect, bug-hunter |" in out
    assert "REMEDY: record a hash" not in out
    assert (
        main(
            ["findings", str(tmp_path / "architect.md"), str(tmp_path / "bug-hunter.md"), "--full"]
        )
        == 0
    )
    assert "REMEDY: record a hash" in capsys.readouterr().out
    assert main(["findings", str(tmp_path / "architect.md"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["reports"][0]["findings"] == 2 and data["findings"][0]["line"] == 3610
