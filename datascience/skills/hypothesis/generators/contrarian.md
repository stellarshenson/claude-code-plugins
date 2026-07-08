# Contrarian hypothesiser

Audit policy - attacks the log's own SUPPORTED findings. Inverted convention: a SUPPORTED verdict here means the attack LANDED and the original finding is qualified or dead.

- **Question** - which of OUR findings is wrong, confounded, or an artifact of how we measured it
- **Operators** - invert (each attack targets a specific recorded verdict by id), condition (does the finding survive a regime it was never tested in), deflate (selection, tempo-vs-quantum mirage, baseline leakage as the alternative explanation)
- **Feeds on** - the full SUPPORTED ledger, weighted toward findings that (a) anchor the SOTA design or (b) were tested in only one regime
- **Sourcing** - each attack names the target verdict id, the suspected flaw class (confound / artifact / overfit / regime-narrow), and the observation that motivates suspicion
- **Hypothesis shape** - "E<b>-H<n> claims <X>; because <suspected flaw>, <re-test under Y> will show <the finding degrade past Z>"
- **Healthy verdict signature** - 30-50% of attacks land; 0 landed = the attacks were weak, not the findings strong; > 70% landed = a systemic methodology hole - stop fanout, fix the protocol
- **Anti-patterns** - attacking REFUTED findings (nothing to win); vague "maybe confounded" without a named confound and a discriminating test; re-litigating a verdict a later round already superseded
- **Complement** - this generator attacks recorded findings; hostile review of the artifact itself (code, notebook, writeup) is `datascience:adversarial-review` with the data-scientist adversary

Worked cue (demographic-collapse campaign) - E13: 25 attacks on the campaign's own findings, 12 survived, 13 qualified - half the ledger gained a caveat the SOTA needed.
