#!/usr/bin/env python3
"""pm-tools - query, lint, report and edit project-management tracking docs.

The markdown file is the entire store. Nothing is recorded twice: the next id is the
highest in the file plus one, and also above every sibling tracker's id of the same
prefix and category; the category index is computed by list-categories, backlinks are
computed by refs. No counter file, no index, no TOC.

  docs/acc-crit*.md   acceptance criteria, ids ACC-<CAT>-<N>-<CODE>, hint line `- test:`
  docs/defects*.md    defects,             ids DEF-<CAT>-<N>-<CODE>, hint line `- repro:`

A defect that is fixed and breaks again keeps a derived id: reopening
DEF-LNCH-3-PARSER opens DEF-LNCH-3-PARSER-1, then -2, then -3. The parent stays
closed with its evidence - it really was proven - so the ordinals count how often
that defect has regressed.

Both disciplines also carry `- test-tags: UNIT, FUNCTIONAL` - which kinds of test
cover the item (UNIT, INTEGRATION, FUNCTIONAL, E2E, MANUAL, or any word; written
upper-case, read in any case; an item with none sits in the NO-TEST bucket) - and
`- evidence: <one line>`, the proof it is actually done. `close` demands the
evidence and writes that line; `reject` on a closed item retires it into the log,
and so does `reopen` on a criterion, while on a closed defect `reopen` mints the
regression instead and the closure keeps its proof. check
fails on a relation to an id that is not in the scanned files, on a blocked-by or
override cycle and on an override written on one item only, and warns when an open
item is blocked by one that is closed or rejected, or is overridden; scan the
directory, not one file, so cross-file links resolve. It also warns on a base id
written on an item's line or a sub-line other than log: and attachment:, naming the
full id to write: `DEF-LNCH-3 has no code; write DEF-LNCH-3-PARSER`.

Each discipline registers one explanation, and it stacks: `- mechanism: <stamp> @xx
<text>` on a criterion says how it is meant to work, `- root-cause: <stamp> @xx <text>`
on a defect says why it happens. A second write puts a new record ABOVE the old one and
keeps it, so a theory that was superseded halfway through a long hunt is still readable;
`--update` rewrites the newest record instead, for a rewording of the same theory. The
topmost record is the current one - every query reports that one. Writing a record is
never logged; it carries its own stamp and author.

Three states: `- [ ]` open, `- [x]` closed, `- [-]` rejected (reason in the log line).
Log lines read `- log: 2026-08-27T15:59:12Z @kj <event>` - ISO 8601 UTC, then the author.
The same line without indent records a change wider than one item: a tracker record in
the preamble, above the first `##` heading, or a category record under the category
description, above its first item. add writes a category record when it creates the
category, describe on every change; migrate-codes writes a tracker record when it codes
an item, upgrade --apply when it changes the file and --author is on the roster;
rename-category writes both. A command that changes nothing writes no record. check
validates them as item log lines, and a log line is never the description.

An open item may carry one `- lock: 2026-08-30T10:11:29Z @kj <note>` line: @kj is likely
working on it until the stamp. The lock is a courtesy signal, never a gate - a write by
another author warns once on stderr and proceeds, exit code and file result unchanged.
Every write command except `upgrade` first removes every lock whose stamp is past,
silently; close and reject remove the item's lock whatever its expiry. Locking is never
logged. report, list, search and refs open with `N item(s) currently worked on: DEF-X by
@xx until <stamp>` on stderr whenever an item they show holds an active lock, ten ids at
most and then `+M more` - the write-time warning is late, the read is when the item is
chosen; --json carries no notice.

An item may carry any number of `- attachment: <path> sha256:<16 hex> edited:<stamp>`
lines - a screenshot, a document - the path relative to the tracker's directory, the
checksum and last-edit stamp the artefact had when attached. check recomputes both and
warns when an artefact changed or is missing; attach on the same path refreshes the
line and logs the checksum it replaced.

Every free-text argument is one line of the file; a real line break inside one is
written as the two characters `\n`, never dropped.

Query - every table is markdown, paste-ready; --json gives the same facts as data:
  report [paths] [FILTERS] [--detail] [--plain] [--summary] [--json]
         ITEMS lists open work only unless --status says otherwise, grouped by
         category and worst level first inside each category; `list --status open`
         is the globally worst-first queue.
         SUMMARY is plain counts in two grids, one per axis: status - `| Category |
         Open | Fixed | Rejected | Total |` (`Done` on criteria, `Worked on` after
         Open when an item is locked) - then the open items by level under `Open by
         severity` (`| Category | CRITICAL | MAJOR | MEDIUM | MINOR | Open |`) or
         `Open by importance` (CRITICAL | HIGH | MEDIUM | LOW), each with a Total
         row. The level grid breaks the Open column down alone, is printed only
         when something is open, and carries UNTRIAGED/UNRATED only when an open
         item lacks a level. Every filter narrows the whole
         report except --status, which narrows ITEMS alone. --plain prints the grids
         and the ITEMS queue without the icons or the categories table; --summary
         stops at the SUMMARY grid, listing no items. --category CODE is the
         category report: under the category's name and description it prints the
         numbered notes, then the category log lines; --json carries notes and log
         on every category.
  list [paths] [FILTERS] [--columns F,F,..] [--sort=F,-F,..] [--json]
         one table per file, the columns and the order chosen by the caller; a `-`
         prefix on a sort field descends (write --sort=-age, the `=` keeps argparse
         from reading it as a flag)
  pivot [paths] --rows FIELD [--cols FIELD] [--values count|ids] [FILTERS] [--json]
         an ad-hoc grid over any two fields - severity by author, regressions per root,
         open items by age band
  coverage [paths] [FILTERS] [--json]
         the test-coverage grid: categories down, test tags across (UNIT,
         INTEGRATION, FUNCTIONAL, E2E, MANUAL, then any other tag; only columns
         that occur, NO-TEST last), open and closed items counted alike, Total row
  search [paths] QUERY [--top N] [FILTERS] [--json]
         the N items most relevant to QUERY, best first, one table over every scanned
         file - BM25 over the full and base id, the code, title, body, evidence,
         mechanism/root-cause and log lines; id, code and title weighted 3x; a typo
         or a stem still hits. Quote a multi-word QUERY. FILTERS narrow the
         candidates first: --grep is the exact filter, search is the ranking
  list-categories [paths] [--json]                 code, name, open, closed, rejected
  refs [paths] --id ID [--json]                    what points at ID, what ID points at,
                                                   and the chain of what blocks it
  check [paths] [--strict]                         conformity gate

FILTERS, the same on report, list, pivot, search and coverage:
  --category CODE  --code C  --severity S  --importance I  --status open|closed|rejected|all
  --author @xx  --tag T (any case)  --regressions  --dates filed|closed|updated
  --since DATE  --until DATE
  --grep PATTERN   case-insensitive regex over title, body, evidence, every
                   mechanism/root-cause record and log lines
  --blocked        items with at least one blocked-by target that is still open
  --related-to ID  items linked to ID in either direction, by any relation line
  --locked         items carrying an active lock (stamp still in the future)
  --locked-by @xx  items whose active lock is held by @xx
  A mention of an id in a log line is prose; only a relation line (related:,
  blocked-by:, overrides:, overridden-by:) is a link. --grep and search find
  mentions, refs, --related-to and --blocked read links.

FIELDS, for --columns, --sort, --rows and --cols:
  id code title body category severity importance status author filed closed updated
  age tags evidence cause hint regr root logs related blockers overrides
  overridden-by lock attachments
  severity, importance and status are ranked, not alphabetical - severity runs
  CRITICAL, MAJOR, MEDIUM, MINOR, importance runs CRITICAL, HIGH, MEDIUM, LOW and
  status runs open, closed, rejected; --sort and a pivot axis both follow that
  order, so ascending is worst first and open first;
  cause is the current mechanism/root-cause record and answers to either name;
  tags, related, blockers, overrides, overridden-by and attachments pivot an item
  into every value it carries;
  filed/closed/updated pivot by month, age by band (<7d, 7-30d, 31-90d, >90d); lock reads
  `@xx until <stamp>` for an active lock and `-` otherwise. report marks a locked
  item `wip @xx until <stamp>` and its SUMMARY grid counts open locked items in a
  `Worked on` column, present when any item in scope is locked; --json carries
  lock as {by, until, note} or null, and cause with cause_kind plus the whole
  record history under causes, and attachments as paths with the checksum and
  edit stamp of each under fingerprints.

Edit (one file):
  add    FILE --category CODE --code C --title T --text D [--name NAME] [--description D]
                    --severity S|--importance I [--repro R|--test T]
                    [--test-tags "UNIT, FUNCTIONAL"] [--mechanism M|--root-cause R]
  edit   FILE --id ID [--title T] [--text D] [--severity S] [--importance I]
                      [--repro R|--test T] [--test-tags TAGS] [--evidence E]
  amend  FILE --id ID [--title T] [--text D]   reword; the log keeps the old wording

--severity is CRITICAL|MAJOR|MEDIUM|MINOR, mandatory on every defect and refused on
a criterion. An untriaged defect is a check error. Foreign vocabularies (P0-P4, S1-S4,
SEV1-4, BLOCKER, URGENT, HIGH, NORMAL, LOW, TRIVIAL ...) are recognised and renamed by
upgrade; anything it cannot map is named and left for a human.
--importance is CRITICAL|HIGH|MEDIUM|LOW, mandatory on every criterion and refused on
a defect. An unrated criterion is a check error. Importance is read only on ACC items
and severity only on DEF items, so a criterion body opening with `Normal, ...` is
prose, never a level.
  mechanism  FILE --id ID --text T --author @xx [--update]   criteria only
  root-cause FILE --id ID --text T --author @xx [--update]   defects only
          a new record above the previous one by default, which is kept; --update
          rewrites the newest record in place. Refused on the other discipline
  author FILE --handle @xx --name "Full Name"      add or update a roster entry
  describe FILE --category CODE (--text D | --text-file F) --author @xx
  describe FILE --category CODE (--append T | --note N (--text T | --remove)) --author @xx
          --text sets the description, the one line under the heading; --text-file
          replaces the prose block from the heading down to the first item, read
          from F or, with -, from stdin, and refuses a `- log:` line. Every non-blank
          prose line after the description is a note, numbered from 1 past blank,
          fenced and log lines: --append adds the last note after the last prose
          line, --note N --text changes note N, --note N --remove removes it. A note
          is one line of prose, never a heading, a checklist item or a `- log:` line.
          Every write keeps the category log
  relate FILE --id ID [--related TEXT] [--blocked-by TEXT] [--overrides TEXT]
              [--overridden-by TEXT] [--author @xx]
          related and blocked-by are written on this item only. An override is
          written on both items - `overrides:` on the one that replaces,
          `overridden-by:` on the one replaced - in the tracker beside FILE when the
          other item lives there; a defect may override a criterion and back, and an
          item may override, or be overridden by, many. A new blocked-by or override
          link that closes a cycle wins: every older link into the item taking the
          new one, from the item it now points at or anything that item leads to, is
          removed and logged where it stood, which needs --author. A base id in TEXT
          is written as the full id it names, the text around it as typed, and the
          code it added is printed
  unrelate FILE --id ID [--related ID] [--blocked-by ID] [--overrides ID]
              [--overridden-by ID] --author @xx [--event E]
          remove a link and log the line it read; an override goes from both items.
          A link the item does not carry is refused and nothing is written
  attach FILE --id ID --path P [--path P]... --author @xx
          one attachment: line per artefact; the same path again refreshes it
  log    FILE --id ID --event E
  close  FILE --id ID --evidence E [--event E]      evidence proves it is done
  reject FILE --id ID --event E                    not reproduced, irrelevant, wontfix;
                                                   a closed item's evidence moves to the log
  reopen FILE --id ID [--event E]                  closed defect -> a numbered regression
  remove FILE --id ID [--force] [--author @xx]     mistakes and duplicates only
  lock   FILE --id ID --author @xx [--hours N | --until STAMP] [--note TEXT]
          write the lock: line, 24 hours by default; the same author again extends
          it, another author's active lock prints one TRANSFER line and is replaced,
          the note reading `taken over from @yy` unless --note says otherwise;
          refused only on a closed or rejected item
  unlock FILE --author @xx (--id ID | --all | --expired)
          remove lock lines: one item, every item, or only the expired ones;
          clearing another author's active lock prints one TRANSFER line and proceeds
  relate and remove take --author to keep a lock held by that handle silent; relate
  also signs with it the log line of a link it removes to break a cycle.
  ack    FILE [--token T --author @xx --reason R]
          a hand edit of a tracker: without --token, print the token for the file as
          it is now; with it, log the reason in pm-hand-edits.md beside FILE. The
          project-management guard hook passes a hand edit of that state of the file
  upgrade FILE [--code "Section=CODE"]... [--author @xx] [--apply]
          --apply always applies every safe rewrite (ids, codes, stamps, severity
          and test-tag canonicalisation, Contents drop) and exits 0; every content
          problem - missing roster or --author, unrated criteria, untriaged
          defects, missing descriptions, hints or evidence, nested items, items
          above the first heading - becomes a HINT line carrying the exact command
          to run. Non-zero only for I/O errors or an unrecognisable file type.
  migrate-codes FILE --map MAPPING --author @xx
          append the code each `BASE-ID CODE` mapping line names to that item's id,
          before any regression ordinal, logging `coded CODE` on every item changed.
          Idempotent: a second run writes nothing. Reports the items that carry no
          code and are not named by the mapping, and the mapping ids that match no
          item, and exits non-zero while either remains; an item already carrying a
          different code is reported for rename-code. One mapping file per tracker;
          references/codes.md
  rename-code FILE --id ID --code NEW --author @xx
          rename the item and its regressions - every item sharing its root and
          code - keeping each ordinal; rewrite every related, blocked-by, overrides
          and overridden-by line in the scanned files that names an old full id,
          and log the rename on each item. A base-id link is left alone - it still
          resolves; references/codes.md
  rename-category FILE --category OLD --to NEW [--name NAME] --author @xx
          rename a category code across FILE and every tracker beside it, the one
          change to an id once assigned. In each tracker of FILE's prefix, every `##`
          heading with code OLD gets NEW (and NAME), and every id with FILE's prefix
          and segment OLD gets NEW, keeping number, code and ordinal. Every mention
          of a renamed id in every tracker is rewritten in its own shape, full or
          base; an id naming no item stays. An id inside a file path outside a
          relation line and every attachment: line stay as written and are listed
          on stderr as file:line.
          Logs the rename on each item, a category record on each heading and a
          tracker record in each tracker written. A rerun after a git merge
          finishes the rename: when no heading of FILE's prefix carries OLD, items
          still do and FILE's NEW heading holds the earlier rename's record, it
          renames those items, refused when an id one would take exists, and
          rewrites each OLD mention of an id now carrying NEW. Refused, with
          nothing written: OLD not a category in FILE; NEW not 2-6 uppercase
          letters, equal to OLD, a category code in a tracker of FILE's prefix, or
          the segment of an id with that prefix anywhere in the store; two renamed
          roots sharing a base id; a handle off the roster of a tracker it writes

Query paths are files or dirs (a dir is scanned for acc-crit*.md and defects*.md);
no path means ./docs when it exists, else . Stdlib only.
"""

import argparse
import datetime
import difflib
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import sys

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
ITEM = re.compile(r"^(\s*)- \[([ xX-])\] (.*)$")
CBOX = re.compile(r"^\s*- \[[^\]]{0,3}\](?:\s|$)")
# An id is `PREFIX-CAT-N[-CODE][-REGR]`. CODE is one or two hyphen-separated
# segments, each starting with a letter; a trailing all-digit segment is the
# regression ordinal, read from the right, so a code can never end in one.
IDTOK = re.compile(
    r"^`(?P<prefix>ACC|DEF)-(?P<cat>[A-Z]{2,6})-(?P<num>\d+)"
    r"(?:-(?P<code>[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)?))?"
    r"(?:-(?P<regr>\d+))?`\s+(?P<body>.*)$"
)
LEGACY = re.compile(r"^`(ACC|DEF)-(\d+)(?:-(\d+))?`\s+(.*)$")  # pre-category id, upgrade only
IDREF = re.compile(
    r"\b(?P<prefix>ACC|DEF)-(?P<cat>[A-Z]{2,6})-(?P<num>\d+)"
    r"(?:-(?P<code>[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)?))?"
    r"(?:-(?P<regr>\d+))?\b"
)
# an id-shaped backticked token whose tail IDTOK refused, so check can name the
# malformed code rather than call the whole id missing
IDBAD = re.compile(r"^`(?P<tok>(?:ACC|DEF)-[A-Z]{2,6}-\d+(?:-[^`]*))`")
# the item code grammar, and the base id a mapping file names
CODE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)?")
BASEID = re.compile(r"(?:ACC|DEF)-[A-Z]{2,6}-\d+")
# what follows an id that sits inside a file path: `DEF-LNCH-3-slug.md`, `DEF-LNCH-3/notes`
PATHTAIL = re.compile(r"[\w-]*(?:[/\\]|\.[A-Za-z])")
CATCODE = re.compile(r"^(.*?)\s*`([A-Z]{2,6})`$")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
# any all-caps token used as a severity, so upgrade can name what it cannot map
SEVWORD = re.compile(r"^([A-Z][A-Z0-9-]{0,11})\s*[;:,]")
LOGLINE = re.compile(r"^(\s+)- log:\s*(\S*)(.*)$")
# a tracker or category log line: the item log form without the indent, the same groups.
# Only a line with an @handle after its first word is one; any other `- log:` bullet is prose
WIDELOG = re.compile(r"^()- log:\s*(\S*)(\s+@\S.*)$")
DATED = re.compile(r"^(\s+)- (\d{4}-\d{2}-\d{2})\b(.*)$")
RELLINE = re.compile(r"^(\s+)- (related|blocked-by|overrides|overridden-by):\s*(.*)$")
# an override is written on both items; each kind names the line the other item carries
MIRROR = {"overrides": "overridden-by", "overridden-by": "overrides"}
HINTLINE = re.compile(r"^(\s+)- (repro|test):\s*(.*)$")
HANDLE = re.compile(r"@[a-z][a-z0-9]{1,3}")
ROSTER = re.compile(r"^\s*- `(@[a-z][a-z0-9]{1,3})`\s+(.*)$")
AUTHORED = re.compile(r"^(@[a-z][a-z0-9]{1,3})\s+(.*)$")
TAGLINE = re.compile(r"^(\s+)- test-tags:\s*(.*)$")
# the proof an item is done, written at closure and retired by a reopen
EVIDLINE = re.compile(r"^(\s+)- evidence:\s*(.*)$")
# `- mechanism: <stamp> @xx <text>` on a criterion, `- root-cause: ...` on a defect -
# how the item is meant to work, or why it breaks. Records stack newest first: the
# topmost is current, the ones under it are what was believed before it.
CAUSELINE = re.compile(r"^(\s+)- (mechanism|root-cause):\s*(\S*)(.*)$")
# `- lock: <stamp> @xx [note]` - who is likely working on the item, until when
LOCKLINE = re.compile(r"^(\s+)- lock:\s*(\S*)(.*)$")
# the path may hold spaces, so it is whatever sits before the two fixed tokens
ATTLINE = re.compile(r"^(\s+)- attachment:\s*(.+?)\s+sha256:([0-9a-f]{16})\s+edited:(\S+)\s*$")
ATTANY = re.compile(r"^(\s+)- attachment:")
REJECTED = re.compile(r"^rejected:?\s*(.*)$", re.I)
CLOSING = re.compile(r"^(closed|rejected)\b", re.I)  # the log line that ended the item
# the log line a rename writes, read back to finish the link rewrite a failed run left
RENAMED = re.compile(r'^renamed code "(%s)" -> "(%s)"$' % (CODE.pattern, CODE.pattern))
SUB = re.compile(r"^\s+- ")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")  # ISO 8601, UTC
DATEONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # legacy, upgrade only
TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+|[a-z0-9]+")  # search: a hyphen run stays whole

# the checkbox is the whole status; nothing else records it
STATE = {" ": "open", "x": "closed", "-": "rejected"}
FLAG = {"open": " ", "closed": "x", "rejected": "-"}
HINT_FOR = {"ACC": "test", "DEF": "repro"}
CAUSE_FOR = {"ACC": "mechanism", "DEF": "root-cause"}
SEVS = ("CRITICAL", "MAJOR", "MEDIUM", "MINOR")
# the vocabularies a tracker is likely to arrive carrying. Recognised so an old file
# parses and gets a precise error instead of "not triaged", and so upgrade can rename
SEV_ALIAS = {
    "BLOCKER": "CRITICAL",
    "URGENT": "CRITICAL",
    "P0": "CRITICAL",
    "S1": "CRITICAL",
    "SEV1": "CRITICAL",
    "HIGH": "MAJOR",
    "IMPORTANT": "MAJOR",
    "P1": "MAJOR",
    "S2": "MAJOR",
    "SEV2": "MAJOR",
    "NORMAL": "MEDIUM",
    "MODERATE": "MEDIUM",
    "P2": "MEDIUM",
    "S3": "MEDIUM",
    "SEV3": "MEDIUM",
    "LOW": "MINOR",
    "TRIVIAL": "MINOR",
    "COSMETIC": "MINOR",
    "P3": "MINOR",
    "P4": "MINOR",
    "S4": "MINOR",
    "SEV4": "MINOR",
}
# A severity is the word followed by the delimiter the format writes
# (`MAJOR; text`). A bare `\b` read `Major refactor ...` as a severity and
# silently re-triaged the item on `edit --text`; the delimiter is the guard.
# Case stays free so a hand-kept `High:` still upgrades and `major;` still
# parses as it did before the delimiter rule.
SEV = re.compile(
    r"^(" + "|".join(sorted(SEVS + tuple(SEV_ALIAS), key=len, reverse=True)) + r")(?=\s*[;:,])",
    re.I,
)
# criterion importance mirrors defect severity: the first word of an ACC body,
# behind the same delimiter guard. Read only on criteria, as severity is read
# only on defects - `Normal, ...` opening a criterion body is prose, not a level
IMPS = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
IMP = re.compile(r"^(" + "|".join(IMPS) + r")(?=\s*[;:,])", re.I)
IMP_RANK = {name: i for i, name in enumerate(IMPS)}


def level_heading(rx, text):
    """The level word heading supplied text as `LEVEL;`; a comma or colon after it is prose."""
    m = rx.match(text)
    return m if m and text[m.end() :].lstrip().startswith(";") else None


# the report exists so a reader sees what is left and in what order to fix it
SEV_RANK = {name: i for i, name in enumerate(SEVS)}
SEV_RANK.update({old: SEV_RANK[new] for old, new in SEV_ALIAS.items()})
STATUS_RANK = {"open": 0, "closed": 1, "rejected": 2}
ICON = {"ACC": "✅", "DEF": "\U0001f41e"}
LABEL = {"ACC": "ACCEPTANCE CRITERIA", "DEF": "DEFECTS"}
# wide emoji read as two cells; one NBSP plus one space is the padding that survives
PAD = "  "

# glyph ranges the format forbids; ASCII - and -> stay legal
FORBIDDEN = [
    (0x2013, 0x2014, "en/em dash"),
    (0x2190, 0x21FF, "arrow glyph"),
    (0x2600, 0x27BF, "symbol/emoji"),
    (0x2B00, 0x2BFF, "symbol/arrow"),
    (0xFE0F, 0xFE0F, "variation selector"),
    (0x1F000, 0x1FAFF, "emoji"),
]

