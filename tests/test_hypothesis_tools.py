"""Guard the hypothesis ledger parser against the three shipped examples.

The examples are the fixtures on purpose. They are what the skill tells an
agent to mirror, so a parser that stops reading them is broken by definition,
and an example edited into a shape the parser cannot read is caught here
rather than the first time an agent asks for the next free ordinal.

Two regressions are pinned below because both were live bugs found by running
the parser over the real examples, not hypothetical:
  - a benchmarks row citing two ids minting a phantom hypothesis
  - a declaration skipped because its PROSE cited a sibling hypothesis
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from stellars_claude_code_plugins.hypothesis.hypothesis_tools import (
    REQUIRED_FIELDS,
    VERDICTS,
    main,
    match_verdict,
    parse_ledger,
    roster_of,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "plugins" / "datascience" / "skills" / "hypothesis" / "examples"

QUANTIZED = EXAMPLES / "quantized-inference-experiments.md"
WMD = EXAMPLES / "wmd-docdistance-experiments.md"
LEXICAL = EXAMPLES / "lexical-grounding-experiments.md"


def _parse(path: Path):
    return parse_ledger(path.read_text(encoding="utf-8"))


# --- Shipped examples stay parseable --------------------------------------


@pytest.mark.parametrize("path", [QUANTIZED, WMD, LEXICAL])
def test_every_shipped_example_parses(path: Path):
    hyps = _parse(path)
    assert hyps, f"{path.name} yielded no hypotheses - the parser lost the format"
    assert len({h.hid for h in hyps}) == len(hyps), "duplicate ids from one document"


def test_quantized_inference_full_block_shape():
    hyps = _parse(QUANTIZED)
    assert [h.hid for h in hyps] == [f"E12-H{n}" for n in range(33, 37)] + [
        f"E13-H{n}" for n in range(37, 42)
    ]
    assert all(h.shape == "full" for h in hyps)
    assert all(h.verdict == "Confirmed" for h in hyps)
    assert all(set(REQUIRED_FIELDS) <= set(h.fields) for h in hyps)


def test_wmd_docdistance_verdict_spread():
    hyps = _parse(WMD)
    assert [h.hid for h in hyps] == [f"E01-H{n}" for n in range(1, 6)]
    assert [h.verdict for h in hyps] == [
        "Refuted",
        "Promoted",
        "Refuted (null)",
        "Refuted",
        "Refuted",
    ]


def test_lexical_grounding_compact_shape_is_unverdicted_not_guessed():
    """Compact hypotheses parse for id and slug, and stop there.

    The verdict is narrative in this shape. Inferring it would read "the
    contradiction features were initially killed" - a sentence about a fix
    that was then repaired - as a Killed verdict.
    """
    hyps = _parse(LEXICAL)
    assert len(hyps) == 27
    assert all(h.shape == "compact" for h in hyps)
    assert all(h.verdict is None for h in hyps)
    assert all(h.author is None for h in hyps)  # written before authorship existed
    assert [h.ordinal for h in hyps] == list(range(1, 28))


# --- The two regressions ---------------------------------------------------


def test_benchmark_row_citing_two_ids_declares_nothing():
    """`- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair` is a timing row.

    Its bold label names two hypotheses, so it declares neither. Without this
    rule the wmd benchmarks section mints a phantom E01-H1.
    """
    assert "**E01-H1 / E01-H1b weighting**" in WMD.read_text(encoding="utf-8"), (
        "fixture drifted - the example no longer contains the multi-id row this pins"
    )
    hyps = _parse(WMD)
    assert len(hyps) == 5, "a cross-reference row leaked in as a hypothesis"
    assert sum(h.hid == "E01-H1" for h in hyps) == 1


def test_declaration_citing_a_sibling_in_prose_still_declares():
    """E8-H17's body cites E8-H16; only the LABEL decides declaration.

    Scoping the multi-id guard to the whole line silently dropped this
    hypothesis - the ledger looked like it had a gap at ordinal 17.
    """
    hyps = _parse(LEXICAL)
    h17 = next((h for h in hyps if h.hid == "E8-H17"), None)
    assert h17 is not None, "a hypothesis was dropped for citing a sibling in its prose"
    assert h17.slug.startswith("alignment-profile features")


def test_field_qualifier_outside_the_bold_span_is_not_lost():
    """`- **Result** (k=1) - DR 0.180` is a Result carrying a qualifier."""
    hyps = _parse(WMD)
    h2 = next(h for h in hyps if h.hid == "E01-H2")
    assert "Result" in h2.fields
    assert h2.fields["Result"].startswith("(k=1)")


def test_fenced_code_does_not_declare_hypotheses():
    text = "# L\n\n```markdown\n### E99-H999 documented example\n\n- **Verdict** - Ships\n```\n"
    assert parse_ledger(text) == []


# --- Verdict vocabulary ----------------------------------------------------


def test_refuted_null_is_not_truncated_to_refuted():
    assert match_verdict("Refuted (null); `arccos` is near-affine") == "Refuted (null)"
    assert match_verdict("Refuted; up-weighting numbers pulls") == "Refuted"


def test_confirmed_is_in_the_vocabulary():
    """Undeclared in SKILL.md yet used by every verdict in the primary example."""
    assert "Confirmed" in VERDICTS
    assert match_verdict("Confirmed; the memory-bound decode win is real") == "Confirmed"


def test_a_short_head_is_an_open_label_and_a_story_is_none():
    """Real ledgers grow their own vocabulary - SUPPORTED, PARTIAL,
    Inconclusive - and reading it beats calling a third of a store
    unverdicted. The line still holds where reading would be guessing:
    a mixed-regime narrative carries no single label."""
    assert match_verdict("Works great, ship it") == "Works great"
    assert match_verdict("SUPPORTED") == "SUPPORTED"
    assert match_verdict("**PARTIAL** - closing the three result blocks") == "PARTIAL"
    assert match_verdict("**Inconclusive** (applicability: Low) - fails") == "Inconclusive"
    assert match_verdict("Refuted for k=1, Confirmed for k=3") is None
    assert match_verdict("pending final vs H121, but leaning REFUTED: x") is None


def test_canonical_labels_read_through_case_emphasis_and_hyphens():
    assert match_verdict("**Confirmed**; 0.91") == "Confirmed"
    assert match_verdict("REFUTED (the registered clause)") == "Refuted"
    assert match_verdict("Killed at gate (proxy)") == "Killed-at-gate"
    assert match_verdict("(2026-07-12) Confirmed; the number") == "Confirmed"
    assert match_verdict("Refuted (null); no signal") == "Refuted (null)"
    # a qualified label is returned AS WRITTEN, never coerced to its canonical
    # neighbour - "Confirmed-partially" is not Confirmed
    assert match_verdict("Confirmed-partially; 0.5") == "Confirmed-partially"


def test_a_canonical_label_followed_by_scoping_prose_reads_as_that_label():
    """Three real verdicts - `Refuted on the replacement bar;`, `**Refuted**
    as an order measure (applicability: Low) - ...`, `**Refuted** as a
    metric (...)` - were the last errors standing on two ledgers: the head
    ran past three words and no label could be read. The scope is prose the
    way `(killed at gate)` is; only a number in it makes a regime, and a
    regime stays a story."""
    assert match_verdict("Refuted on the replacement bar; Spearman 0.9636") == "Refuted"
    assert (
        match_verdict("**Refuted** as an order measure (applicability: Low) - rises") == "Refuted"
    )
    assert (
        match_verdict("**Refuted** as a metric (applicability: Low) - 6.7% violations")
        == "Refuted"
    )
    assert match_verdict("CONFIRMED on both articles - band 0.91-0.93") == "Confirmed"
    assert match_verdict("Refuted for int8-dynamic; the size effect does not show") == "Refuted"
    assert match_verdict("Refuted at the +10% bar; ±5% wash") == "Refuted"
    assert match_verdict("Promoted. The identity-gap class closes") == "Promoted"
    assert match_verdict("Refuted (null) on direction, mechanism confirmed; x") == "Refuted (null)"
    # a regime: the next clause opens with another label
    assert match_verdict("Refuted for k=1, Confirmed for k=3") is None
    assert match_verdict("Refuted for bf16, kept for the recipe; x") is None
    assert match_verdict("Refuted at the 1,000 bar, Confirmed as a deployment pattern") is None
    assert match_verdict("Confirmed-partially; 0.5") == "Confirmed-partially"


# --- CLI -------------------------------------------------------------------


def test_next_id_reports_the_next_free_ordinal(capsys):
    assert main(["next-id", str(QUANTIZED)]) == 0
    out = capsys.readouterr().out
    assert "next_h: H42" in out
    assert "next_batch: E14" in out


def test_next_id_keeps_the_batch_zero_padding(capsys):
    """`E01` must roll to `E02`, not `E2` - the token is the doc's own idiom."""
    assert main(["next-id", str(WMD)]) == 0
    assert "next_batch: E02" in capsys.readouterr().out


def test_check_passes_on_every_shipped_example(capsys):
    for path in (QUANTIZED, WMD, LEXICAL):
        assert main(["check", str(path)]) == 0, f"{path.name} fails its own validator"
    assert "no errors" in capsys.readouterr().out


def test_check_fails_on_a_duplicate_ordinal(tmp_path, capsys):
    ledger = tmp_path / "dup.md"
    ledger.write_text(
        "# L\n\n**Canonical Experiments Document**\n\n"
        "### E1-H7 first\n\n- **Verdict** - Ships; 1.0\n\n"
        "### E2-H7 reset the ordinal\n\n- **Verdict** - Kept; 2.0\n",
        encoding="utf-8",
    )
    assert main(["check", str(ledger)]) == 1
    assert "reuses ordinal H7" in capsys.readouterr().err


def test_check_warns_on_a_grown_label_and_fails_only_when_none_reads(tmp_path, capsys):
    """The vocabulary is open: a ledger-grown label is one aggregated warning,
    and check errors only where no label can be read at all."""
    ledger = tmp_path / "bad.md"
    ledger.write_text(
        "# L\n\n**Canonical Experiments Document**\n\n"
        "### E1-H1 slug\n\n- **Verdict** - Works great; 1.0\n",
        encoding="utf-8",
    )
    assert main(["check", str(ledger)]) == 0
    err = capsys.readouterr().err
    assert "non-canonical verdict labels: Works great (1)" in err
    ledger.write_text(
        "# L\n\n**Canonical Experiments Document**\n\n"
        "### E1-H1 slug\n\n- **Verdict** - Refuted for k=1, Confirmed for k=3\n",
        encoding="utf-8",
    )
    assert main(["check", str(ledger)]) == 1
    assert "carries no readable label" in capsys.readouterr().err


