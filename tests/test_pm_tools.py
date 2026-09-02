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


def add_criterion(f: Path, title: str, category: str = "AUTH", importance: str = "HIGH") -> int:
    return run(
        "add",
        str(f),
        "--category",
        category,
        "--name",
        "Authentication",
        "--author",
        "@kj",
        "--importance",
        importance,
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
    run(
        "close",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "fixed",
        "--evidence",
        "unit suite green",
    )
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
        "close",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "fixed: awaited",
        "--evidence",
        "unit suite green",
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
    run(
        "close",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "fixed",
        "--evidence",
        "unit suite green",
    )
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
    run(
        "close",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "fixed",
        "--evidence",
        "unit suite green",
    )
    add_defect(defects, "splash hang")
    capsys.readouterr()
    run("list-categories", str(defects))
    out = capsys.readouterr().out
    assert "LNCH" in out and "Launch" in out


# --- Evidence -------------------------------------------------------------


def close_with(f: Path, item: str, evidence: str, event: str = "fixed") -> int:
    return run(
        "close",
        str(f),
        "--id",
        item,
        "--author",
        "@kj",
        "--event",
        event,
        "--evidence",
        evidence,
    )


def test_closing_a_defect_demands_evidence(defects: Path):
    """A closure with no proof is a claim. The flag is required so it cannot be one."""
    add_defect(defects, "token race")
    with pytest.raises(SystemExit):
        run("close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed")
    assert "- [ ] `DEF-LNCH-1`" in defects.read_text(encoding="utf-8"), "and nothing was closed"


def test_closing_a_criterion_demands_evidence_too(criteria: Path):
    add_criterion(criteria, "password length")
    with pytest.raises(SystemExit):
        run("close", str(criteria), "--id", "ACC-AUTH-1", "--author", "@kj")
    close_with(criteria, "ACC-AUTH-1", "100 generated passwords, all 16 chars", "met")
    body = criteria.read_text(encoding="utf-8")
    assert "- [x] `ACC-AUTH-1`" in body
    assert "- evidence: 100 generated passwords, all 16 chars" in body


def test_evidence_is_stored_once_on_its_own_line(defects: Path):
    add_defect(defects, "token race")
    close_with(defects, "DEF-LNCH-1", "test_fork_token green on build 412")
    body = defects.read_text(encoding="utf-8")
    assert body.count("- evidence:") == 1
    assert "- evidence: test_fork_token green on build 412" in body
    assert "closed: fixed" in body, "the log still records the closure event"


def test_reopening_a_criterion_retires_the_evidence_and_logs_what_it_was(criteria: Path):
    """Reopened means not done, so the proof cannot stand - but the log keeps it."""
    add_criterion(criteria, "session survives a refresh")
    close_with(criteria, "ACC-AUTH-1", "test_refresh green", event="done")
    run("reopen", str(criteria), "--id", "ACC-AUTH-1", "--author", "@kj", "--event", "not done")
    body = criteria.read_text(encoding="utf-8")
    assert "- evidence:" not in body, "the line goes with the closure"
    assert "evidence retired: test_refresh green" in body, "the log remembers it"


def test_reopening_a_defect_mints_a_regression_and_leaves_the_closure_proven(defects: Path):
    """A proven fix that broke again is a new fact, not a reversal of the old one."""
    add_defect(defects, "token race")
    close_with(defects, "DEF-LNCH-1", "test_fork_token green")
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "regressed")
    body = defects.read_text(encoding="utf-8")
    assert "- [x] `DEF-LNCH-1`" in body, "the parent closure stands"
    assert "- evidence: test_fork_token green" in body, "it was proven when it was made"
    assert "- [ ] `DEF-LNCH-1-1`" in body, "the regression is its own open item"
    assert "regressed as DEF-LNCH-1-1" in body, "the parent names where it went"
    assert "regression of DEF-LNCH-1: regressed" in body, "the child names its parent"


def test_regressions_number_flat_from_the_root(defects: Path):
    """A regression of a regression is the next ordinal on the root, never nested."""
    add_defect(defects, "token race")
    close_with(defects, "DEF-LNCH-1", "green on 412")
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    close_with(defects, "DEF-LNCH-1-1", "green on 470")
    run("reopen", str(defects), "--id", "DEF-LNCH-1-1", "--author", "@kj")
    body = defects.read_text(encoding="utf-8")
    assert "`DEF-LNCH-1-2`" in body, "the third occurrence is -2 on the root"
    assert "DEF-LNCH-1-1-1" not in body, "ordinals never nest"


def test_a_rejected_defect_reopens_without_minting(defects: Path):
    """Rejected was never fixed, so undoing it is triage, not a regression."""
    add_defect(defects, "token race")
    run("reject", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "not ours")
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    body = defects.read_text(encoding="utf-8")
    assert "- [ ] `DEF-LNCH-1`" in body, "the item itself reopens"
    assert "DEF-LNCH-1-1" not in body, "a rejection reversal is not a regression"


def test_the_report_counts_the_regressions(defects: Path, capsys):
    """The count is the whole point of the derived ids."""
    add_defect(defects, "token race")
    close_with(defects, "DEF-LNCH-1", "green on 412")
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    close_with(defects, "DEF-LNCH-1-1", "green on 470")
    run("reopen", str(defects), "--id", "DEF-LNCH-1-1", "--author", "@kj")
    capsys.readouterr()
    run("report", str(defects), "--status", "all")
    assert "2 regressions across 1 defect" in capsys.readouterr().out


def test_a_regression_without_its_root_is_an_error(defects: Path, capsys):
    """A regression is a fact about a defect; orphaned it counts nothing."""
    add_defect(defects, "token race")
    close_with(defects, "DEF-LNCH-1", "green on 412")
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    body = defects.read_text(encoding="utf-8")
    defects.write_text(body.replace("`DEF-LNCH-1`", "`DEF-LNCH-7`"), encoding="utf-8")
    capsys.readouterr()
    assert run("check", str(defects)) == 1
    assert "regression DEF-LNCH-1-1 has no root item DEF-LNCH-1" in capsys.readouterr().out


def test_severity_case_is_free_but_the_delimiter_is_not(defects: Path, capsys):
    run(
        "add",
        str(defects),
        "--category",
        "AUTH",
        "--title",
        "Upper",
        "--text",
        "upper",
        "--severity",
        "MAJOR",
        "--author",
        "@kj",
        "--name",
        "Authentication",
    )
    text = defects.read_text(encoding="utf-8")
    text = text.replace("MAJOR; upper", "major; lower") + (
        "- [ ] `DEF-AUTH-2` **Legacy** - High: hand kept\n"
        "- [ ] `DEF-AUTH-3` **Prose** - Major refactor needed; no level\n"
    )
    defects.write_text(text, encoding="utf-8")
    run("list", str(defects), "--status", "all", "--columns", "id,severity")
    out = capsys.readouterr().out
    assert "| `DEF-AUTH-1` | MAJOR |" in out
    assert "| `DEF-AUTH-2` | MAJOR |" in out
    assert "| `DEF-AUTH-3` | - |" in out


def test_check_anchors_a_cycle_even_on_a_duplicated_id(tmp_path: Path, capsys):
    f = tmp_path / "defects-app.md"
    f.write_text(
        "# Defects - App\n\n## Launch `LNCH`\n\nBoot\n\n"
        "- [ ] `DEF-LNCH-1` **a copy** - MAJOR; duplicate without the link\n"
        "  - log: 2026-01-02T00:00:00Z @kj added\n"
        "- [ ] `DEF-LNCH-1` **a** - MAJOR; one\n"
        "  - blocked-by: DEF-LNCH-2\n"
        "  - log: 2026-01-02T00:00:00Z @kj added\n"
        "- [ ] `DEF-LNCH-2` **b** - MAJOR; two\n"
        "  - blocked-by: DEF-LNCH-1\n"
        "  - log: 2026-01-02T00:00:00Z @kj added\n\n"
        "## Authors\n\n- `@kj` Konrad Jelen\n",
        encoding="utf-8",
    )
    assert run("check", str(f)) == 1  # duplicate id and cycle, never a crash
    out = capsys.readouterr().out
    assert "duplicate id" in out
    assert "blocked-by cycle" in out


def test_search_query_may_share_a_name_with_a_cwd_entry(tmp_path: Path, capsys, monkeypatch):
    f = tmp_path / "defects-app.md"
    f.write_text(DEFECTS_HEADER, encoding="utf-8")
    run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    run(
        "add",
        str(f),
        "--category",
        "DOCS",
        "--name",
        "Docs",
        "--title",
        "docs drift",
        "--text",
        "docs out of date",
        "--severity",
        "MINOR",
        "--author",
        "@kj",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "notes.md").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert run("search", str(f), "docs") == 0  # a query word that names a cwd entry is a query
    assert "docs drift" in capsys.readouterr().out
    with pytest.raises(
        SystemExit
    ):  # no path given and the query is one: the forgotten-QUERY shape
        run("search", "notes.md")


