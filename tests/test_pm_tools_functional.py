"""Functional end-to-end tests for the `pm-tools` CLI.

Where `test_pm_tools.py` calls `main()` in-process to pin individual contracts,
these drive the console entry point as a real subprocess and walk the workflows
an agent actually runs: file a defect and work it to closed, write a criteria doc
for a feature and audit it, upgrade a legacy document, resolve a merge, and read
the report the user is shown. Exit codes are part of the contract - `check` is a
gate, so its status is asserted, never just its output.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import textwrap

import pytest

CLI = [sys.executable, "-m", "stellars_claude_code_plugins.project_management.pm_tools"]

DEFECTS_HEADER = "# Defects - App\n\nDefects for the app.\n"
ACC_HEADER = "# Acceptance Criteria - App\n\nCriteria for the app.\n"


def pm(*args) -> subprocess.CompletedProcess:
    return subprocess.run(CLI + [str(a) for a in args], capture_output=True, text=True)


def ok(*args) -> str:
    """Run a command that must succeed, returning its stdout."""
    r = pm(*args)
    assert r.returncode == 0, f"{args} exited {r.returncode}\n{r.stdout}\n{r.stderr}"
    return r.stdout


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    d = tmp_path / "docs"
    d.mkdir()
    return d


@pytest.fixture
def defects(docs: Path) -> Path:
    f = docs / "defects-app.md"
    f.write_text(DEFECTS_HEADER, encoding="utf-8")
    ok("author", f, "--handle", "@kj", "--name", "Konrad Jelen")
    return f


@pytest.fixture
def criteria(docs: Path) -> Path:
    f = docs / "acc-crit-app.md"
    f.write_text(ACC_HEADER, encoding="utf-8")
    ok("author", f, "--handle", "@kj", "--name", "Konrad Jelen")
    return f


def file_a_defect(f: Path, title: str, severity: str = "MAJOR", category: str = "LNCH") -> str:
    return ok(
        "add",
        f,
        "--category",
        category,
        "--name",
        "Launch",
        "--author",
        "@kj",
        "--severity",
        severity,
        "--description",
        "Cold start and the first turn after a fork",
        "--title",
        title,
        "--text",
        "auth token empty on the first turn; cause under investigation",
        "--repro",
        "fork under load, send a turn inside 2s",
        "--test-tags",
        "integration",
    )


def write_a_criterion(f: Path, title: str, text: str, category: str = "AUTH") -> str:
    return ok(
        "add",
        f,
        "--category",
        category,
        "--name",
        "Authentication",
        "--author",
        "@kj",
        "--description",
        "Login, session lifetime and password handling",
        "--title",
        title,
        "--text",
        text,
        "--test",
        "freeze clock, idle 31 min, assert 401",
        "--test-tags",
        "unit, integration",
    )


# --- Entry point ----------------------------------------------------------


def test_the_console_entry_point_runs(tmp_path: Path):
    """The wheel's `pm-tools` script and `python -m` reach the same main()."""
    r = pm("--help")
    assert r.returncode == 0
    assert "pm-tools" in r.stdout
    assert "report" in r.stdout and "check" in r.stdout


def test_an_unknown_command_fails_loudly():
    r = pm("frobnicate", "docs")
    assert r.returncode != 0


# --- Workflow: file a defect and work it to closed ------------------------


