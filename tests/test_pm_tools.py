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
    d.write_text(d.read_text(encoding="utf-8").replace("MAJOR; regressed", "regressed"), encoding="utf-8")
    run("upgrade", str(d))
    res = capsys.readouterr()
    assert "DEF-LNCH-3-1 not triaged; run pm-tools edit" in res.out + res.err
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
    assert run("check", str(a)) == 0


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
    assert "MINOR" not in out, "an emptied severity gets no column"


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
    assert [r[0] for r in rows[1:]] == ["e2e", "integration", "unit", "untagged", "**Total**"]
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
    assert [r[0] for r in table_rows(lst)[1:]] == ["`DEF-LNCH-2`"] and "(tag e2e)" in lst
    run("pivot", str(defects), "--rows", "severity", "--tag", "integration")
    piv = capsys.readouterr().out
    assert table_rows(piv)[1:] == [["MAJOR", "1"]]


def test_a_malformed_author_is_refused(defects: Path):
    with pytest.raises(SystemExit) as e:
        run("list", str(defects), "--author", "kj")
    assert "@kj" in str(e.value)


def test_a_zero_in_the_summary_pair_reads_as_a_dash_and_the_legend_says_so(defects: Path, capsys):
    a_mixed_file(defects, capsys)
    for flag in ("--plain", "--summary"):
        run("report", str(defects), flag)
        out = capsys.readouterr().out
        assert "| Launch `LNCH` | 1/- | 1/1 | 2/1 |" in out
        assert "Cells are `open/closed`; `-` is zero" in out
        grid = [ln for ln in out.splitlines() if ln.startswith("| ") and "/" in ln]
        assert grid and not any(re.search(r"\b0/|/0\b", ln) for ln in grid)
    run("report", str(defects))
    assert "`-/5` is nothing open, 5 closed" in capsys.readouterr().out


def test_report_json_carries_the_same_facts_as_the_tables(defects: Path, capsys):
    import json

    a_mixed_file(defects, capsys)
    run("report", str(defects), "--json")
    (doc,) = json.loads(capsys.readouterr().out)
    assert doc["type"] == "DEF" and doc["counts"] == {"open": 2, "closed": 1, "rejected": 1}
    assert doc["regressions"] == {"count": 1, "defects": 1}
    assert doc["summary"]["columns"] == ["CRITICAL", "MAJOR"]
    launch = doc["summary"]["rows"][0]
    assert launch["category"] == "LNCH" and launch["cells"]["CRITICAL"] == {"open": 1, "closed": 0}
    assert [i["id"] for i in doc["items"]] == ["DEF-LNCH-2", "DEF-LNCH-1-1"]  # the open queue
    assert doc["rejected"] == [
        {"id": "DEF-UI-3", "title": "misaligned button", "reason": "no repro"}
    ]
    assert doc["coverage"]["tags"] == {"integration": 1, "unit": 1, "e2e": 1}


def test_list_and_pivot_json_are_records_and_cells(defects: Path, capsys):
    import json

    a_mixed_file(defects, capsys)
    run("list", str(defects), "--status", "open", "--json")
    recs = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in recs] == ["DEF-LNCH-2", "DEF-LNCH-1-1"]
    assert recs[1]["root"] == "DEF-LNCH-1" and recs[1]["regr"] == 1
    assert recs[0]["tags"] == ["unit", "e2e"] and recs[0]["file"] == str(defects)
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
    hits = json.loads(capsys.readouterr().out)
    assert [(h["id"], h["kind"]) for h in hits] == [("DEF-LNCH-2", "related")]
