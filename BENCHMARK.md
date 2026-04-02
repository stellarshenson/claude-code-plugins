# Benchmark: Article 01b Editorial Tightening

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + editorial_residual + arc_residual + voice_residual + opening_residual + middle_residual + closing_residual + specificity_residual
```

- `editorial_residual` = 10 - editorial grade (Section 4, graded 0-10)
- `arc_residual` = 10 - arc grade (Section 5, graded 0-10)
- `voice_residual` = 10 - voice grade (Section 6, graded 0-10)
- `opening_residual` = 10 - opening grade (Section 9, graded 0-10)
- `middle_residual` = 10 - middle grade (Section 10, graded 0-10)
- `closing_residual` = 10 - closing grade (Section 11, graded 0-10)
- `specificity_residual` = 10 - specificity grade (Section 12, graded 0-10)

Maximum possible score: ~30 checklist items + 70 graded residual = ~100. Target: < 10.

## Evaluation

1. Read `docs/medium/article_01b_pull-based-workflow-enforcement.md`
2. Compare against `docs/medium/article_01_pull-based-workflow-enforcement.md` (original)
3. Verify each [ ] item against the actual article text - quote specific passages
4. Grade editorial quality, arc, and voice with anchored rubrics
5. EDIT this file with updated marks and quoted evidence
6. UPDATE the Iteration Log below
7. Report composite score

---

## Section 1: Opening Quality

Not just "does it start with failure" - does it SHOW failure?

- [x] First 2 sentences are NOT declarative statements about AI ("AI agents are..." = FAIL)
  > Opens with terminal transcript: `orchestrate skip --reason "Hypothesis already determined from prior research" --force` followed by GATEKEEPER DENY. No declarative "AI agents are..." anywhere.
- [x] Opening contains a specific moment of agent failure (transcript, quote, or concrete scenario - not abstract description)
  > Real terminal output showing force-skip attempt and denial. "This is iteration three. The agent had a reasonable argument..."
- [x] Reader sees the agent's actual rationalisation for cutting corners (not told that it happens)
  > The agent's own reasoning is shown: `--reason "Hypothesis already determined from prior research"` - the reader sees the argument, then the denial.
- [x] Pull-based framing introduced AFTER the failure is shown (problem before solution)
  > Transcript and failure narrative come first (lines 24-36), then "The problem isn't capability" bridge, then "Pull-based workflow enforcement fixes this" (line 38).
- [x] Opening is tighter than original (fewer words for more impact)
  > Original: 4-sentence abstract paragraph. Rewrite: terminal transcript + 2-sentence narration. More visceral, fewer words.

## Section 2: Repetition Eliminated

Verify by searching for each synonym cluster. Quote any remaining duplicates.

- [ ] "External enforcement/control/orchestrator/process control" - canonical phrasing appears ONCE, no synonyms elsewhere
  > PARTIAL: "enforcement" appears 4 times: opening line 15 ("without this enforcement"), line 19 ("Pull-based workflow enforcement"), line 115 ("Gate enforcement" heading), line 117 ("This is enforcement in action"). "Orchestrator" appears 6 times across different sections. The term is used functionally (not as synonym padding) but "enforcement" recurs more than once beyond the canonical introduction.
- [ ] "Separate process/process isolation/independent subprocess/isolated evaluator/no shared context" - established ONCE in Principle 2, then shorthand ("the gate/gatekeeper") used thereafter
  > FAIL: "separate process" in opening (line 32) AND "no shared context" in Principle 2 (line 43) AND "process isolation" in Limitations (line 161). The concept is introduced in the opening narration before Principle 2 establishes it canonically. "Process isolation" reappears in Limitations.
- [x] "Cannot skip/advance/decide/override" - stated ONCE in Principle 1
  > "cannot skip a phase, reorder transitions, or advance" in Principle 1 only. Closing uses "cannot override" but that is a distinct doctrinal statement, not a restatement.
- [x] No paragraph that restates a concept already established in the principles (theoretical section adds citations, not restatements)
  > Theoretical section compressed to single paragraph with 5 inline citations. Each clause maps to a citation, not a principle restatement. "orchestrator keeps instructions compact" [1], "re-injecting instructions at transitions prevents mode carry-over" [2], "comprehension probe" [3], "independent classifier" [4], "generate-feedback-refine loop" [5]. New information (research backing) rather than restating principles.

## Section 3: Content Preserved WITH Quality

Not just "is it present" - is the original punch preserved?

- [x] Five failure modes present with SPECIFIC EXAMPLES (not just names - "invisible zero-length connectors", "relaxes the threshold" level detail)
  > All five present: shallow execution ("I reviewed the codebase"), self-review theatre, process erosion ("by iteration 3 it merges phases"), knowledge loss, benchmark gaming ("invisible zero-length connectors", "relaxes the threshold"). Same specificity as original.
- [x] Pull vs push framing present with the core insight ("prompts are suggestions, state machines are constraints")
  > "Workflows defined in prompts are suggestions. Workflows enforced by a state machine are constraints." Preserved verbatim in Principle 1.
- [x] Three principles present as CONCEPTS (inversion of control/FSM, process isolation, accumulated knowledge)
  > All three: "Principle 1: inversion of control", "Principle 2: process isolation", "Principle 3: accumulated knowledge". Each with subsection header.
- [x] Two gates concept present with MECHANICAL DETAIL (comprehension probe + two-sided evidence assembly)
  > "Comprehension gate (on entry)" with "gatekeeper evaluates whether the summary captures the requirements." "Completion gate (on exit)" with "two-sided view: from the program (exit criteria, required agents, expected artifacts) and from the agent (evidence, claimed agents, output file)."
- [x] Guardian 4-point checklist present in INTERROGATIVE FORM ("do changes game test assertions...?" not "test overfitting")
  > Items 1-3 interrogative: "do changes game test assertions rather than fixing behaviour?", "do changes target benchmark scenarios rather than general capability?", "do changes assume a specific dataset that won't generalise?" Item 4 conditional: "if it looks like overfitting but was explicitly requested, ASK the user."
- [x] Multi-agent panels present with NAMED PERSPECTIVES (contrarian/optimist/pessimist/scientist, not "different perspectives")
  > "contrarian, optimist, pessimist, scientist for hypothesis formation; critic, architect, guardian, forensicist for implementation review."
- [x] Skip-denial transcript present as TERMINAL OUTPUT (not summarised)
  > Present as opening code block: `orchestrate skip --reason... GATEKEEPER: evaluating FORCE-SKIP request... DENY`
- [x] Forensicist F1 transcript present as TERMINAL OUTPUT (not summarised)
  > Full terminal block preserved: "Forensicist: Found critical issue F1 - _clean_artifacts_dir destroys project-local resource customizations on new --clean"
- [x] Theoretical foundations present with 5 INLINE CITATIONS (not a bibliography dump)
  > Single dense paragraph with [1] through [5] inline. References listed at end: Liu et al., Han et al., Deng et al., Ye et al., Madaan et al.
- [x] Program-driven execution present (PROGRAM.md + BENCHMARK.md + Karpathy reference)
  > "inspired by Andrej Karpathy's autoresearch", "PROGRAM.md declares what to achieve", "BENCHMARK.md is the objective function."
- [x] Content/engine separation present (3 YAML files, plugin install via `/install-plugin stellarshenson/claude-code-plugins`)
  > All three YAML files named: `workflow.yaml`, `phases.yaml`, `app.yaml`. Install command: `/install-plugin stellarshenson/claude-code-plugins`.
- [x] Limitations present as HONEST TRADE-OFFS (not undermining)
  > "comprehension gate is lenient and rarely fails", "Multi-agent panels add real latency (~30s per gate)", "process isolation reduces but does not eliminate this", "The method catches process failures, not capability failures." Ends with "But most autonomous agent failures are process failures" - honest without undermining.
- [x] FSM concept present (transitions package, well-established CS concept)
  > "finite state machine... the same well-established CS concept that drives network protocols and compilers... The FSM (Python's `transitions` package)."
- [x] Proof-by-construction postscript preserved
  > "This orchestrator was built and refined through its own process - using earlier versions to iterate on later versions, with the guardian catching overfit patterns along the way."

## Section 4: Editorial Quality (0-10 scale)

Anchored rubric - use these exemplars to calibrate:

| Score | Description |
|-------|-------------|
| 10 | Every sentence earns its place. Opening grabs in 2 sentences. No drag in middle. Closing is quotable. Voice is distinctive. Reader wants to share it. |
| 9 | Near-perfect. One section slightly soft. Reader finishes without skimming. |
| 8 | Strong. Two minor drags (a restated concept, a paragraph that could lose a sentence). Reader finishes but skims one section. |
| 7 | Good internal doc trying to be public article. Solid content, uneven delivery. Reader skims the middle. |
| 6 | Competent but flat. Correct information, no voice. Reader checks length remaining. |
| 5 | Mediocre. Multiple restatements, implementation detail too early, bland opening/closing. |
| <=4 | Needs full rewrite. |

The baseline article_01 is a 7.5 (strong content, uneven delivery, repetitive middle, polite closing).

Criteria for evaluator:
- Does the opening hook in 2 sentences? (not "mentions failure" - genuinely hooks)
- Does each paragraph earn its place? (would the article lose something if this paragraph were deleted?)
- Does the reader's attention hold through the middle? (no "I already understood this" moments)
- Is the closing memorable? (could someone quote the last line?)
- Does it read as a public article by a practitioner? (not an internal doc, not a blog tutorial)

Current grade: [8] /10
Residual: [2] (10 - grade)

**Evidence**: Opening hooks with terminal transcript - genuinely grabs. Each section earns its place - no section could be deleted without losing a mechanism. The theoretical section is now a single dense paragraph (major improvement over original's 5-paragraph restatement). The middle holds attention: failure modes -> principles -> gates -> panels -> guardian -> theory -> program -> content/engine -> real sessions -> limitations. Two minor drags: (1) the "Gate enforcement" subsection under "Real sessions" partially restates the opening transcript ("The transcript at the top of this article is real") rather than adding new evidence, (2) content/engine section remains slightly README-level. Closing "Agents do not need better prompts. They need constraints they cannot override" is quotable and earned. Overall reads as a public article by a practitioner. The reduction from ~1644 to ~1380 words removed genuine fat without losing substance.

## Section 5: Article Arc (0-10 scale)

| Score | Description |
|-------|-------------|
| 10 | Perfect escalation: accessible problem -> conceptual pattern -> technical proof -> earned theory -> doctrine close. Each section more complex than the last. Transition between halves is invisible. |
| 9 | Near-perfect arc. One minor bump in escalation. Reader doesn't notice on first read. |
| 8 | Strong arc. Clear two-half structure. One section slightly out of order. |
| 7 | Good arc but transition between halves is mechanical ("Now let's look at how..."). |
| 6 | Arc exists but bumpy. Technical and accessible content interleaved in places. |
| 5 | Structure present but flat. Reader adjusts expectations twice. |
| 4 | Sections could be partially reordered without reader noticing. |
| 3 | No clear arc. Feature catalogue feel. |
| <=2 | Inverted or absent. Technical detail before the reader cares. |

Baseline (article_01): 6/10 - two-half structure implied but FSM code in Principle 1 breaks it, theoretical section partially restates principles.

Current grade: [8] /10
Residual: [2] (10 - grade)

**Evidence**: Strong two-half structure. First half (accessible): concrete failure opening -> five failure modes -> three principles -> two gates -> panels -> guardian. Second half (technical): theoretical foundations -> program-driven execution -> content/engine -> real sessions -> limitations -> doctrine close. The transition between halves is the theoretical foundations section, which works well as a pivot. One bump: content/engine and real sessions feel slightly out of escalation order - content/engine is lower-stakes than theory, yet appears after it. The FSM code in Principle 1 is now a single inline sentence rather than a full code block, which no longer breaks the accessible-first half. Arc is clear and mostly escalating.

## Section 6: Voice and Craft (0-10 scale)

What makes the article GOOD beyond structure. Not measured by any checklist item.

| Score | Description |
|-------|-------------|
| 10 | Distinctive voice in every paragraph. Punchy short sentences land perfectly. Rhythm varies. Register never wavers. Reader hears a specific person, not "an AI article." |
| 9 | Voice strong throughout. One sentence slightly generic. Rhythm mostly varied. |
| 8 | Voice consistent. Two moments of tech-blog blandness. Specifics preserved. |
| 7 | Good voice but one section feels written by a different author. Rhythm flattens in the middle. |
| 6 | Voice present but diluted. Generic phrasing creeps in ("it's important to note that..."). |
| 5 | Mixed. Some paragraphs sharp, others could be anyone's writing. |
| 4 | Mostly bland. Occasional flash of personality. |
| <=3 | Voice destroyed. "In this article, we explore..." |

Criteria:
- Are punchy short sentences preserved? ("The score improves. The system doesn't." / "No external enforcement. No one checking.")
- Is concrete specificity maintained? (`transitions` package, `_clean_artifacts_dir`, ~30s per gate, 15 agents)
- Does the prose have rhythm variation? (not uniformly medium-length sentences)
- Is the register consistent? (authoritative practitioner, not tutorial, not academic)

Baseline (article_01): 8/10 - strong voice, punchy sentences present, high specificity.

Current grade: [8] /10
Residual: [2] (10 - grade)

**Evidence**: Punchy short sentences preserved: "The score improves. The system doesn't." "The agent had to comply." "No one is checking." "Self-review theatre becomes physically impossible." Concrete specificity maintained throughout: `transitions` package, `_clean_artifacts_dir`, `CLAUDECODE` environment variable, ~30s per gate, 15 agents, `pending -> readback -> in_progress -> gatekeeper -> complete`. Register is consistent authoritative practitioner throughout. Rhythm varies well between short punchy lines and longer technical sentences. Two moments of slight tech-blog blandness: "This is enforcement in action" (telling) and "The implementation is auto-build-claw, a Claude Code plugin, but the pattern applies to any autonomous AI workflow" (slightly promotional). Voice is strong and consistent otherwise.

## Section 7: Title and Subtitle

- [x] Title names the TENSION (agents vs discipline) not the solution pattern
  > "Your AI Agent Will Cut Corners. Here's How to Stop It." - names the tension (agent cutting corners vs stopping it), not the solution pattern.
- [x] Title would make an AI engineer stop scrolling on Medium
  > Direct, specific claim ("will cut corners") that resonates with anyone who has used autonomous agents. Not generic "Improving AI Workflows" or academic "A Framework for..."
- [x] Subtitle telegraphs the two-part arc (why it fails + how to fix it)
  > "Pull-based workflow enforcement: why autonomous agents need constraints they cannot override" - names the mechanism, states the need (constraints), implies the arc (need -> solution).
- [x] Neither title nor subtitle is clickbait or academic
  > Title is direct and specific. Subtitle is technical but accessible. Neither oversells nor hides behind jargon.

## Section 8: SVG Density

- [x] No more than 9 SVGs in article (currently 11 - at least 2 removed)
  > 7 SVGs + 1 PNG cover = 8 total images. Reduced from 10 SVGs to 7 SVGs. Removed: 06-five-failure-modes.svg, 07-three-principles.svg, 11-theoretical-foundations.svg (3 removed).
- [ ] No SVG precedes text that fully explains the same content without the image
  > PARTIAL FAIL: Line 122 `10-end-to-end-journey.svg` appears after the code block but before the "Content/engine separation" section. The image is an end-to-end journey that relates to program-driven execution above it, which is acceptable. However, line 126 `04-content-engine-separation.svg` appears immediately after the section header and before the text paragraph, acting as a lead-in that the text then explains fully.
- [ ] No back-to-back SVGs without text between them
  > Lines 122 and 126: end-to-end SVG, then section header "Content/engine separation", then content/engine SVG. Only a heading between them - no body text separates them.
- [x] Each remaining SVG earns its place (shows what text cannot)
  > 01-push-vs-pull (visual comparison), 02-phase-lifecycle (state diagram), 03-guardian-anti-overfit (architecture), 10-end-to-end-journey (full flow), 04-content-engine-separation (architecture), 05-full-workflow-agents (agent mapping), 09-multi-agent-defect-detection (4-agent review). Each shows a relationship or architecture that text alone would not convey as efficiently.

## Section 9: Opening Impact (0-10 scale)

How hard does the opening hit? Not "does it mention failure" - does the reader FEEL it?

| Score | Description |
|-------|-------------|
| 10 | Reader is hooked by sentence 1. Specific agent failure shown (transcript, real output). Visceral - reader recognises this from their own experience. Pull-based framing lands as revelation after the gut punch. |
| 9 | Hooked by sentence 2. Concrete failure, strong transition to framing. |
| 8 | Strong opening. Shows failure specifically but transition to pattern slightly mechanical. |
| 7 | Good concrete opening. Reader engaged but not grabbed. Shows failure but doesn't make it personal. |
| 6 | Describes failure well but still TELLS rather than SHOWS. "Here's what happens" not "watch this happen." |
| 5 | Competent opening. States the problem clearly. No hook. |
| 4 | Generic AI opening. "AI agents are impressive but..." Reader has seen this 100 times. |
| <=3 | Throat-clearing. Abstract. Reader skips ahead. |

Baseline (article_01): 5/10 - describes deterioration across iterations but in abstract declarative terms.

Current grade: [8] /10
Residual: [2] (10 - grade)

**Evidence**: Opens with real terminal output - the reader SEES the agent's attempt and the gatekeeper's denial before any narration. "This is iteration three" provides the context. The agent's rationalisation is visible in the command itself (`--reason "Hypothesis already determined from prior research"`). Reader recognises the pattern from their own experience. Transition to pull-based framing comes after the gut punch ("The problem isn't capability. It's that agents operate in a push model"). Strong concrete opening that SHOWS rather than tells. Slightly below 9 because the transition paragraph ("By iteration five, without this enforcement...") partially tells rather than shows - it projects future failure abstractly rather than with a second concrete example.

## Section 10: Middle Momentum (0-10 scale)

Does the reader's attention survive the middle? The middle is where articles die.

| Score | Description |
|-------|-------------|
| 10 | Every section adds a new mechanism or proof. No "I already understood this." Reader accelerates because each section raises stakes. Zero restatements. |
| 9 | Strong momentum. One brief moment of elaboration that doesn't quite add new info. |
| 8 | Good forward motion. Reader engaged throughout. One section could lose a sentence. |
| 7 | Mostly moving. One concept partially restated. Reader notices but doesn't skim. |
| 6 | Some drag. Reader skims one section. A concept restated in different words. |
| 5 | Middle sags in one place. Reader re-engages after. Two restatements. |
| 4 | Multiple restatements. Reader considers closing tab. Theory and mechanics blur. |
| <=3 | Reader skips to the transcripts. Middle is a wall. |

Baseline (article_01): 5/10 - principles section restates in multiple ways, theoretical section partially restates principles with citations, content/engine section has README-level detail.

Current grade: [7] /10
Residual: [3] (10 - grade)

**Evidence**: Good forward motion through the middle. Each section adds a new mechanism: failure modes -> principles -> gates -> panels -> guardian -> theory -> program -> content/engine -> real sessions. The theoretical section is now a single dense paragraph with citations rather than a 5-paragraph restatement - major improvement. However, two issues drag this below 8: (1) "Gate enforcement" subsection under "Real sessions" explicitly says "The transcript at the top of this article is real" and recaps the skip-denial scenario - the reader already saw this and already understood it. This is an "I already understood this" moment. (2) Content/engine section remains somewhat flat and README-level ("Three files define everything... Resources are bundled... Users customise the local copy"). Reader could skim this without missing a mechanism. One concept partially restated: process isolation appears in the opening, Principle 2, and Limitations.

## Section 11: Closing Power (0-10 scale)

Does the ending land? Not "does it summarise" - does it RESONATE?

| Score | Description |
|-------|-------------|
| 10 | Closing line is quotable. Reader screenshots it for Twitter. Doctrine stated with conviction. Build-up earns the final line. Postscript is proof-by-construction payoff. |
| 9 | Quotable closing. Build-up strong. Postscript lands. One word could be sharper. |
| 8 | Strong doctrine closing. Reader remembers the last line. Build-up adequate. |
| 7 | Good closing. Doctrine present but build-up slightly rushed - the line hasn't fully been earned. |
| 6 | Adequate. States the thesis clearly but doesn't elevate it. Reader nods. |
| 5 | Correct ending. Summarises rather than declares. No memorable line. |
| 4 | Polite closing. "The method matters more than the tool." Reader forgets immediately. |
| <=3 | Trailing off. Install instructions. Humble-brag. Apology. |

Baseline (article_01): 4/10 - "the method matters more than the tool" + pip install instructions + humble self-reference.

Current grade: [8] /10
Residual: [2] (10 - grade)

**Evidence**: Closing line is quotable: "Agents do not need better prompts. They need constraints they cannot override." This is a strong doctrine statement set apart with horizontal rules. The build-up earns it - Limitations honestly states what the method does NOT catch, then the closing pivots to what it DOES provide. Postscript lands: "built and refined through its own process." The "method matters more than the tool" / pip install / humble self-reference from the original is completely gone - replaced by clean doctrine. The only reason this is not a 9: the build-up is the Limitations section, which is functional but not particularly building toward a climax. The doctrine line arrives slightly abruptly after the limitations rather than being earned through escalation.

## Section 12: Specificity Density (0-10 scale)

The article's credibility comes from concrete detail. Measure its preservation.

| Score | Description |
|-------|-------------|
| 10 | Every technical claim backed by concrete specific. Package names, function names, counts, timings, terminal output. No hand-waving anywhere. Higher density than original where the rewrite added specifics. |
| 9 | All original specifics preserved. No generalisation of concrete details. |
| 8 | Nearly all specifics preserved. One instance compressed but not lost. |
| 7 | Mostly specific. Two sections slightly generalised. |
| 6 | Mixed. Some specifics preserved, others compressed. "The FSM enforces transitions" instead of "pending -> readback -> in_progress -> gatekeeper -> complete." |
| 5 | Half specific, half general. Named agents sometimes, numbered agents other times. |
| 4 | Thinned. Concepts as nouns, specifics lost. "Four review agents" not "critic, architect, guardian, forensicist." |
| <=3 | Abstract rewrite. Generalisations throughout. |

Baseline (article_01): 9/10 - high specificity throughout, occasional generalisation in content/engine section.

Current grade: [9] /10
Residual: [1] (10 - grade)

**Evidence**: All original specifics preserved. Package names (`transitions`), function names (`_clean_artifacts_dir`), counts (15 agents, 3 agents, 4 agents), timings (~30s per gate), terminal output (skip-denial, F1 defect), state transitions (`pending -> readback -> in_progress -> gatekeeper -> complete`), environment variable (`CLAUDECODE`), workflow types (full, fast, gc, hotfix, planning), YAML file names (workflow.yaml, phases.yaml, app.yaml), citation specifics (5 named papers with years). One minor compression: original had "not different prompts within the same session, but separate `claude -p` subprocesses" while rewrite has just "separate `claude -p` subprocesses with no shared context" - the contrast is slightly compressed but the specific detail preserved. No generalisation of concrete details anywhere.

## Completion Conditions

Iterations stop when ANY of these is true:
- [ ] All Section 1-8 items [x] AND editorial >= 9 AND arc >= 8 AND voice >= 8 AND opening >= 8 AND middle >= 8 AND closing >= 8 AND specificity >= 8
  > NOT MET: 2 unchecked in Section 2 (synonym clusters), 2 unchecked in Section 8 (SVG placement). Editorial=8 (needs 9). Middle=7 (needs 8).
- [ ] No score improvement for 2 consecutive iterations (plateau)
  > N/A - first iteration.

Additionally ALL must hold:
- [x] Opening shows failure, not tells
  > Terminal transcript shows the agent's attempt and gatekeeper denial. Reader sees it happen.
- [x] Closing ends with doctrine
  > "Agents do not need better prompts. They need constraints they cannot override."
- [ ] Each synonym cluster appears once
  > FAIL: "process isolation" / "separate process" / "no shared context" appears in opening, Principle 2, AND Limitations (3 locations).
- [x] Transcripts preserved as terminal output
  > Skip-denial: code block with `orchestrate skip...GATEKEEPER...DENY`. F1 defect: code block with `Forensicist: Found critical issue F1...`

**Do NOT stop while any condition above is unmet.**

---

## Iteration Log

| Iteration | Date | Score | Unchecked | Editorial | Arc | Voice | Opening | Middle | Closing | Specificity | Words | Notes |
|-----------|------|-------|-----------|-----------|-----|-------|---------|--------|---------|-------------|-------|-------|
| baseline  | -    | TBD   | (all)     | 7.5       | 6   | 8     | 5       | 5      | 4       | 9           | ~1644 | article_01 before edits |
| 1         | 2026-04-01 | 18   | 4         | 8         | 8   | 8     | 8       | 7      | 8       | 9           | ~1380 | article_01b: transcript opening, compressed theory, quotable closing, 3 SVGs removed. Remaining issues: synonym cluster repetition (process isolation x3), back-to-back SVGs in content/engine, gate enforcement restates opening, middle momentum drag from content/engine section |
