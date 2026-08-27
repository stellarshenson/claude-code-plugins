# Devil's Advocate - Executive Pushback Scenarios

How the executive persona is likely to misread or spin the numbers, and how to respond.

## Scoring

Each concern is scored on two dimensions:

- **Likelihood** (1-5): How likely the executive is to raise this concern
- **Impact** (1-5): How much damage this concern does if left unaddressed

**Risk = Likelihood x Impact**. Higher score = must be addressed in the executive summary.

| # | Concern | Likelihood | Impact | Risk | v1 | v2 | v3 | v4 | v5 | v6 | v7 | v8 |
|---|---------|-----------|--------|------|----|----|-----|-----|-----|-----|-----|-----|
| 1 | Class A missed by half | 5 | 5 | 25 | Partial | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| 2 | Only 2 of 3 targets met | 5 | 4 | 20 | No | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| 3 | Blaming the LLM engine | 3 | 3 | 9 | Partial | Partial | Partial | Yes | Yes | Yes | Yes | Yes |
| 4 | 13% still needs humans | 4 | 3 | 12 | No | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| 5 | 7 wrong fields = 7 wrong tickets | 3 | 4 | 12 | Partial | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| 6 | Reclassified 40 errors away | 4 | 5 | 20 | No | Yes | Yes | Partial | Partial | Partial | Partial | Partial |
| 7 | Why should I sign off on a miss | 5 | 5 | 25 | Partial | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| 8 | Over-explanation reads as excuses | 4 | 5 | 20 | No | No | No | Yes | Yes | Yes | Yes | Yes |
| 9 | Defensive tone erodes confidence | 5 | 5 | 25 | No | Partial | Partial | Yes | Yes | Yes | Yes | Yes |
| 10 | Too many numbers, not enough clarity | 5 | 4 | 20 | No | No | No | No | Yes | Yes | Yes | Yes |
| 11 | Overstructure - too many sections/tables | 4 | 4 | 16 | No | No | No | No | Partial | Yes | Yes | Yes |
| 12 | Finger-pointing at customer | 5 | 5 | 25 | No | No | No | No | Partial | Yes | Yes | Yes |
| 13 | 87% fields but 55% emails - looks like failure | 5 | 5 | 25 | No | No | No | No | No | No | Yes | Yes |
| 14 | Text-based numbers exhaust executive patience | 5 | 5 | 25 | No | No | No | No | No | No | No | Yes |
| 15 | SOW quotes provide legal cover (positive) | 5 | 5 | -25 | Partial | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| 16 | Verbose sentences signal lack of confidence | 5 | 4 | 20 | No | No | No | No | Partial | Partial | Partial | Yes |
| 17 | Why are you using such an outdated model - 3.7? | 4 | 4 | 16 | No | No | No | No | No | No | No | No |
| 18 | Why agree to ABC metrics if mathematically impossible? | 4 | 5 | 20 | No | No | No | No | No | No | No | No |
| 19 | Overcomplicated language | 5 | 4 | 20 | No | Partial | Partial | Partial | Partial | Partial | Partial | Partial |
| 20 | Class A missing from SOW table | 4 | 5 | 20 | No | No | No | No | No | No | No | No |
| 21 | Why didn't you push for Claude 4? | 5 | 5 | 25 | No | No | No | No | No | No | No | No |

**v1: 269 / 400** - "Not met" table, no visuals, verbose, SOW buried
**v2: 156 / 400** - SOW helps but verbose sentences, defensive headers, 13+ inline numbers
**v3: 142 / 400** - SOW + tables but verbose explanations, 5 sections, too many numbers
**v4: 100 / 400** - trimmed but verbose where it counts, percentage-heavy, no visuals
**v5: 64 / 400** - plainer but "routes that email for a quick human check on that specific field rather than guessing" is verbose
**v6: 41 / 400** - cleaner but still text-heavy number delivery, some verbose phrases
**v7: 16 / 400** - concrete example but verbose opening, text-based numbers
**v8: 2 / 400** - SVG infographics replace inline numbers, tight sentences, SOW quote, one table

---

## 1. "You missed the Class A target by half"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: 55% versus 90% is a massive miss. The SOW says 90%. You delivered 55%. That is a failure. I cannot present this to the board as a success when one of three KPIs is at 55%.

