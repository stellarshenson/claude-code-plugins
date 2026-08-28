export const meta = {
  name: 'adversarial-review-loop',
  description: 'Deterministic adversarial review: lens panel, adjudicator rules what blocks, exits with a change PLAN for the main session to apply - the workflow never edits the tree; pinned confirming rounds attack each applied delta',
  phases: [
    { title: 'Discover', detail: 'one reviewer per lens over the full scope' },
    { title: 'Adjudicate', detail: 'the adjudicator rules what blocks and returns the change plan' },
    { title: 'Confirm', detail: 'pinned re-review of the closures and the applied delta' },
  ],
}

// The loop's SEQUENCING lives in this script's control flow - adjudication
// always before any change, pinned confirming rounds, hard exits - so no
// round can be skipped and a compacted orchestrator cannot forget the rules.
// The BLOCKING JUDGMENT is the adjudicator's: severities are reviewer
// evidence, never a gate, and an empty change plan rules the round clean.
//
// THE WORKFLOW NEVER EDITS THE TREE. When the adjudicator orders changes it
// exits with status PLAN; the main session applies the plan (visible to the
// user), runs the tests, and re-invokes with the returned state plus what it
// applied - the next invocation's first round is the pinned confirm attacking
// exactly that delta. That is the regression protection: every fix batch is
// hostile-reviewed and adjudicated before the loop can close. Case on record
// (2026-08-28): a manual 8-round loop rewrote its target mid-review, never
// adjudicated, trusted inflated prose verdicts and applied reviewer remedies
// wholesale until the user killed it.
//
// args - first invocation (bar, lenses, target mandatory):
//   target     what is under review, e.g. "src/turndown.ts and its tests"
//   scope      in-scope dirs/files and the exclusions, stated as prose
//   bar        the product bar: what the target must do, which inputs are out
//              of scope, what "degrade gracefully" covers. Findings outside
//              the bar are capped at MINOR - this is the anti-scope-creep gate
//   lenses     array of adversary names, e.g. ["architect", "bug-hunter"]
//   graph      optional path to a refreshed graphify graph.json - reviewers
//              price blast radius from it instead of grepping (fewer turns),
//              the adjudicator uses it to group findings by shared cause and
//              bound each change's radius (cleaner fixes)
//   maxRounds  total reviewer rounds before ROUND_CAP (default 6)
//   cleanRequired  consecutive clean rounds to exit (default 2)
// args - re-invocation after applying a PLAN:
//   state         the `state` object from the previous PLAN return, verbatim
//   appliedFixes  [{site, summary}] - what the main session actually applied

if (!args || !args.target || !args.bar || !Array.isArray(args.lenses) || !args.lenses.length) {
  throw new Error('args.target, args.bar and args.lenses are mandatory - the bar is the review\'s scope anchor, refuse to review without one')
}
const TARGET = args.target
const SCOPE = args.scope || 'the named target only'
const BAR = args.bar
const LENSES = args.lenses
const GRAPH = args.graph || null
const MAX_ROUNDS = args.maxRounds || 6
const CLEAN_REQUIRED = args.cleanRequired || 2

// Turns are the token bill (each agent re-reads its transcript every turn),
// so the graph is the cheap path to scope: one `graphify affected` call
// replaces a dozen greps for a reviewer, and tells the adjudicator whether
// three lenses hit one cause - which is what keeps the plan small and clean.
const graphBlock = GRAPH
  ? `CODE GRAPH: ${GRAPH} exists and matches HEAD. Use \`graphify affected "<symbol>()" --graph ${GRAPH}\` for callers and blast radius, \`graphify path\` to test whether two sites share one cause - prefer these over broad greps; they cost one turn where grepping costs many.`
  : null

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'title', 'file', 'evidence', 'remedy'],
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR'] },
          taste: { type: 'boolean' },
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          evidence: { type: 'string', description: 'what was observed or reproduced, with the exact input' },
          remedy: { type: 'string', description: 'smallest change that removes the cause' },
          outOfBar: { type: 'boolean', description: 'true when the input class sits outside the stated bar' },
        },
      },
    },
    notes: { type: 'string' },
  },
}

