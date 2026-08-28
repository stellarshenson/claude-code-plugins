#!/usr/bin/env python3
"""pm-tools - query, lint, report and edit project-management tracking docs.

The markdown file is the entire store. Nothing is recorded twice: the next id is the
highest id already in the file plus one, the category index is computed by
list-categories, backlinks are computed by refs. No counter file, no index, no TOC.

  docs/acc-crit*.md   acceptance criteria, ids ACC-<CAT>-<N>, hint line `- test:`
  docs/defects*.md    defects,             ids DEF-<CAT>-<N>, hint line `- repro:`

A defect that is fixed and breaks again keeps a derived id: reopening DEF-LNCH-3
opens DEF-LNCH-3-1, then -2, then -3. The parent stays closed with its evidence -
it really was proven - so the ordinals count how often that defect has regressed.

Both disciplines also carry `- test-tags: UNIT, FUNCTIONAL` - which kinds of test
cover the item (UNIT, INTEGRATION, FUNCTIONAL, E2E, MANUAL, or any word; written
upper-case, read in any case; an item with none sits in the NO-TEST bucket) - and
`- evidence: <one line>`, the proof it is actually done. `close` demands the
evidence and writes that line; on a criterion `reopen` retires it, on a closed
defect it mints the regression instead and the closure keeps its proof. check
fails on a relation to an id that is not in the scanned files and on a blocked-by
cycle, and warns when an open item is blocked by one that is closed or rejected; scan
the directory, not one file, so cross-file links resolve.

Three states: `- [ ]` open, `- [x]` closed, `- [-]` rejected (reason in the log line).
Log lines read `- log: 2026-08-27T15:59:12Z @kj <event>` - ISO 8601 UTC, then the author.

Query - every table is markdown, paste-ready; --json gives the same facts as data:
  report [paths] [FILTERS] [--detail] [--plain] [--summary] [--json]
         ITEMS lists open work only unless --status says otherwise, worst level first.
         The SUMMARY grid is plain counts: `| Category | Open | CRITICAL | MAJOR |
         MEDIUM | MINOR | Fixed | Rejected |` on defects, `| Category | Open |
         CRITICAL | HIGH | MEDIUM | LOW | Done | Rejected |` on criteria, each with
         a Total row; the level columns count OPEN items only, and UNTRIAGED/UNRATED
         appears only when an open item lacks a level. Every filter narrows the whole
         report except --status, which narrows ITEMS alone. --plain prints the grids
         and nothing else; --summary stops at the SUMMARY grid, listing no items.
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
         file - BM25 over id, title, body, evidence and log lines, id and title
         weighted 3x; a typo or a stem still hits. Quote a multi-word QUERY. FILTERS
         narrow the candidates first: --grep is the exact filter, search is the ranking
  list-categories [paths] [--json]                 code, name, open, closed, rejected
  refs [paths] --id ID [--json]                    what points at ID, what ID points at,
                                                   and the chain of what blocks it
  check [paths] [--strict]                         conformity gate

FILTERS, the same on report, list, pivot, search and coverage:
  --category CODE  --severity S  --importance I  --status open|closed|rejected|all
  --author @xx  --tag T (any case)  --regressions  --dates filed|closed|updated
  --since DATE  --until DATE
  --grep PATTERN   case-insensitive regex over title, body, evidence and log lines
  --blocked        items with at least one blocked-by target that is still open
  --related-to ID  items linked to ID in either direction, related or blocked-by
  A mention of an id in a log line is prose; only a related:/blocked-by: line is a
  link. --grep and search find mentions, refs, --related-to and --blocked read links.

FIELDS, for --columns, --sort, --rows and --cols:
  id title body category severity importance status author filed closed updated
  age tags evidence hint regr root logs related blockers
  tags, related and blockers pivot an item into every value it carries; filed/closed/
  updated pivot by month, age by band (<7d, 7-30d, 31-90d, >90d).

Edit (one file):
  add    FILE --category CODE --title T --text D [--name NAME] [--description D]
                    --severity S|--importance I [--repro R|--test T]
                    [--test-tags "UNIT, FUNCTIONAL"]
  edit   FILE --id ID [--title T] [--text D] [--severity S] [--importance I]
                      [--repro R|--test T] [--test-tags TAGS] [--evidence E]

--severity is CRITICAL|MAJOR|MEDIUM|MINOR, mandatory on every defect and refused on
a criterion. An untriaged defect is a check error. Foreign vocabularies (P0-P4, S1-S4,
SEV1-4, BLOCKER, URGENT, HIGH, NORMAL, LOW, TRIVIAL ...) are recognised and renamed by
upgrade; anything it cannot map is named and left for a human.
--importance is CRITICAL|HIGH|MEDIUM|LOW, mandatory on every criterion and refused on
a defect. An unrated criterion is a check error. Importance is read only on ACC items
and severity only on DEF items, so a criterion body opening with `Normal, ...` is
prose, never a level.
  author FILE --handle @xx --name "Full Name"      add or update a roster entry
  describe FILE --category CODE --text D           set the category description
  relate FILE --id ID [--related TEXT] [--blocked-by TEXT]
  log    FILE --id ID --event E
  close  FILE --id ID --evidence E [--event E]      evidence proves it is done
  reject FILE --id ID --event E                    not reproduced, irrelevant, wontfix
  reopen FILE --id ID [--event E]                  closed defect -> a numbered regression
  remove FILE --id ID [--force]                    mistakes and duplicates only
  upgrade FILE [--code "Section=CODE"]... [--author @xx] [--apply]
          --apply always applies every safe rewrite (ids, codes, stamps, severity
          and test-tag canonicalisation, Contents drop) and exits 0; every content
          problem - missing roster or --author, unrated criteria, untriaged
          defects, missing descriptions, hints or evidence, nested items, items
          above the first heading - becomes a HINT line carrying the exact command
          to run. Non-zero only for I/O errors or an unrecognisable file type.

Query paths are files or dirs (a dir is scanned for acc-crit*.md and defects*.md);
no path means ./docs when it exists, else . Stdlib only.
"""

