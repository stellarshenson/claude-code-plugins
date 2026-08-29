export const meta = {
  name: 'adversarial-review-loop',
  description: 'Managed adversarial review: lens panel, adjudicator rules what blocks, exits with a change PLAN for the main session to apply - the workflow never edits the tree; pinned confirming rounds attack each applied delta',
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
// hostile-reviewed and adjudicated before the loop can close.
//
// MATERIALITY BEFORE SEVERITY. A finding must name who is harmed, doing what
// the product is for, on an input inside the input universe - or it is
// immaterial and the script caps it at MINOR/outOfBar whatever its technical
// truth. Case on record (2026-08-28, wf_a1812379): a <select> pasted into a
// notebook cell was rated MAJOR under an output-only bar, became a
// normalisation pass, and that pass hosted 100% of the next two rounds'
// findings - 1.4M tokens on an input nobody pastes. The user deleted the pass
// in one glance; the loop had no ruling that could.
//
// REVERT BEFORE REFINE. A finding living in code a previous plan introduced is
// first tested as "remove that mechanism, defer the original finding"; the
// adjudicator refines only when the original was material. FANOUT_STOP and
// PLAN carry the revert candidates so the main session reverts deterministically.
//
// args - first invocation (bar, lenses, target mandatory):
//   target     what is under review, e.g. "src/turndown.ts and its tests"
//   scope      in-scope dirs/files and the exclusions, stated as prose
//   bar        OBJECT - the product bar. Required: purpose (what the product is
//              for and for whom), inputs (the input universe it converts /
//              handles), primaryPath (the use every CRITICAL/MAJOR must sit on).
//              Optional: guarantees (output guarantees), outOfScope (input
//              classes explicitly out), degrade (what "degrade gracefully" covers)
//   lenses     array of adversary names, e.g. ["architect", "bug-hunter"]
//   graph      optional path to a refreshed graphify graph.json - reviewers
//              price blast radius from it instead of grepping (fewer turns),
//              the adjudicator uses it to group findings by shared cause and
//              bound each change's radius (cleaner fixes)
//   maxRounds  total reviewer rounds before ROUND_CAP (default 6)
//   cleanRequired  consecutive clean rounds to exit (default 2)
//   maxChanges     advisory plan budget per round (default 3)
// args - re-invocation after applying a PLAN:
//   state         the `state` object from the previous PLAN return, verbatim
//   appliedFixes  [{site, summary, files?}] - what the main session actually
//                 applied (reverts included, as "reverted: <mechanism>");
//                 `files` lists the touched paths and sharpens the confirm filter

if (!args || !args.target || !args.bar || !Array.isArray(args.lenses) || !args.lenses.length) {
  throw new Error('args.target, args.bar and args.lenses are mandatory - the bar is the review\'s scope anchor, refuse to review without one')
}
if (typeof args.bar !== 'object' || !args.bar.purpose || !args.bar.inputs || !args.bar.primaryPath) {
  throw new Error('args.bar must be an object with purpose, inputs and primaryPath - an output-only bar gives reviewers nothing to test materiality against (case on record: a <select> rated MAJOR under "never fuse two values")')
}
const TARGET = args.target
const SCOPE = args.scope || 'the named target only'
const BAR = args.bar
const LENSES = args.lenses
const GRAPH = args.graph || null
const MAX_ROUNDS = args.maxRounds || 6
const CLEAN_REQUIRED = args.cleanRequired || 2
const MAX_CHANGES = args.maxChanges || 3

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
        required: ['severity', 'title', 'file', 'evidence', 'material', 'materiality', 'remedy'],
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'MAJOR', 'MINOR'] },
          taste: { type: 'boolean' },
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          evidence: { type: 'string', description: 'what was observed or reproduced, with the exact input' },
          material: { type: 'boolean', description: 'true ONLY when a user on the primary path, with an input inside the input universe, is harmed; false for a technically true defect on an input the product is not for' },
          materiality: { type: 'string', description: 'who is harmed, doing what the product is for, on which input - or NONE and why' },
          remedy: { type: 'string', description: 'smallest EDIT that removes the cause, or DEFER; a remedy that would add a pass, plugin, branch, helper or data shape opens with NEW MECHANISM' },
          outOfBar: { type: 'boolean', description: 'true when the input class sits outside the stated bar' },
          closure: { type: 'string', description: 'confirming rounds only: the closure this finding fails, quoted from the closure list - a closure that is NOT closed, or the closure whose change caused a regression elsewhere (a broken caller or test in a file the change did not touch); empty only for a regression inside the closure\'s own files' },
        },
      },
    },
    notes: { type: 'string' },
  },
}