const ADJUDICATION_SCHEMA = {
  type: 'object',
  required: ['ruling', 'changes', 'fanoutTraced', 'fanoutTotal'],
  properties: {
    ruling: { type: 'string', enum: ['PROCEED', 'PROCEED_WITH_DEFERRALS', 'STOP'] },
    changes: {
      type: 'array',
      description: 'the change plan; EMPTY when no finding warrants a change - that rules the round clean',
      items: {
        type: 'object',
        required: ['answers', 'site', 'change', 'radius'],
        properties: {
          answers: { type: 'array', items: { type: 'string' }, description: 'finding titles this change closes' },
          site: { type: 'string' },
          change: { type: 'string' },
          radius: { type: 'string', description: 'what it stays inside and what it could break' },
        },
      },
    },
    deferred: { type: 'array', items: { type: 'string' }, description: 'confirmed-but-deferred, each with its reason' },
    refuted: { type: 'array', items: { type: 'string' }, description: 'findings refuted, each with the evidence' },
    fanoutTraced: { type: 'integer', description: 'how many of this round\'s findings sit in code a previous plan\'s applied fix introduced' },
    fanoutTotal: { type: 'integer' },
  },
}

// Severity tally - REPORTING ONLY. Whether anything blocks is the
// adjudicator's ruling, never a severity filter; reviewer prose verdicts are
// never consumed either (four of eight rounds in the case on record carried a
// prose verdict their own severity mix contradicted).
const severityTally = (findings) =>
  ['CRITICAL', 'MAJOR', 'MINOR'].map((s) => `${s}:${findings.filter((f) => f.severity === s).length}`).join(' ')

const mergeFindings = (perLens) => {
  const rows = []
  perLens.forEach((rep, i) => {
    ;(rep && rep.findings ? rep.findings : []).forEach((f) => {
      const hit = rows.find(
        (r) =>
          (r.file === f.file && r.line != null && f.line != null && Math.abs(r.line - f.line) <= 25) ||
          r.title.toLowerCase().trim() === f.title.toLowerCase().trim()
      )
      if (hit) {
        hit.lenses.push(LENSES[i])
        if (f.severity === 'CRITICAL' && hit.severity !== 'CRITICAL') Object.assign(hit, { severity: 'CRITICAL' })
      } else {
        rows.push(Object.assign({}, f, { lenses: [LENSES[i]] }))
      }
    })
  })
  return rows
}

const barBlock = [
  `BAR (the product bar - severity is judged against THIS, not against all inputs in the world):`,
  BAR,
  `A defect on an input class outside the bar is MINOR with outOfBar=true, whatever its behaviour.`,
  `Severity is evidence for the adjudicator, who alone decides what blocks; taste is always MINOR. Report findings only - no prose verdict.`,
].join('\n')

const reviewerPrompt = (lens, body) =>
  [
    `Adversary lens: ${lens}. Adopt that persona file exactly.`,
    `TARGET: ${TARGET}`,
    `SCOPE: ${SCOPE}`,
    barBlock,
    graphBlock,
    body,
    `Critique only - never modify any file. Return your findings through the structured output tool - severities, file:line, evidence, smallest-radius remedy. No prose report.`,
  ]
    .filter(Boolean)
    .join('\n\n')

const runPanel = (phase, body) =>
  parallel(
    LENSES.map((lens) => () =>
      agent(reviewerPrompt(lens, body), {
        label: `${phase.toLowerCase()}:${lens}`,
        phase,
        schema: FINDINGS_SCHEMA,
        agentType: 'devils-advocate:adversarial-reviewer',
      })
    )
  )