import argparse
import datetime
import json
import pathlib
import re
import sys

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
ITEM = re.compile(r"^(\s*)- \[([ xX-])\] (.*)$")
CBOX = re.compile(r"^\s*- \[[^\]]{0,3}\](?:\s|$)")
IDTOK = re.compile(
    r"^`(?P<prefix>ACC|DEF)-(?P<cat>[A-Z]{2,6})-(?P<num>\d+)"
    r"(?:-(?P<regr>\d+))?`\s+(?P<body>.*)$"
)
LEGACY = re.compile(r"^`(ACC|DEF)-(\d+)`\s+(.*)$")  # pre-category id, upgrade only
IDREF = re.compile(r"\b(ACC|DEF)-([A-Z]{2,6})-(\d+)(?:-(\d+))?\b")
CATCODE = re.compile(r"^(.*?)\s*`([A-Z]{2,6})`$")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
# any all-caps token used as a severity, so upgrade can name what it cannot map
SEVWORD = re.compile(r"^([A-Z][A-Z0-9-]{0,11})\s*[;:,]")
LOGLINE = re.compile(r"^(\s+)- log:\s*(\S*)(.*)$")
DATED = re.compile(r"^(\s+)- (\d{4}-\d{2}-\d{2})\b(.*)$")
RELLINE = re.compile(r"^(\s+)- (related|blocked-by):\s*(.*)$")
HINTLINE = re.compile(r"^(\s+)- (repro|test):\s*(.*)$")
HANDLE = re.compile(r"@[a-z][a-z0-9]{1,3}")
ROSTER = re.compile(r"^\s*- `(@[a-z][a-z0-9]{1,3})`\s+(.*)$")
AUTHORED = re.compile(r"^(@[a-z][a-z0-9]{1,3})\s+(.*)$")
TAGLINE = re.compile(r"^(\s+)- test-tags:\s*(.*)$")
# the proof an item is done, written at closure and retired by a reopen
EVIDLINE = re.compile(r"^(\s+)- evidence:\s*(.*)$")
REJECTED = re.compile(r"^rejected:?\s*(.*)$", re.I)
CLOSING = re.compile(r"^(closed|rejected)\b", re.I)  # the log line that ended the item
SUB = re.compile(r"^\s+- ")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")  # ISO 8601, UTC
DATEONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # legacy, upgrade only
TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+|[a-z0-9]+")  # search: a hyphen run stays whole

# the checkbox is the whole status; nothing else records it
STATE = {" ": "open", "x": "closed", "-": "rejected"}
FLAG = {"open": " ", "closed": "x", "rejected": "-"}
HINT_FOR = {"ACC": "test", "DEF": "repro"}
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


