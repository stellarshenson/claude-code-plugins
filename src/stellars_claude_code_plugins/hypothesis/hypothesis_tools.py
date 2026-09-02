"""Queries and appends over a canonical hypothesis experiments ledger.

An agent running a hypothesis campaign asks the same questions constantly:
which H ordinals are already burnt (so a fanout does not re-test one), what
every verdict currently is, the full text of one hypothesis, and what a
measured quantity read across the rounds. Reading the whole ledger to answer
them costs thousands of tokens per question and gets worse every round - a
real ledger runs to 6,400 lines the agent re-reads to learn one
number. These commands answer each from a parse.

Writes are append-only, mirroring the ledger's own discipline: `register`
appends a new pre-registered hypothesis at the next free ordinal, `result`
appends a Result bullet, `verdict` records the one verdict a hypothesis gets
(a second is refused - a flip is a new round), `field` adds or replaces a
field the template does not name, `log-event` appends a dated log line.
Nothing rewrites recorded text.

Every write names its author (`--author @xx`, checked against the `## Authors`
roster) and appends a dated log line saying what it did, because a research
ledger with several hands on it needs to say whose reading a number is - and
that fact is unrecoverable once the session that wrote it is gone.

Three hypothesis shapes exist in the wild and all parse:

    full-block   ### E12-H33 slug          + `- **Verdict** - Confirmed; ...`
    compact      - **E1-H1 slug** - prose (verdict lives in the prose)
    table        | E14-H46 | claim | evidence | SUPPORTED |  (an at-a-glance
                 row in a table whose header names a claim or verdict column)

Compact hypotheses yield `verdict=None`. That is deliberate: the verdict is
narrative there ("shipped", "**null**", "initially killed"), and guessing it
with a regex produces confident wrong answers - "the features were initially
killed" is a story about a fix, not a Killed verdict. Absent beats wrong.

Verdict labels are read flexibly - case-insensitive, emphasis and dated
qualifiers stripped, hyphen/space variants folded - and an unknown label
("SUPPORTED", "PARTIAL", "Inconclusive") is still a label: real ledgers grow
their own vocabulary, so `check` warns on a non-canonical label and errors
only when no label can be read at all.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys

# ---------------------------------------------------------------------------
# Format contract
# ---------------------------------------------------------------------------

# `E<batch>|R<round>-H<n>`. The batch is read from the id, never from the
# section heading - headings are free-form across real ledgers ("## E12 - slug"
# in one, "## Contradiction features, bundle E1: slug" in another), while the
# id is the identity the skill guarantees.
_ID = r"(?P<batch>[ER]\d+)-H(?P<ordinal>\d+)"

# The id may be bolded in a heading, and any CommonMark bullet marker opens a
# compact declaration - an editor or formatter can swap `-` for `*` without
# the author noticing, and a dropped declaration is this tool's worst failure.
HEADING_RE = re.compile(rf"^(?P<hashes>#{{2,6}})\s+\*{{0,2}}\s*{_ID}\b(?P<slug>[^\n]*)$")
COMPACT_RE = re.compile(rf"^\s*[-*+]\s+\*\*\s*{_ID}\b(?P<slug>[^*]*)\*\*\s*(?:[-:]\s*)?.*$")

# Used to catch a declaration the parser did NOT recognise: the parser is
# strict, so an unknown shape is dropped, and dropping silently is what
# corrupts the append-only registry. Scoped to a bullet's BOLD LABEL, because
# that is the only place a compact declaration can be attempted - an id in a
# field value (`- **Lever** - reuses the cut proven in R9-H21`) or in a round
# heading's prose is a citation, and citations are normal.
# `\b` would reject `_E1-H52` because `_` is a word character, so an
# underscore-wrapped id slipped the net. Only a letter or digit before the
# token means it is part of a longer word and not an id.
ID_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([ER]\d+)-H(\d+)")
TABLE_ID_RE = re.compile(r"^\s*\|\s*[*_]{0,4}\s*([ER]\d+)-H(\d+)")
# One home for everything that may sit between the margin and a declaration:
# blockquote markers, any list marker, a task-list checkbox. Chasing these one
# decoration at a time is how three rounds of regressions happened; the prefix
# is generalised once here instead.
_BULLET_PREFIX = r"[\s>]*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s*)?"
# The label runs to its closing delimiter, NOT to the first `*` or `_`. A
# class like `[^*_]*` looked equivalent and was not: one underscore in a slug
# (`turbo_throughput`) failed the whole match, so the net stopped looking at
# the line and the drop went silent again.
# The marker is optional for the LABEL scan: a formatter unwrapping a
# one-item list leaves `**E1-H2 slug** - prose` as a bare paragraph, which no
# other arm of the net can see. Parentheticals are stripped before the id
# search, so ordinary bold prose (`**Round 3 (E1-H1 rerun)** - ...`) stays a
# citation rather than becoming a false refusal.
BOLD_LABEL_RE = re.compile(rf"^(?:{_BULLET_PREFIX})?(?:\*\*|__)(?P<label>(?:(?!\*\*|__).)*)")
# An id OPENING a bullet is a declaration attempt whether or not it is bolded -
# dropping the bold is the likeliest way to write the shape wrong. Anchored, so
# `- **Lever** - reuses the cut proven in R9-H21` stays a citation.
BULLET_ID_RE = re.compile(rf"^{_BULLET_PREFIX}[*_]{{0,4}}\s*([ER]\d+)-H(\d+)")
# A heading or setext line that OPENS with an id is a declaration attempt even
# when the parser rejects it - `# E1-H1` (level 1) and a setext underline both
# render as headings a formatter can produce, and both are invisible to
# HEADING_RE. Anchored, so a round heading citing a sibling stays prose.
HEADING_ID_RE = re.compile(r"^[\s>]*#{1,6}\s+[*_]{0,4}\s*([ER]\d+)-H(\d+)")
SETEXT_ID_RE = re.compile(r"^\s*[*_]{0,4}\s*([ER]\d+)-H(\d+)")
SETEXT_RULE_RE = re.compile(r"^\s*(=+|-+)\s*$")
# A field may carry a parenthetical qualifier outside the bold span
# (`- **Result** (k=1) - DR 0.180`); it belongs to the value, not the name.
FIELD_RE = re.compile(
    r"^\s*[-*+]\s+\*\*(?P<name>[^*]+?)\*\*\s*(?P<qualifier>\([^)]*\))?\s*(?:[-:]\s*(?P<value>.*))?$"
)
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")

# A second id inside the BOLD LABEL means the row cites several hypotheses
# rather than declaring one - a benchmarks row like
# `- **E01-H1 / E01-H1b weighting** - 0.08 ms/pair` would otherwise mint a
# phantom hypothesis out of a timing table. Scoped to the label on purpose:
# citing a sibling in the prose that follows is normal and must still declare
# ("**E8-H17 alignment-profile features** - shared E8-H16's gate and died").
SECOND_ID_RE = re.compile(r"[ER]\d+-H\d+")

CANONICAL_MARKER = "**Canonical Experiments Document**"

# Authorship is the project-management toolkit's, unchanged: a `## Authors`
# roster, `@xx` handles, every write naming its author. One handle means one
# person across a project's ledgers, criteria and defects - a second dialect
# would make the same researcher two people depending on which file they wrote.
HANDLE_RE = re.compile(r"@[a-z][a-z0-9]{1,3}")
ROSTER_RE = re.compile(r"^\s*[-*+]\s+`(@[a-z][a-z0-9]{1,3})`\s+(.*\S)\s*$")
# Any markdown heading - distinct from HEADING_RE above, which matches only a
# heading that DECLARES a hypothesis. Naming this one HEADING_RE shadowed that
# one and every declaration heading in the ledger stopped parsing.
ANY_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
ROSTER_HEADING = "Authors"

# `- log: 2026-09-01 @kj - re-ran at n=2x` - the handle sits between the date
# and the event. Both are optional in the pattern because the ledgers predate
# authorship: thousands of unauthored lines are legitimate history, so `check`
# counts them in one warning rather than erroring on each.
LOG_LINE_RE = re.compile(
    r"^\s*[-*+]\s+log:\s*(?P<date>\d{4}-\d{2}-\d{2})?\s*"
    r"(?P<author>@[a-z][a-z0-9]{1,3})?\s*(?:-\s*)?(?P<event>.*)$"
)

# Matched longest-first, so `Refuted (null)` is never truncated.
VERDICTS = (
    "Killed-at-gate",
    "Refuted (null)",
    "Confirmed",
    "Promoted",
    "Refuted",
    "Blocked",
    "Dropped",
    "Ships",
    "Kept",
)

# `Experiment` is conditional by design - a one-toggle batch on a shared Setup
# carries reproducibility at the document level - so it is not required here.
# `Pre-experiment` and `Log` are explicitly optional in the template.
REQUIRED_FIELDS = (
    "Hypothesis",
    "Lever",
    "Mechanism",
    "Prediction",
    "Acceptance bar",
    "Result",
    "Verdict",
)


@dataclass
class Hypothesis:
    """One declared hypothesis and everything the ledger records about it."""

    hid: str
    batch: str
    ordinal: int
    slug: str
    shape: str  # "full" | "compact"
    line: int  # 1-indexed line of the declaration
    fields: dict[str, str] = field(default_factory=dict)
    block: str = ""

    @property
    def verdict(self) -> str | None:
        """The verdict label, or None when the ledger does not state one."""
        raw = self.fields.get("Verdict")
        if not raw:
            return None
        return match_verdict(raw)

    @property
    def verdict_raw(self) -> str | None:
        return self.fields.get("Verdict")

    @property
    def author(self) -> str | None:
        """Who registered it - the handle on its `registered` log line.

        Nothing else records it: the audit trail every write appends is the
        provenance, so a hypothesis written before authorship existed answers
        None rather than guessing at the document's owner.
        """
        for line in self.block.splitlines():
            m = LOG_LINE_RE.match(line)
            if m and m.group("author") and m.group("event").startswith("registered"):
                return m.group("author")
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.hid,
            "batch": self.batch,
            "ordinal": self.ordinal,
            "slug": self.slug,
            "shape": self.shape,
            "line": self.line,
            "verdict": self.verdict,
            "author": self.author,
            "fields": self.fields,
        }


def match_verdict(raw: str) -> str | None:
    """Read the verdict label off a Verdict bullet, else None.

    The bullet is `<label>; <justifying number>` - but real ledgers write the
    label bolded (`**PARTIAL**`), uppercase (`REFUTED`), behind a dated
    qualifier (`(2026-07-12) Confirmed; ...`), or with hyphen/space swapped
    (`Killed at gate`). All of those are labels and all are read. The
    canonical vocabulary is matched first, flexibly, and returns the
    canonical spelling; anything else short and word-like at the head of the
    value is returned as written - an open vocabulary the ledger grew is
    still a vocabulary, and `check` warns rather than errors on it. Only a
    value with no readable label at all returns None.
    """
    text = re.sub(r"[*_]+", "", raw.strip()).strip()
    while True:
        # A dated or scoped qualifier before the label belongs to the field,
        # not the label - but `Refuted (null)` is canonical WITH its parens,
        # so each strip round tries the canonical match first.
        hit = _canonical_verdict(text)
        if hit:
            return hit
        stripped = re.sub(r"^\([^)]*\)\s*", "", text)
        if stripped == text:
            break
        text = stripped
    # Open vocabulary: the head of the value up to the first delimiter, if it
    # still looks like a label. The digit guard keeps the mixed-regime case
    # out - `Refuted for k=1, Confirmed for k=3` is a story, not a label.
    head = re.split(r"\s*(?:;|:|,|\(|\s-\s|\s—\s)", text, maxsplit=1)[0].strip()
    if head and len(head) <= 32 and len(head.split()) <= 3 and not re.search(r"[\d=]", head):
        return head
    return None


# A label ends the value or is followed by a delimiter. `.` is one - `Promoted.
# The identity-gap class closes` is Promoted - and a comma inside a number is
# not, so `at the 1,000 bar` stays one clause.
_LABEL_DELIM = r"(?:[;:(.]|,(?!\d)|\s-\s|$)"
_LABEL_WORD_RE = re.compile(
    r"(?:killed[-\s]at[-\s]gate|refuted|confirmed|promoted|blocked|dropped|ships|kept)\b", re.I
)


def _canonical_verdict(text: str) -> str | None:
    """The canonical label opening `text`, hyphen/space- and case-insensitive.

    The label ends the value, is followed by a delimiter, or is followed by
    scoping prose up to one: `Refuted on the replacement bar;`, `Refuted as
    an order measure (...)` and `Refuted for int8-dynamic;` are Refuted just
    as `Refuted (killed at gate)` is. Two things are not that label. A bare
    prefix - `Confirmed-partially` is not Confirmed, which is the mixed case
    the acceptance rule exists to catch. And a regime - `Refuted for k=1,
    Confirmed for k=3`, `Refuted for bf16, kept for the recipe` - which the
    corpus separates from a scope by one sign: the next clause opens with
    another label. A number in the scope does not: an earlier digit guard
    read `Refuted at the +10% bar` as a story and called four honest
    verdicts unreadable.
    """
    for label in VERDICTS:
        pat = re.escape(label).replace("\\-", "[-\\s]").replace("\\ ", "[-\\s]")
        if re.match(rf"{pat}\s*{_LABEL_DELIM}", text, re.I):
            return label
        m = re.match(rf"{pat}\s+[^;:(]*?\s*{_LABEL_DELIM}\s*(?P<next>[^\s]*)", text, re.I)
        if m:
            return None if _LABEL_WORD_RE.match(m.group("next")) else label
    return None


def _base_name(name: str) -> str:
    """A field's identity, with any trailing parenthetical qualifier removed.

    `Pre-experiment (probe)` is Pre-experiment and `Result (k=1)` is Result -
    the qualifier belongs to the value. Every guard that decides what a field
    IS must ask this same question: while the write-side outcome guard tested
    the raw name instead, `--name "Verdict (2026-09-01)"` walked past it and
    landed a second Verdict above the recorded one, where first-wins made the
    new text the verdict every reader sees.
    """
    return re.sub(r"\s*\(.*\)$", "", name.strip()).strip()


def _unreadable(bullet: str, base: str) -> bool:
    """True when the reader would not see `bullet` as the field `base`.

    Every reader goes through FIELD_RE and `_base_name`; a write that lands a
    line they cannot read reports success on a field no query returns. And
    `_read_block` ends the block at a compact declaration BEFORE it reads any
    field, so a label opening with an id (`- **E01-H2 comparison**`) is not a
    field but a declaration that hides every bullet after it: the Result and
    Verdict vanished from `show` and `list` while `check` stayed clean.
    """
    fm = FIELD_RE.match(bullet)
    return (
        not fm or _base_name(fm.group("name")) != base or _compact_declaration(bullet) is not None
    )


def _strip_fences(lines: list[str]) -> tuple[list[str], int | None]:
    """Blank out fenced code, and report a fence that never closes.

    A fence closes only on the same character at the same run length or
    longer, per CommonMark. A naive toggle lets a ``` inside a ~~~ block, or a
    single unclosed fence, blank every hypothesis after it - the whole ledger
    vanishes and every command answers confidently about nothing. The second
    return value is the 1-indexed line of an unterminated fence, so `check`
    can say so out loud. Line positions are preserved for true line numbers.
    """
    out: list[str] = []
    fence: str | None = None
    opened_at: int | None = None
    for i, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if fence is None:
                fence, opened_at = marker, i + 1
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence, opened_at = None, None
            out.append("")
            continue
        out.append("" if fence is not None else line)
    return out, opened_at


def _compact_declaration(line: str) -> re.Match | None:
    """A compact bullet that DECLARES, with the multi-id guard applied.

    One home for the rule, because `parse_ledger` and `_read_block` must agree
    about it: when only the parser applied the guard, a timing row that
    declares nothing still terminated the block it sat inside, and the
    hypothesis lost its own Result and Verdict.
    """
    m = COMPACT_RE.match(line)
    if not m:
        return None
    # A parenthetical cites; the skill MANDATES a supersede back-reference.
    if SECOND_ID_RE.search(re.sub(r"\([^)]*\)", "", m.group("slug") or "")):
        return None
    return m


# A table declares hypotheses only when its header says so - a timing or
# benchmarks table citing ids must never mint one. The header must carry an
# id-ish first column and at least one column a hypothesis table would have.
_TABLE_FIELD_FOR = (
    ("verdict", "Verdict"),
    ("status", "Verdict"),
    ("claim", "Hypothesis"),
    ("hypothesis", "Hypothesis"),
    ("evidence", "Result"),
    ("result", "Result"),
    ("prediction", "Prediction"),
    ("acceptance", "Acceptance bar"),
    ("bar", "Acceptance bar"),
)
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _table_field(header: str) -> str | None:
    low = header.lower()
    for token, name in _TABLE_FIELD_FOR:
        if token in low:
            return name
    return None


def _table_declarations(lines: list[str]) -> dict[int, tuple[str, str, dict[str, str]]]:
    """Rows that DECLARE a hypothesis, keyed by 0-indexed line.

    A real ledger's at-a-glance table (`| id | claim | evidence | verdict |`)
    is the only declaration some hypotheses ever get - in one real store it is
    the only declaration most of them ever get. A row declares when the table's header maps to
    hypothesis fields AND the row's first cell is exactly one id; everything
    else stays a citation.
    """
    out: dict[int, tuple[str, str, dict[str, str]]] = {}
    headers: list[str] | None = None
    for i, line in enumerate(lines):
        m = _TABLE_ROW_RE.match(line)
        if not m:
            headers = None
            continue
        # `\|` inside a cell is CommonMark's escaped pipe, not a delimiter -
        # a formula cell (`max\|ΔTFR\|`) would otherwise shift every cell
        # after it and the wrong column would read as the verdict.
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", m.group(1))]
        if headers is None:
            headers = cells if any(_table_field(c) for c in cells[1:]) else []
            continue
        if not headers or _TABLE_SEP_RE.match(line):
            continue
        ids = ID_TOKEN_RE.findall(cells[0])
        if len(ids) != 1 or ID_TOKEN_RE.sub("", cells[0]).strip(" `*_"):
            continue  # several ids, or prose around the id - a citation row
        hid = f"{ids[0][0]}-H{int(ids[0][1])}"
        fields: dict[str, str] = {}
        for header, cell in zip(headers[1:], cells[1:]):
            name = _table_field(header)
            if name and cell and name not in fields:
                fields[name] = cell
        out[i] = (hid, fields.get("Hypothesis", ""), fields)
    return out