def test_check_warns_but_passes_on_a_compact_ledger(capsys):
    """One warning covering all 27, not 27 identical lines.

    A wall of identical warnings on a SHIPPED example trains a reader to skip
    the block where the real findings live.
    """
    assert main(["check", str(LEXICAL)]) == 0
    captured = capsys.readouterr()
    assert "27 compact hypotheses" in captured.err
    assert "verdicts not machine-readable" in captured.err
    assert captured.err.count("machine-readable") == 1
    assert "1 warnings" in captured.out


def test_check_counts_unrun_and_aggregates_missing_fields(tmp_path, capsys):
    """Eleven pre-registered hypotheses drew eleven `has no Result, Verdict`
    lines on the ledger they were registered into - a state the skill
    designs for, reported as a defect eleven times. Unrun is a count in the
    summary; a genuinely missing field is one line per field naming the ids,
    and an unrun hypothesis never appears in the `no Result` line."""
    full = (
        "- **Hypothesis** - h\n- **Lever** - l\n- **Mechanism** - m\n"
        "- **Prediction** - p\n- **Acceptance bar** - a\n"
    )
    ledger = tmp_path / "unrun.md"
    ledger.write_text(
        "# L\n\n**Canonical Experiments Document**\n\n"
        "### E1-H1 bare\n\n- **Hypothesis** - h\n\n"
        f"### E1-H2 registered\n\n{full}\n"
        f"### E1-H3 verdicted\n\n{full}- **Verdict** - Confirmed; 1.0\n",
        encoding="utf-8",
    )
    assert main(["check", str(ledger)]) == 0
    captured = capsys.readouterr()
    assert "OK: 3 hypotheses, no errors, 2 unrun, 5 warnings" in captured.out
    assert "has no" not in captured.err
    assert "1 hypotheses have no Lever (E1-H1)" in captured.err
    assert "1 hypotheses have no Result (E1-H3)" in captured.err
    assert "Verdict" not in captured.err