def test_defect_lifecycle_from_report_to_fix(defects: Path):
    """The whole trail a defect leaves: filed, attempted (and failed), fixed."""
    file_a_defect(defects, "token race on relaunch")

    ok(
        "log",
        defects,
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "attempted: 200ms pre-turn delay - did NOT work, the race still fires",
    )
    ok(
        "relate",
        defects,
        "--id",
        "DEF-LNCH-1",
        "--related",
        "ACC-LNCH-8 - the criterion this violates",
    )
    ok(
        "close",
        defects,
        "--id",
        "DEF-LNCH-1",
        "--evidence",
        "tests/test_session.py::test_fork_token green",
        "--author",
        "@kj",
        "--event",
        "fixed: token awaited before the first turn; 79 pytest green",
    )

    body = defects.read_text(encoding="utf-8")
    assert "- [x] `DEF-LNCH-1`" in body
    assert "MAJOR;" in body, "severity survives the lifecycle as the first word of the body"
    assert body.count("- log:") == 3, "add, the failed attempt, and the close"
    assert "did NOT work" in body, "the ruled-out attempt is the reason the file exists"
    assert body.index("attempted") < body.index("fixed:"), "log lines append in order"
    assert pm("check", defects).returncode == 0


def test_a_defect_that_was_never_a_defect_is_rejected_not_closed(defects: Path):
    file_a_defect(defects, "splash hang on a cold cache")
    ok(
        "reject",
        defects,
        "--id",
        "DEF-LNCH-1",
        "--author",
        "@kj",
        "--event",
        "not reproduced on 3 devices over 40 cold starts",
    )

    body = defects.read_text(encoding="utf-8")
    assert "- [-] `DEF-LNCH-1`" in body
    assert "not reproduced on 3 devices" in body, "the reason stays with the item"

    out = ok("report", defects)
    assert "0 open" in out and "1 rejected" in out, "the header line carries the count"
    assert "1 rejected not listed" in out, "rejected work is never in the open fix queue"

    # Drift pinned deliberately: the skill says REJECTED "carries the reasons", but the
    # section only prints under `--status all` or `--status rejected` - the default
    # (`want` is open) is excluded by the same guard that suppresses it under `closed`.
    assert "REJECTED" not in out
    detail = ok("report", defects, "--status", "rejected")
    assert "REJECTED" in detail
    assert "not reproduced on 3 devices" in detail, "the reason is one flag away"


def test_severity_spreads_across_the_summary_columns(defects: Path):
    for title, sev in (
        ("data loss on sync", "CRITICAL"),
        ("token race", "MAJOR"),
        ("stale avatar", "MINOR"),
    ):
        file_a_defect(defects, title, severity=sev)
    out = ok("report", defects)
    for sev in ("CRITICAL", "MAJOR", "MINOR"):
        assert sev in out
    assert "MEDIUM" not in out, "a severity with no items gets no column"


def test_items_is_a_fix_queue_worst_first(defects: Path):
    file_a_defect(defects, "stale avatar", severity="MINOR")
    file_a_defect(defects, "data loss on sync", severity="CRITICAL")
    out = ok("report", defects)
    items = out[out.index("ITEMS") :]
    assert items.index("data loss on sync") < items.index("stale avatar"), (
        "the queue is ordered by severity, not by id"
    )


# --- Workflow: write and audit a criteria document ------------------------


def test_criteria_document_from_empty_to_audited(criteria: Path):
    write_a_criterion(criteria, "Password generation", "16 chars, 3 character classes")
    write_a_criterion(criteria, "Session timeout", "session expires after 30 idle minutes")
    write_a_criterion(
        criteria,
        "Edge: token deleted mid-session",
        "the next call returns 401 and the UI routes to login",
    )
    ok("close", criteria, "--id", "ACC-AUTH-1", "--author", "@kj", "--event", "verified in v1.3.0", "--evidence", "unit suite green")

    assert pm("check", criteria).returncode == 0
    assert pm("check", criteria, "--strict").returncode == 0, (
        "a fully filled criteria doc passes the strict gate"
    )

    out = ok("report", criteria)
    assert "TEST COVERAGE" in out
    assert "unit" in out and "integration" in out
    assert "Session timeout" in out, "open criteria are listed"
    assert "1 closed not listed" in out, "closed work is counted, not enumerated"


