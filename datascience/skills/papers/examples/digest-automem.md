**AUTOMEM: Automated Learning of Memory as a Cognitive Skill (2026)**

The paper proposes a different way of thinking about agent memory. Rather than treating
memory as infrastructure (RAG, vector databases, scratchpads), it treats memory management
itself as a trainable cognitive skill. Inspired by the cognitive science concept of
metamemory, the authors promote file-system operations to first-class agent actions and
then automatically improve both the memory structure and the model's ability to use it.
Evaluation covers three long-horizon environments (Crafter, MiniHack, NetHack). Optimizing
only memory management delivers 2-4x performance improvements and lets a 32B open model
approach or match frontier proprietary models on these benchmarks.

**Key mechanism**

- File-system operations (READ, WRITE, SEARCH, APPEND, CREATE) are promoted to first-class agent
  actions alongside environment actions, which makes every memory decision observable and
  therefore supervisable
- Memory learning is split into two independent optimization axes: the memory scaffold
  (structure, prompts, file schemas) and memory proficiency (model weights)
- Outer Loop 1 iteratively redesigns prompts, file schemas, and memory organization using a
  powerful meta-LLM
- Outer Loop 2 trains a dedicated memory specialist model from successful memory decisions
  collected during earlier episodes
- The task model stays frozen while the memory specialist trains, so memory behavior improves
  without catastrophic forgetting on the task policy

**Main findings**

- Scaffold optimization alone roughly doubles or triples success: Crafter 25.0 to 47.3%,
  MiniHack 7.5 to 27.5%, NetHack 0.42 to 1.57%
- Memory training adds a further increment on top: Crafter 51.4%, MiniHack 30.0%,
  NetHack 1.85%
- Optimized memory beats model scaling on every benchmark reported: Qwen 32B with AUTOMEM
  surpasses vanilla Qwen 72B
- Behavioral telemetry moves in the expected direction: 32-65% fewer wasted actions, 68-83%
  fewer redundant writes, 13-50% fewer unsuccessful searches, 3-30% smaller prompt contexts
- Qualitative behaviors emerge rather than being hand-coded: consult-before-write discipline,
  deduplicated maps, structured inventories, automatic status synchronization
- Caveat on scope: all three environments are synthetic game-like domains with dense action
  loops, and NetHack absolute scores stay near the floor (1.85%), so the relative gains are
  large while the absolute competence remains low

**Key takeaways**

- Treat memory management as its own optimization objective with its own metrics, not as an
  engineering component bolted onto the agent - learning how to remember is separable from
  learning how to solve the task
- Instrument memory operations as explicit actions before trying to improve them; the
  behavioral counts (redundant writes, failed searches) are the cheap signal that tells you
  whether a memory design is working
- A plain file system is sufficient as long-term memory provided the agent learns to organize
  it; a vector database is not a prerequisite for long-horizon competence
- Budget scaffold optimization before parameter scaling - on these benchmarks a 32B model plus
  memory optimization outperformed a 72B model without it, which is the cheaper axis
- Freeze the task model when training a memory specialist to avoid trading task competence for
  memory competence
- The prompt-context reduction (3-30%) is a direct inference-cost lever, not only a quality
  lever; measure it alongside success rate
- Validate on your own domain before generalizing - the results come from synthetic long-horizon
  game environments, and transfer to tool-use or document workflows is untested here
- Relative improvements are reported against a vanilla-memory baseline; check whether your
  current baseline is already stronger than that before expecting comparable multiples

**Relevance**

- Directly applicable to our agent memory layer - the scaffold/proficiency split maps onto our
  prompt-and-schema work versus any future fine-tune, and the two are separable
- Benchmarks are synthetic game environments, so the multiples do not transfer to our document
  workflows without our own measurement; treat them as direction, not magnitude
- The behavioral counters (redundant writes, failed searches, prompt size) are adoptable today
  and cost nothing - worth instrumenting before any memory redesign

**Tags**

- #Memory
- #LLMAgents
- #MetaMemory

**Source**

- https://arxiv.org/abs/<id> (placeholder in this calibration example - a real digest carries
  the resolved provenance URL and nothing else)
