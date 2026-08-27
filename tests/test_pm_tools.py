"""Contract tests for the `pm-tools` CLI.

The markdown file is the whole store, so every test drives the real CLI against a
real file in tmp_path and asserts on what landed on disk - not on internal state.
The invariants that matter are the ones the skill promises: ids are permanent and
never reused, the checkbox is the only status, the log is append-only, an
untriaged defect fails the gate, and every derived fact is computed on read.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from stellars_claude_code_plugins.project_management import pm_tools

DEFECTS_HEADER = "# Defects - App\n\nDefects for the app.\n"
ACC_HEADER = "# Acceptance Criteria - App\n\nCriteria for the app.\n"


def run(*argv: str) -> int:
    """Invoke the CLI the way the console script does."""
    return pm_tools.main(["pm-tools", *argv])


@pytest.fixture
def defects(tmp_path: Path) -> Path:
    f = tmp_path / "defects-app.md"
    f.write_text(DEFECTS_HEADER, encoding="utf-8")
    run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    return f


@pytest.fixture
def criteria(tmp_path: Path) -> Path:
    f = tmp_path / "acc-crit-app.md"
    f.write_text(ACC_HEADER, encoding="utf-8")
    run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    return f


def add_defect(f: Path, title: str, severity: str = "MAJOR", category: str = "LNCH") -> int:
    return run(
        "add",
        str(f),
        "--category",
        category,
        "--name",
        "Launch",
        "--author",
        "@kj",
        "--severity",
        severity,
        "--description",
        "Cold start and the first turn",
        "--title",
        title,
        "--text",
        "symptom; cause under investigation",
        "--repro",
        "fork under load, send a turn inside 2s",
        "--test-tags",
        "integration",
    )


def add_criterion(f: Path, title: str, category: str = "AUTH") -> int:
    return run(
        "add",
        str(f),
        "--category",
        category,
        "--name",
        "Authentication",
        "--author",
        "@kj",
        "--description",
        "Login and session lifetime",
        "--title",
        title,
        "--text",
        "16 chars, 3 character classes",
        "--test",
        "generate 100 passwords, assert length",
        "--test-tags",
        "unit",
    )


# --- Authoring ------------------------------------------------------------


def test_roster_is_required_before_a_handle_can_write(tmp_path: Path):
    """An unknown handle is refused rather than invented into the roster."""
    f = tmp_path / "defects-app.md"
    f.write_text(DEFECTS_HEADER, encoding="utf-8")
    with pytest.raises(SystemExit):
        add_defect(f, "token race")


def test_author_creates_the_roster_section(defects: Path):
    body = defects.read_text(encoding="utf-8")
    assert "## Authors" in body
    assert "- `@kj` Konrad Jelen" in body


# --- Ids ------------------------------------------------------------------


def test_add_assigns_the_next_id_and_the_category_code(defects: Path):
    add_defect(defects, "token race on relaunch")
    assert "`DEF-LNCH-1`" in defects.read_text(encoding="utf-8")


def test_numbers_are_unique_across_the_document_not_per_category(defects: Path):
    add_defect(defects, "token race", category="LNCH")
    run(
        "add",
        str(defects),
        "--category",
        "AUTH",
        "--name",
        "Authentication",
        "--author",
        "@kj",
        "--severity",
        "MINOR",
        "--description",
        "Login",
        "--title",
        "stale avatar",
        "--text",
        "symptom",
        "--repro",
        "log in twice",
    )
    ids = re.findall(r"`(DEF-[A-Z]+-\d+)`", defects.read_text(encoding="utf-8"))
    assert ids == ["DEF-LNCH-1", "DEF-AUTH-2"], "the counter is the whole file, not the category"


def test_a_closed_id_is_never_recycled(defects: Path):
    """Closing leaves the item in place, so its number is still the high-water mark."""
    add_defect(defects, "first")
    run("close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed")
    add_defect(defects, "second")
    ids = re.findall(r"`(DEF-LNCH-\d+)`", defects.read_text(encoding="utf-8"))
    assert ids == ["DEF-LNCH-1", "DEF-LNCH-2"]


def test_removing_the_highest_id_frees_that_number(defects: Path):
    """The consequence of storing no counter: the next id is the highest IN THE FILE
    plus one, so deleting the highest hands its number back.

    That is why `remove` is documented for mistakes and duplicates only - an item
    that turned out to be invalid is `reject`ed, which keeps it (and its number) in
    the file. Pinned here so the tradeoff is a decision, not a surprise.
    """
    add_defect(defects, "first")
    add_defect(defects, "second")
    run("remove", str(defects), "--id", "DEF-LNCH-2")
    add_defect(defects, "third")
    body = defects.read_text(encoding="utf-8")
    assert re.findall(r"`(DEF-LNCH-\d+)`", body) == ["DEF-LNCH-1", "DEF-LNCH-2"]
    assert "third" in body and "second" not in body


def test_rejecting_keeps_the_number_out_of_circulation(defects: Path):
    """The documented alternative to remove: the trail survives and so does the id."""
    add_defect(defects, "first")
    add_defect(defects, "second")
    run("reject", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "no repro")
    add_defect(defects, "third")
    ids = re.findall(r"`(DEF-LNCH-\d+)`", defects.read_text(encoding="utf-8"))
    assert ids == ["DEF-LNCH-1", "DEF-LNCH-2", "DEF-LNCH-3"]


# --- Triage ---------------------------------------------------------------


def test_add_refuses_a_defect_with_no_severity(defects: Path):
    with pytest.raises(SystemExit):
        run(
            "add",
            str(defects),
            "--category",
            "LNCH",
            "--name",
            "Launch",
            "--author",
            "@kj",
            "--title",
            "untriaged",
            "--text",
            "symptom",
            "--repro",
            "boot cold",
        )


def test_severity_is_refused_on_a_criterion(criteria: Path):
    with pytest.raises(SystemExit):
        run(
            "add",
            str(criteria),
            "--category",
            "AUTH",
            "--name",
            "Authentication",
            "--author",
            "@kj",
            "--severity",
            "MAJOR",
            "--title",
            "password rules",
            "--text",
            "16 chars",
            "--test",
            "generate 100",
        )


def test_check_errors_on_an_untriaged_defect(defects: Path, capsys):
    add_defect(defects, "token race")
    body = defects.read_text(encoding="utf-8").replace("MAJOR; ", "")
    defects.write_text(body, encoding="utf-8")
    assert run("check", str(defects)) != 0
    assert "error" in capsys.readouterr().out.lower()


# --- Three states ---------------------------------------------------------


def test_close_flips_the_box_and_logs_it(defects: Path):
    add_defect(defects, "token race")
    run(
        "close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed: awaited"
    )
    body = defects.read_text(encoding="utf-8")
    assert "- [x] `DEF-LNCH-1`" in body
    assert "closed: fixed: awaited" in body


def test_reject_requires_a_reason_and_records_it(defects: Path):
    add_defect(defects, "splash hang")
    with pytest.raises(SystemExit):
        run("reject", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    run(
        "reject",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "not reproduced on 3 devices",
    )
    body = defects.read_text(encoding="utf-8")
    assert "- [-] `DEF-LNCH-1`" in body
    assert "not reproduced on 3 devices" in body


def test_reopen_returns_a_rejected_item_to_open(defects: Path):
    add_defect(defects, "splash hang")
    run("reject", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "no repro")
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    assert "- [ ] `DEF-LNCH-1`" in defects.read_text(encoding="utf-8")


# --- The log --------------------------------------------------------------


def test_the_log_is_append_only_and_keeps_failed_attempts(defects: Path):
    add_defect(defects, "token race")
    run(
        "log",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "attempted: 200ms delay - did NOT work",
    )
    run("close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed")
    logs = [ln for ln in defects.read_text(encoding="utf-8").splitlines() if "- log:" in ln]
    assert len(logs) == 3, "add, attempt and close each leave their own line"
    assert any("did NOT work" in ln for ln in logs), "a failed attempt is logged, never erased"


def test_log_stamps_are_iso_8601_utc(defects: Path):
    add_defect(defects, "token race")
    stamps = re.findall(r"- log: (\S+) @kj", defects.read_text(encoding="utf-8"))
    assert stamps
    for s in stamps:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", s), f"not Zulu ISO 8601: {s}"


# --- Relations and computed facts ----------------------------------------


def test_refs_computes_backlinks_that_are_never_written_back(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash hang")
    run("relate", str(defects), "--id", "DEF-LNCH-1", "--related", "DEF-LNCH-2 - same subsystem")
    body = defects.read_text(encoding="utf-8")
    assert body.count("related:") == 1, "the reverse side is computed, never written"
    capsys.readouterr()
    run("refs", str(defects), "--id", "DEF-LNCH-2")
    assert "DEF-LNCH-1" in capsys.readouterr().out


def test_list_categories_derives_the_index(defects: Path, capsys):
    add_defect(defects, "token race")
    run("close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed")
    add_defect(defects, "splash hang")
    capsys.readouterr()
    run("list-categories", str(defects))
    out = capsys.readouterr().out
    assert "LNCH" in out and "Launch" in out


# --- Reports --------------------------------------------------------------


def test_report_lists_open_work_and_counts_the_rest(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash hang")
    run("close", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "fixed")
    capsys.readouterr()
    run("report", str(defects))
    out = capsys.readouterr().out
    assert "SUMMARY" in out and "ITEMS" in out
    assert "token race" in out, "the open defect is in the fix queue"
    assert "1 closed not listed" in out, "closed work is counted, not enumerated"


def test_report_detail_prints_the_whole_log(defects: Path, capsys):
    add_defect(defects, "token race")
    run(
        "log",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "attempted: 200ms delay - did NOT work",
    )
    capsys.readouterr()
    run("report", str(defects), "--detail")
    out = capsys.readouterr().out
    assert "did NOT work" in out
    assert "fork under load" in out, "--detail carries the repro line verbatim"


# --- The gate -------------------------------------------------------------


def test_check_passes_a_well_formed_file(defects: Path, criteria: Path):
    add_defect(defects, "token race")
    add_criterion(criteria, "Password generation")
    assert run("check", str(defects)) == 0
    assert run("check", str(criteria)) == 0


def test_check_rejects_a_hand_kept_contents_table(criteria: Path, capsys):
    add_criterion(criteria, "Password generation")
    body = criteria.read_text(encoding="utf-8").replace(
        "## Authors", "## Contents\n\n- [Authentication](#authentication)\n\n## Authors", 1
    )
    criteria.write_text(body, encoding="utf-8")
    assert run("check", str(criteria)) != 0
    assert "contents" in capsys.readouterr().out.lower()


def test_check_reports_a_dangling_relation_without_repairing_it(defects: Path, capsys):
    add_defect(defects, "token race")
    run("relate", str(defects), "--id", "DEF-LNCH-1", "--related", "DEF-LNCH-99")
    before = defects.read_text(encoding="utf-8")
    run("check", str(defects))
    assert "DEF-LNCH-99" in capsys.readouterr().out
    assert defects.read_text(encoding="utf-8") == before, "check reports, it does not repair"


def test_the_wrong_hint_for_the_discipline_is_an_error(defects: Path, capsys):
    """A defect carries `repro:`, a criterion carries `test:` - never the other way."""
    add_defect(defects, "token race")
    body = defects.read_text(encoding="utf-8").replace("  - repro:", "  - test:", 1)
    defects.write_text(body, encoding="utf-8")
    assert run("check", str(defects)) != 0


# --- Path resolution ------------------------------------------------------


def test_a_directory_is_scanned_for_both_disciplines(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    d, c = docs / "defects-app.md", docs / "acc-crit-app.md"
    d.write_text(DEFECTS_HEADER, encoding="utf-8")
    c.write_text(ACC_HEADER, encoding="utf-8")
    for f in (d, c):
        run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    add_defect(d, "token race")
    add_criterion(c, "Password generation")
    capsys.readouterr()
    run("report", str(docs))
    out = capsys.readouterr().out
    assert "token race" in out and "Password generation" in out