def parse_ledger(text: str) -> list[Hypothesis]:
    """Parse every declared hypothesis, in document order.

    First occurrence of an id declares it; every later mention is a reference.
    A full-block heading and a compact bullet therefore cannot both declare the
    same hypothesis, which is what keeps results tables and benchmark rows from
    duplicating the hypotheses they cite.
    """
    raw_lines = text.splitlines()
    lines, _ = _strip_fences(raw_lines)
    tables = _table_declarations(lines)
    found: dict[str, Hypothesis] = {}
    order: list[Hypothesis] = []

    for i, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        compact = None if heading else _compact_declaration(line)
        m = heading or compact
        if not m:
            if i in tables and tables[i][0] not in found:
                hid, slug, fields = tables[i]
                batch, _, ord_part = hid.partition("-H")
                hyp = Hypothesis(hid, batch, int(ord_part), slug, "table", i + 1)
                hyp.fields = fields
                hyp.block = raw_lines[i]
                found[hid] = hyp
                order.append(hyp)
            continue

        hid = f"{m.group('batch')}-H{int(m.group('ordinal'))}"
        slug = (m.group("slug") or "").strip(" -:*")
        prior = found.get(hid)
        if prior is not None and (heading is None or prior.shape == "full"):
            continue  # a later mention is a reference, not a declaration

        if heading is not None:
            body, block = _read_block(lines, raw_lines, i, len(m.group("hashes")))
            hyp = Hypothesis(hid, m.group("batch"), int(m.group("ordinal")), slug, "full", i + 1)
            hyp.fields = body
            hyp.block = block
        else:
            hyp = Hypothesis(
                hid, m.group("batch"), int(m.group("ordinal")), slug, "compact", i + 1
            )
            hyp.block = raw_lines[i]

        if prior is None:
            order.append(hyp)
        else:
            # A summary bullet above the rounds must not outrank the block it
            # summarises - the block is where the fields and the verdict live.
            order[order.index(prior)] = hyp
        found[hid] = hyp

    return order


