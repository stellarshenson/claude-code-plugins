# Examples - real validation rule-sets

Authentic, in-use rule-sets from a real document-processing project (preschool conversation transcriptions reworked into a child-development journal). They show what "the final output must look like X" criteria look like in practice.

- **Origin** - the kind of `INSTRUCTIONS.md` the `process` skill generates and the compliance criteria the `validate` skill collects
- **Use** - load when helping a user author rules for their own task
- **Status** - concrete reference material, not templates to copy verbatim
- **Adapt** - reuse the shape (numbered measurable rules, each with name, criteria, examples, checklist line), not the content

## Files

The two files cover both ends of the workflow - the rule definition and the worked check it produces.

- **`INSTRUCTIONS-example-preschool-transcriptions.md`** - a full `INSTRUCTIONS.md`: context, directory structure, uniformization rules R0-R4 (no-fluff, length range with preferred band, child-focus exclusions, text format, list-section format), the processing workflow, and the archival step
- **Rules are measurable** - word ranges, per-bullet word counts, "test: does this sentence change what the reader knows", explicit exclusion lists with example quotes
- **`uniformization-checklist-example.md`** - a worked uniformization checklist for one processed document: per-rule status (✓/❌), the measured numbers, the quotes found, and the action taken or "OK"
- **Produced by** - Phase 3 of the workflow (Uniformize)

## What makes these good rules

Each property below is what makes a rule machine-checkable rather than aspirational.

- **Measurable** - "350-500 words, prefer 350-400" not "keep it short"; "1-5 bullets, 15-30 words each" not "use a few bullets"
- **Exclusion lists with example quotes** - "remove father's feelings: 'Najboleśniejszym dla mnie...', 'Ucieszyło mnie...'" so the check is unambiguous
- **A falsifiable test** - "if deleting the sentence doesn't change what the reader knows, delete it"
- **A preferred band inside the allowed range** - upper bound only "when the content requires it"
- **Honest escape hatches** - short source → 320-350 words is fine rather than padding to 350 with filler
