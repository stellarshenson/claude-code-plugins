**Literate Programming (1984)**

Knuth's proposal that a program be written as a single document addressed to human readers, from
which the machine-readable form is derived rather than maintained alongside it. The paper presents
the WEB system built at Stanford, in which one source file contains prose, typesetting markup and
program code interleaved in whatever order best explains the design, and two processors extract the
two audiences' views from it. The problem it addresses is that documentation maintained separately
from code is a second artefact that must be kept in step and generally is not. The proposed answer
is structural: there is only one artefact, so there is nothing to keep in step. The paper is an
experience report and a design argument, explicitly personal in tone, not an empirical study, and
Knuth says so directly.

**Key mechanism**
- A WEB source file is bilingual: a document formatting language (TeX in the prototype) and a
  programming language (Pascal in the prototype), with neither treated as embedded in the other
- TANGLE reads the WEB file and emits compilable program source, machine-ordered and deliberately
  not human-readable, since nobody is meant to read it
- WEAVE reads the same WEB file and emits a typeset document with cross-references, an index and
  section numbering generated automatically
- The author orders sections for human understanding rather than for the compiler; the macro-like
  section references let TANGLE reassemble them into the order the language requires
- Both languages are pluggable - Knuth names Scribe or troff in place of TeX, and Ada, ALGOL, LISP,
  COBOL, FORTRAN, APL, C or assembly in place of Pascal, so the idea is not tied to either choice

**Main findings**
- One source, two derived outputs, is sufficient: the documentation cannot fall out of step with the
  code because neither is the source, and both are generated from it
- Ordering for the reader and ordering for the compiler are different problems, and separating them
  is what makes the prose readable without making the program invalid
- Indexes and cross-references are computed by WEAVE rather than maintained by hand, which is the
  same argument in miniature - a hand-kept index is a second store that drifts
- Knuth reports the resulting programs are better, not merely better explained, attributing this to
  the discipline the format imposes; this is a first-person claim with no measurement behind it
- The bilingual format has a real cost: errors can arise in TeX, in WEB, in Pascal syntax or in the
  algorithm, and telling them apart takes practice
- Knuth is explicit about narrow applicability, calling WEB suited to "the subset of computer
  scientists who like to write and to explain what they are doing"
- The paper is written to persuade, and warns the reader to discount some of it as enthusiasm

**Key takeaways**
- The durable idea is generation over synchronisation: derive every view from one stored artefact
  rather than maintaining views and reconciling them
- Computed indexes and cross-references are the cheapest instance of that idea and the easiest to
  adopt independently of anything else in the proposal
- A format serving both a human reader and a machine reader is a design that has been in practical
  use since 1984, not a recent idea, and the failure modes are known
- The tax is real - a multi-language source multiplies the kinds of error a reader must distinguish,
  which argues for keeping the machine-readable grammar small
- Adoption evidence is absent; the paper offers no study, no user population and no comparison, so
  it supports the design argument and not any claim about outcomes
- Literate programming as Knuth defined it did not become general practice, which is context worth
  carrying alongside any citation of it

**Relevance**
- The canonical source for one document serving a human reader and a parser at once, which is the
  design this project's markdown store rests on
- Bounds the claim: this is a design argument and experience report from one author, so it
  establishes that the approach is well-founded and long-standing, not that it performs better
- Knuth's direction is the inverse of this project's - prose as the source with code derived from
  it, rather than a fixed grammar parsed by a tool - so the shared premise is the single artefact,
  not the mechanism

**Tags**
- #literate-programming
- #documentation
- #single-source

**Source**
- https://doi.org/10.1093/comjnl/27.2.97
