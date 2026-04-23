"""Tests for stellars_claude_code_plugins.document_processing."""

from __future__ import annotations

import json

import pytest

from stellars_claude_code_plugins.document_processing import (
    GroundingMatch,
    ground,
    ground_many,
)
from stellars_claude_code_plugins.document_processing import settings as settings_mod
from stellars_claude_code_plugins.document_processing.chunking import (
    Chunk,
    recursive_chunk,
)
from stellars_claude_code_plugins.document_processing.cli import main as cli_main
from stellars_claude_code_plugins.document_processing.grounding import Location


class TestExactMatching:
    """Regex (exact) layer — whitespace-tolerant, case-insensitive."""

    def test_exact_verbatim(self):
        m = ground("quick brown fox", ["The quick brown fox jumps."])
        assert m.match_type == "exact"
        assert m.exact_score == 1.0
        assert m.exact_matched_text == "quick brown fox"
        assert m.exact_location.char_start == 4
        assert m.exact_location.char_end == 19

    def test_exact_case_insensitive(self):
        m = ground("QUICK BROWN FOX", ["The quick brown fox jumps."])
        assert m.match_type == "exact"
        assert m.exact_score == 1.0

    def test_exact_whitespace_tolerant(self):
        m = ground("quick brown fox", ["The  quick\n brown  \tfox jumps."])
        assert m.match_type == "exact"
        assert m.exact_score == 1.0

    def test_exact_miss(self):
        m = ground("completely unrelated phrase", ["The quick brown fox jumps."])
        assert m.exact_score == 0.0
        assert m.exact_matched_text == ""

    def test_exact_multi_source_first_hit_wins(self):
        m = ground(
            "brown fox", ["nothing here", "The quick brown fox jumps.", "also has brown fox"]
        )
        assert m.match_type == "exact"
        assert m.exact_location.source_index == 1

    def test_exact_with_source_paths(self):
        m = ground(
            "brown fox",
            [("doc1.txt", "nothing here"), ("doc2.txt", "The quick brown fox jumps.")],
        )
        assert m.match_type == "exact"
        assert m.exact_location.source_path == "doc2.txt"


class TestFuzzyMatching:
    """Levenshtein (fuzzy) layer — always runs, best across sources."""

    def test_fuzzy_above_threshold(self):
        m = ground(
            "quick brown fox jumped over",
            ["The quick brown fox jumps over the lazy dog."],
            fuzzy_threshold=0.80,
        )
        assert m.exact_score == 0.0
        assert m.fuzzy_score >= 0.80
        assert m.match_type == "fuzzy"

    def test_fuzzy_below_threshold(self):
        m = ground(
            "tropical island paradise",
            ["The quick brown fox jumps over the lazy dog."],
            fuzzy_threshold=0.85,
        )
        assert m.exact_score == 0.0
        assert m.fuzzy_score < 0.85
        assert m.match_type == "none"

    def test_fuzzy_always_computed_even_on_exact_hit(self):
        """Both scores always populated; exact match yields fuzzy=1.0 too."""
        m = ground("brown fox", ["The quick brown fox jumps."])
        assert m.exact_score == 1.0
        assert m.fuzzy_score == 1.0
        assert m.match_type == "exact"

    def test_fuzzy_best_across_sources(self):
        m = ground(
            "quick brown fox",
            [
                "blue sky overhead",
                "quirk brown fux jumps",
            ],
        )
        assert m.exact_score == 0.0
        assert m.fuzzy_score > 0.5
        assert m.fuzzy_location.source_index == 1


class TestBothSignalsReported:
    """All three scores always in the result (user requirement)."""

    def test_none_match_still_reports_fuzzy_signal(self):
        """Even when match_type=none, fuzzy_score shows best-effort signal."""
        m = ground("something different", ["slightly different content here"])
        assert m.match_type == "none"
        assert m.fuzzy_score > 0
        assert m.fuzzy_matched_text != ""

    def test_all_three_scores_independent(self):
        """exact=0 does not zero fuzzy or bm25."""
        m = ground("fox jumps", ["the quick fux jumps high"])
        assert m.exact_score == 0.0
        assert m.fuzzy_score > 0
        # BM25 may or may not fire on such a short source, but score is set

    def test_combined_score_is_max_of_three(self):
        m = ground("brown fox", ["The quick brown fox jumps."])
        assert m.combined_score == max(m.exact_score, m.fuzzy_score, m.bm25_score)