def test_show_returns_the_block_verbatim(capsys):
    assert main(["show", str(QUANTIZED), "E12-H33"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("### E12-H33 llama.cpp int4 runs on sm_120")
    assert "- **Verdict** - Confirmed" in out
    assert "E12-H34" not in out, "the block ran past its own hypothesis"


def test_show_accepts_a_bare_ordinal(capsys):
    assert main(["show", str(WMD), "3"]) == 0
    assert capsys.readouterr().out.startswith("### E01-H3")


def test_show_missing_id_exits_nonzero(capsys):
    assert main(["show", str(WMD), "E01-H999"]) == 1
    assert "not found" in capsys.readouterr().err


def test_list_filters_by_exact_verdict_label(capsys):
    assert main(["list", str(WMD), "--verdict", "Refuted"]) == 0
    out = capsys.readouterr().out
    assert "3 hypotheses" in out
    assert "E01-H3" not in out, "'Refuted' must not swallow 'Refuted (null)'"


def test_list_filters_unverdicted(capsys):
    assert main(["list", str(LEXICAL), "--verdict", "none"]) == 0
    assert "27 hypotheses" in capsys.readouterr().out


def test_list_filters_by_batch(capsys):
    assert main(["list", str(QUANTIZED), "--batch", "E13"]) == 0
    out = capsys.readouterr().out
    assert "5 hypotheses" in out
    assert "E12-H33" not in out


def test_list_json_is_machine_readable(capsys):
    import json

    assert main(["list", str(QUANTIZED), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 9
    assert rows[0]["id"] == "E12-H33"
    assert rows[0]["verdict"] == "Confirmed"


def test_missing_ledger_exits_nonzero(tmp_path, capsys):
    assert main(["check", str(tmp_path / "nope.md")]) == 1
    assert "not found" in capsys.readouterr().err


# --- Adversarial-review regressions ---------------------------------------
#
# Every test below pins a defect a hostile reviewer reproduced against the
# first cut. They are grouped because they share one theme: the parser was
# strict, and everything it failed to read it dropped SILENTLY - so `next-id`
# returned an ordinal that was already burnt, which is the one failure that
# corrupts an append-only registry.

MARKER = "**Canonical Experiments Document**"


def _ledger(tmp_path, body: str, name: str = "l.md"):
    p = tmp_path / name
    p.write_text(f"# L\n\n{MARKER}\n\n{body}", encoding="utf-8")
    return p


ROSTER = "## Authors\n\n- `@kj` Konrad Jelen\n\n"


def _writable(tmp_path, body: str, name: str = "l.md"):
    """A ledger carrying a roster - every write names an author on it."""
    return _ledger(tmp_path, ROSTER + body, name)


def _log(path, hid: str, event: str, date: str, author: str = "@kj"):
    return main(
        ["log-event", str(path), hid, "--event", event, "--date", date, "--author", author]
    )


def test_supersede_back_reference_still_declares(tmp_path):
    """The skill MANDATES a back-reference; counting its id dropped the round.

    `fanout.md` step 4: a collision "explicitly supersedes with a back-
    reference". Treating that id as a citation deleted the declaration, and
    next-id then returned H1 with H106 already burnt.
    """
    p = _ledger(tmp_path, "- **R30-H106 global-cut (supersedes R9-H21)** - TNR 0.78, ships\n")
    hyps = _parse(p)
    assert [h.hid for h in hyps] == ["R30-H106"]


def test_multi_id_label_without_a_parenthetical_still_declares_nothing(tmp_path):
    """The narrowing must not reopen the phantom-hypothesis hole."""
    p = _ledger(tmp_path, "- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair\n")
    assert _parse(p) == []


@pytest.mark.parametrize("marker", ["-", "*", "+"])
def test_every_commonmark_bullet_declares(tmp_path, marker):
    """A formatter can swap `-` for `*`; only `-` used to declare."""
    p = _ledger(tmp_path, f"{marker} **E1-H9 slug** - prose\n", name=f"b{marker!r}.md")
    assert [h.hid for h in _parse(p)] == ["E1-H9"]


def test_bolded_heading_id_declares(tmp_path):
    p = _ledger(tmp_path, "### **E30-H107** bolded-id\n\n- **Verdict** - Ships; 1.0\n")
    hyps = _parse(p)
    assert [h.hid for h in hyps] == ["E30-H107"]
    assert hyps[0].slug == "bolded-id"


def test_unparsed_declaration_makes_next_id_refuse(tmp_path, capsys):
    """The safety net: an id shape the parser cannot read must be LOUD.

    Widening regexes fixes the shapes we thought of; this catches the ones we
    did not, which is the whole failure class.
    """
    p = _ledger(
        tmp_path,
        "### E1-H1 fine\n\n- **Verdict** - Ships; 1\n\n- **Round E9-H99 alignment** - prose\n",
    )
    assert main(["next-id", str(p)]) == 1
    err = capsys.readouterr().err
    assert "E9-H99" in err and "did not parse" in err
    assert main(["check", str(p)]) == 1


def test_unterminated_fence_is_loud_not_silent(tmp_path, capsys):
    """One unclosed fence blanked every hypothesis below it, silently."""
    p = _ledger(tmp_path, "```bash\necho hi\n\n### E1-H5 alpha\n\n- **Verdict** - Ships; 1\n")
    assert main(["next-id", str(p)]) == 1
    assert "never closed" in capsys.readouterr().err
    assert main(["check", str(p)]) == 1


def test_mismatched_fence_char_does_not_close(tmp_path):
    """A ``` line inside a ~~~ block is literal content, not a terminator."""
    text = f"# L\n\n{MARKER}\n\n~~~text\n```\n~~~\n\n### E1-H2 after\n\n- **Verdict** - Ships; 1\n"
    assert [h.hid for h in parse_ledger(text)] == ["E1-H2"]


def test_same_id_declared_twice_is_an_error(tmp_path, capsys):
    """The duplicate-ordinal check could not see it - both share one id."""
    p = _ledger(
        tmp_path,
        "### E1-H7 first\n\n- **Verdict** - Ships; 1\n\n### E1-H7 second\n\n- **Verdict** - Refuted; 0\n",
    )
    assert main(["check", str(p)]) == 1
    assert "declared twice" in capsys.readouterr().err


def test_next_batch_is_deterministic_when_e_and_r_tie(tmp_path, capsys):
    """Iterating a set let E12/R12 resolve differently run to run."""
    p = _ledger(
        tmp_path,
        "### E12-H1 a\n\n- **Verdict** - Ships; 1\n\n### R12-H2 b\n\n- **Verdict** - Ships; 1\n",
    )
    seen = set()
    for _ in range(10):
        assert main(["next-id", str(p)]) == 0
        seen.add(
            next(x for x in capsys.readouterr().out.splitlines() if x.startswith("next_batch"))
        )
    assert len(seen) == 1, f"next_batch is nondeterministic: {seen}"


def test_nested_hypothesis_does_not_donate_its_verdict_upward(tmp_path):
    """The parent reported a verdict it never recorded - a fabricated answer."""
    p = _ledger(
        tmp_path,
        "## E1-H1 parent\n\n- **Hypothesis** - x\n\n### E1-H2 child\n\n- **Verdict** - Refuted; 0\n",
    )
    hyps = {h.hid: h for h in _parse(p)}
    assert hyps["E1-H2"].verdict == "Refuted"
    assert hyps["E1-H1"].verdict is None, "a nested child's verdict leaked into its parent"


def test_a_summary_bullet_does_not_outrank_the_block_it_summarises(tmp_path):
    """First-occurrence-declares silently favoured the LEAST informative one."""
    p = _ledger(
        tmp_path,
        "## Executive summary\n\n- **E12-H33 int4** - ships\n\n### E12-H33 llama-int4\n\n"
        "- **Verdict** - Confirmed; 2.27x\n",
    )
    hyps = _parse(p)
    assert len(hyps) == 1
    assert hyps[0].shape == "full"
    assert hyps[0].verdict == "Confirmed"


def test_show_stops_at_the_next_compact_sibling(tmp_path, capsys):
    p = _ledger(
        tmp_path,
        "### E5-H10 target\n\n- **Verdict** - Ships; 1\n\n- **E5-H11 variant-a** - prose\n",
    )
    assert main(["show", str(p), "E5-H10"]) == 0
    out = capsys.readouterr().out
    assert "E5-H11" not in out, "show bled into the following hypothesis"


def test_an_empty_field_bullet_counts_as_missing(tmp_path, capsys):
    """`- **Verdict** -` left the key present and the value blank, so it
    satisfied the missing-field check and the vocabulary check at once."""
    p = _ledger(tmp_path, "### E1-H1 slug\n\n- **Hypothesis** - x\n- **Verdict** -\n")
    assert main(["check", str(p)]) == 0
    # missing Verdict + missing Result = unrun, counted; a blank bullet read
    # as a recorded verdict would leave only `no Result` and no unrun count
    assert "1 unrun" in capsys.readouterr().out


def test_a_qualifier_on_verdict_is_not_an_error(tmp_path):
    """`ledger-queries.md` documents the qualifier as legal on ANY field."""
    p = _ledger(tmp_path, "### E1-H1 slug\n\n- **Verdict** (re-run 2026-08) - Ships; 1.5x\n")
    assert main(["check", str(p)]) == 0
    assert _parse(p)[0].verdict == "Ships"


def test_blocked_is_accepted(tmp_path):
    """The primary reference example declares it in its own verdict head."""
    assert "Blocked" in VERDICTS
    p = _ledger(tmp_path, "### E1-H1 slug\n\n- **Verdict** - Blocked; sm_120 wall\n")
    assert main(["check", str(p)]) == 0


def test_unknown_verdict_filter_exits_two(capsys):
    """An empty table for a typo is indistinguishable from a genuine zero."""
    assert main(["list", str(WMD), "--verdict", "Nonsense"]) == 2
    assert "is not a verdict label" in capsys.readouterr().err


def test_non_utf8_ledger_fails_cleanly(tmp_path, capsys):
    p = tmp_path / "latin.md"
    p.write_bytes("# L\n\n### E1-H1 caf\xe9\n".encode("latin-1"))
    assert main(["check", str(p)]) == 1
    assert "not valid UTF-8" in capsys.readouterr().err


# --- Re-confirm round regressions ------------------------------------------
#
# Every test below pins a defect the fixes ABOVE introduced. A remedy is new
# review surface, so these are the ones that matter most: the orphan net that
# fired on citations, and the block boundary that ate a hypothesis's verdict.


def test_an_id_cited_in_a_field_value_is_not_a_failed_declaration(tmp_path):
    """The orphan net refused a legal ledger on its own template's wording.

    `- **Log** - ... new round E31-H120` is the template's own Log example.
    Scanning the whole line made every citation look like a broken
    declaration, so `next-id` - the load-bearing command - hard-refused.
    """
    p = _ledger(
        tmp_path,
        "### E1-H1 slug\n\n- **Lever** - reuses the cut proven in R9-H21\n"
        "- **Log** - 2026-07-20 - batch 256, new round E31-H120\n"
        "- **Verdict** - Ships; 1.2x\n",
    )
    assert main(["next-id", str(p)]) == 0
    assert main(["check", str(p)]) == 0


def test_a_multi_id_row_inside_a_block_does_not_truncate_it(tmp_path):
    """`_read_block` and `parse_ledger` must agree on what declares.

    Only the parser applied the multi-id guard, so a timing row that declares
    nothing still ended the block - and the hypothesis lost its own Verdict.
    """
    p = _ledger(
        tmp_path,
        "### E1-H1 slug\n\n- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair\n"
        "- **Verdict** - Ships; 1.2x\n",
    )
    hyps = _parse(p)
    assert len(hyps) == 1
    assert hyps[0].verdict == "Ships", "a citation row swallowed the block's verdict"


def test_setext_declaration_is_reported_not_dropped(tmp_path, capsys):
    """A pandoc round-trip can turn `## E1-H50 x` into a setext heading.

    The net had the same blind spot as the parser it guards, and the docs
    claimed otherwise - so the claim was false as well as the behaviour.
    """
    p = _ledger(
        tmp_path, "### E1-H1 a\n\n- **Verdict** - Ships; 1\n\nE1-H50 setext-decl\n-------\n"
    )
    assert main(["next-id", str(p)]) == 1
    assert "E1-H50" in capsys.readouterr().err


def test_level_one_heading_declaration_is_reported(tmp_path, capsys):
    p = _ledger(tmp_path, "### E1-H1 a\n\n- **Verdict** - Ships; 1\n\n# E1-H60 level-one\n")
    assert main(["next-id", str(p)]) == 1
    assert "E1-H60" in capsys.readouterr().err


def test_a_qualifier_does_not_smuggle_an_empty_field_past_check(tmp_path, capsys):
    """`- **Acceptance bar** (v2) -` stored "(v2)", which is non-empty.

    The empty-value fix was defeated by the qualifier fix - a blank
    pre-registration passed clean again.
    """
    p = _ledger(tmp_path, "### E1-H1 s\n\n- **Acceptance bar** (v2) -\n- **Verdict** - Ships; 1\n")
    assert main(["check", str(p)]) == 0
    assert "Acceptance bar" in capsys.readouterr().err


@pytest.mark.parametrize("command", [["list"], ["show", "E1-H5"], ["check"], ["next-id"]])
def test_every_command_refuses_through_an_unterminated_fence(tmp_path, capsys, command):
    """`list` under-counted the tally and `show` reported a present
    hypothesis as missing - only next-id and check had been guarded."""
    p = _ledger(tmp_path, "```bash\necho hi\n\n### E1-H5 alpha\n\n- **Verdict** - Ships; 1\n")
    argv = [command[0], str(p)] + command[1:]
    assert main(argv) == 1
    assert "never closed" in capsys.readouterr().err


def test_star_field_bullets_parse(tmp_path):
    """Declarations accepted `*`; fields did not, so every field vanished."""
    p = _ledger(tmp_path, "### E1-H1 s\n\n* **Verdict** - Ships; 1\n")
    assert _parse(p)[0].verdict == "Ships"


def test_a_field_written_as_sub_bullets_is_not_reported_missing(tmp_path, capsys):
    """The template renders `Log` as indented sub-bullets; the empty-value
    fix read the parent bullet as blank."""
    p = _ledger(
        tmp_path,
        "### E1-H1 s\n\n- **Acceptance bar**\n  - DR >= 1.5x baseline\n- **Verdict** - Ships; 1\n",
    )
    main(["check", str(p)])
    assert "Acceptance bar" not in capsys.readouterr().err


# --- Round-3 regressions: the FALSE-NEGATIVE direction ----------------------
#
# Rounds 1-3 each shipped a narrowing of `find_orphan_ids` that fixed a false
# positive and opened a silent drop, because every test pinned only the
# "citations stay clean" direction. These pin the other one: a near-miss
# declaration must be LOUD. That asymmetry, not any single regex, was the bug.


@pytest.mark.parametrize(
    ("shape", "why"),
    [
        # The id must sit AFTER the underscore, or a label class of `[^*_]*`
        # still captures it and the case passes against the broken build.
        # Mutation-proven: the earlier `Round E9-H99 turbo_throughput` wording
        # left `BOLD_LABEL_RE` free to regress with the suite green.
        ("- **turbo_throughput E9-H99 rerun** - prose", "underscore BEFORE the id"),
        ("- **Round _E9-H99_ rerun** - prose", "underscore-wrapped id, not at label start"),
        ("1. **E9-H99 slug** - prose", "ordered-list marker"),
        ("**E9-H99 unwrapped** - screened at the gate", "bold paragraph, no list marker"),
        ("- E9-H99 turbomind-throughput - screened", "bold dropped entirely"),
        ("- **E9-H99 *n*-gram cut** - prose", "emphasis inside the slug"),
        ("- **E9-H99 unclosed-bold slug - prose", "bold never closed"),
        ("- [ ] **E9-H99 checkbox** - prose", "task-list checkbox prefix"),
        ("- **_E9-H99 wrapped_** - prose", "underscore-wrapped id"),
        ("> - **E9-H99 quoted** - prose", "blockquote prefix"),
        ("# E9-H99 level-one", "level-1 heading"),
        ("- **E9-H99 vs E9-H100 combined** - both new this round", "two UNDECLARED ids"),
    ],
)
def test_a_near_miss_declaration_is_always_loud(tmp_path, capsys, shape, why):
    p = _ledger(tmp_path, f"### E1-H1 fine\n\n- **Verdict** - Ships; 1\n\n{shape}\n")
    assert main(["next-id", str(p)]) == 1, f"silent drop: {why}"
    assert "E9-H99" in capsys.readouterr().err


@pytest.mark.parametrize(
    "citation",
    [
        "- **Lever** - reuses the cut proven in R9-H21",
        "- **Log** - 2026-07-20 - batch 256, new round E31-H120",
        "- **Result** - the E30-H107b fallback showed the same failure",
        "- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair",
    ],
)
def test_a_citation_is_never_mistaken_for_a_declaration(tmp_path, citation):
    """The other half of the pair - narrowing must not swing back too far.

    The declaration is `E01-H1`, not `E1-H1`: the multi-id row cites that
    exact token, and a batch-token mismatch would make it a genuinely
    undeclared id, so the fixture would be testing the wrong thing.
    """
    p = _ledger(tmp_path, f"### E01-H1 slug\n\n{citation}\n- **Verdict** - Ships; 1\n")
    assert main(["next-id", str(p)]) == 0


@pytest.mark.parametrize(
    "prose",
    [
        "**Note** - E1-H1 was rerun at k=2",
        "**Round 3 (E1-H1 rerun)** - three levers",
        "__Result__ - see E1-H1 for the baseline",
    ],
)
def test_bold_prose_citing_a_declared_id_is_not_a_declaration(tmp_path, prose):
    """Dropping the list-marker requirement must not turn ordinary bold prose
    into a false refusal - the id is cited, not declared."""
    p = _ledger(tmp_path, f"### E1-H1 slug\n\n- **Verdict** - Ships; 1\n\n{prose}\n")
    assert main(["next-id", str(p)]) == 0


def test_a_loose_nested_list_field_is_not_reported_missing(tmp_path, capsys):
    """A blank line before nested items is valid CommonMark and what several
    formatters emit; it read as an empty pre-registered bar."""
    p = _ledger(
        tmp_path,
        "### E1-H1 s\n\n- **Acceptance bar** -\n\n    - DR >= 0.2\n- **Verdict** - Ships; 1\n",
    )
    main(["check", str(p)])
    assert "Acceptance bar" not in capsys.readouterr().err


# --- Table-declared hypotheses ---------------------------------------------
#
# One real store declares most of its hypotheses nowhere but in per-batch
# at-a-glance tables. A row declares only when the table's header names
# hypothesis columns, so a timing table can never mint a phantom.

AT_A_GLANCE = (
    "## E14 at a glance\n\n"
    "| id | claim (what is under test) | evidence | verdict |\n"
    "|---|---|---|---|\n"
    "| E14-H46 | no single lever reverses | best lever -50% | SUPPORTED |\n"
    "| E14-H47 | a bundle reverses | +129% | REFUTED |\n"
)


def test_an_at_a_glance_row_declares_with_its_verdict(tmp_path, capsys):
    p = _ledger(tmp_path, AT_A_GLANCE)
    hyps = parse_ledger(p.read_text(encoding="utf-8"))
    assert [(h.hid, h.shape, h.verdict) for h in hyps] == [
        ("E14-H46", "table", "SUPPORTED"),
        ("E14-H47", "table", "Refuted"),
    ]
    assert hyps[0].fields["Hypothesis"] == "no single lever reverses"
    assert main(["check", str(p)]) == 0
    assert "declared only by a table row" in capsys.readouterr().err


def test_a_timing_table_declares_nothing(tmp_path, capsys):
    """Header `| id | ms/pair |` maps to no hypothesis field, so its rows are
    citations - and an id declared nowhere else is an orphan, not a phantom."""
    p = _ledger(tmp_path, "## timings\n\n| id | ms/pair |\n|---|---|\n| E1-H9 | 0.08 |\n")
    assert parse_ledger(p.read_text(encoding="utf-8")) == []
    assert main(["check", str(p)]) == 1
    assert "E1-H9" in capsys.readouterr().err


def test_a_full_block_outranks_its_table_row():
    text = AT_A_GLANCE + "\n### E14-H47 a-bundle-reverses\n\n- **Verdict** - Confirmed; +129%\n"
    h47 = next(h for h in parse_ledger(text) if h.hid == "E14-H47")
    assert (h47.shape, h47.verdict) == ("full", "Confirmed")


def test_an_escaped_pipe_does_not_shift_the_verdict_column():
    text = (
        "| id | claim | evidence | verdict |\n|---|---|---|---|\n"
        "| E35-H339 | operator is inert | max\\|ΔTFR\\| = 0 on the anchor | REFUTED |\n"
    )
    (h,) = parse_ledger(text)
    assert h.verdict == "Refuted"  # canonical spelling, normalized from REFUTED


# --- register ---------------------------------------------------------------


def test_register_appends_a_parseable_block_and_burns_the_next_ordinal(tmp_path, capsys):
    p = _writable(tmp_path, "## E1\n\n### E1-H1 first\n\n- **Verdict** - Ships; 1\n")
    assert (
        main(
            [
                "register",
                str(p),
                "--author",
                "@kj",
                "--slug",
                "gate-cheap-kill",
                "--field",
                "Hypothesis=because the gate is cheap, killing early saves the run",
                "--field",
                "Prediction=kill rate >= 30%",
                "--field",
                "Persona=contrarian",
            ]
        )
        == 0
    )
    assert "registered E1-H2" in capsys.readouterr().out
    body = p.read_text(encoding="utf-8")
    assert "### E1-H2 gate-cheap-kill" in body
    # canonical order first, unknown fields after
    assert body.index("**Hypothesis**") < body.index("**Prediction**") < body.index("**Persona**")
    assert main(["next-id", str(p)]) == 0
    assert "next_h: H3" in capsys.readouterr().out


def test_register_opens_the_next_batch_with_its_heading(tmp_path):
    p = _writable(tmp_path, "## E01\n\n### E01-H1 first\n\n- **Verdict** - Ships; 1\n")
    main(
        [
            "register",
            str(p),
            "--author",
            "@kj",
            "--new-batch",
            "--batch-slug",
            "gate levers",
            "--slug",
            "s",
            "--field",
            "Hypothesis=x",
        ]
    )
    body = p.read_text(encoding="utf-8")
    assert "## E02 - gate levers" in body
    assert "### E02-H2 s" in body


def test_register_refuses_an_outcome_field(tmp_path, capsys):
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Verdict** - Ships; 1\n")
    assert (
        main(
            [
                "register",
                str(p),
                "--author",
                "@kj",
                "--slug",
                "s",
                "--field",
                "Verdict=Confirmed; 1",
            ]
        )
        == 2
    )
    assert "precedes its outcome" in capsys.readouterr().err
    assert "Confirmed" not in p.read_text(encoding="utf-8").split("### E1-H1")[0]


def test_register_refuses_while_a_declaration_is_unparsed(tmp_path, capsys):
    """The same refusal as next-id: writing past an unparsed id burns an
    ordinal twice."""
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Verdict** - Ships; 1\n\n# E1-H2 broken\n")
    before = p.read_text(encoding="utf-8")
    assert (
        main(["register", str(p), "--author", "@kj", "--slug", "s", "--field", "Hypothesis=x"])
        == 1
    )
    assert "refusing -" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


# --- result / verdict / log-event -------------------------------------------


def _registered(tmp_path):
    p = _writable(
        tmp_path,
        "### E1-H1 s\n\n- **Hypothesis** - x\n- **Acceptance bar** - DR >= 1.5x\n",
    )
    return p


def test_result_then_verdict_land_in_canonical_order(tmp_path):
    p = _registered(tmp_path)
    assert main(["result", str(p), "E1-H1", "--text", "DR 2.7x, V = 0", "--author", "@kj"]) == 0
    assert (
        main(["verdict", str(p), "E1-H1", "--text", "Confirmed; DR 2.7x", "--author", "@kj"]) == 0
    )
    body = p.read_text(encoding="utf-8")
    assert body.index("**Acceptance bar**") < body.index("**Result**") < body.index("**Verdict**")
    (h,) = parse_ledger(body)
    assert h.verdict == "Confirmed"


def test_a_recorded_result_is_immutable_and_a_second_needs_a_qualifier(tmp_path, capsys):
    p = _registered(tmp_path)
    main(["result", str(p), "E1-H1", "--text", "DR 2.7x", "--author", "@kj"])
    assert main(["result", str(p), "E1-H1", "--text", "DR 2.9x", "--author", "@kj"]) == 2
    assert "immutable" in capsys.readouterr().err
    assert (
        main(
            [
                "result",
                str(p),
                "E1-H1",
                "--text",
                "DR 2.9x",
                "--qualifier",
                "re-run b256",
                "--author",
                "@kj",
            ]
        )
        == 0
    )
    body = p.read_text(encoding="utf-8")
    assert "- **Result** - DR 2.7x" in body
    assert "- **Result (re-run b256)** - DR 2.9x" in body


def test_a_recorded_verdict_refuses_a_second(tmp_path, capsys):
    p = _registered(tmp_path)
    main(["verdict", str(p), "E1-H1", "--text", "Refuted; DR 0.9x", "--author", "@kj"])
    assert (
        main(["verdict", str(p), "E1-H1", "--text", "Confirmed; DR 2.7x", "--author", "@kj"]) == 2
    )
    assert "a flip is a new round" in capsys.readouterr().err
    assert "Confirmed" not in p.read_text(encoding="utf-8")


def test_verdict_refuses_an_unreadable_label_and_notes_a_grown_one(tmp_path, capsys):
    p = _registered(tmp_path)
    assert (
        main(
            [
                "verdict",
                str(p),
                "E1-H1",
                "--text",
                "went fine at k=1, worse at k=3",
                "--author",
                "@kj",
            ]
        )
        == 2
    )
    assert "no readable label" in capsys.readouterr().err
    assert (
        main(["verdict", str(p), "E1-H1", "--text", "SUPPORTED; 4/4 windows", "--author", "@kj"])
        == 0
    )
    assert "not canonical" in capsys.readouterr().err


def test_writes_refuse_a_table_declared_hypothesis(tmp_path, capsys):
    p = _writable(tmp_path, AT_A_GLANCE)
    assert main(["verdict", str(p), "E14-H46", "--text", "Confirmed; 1", "--author", "@kj"]) == 1
    assert "table row" in capsys.readouterr().err


def test_log_event_creates_then_appends_newest_last(tmp_path):
    p = _registered(tmp_path)
    _log(p, "E1-H1", "first run, b128 - 2,910 tok/s", "2026-07-10")
    _log(p, "E1-H1", "re-ran after padding fix", "2026-07-14")
    body = p.read_text(encoding="utf-8")
    assert body.count("- **Log**") == 1
    assert body.index("2026-07-10") < body.index("2026-07-14")
    assert "  - log: 2026-07-14 @kj - re-ran after padding fix" in body


# --- report and values -------------------------------------------------------


def test_report_tallies_batches_down_and_verdicts_across(tmp_path, capsys):
    p = _ledger(
        tmp_path,
        "### E1-H1 a\n\n- **Verdict** - Confirmed; 1\n\n"
        "### E1-H2 b\n\n- **Verdict** - SUPPORTED\n\n"
        "### E2-H3 c\n\n- **Hypothesis** - open\n",
    )
    assert main(["report", str(p)]) == 0
    out = capsys.readouterr().out
    assert "| Batch | N | Confirmed | SUPPORTED | other | unverdicted |" in out
    assert "| E1 | 2 | 1 | 1 |  |  |" in out
    assert "| E2 | 1 |  |  |  | 1 |" in out
    assert "| **Total** | 3 | 1 | 1 |  | 1 |" in out


def test_values_reads_a_quantity_off_every_block(tmp_path, capsys):
    p = _ledger(
        tmp_path,
        "### E1-H1 a\n\n- **Result** - `DR` 0.2286 = 2.7x baseline, margin `+18.48`\n"
        "- **Verdict** - Confirmed; DR 2.7x\n\n"
        "### E1-H2 b\n\n- **Result** (k=1) - DR 0.180, pop residual < 0.58%\n"
        "- **Verdict** - Refuted; theta(0.08) = 0.7644\n",
    )
    assert main(["values", str(p), "DR"]) == 0
    out = capsys.readouterr().out
    assert "0.2286" in out and "0.180" in out
    assert "E1-H1" in out and "E1-H2" in out
    main(["values", str(p), "pop residual"])
    assert "< 0.58%" in capsys.readouterr().out
    main(["values", str(p), "theta"])
    assert "0.7644" in capsys.readouterr().out
    main(["values", str(p), "margin"])
    assert "+18.48" in capsys.readouterr().out


def test_values_restricts_by_batch_and_id_and_says_when_dry(tmp_path, capsys):
    p = _ledger(
        tmp_path,
        "### E1-H1 a\n\n- **Result** - DR 0.1\n\n### E2-H2 b\n\n- **Result** - DR 0.2\n",
    )
    main(["values", str(p), "DR", "--batch", "E2"])
    out = capsys.readouterr().out
    assert "0.2" in out and "0.1" not in out
    main(["values", str(p), "DR", "--id", "E1-H1"])
    out = capsys.readouterr().out
    assert "0.1" in out and "0.2" not in out
    main(["values", str(p), "gold_full"])
    assert "no readings of 'gold_full'" in capsys.readouterr().out


# --- authorship --------------------------------------------------------------


def test_author_creates_the_roster_above_the_first_round(tmp_path, capsys):
    """The roster is document metadata, so it lands under the overview and
    above the rounds - never between a round heading and its hypotheses."""
    p = _ledger(tmp_path, "## E1\n\n### E1-H1 first\n\n- **Verdict** - Ships; 1\n")
    assert main(["author", str(p), "--handle", "kj", "--name", "Konrad Jelen"]) == 0
    assert "roster created" in capsys.readouterr().out
    body = p.read_text(encoding="utf-8")
    assert body.index("## Authors") < body.index("## E1")
    assert "- `@kj` Konrad Jelen" in body
    # a second call for the same handle updates the entry, never doubles it
    assert main(["author", str(p), "--handle", "@kj", "--name", "K. Jelen"]) == 0
    body = p.read_text(encoding="utf-8")
    assert body.count("`@kj`") == 1
    assert "- `@kj` K. Jelen" in body
    # and the ledger still parses - the roster is not a declaration
    assert [h.hid for h in parse_ledger(body)] == ["E1-H1"]


def test_a_second_author_joins_the_roster(tmp_path):
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Hypothesis** - x\n")
    assert main(["author", str(p), "--handle", "@ab", "--name", "Ada B"]) == 0
    body = p.read_text(encoding="utf-8")
    assert "- `@kj` Konrad Jelen" in body and "- `@ab` Ada B" in body


def test_every_write_refuses_a_handle_that_is_not_on_the_roster(tmp_path, capsys):
    """A handle nobody is rostered for is a typo far more often than a new
    researcher, and after the fact the ledger cannot tell them apart."""
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Hypothesis** - x\n")
    before = p.read_text(encoding="utf-8")
    for argv in (
        ["register", str(p), "--slug", "s", "--field", "Hypothesis=x", "--author", "@zz"],
        ["result", str(p), "E1-H1", "--text", "DR 2.7x", "--author", "@zz"],
        ["verdict", str(p), "E1-H1", "--text", "Confirmed; 1", "--author", "@zz"],
        ["field", str(p), "E1-H1", "--name", "Grounding", "--text", "x", "--author", "@zz"],
        ["log-event", str(p), "E1-H1", "--event", "x", "--author", "@zz"],
    ):
        assert main(argv) == 2, f"{argv[0]} accepted an unrostered handle"
        assert "not on the ## Authors roster" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


def test_a_malformed_handle_is_refused_before_the_roster_is_read(tmp_path, capsys):
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Hypothesis** - x\n")
    assert main(["result", str(p), "E1-H1", "--text", "x", "--author", "@Konrad"]) == 2
    assert "bad handle" in capsys.readouterr().err


def test_every_write_stamps_an_authored_log_line(tmp_path):
    """The audit trail IS the provenance - nothing else records who wrote
    what, so a write that skips it loses the fact permanently."""
    p = _writable(tmp_path, "## E1\n\n### E1-H1 first\n\n- **Verdict** - Ships; 1\n")
    main(["register", str(p), "--slug", "s", "--field", "Hypothesis=x", "--author", "@kj"])
    main(["result", str(p), "E1-H2", "--text", "DR 2.7x", "--author", "@kj"])
    main(["verdict", str(p), "E1-H2", "--text", "Confirmed; DR 2.7x", "--author", "@kj"])
    main(
        ["field", str(p), "E1-H2", "--name", "Persona", "--text", "contrarian", "--author", "@kj"]
    )
    block = next(h for h in parse_ledger(p.read_text(encoding="utf-8")) if h.hid == "E1-H2").block
    logged = [ln.split("@kj - ", 1)[1] for ln in block.splitlines() if "- log:" in ln]
    assert logged == [
        "registered",
        "result recorded",
        "verdict recorded: Confirmed",
        "field Persona added",
    ]
    assert block.count("- **Log**") == 1
    assert all("@kj" in ln for ln in block.splitlines() if "- log:" in ln)


def test_a_qualified_result_names_its_qualifier_in_the_audit_line(tmp_path):
    p = _registered(tmp_path)
    main(["result", str(p), "E1-H1", "--text", "DR 2.7x", "--author", "@kj"])
    main(
        [
            "result",
            str(p),
            "E1-H1",
            "--text",
            "DR 2.9x",
            "--qualifier",
            "re-run b256",
            "--author",
            "@kj",
        ]
    )
    body = p.read_text(encoding="utf-8")
    assert "result recorded (re-run b256)" in body


def test_list_filters_by_author(tmp_path, capsys):
    p = _writable(tmp_path, "### E1-H1 old\n\n- **Hypothesis** - x\n")
    main(["author", str(p), "--handle", "@ab", "--name", "Ada B"])
    main(["register", str(p), "--slug", "mine", "--field", "Hypothesis=x", "--author", "@kj"])
    main(["register", str(p), "--slug", "theirs", "--field", "Hypothesis=x", "--author", "@ab"])
    capsys.readouterr()  # the register lines name both ids; only the list is under test
    assert main(["list", str(p), "--author", "kj"]) == 0
    out = capsys.readouterr().out
    assert "E1-H2" in out and "E1-H3" not in out and "E1-H1" not in out
    assert main(["list", str(p), "--author", "@ab", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [r["id"] for r in payload] == ["E1-H3"]
    assert payload[0]["author"] == "@ab"


def test_check_warns_once_on_unauthored_lines_and_errors_on_an_unknown_handle(tmp_path, capsys):
    """Thousands of unauthored lines are legitimate history in the ledgers
    that predate the roster - one aggregated warning, never an error each."""
    p = _writable(
        tmp_path,
        "### E1-H1 s\n\n- **Hypothesis** - x\n- **Log**\n"
        "  - log: 2026-07-10 - first run\n"
        "  - log: 2026-07-11 - second run\n"
        "  - log: 2026-07-12 @zz - by a stranger\n",
    )
    assert main(["check", str(p)]) == 1
    err = capsys.readouterr().err
    assert err.count("carry no @handle") == 1
    assert "2 log lines carry no @handle" in err
    assert "@zz is not on the ## Authors roster" in err


# --- field -------------------------------------------------------------------


def test_field_adds_a_free_form_field_before_the_outcomes(tmp_path):
    """The template's field set is a checklist, not a form - the real ledgers
    carry 520 field names of their own."""
    p = _registered(tmp_path)
    main(["result", str(p), "E1-H1", "--text", "DR 2.7x", "--author", "@kj"])
    assert (
        main(
            [
                "field",
                str(p),
                "E1-H1",
                "--name",
                "Grounding",
                "--text",
                "SOTA x",
                "--author",
                "@kj",
            ]
        )
        == 0
    )
    body = p.read_text(encoding="utf-8")
    assert (
        body.index("**Acceptance bar**") < body.index("**Grounding**") < body.index("**Result**")
    )
    (h,) = parse_ledger(body)
    assert h.fields["Grounding"] == "SOTA x"


def test_field_refuses_to_overwrite_without_update(tmp_path, capsys):
    p = _registered(tmp_path)
    main(["field", str(p), "E1-H1", "--name", "Status", "--text", "open", "--author", "@kj"])
    assert (
        main(["field", str(p), "E1-H1", "--name", "Status", "--text", "closed", "--author", "@kj"])
        == 2
    )
    assert "pass --update" in capsys.readouterr().err
    assert "**Status** - open" in p.read_text(encoding="utf-8")
    assert (
        main(
            [
                "field",
                str(p),
                "E1-H1",
                "--name",
                "Status",
                "--text",
                "closed",
                "--update",
                "--author",
                "@kj",
            ]
        )
        == 0
    )
    body = p.read_text(encoding="utf-8")
    assert "**Status** - closed" in body
    assert body.count("**Status**") == 1
    assert "field Status updated" in body


def test_field_keeps_a_qualifier_when_it_updates(tmp_path):
    """`- **Acceptance bar** (v2)` is that field with a qualifier; rewriting
    the label would change what the field is."""
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Acceptance bar** (v2) - DR >= 1.5x\n")
    assert (
        main(
            [
                "field",
                str(p),
                "E1-H1",
                "--name",
                "Acceptance bar",
                "--text",
                "DR >= 2.0x",
                "--update",
                "--author",
                "@kj",
            ]
        )
        == 0
    )
    assert "- **Acceptance bar** (v2) - DR >= 2.0x" in p.read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["Result", "verdict", "Log"])
def test_field_refuses_an_outcome_name(tmp_path, capsys, name):
    """Each outcome has its own command and its own immutability rule;
    reaching them through `field` would route around both."""
    p = _registered(tmp_path)
    before = p.read_text(encoding="utf-8")
    assert main(["field", str(p), "E1-H1", "--name", name, "--text", "x", "--author", "@kj"]) == 2
    assert "own command" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


def test_field_refuses_a_table_declared_hypothesis(tmp_path, capsys):
    p = _writable(tmp_path, AT_A_GLANCE)
    assert (
        main(["field", str(p), "E14-H46", "--name", "Persona", "--text", "x", "--author", "@kj"])
        == 1
    )
    assert "table row" in capsys.readouterr().err


# --- round-1 adversarial review fixes ----------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["register", "--slug", "s\n### E9-H99 forged", "--field", "Hypothesis=x"],
        ["register", "--slug", "s", "--field", "Hypothesis=a\n### E9-H99 forged"],
        ["result", "E1-H1", "--text", "DR 2.7x\n\n### E9-H99 forged"],
        ["verdict", "E1-H1", "--text", "Confirmed; 1\n### E9-H99 forged"],
        ["field", "E1-H1", "--name", "Note", "--text", "see\n### E9-H99 forged"],
        ["field", "E1-H1", "--name", "No\nte", "--text", "x"],
        ["log-event", "E1-H1", "--event", "ran\n### E9-H99 forged"],
    ],
)
def test_a_newline_in_any_written_value_is_refused(tmp_path, capsys, argv):
    """A value is embedded as ONE line of the ledger, so a newline splits the
    block: the forged id below minted a hypothesis nobody registered, handed it
    the real one's Result and Verdict, burnt an ordinal - and `check` reported
    the file clean. Every write command, one guard."""
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Hypothesis** - x\n")
    before = p.read_text(encoding="utf-8")
    cmd, rest = argv[0], argv[1:]
    assert main([cmd, str(p), *rest, "--author", "@kj"]) == 2
    assert "single line" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before
    assert [h.hid for h in parse_ledger(before)] == ["E1-H1"]


def test_a_bare_bold_h_bullet_still_claims_its_ordinal(tmp_path, capsys):
    """`- **H655** - ...` is how a real 6,432-line ledger writes a gated
    registration. It carries no batch prefix, so neither the parser nor the
    orphan net sees it - and `next-id` handed back an ordinal the document had
    already assigned. Counted, not refused: refusing would block every read and
    write on that ledger until 25 recorded lines were rewritten by hand."""
    p = _writable(
        tmp_path,
        "### E1-H1 first\n\n- **Hypothesis** - x\n\n"
        "### E1-H2 gated-registrations\n\n"
        "- **H655** - cross-query associative memory\n"
        "- **H656** - ingest-time answerable-question nodes\n",
    )
    assert main(["next-id", str(p)]) == 0
    assert "next_h: H657" in capsys.readouterr().out
    assert (
        main(["register", str(p), "--slug", "after", "--field", "Hypothesis=x", "--author", "@kj"])
        == 0
    )
    assert "registered E1-H657" in capsys.readouterr().out


def test_a_prose_citation_of_a_bare_ordinal_does_not_claim_it(tmp_path, capsys):
    """The claim is scoped to a bullet's bold label, so a sentence about H655
    cannot silently skip 600 ordinals."""
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Result** - H655 recovers 92/110, see H700\n")
    assert main(["next-id", str(p)]) == 0
    assert "next_h: H2" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["Verdict (2026-09-01)", "Result (rerun)", "Log (old)"])
def test_a_parenthesised_outcome_name_is_still_an_outcome(tmp_path, capsys, name):
    """The parser strips a trailing parenthetical when it decides what a field
    IS, so a guard that tests the raw name lets `Verdict (2026-09-01)` past -
    and it lands ABOVE the recorded verdict, where first-wins makes the new
    text the verdict every reader sees."""
    p = _writable(
        tmp_path,
        "### E1-H1 s\n\n- **Hypothesis** - x\n- **Verdict** - Confirmed; DR 2.7x\n",
    )
    before = p.read_text(encoding="utf-8")
    assert (
        main(
            [
                "field",
                str(p),
                "E1-H1",
                "--name",
                name,
                "--text",
                "Refuted; re-read",
                "--author",
                "@kj",
            ]
        )
        == 2
    )
    assert "own command" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before
    (h,) = parse_ledger(before)
    assert h.verdict == "Confirmed"


def test_register_refuses_a_parenthesised_outcome_field(tmp_path, capsys):
    p = _writable(tmp_path, "### E1-H1 s\n\n- **Hypothesis** - x\n")
    assert (
        main(
            [
                "register",
                str(p),
                "--slug",
                "s",
                "--field",
                "Verdict (interim)=Confirmed; 1",
                "--author",
                "@kj",
            ]
        )
        == 2
    )
    assert "precedes its outcome" in capsys.readouterr().err


def test_verdict_refuses_an_empty_placeholder_bullet(tmp_path, capsys):
    """Guarding on the field VALUE let an empty `- **Verdict** -` through: the
    write reported success, first-wins kept the blank bullet as the canonical
    verdict, `list` still read unverdicted, and the guard never fired again -
    three calls stacked three Verdict bullets."""
    p = _writable(
        tmp_path,
        "### E1-H1 s\n\n- **Hypothesis** - x\n- **Result** -\n- **Verdict** -\n",
    )
    before = p.read_text(encoding="utf-8")
    assert (
        main(["verdict", str(p), "E1-H1", "--text", "Confirmed; DR 1.8x", "--author", "@kj"]) == 2
    )
    err = capsys.readouterr().err
    assert "already carries a Verdict bullet" in err and "empty" in err
    assert p.read_text(encoding="utf-8") == before


def test_a_fenced_roster_grants_nobody_write_authority(tmp_path, capsys):
    """A ledger that documents the roster format in a ```markdown example must
    not thereby roster the handle in the example."""
    p = _ledger(
        tmp_path,
        "```markdown\n## Authors\n\n- `@ab` Ada B\n```\n\n### E1-H1 s\n\n- **Hypothesis** - x\n",
    )
    assert main(["log-event", str(p), "E1-H1", "--event", "x", "--author", "@ab"]) == 2
    assert "not on the ## Authors roster" in capsys.readouterr().err


def test_a_fence_inside_the_roster_section_does_not_empty_it(tmp_path):
    """The mirror case, and the worse one: reading raw, a fenced example inside
    a real `## Authors` section refused every write by the author on it."""
    p = _ledger(
        tmp_path,
        "## Authors\n\n- `@kj` Konrad Jelen\n\n```markdown\n- `@xx` Example Entry\n```\n\n"
        "### E1-H1 s\n\n- **Hypothesis** - x\n",
    )
    assert main(["log-event", str(p), "E1-H1", "--event", "x", "--author", "@kj"]) == 0
    assert main(["author", str(p), "--handle", "@ab", "--name", "Ada B"]) == 0
    body = p.read_text(encoding="utf-8")
    assert "- `@xx` Example Entry" in body  # the fenced example is untouched, never updated
    assert body.index("- `@ab` Ada B") < body.index("### E1-H1")  # inside the Authors section
    assert set(roster_of(body)) == {"@kj", "@ab"}


# --- confirming-round fixes ---------------------------------------------------


@pytest.mark.parametrize("brk", ["\r", "\v", "\f", "\x1c", "\x85", " ", " "])
def test_any_line_break_is_refused_not_only_the_newline(tmp_path, capsys, brk):
    """The guard tested `"\\n" in value` while the parser splits with
    `str.splitlines()`, which breaks on nine characters. A bare CR - what a
    captured run log or a PDF paste carries - minted a phantom hypothesis
    exactly as the newline did. Guard and mechanism must ask one question."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Hypothesis** - x\n")
    before = p.read_text(encoding="utf-8")
    assert (
        main(
            [
                "verdict",
                str(p),
                "E01-H1",
                "--text",
                f"Confirmed; 1{brk}### E09-H99 minted",
                "--author",
                "@kj",
            ]
        )
        == 2
    )
    assert "single line" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before
    assert [h.hid for h in parse_ledger(before)] == ["E01-H1"]


def test_a_qualified_name_finds_the_field_it_qualifies(tmp_path, capsys):
    """`_field_lines` keys by base name, so a raw-label lookup let
    `--name "Grounding (v2)"` miss the existing `Grounding` and append a second
    bullet the parser could never reach - with `--update` appending a third."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Hypothesis** - x\n- **Grounding** - original\n")
    assert (
        main(
            [
                "field",
                str(p),
                "E01-H1",
                "--name",
                "Grounding (v2)",
                "--text",
                "new",
                "--author",
                "@kj",
            ]
        )
        == 2
    )
    assert "pass --update" in capsys.readouterr().err
    assert (
        main(
            [
                "field",
                str(p),
                "E01-H1",
                "--name",
                "Grounding (v2)",
                "--text",
                "new",
                "--update",
                "--author",
                "@kj",
            ]
        )
        == 0
    )
    body = p.read_text(encoding="utf-8")
    assert body.count("**Grounding**") == 1
    (h,) = parse_ledger(body)
    assert h.fields["Grounding"] == "new"
    # the audit line names the bullet as written, not the key that found it
    assert "field Grounding updated" in body


def test_a_plain_bullet_outranks_a_qualified_one_already_stored(tmp_path):
    """A real ledger writes `- **Verdict (interim)**` ABOVE the `- **Verdict**`
    that supersedes it. First-wins alone reported the interim as the record:
    one kgf hypothesis read "gate PASSED decisively" while its own recorded
    verdict was "REFUTED by 1.7 pts". Confidently wrong on the round-state
    tally is what this parser refuses everywhere else."""
    p = _ledger(
        tmp_path,
        "### E01-H1 s\n\n"
        "- **Verdict (interim)** - Confirmed; gate passed\n"
        "- **Verdict** - Refuted; the adjudication clause fails by 1.7 pts\n"
        "- **Result (gate)** - DR 1.1x\n",
    )
    (h,) = parse_ledger(p.read_text(encoding="utf-8"))
    assert h.verdict == "Refuted"
    assert h.fields["Verdict"].startswith("Refuted")
    # and the qualified-only field is still recognised - that is what the fold buys
    assert h.fields["Result"] == "DR 1.1x"


# --- round-3 confirming fixes -------------------------------------------------


def test_the_reader_and_the_writer_agree_which_bullet_is_the_field(tmp_path):
    """`_read_block` preferred the plain bullet while `_field_lines` stayed
    first-wins, so `field --update` rewrote the SUPERSEDED bullet while every
    reader kept returning the plain one - the write was lost and the audit line
    reported success. The two must answer one question."""
    p = _writable(
        tmp_path,
        "### E01-H1 s\n\n"
        "- **Grounding (superseded)** - the old grounding\n"
        "- **Grounding** - the REAL grounding\n",
    )
    assert (
        main(
            [
                "field",
                str(p),
                "E01-H1",
                "--name",
                "Grounding",
                "--text",
                "THE UPDATED VALUE",
                "--update",
                "--author",
                "@kj",
            ]
        )
        == 0
    )
    body = p.read_text(encoding="utf-8")
    (h,) = parse_ledger(body)
    assert h.fields["Grounding"] == "THE UPDATED VALUE", (
        "the write landed on a bullet no reader returns"
    )
    assert "- **Grounding (superseded)** - the old grounding" in body


def test_a_trailing_line_break_in_a_qualifier_cannot_tear_the_bullet(tmp_path):
    """A trailing break is deliberately allowed - it merges into the line
    terminator everywhere else. `--qualifier` was the one value embedded
    unstripped, so `- **Result (rerun<CR>)**` parsed as neither a Result nor
    anything else while `check` called the file clean."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Result** - first reading\n")
    assert (
        main(
            [
                "result",
                str(p),
                "E01-H1",
                "--text",
                "second reading 7",
                "--qualifier",
                "rerun\r",
                "--author",
                "@kj",
            ]
        )
        == 0
    )
    body = p.read_text(encoding="utf-8")
    assert "- **Result (rerun)** - second reading 7" in body
    assert "\r" not in body
    assert main(["check", str(p)]) == 0


@pytest.mark.parametrize("name", ["(v2)", "   ", "()"])
def test_a_name_that_is_empty_once_qualified_is_refused(tmp_path, capsys, name):
    """`- **** - ghost` matches no regex in the module, so the field is
    invisible to every reader while the tool reports success."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Hypothesis** - x\n")
    before = p.read_text(encoding="utf-8")
    assert (
        main(["field", str(p), "E01-H1", "--name", name, "--text", "ghost", "--author", "@kj"])
        == 2
    )
    assert "not a field name" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


