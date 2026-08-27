#!/usr/bin/env python3
"""pm-tools - query, lint, report and edit project-management tracking docs.

The markdown file is the entire store. Nothing is recorded twice: the next id is the
highest id already in the file plus one, the category index is computed by
list-categories, backlinks are computed by refs. No counter file, no index, no TOC.

  docs/acc-crit*.md   acceptance criteria, ids ACC-<CAT>-<N>, hint line `- test:`
  docs/defects*.md    defects,             ids DEF-<CAT>-<N>, hint line `- repro:`

Both disciplines also carry `- test-tags: unit, functional` - which kinds of test
cover the item - and `- evidence: <one line>`, the proof it is actually done. `close`
demands the evidence and writes that line; `reopen` retires it.

Three states: `- [ ]` open, `- [x]` closed, `- [-]` rejected (reason in the log line).
Log lines read `- log: 2026-08-27T15:59:12Z @kj <event>` - ISO 8601 UTC, then the author.

Query:
  report [paths] [--category CODE] [--severity S] [--status open|closed|rejected|all]
         [--dates filed|closed|updated] [--since DATE] [--until DATE]
         [--detail] [--plain] [--summary]
         ITEMS lists open work only unless --status says otherwise, worst severity first.
         --category, --severity and the date window narrow the whole report; --status
         narrows ITEMS alone. --plain prints the grids and nothing else; --summary stops
         at the SUMMARY grid, listing no items at all.
  list-categories [paths]                          code, name, open/closed/rejected
  list [paths] [--open|--closed|--rejected] [--category CODE]
  refs [paths] --id ID                             every item pointing at ID
  check [paths] [--strict]                         conformity gate

Edit (one file):
  add    FILE --category CODE --title T --text D [--name NAME] [--description D]
                    --severity S [--repro R|--test T] [--test-tags "unit, functional"]
  edit   FILE --id ID [--title T] [--text D] [--severity S] [--repro R|--test T]
                      [--test-tags TAGS] [--evidence E]

--severity is CRITICAL|MAJOR|MEDIUM|MINOR, mandatory on every defect and refused on
a criterion. An untriaged defect is a check error. Foreign vocabularies (P0-P4, S1-S4,
SEV1-4, BLOCKER, URGENT, HIGH, NORMAL, LOW, TRIVIAL ...) are recognised and renamed by
upgrade; anything it cannot map is named and left for a human.
  author FILE --handle @xx --name "Full Name"      add or update a roster entry
  describe FILE --category CODE --text D           set the category description
  relate FILE --id ID [--related TEXT] [--blocked-by TEXT]
  log    FILE --id ID --event E
  close  FILE --id ID --evidence E [--event E]      evidence proves it is done
  reject FILE --id ID --event E                    not reproduced, irrelevant, wontfix
  reopen FILE --id ID [--event E]
  remove FILE --id ID [--force]                    mistakes and duplicates only
  upgrade FILE [--code "Section=CODE"]... [--author @xx] [--apply]

Query paths are files or dirs (a dir is scanned for acc-crit*.md and defects*.md);
no path means ./docs when it exists, else . Stdlib only.
"""

import argparse
import datetime
import pathlib
import re
import sys

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
ITEM = re.compile(r"^(\s*)- \[([ xX-])\] (.*)$")
CBOX = re.compile(r"^\s*- \[[^\]]{0,3}\](?:\s|$)")
IDTOK = re.compile(r"^`(ACC|DEF)-([A-Z]{2,6})-(\d+)`\s+(.*)$")
LEGACY = re.compile(r"^`(ACC|DEF)-(\d+)`\s+(.*)$")  # pre-category id, upgrade only
IDREF = re.compile(r"\b(ACC|DEF)-([A-Z]{2,6})-(\d+)\b")
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
SEV = re.compile(
    r"^(" + "|".join(sorted(SEVS + tuple(SEV_ALIAS), key=len, reverse=True)) + r")\b", re.I
)
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
            body = idm.group(4) if idm else text
            bold = BOLD.search(body)
            after = body[bold.end() :].lstrip(" -") if bold else body
            sm = SEV.match(after)
            plain = SEV.sub("", after).lstrip(" ;:,-") if sm else after
            cur = dict(
                line=lineno,
                indent=indent,
                state=state,
                text=text,
                prefix=idm.group(1) if idm else None,
                cat=idm.group(2) if idm else None,
                num=int(idm.group(3)) if idm else None,
                body=body,
                title=bold.group(1) if bold else None,
                severity=sm.group(1).upper() if sm else None,
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
                cur["dates"].append(lm.group(2) if STAMP.match(lm.group(2)) else None)
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
    return f"{b['prefix']}-{b['cat']}-{b['num']}" if b["prefix"] else "(no id)"


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


def scope_of(blocks, cat, sev, which, since, until):
    """The items the report is about - every filter except --status, which narrows the
    ITEMS queue alone so a filtered report still says where the whole scope stands."""
    out = [b for b in blocks if not b["indent"]]
    if cat:
        out = [b for b in out if b["cat"] == cat]
    if sev:
        out = [b for b in out if sev_of(b) == sev]
    if since or until:
        out = [b for b in out if in_window(b, which, since, until)]
    return out


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
        SEV_RANK.get(b["severity"], len(SEVS)),
        b["num"] if b["num"] is not None else 0,
    )