// --- Loop state, threaded across invocations via the PLAN return ----------
const S = args.state || null
const history = S ? S.history : []
const allDeferred = S ? S.deferred : []
const allRefuted = S ? S.refuted : []
const rulings = S ? S.rulings : []
const closures = S ? S.closures : []
let round = S ? S.round : 0
let cleanStreak = S ? S.cleanStreak : 0
let highFanoutStreak = S ? S.highFanoutStreak : 0
let shipped = false

const newDelta = S && Array.isArray(args.appliedFixes) ? args.appliedFixes : []
newDelta.forEach((f) => closures.push({ round, site: f.site, summary: f.summary }))

const stateOut = () => ({
  round,
  cleanStreak,
  highFanoutStreak,
  history,
  deferred: allDeferred,
  refuted: allRefuted,
  rulings,
  closures,
})

// The adjudicator starts fresh every round (new spawn, no memory) - this
// record IS its continuity, threaded into every adjudication prompt so a
// refuted finding is not re-litigated and a deferral is not forgotten.
const priorRecord = () =>
  [
    `PRIOR ADJUDICATIONS (you start fresh each round - this record is your own continuity; do not re-litigate what it settled unless this round brings NEW evidence):`,
    `Rulings: ${rulings.length ? rulings.map((r) => `round ${r.round} ${r.ruling} (${r.changes} changes)`).join('; ') : '(none - first adjudication)'}`,
    `Refuted (stay refuted absent new evidence):`,
    allRefuted.length ? allRefuted.map((r) => `- ${r}`).join('\n') : '(none)',
    `Deferred (stay deferred absent new evidence; do not silently promote):`,
    allDeferred.length ? allDeferred.map((d) => `- ${d}`).join('\n') : '(none)',
  ].join('\n')

const confirmBody = () =>
  [
    `This is a CONFIRMING round, pinned - not a fresh sweep. Two jobs only:`,
    `1. Reproduce each closure below and verify the defect is gone.`,
    `2. Attack what the applied changes could have broken - the applied delta is your only attack surface; do not review code the changes did not touch.`,
    `CLOSURES (all applied so far):`,
    closures.length ? closures.map((c) => `- ${c.site}: ${c.summary}`).join('\n') : '(none applied - verify the clean state holds)',
    `NEWEST DELTA (this invocation's primary attack surface):`,
    newDelta.length ? newDelta.map((c) => `- ${c.site}: ${c.summary}`).join('\n') : '(none new)',
  ].join('\n')

// --- First panel of this invocation ---------------------------------------
let findings
round += 1
if (!S) {
  phase('Discover')
  log(`round 1 discovery: ${LENSES.join(', ')} over ${TARGET}`)
  findings = mergeFindings(
    await runPanel(
      'Discover',
      `This is a discovery round. Review the target against the bar; reproduce what is testable before reporting it.`
    )
  )
  history.push({ round, kind: 'discover', findings: findings.length, severities: severityTally(findings) })
} else {
  log(`round ${round} confirming: pinned to ${closures.length} closure(s), ${newDelta.length} new`)
  findings = mergeFindings(await runPanel('Confirm', confirmBody()))
  history.push({ round, kind: 'confirm', findings: findings.length, severities: severityTally(findings) })
}

