# architect research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Convention consistency
- [PEP 8](https://peps.python.org/pep-0008/) - module consistency beats project beats guide; readability overrides

## Single source of truth
- [Hunt, Thomas DRY](https://www.artima.com/articles/orthogonality-and-the-dry-principle) - one authoritative representation per knowledge item, not just code

## Leaky and wrong abstractions
- [Spolsky 2002](https://www.joelonsoftware.com/2002/11/11/the-law-of-leaky-abstractions/) - all non-trivial abstractions leak; callers still learn lower layer
- [Metz Wrong Abstraction 2016](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction) - bounds DRY: abstraction grown by flag parameters → re-inline into callers

## Separation of concerns
- [Dijkstra EWD447 1974](https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD447.html) - study one concern (correctness, efficiency) at a time

## Configuration plane
- [Replace Magic Literal](https://refactoring.com/catalog/replaceMagicLiteral.html) - unexplained literal → named constant
- [Twelve-Factor Config](https://12factor.net/config) - bounds above: deploy-varying values, credentials → env; internal config stays in code

## Security smells
- [Saltzer, Schroeder 1975](https://www.cs.virginia.edu/~evans/cs551/saltzer/) - least privilege; permission not exclusion; check every access
- [OWASP Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html) - server-side allowlist; never primary injection defence

## Error handling
- [Yuan et al. OSDI 2014](https://petertsehsun.github.io/soen691/current/papers/osdi14-paper-yuan.pdf): "Almost all catastrophic failures (92%) are the result of incorrect handling of non-fatal errors explicitly signaled in software." Rule: error handlers = top review target. Tell: empty or log-only handler; catch `Exception`/`Throwable` then abort; TODO/FIXME in handler.

## Speculative structure
- [Fowler Yagni 2015](https://www.martinfowler.com/bliki/Yagni.html) - presumptive feature costs build, delay, carry, repair; change-easing work exempt

## Exposed surface
- [Hyrum's Law](https://www.hyrumslaw.com/) - users depend on every observable behaviour, contract or not

## Naming
- [Linguistic Antipatterns](https://www.linguistic-antipatterns.com/) - name, docs, behaviour disagree = recurring defect impairing understanding

## Advertised surface drift
- [Outdated doc references 2022](https://arxiv.org/abs/2212.01479): "We analysed over 3,000 GitHub projects and found that most projects contain at least one outdated code element reference at some point in their history." Rule: stale doc references normal, not rare; check each named element exists. Tell: README, docstring or help text naming symbol, flag or route absent from code.

Unsourced: dead code harm, documentation over-structure
