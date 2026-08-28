export const meta = {
  name: 'adversarial-review-loop',
  description: 'Deterministic multi-round adversarial review: lens panel, forced adjudication, constrained fixes, pinned confirming rounds, two-clean exit',
  phases: [
    { title: 'Discover', detail: 'one reviewer per lens over the full scope' },
    { title: 'Adjudicate', detail: 'findings become one change plan or a STOP' },
    { title: 'Fix', detail: 'apply only the adjudicated plan' },
    { title: 'Confirm', detail: 'pinned re-review of the closures and the fix delta' },
  ],
}

// The loop protocol lives in this script's control flow, not in any agent's
// context, so no round can be skipped, no verdict can drift, and a compacted
// orchestrator cannot forget the rules. Case on record (2026-08-28): a manual
// 8-round loop rewrote its target mid-review, never adjudicated, trusted
// inflated prose verdicts and fixed reviewer remedies wholesale until the user
// killed it. Every gate below exists because that session lacked it.
//
// args (bar, lenses and target are mandatory):
//   target     what is under review, e.g. "src/turndown.ts and its tests"
//   scope      in-scope dirs/files and the exclusions, stated as prose
//   bar        the product bar: what the target must do, which inputs are out
//              of scope, what "degrade gracefully" covers. Findings outside
//              the bar are capped at MINOR - this is the anti-scope-creep gate
//   lenses     array of adversary names, e.g. ["architect", "bug-hunter"]
//   testCmd    optional command the fixer must keep green, e.g. "uv run pytest -q"
//   maxRounds  total reviewer rounds before ROUND_CAP (default 6)
//   cleanRequired  consecutive clean confirming rounds to exit (default 2)

if (!args || !args.target || !args.bar || !Array.isArray(args.lenses) || !args.lenses.length) {
  throw new Error('args.target, args.bar and args.lenses are mandatory - the bar is the review\'s scope anchor, refuse to review without one')
}
const TARGET = args.target
const SCOPE = args.scope || 'the named target only'
const BAR = args.bar
const LENSES = args.lenses
const TEST_CMD = args.testCmd || null
const MAX_ROUNDS = args.maxRounds || 6
const CLEAN_REQUIRED = args.cleanRequired || 2

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
    fanoutTraced: { type: 'integer', description: 'how many of this round\'s findings sit in code a previous round\'s fix introduced' },
    fanoutTotal: { type: 'integer' },
  },
}

const FIX_SCHEMA = {
  type: 'object',
  required: ['applied', 'testsPass'],
  properties: {
    applied: { type: 'array', items: { type: 'object', required: ['site', 'summary'], properties: { site: { type: 'string' }, summary: { type: 'string' } } } },
    skipped: { type: 'array', items: { type: 'string' } },
    testsPass: { type: 'boolean' },
    notes: { type: 'string' },
  },
}

// Verdict is COMPUTED, never trusted from reviewer prose: blocking iff any
// CRITICAL or MAJOR. Four of the eight rounds in the case on record carried a
// prose verdict the severity mix contradicted.
const blockingOf = (findings) => findings.filter((f) => f.severity === 'CRITICAL' || f.severity === 'MAJOR')

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
  `Severity contract: CRITICAL and MAJOR both block; taste is always MINOR. The verdict is computed by the caller from your severities - report findings only.`,
].join('\n')

const reviewerPrompt = (lens, body) =>
  [
    `Adversary lens: ${lens}. Adopt that persona file exactly.`,
    `TARGET: ${TARGET}`,
    `SCOPE: ${SCOPE}`,
    barBlock,
    body,
    `Return your findings through the structured output tool - severities, file:line, evidence, smallest-radius remedy. No prose report.`,
  ].join('\n\n')

const fixDeltaOf = (fix) => (fix && fix.applied ? fix.applied.map((a) => `${a.site}: ${a.summary}`).join('\n') : '(none)')

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

const history = []
const allDeferred = []
const allRefuted = []
const appliedFixes = []
let round = 0
let cleanStreak = 0
let highFanoutStreak = 0
let findings = null

// --- Round 1: discovery ---------------------------------------------------
round += 1
phase('Discover')
log(`round 1 discovery: ${LENSES.join(', ')} over ${TARGET}`)
findings = mergeFindings(
  await runPanel(
    'Discover',
    `This is a discovery round. Review the target against the bar; reproduce what is testable before reporting it.`
  )
)
history.push({ round, kind: 'discover', findings: findings.length, blocking: blockingOf(findings).length })