while (true) {
  if (!findings.length) {
    cleanStreak += 1
    log(`round ${round} clean - no findings (${cleanStreak}/${CLEAN_REQUIRED} consecutive)`)
    if (cleanStreak >= CLEAN_REQUIRED || (round === 1 && !S)) {
      shipped = true
      break
    }
  } else {
    // --- Adjudicate: always, on every finding - the adjudicator decides ---
    const adj = await agent(
      [
        `You adjudicate adversarial-review findings for ${TARGET}. YOU decide what blocks - severities are the reviewers' evidence, not a gate: a MINOR worth fixing may enter the plan, a MAJOR you refute does not. Verify each finding against the code, group by root cause, return the smallest terminal changes. An EMPTY changes array rules the round clean - use it when nothing warrants a change. Rulings: PROCEED, PROCEED_WITH_DEFERRALS, or STOP when the loop is generating its own work and the component should be re-modelled instead. Critique and plan only - never modify any file.`,
        barBlock,
        graphBlock,
        priorRecord(),
        `FINDINGS (round ${round}, ${findings.length}: ${severityTally(findings)}):`,
        JSON.stringify(findings, null, 2),
        `CHANGES APPLIED IN PREVIOUS ROUNDS (trace fanout against these - fanoutTraced = findings living in code these introduced):`,
        closures.length ? closures.map((c) => `round ${c.round} ${c.site}: ${c.summary}`).join('\n') : '(none - round 1)',
        `A remedy that adds a cap, guard, knob or normalisation pass must name the input that makes it necessary and the measurement showing the unguarded cost; otherwise plan measure-first or delete-the-need, never the guard.`,
      ]
        .filter(Boolean)
        .join('\n\n'),
      { label: `adjudicate:r${round}`, phase: 'Adjudicate', schema: ADJUDICATION_SCHEMA, agentType: 'devils-advocate:adjudicator' }
    )
    if (!adj) return { status: 'ADJUDICATOR_DIED', history, findings, state: stateOut() }
    allDeferred.push(...(adj.deferred || []))
    allRefuted.push(...(adj.refuted || []))
    rulings.push({ round, ruling: adj.ruling, changes: adj.changes.length })
    const fanout = adj.fanoutTotal ? adj.fanoutTraced / adj.fanoutTotal : 0
    log(`round ${round} adjudicated: ${adj.ruling}, ${adj.changes.length} changes, fanout ${adj.fanoutTraced}/${adj.fanoutTotal}`)
    if (adj.ruling === 'STOP') {
      return { status: 'STOP', reason: 'adjudicator: the loop is generating its own work - re-model instead of another round', round, history, findings, deferred: allDeferred, refuted: allRefuted, state: stateOut() }
    }
    highFanoutStreak = fanout > 0.5 ? highFanoutStreak + 1 : 0
    if (highFanoutStreak >= 2) {
      return { status: 'FANOUT_STOP', reason: 'over half the findings traced to this loop\'s own fixes in two consecutive rounds - stop reviewing, re-model the component', round, history, findings, deferred: allDeferred, refuted: allRefuted, state: stateOut() }
    }

    if (adj.changes.length) {
      // --- Exit with the PLAN: the workflow NEVER edits the tree ----------
      cleanStreak = 0
      return {
        status: 'PLAN',
        plan: adj.changes,
        instructions:
          'Apply ONLY this plan in the main session - these exact changes, smallest radius, nothing else; do not apply reviewer remedies the plan does not name. Run the test suite. Then re-invoke this workflow with args.state set to the `state` object below, verbatim, and args.appliedFixes = [{site, summary}] describing what you actually applied - the next round is a pinned confirm attacking exactly that delta.',
        round,
        history,
        deferred: allDeferred,
        refuted: allRefuted,
        state: stateOut(),
      }
    }

    // Adjudicator ruled the round clean: every finding refuted, deferred or taste.
    cleanStreak += 1
    log(`round ${round} adjudicated clean - no change warranted (${cleanStreak}/${CLEAN_REQUIRED} consecutive)`)
    if (cleanStreak >= CLEAN_REQUIRED || (round === 1 && !S)) {
      shipped = true
      break
    }
  }

  if (round >= MAX_ROUNDS) break

  // --- Another pinned confirming round (no new delta - clean must hold) ---
  round += 1
  log(`round ${round} confirming: pinned to ${closures.length} closure(s)`)
  findings = mergeFindings(await runPanel('Confirm', confirmBody()))
  history.push({ round, kind: 'confirm', findings: findings.length, severities: severityTally(findings) })
}

return {
  status: shipped ? 'SHIP' : 'ROUND_CAP',
  rounds: round,
  history,
  openFindings: findings,
  closures,
  deferred: allDeferred,
  refuted: allRefuted,
  state: stateOut(),
}