def find_orphan_ids(text: str, declared: set[str]) -> list[tuple[int, str]]:
    """Id-shaped tokens in a declaration position that never parsed.

    The safety net for the whole parser. Any shape it does not recognise is
    dropped, and a silent drop makes `next-id` hand back an ordinal that is
    already burnt - the one failure the skill says "has to be undone later".

    An id is a declaration attempt when it sits in a bullet's bold label, when
    it OPENS a bullet bolded or not, or when it opens a heading or setext line.
    Everywhere else on the line it is a citation and must stay clean - the
    skill MANDATES a supersede back-reference, so a cited sibling can never be
    allowed to look like a failed declaration. Parentheticals are stripped for
    the same reason, matching the exemption `parse_ledger` applies.
    """
    lines, _ = _strip_fences(text.splitlines())
    orphans = []
    for i, line in enumerate(lines):
        hit = None
        if m := BOLD_LABEL_RE.match(line):
            label = re.sub(r"\([^)]*\)", "", m.group("label"))
            cited = {f"{b}-H{int(n)}" for b, n in ID_TOKEN_RE.findall(label)}
            # A label naming several ids declares nothing - but it is only a
            # CITATION row when everything it names already exists. Exempting
            # it unconditionally meant `- **E8-H17 that beat E8-H16**` was
            # neither declared nor reported: an ordinal burnt in silence.
            if len(cited) > 1 and cited <= declared:
                continue
            # Anywhere in the label, so an id that is not first is still caught.
            hit = ID_TOKEN_RE.search(label)
        # A table row's first cell is a declaration position too: the skill's
        # research-at-a-glance table carries `id + slug` per row, and an id that
        # lives only there was reissued by `next-id`.
        hit = (
            hit or BULLET_ID_RE.match(line) or HEADING_ID_RE.match(line) or TABLE_ID_RE.match(line)
        )
        if hit is None and i + 1 < len(lines) and SETEXT_RULE_RE.match(lines[i + 1]):
            hit = SETEXT_ID_RE.match(line)
        if hit and (hid := f"{hit.group(1)}-H{int(hit.group(2))}") not in declared:
            orphans.append((i + 1, hid))
    return orphans


def find_duplicate_declarations(text: str) -> list[tuple[int, str]]:
    """Ids declared twice by a full block.

    `parse_ledger` keeps the first declaration and treats later mentions as
    references, which is what stops a results table double-counting - but a
    second `### E1-H7` block is a real collision, and it must not hide behind
    that rule. The duplicate-ordinal check cannot see it: both share one id.
    """
    lines, _ = _strip_fences(text.splitlines())
    seen: set[str] = set()
    dupes = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if not m:
            continue
        hid = f"{m.group('batch')}-H{int(m.group('ordinal'))}"
        if hid in seen:
            dupes.append((i + 1, hid))
        seen.add(hid)
    return dupes


def _read_block(
    lines: list[str], raw_lines: list[str], start: int, level: int
) -> tuple[dict[str, str], str]:
    """Collect a full-block hypothesis: its fields and its verbatim text.

    The block runs to the next heading at the same level or shallower, so a
    deeper sub-heading stays inside the hypothesis it belongs to - EXCEPT when
    that sub-heading is itself a hypothesis. A nested declaration ends the
    block, or its fields leak upward and the parent reports a verdict it never
    recorded; a fabricated verdict is worse than the null the compact shape
    deliberately returns. A following compact declaration ends it for the same
    reason, which also stops `show` bleeding into the next hypothesis.
    """
    end = len(lines)
    for j in range(start + 1, len(lines)):
        h = re.match(r"^(#{1,6})\s", lines[j])
        if h and len(h.group(1)) <= level:
            end = j
            break
        if HEADING_RE.match(lines[j]) or _compact_declaration(lines[j]):
            end = j
            break

    fields: dict[str, str] = {}
    # Names whose stored value came from a `- **Name (qualifier)**` bullet.
    from_qualified: set[str] = set()
    body = lines[start + 1 : end]
    for offset, line in enumerate(body):
        fm = FIELD_RE.match(line)
        if not fm:
            continue
        written = fm.group("name").strip()
        name = _base_name(written)
        qualified = written != name
        # First wins, EXCEPT that the plain bullet outranks a qualified one
        # already stored. A real ledger writes `- **Verdict (interim)**` above
        # the `- **Verdict**` that supersedes it, and first-wins alone reported
        # the interim as the record: one kgf hypothesis read "gate PASSED
        # decisively" while its own recorded verdict was "REFUTED by 1.7 pts".
        # Confidently wrong on the round-state tally is the failure this
        # parser refuses everywhere else.
        if name not in fields or (not qualified and name in from_qualified):
            if qualified:
                from_qualified.add(name)
            else:
                from_qualified.discard(name)
            value = (fm.group("value") or "").strip()
            # A field may be written as indented sub-bullets instead of inline
            # (the template renders `Log` that way); the content is on the
            # following lines, so the bullet is not empty.
            if not value:
                # A loose CommonMark list puts blank lines between the parent
                # bullet and its nested items, and a list is not terminated by
                # them - so scan to the first non-blank line, not a fixed
                # window. It must be an indented LIST ITEM: an indented comment
                # or stray text would otherwise pass a blank field as filled.
                nxt = next((ln for ln in body[offset + 1 :] if ln.strip()), "")
                if nxt[:1].isspace() and nxt.lstrip()[:1] in "-*+":
                    value = nxt.strip()
            qualifier = fm.group("qualifier")
            fields[name] = f"{qualifier} {value}".strip() if qualifier else value

    return fields, "\n".join(raw_lines[start:end]).rstrip()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _load(path: Path) -> tuple[str, list[Hypothesis]] | None:
    if not path.is_file():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"ERROR: {path} is not valid UTF-8", file=sys.stderr)
        return None
    # An unterminated fence blanks every hypothesis below it, so EVERY command
    # would answer confidently about a ledger it cannot see - `list` under-
    # counting the tally, `show` reporting a present hypothesis as missing.
    # Refusing here is the one place that covers all four.
    _, unterminated = _strip_fences(text.splitlines())
    if unterminated is not None:
        print(
            f"ERROR: {path}: line {unterminated}: code fence is never closed, so every "
            "hypothesis below it is invisible - refusing to answer",
            file=sys.stderr,
        )
        return None
    return text, parse_ledger(text)