**Reality**: Class A is not a quality metric. It is a composite metric that collapses when any one of 20-30 fields has low confidence. The system's actual field-level accuracy is 87%. Class A penalises caution - flagging a field for review instead of guessing moves the entire email from A to B.

**Response**: "The 55% reflects the system being cautious, not wrong. 87% of fields need no human touch. The 45% Class B emails are not failures - they are emails where the system correctly asked for help on one or two fields."

## 2. "Only two of three targets met - that is not a pass"

**Likelihood: 5** | **Impact: 4** | **Risk: 20**

**Their take**: We agreed on three targets. You met two. That is 67%. I would not accept 67% from my team.

**Reality**: The SOW explicitly includes a provision for reduced metrics with customer approval. The two targets met are the safety-critical ones (error rate and combined accuracy). The one missed is an efficiency metric.

**Response**: "The two targets met are the ones that protect Meridian Networks from bad data entering the system. Class A is about how much human review is needed - not about whether the system works."

## 3. "You are blaming the LLM engine - that is an excuse"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: You chose the technology. Now you say the LLM is old and better ones exist. If you knew this, why did you build on it? This sounds like you want more budget to upgrade.

**Reality**: Meridian Networks selected Claude Sonnet 3.5 and 3.7 for cost and security (EU hosting region). The SOW explicitly allows better models: *"model selection best suitable to implement its features"* and *"Other models can be discussed during the project."* The team proposed Sonnet 4 but it was not approved. Both 3.5 and 3.7 are approaching end-of-life.

**Response**: "The SOW allows selecting the best model for the task. The current models were selected for cost and hosting reasons. Newer models would improve Class A directly when approved."

## 4. "87% automation means 13% still needs humans"

**Likelihood: 4** | **Impact: 3** | **Risk: 12**

**Their take**: So we still need people. What is the point of the automation if 13% needs manual review?

**Reality**: Before the system, 100% of fields required manual processing. Now 87% are fully automated and 12% need a quick review of a flagged field - not full manual processing. The human reviews one or two fields, not the entire email.

**Response**: "Before this system, operators processed every field of every email manually. Now they only review specific flagged fields on 12% of extractions. That is a reduction from 100% manual to 13% partial review."

## 5. "0.4% error rate sounds good but 7 wrong fields is 7 wrong tickets"

**Likelihood: 3** | **Impact: 4** | **Risk: 12**

**Their take**: Each wrong field could mean a misconfigured maintenance window. Seven errors in 98 emails is seven potential service disruptions.

**Reality**: The 7 errors are across 1,583 fields, not 98 emails. Six of the seven are timezone or impact interpretation differences - not the kind of error that causes service disruption. The one genuine error was a timezone swap (New York vs Los Angeles).

**Response**: "Six of the seven are borderline interpretations that a human reviewer would also debate. The one genuine error was caught during review. No system - human or automated - achieves zero errors across 1,583 data points."

## 6. "You reclassified 40 errors as non-errors - that is moving the goalposts"

**Likelihood: 4** | **Impact: 5** | **Risk: 20**

**Their take**: You took 47 failures and argued 40 of them away. That is convenient. How do I know you are not just explaining away real problems?

**Reality**: The reclassification was validated with Meridian Networks's own evaluation team. The largest group (26 fields) is the system returning "8 HOURS" where the scoring expected "480 MINUTES" - the same value in a different unit. This is a scoring issue, not an extraction error.

**Response**: "Your evaluation team reviewed every reclassification and agreed. The biggest category - 26 fields - is the system saying 8 hours instead of 480 minutes. That is the same answer in a different format."

## 7. "Why should I approve production with a missed target?"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: My signature on this means I accepted a deliverable that did not meet spec. That is a risk for me personally.

**Reality**: The SOW provision exists precisely for this scenario. The approval is conditional and documented. The field-level metrics demonstrate the system works. The missed target is a known mathematical limitation of composite metrics with many fields.

**Response**: "The SOW includes a provision for exactly this situation - reduced metrics accepted after review. Your evaluation team has reviewed the data. The system automates 87% of the work and catches its own uncertainty. This is the approval the SOW was designed for."

## 8. "This reads like you are making excuses"

**Likelihood: 4** | **Impact: 4** | **Risk: 16**

**Their take**: Too many paragraphs explaining why Class A is low. If the system worked, you would not need this much explanation. The more you explain, the less confident I am.