class TestBM25Matching:
    """BM25 layer — topical/lexical grounding across passages."""

    _LONG_SOURCE = (
        "Introduction paragraph about birds.\n\n"
        "The quick brown fox jumps over the lazy dog in the meadow.\n\n"
        "Cats sleep most of the day on windowsills.\n\n"
        "Aquatic mammals like dolphins are highly intelligent.\n"
    )

    def test_bm25_finds_right_passage(self):
        """Paraphrased claim with same key terms lands in the right passage."""
        m = ground(
            "fox and dog in a meadow",
            [self._LONG_SOURCE],
            fuzzy_threshold=0.95,  # high, so fuzzy fails
            bm25_threshold=0.4,
        )
        # The fox passage should win
        assert "fox" in m.bm25_matched_text
        assert m.bm25_score > 0
        assert m.bm25_token_recall > 0

    def test_bm25_token_recall_is_fraction(self):
        """Token recall = fraction of unique claim tokens in best passage."""
        m = ground("fox dog meadow", [self._LONG_SOURCE])
        # All 3 tokens present → recall = 1.0
        assert m.bm25_token_recall == 1.0

    def test_bm25_raw_score_available(self):
        """Raw BM25 score exposed for callers who want the unbounded signal."""
        m = ground("fox dog meadow", [self._LONG_SOURCE])
        assert m.bm25_raw_score >= 0

    def test_bm25_location_populated(self):
        """BM25 location has line/paragraph/page just like other layers."""
        m = ground("fox dog", [self._LONG_SOURCE])
        assert m.bm25_location.line_start > 0
        assert m.bm25_location.paragraph > 0
        assert m.bm25_location.page == 1

    def test_bm25_matches_topical_paraphrase(self):
        """Same terms, different order — BM25 catches what Levenshtein misses."""
        # "Dolphins are smart aquatic mammals" — paraphrase of sentence in source
        m = ground(
            "dolphins mammals intelligent aquatic",
            [self._LONG_SOURCE],
            fuzzy_threshold=0.95,
            bm25_threshold=0.5,
        )
        assert m.exact_score == 0.0
        # BM25 should catch this
        assert m.bm25_token_recall >= 0.5
        assert "dolphins" in m.bm25_matched_text.lower()

    def test_bm25_below_threshold_classified_none(self):
        """When BM25 token-recall below threshold, match_type=none."""
        m = ground(
            "quantum physics neutrino detector",
            [self._LONG_SOURCE],
            fuzzy_threshold=0.95,
            bm25_threshold=0.5,
        )
        assert m.match_type == "none"

    def test_bm25_priority_below_fuzzy(self):
        """When both fuzzy and bm25 would classify, fuzzy wins."""
        m = ground(
            "quick brown fox jumped",  # fuzzy match of "quick brown fox jumps"
            [self._LONG_SOURCE],
            fuzzy_threshold=0.80,
            bm25_threshold=0.5,
        )
        assert m.match_type == "fuzzy"  # fuzzy wins over bm25


class TestLocation:
    """Location metadata — line, column, paragraph, page, context."""

    def test_line_number_single_line(self):
        m = ground("fox", ["The quick brown fox jumps."])
        assert m.exact_location.line_start == 1
        assert m.exact_location.line_end == 1

    def test_line_number_multiline_source(self):
        text = "line one\nline two\nthe fox is here\nline four"
        m = ground("fox is here", [text])
        assert m.match_type == "exact"
        assert m.exact_location.line_start == 3
        assert m.exact_location.line_end == 3

    def test_column_number(self):
        text = "hello brown fox and more"
        m = ground("brown fox", [text])
        assert m.exact_location.line_start == 1
        # "brown fox" starts at char 6 on line 1 → column 7 (1-indexed)
        assert m.exact_location.column_start == 7

    def test_paragraph_number(self):
        text = "first paragraph text\n\nsecond paragraph with fox here\n\nthird paragraph"
        m = ground("fox", [text])
        assert m.match_type == "exact"
        assert m.exact_location.paragraph == 2

    def test_paragraph_blank_line_with_whitespace(self):
        """Blank lines with whitespace still separate paragraphs."""
        text = "first para\n  \t  \nsecond para fox"
        m = ground("fox", [text])
        assert m.exact_location.paragraph == 2

    def test_page_number_via_form_feed(self):
        """Pages separated by \\f (pdftotext convention)."""
        text = "page one content\fpage two with fox\fpage three"
        m = ground("fox", [text])
        assert m.match_type == "exact"
        assert m.exact_location.page == 2

    def test_page_1_when_no_form_feed(self):
        m = ground("fox", ["no form feeds here just fox content"])
        assert m.exact_location.page == 1

    def test_context_before_after(self):
        text = "The quick brown fox jumps over the lazy dog gently."
        m = ground("brown fox", [text])
        # Context should include surrounding words
        ctx_before = m.exact_location.context_before
        ctx_after = m.exact_location.context_after
        assert "quick" in ctx_before or "The" in ctx_before
        assert "jumps" in ctx_after or "over" in ctx_after

    def test_context_trimmed_to_max_chars(self):
        """Long context is trimmed with ellipsis."""
        long_text = "x" * 200 + " brown fox " + "y" * 200
        m = ground("brown fox", [long_text], context_chars=40)
        assert len(m.exact_location.context_before) <= 41  # 40 + ellipsis
        assert len(m.exact_location.context_after) <= 41


