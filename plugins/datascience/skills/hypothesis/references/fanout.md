# Hypothesis fanout

Generate the next round of hypotheses from the campaign's kernel - one specific hypothesis on request, or a persona-driven batch. Pre-registration is the prerequisite at every scale: no generated hypothesis, single or batch, is appended to the log or executed before the user signs off its prediction + acceptance bar. This is the methodology, not a courtesy.

## Two scales, one gate

- **Single hypothesis** - the user names what to test → fill the per-hypothesis template directly, no persona ceremony; still pre-registered (prediction + acceptance bar shown as a one-row pre-registration table, user confirms) before it lands or runs
- **Fanout batch** - a new `E<batch>` generated under a chosen persona; proposed via the full pre-registration table, user signs off, edits fold in - only then appended and executed
- **Multiple fanouts may merge into one experiment batch** - when reasonable (shared setup, one execution vehicle, compatible verdict protocol), fanouts from several seeds or personas are batched into a single `E<batch>`; keep each hypothesis tagged with its generating persona so the verdict-signature self-test still reads per persona
- **Ask scale + type first** - before generating, ask the user two things: how many (probe 3-5 / round 8-12 / campaign batch 15-25) and which persona(s); recommend both from the log state (portfolio rule below)
- **The user's framework is the generative seed (key)** - when the user dictates a framework - a hypothesis, a mechanism, a lever, an area, a hunch - the fanout is composed FROM it: perturb it with the operators, extrapolate it along its own logic, explore its neighbourhood creatively; the persona shapes the exploration, the user's framework anchors it. A dictated framework is never merely filed as one more candidate beside machine-generated ones - it is the kernel-of-the-round the rest are generated around

## Pointed at an area - derive the kernel yourself

The user often will not hand you a kernel. They point at an issue - "fanout must happen here, with hypotheses" - and the agent derives the frame: read the code / data / logs in that area and identify the key metrics (what would move), the levers (what can be changed), the aspects (what the outcome depends on), and the mechanisms (why any of it works). That derived frame IS the round's kernel; state it back and confirm before generating. A user framework, when given, seeds this; when absent, the agent builds it from the area itself.

- **Observation, not invention** - the highest-value hypotheses are usually a cheap measurement nobody ran, not a clever build; before proposing a build, propose the free probe (set-diff over checkpoints, a count, a ratio) that would reveal the cure or kill the idea. Plausible-but-untested is what you ship when you stop at thinking and skip the measuring
- **Reach far - cross-domain transfer is first-class** - a lever may come from a field far from the target domain: species-richness estimators from ecology, Heaps' law from linguistics, record-linkage from census statistics, isotonic calibration from ML metrology, optimal transport from mathematics. Do not invent where another field already solved it - recognise the analogue, map it onto a channel, test it honestly. Far-reaching assumptions and mechanisms are wanted here, not filtered out
- **Attack the load-bearing assumption** - the contrarian persona applied to the area's own foundations produces the highest-value verdicts (a killed pet idea, an expensive program refuted for free); point it at what the design most depends on

## The kernel (prerequisite for fanout)

The fixed typed interface every hypothesis compiles to - what makes wildly different levers comparable and a 300-hypothesis campaign composable. Lives in the log's Methodology section; elicit it on the first fanout, or derive it from the area the user points at (above). Ask the author for what only they know; derive what the code and data show. Start thin, grow fields as the model earns them (the demographic campaign added cross-generation fields only when its cohort machinery arrived).

- **Channel vocabulary** - closed set of named levers/states the system exposes; a hypothesis may act only through named channels
- **Lever record** - forcing (channel + direction + magnitude), a decay/evasion analogue (whatever erodes the gross effect - defection, leakage, overfitting), a named cost/guardrail vector
- **Metric panel + naive baseline** - the axes every hypothesis is scored on and the floor it must beat
- **Verdict protocol** - the stages a verdict requires (e.g. simulate → ablate); a literature digest yields a verdict-LEAN, never a verdict

Domain translation - demography: channels C/ρ/P̄/τ/S/N/q, decay = evasion δ, cost = autonomy/coercion/fiscal. ML: channels = data / architecture / objective / inference knobs, decay = leakage/overfit risk, cost = compute + complexity. Lab: channels = protocol parameters, decay = contamination/drift, cost = reagent + time.

