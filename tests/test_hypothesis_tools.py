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

from pathlib import Path

import pytest

from stellars_claude_code_plugins.hypothesis.hypothesis_tools import (
    REQUIRED_FIELDS,
    VERDICTS,
    main,
    match_verdict,
    parse_ledger,
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


def test_unknown_label_reads_as_no_verdict():
    assert match_verdict("Works great, ship it") is None


def test_bold_label_still_reads():
    assert match_verdict("**Confirmed**; 0.91") == "Confirmed"
    assert match_verdict("Confirmed-partially; 0.5") is None


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


def test_check_fails_on_a_verdict_outside_the_vocabulary(tmp_path, capsys):
    ledger = tmp_path / "bad.md"
    ledger.write_text(
        "# L\n\n**Canonical Experiments Document**\n\n"
        "### E1-H1 slug\n\n- **Verdict** - Works great; 1.0\n",
        encoding="utf-8",
    )
    assert main(["check", str(ledger)]) == 1
    assert "is not one of" in capsys.readouterr().err


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
    assert "Verdict" in capsys.readouterr().err


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