def test_the_duplicate_refusal_names_the_bullet_as_written(tmp_path, capsys):
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Notes (v2)** - x\n")
    assert (
        main(["field", str(p), "E01-H1", "--name", "Notes", "--text", "y", "--author", "@kj"]) == 2
    )
    assert "already carries 'Notes (v2)'" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv, refused",
    [
        (["result", "--text", "r 0.9", "--qualifier", "n*2"], "read back as a Result"),
        (["field", "--name", "Grounding (k*2)", "--text", "x"], "read back as 'Grounding'"),
        (
            ["field", "--name", "E01-H2 comparison", "--text", "x"],
            "read back as 'E01-H2 comparison'",
        ),
    ],
)
def test_a_bullet_no_reader_matches_is_refused_before_the_write(tmp_path, capsys, argv, refused):
    """`- **Result (n*2)** - ...` landed, `show` listed one Result and `check`
    called the file clean: four of five writes never parse-back verified. The
    line is now read with the same FIELD_RE every query uses before write_text."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Hypothesis** - x\n- **Result** - r 0.5\n")
    before = p.read_text(encoding="utf-8")
    cmd, rest = argv[0], argv[1:]
    assert main([cmd, str(p), "E01-H1", *rest, "--author", "@kj"]) == 2
    assert refused in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


@pytest.mark.parametrize("second", ["Hypothesis", "Hypothesis (v2)"])
def test_register_refuses_a_field_name_given_twice(tmp_path, capsys, second):
    """The parser returns one bullet per base name, so the second value no
    query returns and no --update reaches; `field` refuses the same shape."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Hypothesis** - x\n")
    before = p.read_text(encoding="utf-8")
    argv = ["register", str(p), "--slug", "dup", "--field", "Hypothesis=a"]
    argv += ["--field", f"{second}=b", "--author", "@kj"]
    assert main(argv) == 1
    assert "a name given twice" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