GLOBS = ("acc-crit*.md", "defects*.md")


# --------------------------------------------------------------------------- io


def load(path):
    return open(path, encoding="utf-8").read().splitlines()


def unglyph(text):
    """`text` with each FORBIDDEN glyph written as its U+XXXX escape."""
    return "".join(
        f"U+{ord(ch):04X}" if any(lo <= ord(ch) <= hi for lo, hi, _ in FORBIDDEN) else ch
        for ch in text
    )


def save(path, lines):
    # a log line is append-only: one this write adds or changes gets each FORBIDDEN glyph
    # as U+XXXX, so text a record copies from the file, which oneline never saw, cannot
    # fail check on a line no command can fix
    had = set(load(path)) if os.path.exists(path) else set()
    unfenced = {n for n, _ in non_fenced(lines)}
    lines = [
        unglyph(ln)
        if n in unfenced and ln not in had and (LOGLINE.match(ln) or WIDELOG.match(ln))
        else ln
        for n, ln in enumerate(lines, 1)
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def now():
    """ISO 8601 in UTC - one unambiguous instant, comparable as a plain string."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def oneline(text):
    """argparse type for every free-text argument: an item and each of its sub-lines
    is one line of the file, so a real line break inside the text is written as the
    two characters `\\n` - nothing is lost, and the reader sees where the break was.
    A FORBIDDEN glyph is refused here: log lines copy the text and are append-only, so
    once written, check fails on a line no command can fix."""
    for ch in text:
        for lo, hi, name in FORBIDDEN:
            if lo <= ord(ch) <= hi:
                raise argparse.ArgumentTypeError(
                    f"forbidden glyph {name} U+{ord(ch):04X} {ch!r}; "
                    "use ASCII instead (- for a dash, -> for an arrow)"
                )
    return re.sub("\r\n|[\n\r\x0b\x0c\x1c-\x1e\x85\u2028\u2029]", r"\\n", text)


# a writeup past this many words is explaining itself; --reason must say why it needs the length
WRITEUP_WORDS = 50


def words(text):
    # oneline writes a line break as the two characters \n; count it as a space
    return len(text.replace("\\n", " ").split())


def because(reason):
    """The tail a write's log line carries when the author gave a reason."""
    return f"; reason: {reason}" if reason else ""


def gate_writeups(parser, a):
    """Refuse a free-text argument over WRITEUP_WORDS unless --reason is given; with one
    it is written and warned. The reason is capped too, and a command that writes no
    log line has nowhere to keep a reason, so it takes none."""
    reason = getattr(a, "reason", None)
    for act in parser._actions:
        value = getattr(a, act.dest, None) if act.type is oneline else None
        n = words(value) if value else 0
        if n <= WRITEUP_WORDS:
            continue
        flag = act.option_strings[0]
        if act.dest == "reason" or not hasattr(a, "reason"):
            raise SystemExit(f"{flag} is {n} words; the limit is {WRITEUP_WORDS} - shorten it")
        if not reason:
            raise SystemExit(
                f"{flag} is {n} words; the limit is {WRITEUP_WORDS} - shorten it, "
                "or pass --reason saying why it needs the length"
            )
        print(
            f"warning: {flag} is {n} words, over {WRITEUP_WORDS}; written because --reason was given",
            file=sys.stderr,
        )


def fingerprint(path):
    """(sha256 prefix, last-edit stamp) of an artefact - what an attachment line records
    and what check recomputes to tell whether the artefact changed since it was attached."""
    digest = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()[:16]
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path), datetime.timezone.utc)
    return digest, mtime.strftime("%Y-%m-%dT%H:%M:%SZ")


def att_path(file, rel):
    """An attachment line's path is relative to the tracker's own directory, so the
    file and its artefacts move together."""
    return pathlib.Path(file).resolve().parent / rel


def non_fenced(lines):
    fence = False
    for i, ln in enumerate(lines):
        if re.match(r"^\s*```", ln):
            fence = not fence
            continue
        if not fence:
            yield i + 1, ln


def resolve(paths):
    if not paths:
        base = pathlib.Path("docs") if pathlib.Path("docs").is_dir() else pathlib.Path(".")
        paths = [str(base)]
    out = []
    for p in paths:
        pp = pathlib.Path(p)
        if pp.is_dir():
            for g in GLOBS:
                out += sorted(str(x) for x in pp.glob(g))
        elif pp.is_file():
            out.append(str(pp))
        else:
            print(f"warning: no such path: {p}", file=sys.stderr)
    return sorted(set(out))


def doc_prefix(path, blocks=None):
    """ACC or DEF, from the filename first, then from the ids already in the file."""
    name = pathlib.Path(path).name
    if name.startswith("acc-crit"):
        return "ACC"
    if name.startswith("defects"):
        return "DEF"
    for b in blocks or []:
        if b["prefix"]:
            return b["prefix"]
    raise SystemExit(f"{path}: cannot tell the doc type; name it acc-crit*.md or defects*.md")


# ------------------------------------------------------------------------ parse


def roster_of(path):
    """handle -> name, read off the `## Authors` section. Empty when there is none."""
    out, inside = {}, False
    for _, ln in non_fenced(load(path)):
        h = HEADING.match(ln)
        if h:
            inside = len(h.group(1)) == 2 and h.group(2).strip().lower() == "authors"
            continue
        if inside:
            m = ROSTER.match(ln)
            if m:
                out[m.group(1)] = m.group(2).strip()
    return out


def tracker_log(lines):
    """The tracker log: (line number, line) for each WIDELOG line of the preamble,
    above the first `##` heading, in file order."""
    out = []
    for lineno, ln in non_fenced(lines):
        h = HEADING.match(ln)
        if h and len(h.group(1)) == 2:
            break
        if WIDELOG.match(ln):
            out.append((lineno, ln))
    return out


def parse(path):
    """Return (blocks, sections). A block is one item plus its indented sub-lines. A
    section carries its category log as `log_lines` and its notes, the prose lines
    after the description, as `notes`: (line number, line) pairs."""
    name = pathlib.Path(path).name
    docp = "ACC" if name.startswith("acc-crit") else "DEF" if name.startswith("defects") else None
    blocks, sections, cur, sec = [], [], None, None
    in_authors = in_prose = False  # in_prose: under a `##` heading, above its first item
    for lineno, ln in non_fenced(load(path)):
        if in_authors and not HEADING.match(ln):
            continue
        h = HEADING.match(ln)
        if h:
            in_authors = False
            in_prose = len(h.group(1)) == 2
            if len(h.group(1)) == 2 and h.group(2).strip().lower() == "authors":
                in_authors, sec, cur = True, None, None
                continue
            if len(h.group(1)) == 2:
                m = CATCODE.match(h.group(2))
                sec = dict(
                    line=lineno,
                    name=(m.group(1) if m else h.group(2)).strip(),
                    code=m.group(2) if m else None,
                    raw=h.group(2).strip(),
                    desc=None,
                    log_lines=[],
                    notes=[],
                )
                sections.append(sec)
            cur = None
            continue
        m = ITEM.match(ln)
        if m:
            in_prose = False
            indent, state, text = len(m.group(1)), m.group(2), m.group(3)
            idm = IDTOK.match(text)
            badid = IDBAD.match(text)
            body = idm.group("body") if idm else text
            bold = BOLD.search(body)
            after = body[bold.end() :].lstrip(" -") if bold else body
            eff = (idm.group("prefix") if idm else None) or docp
            sm = SEV.match(after) if eff == "DEF" else None
            im = IMP.match(after) if eff == "ACC" else None
            plain = (SEV if sm else IMP).sub("", after).lstrip(" ;:,-") if sm or im else after
            cur = dict(
                line=lineno,
                indent=indent,
                state=state,
                text=text,
                prefix=idm.group("prefix") if idm else None,
                cat=idm.group("cat") if idm else None,
                num=int(idm.group("num")) if idm else None,
                code=idm.group("code") if idm else None,
                regr=int(idm.group("regr")) if idm and idm.group("regr") else None,
                bad_id=bool(badid and not idm),
                body=body,
                title=bold.group(1) if bold else None,
                severity=sm.group(1).upper() if sm else None,
                importance=im.group(1).upper() if im else None,
                plain=plain,
                subs=[],
                section=sec,
                dates=[],
                logs=[],
                log_authors=[],
                has_log=False,
                refs=[],
                hint=None,
                hint_kind=None,
                hint_n=0,
                tags=None,
                tag_n=0,
                evidence=None,
                evid_n=0,
                cause=None,
                cause_kind=None,
                causes=[],
                cause_bad=False,
                cause_order=True,
                lock=None,
                lock_n=0,
                lock_bad=False,
                attachments=[],
                att_bad=False,
            )
            blocks.append(cur)
            continue
        if cur is not None and SUB.match(ln):
            cur["subs"].append(ln.strip())
            lm = LOGLINE.match(ln)
            if lm:
                cur["has_log"] = True
                rest = lm.group(3).strip()
                am = AUTHORED.match(rest)
                if am:
                    cur["log_authors"].append(am.group(1))
                    rest = am.group(2).strip()
                else:
                    cur["log_authors"].append(None)
                cur["logs"].append(rest)
                # one entry per log line, None when the stamp is malformed, so
                # dates[i] always belongs to logs[i] - the date filters read the pair
                cur["dates"].append(lm.group(2) if _valid_stamp(lm.group(2)) else None)
            rm = RELLINE.match(ln)
            if rm:
                for r in IDREF.finditer(rm.group(3)):
                    cur["refs"].append((rm.group(2), r.group(0), lineno))
            hm = HINTLINE.match(ln)
            if hm:
                cur["hint_n"] += 1
                cur["hint_kind"] = hm.group(2)
                cur["hint"] = hm.group(3).strip()
            tm = TAGLINE.match(ln)
            if tm:
                cur["tag_n"] += 1
                cur["tags"] = tm.group(2).strip()
            em = EVIDLINE.match(ln)
            if em:
                cur["evid_n"] += 1
                cur["evidence"] = em.group(2).strip()
            cm = CAUSELINE.match(ln)
            if cm:
                rest = cm.group(4).strip()
                am = AUTHORED.match(rest)
                rec = {
                    "kind": cm.group(2),
                    "stamp": cm.group(3),
                    "author": am.group(1) if am else None,
                    "text": (am.group(2).strip() if am else rest),
                }
                if not (_valid_stamp(rec["stamp"]) and rec["author"]):
                    cur["cause_bad"] = True
                elif cur["causes"] and rec["stamp"] > cur["causes"][-1]["stamp"]:
                    # written newest first, so a later stamp below an earlier one
                    # means the current record is not the one at the top
                    cur["cause_order"] = False
                cur["causes"].append(rec)
                if cur["cause"] is None:
                    cur["cause"], cur["cause_kind"] = rec["text"], rec["kind"]
            km = LOCKLINE.match(ln)
            if km:
                cur["lock_n"] += 1
                by, _, note = km.group(3).strip().partition(" ")
                if _valid_stamp(km.group(2)) and HANDLE.fullmatch(by):
                    cur["lock"] = {"by": by, "until": km.group(2), "note": note.strip() or None}
                else:
                    cur["lock_bad"] = True
            xm = ATTLINE.match(ln)
            if xm:
                cur["attachments"].append(
                    {
                        "path": xm.group(2),
                        "sha256": xm.group(3),
                        "edited": xm.group(4),
                        "line": lineno,
                    }
                )
            elif ATTANY.match(ln):
                cur["att_bad"] = True
            continue
        if in_prose and WIDELOG.match(ln):
            sec["log_lines"].append((lineno, ln))
            continue
        # the first prose line under a `##` heading, before any item and not a log line,
        # is the description
        if cur is None and sec is not None and sec["desc"] is None and ln.strip():
            sec["desc"] = ln.strip()
        elif in_prose and ln.strip():
            sec["notes"].append((lineno, ln.strip()))
    return blocks, sections


def ident(b):
    if not b["prefix"]:
        return "(no id)"
    root = f"{b['prefix']}-{b['cat']}-{b['num']}"
    if b["code"]:
        root += f"-{b['code']}"
    return f"{root}-{b['regr']}" if b["regr"] else root


def author_of(b):
    """Who filed the item - the handle on its first log line. Nothing else records it."""
    for h in b["log_authors"]:
        if h:
            return h
    return None


def status_of(b):
    return STATE.get(b["state"].lower() if b["state"].strip() else " ", "?")


def reject_reason(b):
    """Why an item was rejected - read back off the newest matching log line."""
    for txt in reversed(b["logs"]):
        m = REJECTED.match(txt.lstrip("- ").strip())
        if m:
            return m.group(1).strip()
    return ""


def sev_of(b):
    """The severity in this vocabulary - an un-upgraded file may still say HIGH."""
    return SEV_ALIAS.get(b["severity"], b["severity"])


def stamped(b, which):
    """When the item was `filed`, `closed` or last `updated` - YYYY-MM-DD, or None.

    The log is the only place a date is recorded. A closed date exists only while the
    item is closed or rejected, so a reopen retires it rather than leaving a stale one.
    """
    if which == "filed":
        return next((d[:10] for d in b["dates"] if d), None)
    if which == "updated":
        return next((d[:10] for d in reversed(b["dates"]) if d), None)
    if status_of(b) not in ("closed", "rejected"):
        return None
    pairs = zip(reversed(b["dates"]), reversed(b["logs"]))
    return next((d[:10] for d, txt in pairs if d and CLOSING.match(txt)), None)


def in_window(b, which, since, until):
    d = stamped(b, which)
    if d is None:
        return False
    return (since is None or d >= since) and (until is None or d <= until)


def lock_active(b):
    """The lock that still holds - stamp in the future - or None. ISO 8601 UTC stamps
    compare as plain strings, so no clock arithmetic is needed."""
    k = b["lock"]
    return k if k and k["until"] > now() else None


def expire_locks(file):
    """Drop every lock line whose stamp is past - the first step of every write but
    `upgrade`, which leaves lock lines untouched.
    Silent and unlogged: an expired lock is a courtesy that ran out, not an event.
    Returns how many were dropped."""
    lines = load(file)
    at = now()
    gone = [
        i - 1
        for i, ln in non_fenced(lines)
        if (m := LOCKLINE.match(ln)) and _valid_stamp(m.group(2)) and m.group(2) <= at
    ]
    for i in reversed(gone):
        del lines[i]
    if gone:
        save(file, lines)
    return len(gone)


def as_handle(author):
    """`kj` or `@kj` to `@kj`; None stays None. No roster check - used only to tell
    whether a lock is the caller's own."""
    return None if not author else author if author.startswith("@") else "@" + author


def warn_lock(file, b, who):
    """One stderr line when an active lock is held by someone other than `who`. The
    write goes ahead regardless: the lock is a signal, never a gate."""
    k = lock_active(b)
    if k and k["by"] != who:
        print(
            f"{file}:{b['line']}: {ident(b)} locked by {k['by']} until {k['until']} - "
            "someone is likely working on it; ask before continuing",
            file=sys.stderr,
        )


def notice_locked(items):
    """One stderr line naming the items a read is about to show that someone else is on.
    The write-time warning is late by design - the work is already done by then; the
    choice of what to pick up happens while reading, so that is where the signal goes.
    Silent when nothing shown is locked, and stderr keeps a piped table clean."""
    held = [(b, k) for b in items if (k := lock_active(b))]
    if not held:
        return
    named = [f"{ident(b)} by {k['by']} until {k['until']}" for b, k in held[:10]]
    more = f", +{len(held) - 10} more" if len(held) > 10 else ""
    print(f"{len(held)} item(s) currently worked on: {', '.join(named)}{more}", file=sys.stderr)


def warn_transfer(b, k, doing):
    """`lock` or `unlock` over another author's active lock: taking their work over is
    allowed, going quiet about it is not. Replaces warn_lock on those two commands."""
    print(
        f"TRANSFER: {ident(b)} was locked by {k['by']} until {k['until']} - "
        f"you are {doing}; ask {k['by']}",
        file=sys.stderr,
    )


def set_lock(lines, b, value):
    """Replace the item's lock: line, or add one above its first log: line - the lock
    sits with the other sub-lines, before the history."""
    ind = sub_indent(lines, b)
    end = block_end(lines, b)
    for i in range(b["line"], end):
        if LOCKLINE.match(lines[i]):
            lines[i] = f"{ind}- lock: {value}"
            return
    at = next((i for i in range(b["line"], end) if LOGLINE.match(lines[i])), end)
    lines.insert(at, f"{ind}- lock: {value}")


def scope_of(
    blocks,
    cat,
    sev,
    which,
    since,
    until,
    author=None,
    tag=None,
    regr=False,
    grep=None,
    blocked=False,
    related_to=None,
    index=None,
    imp=None,
    locked=False,
    locked_by=None,
    code=None,
):
    """The items a query is about - every filter except --status. On `report` that one
    narrows the ITEMS queue alone, so a filtered report still says where the whole
    scope stands; `list` and `pivot` apply it through `select`."""
    out = [b for b in blocks if not b["indent"]]
    if locked:
        out = [b for b in out if lock_active(b)]
    if locked_by:
        out = [b for b in out if (lock_active(b) or {}).get("by") == locked_by]
    if cat:
        out = [b for b in out if b["cat"] == cat]
    if code:
        out = [b for b in out if b["code"] == code]
    if sev:
        out = [b for b in out if sev_of(b) == sev]
    if imp:
        out = [b for b in out if b["importance"] == imp]
    if author:
        out = [b for b in out if author_of(b) == author]
    if tag:
        out = [b for b in out if tag in tag_set(b)]
    if regr:
        out = [b for b in out if b["regr"]]
    if grep:
        rx = re.compile(grep, re.I)
        out = [b for b in out if any(rx.search(t) for t in text_of(b))]
    if blocked:
        out = [b for b in out if is_blocked(b, index)]
    if related_to:
        out = [b for b in out if linked(b, related_to, index)]
    if since or until:
        out = [b for b in out if in_window(b, which, since, until)]
    return out


def select(blocks, fl, index=None):
    """scope_of plus the status filter - the item set `list` and `pivot` work on."""
    out = scope_of(
        blocks,
        fl["category"],
        fl["severity"],
        fl["dates"],
        fl["since"],
        fl["until"],
        fl["author"],
        fl["tag"],
        fl["regr"],
        fl["grep"],
        fl["blocked"],
        fl["related_to"],
        index,
        fl["importance"],
        fl["locked"],
        fl["locked_by"],
        code=fl["code"],
    )
    if fl["status"] and fl["status"] != "all":
        out = [b for b in out if status_of(b) == fl["status"]]
    return out


def filter_note(fl, status=None):
    """The `(open, category AUTH, @kj)` suffix a filtered table carries in its title."""
    bits = [
        status,
        f"category {fl['category']}" if fl["category"] else None,
        f"code {fl['code']}" if fl["code"] else None,
        fl["severity"],
        fl["importance"],
        fl["author"],
        f"tag {fl['tag']}" if fl["tag"] else None,
        "regressions only" if fl["regr"] else None,
        f"grep /{fl['grep']}/" if fl["grep"] else None,
        "blocked" if fl["blocked"] else None,
        f"related to {fl['related_to']}" if fl["related_to"] else None,
        "locked" if fl["locked"] else None,
        f"locked by {fl['locked_by']}" if fl["locked_by"] else None,
        window_note(fl["dates"], fl["since"], fl["until"]),
    ]
    bits = [x for x in bits if x]
    return f" ({', '.join(bits)})" if bits else ""


def window_note(which, since, until):
    if since and until:
        return f"{which} {since} to {until}"
    if since:
        return f"{which} since {since}"
    if until:
        return f"{which} until {until}"
    return None


def banner(icon, title, plain):
    return f"## {title}" if plain else f"## {icon}{PAD}{title}"


def fix_order(b):
    """Open before done, worst before mild, oldest before newest."""
    return (
        STATUS_RANK.get(status_of(b), 3),
        SEV_RANK.get(b["severity"], IMP_RANK.get(b["importance"], len(SEVS))),
        b["num"] if b["num"] is not None else 0,
        b["code"] or "",
        b["regr"] or 0,
    )


def tag_set(b):
    """Tags read case-insensitively off the file, carried upper-case everywhere,
    once each - a hand-edited `unit, UNIT` is one tag, not two."""
    return list(
        dict.fromkeys(t.strip().upper() for t in (b["tags"] or "").split(",") if t.strip())
    )


def canon_tags(spec):
    """The written form of a test-tags value: upper-case, comma-space separated,
    case-duplicates dropped keeping first position."""
    return ", ".join(dict.fromkeys(t.strip().upper() for t in spec.split(",") if t.strip()))


def targets(b, kind):
    """The ids this item's relation lines of one kind name, file order, once each."""
    return list(dict.fromkeys(rid for k, rid, _ in b["refs"] if k == kind))


def text_of(b):
    """What --grep reads: title, body, evidence, every record and every log event."""
    return [
        b["title"] or "",
        b["plain"] or "",
        b["evidence"] or "",
        *[c["text"] for c in b["causes"]],
        *b["logs"],
    ]


def link_index(files):
    """ident -> block over every scanned file, the cross-file view the relation
    filters, refs and check read. Built only when a query needs it."""
    return {ident(b): b for f in files for b in parse(f)[0] if b["prefix"]}


def resolve_ref(index, rid):
    """The full id a reference names. The full id itself wins; otherwise the family
    root whose base id it is, so `DEF-X-1` resolves `DEF-X-1-CODE`. A regression is
    named by its full id; a dangling reference comes back unchanged for check to
    report."""
    if rid in index:
        return rid
    return next((i for i in index if root_of(index[i]) == rid and not index[i]["regr"]), rid)


def coded_ref(index, m):
    """The full id an IDREF match names when it carries no code and is not itself an
    item's id: a base id names its coded root, a base id plus ordinal (`DEF-LNCH-3-1`)
    the coded regression. None for a full id, an uncoded item's own id, an id that
    names no item and an id inside a file path."""
    if m["code"] or m[0] in index:
        return None
    s, at = m.string, m.start()
    if s[at - 1 : at] in ("/", "\\") or PATHTAIL.match(s, m.end()):
        return None
    if not m["regr"]:
        full = resolve_ref(index, m[0])
        return full if full != m[0] else None
    base = f"{m['prefix']}-{m['cat']}-{m['num']}"
    return next(
        (
            i
            for i, b in index.items()
            if root_of(b) == base and b["regr"] == int(m["regr"]) and b["code"]
        ),
        None,
    )


def is_blocked(b, index):
    """At least one blocked-by target that exists in the scanned files and is open.
    A dangling target is a check error, not a block."""
    return any(
        t in index and status_of(index[t]) == "open"
        for t in (resolve_ref(index, r) for r in targets(b, "blocked-by"))
    )


def linked(b, wanted, index):
    """Either direction, either kind; an item is not linked to itself."""
    me = ident(b)
    target = resolve_ref(index, wanted)
    if me == target:
        return False
    if any(resolve_ref(index, r) == target for _, r, _ in b["refs"]):
        return True
    t = index.get(target)
    return t is not None and any(resolve_ref(index, r) == me for _, r, _ in t["refs"])