def tag_set(b):
    return [t.strip().lower() for t in (b["tags"] or "").split(",") if t.strip()]


def tally(items):
    return {name: sum(1 for b in items if status_of(b) == name) for name in FLAG}


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
    raise SystemExit(f"malformed id {raw!r}; expected {prefix}-<CAT>-<N>")


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


def cmd_report(files, cat, status, detail, sev, dates, since, until, plain, summary):
    cat = cat.upper() if cat else None
    plain = plain or summary  # a summary is the compact form; the blurbs are not part of it
    # a closed-date window can only select closed and rejected items, so the default
    # open queue would list nothing; list what the window actually found
    if dates == "closed" and (since or until) and status is None:
        status = "all"
    want = None if status == "all" else FLAG[status or "open"]
    for f in files:
        blocks, sections = parse(f)
        prefix = doc_prefix(f, blocks)
        if sev and prefix != "DEF":
            print(f"{f}: skipped, --severity is a defect attribute", file=sys.stderr)
            continue
        scope = scope_of(blocks, cat, sev, dates, since, until)
        shown = [s for s in sections if not cat or s["code"] == cat]
        if sev or since or until:
            # a category the filter emptied is not part of the answer
            shown = [s for s in shown if any(b["section"] is s for b in scope)]
        t = tally(scope)

        filt = [
            x
            for x in (
                status,
                f"category {cat}" if cat else None,
                sev,
                window_note(dates, since, until),
            )
            if x
        ]
        note = f" ({', '.join(filt)})" if filt else ""
        title = LABEL[prefix] if plain else f"{ICON[prefix]}{PAD}{LABEL[prefix]}"
        print(f"\n# {title} - {f}{note}\n")
        print(
            f"{t['open']} open / {t['closed']} closed / {t['rejected']} rejected "
            f"across {len(shown)} categor" + ("y\n" if len(shown) == 1 else "ies\n")
        )
        solo = shown[0] if len(shown) == 1 else None
        if solo:
            print(
                f"**{solo['name']}** `{solo['code'] or '?'}`"
                + (f" - {solo['desc']}" if solo["desc"] else "")
                + "\n"
            )

        # the one aggregate: category down, severity or tag across, `open/closed` in
        # every cell so the whole grid reads in one unit. rejected is not work - it is
        # excluded outright and lives in its own section. --status never narrows this
        live = [b for b in scope if status_of(b) != "rejected"]
        if prefix == "DEF":
            axis, none_col = "severity", "untriaged"

            def keys(b):
                return [b["severity"] or none_col]

            seen = {k for b in live for k in keys(b)}
            cols = [x for x in SEVS if x in seen] + ([none_col] if none_col in seen else [])
            cut = []
        else:
            axis, none_col = "test tag", "untagged"

            def keys(b):
                return tag_set(b) or [none_col]

            freq = {}
            for b in live:
                for k in keys(b):
                    freq[k] = freq.get(k, 0) + 1
            rank = sorted((k for k in freq if k != none_col), key=lambda k: (-freq[k], k))
            cut = rank[8:]
            cols = rank[:8] + ([none_col] if none_col in freq else [])

        if scope:
            print(banner("\U0001f4ca", "SUMMARY", plain) + "\n")
            if not plain:
                multi = (
                    ""
                    if prefix == "DEF"
                    else " An item with several tags counts in several columns."
                )
                print(
                    f"Categories down, {axis} across, `open/closed` in every cell - "
                    f"`10/43` is 10 open, 43 closed. A dash means nothing in that bucket. "
                    f"Rejected items are excluded; they are listed at the end.{multi}\n"
                )
            head = ["Category"] + cols + ["Open/Closed"]
            print("| " + " | ".join(head) + " |")
            print("|---|" + "--:|" * (len(head) - 1))

            groups = [(sec, [b for b in scope if b["section"] is sec]) for sec in shown]
            loose = [b for b in scope if b["section"] is None]
            if loose:
                groups.append((None, loose))

            def pair(o, c):
                return f"{o}/{c}" if (o or c) else "-"

            tot = {c: [0, 0] for c in cols}
            tot_o = tot_c = 0
            for sec, own in groups:
                cnt = {c: [0, 0] for c in cols}
                op = cl = 0
                for b in own:
                    st = status_of(b)
                    if st == "rejected":
                        continue
                    slot = 0 if st == "open" else 1
                    op, cl = (op + 1, cl) if slot == 0 else (op, cl + 1)
                    for k in keys(b):
                        if k in cnt:
                            cnt[k][slot] += 1
                label = f"{sec['name']} `{sec['code'] or '?'}`" if sec else "(no category)"
                row = [label] + [pair(*cnt[c]) for c in cols] + [pair(op, cl)]
                print("| " + " | ".join(row) + " |")
                for c in cols:
                    tot[c][0] += cnt[c][0]
                    tot[c][1] += cnt[c][1]
                tot_o += op
                tot_c += cl
            if len(groups) > 1:
                row = ["**Total**"] + [pair(*tot[c]) for c in cols] + [f"**{pair(tot_o, tot_c)}**"]
                print("| " + " | ".join(row) + " |")
            if cut:
                print(f"\nTag columns omitted from the grid: {', '.join(cut)}")

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

        counts, tagged = {}, 0
        for b in scope:
            ts = tag_set(b)
            tagged += 1 if ts else 0
            for t2 in ts:
                counts[t2] = counts.get(t2, 0) + 1
        n = len(scope)
        if n and not plain:

            def pct(k):
                return f"{round(100 * k / n)}%"

            print(f"\n## \U0001f9ea{PAD}TEST COVERAGE\n")
            print(
                f"{tagged} of {n} items tagged ({pct(tagged)}); an item may carry several tags\n"
            )
            print("| Tag | Items | Share |")
            print("|-----|------:|------:|")
            for t2, k in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
                print(f"| {cell(t2, 24)} | {k} | {pct(k)} |")
            if tagged < n:
                print(f"| (untagged) | {n - tagged} | {pct(n - tagged)} |")

        listed = [b for b in scope if want is None or b["state"].lower() == want]
        show_evid = any(b["evidence"] for b in listed)
        print("\n" + banner("\U0001f4cc", "ITEMS", plain))
        groups = [(sec, [b for b in scope if b["section"] is sec]) for sec in shown]
        loose = [b for b in scope if b["section"] is None]
        if loose:
            groups.append((None, loose))
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
                    head = f"{b['severity']}, {status_of(b)}" if b["severity"] else status_of(b)
                    print(f"\n{h} `{ident(b)}` **{b['title'] or '?'}** - {head}\n")
                    if b["plain"]:
                        print(f"{b['plain']}\n")
                    for line in b["subs"]:
                        print(line)
                continue
            sev_h, sev_r = ("Severity | ", "----------|") if prefix == "DEF" else ("", "")
            ev_h, ev_r = (" Evidence |", "----------|") if show_evid else ("", "")
            # a column where every row reads the same carries nothing; the header
            # and the footer already say which status is being listed
            st_h, st_r = ("Status | ", "--------|") if want is None else ("", "")
            if solo:
                print()
            print(f"| Id | Title | Description | {sev_h}{st_h}Tests |{ev_h}")
            print(f"|----|-------|-------------|{sev_r}{st_r}-------|{ev_r}")
            for b in rows:
                sev = f"{b['severity'] or '-'} | " if prefix == "DEF" else ""
                st = f"{status_of(b)} | " if want is None else ""
                evid = f" {cell(b['evidence'], 56)} |" if show_evid else ""
                print(
                    f"| `{ident(b)}` | {cell(b['title'] or '?', 40)} "
                    f"| {cell(b['plain'], 88)} | {sev}{st}{cell(b['tags'], 24)} |{evid}"
                )

        hidden = [b for b in scope if want is not None and b["state"].lower() != want]
        if hidden:
            h = tally(hidden)
            bits = [f"{h[k]} {k}" for k in ("open", "closed", "rejected") if h[k]]
            tail = "" if plain else " - pass `--status all`, or `--status closed` / `rejected`"
            print(f"\n{', '.join(bits)} not listed{tail}")

        rej = [b for b in scope if status_of(b) == "rejected"]
        if rej and want in (None, "-") and not detail:
            print("\n" + banner("\U0001f6ab", "REJECTED", plain) + "\n")
            print("| Id | Title | Reason |")
            print("|----|-------|--------|")
            for b in rej:
                print(
                    f"| `{ident(b)}` | {cell(b['title'] or '?', 40)} "
                    f"| {cell(reject_reason(b), 72)} |"
                )
    return 0