def test_author_is_the_registrant_never_the_first_writer(tmp_path, capsys):
    """A hand-written block answered `@kj` after its first result write: the
    property took the first authored log line, whatever its event. Only a
    `registered` event names the registrant; anything else answers None."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Hypothesis** - x\n")
    assert main(["result", str(p), "E01-H1", "--text", "r 0.7", "--author", "@kj"]) == 0
    assert (
        main(["register", str(p), "--slug", "mine", "--field", "Hypothesis=y", "--author", "@kj"])
        == 0
    )
    by_id = {h.hid: h for h in parse_ledger(p.read_text(encoding="utf-8"))}
    assert by_id["E01-H1"].author is None
    assert by_id["E01-H2"].author == "@kj"
    capsys.readouterr()
    assert main(["list", str(p), "--author", "@kj"]) == 0
    out = capsys.readouterr().out
    assert "E01-H2" in out and "E01-H1" not in out


def test_a_blank_qualifier_is_no_qualifier(tmp_path, capsys):
    """`--qualifier " "` passed the `not qualifier` immutability test, was
    stripped to nothing, and landed a second plain Result."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Result** - r 0.5\n")
    before = p.read_text(encoding="utf-8")
    argv = ["result", str(p), "E01-H1", "--text", "r 0.9", "--qualifier", " ", "--author", "@kj"]
    assert main(argv) == 2
    assert "immutable" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