def graph(index, kind):
    """id -> the ids it points at in one dependency graph, read off the scanned items.
    `blocked-by`: an item points at its blockers. `overrides`: an item points at what
    it overrides, a link either line of the pair states."""
    adj = {
        i: list(dict.fromkeys(resolve_ref(index, r) for r in targets(b, kind)))
        for i, b in index.items()
    }
    if kind == "overrides":
        for i, b in index.items():
            for raw in targets(b, "overridden-by"):
                r = resolve_ref(index, raw)
                if r in adj and i not in adj[r]:
                    adj[r].append(i)
    return adj


def cycles_in(adj):
    """Every cycle one depth-first pass over a dependency graph finds, each as
    [m, ..., m] starting at its smallest id. A self-link is the one-step case.
    Status is ignored: a loop through a closed item is still a structural error.
    One pass, iterative: a tracker where every task is blocked by the last few, or
    a chain hundreds deep, costs one visit per item and per link."""
    state, cycles = {}, []  # missing: unvisited, 1: on the path, 2: done
    for start in adj:
        if start in state:
            continue
        state[start] = 1
        path, pending = [start], [iter(adj[start])]
        while path:
            rid = next(pending[-1], None)
            if rid is None:
                state[path.pop()] = 2
                pending.pop()
            elif state.get(rid) == 1:
                loop = path[path.index(rid) :]
                i = loop.index(min(loop))
                cycles.append(loop[i:] + loop[:i] + [loop[i]])
            elif rid in adj and rid not in state:
                state[rid] = 1
                path.append(rid)
                pending.append(iter(adj[rid]))
    return cycles


def tally(items):
    return {name: sum(1 for b in items if status_of(b) == name) for name in FLAG}


def next_regr(blocks, b):
    """The next free regression ordinal in this item's family.

    Flat, not nested: a regression of a regression is the next ordinal on the same
    root, so the count of regressions an item has suffered is the highest ordinal.
    """
    used = [
        x["regr"]
        for x in blocks
        if x["regr"]
        and x["prefix"] == b["prefix"]
        and x["cat"] == b["cat"]
        and x["num"] == b["num"]
    ]
    return (max(used) + 1) if used else 1


def next_num(blocks):
    nums = [b["num"] for b in blocks if b["num"] is not None]
    return (max(nums) + 1) if nums else 1


def find_id(blocks, wanted):
    """The item a full id names, else the item a base id names. Full first, so an
    uncoded `DEF-X-1` wins over a coded `DEF-X-1-CODE` when both exist."""
    hits = [b for b in blocks if ident(b) == wanted]
    if not hits:
        hits = [b for b in blocks if root_of(b) == wanted and not b["regr"]]
    if not hits:
        raise SystemExit(f"no item with id {wanted}")
    return hits[0]


def norm_id(raw, prefix):
    raw = raw.strip().upper()
    if IDREF.fullmatch(raw):
        return raw
    raise SystemExit(f"malformed id {raw!r}; expected {prefix}-<CAT>-<N>[-<CODE>][-<R>]")


def norm_code(raw):
    """An item code as the id grammar carries it. A trailing all-digit segment is the
    regression ordinal, so a code ending in one is refused rather than read as a code."""
    code = raw.strip().upper()
    if not CODE.fullmatch(code):
        raise SystemExit(
            f"code {raw!r} must be one or two hyphen-separated segments of "
            "A-Z0-9, each starting with a letter"
        )
    return code


def block_end(lines, b):
    """0-based index just past the block's contiguous indented sub-lines."""
    i, n = b["line"], len(lines)
    while i < n and lines[i].strip() and lines[i][:1] in (" ", "\t"):
        i += 1
    return i


def sub_indent(lines, b):
    idx = b["line"]
    if idx < len(lines) and lines[idx].strip() and lines[idx][:1] in (" ", "\t"):
        s = lines[idx]
        return s[: len(s) - len(s.lstrip())]
    return "  "


# ------------------------------------------------------------------------ query


def cell(text, width=64):
    """One table cell: pipes escaped, one line, truncated. Empty reads as a dash."""
    s = re.sub(r"\s+", " ", (text or "")).replace("|", r"\|").strip()
    if not s:
        return "-"
    if len(s) <= width:
        return s
    cut = s[: width - 3]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > width // 2 else cut).rstrip() + "..."


FIELDS = (
    "id",
    "code",
    "title",
    "body",
    "category",
    "severity",
    "importance",
    "status",
    "author",
    "filed",
    "closed",
    "updated",
    "age",
    "tags",
    "evidence",
    "cause",
    "hint",
    "regr",
    "root",
    "logs",
    "related",
    "blockers",
    "overrides",
    "overridden-by",
    "lock",
    "attachments",
)
# the fields that hold ids of other items, one per relation kind
LINK_FIELDS = ("related", "blockers", "overrides", "overridden-by")
HEAD = {
    "id": "Id",
    "code": "Code",
    "title": "Title",
    "body": "Description",
    "category": "Category",
    "severity": "Severity",
    "importance": "Importance",
    "status": "Status",
    "author": "Author",
    "filed": "Filed",
    "closed": "Closed",
    "updated": "Updated",
    "age": "Age",
    "tags": "Tests",
    "evidence": "Evidence",
    "cause": "Cause",
    "hint": "Hint",
    "regr": "Regr",
    "root": "Root",
    "logs": "Logs",
    "related": "Related",
    "blockers": "Blockers",
    "overrides": "Overrides",
    "overridden-by": "Overridden by",
    "lock": "Lock",
    "attachments": "Attachments",
}
WIDTH = {
    "title": 40,
    "body": 88,
    "evidence": 56,
    "cause": 64,
    "tags": 24,
    "hint": 64,
    "related": 48,
    "blockers": 48,
    "overrides": 48,
    "overridden-by": 48,
    "attachments": 56,
}
NUMERIC = ("age", "regr", "logs")
DEFAULT_COLS = {
    "DEF": ("id", "title", "severity", "status", "category", "author", "filed", "tags"),
    "ACC": ("id", "title", "importance", "status", "category", "author", "filed", "tags"),
}
AGE_BANDS = ("<7d", "7-30d", "31-90d", ">90d")
# the canonical coverage columns, in reading order; other tags follow, NO-TEST last
TAG_ORDER = ("UNIT", "INTEGRATION", "FUNCTIONAL", "E2E", "MANUAL")
NO_TEST = "NO-TEST"
# the pivot bucket an item lands in when the field is empty
NONE_KEY = {
    "code": "uncoded",
    "tags": NO_TEST,
    "severity": "untriaged",
    "importance": "unrated",
    "related": "unlinked",
    "blockers": "unblocked",
    "overrides": "overrides none",
    "overridden-by": "not overridden",
    "attachments": "unattached",
}


def root_of(b):
    return f"{b['prefix']}-{b['cat']}-{b['num']}" if b["prefix"] else None


def age_of(b, today=None):
    """Days from filing to closure, or to today while the item is still open.
    A closed item with no closing stamp has no age: counting it to today would
    band a hand-ticked fix as `>90d` open."""
    filed = stamped(b, "filed")
    if not filed:
        return None
    end = stamped(b, "closed")
    if not end and status_of(b) != "open":
        return None
    end = end or today or datetime.date.today().isoformat()
    return (datetime.date.fromisoformat(end) - datetime.date.fromisoformat(filed)).days


def age_band(days):
    if days is None:
        return "-"
    return AGE_BANDS[0 if days < 7 else 1 if days <= 30 else 2 if days <= 90 else 3]


def record(b, today=None, index=None):
    """One item as data - what every table, pivot cell and --json document is built from.
    `category` is the live section the item sits under, not the segment in its id. With
    `index`, every link is the full id it names, once: a target spelled as a base id and
    as its full id is one link, not two."""
    sec = b["section"]
    out = {
        "id": ident(b),
        "code": b["code"],
        "title": b["title"],
        "body": b["plain"],
        "category": (sec["code"] if sec else None) or b["cat"],
        "severity": sev_of(b),
        "importance": b["importance"],
        "status": status_of(b),
        "author": author_of(b),
        "filed": stamped(b, "filed"),
        "closed": stamped(b, "closed"),
        "updated": stamped(b, "updated"),
        "age": age_of(b, today),
        "tags": tag_set(b),
        "evidence": b["evidence"],
        "cause": b["cause"],
        "cause_kind": b["cause_kind"],
        "causes": b["causes"],
        "hint": b["hint"],
        "regr": b["regr"] or 0,
        "root": root_of(b),
        "related": targets(b, "related"),
        "blockers": targets(b, "blocked-by"),
        "overrides": targets(b, "overrides"),
        "overridden-by": targets(b, "overridden-by"),
        "logs": len(b["logs"]),
        "lock": lock_active(b),
        "attachments": [a["path"] for a in b["attachments"]],
        "fingerprints": [
            {k: a[k] for k in ("path", "sha256", "edited")} for a in b["attachments"]
        ],
        "line": b["line"],
    }
    if index is not None:
        for field in LINK_FIELDS:
            out[field] = list(dict.fromkeys(resolve_ref(index, rid) for rid in out[field]))
    return out


def lock_text(k):
    """`@kj until 2026-08-30T10:11:29Z`, or `-` when no lock holds."""
    return f"{k['by']} until {k['until']}" if k else "-"


def field_cell(rec, field):
    v = rec.get(field)
    if field == "lock":
        return lock_text(v)
    if field in ("id", "root") and v:
        return f"`{v}`"
    if field in LINK_FIELDS:
        return cell(", ".join(f"`{i}`" for i in v), WIDTH[field]) if v else "-"
    if isinstance(v, list):
        return cell(", ".join(v), WIDTH.get(field, 64))
    if v is None:
        return "-"
    return cell(str(v), WIDTH.get(field, 64))


def md_table(headers, rows, numeric=()):
    """Markdown table lines; the named columns right-aligned."""
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join("--:" if h in numeric else "---" for h in headers) + "|")
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out


# both discipline names reach the one field, so a caller writes what the document
# calls it rather than the internal name
FIELD_ALIAS = {"mechanism": "cause", "root-cause": "cause"}


def parse_fields(spec, what):
    out = []
    for raw in (spec or "").split(","):
        f = raw.strip().lower()
        if not f:
            continue
        desc = f.startswith("-")
        f = ("-" if desc else "") + FIELD_ALIAS.get(f.lstrip("-"), f.lstrip("-"))
        if f.lstrip("-") not in FIELDS:
            raise SystemExit(f"{what}: unknown field {f!r}; one of {', '.join(FIELDS)}")
        out.append(f)
    return out


def sort_key(b, rec, field):
    """Rank-aware: severity worst first, status open first, empty values last."""
    if field == "severity":
        return (0, SEV_RANK.get(b["severity"], len(SEVS)))
    if field == "importance":
        return (0, IMP_RANK.get(b["importance"], len(IMPS)))
    if field == "status":
        return (0, STATUS_RANK.get(rec["status"], 3))
    if field == "id":
        return (0, (b["cat"] or "", b["num"] or 0, b["code"] or "", b["regr"] or 0))
    v = rec.get(field)
    if field == "lock":
        return (0, v["until"]) if v else (1, "")
    if v is None or v == []:
        return (1, "")
    return (0, ", ".join(v) if isinstance(v, list) else v)


def sorted_items(pairs, sort):
    """pairs are (block, record). No sort means the fix order; `-field` descends."""
    if not sort:
        return sorted(pairs, key=lambda p: fix_order(p[0]))
    out = list(pairs)
    for f in reversed(sort):  # stable sorts applied minor-to-major
        key = f.lstrip("-")
        out.sort(key=lambda p, k=key: sort_key(p[0], p[1], k), reverse=f.startswith("-"))
    return out


def bucket(rec, field):
    """The pivot keys an item falls in for one field - a list, since tags are many."""
    if field in ("tags", *LINK_FIELDS, "attachments"):
        return rec[field] or [NONE_KEY[field]]
    if field in ("filed", "closed", "updated"):
        return [rec[field][:7] if rec[field] else "-"]
    if field == "age":
        return [age_band(rec["age"])]
    if field == "regr":
        return ["regression" if rec["regr"] else "original"]
    if field == "lock":
        return [lock_text(rec["lock"])]
    v = rec.get(field)
    return [str(v) if v not in (None, "", []) else NONE_KEY.get(field, "-")]


def key_order(field, keys):
    """Severity worst first, status open first, age youngest first, the rest by name
    with the empty bucket last."""
    if field == "severity":
        return sorted(keys, key=lambda k: (SEV_RANK.get(k, len(SEVS)), k))
    if field == "importance":
        return sorted(keys, key=lambda k: (IMP_RANK.get(k, len(IMPS)), k))
    if field == "status":
        return sorted(keys, key=lambda k: STATUS_RANK.get(k, 3))
    if field == "age":
        return sorted(keys, key=lambda k: AGE_BANDS.index(k) if k in AGE_BANDS else 9)
    if field == "regr":
        return [k for k in ("original", "regression") if k in keys]
    empties = ("-", *NONE_KEY.values())
    return sorted(keys, key=lambda k: (k in empties, k))


def summary_grid(scope, shown, prefix):
    """The one aggregate, plain counts, rendered as two grids: status - open,
    closed, rejected and the category size - then the open items split by level
    (severity on a defects document, importance on a criteria document), a
    breakdown of the Open column alone. UNTRIAGED/UNRATED appears only when an
    open item lacks a level. --status never narrows this."""
    cols = list(SEVS if prefix == "DEF" else IMPS)
    none_col = "UNTRIAGED" if prefix == "DEF" else "UNRATED"

    def level_of(b):
        return sev_of(b) if prefix == "DEF" else b["importance"]

    if any(status_of(b) == "open" and level_of(b) not in cols for b in scope):
        cols.append(none_col)
    groups = [(sec, [b for b in scope if b["section"] is sec]) for sec in shown]
    loose = [b for b in scope if b["section"] is None]
    if loose:
        groups.append((None, loose))
    rows = []
    for sec, own in groups:
        cnt = {c: 0 for c in cols}
        op = cl = rj = wip = 0
        for b in own:
            st = status_of(b)
            if st == "open":
                op += 1
                lv = level_of(b)
                cnt[lv if lv in cnt else none_col] += 1
                wip += 1 if lock_active(b) else 0
            elif st == "closed":
                cl += 1
            else:
                rj += 1
        rows.append(dict(section=sec, cells=cnt, open=op, closed=cl, rejected=rj, worked=wip))
    total = dict(
        cells={c: sum(r["cells"][c] for r in rows) for c in cols},
        open=sum(r["open"] for r in rows),
        closed=sum(r["closed"] for r in rows),
        rejected=sum(r["rejected"] for r in rows),
        worked=sum(r["worked"] for r in rows),
    )
    # like UNTRIAGED: a column of zeros carries nothing, so it appears only when it counts
    return dict(prefix=prefix, cols=cols, rows=rows, total=total, worked=total["worked"] > 0)


def grid_json(grid):
    done = "fixed" if grid["prefix"] == "DEF" else "done"

    def row(r):
        sec = r["section"]
        return {
            "category": sec["code"] if sec else None,
            "name": sec["name"] if sec else None,
            "open": r["open"],
            "levels": dict(r["cells"]),
            "worked_on": r["worked"],
            done: r["closed"],
            "rejected": r["rejected"],
        }

    t = grid["total"]
    return {
        "columns": grid["cols"],
        "rows": [row(r) for r in grid["rows"]],
        "total": {
            "open": t["open"],
            "levels": dict(t["cells"]),
            "worked_on": t["worked"],
            done: t["closed"],
            "rejected": t["rejected"],
        },
    }


def cmd_report(files, fl, detail, plain, summary, as_json):
    cat, sev, status = fl["category"], fl["severity"], fl["status"]
    dates, since, until = fl["dates"], fl["since"], fl["until"]
    plain = plain or summary  # a summary is the compact form; the blurbs are not part of it
    # a closed-date window can only select closed and rejected items, so the default
    # open queue would list nothing; list what the window actually found
    if dates == "closed" and (since or until) and status is None:
        status = "all"
    want = None if status == "all" else FLAG[status or "open"]
    docs = []
    index = link_index(files) if fl["blocked"] or fl["related_to"] or as_json else None
    for f in files:
        blocks, sections = parse(f)
        prefix = doc_prefix(f, blocks)
        if sev and prefix != "DEF":
            print(f"{f}: skipped, --severity is a defect attribute", file=sys.stderr)
            continue
        if fl["importance"] and prefix != "ACC":
            print(f"{f}: skipped, --importance is a criterion attribute", file=sys.stderr)
            continue
        scope = scope_of(
            blocks,
            cat,
            sev,
            dates,
            since,
            until,
            fl["author"],
            fl["tag"],
            fl["regr"],
            fl["grep"],
            fl["blocked"],
            fl["related_to"],
            index,
            fl["importance"],
            fl["locked"],
            fl["locked_by"],
            code=fl["code"],
        )
        shown = [s for s in sections if not cat or s["code"] == cat]
        if (
            sev
            or fl["importance"]
            or fl["code"]
            or since
            or until
            or fl["author"]
            or fl["tag"]
            or fl["regr"]
            or fl["grep"]
            or fl["blocked"]
            or fl["related_to"]
            or fl["locked"]
            or fl["locked_by"]
        ):
            # a category the filter emptied is not part of the answer
            shown = [s for s in shown if any(b["section"] is s for b in scope)]
        t = tally(scope)
        note = filter_note(fl, status)
        regs = [b for b in scope if b["regr"]]
        regn, regd = len(regs), len({(b["cat"], b["num"]) for b in regs})
        solo = shown[0] if len(shown) == 1 else None
        grid = summary_grid(scope, shown, prefix)
        groups = [(sec, [b for b in scope if b["section"] is sec]) for sec in shown]
        loose = [b for b in scope if b["section"] is None]
        if loose:
            groups.append((None, loose))
        listed = [b for b in scope if want is None or b["state"].lower() == want]
        rej = [b for b in scope if status_of(b) == "rejected"]

        if as_json:
            items = []
            for _, own in groups:
                items += [
                    record(b, index=index) for b in sorted(own, key=fix_order) if b in listed
                ]
            docs.append(
                {
                    "file": f,
                    "type": prefix,
                    "filters": dict(fl, status=status or "open"),
                    "counts": t,
                    "regressions": {"count": regn, "defects": regd},
                    "categories": [
                        dict(
                            code=sec["code"],
                            name=sec["name"],
                            description=sec["desc"],
                            notes=[t for _, t in sec["notes"]],
                            log=[ln for _, ln in sec["log_lines"]],
                            **tally([b for b in scope if b["section"] is sec]),
                        )
                        for sec in shown
                    ],
                    "summary": grid_json(grid),
                    "items": items,
                    "rejected": [
                        {"id": ident(b), "title": b["title"], "reason": reject_reason(b)}
                        for b in rej
                    ],
                }
            )
            continue

        title = LABEL[prefix] if plain else f"{ICON[prefix]}{PAD}{LABEL[prefix]}"
        print(f"\n# {title} - {f}{note}\n")
        print(
            f"{t['open']} open / {t['closed']} closed / {t['rejected']} rejected "
            f"across {len(shown)} categor" + ("y\n" if len(shown) == 1 else "ies\n")
        )
        if regs:
            print(
                f"{regn} regression{'' if regn == 1 else 's'} "
                f"across {regd} defect{'' if regd == 1 else 's'}\n"
            )
        if solo:
            print(
                f"**{solo['name']}** `{solo['code'] or '?'}`"
                + (f" - {solo['desc']}" if solo["desc"] else "")
                + "\n"
            )
        if solo and cat:  # the category report: its notes, then its category log
            for part in (
                [f"{k}. {t}" for k, (_, t) in enumerate(solo["notes"], 1)],
                [ln for _, ln in solo["log_lines"]],
            ):
                if part:
                    print("\n".join(part) + "\n")

        if scope:
            cols = grid["cols"]
            done_h = "Fixed" if prefix == "DEF" else "Done"
            level_h = "severity" if prefix == "DEF" else "importance"
            print(banner("\U0001f4ca", "SUMMARY", plain) + "\n")
            wip_h = ["Worked on"] if grid["worked"] else []

            def table(head, cells):
                print("| " + " | ".join(head) + " |")
                print("|---|" + "--:|" * (len(head) - 1))
                for r in grid["rows"]:
                    sec = r["section"]
                    label = f"{sec['name']} `{sec['code'] or '?'}`" if sec else "(no category)"
                    print("| " + " | ".join([label] + [str(x) for x in cells(r)]) + " |")
                print(
                    "| "
                    + " | ".join(["**Total**"] + [str(x) for x in cells(grid["total"])])
                    + " |"
                )

            def by_status(r):
                wip = [r["worked"]] if grid["worked"] else []
                size = r["open"] + r["closed"] + r["rejected"]
                return [r["open"], *wip, r["closed"], r["rejected"], size]

            # Two axes, two grids (DEF-PMGT-51): status answers how much is left,
            # the level split answers how bad. On one row the level cells read
            # as peers of Done and Rejected when they only break Open down.
            table(["Category", "Open"] + wip_h + [done_h, "Rejected", "Total"], by_status)
            if grid["total"]["open"]:
                print(f"\n**Open by {level_h}**\n")
                table(
                    ["Category"] + cols + ["Open"],
                    lambda r: [*(r["cells"][c] for c in cols), r["open"]],
                )

        if summary:
            continue

        if not solo and not plain:
            print(f"\n## \U0001f4c1{PAD}CATEGORIES\n")
            print("| Code | Category | Description |")
            print("|------|----------|-------------|")
            for sec in shown:
                print(
                    f"| `{sec['code'] or '?'}` | {cell(sec['name'], 32)} "
                    f"| {cell(sec['desc'], 72)} |"
                )

        show_evid = any(b["evidence"] for b in listed)
        show_lock = any(lock_active(b) for b in listed)
        notice_locked(listed)
        print("\n" + banner("\U0001f4cc", "ITEMS", plain))
        for sec, own in groups:
            rows = [b for b in own if want is None or b["state"].lower() == want]
            if not rows:
                continue
            rows.sort(key=fix_order)
            if not solo:
                print(
                    f"\n### {sec['name']} `{sec['code'] or '?'}`\n"
                    if sec
                    else "\n### (no category)\n"
                )
            if detail:
                h = "###" if solo else "####"  # one level under whatever heading precedes
                for b in rows:
                    lvl = b["severity"] if prefix == "DEF" else b["importance"]
                    head = f"{lvl}, {status_of(b)}" if lvl else status_of(b)
                    print(f"\n{h} `{ident(b)}` **{b['title'] or '?'}** - {head}\n")
                    if b["plain"]:
                        print(f"{b['plain']}\n")
                    for line in b["subs"]:
                        print(line)
                continue
            lvl_h, lvl_r = (
                ("Severity | ", "----------|")
                if prefix == "DEF"
                else ("Importance | ", "------------|")
            )
            ev_h, ev_r = (" Evidence |", "----------|") if show_evid else ("", "")
            lk_h, lk_r = (" Lock |", "------|") if show_lock else ("", "")
            # a column where every row reads the same carries nothing; the header
            # and the footer already say which status is being listed
            st_h, st_r = ("Status | ", "--------|") if want is None else ("", "")
            if solo:
                print()
            print(f"| Id | Title | Description | {lvl_h}{st_h}Tests |{ev_h}{lk_h}")
            print(f"|----|-------|-------------|{lvl_r}{st_r}-------|{ev_r}{lk_r}")
            for b in rows:
                lvl = (b["severity"] if prefix == "DEF" else b["importance"]) or "-"
                st = f"{status_of(b)} | " if want is None else ""
                evid = f" {cell(b['evidence'], 56)} |" if show_evid else ""
                k = lock_active(b)
                wip = (f" wip {lock_text(k)} |" if k else " - |") if show_lock else ""
                print(
                    f"| `{ident(b)}` | {cell(b['title'] or '?', 40)} "
                    f"| {cell(b['plain'], 88)} | {lvl} | {st}{cell(', '.join(tag_set(b)), 24)} |"
                    f"{evid}{wip}"
                )

        hidden = [b for b in scope if want is not None and b["state"].lower() != want]
        if hidden:
            h = tally(hidden)
            bits = [f"{h[k]} {k}" for k in ("open", "closed", "rejected") if h[k]]
            tail = "" if plain else " - pass `--status all`, or `--status closed` / `rejected`"
            print(f"\n{', '.join(bits)} not listed{tail}")

        if rej and want in (None, "-") and not detail:
            print("\n" + banner("\U0001f6ab", "REJECTED", plain) + "\n")
            print("| Id | Title | Reason |")
            print("|----|-------|--------|")
            for b in rej:
                print(
                    f"| `{ident(b)}` | {cell(b['title'] or '?', 40)} "
                    f"| {cell(reject_reason(b), 72)} |"
                )
    if as_json:
        print(json.dumps(docs, indent=2))
    return 0


