"""review-tools: the dossier, the cost profile, the findings merge and the research search.

Each fixture is the smallest input that exercises a decision the tool makes:
a loop-built subcommand only `--help` can see, a script name in prose that is
not a command, a transcript whose thinking and tool_use share one message id,
two lenses citing the same file twenty lines apart.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import textwrap

import pytest

from stellars_claude_code_plugins.review.review_tools import (
    FINDING_FIELDS,
    build_dossier,
    cost_of,
    help_subcommands,
    main,
    merge_findings,
    parse_report,
    render_dossier,
    reviewer_prompt,
    verdict_inconsistencies,
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


def test_help_probe_reads_bare_and_quoted_choice_lists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """argparse quoted the choices on 3.11 and 3.13 and listed them bare on 3.12.13;
    the probe read only quoted names, so on 3.12 it returned an empty set and the
    `--help` fallback never ran. Both shapes must yield the subcommand names."""
    for shape in ("run, fly", "'run', 'fly'"):
        mod = tmp_path / "shaped.py"
        mod.write_text(
            "import sys\n"
            f"sys.stderr.write(\"mytool: error: argument cmd: invalid choice: '__probe__' (choose from {shape})\\n\")\n"
            "sys.exit(2)\n"
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))
        assert help_subcommands("shaped") == {"run", "fly"}, shape


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
    # bug-hunter says SHIP over a MAJOR - the coupling check makes the run exit 1
    assert main(["findings", str(tmp_path / "architect.md"), str(tmp_path / "bug-hunter.md")]) == 1
    out = capsys.readouterr().out
    assert "| architect | DO-NOT-SHIP | 2 | 2 | 1 | 0 | 1 |" in out
    assert "## Findings (3 after merge)" in out
    assert "| architect, bug-hunter |" in out
    assert "REMEDY: record a hash" not in out
    assert "## Verdict check" in out and "bug-hunter: VERDICT INCONSISTENT - SHIP with 1" in out
    assert (
        main(
            ["findings", str(tmp_path / "architect.md"), str(tmp_path / "bug-hunter.md"), "--full"]
        )
        == 1
    )
    assert "REMEDY: record a hash" in capsys.readouterr().out
    assert main(["findings", str(tmp_path / "architect.md"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["reports"][0]["findings"] == 2 and data["findings"][0]["line"] == 3610
    assert data["inconsistencies"] == []  # DO-NOT-SHIP over a CRITICAL is consistent


def test_parse_report_reads_numbered_bold_findings():
    numbered = (
        "## Verdict\n\n`VERDICT: DO-NOT-SHIP (2 findings)` - worst one.\n\n## Findings\n\n"
        "**1. [CRITICAL] A table wrapped in `<a href>` is silently deleted** - `src/turndown.ts:118`\n\n"
        "Reproduction paragraph.\n\n"
        "**2. [MINOR] `<thead>` after `<tbody>` swaps rows** - `src/turndown.ts:60`\n"
    )
    rep = parse_report(numbered, "bh")
    assert [f["severity"] for f in rep["findings"]] == ["CRITICAL", "MINOR"]
    assert rep["findings"][0]["file"] == "src/turndown.ts"
    assert verdict_inconsistencies([rep]) == []


def test_verdict_coupling_ship_needs_no_critical_and_no_major(
    tmp_path: Path, capsys: pytest.CaptureFixture
):
    inflated = "VERDICT: DO-NOT-SHIP (2 findings) - blocked.\n\n- [MAJOR] a.py:10 - real. REMEDY: x.\n- [MINOR] b.py:2 - nit.\n"
    assert verdict_inconsistencies([parse_report(inflated, "bh")]) == []  # MAJOR blocks now
    minors_only = "VERDICT: DO-NOT-SHIP (1 findings) - blocked.\n\n- [MINOR] a.py:10 - nit.\n"
    (msg,) = verdict_inconsistencies([parse_report(minors_only, "bh")])
    assert "DO-NOT-SHIP with no CRITICAL or MAJOR" in msg
    (tmp_path / "bh.md").write_text(minors_only)
    assert main(["findings", str(tmp_path / "bh.md"), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["inconsistencies"]


def test_research_search_ranks_the_answering_entry_and_skips_a_missing_cache(
    tmp_path: Path, capsys: pytest.CaptureFixture
):
    """The project cache does not exist until the first research lands, so a
    missing file is skipped; `tooltips` finds the `tooltip` entry and nothing
    that shares no word with the question."""
    plugin = tmp_path / "research.md"
    plugin.write_text(
        textwrap.dedent(
            """
            # ux-designer research

            ## Static text

            - [NN/g Tooltip Guidelines 2019](https://example.org/t): "Users shouldn't need to find a tooltip in order to complete their task." Tell: required step only in tooltip.
            - [NN/g Placeholders 2014](https://example.org/p): "Disappearing placeholder text strains users' short-term memory". Tell: placeholder as label.

            ## Reuse the design language

            - [Nielsen heuristic 4](https://example.org/h): "Follow platform and industry conventions." Tell: third button style.
            """
        ),
        encoding="utf-8",
    )
    cache = tmp_path / ".claude" / "review-research" / "ux-designer" / "research.md"
    assert (
        main(["research", "search", "tooltips on touch", str(plugin), str(cache), "--json"]) == 0
    )
    hits = json.loads(capsys.readouterr().out)
    assert [(h["line"], h["topic"]) for h in hits] == [(6, "Static text")]
    assert main(["research", "search", "quantum", str(plugin)]) == 0
    assert "no entry matches (3 entries searched)" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# prompt - the workflow script's reviewer prompt for a hand spawn (DEF-ADVR-68)
# ---------------------------------------------------------------------------

LOOP_SCRIPT = (
    Path(__file__).parent.parent
    / "plugins/devils-advocate/skills/adversarial-review/workflows/adversarial-loop.js"
)

REVIEW_ARGS = {
    "target": "the amend change",
    "scope": "pm_tools.py only",
    "bar": {
        "purpose": "p",
        "inputs": "i",
        "primaryPath": "pp",
        "outOfScope": "hand-edited files",
    },
    "lenses": ["bug-hunter", "architect"],
    "graph": "tmp/graphify-out/graph.json",
    "research": {"allowed": False},
}

CONFIRM_ARGS = {
    **REVIEW_ARGS,
    "state": {
        "contract": 2,
        "round": 1,
        "spiralStreak": 0,
        "history": [],
        "deferred": [],
        "refuted": [],
        "rulings": [],
        "closures": [
            {
                "round": 1,
                "site": "a.py:1",
                "summary": "s1",
                "files": ["a.py"],
                "patch": "/tmp/r1.patch",
            }
        ],
        "settled": [],
        "research": {"allowed": False},
    },
    "appliedFixes": [
        {"site": "b.py:2", "summary": "s2", "files": ["b.py"], "patch": "/tmp/r2.patch"}
    ],
}

PROMPT_DRIVER = r"""
const fs = require('fs')
const body = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const args = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'))
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const run = new AsyncFunction('args', 'budget', 'agent', 'parallel', 'pipeline', 'phase', 'log', 'workflow', body)
const prompts = []
const agent = async (prompt, opts) => { prompts.push({ label: opts.label, prompt }); throw new Error('captured') }
const parallel = (thunks) => Promise.all(thunks.map((thunk) => thunk()))
run(args, null, agent, parallel, null, () => {}, () => {}, null).then(
  () => console.log(JSON.stringify(prompts)),
  () => console.log(JSON.stringify(prompts))
)
"""


def _script_prompts(tmp_path: Path, args: dict) -> dict[str, str]:
    driver, scenario = tmp_path / "driver.js", tmp_path / "args.json"
    driver.write_text(PROMPT_DRIVER, encoding="utf-8")
    scenario.write_text(json.dumps(args), encoding="utf-8")
    r = subprocess.run(
        ["node", str(driver), str(LOOP_SCRIPT), str(scenario)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    return {p["label"]: p["prompt"] for p in json.loads(r.stdout)}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
@pytest.mark.parametrize("args, label", [(REVIEW_ARGS, "discover"), (CONFIRM_ARGS, "confirm")])
def test_prompt_equals_the_script_prompt_up_to_the_output_line(tmp_path: Path, args, label):
    """DEF-ADVR-68: the prompt text lives twice - in the script, which cannot
    read a file, and here. The two are held equal on every block but the
    last: the script's reviewer returns structured output, a hand spawn
    returns prose."""
    script = _script_prompts(tmp_path, args)
    for lens in args["lenses"]:
        expected = script[f"{label}:{lens}"].rsplit("\n\n", 1)[0]
        assert reviewer_prompt(args, lens).rsplit("\n\n", 1)[0] == expected


def test_prompt_blocks_are_verbatim_from_the_script_and_name_every_finding_field():
    """Node-free half of the parity check: each static sentence and the field
    list are in the script's source."""
    js = LOOP_SCRIPT.read_text(encoding="utf-8").replace("\\`", "`")  # template-literal escapes
    prompt = reviewer_prompt(CONFIRM_ARGS, "bug-hunter")
    for line in prompt.splitlines():
        static = (
            line.split(":")[0]
            if line.startswith(
                ("PURPOSE", "INPUT UNIVERSE", "PRIMARY PATH", "OUT OF SCOPE", "SCOPE", "TARGET")
            )
            else line
        )
        if static.startswith(
            ("Adversary lens", "- ", "Return your findings", "INSTRUMENT AVAILABLE")
        ):
            continue
        assert static in js, f"not in the script: {static[:60]!r}"
    fields = re.search(r"required: \[('severity'.*?)\]", js).group(1)
    assert all(f"'{f}'" in fields or f"{f}:" in js for f in FINDING_FIELDS)
    assert prompt.endswith(", ".join(FINDING_FIELDS) + ".")


def test_prompt_cli_refuses_the_script_refusals(tmp_path: Path, capsys: pytest.CaptureFixture):
    no_bar = tmp_path / "no-bar.json"
    no_bar.write_text(json.dumps({**REVIEW_ARGS, "bar": {"purpose": "p"}}), encoding="utf-8")
    assert main(["prompt", str(no_bar), "--lens", "bug-hunter"]) == 2
    assert "purpose, inputs and primaryPath" in capsys.readouterr().err
    stale = tmp_path / "stale.json"
    stale.write_text(
        json.dumps({**CONFIRM_ARGS, "state": {**CONFIRM_ARGS["state"], "contract": 1}}),
        encoding="utf-8",
    )
    assert main(["prompt", str(stale), "--lens", "bug-hunter"]) == 2
    assert "loop contract 1" in capsys.readouterr().err
    good = tmp_path / "good.json"
    good.write_text(json.dumps(CONFIRM_ARGS), encoding="utf-8")
    out = tmp_path / "prompt.txt"
    assert main(["prompt", str(good), "--lens", "architect", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Adversary lens: architect." in text
    assert "- b.py:2: s2 [b.py] patch: /tmp/r2.patch" in text
    assert "OUT OF SCOPE (explicitly): hand-edited files" in text
