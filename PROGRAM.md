# Program: Tighten Article 01b from 7.5 to 9/10

## Objective

Tighten `docs/medium/article_01b_pull-based-workflow-enforcement.md` from a 7.5/10 internal design note into a 9/10 public article. The core thesis is strong - agents cannot be trusted with their own process control. The delivery is uneven. Cut repetition, restructure the arc, sharpen opening and closing.

## Article Arc

The article has two halves with a clear transition:

**First half** (problem + pattern): failure modes, pull vs push, three principles stated concisely. Accessible, visceral. Technical detail minimal - the FSM code block and `claude -p` detail move to second half.

**Second half** (proof + depth): gates mechanics, multi-agent panels, guardian checklist, theoretical foundations, implementation proof (transcripts), program-driven execution, content/engine separation. Technical, specific, earned.

**Section-to-half mapping**:
- FIRST HALF: Opening, Five failure modes, Push vs Pull SVG, Three principles (stated as concepts, no code)
- TRANSITION: Phase lifecycle SVG bridges to mechanics
- SECOND HALF: Two gates (with FSM code), Multi-agent panels, Guardian, Theoretical foundations, Program-driven execution, Content/engine separation, Real sessions, Limitations, Closing

## Work Items

- **Rewrite opening to show, not tell** (high)
  - Scope: first 3-4 paragraphs of article_01b
  - Current opening TELLS about failure abstractly: "the first iteration gets a thorough plan, the second cuts research short"
  - New opening SHOWS failure: use a real or realistic transcript snippet of an agent rationalising a skip, then pull back to "this is what happens without enforcement"
  - The pull-based framing comes AFTER the reader has seen the agent break discipline
  - BEFORE: "AI coding agents generate impressive code. They are terrible at following process."
  - AFTER: [agent transcript of deterioration] -> "This is what happens when the agent owns the control flow."
  - Acceptance: first 2 sentences are not declarative statements about AI - they show a specific moment of failure

- **Eliminate concept restatement** (high)
  - Scope: full article
  - These synonyms currently appear - consolidate to ONE canonical phrasing per concept:
    - "external enforcement" / "external control" / "external orchestrator" / "external process control" -> keep "external enforcement" once
    - "separate process" / "process isolation" / "independent subprocess" / "isolated evaluator" / "no shared context" -> keep "process isolation" once in Principle 2, then use "the gate" or "the gatekeeper" as shorthand
    - "the agent cannot skip" / "cannot advance" / "cannot decide" / "cannot override" -> state once in Principle 1
  - Each section after the principles adds NEW mechanism or proof, never restates
  - Acceptance: grep for each synonym cluster shows exactly 1 canonical usage

- **Propose new title and subtitle** (high)
  - Scope: frontmatter and H1
  - Current: "Pull-Based Workflow Enforcement for Autonomous AI Agents" - reads like a paper abstract
  - Title should name the tension (agents vs discipline) not the solution pattern
  - Subtitle should telegraph the two-part arc (why + how)
  - BAD: "I Gave an AI Agent Full Autonomy. Here's What Broke." (clickbait)
  - BAD: "A Novel Approach to Agent Process Management" (academic)
  - GOOD DIRECTION: names the problem in the agent's voice, implies the solution exists
  - Acceptance: title hooks an AI engineer, subtitle previews the article structure

- **Tighten the middle - specific cuts** (high)
  - Scope: three principles, two gates, multi-agent, guardian sections
  - Three principles: state each as 2-3 sentences of concept ONLY (no code, no implementation detail). Move FSM code block and `transitions` package mention to Two Gates section. Move `claude -p` detail to Two Gates.
  - Two gates: this becomes the first technical section. Combine comprehension + completion gates with FSM mechanics. The CLAUDECODE gotcha stays here.
  - Multi-agent panels: currently 3 sentences. Keep as-is - already tight.
  - Guardian: keep 4-point checklist verbatim. Cut the surrounding "appears twice" explanation to 1 sentence.
  - Theoretical foundations: compress to a single paragraph with inline citations. Currently 5 separate bold paragraphs = 130 words of restating principles + citations. Target: 60-80 words that add the academic layer without restating.
  - Content/engine: cut FQN naming detail, strict-lookup detail, `cli_name` detail. These are README material. Keep: 3 files, YAML-driven, plugin install (`/install-plugin stellarshenson/claude-code-plugins`), 5 workflow types. NOT pip install - the plugin handles installation automatically in Claude Code.
  - Acceptance: no section restates a concept from the principles; theoretical section is 1 paragraph

- **Rewrite closing as doctrine** (high)
  - Scope: last 2-3 paragraphs + italic postscript
  - Current closing: "the method matters more than the tool" + polite install instructions + humble self-reference
  - New closing builds to: "Agents do not need better prompts. They need constraints they cannot override."
  - The italic postscript ("built through its own process") is the proof-by-construction payoff - keep it, but make it earn its place after the doctrine line
  - Acceptance: final non-italic sentence is doctrine, not suggestion

- **Reduce SVG density** (medium)
  - Scope: image references in article
  - Currently 11 SVGs in ~1700 words = 1 per 155 words. Too many for Medium.
  - Remove SVGs that illustrate text already clear without them:
    - `06-five-failure-modes.svg` - the enumerated list IS the visualization
    - `07-three-principles.svg` - principles are immediately explained in prose
  - Keep SVGs that show things text cannot: lifecycle FSM, guardian architecture, agent defect matrix, end-to-end flow, content/engine separation, push vs pull
  - Target: 7-8 SVGs max
  - Acceptance: no SVG precedes text that fully explains the same content

- **Address the Limitations section** (low)
  - Scope: limitations paragraph
  - Current: 2 sentences that quietly concede the architecture doesn't fully solve the problem
  - Expand to 3-4 sentences: honest about correlated errors, honest about latency cost, but frame as known trade-offs not fatal flaws
  - Acceptance: limitations feel like earned honesty, not undermining

## Exit Conditions

Iterations stop when ANY of these is true:
1. Article editorial grade >= 9/10 AND all work items met
2. No improvement for 2 consecutive iterations (plateau)

Additionally ALL must hold:
- Opening shows failure, not tells about it
- Closing ends with doctrine
- Each synonym cluster appears exactly once
- No section restates a concept from the principles

## Constraints

- Work ONLY on article_01b (not article_01)
- Preserve ALL distinct ideas - cut restatements, not concepts
- Preserve: both real session transcripts in full terminal-output form
- Preserve: voice and register (authoritative, direct, punchy short sentences mixed with technical precision)
- Preserve: concrete specificity (package names, function names, agent counts, timing)
- Preserve: proof-by-construction postscript
- Do NOT change SVG content - only adjust which SVGs are included and placement