def cmd_list_categories(files, as_json=False):
    total, docs = 0, []
    for f in files:
        blocks, sections = parse(f)
        if as_json:
            docs.append(
                {
                    "file": f,
                    "categories": [
                        dict(
                            code=s["code"],
                            name=s["name"],
                            description=s["desc"],
                            **tally([b for b in blocks if b["section"] is s and not b["indent"]]),
                        )
                        for s in sections
                    ],
                }
            )
            continue
        print(f"\n{f}")
        if not sections:
            print("  (no ## category headings)")
            continue
        width = max(len(s["code"] or "?") for s in sections)
        for s in sections:
            own = [b for b in blocks if b["section"] is s and b["indent"] == 0]
            c = tally(own)
            print(
                f"  {(s['code'] or '?'):<{width}}  {s['name']:<28} "
                f"{c['open']} open / {c['closed']} closed / {c['rejected']} rejected"
            )
            total += len(own)
    if as_json:
        print(json.dumps(docs, indent=2))
    else:
        print(f"\n{total} item(s)")
    return 0


def cmd_list(files, fl, columns, sort, as_json):
    """One markdown table per file; the caller picks the columns and the order."""
    docs = []
    index = link_index(files)
    for f in files:
        blocks, _ = parse(f)
        prefix = doc_prefix(f, blocks)
        if fl["severity"] and prefix != "DEF":
            print(f"{f}: skipped, --severity is a defect attribute", file=sys.stderr)
            continue
        if fl["importance"] and prefix != "ACC":
            print(f"{f}: skipped, --importance is a criterion attribute", file=sys.stderr)
            continue
        cols = columns or list(DEFAULT_COLS[prefix])
        pairs = sorted_items(
            [(b, record(b, index=index)) for b in select(blocks, fl, index)], sort
        )
        if as_json:
            docs += [dict(rec, file=f) for _, rec in pairs]
            continue
        notice_locked([b for b, _ in pairs])
        heads = [
            (
                HINT_FOR[prefix].title()
                if c == "hint"
                # one stored field, named per discipline: Mechanism / Root cause
                else CAUSE_FOR[prefix].replace("-", " ").capitalize()
                if c == "cause"
                else HEAD[c]
            )
            for c in cols
        ]
        rows = [[field_cell(rec, c) for c in cols] for _, rec in pairs]
        print(f"\n# {LABEL[prefix]} - {f}{filter_note(fl, fl['status'])}\n")
        print("\n".join(md_table(heads, rows, [HEAD[c] for c in NUMERIC])))
        print(f"\n{len(pairs)} item(s)")
    if as_json:
        print(json.dumps(docs, indent=2))
    return 0


def cmd_pivot(files, rows_f, cols_f, values, fl, as_json):
    """An ad-hoc grid: one field down, another across, a count or the ids in every cell.
    A multi-valued field (tags) puts an item in every bucket it belongs to."""
    docs = []
    index = link_index(files)
    for f in files:
        blocks, sections = parse(f)
        prefix = doc_prefix(f, blocks)
        if fl["severity"] and prefix != "DEF":
            print(f"{f}: skipped, --severity is a defect attribute", file=sys.stderr)
            continue
        if fl["importance"] and prefix != "ACC":
            print(f"{f}: skipped, --importance is a criterion attribute", file=sys.stderr)
            continue
        names = {s["code"]: s["name"] for s in sections if s["code"]}
        scope = select(blocks, fl, index)
        grid = {}
        for b in scope:
            rec = record(b, index=index)
            for r in bucket(rec, rows_f):
                for c in bucket(rec, cols_f) if cols_f else ("Items",):
                    grid.setdefault(r, {}).setdefault(c, []).append(rec["id"])
        rkeys = key_order(rows_f, grid)
        ckeys = key_order(cols_f, {c for d in grid.values() for c in d}) if cols_f else ["Items"]
        table = [
            {
                "row": r,
                "cells": {c: grid[r].get(c, []) for c in ckeys},
                "total": sum(len(grid[r].get(c, [])) for c in ckeys),
            }
            for r in rkeys
        ]
        if as_json:
            docs.append(
                {
                    "file": f,
                    "rows": rows_f,
                    "cols": cols_f,
                    "values": values,
                    "columns": ckeys,
                    "table": [
                        dict(
                            t,
                            cells={
                                c: (len(v) if values == "count" else v)
                                for c, v in t["cells"].items()
                            },
                        )
                        for t in table
                    ],
                    "items": len(scope),
                }
            )
            continue

        def show(ids):
            if not ids:
                return "-"
            return str(len(ids)) if values == "count" else ", ".join(f"`{i}`" for i in ids)

        def label(k):
            if rows_f == "category" and k in names:
                return f"{names[k]} `{k}`"
            linkish = rows_f in ("id", "root", *LINK_FIELDS)
            return f"`{k}`" if linkish and k not in ("-", NONE_KEY.get(rows_f)) else k

        head = [HEAD[rows_f]] + ckeys + (["Total"] if cols_f else [])
        lines = [
            [label(t["row"])]
            + [show(t["cells"][c]) for c in ckeys]
            + ([str(t["total"])] if cols_f else [])
            for t in table
        ]
        if len(table) > 1:
            tot = {c: sum(len(t["cells"][c]) for t in table) for c in ckeys}
            lines.append(
                ["**Total**"]
                + [str(tot[c]) for c in ckeys]
                + ([f"**{sum(tot.values())}**"] if cols_f else [])
            )
        note = filter_note(fl, fl["status"])
        print(f"\n# {LABEL[prefix]} - {f} - {rows_f}" + (f" by {cols_f}" if cols_f else "") + note)
        print()
        print("\n".join(md_table(head, lines, ckeys + ["Total", "Items"])))
        print(f"\n{len(scope)} item(s)")
    if as_json:
        print(json.dumps(docs, indent=2))
    return 0


def cmd_coverage(files, fl, as_json):
    """The test-coverage grid: categories down, test tags across, counting the open
    and closed items alike - coverage is a property of the whole tracked surface,
    not of the queue. Rejected items are excluded unless --status asks for them.
    An item with several tags counts in several columns; NO-TEST is the bucket for
    items carrying no test-tags: line, always the last column."""
    docs = []
    index = link_index(files) if fl["blocked"] or fl["related_to"] else None
    for f in files:
        blocks, sections = parse(f)
        prefix = doc_prefix(f, blocks)
        if fl["severity"] and prefix != "DEF":
            print(f"{f}: skipped, --severity is a defect attribute", file=sys.stderr)
            continue
        if fl["importance"] and prefix != "ACC":
            print(f"{f}: skipped, --importance is a criterion attribute", file=sys.stderr)
            continue
        scope = select(blocks, fl, index)
        if fl["status"] is None:
            scope = [b for b in scope if status_of(b) != "rejected"]

        def keys(b):
            return tag_set(b) or [NO_TEST]

        seen = {k for b in scope for k in keys(b)}
        cols = [t for t in TAG_ORDER if t in seen]
        cols += sorted(t for t in seen if t not in TAG_ORDER and t != NO_TEST)
        cols += [NO_TEST] if NO_TEST in seen else []
        groups = [(sec, [b for b in scope if b["section"] is sec]) for sec in sections]
        loose = [b for b in scope if b["section"] is None]
        if loose:
            groups.append((None, loose))
        rows = []
        for sec, own in groups:
            if not own:
                continue
            cnt = {c: 0 for c in cols}
            for b in own:
                for k in keys(b):
                    cnt[k] += 1
            rows.append(dict(section=sec, cells=cnt, items=len(own)))
        total = dict(
            cells={c: sum(r["cells"][c] for r in rows) for c in cols},
            items=len(scope),
        )
        if as_json:

            def row_json(sec, cells, items):
                return {
                    "category": sec["code"] if sec else None,
                    "name": sec["name"] if sec else None,
                    "cells": cells,
                    "items": items,
                }

            docs.append(
                {
                    "file": f,
                    "type": prefix,
                    "columns": cols,
                    "rows": [row_json(r["section"], r["cells"], r["items"]) for r in rows],
                    "total": {"cells": total["cells"], "items": total["items"]},
                }
            )
            continue
        print(f"\n# TEST COVERAGE - {f}{filter_note(fl, fl['status'])}\n")
        head = ["Category"] + cols
        lines = []
        for r in rows:
            sec = r["section"]
            label = f"{sec['name']} `{sec['code'] or '?'}`" if sec else "(no category)"
            lines.append([label] + [str(r["cells"][c]) for c in cols])
        lines.append(["**Total**"] + [str(total["cells"][c]) for c in cols])
        print("\n".join(md_table(head, lines, cols)))
        print(f"\n{len(scope)} item(s); an item with several tags counts in several columns")
    if as_json:
        print(json.dumps(docs, indent=2))
    return 0


def tokens(text):
    """Lowercase alphanumeric runs; a hyphenated run such as an id is kept whole and
    also split into its parts, so DEF-LNCH-3 yields def-lnch-3, def, lnch, 3."""
    out = []
    for t in TOKEN.findall((text or "").lower()):
        out.append(t)
        if "-" in t:
            out += t.split("-")
    return out


SEARCH_W = {
    "id": 3.0,
    "code": 3.0,
    "title": 3.0,
    "body": 1.0,
    "evidence": 1.0,
    "cause": 1.0,
    "log": 1.0,
}
FUZZ = 0.8


def fuzzable(t):
    return len(t) >= 4 and "-" not in t and not any(c.isdigit() for c in t)


def rank_items(query, cands):
    """[(score, matched_fields, file, block)] best first; items scoring 0 are dropped."""
    import difflib
    import math

    q = list(dict.fromkeys(tokens(query)))
    if not q:
        raise SystemExit("search: the query has no searchable word")
    docs = []  # (f, b, {field: token list})
    for f, b in cands:
        fields = {
            # the base id is indexed too, so a search for DEF-LNCH-2 finds the
            # coded DEF-LNCH-2-PARSER as well as the full id does
            "id": tokens(ident(b)) + tokens(root_of(b)),
            "code": tokens(b["code"]),
            "title": tokens(b["title"]),
            "body": tokens(b["plain"]),
            "evidence": tokens(b["evidence"]),
            "cause": tokens(" ".join(c["text"] for c in b["causes"])),
            "log": tokens(" ".join(b["logs"])),
        }
        docs.append((f, b, fields))
    n = len(docs)
    if not n:
        return []
    tf, dl, df = [], [], {}
    for _, _, fields in docs:
        counts = {}
        for name, toks in fields.items():
            for t in toks:
                counts[t] = counts.get(t, 0.0) + SEARCH_W[name]
        tf.append(counts)
        dl.append(sum(counts.values()))
        for t in counts:
            df[t] = df.get(t, 0) + 1
    avgdl = sum(dl) / n or 1.0
    vocab = list(df)
    k1, bb = 1.5, 0.75

    def matches(w):
        """vocabulary token -> weight for one query token."""
        out = {w: 1.0} if w in df else {}
        if not fuzzable(w):
            return out
        for v in vocab:
            if v == w or not fuzzable(v):
                continue
            stem = v.startswith(w) or w.startswith(v)
            close = 2 * max(len(w), len(v)) <= 3 * min(len(w), len(v))
            if not (stem or close):
                continue
            r = difflib.SequenceMatcher(None, w, v).ratio()
            if stem or r >= FUZZ:
                out[v] = r
        return out

    hits = []
    qm = {w: matches(w) for w in q}
    for i, (f, b, fields) in enumerate(docs):
        score, seen = 0.0, set()
        for w, ms in qm.items():
            best = 0.0
            for v, wt in ms.items():
                t = tf[i].get(v)
                if not t:
                    continue
                idf = math.log(1 + (n - df[v] + 0.5) / (df[v] + 0.5))
                s = wt * idf * t * (k1 + 1) / (t + k1 * (1 - bb + bb * dl[i] / avgdl))
                if s > best:
                    best = s
                seen.add(v)
            score += best
        if score > 0:
            where = [name for name, toks in fields.items() if seen & set(toks)]
            hits.append((score, where, f, b))
    hits.sort(key=lambda h: (-h[0], fix_order(h[3]), h[2]))
    return hits


def cmd_search(files, fl, query, top, as_json):
    """The items most relevant to QUERY, best first - one table over every scanned
    file, since idf is a property of the whole candidate set."""
    index = link_index(files) if fl["blocked"] or fl["related_to"] else None
    cands = []
    for f in files:
        blocks, _ = parse(f)
        prefix = doc_prefix(f, blocks)
        if fl["severity"] and prefix != "DEF":
            print(f"{f}: skipped, --severity is a defect attribute", file=sys.stderr)
            continue
        if fl["importance"] and prefix != "ACC":
            print(f"{f}: skipped, --importance is a criterion attribute", file=sys.stderr)
            continue
        cands += [(f, b) for b in select(blocks, fl, index)]
    hits = rank_items(query, cands)
    rows = hits[:top]
    if as_json:
        print(
            json.dumps(
                [
                    {
                        "rank": i,
                        "id": ident(b),
                        "score": round(s, 3),
                        "title": b["title"],
                        "matched_in": where,
                        "file": f,
                        "line": b["line"],
                    }
                    for i, (s, where, f, b) in enumerate(rows, 1)
                ],
                indent=2,
            )
        )
        return 0
    notice_locked([b for _, _, _, b in rows])
    print(f'\n# SEARCH "{query}" - {", ".join(files)}{filter_note(fl, fl["status"])}\n')
    table = [
        [
            str(i),
            f"`{ident(b)}`",
            f"{s:.2f}",
            cell(b["title"] or "?", WIDTH["title"]),
            ", ".join(where),
        ]
        for i, (s, where, f, b) in enumerate(rows, 1)
    ]
    print(
        "\n".join(
            md_table(["Rank", "Id", "Score", "Title", "Matched in"], table, ["Rank", "Score"])
        )
    )
    more = f", top {top} shown" if len(hits) > top else ""
    print(f"\n{len(hits)} of {len(cands)} item(s) matched{more}")
    return 0


def cmd_refs(files, wanted, as_json=False):
    """Both directions of the link graph around one id, plus the transitive
    blocked-by chain. A blocker reached by a second route ends that chain with
    `...`: its own blockers were printed the first time. Inbound is listed even
    for an id no item carries - that is what `remove --force` leaves behind, and
    what separates it from a typo, which is refused."""
    index, scanned, inbound = {}, [], []
    for f in files:
        for b in parse(f)[0]:
            scanned.append((f, b))
            if b["prefix"]:
                index[ident(b)] = (f, b)
    blocks_by_id = {i: b for i, (_, b) in index.items()}
    wanted = resolve_ref(blocks_by_id, wanted)
    inbound = [
        {"file": f, "line": ln, "id": ident(b), "kind": k}
        for f, b in scanned
        for k, rid, ln in b["refs"]
        if resolve_ref(blocks_by_id, rid) == wanted
    ]
    if wanted not in index and not inbound:
        raise SystemExit(
            f"no item with id {wanted} in the scanned files, and nothing points at it"
        )
    outbound, paths, blockers = [], [], []
    if wanted in index:
        f, b = index[wanted]
        outbound = [
            {"file": f, "line": ln, "id": resolve_ref(blocks_by_id, rid), "kind": k}
            for k, rid, ln in b["refs"]
        ]
        seen = set()
        # (id, ids on the route so far, printed hops, depth); depth first, file order
        todo = [
            (resolve_ref(blocks_by_id, rid), [wanted], [], 1)
            for rid in reversed(targets(b, "blocked-by"))
        ]
        while todo:
            rid, ids, hops, depth = todo.pop()
            if rid in ids:
                paths.append(hops + [f"{rid} (cycle)"])
                continue
            st = status_of(index[rid][1]) if rid in index else "not found"
            hop = hops + [f"{rid} ({st})"]
            nxt = (
                [resolve_ref(blocks_by_id, r) for r in targets(index[rid][1], "blocked-by")]
                if rid in index
                else []
            )
            if rid in seen:
                paths.append(hop + ["..."] if nxt else hop)
                continue
            seen.add(rid)
            blockers.append({"id": rid, "status": st, "depth": depth})
            if nxt:
                todo += [(r, ids + [rid], hop, depth + 1) for r in reversed(nxt)]
            else:
                paths.append(hop)
    if as_json:
        print(
            json.dumps(
                {"id": wanted, "inbound": inbound, "outbound": outbound, "blockers": blockers},
                indent=2,
            )
        )
        return 0
    shown = [wanted, *(h["id"] for h in inbound + outbound), *(x["id"] for x in blockers)]
    notice_locked([index[i][1] for i in dict.fromkeys(shown) if i in index])
    for h in inbound:
        print(f"{h['file']}:{h['line']}: {h['id']} {h['kind']} -> {wanted}")
    for h in outbound:
        print(f"{h['file']}:{h['line']}: {wanted} {h['kind']} -> {h['id']}")
    for p in paths:
        print("blocked-by chain: " + " -> ".join(p))
    k = sum(1 for x in blockers if x["status"] == "open")
    print(f"\n{len(inbound)} inbound, {len(outbound)} outbound reference(s); {k} open blocker(s)")
    return 0


