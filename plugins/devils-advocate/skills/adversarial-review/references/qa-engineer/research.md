# qa-engineer research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Risk-based test effort
- [Felderer, Schieferdecker 2014](https://arxiv.org/abs/1912.11519) - risk assessment steers all test phases; effort goes where risk is

## Tier mix and gaps
- [SWE at Google ch11 2020](https://abseil.io/resources/swe-book/html/ch11.html) - ~80/15/5 unit/integration/e2e; hourglass = unit + e2e, no integration

## Placement and duplication
- [Vocke Practical Test Pyramid 2018](https://martinfowler.com/articles/practical-test-pyramid.html) - push tests down; no duplicate layers; high-level-only catch → add lower test

## Tier gating
- [Fowler Continuous Integration 2024](https://martinfowler.com/articles/continuousIntegration.html) - ten-minute commit build; slower tests in later stages; fix red first
- [Fowler ContractTest 2011](https://martinfowler.com/bliki/ContractTest.html) - check doubles against real service; daily enough; need not break build

## Mutation adequacy
- [Petrović et al. TSE 2021](https://arxiv.org/abs/2102.11378) - mutants on changed code in review; filter unproductive; cap per line

## Test doubles
- [SWE at Google ch13 2020](https://abseil.io/resources/swe-book/html/ch13.html) - prefer real, then fake; state over interaction; don't mock unowned types

## Regression pinning
- [Feathers Characterization Testing 2016](https://michaelfeathers.silvrback.com/characterization-testing) - pin actual current behaviour before change, not wished-for behaviour

## Parametrized tests
- [Go wiki TableDrivenTests](https://go.dev/wiki/TableDrivenTests) - one table of named cases; failure names input; t.Errorf reports all
- [SWE at Google ch12 2020](https://abseil.io/resources/swe-book/html/ch12.html) - DAMP over DRY; no loops or conditionals in tests; clear failure message

## Brittle tests
- [SWE at Google ch12 2020](https://abseil.io/resources/swe-book/html/ch12.html) - test via public API, assert state; test changes only when requirements change

## Flake sources
- [Fowler Non-Determinism 2011](https://martinfowler.com/articles/nonDeterminism.html) - quarantine then fix fast; poll, never bare sleep; wrap clock; isolate order

## Coverage vs effectiveness
- [Inozemtseva, Holmes 2014](https://www.cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf) - coverage weakly predicts effectiveness once suite size controlled; not a target

Unsourced: harness reinvention vs standard tools; tests verifying the library; unread golden/snapshot files
