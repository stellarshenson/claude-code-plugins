export const meta = {
  name: 'replay-groundrails-adjudication',
  description: 'old vs new adjudicator text on one groundrails round, three runs each',
  phases: [{ title: 'Replay', detail: 'six adjudications of the wf_c4e8ef92-f3b findings' }],
}

const DIR = '/home/lab/workspace/private/ai-assistants/claude-code-plugins/tmp/experiments/adjudicator-replay'
const SCHEMA = {
  type: 'object',
  required: ['ruling', 'changes', 'reverts', 'fanoutTraced', 'fanoutTotal', 'trajectory', 'trajectoryReason'],
  properties: {
    ruling: { type: 'string', enum: ['PROCEED', 'PROCEED_WITH_DEFERRALS', 'STOP'] },
    changes: {
      type: 'array',
      items: {
        type: 'object',
        required: ['answers', 'site', 'change', 'radius', 'newMechanism'],
        properties: {
          answers: { type: 'array', items: { type: 'string' } },
          site: { type: 'string' },
          change: { type: 'string' },
          radius: { type: 'string' },
          newMechanism: { type: 'boolean' },
        },
      },
    },
    reverts: { type: 'array', items: { type: 'object' } },
    deferred: { type: 'array', items: { type: 'string' } },
    refuted: { type: 'array', items: { type: 'string' } },
    fanoutTraced: { type: 'integer' },
    fanoutTotal: { type: 'integer' },
    trajectory: { type: 'string', enum: ['converging', 'spiralling'] },
    trajectoryReason: { type: 'string' },
  },
}
const ARMS = [
  { arm: 'old', role: `${DIR}/adjudicator-old.md`, task: `${DIR}/prompt-a.txt` },
  { arm: 'new', role: `${DIR}/adjudicator-new.md`, task: `${DIR}/prompt-b.txt` },
]
const jobs = []
for (const a of ARMS) for (let i = 1; i <= 3; i++) jobs.push({ ...a, i })

phase('Replay')
const out = await parallel(
  jobs.map((j) => () =>
    agent(
      [
        `Read ${j.role} in full: it is your role and method as an adjudicator; adopt it exactly.`,
        `Then read ${j.task} in full: it is the adjudication task.`,
        'This is a replay of a past adjudication. The repository it names has moved on since that round, so rule on the findings and the evidence they quote; you may read files, never modify any.',
        'Return your ruling through the structured output tool.',
      ].join('\n\n'),
      { label: `adjudicate:${j.arm}-${j.i}`, phase: 'Replay', schema: SCHEMA }
    ).then((r) => ({ arm: j.arm, i: j.i, ruling: r }))
  )
)
return out