## Perturbation operators

New hypotheses are transformations of existing ones, rarely inventions from nothing.

| operator | move | example (demographic campaign) |
|---|---|---|
| sweep | vary one lever's magnitude; verdict on the optimum type (interior / corner / sign-flip) | E17 swept design spans |
| hybridize | compose winners; test `I(A,B) = effect(A+B) − effect(A) − effect(B)`, bundles run JOINTLY | E18 hybrids, E28 interaction matrix |
| extremize | push a channel to its historical maximum, anchored to a real analogue | E34 Decree 770 → Gilead ceiling |
| invert | attack the log's own Confirmed verdicts | E13 contrarian audit |
| condition | re-run across regimes (region, generation, cohort) hunting sign-flips | Korea/Germany/France triad, gen-1 vs gen-4 |
| transfer | import a mechanism from another field into a named channel - reach far, the best levers are other domains' solved problems | Chao1 from ecology, record-linkage from census stats, OT from mathematics |

## Personas (hypothesisers)

Each `generators/<persona>.md` is an exploration policy over the kernel - its question, operator bias, sourcing requirements, and an expected verdict signature that self-tests the round. Read the chosen file before generating; blend two personas only when the user asks.

| persona | question | healthy verdict signature |
|---|---|---|
| follower | the winner works - how deep does it go? | SUPPORT-heavy |
| contrarian | which of OUR findings is wrong? | 30-50% of attacks land; 0 = weak attacks |
| heretical | what lives at the edge nobody will test? | REFUTE-heavy; SUPPORT-heavy = wasn't heretical |
| hybridizer | do the winners compound or collide? | mixed; the finding is the interaction sign |
| mechanist | what undercurrent drives the winning effect? | Refuted-mechanism-heavy |
| deflationist | what's the boring explanation? | kills cheaply pre-build |
| scout | what machinery haven't we modelled? | verdict-LEANS only, no modelled verdicts |

## Portfolio rule - recommending the next persona

Read the log's last 1-2 rounds and recommend; the user overrides freely.

- fresh winners → follower (depth) or hybridizer (composition)
- verdicts too clean / progress stagnant → contrarian
- laws forming across rounds → heretical (stress the law at the extremes)
- unknown machinery, thin literature → scout (research round, digests only)
- before any expensive build → deflationist kill-gates first

## Mechanics

1. Find the canonical log, tally the current verdict state, extract the kernel (elicit it if absent)
2. Ask scale + persona - recommend both; if the user dictated a framework (hypothesis, mechanism, lever, area, hunch), it becomes the round's generative seed - the batch is perturbed, extrapolated and explored from it
3. Generate candidates - each a FULL per-hypothesis record (Hypothesis, Lever, Mechanism, Prediction, Acceptance bar; Experiment block where it owns a regime); no bare "try X"
4. Dedupe against the global H-ordinal registry (`hypothesis-tools next-id <log>` for the next free `H<n>`, `list` for what is taken) - a collision is dropped or explicitly supersedes with a back-reference, never silently re-tested
5. Cheap kill-gate pass - drop candidates whose precondition is measurably absent before proposing them
6. **Pre-register (the gate)** - present the pre-registration table (SKILL.md format); the user signs off, edits fold in; nothing is appended or executed before this
7. On approval - append the new `E<batch>` to the log, execute per `references/execution-and-ablation.md`
8. After execution - verdict-signature self-test: compare the round's verdict distribution to the persona's expected signature; drift is a generator failure - record it in Lessons learned, do not spin it

## Quality gates

- Pre-registration is the prerequisite - single or batch, no hypothesis runs without a signed-off prediction + acceptance bar
- Every candidate fills the full record; the kill-gate and dedupe run BEFORE the proposal, so the user signs off a clean batch
- Heretic anchors every candidate to a real analogue (one fictional ceiling per round, named as such)
- Hybridizer super-additivity claims run jointly through the system, never summed from solo runs
- The append-only registry is what prevents burning the same H-space twice - dedupe is mandatory
- A persona round that matches no part of its verdict signature failed as a generator - the failure is recorded, the round still counts
- The discipline is what makes the grinding compound - bars registered before results exist, labels frozen before any model sees them, kill criteria written down so a pet idea can die, and refutations promoted into the SOTA doc as knowledge, never buried as embarrassments
