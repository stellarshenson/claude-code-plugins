# Fact Repository - Article 01b Editorial Tightening

Verified claims sourced from the article, codebase, and editorial critique.
No interpretation - just facts.

## Article metrics
- Word count (body, excluding frontmatter/code/images): ~1639
- SVG count: 11 (01-08, 09, 10, 11 + cover + ds-project-structure orphan)
- "External enforcement" synonym count: 5+ variants across article
- "Separate process" synonym count: 1 (after prior iteration reduced from 13)
- Session transcripts: 2 (skip-denial, forensicist F1)
- Academic citations: 5 inline [1]-[5]
- Source: article_01b word count analysis, grep of article text

## Editorial critique facts
- Overall assessment: 7.5/10 current, 9/10 achievable with cuts
- Strongest sections: five failure modes, pull vs push, independent gates, guardian
- Weakest aspects: over-explanation, implementation too early, assumes reader patience
- Core structural problem: article does 3 things at once (failure mode, design pattern, implementation docs)
- "External enforcement" said in 5 different ways
- Opening diagnosed as "telling about failure" not "showing failure"
- Closing diagnosed as "polite, asking permission" not "doctrine"
- Source: user-provided editorial critique

## Codebase facts
- Package: stellars-claude-code-plugins v0.8.47
- YAML resource files: 3 (workflow.yaml, phases.yaml, app.yaml)
- Workflow types: 5 (WORKFLOW::FULL, PLANNING, GC, HOTFIX, FAST)
- Full workflow phases: 8 (RESEARCH, HYPOTHESIS, PLAN, IMPLEMENT, TEST, REVIEW, RECORD, NEXT)
- Total agents in full workflow: 15
- FSM package: transitions (Python)
- FSM states: pending, readback, in_progress, gatekeeper, complete (+ skipped, rejected)
- Gate types: readback (entry), gatekeeper (exit)
- Gate execution: claude -p subprocess with CLAUDECODE env stripped
- Gate latency: ~30s per gate
- Source: stellars_claude_code_plugins/engine/ codebase

## Academic citations
- [1] Liu et al. "Lost in the Middle" (2023) - attention dilution in long contexts
- [2] Han et al. "LLM Multi-Agent Systems" (2024) - role specialization outperforms monolithic
- [3] Deng et al. "Rephrase and Respond" (2023) - rephrasing improves accuracy
- [4] Ye et al. "Justice or Prejudice?" (2024) - 12 biases in self-evaluation
- [5] Madaan et al. "Self-Refine" (NeurIPS 2023) - ~20% improvement via generate-feedback-refine
- Source: references/ folder, arxiv downloads

## Real session transcripts
- Transcript 1 (skip-denial): agent tried to force-skip HYPOTHESIS, gatekeeper denied with "provides independent creative direction; prior research does not substitute"
- Transcript 2 (forensicist F1): 4 agents reviewed, critic approved, forensicist found _clean_artifacts_dir destroys project-local resources on new --clean. Rejected back to IMPLEMENT.
- Source: actual orchestrator sessions during iterations 9-11