def test_register_refuses_a_field_name_opening_with_an_id_and_says_so(tmp_path, capsys):
    """The count check already refused the block (the reader takes the bullet
    for a declaration that ends it), but the message named `*` and a repeated
    name as the only causes - a diagnosis none of which applied."""
    p = _writable(tmp_path, "### E01-H1 s\n\n- **Hypothesis** - x\n")
    before = p.read_text(encoding="utf-8")
    argv = ["register", str(p), "--slug", "cmp", "--field", "Hypothesis=a"]
    argv += ["--field", "E01-H1 comparison=b", "--author", "@kj"]
    assert main(argv) == 1
    assert "an opening hypothesis id" in capsys.readouterr().err
    assert p.read_text(encoding="utf-8") == before


# --- Locks: who is working on what, the pm-tools discipline ----------------


def _stamp(hours: float) -> str:
    return (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


TWO_AUTHORS = "## Authors\n\n- `@kj` Konrad Jelen\n- `@ab` Ann Bee\n\n"


def _two(tmp_path):
    """Two rostered authors, two registered hypotheses, no lock."""
    return _ledger(
        tmp_path,
        TWO_AUTHORS + "### E1-H1 s\n\nOverview: why, what it tests.\n\n"
        "- **Hypothesis** - x\n- **Acceptance bar** - DR >= 1.5x\n"
        "- **Log**\n  - log: 2026-09-01 @kj - registered\n\n"
        "### E1-H2 t\n\n- **Hypothesis** - y\n- **Log**\n  - log: 2026-09-01 @kj - registered\n",
    )


def _lock_lines(p):
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if "- lock:" in ln]