def save(path, lines):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def now():
    """ISO 8601 in UTC - one unambiguous instant, comparable as a plain string."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def parse(path):
    """Return (blocks, sections). A block is one item plus its indented sub-lines."""
    name = pathlib.Path(path).name
    docp = "ACC" if name.startswith("acc-crit") else "DEF" if name.startswith("defects") else None
    blocks, sections, cur, sec = [], [], None, None
    in_authors = False
    for lineno, ln in non_fenced(load(path)):
        if in_authors and not HEADING.match(ln):
            continue
        h = HEADING.match(ln)
        if h:
            in_authors = False
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
                )
                sections.append(sec)
            cur = None
            continue
        m = ITEM.match(ln)
        if m:
            indent, state, text = len(m.group(1)), m.group(2), m.group(3)
            idm = IDTOK.match(text)
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
                regr=int(idm.group("regr")) if idm and idm.group("regr") else None,
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
            continue
        # the first prose line under a `##` heading, before any item, is the description
        if cur is None and sec is not None and sec["desc"] is None and ln.strip():
            sec["desc"] = ln.strip()
    return blocks, sections


def ident(b):
    if not b["prefix"]:
        return "(no id)"
    root = f"{b['prefix']}-{b['cat']}-{b['num']}"
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
):
    """The items a query is about - every filter except --status. On `report` that one
    narrows the ITEMS queue alone, so a filtered report still says where the whole
    scope stands; `list` and `pivot` apply it through `select`."""
    out = [b for b in blocks if not b["indent"]]
    if cat:
        out = [b for b in out if b["cat"] == cat]
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
    )
    if fl["status"] and fl["status"] != "all":
        out = [b for b in out if status_of(b) == fl["status"]]
    return out


def filter_note(fl, status=None):
    """The `(open, category AUTH, @kj)` suffix a filtered table carries in its title."""
    bits = [
        status,
        f"category {fl['category']}" if fl["category"] else None,
        fl["severity"],
        fl["importance"],
        fl["author"],
        f"tag {fl['tag']}" if fl["tag"] else None,
        "regressions only" if fl["regr"] else None,
        f"grep /{fl['grep']}/" if fl["grep"] else None,
        "blocked" if fl["blocked"] else None,
        f"related to {fl['related_to']}" if fl["related_to"] else None,
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
    """The ids this item's related: or blocked-by: lines name, file order, once each."""
    return list(dict.fromkeys(rid for k, rid, _ in b["refs"] if k == kind))


def text_of(b):
    """What --grep reads: title, body, evidence and every log event."""
    return [b["title"] or "", b["plain"] or "", b["evidence"] or "", *b["logs"]]


def link_index(files):
    """ident -> block over every scanned file, the cross-file view the relation
    filters, refs and check read. Built only when a query needs it."""
    return {ident(b): b for f in files for b in parse(f)[0] if b["prefix"]}


def is_blocked(b, index):
    """At least one blocked-by target that exists in the scanned files and is open.
    A dangling target is a check error, not a block."""
    return any(r in index and status_of(index[r]) == "open" for r in targets(b, "blocked-by"))


def linked(b, wanted, index):
    """Either direction, either kind; an item is not linked to itself."""
    me = ident(b)
    if me == wanted:
        return False
    if any(r == wanted for _, r, _ in b["refs"]):
        return True
    t = index.get(wanted)
    return t is not None and any(r == me for _, r, _ in t["refs"])


def blocker_cycles(index):
    """Every blocked-by cycle one depth-first pass over the scanned items finds, each
    as [m, ..., m] starting at its smallest id. Self-block is the one-step case.
    Status is ignored: a loop through a closed item is still a structural error.
    One pass, iterative: a tracker where every task is blocked by the last few, or
    a chain hundreds deep, costs one visit per item and per link."""
    state, cycles = {}, []  # missing: unvisited, 1: on the path, 2: done
    for start in index:
        if start in state:
            continue
        state[start] = 1
        path, pending = [start], [iter(targets(index[start], "blocked-by"))]
        while path:
            rid = next(pending[-1], None)
            if rid is None:
                state[path.pop()] = 2
                pending.pop()
            elif state.get(rid) == 1:
                loop = path[path.index(rid) :]
                i = loop.index(min(loop))
                cycles.append(loop[i:] + loop[:i] + [loop[i]])
            elif rid in index and rid not in state:
                state[rid] = 1
                path.append(rid)
                pending.append(iter(targets(index[rid], "blocked-by")))
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
    hits = [b for b in blocks if ident(b) == wanted]
    if not hits:
        raise SystemExit(f"no item with id {wanted}")
    return hits[0]