def cmd_list_categories(files):
    total = 0
    for f in files:
        blocks, sections = parse(f)
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
    print(f"\n{total} item(s)")
    return 0


def cmd_list(files, state, cat):
    n = 0
    for f in files:
        blocks, _ = parse(f)
        for b in blocks:
            if b["indent"] or (state and b["state"].lower() != state):
                continue
            if cat and b["cat"] != cat.upper():
                continue
            print(f"{f}:{b['line']}: [{b['state']}] {ident(b)} **{b['title'] or '?'}**")
            n += 1
    print(f"\n{n} item(s)")
    return 0


def cmd_refs(files, wanted):
    n = 0
    for f in files:
        blocks, _ = parse(f)
        for b in blocks:
            for kind, rid, lineno in b["refs"]:
                if rid == wanted:
                    print(f"{f}:{lineno}: {ident(b)} {kind} -> {wanted}")
                    n += 1
    print(f"\n{n} inbound reference(s) to {wanted}")
    return 0


def _valid_stamp(s):
    try:
        datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def cmd_check(files, strict):
    known = set()
    for f in files:
        blocks, _ = parse(f)
        known.update(ident(b) for b in blocks if b["prefix"])

    errors = warns = 0
    for f in files:
        lines = load(f)
        blocks, sections = parse(f)
        prefix = doc_prefix(f, blocks)
        want_hint = HINT_FOR[prefix]
        known_authors = roster_of(f)
        e, w, seen, codes = [], [], {}, {}

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
                    e.append((b["line"], f"duplicate id {key} (first at line {seen[key]})"))
                else:
                    seen[key] = b["line"]
            if not b["title"]:
                e.append((b["line"], "missing **bold title**"))
            if prefix == "DEF" and not b["severity"]:
                e.append(
                    (b["line"], "defect not triaged; the body must open with " + "/".join(SEVS))
                )
            elif b["severity"] in SEV_ALIAS:
                e.append(
                    (
                        b["line"],
                        f"foreign severity {b['severity']}; run upgrade "
                        f"(it becomes {SEV_ALIAS[b['severity']]})",
                    )
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
                w.append((b["line"], "no test-tags: line under the item"))
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
                if rid not in known:
                    w.append((lineno, f"{kind} points at {rid}, not found in the scanned files"))

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


def cmd_add(file, code, name, desc, title, text, severity, repro, test, tags, author):
    lines = load(file)
    blocks, sections = parse(file)
    prefix = doc_prefix(file, blocks)
    kind, value = hint_kind_for(file, blocks, repro, test)
    who = need_author(file, author)
    if prefix == "DEF" and not severity:
        raise SystemExit("a defect must be triaged; pass --severity " + "|".join(SEVS))
    if prefix == "ACC" and severity:
        raise SystemExit("acceptance criteria carry no severity")
    code = code.upper()
    if not re.fullmatch(r"[A-Z]{2,6}", code):
        raise SystemExit(
            f"category code {code!r} must be 2-6 uppercase letters; "
            f"three to five is the normal range, six the ceiling"
        )
    sec, lines = section_for(sections, code, name, desc, lines)
    num = next_num(blocks)
    body = f"{severity.upper()}; {text}" if severity else text
    item = f"- [ ] `{prefix}-{code}-{num}` **{title}** - {body}"
    at = insert_index(lines, sec)
    tail = [f"  - {kind}: {value}"] if kind else []
    tail += [f"  - test-tags: {tags}"] if tags else []
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


def cmd_edit(file, wanted, title, text, sev, repro, test, tags, author, evidence=None):
    lines = load(file)
    blocks, _ = parse(file)
    prefix = doc_prefix(file, blocks)
    kind, value = hint_kind_for(file, blocks, repro, test)
    who = need_author(file, author)
    if sev and prefix != "DEF":
        raise SystemExit("acceptance criteria carry no severity")
    if not (title or text or sev or kind or tags or evidence):
        raise SystemExit(
            "nothing to change; pass --title, --text, --severity, "
            "--repro/--test, --test-tags or --evidence"
        )
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    done = []
    if title or text or sev:
        body = b["body"]
        bold = BOLD.search(body)
        cur_title = bold.group(1) if bold else ""
        cur_text = body[bold.end() :].lstrip(" -") if bold else body
        new_text = text if text else cur_text
        if sev:
            new_text = f"{sev}; " + SEV.sub("", new_text).lstrip(" ;:,-")
        elif b["severity"] and not SEV.match(new_text):
            # a --text rewrite must not quietly untriage the defect
            new_text = f"{b['severity']}; {new_text}"
        new = f"`{ident(b)}` **{title or cur_title}** - {new_text}"
        lines[b["line"] - 1] = f"- [{b['state']}] {new}"
        done += [x for x in (title and "title", text and "text", sev and "severity") if x]
    if kind:
        done.append(f"{kind} ({set_line(lines, b, kind, value, HINTLINE)})")
    if tags:
        done.append(f"test-tags ({set_line(lines, b, 'test-tags', tags, TAGLINE)})")
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


def cmd_setstate(file, wanted, target, verb, event, author, evidence=None):
    lines = load(file)
    blocks, _ = parse(file)
    who = need_author(file, author)
    b = find_id(blocks, norm_id(wanted, doc_prefix(file, blocks)))
    if b["state"] == target:
        print(f"{file}:{b['line']}: {ident(b)} already [{target}]; no change")
        return 0
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
    # rather than being asked to hand-edit every log line it inherited
    stamp = need_author(file, author) if author else None
    bare = sum(
        1
        for _, ln in non_fenced(lines)
        if (m := LOGLINE.match(ln)) and not AUTHORED.match(m.group(3).strip())
    )
    plan, taken = [], {s["code"] for s in sections if s["code"]}
    manual = []
    if not roster_of(file):
        manual.append(
            "no ## Authors roster; run "
            f'pm-tools author {file} --handle @xx --name "Full Name" first'
        )
    if bare and not stamp:
        manual.append(
            f"{bare} log line(s) carry no @handle; re-run with "
            f"--author @xx to sign the imported history"
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
            manual.append(
                f"line {s['line']}: category '{s['name']}' needs a description; "
                f"run describe --category {code}"
            )

    # numbers already carried by the doc win, new-style or legacy `DEF-N`; the rest
    # continue above the highest one, so no existing id is ever renumbered or reused
    todo = []
    for b in blocks:
        if b["indent"]:
            manual.append(f"line {b['line']}: nested item must be promoted to its own item")
            continue
        if b["section"] is None or codes[id(b["section"])] is None:
            manual.append(f"line {b['line']}: item sits above any ## category heading")
            continue
        lg = LEGACY.match(b["body"])
        num = b["num"] if b["num"] is not None else (int(lg.group(2)) if lg else None)
        todo.append((b, codes[id(b["section"])], num))

    unproven = sum(1 for b, _, _ in todo if b["state"].lower() == "x" and not b["evidence"])
    if unproven:
        manual.append(
            f"{unproven} closed item(s) carry no evidence: line; add one with "
            f"edit --evidence as each closure is verified"
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
        assign[b["line"]] = (code, num)
        lg = LEGACY.match(b["body"])
        old = ident(b) if b["prefix"] else (f"{lg.group(1)}-{lg.group(2)}" if lg else "(no id)")
        plan.append(f"line {b['line']}: {old} -> {prefix}-{code}-{num}")
        if prefix == "DEF" and not b["severity"]:
            odd = SEVWORD.match(b["plain"])
            why = f"carries an unmapped severity word {odd.group(1)!r}" if odd else "not triaged"
            manual.append(
                f"line {b['line']}: {prefix}-{code}-{num} {why}; run "
                f"pm-tools edit {file} --id {prefix}-{code}-{num} "
                f"--severity {'|'.join(SEVS)}"
            )
        if not author_of(b) and not stamp:
            manual.append(f"line {b['line']}: {prefix}-{code}-{num} has no authored log")

    out, drop_toc, converted, widened, renamed = [], False, 0, 0, {}
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
            code, num = assign[i]
            m = ITEM.match(ln)
            body = m.group(3)
            idm = IDTOK.match(body)
            if idm:
                body = idm.group(4)
            else:
                lg = LEGACY.match(body)
                if lg:
                    body = lg.group(3)
            bm = BOLD.search(body)
            lead, after = (body[: bm.end()], body[bm.end() :]) if bm else ("", body)
            rest = after.lstrip(" -")
            gap = after[: len(after) - len(rest)]
            sm = SEV.match(rest)
            if sm and sm.group(1).upper() in SEV_ALIAS:
                was = sm.group(1).upper()
                rest = SEV_ALIAS[was] + rest[sm.end() :]
                body = lead + gap + rest
                renamed[was] = renamed.get(was, 0) + 1
            out.append(f"- [{m.group(2).lower()}] `{prefix}-{code}-{num}` {body}")
            continue
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
    if renamed:
        plan.append(
            "severity renamed: "
            + ", ".join(f"{w} -> {SEV_ALIAS[w]} x{n}" for w, n in sorted(renamed.items()))
        )
    if stamp and bare:
        plan.append(f"{bare} unauthored log line(s) signed {stamp}")

    for p in plan:
        print(p)
    for m in manual:
        print(f"MANUAL {m}", file=sys.stderr)
    if not apply:
        print(f"\ndry run: {len(plan)} change(s), {len(manual)} manual. Re-run with --apply")
        return 0
    save(file, out)
    print(f"\napplied {len(plan)} change(s) to {file}; {len(manual)} need a hand. Run check next")
    return 0


# -------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv
    ap = argparse.ArgumentParser(
        prog="pm-tools", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", metavar="COMMAND")

    for name in ("report", "list-categories", "list", "refs", "check"):
        sp = sub.add_parser(name)
        sp.add_argument("paths", nargs="*")
        if name == "report":
            sp.add_argument("--category", help="narrows the whole report to one code")
            sp.add_argument(
                "--severity",
                type=str.upper,
                choices=SEVS,
                help="narrows the whole report to one level; defect documents only",
            )
            sp.add_argument(
                "--status",
                choices=("open", "closed", "rejected", "all"),
                help="which items ITEMS lists; open by default",
            )
            sp.add_argument(
                "--dates",
                choices=("filed", "closed", "updated"),
                default="filed",
                help="which log stamp --since/--until read; filed by default",
            )
            sp.add_argument("--since", metavar="YYYY-MM-DD", help="on or after, inclusive")
            sp.add_argument("--until", metavar="YYYY-MM-DD", help="on or before, inclusive")
            sp.add_argument(
                "--detail",
                action="store_true",
                help="one readable block per item instead of the table",
            )
            sp.add_argument(
                "--plain",
                action="store_true",
                help="the grids alone - no blurbs, categories or coverage",
            )
            sp.add_argument(
                "--summary",
                action="store_true",
                help="stop at the SUMMARY grid; list no items. Implies --plain",
            )
        if name == "list":
            g = sp.add_mutually_exclusive_group()
            g.add_argument("--open", action="store_true")
            g.add_argument("--closed", action="store_true")
            g.add_argument("--rejected", action="store_true")
            sp.add_argument("--category")
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

    a = ap.parse_args(argv[1:])
    if not a.cmd:
        ap.print_help()
        return 0

    if a.cmd in ("report", "list-categories", "list", "refs", "check"):
        files = resolve(a.paths)
        if not files:
            print("no acc-crit*.md or defects*.md found", file=sys.stderr)
            return 2
        if a.cmd == "report":
            for v in (a.since, a.until):
                if v and not DATEONLY.match(v):
                    raise SystemExit(f"--since/--until take YYYY-MM-DD, got {v!r}")
            return cmd_report(
                files,
                a.category,
                a.status,
                a.detail,
                a.severity,
                a.dates,
                a.since,
                a.until,
                a.plain,
                a.summary,
            )
        if a.cmd == "list-categories":
            return cmd_list_categories(files)
        if a.cmd == "list":
            state = " " if a.open else "x" if a.closed else "-" if a.rejected else None
            return cmd_list(files, state, a.category)
        if a.cmd == "refs":
            return cmd_refs(files, a.id.strip().upper())
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
