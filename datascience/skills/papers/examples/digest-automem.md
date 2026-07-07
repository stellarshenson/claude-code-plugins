**AUTOMEM: Automated Learning of Memory as a Cognitive Skill (2026)**

The paper proposes a different way of thinking about agent memory. Rather than
treating memory as infrastructure (RAG, vector databases, scratchpads), it treats
**memory management itself as a trainable cognitive skill**. Inspired by the
cognitive science concept of metamemory, the authors allow an LLM to explicitly
perform file-system operations (read, write, search, append, create) and then
automatically improve both the memory structure and the model's ability to use it.
On three long-horizon environments (Crafter, MiniHack, NetHack), optimizing only
memory management delivers **2-4x performance improvements**, allowing a 32B open
model to approach or match frontier proprietary models.

**Key mechanism**
- File-system operations (READ, WRITE, SEARCH, APPEND, CREATE) promoted to
  first-class agent actions alongside environment actions
- Memory learning separated into two independent optimization axes: memory
  scaffold (structure) and memory proficiency (model weights)
- Outer Loop 1 iteratively redesigns prompts, file schemas and memory
  organization using a powerful meta-LLM
- Outer Loop 2 trains a dedicated memory specialist model from successful memory
  decisions collected during previous episodes
- The task model stays frozen during memory training - improves memory behavior
  without catastrophic forgetting

**Main findings**
- Scaffold optimization alone roughly doubles or triples performance: Crafter
  25.0 -> 47.3%, MiniHack 7.5 -> 27.5%, NetHack 0.42 -> 1.57%
- Memory training adds further: Crafter 51.4%, MiniHack 30.0%, NetHack 1.85%
- Optimized memory beats model scaling: Qwen 32B + AUTOMEM surpasses vanilla
  Qwen 72B on every benchmark
- Behavioral gains: 32-65% fewer wasted actions, 68-83% fewer redundant writes,
  13-50% fewer unsuccessful searches, 3-30% smaller prompt contexts
- Learned behaviors: consult-before-write discipline, deduplicated maps,
  structured inventories, automatic status synchronization

**Key takeaways**
- Memory management is an independent optimization objective, not an
  engineering component - learning HOW to remember is distinct from learning
  how to solve the task
- Memory operations as observable actions can be supervised, evaluated and
  improved like any other policy
- A simple file system suffices as long-term memory if the agent learns to
  organize it; improving memory can rival large increases in model size

**Tags**
- #Memory
- #LLMAgents
- #MetaMemory

**Source**
- Download: <verified PDF URL>
- Local: [paper] automem memory as cognitive skill, 2026.pdf