def _valid_stamp(s):
    try:
        datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def cmd_check(files, strict):
    index = link_index(files)
    cycles = {}  # smallest id -> the (kind, cycle) pairs reported on it
    for kind in ("blocked-by", "overrides"):
        for loop in cycles_in(graph(index, kind)):
            cycles.setdefault(loop[0], []).append((kind, loop))

    errors = warns = 0
    seen = {}  # ident -> (file, line); an id is unique across the scanned files
    roots = {}  # base id -> (file, line, ident); one root family per base, store-wide
    root_bases = {root_of(b) for b in index.values() if not b["regr"]}
    for f in files:
        lines = load(f)
        blocks, sections = parse(f)
        prefix = doc_prefix(f, blocks)
        want_hint = HINT_FOR[prefix]
        known_authors = roster_of(f)
        e, w, codes = [], [], {}
        # tracker and category log lines are validated as item log lines are
        wide = {n for n, _ in tracker_log(lines)}
        wide |= {n for s in sections for n, _ in s["log_lines"]}

        if not any(
            len(m.group(1)) == 1 for _, ln in non_fenced(lines) if (m := HEADING.match(ln))
        ):
            e.append((1, "no H1 title"))

        in_item = False  # between an item line and the next heading, as parse reads it
        for lineno, ln in non_fenced(lines):
            for ch in ln:
                cp = ord(ch)
                for lo, hi, name in FORBIDDEN:
                    if lo <= cp <= hi:
                        e.append((lineno, f"forbidden glyph {name} U+{cp:04X} {ch!r}"))
                        break
            if CBOX.match(ln) and not ITEM.match(ln):
                e.append((lineno, "malformed checkbox (use [ ], [x] or [-])"))
            h = HEADING.match(ln)
            if h:
                if IDREF.search(h.group(2)):
                    e.append((lineno, "id used as a heading; items are checklist lines only"))
                if h.group(2).strip().lower() == "contents":
                    e.append(
                        (
                            lineno,
                            "## Contents is a second source of truth; "
                            "delete it and derive the index with list-categories",
                        )
                    )
            lm = LOGLINE.match(ln) or (WIDELOG.match(ln) if lineno in wide else None)
            if lm and not (STAMP.match(lm.group(2)) and _valid_stamp(lm.group(2))):
                bad = "date only; run upgrade" if DATEONLY.match(lm.group(2)) else "malformed"
                e.append((lineno, f"log: stamp is {bad}; use ISO 8601 UTC, YYYY-MM-DDTHH:MM:SSZ"))
            if lm:
                am = AUTHORED.match(lm.group(3).strip())
                if not am:
                    e.append(
                        (
                            lineno,
                            "log: line has no @handle after the date; every entry is authored",
                        )
                    )
                elif am.group(1) not in known_authors:
                    e.append((lineno, f"{am.group(1)} is not on the ## Authors roster"))
            dm = DATED.match(ln)
            if dm and not LOGLINE.match(ln):
                e.append((lineno, "dated note missing the `log:` marker"))
            # a base id in an item's line or sub-lines: name the full id to write. A
            # log: line is append-only history and an attachment: line holds a path
            in_item = bool(ITEM.match(ln)) or (in_item and not h)
            if in_item and (ITEM.match(ln) or SUB.match(ln)) and not (lm or ATTANY.match(ln)):
                said = set()
                for m in IDREF.finditer(ln):
                    full = coded_ref(index, m)
                    if full and m[0] not in said:
                        said.add(m[0])
                        w.append((lineno, f"{m[0]} has no code; write {full}"))

        for s in sections:
            if not s["code"]:
                e.append((s["line"], f"category '{s['name']}' has no `CODE` on its heading"))
            elif s["code"] in codes:
                e.append(
                    (
                        s["line"],
                        f"duplicate category code {s['code']} (also line {codes[s['code']]})",
                    )
                )
            else:
                codes[s["code"]] = s["line"]
            if s["code"] and not s["desc"]:
                w.append(
                    (
                        s["line"],
                        f"category {s['code']} has no description line "
                        f"under its heading; run describe",
                    )
                )

        for b in blocks:
            if b["indent"]:
                e.append(
                    (b["line"], "nested checklist item; every item is top level with its own id")
                )
                continue
            if b["state"] == "X":
                e.append((b["line"], "uppercase [X], use [x]"))
            if b["section"] is None:
                e.append((b["line"], "item is not under a ## category heading"))
            if not b["prefix"]:
                if b["bad_id"]:
                    tok = IDBAD.match(b["text"]).group("tok")
                    e.append(
                        (
                            b["line"],
                            f"malformed code in id `{tok}`; a code is one or two "
                            "hyphen-separated A-Z0-9 segments, each starting with a letter",
                        )
                    )
                else:
                    e.append((b["line"], f"item has no `{prefix}-<CAT>-<N>` id; run upgrade"))
            else:
                if not b["code"]:
                    w.append(
                        (
                            b["line"],
                            "id has no code; every id carries one - run migrate-codes",
                        )
                    )
                if b["prefix"] != prefix:
                    e.append((b["line"], f"id prefix {b['prefix']} in a {prefix} document"))
                key = ident(b)
                if key in seen:
                    sf, sl = seen[key]
                    at = f"line {sl}" if sf == f else f"{sf}:{sl}"
                    e.append((b["line"], f"duplicate id {key} (first at {at})"))
                else:
                    seen[key] = (f, b["line"])
                if not b["regr"]:
                    # a base id names one family: its root and every regression.
                    # Two roots with different full ids would make a base-id link
                    # ambiguous across the store, so the second is an error.
                    base = root_of(b)
                    prev = roots.get(base)
                    if prev is None:
                        roots[base] = (f, b["line"], key)
                    elif prev[2] != key:
                        pf, pl, pid = prev
                        e.append(
                            (
                                b["line"],
                                f"duplicate base id {base}: roots {pid} ({pf}:{pl}) "
                                f"and {key} ({f}:{b['line']})",
                            )
                        )
                if b["regr"]:
                    # a regression is a fact about a defect; without its root anywhere
                    # in the scanned files it counts nothing and points nowhere
                    root = root_of(b)
                    if root not in root_bases:
                        e.append((b["line"], f"regression {key} has no root item {root}"))
            if not b["title"]:
                e.append((b["line"], "missing **bold title**"))
            if prefix == "DEF" and not b["severity"]:
                e.append(
                    (b["line"], "defect not triaged; the body must open with " + "/".join(SEVS))
                )
            elif prefix == "DEF" and b["severity"] in SEV_ALIAS:
                e.append(
                    (
                        b["line"],
                        f"foreign severity {b['severity']}; run upgrade "
                        f"(it becomes {SEV_ALIAS[b['severity']]})",
                    )
                )
            if prefix == "ACC" and not b["importance"]:
                e.append(
                    (b["line"], "criterion not rated; the body must open with " + "/".join(IMPS))
                )
            if b["hint_n"] > 1:
                e.append((b["line"], f"more than one {want_hint}: line; keep exactly one"))
            elif b["hint_kind"] and b["hint_kind"] != want_hint:
                e.append(
                    (
                        b["line"],
                        f"`{b['hint_kind']}:` line in a {prefix} document; use `{want_hint}:`",
                    )
                )
            elif not b["hint"]:
                w.append((b["line"], f"no {want_hint}: line under the item"))
            if b["tag_n"] > 1:
                e.append((b["line"], "more than one test-tags: line; keep exactly one"))
            elif not b["tags"]:
                w.append((b["line"], "no test-tags: line (NO-TEST)"))
            if b["evid_n"] > 1:
                e.append((b["line"], "more than one evidence: line; keep exactly one"))
            elif status_of(b) == "closed" and not b["evidence"]:
                w.append(
                    (
                        b["line"],
                        "closed with no evidence: line; record the proof with edit --evidence",
                    )
                )
            elif b["evidence"] and status_of(b) != "closed":
                w.append((b["line"], "evidence: on an item that is not closed"))
            if b["causes"]:
                want_cause = CAUSE_FOR[prefix]
                foreign = sorted({c["kind"] for c in b["causes"]} - {want_cause})
                if foreign:
                    e.append(
                        (
                            b["line"],
                            f"`{foreign[0]}:` line in a {prefix} document; use `{want_cause}:`",
                        )
                    )
                if b["cause_bad"]:
                    e.append(
                        (
                            b["line"],
                            f"{want_cause}: line is malformed; use "
                            f"`- {want_cause}: <ISO 8601 UTC stamp> @xx <text>`",
                        )
                    )
                if not b["cause_order"]:
                    w.append(
                        (
                            b["line"],
                            f"{want_cause}: records are not newest first; the topmost "
                            "record is the one read as current",
                        )
                    )
            if status_of(b) == "rejected" and not reject_reason(b):
                w.append((b["line"], "rejected with no reason; log `rejected: <why>`"))
            # read-only: an expired or stray lock is reported, never removed here
            if b["lock_n"] > 1:
                e.append((b["line"], "more than one lock: line; keep exactly one"))
            if b["lock_bad"]:
                e.append(
                    (
                        b["line"],
                        "lock: line is malformed; use `- lock: <ISO 8601 UTC stamp> @xx [note]`",
                    )
                )
            if b["lock"] and not lock_active(b):
                w.append((b["line"], "expired lock, cleared on the next write"))
            elif b["lock"] and status_of(b) != "open":
                w.append((b["line"], f"lock on a {status_of(b)} item; run unlock"))
            if b["att_bad"]:
                e.append(
                    (
                        b["line"],
                        "attachment: line is malformed; use "
                        "`- attachment: <path> sha256:<16 hex> edited:<ISO 8601 UTC stamp>`",
                    )
                )
            seen_att = set()
            for a in b["attachments"]:
                if not _valid_stamp(a["edited"]):
                    e.append(
                        (a["line"], f"attachment {a['path']}: edited stamp is not ISO 8601 UTC")
                    )
                if a["path"] in seen_att:
                    e.append((a["line"], f"attachment {a['path']} listed twice; keep one line"))
                seen_att.add(a["path"])
                target = att_path(f, a["path"])
                if not target.is_file():
                    w.append((a["line"], f"attachment {a['path']} is missing"))
                    continue
                sha, edited = fingerprint(target)
                if sha != a["sha256"]:
                    w.append(
                        (
                            a["line"],
                            f"attachment {a['path']} changed since {a['edited']} "
                            f"(sha256 {a['sha256']} is now {sha}, edited {edited}); "
                            "run attach to refresh",
                        )
                    )
            if not b["has_log"]:
                e.append((b["line"], "item has no authored log: line; every entry is authored"))
            for kind, rid, lineno in b["refs"]:
                tgt = resolve_ref(index, rid)
                if tgt not in index:
                    e.append((lineno, f"{kind} points at {rid}, not found in the scanned files"))
                    continue
                if kind == "blocked-by" and status_of(b) == "open":
                    state = status_of(index[tgt])
                    if state in ("closed", "rejected"):
                        w.append(
                            (
                                lineno,
                                f"blocked-by {tgt} is {state}; the block no longer holds",
                            )
                        )
                    else:
                        w.append(
                            (
                                lineno,
                                f"blocked-by {tgt} is {state}; the block still holds",
                            )
                        )
                if kind in MIRROR and not any(
                    resolve_ref(index, r) == ident(b) for r in targets(index[tgt], MIRROR[kind])
                ):
                    e.append(
                        (
                            lineno,
                            f"{kind} {tgt}, but {tgt} has no `{MIRROR[kind]}: {ident(b)}` "
                            f"line; run: pm-tools relate {f} --id {ident(b)} --{kind} {tgt}",
                        )
                    )
                if kind == "overridden-by" and status_of(b) == "open":
                    w.append(
                        (
                            lineno,
                            f"overridden-by {tgt} but still open; an overridden item "
                            "no longer holds, reject it or close it",
                        )
                    )
            for kind, loop in cycles.get(ident(b), []) if b["prefix"] else []:
                # a duplicated id (its own check error) can hand the cycle to a
                # copy that lacks the closing line; anchor on the item then
                at = next(
                    (
                        ln
                        for k, r, ln in b["refs"]
                        if k == kind and resolve_ref(index, r) == loop[1]
                    ),
                    b["line"],
                )
                e.append(
                    (
                        at,
                        f"{'override' if kind == 'overrides' else kind} cycle: "
                        + " -> ".join(loop)
                        + "; run relate again for the link that holds, "
                        "it removes the older one",
                    )
                )

        for lineno, msg in sorted(e):
            print(f"{f}:{lineno}: ERROR {msg}")
        for lineno, msg in sorted(w):
            print(f"{f}:{lineno}: warn  {msg}")
        errors += len(e)
        warns += len(w)

    ok = errors == 0 and (warns == 0 or not strict)
    print(f"\n{errors} error(s), {warns} warning(s)" + ("" if ok else "  [FAIL]"))
    return 0 if ok else 1


# ------------------------------------------------------------------------- edit


def section_for(sections, code, name, desc, lines):
    for s in sections:
        if s["code"] == code:
            return s, lines
    if not name:
        have = ", ".join(s["code"] or "?" for s in sections) or "(none)"
        raise SystemExit(
            f"unknown category code {code}; have: {have}. Pass --name to create the category"
        )
    lines = lines + ([""] if lines and lines[-1].strip() else []) + [f"## {name} `{code}`", ""]
    sec = dict(line=len(lines) - 1, name=name, code=code, raw=f"{name} `{code}`", desc=desc)
    if desc:
        lines = lines + [desc, ""]
    return sec, lines


def insert_index(lines, sec):
    j = sec["line"]
    while j < len(lines) and not HEADING.match(lines[j]):
        j += 1
    while j - 1 > sec["line"] and not lines[j - 1].strip():
        j -= 1
    return j


def hint_kind_for(file, blocks, repro, test):
    """Which hint the flags asked for, checked against the discipline of the doc."""
    if repro and test:
        raise SystemExit("pass --repro or --test, not both")
    kind, value = ("repro", repro) if repro else ("test", test) if test else (None, None)
    if kind:
        want = HINT_FOR[doc_prefix(file, blocks)]
        if kind != want:
            raise SystemExit(f"this is a {want}: document; use --{want}")
    return kind, value


def cause_kind_for(file, blocks, mechanism, root_cause):
    """Which record the flags asked for, checked against the discipline of the doc."""
    if mechanism and root_cause:
        raise SystemExit("pass --mechanism or --root-cause, not both")
    kind, value = (
        ("mechanism", mechanism)
        if mechanism
        else ("root-cause", root_cause)
        if root_cause
        else (None, None)
    )
    if kind:
        want = CAUSE_FOR[doc_prefix(file, blocks)]
        if kind != want:
            raise SystemExit(f"this is a {want}: document; use --{want}")
    return kind, value


def set_cause(lines, b, kind, value, update):
    """Write a record. By default it goes above the ones already there - the previous
    theory stays readable, which is the whole point of the field on a long hunt.
    --update rewrites the newest record instead, for a rewording of the same theory."""
    ind = sub_indent(lines, b)
    line = f"{ind}- {kind}: {value}"
    for i in range(b["line"], block_end(lines, b)):
        if CAUSELINE.match(lines[i]):
            if update:
                lines[i] = line
                return "updated"
            lines.insert(i, line)
            return "overridden"
    lines.insert(b["line"], line)
    return "recorded"


def set_line(lines, b, marker, value, pat):
    """Replace the item's `- <marker>:` sub-line, or add one under the item line.
    Returns the value it replaced, or None when it added the line."""
    ind = sub_indent(lines, b)
    for i in range(b["line"], block_end(lines, b)):
        if pat.match(lines[i]):
            old = lines[i].split(":", 1)[1].strip()
            lines[i] = f"{ind}- {marker}: {value}"
            return old
    lines.insert(b["line"], f"{ind}- {marker}: {value}")
    return None


def drop_line(lines, b, pat):
    """Remove the item's `- <marker>:` sub-line. Returns what it said, or None."""
    for i in range(b["line"], block_end(lines, b)):
        if pat.match(lines[i]):
            return lines.pop(i).split(":", 1)[1].strip()
    return None


def need_author(file, handle):
    """Every log line names who wrote it, and the handle must already be on the roster."""
    if not handle:
        raise SystemExit("every entry is authored; pass --author @xx")
    h = handle if handle.startswith("@") else "@" + handle
    if not HANDLE.fullmatch(h):
        raise SystemExit(f"bad handle {handle!r}; use @ plus 2-4 letters, e.g. @kj")
    known = roster_of(file)
    if h not in known:
        have = ", ".join(sorted(known)) or "(roster empty)"
        raise SystemExit(
            f"{h} is not on the authors roster of {file} - have: {have}. "
            f'Run: pm-tools author {file} --handle {h} --name "Full Name"'
        )
    return h


def put_record(lines, head, record):
    """Insert a wide log line into `lines`: under the `##` heading at 0-based index
    `head`, or in the preamble with head None. It goes after the log's last line, else
    at the end of the prose there, a blank line between it and any prose or item."""
    start = 0 if head is None else head + 1
    stop, last = len(lines), None
    for lineno, ln in non_fenced(lines):
        i = lineno - 1
        if i < start:
            continue
        h = HEADING.match(ln)
        if (h and (head is not None or len(h.group(1)) == 2)) or (
            head is not None and ITEM.match(ln)
        ):
            stop = i
            break
        if WIDELOG.match(ln):
            last = i
    if last is not None:
        lines.insert(last + 1, record)
        return
    at = stop
    while at > start and not lines[at - 1].strip():
        at -= 1
    block = [record]
    if at > 0 and lines[at - 1].strip():
        block.insert(0, "")
    if at < len(lines) and lines[at].strip():
        block.append("")
    lines[at:at] = block


def tracker_record(file, lines, author, event):
    """Append a tracker record, a tracker-wide change, to the preamble of `lines` (the
    content of FILE) in place: `- log: <stamp> @xx <event>`."""
    put_record(lines, None, f"- log: {now()} {need_author(file, author)} {event}")


def category_record(file, lines, head, author, event):
    """Append a category record, a category-wide change, to the category log under the
    `##` heading at 0-based index `head` of `lines` (the content of FILE) in place."""
    put_record(lines, head, f"- log: {now()} {need_author(file, author)} {event}")


def cmd_author(file, handle, name):
    h = handle if handle.startswith("@") else "@" + handle
    if not HANDLE.fullmatch(h):
        raise SystemExit(f"bad handle {handle!r}; use @ plus 2-4 letters, e.g. @kj")
    expire_locks(file)
    lines = load(file)
    entry = f"- `{h}` {name}"
    start = end = None
    for i, ln in enumerate(lines):
        m = HEADING.match(ln)
        if m and len(m.group(1)) == 2 and m.group(2).strip().lower() == "authors":
            start = i
        elif m and start is not None:
            end = i
            break
    if start is None:
        # roster is document metadata: it goes directly under the H1, above the first ##
        at = next(
            (i for i, ln in enumerate(lines) if (m := HEADING.match(ln)) and len(m.group(1)) == 2),
            len(lines),
        )
        block = ["## Authors", "", entry, ""]
        if at > 0 and lines[at - 1].strip():
            block = [""] + block
        lines[at:at] = block
        what = "roster created"
    else:
        end = end if end is not None else len(lines)
        for i in range(start, end):
            m = ROSTER.match(lines[i])
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
    save(file, lines)
    print(f"{file}: {h} {what}")
    return 0


def cmd_add(
    file,
    cat,
    name,
    desc,
    title,
    text,
    severity,
    importance,
    repro,
    test,
    tags,
    author,
    code,
    mechanism=None,
    root_cause=None,
    reason=None,
):
    expire_locks(file)
    lines = load(file)
    blocks, sections = parse(file)
    prefix = doc_prefix(file, blocks)
    kind, value = hint_kind_for(file, blocks, repro, test)
    ckind, cvalue = cause_kind_for(file, blocks, mechanism, root_cause)
    who = need_author(file, author)
    if prefix == "ACC" and severity:
        raise SystemExit("acceptance criteria carry no severity")
    if prefix == "DEF" and importance:
        raise SystemExit("defects carry no importance; triage with --severity")
    if prefix == "DEF" and not severity:
        raise SystemExit("a defect must be triaged; pass --severity " + "|".join(SEVS))
    if prefix == "ACC" and not importance:
        raise SystemExit("a criterion must be rated; pass --importance " + "|".join(IMPS))
    cat = cat.upper()
    if not re.fullmatch(r"[A-Z]{2,6}", cat):
        raise SystemExit(
            f"category code {cat!r} must be 2-6 uppercase letters; "
            f"three to five is the normal range, six the ceiling"
        )
    code = norm_code(code)
    sec, lines = section_for(sections, cat, name, desc, lines)
    if all(s is not sec for s in sections):
        category_record(file, lines, sec["line"] - 1, who, "category created")
    beside = [
        b
        for f in siblings(file)[1:]
        for b in parse(f)[0]
        if b["prefix"] == prefix and b["cat"] == cat
    ]
    num = next_num(blocks + beside)
    lead = severity or importance
    opening = level_heading(SEV if prefix == "DEF" else IMP, text)
    if opening:  # a `LEVEL;` heading on the text; the flag's level replaces it
        text = text[opening.end() :].lstrip(" ;:,")
    body = f"{lead.upper()}; {text}" if lead else text
    item = f"- [ ] `{prefix}-{cat}-{num}-{code}` **{title}** - {body}"
    at = insert_index(lines, sec)
    stamp = now()
    tail = [f"  - {kind}: {value}"] if kind else []
    tail += [f"  - test-tags: {canon_tags(tags)}"] if tags else []
    tail += [f"  - {ckind}: {stamp} {who} {cvalue.strip()}"] if ckind else []
    # the category description is a paragraph; a list must not butt straight onto it
    prose = (
        at > 0
        and lines[at - 1].strip()
        and not ITEM.match(lines[at - 1])
        and not SUB.match(lines[at - 1])
    )
    lead = [""] if prose else []
    lines[at:at] = lead + [item] + tail + [f"  - log: {stamp} {who} added{because(reason)}"]
    save(file, lines)
    print(f"{file}:{at + len(lead) + 1}: {prefix}-{cat}-{num}-{code} added")
    return 0


def cmd_cause(file, wanted, kind, text, author, update, reason=None):
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    prefix = doc_prefix(file, blocks)
    want = CAUSE_FOR[prefix]
    if kind != want:
        raise SystemExit(f"this is a {want}: document; run pm-tools {want}")
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, prefix))
    warn_lock(file, b, who)
    if update and not b["causes"]:
        raise SystemExit(
            f"{ident(b)} carries no {want}: record to update; write one without --update"
        )
    # --update rewrites the newest record, which set_cause finds first, as parse does
    c = b["causes"][0] if update else None
    old = " ".join(filter(None, (c["stamp"], c["author"], c["text"]))) if c else None
    did = set_cause(lines, b, kind, f"{now()} {who} {text.strip()}", update)
    if reason or old:
        # after an update the replaced record's stamp, author and wording exist nowhere
        # else, so the log keeps them; a new record carries its own and is logged only
        # for a --reason
        what = f'{kind} {did} "{old}" -> "{text.strip()}"' if old else f"{kind} {did}"
        lines.insert(
            block_end(lines, b),
            f"{sub_indent(lines, b)}- log: {now()} {who} {what}{because(reason)}",
        )
    save(file, lines)
    print(f"{file}:{b['line']}: {ident(b)} {want} {did}")
    return 0


def rewrite_head(lines, b, title=None, text=None, sev=None, importance=None):
    """Rewrite the item line with a new title, text, severity or importance."""
    body = b["body"]
    bold = BOLD.search(body)
    cur_title = bold.group(1) if bold else ""
    cur_text = body[bold.end() :].lstrip(" -") if bold else body
    new_text = text if text else cur_text
    if sev or importance:
        rx = SEV if sev else IMP
        # the kept body is headed by its old level; supplied text only by a `LEVEL;` heading
        head = level_heading(rx, new_text) if text else rx.match(new_text)
        rest = new_text[head.end() :] if head else new_text
        new_text = f"{sev or importance}; " + rest.lstrip(" ;:,-")
    elif text and b["severity"] and not level_heading(SEV, new_text):
        # a --text rewrite must not quietly untriage the defect
        new_text = f"{b['severity']}; {new_text}"
    elif text and b["importance"] and not level_heading(IMP, new_text):
        # nor quietly unrate the criterion
        new_text = f"{b['importance']}; {new_text}"
    lines[b["line"] - 1] = f"- [{b['state']}] `{ident(b)}` **{title or cur_title}** - {new_text}"


def changed(field, old, new):
    """One field's change as a log fragment - the old value kept, or marked as added."""
    return f'{field} "{old}" -> "{new}"' if old else f'{field} added "{new}"'


def cmd_edit(
    file,
    wanted,
    title,
    text,
    sev,
    importance,
    repro,
    test,
    tags,
    author,
    evidence=None,
    reason=None,
):
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    prefix = doc_prefix(file, blocks)
    kind, value = hint_kind_for(file, blocks, repro, test)
    who = need_author(file, author)
    if sev and prefix != "DEF":
        raise SystemExit("acceptance criteria carry no severity")
    if importance and prefix != "ACC":
        raise SystemExit("defects carry no importance; triage with --severity")
    if not (title or text or sev or importance or kind or tags or evidence):
        raise SystemExit(
            "nothing to change; pass --title, --text, --severity, --importance, "
            "--repro/--test, --test-tags or --evidence"
        )
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    warn_lock(file, b, who)
    # the log keeps each value the edit replaces, so the item's history survives it
    done = [
        changed(field, old, new)
        for field, old, new in (
            ("title", b["title"], title),
            ("text", b["plain"], text),
            ("severity", b["severity"], sev),
            ("importance", b["importance"], importance),
        )
        if new
    ]
    if title or text or sev or importance:
        rewrite_head(lines, b, title, text, sev, importance)
    if kind:
        done.append(changed(kind, set_line(lines, b, kind, value, HINTLINE), value))
    if tags:
        tagged = canon_tags(tags)
        done.append(changed("test-tags", set_line(lines, b, "test-tags", tagged, TAGLINE), tagged))
    if evidence:
        done.append(
            changed("evidence", set_line(lines, b, "evidence", evidence, EVIDLINE), evidence)
        )
    lines.insert(
        block_end(lines, b),
        f"{sub_indent(lines, b)}- log: {now()} {who} edited {'; '.join(done)}{because(reason)}",
    )
    save(file, lines)
    print(
        f"{file}:{b['line']}: {ident(b)} {' and '.join(d.split(' ', 1)[0] for d in done)} updated"
    )
    return 0


def cmd_amend(file, wanted, title, text, author, reason=None):
    """Reword an item; the log line keeps the wording it replaced, so a title
    renamed three times shows three log lines under the current one."""
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    if not (title or text):
        raise SystemExit("nothing to amend; pass --title and/or --text")
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    warn_lock(file, b, who)
    was = [
        f'{what} "{old}" -> "{new}"'
        for what, old, new in (("title", b["title"] or "", title), ("text", b["plain"], text))
        if new
    ]
    rewrite_head(lines, b, title, text)
    lines.insert(
        block_end(lines, b),
        f"{sub_indent(lines, b)}- log: {now()} {who} amended {'; '.join(was)}{because(reason)}",
    )
    save(file, lines)
    print(
        f"{file}:{b['line']}: {ident(b)} amended {' and '.join(w.split(' ', 1)[0] for w in was)}"
    )
    return 0


