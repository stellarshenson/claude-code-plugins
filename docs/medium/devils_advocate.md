# Devil's Advocate - Article 01b Editorial Tightening

## The Devil

**Role**: Senior AI engineer who reads 50 Medium articles a week, skips most by paragraph 3
**Cares about**: (1) Practical value - can I use this? (2) Originality - have I heard this before? (3) Respect for my time - is every sentence earned?
**Style**: Scans first, reads second. Judges opening in 5 seconds. Skips to code blocks and transcripts.
**Default bias**: Skeptical of "thought leadership" that's really a product pitch
**Triggers**: Restated concepts, implementation onboarding in articles, academic citations without payoff, excessive images
**Decision**: Share on Twitter/X or close tab
**Source**: Composite - senior AI engineer + Medium power reader + open-source contributor

---

## Concern Catalogue

### 1. "The opening tells me about failure instead of showing me one"

**Likelihood: 8** | **Impact: 5** | **Risk: 40**

**Their take**: "AI coding agents generate impressive code. They are terrible at following process." I've read this opener 100 times. Every AI article starts with "X is impressive but Y." Show me an agent breaking. Show me the actual terminal output where it rationalises skipping a phase. Make me feel it.

**Reality**: The article has two real transcripts (skip-denial, forensicist F1) but buries them in the second half.

**Response**: Move a transcript fragment to the opening. Let the reader see the agent's words before explaining the pattern.

### 2. "You say 'external enforcement' five different ways"

**Likelihood: 8** | **Impact: 5** | **Risk: 40**

**Their take**: "External enforcement", "external control", "external orchestrator", "external process control", "process isolation", "independent verification" - I got it the first time. Each restatement signals you don't trust me to remember. That's insulting.

**Reality**: The concept is restated 13+ times across the article in various phrasings.

**Response**: State it once with conviction in Principle 2. Then use "the gate" or "the gatekeeper" as shorthand. Trust the reader.

### 3. "This is three articles stapled together"

**Likelihood: 5** | **Impact: 8** | **Risk: 40**

**Their take**: You're explaining a failure mode, introducing a design pattern, AND documenting your implementation. Pick one. The failure mode + design pattern article is a 9/10. The implementation docs are a README. Stapling them creates drag in the middle.

**Reality**: The article's middle (gates, multi-agent, guardian, theory, content/engine, implementation) is where attention drops.

**Response**: Don't remove implementation - restructure the arc. Problem + pattern first half (accessible). Mechanics + proof second half (technical). The reader who stays past the transition wants the depth.

### 4. "Too many images for a 1700-word article"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: 11 SVGs in 1700 words. One every 155 words. This is a slide deck, not an article. The five-failure-modes SVG illustrates a list that's already perfectly clear. The three-principles SVG precedes text that immediately explains the same thing.

**Reality**: Some SVGs are genuinely useful (lifecycle FSM, guardian architecture, agent defect matrix). Others are decorative.

**Response**: Remove SVGs that illustrate text already clear without them. Target 7-8 max.

### 5. "The closing asks permission instead of stating doctrine"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: "The method matters more than the tool" - that's a disclaimer, not a conclusion. You built a strong thesis and then apologised for it. End with conviction: "Agents do not need better prompts. They need constraints they cannot override."

**Reality**: The closing also includes pip install instructions (onboarding) and a humble self-referential postscript.

**Response**: Doctrine line as the final non-italic sentence. Proof-by-construction postscript earns its place after doctrine, not before.

### 6. "The theoretical section is post-hoc justification"

**Likelihood: 3** | **Impact: 5** | **Risk: 15**

**Their take**: Five citations rapid-fire, each doing the same thing: "research says X, our system does Y." Reads like you built the system first and went shopping for papers to legitimise it.

**Reality**: The citations ARE relevant. But the structure (5 bold paragraphs, each restating a principle + adding a citation) makes them feel decorative.

**Response**: Compress to one paragraph with inline citations. The academic backing should be a single confident layer, not a parade.

### 7. "The Limitations section undermines the whole article"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: "The same underlying model evaluating itself introduces correlated errors - process isolation helps but the model's blind spots remain." So the architecture doesn't actually solve the problem? Why did I read 1700 words?

**Reality**: Every architecture has trade-offs. Stating them honestly is a strength, not a weakness. But 2 sentences is too brief to frame this as an earned trade-off.

**Response**: Expand to 3-4 sentences. Frame as known trade-offs with specific mitigations, not a quiet concession.

---

## Scorecard v01 (baseline - article_01b before any edits)

| # | Concern | Risk | Score | Residual | How addressed |
|---|---------|------|-------|----------|---------------|
| 1 | Opening tells not shows | 40 | 30% | 28.0 | Opening describes failure abstractly ("the first iteration gets a thorough plan, the second cuts research short") but doesn't show a specific moment |
| 2 | Concept restatement | 40 | 15% | 34.0 | "External enforcement" concept appears in 5+ variants throughout. Minimal consolidation. |
| 3 | Three articles stapled | 40 | 40% | 24.0 | Content all present but interleaved. Technical detail in first half (FSM code in Principle 1). No clear arc transition. |
| 4 | SVG density | 25 | 30% | 17.5 | 11 SVGs. Some decorative (06, 07). |
| 5 | Closing asks permission | 25 | 25% | 18.8 | "Method matters more than the tool" + pip install + humble postscript. No doctrine. |
| 6 | Theory post-hoc | 15 | 50% | 7.5 | Citations relevant but structure is 5 restating paragraphs. |
| 7 | Limitations undermine | 9 | 40% | 5.4 | 2 sentences, honest but too brief to frame as trade-off. |

**Document score**: 135.2 (total residual risk)
**Total absolute risk**: 194.0
**Residual %**: 69.7%

**Top gaps**:
1. Concept restatement (34.0) - systemic, affects every section
2. Opening tells not shows (28.0) - first impression
3. Three articles stapled (24.0) - structural drag
4. Closing asks permission (18.8) - last impression
5. SVG density (17.5) - reading flow disruption