def test_detail_view_carries_every_sub_line(criteria: Path):
    write_a_criterion(criteria, "Session timeout", "session expires after 30 idle minutes")
    ok("relate", criteria, "--id", "ACC-AUTH-1", "--blocked-by", "DEF-LNCH-3")
    out = ok("report", criteria, "--detail")
    assert "freeze clock, idle 31 min" in out, "the test hint is shown verbatim"
    assert "DEF-LNCH-3" in out, "relations are shown"
    assert "@kj added" in out, "the whole log is shown"


def test_category_filter_narrows_every_section(criteria: Path):
    write_a_criterion(criteria, "Password generation", "16 chars")
    ok(
        "add",
        criteria,
        "--category",
        "BRSW",
        "--name",
        "Branch Switching",
        "--author",
        "@kj",
        "--description",
        "Switching between conversation branches",
        "--title",
        "Submenu",
        "--text",
        "a row with >1 branch shows the submenu",
        "--test",
        "seed 2 JSONLs, right-click",
        "--test-tags",
        "e2e",
    )
    out = ok("report", criteria, "--category", "AUTH")
    assert "Password generation" in out
    assert "Submenu" not in out


# --- Workflow: both disciplines in one directory --------------------------


def test_a_directory_reports_both_disciplines(docs: Path, defects: Path, criteria: Path):
    file_a_defect(defects, "token race on relaunch")
    write_a_criterion(criteria, "Session timeout", "session expires after 30 idle minutes")

    out = ok("report", docs)
    assert "token race on relaunch" in out
    assert "Session timeout" in out
    assert "DEFECTS" in out and "ACCEPTANCE" in out.upper()
    assert pm("check", docs).returncode == 0


def test_a_criterion_and_a_defect_cite_each_other_across_files(
    docs: Path, defects: Path, criteria: Path
):
    """Relations are cross-type, and each side is written on its own item."""
    file_a_defect(defects, "token race on relaunch")
    write_a_criterion(
        criteria, "First turn authenticates", "the first turn after a fork is authed"
    )
    ok(
        "relate",
        defects,
        "--id",
        "DEF-LNCH-1",
        "--related",
        "ACC-AUTH-1 - the criterion this breaks",
    )
    ok(
        "relate",
        criteria,
        "--id",
        "ACC-AUTH-1",
        "--related",
        "DEF-LNCH-1 - the defect that breaks it",
    )

    assert "ACC-AUTH-1" in ok("refs", docs, "--id", "DEF-LNCH-1")
    assert "DEF-LNCH-1" in ok("refs", docs, "--id", "ACC-AUTH-1")
    assert pm("check", docs).returncode == 0


# --- The gate -------------------------------------------------------------


def test_check_is_a_gate_not_a_reporter(defects: Path):
    """Non-zero exit on errors is what makes `check` usable in a workflow."""
    file_a_defect(defects, "token race")
    assert pm("check", defects).returncode == 0

    broken = defects.read_text(encoding="utf-8").replace("MAJOR; ", "", 1)
    defects.write_text(broken, encoding="utf-8")
    r = pm("check", defects)
    assert r.returncode != 0
    assert "error" in r.stdout.lower()


def test_strict_promotes_warnings_to_failures(defects: Path):
    """A missing repro line is a warning - the doc is usable, the gate is not clean."""
    ok(
        "add",
        defects,
        "--category",
        "LNCH",
        "--name",
        "Launch",
        "--author",
        "@kj",
        "--severity",
        "MEDIUM",
        "--description",
        "Cold start",
        "--title",
        "no repro yet",
        "--text",
        "symptom only",
    )
    assert pm("check", defects).returncode == 0, "a warning does not fail the normal gate"
    assert pm("check", defects, "--strict").returncode != 0


def test_a_duplicate_id_is_caught(defects: Path):
    file_a_defect(defects, "token race")
    body = defects.read_text(encoding="utf-8")
    dupe = [ln for ln in body.splitlines() if "`DEF-LNCH-1`" in ln][0]
    defects.write_text(body + "\n" + dupe + "\n", encoding="utf-8")
    r = pm("check", defects)
    assert r.returncode != 0
    assert "DEF-LNCH-1" in r.stdout


