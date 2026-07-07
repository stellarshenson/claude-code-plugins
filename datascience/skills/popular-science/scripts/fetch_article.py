#!/usr/bin/env python3
"""Fetch a reference / exemplar article into the popular-science skill, license-aware.

Delivering this as a tool keeps the download OUT of the model's context - the agent
runs it instead of ingesting HTML, saving tokens. Licensing is enforced here, not left
to judgement:

- Permissive verbatim-redistributable license (CC-BY, CC-BY-SA, CC-BY-ND, CC0,
  public-domain) -> save the full article text verbatim with an attribution + license
  header.
- Proprietary / unknown / NonCommercial (CC*-NC*) -> save ONLY a stub (title, author,
  outlet, url, license, retrieved date) plus a teardown template. The body is NOT
  bundled; your own teardown + short fair-use excerpts + the link stay in examples/.

Every run also appends a row to examples/downloaded/ATTRIBUTION.md.

Usage:
  python fetch_article.py URL --license CC-BY-4.0 --name "deadliest animals" \
      --author "Ritchie & Roser" --outlet "Our World in Data"
  python fetch_article.py URL --license proprietary --name "algorithms memory" \
      --author "Kevin Hartnett" --outlet "Quanta Magazine"      # -> stub only

Exit codes: 0 saved (verbatim or stub), 2 fetch/parse error, 3 bad arguments.
"""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path
import re
import sys
import urllib.request

# Licenses that permit bundling a verbatim copy (ND is fine - verbatim is not a derivative;
# SA is fine for verbatim; NC is deliberately excluded because a published plugin is a grey area).
BUNDLE_OK = re.compile(
    r"^(cc0|public[- ]?domain|cc[- ]?by([- ]?(sa|nd))?([- ]?\d(\.\d)?)?)$", re.I
)
UA = "Mozilla/5.0 (popular-science skill; article archival for reference)"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - explicit http(s) only
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError("only http(s) URLs")
        return r.read().decode("utf-8", "replace")


def extract(html: str) -> tuple[str, str]:
    """Return (title, body_text). Prefer bs4; fall back to a regex strip."""
    try:
        from bs4 import BeautifulSoup  # optional dependency
    except ImportError:
        title = (re.search(r"<title>(.*?)</title>", html, re.S | re.I) or [None, ""])[1]
        text = re.sub(r"(?is)<(script|style|nav|header|footer|aside).*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = re.sub(r"\s+\n", "\n", re.sub(r"[ \t]+", " ", text))
        return title.strip(), text.strip()

    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string if soup.title else "") or ""
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    root = (
        soup.find("article")
        or soup.find(attrs={"itemprop": "articleBody"})
        or soup.find("main")
        or soup.body
        or soup
    )
    parts: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        txt = el.get_text(" ", strip=True)
        if not txt:
            continue
        if el.name in ("h1", "h2", "h3"):
            parts.append(("#" * int(el.name[1])) + " " + txt)
        elif el.name == "li":
            parts.append("- " + txt)
        else:
            parts.append(txt)
    return title.strip(), "\n\n".join(parts)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url")
    ap.add_argument("--license", required=True, help="SPDX-ish id or 'proprietary'")
    ap.add_argument("--name", required=True, help="short human name -> filename slug")
    ap.add_argument("--author", default="")
    ap.add_argument("--outlet", default="")
    ap.add_argument(
        "--outdir",
        default=str(Path(__file__).resolve().parent.parent / "examples" / "downloaded"),
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    bundle = bool(BUNDLE_OK.match(args.license.strip()))
    slug = slugify(args.name)

    try:
        html = fetch(args.url)
        title, body = extract(html)
    except Exception as e:  # noqa: BLE001 - report and exit non-zero
        print(f"fetch/parse failed: {e}", file=sys.stderr)
        return 2

    header = (
        f"<!--\nsource: {args.url}\ntitle: {title}\nauthor: {args.author}\n"
        f"outlet: {args.outlet}\nlicense: {args.license}\nretrieved: {today}\n-->\n\n"
        f"# {title or args.name}\n\n"
        f"> {args.outlet}{' - ' if args.outlet and args.author else ''}{args.author}. "
        f"Source: <{args.url}>\n"
    )

    out = outdir / f"{slug}.md"
    if bundle:
        notice = (
            f"> Reproduced verbatim under {args.license}, retrieved {today}. "
            f"No modifications. Attribution above.\n\n"
        )
        out.write_text(header + notice + body + "\n", encoding="utf-8")
        kind = "verbatim"
    else:
        stub = (
            f"> License **{args.license}** - full text NOT bundled. Link + attribution "
            f"only; keep commentary and short fair-use excerpts in `examples/teardowns.md`.\n\n"
            f"## Teardown (fill in from the link)\n"
            f"- **Hook** -\n- **Nut graf** -\n- **Structure** -\n- **Sourcing** -\n"
            f"- **Imagery** -\n- **Kicker** -\n- **Why it works** -\n"
        )
        out.write_text(header + stub, encoding="utf-8")
        kind = "stub"

    attr = outdir / "ATTRIBUTION.md"
    if not attr.exists():
        attr.write_text(
            "# Attribution and licenses\n\n"
            "Every bundled or referenced article, its license, and how it is stored.\n\n"
            "| Name | Outlet | Author | License | Stored | Source |\n"
            "|------|--------|--------|---------|--------|--------|\n",
            encoding="utf-8",
        )
    row = (
        f"| {args.name} | {args.outlet} | {args.author} | {args.license} | "
        f"{kind} | <{args.url}> |\n"
    )
    with attr.open("a", encoding="utf-8") as fh:
        fh.write(row)

    print(f"{kind}: {out}  (license={args.license})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
