# analyst research

Fetched 2026-09-15. Reference = model knows it; open source only if unsure. Full entry = model did not know it; cite the quote.

## Coverage matrix
- [Ostrand, Balcer 1988](https://doi.org/10.1145/62959.62964) - category-partition: tests from spec; constraints cap combination count

## ISO 29148 characteristics
- [29148:2018 table, Lubos 2024](https://arxiv.org/html/2408.10886) - Verifiable: provable, ideally measured; Singular: one aspect; Appropriate: no implementation details

## Verifiability
- [INVEST, Wake 2003](https://xp123.com/invest-in-good-stories-and-smart-tasks/) - customer cannot test it → story unclear, not valuable, or needs help

## Requirements smells
- [Femmer et al. 2017](https://doi.org/10.1016/j.jss.2016.02.047) - ISO 29148-based smells; precision 59%, recall 82%; supplement to review
- [Alem et al. Sci Rep 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11833090/): "Beer and Felder introduced passive voice in 2017 and Morteza introduced uncertain verbs and polysemy in 2024". Rule: passive voice = later extension, not Femmer or ISO 29148 smell. Tell: finding cites Femmer or ISO 29148 for passive voice.

## Singularity
- [Cucumber anti-patterns](https://cucumber.io/docs/guides/anti-patterns/) - conjunction steps block step reuse; singular criteria rest on ISO 29148

## Design in requirements
- [Zave, Jackson 1997](https://www.pamelazave.com/fre.html) - requirements describe environment only; machine internals not requirements

## Traceability
- [Gotel, Finkelstein 1994](https://doi.org/10.1109/ICRE.1994.292398) - most traceability problems pre-RS (requirement origin), not spec→code links

## Gold plating
- [Wiegers, 10 Requirements Traps 2000](https://www.cs.hmc.edu/~mike/courses/mike121/readings/requirements/reqtraps.html) - cut functionality not tracing to use case, business rule, user task

## Non-functional coverage
- [ISO/IEC 25010:2023, arc42](https://quality.arc42.org/standards/iso-25010) - sweep nine characteristics; safety new; usability→interaction capability, portability→flexibility