**Reality**: Executive personas read length as defensiveness. Every sentence of justification erodes confidence rather than building it. The persona wants a headline and a number, not a statistical argument.

**Response**: Do not respond verbally. Fix the document. State Class A in one sentence, not four. Let the numbers speak. If the executive asks why, answer then - do not pre-answer questions they have not asked.

## 9. "This reads like you are on the back foot"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: Section headers like "Why Class A is below target" or "Quality validation" signal a problem before the reader even gets to the content. The document structure itself tells me something went wrong and you are trying to manage my reaction. If you were confident, you would state the result and move on.

**Reality**: Defensive framing is cumulative. Each hedging phrase ("below target", "not a failure", "the system is being cautious") adds to the impression that the vendor is managing expectations downward. The executive reads tone, not detail.

**Response**: Restructure. Lead with what the system does (87%, 0.4% errors). State SOW compliance as fact, not argument. Class A goes in one sentence without a dedicated section. No section header should contain the word "why" or frame a result as needing explanation.

## 10. "I stopped reading after the third percentage"

**Likelihood: 5** | **Impact: 4** | **Risk: 20**

**Their take**: 87%, 12%, 0.4%, 71%, 16%, 98%, 2%, 55%, 90%. I have lost track of which number matters. This reads like a lab report, not a business summary. Tell me what the system does, not how you measured it.

**Reality**: Executives process one or two key numbers per section. Every additional percentage dilutes the message. A table with four percentage rows is a spreadsheet, not communication. The persona understands "nearly all fields automated, almost no errors" faster than "71% TP + 16% TN = 87%".

**Response**: Lead with plain language. Use one number per key message. "The system automates nearly all field extraction. Out of 1,583 fields tested, 7 were wrong." Reserve the detailed breakdown for an appendix or follow-up if asked. One table maximum - SOW compliance only.

## 11. "This document has too many sections"

**Likelihood: 4** | **Impact: 4** | **Risk: 16**

**Their take**: Five sections with headers, two tables, bullet lists - this looks like a project status report, not a summary. I need to present this to the board in two minutes. Give me something I can scan in 30 seconds.

**Reality**: Every additional section header is a decision point where the reader can stop reading. Executives scan structure before content. Five sections signals complexity. Two tables signal data analysis. The persona wants a narrative with one supporting table at most.

**Response**: Three sections maximum. One table (SOW compliance). Everything else in flowing paragraphs. The document should fit on one screen.

## 12. "You are pointing the finger at us"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: "Customer-imposed constraint", "Meridian Networks declined", "Meridian Networks chose to restrict" - you are saying this is our fault. That is not how a vendor talks to a customer. Even if it is true, putting it in writing makes me defensive and less likely to approve.

**Reality**: Factually accurate blame-shifting is still blame-shifting. The executive will react to the framing, not the facts. Stating that the customer made a choice that limited performance reads as an accusation regardless of intent.

**Response**: Use neutral, forward-looking language. "The current models were selected for cost and hosting reasons" - no subject, no blame. "Newer models will improve metrics when available in the region" - positions it as opportunity, not complaint. Never use "Meridian Networks chose", "customer declined", or "we were forbidden".

## 13. "If 87% of fields are correct, why are only 55% of emails correct? That is a failure."

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: You say 87% of fields are handled correctly. But only 55% of emails pass as Class A. How does 87% become 55%? If the system gets 87% of things right, it should get 87% of emails right. The gap between 87% and 55% tells me something is broken. This is a total failure of the automation.

**Reality**: This is the most dangerous confusion in the document because it is intuitive and wrong. The executive assumes field accuracy maps linearly to email accuracy. It does not. An email with 30 fields only passes Class A if every single field is correct. If 87% of fields are correct, that means roughly 4 out of 30 fields per email are uncertain. One uncertain field fails the entire email. The analogy: if a factory has 30 quality checkpoints and each one passes 87% of the time, only 1.3% of products pass all 30 checks. The field rate and the email rate measure fundamentally different things.

**Response**: Do not use percentages to explain this. Use a concrete example the executive can picture: "Each email has 30 fields. The system gets nearly all of them right. But if it flags even one field as uncertain - say, an ambiguous maintenance time - the entire email moves to Class B for a quick human check. That is why 87% field accuracy produces 55% email pass rate. The system is not getting emails wrong - it is asking for help on one field out of thirty."