def cmd_describe(file, code, text, author, block=None, append=None, note=None, remove=False):
    """--text sets the description line, or note N when `note` is given; `block` replaces
    every line from the heading down to the first item or heading, so a list or note under
    the description has a write command too; `append` adds a note after the last prose
    line and `remove` drops note N. Each keeps the category log lines and appends a
    category record."""
    if remove and note is None:
        raise SystemExit("--remove needs --note N")
    if note is not None and text is None and not remove:
        raise SystemExit("--note N needs --text or --remove")
    who = need_author(file, author)
    expire_locks(file)
    lines = load(file)
    _, sections = parse(file)
    code = code.upper()
    sec = next((s for s in sections if s["code"] == code), None)
    if sec is None:
        have = ", ".join(s["code"] or "?" for s in sections) or "(none)"
        raise SystemExit(f"unknown category code {code}; have: {have}")
    new = None  # the prose lines to write; a note's text is a block of one line
    if block is not None:
        flag, new = "--text-file", [ln.rstrip() for ln in block.splitlines()]
    elif append is not None:
        flag, new = "--append", [append.strip()]
    elif note is not None and not remove:
        flag, new = "--text", [text.strip()]
    if new is not None:
        while new and not new[-1]:
            new.pop()
        while new and not new[0]:
            new.pop(0)
        if not new:
            raise SystemExit(f"{flag} is empty; the prose block needs at least one line")
        fences = sum(1 for ln in new if re.match(r"^\s*```", ln))
        if fences % 2 or any(
            HEADING.match(ln) or CBOX.match(ln) or re.match(r"^\s*- log:", ln)
            for _, ln in non_fenced(new)
        ):
            raise SystemExit(
                f"{flag} holds a heading, a checklist item, a `- log:` line or an "
                "unclosed code fence; the prose block takes prose only"
            )
    start = end = sec["line"]  # 0-based index of the line after the heading
    fence, at = False, [n - 1 for n, _ in sec["log_lines"]]  # at: the category log lines
    while end < len(lines):
        if re.match(r"^\s*```", lines[end]):
            fence = not fence
        elif not fence and (HEADING.match(lines[end]) or ITEM.match(lines[end])):
            break
        end += 1
    if append is not None or note is not None:
        notes = sec["notes"]
        if append is not None:
            # the last prose line, a closing fence included, so the note follows it
            prose = [j for j in range(start, end) if j not in at and lines[j].strip()]
            if sec["desc"] is None or not prose:
                raise SystemExit(
                    f"category {code} has no description line, which an appended note would "
                    f'become; set one first: pm-tools describe {file} --category {code} --text "..." --author @xx'
                )
            lines[prose[-1] + 1 : prose[-1] + 1] = ["", new[0]]
            note, event, what = len(notes) + 1, f'added note "{new[0]}"', f'added "{new[0]}"'
        else:
            if not 1 <= note <= len(notes):
                raise SystemExit(f"no note {note} in {code}; it has {len(notes)} note(s)")
            n, old = notes[note - 1]
            if remove:
                del lines[n - 1]
                event, what = f'removed note {note} "{old}"', f'removed "{old}"'
            elif new[0] == old:
                print(f"{file}:{sec['line']}: {code} note {note} unchanged")
                return 0
            else:
                s = lines[n - 1]
                lines[n - 1] = s[: len(s) - len(s.lstrip())] + new[0]
                event = f'changed note {note} "{old}" -> "{new[0]}"'
                what = f'changed "{old}" -> "{new[0]}"'
        category_record(file, lines, sec["line"] - 1, who, event)
        save(file, lines)
        print(f"{file}:{sec['line']}: {code} note {note} {what}")
        return 0
    if block is not None:
        logs = [lines[j] for j in at]
        old = [lines[j].rstrip() for j in range(start, end) if j not in at]
        while old and not old[-1]:
            old.pop()
        while old and not old[0]:
            old.pop(0)
        if old == new:
            print(f"{file}:{sec['line']}: {code} prose block unchanged")
            return 0
        tail = ["", *logs] if logs else []
        lines[start:end] = ["", *new, *tail, *([""] if end < len(lines) else [])]
        category_record(
            file,
            lines,
            sec["line"] - 1,
            who,
            f"prose block replaced, {len(old)} line(s) -> {len(new)} line(s)",
        )
        save(file, lines)
        print(f"{file}:{sec['line']}: {code} prose block replaced, {len(new)} lines")
        return 0
    i = sec["line"]  # 0-based index of the line after the heading
    while i < len(lines) and (not lines[i].strip() or WIDELOG.match(lines[i])):
        i += 1
    prose = (
        i < len(lines)
        and lines[i].strip()
        and not HEADING.match(lines[i])
        and not ITEM.match(lines[i])
        and not SUB.match(lines[i])
    )
    old = lines[i].strip() if prose else None
    if old == text:
        print(f"{file}:{sec['line']}: {code} description unchanged")
        return 0
    if prose:
        lines[i] = text
        what = "replaced"
    else:
        ins = ["", text]
        if sec["line"] < len(lines) and lines[sec["line"]].strip():
            ins.append("")
        lines[sec["line"] : sec["line"]] = ins
        what = "added"
    category_record(file, lines, sec["line"] - 1, who, changed("description", old, text))
    save(file, lines)
    print(f"{file}:{sec['line']}: {code} description {what}")
    return 0


def siblings(file):
    """FILE first, then every other tracker beside it: a link may run from a criterion
    to a defect, so a dependency graph spans the directory."""
    here = pathlib.Path(file).resolve()
    beside = resolve([str(pathlib.Path(file).parent)])
    return [file, *(f for f in beside if pathlib.Path(f).resolve() != here)]


def put_rel(file, wanted, kind, value):
    """One relation line under an item, after its last one. Never merged into an
    existing line: a relation line may end in free text, and appending an id after
    that prose would bury it. check unions them."""
    lines = load(file)
    b = find_id(parse(file)[0], wanted)
    at = b["line"]
    for i in range(b["line"], block_end(lines, b)):
        if RELLINE.match(lines[i]):
            at = i + 1
    lines.insert(at, f"{sub_indent(lines, b)}- {kind}: {value}")
    save(file, lines)
    print(f"{file}:{b['line']}: {ident(b)} {kind}: {value}")


def cut_rel(file, wanted, kind, rid, who, why):
    """Remove the link to `rid` from an item's lines of one kind and log what stood
    there. A line that names other ids keeps them; `rid` and the line may name the
    same item by its base id or its full id."""
    lines = load(file)
    b = find_id(parse(file)[0], wanted)
    index = link_index(siblings(file))
    rid = resolve_ref(index, rid)
    was = []
    for i in range(block_end(lines, b) - 1, b["line"] - 1, -1):
        m = RELLINE.match(lines[i])
        if not m or m.group(2) != kind:
            continue
        spans = [r.span() for r in IDREF.finditer(m.group(3)) if resolve_ref(index, r[0]) == rid]
        if not spans:
            continue
        was.insert(0, m.group(3).strip())
        rest = m.group(3)
        for start, end in reversed(spans):
            rest = rest[:start] + rest[end:]
        rest = re.sub(r"^[\s,]+|,\s*(?=,)|,\s*(?=$| - )", "", rest).strip()
        if IDREF.search(rest):
            lines[i] = f"{m.group(1)}- {kind}: {rest}"
        else:
            del lines[i]
    if not was:
        return
    said = "; ".join(was)
    event = f"{kind} {rid} removed" + ("" if said == rid else f', line read "{said}"')
    event += f" - {why}" if why else ""
    lines.insert(block_end(lines, b), f"{sub_indent(lines, b)}- log: {now()} {who} {event}")
    save(file, lines)
    print(f"{file}:{b['line']}: {ident(b)} {event}")


def cmd_relate(file, wanted, related, blocked, overrides=None, overridden=None, author=None):
    """Write relation lines, and keep both dependency graphs free of cycles while doing
    it. An override is written on both items. When a new blocked-by or override link
    closes a cycle the newest link holds: every older link into the item that takes
    the new one, from the item it now points at or from anything that item leads to,
    is removed and logged where it stood. Planned on the graph first, so a refusal
    writes nothing."""
    if not (related or blocked or overrides or overridden):
        raise SystemExit(
            "nothing to link; pass --related, --blocked-by, --overrides or --overridden-by"
        )
    expire_locks(file)
    blocks, _ = parse(file)
    me = norm_id(wanted, doc_prefix(file, blocks))
    mine = find_id(blocks, me)
    me = ident(mine)
    warn_lock(file, mine, as_handle(author))
    where, index = {}, {}
    for f in siblings(file):
        for b in parse(f)[0]:
            if b["prefix"]:
                where.setdefault(ident(b), f)
                index.setdefault(ident(b), b)

    def ids(value):
        return list(dict.fromkeys(r[0] for r in IDREF.finditer(value or "")))

    # a base id is written as the full id it names; the text around the ids stays as typed
    added = {}

    def coded(kind, value):
        def full(m):
            rid = coded_ref(index, m)
            if rid:
                added.setdefault(kind, []).append((m[0], rid))
            return rid or m[0]

        return IDREF.sub(full, value) if value else value

    related, blocked = coded("related", related), coded("blocked-by", blocked)
    overrides, overridden = coded("overrides", overrides), coded("overridden-by", overridden)

    def write(kind, value):
        put_rel(file, me, kind, value)
        for typed, rid in dict.fromkeys(added.get(kind, [])):
            print(f"{file}: {me} {kind}: {typed} -> {rid}, added code {index[rid]['code']}")

    for kind, value in (("overrides", overrides), ("overridden-by", overridden)):
        if value and not ids(value):
            raise SystemExit(f"--{kind} names no id")
        absent = [t for t in ids(value) if resolve_ref(index, t) not in where]
        if absent:
            raise SystemExit(
                f"{absent[0]} is not in the trackers beside {file}; "
                "an override is written on both items"
            )
    both = sorted(
        {resolve_ref(index, t) for t in ids(overrides)}
        & {resolve_ref(index, t) for t in ids(overridden)}
    )
    if both:
        raise SystemExit(f"{both[0]} is named by --overrides and by --overridden-by; pick one")
    # (graph, from, to): blocked-by points at the blocker, overrides at the overridden
    links = [("blocked-by", me, resolve_ref(index, t)) for t in ids(blocked)]
    links += [("overrides", me, resolve_ref(index, t)) for t in ids(overrides)]
    links += [("overrides", resolve_ref(index, t), me) for t in ids(overridden)]
    if any(src == dst for _, src, dst in links):
        raise SystemExit(f"{me} cannot link to itself")

    adj = {kind: graph(index, kind) for kind in ("blocked-by", "overrides")}
    cuts = []
    for kind, src, dst in links:
        g = adj[kind]
        reach, todo = set(), [dst]
        while todo:
            n = todo.pop()
            if n not in reach:
                reach.add(n)
                todo += g.get(n, [])
        for n in sorted(x for x in reach if src in g.get(x, [])):
            g[n].remove(src)
            cuts.append((kind, n, src, dst))
        g.setdefault(src, []).append(dst)
    if cuts and not author:
        kind, n, src, dst = cuts[0]
        raise SystemExit(
            f"{src} {kind} {dst} closes a cycle; the older link {n} {kind} {src} "
            "is removed and logged, so pass --author @xx"
        )
    fresh = {file}

    def ready(f, item):
        """Another item is about to be written: its file drops expired locks once, and
        a lock someone else holds on it is named."""
        if f not in fresh:
            fresh.add(f)
            expire_locks(f)
        if item != me:
            warn_lock(f, find_id(parse(f)[0], item), as_handle(author))

    who = {
        f: need_author(f, author) for f in {where[x] for kind, n, src, _ in cuts for x in (n, src)}
    }
    for kind, n, src, dst in cuts:
        why = f"cycle with newer link {src} {kind} {dst}"
        ready(where[n], n)
        cut_rel(where[n], n, kind, src, who[where[n]], why)
        if kind == "overrides":
            ready(where[src], src)
            cut_rel(where[src], src, "overridden-by", n, who[where[src]], why)

    for kind, value in (
        ("related", related),
        ("blocked-by", blocked),
        ("overrides", overrides),
        ("overridden-by", overridden),
    ):
        if not value:
            continue
        if kind not in MIRROR:
            write(kind, value)
            continue
        # run again on a pair that lost one line: the missing line alone is written
        recorded = {resolve_ref(index, r) for r in targets(find_id(parse(file)[0], me), kind)}
        if all(resolve_ref(index, t) in recorded for t in ids(value)):
            print(f"{file}: {me} {kind}: {value} is already recorded")
        else:
            write(kind, value)
        for t in ids(value):
            t = resolve_ref(index, t)
            other = find_id(parse(where[t])[0], t)
            if me not in {resolve_ref(index, r) for r in targets(other, MIRROR[kind])}:
                ready(where[t], t)
                put_rel(where[t], t, MIRROR[kind], me)
    return 0


def cmd_unrelate(file, wanted, related, blocked, overrides, overridden, author, event):
    """Remove links and log each on the item that lost it; an override goes from both
    items. Planned first, so a link the item does not carry writes nothing."""
    asked = [
        (kind, value)
        for kind, value in (
            ("related", related),
            ("blocked-by", blocked),
            ("overrides", overrides),
            ("overridden-by", overridden),
        )
        if value
    ]
    if not asked:
        raise SystemExit(
            "nothing to unlink; pass --related, --blocked-by, --overrides or --overridden-by"
        )
    expire_locks(file)
    blocks, _ = parse(file)
    me = norm_id(wanted, doc_prefix(file, blocks))
    b = find_id(blocks, me)
    me = ident(b)
    who = need_author(file, author)
    warn_lock(file, b, who)
    where, index = {}, {}
    for f in siblings(file):
        for x in parse(f)[0]:
            if x["prefix"]:
                where.setdefault(ident(x), f)
                index.setdefault(ident(x), x)
    cuts = []
    for kind, value in asked:
        rids = list(dict.fromkeys(r[0] for r in IDREF.finditer(value)))
        if not rids:
            raise SystemExit(f"--{kind} names no id")
        for rid in rids:
            rid = resolve_ref(index, rid)
            if rid not in {resolve_ref(index, r) for r in targets(b, kind)}:
                raise SystemExit(f"{me} has no `{kind}: {rid}` line; nothing was removed")
            mirror = None
            if kind in MIRROR and rid in where:
                f = where[rid]
                if f != file:
                    expire_locks(f)
                other = find_id(parse(f)[0], rid)
                if me in {resolve_ref(index, r) for r in targets(other, MIRROR[kind])}:
                    mirror = (f, need_author(f, author))
                    warn_lock(f, other, who)
            cuts.append((kind, rid, mirror))
    for kind, rid, mirror in cuts:
        cut_rel(file, me, kind, rid, who, event)
        if mirror:
            cut_rel(mirror[0], rid, MIRROR[kind], me, mirror[1], event)
    return 0


def cmd_attach(file, wanted, paths, author):
    """Record artefacts - a screenshot, a document - under an item with the checksum and
    last-edit stamp they had when attached, so check can tell when one changed. The
    same path again refreshes its line and the log keeps the checksum it replaced."""
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    warn_lock(file, b, who)
    ind = sub_indent(lines, b)
    base = pathlib.Path(file).resolve().parent
    for raw in paths:
        ap = pathlib.Path(raw).resolve()
        if not ap.is_file():
            raise SystemExit(f"attachment not found: {raw}")
        rel = pathlib.PurePath(os.path.relpath(ap, base)).as_posix()
        sha, edited = fingerprint(ap)
        line = f"{ind}- attachment: {rel} sha256:{sha} edited:{edited}"
        had = next((a for a in b["attachments"] if a["path"] == rel), None)
        if had and (had["sha256"], had["edited"]) == (sha, edited):
            print(f"{file}:{b['line']}: {ident(b)} attachment {rel} unchanged")
            continue
        if had:
            # earlier inserts in this loop shift the line, so find it by its path
            at = next(
                i
                for i in range(b["line"], block_end(lines, b))
                if (m := ATTLINE.match(lines[i])) and m.group(2) == rel
            )
            lines[at] = line
            event = f"refreshed attachment {rel} sha256:{had['sha256']} -> sha256:{sha}"
            had.update(sha256=sha, edited=edited)
        else:
            # one line per artefact, kept together directly under the item line
            at = b["line"]
            for i in range(b["line"], block_end(lines, b)):
                if ATTANY.match(lines[i]):
                    at = i + 1
            lines.insert(at, line)
            b["attachments"].append({"path": rel, "sha256": sha, "edited": edited})
            event = f"attached {rel} sha256:{sha}"
        lines.insert(block_end(lines, b), f"{ind}- log: {now()} {who} {event}")
        print(f"{file}:{b['line']}: {ident(b)} {event}")
    save(file, lines)
    return 0


def cmd_log(file, wanted, event, author, reason=None):
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    warn_lock(file, b, who)
    line = f"{sub_indent(lines, b)}- log: {now()} {who} {event}{because(reason)}"
    lines.insert(block_end(lines, b), line)
    save(file, lines)
    print(f"{file}:{b['line']}: {ident(b)} logged -> {line.strip()}")
    return 0


def mint_regression(file, lines, blocks, b, event, who, reason=None):
    """Reopening a closed defect opens `<parent>-<next>` and leaves the parent closed.

    The closure was proven when it was made, so retiring it would delete a true fact.
    A defect that broke again is a new fact about the same defect, and giving it its
    own item is what makes regressions countable.
    """
    rid = f"{b['prefix']}-{b['cat']}-{b['num']}"
    rid += f"-{b['code']}" if b["code"] else ""
    rid += f"-{next_regr(blocks, b)}"
    pad = sub_indent(lines, b)
    at = block_end(lines, b)
    # the parent names its regression, so its own history is complete
    lines.insert(at, f"{pad}- log: {now()} {who} regressed as {rid}")
    ev = f"regression of {ident(b)}" + (f": {event}" if event else "") + because(reason)
    lines[at + 1 : at + 1] = [
        f"{' ' * b['indent']}- [ ] `{rid}` {b['body']}",
        f"{pad}- log: {now()} {who} {ev}",
    ]
    save(file, lines)
    print(f"{file}:{at + 2}: [ ] {rid} ({ev})")
    return 0


def cmd_setstate(file, wanted, target, verb, event, author, evidence=None, reason=None):
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    warn_lock(file, b, who)
    if b["state"] == target:
        print(f"{file}:{b['line']}: {ident(b)} already [{target}]; no change")
        return 0
    if target == " " and b["state"].lower() == "x" and b["prefix"] == "DEF":
        return mint_regression(file, lines, blocks, b, event, who, reason)
    idx = b["line"] - 1
    lines[idx] = re.sub(r"\[[ xX-]\]", f"[{target}]", lines[idx], count=1)
    ev = f"{verb}: {event}" if event else verb
    if target in ("x", "-"):
        # nobody works on a finished item; the lock goes whatever its expiry, unlogged
        drop_line(lines, b, LOCKLINE)
    if target == "x":
        # nothing closes without a proof; the line is the proof, stored once
        set_line(lines, b, "evidence", evidence, EVIDLINE)
    else:
        # reopened or rejected means not done, so the proof no longer stands. The log
        # keeps it
        was = drop_line(lines, b, EVIDLINE)
        if was:
            ev += f"; evidence retired: {was}"
    ev += because(reason)
    lines.insert(block_end(lines, b), f"{sub_indent(lines, b)}- log: {now()} {who} {ev}")
    save(file, lines)
    print(f"{file}:{b['line']}: [{target}] {ident(b)} ({ev})")
    return 0


def cmd_remove(file, wanted, force, author=None):
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    wanted = norm_id(wanted, doc_prefix(file, blocks))
    b = find_id(blocks, wanted)
    wanted = ident(b)
    warn_lock(file, b, as_handle(author))
    # a criterion may cite a defect and back, so scan every tracking doc beside this one
    scanned = [(f, o) for f in resolve([str(pathlib.Path(file).parent)]) for o in parse(f)[0]]
    index = {ident(o): o for f, o in scanned if o["prefix"]}
    inbound = [
        (f, o, lineno)
        for f, o in scanned
        for k, rid, lineno in o["refs"]
        if resolve_ref(index, rid) == wanted
    ]
    if inbound and not force:
        for f, o, lineno in inbound:
            print(f"{f}:{lineno}: {ident(o)} still points at {wanted}", file=sys.stderr)
        raise SystemExit(f"{wanted} is referenced; close it as invalid, or pass --force")
    end = block_end(lines, b)
    del lines[b["line"] - 1 : end]
    save(file, lines)
    print(f"{file}: removed {wanted} ({end - b['line'] + 1} line(s))")
    return 0


# beside the tracker; the project-management guard hook reads it
HAND_EDITS = "pm-hand-edits.md"


def edit_token(file):
    """(token, content digest) of a tracker as it is now. Only pm-tools derives the
    token; the guard hook matches the digest `ack` logs beside it."""
    digest = hashlib.sha256(pathlib.Path(file).read_bytes()).hexdigest()
    name = pathlib.Path(file).name
    return hashlib.sha256(f"{name} {digest}".encode()).hexdigest()[:8], digest


def cmd_ack(file, token, author, reason):
    """Log why a hand edit of a tracker is needed. Without a token, print the one for
    the file as it is now; with it, check it and append the line the guard hook reads."""
    name = pathlib.Path(file).name
    if not any(fnmatch.fnmatch(name, g) for g in GLOBS):
        raise SystemExit(f"{file} is not a tracker (acc-crit*.md, defects*.md)")
    if not os.path.isfile(file):
        raise SystemExit(f"{file}: no such file")
    current, digest = edit_token(file)
    if not token:
        print(
            f"{file}: token {current} for the file as it is now; log why with: "
            f'pm-tools ack {file} --token {current} --author @xx --reason "<why>"'
        )
        return 0
    # a handle check only: ack exists for repairs, and the roster may sit in the part
    # of the file being repaired, where pm-tools cannot read it
    if not author:
        raise SystemExit("every entry is authored; pass --author @xx")
    who = author if author.startswith("@") else "@" + author
    if not HANDLE.fullmatch(who):
        raise SystemExit(f"bad handle {author!r}; use @ plus 2-4 letters, e.g. @kj")
    if token != current:
        raise SystemExit(
            f"--token {token} is not the token of {file} as it is now - "
            f"run pm-tools ack {file} for the current one"
        )
    if not reason:
        raise SystemExit("pass --reason: why pm-tools cannot make this change")
    log = pathlib.Path(file).parent / HAND_EDITS
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(f"- {now()} {who} {name} {token} sha256:{digest}: {reason}\n")
    print(f"{file}: hand edit acknowledged, logged in {log}; send the edit again")
    return 0


def cmd_lock(file, wanted, author, hours, until, note):
    """Write `- lock: <stamp> @xx [note]` on an open item. Never logged: the lock is a
    signal about the near future, not an event in the item's history."""
    if hours is not None and until:
        raise SystemExit("pass --hours or --until, not both")
    if until and not (STAMP.match(until) and _valid_stamp(until)):
        raise SystemExit(f"--until takes ISO 8601 UTC, YYYY-MM-DDTHH:MM:SSZ, got {until!r}")
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    if status_of(b) != "open":
        raise SystemExit(f"{ident(b)} is {status_of(b)}; only an open item can be locked")
    held = lock_active(b)
    if held and held["by"] != who:
        warn_transfer(b, held, "taking it over")
        note = note or f"taken over from {held['by']}"
    if not until:
        span = datetime.timedelta(hours=24 if hours is None else hours)
        until = (datetime.datetime.now(datetime.timezone.utc) + span).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    set_lock(lines, b, f"{until} {who}" + (f" {note}" if note else ""))
    what = "extended" if held and held["by"] == who else "locked"
    save(file, lines)
    print(f"{file}:{b['line']}: {ident(b)} {what} by {who} until {until}")
    return 0


def cmd_unlock(file, author, wanted, every, expired):
    """Remove lock lines - one item, every item, or only the expired ones. Never
    logged, never refused; another author's active lock is named once on the way out."""
    if sum(1 for x in (wanted, every, expired) if x) != 1:
        raise SystemExit("pass exactly one of --id, --all or --expired")
    who = need_author(file, author)
    gone = expire_locks(file)
    if expired:
        print(f"{file}: {gone} expired lock(s) cleared")
        return 0
    lines = load(file)
    blocks, _ = parse(file)
    if wanted:
        blocks = [find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))]
    cleared = 0
    for b in sorted((b for b in blocks if b["lock_n"]), key=lambda b: -b["line"]):
        if (k := lock_active(b)) and k["by"] != who:
            warn_transfer(b, k, "clearing it")
        while drop_line(lines, b, LOCKLINE) is not None:
            cleared += 1
    save(file, lines)
    print(f"{file}: {cleared} lock(s) cleared")
    return 0