def _log_count(p):
    return p.read_text(encoding="utf-8").count("- log:")


def test_lock_writes_one_line_24h_ahead_as_the_first_bullet_and_never_logs(tmp_path, capsys):
    p = _two(tmp_path)
    assert main(["lock", str(p), "E1-H1", "--author", "@kj", "--note", "bisect"]) == 0
    (line,) = _lock_lines(p)
    stamp = line.split()[2]
    assert line == f"- lock: {stamp} @kj bisect"
    assert _stamp(23.99) <= stamp <= _stamp(24.01), "24 hours from now by default"
    body = p.read_text(encoding="utf-8")
    assert body.index("### E1-H1") < body.index("- lock:") < body.index("**Hypothesis**"), (
        "the lock is the block's first bullet, so `show` opens with it"
    )
    assert body.index("Overview") < body.index("- lock:"), (
        "first BULLET - the overview paragraph stays a paragraph, never the lock's text"
    )
    assert _log_count(p) == 2, "locking is never logged"
    out = capsys.readouterr()
    assert "E1-H1 locked by @kj until " + stamp in out.out
    assert out.err == "", "own lock on a free hypothesis: nothing to warn about"
    (h1, h2) = parse_ledger(body)
    assert h1.lock == {"by": "@kj", "until": stamp, "note": "bisect"}
    assert "lock" not in {k.lower() for k in h1.fields}, "no field reader sees the lock line"
    assert h2.lock is None


def test_lock_lands_after_a_fenced_bold_bullet_in_the_overview(tmp_path):
    p = _ledger(
        tmp_path,
        TWO_AUTHORS + "### E1-H3 u\n\nOverview paragraph.\n\n"
        "```\n- **Verdict** - <label>; <number>\n```\n\n"
        "- **Hypothesis** - z\n- **Log**\n  - log: 2026-09-01 @kj - registered\n",
    )
    assert main(["lock", str(p), "E1-H3", "--author", "@kj", "--note", "bisect"]) == 0
    body = p.read_text(encoding="utf-8")
    fence_close = body.index("<number>\n```")
    assert fence_close < body.index("- lock:") < body.index("**Hypothesis**"), (
        "the insert scan and the Verdict guard read the fence-stripped view, as every other lock path does"
    )
    (h,) = parse_ledger(body)
    assert h.lock["by"] == "@kj" and h.lock["note"] == "bisect"
    assert main(["check", str(p)]) == 0


def test_lock_hours_and_until_are_honoured_and_a_relock_extends(tmp_path, capsys):
    p = _two(tmp_path)
    main(["lock", str(p), "E1-H1", "--author", "@kj", "--hours", "2"])
    (line,) = _lock_lines(p)
    assert _stamp(1.99) <= line.split()[2] <= _stamp(2.01)
    later = _stamp(72)
    assert main(["lock", str(p), "E1-H1", "--author", "@kj", "--until", later]) == 0
    assert _lock_lines(p) == [f"- lock: {later} @kj"], "the same author replaces the line"
    out = capsys.readouterr()
    assert "extended by @kj" in out.out and out.err == "", "extending your own lock is silent"
    assert main(["lock", str(p), "E1-H1", "--author", "@kj", "--until", "2026-09-01"]) == 2
    assert "ISO 8601" in capsys.readouterr().err
    assert (
        main(["lock", str(p), "E1-H1", "--author", "@kj", "--hours", "1", "--until", later]) == 2
    )
    assert "not both" in capsys.readouterr().err
    assert _lock_lines(p) == [f"- lock: {later} @kj"], "a refused call changes nothing"


def test_locking_over_another_authors_lock_is_a_transfer_and_is_called_out(tmp_path, capsys):
    p = _two(tmp_path)
    main(["lock", str(p), "E1-H1", "--author", "@kj"])
    capsys.readouterr()
    assert main(["lock", str(p), "E1-H1", "--author", "@ab"]) == 0
    err = capsys.readouterr().err
    assert err.startswith("TRANSFER: E1-H1 was locked by @kj until ") and "ask @kj" in err
    (line,) = _lock_lines(p)
    assert line.endswith(" @ab taken over from @kj"), line
    assert main(["lock", str(p), "E1-H1", "--author", "@kj", "--note", "mine again"]) == 0
    (line,) = _lock_lines(p)
    assert line.endswith(" @kj mine again"), "a given note wins over the default"
    assert _log_count(p) == 2


def test_lock_refuses_a_verdicted_hypothesis_and_a_compact_one(tmp_path, capsys):
    p = _two(tmp_path)
    main(["verdict", str(p), "E1-H1", "--text", "Confirmed; DR 2x", "--author", "@kj"])
    assert main(["lock", str(p), "E1-H1", "--author", "@ab"]) == 2
    assert "only an unverdicted hypothesis" in capsys.readouterr().err
    assert _lock_lines(p) == []
    q = _writable(tmp_path, "- **E2-H9 compact** - prose\n", name="c.md")
    assert main(["lock", str(q), "E2-H9", "--author", "@kj"]) == 1
    assert "only a full block" in capsys.readouterr().err
    r = _ledger(
        tmp_path,
        TWO_AUTHORS + "### E1-H1 s\n\n- **Hypothesis** - x\n- **Verdict** -\n"
        "- **Log**\n  - log: 2026-09-01 @kj - registered\n",
        name="e.md",
    )
    assert main(["lock", str(r), "E1-H1", "--author", "@kj"]) == 2, (
        "presence, not value: an empty Verdict placeholder still closes the block to a lock"
    )
    assert "only an unverdicted hypothesis" in capsys.readouterr().err


def test_a_foreign_lock_warns_once_and_every_write_lands_unchanged(tmp_path, capsys):
    p = _two(tmp_path)
    main(["lock", str(p), "E1-H1", "--author", "@ab"])
    capsys.readouterr()
    writes = [
        ["result", str(p), "E1-H1", "--text", "DR 2.0x", "--author", "@kj"],
        ["field", str(p), "E1-H1", "--name", "Grounding", "--text", "g", "--author", "@kj"],
        ["log-event", str(p), "E1-H1", "--event", "re-ran", "--author", "@kj"],
    ]
    for argv in writes:
        assert main(argv) == 0, argv
        err = capsys.readouterr().err
        assert err.count("locked by @ab until") == 1, argv
        assert "ask before continuing" in err
    body = p.read_text(encoding="utf-8")
    assert "**Result** - DR 2.0x" in body and "**Grounding** - g" in body and "re-ran" in body
    assert len(_lock_lines(p)) == 1, "the lock survives another author's writes"
    assert main(["log-event", str(p), "E1-H1", "--event", "mine", "--author", "@ab"]) == 0
    assert capsys.readouterr().err == "", "the holder is never warned about their own lock"