## 14. "I stopped reading - too many numbers in the text"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: "98 emails, 1,583 fields, 7 wrong, 87%, 55%, 98%, 2%" - I read one paragraph and I have already seen seven numbers. My eyes glaze over. I cannot relay this to my board because I cannot remember which number matters. If you need this many numbers to make your case, maybe the case is not strong.

**Reality**: Every inline number in flowing text competes for executive attention. Text is the worst medium for conveying numerical relationships. A single visual - a pie chart, a stacked bar, an infographic - communicates what three paragraphs of percentages cannot. The executive processes "a big green bar and a tiny red sliver" instantly. They do not process "1,122 out of 1,583 fields (71%) were true positives while 7 (0.4%) were false positives."

**Response**: Replace text-based number delivery with SVG infographics. Key visuals needed: (1) field-level breakdown as a stacked bar or pie showing green/amber/red proportions, (2) email-level Class A/B/C as a simple visual, (3) before/after comparison (100% manual -> 87% automated). Keep the SOW compliance table as the only text-based numbers. Reference infographics from the document with `![](images/filename.svg)` links.

## 15. SOW quotes provide legal cover (POSITIVE - reduces risk)

**Likelihood: 5** | **Impact: 5** | **Risk: -25** (reduces total risk when used)

**Their take**: The executive sees a direct quote from the contract. This is not vendor interpretation - this is what was agreed. It shifts the conversation from "should we accept this" to "the contract already provides for this."

**Reality**: SOW clauses are legally binding. Quoting them transforms the executive summary from a persuasion document into a compliance document. Key clauses available:
- *"Reduced metric values would be potentially allowed given approval from the customer after review of the data and circumstances"* - covers Class A gap
- *"model selection best suitable to implement its features"* and *"Other models can be discussed during the project"* - covers model constraint
- *"Team should primarily use Anthropic models (i.e. ideally Claude 3.5 and 3.7)"* - documents that 3.5/3.7 was the baseline expectation

**Response**: Use SOW quotes strategically. One quote per key decision point. The reduced metrics clause is the most powerful - it was written for exactly this scenario. The model selection clause is useful if the executive pushes on LLM choice. Do not over-quote - one or two direct citations carry more weight than three or four.

## 16. "This sentence could have been five words"

**Likelihood: 5** | **Impact: 4** | **Risk: 20**

**Their take**: "It routes that email for a quick human check on that specific field rather than guessing" - I stopped reading halfway. Just say "email goes to manual queue." Every extra word is a word I have to process. If you need 20 words to say what 5 words can say, you are padding.

**Reality**: Verbose sentences signal that the writer is uncertain and compensating with volume. Short, direct sentences project confidence. The executive equates brevity with competence.

**Response**: Cut every sentence to its core. "The system flags uncertain fields" not "the system identifies fields where it has low confidence and routes them for human review." "Email goes to manual queue" not "it routes that email for a quick human check on that specific field rather than guessing." If a sentence has a clause after a dash, delete the clause.

## 17. "Why are you using such an outdated model - 3.7?"

**Likelihood: 4** | **Impact: 4** | **Risk: 16**

**Their take**: Claude 3.7 is approaching end-of-life. Claude 4 has been out for months. You are running production on a model the vendor is about to deprecate. That is a technology risk. Why would I approve a system built on yesterday's engine? This looks like the team stopped paying attention.

**Reality**: The SOW specifies *"Team should primarily use Anthropic models (i.e. ideally Claude 3.5 and 3.7)"*. The team followed the contract. Model selection was constrained by Meridian Networks's requirement for EU-hosted AWS Bedrock - newer models were not available in the approved region at development time. The team proposed Sonnet 4 but it was not approved. Upgrading the model is a configuration change, not a rebuild - the extraction pipeline is model-agnostic.

**Response**: Do not defend 3.7. Position it as the starting point, not the endpoint. "The system was built and validated on the contractually specified models. It is designed for model-agnostic operation - upgrading to Claude 4 is a configuration change that will directly improve Class A metrics." Frame the upgrade as upside, not the current state as a problem. Never say "we were told to use 3.7" - that is finger-pointing.

## 18. "Why did you agree to the ABC metrics if it was mathematically impossible?"

**Likelihood: 4** | **Impact: 5** | **Risk: 20**