while (round < MAX_ROUNDS) {
  const blocking = blockingOf(findings)
  if (!blocking.length) {
    cleanStreak += 1
    log(`round ${round} clean (${cleanStreak}/${CLEAN_REQUIRED} consecutive)`)
    if (cleanStreak >= CLEAN_REQUIRED || round === 1) break
  } else {
    cleanStreak = 0

    // --- Adjudicate: forced by control flow, never optional ---------------
    const adj = await agent(
      [
        `You adjudicate adversarial-review findings for ${TARGET}. Verify each against the code, group by root cause, return the smallest terminal changes. Rulings: PROCEED, PROCEED_WITH_DEFERRALS, or STOP when the loop is generating its own work and the component should be re-modelled instead.`,
        barBlock,
        `FINDINGS (round ${round}, ${blocking.length} blocking of ${findings.length}):`,
        JSON.stringify(findings, null, 2),
        `FIXES APPLIED IN PREVIOUS ROUNDS (trace fanout against these - fanoutTraced = findings living in code these introduced):`,
        appliedFixes.length ? appliedFixes.map((f) => `round ${f.round} ${f.site}: ${f.summary}`).join('\n') : '(none - round 1)',
        `A remedy that adds a cap, guard, knob or normalisation pass must name the input that makes it necessary and the measurement showing the unguarded cost; otherwise plan measure-first or delete-the-need, never the guard.`,
      ].join('\n\n'),
      { label: `adjudicate:r${round}`, phase: 'Adjudicate', schema: ADJUDICATION_SCHEMA, agentType: 'devils-advocate:adjudicator' }
    )
    if (!adj) return { status: 'ADJUDICATOR_DIED', history, findings }
    allDeferred.push(...(adj.deferred || []))
    allRefuted.push(...(adj.refuted || []))
    const fanout = adj.fanoutTotal ? adj.fanoutTraced / adj.fanoutTotal : 0
    log(`round ${round} adjudicated: ${adj.ruling}, ${adj.changes.length} changes, fanout ${adj.fanoutTraced}/${adj.fanoutTotal}`)
    if (adj.ruling === 'STOP') {
      return { status: 'STOP', reason: 'adjudicator: the loop is generating its own work - re-model instead of another round', round, history, findings, deferred: allDeferred, refuted: allRefuted }
    }
    highFanoutStreak = fanout > 0.5 ? highFanoutStreak + 1 : 0
    if (highFanoutStreak >= 2) {
      return { status: 'FANOUT_STOP', reason: 'over half the findings traced to this loop\'s own fixes in two consecutive rounds - stop reviewing, re-model the component', round, history, findings, deferred: allDeferred, refuted: allRefuted }
    }

    // --- Fix: only the adjudicated plan, nothing else ---------------------
    const fix = await agent(
      [
        `Apply this adjudicated change plan to ${TARGET} - these exact changes, smallest radius, nothing else. Do not apply reviewer remedies that are not in the plan. Do not restructure.`,
        JSON.stringify(adj.changes, null, 2),
        TEST_CMD ? `Then run \`${TEST_CMD}\` and iterate until green; report testsPass honestly.` : 'Report testsPass=true only if you verified the change compiles/parses.',
      ].join('\n\n'),
      { label: `fix:r${round}`, phase: 'Fix', schema: FIX_SCHEMA }
    )
    if (!fix || !fix.testsPass) {
      return { status: 'FIX_FAILED', round, history, plan: adj.changes, fix, deferred: allDeferred, refuted: allRefuted }
    }
    fix.applied.forEach((a) => appliedFixes.push({ round, site: a.site, summary: a.summary }))
  }

  // --- Confirming round: pinned by construction ---------------------------
  round += 1
  const closures = appliedFixes.length
    ? appliedFixes.map((f) => `- ${f.site}: ${f.summary}`).join('\n')
    : '(no fixes this loop - verify the clean state holds)'
  log(`round ${round} confirming: pinned to ${appliedFixes.length} closure(s)`)
  findings = mergeFindings(
    await runPanel(
      'Confirm',
      [
        `This is a CONFIRMING round, pinned - not a fresh sweep. Two jobs only:`,
        `1. Reproduce each closure below and verify the defect is gone.`,
        `2. Attack what the fixes could have broken - the fix delta is your only attack surface; do not review code the fixes did not touch.`,
        `CLOSURES:`,
        closures,
        `FIX DELTA:`,
        fixDeltaOf({ applied: appliedFixes.map((f) => ({ site: f.site, summary: f.summary })) }),
      ].join('\n')
    )
  )
  history.push({ round, kind: 'confirm', findings: findings.length, blocking: blockingOf(findings).length })
}

const capped = round >= MAX_ROUNDS && cleanStreak < CLEAN_REQUIRED && blockingOf(findings).length > 0
return {
  status: capped ? 'ROUND_CAP' : 'SHIP',
  rounds: round,
  history,
  openMinors: findings.filter((f) => f.severity === 'MINOR'),
  openBlocking: blockingOf(findings),
  fixes: appliedFixes,
  deferred: allDeferred,
  refuted: allRefuted,
}