def cmd_next_id(path: Path, as_json: bool) -> int:
    """The next free global H ordinal and the next batch token.

    Fanout dedupes against the global H-ordinal registry before proposing a
    round; resetting the ordinal makes one number name several hypotheses and
    has to be undone later, so this is the number that must not be guessed.
    """
    # One high-water mark for the whole module - `_next_free` is the same
    # computation with the same orphan refusal, and two copies of the rule that
    # must not be guessed is the rule drifting in waiting.
    ready = _next_free(path)
    if ready is None:
        return 1
    _, hyps, next_h, next_batch = ready

    payload = {
        "next_h": next_h,
        "next_batch": next_batch,
        "hypotheses": len(hyps),
        "batches": len({h.batch for h in hyps}),
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"next_h: H{next_h}")
        print(f"next_batch: {next_batch}")
        print(f"in ledger: {len(hyps)} hypotheses across {payload['batches']} batches")
    return 0


def cmd_list(
    path: Path, verdict: str | None, batch: str | None, author: str | None, as_json: bool
) -> int:
    """Every hypothesis with its verdict - the round-state tally in one call."""
    loaded = _load(path)
    if loaded is None:
        return 1
    _, hyps = loaded

    rows = hyps
    if batch:
        rows = [h for h in rows if h.batch.lower() == batch.lower()]
    if author:
        want_author = author if author.startswith("@") else "@" + author
        rows = [h for h in rows if h.author == want_author]
    if verdict:
        want = verdict.strip().lower()
        present = {(h.verdict or "").lower() for h in rows}
        if want in ("none", "null", "unverdicted"):
            rows = [h for h in rows if h.verdict is None]
        elif want not in {v.lower() for v in VERDICTS} and want not in present:
            # An unknown label would otherwise return a confident empty table,
            # indistinguishable from a genuine zero. The ledger's own labels
            # count as known - the vocabulary is open by design.
            occurring = sorted({h.verdict for h in rows if h.verdict})
            print(
                f"ERROR: {verdict!r} is not a verdict label; canonical: "
                f"{', '.join(VERDICTS)}; in this ledger: "
                f"{', '.join(occurring) or '(none)'}; or 'none'",
                file=sys.stderr,
            )
            return 2
        else:
            unread = sum(1 for h in rows if h.verdict is None and h.verdict_raw is None)
            rows = [h for h in rows if (h.verdict or "").lower() == want]
            if unread:
                # A compact hypothesis carries its verdict in prose the parser
                # does not read; an empty table would look like a genuine zero.
                print(
                    f"note: {unread} hypotheses not judged (verdict unreadable)",
                    file=sys.stderr,
                )

    if as_json:
        print(json.dumps([h.to_dict() for h in rows], indent=2))
        return 0

    if not rows:
        print("no hypotheses match")
        return 0

    id_w = max(len(h.hid) for h in rows)
    slug_w = min(max((len(h.slug) for h in rows), default=4), 46)
    print(f"{'ID':<{id_w}}  {'SLUG':<{slug_w}}  {'SHAPE':<7}  VERDICT")
    for h in rows:
        slug = h.slug if len(h.slug) <= slug_w else h.slug[: slug_w - 1] + "…"
        print(f"{h.hid:<{id_w}}  {slug:<{slug_w}}  {h.shape:<7}  {h.verdict or '-'}")

    tally: dict[str, int] = {}
    for h in rows:
        tally[h.verdict or "unverdicted"] = tally.get(h.verdict or "unverdicted", 0) + 1
    summary = ", ".join(f"{k} {v}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))
    print(f"\n{len(rows)} hypotheses | {summary}")
    return 0


def cmd_show(path: Path, hid: str, as_json: bool) -> int:
    """One hypothesis verbatim, so the agent reads it instead of the ledger."""
    loaded = _load(path)
    if loaded is None:
        return 1
    _, hyps = loaded

    want = hid.strip().lower()
    hit = next((h for h in hyps if h.hid.lower() == want), None)
    if hit is None:
        # An ordinal alone is unambiguous - it is global and never reset.
        bare = want.lstrip("h")
        if bare.isdigit():
            hit = next((h for h in hyps if h.ordinal == int(bare)), None)
    if hit is None:
        print(f"ERROR: {hid} not found in {path}", file=sys.stderr)
        return 1

    if as_json:
        print(json.dumps({**hit.to_dict(), "block": hit.block}, indent=2))
    else:
        print(hit.block)
    return 0


def cmd_check(path: Path) -> int:
    """Validate the ledger's machine-checkable invariants.

    Errors are unambiguous defects. Warnings are shapes the skill permits but
    that cost a reader something - the template is a checklist to judge
    against, not a blank form, so a missing optional field is never an error.
    """
    loaded = _load(path)
    if loaded is None:
        return 1
    text, hyps = loaded

    errors: list[str] = []
    warnings: list[str] = []

    for line, hid in find_orphan_ids(text, {h.hid for h in hyps}):
        errors.append(
            f"line {line}: {hid} looks like a declaration but did not parse - "
            "an id first in a plain heading or a `- **id slug**` bullet"
        )

    for line, hid in find_duplicate_declarations(text):
        errors.append(f"line {line}: {hid} is declared twice; the second block is ignored")

    seen: dict[int, Hypothesis] = {}
    for h in hyps:
        if h.ordinal in seen:
            errors.append(
                f"line {h.line}: {h.hid} reuses ordinal H{h.ordinal}, already "
                f"declared by {seen[h.ordinal].hid} at line {seen[h.ordinal].line} - "
                "the ordinal is global and never reset"
            )
        else:
            seen[h.ordinal] = h

    noncanon: dict[str, int] = {}
    for h in hyps:
        raw = h.verdict_raw
        if raw and h.verdict is None:
            errors.append(
                f"line {h.line}: {h.hid} verdict {raw.split(';')[0].strip()!r} carries no "
                "readable label - open the bullet with the label, then `;` and the number"
            )
        elif h.verdict is not None and h.verdict not in VERDICTS:
            noncanon[h.verdict] = noncanon.get(h.verdict, 0) + 1
    if noncanon:
        # One line, not one per hypothesis - a ledger-grown vocabulary is
        # legitimate, and 40 identical warnings would bury the real ones.
        labels = ", ".join(
            f"{k} ({v})" for k, v in sorted(noncanon.items(), key=lambda kv: -kv[1])
        )
        warnings.append(
            f"non-canonical verdict labels: {labels} - the canonical set is "
            f"{', '.join(VERDICTS)}; a consistent vocabulary keeps the tally comparable"
        )

    if CANONICAL_MARKER not in text:
        warnings.append(f"no {CANONICAL_MARKER} marker - this may not be the canonical log")

    # One line, not one per hypothesis - 27 identical warnings on a shipped
    # example trains a reader to skip the block where the real ones live.
    compact = [h for h in hyps if h.shape == "compact"]
    if compact:
        shown = ", ".join(str(h.line) for h in compact[:5])
        more = f", +{len(compact) - 5} more" if len(compact) > 5 else ""
        warnings.append(
            f"{len(compact)} compact hypotheses (lines {shown}{more}) - "
            "verdicts not machine-readable"
        )

    tabled = [h for h in hyps if h.shape == "table"]
    if tabled:
        shown = ", ".join(str(h.line) for h in tabled[:5])
        more = f", +{len(tabled) - 5} more" if len(tabled) > 5 else ""
        warnings.append(
            f"{len(tabled)} hypotheses declared only by a table row (lines {shown}{more}) - "
            "readable, but a row cannot carry the full field set"
        )

    # Authorship: a handle nobody is on the roster for is a typo, and a typo
    # attributes work to a researcher who does not exist. Unauthored lines are
    # the ledgers' own history and only ever earn one aggregated warning.
    known = roster_of(text)
    unknown: dict[str, list[int]] = {}
    unauthored: list[int] = []
    for h in hyps:
        for offset, line in enumerate(h.block.splitlines()):
            m = LOG_LINE_RE.match(line)
            if not m:
                continue
            handle = m.group("author")
            if handle is None:
                unauthored.append(h.line + offset)
            elif handle not in known:
                unknown.setdefault(handle, []).append(h.line + offset)
    for handle, at in sorted(unknown.items()):
        shown = ", ".join(str(n) for n in at[:5]) + (
            f", +{len(at) - 5} more" if len(at) > 5 else ""
        )
        errors.append(
            f"line {at[0]}: {handle} is not on the ## Authors roster "
            f"({len(at)} log line(s): {shown}) - add them with `author` or fix the handle"
        )
    if unauthored:
        shown = ", ".join(str(n) for n in unauthored[:5])
        more = f", +{len(unauthored) - 5} more" if len(unauthored) > 5 else ""
        warnings.append(
            f"{len(unauthored)} log lines carry no @handle (lines {shown}{more}) - "
            "written before the roster or by hand; every CLI write records its author"
        )

    # A hypothesis with neither Result nor Verdict is unrun - a state the
    # skill designs for (register, sign off, then execute), so it is counted
    # in the summary rather than warned about eleven times per fanout.
    unrun: list[str] = []
    lacking: dict[str, list[str]] = {}
    for h in hyps:
        if h.shape != "full":
            continue
        # An empty bullet is not a recorded field. `- **Verdict** -` left the
        # key present and the value blank, which satisfied both checks at once
        # and let a hypothesis with no verdict and no bar pass clean.
        # Strip the qualifier before testing: `- **Acceptance bar** (v2) -`
        # stored "(v2)", which is non-empty and let a blank bar pass clean.
        missing = [
            f
            for f in REQUIRED_FIELDS
            if not re.sub(r"^\([^)]*\)\s*", "", h.fields.get(f, "")).strip()
        ]
        if "Result" in missing and "Verdict" in missing:
            unrun.append(h.hid)
            missing = [f for f in missing if f not in ("Result", "Verdict")]
        for f in missing:
            lacking.setdefault(f, []).append(h.hid)
    # One line per field, not one per hypothesis - 17 `has no Lever` lines on
    # a ledger written before Lever existed bury the one warning that matters.
    for f in REQUIRED_FIELDS:
        ids = lacking.get(f)
        if ids:
            shown = ", ".join(ids[:5]) + (f", +{len(ids) - 5} more" if len(ids) > 5 else "")
            warnings.append(f"{len(ids)} hypotheses have no {f} ({shown})")

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    tally = f"{len(hyps)} hypotheses, "
    tally += f"{len(errors)} errors" if errors else "no errors"
    tally += f", {len(unrun)} unrun" if unrun else ""
    tally += f", {len(warnings)} warnings"
    if errors:
        print(f"FAIL: {tally}")
        return 1
    print(f"OK: {tally}")
    return 0


# ---------------------------------------------------------------------------
# Authors - the roster every write is checked against
# ---------------------------------------------------------------------------


def roster_of(text: str) -> dict[str, str]:
    """handle -> name, read off the `## Authors` section. Empty when absent."""
    out: dict[str, str] = {}
    inside = False
    # Fence-stripped, as `pm_tools.roster_of` reads it and as every other scan
    # in this module does. Reading raw cut both ways: a roster written inside a
    # ```markdown example granted an unrostered handle write authority, and a
    # fenced block INSIDE a real `## Authors` section emptied the roster and
    # refused the author who was on it.
    for line in _strip_fences(text.splitlines())[0]:
        h = ANY_HEADING_RE.match(line)
        if h:
            inside = len(h.group(1)) == 2 and h.group(2).strip().lower() == ROSTER_HEADING.lower()
            continue
        if inside:
            m = ROSTER_RE.match(line)
            if m:
                out[m.group(1)] = m.group(2).strip()
    return out


def need_author(path: Path, text: str, handle: str) -> str | None:
    """The normalised handle, or None after saying why it cannot be used.

    A write names who made it, and the handle must already be on the roster -
    an unrostered handle is a typo far more often than a new researcher, and
    the ledger has no way to tell them apart after the fact.
    """
    h = handle if handle.startswith("@") else "@" + handle
    if not HANDLE_RE.fullmatch(h):
        print(
            f"ERROR: bad handle {handle!r}; use @ plus 2-4 lowercase characters, e.g. @kj",
            file=sys.stderr,
        )
        return None
    known = roster_of(text)
    if h not in known:
        have = ", ".join(sorted(known)) or "(roster empty)"
        print(
            f"ERROR: {h} is not on the ## Authors roster of {path} - have: {have}. "
            f'Run: hypothesis-tools author {path} --handle {h} --name "Full Name"',
            file=sys.stderr,
        )
        return None
    return h


def cmd_author(path: Path, handle: str, name: str) -> int:
    """Add or update one roster entry, creating the `## Authors` section."""
    loaded = _load(path)
    if loaded is None:
        return 1
    text, _ = loaded
    h = handle if handle.startswith("@") else "@" + handle
    if not HANDLE_RE.fullmatch(h):
        print(
            f"ERROR: bad handle {handle!r}; use @ plus 2-4 lowercase characters, e.g. @kj",
            file=sys.stderr,
        )
        return 2

    lines = text.splitlines()
    entry = f"- `{h}` {name.strip()}"
    start = end = None
    # Positions are read off the fence-stripped view and applied to the raw
    # lines - `_strip_fences` blanks fenced lines in place, so the indices
    # agree. A fenced `## Authors` example must not attract the write.
    scan = _strip_fences(lines)[0]
    for i, line in enumerate(scan):
        m = ANY_HEADING_RE.match(line)
        if m and len(m.group(1)) == 2 and m.group(2).strip().lower() == ROSTER_HEADING.lower():
            start = i
        elif m and start is not None:
            end = i
            break
    if start is None:
        # The roster is document metadata: under the H1 and the overview,
        # above the first round - never between a round and its hypotheses.
        at = next(
            (
                i
                for i, line in enumerate(scan)
                if (m := ANY_HEADING_RE.match(line)) and len(m.group(1)) == 2
            ),
            len(lines),
        )
        block = [f"## {ROSTER_HEADING}", "", entry, ""]
        if at > 0 and lines[at - 1].strip():
            block = [""] + block
        lines[at:at] = block
        what = "roster created"
    else:
        end = end if end is not None else len(lines)
        for i in range(start, end):
            m = ROSTER_RE.match(scan[i])
            if m and m.group(1) == h:
                lines[i] = entry
                what = "updated"
                break
        else:
            at = end
            while at - 1 > start and not lines[at - 1].strip():
                at -= 1
            lines[at:at] = [entry]
            what = "added"

    new_text = "\n".join(lines) + "\n"
    path.write_text(new_text, encoding="utf-8")
    print(f"{h} {what}; roster: {', '.join(sorted(roster_of(new_text)))}")
    return 0


# ---------------------------------------------------------------------------
# Writes - append-only, mirroring the ledger's own discipline
# ---------------------------------------------------------------------------

# The canonical field order for a registered block; unknown fields follow in
# the order given. Result, Verdict and Log are deliberately absent: a
# registration precedes its result - record those with `result` / `verdict` /
# `log-event` once the run has happened.
REGISTER_ORDER = (
    "Hypothesis",
    "Lever",
    "Mechanism",
    "Prediction",
    "Acceptance bar",
    "Pre-experiment",
    "Experiment",
)
_UNREGISTERABLE = {"result", "verdict", "log"}


def _claimed_bare_ordinals(text: str) -> list[int]:
    """Ordinals claimed by a bullet whose bold label drops the batch prefix.

    `- **H655** - cross-query associative memory` is how the flagship ledger
    writes a gated registration, and `ID_TOKEN_RE` cannot see it: no batch
    prefix, so neither the parser NOR the orphan net reports it, and `next-id`
    answered H655 on a document that had already assigned H655 and H656.

    Counted, not refused. Refusing would block every read and write on that
    ledger until its author rewrote 25 recorded lines - in a tool whose skill
    forbids free-editing the file. Across the four real stores and every
    shipped example this changes exactly one answer, and to the correct one;
    a false positive can only skip an ordinal, never re-issue one, so the
    error direction is safe by construction.
    """
    return [
        int(m.group(1))
        for line in _strip_fences(text.splitlines())[0]
        if (m := re.match(r"^\s*[-*+]\s+\*\*\s*H(\d+)\b", line))
    ]


def _next_free(path: Path) -> tuple[str, list[Hypothesis], int, str] | None:
    """Load and answer (text, hyps, next_h, next_batch), refusing on orphans.

    The same refusal as `next-id`: an unparsed declaration means the highest
    ordinal may not be the highest, and writing past it burns a number twice.
    """
    loaded = _load(path)
    if loaded is None:
        return None
    text, hyps = loaded
    orphans = find_orphan_ids(text, {h.hid for h in hyps})
    if orphans:
        for line, hid in orphans:
            print(
                f"ERROR: line {line}: {hid} looks like a declaration but did not parse",
                file=sys.stderr,
            )
        print(
            f"ERROR: refusing - {len(orphans)} unparsed declaration(s) mean the next "
            "free ordinal cannot be trusted; run `check` and fix them first",
            file=sys.stderr,
        )
        return None
    next_h = max([h.ordinal for h in hyps] + _claimed_bare_ordinals(text), default=0) + 1
    batches = {h.batch for h in hyps}
    if batches:
        top = max(batches, key=lambda b: (int(b[1:]), b))
        next_batch = f"{top[0]}{int(top[1:]) + 1:0{len(top) - 1}d}"
    else:
        next_batch = "E01"
    return text, hyps, next_h, next_batch


def cmd_register(
    path: Path,
    slug: str,
    fields: list[tuple[str, str]],
    batch: str | None,
    new_batch: bool,
    batch_slug: str | None,
    as_json: bool,
    author: str,
) -> int:
    """Append a pre-registered hypothesis at the next free ordinal.

    Registration is the pre-commitment the skill demands before anything runs,
    so the block carries the declaration fields only - `result` and `verdict`
    record the outcome later, and passing them here is refused rather than
    letting a "registration" arrive already decided.
    """
    ready = _next_free(path)
    if ready is None:
        return 1
    text, hyps, next_h, next_batch = ready
    who = need_author(path, text, author)
    if who is None:
        return 2

    for name, _ in fields:
        if _base_name(name).lower().rstrip("s") in _UNREGISTERABLE:
            print(
                f"ERROR: {name!r} is not a registration field - a registration "
                "precedes its outcome; record it with `result` / `verdict` / "
                "`log-event` after the run",
                file=sys.stderr,
            )
            return 2

    if new_batch:
        use_batch = next_batch
    elif batch:
        use_batch = batch
        known = {h.batch for h in hyps}
        if known and use_batch not in known and use_batch != next_batch:
            styles = {b[0] for b in known}
            if use_batch[:1] not in styles or not use_batch[1:].isdigit():
                print(
                    f"ERROR: batch {batch!r} does not match this ledger's tokens "
                    f"({', '.join(sorted(known)[:6])}...); pass --new-batch for the "
                    f"next one ({next_batch})",
                    file=sys.stderr,
                )
                return 2
    else:
        known = {h.batch for h in hyps}
        use_batch = max(known, key=lambda b: (int(b[1:]), b)) if known else next_batch

    hid = f"{use_batch}-H{next_h}"

    ordered: list[tuple[str, str]] = []
    given = dict(fields)
    for name in REGISTER_ORDER:
        for gname, gvalue in fields:
            if gname.strip().lower() == name.lower():
                ordered.append((name, gvalue))
                given.pop(gname, None)
    for gname, gvalue in fields:
        if gname in given:
            ordered.append((gname.strip(), gvalue))

    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if use_batch not in {h.batch for h in hyps}:
        heading = f"## {use_batch}" + (f" - {batch_slug}" if batch_slug else "")
        lines += ["", heading]
    lines += ["", f"### {hid} {slug}", ""]
    lines += [f"- **{name}** - {value}" for name, value in ordered]
    lines += ["- **Log**", _log_entry(who, "registered")]
    new_text = "\n".join(lines) + "\n"

    # Verify before writing: the registered id must parse back, or the write
    # would create exactly the orphan the tool refuses to work around.
    reparsed = {h.hid: h for h in parse_ledger(new_text)}
    # `+ 1` is the Log bullet; a name given twice, a name with `*` in it, or a
    # name opening with a hypothesis id (the reader takes it for a declaration
    # that ends the block) reads back as fewer fields than were written.
    if hid not in reparsed or len(reparsed[hid].fields) != len(ordered) + 1:
        print(
            f"ERROR: {hid} would not parse back after writing - not written; "
            "check the slug for characters that break the declaration line, "
            "and the field names for `*`, a name given twice, or an opening hypothesis id",
            file=sys.stderr,
        )
        return 1
    path.write_text(new_text, encoding="utf-8")
    if as_json:
        print(json.dumps({**reparsed[hid].to_dict(), "registered": True}, indent=2))
    else:
        print(f"registered {hid} at line {reparsed[hid].line} by {who}")
    return 0


def _locate(hyps: list[Hypothesis], hid: str) -> Hypothesis | None:
    want = hid.strip().lower()
    hit = next((h for h in hyps if h.hid.lower() == want), None)
    if hit is None:
        bare = want.lstrip("h")
        if bare.isdigit():
            hit = next((h for h in hyps if h.ordinal == int(bare)), None)
    return hit


def _writable_block(path: Path, hid: str) -> tuple[list[str], Hypothesis] | None:
    """The raw lines and the FULL-block hypothesis a write may append into."""
    loaded = _load(path)
    if loaded is None:
        return None
    text, hyps = loaded
    hit = _locate(hyps, hid)
    if hit is None:
        print(f"ERROR: {hid} not found in {path}", file=sys.stderr)
        return None
    if hit.shape != "full":
        print(
            f"ERROR: {hit.hid} is declared by a {hit.shape} "
            f"{'row' if hit.shape == 'table' else 'bullet'} (line {hit.line}); only a "
            "full block takes appended fields - give it a `### id slug` block first",
            file=sys.stderr,
        )
        return None
    return text.splitlines(), hit


def _block_span(lines: list[str], h: Hypothesis) -> tuple[int, int]:
    """0-indexed [start, end) of the block in the raw lines."""
    start = h.line - 1
    return start, start + len(h.block.splitlines())


def _field_lines(lines: list[str], h: Hypothesis) -> dict[str, int]:
    """0-indexed line of each field bullet in the block, by base name.

    Same precedence as `_read_block`, and it has to be: while this one was
    plain first-wins and the parser preferred the unqualified bullet, the two
    disagreed about which line IS the field. `field --update` then rewrote the
    superseded `- **Grounding (superseded)**` while every reader kept returning
    `- **Grounding**` - the write was lost and the audit line reported success.
    A test pins the two functions to one answer.
    """
    start, end = _block_span(lines, h)
    out: dict[str, int] = {}
    from_qualified: set[str] = set()
    for i in range(start + 1, end):
        fm = FIELD_RE.match(lines[i])
        if not fm:
            continue
        written = fm.group("name").strip()
        name = _base_name(written)
        qualified = written != name
        if name not in out or (not qualified and name in from_qualified):
            out[name] = i
            from_qualified.add(name) if qualified else from_qualified.discard(name)
    return out


def _last_content(lines: list[str], h: Hypothesis) -> int:
    """0-indexed line after the block's last non-blank line."""
    start, end = _block_span(lines, h)
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return end


def _today() -> str:
    import datetime

    return datetime.date.today().isoformat()


def _log_entry(author: str, event: str, date: str | None = None) -> str:
    """One authored log line, indented under the Log bullet."""
    return f"  - log: {date or _today()} {author} - {event.strip()}"


def _insert_log_line(lines: list[str], h: Hypothesis, entry: str) -> int:
    """Append one log line to the hypothesis, creating `- **Log**` when absent.

    Newest lands last, so the log reads as the order things happened.
    """
    fields = _field_lines(lines, h)
    if "Log" in fields:
        _, end = _block_span(lines, h)
        at = fields["Log"] + 1
        while at < end and lines[at].startswith((" ", "\t")) and lines[at].strip():
            at += 1
        lines.insert(at, entry)
        return at
    at = _last_content(lines, h)
    lines[at:at] = ["- **Log**", entry]
    return at + 1


def cmd_result(path: Path, hid: str, text_value: str, qualifier: str | None, author: str) -> int:
    """Append a Result bullet. A recorded Result is immutable, so a re-run or a
    second phase appends another bullet, distinguished by its qualifier - the
    shape real ledgers already use (`- **Result (engine replay, 2026-07-11)**`)."""
    ready = _writable_block(path, hid)
    if ready is None:
        return 1
    lines, h = ready
    who = need_author(path, "\n".join(lines), author)
    if who is None:
        return 2
    fields = _field_lines(lines, h)
    qualifier = qualifier.strip() if qualifier else qualifier
    if "Result" in fields and not qualifier:
        print(
            f"ERROR: {h.hid} already records a Result (line {fields['Result'] + 1}) and a "
            "recorded Result is immutable - pass --qualifier to append a distinguishable "
            "second reading (a re-run, another phase), or log the change with log-event",
            file=sys.stderr,
        )
        return 2
    # Stripped, like every other written value. Unstripped, a TRAILING line
    # break - which the single-line guard deliberately allows, because it
    # merges into the line terminator everywhere else - tore this bullet in
    # two: `- **Result (rerun<CR>)** - ...` parsed as neither a Result nor
    # anything else, and `check` called the file clean.
    label = f"- **Result ({qualifier})**" if qualifier else "- **Result**"
    bullet = f"{label} - {text_value.strip()}"
    if _unreadable(bullet, "Result"):
        print(
            f"ERROR: {bullet!r} would not read back as a Result - not written; "
            "check the qualifier for `*`, which no field label can carry",
            file=sys.stderr,
        )
        return 2
    at = fields.get("Verdict", fields.get("Log", _last_content(lines, h)))
    # The audit line goes in first: its position was computed on the current
    # lines, and it always sits at or after the field bullet, so inserting the
    # bullet afterwards shifts it down instead of landing behind it.
    event = f"result recorded ({qualifier})" if qualifier else "result recorded"
    _insert_log_line(lines, h, _log_entry(who, event))
    lines.insert(at, bullet)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{path}:{at + 1}: {h.hid} result recorded by {who}")
    return 0


def cmd_verdict(path: Path, hid: str, text_value: str, author: str) -> int:
    """Record the one verdict a hypothesis gets. A second is refused: a recorded
    verdict is immutable, and later evidence is a new round superseding it."""
    ready = _writable_block(path, hid)
    if ready is None:
        return 1
    lines, h = ready
    who = need_author(path, "\n".join(lines), author)
    if who is None:
        return 2
    # Presence, not value - the test `cmd_result` already applies. Testing the
    # VALUE let an empty `- **Verdict** -` placeholder through: the write
    # reported success, first-wins kept the blank bullet as the canonical
    # verdict, `list` still read unverdicted, and the guard never fired again,
    # so three calls stacked three Verdict bullets.
    at = _field_lines(lines, h).get("Verdict")
    if at is not None:
        carried = (
            f"({h.verdict or h.verdict_raw!r})" if h.verdict_raw else "(empty, fill it by hand)"
        )
        print(
            f"ERROR: {h.hid} already carries a Verdict bullet at line {at + 1} {carried} and a "
            "recorded verdict is immutable - a flip is a new round with a back-reference, "
            "and a re-run on the same claim registers a fresh hypothesis",
            file=sys.stderr,
        )
        return 2
    label = match_verdict(text_value)
    if label is None:
        print(
            f"ERROR: no readable label opens {text_value!r} - open with the label, "
            f"then `;` and the number that justifies it (canonical: {', '.join(VERDICTS)})",
            file=sys.stderr,
        )
        return 2
    if label not in VERDICTS:
        print(
            f"note: {label!r} is not canonical ({', '.join(VERDICTS)}) - recorded as given",
            file=sys.stderr,
        )
    fields = _field_lines(lines, h)
    at = fields.get("Log", _last_content(lines, h))
    _insert_log_line(lines, h, _log_entry(who, f"verdict recorded: {label}"))
    lines.insert(at, f"- **Verdict** - {text_value.strip()}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{path}:{at + 1}: {h.hid} verdict recorded by {who}: {label}")
    return 0


def cmd_log_event(path: Path, hid: str, event: str, date: str | None, author: str) -> int:
    """Append one dated line to the hypothesis's Log, creating the Log bullet
    at the end of the block when it does not exist yet."""
    stamp = date or _today()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
        print(f"ERROR: --date must be YYYY-MM-DD, got {stamp!r}", file=sys.stderr)
        return 2
    ready = _writable_block(path, hid)
    if ready is None:
        return 1
    lines, h = ready
    who = need_author(path, "\n".join(lines), author)
    if who is None:
        return 2
    at = _insert_log_line(lines, h, _log_entry(who, event, stamp))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{path}:{at + 1}: {h.hid} logged by {who}")
    return 0


def cmd_field(path: Path, hid: str, name: str, text_value: str, update: bool, author: str) -> int:
    """Add - or with --update replace - one field on an existing hypothesis.

    The template's field set is a checklist, not a form: real ledgers carry
    hundreds of their own names (`Grounding`, `Persona`, `Status`, `Vet`), and
    a researcher who can only add fields at registration ends up hand-editing
    the ledger the tool is meant to own.
    """
    if not _base_name(name):
        print(
            f"ERROR: {name!r} is not a field name - a name that is empty once its "
            "qualifier is removed writes a bullet no reader can match",
            file=sys.stderr,
        )
        return 2
    if _base_name(name).lower().rstrip("s") in _UNREGISTERABLE:
        print(
            f"ERROR: {name!r} is an outcome field with its own command and its own "
            "immutability rule - use `result`, `verdict` or `log-event`",
            file=sys.stderr,
        )
        return 2
    ready = _writable_block(path, hid)
    if ready is None:
        return 1
    lines, h = ready
    who = need_author(path, "\n".join(lines), author)
    if who is None:
        return 2
    fields = _field_lines(lines, h)
    label = name.strip()
    # `_field_lines` keys by base name, so the lookup must too: comparing the
    # raw label let `--name "Grounding (v2)"` miss an existing `Grounding` and
    # append a second bullet the parser could never reach, with `--update`
    # appending a third rather than replacing.
    key = _base_name(label)

    if key in fields:
        if not update:
            existing = FIELD_RE.match(lines[fields[key]])
            print(
                f"ERROR: {h.hid} already carries "
                f"{existing.group('name').strip()!r} (line {fields[key] + 1}) - "
                "pass --update to replace the value; the ledger is append-only by "
                "default so a recorded field is not overwritten by accident",
                file=sys.stderr,
            )
            return 2
        at = fields[key]
        fm = FIELD_RE.match(lines[at])
        # Keep the label and any qualifier exactly as written - the qualifier
        # belongs to the value, and rewriting it changes what the field is.
        head = f"- **{fm.group('name').strip()}**"
        if fm.group("qualifier"):
            head += f" {fm.group('qualifier')}"
        # The audit line names the bullet as WRITTEN, not the base name that
        # found it: `--name "Acceptance bar"` resolves a bullet written
        # `- **Acceptance bar (two-sided)**`, and a log line naming the base
        # sends a later reader looking for a bullet the block does not have.
        written = fm.group("name").strip()
        lines[at] = f"{head} - {text_value.strip()}"
        _insert_log_line(lines, h, _log_entry(who, f"field {written} updated"))
        what = "updated"
    else:
        # A new field lands before the outcomes, so the block still reads
        # declaration first, measurement second, judgment last.
        at = min(
            [fields[f] for f in ("Result", "Verdict", "Log") if f in fields]
            or [_last_content(lines, h)]
        )
        bullet = f"- **{label}** - {text_value.strip()}"
        if _unreadable(bullet, key):
            print(
                f"ERROR: {bullet!r} would not read back as {key!r} - not written; "
                "check the name for `*`, which no field label can carry, or for an "
                "opening hypothesis id, which the reader takes as a declaration",
                file=sys.stderr,
            )
            return 2
        _insert_log_line(lines, h, _log_entry(who, f"field {label} added"))
        lines.insert(at, bullet)
        written, what = label, "added"

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{path}:{at + 1}: {h.hid} {written} {what} by {who}")
    return 0


# ---------------------------------------------------------------------------
# Report and measured quantities
# ---------------------------------------------------------------------------


def cmd_report(path: Path, as_json: bool) -> int:
    """The round state as one paste-ready table: batches down, verdicts across.

    The column set is the ledger's own vocabulary - canonical labels first in
    their canonical order, then the ledger-grown ones by frequency, capped so a
    35-label ledger still renders; the tail folds into `other`.
    """
    loaded = _load(path)
    if loaded is None:
        return 1
    _, hyps = loaded
    if not hyps:
        print("no hypotheses")
        return 0

    batches: list[str] = []
    for h in hyps:
        if h.batch not in batches:
            batches.append(h.batch)
    tally: dict[str, dict[str, int]] = {b: {} for b in batches}
    total: dict[str, int] = {}
    for h in hyps:
        key = h.verdict or "unverdicted"
        tally[h.batch][key] = tally[h.batch].get(key, 0) + 1
        total[key] = total.get(key, 0) + 1

    canon = [v for v in VERDICTS if v in total]
    grown = sorted(
        (k for k in total if k not in VERDICTS and k != "unverdicted"),
        key=lambda k: -total[k],
    )
    cols = (canon + grown)[:8]
    other = [k for k in canon + grown if k not in cols]

    if as_json:
        print(
            json.dumps(
                {
                    "batches": {b: tally[b] for b in batches},
                    "total": total,
                    "hypotheses": len(hyps),
                },
                indent=2,
            )
        )
        return 0

    def row(name: str, t: dict[str, int]) -> str:
        n = sum(t.values())
        cells = [str(t.get(c, 0) or "") for c in cols]
        oth = sum(t.get(k, 0) for k in other)
        return (
            f"| {name} | {n} | " + " | ".join(cells) + f" | {oth or ''} | "
            f"{t.get('unverdicted', 0) or ''} |"
        )

    head = "| Batch | N | " + " | ".join(cols) + " | other | unverdicted |"
    print(head)
    print("|" + "---|" * (len(cols) + 4))
    for b in batches:
        print(row(b, tally[b]))
    print(row("**Total**", total))
    print(
        f"\n{len(hyps)} hypotheses across {len(batches)} batches"
        + (f" | other: {', '.join(other)}" if other else "")
    )
    return 0


# A reading is the quantity's name - optionally backticked or bolded, with an
# optional parenthetical argument (`theta(0.08) = 0.7644`) - followed by an
# optional separator and one number token, comparator and unit included.
_NUM = r"[<>≤≥≈~]?\s*[+\-−±]?\d[\d,]*(?:\.\d+)?(?:e-?\d+)?\s*(?:%|x\b|ms\b|s\b)?"


def _quantity_re(quantity: str) -> re.Pattern:
    name = re.escape(quantity.strip()).replace(r"\ ", r"\s+")
    return re.compile(
        rf"(?<![A-Za-z0-9_]){name}[`*_']*\s*(?:\([^()]{{0,40}}\))?\s*(?:[=:→]|->)?\s*[`*_]*"
        rf"(?P<value>{_NUM})",
        re.I,
    )


def cmd_values(
    path: Path, quantity: str, batch: str | None, hid: str | None, as_json: bool
) -> int:
    """Every reading of one measured quantity, per hypothesis, with context.

    "What did gold_full read across E5" is otherwise a full re-read of the
    ledger; here it is one scan of the declared blocks. The match is textual
    on purpose - the context column is printed so a false hit is visible, not
    silently averaged into an answer.
    """
    loaded = _load(path)
    if loaded is None:
        return 1
    _, hyps = loaded
    rows = hyps
    if batch:
        rows = [h for h in rows if h.batch.lower() == batch.lower()]
    if hid:
        hit = _locate(rows, hid)
        rows = [hit] if hit else []
    pat = _quantity_re(quantity)

    readings = []
    for h in rows:
        for offset, line in enumerate(h.block.splitlines()):
            for m in pat.finditer(line):
                lo, hi = max(0, m.start() - 44), min(len(line), m.end() + 44)
                ctx = ("…" if lo else "") + line[lo:hi].strip() + ("…" if hi < len(line) else "")
                readings.append(
                    {
                        "id": h.hid,
                        "value": m.group("value").strip(),
                        "line": h.line + offset,
                        "context": ctx,
                    }
                )

    if as_json:
        print(json.dumps(readings, indent=2))
        return 0
    if not readings:
        print(f"no readings of {quantity!r}" + (f" in {batch}" if batch else ""))
        return 0
    id_w = max(len(r["id"]) for r in readings)
    val_w = max(len(r["value"]) for r in readings)
    for r in readings:
        print(f"{r['id']:<{id_w}}  {r['value']:>{val_w}}  (line {r['line']})  {r['context']}")
    ids = len({r["id"] for r in readings})
    print(f"\n{len(readings)} reading(s) of {quantity!r} across {ids} hypotheses")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hypothesis-tools",
        description="Query a canonical hypothesis experiments ledger without reading it.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_next = sub.add_parser("next-id", help="Next free H ordinal and batch token.")
    p_next.add_argument("ledger", type=Path)
    p_next.add_argument("--json", action="store_true")

    p_list = sub.add_parser("list", help="Every hypothesis with its verdict.")
    p_list.add_argument("ledger", type=Path)
    p_list.add_argument("--verdict", help="Filter by verdict label, or 'none' for unverdicted.")
    p_list.add_argument("--batch", help="Filter by batch token, e.g. E12.")
    p_list.add_argument("--author", help="Filter by the handle that registered it, e.g. @kj.")
    p_list.add_argument("--json", action="store_true")

    p_auth = sub.add_parser("author", help="Add or update a `## Authors` roster entry.")
    p_auth.add_argument("ledger", type=Path)
    p_auth.add_argument("--handle", required=True, help="@ plus 2-4 lowercase characters.")
    p_auth.add_argument("--name", required=True, help="Full name.")

    p_show = sub.add_parser("show", help="One hypothesis verbatim.")
    p_show.add_argument("ledger", type=Path)
    p_show.add_argument("id", help="Hypothesis id (E12-H33) or bare ordinal (33).")
    p_show.add_argument("--json", action="store_true")

    p_check = sub.add_parser("check", help="Validate ledger invariants.")
    p_check.add_argument("ledger", type=Path)

    p_reg = sub.add_parser(
        "register",
        help="Append a pre-registered hypothesis at the next free ordinal.",
    )
    p_reg.add_argument("ledger", type=Path)
    p_reg.add_argument("--slug", required=True, help="2-3 part kebab-case slug.")
    p_reg.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="A declaration field; repeatable. The template's names render in canonical "
        "order (references/ledger-queries.md), other names follow as given. "
        "Result, Verdict and Log are refused - they come after the run.",
    )
    p_reg.add_argument("--batch", help="Batch token (E13); default: the ledger's latest.")
    p_reg.add_argument(
        "--new-batch", action="store_true", help="Open the next batch token instead."
    )
    p_reg.add_argument("--batch-slug", help="Slug for a newly opened batch heading.")
    p_reg.add_argument("--author", required=True, help="Roster handle, e.g. @kj.")
    p_reg.add_argument("--json", action="store_true")

    p_res = sub.add_parser("result", help="Append a Result bullet to one hypothesis.")
    p_res.add_argument("ledger", type=Path)
    p_res.add_argument("id")
    p_res.add_argument("--text", required=True, help="The measured numbers.")
    p_res.add_argument(
        "--qualifier",
        help="Distinguishes a second reading (a re-run, another phase); required then.",
    )
    p_res.add_argument("--author", required=True, help="Roster handle, e.g. @kj.")

    p_ver = sub.add_parser("verdict", help="Record the verdict - once; a flip is a new round.")
    p_ver.add_argument("ledger", type=Path)
    p_ver.add_argument("id")
    p_ver.add_argument("--text", required=True, help="`<label>; <justifying number>`.")
    p_ver.add_argument("--author", required=True, help="Roster handle, e.g. @kj.")

    p_fld = sub.add_parser("field", help="Add or replace one field on a hypothesis.")
    p_fld.add_argument("ledger", type=Path)
    p_fld.add_argument("id")
    p_fld.add_argument("--name", required=True, help="Field name, template or the ledger's own.")
    p_fld.add_argument("--text", required=True, help="The value.")
    p_fld.add_argument(
        "--update", action="store_true", help="Replace a value already recorded under this name."
    )
    p_fld.add_argument("--author", required=True, help="Roster handle, e.g. @kj.")

    p_log = sub.add_parser("log-event", help="Append a dated log line to one hypothesis.")
    p_log.add_argument("ledger", type=Path)
    p_log.add_argument("id")
    p_log.add_argument("--event", required=True)
    p_log.add_argument("--date", help="YYYY-MM-DD; default today.")
    p_log.add_argument("--author", required=True, help="Roster handle, e.g. @kj.")

    p_rep = sub.add_parser("report", help="Batches down, verdicts across - one table.")
    p_rep.add_argument("ledger", type=Path)
    p_rep.add_argument("--json", action="store_true")

    p_val = sub.add_parser("values", help="Every reading of one measured quantity, with context.")
    p_val.add_argument("ledger", type=Path)
    p_val.add_argument("quantity", help="The quantity's name as written, e.g. DR, gold_full.")
    p_val.add_argument("--batch", help="Restrict to one batch.")
    p_val.add_argument("--id", help="Restrict to one hypothesis.")
    p_val.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    # Every write embeds its value as ONE line of the ledger, so a newline in
    # any of them splits the block: a value carrying `### E9-H99 slug` minted a
    # hypothesis nobody registered, handed it the real one's Result and
    # Verdict, burnt an ordinal - and `check` reported the file clean.
    # Refused, never folded: rewriting the researcher's text is the one thing
    # this module promises not to do. The ledger's own multi-line form is
    # `<br>` (per-hypothesis-template.md, the Result bullet).
    for name in ("slug", "batch", "batch_slug", "name", "text", "event", "qualifier"):
        value = getattr(args, name, None)
        # `splitlines`, not `"\n" in ...` - the parser splits on nine characters
        # (CR, VT, FF, the separators, U+2028/9), so testing for the newline alone
        # left a bare CR from a captured run log or a PDF paste minting a phantom
        # hypothesis exactly as before. Guard and mechanism must ask one question.
        if isinstance(value, str) and len(value.splitlines()) > 1:
            print(
                f"ERROR: --{name.replace('_', '-')} must be a single line - a newline would "
                "split the block and can mint a hypothesis nobody registered; use `<br>` "
                "for a line break inside a value",
                file=sys.stderr,
            )
            return 2
    for raw in getattr(args, "field", []) or []:
        if len(raw.splitlines()) > 1:
            print(
                "ERROR: --field must be a single line - a newline would split the block "
                "and can mint a hypothesis nobody registered; use `<br>` for a line break",
                file=sys.stderr,
            )
            return 2

    if args.command == "next-id":
        return cmd_next_id(args.ledger, args.json)
    if args.command == "list":
        return cmd_list(args.ledger, args.verdict, args.batch, args.author, args.json)
    if args.command == "author":
        return cmd_author(args.ledger, args.handle, args.name)
    if args.command == "show":
        return cmd_show(args.ledger, args.id, args.json)
    if args.command == "check":
        return cmd_check(args.ledger)
    if args.command == "register":
        fields = []
        for raw in args.field:
            name, eq, value = raw.partition("=")
            if not eq or not name.strip():
                print(f"ERROR: --field takes NAME=VALUE, got {raw!r}", file=sys.stderr)
                return 2
            fields.append((name.strip(), value.strip()))
        return cmd_register(
            args.ledger,
            args.slug,
            fields,
            args.batch,
            args.new_batch,
            args.batch_slug,
            args.json,
            args.author,
        )
    if args.command == "result":
        return cmd_result(args.ledger, args.id, args.text, args.qualifier, args.author)
    if args.command == "verdict":
        return cmd_verdict(args.ledger, args.id, args.text, args.author)
    if args.command == "field":
        return cmd_field(args.ledger, args.id, args.name, args.text, args.update, args.author)
    if args.command == "log-event":
        return cmd_log_event(args.ledger, args.id, args.event, args.date, args.author)
    if args.command == "report":
        return cmd_report(args.ledger, args.json)
    if args.command == "values":
        return cmd_values(args.ledger, args.quantity, args.batch, args.id, args.json)
    return 1


if __name__ == "__main__":
    sys.exit(main())