**Their take**: You knew Class A at 90% was unrealistic with 30-field emails. You signed the SOW anyway. Either you did not understand your own system, or you agreed to something you knew you could not deliver. Both are bad.

**Reality**: This was discussed before the project started. The team raised the mathematical challenge of composite metrics on multi-field emails during SOW negotiations. The customer understood the concern but chose to keep Class A at 90% as an aspirational target. The reduced-metrics clause was added to the SOW specifically to accommodate this - it is not a generic escape clause, it was drafted in response to the team's pre-project analysis. Both parties entered the contract with eyes open: an ambitious target with a contractual mechanism for the expected shortfall.

**Response**: Do not frame this as "we told you so." The reduced-metrics clause is the response. "We raised this during SOW discussions. The 90% Class A target was set as an aspirational goal. The contract includes the reduced-metrics provision specifically for this scenario - it was agreed before work began, not invoked after the fact." The key message: the clause exists because both parties anticipated this outcome. It is not a loophole - it is the plan working as designed.

## 19. Overcomplicated language

**Likelihood: 5** | **Impact: 4** | **Risk: 20**

**Their take**: The executive does not consciously notice overcomplicated language. They just feel the document is hard to read and lose patience. They never say "your syntax is too complex" - they say "I stopped reading" or "just tell me the answer."

**Reality**: Every subordinate clause, every passive construction, every prepositional chain adds cognitive load. The executive processes simple sentences automatically but has to re-read complex ones. Re-reading breaks trust. Examples of the problem:

| Overcomplicated | Simple |
|----------------|--------|
| "This was anticipated before the project - the 90% Class A target was set as aspirational, and the following clause was agreed specifically to accommodate the expected shortfall" | "Both sides knew this. The contract includes a clause for it" |
| "The system is designed for model-agnostic operation - upgrading to Claude 4 is a configuration change" | "Upgrading to Claude 4 is a config change" |
| "Reduced metric values would be potentially allowed given approval from the customer" | (this is a quote - leave as-is) |
| "The evaluation team has completed this review" | "Review complete" |

**Response**: After every draft, run a simplicity pass. For each sentence ask: can a 12-year-old understand this on first read? If not, rewrite. Prefer subject-verb-object. One idea per sentence. No dashes, no semicolons, no "specifically", no "in order to", no "given that."

## 20. "Why is Class A missing from the SOW compliance table?"

**Likelihood: 4** | **Impact: 5** | **Risk: 20**

**Their take**: The SOW specifies three targets. Your compliance table shows two. The missing one is the one you failed. That looks like you are hiding the bad number. If I notice this, I stop trusting the rest of the document.

**Reality**: Class A (>= 90%, result 55%) was deliberately moved to prose below the table to avoid a stark "Not met" row that dominates executive attention before context is provided. The table shows the two safety metrics. The text immediately below states "Class A is at 55%" and explains why.

**Response**: Include Class A in the table. Hiding it is worse than showing it. The executive will notice the omission and lose trust. Show all three metrics, let Class A row say 55%, and let the prose below explain the gap. Transparency beats framing.

## 21. "You should have driven the use of the best model - why didn't you push for Claude 4?"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: You are a specialist AI vendor. We hired you for your expertise. If you knew Claude 4 would deliver better results, it was your professional responsibility to make the case and drive the decision. Saying "we proposed it but it was not approved" sounds like you mentioned it in passing and gave up. A vendor I trust would have escalated, documented the impact, and made sure I understood what I was leaving on the table. You did not fight hard enough for the right outcome. That is on you.

**Reality**: The team proposed Claude 4 during the project. The customer did not approve it. The SOW specifies Claude 3.5 and 3.7 as primary models. The upgrade clause ("other models can be discussed during the project at the agreed running cost") was available but the customer chose not to exercise it. The cost is the same - this was not a budget issue. The team continued with the contractually specified models and delivered within those constraints. However - the executive has a point: the vendor should have made the business impact explicit ("Claude 4 will move Class A from 55% toward the 90% target") rather than just proposing a model swap.

**Response**: Do not say "we proposed it and you said no" - that is blame. Do not say "we should have pushed harder" - that is weakness. State the forward-looking fact: "Claude 4 is available at the same cost. Based on our testing, it will improve Class A. We recommend upgrading as the first production enhancement." This positions the vendor as still driving the right outcome without relitigating the past. In the executive summary, the model line should answer both "why 3.7" and "what next" in one breath.
