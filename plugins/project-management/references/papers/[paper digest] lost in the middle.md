**Lost in the Middle: How Language Models Use Long Contexts (2024)**

A controlled study of whether models actually use the long contexts they accept. The authors hold
the task fixed and vary two things: how much text is in the context, and where in it the relevant
information sits. Two settings are used - multi-document question answering, which mirrors
retrieval-augmented generation, and a synthetic key-value retrieval task. The result is a U-shaped
accuracy curve: models are best when the needed information is at the very start or the very end of
the context and markedly worse when it is in the middle. Accuracy also falls as the context grows,
including for models marketed on extended context length. The practical consequence is that context
capacity and context utility are different quantities, and the first is not evidence of the second.
Published in Transactions of the Association for Computational Linguistics, volume 12.

**Key mechanism**
- Multi-document QA: the context holds exactly one document containing the answer plus k distractors,
  so both context length and answer position can be varied independently of task difficulty
- Position is manipulated by reordering documents to put the answering one first, middle or last;
  length is manipulated by changing k, giving roughly 1.5k, 3k and 4.4k tokens for 10, 20 and 30
  documents
- A synthetic key-value retrieval task strips away all semantics, isolating the positional effect
  from any language understanding the QA task might involve
- Evaluated across open models (MPT-30B-Instruct, LongChat-13B 16K, Llama-2 at 7B/13B/70B with and
  without instruction tuning) and closed ones (GPT-3.5-Turbo and its 16K variant, Claude-1.3 and its
  100K variant)
- An open-domain case study pairs a real retriever over Wikipedia with these models as readers, to
  see whether the controlled effect shows up in a deployed-style pipeline

**Main findings**
- Accuracy traces a U-shape against answer position: highest at the beginning (primacy) and the end
  (recency), lowest in the middle
- With the answer in the middle of its context, GPT-3.5-Turbo scores below its own closed-book
  performance of 56.1%, meaning the retrieved documents actively hurt rather than help
- Extended-context variants frequently match their base counterparts, so a larger stated window does
  not by itself improve context use
- Performance falls as context grows regardless of where the answer sits, so length and position are
  two separate penalties
- In the retriever-reader study, reader performance saturates long before retriever recall does:
  moving from 20 to 50 retrieved documents gains roughly 1.5% for GPT-3.5-Turbo and 1% for
  Claude-1.3, while multiplying input length, latency and cost
- Query-aware contextualization (repeating the query before and after the content) nearly solves the
  synthetic key-value task but barely shifts the multi-document QA trend
- Base models without instruction tuning show the same U-shape, so the effect is not an artefact of
  instruction fine-tuning; Llama-2 70B with and without fine-tuning show similar positional bias
- The authors propose that any claim of robust long-context use must show a small gap between
  best-case and worst-case answer position, not merely a high maximum

**Key takeaways**
- Treat context capacity as an upper bound, not a working budget; filling it degrades the result
  measurably
- Retrieving more is not free and is often not better - past roughly 20 documents the returns are
  around 1%, paid for in full token cost
- Give a model the rows it needs rather than the document that contains them; the discipline that
  matters is selection, not window size
- Where information sits in the prompt is a design variable, and putting the decisive material at
  the edges rather than buried mid-context is a cheap intervention
- Benchmark long-context claims by best-versus-worst position spread; a single averaged number hides
  exactly the failure this paper isolates
- Model set is 2023-era; the positional mechanism is likely durable but the specific magnitudes
  should not be quoted as current
- The multi-document setting guarantees exactly one relevant document, which is cleaner than real
  retrieval, so the controlled numbers are an optimistic bound on deployed behaviour

**Relevance**
- The direct support for keeping the tracker file out of the context window and returning only
  queried rows; the failure mode it documents is precisely what pasting a whole document would
  invite
- Also argues the CLI-mediated read is the substantive design choice rather than an implementation
  detail, since selection is what the paper shows to matter

**Tags**
- #long-context
- #retrieval
- #llm-evaluation

**Source**
- https://aclanthology.org/2024.tacl-1.9/