def test_forbidden_glyphs_are_rejected(criteria: Path):
    """The format bans em-dashes, unicode arrows and emojis in item text."""
    write_a_criterion(criteria, "Session timeout", "session expires after 30 idle minutes")
    body = criteria.read_text(encoding="utf-8").replace(
        "session expires after 30 idle minutes",
        "session expires — after 30 idle minutes",
    )
    criteria.write_text(body, encoding="utf-8")
    assert pm("check", criteria).returncode != 0


def test_remove_refuses_while_something_still_cites_the_item(docs: Path, defects: Path):
    file_a_defect(defects, "token race")
    file_a_defect(defects, "splash hang")
    ok("relate", defects, "--id", "DEF-LNCH-1", "--related", "DEF-LNCH-2 - same subsystem")

    r = pm("remove", defects, "--id", "DEF-LNCH-2")
    assert r.returncode != 0, "an item something points at cannot be silently deleted"
    assert "DEF-LNCH-2" in defects.read_text(encoding="utf-8")

    assert pm("remove", defects, "--id", "DEF-LNCH-2", "--force").returncode == 0
    r = pm("check", defects)
    assert r.returncode == 0, "a dangling id is a warning to read, not an error to fix blind"
    assert "DEF-LNCH-2" in r.stdout and "warn" in r.stdout
    assert pm("check", defects, "--strict").returncode != 0, "--strict is where it bites"


# --- Workflow: upgrade a legacy document ----------------------------------


LEGACY = textwrap.dedent("""\
    # Acceptance Criteria - Legacy App

    Criteria inherited from the old tracker.

    ## Contents

    - [Authentication](#authentication)

    ## Authentication

    Login and session handling

    - [x] **Password generation** - 16 chars, 3 character classes
      - 2026-06-12 implemented
    - [ ] **Session timeout** - session expires after 30 idle minutes
    """)


def test_upgrade_dry_run_writes_nothing(tmp_path: Path):
    f = tmp_path / "acc-crit-legacy.md"
    f.write_text(LEGACY, encoding="utf-8")
    before = f.read_text(encoding="utf-8")

    r = pm("upgrade", f)
    assert "ACC-" in r.stdout, "the dry run shows the ids it would assign"
    assert f.read_text(encoding="utf-8") == before, "a dry run writes nothing"


def test_upgrade_assigns_ids_signs_the_history_and_drops_the_contents_table(tmp_path: Path):
    f = tmp_path / "acc-crit-legacy.md"
    f.write_text(LEGACY, encoding="utf-8")
    ok("author", f, "--handle", "@kj", "--name", "Konrad Jelen")

    ok("upgrade", f, "--code", "Authentication=AUTH", "--author", "@kj", "--apply")
    body = f.read_text(encoding="utf-8")

    assert "## Contents" not in body, "the hand-kept index is a second store; it goes"
    assert re.search(r"`ACC-AUTH-\d+`", body), "every item carries an id"
    assert "`AUTH`" in body, "the category heading carries its code"
    assert "@kj" in body, "--author signs the inherited, unauthored history"
    assert "- [x]" in body and "- [ ]" in body, "the states survive the rebuild"


# --- Workflow: resolve a merge --------------------------------------------


def test_a_merge_that_duplicated_a_number_is_caught_by_the_gate(defects: Path):
    """Two contributors adding offline both take the same next id."""
    file_a_defect(defects, "token race")
    theirs = defects.read_text(encoding="utf-8").splitlines()
    mine = [ln.replace("token race", "splash hang") for ln in theirs if "`DEF-LNCH-1`" in ln]
    defects.write_text("\n".join(theirs + mine) + "\n", encoding="utf-8")

    r = pm("check", defects)
    assert r.returncode != 0, "the duplicate is the gate's job to catch, not the reader's"
    assert "DEF-LNCH-1" in r.stdout


