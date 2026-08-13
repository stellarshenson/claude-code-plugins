# EDGAR-CORPUS, restricted slice (non-S&P-500 filers, filing year >= 2020)

The only corpus carrying 10-K management-discussion discourse at volume, which the
R14 register-gap audit measured as the largest finqa-side training deficit - 904 rows carrying
financial vocabulary, 0.13% of the mix, against 50.3% of finqa arena rows, a 382x gap. Admitted
only as a restricted slice, because raw EDGAR sits on the same document population FinQA was
built from.

- **Source** - `eloukas/edgar-corpus` on HuggingFace; the year-2020 `train` /
  `validate` / `test` shards fetched as raw JSONL from the Hub resolve endpoint
- **Licence** - Apache-2.0 (HuggingFace dataset tag); the underlying 10-K filings are US
  government-published public records carrying no copyright
- **Restriction** - **non-S&P-500 filers AND filing year >= 2020, both clauses, no relaxation**.
  EDGAR-CORPUS ends at 2020, so the year clause selects the `2020` shards alone; the filer clause
  drops every CIK resolving to an S&P 500 constituent at any point in 1999-2019
- **Reason for the restriction** - FinQA's source population is S&P 500 annual reports 1999-2019,
  reached via FinTabNet. Excluding those filers and those years makes the slice document-disjoint
  from FinQA's population by company and by year, which is what turns the corpus from SUSPECT-HIGH
  into gateable
- **S&P 500 exclusion list** - union of constituents over 1999-2019 from `fja05680/sp500`
  (`S&P 500 Historical Components & Changes.csv`), tickers resolved to CIK through the SEC's
  `company_tickers.json`: 981 distinct tickers, 550 resolving to 546 distinct CIKs, 431
  unresolved because the company no longer trades under that ticker
- **Size** - **6,379 filings kept** of 6,851 raw 2020 filings; 472 dropped by the S&P 500 clause,
  0 by the year clause (the 2020 shards are already year-pure). 4,384 of the survivors carry an
  MD&A section over 500 characters. Full breakdown in `edgar-restricted/_counts.json`
- **Languages** - English
- **How negatives were made** - none ship with the corpus; it arrives as unlabeled clean prose and
  negatives are manufactured by the admitted DR corruption engine at lane build
- **How labels were made** - unlabeled
- **Mapping onto our task** - section_7 (MD&A) prose chunked to the project's 1,500-char window →
  evidence; claims manufactured at lane build

## Caveats

The 8-gram Jaccard provenance gate against the finqa and tatqa arena documents
(`experiments/grounding-semantic/provenance_gate.py`, the SciFact gate pattern, KILL at > 2%
overlap) has **not** run at fetch time - it runs at LANE BUILD, and the slice enters no training
mix until it passes.

The S&P 500 exclusion resolves historical tickers through a present-day SEC ticker-to-CIK map, so
constituents delisted, acquired or renamed before that map was published do not resolve and are
not excluded. The provenance gate is the backstop for that residue.

This slice overturns the standing no-EDGAR ruling for itself alone (`R10-H108_gate_report.md`);
the ban stands for every other EDGAR packaging.

## Provenance

Admitted by the author's ruling of 2026-08-09, clause 1 ("EDGAR admit-with-restriction"). The
corpus is rated register fit A-strong and provenance-wall verdict SUSPECT-HIGH; the restriction
above is exactly the filter that turns it into something gateable.

Fetched by `scripts/fetch_register_corpora.py edgar-restricted`. The downloaded data under
`data/external/grounding-datasets/edgar-restricted/` is gitignored; this sidecar is tracked.