def test_verdict_clears_the_lock_whatever_its_expiry_after_warning(tmp_path, capsys):
    p = _two(tmp_path)
    main(["lock", str(p), "E1-H1", "--author", "@ab", "--until", _stamp(500)])
    capsys.readouterr()
    assert main(["verdict", str(p), "E1-H1", "--text", "Refuted; DR 1.1x", "--author", "@kj"]) == 0
    assert "locked by @ab" in capsys.readouterr().err
    assert _lock_lines(p) == [], "a verdict closes the hypothesis, so the lock goes"
    h1, h2 = parse_ledger(p.read_text(encoding="utf-8"))
    assert h1.verdict == "Refuted" and h1.fields["Hypothesis"] == "x"
    assert h2.fields["Hypothesis"] == "y", "the next block is untouched by the line removal"
    assert _log_count(p) == 3


def test_an_expired_lock_is_cleared_by_the_next_write_silently(tmp_path, capsys):
    p = _two(tmp_path)
    main(["lock", str(p), "E1-H1", "--author", "@ab", "--until", "2020-01-01T00:00:00Z"])
    capsys.readouterr()
    assert main(["log-event", str(p), "E1-H2", "--event", "ping", "--author", "@kj"]) == 0
    assert _lock_lines(p) == [], "any write drops every expired lock, not only its own item's"
    assert capsys.readouterr().err == "", "an expired lock is a courtesy that ran out"
    assert _log_count(p) == 3
    main(["lock", str(p), "E1-H1", "--author", "@ab", "--until", "2020-01-01T00:00:00Z"])
    assert main(["author", str(p), "--handle", "@cd", "--name", "C D"]) == 0
    assert _lock_lines(p) == [], "the roster write clears it too"
    main(["lock", str(p), "E1-H1", "--author", "@ab", "--until", "2020-01-01T00:00:00Z"])
    assert main(["register", str(p), "--slug", "a-b", "--author", "@kj"]) == 0
    assert _lock_lines(p) == [], "and so does register"
    assert main(["lock", str(p), "E1-H1", "--author", "@kj"]) == 0
    assert "TRANSFER" not in capsys.readouterr().err, "no transfer over a lock that has expired"


def test_check_errors_on_a_malformed_or_duplicate_lock_and_warns_on_an_expired_or_finished_one(
    tmp_path, capsys
):
    p = _two(tmp_path)
    good = f"- lock: {_stamp(1)} @kj"
    body = p.read_text(encoding="utf-8").replace(
        "### E1-H1 s\n\n", f"### E1-H1 s\n\n- lock: notastamp @kj\n{good}\n"
    )
    p.write_text(body, encoding="utf-8")
    assert main(["check", str(p)]) == 1
    err = capsys.readouterr().err
    assert "E1-H1 carries more than one lock: line" in err
    assert "E1-H1 lock: line is malformed" in err
    assert len(_lock_lines(p)) == 2, "check reports, it never repairs"
    p.write_text(body.replace("- lock: notastamp @kj\n", ""), encoding="utf-8")
    assert main(["check", str(p)]) == 0
    assert "lock" not in capsys.readouterr().err
    p.write_text(
        body.replace("- lock: notastamp @kj\n", "").replace(
            good, "- lock: 2020-01-01T00:00:00Z @kj"
        ),
        encoding="utf-8",
    )
    main(["check", str(p)])
    assert "E1-H1 expired lock, cleared on the next write" in capsys.readouterr().err
    p.write_text(
        body.replace("- lock: notastamp @kj\n", "").replace(
            "- **Acceptance bar** - DR >= 1.5x\n",
            "- **Acceptance bar** - DR >= 1.5x\n- **Verdict** - Confirmed; 2x\n",
        ),
        encoding="utf-8",
    )
    main(["check", str(p)])
    assert "E1-H1 is locked but carries a Verdict" in capsys.readouterr().err


def test_unlock_clears_one_every_or_only_the_expired_locks(tmp_path, capsys):
    p = _two(tmp_path)
    main(["lock", str(p), "E1-H1", "--author", "@kj"])
    main(["lock", str(p), "E1-H2", "--author", "@ab"])
    body = p.read_text(encoding="utf-8").replace(
        "### E1-H2 t\n\n", "### E1-H2 t\n\n- lock: 2020-01-01T00:00:00Z @kj stale\n"
    )
    p.write_text(body, encoding="utf-8")
    assert len(_lock_lines(p)) == 3
    capsys.readouterr()
    assert main(["unlock", str(p), "--author", "@kj", "--expired"]) == 0
    assert "1 expired lock(s) cleared" in capsys.readouterr().out
    assert len(_lock_lines(p)) == 2
    assert main(["unlock", str(p), "E1-H2", "--author", "@kj"]) == 0
    out = capsys.readouterr()
    assert out.err.startswith("TRANSFER: E1-H2 was locked by @ab") and "clearing it" in out.err
    assert "1 lock(s) cleared" in out.out
    (line,) = _lock_lines(p)
    assert " @kj" in line
    main(["lock", str(p), "E1-H2", "--author", "@kj"])
    assert main(["unlock", str(p), "--author", "@kj", "--all"]) == 0
    assert _lock_lines(p) == []
    assert "2 lock(s) cleared" in capsys.readouterr().out
    assert main(["unlock", str(p), "--author", "@kj"]) == 2
    assert main(["unlock", str(p), "E1-H1", "--author", "@kj", "--all"]) == 2
    assert main(["unlock", str(p), "E1-H1", "--author", "@zz"]) == 2, "the roster still applies"
    assert main(["unlock", str(p), "E9-H99", "--author", "@kj"]) == 1
    assert _log_count(p) == 2, "unlocking is never logged"
    h1, h2 = parse_ledger(p.read_text(encoding="utf-8"))
    assert h1.fields["Hypothesis"] == "x" and h2.fields["Hypothesis"] == "y"


def test_reads_announce_worked_on_hypotheses_and_json_carries_the_lock(tmp_path, capsys):
    p = _two(tmp_path)
    for argv in (["list", str(p)], ["show", str(p), "E1-H1"], ["report", str(p)]):
        main(argv)
        assert "currently worked on" not in capsys.readouterr().err, argv
    main(["lock", str(p), "E1-H1", "--author", "@kj", "--note", "bisect"])
    stamp = _lock_lines(p)[0].split()[2]
    capsys.readouterr()
    for argv in (["list", str(p)], ["show", str(p), "E1-H1"], ["report", str(p)]):
        main(argv)
        out = capsys.readouterr()
        assert out.err == f"1 hypothesis(es) currently worked on: E1-H1 by @kj until {stamp}\n", (
            argv
        )
        assert "currently worked on" not in out.out, "the notice keeps a piped table clean"
    main(["show", str(p), "E1-H2"])
    assert capsys.readouterr().err == "", "silent when nothing shown is locked"
    main(["list", str(p), "--json"])
    out = capsys.readouterr()
    assert out.err == "", "--json carries no notice"
    rows = {r["id"]: r["lock"] for r in json.loads(out.out)}
    assert rows == {"E1-H1": {"by": "@kj", "until": stamp, "note": "bisect"}, "E1-H2": None}
    main(["show", str(p), "E1-H1", "--json"])
    assert json.loads(capsys.readouterr().out)["lock"]["by"] == "@kj"
    p.write_text(
        p.read_text(encoding="utf-8").replace(stamp, "2020-01-01T00:00:00Z"), encoding="utf-8"
    )
    main(["list", str(p)])
    assert capsys.readouterr().err == "", "an expired lock is not announced"
    main(["list", str(p), "--json"])
    rows = {r["id"]: r["lock"] for r in json.loads(capsys.readouterr().out)}
    assert rows["E1-H1"] is None, "--json carries the active lock, never an expired one"


def test_the_notice_names_ten_and_counts_the_rest(tmp_path, capsys):
    blocks = "".join(
        f"### E1-H{n} s{n}\n\n- lock: {_stamp(1)} @kj\n- **Hypothesis** - x\n\n"
        for n in range(1, 13)
    )
    p = _ledger(tmp_path, TWO_AUTHORS + blocks)
    main(["list", str(p)])
    err = capsys.readouterr().err
    assert err.startswith("12 hypothesis(es) currently worked on: E1-H1 by @kj")
    assert err.rstrip().endswith(", +2 more") and "E1-H10 " in err and "E1-H11" not in err


def test_locked_and_locked_by_narrow_list(tmp_path, capsys):
    p = _two(tmp_path)
    main(["lock", str(p), "E1-H1", "--author", "@kj"])
    capsys.readouterr()
    main(["list", str(p), "--locked", "--json"])
    assert [r["id"] for r in json.loads(capsys.readouterr().out)] == ["E1-H1"]
    main(["list", str(p), "--locked-by", "kj", "--json"])
    assert [r["id"] for r in json.loads(capsys.readouterr().out)] == ["E1-H1"]
    main(["list", str(p), "--locked-by", "@ab", "--json"])
    assert json.loads(capsys.readouterr().out) == []
    main(["list", str(p), "--locked", "--verdict", "none", "--batch", "E1", "--json"])
    assert [r["id"] for r in json.loads(capsys.readouterr().out)] == ["E1-H1"]


def test_a_lock_note_must_be_one_line(tmp_path, capsys):
    p = _two(tmp_path)
    assert main(["lock", str(p), "E1-H1", "--author", "@kj", "--note", "two\nlines"]) == 2
    assert "single line" in capsys.readouterr().err
    assert _lock_lines(p) == []


def test_the_hypothesis_skill_carries_the_lock_discipline():
    skill = (ROOT / "plugins" / "datascience" / "skills" / "hypothesis").resolve()
    body = (skill / "SKILL.md").read_text(encoding="utf-8")
    ref = (skill / "references" / "ledger-queries.md").read_text(encoding="utf-8")
    assert "hypothesis-tools lock" in body and "never a gate" in body
    assert "hypothesis-tools lock <log> <id> --author @xx" in ref
    assert "hypothesis-tools unlock <log>" in ref
    assert "currently worked on" in ref and "TRANSFER" in ref
    assert "24 hours" in body and "24 hours" in ref