const ADJUDICATION_SCHEMA = {
  type: 'object',
  required: ['ruling', 'changes', 'reverts', 'fanoutTraced', 'fanoutTotal'],
  properties: {
    ruling: { type: 'string', enum: ['PROCEED', 'PROCEED_WITH_DEFERRALS', 'STOP'] },
    changes: {
      type: 'array',
      description: 'the change plan, ranked by the materiality of what each answers; EMPTY when no finding warrants a change - that rules the round clean',
      items: {
        type: 'object',
        required: ['answers', 'site', 'change', 'radius', 'newMechanism'],
        properties: {
          answers: { type: 'array', items: { type: 'string' }, description: 'finding titles this change closes' },
          site: { type: 'string' },
          change: { type: 'string' },
          radius: { type: 'string', description: 'what it stays inside and what it could break' },
          newMechanism: { type: 'boolean', description: 'true when the change adds a pass, plugin, branch, helper, guard or data shape that did not exist - new review surface' },
        },
      },
    },
    reverts: {
      type: 'array',
      description: 'mechanisms a previous plan introduced that this round removes instead of refining; EMPTY when nothing loop-introduced is reverted',
      items: {
        type: 'object',
        required: ['mechanism', 'site', 'dissolves', 'defers'],
        properties: {
          mechanism: { type: 'string', description: 'the applied change being removed, as listed under CHANGES APPLIED' },
          site: { type: 'string' },
          dissolves: { type: 'array', items: { type: 'string' }, description: 'this round\'s finding titles that cease to exist once the mechanism is gone' },
          defers: { type: 'array', items: { type: 'string' }, description: 'the original finding(s) the mechanism answered, now deferred with a reason' },
        },
      },
    },
    deferred: { type: 'array', items: { type: 'string' }, description: 'confirmed-but-deferred, each with its reason' },
    refuted: { type: 'array', items: { type: 'string' }, description: 'findings refuted, each with the evidence - immaterial findings land here' },
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

// Materiality cap - SCOPE, not blocking. A finding the reviewer itself marks
// immaterial (material === false) cannot carry CRITICAL or MAJOR into
// adjudication: it is MINOR with outOfBar, whatever its technical truth.
const capImmaterial = (findings) => {
  let capped = 0
  findings.forEach((f) => {
    if (f.material === false && f.severity !== 'MINOR') {
      Object.assign(f, { severity: 'MINOR', outOfBar: true, cappedFrom: f.severity })
      capped += 1
    }
  })
  if (capped) log(`materiality cap: ${capped} immaterial finding(s) reduced to MINOR/outOfBar`)
  return findings
}

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
  return capImmaterial(rows)
}

const barBlock = [
  `BAR (the product bar - severity is judged against THIS, not against all inputs in the world):`,
  `PURPOSE (what the product is for, and for whom): ${BAR.purpose}`,
  `INPUT UNIVERSE (what it handles - anything outside is out of bar): ${BAR.inputs}`,
  `PRIMARY PATH (every CRITICAL or MAJOR must sit on it): ${BAR.primaryPath}`,
  BAR.guarantees ? `GUARANTEES (on the primary path, for the input universe): ${BAR.guarantees}` : null,
  BAR.outOfScope ? `OUT OF SCOPE (explicitly): ${BAR.outOfScope}` : null,
  BAR.degrade ? `DEGRADE GRACEFULLY COVERS: ${BAR.degrade}` : null,
  `MATERIALITY, before severity, for every finding: who is harmed, doing what the product is for, on an input inside the input universe? Nobody → material=false, and the script caps it at MINOR/outOfBar whatever the reproduction shows. A technically true defect on an input the product is not for is not a MAJOR; a guarantee clause never promotes an out-of-universe input into the bar.`,
  `A defect on an input class outside the bar is MINOR with outOfBar=true, whatever its behaviour.`,
  `Severity is evidence for the adjudicator, who alone decides what blocks; taste is always MINOR. Report findings only - no prose verdict.`,
]
  .filter(Boolean)
  .join('\n')

const reviewerPrompt = (lens, body) =>
  [
    `Adversary lens: ${lens}. Adopt that persona file exactly.`,
    `TARGET: ${TARGET}`,
    `SCOPE: ${SCOPE}`,
    barBlock,
    graphBlock,
    body,
    `Critique only - never modify any file. Return your findings through the structured output tool - severities, file:line, evidence, material + materiality, smallest-radius remedy (EDIT or DEFER; NEW MECHANISM named as such). No prose report.`,
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
newDelta.forEach((f) => closures.push({ round, site: f.site, summary: f.summary, files: f.files || [] }))

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
    `Rulings: ${rulings.length ? rulings.map((r) => `round ${r.round} ${r.ruling} (${r.changes} changes, ${r.reverts} reverts, fanout ${r.fanout})`).join('; ') : '(none - first adjudication)'}`,
    `Refuted (stay refuted absent new evidence):`,
    allRefuted.length ? allRefuted.map((r) => `- ${r}`).join('\n') : '(none)',
    `Deferred (stay deferred absent new evidence; do not silently promote):`,
    allDeferred.length ? allDeferred.map((d) => `- ${d}`).join('\n') : '(none)',
  ].join('\n')

const confirmBody = () =>
  [
    `This is a CONFIRMING round, pinned - not a fresh sweep. Two jobs only:`,
    `1. Reproduce each closure below and verify the defect is gone - a closure that is NOT closed is reported with its text in the \`closure\` field.`,
    `2. Attack what the applied changes could have broken - the applied delta is your only attack surface; do not review code the changes did not touch. A regression the change caused outside its own files - a caller, a test - is reported with the causing closure quoted in \`closure\`; the filter keeps a finding by that field, so an unnamed closure means the finding is discarded.`,
    `TURN BUDGET: read the delta, reproduce the closures, run the test command once if one is named, report. Do not rebuild the inventory, do not audit prose, naming, comments or test style, do not write scratch specs beyond what reproduces a closure. The script DISCARDS any finding that is taste, or sits outside the applied delta without naming a failing closure - do not spend turns producing one.`,
    `CLOSURES (all applied so far):`,
    closures.length ? closures.map((c) => `- ${c.site}: ${c.summary}`).join('\n') : '(none applied - verify the clean state holds)',
    `NEWEST DELTA (this invocation's primary attack surface):`,
    newDelta.length ? newDelta.map((c) => `- ${c.site}: ${c.summary}${c.files && c.files.length ? ` [${c.files.join(', ')}]` : ''}`).join('\n') : '(none new)',
  ].join('\n')

// Confirm-round filter - SCOPE, not blocking. Pinning was prompt-only on
// record and reviewers swept anyway (README wording, log-prefix literals,
// doc comments, test style - 19 raw findings per confirming round). A
// confirming finding survives only if it names a failing closure or sits in a
// file the applied changes touched, and is not taste.
const stem = (p) => (p || '').split('/').pop().replace(/\.[^.]+$/, '').toLowerCase()
const inDelta = (f) => {
  const s = stem(f.file)
  if (!s) return false
  return closures.some(
    (c) => (c.files || []).some((p) => stem(p) === s) || (c.site || '').toLowerCase().includes(s)
  )
}
const pinFilter = (findings) => {
  const kept = []
  const dropped = []
  findings.forEach((f) => {
    if (!f.taste && ((f.closure && f.closure.trim()) || inDelta(f))) kept.push(f)
    else dropped.push(f)
  })
  if (dropped.length) {
    log(`confirm filter: ${dropped.length} finding(s) discarded - taste or outside the applied delta: ${dropped.map((d) => d.title).join(' | ')}`)
    history.push({ round, kind: 'confirm-filter', discarded: dropped.map((d) => `${d.file}: ${d.title}`) })
  }
  return kept
}

// --- First panel of this invocation ---------------------------------------
let findings
round += 1
if (!S) {
  phase('Discover')
  log(`round 1 discovery: ${LENSES.join(', ')} over ${TARGET}`)
  findings = mergeFindings(
    await runPanel(
      'Discover',
      `This is a discovery round. Review the target against the bar; reproduce what is testable before reporting it. Answer materiality for every finding before you set its severity.`
    )
  )
  history.push({ round, kind: 'discover', findings: findings.length, severities: severityTally(findings) })
} else {
  log(`round ${round} confirming: pinned to ${closures.length} closure(s), ${newDelta.length} new`)
  findings = pinFilter(mergeFindings(await runPanel('Confirm', confirmBody())))
  history.push({ round, kind: 'confirm', findings: findings.length, severities: severityTally(findings) })
}

while (true) {
  if (!findings.length) {
    cleanStreak += 1
    highFanoutStreak = 0
    log(`round ${round} clean - no findings (${cleanStreak}/${CLEAN_REQUIRED} consecutive)`)
    if (cleanStreak >= CLEAN_REQUIRED || (round === 1 && !S)) {
      shipped = true
      break
    }
  } else {
    // --- Adjudicate: always, on every finding - the adjudicator decides ---
    const adj = await agent(
      [
        `You adjudicate adversarial-review findings for ${TARGET}. YOU decide what blocks - severities are the reviewers' evidence, not a gate: a MINOR worth fixing may enter the plan, a MAJOR you refute does not. An EMPTY changes array rules the round clean - use it when nothing warrants a change. Rulings: PROCEED, PROCEED_WITH_DEFERRALS, or STOP when the loop is generating its own work and the component should be re-modelled instead. Critique and plan only - never modify any file.`,
        barBlock,
        graphBlock,
        priorRecord(),
        `STEP 0 - MATERIALITY TRIAGE, before verifying anything: for each finding ask whether a user on the primary path, with an input inside the input universe, is harmed. Not harmed → refute it as immaterial (list it under refuted with that reason) and spend no verification on it. A reviewer's material=true is a claim, not a fact - test it against the bar. Only then verify the survivors against the code, group by root cause, and return the smallest terminal changes.`,
        `FINDINGS (round ${round}, ${findings.length}: ${severityTally(findings)}; findings carrying cappedFrom were reduced by the script for material=false):`,
        JSON.stringify(findings, null, 2),
        `CHANGES APPLIED IN PREVIOUS ROUNDS (trace fanout against these - fanoutTraced = findings living in code these introduced):`,
        closures.length ? closures.map((c) => `round ${c.round} ${c.site}: ${c.summary}`).join('\n') : '(none - round 1)',
        closures.length
          ? `REVERT BEFORE REFINE: every applied change above is a REVERT CANDIDATE. For each finding that lives in code an applied change introduced, first test the ruling "remove that mechanism and defer the original finding it answered" - that is a \`reverts\` entry, with the findings it dissolves and the originals it defers. Refine the mechanism only when the original finding was material CRITICAL or MAJOR and the refinement is smaller than the removal. Two rounds of conflicting findings on one loop-introduced site are contested semantics: always a revert, never a third refinement. Fanout above 0.5 with no revert must be justified in the ruling.`
          : null,
        `CHANGE BUDGET: rank changes by the materiality of what they answer; at most ${MAX_CHANGES} per round, the rest deferred with a reason to the next invocation. Mark newMechanism=true on any change that adds a pass, plugin, branch, helper, guard or data shape - a new mechanism enters the plan only when it answers a material CRITICAL or MAJOR; otherwise defer it with the finding. Every applied change is next round's attack surface: the round-1 plan on record touched six sites and introduced four mechanisms, and all four hosted the next round's findings.`,
        `A remedy that adds a cap, guard, knob or normalisation pass must name the input that makes it necessary and the measurement showing the unguarded cost; otherwise plan measure-first or delete-the-need, never the guard.`,
      ]
        .filter(Boolean)
        .join('\n\n'),
      { label: `adjudicate:r${round}`, phase: 'Adjudicate', schema: ADJUDICATION_SCHEMA, agentType: 'devils-advocate:adjudicator' }
    )
    if (!adj) return { status: 'ADJUDICATOR_DIED', history, findings, state: stateOut() }
    const reverts = adj.reverts || []
    allDeferred.push(...(adj.deferred || []))
    allRefuted.push(...(adj.refuted || []))
    const fanout = adj.fanoutTotal ? adj.fanoutTraced / adj.fanoutTotal : 0
    rulings.push({ round, ruling: adj.ruling, changes: adj.changes.length, reverts: reverts.length, fanout: `${adj.fanoutTraced}/${adj.fanoutTotal}` })
    log(`round ${round} adjudicated: ${adj.ruling}, ${adj.changes.length} changes, ${reverts.length} reverts, fanout ${adj.fanoutTraced}/${adj.fanoutTotal}`)
    const mechanisms = adj.changes.filter((c) => c.newMechanism)
    if (mechanisms.length) log(`round ${round}: ${mechanisms.length} change(s) add a NEW MECHANISM - veto at PLAN unless each answers a material CRITICAL/MAJOR: ${mechanisms.map((m) => m.site).join(' | ')}`)
    if (fanout > 0.5 && !reverts.length) log(`round ${round}: fanout ${adj.fanoutTraced}/${adj.fanoutTotal} above 0.5 with NO revert ruled - the plan refines loop-introduced code; veto at PLAN or revert by hand`)
    if (adj.changes.length > MAX_CHANGES) log(`round ${round}: plan carries ${adj.changes.length} changes against a budget of ${MAX_CHANGES} - apply the top ${MAX_CHANGES}, defer the rest`)
    if (adj.ruling === 'STOP') {
      return { status: 'STOP', reason: 'adjudicator: the loop is generating its own work - re-model instead of another round - `reverts` is the adjudicator\'s list ({mechanism, site, dissolves, defers}); when the adjudicator ruled none it is every applied change in closure shape ({site, summary, files}) - revert each whose summary does not start "reverted:" (those are reverts already applied, not mechanisms), defer what it answered', round, history, findings, reverts: reverts.length ? reverts : closures, deferred: allDeferred, refuted: allRefuted, state: stateOut() }
    }
    // Fanout counts only while the adjudicator keeps ordering changes: a round
    // it rules clean means the loop stopped generating work, whatever the
    // findings' lineage (case on record: round 3 of the loop's own review -
    // PROCEED, 0 changes, 3 refuted, fanout 3/3 - exited FANOUT_STOP instead
    // of SHIP because this streak was counted before the clean check).
    const refining = adj.changes.length > 0 || reverts.length > 0
    highFanoutStreak = fanout > 0.5 && refining ? highFanoutStreak + 1 : 0
    if (highFanoutStreak >= 2) {
      // Revert candidates: what the adjudicator ruled ({mechanism, site,
      // dissolves, defers}), else every applied change in closure shape
      // ({site, summary, files}) - the findings live in the loop's own fixes
      // by definition; entries whose summary starts "reverted:" are reverts
      // already applied and are skipped by the main session.
      return { status: 'FANOUT_STOP', reason: 'over half the findings traced to this loop\'s own fixes in two consecutive rounds - revert the listed mechanisms, defer what they answered, then re-model if anything material remains - `reverts` is the adjudicator\'s list ({mechanism, site, dissolves, defers}); when the adjudicator ruled none it is every applied change in closure shape ({site, summary, files}) - revert each whose summary does not start "reverted:" (those are reverts already applied, not mechanisms), defer what it answered', round, history, findings, reverts: reverts.length ? reverts : closures, deferred: allDeferred, refuted: allRefuted, state: stateOut() }
    }

    if (adj.changes.length || reverts.length) {
      // --- Exit with the PLAN: the workflow NEVER edits the tree ----------
      cleanStreak = 0
      return {
        status: 'PLAN',
        reverts,
        mechanisms,
        plan: adj.changes,
        fanout: `${adj.fanoutTraced}/${adj.fanoutTotal}`,
        instructions:
          'Apply ONLY this plan in the main session: first `reverts` (remove each listed mechanism, record its deferred originals), then `plan` - these exact changes, smallest radius, nothing else; do not apply reviewer remedies the plan does not name. Read `mechanisms` before applying: each adds review surface and is yours to veto unless it answers a material CRITICAL/MAJOR. Run the test suite. Then re-invoke this workflow with args.state set to the `state` object below, verbatim, and args.appliedFixes = [{site, summary, files}] describing what you actually applied, reverts included - record each applied revert with summary starting "reverted: <mechanism>"; STOP and FANOUT_STOP skip those entries - the next round is a pinned confirm attacking exactly that delta.',
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
  findings = pinFilter(mergeFindings(await runPanel('Confirm', confirmBody())))
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