def test_upgrade_writes_the_canonical_severity_form(tmp_path: Path, capsys):
    f = tmp_path / "defects-legacy.md"
    f.write_text(
        "# Defects - Legacy\n\n## Launch `LNCH`\n\nCold start\n\n"
        "- [ ] `DEF-LNCH-1` **Legacy** - High: hand kept\n"
        "  - log: 2026-01-02T00:00:00Z @kj filed\n"
        "- [ ] `DEF-LNCH-2` **Lower** - major; typed by hand\n"
        "  - log: 2026-01-02T00:00:00Z @kj filed\n\n"
        "## Authors\n\n- `@kj` Konrad Jelen\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    run("upgrade", str(f), "--apply")
    body = f.read_text(encoding="utf-8")
    assert "**Legacy** - MAJOR; hand kept" in body
    assert "**Lower** - MAJOR; typed by hand" in body
    assert "HIGH -> MAJOR x1" in capsys.readouterr().out


def test_upgrade_keeps_regression_ordinals_and_leaves_criteria_alone(tmp_path: Path, capsys):
    d = tmp_path / "defects-legacy.md"
    d.write_text(
        "# Defects - Legacy\n\n## Launch `LNCH`\n\nCold start\n\n"
        "- [x] `DEF-LNCH-3` **Root** - MAJOR; fixed once\n"
        "  - log: 2026-01-02T00:00:00Z @kj closed: fixed\n"
        "- [ ] `DEF-LNCH-3-1` **Root again** - MAJOR; regressed\n"
        "  - log: 2026-01-03T00:00:00Z @kj filed\n\n"
        "## Authors\n\n- `@kj` Konrad Jelen\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    run("upgrade", str(d), "--apply")
    assert "`DEF-LNCH-3-1`" in d.read_text(encoding="utf-8")
    assert "0 change(s)" in capsys.readouterr().out
    assert run("check", str(d)) == 0
    d.write_text(
        d.read_text(encoding="utf-8").replace("MAJOR; regressed", "regressed"), encoding="utf-8"
    )
    run("upgrade", str(d))
    res = capsys.readouterr()
    assert "DEF-LNCH-3-1 not triaged; run: pm-tools edit" in res.out + res.err
    a = tmp_path / "acc-crit-legacy.md"
    a.write_text(
        "# Acceptance Criteria - Legacy\n\n## Banner `BNR`\n\nBanner\n\n"
        "- [ ] `ACC-BNR-1` **modes** - Normal, degraded and offline modes render the banner\n"
        "  - log: 2026-01-02T00:00:00Z @kj filed\n\n"
        "## Authors\n\n- `@kj` Konrad Jelen\n",
        encoding="utf-8",
    )
    run("upgrade", str(a), "--apply")
    assert "Normal, degraded and offline" in a.read_text(encoding="utf-8")
    capsys.readouterr()
    assert run("check", str(a)) != 0, "an unrated criterion is a check error"
    assert "criterion not rated" in capsys.readouterr().out


def test_edit_records_evidence_after_the_fact(defects: Path, capsys):
    """A document closed before evidence existed is fixed forward, not rewritten."""
    add_defect(defects, "token race")
    close_with(defects, "DEF-LNCH-1", "placeholder")
    run(
        "edit",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--evidence",
        "manual retest on build 412",
    )
    body = defects.read_text(encoding="utf-8")
    assert body.count("- evidence:") == 1, "replaced, never duplicated"
    assert "- evidence: manual retest on build 412" in body


def test_check_warns_on_a_closed_item_carrying_no_evidence(tmp_path: Path, capsys):
    f = tmp_path / "defects-legacy.md"
    f.write_text(
        "# Defects - Legacy\n\n## Launch `LNCH`\n\nCold start\n\n"
        "- [x] `DEF-LNCH-1` **old bug** - MAJOR; fixed long ago\n"
        "  - repro: n/a\n  - test-tags: manual\n"
        "  - log: 2026-01-02T00:00:00Z @kj closed: fixed\n\n"
        "## Authors\n\n- `@kj` Konrad Jelen\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    assert run("check", str(f)) == 0, "a legacy closure is a warning, not a broken document"
    assert "closed with no evidence" in capsys.readouterr().out
    assert run("check", str(f), "--strict") == 1, "but --strict refuses it"


def test_report_carries_an_evidence_column_when_something_has_one(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash flicker")
    close_with(defects, "DEF-LNCH-1", "test_fork_token green on build 412")
    capsys.readouterr()
    run("report", str(defects), "--status", "closed")
    assert "Evidence" in capsys.readouterr().out

    capsys.readouterr()
    run("report", str(defects))
    out = capsys.readouterr().out
    assert "Evidence" not in out, "an open queue has nothing proven yet, so no column"


# --- Reports --------------------------------------------------------------


def test_report_lists_open_work_and_counts_the_rest(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash hang")
    run(
        "close",
        str(defects),
        "--id",
        "DEF-LNCH-2",
        "--author",
        "@kj",
        "--event",
        "fixed",
        "--evidence",
        "unit suite green",
    )
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


def restamp(f: Path, item: str, stamp: str, event: str = "added") -> None:
    """Set the stamp on one of an item's log lines - the file is the whole store, so a
    test that needs a specific date writes one into it."""
    lines = f.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if f"`{item}`" in ln and "- [" in ln)
    for i in range(start + 1, len(lines)):
        if "- [" in lines[i]:
            break
        if lines[i].strip().startswith("- log: ") and event in lines[i]:
            lines[i] = re.sub(r"- log: \S+", f"- log: {stamp}", lines[i])
            f.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise AssertionError(f"{item} has no {event!r} log line")


def test_report_severity_filter_narrows_the_whole_report(defects: Path, capsys):
    """ "show me the critical defects" is a flag, not something the reader filters."""
    add_defect(defects, "token race", severity="CRITICAL")
    add_defect(defects, "splash flicker", severity="MINOR")
    capsys.readouterr()
    run("report", str(defects), "--severity", "CRITICAL")
    out = capsys.readouterr().out
    assert "token race" in out and "splash flicker" not in out
    assert "1 open / 0 closed" in out, "the counts follow the filter, not the file"
    assert "| Category | Open | Fixed | Rejected | Total |" in out
    assert "| Launch `LNCH` | 1 | 0 | 0 | 1 |" in out
    assert "| Launch `LNCH` | 1 | 0 | 0 | 0 | 1 |" in out, "an emptied level reads 0"


def test_report_severity_is_refused_on_a_criteria_document(criteria: Path, capsys):
    add_criterion(criteria, "password length")
    capsys.readouterr()
    run("report", str(criteria), "--severity", "CRITICAL")
    cap = capsys.readouterr()
    assert "skipped" in cap.err, "severity is a defect attribute; say so rather than print zeros"
    assert "SUMMARY" not in cap.out


def test_report_filters_on_the_date_an_item_was_filed(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash flicker")
    restamp(defects, "DEF-LNCH-1", "2026-05-04T09:00:00Z")
    restamp(defects, "DEF-LNCH-2", "2026-07-21T12:00:00Z")
    capsys.readouterr()
    run("report", str(defects), "--since", "2026-07-01", "--until", "2026-07-31")
    out = capsys.readouterr().out
    assert "splash flicker" in out and "token race" not in out
    assert "filed 2026-07-01 to 2026-07-31" in out, "the header says which window was applied"


def test_report_filters_on_the_date_an_item_was_closed(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash flicker")
    run(
        "close",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "fixed",
        "--evidence",
        "unit suite green",
    )
    restamp(defects, "DEF-LNCH-1", "2026-08-26T14:00:00Z", event="closed")
    capsys.readouterr()
    run("report", str(defects), "--dates", "closed", "--since", "2026-08-01")
    out = capsys.readouterr().out
    assert "token race" in out, "a closed window lists what it found without --status all"
    assert "splash flicker" not in out, "an open item has no closed date"


def test_a_reopened_criterion_has_no_closed_date(criteria: Path, capsys):
    add_criterion(criteria, "session survives a refresh")
    close_with(criteria, "ACC-AUTH-1", "unit suite green", event="done")
    restamp(criteria, "ACC-AUTH-1", "2026-08-26T14:00:00Z", event="closed")
    run("reopen", str(criteria), "--id", "ACC-AUTH-1", "--author", "@kj")
    capsys.readouterr()
    run("report", str(criteria), "--dates", "closed", "--since", "2026-08-01")
    out = capsys.readouterr().out
    assert "session survives a refresh" not in out, "reopening retires the closed date"


def test_a_regressed_defect_keeps_its_closed_date(defects: Path, capsys):
    """The parent really was closed on that day; the regression is a separate item."""
    add_defect(defects, "token race")
    close_with(defects, "DEF-LNCH-1", "unit suite green")
    restamp(defects, "DEF-LNCH-1", "2026-08-26T14:00:00Z", event="closed")
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    capsys.readouterr()
    run("report", str(defects), "--dates", "closed", "--since", "2026-08-01")
    out = capsys.readouterr().out
    assert "`DEF-LNCH-1`" in out, "the closure happened and keeps its date"
    assert "`DEF-LNCH-1-1`" not in out, "the open regression has no closed date"


def test_report_plain_drops_the_chrome_and_keeps_the_data(defects: Path, capsys):
    add_defect(defects, "token race")
    capsys.readouterr()
    run("report", str(defects), "--plain")
    out = capsys.readouterr().out
    assert "SUMMARY" in out and "ITEMS" in out and "DEF-LNCH-1" in out
    assert "\U0001f4ca" not in out and "\U0001f41e" not in out, "no icons"
    assert "Categories down" not in out, "no section blurb"
    assert "CATEGORIES" not in out and "TEST COVERAGE" not in out


def test_report_summary_stops_at_the_grid(defects: Path, capsys):
    """A summary is the aggregate. Listing the items underneath is answering a
    different question than the one that was asked."""
    add_defect(defects, "token race")
    add_defect(defects, "splash flicker")
    capsys.readouterr()
    run("report", str(defects), "--summary")
    out = capsys.readouterr().out
    assert "SUMMARY" in out and "2 open / 0 closed" in out
    assert "ITEMS" not in out
    assert "token race" not in out and "splash flicker" not in out
    assert "CATEGORIES" not in out and "TEST COVERAGE" not in out
    assert "Categories down" not in out, "--summary is plain by itself"


def test_report_refuses_a_malformed_date(defects: Path):
    add_defect(defects, "token race")
    with pytest.raises(SystemExit):
        run("report", str(defects), "--since", "2026-8-1")


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
    assert run("check", str(defects)) != 0
    out = capsys.readouterr().out
    assert "DEF-LNCH-99" in out and "ERROR" in out
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


# --- Tables, pivots, filters and --json ---------------------------------------


def a_mixed_file(defects: Path, capsys) -> None:
    """Two authors, three severities, one regression, one rejection, mixed tags."""
    run("author", str(defects), "--handle", "@mb", "--name", "M B")
    add_defect(defects, "token race", "MAJOR")  # DEF-LNCH-1, @kj, integration
    run(
        "add",
        str(defects),
        "--category",
        "LNCH",
        "--author",
        "@mb",
        "--severity",
        "CRITICAL",
        "--title",
        "crash on boot",
        "--text",
        "segfault",
        "--repro",
        "boot twice",
        "--test-tags",
        "unit, e2e",
    )  # DEF-LNCH-2
    run(
        "add",
        str(defects),
        "--category",
        "UI",
        "--name",
        "Interface",
        "--description",
        "Screens",
        "--author",
        "@kj",
        "--severity",
        "MINOR",
        "--title",
        "misaligned button",
        "--text",
        "2px off",
        "--repro",
        "open settings",
    )  # DEF-UI-3
    run(
        "close",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--evidence",
        "clean on 412",
    )
    run("reopen", str(defects), "--id", "DEF-LNCH-1", "--author", "@mb", "--event", "back on 413")
    run(
        "reject",
        str(defects),
        "--id",
        "DEF-UI-3",
        "--author",
        "@kj",
        "--event",
        "no repro",
    )
    capsys.readouterr()  # the writes above narrate to stdout; the query under test starts clean


def table_rows(out: str) -> list[list[str]]:
    """Every markdown table body row in the output, split into cells."""
    rows = []
    for ln in out.splitlines():
        if ln.startswith("| ") and not set(ln) <= set("|-: "):
            rows.append([c.strip() for c in ln.strip("|").split("|")])
    return rows


def test_list_is_a_markdown_table_by_default(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    assert run("list", str(defects)) == 0
    out = capsys.readouterr().out
    rows = table_rows(out)
    assert rows[0] == ["Id", "Title", "Severity", "Status", "Category", "Author", "Filed", "Tests"]
    assert len(rows) == 5 and "4 item(s)" in out
    assert rows[1][0] == "`DEF-LNCH-2`"  # fix order: open first, worst first
    assert rows[-1][3] == "rejected"
    assert ":" not in out.split("\n# ")[1].split("\n")[0]  # no file:line prose lines


def test_list_columns_and_sort_are_the_callers_choice(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("list", str(defects), "--columns", "id,author,root,regr,age", "--sort=-severity,id")
    rows = table_rows(capsys.readouterr().out)
    assert rows[0] == ["Id", "Author", "Root", "Regr", "Age"]
    assert [r[0] for r in rows[1:]] == [
        "`DEF-UI-3`",  # MINOR first when severity descends
        "`DEF-LNCH-1`",
        "`DEF-LNCH-1-1`",
        "`DEF-LNCH-2`",
    ]
    assert rows[3][2:4] == ["`DEF-LNCH-1`", "1"]  # the regression names its root


def test_an_unknown_field_is_refused_with_the_vocabulary(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    with pytest.raises(SystemExit) as e:
        run("list", str(defects), "--columns", "id,bogus")
    assert "unknown field 'bogus'" in str(e.value) and "severity" in str(e.value)


def test_the_status_filter_narrows_the_list_and_is_named_in_its_title(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("list", str(defects), "--status", "open")
    out = capsys.readouterr().out
    assert "(open)" in out.splitlines()[1]
    assert {r[3] for r in table_rows(out)[1:]} == {"open"}
    assert "2 item(s)" in out


def test_pivot_counts_one_field_by_another(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    assert run("pivot", str(defects), "--rows", "severity", "--cols", "status") == 0
    out = capsys.readouterr().out
    rows = table_rows(out)
    assert rows[0] == ["Severity", "open", "closed", "rejected", "Total"]
    assert rows[1] == ["CRITICAL", "1", "-", "-", "1"]  # worst first, zero is a dash
    assert rows[2] == ["MAJOR", "1", "1", "-", "2"]
    assert rows[3] == ["MINOR", "-", "-", "1", "1"]
    assert rows[4] == ["**Total**", "2", "1", "1", "**4**"]
    assert "severity by status" in out


def test_pivot_can_fill_cells_with_ids(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("pivot", str(defects), "--rows", "author", "--values", "ids")
    rows = table_rows(capsys.readouterr().out)
    assert rows[0] == ["Author", "Items"]
    assert rows[1] == ["@kj", "`DEF-LNCH-1`, `DEF-UI-3`"]
    assert rows[2] == ["@mb", "`DEF-LNCH-1-1`, `DEF-LNCH-2`"]


def test_pivot_counts_a_tagged_item_in_every_tag(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("pivot", str(defects), "--rows", "tags")
    out = capsys.readouterr().out
    rows = table_rows(out)
    assert [r[0] for r in rows[1:]] == ["E2E", "INTEGRATION", "UNIT", "NO-TEST", "**Total**"]
    assert rows[-1][1] == "5" and "4 item(s)" in out  # one item sits in two tag buckets


def test_pivot_regressions_per_root_answers_how_regressive_the_system_is(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("pivot", str(defects), "--rows", "root", "--regressions", "--values", "ids")
    out = capsys.readouterr().out
    rows = table_rows(out)
    assert rows[1] == ["`DEF-LNCH-1`", "`DEF-LNCH-1-1`"]
    assert len(rows) == 2 and "(regressions only)" in out


def test_pivot_category_rows_carry_the_full_name(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("pivot", str(defects), "--rows", "category", "--cols", "status")
    rows = table_rows(capsys.readouterr().out)
    assert rows[1][0] == "Launch `LNCH`" and rows[2][0] == "Interface `UI`"


def test_author_and_tag_filters_narrow_report_list_and_pivot_alike(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("report", str(defects), "--author", "@mb", "--plain")
    rep = capsys.readouterr().out
    assert "(@mb)" in rep and "2 open / 0 closed / 0 rejected" in rep
    assert "Interface" not in rep  # a category the filter emptied gets no row
    run("list", str(defects), "--tag", "e2e")
    lst = capsys.readouterr().out
    assert [r[0] for r in table_rows(lst)[1:]] == ["`DEF-LNCH-2`"] and "(tag E2E)" in lst
    run("pivot", str(defects), "--rows", "severity", "--tag", "integration")
    piv = capsys.readouterr().out
    assert table_rows(piv)[1:] == [["MAJOR", "1"]]


def test_a_malformed_author_is_refused(defects: Path):
    with pytest.raises(SystemExit) as e:
        run("list", str(defects), "--author", "kj")
    assert "@kj" in str(e.value)


def test_the_defects_grid_is_plain_open_counts_per_severity(defects: Path, capsys):
    """Status and level are two grids (DEF-PMGT-51): Fixed and Rejected are single
    counts beside Open, the severity columns break Open down and end in it, zeros
    are written as 0, and there is no legend line."""
    a_mixed_file(defects, capsys)
    for args in ((), ("--plain",), ("--summary",)):
        run("report", str(defects), *args)
        out = capsys.readouterr().out
        assert "| Category | Open | Fixed | Rejected | Total |" in out
        assert "| Launch `LNCH` | 2 | 1 | 0 | 3 |" in out
        assert "| Interface `UI` | 0 | 0 | 1 | 1 |" in out
        assert "| **Total** | 2 | 1 | 1 | 4 |" in out
        assert "**Open by severity**" in out
        assert "| Category | CRITICAL | MAJOR | MEDIUM | MINOR | Open |" in out
        assert "| Launch `LNCH` | 1 | 1 | 0 | 0 | 2 |" in out
        assert "| Interface `UI` | 0 | 0 | 0 | 0 | 0 |" in out
        assert "| **Total** | 1 | 1 | 0 | 0 | 2 |" in out
        assert "| Open | CRITICAL" not in out, "status and level never share a row"
        assert "Cells are" not in out and "open/closed" not in out, "no legend in any form"


def test_the_level_grid_is_absent_when_nothing_is_open(defects: Path, capsys):
    """A grid of zeros carries nothing - like UNTRIAGED, the level split is printed
    only when something is open (DEF-PMGT-51)."""
    add_defect(defects, "token race")
    run("close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--evidence", "1.2 green")
    capsys.readouterr()
    run("report", str(defects), "--summary")
    out = capsys.readouterr().out
    assert "| Launch `LNCH` | 0 | 1 | 0 | 1 |" in out
    assert "Open by severity" not in out and "| CRITICAL |" not in out


def test_report_json_carries_the_same_facts_as_the_tables(defects: Path, capsys):
    import json

    a_mixed_file(defects, capsys)
    run("report", str(defects), "--json")
    (doc,) = json.loads(capsys.readouterr().out)
    assert doc["type"] == "DEF" and doc["counts"] == {"open": 2, "closed": 1, "rejected": 1}
    assert doc["regressions"] == {"count": 1, "defects": 1}
    assert doc["summary"]["columns"] == ["CRITICAL", "MAJOR", "MEDIUM", "MINOR"]
    launch = doc["summary"]["rows"][0]
    assert launch["category"] == "LNCH" and launch["open"] == 2
    assert launch["levels"] == {"CRITICAL": 1, "MAJOR": 1, "MEDIUM": 0, "MINOR": 0}
    assert launch["fixed"] == 1 and launch["rejected"] == 0
    assert [i["id"] for i in doc["items"]] == ["DEF-LNCH-2", "DEF-LNCH-1-1"]  # the open queue
    assert doc["rejected"] == [
        {"id": "DEF-UI-3", "title": "misaligned button", "reason": "no repro"}
    ]
    assert "coverage" not in doc, "coverage is its own command now"


def test_list_and_pivot_json_are_records_and_cells(defects: Path, capsys):
    import json

    a_mixed_file(defects, capsys)
    run("list", str(defects), "--status", "open", "--json")
    recs = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in recs] == ["DEF-LNCH-2", "DEF-LNCH-1-1"]
    assert recs[1]["root"] == "DEF-LNCH-1" and recs[1]["regr"] == 1
    assert recs[0]["tags"] == ["UNIT", "E2E"] and recs[0]["file"] == str(defects)
    run("pivot", str(defects), "--rows", "severity", "--cols", "status", "--json")
    (piv,) = json.loads(capsys.readouterr().out)
    assert piv["columns"] == ["open", "closed", "rejected"]
    assert piv["table"][1] == {
        "row": "MAJOR",
        "cells": {"open": 1, "closed": 1, "rejected": 0},
        "total": 2,
    }
    run("pivot", str(defects), "--rows", "author", "--values", "ids", "--json")
    (piv,) = json.loads(capsys.readouterr().out)
    assert piv["table"][0]["cells"] == {"Items": ["DEF-LNCH-1", "DEF-UI-3"]}


def test_list_categories_and_refs_take_json_too(defects: Path, capsys):
    import json

    a_mixed_file(defects, capsys)
    run("relate", str(defects), "--id", "DEF-LNCH-2", "--related", "DEF-LNCH-1 - same boot path")
    capsys.readouterr()
    run("list-categories", str(defects), "--json")
    (doc,) = json.loads(capsys.readouterr().out)
    assert doc["categories"][0] == {
        "code": "LNCH",
        "name": "Launch",
        "description": "Cold start and the first turn",
        "open": 2,
        "closed": 1,
        "rejected": 0,
    }
    run("refs", str(defects), "--id", "DEF-LNCH-1", "--json")
    doc = json.loads(capsys.readouterr().out)
    assert [(h["id"], h["kind"]) for h in doc["inbound"]] == [("DEF-LNCH-2", "related")]
    assert doc["outbound"] == []


# --- Relations in queries, --grep, search, link integrity ------------------------


def relate(f: Path, item: str, related: str | None = None, blocked: str | None = None) -> int:
    argv = ["relate", str(f), "--id", item]
    if related:
        argv += ["--related", related]
    if blocked:
        argv += ["--blocked-by", blocked]
    return run(*argv)


def ids_of(rows: list[list[str]]) -> list[str]:
    """The ids in a table's body rows, in order; the header row is dropped."""
    return [r[0].strip("`") for r in rows[1:]]


def three_defects(defects: Path, capsys) -> None:
    add_defect(defects, "token race on relaunch")  # DEF-LNCH-1
    add_defect(defects, "splash hang")  # DEF-LNCH-2
    add_defect(defects, "misaligned button")  # DEF-LNCH-3
    capsys.readouterr()


def test_related_and_blockers_are_list_columns(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    relate(defects, "DEF-LNCH-2", "DEF-LNCH-1 - same boot path", "DEF-UI-3")
    capsys.readouterr()
    run("list", str(defects), "--columns", "id,related,blockers", "--status", "all")
    rows = table_rows(capsys.readouterr().out)
    assert "Related" in rows[0] and "Blockers" in rows[0]
    by_id = {r[0]: r for r in rows[1:]}
    assert by_id["`DEF-LNCH-2`"] == ["`DEF-LNCH-2`", "`DEF-LNCH-1`", "`DEF-UI-3`"]
    for rid, row in by_id.items():
        if rid != "`DEF-LNCH-2`":
            assert row[1:] == ["-", "-"]


def test_pivot_puts_an_item_under_every_blocker(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    relate(defects, "DEF-LNCH-2", blocked="DEF-LNCH-1, DEF-UI-3")
    capsys.readouterr()
    run("pivot", str(defects), "--rows", "blockers", "--values", "ids", "--status", "all")
    rows = table_rows(capsys.readouterr().out)
    assert rows[1] == ["`DEF-LNCH-1`", "`DEF-LNCH-2`"]
    assert rows[2] == ["`DEF-UI-3`", "`DEF-LNCH-2`"]
    assert rows[3][0] == "unblocked"
    assert rows[4][0] == "**Total**"


def test_blocked_lists_only_items_behind_an_open_blocker(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    relate(defects, "DEF-LNCH-2", blocked="DEF-LNCH-1-1")
    relate(defects, "DEF-LNCH-1-1", blocked="DEF-LNCH-1")  # closed
    capsys.readouterr()
    run("list", str(defects), "--blocked")
    out = capsys.readouterr().out
    assert ids_of(table_rows(out)) == ["DEF-LNCH-2"]
    assert "(blocked)" in out.split("\n# ")[1].split("\n")[0]
    run("report", str(defects), "--blocked", "--plain")
    assert "1 open / 0 closed / 0 rejected" in capsys.readouterr().out


def test_a_dangling_blocker_does_not_count_as_open(defects: Path, capsys):
    add_defect(defects, "token race")
    relate(defects, "DEF-LNCH-1", blocked="DEF-LNCH-99")
    capsys.readouterr()
    run("list", str(defects), "--blocked")
    assert "0 item(s)" in capsys.readouterr().out


def test_related_to_reads_both_directions_and_both_kinds(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    relate(defects, "DEF-LNCH-2", related="DEF-LNCH-1")
    relate(defects, "DEF-UI-3", blocked="DEF-LNCH-1")
    capsys.readouterr()
    run("list", str(defects), "--related-to", "DEF-LNCH-1", "--status", "all")
    out = capsys.readouterr().out
    assert set(ids_of(table_rows(out))) == {"DEF-LNCH-2", "DEF-UI-3"}
    assert "related to DEF-LNCH-1)" in out
    run("pivot", str(defects), "--rows", "status", "--related-to", "def-lnch-1")
    assert "2 item(s)" in capsys.readouterr().out


def test_a_malformed_related_to_is_refused(defects: Path):
    add_defect(defects, "token race")
    with pytest.raises(SystemExit) as ex:
        run("list", str(defects), "--related-to", "lnch1")
    assert "DEF-LNCH-3" in str(ex.value)


def test_report_detail_prints_the_relation_lines(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash hang")
    relate(defects, "DEF-LNCH-1", "DEF-LNCH-2", "DEF-LNCH-2")
    capsys.readouterr()
    run("report", str(defects), "--detail")
    out = capsys.readouterr().out
    assert "- related: DEF-LNCH-2" in out and "- blocked-by: DEF-LNCH-2" in out


def test_grep_is_a_case_insensitive_regex_over_title_body_evidence_and_log(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("list", str(defects), "--grep", "SEG.?FAULT")
    assert ids_of(table_rows(capsys.readouterr().out)) == ["DEF-LNCH-2"]
    run("list", str(defects), "--grep", "clean on 41\\d", "--status", "all")
    assert ids_of(table_rows(capsys.readouterr().out)) == ["DEF-LNCH-1"]  # evidence
    run("list", str(defects), "--grep", "back on")
    out = capsys.readouterr().out
    assert ids_of(table_rows(out)) == ["DEF-LNCH-1-1"]  # the log event
    assert "(grep /back on/)" in out
    run("list", str(defects), "--grep", "boot twice")
    assert "0 item(s)" in capsys.readouterr().out, "the repro line is not searched"


def test_grep_composes_with_the_other_filters_on_every_query(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("list", str(defects), "--grep", "segfault|misaligned", "--author", "@mb")
    assert ids_of(table_rows(capsys.readouterr().out)) == ["DEF-LNCH-2"]
    run("report", str(defects), "--grep", "segfault", "--plain")
    assert "Interface" not in capsys.readouterr().out, "an emptied category gets no row"
    run("pivot", str(defects), "--rows", "severity", "--grep", "segfault")
    assert "1 item(s)" in capsys.readouterr().out


def test_a_bad_grep_pattern_is_refused(defects: Path):
    add_defect(defects, "token race")
    with pytest.raises(SystemExit) as ex:
        run("list", str(defects), "--grep", "(")
    assert "--grep" in str(ex.value)


def test_search_ranks_a_title_hit_above_a_log_hit(defects: Path, capsys):
    three_defects(defects, capsys)
    run(
        "log",
        str(defects),
        "--id",
        "DEF-LNCH-2",
        "--author",
        "@kj",
        "--event",
        "seen after the token refresh",
    )
    capsys.readouterr()
    assert run("search", str(defects), "token race") == 0
    out = capsys.readouterr().out
    rows = table_rows(out)
    assert rows[0] == ["Rank", "Id", "Score", "Title", "Matched in"]
    assert rows[1][1] == "`DEF-LNCH-1`" and rows[1][4] == "title"
    assert rows[2][1] == "`DEF-LNCH-2`" and rows[2][4] == "log"
    assert "2 of 3 item(s) matched" in out


def test_search_tolerates_a_typo_and_a_stem(defects: Path, capsys):
    three_defects(defects, capsys)
    run("log", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "test added")
    capsys.readouterr()
    for q in ("relunch", "tokens", "testing"):
        run("search", str(defects), q)
        rows = table_rows(capsys.readouterr().out)
        assert rows[1][1] == "`DEF-LNCH-1`", q
    run("search", str(defects), "boo")
    assert "0 of 3 item(s) matched" in capsys.readouterr().out, "under four characters: exact only"


def test_search_finds_an_item_by_its_id_in_any_case(defects: Path, capsys):
    import json

    three_defects(defects, capsys)
    run("search", str(defects), "def-lnch-2")
    rows = table_rows(capsys.readouterr().out)
    assert rows[1][1] == "`DEF-LNCH-2`" and rows[1][4].startswith("id")
    run("search", str(defects), "DEF-LNCH-2", "--json")
    hits = json.loads(capsys.readouterr().out)
    assert hits[0]["rank"] == 1 and hits[0]["id"] == "DEF-LNCH-2"


def test_search_narrows_by_the_filters_before_ranking(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    run("search", str(defects), "token race", "--status", "closed", "--top", "1")
    out = capsys.readouterr().out
    rows = table_rows(out)
    assert len(rows) == 2 and rows[1][1] == "`DEF-LNCH-1`"
    assert "1 of 1 item(s) matched" in out
    run("search", str(defects), "token", "--top", "1")
    assert capsys.readouterr().out.rstrip().endswith("top 1 shown")


def test_search_json_carries_the_same_facts(defects: Path, capsys):
    import json

    three_defects(defects, capsys)
    run("search", str(defects), "token", "--json")
    hits = json.loads(capsys.readouterr().out)
    assert hits, "something matched"
    for h in hits:
        assert set(h) == {"rank", "id", "score", "title", "matched_in", "file", "line"}
        assert h["file"] == str(defects)
    assert [h["rank"] for h in hits] == list(range(1, len(hits) + 1))
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_search_with_nothing_matching_prints_an_empty_table(defects: Path, capsys):
    three_defects(defects, capsys)
    assert run("search", str(defects), "zzzz") == 0
    out = capsys.readouterr().out
    assert len(table_rows(out)) == 1, "the header row alone"
    assert "0 of 3 item(s) matched" in out


def test_search_refuses_an_empty_query_and_an_unquoted_query(defects: Path):
    add_defect(defects, "token race")
    with pytest.raises(SystemExit) as ex:
        run("search", str(defects), "!!!")
    assert "no searchable word" in str(ex.value)
    with pytest.raises(SystemExit) as ex:
        run("search", str(defects), "token", "race")
    assert "token" in str(ex.value) and "one argument" in str(ex.value)


def test_search_ranks_across_both_disciplines_in_one_table(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    d, c = docs / "defects-app.md", docs / "acc-crit-app.md"
    d.write_text(DEFECTS_HEADER, encoding="utf-8")
    c.write_text(ACC_HEADER, encoding="utf-8")
    for f in (d, c):
        run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    add_defect(d, "password field empty")
    add_criterion(c, "Password generation")
    capsys.readouterr()
    run("search", str(docs), "password")
    out = capsys.readouterr().out
    assert out.count("# SEARCH") == 1
    assert {"DEF-LNCH-1", "ACC-AUTH-1"} <= set(r[1].strip("`") for r in table_rows(out)[1:])


def test_refs_lists_both_directions_and_the_blocker_chain(defects: Path, capsys):
    import json

    three_defects(defects, capsys)
    relate(defects, "DEF-LNCH-1", blocked="DEF-LNCH-2")
    relate(defects, "DEF-LNCH-2", blocked="DEF-LNCH-3")
    close_with(defects, "DEF-LNCH-3", "fixed on 412")
    relate(defects, "DEF-LNCH-3", related="DEF-LNCH-1")
    capsys.readouterr()
    assert run("refs", str(defects), "--id", "DEF-LNCH-1") == 0
    out = capsys.readouterr().out
    assert "DEF-LNCH-3 related -> DEF-LNCH-1" in out
    assert "DEF-LNCH-1 blocked-by -> DEF-LNCH-2" in out
    assert "blocked-by chain: DEF-LNCH-2 (open) -> DEF-LNCH-3 (closed)" in out
    assert "1 inbound, 1 outbound reference(s); 1 open blocker(s)" in out
    run("refs", str(defects), "--id", "DEF-LNCH-1", "--json")
    doc = json.loads(capsys.readouterr().out)
    assert doc["inbound"][0]["id"] == "DEF-LNCH-3"
    assert doc["outbound"][0]["id"] == "DEF-LNCH-2"
    assert doc["blockers"] == [
        {"id": "DEF-LNCH-2", "status": "open", "depth": 1},
        {"id": "DEF-LNCH-3", "status": "closed", "depth": 2},
    ]


def test_refs_marks_a_cycle_and_a_missing_blocker_and_stops(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash hang")
    relate(defects, "DEF-LNCH-1", blocked="DEF-LNCH-2")
    relate(defects, "DEF-LNCH-2", blocked="DEF-LNCH-1, DEF-LNCH-99")
    capsys.readouterr()
    assert run("refs", str(defects), "--id", "DEF-LNCH-1") == 0
    out = capsys.readouterr().out
    assert "blocked-by chain: DEF-LNCH-2 (open) -> DEF-LNCH-1 (cycle)" in out
    assert "blocked-by chain: DEF-LNCH-2 (open) -> DEF-LNCH-99 (not found)" in out


def test_refs_on_a_removed_id_still_lists_what_points_at_it(defects: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash hang")
    relate(defects, "DEF-LNCH-1", related="DEF-LNCH-2")
    run("remove", str(defects), "--id", "DEF-LNCH-2", "--force")
    capsys.readouterr()
    assert run("refs", str(defects), "--id", "DEF-LNCH-2") == 0
    out = capsys.readouterr().out
    assert "DEF-LNCH-1 related -> DEF-LNCH-2" in out
    assert "1 inbound, 0 outbound reference(s); 0 open blocker(s)" in out


def test_check_errors_on_a_relation_to_an_unknown_id(defects: Path, capsys):
    add_defect(defects, "token race")
    relate(defects, "DEF-LNCH-1", related="DEF-LNCH-99")
    capsys.readouterr()
    assert run("check", str(defects)) != 0
    assert "ERROR related points at DEF-LNCH-99, not found in the scanned files" in (
        capsys.readouterr().out
    )


def test_check_errors_once_on_a_blocked_by_cycle(defects: Path, tmp_path: Path, capsys):
    add_defect(defects, "token race")
    add_defect(defects, "splash hang")
    relate(defects, "DEF-LNCH-1", blocked="DEF-LNCH-2")
    relate(defects, "DEF-LNCH-2", blocked="DEF-LNCH-1")
    capsys.readouterr()
    assert run("check", str(defects)) != 0
    out = capsys.readouterr().out
    assert out.count("blocked-by cycle") == 1
    assert "blocked-by cycle: DEF-LNCH-1 -> DEF-LNCH-2 -> DEF-LNCH-1" in out

    solo = tmp_path / "defects-solo.md"
    solo.write_text(DEFECTS_HEADER, encoding="utf-8")
    run("author", str(solo), "--handle", "@kj", "--name", "Konrad Jelen")
    add_defect(solo, "token race")
    relate(solo, "DEF-LNCH-1", blocked="DEF-LNCH-1")
    capsys.readouterr()
    assert run("check", str(solo)) != 0
    assert "blocked-by cycle: DEF-LNCH-1 -> DEF-LNCH-1" in capsys.readouterr().out


def test_check_warns_when_an_open_item_is_blocked_by_a_finished_one(defects: Path, capsys):
    three_defects(defects, capsys)
    close_with(defects, "DEF-LNCH-2", "fixed on 412")
    relate(defects, "DEF-LNCH-1", blocked="DEF-LNCH-2")
    capsys.readouterr()
    assert run("check", str(defects)) == 0
    assert "warn  blocked-by DEF-LNCH-2 is closed; the block no longer holds" in (
        capsys.readouterr().out
    )
    assert run("check", str(defects), "--strict") != 0
    capsys.readouterr()
    run(
        "reject",
        str(defects),
        "--id",
        "DEF-LNCH-3",
        "--author",
        "@kj",
        "--event",
        "rejected: wontfix",
    )
    relate(defects, "DEF-LNCH-1", blocked="DEF-LNCH-3")
    capsys.readouterr()
    run("check", str(defects))
    assert (
        "blocked-by DEF-LNCH-3 is rejected; the block no longer holds" in capsys.readouterr().out
    )
    close_with(defects, "DEF-LNCH-1", "fixed on 413")
    capsys.readouterr()
    run("check", str(defects))
    assert "no longer holds" not in capsys.readouterr().out


def test_a_cross_file_blocker_resolves_only_when_the_directory_is_scanned(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    d, c = docs / "defects-app.md", docs / "acc-crit-app.md"
    d.write_text(DEFECTS_HEADER, encoding="utf-8")
    c.write_text(ACC_HEADER, encoding="utf-8")
    for f in (d, c):
        run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    add_defect(d, "token race")
    add_criterion(c, "Password generation")
    relate(c, "ACC-AUTH-1", blocked="DEF-LNCH-1")
    capsys.readouterr()
    assert run("check", str(docs)) == 0
    capsys.readouterr()
    assert run("check", str(c)) != 0
    assert "not found in the scanned files" in capsys.readouterr().out
    run("list", str(docs), "--blocked")
    assert "ACC-AUTH-1" in capsys.readouterr().out


def ladder(f: Path, blocked_by: dict[int, list[int]], n: int, cat: str = "LAD") -> None:
    """Write n open defects straight to disk; item i is blocked by blocked_by[i]."""
    body = [
        DEFECTS_HEADER,
        "\n## Authors\n\n- `@kj` Konrad\n",
        f"\n## Ladder `{cat}`\n\nladder\n\n",
    ]
    for i in range(1, n + 1):
        body.append(
            f"- [ ] `DEF-{cat}-{i}` **step {i}** - MAJOR; step\n  - repro: r\n  - test-tags: unit\n"
        )
        if blocked_by.get(i):
            body.append(
                "  - blocked-by: " + ", ".join(f"DEF-{cat}-{j}" for j in blocked_by[i]) + "\n"
            )
        body.append("  - log: 2026-08-01T10:00:00Z @kj filed\n")
    f.write_text("".join(body), encoding="utf-8")


def test_check_reports_every_cycle_once_on_its_smallest_id(defects: Path, capsys):
    ladder(defects, {1: [2], 2: [1, 3], 3: [2]}, 3)
    assert run("check", str(defects)) != 0
    out = capsys.readouterr().out
    assert "blocked-by cycle: DEF-LAD-1 -> DEF-LAD-2 -> DEF-LAD-1" in out
    assert "blocked-by cycle: DEF-LAD-2 -> DEF-LAD-3 -> DEF-LAD-2" in out
    assert out.count("blocked-by cycle") == 2 and "2 error(s)" in out


def test_check_and_refs_walk_a_dense_graph_and_a_deep_chain(defects: Path, capsys):
    import time

    # every step blocked by two of the five before it: the number of routes to the
    # first step grows exponentially, the number of links does not
    ladder(defects, {i: [i - 1, i - 3] for i in range(4, 81)} | {2: [1], 3: [1, 2]}, 80)
    t = time.perf_counter()
    assert run("check", str(defects)) == 0
    assert run("refs", str(defects), "--id", "DEF-LAD-80") == 0
    assert time.perf_counter() - t < 5
    out = capsys.readouterr().out
    assert "79 open blocker(s)" in out
    assert "(open) -> ..." in out, "a blocker reached twice is expanded once"

    ladder(defects, {i: [i - 1] for i in range(2, 1501)}, 1500)
    assert run("check", str(defects)) == 0
    assert run("refs", str(defects), "--id", "DEF-LAD-1500") == 0
    assert "1499 open blocker(s)" in capsys.readouterr().out


def test_refs_expands_a_shared_blocker_once(defects: Path, capsys):
    ladder(defects, {1: [2, 3], 2: [4], 3: [4], 4: [5]}, 5)
    assert run("refs", str(defects), "--id", "DEF-LAD-1") == 0
    out = capsys.readouterr().out
    assert "blocked-by chain: DEF-LAD-2 (open) -> DEF-LAD-4 (open) -> DEF-LAD-5 (open)" in out
    assert "blocked-by chain: DEF-LAD-3 (open) -> DEF-LAD-4 (open) -> ..." in out
    assert "4 open blocker(s)" in out


def test_check_errors_on_an_id_duplicated_across_files(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    a, b = docs / "defects-a.md", docs / "defects-b.md"
    ladder(a, {}, 1)
    ladder(b, {}, 1)
    assert run("check", str(docs)) != 0
    out = capsys.readouterr().out
    assert re.search(rf"{b}:\d+: ERROR duplicate id DEF-LAD-1 \(first at {a}:\d+\)", out)
    assert run("check", str(a)) == 0


def test_search_takes_its_query_after_an_option_and_never_a_path(defects: Path, capsys):
    three_defects(defects, capsys)
    assert run("search", str(defects), "--top", "1", "splash") == 0
    assert table_rows(capsys.readouterr().out)[1][1] == "`DEF-LNCH-2`"
    assert run("search", str(defects), "--json", "token race") == 0
    assert '"id": "DEF-LNCH-1"' in capsys.readouterr().out
    with pytest.raises(SystemExit) as ex:
        run("search", str(defects), "--top", "1", "splash", "--bogus")
    assert ex.value.code == 2
    with pytest.raises(SystemExit) as ex:
        run("search", str(defects))
    assert "is a path; the last argument is the QUERY" in str(ex.value)


# --- Importance, the criteria grid, coverage and tag casing ----------------


def test_add_refuses_an_unrated_criterion(criteria: Path):
    """Mirrors the defect triage rule: a criterion must say how much it matters."""
    with pytest.raises(SystemExit) as e:
        run(
            "add",
            str(criteria),
            "--category",
            "AUTH",
            "--name",
            "Authentication",
            "--author",
            "@kj",
            "--title",
            "password rules",
            "--text",
            "16 chars",
            "--test",
            "generate 100",
        )
    assert "a criterion must be rated; pass --importance CRITICAL|HIGH|MEDIUM|LOW" in str(e.value)


def test_importance_is_refused_on_a_defect(defects: Path):
    with pytest.raises(SystemExit) as e:
        run(
            "add",
            str(defects),
            "--category",
            "LNCH",
            "--name",
            "Launch",
            "--author",
            "@kj",
            "--importance",
            "HIGH",
            "--title",
            "token race",
            "--text",
            "symptom",
            "--repro",
            "boot cold",
        )
    assert "defects carry no importance" in str(e.value)
    add_defect(defects, "token race")
    with pytest.raises(SystemExit):
        run("edit", str(defects), "--id", "DEF-LNCH-1", "--importance", "HIGH", "--author", "@kj")


def test_edit_sets_the_importance_and_keeps_it_through_a_text_rewrite(criteria: Path):
    add_criterion(criteria, "password rules")
    run("edit", str(criteria), "--id", "ACC-AUTH-1", "--importance", "CRITICAL", "--author", "@kj")
    body = criteria.read_text(encoding="utf-8")
    assert "**password rules** - CRITICAL; 16 chars" in body
    run("edit", str(criteria), "--id", "ACC-AUTH-1", "--text", "20 chars", "--author", "@kj")
    body = criteria.read_text(encoding="utf-8")
    assert "**password rules** - CRITICAL; 20 chars" in body, "a --text rewrite keeps the rating"


def test_check_errors_on_an_unrated_criterion(criteria: Path, capsys):
    add_criterion(criteria, "password rules")
    body = criteria.read_text(encoding="utf-8").replace("HIGH; ", "")
    criteria.write_text(body, encoding="utf-8")
    capsys.readouterr()
    assert run("check", str(criteria)) != 0
    assert "criterion not rated; the body must open with CRITICAL/HIGH/MEDIUM/LOW" in (
        capsys.readouterr().out
    )


def test_the_criteria_grid_counts_open_items_per_importance(criteria: Path, capsys):
    add_criterion(criteria, "password rules", importance="CRITICAL")
    add_criterion(criteria, "session timeout", importance="HIGH")
    add_criterion(criteria, "avatar cache")  # HIGH
    run(
        "close",
        str(criteria),
        "--id",
        "ACC-AUTH-3",
        "--author",
        "@kj",
        "--evidence",
        "unit suite green",
    )
    run("reject", str(criteria), "--id", "ACC-AUTH-2", "--author", "@kj", "--event", "wontfix")
    capsys.readouterr()
    run("report", str(criteria), "--summary")
    out = capsys.readouterr().out
    assert "| Category | Open | Done | Rejected | Total |" in out
    assert "| Authentication `AUTH` | 1 | 1 | 1 | 3 |" in out
    assert "| **Total** | 1 | 1 | 1 | 3 |" in out
    assert "**Open by importance**" in out
    assert "| Category | CRITICAL | HIGH | MEDIUM | LOW | Open |" in out
    assert "| Authentication `AUTH` | 1 | 0 | 0 | 0 | 1 |" in out
    assert "UNRATED" not in out, "every open criterion is rated, so no UNRATED column"


def test_an_open_unrated_criterion_earns_the_unrated_column(criteria: Path, capsys):
    add_criterion(criteria, "password rules", importance="CRITICAL")
    body = criteria.read_text(encoding="utf-8").replace("CRITICAL; ", "")
    criteria.write_text(body, encoding="utf-8")
    capsys.readouterr()
    run("report", str(criteria), "--summary")
    out = capsys.readouterr().out
    assert "| Category | CRITICAL | HIGH | MEDIUM | LOW | UNRATED | Open |" in out
    assert "| Authentication `AUTH` | 0 | 0 | 0 | 0 | 1 | 1 |" in out


def test_report_items_carries_an_importance_column_for_criteria(criteria: Path, capsys):
    add_criterion(criteria, "password rules", importance="MEDIUM")
    capsys.readouterr()
    run("report", str(criteria))
    out = capsys.readouterr().out
    assert "| Id | Title | Description | Importance | Tests |" in out
    assert "| MEDIUM |" in out


def test_importance_filters_and_fields_mirror_severity(criteria: Path, defects: Path, capsys):
    add_criterion(criteria, "password rules", importance="CRITICAL")
    add_criterion(criteria, "session timeout", importance="LOW")
    capsys.readouterr()
    run("report", str(criteria), "--importance", "CRITICAL")
    out = capsys.readouterr().out
    assert "password rules" in out and "session timeout" not in out
    assert "(CRITICAL)" in out, "the filter is named in the title"
    run("list", str(criteria), "--columns", "id,importance", "--sort=importance")
    rows = table_rows(capsys.readouterr().out)
    assert rows[0] == ["Id", "Importance"]
    assert [r[1] for r in rows[1:]] == ["CRITICAL", "LOW"], "worst first"
    run("pivot", str(criteria), "--rows", "importance")
    rows = table_rows(capsys.readouterr().out)
    assert [r[0] for r in rows[1:]] == ["CRITICAL", "LOW", "**Total**"]
    add_defect(defects, "token race")
    capsys.readouterr()
    run("report", str(defects), "--importance", "CRITICAL")
    cap = capsys.readouterr()
    assert "skipped, --importance is a criterion attribute" in cap.err
    assert "SUMMARY" not in cap.out


def test_a_criterion_opening_with_a_level_word_is_prose_not_a_severity(tmp_path: Path, capsys):
    """The standing defect: parse() read `Normal, ...` on a criterion as a severity.
    Severity is gated on DEF items now, so the body survives every command intact."""
    f = tmp_path / "acc-crit-app.md"
    f.write_text(
        "# Acceptance Criteria - App\n\n## Authors\n\n- `@kj` Konrad Jelen\n\n"
        "## Banner `BNR`\n\nBanner rendering\n\n"
        "- [ ] `ACC-BNR-1` **modes** - Normal, degraded and offline modes render the banner\n"
        "  - test: render all three\n"
        "  - log: 2026-01-02T00:00:00Z @kj filed\n",
        encoding="utf-8",
    )
    run("list", str(f), "--columns", "id,severity,importance,body")
    rows = table_rows(capsys.readouterr().out)
    assert rows[1][1] == "-", "no severity is read off a criterion"
    assert rows[1][2] == "-", "Normal is not an importance word either"
    assert rows[1][3].startswith("Normal, degraded"), "the body keeps its first word"
    run("report", str(f))
    assert "Normal, degraded and offline modes render the banner" in capsys.readouterr().out
    run(
        "edit",
        str(f),
        "--id",
        "ACC-BNR-1",
        "--text",
        "Normal, degraded and offline modes render",
        "--author",
        "@kj",
    )
    body = f.read_text(encoding="utf-8")
    assert "- [ ] `ACC-BNR-1` **modes** - Normal, degraded and offline modes render\n" in body, (
        "edit --text neither strips the word nor prepends a level"
    )


def test_tags_are_written_upper_case_and_filtered_in_any_case(defects: Path, capsys):
    add_defect(defects, "token race")  # --test-tags integration
    assert "- test-tags: INTEGRATION" in defects.read_text(encoding="utf-8")
    run(
        "edit",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--test-tags",
        "unit, Functional",
        "--author",
        "@kj",
    )
    assert "- test-tags: UNIT, FUNCTIONAL" in defects.read_text(encoding="utf-8")
    capsys.readouterr()
    run("list", str(defects), "--tag", "functional")
    out = capsys.readouterr().out
    assert "`DEF-LNCH-1`" in out and "(tag FUNCTIONAL)" in out, "--tag reads in any case"


def test_a_legacy_lower_case_tag_line_still_parses(defects: Path, capsys):
    add_defect(defects, "token race")
    body = defects.read_text(encoding="utf-8").replace("INTEGRATION", "integration")
    defects.write_text(body, encoding="utf-8")
    capsys.readouterr()
    run("list", str(defects), "--tag", "INTEGRATION", "--columns", "id,tags")
    rows = table_rows(capsys.readouterr().out)
    assert rows[1] == ["`DEF-LNCH-1`", "INTEGRATION"], "read in any case, printed upper-case"


def test_coverage_is_a_grid_of_categories_by_tags_with_no_test_last(
    criteria: Path, defects: Path, capsys
):
    add_criterion(criteria, "password rules", importance="CRITICAL")  # unit
    add_criterion(criteria, "session timeout", category="SESS")  # unit
    run(
        "edit",
        str(criteria),
        "--id",
        "ACC-SESS-2",
        "--test-tags",
        "smoke",
        "--author",
        "@kj",
    )
    add_criterion(criteria, "avatar cache")  # unit, then untagged below
    body = criteria.read_text(encoding="utf-8")
    at = body.rindex("  - test-tags: UNIT\n")
    criteria.write_text(body[:at] + body[at + len("  - test-tags: UNIT\n") :], encoding="utf-8")
    run(
        "close",
        str(criteria),
        "--id",
        "ACC-AUTH-1",
        "--author",
        "@kj",
        "--evidence",
        "unit suite green",
    )
    capsys.readouterr()
    assert run("coverage", str(criteria)) == 0
    out = capsys.readouterr().out
    assert "# TEST COVERAGE" in out
    rows = table_rows(out)
    assert rows[0] == ["Category", "UNIT", "SMOKE", "NO-TEST"], (
        "canonical tags first, free tags next, NO-TEST last"
    )
    assert rows[1] == ["Authentication `AUTH`", "1", "0", "1"], "closed items count too"
    assert rows[2] == ["Authentication `SESS`", "0", "1", "0"]
    assert rows[3] == ["**Total**", "1", "1", "1"]
    add_defect(defects, "token race")
    capsys.readouterr()
    run("coverage", str(defects), "--json")
    import json

    (doc,) = json.loads(capsys.readouterr().out)
    assert doc["columns"] == ["INTEGRATION"]
    assert doc["rows"][0]["cells"] == {"INTEGRATION": 1}
    assert doc["total"] == {"cells": {"INTEGRATION": 1}, "items": 1}


def test_coverage_excludes_rejected_items_and_takes_the_shared_filters(criteria: Path, capsys):
    add_criterion(criteria, "password rules", importance="CRITICAL")
    add_criterion(criteria, "session timeout")
    run("reject", str(criteria), "--id", "ACC-AUTH-2", "--author", "@kj", "--event", "wontfix")
    capsys.readouterr()
    run("coverage", str(criteria))
    out = capsys.readouterr().out
    assert "1 item(s)" in out, "a rejected item needs no test"
    run("coverage", str(criteria), "--importance", "LOW")
    out = capsys.readouterr().out
    assert "0 item(s)" in out and "(LOW)" in out, "the shared filters narrow the grid"


def test_report_no_longer_prints_test_coverage(criteria: Path, capsys):
    add_criterion(criteria, "password rules")
    capsys.readouterr()
    run("report", str(criteria))
    assert "TEST COVERAGE" not in capsys.readouterr().out


def test_upgrade_applies_the_safe_rewrites_and_hints_the_rest(tmp_path: Path, capsys):
    """No content problem refuses --apply: ids land, tags upper-case, and every
    problem prints as a HINT carrying the command that fixes it. Exit 0."""
    f = tmp_path / "acc-crit-legacy.md"
    f.write_text(
        "# Acceptance Criteria - Legacy\n\n## Authentication\n\nLogin\n\n"
        "- [ ] **Password generation** - 16 chars\n"
        "  - test-tags: unit, e2e\n"
        "  - 2026-06-12 drafted\n",
        encoding="utf-8",
    )
    assert run("upgrade", str(f), "--apply") == 0, "content problems never refuse --apply"
    cap = capsys.readouterr()
    body = f.read_text(encoding="utf-8")
    assert "`ACC-AUTH-1`" in body, "the id landed"
    assert "- test-tags: UNIT, E2E" in body, "tags upper-cased"
    assert "- log: 2026-06-12T00:00:00Z drafted" in body, "the dated note became a log line"
    assert "hint(s) remain. Run check next" in cap.out
    hints = [ln for ln in cap.err.splitlines() if ln.startswith("HINT ")]
    assert any("no ## Authors roster" in h and f"pm-tools author {f}" in h for h in hints), (
        "the roster hint carries the exact command"
    )
    assert any(
        f"pm-tools edit {f} --id ACC-AUTH-1 --importance CRITICAL|HIGH|MEDIUM|LOW" in h
        for h in hints
    ), "one ready edit command per unrated criterion"
    assert any("--id ACC-AUTH-1 --test" in h for h in hints), "the missing hint line is hinted"


def test_upgrade_with_an_unknown_author_hints_instead_of_refusing(tmp_path: Path, capsys):
    f = tmp_path / "defects-legacy.md"
    f.write_text(
        "# Defects - Legacy\n\n## Launch\n\nCold start\n\n"
        "- [ ] **token race** - MAJOR; symptom\n"
        "  - log: 2026-06-12T00:00:00Z filed\n",
        encoding="utf-8",
    )
    assert run("upgrade", str(f), "--author", "@kj", "--apply") == 0
    cap = capsys.readouterr()
    assert "`DEF-LAUNCH-1`" in f.read_text(encoding="utf-8"), "the rewrite still applied"
    assert "@kj filed" not in f.read_text(encoding="utf-8"), "an unknown handle signs nothing"
    assert "@kj is not on the ## Authors roster" in cap.err
    assert f"pm-tools author {f} --handle @kj" in cap.err
    assert f"pm-tools upgrade {f} --author @kj --apply" in cap.err, "the re-run command is ready"


def test_case_duplicated_tags_collapse_to_one_on_write_and_on_read(defects: Path, capsys):
    """The spec's named attack: an item tagged twice with different cases is one
    tag - edit writes it once, and a hand-edited duplicate reads as one, so
    coverage, pivot and the report never double-count."""
    add_defect(defects, "token race")
    run(
        "edit",
        str(defects),
        "--id",
        "DEF-LNCH-1",
        "--test-tags",
        "unit, UNIT, Unit",
        "--author",
        "@kj",
    )
    body = defects.read_text(encoding="utf-8")
    assert "- test-tags: UNIT\n" in body, "the written line carries the tag once"
    assert "UNIT, UNIT" not in body
    # the read path protects a hand-edited file the tool never touched
    defects.write_text(body.replace("- test-tags: UNIT", "- test-tags: unit, UNIT"))
    capsys.readouterr()
    run("coverage", str(defects))
    out = capsys.readouterr().out
    row = next(ln for ln in out.splitlines() if ln.startswith("| Launch"))
    assert row.split("|")[2].strip() == "1", "one item counts once in the UNIT column"


def test_upgrade_first_run_hints_the_unsigned_history_behind_dated_notes(tmp_path: Path, capsys):
    """Dated notes become log lines in the same rewrite; the no-@handle hint must
    count them on the FIRST run, not arrive one run late."""
    f = tmp_path / "acc-crit-legacy.md"
    f.write_text(
        "# Acceptance Criteria - Legacy\n\n## Authentication\n\nLogin\n\n"
        "- [ ] **Password generation** - 16 chars\n"
        "  - 2026-06-12 drafted\n",
        encoding="utf-8",
    )
    assert run("upgrade", str(f)) == 0
    cap = capsys.readouterr()
    assert "1 log line(s) carry no @handle" in cap.err, "the hint fires on the first dry run"
    # and the first --apply with an on-roster author announces the signing it does
    run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    capsys.readouterr()
    assert run("upgrade", str(f), "--author", "@kj", "--apply") == 0
    cap = capsys.readouterr()
    assert "1 unauthored log line(s) signed @kj" in cap.out
    assert "- log: 2026-06-12T00:00:00Z @kj drafted" in f.read_text(encoding="utf-8")


def test_upgrade_nested_item_hint_command_is_accepted_by_add(tmp_path: Path, capsys):
    """Change 5's bar: every hint carries the exact command to run. The nested-item
    hint must include the discipline's mandatory level flag, and the command it
    prints must be accepted by add."""
    f = tmp_path / "defects-legacy.md"
    f.write_text(
        "# Defects - Legacy\n\n## Launch\n\nCold start\n\n"
        "- [ ] **token race** - MAJOR; symptom\n"
        "  - [ ] nested sub-item\n",
        encoding="utf-8",
    )
    run("author", str(f), "--handle", "@kj", "--name", "Konrad Jelen")
    capsys.readouterr()
    assert run("upgrade", str(f), "--author", "@kj", "--apply") == 0
    cap = capsys.readouterr()
    (hint,) = [ln for ln in cap.err.splitlines() if "nested checklist item" in ln]
    assert "--severity CRITICAL|MAJOR|MEDIUM|MINOR" in hint, "the mandatory flag is in the hint"
    assert (
        run(
            "add",
            str(f),
            "--category",
            "LNCH",
            "--name",
            "Launch",
            "--title",
            "nested sub-item",
            "--text",
            "filed from the nested line",
            "--severity",
            "MAJOR",
            "--author",
            "@kj",
        )
        == 0
    ), "the hinted command shape is accepted"
    # the criteria discipline symmetrically hints its own mandatory flag
    g = tmp_path / "acc-crit-legacy.md"
    g.write_text(
        "# Acceptance Criteria - Legacy\n\n## Authentication\n\nLogin\n\n"
        "- [ ] **Password generation** - 16 chars\n"
        "  - [ ] nested sub-item\n",
        encoding="utf-8",
    )
    capsys.readouterr()
    assert run("upgrade", str(g)) == 0
    (hint,) = [ln for ln in capsys.readouterr().err.splitlines() if "nested checklist item" in ln]
    assert "--importance CRITICAL|HIGH|MEDIUM|LOW" in hint


# --- Soft lock (ACC-PMLOCK-64..71) ------------------------------------------


def stamp(hours: float) -> str:
    """An ISO 8601 UTC stamp `hours` from now; negative is the past."""
    import datetime as dt

    at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=hours)
    return at.strftime("%Y-%m-%dT%H:%M:%SZ")


def lock_lines(f: Path) -> list[str]:
    return [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if "- lock:" in ln]


def log_lines(f: Path) -> list[str]:
    return [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if "- log:" in ln]


def two_authors_two_defects(defects: Path, capsys) -> None:
    run("author", str(defects), "--handle", "@xy", "--name", "X Y")
    add_defect(defects, "token race")  # DEF-LNCH-1
    add_defect(defects, "splash hang")  # DEF-LNCH-2
    capsys.readouterr()


def test_lock_writes_one_line_24h_ahead_before_the_log_and_never_logs(defects: Path, capsys):
    """ACC-PMLOCK-64. Fails without the change on `run("lock", ...)`: argparse knows no
    such command and raises SystemExit(2)."""
    two_authors_two_defects(defects, capsys)
    assert (
        run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--note", "bisect") == 0
    )
    (line,) = lock_lines(defects)
    m = re.fullmatch(r"- lock: (\S+) @kj bisect", line)
    assert m, line
    assert stamp(23.99) <= m.group(1) <= stamp(24.01), "24 hours from now by default"
    body = defects.read_text(encoding="utf-8")
    assert body.index("- lock:") < body.index("- log:"), "the lock sits before the history"
    assert body.index("- test-tags:") < body.index("- lock:"), "and after the other sub-lines"
    assert len(log_lines(defects)) == 2, "locking is never logged"
    assert capsys.readouterr().err == "", "own lock, fresh item: nothing to warn about"


def test_lock_hours_and_until_are_honoured_and_a_relock_extends(defects: Path, capsys):
    """ACC-PMLOCK-64. The `len(lock_lines) == 1` after the relock is the assertion that
    pins replace-not-append."""
    two_authors_two_defects(defects, capsys)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--hours", "2")
    (line,) = lock_lines(defects)
    assert stamp(1.99) <= line.split()[2] <= stamp(2.01)
    later = stamp(72)
    assert (
        run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--until", later) == 0
    )
    assert lock_lines(defects) == [f"- lock: {later} @kj"], "the same author replaces the line"
    assert capsys.readouterr().err == "", "extending your own lock is silent"
    with pytest.raises(SystemExit):
        run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--until", "2026-09-01")
    with pytest.raises(SystemExit):
        run(
            "lock",
            str(defects),
            "--id",
            "DEF-LNCH-1",
            "--author",
            "@kj",
            "--hours",
            "1",
            "--until",
            later,
        )


def test_locking_over_another_authors_lock_warns_and_replaces(defects: Path, capsys):
    """ACC-PMLOCK-64, the warning now worded as the transfer it is (ACC-PMLOCK-71)."""
    two_authors_two_defects(defects, capsys)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    until = lock_lines(defects)[0].split()[2]
    capsys.readouterr()
    assert run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy") == 0
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and f"locked by @kj until {until}" in err
    assert "you are taking it over; ask @kj" in err
    (line,) = lock_lines(defects)
    assert line.endswith(" @xy taken over from @kj"), "warned, then replaced anyway"


def test_lock_refuses_a_closed_or_rejected_item(defects: Path, capsys):
    """ACC-PMLOCK-64 - the one refusal in the feature."""
    two_authors_two_defects(defects, capsys)
    run("close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--evidence", "green")
    run("reject", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "no repro")
    for rid, st in (("DEF-LNCH-1", "closed"), ("DEF-LNCH-2", "rejected")):
        with pytest.raises(SystemExit) as ex:
            run("lock", str(defects), "--id", rid, "--author", "@kj")
        assert st in str(ex.value)
    assert lock_lines(defects) == []


def test_a_foreign_lock_warns_once_and_every_write_lands_unchanged(defects: Path, capsys):
    """ACC-PMLOCK-65. Without the change `log` by @kj on @xy's lock prints nothing to
    stderr, so the `"locked by @xy"` assertion fails."""
    two_authors_two_defects(defects, capsys)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy")
    until = lock_lines(defects)[0].split()[2]
    capsys.readouterr()
    writes = [
        ["log", "--author", "@kj", "--event", "attempted: retry - did NOT work"],
        ["edit", "--author", "@kj", "--title", "token race on relaunch"],
        ["relate", "--author", "@kj", "--related", "DEF-LNCH-2 - same boot path"],
    ]
    for argv in writes:
        assert run(argv[0], str(defects), "--id", "DEF-LNCH-1", *argv[1:]) == 0
        err = capsys.readouterr().err
        assert err.count("\n") == 1, f"{argv[0]}: exactly one warning line"
        assert f"DEF-LNCH-1 locked by @xy until {until}" in err
    body = defects.read_text(encoding="utf-8")
    assert "@kj attempted: retry - did NOT work" in body
    assert "**token race on relaunch**" in body
    assert "- related: DEF-LNCH-2 - same boot path" in body
    assert lock_lines(defects) == [f"- lock: {until} @xy"], "the lock itself is untouched"
    # the holder writes in silence
    assert (
        run("log", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy", "--event", "mine") == 0
    )
    assert capsys.readouterr().err == ""
    # an unlocked item writes in silence too - the warning is the only difference
    assert run("log", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "x") == 0
    assert capsys.readouterr().err == ""


def test_close_reject_reopen_and_remove_warn_and_proceed_on_a_foreign_lock(defects: Path, capsys):
    """ACC-PMLOCK-65 and 66: close and reject also clear the lock they find, whatever
    its expiry. Without the change close leaves the lock line in place."""
    two_authors_two_defects(defects, capsys)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy", "--hours", "100")
    run("lock", str(defects), "--id", "DEF-LNCH-2", "--author", "@xy", "--hours", "100")
    capsys.readouterr()
    assert (
        run("close", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--evidence", "ok")
        == 0
    )
    assert "locked by @xy" in capsys.readouterr().err
    assert (
        run("reject", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "dup") == 0
    )
    assert "locked by @xy" in capsys.readouterr().err
    body = defects.read_text(encoding="utf-8")
    assert "- [x] `DEF-LNCH-1`" in body and "- [-] `DEF-LNCH-2`" in body
    assert lock_lines(defects) == [], "close and reject clear the lock, active or not"
    assert not any("lock" in ln for ln in log_lines(defects)), "clearing is not logged"
    # reopen, then remove, on a fresh foreign lock
    run("reopen", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj")
    run("lock", str(defects), "--id", "DEF-LNCH-2", "--author", "@xy")
    capsys.readouterr()
    # reopen on an already-open item still runs the shared warn, and leaves the lock
    assert run("reopen", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj") == 0
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "DEF-LNCH-2 locked by @xy" in err
    assert len(lock_lines(defects)) == 1, "only close and reject clear the lock"
    assert run("remove", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj") == 0
    assert "DEF-LNCH-2 locked by @xy" in capsys.readouterr().err
    assert "DEF-LNCH-2" not in defects.read_text(encoding="utf-8")


def test_an_expired_lock_is_cleared_by_the_next_write_silently(defects: Path, capsys):
    """ACC-PMLOCK-66. A past-dated --until makes the expired lock without sleeping.
    Without the change the lock line survives the `log` and `lock_lines == []` fails."""
    two_authors_two_defects(defects, capsys)
    past = stamp(-1)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy", "--until", past)
    assert lock_lines(defects) == [f"- lock: {past} @xy"], "lock itself writes what it is told"
    capsys.readouterr()
    # reads leave it in place; check names it
    run("list", str(defects))
    assert lock_lines(defects) == [f"- lock: {past} @xy"]
    assert run("check", str(defects)) == 0
    assert "expired lock, cleared on the next write" in capsys.readouterr().out
    assert lock_lines(defects) == [f"- lock: {past} @xy"], "check is read-only"
    # a write on ANOTHER item sweeps it, with no warning and no log line
    before = len(log_lines(defects))
    assert run("log", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "x") == 0
    assert capsys.readouterr().err == ""
    assert lock_lines(defects) == []
    assert len(log_lines(defects)) == before + 1, "only the event itself was logged"


def test_check_errors_on_a_malformed_or_duplicate_lock_and_warns_on_a_finished_item(
    defects: Path, capsys
):
    """ACC-PMLOCK-66. Without the change check ignores lock lines and exits 0."""
    two_authors_two_defects(defects, capsys)
    run("close", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj", "--evidence", "ok")
    body = defects.read_text(encoding="utf-8")
    future = stamp(5)
    body = body.replace(
        "  - log: ",
        f"  - lock: {future} @kj\n  - lock: 2026-13-01T00:00:00Z @kj\n  - lock: {future} nobody\n  - log: ",
        1,
    )
    # a hand-written lock on the closed item
    at = body.index("- [x] `DEF-LNCH-2`")
    at = body.index("  - log: ", at)
    body = body[:at] + f"  - lock: {future} @xy\n" + body[at:]
    defects.write_text(body, encoding="utf-8")
    capsys.readouterr()
    assert run("check", str(defects)) == 1
    out = capsys.readouterr().out
    assert "ERROR more than one lock: line; keep exactly one" in out
    assert out.count("ERROR lock: line is malformed") == 1, "one item, one malformed report"
    assert "warn  lock on a closed item" in out
    assert defects.read_text(encoding="utf-8") == body, "check never removes anything"


def test_unlock_clears_one_every_or_only_the_expired_locks(defects: Path, capsys):
    """ACC-PMLOCK-67. Without the change `run("unlock", ...)` raises SystemExit(2)."""
    two_authors_two_defects(defects, capsys)
    add_defect(defects, "misaligned button")  # DEF-LNCH-3
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    run("lock", str(defects), "--id", "DEF-LNCH-2", "--author", "@xy")
    run("lock", str(defects), "--id", "DEF-LNCH-3", "--author", "@xy", "--until", stamp(-2))
    logs = len(log_lines(defects))
    capsys.readouterr()
    with pytest.raises(SystemExit):
        run("unlock", str(defects), "--author", "@kj")
    with pytest.raises(SystemExit):
        run("unlock", str(defects), "--author", "@kj", "--all", "--expired")
    assert run("unlock", str(defects), "--author", "@kj", "--expired") == 0
    assert capsys.readouterr().err == ""
    assert [ln.split()[3] for ln in lock_lines(defects)] == ["@kj", "@xy"]
    assert run("unlock", str(defects), "--author", "@kj", "--id", "DEF-LNCH-1") == 0
    assert capsys.readouterr().err == "", "your own lock goes quietly"
    assert [ln.split()[3] for ln in lock_lines(defects)] == ["@xy"]
    assert run("unlock", str(defects), "--author", "@kj", "--all") == 0
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "DEF-LNCH-2 was locked by @xy" in err, (
        "warned once, cleared anyway"
    )
    assert lock_lines(defects) == []
    assert len(log_lines(defects)) == logs, "unlock never logs"


def test_lock_is_a_field_and_an_expired_one_reads_as_a_dash(defects: Path, capsys):
    """ACC-PMLOCK-68. Without the change parse_fields refuses `lock` as an unknown
    field and raises SystemExit."""
    two_authors_two_defects(defects, capsys)
    add_defect(defects, "misaligned button")  # DEF-LNCH-3
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--hours", "48")
    run("lock", str(defects), "--id", "DEF-LNCH-2", "--author", "@xy", "--hours", "1")
    run("lock", str(defects), "--id", "DEF-LNCH-3", "--author", "@xy", "--until", stamp(-1))
    kj = lock_lines(defects)[0].split()[2]
    xy = lock_lines(defects)[1].split()[2]
    capsys.readouterr()
    assert run("list", str(defects), "--columns", "id,lock", "--sort=lock") == 0
    rows = table_rows(capsys.readouterr().out)
    assert rows[0] == ["Id", "Lock"]
    assert rows[1:] == [
        ["`DEF-LNCH-2`", f"@xy until {xy}"],
        ["`DEF-LNCH-1`", f"@kj until {kj}"],
        ["`DEF-LNCH-3`", "-"],
    ], "soonest expiry first, the expired lock is no lock"
    run("pivot", str(defects), "--rows", "lock", "--cols", "status")
    rows = table_rows(capsys.readouterr().out)
    assert [r[0] for r in rows[1:]] == [f"@kj until {kj}", f"@xy until {xy}", "-", "**Total**"]
    run("pivot", str(defects), "--rows", "author", "--cols", "lock")
    assert f"@xy until {xy}" in table_rows(capsys.readouterr().out)[0]


def test_locked_and_locked_by_narrow_every_query(defects: Path, capsys):
    """ACC-PMLOCK-68. Without the change argparse rejects --locked with exit 2."""
    two_authors_two_defects(defects, capsys)
    add_defect(defects, "misaligned button")  # DEF-LNCH-3
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    run("lock", str(defects), "--id", "DEF-LNCH-2", "--author", "@xy")
    run("lock", str(defects), "--id", "DEF-LNCH-3", "--author", "@xy", "--until", stamp(-1))
    capsys.readouterr()
    run("list", str(defects), "--locked")
    out = capsys.readouterr().out
    assert ids_of(table_rows(out)) == ["DEF-LNCH-1", "DEF-LNCH-2"], "expired is not active"
    assert "(locked)" in out
    run("list", str(defects), "--locked-by", "@xy")
    out = capsys.readouterr().out
    assert ids_of(table_rows(out)) == ["DEF-LNCH-2"] and "(locked by @xy)" in out
    run("report", str(defects), "--locked-by", "@kj", "--plain")
    assert "1 open / 0 closed / 0 rejected" in capsys.readouterr().out
    run("pivot", str(defects), "--rows", "severity", "--locked")
    assert "2 item(s)" in capsys.readouterr().out
    run("coverage", str(defects), "--locked-by", "@kj")
    assert "1 item(s)" in capsys.readouterr().out
    run("search", str(defects), "race", "--locked-by", "@xy")
    assert "0 of 1 item(s) matched" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        run("list", str(defects), "--locked-by", "xy")


def test_report_marks_wip_rows_and_counts_them_in_a_worked_on_column(defects: Path, capsys):
    """ACC-PMLOCK-68. Without the change the ITEMS row carries no `wip` cell and the
    `"Worked on"` header assertion fails."""
    two_authors_two_defects(defects, capsys)
    add_defect(defects, "misaligned button", category="UI")  # DEF-UI-3
    run("report", str(defects), "--plain")
    out = capsys.readouterr().out
    assert "Worked on" not in out and "Lock" not in out, "no lock, no column - like UNTRIAGED"
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    run("lock", str(defects), "--id", "DEF-UI-3", "--author", "@xy", "--until", stamp(-1))
    until = lock_lines(defects)[0].split()[2]
    capsys.readouterr()
    run("report", str(defects), "--plain")
    out = capsys.readouterr().out
    assert "| Category | Open | Worked on | Fixed | Rejected | Total |" in out
    assert "| Launch `LNCH` | 2 | 1 | 0 | 0 | 2 |" in out
    assert "| Launch `UI` | 1 | 0 | 0 | 0 | 1 |" in out, "an expired lock counts nothing"
    assert "| **Total** | 3 | 1 | 0 | 0 | 3 |" in out
    rows = table_rows(out)
    assert rows[-1][0] == "`DEF-UI-3`" and rows[-1][-1] == "-"
    (wip,) = [r for r in rows if r[0] == "`DEF-LNCH-1`"]
    assert wip[-1] == f"wip @kj until {until}"
    (other,) = [r for r in rows if r[0] == "`DEF-LNCH-2`"]
    assert other[-1] == "-"
    run("report", str(defects), "--detail", "--category", "LNCH")
    assert f"- lock: {until} @kj" in capsys.readouterr().out, "detail prints the sub-line"


def test_json_carries_the_lock_as_a_record_or_null(defects: Path, capsys):
    """ACC-PMLOCK-68. Without the change the record has no `lock` key (KeyError)."""
    import json

    two_authors_two_defects(defects, capsys)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--note", "bisecting")
    run("lock", str(defects), "--id", "DEF-LNCH-2", "--author", "@xy", "--until", stamp(-1))
    until = lock_lines(defects)[0].split()[2]
    capsys.readouterr()
    run("list", str(defects), "--json")
    recs = {r["id"]: r for r in json.loads(capsys.readouterr().out)}
    assert recs["DEF-LNCH-1"]["lock"] == {"by": "@kj", "until": until, "note": "bisecting"}
    assert recs["DEF-LNCH-2"]["lock"] is None, "expired is null"
    run("report", str(defects), "--json")
    (doc,) = json.loads(capsys.readouterr().out)
    assert doc["summary"]["rows"][0]["worked_on"] == 1
    assert doc["summary"]["total"]["worked_on"] == 1
    assert doc["items"][0]["lock"]["by"] == "@kj"


def test_upgrade_leaves_lock_lines_untouched(defects: Path, capsys):
    """ACC-PMLOCK-66 corollary: upgrade is not a lock sweep."""
    two_authors_two_defects(defects, capsys)
    past = stamp(-1)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--until", past)
    assert run("upgrade", str(defects), "--apply") == 0
    assert lock_lines(defects) == [f"- lock: {past} @kj"]


def test_a_read_announces_the_items_someone_is_working_on(defects: Path, capsys):
    """ACC-PMLOCK-70. Without the change no read writes anything to stderr, so every
    notice assertion below fails on an empty string."""
    two_authors_two_defects(defects, capsys)
    add_defect(defects, "misaligned button")  # DEF-LNCH-3
    relate(defects, "DEF-LNCH-3", related="DEF-LNCH-1 - same boot path")
    run("list", str(defects))
    assert capsys.readouterr().err == "", "nothing locked, nothing announced"
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy", "--note", "bisecting")
    until = lock_lines(defects)[0].split()[2]
    capsys.readouterr()
    notice = f"1 item(s) currently worked on: DEF-LNCH-1 by @xy until {until}\n"
    reads = [
        ["report", str(defects)],
        ["list", str(defects)],
        ["search", str(defects), "token"],
        ["refs", str(defects), "--id", "DEF-LNCH-3"],  # reached through the link
    ]
    for argv in reads:
        assert run(*argv) == 0
        assert capsys.readouterr().err == notice, argv[0]
        assert run(*argv, "--json") == 0
        assert capsys.readouterr().err == "", f"{argv[0]} --json is data, not a notice"
    # the notice is about what the read shows, not what the file holds
    run("list", str(defects), "--grep", "misaligned")
    assert capsys.readouterr().err == "", "the locked item is out of scope"
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy", "--until", stamp(-1))
    capsys.readouterr()
    run("report", str(defects))
    assert capsys.readouterr().err == "", "an expired lock is nobody working on anything"


def test_the_pick_up_notice_names_ten_items_at_most(defects: Path, capsys):
    """ACC-PMLOCK-70. Without the change stderr stays empty and the first assertion
    fails."""
    two_authors_two_defects(defects, capsys)
    for i in range(3, 15):
        add_defect(defects, f"defect {i}")
    for i in range(1, 13):
        run("lock", str(defects), "--id", f"DEF-LNCH-{i}", "--author", "@xy")
    capsys.readouterr()
    run("list", str(defects))
    err = capsys.readouterr().err
    assert err.startswith("12 item(s) currently worked on: DEF-LNCH-1 by @xy until ")
    assert err.count("DEF-LNCH-") == 10, "ten ids at most"
    assert err.rstrip().endswith(", +2 more") and "DEF-LNCH-11" not in err


def test_taking_another_authors_lock_over_is_named_a_transfer(defects: Path, capsys):
    """ACC-PMLOCK-71. Without the change the ordinary warning prints and the new lock
    line carries no note, so the `TRANSFER:` and `taken over from` assertions fail."""
    two_authors_two_defects(defects, capsys)
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj")
    until = lock_lines(defects)[0].split()[2]
    capsys.readouterr()
    assert run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy") == 0, "never refused"
    assert capsys.readouterr().err == (
        f"TRANSFER: DEF-LNCH-1 was locked by @kj until {until} - you are taking it over; ask @kj\n"
    )
    (line,) = lock_lines(defects)
    assert line.endswith(" @xy taken over from @kj"), "the previous holder stays on the item"
    assert len(log_lines(defects)) == 2, "a transfer is not an event either"
    # an explicit note wins over the default
    until = line.split()[2]
    assert (
        run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@kj", "--note", "mine now")
        == 0
    )
    assert f"TRANSFER: DEF-LNCH-1 was locked by @xy until {until}" in capsys.readouterr().err
    assert lock_lines(defects)[0].endswith(" @kj mine now")


def test_clearing_another_authors_lock_is_named_a_transfer(defects: Path, capsys):
    """ACC-PMLOCK-71. Without the change unlock prints the ordinary warning, so the
    `TRANSFER:` assertion fails."""
    two_authors_two_defects(defects, capsys)
    add_defect(defects, "misaligned button")  # DEF-LNCH-3
    run("lock", str(defects), "--id", "DEF-LNCH-1", "--author", "@xy")
    run("lock", str(defects), "--id", "DEF-LNCH-2", "--author", "@kj")
    run("lock", str(defects), "--id", "DEF-LNCH-3", "--author", "@xy")
    one, _, three = (ln.split()[2] for ln in lock_lines(defects))
    capsys.readouterr()
    assert run("unlock", str(defects), "--author", "@kj", "--id", "DEF-LNCH-1") == 0
    assert capsys.readouterr().err == (
        f"TRANSFER: DEF-LNCH-1 was locked by @xy until {one} - you are clearing it; ask @xy\n"
    )
    assert run("unlock", str(defects), "--author", "@kj", "--all") == 0
    err = capsys.readouterr().err
    assert err.count("\n") == 1, "one line per foreign active lock, none for your own"
    assert f"TRANSFER: DEF-LNCH-3 was locked by @xy until {three} - you are clearing it" in err
    assert lock_lines(defects) == []
