# slop-hunter research

Fetched 2026-09-03. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Duplication over reuse
- [GitClear 2026](https://www.gitclear.com/the_ai_code_quality_maintainability_gap) - copy/paste 15.7% vs moved code 3.8%, H1 2026, 623M changes

## Test value
- [Hora & Robbes MSR 2026](https://arxiv.org/abs/2602.00409): "36% of commits made by coding agents add mocks to tests, compared with 26% by non-agents". Rule: agents add mocks more often than non-agents; each mock must replace real I/O. Tell: `patch`/`MagicMock` on in-process collaborator.
- [Chen et al. 2026](https://arxiv.org/abs/2602.07900): "mainly serve as observational feedback channels, with value-revealing print statements appearing much more often than assertion-based checks". Rule: agent tests mostly print probes; writing tests does not predict resolution. Tell: test prints computed value, no assert.
- [MUTGEN 2025](https://arxiv.org/abs/2506.02954) - some suites: 100% coverage, 4% mutation score; coverage no proxy

## Fake passes
- [SWE-ABS 2026](https://arxiv.org/abs/2603.00520): "rejects 19.71% of previously passing patches". Rule: green suite weak evidence; strengthened tests reject ~1 in 5 passing patches. Tell: fix handles tested inputs; issue case outside tests still fails.
- [Opus 4.5 system card 2025](https://www-cdn.anthropic.com/bf10f64990cfda0ba858290be7b8cc6317685f47.pdf): "Do not hard code any test cases". Rule: impossible-task hack rate 55% unprompted, 35% with prompt containing this line. Tell: green suite on infeasible task, no infeasibility report.
- [Baker et al. 2025](https://arxiv.org/abs/2503.11926) - hacks include parsing expected values from test files, overwriting local library copies

## Scope and change size
- [RECAP 2026](https://arxiv.org/abs/2608.13292): "even successful patches are consistently larger and more complex than developer patches". Rule: correct agent patch median +121.78% total changes, +43.99% cyclomatic complexity. Tell: passing fix adds branches, helpers or files minimal fix lacks.
- [Agents Don't Know When to Act 2026](https://arxiv.org/abs/2605.07769): "undesirable changes (excluding tests and documentation) in 35 to 65% of cases". Rule: on stale bug reports agents still change code; reproduce on main first. Tell: fix PR for issue already passing on main.
- [Tang et al. 2026](https://arxiv.org/abs/2605.29442) - 16,118 agent episodes: developer constraint violation 38.33%, self-initiated overreach 10.20%
- [AI code in real repos 2026](https://arxiv.org/abs/2603.27130): "real-world AI-Human differences on code-level metrics are rather small". Rule: machine-change signal sits in commit size and stability, not line style. Tell: finding infers AI authorship from style; diff size against request unmeasured.

## Unverified claims
- [Tang et al. 2026](https://arxiv.org/abs/2605.29442): "prematurely claim success, completion, or readiness". Rule: 22.58% of agent episodes self-report inaccurately; claim without command output unverified. Tell: "all tests pass" with no matching tool output.

## Hallucinated packages and APIs
- [Spracklen et al. USENIX Security 2025](https://arxiv.org/abs/2406.10279) - package hallucination at least 5.2% commercial, 21.7% open-source
- [CloudAPIBench 2024](https://arxiv.org/abs/2407.09726) - low-frequency APIs: GPT-4o invokes validly 38.58%; check rare calls first

## AI-slop prose tells
- [Wikipedia Signs of AI writing 2026](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) - promotional vocabulary, negative parallelism, rule of three, vague attribution, outline-like conclusions