def test_renumbering_is_never_the_fix_the_tool_offers(defects: Path):
    """There is no renumber command - ids are permanent, so a clash is resolved
    by re-adding one side, which takes the next free number."""
    assert "renumber" not in ok("--help").lower()


# --- Reports the user is shown --------------------------------------------


def test_report_prints_paste_ready_markdown_tables(defects: Path):
    file_a_defect(defects, "token race on relaunch")
    out = ok("report", defects)
    table_rows = [ln for ln in out.splitlines() if ln.startswith("|")]
    assert table_rows, "the report is markdown tables"
    assert any(set(ln) <= set("|-: ") for ln in table_rows), "with a header separator row"


def test_status_filter_narrows_items_but_not_the_summary(defects: Path):
    file_a_defect(defects, "token race")
    file_a_defect(defects, "splash hang")
    ok("close", defects, "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "fixed", "--evidence", "unit suite green")

    out = ok("report", defects, "--status", "closed")
    assert "splash hang" in out, "ITEMS now lists the closed work"
    summary = out[out.index("SUMMARY") : out.index("ITEMS")]
    assert "1/1" in summary, "the summary still shows the whole scope, not the filter"


def restamp(f: Path, item: str, stamp: str, event: str = "added") -> None:
    """Set the stamp on one of an item's log lines. The file is the whole store, so a
    test that needs a particular date writes one into it rather than mocking a clock."""
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


def test_a_severity_ask_is_a_flag_not_a_reading_of_the_file(defects: Path):
    """ "show me the critical defects" has to be one command. The moment the agent reads
    the document and filters inside its answer, the counts stop being computed."""
    file_a_defect(defects, "token race", severity="CRITICAL")
    file_a_defect(defects, "splash flicker", severity="MINOR")

    out = ok("report", defects, "--severity", "CRITICAL")
    assert "token race" in out and "splash flicker" not in out
    assert "1 open / 0 closed" in out, "the counts follow the filter, not the file"
    assert "MINOR" not in out, "a severity the filter empties gets no column"


def test_the_date_window_reads_the_log_which_is_where_dates_live(defects: Path):
    """filed, closed and updated are three questions about the same item, and all three
    are answered from the log lines - nothing else records a date."""
    file_a_defect(defects, "token race")
    file_a_defect(defects, "splash flicker")
    ok("close", defects, "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed", "--evidence", "unit suite green")
    restamp(defects, "DEF-LNCH-1", "2026-05-04T09:00:00Z")
    restamp(defects, "DEF-LNCH-1", "2026-08-26T14:00:00Z", event="closed")
    restamp(defects, "DEF-LNCH-2", "2026-07-21T12:00:00Z")

    filed = ok("report", defects, "--since", "2026-07-01", "--until", "2026-07-31")
    assert "splash flicker" in filed and "token race" not in filed
    assert "filed 2026-07-01 to 2026-07-31" in filed, "the header names the window applied"

    closed = ok("report", defects, "--dates", "closed", "--since", "2026-08-01")
    assert "token race" in closed, "a closed window lists what it found without --status all"
    assert "splash flicker" not in closed, "an open item has no closed date"

    stale = ok("report", defects, "--dates", "updated", "--until", "2026-07-31", "--status", "all")
    assert "splash flicker" in stale and "token race" not in stale


def test_a_reopened_criterion_retires_the_closed_date(criteria: Path):
    write_a_criterion(criteria, "session survives a refresh", "the token is rotated in place")
    ok("close", criteria, "--id", "ACC-AUTH-1", "--author", "@kj", "--event", "done", "--evidence", "unit suite green")
    restamp(criteria, "ACC-AUTH-1", "2026-08-26T14:00:00Z", event="closed")
    ok("reopen", criteria, "--id", "ACC-AUTH-1", "--author", "@kj")

    out = ok("report", criteria, "--dates", "closed", "--since", "2026-08-01")
    assert "session survives a refresh" not in out, "it is open again, so it has no closed date"


def test_a_regressed_defect_keeps_the_closed_date_it_earned(defects: Path):
    """The closure really happened on that day; the regression is a separate item."""
    file_a_defect(defects, "token race")
    ok("close", defects, "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed", "--evidence", "unit suite green")
    restamp(defects, "DEF-LNCH-1", "2026-08-26T14:00:00Z", event="closed")
    ok("reopen", defects, "--id", "DEF-LNCH-1", "--author", "@kj")

    out = ok("report", defects, "--dates", "closed", "--since", "2026-08-01")
    assert "`DEF-LNCH-1`" in out, "the closure stands and keeps its date"
    assert "`DEF-LNCH-1-1`" not in out, "the open regression has no closed date"


def test_summary_stops_at_the_grid_and_plain_only_drops_the_chrome(defects: Path):
    """A summary and a plain report are different asks: one removes the items, the other
    removes the decoration around them."""
    file_a_defect(defects, "token race")

    brief = ok("report", defects, "--summary")
    assert "SUMMARY" in brief and "1 open / 0 closed" in brief, "the grid and its counts"
    assert "ITEMS" not in brief and "token race" not in brief
    assert "CATEGORIES" not in brief and "TEST COVERAGE" not in brief

    flat = ok("report", defects, "--plain")
    assert "ITEMS" in flat and "token race" in flat, "plain keeps the queue"
    assert "CATEGORIES" not in flat and "TEST COVERAGE" not in flat
    assert "Categories down" not in flat, "no section blurb"
    assert not any(ord(ch) > 0x2500 for ch in flat), "and no icons"


def test_severity_on_a_criteria_document_is_named_not_reported_as_zeros(criteria: Path):
    write_a_criterion(criteria, "session expiry", "idle 30 min ends the session")
    r = pm("report", criteria, "--severity", "CRITICAL")
    assert r.returncode == 0
    assert "skipped" in r.stderr, "severity is a defect attribute; say so"
    assert "SUMMARY" not in r.stdout, "and print no grid of zeros"


def test_a_malformed_date_is_refused_rather_than_guessed(defects: Path):
    file_a_defect(defects, "token race")
    r = pm("report", defects, "--since", "2026-8-1")
    assert r.returncode != 0
    assert "YYYY-MM-DD" in r.stderr + r.stdout


def test_neither_discipline_closes_without_evidence(defects: Path, criteria: Path):
    """A closure with no proof is a claim, so the CLI refuses it on both documents and
    the item is left exactly as it was."""
    file_a_defect(defects, "token race")
    write_a_criterion(criteria, "session expiry", "idle 30 min ends the session")

    for f, item in ((defects, "DEF-LNCH-1"), (criteria, "ACC-AUTH-1")):
        r = pm("close", f, "--id", item, "--author", "@kj", "--event", "done")
        assert r.returncode != 0, f"{item} closed with no evidence"
        assert "--evidence" in r.stderr
        assert f"- [ ] `{item}`" in f.read_text(encoding="utf-8"), "and nothing changed"

    ok("close", defects, "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed",
       "--evidence", "test_fork_token green on build 412")
    ok("close", criteria, "--id", "ACC-AUTH-1", "--author", "@kj", "--event", "met",
       "--evidence", "frozen clock, idle 31 min, 401 observed")

    for f in (defects, criteria):
        assert pm("check", f, "--strict").returncode == 0, "a proven closure passes the gate"

    out = ok("report", defects, "--status", "closed")
    assert "Evidence" in out and "build 412" in out, "the proof is in the report"


def test_a_criterion_proven_then_reopened_gives_the_evidence_back_to_the_log(criteria: Path):
    write_a_criterion(criteria, "session survives a refresh", "the token is rotated in place")
    ok("close", criteria, "--id", "ACC-AUTH-1", "--author", "@kj", "--event", "done",
       "--evidence", "test_refresh green on build 412")
    ok("reopen", criteria, "--id", "ACC-AUTH-1", "--author", "@kj", "--event", "not done")

    body = criteria.read_text(encoding="utf-8")
    assert "- evidence:" not in body, "an open item carries no proof of being done"
    assert "evidence retired: test_refresh green on build 412" in body
    assert pm("check", criteria, "--strict").returncode == 0


def test_reopening_a_defect_files_a_numbered_regression(defects: Path):
    """A proven fix that broke again is a new open item, not a reversal of the old one."""
    file_a_defect(defects, "token race")
    ok("close", defects, "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed",
       "--evidence", "test_fork_token green on build 412")
    out = ok("reopen", defects, "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "came back on 470")

    assert "DEF-LNCH-1-1" in out, "the command names the item it minted"
    body = defects.read_text(encoding="utf-8")
    assert "- [x] `DEF-LNCH-1`" in body, "the parent closure stands"
    assert "- evidence: test_fork_token green on build 412" in body, "proven when it was made"
    assert "- [ ] `DEF-LNCH-1-1`" in body, "the regression is its own open item"
    assert "regressed as DEF-LNCH-1-1" in body, "the parent records where it went"
    assert "regression of DEF-LNCH-1: came back on 470" in body, "the child names its parent"
    assert pm("check", defects).returncode == 0


def test_the_report_says_how_regressive_the_system_is(defects: Path):
    """Counting regressions is the reason the derived ids exist."""
    file_a_defect(defects, "token race")
    file_a_defect(defects, "cold start hangs")
    ok("close", defects, "--id", "DEF-LNCH-1", "--author", "@kj", "--event", "fixed", "--evidence", "green on 412")
    ok("reopen", defects, "--id", "DEF-LNCH-1", "--author", "@kj")
    ok("close", defects, "--id", "DEF-LNCH-1-1", "--author", "@kj", "--event", "fixed", "--evidence", "green on 470")
    ok("reopen", defects, "--id", "DEF-LNCH-1-1", "--author", "@kj")
    ok("close", defects, "--id", "DEF-LNCH-2", "--author", "@kj", "--event", "fixed", "--evidence", "green on 480")
    ok("reopen", defects, "--id", "DEF-LNCH-2", "--author", "@kj")

    assert "3 regressions across 2 defects" in ok("report", defects, "--status", "all")
    assert "3 regressions across 2 defects" in ok("report", defects, "--summary", "--status", "all")
    body = defects.read_text(encoding="utf-8")
    assert "`DEF-LNCH-1-2`" in body and "DEF-LNCH-1-1-1" not in body, "ordinals stay flat"


def test_upgrade_names_the_closed_items_that_carry_no_evidence(docs: Path):
    """A legacy tracker closed everything without proof. upgrade cannot invent it, so it
    says how many need one rather than fabricating a line."""
    f = docs / "defects-legacy.md"
    f.write_text(
        "# Defects - Legacy\n\n## Launch\n\nCold start\n\n"
        "- [x] **old bug** - MAJOR; fixed long ago\n"
        "  - log: 2026-01-02T00:00:00Z @kj closed: fixed\n\n"
        "## Authors\n\n- `@kj` Konrad Jelen\n",
        encoding="utf-8",
    )
    r = pm("upgrade", f)
    assert r.returncode == 0
    assert "1 closed item(s) carry no evidence" in r.stderr


def test_list_categories_is_the_derived_index(defects: Path):
    file_a_defect(defects, "token race", category="LNCH")
    ok(
        "add",
        defects,
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
    out = ok("list-categories", defects)
    assert "LNCH" in out and "AUTH" in out
    assert "Launch" in out and "Authentication" in out