class TestEdgeCases:
    def test_empty_sources(self):
        m = ground("anything", [])
        assert isinstance(m, GroundingMatch)
        assert m.match_type == "none"
        assert m.exact_score == 0.0
        assert m.fuzzy_score == 0.0

    def test_empty_claim(self):
        m = ground("", ["some source text"])
        assert m.exact_score == 0.0

    def test_empty_source_text(self):
        m = ground("anything", [""])
        assert m.exact_score == 0.0
        assert m.fuzzy_score == 0.0

    def test_location_dataclass_default_is_neg_one(self):
        loc = Location()
        assert loc.line_start == -1
        assert loc.paragraph == -1
        assert loc.page == -1


class TestBatch:
    def test_ground_many_preserves_order(self):
        claims = ["brown fox", "lazy dog", "unrelated claim"]
        sources = ["The quick brown fox jumps over the lazy dog."]
        results = ground_many(claims, sources, fuzzy_threshold=0.85)
        assert len(results) == 3
        assert results[0].match_type == "exact"
        assert results[1].match_type == "exact"
        assert results[2].match_type in ("fuzzy", "none")


class TestCLI:
    """End-to-end CLI tests via the main() entrypoint."""

    def test_ground_exit_zero_on_hit(self, tmp_path, capsys):
        src = tmp_path / "src.txt"
        src.write_text("The quick brown fox jumps over the lazy dog.")
        code = cli_main(["ground", "--claim", "brown fox", "--source", str(src)])
        assert code == 0
        out = capsys.readouterr().out
        assert "EXACT" in out
        assert "exact=1.000" in out

    def test_ground_output_includes_location(self, tmp_path, capsys):
        src = tmp_path / "src.txt"
        src.write_text("line one\nline two with brown fox here\nline three")
        code = cli_main(["ground", "--claim", "brown fox", "--source", str(src)])
        assert code == 0
        out = capsys.readouterr().out
        assert "L2" in out  # line 2
        assert "¶1" in out  # paragraph 1

    def test_ground_exit_one_on_miss(self, tmp_path, capsys):
        src = tmp_path / "src.txt"
        src.write_text("Only about horticulture.")
        code = cli_main(
            [
                "ground",
                "--claim",
                "quantum physics",
                "--source",
                str(src),
                "--threshold",
                "0.95",
                "--semantic",
                "off",  # ensure test doesn't depend on optional model download
            ]
        )
        assert code == 1
        out = capsys.readouterr().out
        assert "NONE" in out

    def test_ground_json_output(self, tmp_path, capsys):
        src = tmp_path / "src.txt"
        src.write_text("The quick brown fox jumps.")
        code = cli_main(["ground", "--claim", "brown fox", "--source", str(src), "--json"])
        assert code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["match_type"] == "exact"
        assert data["exact_score"] == 1.0
        assert data["fuzzy_score"] >= 0.0
        # Nested Location should serialize too
        assert "exact_location" in data
        assert data["exact_location"]["line_start"] == 1
        assert data["exact_location"]["paragraph"] == 1

    def test_ground_many_markdown_report(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("The quick brown fox jumps over the lazy dog.")
        claims = tmp_path / "claims.json"
        claims.write_text(json.dumps(["brown fox", "unrelated claim"]))
        out = tmp_path / "report.md"
        cli_main(
            [
                "ground-many",
                "--claims",
                str(claims),
                "--source",
                str(src),
                "--output",
                str(out),
            ]
        )
        report = out.read_text()
        assert "Grounding Report" in report
        assert "CONFIRMED" in report
        assert "L1" in report  # location in report
        assert "¶1" in report

    def test_ground_many_json_report(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("The quick brown fox jumps.")
        claims = tmp_path / "claims.json"
        claims.write_text(json.dumps([{"claim": "brown fox"}, {"claim": "missing"}]))
        out = tmp_path / "report.json"
        cli_main(
            [
                "ground-many",
                "--claims",
                str(claims),
                "--source",
                str(src),
                "--output",
                str(out),
                "--json",
            ]
        )
        data = json.loads(out.read_text())
        assert data["summary"]["total"] == 2
        assert data["summary"]["exact"] >= 1
        assert len(data["matches"]) == 2
        # Location fields should be in the JSON
        assert "exact_location" in data["matches"][0]

    def test_ground_missing_source_errors(self, capsys):
        with pytest.raises(SystemExit):
            cli_main(["ground", "--claim", "anything", "--source", "/nonexistent/file.txt"])


class TestChunking:
    """Recursive chunking preserves offsets + boundaries."""

    def test_empty_text_returns_empty(self):
        assert recursive_chunk("") == []

    def test_short_text_one_chunk(self):
        text = "The quick brown fox."
        chunks = recursive_chunk(text, max_chars=1500)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].char_start == 0
        assert chunks[0].char_end == len(text)

    def test_paragraph_split(self):
        text = "First paragraph here.\n\nSecond paragraph longer content here.\n\nThird paragraph ends the document."
        chunks = recursive_chunk(text, max_chars=30, min_chunk_chars=10)
        assert len(chunks) >= 2

    def test_offsets_are_valid(self):
        text = "paragraph one\n\nparagraph two content\n\nparagraph three final"
        chunks = recursive_chunk(text, max_chars=200, min_chunk_chars=5)
        for c in chunks:
            # Char offsets must be valid bounds into the source
            assert 0 <= c.char_start < c.char_end <= len(text)
            # First + last words of the chunk should appear inside the source span
            first_word = c.text.split()[0]
            last_word = c.text.split()[-1]
            span = text[c.char_start : c.char_end]
            assert first_word in span
            assert last_word in span

    def test_long_sentence_sliding_window(self):
        sentence = "word " * 500  # long single sentence
        chunks = recursive_chunk(sentence, max_chars=200, overlap_chars=50)
        assert len(chunks) > 1
        # Overlap: consecutive chunks share some content
        if len(chunks) >= 2:
            assert chunks[0].char_end > chunks[1].char_start

    def test_offsets_monotonic(self):
        text = "a " * 200 + "\n\n" + "b " * 200
        chunks = recursive_chunk(text, max_chars=100)
        starts = [c.char_start for c in chunks]
        assert starts == sorted(starts)

    def test_chunk_dataclass(self):
        c = Chunk("hello", 0, 5)
        assert len(c) == 5


class TestSettings:
    """Settings load/save/prompt — zero-dep."""

    def test_defaults_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        cfg = settings_mod.load()
        assert cfg.semantic_enabled is False
        assert cfg.semantic_model == "intfloat/multilingual-e5-small"
        assert cfg.semantic_device == "auto"

    def test_save_then_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        # Create project root marker
        (tmp_path / ".claude").mkdir()
        s = settings_mod.Settings(semantic_enabled=True, semantic_model="custom/model")
        path = settings_mod.save(s)
        assert path.exists()
        loaded = settings_mod.load()
        assert loaded.semantic_enabled is True
        assert loaded.semantic_model == "custom/model"

    def test_is_semantic_available_reflects_imports(self):
        # This may be True or False depending on test env — just ensure the
        # function runs without error and returns a bool
        result = settings_mod.is_semantic_available()
        assert isinstance(result, bool)

    def test_install_hint_is_helpful(self):
        hint = settings_mod.semantic_install_hint()
        assert "pip install" in hint
        assert "semantic" in hint.lower()


class TestCLISetup:
    """CLI setup subcommand."""

    def test_setup_shows_current_if_present(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        (tmp_path / ".claude").mkdir()
        # Pre-seed settings
        settings_mod.save(settings_mod.Settings(semantic_enabled=True))
        code = cli_main(["setup"])
        assert code == 0
        err = capsys.readouterr().err
        assert "semantic_enabled" in err
