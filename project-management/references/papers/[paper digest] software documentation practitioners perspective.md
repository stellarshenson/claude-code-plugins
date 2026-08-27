**Software Documentation: The Practitioners' Perspective (2020)**

Two surveys of 146 professional practitioners, run to check an academic taxonomy of documentation
issues against what working engineers actually experience. Most respondents (125) came from ABB, a
multinational automation company, with 21 recruited from specialist forums, spanning developer,
tester and lead roles. The first survey asked which documentation issues practitioners find relevant
and what they do when those issues arise; the second asked which documentation types matter for
which tasks. The paper's usefulness outside documentation-tooling research is its measurement of two
specific failure modes: information that has drifted out of step with the system it describes, and
information duplicated across places that then diverge. Both are reported as top recurring problems
rather than theoretical risks, with practitioner-supplied percentages attached.

**Key mechanism**
- The instrument is a prior taxonomy of documentation issues, derived from mining developer
  discussions, presented to practitioners for relevance rating
- Survey one rates each taxonomy issue for importance and asks for the workaround actually applied
- Survey two maps documentation types onto concrete engineering tasks, so importance is measured per
  task rather than in the abstract
- Reported percentages are the share of surveyed practitioners rating an issue important, not
  incidence rates in a corpus, and the two should not be read interchangeably
- Findings are cross-checked against earlier mining studies, and the paper marks where they agree

**Main findings**
- Inconsistency between code and documentation was rated important by 59% of practitioners and is
  named one of the top recurring issues they face
- Clone and duplicate content was a main maintainability concern for 46% of practitioners, and
  superfluous content for 55%; the two together account for roughly 71% of developer discussion on
  documentation maintainability in the authors' earlier mining study
- Missing documentation for a new feature or component was both the most important up-to-dateness
  issue (69%) and the most recurring one
- Outdated installation instructions were rated important by 54% and outdated examples by 51%
- Not all staleness matters equally: outdated version information (32%), screenshots (29%),
  license or copyright text (26%) and translations (19%) all fell well below the rest
- Documentation clarity was the single most important issue overall at 88%
- Information Content is the dominant taxonomy category at 55% of issues, with presentation and
  organisation at 29%, tooling at 15% and process at 9%
- Only 7 of 23 Information Content issues (30%) cleared a 60% importance threshold, while 9 (39%)
  fell below 40%, which the authors read as evidence the taxonomy is broader than practitioner need
- One practitioner's proposed remedy for staleness is to keep comments to the minimum needed, on the
  reasoning that less duplicated detail is easier to co-evolve with the code

**Key takeaways**
- Duplication is not a tidiness concern; it is the reported mechanism by which two descriptions of
  the same system stop agreeing, and it is expensive enough to dominate maintainability complaints
- A design that stores each fact once removes the class of problem this survey measures, rather than
  mitigating it, which is a stronger position than any reconciliation tooling can reach
- Minimising what is written down is a practitioner-endorsed staleness remedy, not only an
  aesthetic preference
- Staleness should be triaged, not treated uniformly - practitioners care about drifted instructions
  and examples far more than about drifted version strings or screenshots
- Clarity outranks every other property measured, so terseness is only a virtue when it does not
  cost comprehensibility
- The population is heavily one company (86% ABB) in industrial automation, so the distribution of
  concerns may not transfer to open-source or web-service contexts
- Self-reported importance is not observed incidence; the paper measures what practitioners say
  hurts, and treats that as the prioritisation signal for tool builders

**Relevance**
- Supplies the measured basis for the claim that two stores of the same facts drift apart, and for
  storing each fact exactly once
- Note the scope: the paper measures documentation-versus-code drift. Where the project's README
  invokes model-driven architecture, that is an analogy for the two-representation split, and this
  citation carries the measurement rather than any MDA-specific claim
- Also supports keeping entries short, but with the clarity finding (88%) as a stated limit on how
  far terseness should be pushed

**Tags**
- #documentation
- #empirical-software-engineering
- #consistency

**Source**
- https://doi.org/10.1145/3377811.3380405