def norm_id(raw, prefix):
    raw = raw.strip().upper()
    if IDREF.fullmatch(raw):
        return raw
    raise SystemExit(f"malformed id {raw!r}; expected {prefix}-<CAT>-<N>[-<R>]")


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
    "hint",
    "regr",
    "root",
    "logs",
    "related",
    "blockers",
)
HEAD = {
    "id": "Id",
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
    "hint": "Hint",
    "regr": "Regr",
    "root": "Root",
    "logs": "Logs",
    "related": "Related",
    "blockers": "Blockers",
}
WIDTH = {
    "title": 40,
    "body": 88,
    "evidence": 56,
    "tags": 24,
    "hint": 64,
    "related": 48,
    "blockers": 48,
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
    "tags": NO_TEST,
    "severity": "untriaged",
    "importance": "unrated",
    "related": "unlinked",
    "blockers": "unblocked",
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


def record(b, today=None):
    """One item as data - what every table, pivot cell and --json document is built from.
    `category` is the live section the item sits under, not the segment in its id."""
    sec = b["section"]
    return {
        "id": ident(b),
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
        "hint": b["hint"],
        "regr": b["regr"] or 0,
        "root": root_of(b),
        "related": targets(b, "related"),
        "blockers": targets(b, "blocked-by"),
        "logs": len(b["logs"]),
        "line": b["line"],
    }


def field_cell(rec, field):
    v = rec.get(field)
    if field in ("id", "root") and v:
        return f"`{v}`"
    if field in ("related", "blockers"):
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


def parse_fields(spec, what):
    out = []
    for raw in (spec or "").split(","):
        f = raw.strip().lower()
        if not f:
            continue
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
        return (0, (b["cat"] or "", b["num"] or 0, b["regr"] or 0))
    v = rec.get(field)
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
    if field in ("tags", "related", "blockers"):
        return rec[field] or [NONE_KEY[field]]
    if field in ("filed", "closed", "updated"):
        return [rec[field][:7] if rec[field] else "-"]
    if field == "age":
        return [age_band(rec["age"])]
    if field == "regr":
        return ["regression" if rec["regr"] else "original"]
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
    """The one aggregate, plain counts: categories down; the open items split by
    level - severity on a defects document, importance on a criteria document -
    then the closed and rejected totals. The level columns count OPEN items only:
    they answer how bad what is left is. UNTRIAGED/UNRATED appears only when an
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
        op = cl = rj = 0
        for b in own:
            st = status_of(b)
            if st == "open":
                op += 1
                lv = level_of(b)
                cnt[lv if lv in cnt else none_col] += 1
            elif st == "closed":
                cl += 1
            else:
                rj += 1
        rows.append(dict(section=sec, cells=cnt, open=op, closed=cl, rejected=rj))
    total = dict(
        cells={c: sum(r["cells"][c] for r in rows) for c in cols},
        open=sum(r["open"] for r in rows),
        closed=sum(r["closed"] for r in rows),
        rejected=sum(r["rejected"] for r in rows),
    )
    return dict(prefix=prefix, cols=cols, rows=rows, total=total)


def grid_json(grid):
    done = "fixed" if grid["prefix"] == "DEF" else "done"

    def row(r):
        sec = r["section"]
        return {
            "category": sec["code"] if sec else None,
            "name": sec["name"] if sec else None,
            "open": r["open"],
            "levels": dict(r["cells"]),
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
    index = link_index(files) if fl["blocked"] or fl["related_to"] else None
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
        )
        shown = [s for s in sections if not cat or s["code"] == cat]
        if (
            sev
            or fl["importance"]
            or since
            or until
            or fl["author"]
            or fl["tag"]
            or fl["regr"]
            or fl["grep"]
            or fl["blocked"]
            or fl["related_to"]
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
                items += [record(b) for b in sorted(own, key=fix_order) if b in listed]
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

        if scope:
            cols = grid["cols"]
            done_h = "Fixed" if prefix == "DEF" else "Done"
            print(banner("\U0001f4ca", "SUMMARY", plain) + "\n")
            head = ["Category", "Open"] + cols + [done_h, "Rejected"]
            print("| " + " | ".join(head) + " |")
            print("|---|" + "--:|" * (len(head) - 1))

            def counts_of(r):
                return [r["open"], *(r["cells"][c] for c in cols), r["closed"], r["rejected"]]

            for r in grid["rows"]:
                sec = r["section"]
                label = f"{sec['name']} `{sec['code'] or '?'}`" if sec else "(no category)"
                print("| " + " | ".join([label] + [str(x) for x in counts_of(r)]) + " |")
            print(
                "| "
                + " | ".join(["**Total**"] + [str(x) for x in counts_of(grid["total"])])
                + " |"
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
            # a column where every row reads the same carries nothing; the header
            # and the footer already say which status is being listed
            st_h, st_r = ("Status | ", "--------|") if want is None else ("", "")
            if solo:
                print()
            print(f"| Id | Title | Description | {lvl_h}{st_h}Tests |{ev_h}")
            print(f"|----|-------|-------------|{lvl_r}{st_r}-------|{ev_r}")
            for b in rows:
                lvl = (b["severity"] if prefix == "DEF" else b["importance"]) or "-"
                st = f"{status_of(b)} | " if want is None else ""
                evid = f" {cell(b['evidence'], 56)} |" if show_evid else ""
                print(
                    f"| `{ident(b)}` | {cell(b['title'] or '?', 40)} "
                    f"| {cell(b['plain'], 88)} | {lvl} | {st}{cell(', '.join(tag_set(b)), 24)} |{evid}"
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
    index = link_index(files) if fl["blocked"] or fl["related_to"] else None
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
        pairs = sorted_items([(b, record(b)) for b in select(blocks, fl, index)], sort)
        if as_json:
            docs += [dict(rec, file=f) for _, rec in pairs]
            continue
        heads = [(HINT_FOR[prefix].title() if c == "hint" else HEAD[c]) for c in cols]
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
        names = {s["code"]: s["name"] for s in sections if s["code"]}
        scope = select(blocks, fl, index)
        grid = {}
        for b in scope:
            rec = record(b)
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
            linkish = rows_f in ("id", "root", "related", "blockers")
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


SEARCH_W = {"id": 3.0, "title": 3.0, "body": 1.0, "evidence": 1.0, "log": 1.0}
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
            "id": tokens(ident(b)),
            "title": tokens(b["title"]),
            "body": tokens(b["plain"]),
            "evidence": tokens(b["evidence"]),
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
    for an id no item carries - that is what `remove --force` leaves behind."""
    index, inbound = {}, []
    for f in files:
        for b in parse(f)[0]:
            if b["prefix"]:
                index[ident(b)] = (f, b)
            inbound += [
                {"file": f, "line": ln, "id": ident(b), "kind": k}
                for k, rid, ln in b["refs"]
                if rid == wanted
            ]
    outbound, paths, blockers = [], [], []
    if wanted in index:
        f, b = index[wanted]
        outbound = [{"file": f, "line": ln, "id": rid, "kind": k} for k, rid, ln in b["refs"]]
        seen = set()
        # (id, ids on the route so far, printed hops, depth); depth first, file order
        todo = [(rid, [wanted], [], 1) for rid in reversed(targets(b, "blocked-by"))]
        while todo:
            rid, ids, hops, depth = todo.pop()
            if rid in ids:
                paths.append(hops + [f"{rid} (cycle)"])
                continue
            st = status_of(index[rid][1]) if rid in index else "not found"
            hop = hops + [f"{rid} ({st})"]
            nxt = targets(index[rid][1], "blocked-by") if rid in index else []
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
    cycles = {}  # smallest id -> the cycles reported on it
    for loop in blocker_cycles(index):
        cycles.setdefault(loop[0], []).append(loop)

    errors = warns = 0
    seen = {}  # ident -> (file, line); an id is unique across the scanned files
    for f in files:
        lines = load(f)
        blocks, sections = parse(f)
        prefix = doc_prefix(f, blocks)
        want_hint = HINT_FOR[prefix]
        known_authors = roster_of(f)
        e, w, codes = [], [], {}

        if not any(
            len(m.group(1)) == 1 for _, ln in non_fenced(lines) if (m := HEADING.match(ln))
        ):
            e.append((1, "no H1 title"))

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
            lm = LOGLINE.match(ln)
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
                e.append((b["line"], f"item has no `{prefix}-<CAT>-<N>` id; run upgrade"))
            else:
                if b["prefix"] != prefix:
                    e.append((b["line"], f"id prefix {b['prefix']} in a {prefix} document"))
                key = ident(b)
                if key in seen:
                    sf, sl = seen[key]
                    at = f"line {sl}" if sf == f else f"{sf}:{sl}"
                    e.append((b["line"], f"duplicate id {key} (first at {at})"))
                else:
                    seen[key] = (f, b["line"])
                if b["regr"]:
                    # a regression is a fact about a defect; without its root it counts
                    # nothing and points nowhere
                    root = f"{b['prefix']}-{b['cat']}-{b['num']}"
                    if not any(
                        x["prefix"] == b["prefix"]
                        and x["cat"] == b["cat"]
                        and x["num"] == b["num"]
                        and not x["regr"]
                        for x in blocks
                    ):
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
            if status_of(b) == "rejected" and not reject_reason(b):
                w.append((b["line"], "rejected with no reason; log `rejected: <why>`"))
            if not b["has_log"]:
                e.append((b["line"], "item has no authored log: line; every entry is authored"))
            for kind, rid, lineno in b["refs"]:
                if rid not in index:
                    e.append((lineno, f"{kind} points at {rid}, not found in the scanned files"))
                elif (
                    kind == "blocked-by"
                    and status_of(b) == "open"
                    and status_of(index[rid]) in ("closed", "rejected")
                ):
                    w.append(
                        (
                            lineno,
                            f"blocked-by {rid} is {status_of(index[rid])}; "
                            "the block no longer holds",
                        )
                    )
            for loop in cycles.get(ident(b), []) if b["prefix"] else []:
                # a duplicated id (its own check error) can hand the cycle to a
                # copy that lacks the closing line; anchor on the item then
                at = next(
                    (ln for k, r, ln in b["refs"] if k == "blocked-by" and r == loop[1]),
                    b["line"],
                )
                e.append((at, "blocked-by cycle: " + " -> ".join(loop)))

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


def set_line(lines, b, marker, value, pat):
    """Replace the item's `- <marker>:` sub-line, or add one under the item line."""
    ind = sub_indent(lines, b)
    for i in range(b["line"], block_end(lines, b)):
        if pat.match(lines[i]):
            lines[i] = f"{ind}- {marker}: {value}"
            return "replaced"
    lines.insert(b["line"], f"{ind}- {marker}: {value}")
    return "added"


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


def cmd_author(file, handle, name):
    h = handle if handle.startswith("@") else "@" + handle
    if not HANDLE.fullmatch(h):
        raise SystemExit(f"bad handle {handle!r}; use @ plus 2-4 letters, e.g. @kj")
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


def cmd_add(file, code, name, desc, title, text, severity, importance, repro, test, tags, author):
    lines = load(file)
    blocks, sections = parse(file)
    prefix = doc_prefix(file, blocks)
    kind, value = hint_kind_for(file, blocks, repro, test)
    who = need_author(file, author)
    if prefix == "ACC" and severity:
        raise SystemExit("acceptance criteria carry no severity")
    if prefix == "DEF" and importance:
        raise SystemExit("defects carry no importance; triage with --severity")
    if prefix == "DEF" and not severity:
        raise SystemExit("a defect must be triaged; pass --severity " + "|".join(SEVS))
    if prefix == "ACC" and not importance:
        raise SystemExit("a criterion must be rated; pass --importance " + "|".join(IMPS))
    code = code.upper()
    if not re.fullmatch(r"[A-Z]{2,6}", code):
        raise SystemExit(
            f"category code {code!r} must be 2-6 uppercase letters; "
            f"three to five is the normal range, six the ceiling"
        )
    sec, lines = section_for(sections, code, name, desc, lines)
    num = next_num(blocks)
    lead = severity or importance
    body = f"{lead.upper()}; {text}" if lead else text
    item = f"- [ ] `{prefix}-{code}-{num}` **{title}** - {body}"
    at = insert_index(lines, sec)
    tail = [f"  - {kind}: {value}"] if kind else []
    tail += [f"  - test-tags: {canon_tags(tags)}"] if tags else []
    # the category description is a paragraph; a list must not butt straight onto it
    prose = (
        at > 0
        and lines[at - 1].strip()
        and not ITEM.match(lines[at - 1])
        and not SUB.match(lines[at - 1])
    )
    lead = [""] if prose else []
    lines[at:at] = lead + [item] + tail + [f"  - log: {now()} {who} added"]
    save(file, lines)
    print(f"{file}:{at + len(lead) + 1}: {prefix}-{code}-{num} added")
    return 0


def cmd_edit(file, wanted, title, text, sev, importance, repro, test, tags, author, evidence=None):
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
    done = []
    if title or text or sev or importance:
        body = b["body"]
        bold = BOLD.search(body)
        cur_title = bold.group(1) if bold else ""
        cur_text = body[bold.end() :].lstrip(" -") if bold else body
        new_text = text if text else cur_text
        if sev:
            new_text = f"{sev}; " + SEV.sub("", new_text).lstrip(" ;:,-")
        elif importance:
            new_text = f"{importance}; " + IMP.sub("", new_text).lstrip(" ;:,-")
        elif b["severity"] and not SEV.match(new_text):
            # a --text rewrite must not quietly untriage the defect
            new_text = f"{b['severity']}; {new_text}"
        elif b["importance"] and not IMP.match(new_text):
            # nor quietly unrate the criterion
            new_text = f"{b['importance']}; {new_text}"
        new = f"`{ident(b)}` **{title or cur_title}** - {new_text}"
        lines[b["line"] - 1] = f"- [{b['state']}] {new}"
        done += [
            x
            for x in (
                title and "title",
                text and "text",
                sev and "severity",
                importance and "importance",
            )
            if x
        ]
    if kind:
        done.append(f"{kind} ({set_line(lines, b, kind, value, HINTLINE)})")
    if tags:
        done.append(f"test-tags ({set_line(lines, b, 'test-tags', canon_tags(tags), TAGLINE)})")
    if evidence:
        done.append(f"evidence ({set_line(lines, b, 'evidence', evidence, EVIDLINE)})")
    what = " and ".join(done)
    lines.insert(block_end(lines, b), f"{sub_indent(lines, b)}- log: {now()} {who} edited {what}")
    save(file, lines)
    print(f"{file}:{b['line']}: {ident(b)} {what} updated")
    return 0


def cmd_describe(file, code, text):
    lines = load(file)
    _, sections = parse(file)
    code = code.upper()
    sec = next((s for s in sections if s["code"] == code), None)
    if sec is None:
        have = ", ".join(s["code"] or "?" for s in sections) or "(none)"
        raise SystemExit(f"unknown category code {code}; have: {have}")
    i = sec["line"]  # 0-based index of the line after the heading
    while i < len(lines) and not lines[i].strip():
        i += 1
    prose = (
        i < len(lines)
        and lines[i].strip()
        and not HEADING.match(lines[i])
        and not ITEM.match(lines[i])
        and not SUB.match(lines[i])
    )
    if prose:
        lines[i] = text
        what = "replaced"
    else:
        ins = ["", text]
        if sec["line"] < len(lines) and lines[sec["line"]].strip():
            ins.append("")
        lines[sec["line"] : sec["line"]] = ins
        what = "added"
    save(file, lines)
    print(f"{file}:{sec['line']}: {code} description {what}")
    return 0


def cmd_relate(file, wanted, related, blocked):
    if not (related or blocked):
        raise SystemExit("nothing to link; pass --related and/or --blocked-by")
    lines = load(file)
    blocks, _ = parse(file)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    ind = sub_indent(lines, b)
    # one line per call, never merged into an existing one: a relation line may end in
    # free text, and appending an id after that prose would bury it. check unions them
    at = b["line"]
    for i in range(b["line"], block_end(lines, b)):
        if RELLINE.match(lines[i]):
            at = i + 1
    for kind, value in (("related", related), ("blocked-by", blocked)):
        if not value:
            continue
        lines.insert(at, f"{ind}- {kind}: {value}")
        at += 1
        print(f"{file}:{b['line']}: {ident(b)} {kind}: {value}")
    save(file, lines)
    return 0


def cmd_log(file, wanted, event, author):
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    line = f"{sub_indent(lines, b)}- log: {now()} {who} {event}"
    lines.insert(block_end(lines, b), line)
    save(file, lines)
    print(f"{file}:{b['line']}: {ident(b)} logged -> {line.strip()}")
    return 0


def mint_regression(file, lines, blocks, b, event, who):
    """Reopening a closed defect opens `<parent>-<next>` and leaves the parent closed.

    The closure was proven when it was made, so retiring it would delete a true fact.
    A defect that broke again is a new fact about the same defect, and giving it its
    own item is what makes regressions countable.
    """
    rid = f"{b['prefix']}-{b['cat']}-{b['num']}-{next_regr(blocks, b)}"
    pad = sub_indent(lines, b)
    at = block_end(lines, b)
    # the parent names its regression, so its own history is complete
    lines.insert(at, f"{pad}- log: {now()} {who} regressed as {rid}")
    ev = f"regression of {ident(b)}" + (f": {event}" if event else "")
    lines[at + 1 : at + 1] = [
        f"{' ' * b['indent']}- [ ] `{rid}` {b['body']}",
        f"{pad}- log: {now()} {who} {ev}",
    ]
    save(file, lines)
    print(f"{file}:{at + 2}: [ ] {rid} ({ev})")
    return 0


def cmd_setstate(file, wanted, target, verb, event, author, evidence=None):
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    if b["state"] == target:
        print(f"{file}:{b['line']}: {ident(b)} already [{target}]; no change")
        return 0
    if target == " " and b["state"].lower() == "x" and b["prefix"] == "DEF":
        return mint_regression(file, lines, blocks, b, event, who)
    idx = b["line"] - 1
    lines[idx] = re.sub(r"\[[ xX-]\]", f"[{target}]", lines[idx], count=1)
    ev = f"{verb}: {event}" if event else verb
    if target == "x":
        # nothing closes without a proof; the line is the proof, stored once
        set_line(lines, b, "evidence", evidence, EVIDLINE)
    elif target == " ":
        # reopened means not done, so the proof no longer stands. The log keeps it
        was = drop_line(lines, b, EVIDLINE)
        if was:
            ev += f"; evidence retired: {was}"
    lines.insert(block_end(lines, b), f"{sub_indent(lines, b)}- log: {now()} {who} {ev}")
    save(file, lines)
    print(f"{file}:{b['line']}: [{target}] {ident(b)} ({ev})")
    return 0


def cmd_remove(file, wanted, force):
    lines = load(file)
    blocks, _ = parse(file)
    wanted = norm_id(wanted, doc_prefix(file, blocks))
    b = find_id(blocks, wanted)
    # a criterion may cite a defect and back, so scan every tracking doc beside this one
    inbound = []
    for f in resolve([str(pathlib.Path(file).parent)]):
        for o, _ in [(x, 0) for x in parse(f)[0]]:
            inbound += [(f, o, lineno) for k, rid, lineno in o["refs"] if rid == wanted]
    if inbound and not force:
        for f, o, lineno in inbound:
            print(f"{f}:{lineno}: {ident(o)} still points at {wanted}", file=sys.stderr)
        raise SystemExit(f"{wanted} is referenced; close it as invalid, or pass --force")
    end = block_end(lines, b)
    del lines[b["line"] - 1 : end]
    save(file, lines)
    print(f"{file}: removed {wanted} ({end - b['line'] + 1} line(s))")
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
                f'pm-tools describe {file} --category {code} --text "<one line>"'
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
                f'pm-tools add {file} --category <CODE> --title "..." --text "..." '
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
        assign[b["line"]] = (code, num, b["regr"])
        lg = LEGACY.match(b["body"])
        old = ident(b) if b["prefix"] else (f"{lg.group(1)}-{lg.group(2)}" if lg else "(no id)")
        new = f"{prefix}-{code}-{num}" + (f"-{b['regr']}" if b["regr"] else "")
        if old != new:
            plan.append(f"line {b['line']}: {old} -> {new}")
        if prefix == "DEF" and not b["severity"]:
            odd = SEVWORD.match(b["plain"])
            why = f"carries an unmapped severity word {odd.group(1)!r}" if odd else "not triaged"
            hints.append(
                f"line {b['line']}: {new} {why}; run: "
                f"pm-tools edit {file} --id {new} --severity {'|'.join(SEVS)}"
            )
        if prefix == "ACC" and not b["importance"]:
            hints.append(
                f"line {b['line']}: {new} not rated; run: "
                f"pm-tools edit {file} --id {new} --importance {'|'.join(IMPS)}"
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
    for i, ln in enumerate(lines, start=1):
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
            code, num, regr = assign[i]
            m = ITEM.match(ln)
            body = m.group(3)
            idm = IDTOK.match(body)
            if idm:
                body = idm.group("body")
            else:
                lg = LEGACY.match(body)
                if lg:
                    body = lg.group(3)
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
            new_id = f"{prefix}-{code}-{num}" + (f"-{regr}" if regr else "")
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
    save(file, out)
    print(
        f"\napplied {len(plan)} change(s) to {file}; {len(hints)} hint(s) remain. Run check next"
    )
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
        sp.add_argument("--category", help="one category code" + whole)
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
            help="items linked to ID either way, related or blocked-by" + whole,
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
                help="the grid and the queue alone - no blurbs, no categories table",
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
                "shell does not read it as a flag. Fix order by default",
            )
        if name == "pivot":
            sp.add_argument("--rows", required=True, type=str.lower, help="the field down")
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
    sa.add_argument("--title", required=True)
    sa.add_argument("--text", required=True)
    sa.add_argument("--name", help="category name, needed only when the code is new")
    sa.add_argument("--description", help="category description, when the code is new")
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
    sa.add_argument("--repro", help="one line saying how to reproduce, defects only")
    sa.add_argument("--test", help="one line saying how to test, criteria only")
    sa.add_argument(
        "--author",
        required=True,
        metavar="@xx",
        help="handle of the person filing this, must be on the roster",
    )
    sa.add_argument(
        "--test-tags", dest="tags", help='which tests cover it, e.g. "unit, functional"'
    )

    se = sub.add_parser("edit")
    se.add_argument("file")
    se.add_argument("--id", required=True)
    se.add_argument("--title")
    se.add_argument("--text")
    se.add_argument("--severity", type=str.upper, choices=SEVS)
    se.add_argument("--importance", type=str.upper, choices=IMPS)
    se.add_argument("--repro")
    se.add_argument("--test")
    se.add_argument("--test-tags", dest="tags")
    se.add_argument("--evidence", help="one line proving the item is done")
    se.add_argument("--author", required=True, metavar="@xx")

    sh = sub.add_parser("author")
    sh.add_argument("file")
    sh.add_argument("--handle", required=True, metavar="@xx")
    sh.add_argument("--name", required=True)

    sd = sub.add_parser("describe")
    sd.add_argument("file")
    sd.add_argument("--category", required=True)
    sd.add_argument("--text", required=True)

    sr = sub.add_parser("relate")
    sr.add_argument("file")
    sr.add_argument("--id", required=True)
    sr.add_argument("--related")
    sr.add_argument("--blocked-by", dest="blocked")

    for name in ("log", "close", "reject", "reopen"):
        sp = sub.add_parser(name)
        sp.add_argument("file")
        sp.add_argument("--id", required=True)
        sp.add_argument("--author", required=True, metavar="@xx")
        sp.add_argument("--event", required=(name in ("log", "reject")))
        if name == "close":
            sp.add_argument(
                "--evidence",
                required=True,
                help="one line proving it is done - the test that passes, the run, the commit",
            )

    sx = sub.add_parser("remove")
    sx.add_argument("file")
    sx.add_argument("--id", required=True)
    sx.add_argument("--force", action="store_true")

    su = sub.add_parser("upgrade")
    su.add_argument("file")
    su.add_argument("--code", action="append", default=[], metavar='"Section=CODE"')
    su.add_argument(
        "--author", metavar="@xx", help="sign every unauthored log line in the legacy file"
    )
    su.add_argument("--apply", action="store_true")

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
                severity=a.severity,
                importance=a.importance,
                status=a.status,
                author=a.author,
                tag=a.tag.strip().upper() if a.tag else None,
                regr=a.regressions,
                grep=a.grep,
                blocked=a.blocked,
                related_to=rid,
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
            return cmd_refs(files, a.id.strip().upper(), a.json)
        return cmd_check(files, a.strict)

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
        )
    if a.cmd == "author":
        return cmd_author(a.file, a.handle, a.name)
    if a.cmd == "describe":
        return cmd_describe(a.file, a.category, a.text)
    if a.cmd == "relate":
        return cmd_relate(a.file, a.id, a.related, a.blocked)
    if a.cmd == "log":
        return cmd_log(a.file, a.id, a.event, a.author)
    if a.cmd == "close":
        return cmd_setstate(a.file, a.id, "x", "closed", a.event, a.author, a.evidence)
    if a.cmd == "reject":
        return cmd_setstate(a.file, a.id, "-", "rejected", a.event, a.author)
    if a.cmd == "reopen":
        return cmd_setstate(a.file, a.id, " ", "reopened", a.event, a.author)
    if a.cmd == "remove":
        return cmd_remove(a.file, a.id, a.force)
    if a.cmd == "upgrade":
        ov = {}
        for spec in a.code:
            k, _, v = spec.partition("=")
            if not v:
                raise SystemExit(f"--code needs Section=CODE, got {spec!r}")
            ov[k.strip().lower()] = v.strip().upper()
        return cmd_upgrade(a.file, ov, a.apply, a.author)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
