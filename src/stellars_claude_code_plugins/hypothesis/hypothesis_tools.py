"""Read-only queries over a canonical hypothesis experiments ledger.

An agent running a hypothesis campaign asks the same three questions
constantly: which H ordinals are already burnt (so a fanout does not re-test
one), what every verdict currently is, and the full text of one hypothesis.
Reading the whole ledger to answer them costs thousands of tokens per
question and gets worse every round - a twelve-round log is 300+ lines the
agent re-reads to learn one number. These commands answer each from a parse.

Nothing here writes to a ledger. The log is append-only and a recorded
verdict is immutable; a tool that could rewrite either would be a liability,
so the module has no write path at all.

Two hypothesis shapes exist in the wild and both parse:

    full-block   ### E12-H33 slug          + `- **Verdict** - Confirmed; ...`
    compact      - **E1-H1 slug** - prose (verdict lives in the prose)

Compact hypotheses yield `verdict=None`. That is deliberate: the verdict is
narrative there ("shipped", "**null**", "initially killed"), and guessing it
with a regex produces confident wrong answers - "the features were initially
killed" is a story about a fix, not a Killed verdict. Absent beats wrong.
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

    def to_dict(self) -> dict:
        return {
            "id": self.hid,
            "batch": self.batch,
            "ordinal": self.ordinal,
            "slug": self.slug,
            "shape": self.shape,
            "line": self.line,
            "verdict": self.verdict,
            "fields": self.fields,
        }


def match_verdict(raw: str) -> str | None:
    """Read the verdict label off a Verdict bullet, else None.

    The bullet is `<label>; <justifying number>` - the label is a closed
    vocabulary, the rest is prose. An unrecognised opening is reported as
    None so `check` can flag it rather than inventing a category.
    """
    text = raw.strip().lstrip("*").strip()
    # A qualifier outside the bold span (`- **Verdict** (re-run) - Ships`) is
    # kept in the value by design; the label follows it.
    text = re.sub(r"^\([^)]*\)\s*", "", text)
    # The label must end the value or be followed by `;` - a bare prefix match
    # read `Confirmed-partially` and `Refuted for k=1, Confirmed for k=3` as
    # clean single verdicts, which is the mixed-regime case the acceptance
    # rule exists to catch. Unmatched falls through to `check`'s label error.
    for label in VERDICTS:
        if re.match(rf"{re.escape(label)}\**\s*(?:;|$)", text, re.I):
            return label
    return None


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


def parse_ledger(text: str) -> list[Hypothesis]:
    """Parse every declared hypothesis, in document order.

    First occurrence of an id declares it; every later mention is a reference.
    A full-block heading and a compact bullet therefore cannot both declare the
    same hypothesis, which is what keeps results tables and benchmark rows from
    duplicating the hypotheses they cite.
    """
    raw_lines = text.splitlines()
    lines, _ = _strip_fences(raw_lines)
    found: dict[str, Hypothesis] = {}
    order: list[Hypothesis] = []

    for i, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        compact = None if heading else _compact_declaration(line)
        m = heading or compact
        if not m:
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
    body = lines[start + 1 : end]
    for offset, line in enumerate(body):
        fm = FIELD_RE.match(line)
        if not fm:
            continue
        name = fm.group("name").strip()
        # `Pre-experiment (probe)` -> `Pre-experiment`, so an optional
        # parenthetical gloss never changes the field's identity.
        name = re.sub(r"\s*\(.*\)$", "", name).strip()
        if name not in fields:
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
    loaded = _load(path)
    if loaded is None:
        return 1
    text, hyps = loaded

    # Refuse rather than under-report. An id the parser could not read means
    # the highest ordinal may not be the highest ordinal, and a wrong answer
    # here silently burns an ordinal twice - a loud failure is far better.
    orphans = find_orphan_ids(text, {h.hid for h in hyps})
    if orphans:
        for line, hid in orphans:
            print(
                f"ERROR: line {line}: {hid} looks like a declaration but did not parse",
                file=sys.stderr,
            )
        print(
            f"ERROR: refusing to answer - {len(orphans)} unparsed id(s) mean the next "
            "free ordinal cannot be trusted; run `check` and fix the declarations",
            file=sys.stderr,
        )
        return 1

    next_h = max((h.ordinal for h in hyps), default=0) + 1
    batches = {h.batch for h in hyps}
    if batches:
        # Sort on the NUMBER then the token - iterating a set let an E12/R12
        # tie resolve differently run to run, forking the round's naming.
        top_batch = max(batches, key=lambda b: (int(b[1:]), b))
        next_batch = f"{top_batch[0]}{int(top_batch[1:]) + 1:0{len(top_batch) - 1}d}"
    else:
        next_batch = "E01"

    payload = {
        "next_h": next_h,
        "next_batch": next_batch,
        "hypotheses": len(hyps),
        "batches": len(batches),
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"next_h: H{next_h}")
        print(f"next_batch: {next_batch}")
        print(f"in ledger: {len(hyps)} hypotheses across {len(batches)} batches")
    return 0


def cmd_list(path: Path, verdict: str | None, batch: str | None, as_json: bool) -> int:
    """Every hypothesis with its verdict - the round-state tally in one call."""
    loaded = _load(path)
    if loaded is None:
        return 1
    _, hyps = loaded

    rows = hyps
    if batch:
        rows = [h for h in rows if h.batch.lower() == batch.lower()]
    if verdict:
        want = verdict.strip().lower()
        if want in ("none", "null", "unverdicted"):
            rows = [h for h in rows if h.verdict is None]
        elif want not in {v.lower() for v in VERDICTS}:
            # An unknown label would otherwise return a confident empty table,
            # indistinguishable from a genuine zero.
            print(
                f"ERROR: {verdict!r} is not a verdict label; use one of "
                f"{', '.join(VERDICTS)}, or 'none'",
                file=sys.stderr,
            )
            return 2
        else:
            compact = sum(1 for h in rows if h.verdict is None)
            rows = [h for h in rows if (h.verdict or "").lower() == want]
            if compact:
                # A compact hypothesis carries its verdict in prose the parser
                # does not read; an empty table would look like a genuine zero.
                print(
                    f"note: {compact} compact hypotheses not judged (verdict unreadable)",
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

    for h in hyps:
        raw = h.verdict_raw
        if raw and h.verdict is None:
            errors.append(
                f"line {h.line}: {h.hid} verdict {raw.split(';')[0].strip()!r} is not "
                f"one of {', '.join(VERDICTS)}"
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

    for h in hyps:
        if h.shape == "compact":
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
        if missing:
            warnings.append(f"line {h.line}: {h.hid} has no {', '.join(missing)}")

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if errors:
        print(f"FAIL: {len(hyps)} hypotheses, {len(errors)} errors, {len(warnings)} warnings")
        return 1
    print(f"OK: {len(hyps)} hypotheses, no errors, {len(warnings)} warnings")
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
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="One hypothesis verbatim.")
    p_show.add_argument("ledger", type=Path)
    p_show.add_argument("id", help="Hypothesis id (E12-H33) or bare ordinal (33).")
    p_show.add_argument("--json", action="store_true")

    p_check = sub.add_parser("check", help="Validate ledger invariants.")
    p_check.add_argument("ledger", type=Path)

    args = parser.parse_args(argv)

    if args.command == "next-id":
        return cmd_next_id(args.ledger, args.json)
    if args.command == "list":
        return cmd_list(args.ledger, args.verdict, args.batch, args.json)
    if args.command == "show":
        return cmd_show(args.ledger, args.id, args.json)
    if args.command == "check":
        return cmd_check(args.ledger)
    return 1


if __name__ == "__main__":
    sys.exit(main())
