**On the Nature of Merge Conflicts: A Study of 2,731 Open Source Java Projects Hosted by GitHub
(2020)**

A large-scale characterisation of what merge conflicts actually contain and how developers actually
resolve them. Merge conflict rates of 10% to 20% were already known, but not what the conflicts look
like in detail. The authors manually analysed five project histories to build a classification, then
automated that analysis across 2,731 open-source Java projects covering 25,328 failed merges. Each
conflicting chunk is characterised by its size, the language constructs involved, and which of six
resolution strategies the developer chose. The headline conclusion is deflationary for automation -
too many resolutions are unpredictable for a fully automatic merge tool to be plausible - but the
distribution of resolutions is highly skewed toward reusing lines that are already present, which is
what makes tool assistance and history-based suggestion viable. Published in IEEE Transactions on
Software Engineering.

**Key mechanism**
- Unit of analysis is the conflicting chunk, not the failed merge, since one failed merge often
  contains several independent conflicts
- Six resolution strategies are coded: take version 1, take version 2, concatenate both, combine
  lines from both, write new code, or use none of the conflicting lines
- Strategies are grouped as straightforward (version 1, version 2, concatenation, none) or complex
  (combination, new code), on the argument that the latter demand more developer effort
- Conflicts are also characterised by the Java language constructs involved, using the language
  specification to define the construct vocabulary
- The manual pass over five projects seeds and validates the classification that the automated pass
  applies at scale

**Main findings**
- 10% to 20% of merge attempts fail across the literature, with some projects reaching nearly 50%
- For 87% of conflicting chunks, the merged result contained only lines already present in the
  chunk, so no new code was written
- In 94% of those cases, each version of the chunk was under 50 lines
- 60% of failed merges involved more than one conflicting chunk
- Depending on the project, 14% to 46% of multi-chunk failed merges had dependencies between chunks,
  where resolving one indicates how to resolve the rest - a declaration conflict and its
  corresponding invocation conflicts, for example
- Resolution behaviour is patterned by project and by individual: one project resolved nearly 20% of
  chunks with new code while some developers in it rarely chose that strategy at all
- Certain conflict kinds attract certain strategies consistently across projects, independent of
  individual preference
- The authors conclude fully automated merging is likely impossible, because a substantial tail of
  resolutions cannot be anticipated from the conflict alone
- The three recommendations that follow are heuristics for common cases, dependency-ordered
  presentation of chunks, and surfacing the historical distribution of past choices to the developer

**Key takeaways**
- Most conflict resolution is selection among material already in the file, not authorship of new
  material, which is what makes assisted resolution tractable
- Conflicts are small - under 50 lines per side in the overwhelming majority - so the context needed
  to resolve one is local, not project-wide
- Past resolutions predict future ones well enough to be worth surfacing, which is an argument for
  keeping decision history rather than only current state
- Chunk order matters: resolving a dependency-linked chunk first can determine the others, so
  presenting conflicts in arbitrary order wastes effort
- Do not promise full automation; the reachable goal is reducing the manual portion, and the paper
  is explicit that a tail will remain
- Scope is Java and unstructured line-based merging on GitHub, so the construct-level findings are
  language-specific even where the size and strategy distributions may generalise
- Failed merges are reconstructed from history, so what is observed is the committed resolution, not
  the process the developer went through to reach it

**Relevance**
- Supports resolving conflicts on a shared tracked file from the file's own content: the dominant
  case is choosing among lines already present, which is exactly what an append-only log of stamped,
  attributed events makes decidable
- Bounds the claim honestly - this measures Java source conflicts, not markdown checklist conflicts,
  and it explicitly denies that any tool resolves the whole distribution, so "no server needed" must
  not be read as "always resolvable"

**Tags**
- #version-control
- #merge-conflicts
- #empirical-software-engineering

**Source**
- https://doi.org/10.1109/TSE.2018.2871083