# ---------------------------------------------------------------------- upgrade


def propose_code(name, taken):
    """A mnemonic, not an abbreviation: the first word whole when it is short enough to
    read as one (Launch -> LAUNCH), otherwise its first four letters (Authentication ->
    AUTH). Override with --code where a longer prefix spells the word - Frontend -> FRONT."""
    words = re.findall(r"[A-Za-z0-9]+", name) or ["GENERAL"]
    first, src = words[0].upper(), "".join(words).upper()
    cands = [first] if 3 <= len(first) <= 6 else []
    cands += [first[:4], first[:5], first[:3]]
    cands += [src[:i] for i in range(3, 7)]
    cands += [(first[:3] + ch) for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
    for c in cands:
        if 3 <= len(c) <= 6 and c not in taken:
            return c
    raise SystemExit(f"cannot propose a free code for '{name}'; pass --code")


def cmd_upgrade(file, overrides, apply, author):
    lines = load(file)
    blocks, sections = parse(file)
    prefix = doc_prefix(file, blocks)
    # a legacy file has no handles at all; the importer signs the imported history
    # rather than being asked to hand-edit every log line it inherited. A handle
    # that is not on the roster is a content problem: apply still runs, the
    # signature waits, and the hint carries the commands that finish the job
    stamp, hints = None, []
    if author:
        h = author if author.startswith("@") else "@" + author
        if not HANDLE.fullmatch(h):
            raise SystemExit(f"bad handle {author!r}; use @ plus 2-4 letters, e.g. @kj")
        if h in roster_of(file):
            stamp = h
        else:
            hints.append(
                f"{h} is not on the ## Authors roster; run: "
                f'pm-tools author {file} --handle {h} --name "Full Name", '
                f"then re-run: pm-tools upgrade {file} --author {h} --apply"
            )

    def as_log(ln):
        # a dated note counts as the log line this same rewrite turns it into,
        # so the unsigned-history hint fires on the first run, not the second
        dm = DATED.match(ln)
        if dm and not LOGLINE.match(ln):
            return f"{dm.group(1)}- log: {dm.group(2)}{dm.group(3)}"
        return ln

    bare = sum(
        1
        for _, ln in non_fenced(lines)
        if (m := LOGLINE.match(as_log(ln))) and not AUTHORED.match(m.group(3).strip())
    )
    plan, taken = [], {s["code"] for s in sections if s["code"]}
    if not roster_of(file):
        hints.append(
            "no ## Authors roster; run: "
            f'pm-tools author {file} --handle @xx --name "Full Name", '
            f"then re-run: pm-tools upgrade {file} --author @xx --apply"
        )
    if bare and not stamp:
        hints.append(
            f"{bare} log line(s) carry no @handle; run: "
            f"pm-tools upgrade {file} --author @xx --apply to sign the imported history"
        )

    codes = {}
    for s in sections:
        key = s["name"].strip().lower()
        if key == "contents":
            codes[id(s)] = None
            continue
        code = overrides.get(key, s["code"])
        if not code:
            code = propose_code(s["name"], taken)
            plan.append(f"line {s['line']}: category '{s['name']}' -> code `{code}`")
        codes[id(s)] = code
        taken.add(code)
        if not s["desc"]:
            hints.append(
                f"line {s['line']}: category '{s['name']}' has no description; run: "
                f'pm-tools describe {file} --category {code} --text "<one line>" --author @xx'
            )

    # numbers already carried by the doc win, new-style or legacy `DEF-N`; the rest
    # continue above the highest one, so no existing id is ever renumbered or reused
    todo = []
    for b in blocks:
        if b["indent"]:
            level = (
                f"--severity {'|'.join(SEVS)}"
                if prefix == "DEF"
                else f"--importance {'|'.join(IMPS)}"
            )
            hints.append(
                f"line {b['line']}: nested checklist item; file it as its own item with: "
                f'pm-tools add {file} --category <CODE> --code <CODE> --title "..." '
                f'--text "..." '
                f"{level} --author @xx, then delete the nested line"
            )
            continue
        if b["section"] is None or codes[id(b["section"])] is None:
            hints.append(
                f"line {b['line']}: item sits above any ## category heading; move it "
                f"under one, then re-run: pm-tools upgrade {file} --apply"
            )
            continue
        lg = LEGACY.match(b["body"])
        num = b["num"] if b["num"] is not None else (int(lg.group(2)) if lg else None)
        todo.append((b, codes[id(b["section"])], num))

    unproven = sum(1 for b, _, _ in todo if b["state"].lower() == "x" and not b["evidence"])
    if unproven:
        hints.append(
            f"{unproven} closed item(s) carry no evidence: line; run: "
            f'pm-tools edit {file} --id <ID> --evidence "<proof>" --author @xx '
            f"as each closure is verified"
        )

    used = {n for _, _, n in todo if n is not None}
    counter = max(used) + 1 if used else 1
    assign = {}
    for b, code, num in todo:
        if num is None:
            while counter in used:
                counter += 1
            num, used = counter, used | {counter}
            counter += 1
        lg = LEGACY.match(b["body"])
        regr = b["regr"] or (int(lg.group(3)) if lg and lg.group(3) else None)
        assign[b["line"]] = (code, num, regr, b["code"])
        old = ident(b) if b["prefix"] else (lg.group(0).split("`")[1] if lg else "(no id)")
        new = f"{prefix}-{code}-{num}"
        new += f"-{b['code']}" if b["code"] else ""
        new += f"-{regr}" if regr else ""
        if old != new:
            plan.append(f"line {b['line']}: {old} -> {new}")
        if prefix == "DEF" and not b["severity"]:
            odd = SEVWORD.match(b["plain"])
            why = f"carries an unmapped severity word {odd.group(1)!r}" if odd else "not triaged"
            hints.append(
                f"line {b['line']}: {new} {why}; run: "
                f"pm-tools edit {file} --id {new} --severity {'|'.join(SEVS)} --author @xx"
            )
        if prefix == "ACC" and not b["importance"]:
            hints.append(
                f"line {b['line']}: {new} not rated; run: "
                f"pm-tools edit {file} --id {new} --importance {'|'.join(IMPS)} --author @xx"
            )
        if not b["hint"]:
            want = HINT_FOR[prefix]
            hints.append(
                f"line {b['line']}: {new} has no {want}: line; run: "
                f'pm-tools edit {file} --id {new} --{want} "<one line>" --author @xx'
            )
        if not author_of(b) and not stamp:
            hints.append(
                f"line {b['line']}: {new} has no authored log; run: "
                f"pm-tools upgrade {file} --author @xx --apply"
            )

    out, drop_toc, converted, widened, retagged, renamed = [], False, 0, 0, 0, {}
    fenced = False
    for i, ln in enumerate(lines, start=1):
        # a code fence holds examples, never the item's own history
        if re.match(r"^\s*```", ln):
            fenced = not fenced
        if fenced or re.match(r"^\s*```", ln):
            out.append(ln)
            continue
        h = HEADING.match(ln)
        if h and len(h.group(1)) == 2:
            drop_toc = h.group(2).strip().lower() == "contents"
            if drop_toc:
                plan.append(f"line {i}: drop the ## Contents section (index is derived)")
                continue
            for s in sections:
                if s["line"] == i:
                    out.append(f"## {s['name']} `{codes[id(s)]}`")
                    break
            else:
                out.append(ln)
            continue
        if drop_toc:
            if h:
                drop_toc = False
            else:
                continue
        if i in assign:
            code, num, regr, item_code = assign[i]
            m = ITEM.match(ln)
            body = m.group(3)
            idm = IDTOK.match(body)
            if idm:
                body = idm.group("body")
            else:
                lg = LEGACY.match(body)
                if lg:
                    body = lg.group(4)
            bm = BOLD.search(body)
            lead, after = (body[: bm.end()], body[bm.end() :]) if bm else ("", body)
            rest = after.lstrip(" -")
            gap = after[: len(after) - len(rest)]
            sm = SEV.match(rest) if prefix == "DEF" else None
            if sm:
                # alias, case and delimiter all land on the form `add` writes
                was = sm.group(1).upper()
                canon = SEV_ALIAS.get(was, was)
                fixed = canon + "; " + rest[sm.end() :].lstrip(" ;:,")
                if fixed != rest:
                    rest = fixed
                    body = lead + gap + rest
                    key = was if was in SEV_ALIAS else sm.group(1)
                    renamed[key] = renamed.get(key, 0) + 1
            new_id = f"{prefix}-{code}-{num}"
            new_id += f"-{item_code}" if item_code else ""
            new_id += f"-{regr}" if regr else ""
            out.append(f"- [{m.group(2).lower()}] `{new_id}` {body}")
            continue
        tm = TAGLINE.match(ln)
        if tm and canon_tags(tm.group(2)) != tm.group(2).strip():
            ln = f"{tm.group(1)}- test-tags: {canon_tags(tm.group(2))}"
            retagged += 1
        dm = DATED.match(ln)
        if dm and not LOGLINE.match(ln):
            ln = f"{dm.group(1)}- log: {dm.group(2)}{dm.group(3)}"
            converted += 1
        lm = LOGLINE.match(ln)
        if lm and DATEONLY.match(lm.group(2)):
            # a legacy day has no time; midnight UTC is the honest widening
            ln = f"{lm.group(1)}- log: {lm.group(2)}T00:00:00Z{lm.group(3)}"
            widened += 1
            lm = LOGLINE.match(ln)
        if stamp and lm and not AUTHORED.match(lm.group(3).strip()):
            out.append(f"{lm.group(1)}- log: {lm.group(2)} {stamp}{lm.group(3)}")
            continue
        out.append(ln)

    if converted:
        plan.append(f"{converted} dated note(s) -> `- log: <stamp> ...`")
    if widened:
        plan.append(f"{widened} date-only stamp(s) -> ISO 8601 UTC at 00:00:00Z")
    if retagged:
        plan.append(f"{retagged} test-tags line(s) upper-cased")
    if renamed:
        plan.append(
            "severity renamed: "
            + ", ".join(
                f"{w} -> {SEV_ALIAS.get(w.upper(), w.upper())} x{n}"
                for w, n in sorted(renamed.items())
            )
        )
    if stamp and bare:
        plan.append(f"{bare} unauthored log line(s) signed {stamp}")

    for p in plan:
        print(p)
    for m in hints:
        print(f"HINT {m}", file=sys.stderr)
    if not apply:
        print(f"\ndry run: {len(plan)} change(s), {len(hints)} hint(s). Re-run with --apply")
        return 0
    if stamp and out != lines:
        # the record needs a handle on the roster; without one the hints say how to get it
        tracker_record(file, out, stamp, "upgraded")
    save(file, out)
    edited = sum(
        max(i2 - i1, j2 - j1)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            a=lines, b=out, autojunk=False
        ).get_opcodes()
        if tag != "equal"
    )
    print(
        f"\napplied {len(plan)} change(s) to {file}, {edited} line(s) edited; "
        f"{len(hints)} hint(s) remain. Run check next"
    )
    return 0


# -------------------------------------------------------------------- migration


def read_mapping(path):
    """`BASE-ID CODE` pairs, one per line, with the mapping line each came from.
    Blank lines and `#` comments are skipped; the base id is the id without its code
    or regression ordinal, as root_of reads it."""
    pairs = {}
    for n, ln in enumerate(load(path), start=1):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) != 2:
            raise SystemExit(f'{path}:{n}: expected "BASE-ID CODE", got {ln.strip()!r}')
        base, code = parts[0].upper(), norm_code(parts[1])
        if not BASEID.fullmatch(base):
            raise SystemExit(
                f"{path}:{n}: {parts[0]!r} is not a base id; write PREFIX-CAT-N "
                "without the code or the regression ordinal"
            )
        if base in pairs and pairs[base][0] != code:
            raise SystemExit(f"{path}:{n}: {base} is mapped twice with different codes")
        pairs[base] = (code, n)
    return pairs


def cmd_migrate_codes(file, mapping, author):
    """Append the code each mapping line names to that item's id, one log line per
    item changed. Re-running the same mapping writes nothing; the report names the
    items that carry no code and are not named by the mapping and the mapping ids
    that match no item, and the exit code is non-zero while either remains."""
    if not pathlib.Path(mapping).is_file():
        raise SystemExit(f"--map not found: {mapping}")
    pairs = read_mapping(mapping)
    expire_locks(file)
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    plan, conflicts, already = {}, [], 0
    for b in blocks:
        if b["indent"] or not b["prefix"]:
            continue
        hit = pairs.get(root_of(b))
        if hit is None:
            continue
        code = hit[0]
        if b["code"] == code:
            already += 1
            continue
        if b["code"]:
            conflicts.append(b)
            continue
        new = f"{root_of(b)}-{code}" + (f"-{b['regr']}" if b["regr"] else "")
        plan[b["line"]] = (new, code)
    roots = {root_of(b) for b in blocks if b["prefix"] and not b["indent"]}
    uncovered = [
        b
        for b in blocks
        if not b["indent"] and (not b["prefix"] or (b["code"] is None and root_of(b) not in pairs))
    ]
    missing = [(base, code, n) for base, (code, n) in pairs.items() if base not in roots]
    if plan:
        heads = {b["line"]: b for b in blocks if b["line"] in plan}
        # block_end is a 0-based index into lines; after 1-based line i is where it lands
        inserts = {block_end(lines, b): (b, plan[b["line"]][1]) for b in heads.values()}
        out = []
        for i, ln in enumerate(lines, start=1):
            b = heads.get(i)
            if b is not None:
                m = ITEM.match(ln)
                body = m.group(3)
                ln = f"{m.group(1)}- [{m.group(2)}] `{plan[i][0]}`{body[len(ident(b)) + 2 :]}"
            out.append(ln)
            at = inserts.get(i)
            if at is not None:
                b, code = at
                out.append(f"{sub_indent(lines, b)}- log: {now()} {who} coded {code}")
        tracker_record(
            file, out, who, f"coded {len(plan)} item(s) from {pathlib.Path(mapping).name}"
        )
        save(file, out)
        files = siblings(file)
        for f in files:
            expire_locks(f)
        for b in heads.values():
            rewrite_links(ident(b), plan[b["line"]][0], files)
    print(f"{file}: {len(plan)} item(s) coded, {already} already carried the code")
    for b in uncovered:
        if b["prefix"]:
            print(f"{file}:{b['line']}: {ident(b)} is not in the mapping", file=sys.stderr)
        elif b["bad_id"]:
            print(f"{file}:{b['line']}: id is malformed; run check", file=sys.stderr)
        else:
            print(f"{file}:{b['line']}: item has no id; run upgrade", file=sys.stderr)
    for b in conflicts:
        code = pairs[root_of(b)][0]
        print(
            f"{file}:{b['line']}: {ident(b)} already carries {b['code']}, "
            f"mapping says {code} - run rename-code",
            file=sys.stderr,
        )
    for base, code, n in missing:
        print(f"{mapping}:{n}: {base} is not in {file}", file=sys.stderr)
    return 1 if uncovered or conflicts or missing else 0


def rewrite_links(old, new, files):
    """Replace the full id `old` with `new` on every relation line that names it,
    across `files`. Returns the (file, line, kind) triples rewritten. A base-id
    reference is left alone: it still resolves to the renamed item."""
    touched = []
    for f in files:
        lines = load(f)
        edited = False
        for i, ln in enumerate(lines, start=1):
            m = RELLINE.match(ln)
            if not m:
                continue
            spans = [r.span() for r in IDREF.finditer(m.group(3)) if r.group(0) == old]
            if not spans:
                continue
            rest = m.group(3)
            for start, end in reversed(spans):
                rest = rest[:start] + new + rest[end:]
            lines[i - 1] = f"{m.group(1)}- {m.group(2)}: {rest}"
            touched.append((f, i, m.group(2)))
            edited = True
        if edited:
            save(f, lines)
    return touched


def cmd_rename_code(file, wanted, code, author):
    """Rename the code on an item and on every regression sharing its root, rewrite
    every relation line in the scanned trackers that names an old full id, and log the
    rename on each item. A regression shares its parent's code: renaming the parent
    alone would split the family."""
    code = norm_code(code)
    expire_locks(file)
    blocks = parse(file)[0]
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    who = need_author(file, author)
    if not b["code"]:
        raise SystemExit(f"{ident(b)} carries no code; run migrate-codes first")
    # the parent and its regressions are one family: same root, same code, top level
    family = [
        x
        for x in blocks
        if not x["indent"] and root_of(x) == root_of(b) and x["code"] == b["code"]
    ]
    if not any(x is b for x in family):
        family.insert(0, b)
    if b["code"] == code:
        # The rename logs are the durable record of the codes this family used to
        # carry, so a run that renamed the items and died before rewriting their
        # links is finished by the same command with the same code even though the
        # item already carries it.
        olds = [m.group(1) for txt in b["logs"] if (m := RENAMED.match(txt))]
        files = siblings(file)
        touched = []
        for x in family:
            current = ident(x)
            for old_code in olds:
                old = f"{root_of(x)}-{old_code}" + (f"-{x['regr']}" if x["regr"] else "")
                if old != current:
                    touched += [(old, current, *hit) for hit in rewrite_links(old, current, files)]
        for old, new, f, lineno, kind in touched:
            print(f"{f}:{lineno}: {kind}: {old} -> {new}")
        print(f"{file}: {ident(b)} already carries code {code}; no change")
        return 0
    renames = {}
    for x in family:
        new = f"{root_of(x)}-{code}" + (f"-{x['regr']}" if x["regr"] else "")
        renames[x["line"]] = (ident(x), new)
    where = link_index(siblings(file))
    for old, new in renames.values():
        if new in where:
            raise SystemExit(f"{new} already exists; pick another code")
    lines = load(file)
    stamp = now()
    for x in family:
        old, new = renames[x["line"]]
        warn_lock(file, x, who)
        m = ITEM.match(lines[x["line"] - 1])
        body = m.group(3)
        lines[x["line"] - 1] = f"{m.group(1)}- [{m.group(2)}] `{new}`{body[len(old) + 2 :]}"
    logs = [
        (
            block_end(lines, x),
            f'{sub_indent(lines, x)}- log: {stamp} {who} renamed code "{b["code"]}" -> "{code}"',
        )
        for x in family
    ]
    for at, text in sorted(logs, reverse=True):
        lines.insert(at, text)
    save(file, lines)
    files = siblings(file)
    for f in files:
        expire_locks(f)
    touched = []
    for old, new in renames.values():
        touched += [(old, new, *hit) for hit in rewrite_links(old, new, files)]
    for x in family:
        old, new = renames[x["line"]]
        print(f"{file}:{x['line']}: {old} renamed to {new}")
    for old, new, f, lineno, kind in touched:
        print(f"{f}:{lineno}: {kind}: {old} -> {new}")
    return 0


def left_alone(m):
    """Why a rename leaves an IDREF match as written, or None: an attachment line holds
    an artefact's path, and an id inside a file path (the rule coded_ref reads) names a
    file the rename does not move."""
    s, at = m.string, m.start()
    if ATTANY.match(s):
        return "an attachment line"
    if RELLINE.match(s):
        return None  # parse reads every id on a relation line as a link
    if s[at - 1 : at] in ("/", "\\") or PATHTAIL.match(s, m.end()):
        return "a file path"
    return None


def rename_plan(file, old, new, name, who):
    """Validate a category rename and compute, writing nothing, the new content of every
    store file it changes. Returns ({file: (lines, renamed items, mentions rewritten)},
    [(file, line, id, why)] for each mention left as written). A refusal raises."""
    if not re.fullmatch(r"[A-Z]{2,6}", new):
        raise SystemExit(f"category code {new!r} must be 2-6 uppercase letters")
    if new == old:
        raise SystemExit(f"--to {new} is the code the category already carries")
    store = siblings(file)
    parsed = {f: (load(f), *parse(f)) for f in store}
    prefix = doc_prefix(file, parsed[file][1])
    same = [f for f in store if doc_prefix(f, parsed[f][1]) == prefix]
    renamed = {
        f: [b for b in parsed[f][1] if b["prefix"] == prefix and b["cat"] == old] for f in same
    }
    event = f'renamed category "{old}" -> "{new}"'
    record = re.compile(rf"- log: \S+ @\S+ {re.escape(event)}(,|\s*$)")
    # a rerun finishes a rename a git merge left half done: no heading carries OLD any
    # more, the other branch's items still do, and FILE's NEW heading holds the record
    rerun = (
        all(s["code"] != old for f in same for s in parsed[f][2])
        and any(renamed.values())
        and any(
            s["code"] == new and any(record.match(ln) for _, ln in s["log_lines"])
            for s in parsed[file][2]
        )
    )
    if not rerun and all(s["code"] != old for s in parsed[file][2]):
        have = ", ".join(s["code"] or "?" for s in parsed[file][2]) or "(none)"
        raise SystemExit(f"unknown category code {old}; have: {have}")
    stale = []  # on a rerun, the earlier run's items, which the other branch names by OLD
    if rerun:
        name = None  # the earlier run renamed the headings
        stale = [
            b for f in store for b in parsed[f][1] if b["prefix"] == prefix and b["cat"] == new
        ]
        idx = {ident(b): b for b in stale}
        for f, items in renamed.items():
            for b in items:
                moved = dict(b, cat=new)
                nid = ident(moved)
                hit = nid if nid in idx or b["regr"] else resolve_ref(idx, root_of(moved))
                if hit in idx:
                    raise SystemExit(
                        f"{f}:{b['line']}: {ident(b)} would become {nid}, which collides "
                        f"with {hit}; fix it before the rerun"
                    )
    else:
        for f in same:
            if any(s["code"] == new for s in parsed[f][2]):
                raise SystemExit(f"{f}: {new} is already a category code; pick another")
        for f in store:
            for b in parsed[f][1]:
                if b["prefix"] == prefix and b["cat"] == new:
                    raise SystemExit(f"{f}:{b['line']}: {ident(b)} already exists; pick another")
    roots, names = {}, set()  # names: the full, base and base-plus-ordinal ids of the items
    for b in [dict(b, cat=old) for b in stale] + [b for items in renamed.values() for b in items]:
        names |= {ident(b), root_of(b)} | ({f"{root_of(b)}-{b['regr']}"} if b["regr"] else set())
    for f, items in renamed.items():
        for b in items:
            if b["regr"]:
                continue
            prev = roots.setdefault(root_of(b), (f, b["line"], ident(b)))
            if prev[2] != ident(b):
                raise SystemExit(
                    f"duplicate base id {root_of(b)}: roots {prev[2]} ({prev[0]}:{prev[1]}) "
                    f"and {ident(b)} ({f}:{b['line']}); fix it before the rename"
                )
    wide = f'finished renaming category "{old}" -> "{new}"' if rerun else event
    stamp = now()
    plan, kept = {}, []
    for f in store:
        lines, _, sections = parsed[f]
        mine = renamed.get(f, [])
        heads = [s for s in sections if f in renamed and s["code"] == old]
        for s in heads:
            lines[s["line"] - 1] = f"## {name or s['name']} `{new}`"
        if rerun and mine:
            heads = [s for s in sections if s["code"] == new]  # they get the finishing record
        hits = 0
        for i, ln in enumerate(lines):
            spans = [
                m.span("cat") for m in IDREF.finditer(ln) if m[0] in names and not left_alone(m)
            ]
            for a, z in reversed(spans):
                ln = ln[:a] + new + ln[z:]
            lines[i], hits = ln, hits + len(spans)
        mentions = hits - len(mine)  # each renamed item's own id is one of the hits
        if mine or heads or mentions:
            # bottom up, so each insert leaves the positions above it valid. On a tie the
            # heading's record goes first: it lands below the heading, the item log above
            ops = [(block_end(lines, b), 0, b) for b in mine]
            ops += [(s["line"] - 1, 1, s) for s in heads]
            for at, head, x in sorted(ops, key=lambda op: op[:2], reverse=True):
                if not head:
                    lines.insert(at, f"{sub_indent(lines, x)}- log: {stamp} {who} {event}")
                    continue
                renamed_to = (
                    f', name "{x["name"]}" -> "{name}"' if name and name != x["name"] else ""
                )
                category_record(f, lines, at, who, wide + renamed_to)
            count = f"{len(mine)} item(s)" if mine or heads else f"{mentions} mention(s) rewritten"
            tracker_record(f, lines, who, f"{wide}, {count}")
            plan[f] = (lines, mine, mentions)
        kept += [
            (f, n, m[0], why)
            for n, ln in enumerate(lines, start=1)
            for m in IDREF.finditer(ln)
            if m[0] in names and (why := left_alone(m))
        ]
    return plan, kept


