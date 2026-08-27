**Same Task, More Tokens: the Impact of Input Length on the Reasoning Performance of Large Language
Models (2024)**

An experiment isolating input length as a variable while holding the reasoning task completely
fixed. Earlier long-context benchmarks changed both the length and the task, so degradation could
not be attributed to either. This work builds FLenQA, a dataset in which each sample is a
true/false question answerable only by combining two specific text spans, and then produces
multiple versions of that same sample padded to different lengths, with padding of different types
and the spans in different positions. Because the reasoning required never changes, any accuracy
difference across versions is attributable to length. Models degrade sharply and early - well below
their advertised maximum context. The paper also shows that next-word-prediction quality on long
inputs does not predict reasoning quality on long inputs, and that chain-of-thought prompting does
not rescue the loss. Published at ACL 2024.

**Key mechanism**
- Each FLenQA sample requires two distinct spans reasoned over jointly, deliberately excluding
  divide-and-conquer tasks such as summarisation that can be solved span by span
- The same sample is emitted at several lengths by embedding the two spans in padding, so the task
  is constant and only length varies
- Padding is varied by type - text similar to the relevant spans, and text dissimilar to them - to
  test whether interference or mere volume drives the effect
- Span position within the padded input is controllable, letting position and length be separated
- Facts are novel rather than drawn from existing datasets, to keep models from answering from
  parametric knowledge instead of reasoning over the supplied text
- Both plain and chain-of-thought prompting are run at every length, so the mitigation is measured
  rather than assumed

**Main findings**
- Mean accuracy across tested models falls from 0.92 to 0.68 as input grows to 3000 tokens, far
  short of any tested model's technical limit
- Degradation appears in every version of the dataset - every padding type, every span location -
  differing in intensity but not in direction
- The effect holds across GPT-4, GPT-3.5, Gemini Pro, Mistral Medium and Mixtral 8x7B, so it is not
  a property of one vendor or one training recipe
- Next-word prediction performance on long inputs correlates negatively with reasoning performance
  on them, so perplexity-style metrics are the wrong instrument for this failure
- Chain-of-thought raises accuracy at every length but by a roughly constant amount, leaving the
  length-driven drop essentially intact; GPT-4 is the single exception, where the CoT advantage
  widens with length
- Failure modes are behavioural, not merely numeric: with longer inputs models increasingly fail to
  follow explicit instructions, sometimes returning no answer at all
- Under CoT prompting at length, models begin stating the final answer before the reasoning steps,
  inverting the ordering the prompt requested
- A bias toward answering "false" grows with input length, alongside a declining ability to
  incorporate the relevant spans into the response
- Each reported point aggregates 600 samples

**Key takeaways**
- Input length is an independent degradation axis, separate from task difficulty and separate from
  where in the input the evidence sits
- The usable working length is far below the advertised context window; 3000 tokens already costs
  roughly a quarter of the accuracy in this setup
- Do not use perplexity or next-word metrics to certify long-context competence - this paper finds
  the correlation runs the wrong way
- Chain-of-thought is not a remedy for length; budget for it as a constant gain, not a mitigation
- Instruction-following decays with length, which matters for any pipeline whose correctness depends
  on the model honouring an output contract
- Keeping supplied material short is a measurable accuracy intervention, not a stylistic preference
- FLenQA is synthetic and binary-answer, and padding is artificial, so the magnitudes are specific
  to this construction even though the direction is consistent

**Relevance**
- Grounds two claims at once: that the tracker document should not be handed over whole, and that
  entries themselves should be short
- Careful reading needed on the second - the paper measures the cost of *more* input, not the
  benefit of *terser* input, so it supports keeping entries brief without evidencing that a dry
  register beats a discursive one at equal length

**Tags**
- #long-context
- #reasoning
- #llm-evaluation

**Source**
- https://aclanthology.org/2024.acl-long.818/