def cmd_rename_category(file, old, new, name, author):
    """Rename a category code across the store: the `##` headings and the item ids with
    FILE's prefix and code OLD in every tracker of that prefix, and every mention of
    those ids in every tracker beside FILE. Every check runs before the first write."""
    who = need_author(file, author)
    old = old.upper()
    for f in rename_plan(file, old, new, name, who)[0]:
        expire_locks(f)
    plan, kept = rename_plan(file, old, new, name, who)  # again, past the dropped locks
    for f, (_, mine, _) in plan.items():
        for b in mine:
            warn_lock(f, b, who)
    for f, (lines, _, _) in plan.items():
        save(f, lines)
    for f, (_, mine, mentions) in plan.items():
        at = link_index([f])
        for b in mine:
            nid = ident(dict(b, cat=new))
            print(f"{f}:{at[nid]['line']}: {ident(b)} -> {nid}")
        print(f"{f}: {mentions} mention(s) rewritten")
    for f, n, rid, why in kept:
        print(f"{f}:{n}: {rid} left as written in {why}", file=sys.stderr)
    return 0


# -------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    ap = argparse.ArgumentParser(
        prog="pm-tools", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", metavar="COMMAND")

    def add_filters(sp, on_report):
        whole = " - narrows the whole report" if on_report else ""
        sp.add_argument(
            "--category",
            help="one category code"
            + whole
            + ("; also prints its notes and category log" if on_report else ""),
        )
        sp.add_argument(
            "--code",
            type=str.upper,
            metavar="CODE",
            help="one item code, e.g. PARSER" + whole,
        )
        sp.add_argument(
            "--severity",
            type=str.upper,
            choices=SEVS,
            help="one level, defect documents only" + whole,
        )
        sp.add_argument(
            "--importance",
            type=str.upper,
            choices=IMPS,
            help="one level, criteria documents only" + whole,
        )
        sp.add_argument(
            "--status",
            choices=("open", "closed", "rejected", "all"),
            help="which items ITEMS lists; open by default"
            if on_report
            else "one status; every item by default",
        )
        sp.add_argument("--author", metavar="@xx", help="items filed by this handle" + whole)
        sp.add_argument("--tag", help="items carrying this test tag" + whole)
        sp.add_argument(
            "--regressions", action="store_true", help="only the -N regression items" + whole
        )
        sp.add_argument(
            "--grep",
            metavar="PATTERN",
            help="case-insensitive regex over title, body, evidence and log lines" + whole,
        )
        sp.add_argument(
            "--blocked",
            action="store_true",
            help="items with a blocked-by target that is still open" + whole,
        )
        sp.add_argument(
            "--related-to",
            dest="related_to",
            metavar="ID",
            help="items linked to ID either way, by any relation line" + whole,
        )
        sp.add_argument(
            "--locked", action="store_true", help="items carrying an active lock" + whole
        )
        sp.add_argument(
            "--locked-by",
            dest="locked_by",
            metavar="@xx",
            help="items whose active lock is held by this handle" + whole,
        )
        sp.add_argument(
            "--dates",
            choices=("filed", "closed", "updated"),
            default="filed",
            help="which log stamp --since/--until read; filed by default",
        )
        sp.add_argument("--since", metavar="YYYY-MM-DD", help="on or after, inclusive")
        sp.add_argument("--until", metavar="YYYY-MM-DD", help="on or before, inclusive")

    queries = ("report", "list", "pivot", "search", "coverage", "list-categories", "refs", "check")
    for name in queries:
        sp = sub.add_parser(name)
        sp.add_argument("paths", nargs="*")
        if name == "search":
            sp.add_argument(
                "query", metavar="QUERY", help="what to look for; quote a multi-word query"
            )
        if name in ("report", "list", "pivot", "search", "coverage"):
            add_filters(sp, name == "report")
        if name != "check":
            sp.add_argument("--json", action="store_true", help="the same facts as JSON")
        if name == "report":
            sp.add_argument(
                "--detail",
                action="store_true",
                help="one readable block per item instead of the table",
            )
            sp.add_argument(
                "--plain",
                action="store_true",
                help="the grids and the queue without the icons or the categories table",
            )
            sp.add_argument(
                "--summary",
                action="store_true",
                help="stop at the SUMMARY grid; list no items. Implies --plain",
            )
        if name == "list":
            sp.add_argument(
                "--columns", metavar="F,F,..", help="the table's columns, in order; see FIELDS"
            )
            sp.add_argument(
                "--sort",
                metavar="F,-F,..",
                help="sort fields; a `-` prefix descends, written --sort=-age so the "
                "shell does not read it as a flag. severity, importance and status are "
                "ranked, not alphabetical - ascending is worst first and open first, so "
                "--sort=-severity lists MINOR first. Fix order by default - open, worst, "
                "oldest",
            )
        if name == "pivot":
            sp.add_argument(
                "--rows",
                required=True,
                type=str.lower,
                help="the field down; a ranked or banded field keeps its own order - "
                "severity and importance worst first, status open first, age by band",
            )
            sp.add_argument("--cols", type=str.lower, help="the field across; one column without")
            sp.add_argument(
                "--values",
                choices=("count", "ids"),
                default="count",
                help="what fills a cell; count by default",
            )
        if name == "search":
            sp.add_argument(
                "--top",
                type=int,
                default=10,
                metavar="N",
                help="how many items to list; 10 by default",
            )
        if name == "refs":
            sp.add_argument("--id", required=True)
        if name == "check":
            sp.add_argument("--strict", action="store_true", help="treat warnings as failures")

    sa = sub.add_parser("add")
    sa.add_argument("file")
    sa.add_argument("--category", required=True, help="category CODE, e.g. AUTH")
    sa.add_argument(
        "--code",
        required=True,
        type=str.upper,
        metavar="CODE",
        help="the item's code, e.g. PARSER; one or two hyphen-separated segments",
    )
    sa.add_argument("--title", type=oneline, required=True)
    sa.add_argument("--text", type=oneline, required=True)
    sa.add_argument("--name", type=oneline, help="category name, needed only when the code is new")
    sa.add_argument(
        "--description", type=oneline, help="category description, when the code is new"
    )
    sa.add_argument(
        "--severity",
        type=str.upper,
        choices=SEVS,
        help="mandatory on a defect, refused on a criterion",
    )
    sa.add_argument(
        "--importance",
        type=str.upper,
        choices=IMPS,
        help="mandatory on a criterion, refused on a defect",
    )
    sa.add_argument("--repro", type=oneline, help="one line saying how to reproduce, defects only")
    sa.add_argument("--test", type=oneline, help="one line saying how to test, criteria only")
    sa.add_argument("--mechanism", type=oneline, help="how it is meant to work, criteria only")
    sa.add_argument(
        "--root-cause", type=oneline, dest="root_cause", help="why it happens, defects only"
    )
    sa.add_argument(
        "--author",
        required=True,
        metavar="@xx",
        help="handle of the person filing this, must be on the roster",
    )
    sa.add_argument(
        "--test-tags",
        type=oneline,
        dest="tags",
        help='which tests cover it, e.g. "unit, functional"',
    )
    sa.add_argument(
        "--reason",
        type=oneline,
        help="why; needed for a free-text argument over 50 words, kept on the log line",
    )

    se = sub.add_parser("edit")
    se.add_argument("file")
    se.add_argument("--id", required=True)
    se.add_argument("--title", type=oneline)
    se.add_argument("--text", type=oneline)
    se.add_argument("--severity", type=str.upper, choices=SEVS)
    se.add_argument("--importance", type=str.upper, choices=IMPS)
    se.add_argument("--repro", type=oneline)
    se.add_argument("--test", type=oneline)
    se.add_argument("--test-tags", type=oneline, dest="tags")
    se.add_argument("--evidence", type=oneline, help="one line proving the item is done")
    se.add_argument("--author", required=True, metavar="@xx")
    se.add_argument(
        "--reason",
        type=oneline,
        help="why; needed for a free-text argument over 50 words, kept on the log line",
    )

    sm = sub.add_parser("amend")
    sm.add_argument("file")
    sm.add_argument("--id", required=True)
    sm.add_argument("--title", type=oneline)
    sm.add_argument("--text", type=oneline)
    sm.add_argument("--author", required=True, metavar="@xx")
    sm.add_argument(
        "--reason",
        type=oneline,
        help="why; needed for a free-text argument over 50 words, kept on the log line",
    )

    sh = sub.add_parser("author")
    sh.add_argument("file")
    sh.add_argument("--handle", required=True, metavar="@xx")
    sh.add_argument("--name", type=oneline, required=True)

    sd = sub.add_parser("describe")
    sd.add_argument("file")
    sd.add_argument("--category", required=True)
    sd.add_argument("--author", required=True, metavar="@xx", help="signs the category record")
    sdw = sd.add_mutually_exclusive_group(required=True)
    sdw.add_argument("--text", type=oneline, help="the description, one line; with --note, note N")
    sdw.add_argument(
        "--text-file",
        dest="block",
        metavar="F",
        help="the whole prose block under the heading; - reads stdin",
    )
    sdw.add_argument(
        "--append",
        type=oneline,
        metavar="TEXT",
        help="add TEXT as the last note, after the last prose line",
    )
    sdw.add_argument("--remove", action="store_true", help="with --note, remove note N")
    sd.add_argument(
        "--note",
        type=int,
        metavar="N",
        help="note N, the Nth non-blank prose line after the description; blank, fenced "
        "and log lines are not counted",
    )

    sr = sub.add_parser("relate")
    sr.add_argument("file")
    sr.add_argument("--id", required=True)
    sr.add_argument("--related", type=oneline)
    sr.add_argument("--blocked-by", dest="blocked", type=oneline)
    sr.add_argument(
        "--overrides", type=oneline, help="this item overrides ID; both items get a line"
    )
    sr.add_argument(
        "--overridden-by",
        dest="overridden",
        type=oneline,
        help="ID overrides this item; both items get a line",
    )
    sr.add_argument(
        "--author",
        metavar="@xx",
        help="your handle; keeps your own lock silent, and signs the log line when "
        "an older link is removed to break a cycle",
    )

    su = sub.add_parser("unrelate")
    su.add_argument("file")
    su.add_argument("--id", required=True)
    su.add_argument("--related")
    su.add_argument("--blocked-by", dest="blocked")
    su.add_argument("--overrides", help="removed from both items")
    su.add_argument("--overridden-by", dest="overridden", help="removed from both items")
    su.add_argument("--author", required=True, metavar="@xx", help="signs the log line")
    su.add_argument("--event", type=oneline, help="why, kept on the log line")

    st = sub.add_parser("attach")
    st.add_argument("file")
    st.add_argument("--id", required=True)
    st.add_argument(
        "--path",
        action="append",
        required=True,
        metavar="P",
        help="an artefact to attach; repeat for several",
    )
    st.add_argument("--author", required=True, metavar="@xx")

    for name in ("log", "close", "reject", "reopen"):
        sp = sub.add_parser(name)
        sp.add_argument("file")
        sp.add_argument("--id", required=True)
        sp.add_argument("--author", required=True, metavar="@xx")
        sp.add_argument("--event", type=oneline, required=(name in ("log", "reject")))
        sp.add_argument(
            "--reason",
            type=oneline,
            help="why; needed for a free-text argument over 50 words, kept on the log line",
        )
        if name == "close":
            sp.add_argument(
                "--evidence",
                type=oneline,
                required=True,
                help="one line proving it is done - the test that passes, the run, the commit",
            )

    for name in ("mechanism", "root-cause"):
        sp = sub.add_parser(name)
        sp.add_argument("file")
        sp.add_argument("--id", required=True)
        sp.add_argument("--text", type=oneline, required=True, help="the explanation, one line")
        sp.add_argument("--author", required=True, metavar="@xx")
        sp.add_argument(
            "--update",
            action="store_true",
            help="rewrite the newest record instead of writing a new one above it",
        )
        sp.add_argument(
            "--reason",
            type=oneline,
            help="why; needed for a free-text argument over 50 words, kept on the log line",
        )

    sx = sub.add_parser("remove")
    sx.add_argument("file")
    sx.add_argument("--id", required=True)
    sx.add_argument("--force", action="store_true")
    sx.add_argument("--author", metavar="@xx", help="your handle; keeps your own lock silent")

    sl = sub.add_parser("lock")
    sl.add_argument("file")
    sl.add_argument("--id", required=True)
    sl.add_argument("--author", required=True, metavar="@xx", help="who is working on it")
    sl.add_argument("--hours", type=float, metavar="N", help="how long from now; 24 by default")
    sl.add_argument("--until", metavar="STAMP", help="the expiry as ISO 8601 UTC instead")
    sl.add_argument("--note", type=oneline, help="what is being done, one line")

    sn = sub.add_parser("unlock")
    sn.add_argument("file")
    sn.add_argument("--author", required=True, metavar="@xx")
    sn.add_argument("--id", help="clear this item's lock")
    sn.add_argument("--all", action="store_true", help="clear every lock in the file")
    sn.add_argument("--expired", action="store_true", help="clear only the expired locks")

    sk = sub.add_parser("ack")
    sk.add_argument("file")
    sk.add_argument("--token", help="the token `pm-tools ack FILE` printed; omit it to print one")
    sk.add_argument("--author", metavar="@xx")
    sk.add_argument("--reason", type=oneline, help="why pm-tools cannot make this change")

    su = sub.add_parser("upgrade")
    su.add_argument("file")
    su.add_argument("--code", action="append", default=[], metavar='"Section=CODE"')
    su.add_argument(
        "--author", metavar="@xx", help="sign every unauthored log line in the legacy file"
    )
    su.add_argument("--apply", action="store_true")

    smc = sub.add_parser("migrate-codes")
    smc.add_argument("file")
    smc.add_argument(
        "--map", required=True, metavar="MAPPING", help='a file of "BASE-ID CODE" lines'
    )
    smc.add_argument("--author", required=True, metavar="@xx")

    src = sub.add_parser("rename-code")
    src.add_argument("file")
    src.add_argument("--id", required=True)
    src.add_argument("--code", required=True, metavar="NEW")
    src.add_argument("--author", required=True, metavar="@xx")

    srn = sub.add_parser("rename-category")
    srn.add_argument("file")
    srn.add_argument("--category", required=True, metavar="OLD", help="the code to rename")
    srn.add_argument(
        "--to", required=True, metavar="NEW", help="the new code, 2-6 uppercase letters"
    )
    srn.add_argument("--name", type=oneline, help="a new name for every renamed heading")
    srn.add_argument("--author", required=True, metavar="@xx", help="signs every log line written")

    a, extra = ap.parse_known_args(argv[1:])
    if extra and (a.cmd != "search" or any(x.startswith("-") for x in extra)):
        ap.error("unrecognized arguments: " + " ".join(extra))
    if extra:
        # `search docs --top 3 splash`: argparse stops collecting positionals at the
        # first option, so the words after it arrive here; the last one is the query
        words = [*a.paths, a.query, *extra]
        a.paths, a.query = words[:-1], words[-1]
    if not a.cmd:
        ap.print_help()
        return 0

    if a.cmd in queries:
        if a.cmd == "search":
            if a.top < 1:
                raise SystemExit("--top takes a positive count")
            # argparse hands `paths` every positional but the last, so an unquoted
            # `search docs token race` arrives as paths=[docs, token], query=race
            for p in a.paths:
                if not pathlib.Path(p).exists():
                    raise SystemExit(
                        f"search: no such path {p!r}; a multi-word query is one argument - "
                        'search docs "token race"'
                    )
            if not a.paths and pathlib.Path(a.query).exists():
                # `search docs` with the query forgotten; with a path given, a
                # query word that also names a cwd entry is just a query
                raise SystemExit(f"search: {a.query!r} is a path; the last argument is the QUERY")
        files = resolve(a.paths)
        if not files:
            print("no acc-crit*.md or defects*.md found", file=sys.stderr)
            return 2
        if a.cmd in ("report", "list", "pivot", "search", "coverage"):
            for v in (a.since, a.until):
                if v and not DATEONLY.match(v):
                    raise SystemExit(f"--since/--until take YYYY-MM-DD, got {v!r}")
            if a.author and not HANDLE.fullmatch(a.author):
                raise SystemExit(f"--author takes a handle like @kj, got {a.author!r}")
            if a.locked_by and not HANDLE.fullmatch(a.locked_by):
                raise SystemExit(f"--locked-by takes a handle like @kj, got {a.locked_by!r}")
            if a.grep:
                try:
                    re.compile(a.grep, re.I)
                except re.error as err:
                    raise SystemExit(f"--grep: bad pattern {a.grep!r}: {err}")
            rid = a.related_to.strip().upper() if a.related_to else None
            if rid and not IDREF.fullmatch(rid):
                raise SystemExit(f"--related-to takes an id like DEF-LNCH-3, got {a.related_to!r}")
            fl = dict(
                category=a.category.upper() if a.category else None,
                code=a.code.upper() if a.code else None,
                severity=a.severity,
                importance=a.importance,
                status=a.status,
                author=a.author,
                tag=a.tag.strip().upper() if a.tag else None,
                regr=a.regressions,
                grep=a.grep,
                blocked=a.blocked,
                related_to=rid,
                locked=a.locked,
                locked_by=a.locked_by,
                dates=a.dates,
                since=a.since,
                until=a.until,
            )
        if a.cmd == "report":
            return cmd_report(files, fl, a.detail, a.plain, a.summary, a.json)
        if a.cmd == "list":
            cols = parse_fields(a.columns, "--columns")
            return cmd_list(files, fl, cols, parse_fields(a.sort, "--sort"), a.json)
        if a.cmd == "pivot":
            rows_f = parse_fields(a.rows, "--rows")[0]
            cols_f = (parse_fields(a.cols, "--cols") or [None])[0]
            return cmd_pivot(files, rows_f, cols_f, a.values, fl, a.json)
        if a.cmd == "search":
            return cmd_search(files, fl, a.query, a.top, a.json)
        if a.cmd == "coverage":
            return cmd_coverage(files, fl, a.json)
        if a.cmd == "list-categories":
            return cmd_list_categories(files, a.json)
        if a.cmd == "refs":
            rid = a.id.strip().upper()
            if not IDREF.fullmatch(rid):
                raise SystemExit(f"--id takes an id like DEF-LNCH-3, got {a.id!r}")
            return cmd_refs(files, rid, a.json)
        return cmd_check(files, a.strict)

    gate_writeups(sub.choices[a.cmd], a)
    if a.cmd == "add":
        return cmd_add(
            a.file,
            a.category,
            a.name,
            a.description,
            a.title,
            a.text,
            a.severity,
            a.importance,
            a.repro,
            a.test,
            a.tags,
            a.author,
            a.code,
            a.mechanism,
            a.root_cause,
            a.reason,
        )
    if a.cmd == "edit":
        return cmd_edit(
            a.file,
            a.id,
            a.title,
            a.text,
            a.severity,
            a.importance,
            a.repro,
            a.test,
            a.tags,
            a.author,
            a.evidence,
            a.reason,
        )
    if a.cmd == "amend":
        return cmd_amend(a.file, a.id, a.title, a.text, a.author, a.reason)
    if a.cmd in ("mechanism", "root-cause"):
        return cmd_cause(a.file, a.id, a.cmd, a.text, a.author, a.update, a.reason)
    if a.cmd == "author":
        return cmd_author(a.file, a.handle, a.name)
    if a.cmd == "describe":
        block = None
        if a.block == "-":
            block = sys.stdin.read()
        elif a.block is not None:
            if not pathlib.Path(a.block).is_file():
                raise SystemExit(f"--text-file not found: {a.block}")
            block = pathlib.Path(a.block).read_text(encoding="utf-8")
        return cmd_describe(
            a.file, a.category, a.text, a.author, block, a.append, a.note, a.remove
        )
    if a.cmd == "relate":
        return cmd_relate(a.file, a.id, a.related, a.blocked, a.overrides, a.overridden, a.author)
    if a.cmd == "unrelate":
        return cmd_unrelate(
            a.file, a.id, a.related, a.blocked, a.overrides, a.overridden, a.author, a.event
        )
    if a.cmd == "attach":
        return cmd_attach(a.file, a.id, a.path, a.author)
    if a.cmd == "log":
        return cmd_log(a.file, a.id, a.event, a.author, a.reason)
    if a.cmd == "close":
        return cmd_setstate(a.file, a.id, "x", "closed", a.event, a.author, a.evidence, a.reason)
    if a.cmd == "reject":
        return cmd_setstate(a.file, a.id, "-", "rejected", a.event, a.author, reason=a.reason)
    if a.cmd == "reopen":
        return cmd_setstate(a.file, a.id, " ", "reopened", a.event, a.author, reason=a.reason)
    if a.cmd == "remove":
        return cmd_remove(a.file, a.id, a.force, a.author)
    if a.cmd == "lock":
        return cmd_lock(a.file, a.id, a.author, a.hours, a.until, a.note)
    if a.cmd == "unlock":
        return cmd_unlock(a.file, a.author, a.id, a.all, a.expired)
    if a.cmd == "ack":
        return cmd_ack(a.file, a.token, a.author, a.reason)
    if a.cmd == "upgrade":
        ov = {}
        for spec in a.code:
            k, _, v = spec.partition("=")
            if not v:
                raise SystemExit(f"--code needs Section=CODE, got {spec!r}")
            ov[k.strip().lower()] = v.strip().upper()
        return cmd_upgrade(a.file, ov, a.apply, a.author)
    if a.cmd == "migrate-codes":
        return cmd_migrate_codes(a.file, a.map, a.author)
    if a.cmd == "rename-code":
        return cmd_rename_code(a.file, a.id, a.code, a.author)
    if a.cmd == "rename-category":
        return cmd_rename_category(a.file, a.category, a.to, a.name, a.author)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
