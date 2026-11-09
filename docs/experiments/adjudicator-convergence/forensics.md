# Adjudicator convergence - fix-induced findings forensics v1

## 1. Summary

The campaign produced 34 distinct findings: 30 from statistics review rounds 15-27 and 4 from grid review rounds 3-4. 33 of the 34 were introduced by an earlier patch in the same campaign. The only exception is the tile-typography decision, which predates the campaign (`01-inventory.json` totals; item 10 carries `introducedByPatch: none`). Outcomes: 26 fixed, 1 deferred, 5 refuted, 2 rejected (`01-inventory.json` items).

Five of the six root-cause classes are spirals, meaning a fix produced the next finding. The 75vh-cap class is not a spiral: four of its five items are independent consequences of patch 33, and item 6 is the test-coverage guard for patch 42 (`01-inventory.json` classes).

| Class | Findings | Spiral | Change that would have stopped it | Round stopped |
|---|---:|---|---|---:|
| 75vh cap: statistics-column overflow and keyboard reach | 5 | no | Extend `appliedFixes` with a `barGuarantee` field, so a fix that changes a bar clause replaces the clause in the same invocation | 15 |
| Box plot geometry | 3 | yes | Extend `newMechanism` to any rule that hides, clips or makes content unreachable, so a clip is priced as new review surface | 15 |
| Fixed-width tile typography | 5 | yes | Make each deferred entry carry a blocking `ownerDecision` that names the open design question | 17 |
| Tile accessibility and copy | 11 | yes | Add `fixVerdicts`, one keep, revert or refine verdict with a reason per closure | 19 |
| Regex browser compatibility and lint selector scope | 6 | yes | Judge the trajectory over all applied changes, persist the reason, and let the existing two-of-three window count a round with a non-empty applied delta | 26 |
| Header strip scroll sync and wheel forwarding | 4 | yes | Add `graphGap`, naming the layer the AST graph did not cover for the adjudicated findings | grid 3 |

The shipped adjudicator ran. The agent type `devils-advocate:adjudicator` was spawned on all 24 finding-bearing rounds (`review.js:515`; `02-audit.json` .adjudication.personaInvoked), and it ordered 8 reverts in 5 rulings (`state-r27.json` .rulings). It did not stop the campaign for two recorded reasons. From round 16 the owner applied fixes after clean rulings, so those changes were never adjudicated (`state-r27.json` .rulings; `02-audit.json` .adjudication.campaignLocalPlanning). The trajectory judgment was tied to the adjudicator's own plan, which was empty in rounds 16, 18-22 and 24-27, so `FANOUT_STOP` could not count a spiralling round (`review.js:543`; `adversarial-loop.js:546-547`).

## 2. The campaign record

The campaign ran in `/home/lab/workspace/private/jupyterlab/jupyterlab_tabular_data_viewer_extension/tmp/workflows/column-stats`. The checkpoint files `01-inventory.json`, `02-audit.json` and `03-mechanisms.json` live in `/home/lab/workspace/private/ai-assistants/claude-code-plugins/tmp/workflows/fix-induced-findings`. Patch numbers name files under `tmp/workflows/column-stats/patches/`; patches 33-59 are present and were read. Defect ids name entries in `docs/defects.md`.

| Measure | Value | Source |
|---|---|---|
| Statistics rounds | 1-28 | `state-r28.json` |
| Grid rounds | 1-5 | `state-grid-r5.json` |
| Finding-bearing rounds in scope | statistics 15-27 (30 findings), grid 3-4 (4 findings) | `01-inventory.json` |
| Statistics adjudications | 24, rounds 1-6, 8-13, 15-22, 24-27 | `state-r27.json` .rulings |
| Clean rulings | 11, rounds 3, 16, 18-22, 24-27 | `state-r27.json` .rulings |
| PLAN rulings | 13 | `state-r27.json` .rulings |
| Changes planned | 18 | `state-r27.json` .rulings |
| Reverts ordered | 8, rounds 2, 4, 12, 13, 17 | `state-r27.json` .rulings |
| Closures at finish | 49 statistics, 8 grid | `state-r28.json`, `state-grid-r5.json` |
| Deferred and refuted at finish | 26 deferred, 36 refuted | `state-r27.json` |
| Final status | statistics SHIP at round 28 with 0 findings; grid round 5 shipped | `state-r28.json`, `state-grid-r5.json` |

The statistics rounds 7, 14 and 23 had zero findings and skipped adjudication (`state-r27.json` .history, rounds 7, 14 and 23). Grid round 5 had zero findings and shipped (`state-grid-r5.json` .shipped).

### 2.1 75vh cap

The class is not a spiral. Patch 33 gave the statistics column `overflow-y: auto` under the owner's 75vh dialog cap, and items 0-3 are independent consequences of that one change; item 6 is the test-coverage guard for patch 42 (`01-inventory.json` class 1).

| # | Round | Finding | Introduced by | Fix | Defect | Recorded ruling |
|---:|---|---|---|---|---|---|
| 0 | 15 | Statistics column gains a horizontal scrollbar from the box plot's 2 px max-edge overhang | patch 33 | patch 42 | - | `PROCEED_WITH_DEFERRALS` (round 15), plan item 1; patch 42, confirmed at round 16 SHIP (`state-r27.json`) |
| 1 | 15 | Short-viewport comment still says only the values pane scrolls | patch 33 | patch 43 | - | `PROCEED_WITH_DEFERRALS` (round 15), plan item 2; patch 43 (`state-r27.json`) |
| 2 | 15 | Stacked narrow layout shrinks the statistics column to a 77-101 px scroll strip | patch 33 | none | DEF-STATS-52-NARROW-STRIP | deferred as `deferred[23]` (`state-r27.json`); owner rejected 2026-11-06 (`docs/defects.md:388`) |
| 3 | 15 | Statistics column that overflows the 75vh cap cannot be scrolled from the keyboard | patch 33 | none | - | refuted as immaterial (`state-r15.json` refuted; `state-r27.json` refuted entry quoting `src/modal.ts:54`) |
| 6 | 16 | No test fails if the statistics column again scrolls sideways | patch 42 | patch 47 | - | `PROCEED` (round 16); test guard patch 47 (`state-r27.json`) |

The class has two loop-supplied fixes, patches 42 and 43 (`01-inventory.json` items 0 and 1; `state-r27.json` .closures round 15); only patch 42 became the cause of later findings, producing items 4 and 5 in classes 2 and 3 (`01-inventory.json` items 4 and 5; `03-mechanisms.json` class 1).

### 2.2 Box plot geometry

The class is a spiral. Patch 42's `overflow-x: hidden` turned the content-box overhang into `DEF-STATS-50`, and patch 45's `box-sizing` plus clamp produced two round-17 residue findings, both refuted (`01-inventory.json` class 2).

| # | Round | Finding | Introduced by | Fix | Defect | Recorded ruling |
|---:|---|---|---|---|---|---|
| 4 | 16 | Box plot right edge clipped when Q3 or the median equals the max | patch 42 | patch 45 | DEF-STATS-50-BOX-CLIP | `PROCEED` (round 16); owner-chosen cause fix patch 45; closed (`state-r27.json` closures round 16) |
| 8 | 17 | Box plot clamp repeats the 2 px line width as a TypeScript literal | patch 45 | none | - | refuted as immaterial (`state-r27.json` refuted entry at `src/modal.ts:755,759`) |
| 9 | 17 | Box plot residue: a box narrower than 2 px at the max end is fully or partly clipped | patch 45 | none | - | refuted as immaterial (`state-r27.json`; `80-ponytail-stats-delta.json` finding 1) |

The class ended when patch 45 removed the overhang at its cause instead of clipping it (`01-inventory.json` class 2).

### 2.3 Fixed-width tile typography

The class is a spiral. Patch 42's clip created `DEF-STATS-51`; patch 46's wrap created `DEF-STATS-53`; patch 50's 16 px font shrank the break; patch 51's `<wbr>` split moved it to a group separator (`01-inventory.json` class 3). The statistics defect chain is `DEF-STATS-51` → `DEF-STATS-53` → {`DEF-STATS-54` → `DEF-STATS-55`, `DEF-STATS-56`} (`01-inventory.json` summary).

| # | Round | Finding | Introduced by | Fix | Defect | Recorded ruling |
|---:|---|---|---|---|---|---|
| 5 | 16 | Rightmost summary tile count clipped at the column edge and no longer scrollable | patch 42 | patch 46 | DEF-STATS-51-TILE-CLIP | `PROCEED` (round 16); patch 46; closed (`docs/defects.md:375-381`) |
| 7 | 17 | Total-rows and Non-null counts break inside a digit group in the 980 px split dialog | patch 46 | patch 50 | DEF-STATS-53-TILE-BREAK | round-17 plan proposed reverting patch 46; owner rejected the revert and chose patch 50 (`review-final3-result.json` results[0].reverts[0]) |
| 10 | 17 | Tile count typography does not fit the fixed-width tile at the approved design size | none, predates the campaign | none | - | deferred as `deferred[24]` (`state-r27.json`) |
| 11 | 18 | An 8-digit count still breaks inside a digit group when the statistics column shows a classic scrollbar | patch 46; patch 50 left the scrollbar case | patch 51 | DEF-STATS-53-TILE-BREAK | refuted as immaterial (`state-r27.json` refuted); owner chose patch 51; closed (`state-r28.json`) |
| 12 | 18 | The digit-group break returns in the split dialog in windows 721-1011 px wide | patch 46, aggravated by patch 50 | patch 51 | DEF-STATS-53-TILE-BREAK | deferred as `deferred[25]` (`state-r27.json`); owner chose patch 51; closed (`state-r28.json`) |

### 2.4 Tile accessibility and copy

The class is a spiral. Patch 51's `<wbr>` split made one `StaticText` leaf per segment (`DEF-STATS-54`); patch 52's screen-reader copy fixed speech but stayed selectable, so a tile selection copied the count twice (`DEF-STATS-55`); patch 53's `user-select` then needed the Safari prefix (`patch 55`) (`01-inventory.json` class 4).

| # | Round | Finding | Introduced by | Fix | Defect | Recorded ruling |
|---:|---|---|---|---|---|---|
| 13 | 19 | Each tile count is now three accessible text nodes instead of one | patch 51 | patch 52 | DEF-STATS-54-TILE-SPEECH | refuted as immaterial and UNPROVEN; owner chose patch 52; closed (`docs/defects.md:398-405`) |
| 14 | 19 | The `<wbr>` split exposes a tile count to assistive technology as three separate text leaves | patch 51 | patch 52 | DEF-STATS-54-TILE-SPEECH | refuted as immaterial and UNPROVEN; one root cause with item 13 (`state-r27.json`) |
| 15 | 20 | Selecting a whole tile copies the count twice | patch 52 | patch 53 | DEF-STATS-55-TILE-COPY | refuted as immaterial, all four lenses `material=false`; owner chose patch 53 (`state-r27.json` refuted) |
| 16 | 20 | Copying across a tile now pastes the count twice | patch 52 | patch 53 | DEF-STATS-55-TILE-COPY | refuted as immaterial (`state-r27.json` refuted) |
| 17 | 20 | Copying a summary tile now puts the count on the clipboard twice | patch 52 | patch 53 | DEF-STATS-55-TILE-COPY | refuted as immaterial (`state-r27.json` refuted) |
| 18 | 20 | Selecting and copying a tile copies its count twice | patch 52 | patch 53 | DEF-STATS-55-TILE-COPY | refuted as immaterial (`state-r27.json` refuted) |
| 19 | 20 | No test fails when the screen-reader copy becomes visible | patch 52 | patch 54 | - | refuted as test coverage, not product behaviour; owner chose patch 54 (`state-r27.json`) |
| 20 | 21 | Copying a summary tile now pastes its count twice | patch 52 | patch 53 | DEF-STATS-55-TILE-COPY | round-20 refutation upheld; owner chose patch 53; closed (`state-r27.json` refuted) |
| 21 | 21 | Copying a tile by mouse selection pastes its count twice | patch 52 | patch 53 | DEF-STATS-55-TILE-COPY | refuted as immaterial; owner chose patch 53 (`state-r27.json`) |
| 22 | 22 | The copy-once rule has no `-webkit-` prefix, so Safari still copies the tile count twice | patch 53 | patch 55 | DEF-STATS-55-TILE-COPY | refuted as immaterial, Safari outside the bar; owner chose patch 55 (`state-r27.json`) |
| 23 | 22 | Safari ignores the unprefixed `user-select`, so a copied tile still holds the count twice | patch 53 | patch 55 | DEF-STATS-55-TILE-COPY | refuted as immaterial; owner chose patch 55 (`state-r28.json` closures round 22) |

### 2.5 Regex compatibility and lint selectors

The class is a spiral in the guard layer. Patch 51's lookbehind broke Safari 16.3 (`DEF-STATS-56`); patch 56 replaced it without a guard; patch 57's literal-only rule produced the string-built finding and one rejected false-positive finding; patch 58's `NewExpression`-only selector produced two round-27 gaps, closed by patch 59 (`01-inventory.json` class 5).

| # | Round | Finding | Introduced by | Fix | Defect | Recorded ruling |
|---:|---|---|---|---|---|---|
| 24 | 24 | The `<wbr>` split uses a regex lookbehind, so the extension chunk fails to parse on Safari 16.3 and older | patch 51 | patch 56 | DEF-STATS-56-LOOKBEHIND | refuted as immaterial, Safari 16.3 outside the bar; owner chose patch 56; closed (`docs/defects.md:415-422`) |
| 25 | 25 | No check fails when a regex lookbehind returns to `src/` | patch 51; patch 56 removed it without a guard | patch 57 | - | refuted as immaterial test tooling; owner chose patch 57 (`state-r27.json` refuted) |
| 26 | 26 | A lookbehind built from a string passes the new lint rule | patch 57 | patch 58 | - | refuted as immaterial; owner chose patch 58 (`state-r27.json` refuted) |
| 27 | 26 | The rule rejects two regex literals that hold no lookbehind | patch 57 | none | - | refuted as immaterial; owner rejected the remedy, outcome REJECTED (`state-r28.json` closures round 26) |
| 28 | 27 | Lookbehind guard misses `RegExp(...)` without `new`, and non-literal patterns | patch 58 | patch 59 | - | refuted as immaterial and out of bar (`state-r27.json`); owner chose patch 59 (`state-r28.json`) |
| 29 | 27 | The string selector misses `RegExp()` without `new`, a template literal and a concatenated pattern | patch 58 | patch 59 | - | refuted as immaterial; owner chose patch 59; round 28 SHIP with 0 findings (`state-r28.json`) |

A pattern held in a variable or passed to `String.prototype.match` still passes the guard after patch 59 (`01-inventory.json` item 28).

### 2.6 Header strip scroll and wheel

The class is a spiral. The `DEF-GRID-46` header-strip rebuild and its follow-ups each created the next finding: patch 39's handle-overhang fix covered the last column's sort arrow (`DEF-GRID-47`), patch 41's wheel guard added two refuted findings, and patch 44's block (g) clicked the arrow centre (`01-inventory.json` class 6).

| # | Round | Finding | Introduced by | Fix | Defect | Recorded ruling |
|---:|---|---|---|---|---|---|
| 30 | grid 3 | The last column's resize handle now covers its sort arrow, so a click on the arrow no longer sorts | patch 39 | patch 44 | - | grid round-3 ruling `PROCEED`, 1 change, `spiralling` (`state-grid-r3.json` .rulings); patch 44 plus block (g) (`state-grid-r4.json` closures) |
| 31 | grid 3 | The header wheel guard lets only Ctrl through, so Firefox macOS Cmd+wheel zoom is cancelled over the header | patch 41 | none | - | refuted as immaterial (`state-grid-r3.json` refuted; `src/widget.ts:265-271`) |
| 32 | grid 3 | Shift+wheel over the header scrolls the grid vertically in Firefox on Windows and Linux | patch 41 | none | - | refuted as UNPROVEN and immaterial (`state-grid-r3.json` refuted; `src/widget.ts:275`) |
| 33 | grid 4 | Block (g) clicks the arrow centre, so a handle up to 13 px wide still passes while it covers part of the arrow | patch 44 | patch 48 | - | refuted as an immaterial coverage gap (`state-grid-r4.json` .refuted); owner applied patch 48 (`state-grid-r5.json` closures) |

The grid chain in `docs/defects.md` is the header-strip rebuild → `DEF-GRID-47` handle overhang → the round-3 sort-arrow finding → patch 44 → the round-4 block (g) finding → patch 48 (`01-inventory.json` summary). `DEF-GRID-48` and `DEF-GRID-49` are independent of that sequence (`docs/defects.md:444-451`).

## 3. Why the graph did not prevent it

The campaign passed `graphify-out/graph.json` on every invocation (`review-args-r7-base.json:11`, cited in `03-mechanisms.json`). The instrument is AST-only, and its coverage stops at the symbol layer.

| What the graph holds | Value | Source |
|---|---|---|
| Nodes | 1031, built from commit `e089aa11` | `GRAPH_REPORT.md` Summary and Graph Freshness; `03-mechanisms.json` |
| Nodes sourced from `style/base.css` | 0 | read-only count over `graph.json` |
| Nodes for lint rules or selectors | 0; one file-level node `eslint_config` at `eslint.config.mjs:1` | read-only count over `graph.json` |
| Nodes per test body | 0; one spec file node plus helper callables | `03-mechanisms.json` graphCoverage |
| Accessibility tree, browser parse matrix, rendered layout, scroll geometry | absent | `03-mechanisms.json` graphCoverage |
| Modal-to-widget call edge | absent | `root-cause-analysis/02-graph.json` notes; `03-mechanisms.json` |

The graph does hold the symbols the campaign argued about. `._tile()` at `src/modal.ts:181` is reached from `._renderTiles()` at line 144, `._render()` at line 55, `.constructor()` at line 25, and `TabularDataViewer._showColumnStats()` at `src/widget.ts:1308`. `._boxPlot()` at `src/modal.ts:742` is reached from `._appendNumericPanel()` at line 441, `._renderPanel()` at line 260 and `._render()` at line 56 (`03-mechanisms.json` graphCoverage). Those edges answer which function renders the element and which function calls it.

The graph cannot answer the question each class turned on:

- CSS layout (classes 1, 2, 3 and the CSS half of 6). The rule that styles the element has no node. `overflow-x: hidden` (patch 42), `box-sizing` and `clamp` (patch 45), `overflow-wrap: anywhere` (patch 46), the 16 px font (patch 50), the `<wbr>` split (patch 51) and the last-child handle width (patch 39) are invisible to the graph
- Lint config (class 5). The graph holds `eslint.config.mjs` as one file node. It cannot show a selector's scope, so a regex literal (patch 57), `new RegExp(<literal>)` (patch 58) and `:matches(NewExpression, CallExpression)` (patch 59) are one undifferentiated file
- Accessibility (class 4). The number of `StaticText` leaves per text node and the selectability of `.jp-sr-only` are properties of the accessibility tree. The graph has no such layer, so `DEF-STATS-54` and `DEF-STATS-55` have no instrument here
- Browser compatibility (classes 4 and 5). The graph holds no parse target and no browser matrix. The Safari 16.3 lookbehind failure (`DEF-STATS-56`) and the `-webkit-user-select` requirement (`DEF-STATS-55`) are absent
- Test coverage (class 1 item 6, class 6 item 33). There is no node per test. Block (g)'s click coordinate (patch 48) has no symbol

`adjudicator.md:17` says never let a tool's silence pass as evidence, and `adjudicator.md:22` requires the radius source to be named. The campaign gave the adjudicator one named instrument, the AST graph. No ruling records a graph-gap line (`review.js:175` ADJUDICATION_SCHEMA carries no `graphGap` field). The graph answers "which symbol calls this" and "where else is the cause live at the symbol layer". It cannot answer what a CSS rule, a test click or an accessibility tree does. Whether the gap changed any individual ruling is UNKNOWN.

## 4. Why the adjudicator did not stop it

Two layers need separating. The shipped adjudicator contract is located in `plugins/devils-advocate`. The campaign wrapped it in `review-final*.js` workflows that applied an owner-chosen fix before each confirm invocation.

### 4.1 The shipped adjudicator ran

- The shipped agent type `devils-advocate:adjudicator` was spawned on all 24 finding-bearing statistics rounds (`review.js:515`; `02-audit.json` .adjudication.personaInvoked)
- Rounds 7, 14, 23 and 28 had zero findings and skipped adjudication (`state-r27.json` .history; `state-r28.json` round-28 history entry with 0 findings)
- The exact plugin build resolved at run time is UNKNOWN (`02-audit.json` .adjudication.personaInvoked)
- The adjudicator received the closure list as the appliedFixes equivalent (`review.js:508-509`; 48 closures in `state-r27.json` .closures)
- Proof of use: the round-17 revert names "round 16 style/base.css .jp-ColumnStatsModal-tileValue" (`review-final3-result.json` results[0].reverts[0])

### 4.2 Which invariants held

The audit checked all nine invariants against the campaign script and its recorded runs (`02-audit.json` .invariants).

| Invariant | Held | What the record shows |
|---|---|---|
| INV-1: a bar naming purpose, inputs and primary path | yes | `review.js:83-88` throws without target, bar and lenses; the bar requires purpose, inputs and primaryPath; `review-args-r7-base.json` holds the bar |
| INV-2: the adjudicator rules what blocks, severities are evidence, an empty plan is clean | partial | severity tally is reporting only (`review.js:230-232`); an empty change set falls through to SHIP (`review.js:575-580`); the adjudicator returned 11 clean rulings, and the main session applied owner fixes after every one |
| INV-3: every finding-bearing round is adjudicated, a non-empty plan exits | partial | all 24 finding-bearing rounds were adjudicated and 13 returned PLAN; from round 16 the fixes came from `FIX_BASE` and were applied before the review ran, so they were never an adjudicated plan |
| INV-4: confirms are pinned to closures and the applied delta, with filters | yes | `review.js:410-421` confirm body; `review.js:434-452` pin filter; `review.js:454-466` settled filter; no filter drop is recorded (`state-r27.json` .history has 27 entries, all discover or confirm) |
| INV-5: the exit set | yes | `review.js:469-471`, 493-494, 517-518, 534-535, 543-550, 586-597; SHIP at every round with an empty change set, including the zero-finding rounds 7, 14, 23 and 28; `shipped: true` is recorded at 7, 14, 16, 18, 19, 21, 22 and 24-28; `FANOUT_STOP` never fired; `ROUND_CAP` never fired because maxRounds was raised from 7 to 28 |
| INV-6: the workflow never edits the tree | partial | `review.js` spawns only the reviewer and adjudicator and never writes; the wrapper's Apply phase and `apply-*.js` edit the repository through agents |
| INV-7: full history and research routing on every return | yes | every return carries history, closures, deferred, refuted and research; `state-r27.json` holds 27 history entries, 48 closures, 26 deferred and 36 refuted |
| INV-8: materiality before severity | yes | `review.js:237-247` caps `material=false` at MINOR/out-of-bar before adjudication; the adjudicator prompt states the cap (`review.js:506`); every round tally is `CRITICAL:0`; refuted entries carry the capped ruling |
| INV-9: revert before refine, with newMechanism and reverts returned | partial | 8 reverts were ordered in rounds 2, 4, 12, 13 and 17; the round-17 revert of patch 46 was rejected by the owner; rounds 18-27 ordered no reverts while 33 of 34 findings were fix-induced; owner fixes entered as `appliedFixes` and were never priced for `newMechanism` |

### 4.3 Per class

**75vh cap.** No stop was due in the loop's terms because the class is not a spiral. The bar kept the guarantee "the unique values pane is the only scroll region" after patch 33; `make-review-final9.py:31-35` records the clause as stale since the owner's 75vh cap and replaces it at round 25. The keyboard finding was refuted as immaterial against a contract the code had already contradicted (`state-r15.json` refuted; `state-r27.json` refuted entry quoting `src/modal.ts:54`), the strip was deferred (`state-r27.json` deferred[23]) and then rejected by the owner (`docs/defects.md:388`), and the comment was corrected by patch 43. Whether the stale clause changed any individual ruling is UNKNOWN (`03-mechanisms.json` class 1).

**Box plot geometry.** The adjudicator planned the clip that created the class. Round 15 ruled `PROCEED_WITH_DEFERRALS` with 2 changes (`state-r27.json` .rulings), and round 15 has two closures, patches 42 and 43; closure r15 is patch 42 `overflow: hidden auto`. `newMechanism` is a closed list at `adversarial-loop.js:190`, identical in the campaign copy: "a pass, plugin, branch, helper, guard, data shape, or a special case for one input". A CSS overflow or clip rule is none of these, so the clip was not priced as new review surface. `DEF-STATS-50` is the next round's finding. The class ended when the owner chose patch 45 at round 16 after a clean `PROCEED` with 0 changes and 0 reverts (`state-r27.json` .rulings; closure r16).

**Fixed-width tile typography.** The adjudicator had the correct ruling at round 17 and the owner overrode it. `review-final3-result.json` results[0].reverts[0] proposes reverting patch 46 because it broke digit groups, and states that this reverses a round-16 owner choice. The owner rejected the revert and chose patch 50 (`state-r27.json` closure r17). The open typography decision is recorded as `deferred[24]`, a bare string with no decision reference and no blocking force. `deferred[25]` calls the `<wbr>` split "a new mechanism for a MINOR finding" and "the third rule on a site where two rounds of findings conflict", and the owner applied patch 51 anyway (`state-r27.json` deferred[25]). The shipped contract already says two rounds of conflicting findings on one loop-introduced site are a revert (`adjudicator.md:23`). The campaign refined instead.

**Tile accessibility and copy.** Every item is MINOR and `material=false`, and the adjudicator refuted each (`state-r27.json` refuted entries at `src/modal.ts:192`, `201`, `211`; `90-ponytail-tile-speech.json` has two findings and `93-ponytail-tile-copy.json` one, all `material=false`, and `96-ponytail-tile-webkit.json` records no findings). The owner applied patches 52-55 after those refutations. The loop carries applied fixes as revert candidates (`review.js:508-509`) but requires no verdict on one. The adjudicator can rule a round clean, and the next round sees only the resulting finding. No ruling records a keep or revert decision on patches 52, 53 or 55 (`state-r27.json` .rulings; `03-mechanisms.json` class 4).

**Regex compatibility and lint selectors.** The trajectory judgment had no input from the applied delta. Rounds 16-27 are all `converging` with 0 changes; rounds 18-27 ordered no reverts, while round 17 ordered 1 revert (`state-r27.json` .rulings). `FANOUT_STOP` requires two of the last three rulings judged `spiralling` with changes or reverts greater than 0 (`review.js:543`; `adversarial-loop.js:546-547`). An empty plan cannot meet that condition. The `trajectory` definition ties spiralling to a plan that "enlarges or refines" a loop-introduced mechanism (`review.js:214`; `adversarial-loop.js:212`), so a round with no plan scores converging even when every finding sits in an owner-applied fix. The reason text is passed only to `log()` (`review.js:530`; shipped `adversarial-loop.js:533`), and `rulings.push` persists the enum only (`review.js:529`; shipped `adversarial-loop.js:532`). The reasons for rounds 16-27 are therefore UNKNOWN.

**Header strip scroll and wheel.** Grid round 3 is the grid chain's one recorded `spiralling` ruling: `PROCEED`, 1 change (`state-grid-r3.json` .rulings). The change was patch 44. The round-4 finding that block (g) clicks the arrow centre was refuted as an immaterial coverage gap (`state-grid-r4.json` .refuted), and the owner applied patch 48 anyway (`state-grid-r5.json` closures). The graph gap is proven: 0 CSS nodes and no per-test nodes. Whether it changed the round-3 or round-4 ruling is UNKNOWN (`03-mechanisms.json` class 6).

### 4.4 Campaign-local planning versus the shipped contract

`review.js` is a near-verbatim copy of the shipped `adversarial-loop.js`, with `INV` annotations added; it declares `LOOP_CONTRACT` 4 and `meta.name` `review-column-stats-dialog`; the shipped file was not the script that ran (`02-audit.json` .loop). The `review-final*.js` wrappers run Apply → Verify → Ponytail → Review, and the fix text is authored in `make-review-final*.py` `FIX_BASE` and applied before the review is invoked (`02-audit.json` .loop.wrapperShape; `make-review-final9.py:38-52` defines patch 56's fix this way). From round 16 no adjudicator plan was applied: rounds 16, 18-22 and 24-27 ruled `PROCEED`, except round 18 which ruled `PROCEED_WITH_DEFERRALS`, with 0 changes and 0 reverts while owner-chosen patches 45-59 were applied (`state-r27.json` .rulings; `02-audit.json` .adjudication.campaignLocalPlanning). The round-25 owner directive is recorded in `make-review-final9.py:20-30`: rounds 16-24 each fixed a rare edge case and most fixes caused the next finding. The adjudicator then deferred and planned nothing (`state-r27.json` .deferred, 26 entries), and the owner still applied patches 57-59 (`state-r28.json` .closures rounds 25, 26 and 27).

The campaign copy lacks three guards present in the shipped file. `mergeFindings` lacks the `material !== false` guard (`adversarial-loop.js:282`, DEF-ADVR-91). `settledFilter` matches the title only and lacks `sameFile` (`review.js:458`; `adversarial-loop.js:458`, DEF-ADVR-92/93). `ROUND_CAP` does not carry `args.findings` rows (`adversarial-loop.js:469-475`, DEF-ADVR-90). None had a recorded effect: every round tally is `CRITICAL:0`, no filter drop appears in `state-r27.json`, `state-r28.json` or any `review-final*-result.json`, and `ROUND_CAP` never fired (`02-audit.json` .loop.differencesFromCurrentShipped).

## 5. What better adjudication looks like

Each change below is a field, a definition or a return-shape extension that the adjudicator writes with a reason. None adds a severity, count or ratio threshold to the script. `maxRounds` remains the only unconditional numeric bound (`loop-spec.md:21`; `adversarial-loop.js:115`).

| Class | Change | File and section | Round stopped |
|---|---|---|---:|
| 75vh cap | `appliedFixes` row carries a replacement `barGuarantee` when a fix changes a bar clause, and the script rebuilds `barBlock` from it | `adversarial-loop.js` appliedFixes validation (98-103), `barBlock` (305-317); `loop-spec.md` INV-1 (17) and appliedFixes row (55) | 15 |
| Box plot geometry | `newMechanism` includes any rule that hides, clips or makes content unreachable, and the change must name what becomes unreachable | `adversarial-loop.js` newMechanism (190) and remedy (150); `adjudicator.md` step 5 (24); `loop-spec.md` INV-9 (25) | 15 |
| Tile typography | Each deferred entry is `{finding, reason, ownerDecision}`; a change whose cause depends on an open decision is not planned | `adversarial-loop.js` deferred items (208) and `priorRecord` (397-405); `adjudicator.md` steps 7 (26) and 4 (23); `loop-spec.md` INV-3 (19) | 17 |
| Tile accessibility and copy | `fixVerdicts` adds one keep, revert or refine verdict with a reason per closure, and reverts become the plan's reverts | `adversarial-loop.js` schema (new field after reverts at 207; required list 176), prompt (511-512), assembly (523-538); `adjudicator.md` step 4 (23); `loop-spec.md` INV-9 (25) | 19 |
| Regex compatibility and lint selectors | Trajectory is judged over all applied changes, the reason is persisted, and the existing two-of-three window counts a round with a non-empty applied delta | `adversarial-loop.js` trajectory fields (212-213), `rulings.push` (532), `priorRecord` (400), `FANOUT_STOP` window (546-547); `adjudicator.md` step 8 (27); `loop-spec.md` INV-5 (21) | 26 |
| Header strip scroll and wheel | `graphGap` names the layer the graph did not cover, and the adjudicator must name the uncovered layer before claiming a radius | `adversarial-loop.js` `graphBlock` (123-125) and schema; `adjudicator.md` steps 3 (22) and 2 (21); `loop-spec.md` graph row (53) and INV-3 (19) | grid 3 |

### 5.1 Consolidated change list

**A1 - bar guarantee carried with the fix.** When an applied fix changes a guarantee the bar states, the main session passes the replacement text in the `appliedFixes` row as `barGuarantee`. The script refuses a re-invocation whose fix names a `barGuarantee` while `args.bar` still carries the superseded clause, and rebuilds `barBlock` from the updated bar (`adversarial-loop.js:98-103`, `305-317`; `loop-spec.md:17,55`).

**A2 - clipping is a new mechanism.** Extend the `newMechanism` definition and the remedy description to any rule that hides, clips or makes content unreachable: an overflow and clip pairing, `clip-path`, `visibility: hidden`, `aria-hidden`. The change must name what becomes unreachable and the finding that justifies it (`adversarial-loop.js:150,190`; `adjudicator.md:24`; `loop-spec.md:25`).

**A3 - deferred entries carry the open decision.** Each deferred entry becomes `{finding, reason, ownerDecision}`, where `ownerDecision` names the design question and the decision that must answer it. The adjudicator may not plan a change whose cause depends on an open `ownerDecision`; the script carries open decisions into `priorRecord` and the return payload (`adversarial-loop.js:208,397-405`; `adjudicator.md:23,26`; `loop-spec.md:19`).

**A4 - a verdict on every closure.** `fixVerdicts` records `{fix, verdict: keep | revert | refine, reason}` for each closure. A fix that answered a finding the prior record refuted, or that is the cause of this round's finding, is `revert` unless the owner supplies new evidence; `refine` is allowed only when the original finding was material CRITICAL or MAJOR and the refinement is smaller than removal. The script turns revert verdicts into the plan's `reverts` and records the verdicts in `rulings` (`adversarial-loop.js:176,207,511-512,523-538`; `adjudicator.md:23`; `loop-spec.md:25`).

**A5 - trajectory over the applied delta.** Define spiralling against all applied changes, planned and owner-applied: a finding sitting in a mechanism the invocation's `appliedFixes` introduced, with a plan that leaves the mechanism in place, is spiralling with the mechanism named. Persist `trajectoryReason` in `rulings` and render it in `priorRecord`. Record whether the invocation carried an applied delta, and let the existing two-of-three window count a spiralling round with a non-empty applied delta even when its plan is empty (`adversarial-loop.js:212-213,400,532,546-547`; `adjudicator.md:27`; `loop-spec.md:21`).

**A6 - graph gap named.** Add `graphGap`: a line naming the layer the graph did not cover for the adjudicated findings (CSS rule and geometry, lint config, test body, accessibility tree, browser behaviour, rendered layout), empty only when the graph held a node for every adjudicated finding's file and symbol. Extend `graphBlock` to state what the graph covers and does not, and step 3 to require the radius source and the uncovered layer to be named (`adversarial-loop.js:123-125`; `adjudicator.md:21-22`; `loop-spec.md:19,53`).

The list touches three files. `adjudicator.md` gets A2 in step 5, A3 in steps 7 and 4, A4 in step 4, A5 in step 8, and A6 in steps 3 and 2. `loop-spec.md` gets A1 in INV-1 and the appliedFixes row, A3 in INV-3, A4 and A2 in INV-9, A5 in INV-5, and A6 in the graph row and INV-3. `adversarial-loop.js` gets every field, definition and control-flow change at the lines named above.

### 5.2 Expected effect on the loop exit conditions

- **Revert before refine.** A4 puts a verdict on every closure, so the round-17 revert proposal is recorded with its reason and the owner's rejection is recorded as new evidence. At round 19 the adjudicator's own `deferred[25]` wording makes the `<wbr>` split a revert, so patch 52 never answers it. The rule reaches owner-applied fixes, which enter through `appliedFixes` and currently pass unjudged
- **Trajectory stop.** A5 extends the trajectory input to the applied delta and leaves the existing judgment and window in place. Rounds 25 and 26 are spiralling because their findings sit in patches 56 and 57 and the plan leaves them in place. The existing two-of-three window counts a non-empty applied delta, so `FANOUT_STOP` fires at round 26 with patches 56 and 57 as revert candidates
- **Settled record.** The filters are unchanged: INV-4 held and no confirm-filter or settled-filter drop is recorded across 28 rounds (`state-r27.json` .history). A1, A3 and A4 add fields that `priorRecord` renders, so a changed bar clause, an open owner decision and a fix verdict are carried as settled evidence instead of being inferred from the next round's finding
- **Materiality triage.** The cap is unchanged: INV-8 held, and every round tally is `CRITICAL:0` (`state-r27.json` .rulings). The campaign's gap was that `material=false` findings were fixed by the owner after refutation. A4 requires the adjudicator to rule keep, revert or refine on those fixes, so a refutation is followed by a verdict on the change
- **Pinned confirm.** The confirm contract is unchanged: INV-4 held and the confirm read exactly the applied patch (`review.js:410-421`). A2 and A6 reduce the surface the confirm must attack by pricing clips and graph gaps at planning time. A1 keeps the confirm's bar current, so a confirm cannot reproduce a finding against a clause the code no longer claims. A4 gives the confirm a verdict ledger to attack

## 6. Prior cases that inform this

### 6.1 Paste-as-markdown fanout, 2026-08-28

The case ran 8 adversarial rounds on `jupyterlab_paste_content_as_markdown_extension`: architect and bug-hunter lenses, 14 reviewer runs, about 1080 reviewer turns and 3.5 hours; every verdict was DO-NOT-SHIP and the user killed round 8. Rounds 3-5 findings attached almost entirely to code the previous round's remedies introduced, and one CRITICAL data-loss defect was introduced by a fix. `devils-advocate:adjudicator` was never invoked. The code was rewritten while a review ran, with no frozen hash and no pinned confirming rounds. Measurement ended the loop: 537 lines fell to 302 (`project_paste_ext_review_fanout.md`; `loop-spec.md:7`).

This campaign contradicts the never-invoked half: the shipped adjudicator ran on all 24 finding-bearing rounds and ordered 8 reverts (`review.js:515`; `state-r27.json` .rulings). It confirms the unadjudicated-change risk in another shape: 11 clean rulings (rounds 3, 16, 18-22 and 24-27) were each followed by an owner-chosen fix, and from round 16 the wrapper applied the fix before the confirm, so those changes were never an adjudicated plan (`state-r27.json` .rulings; `02-audit.json` .adjudication.campaignLocalPlanning). Round 6 was stopped once when the applied delta changed under the confirm round (`02-audit.json` ownerDecisions round 5; `JOURNAL.md` entry 94). It also confirms the deletion lesson: the one chain ended by deletion, rounds 12-14 after the pandas dependency removed two mechanisms, shipped clean at round 14 (`state-r27.json` .rulings; `JOURNAL.md` entry 97).

### 6.2 Adjudicator replay experiment

`docs/experiments/adjudicator-replay/` replayed one groundrails review round (`wf_c4e8ef92-f3b`) against two adjudicator texts, 3 runs per arm on Opus 5.5, run `wf_aa37307f-f3c` (`PREREGISTRATION.md:5`). The experiment adds one lesson about instrumentation. The pre-registered primary outcome was a regex over planned-change text, and it counted any change naming a regex arm; 12 of its 14 matches were reverts that named the arm they removed, and the hand-coded replacement was made after the results were read (`report.md:26`). A closed prose list is not a reliable measurement instrument.

This campaign shows the same instrument problem inside the loop. `newMechanism`'s closed list (`adversarial-loop.js:190`) excludes a CSS clip, so patch 42 was not priced and produced `DEF-STATS-50` and `DEF-STATS-51` (`01-inventory.json` items 4 and 5). A2, A3, A4, A5 and A6 move the judgment into schema fields that the adjudicator writes with a reason at adjudication time, so no post-hoc text coding is needed. The replay differs in scale: 3 runs per arm on one round cannot show a field would change a ruling, while this campaign is one 28-round product run and can show which field was absent at each class's first round.

### 6.3 Generative loop criteria, 2026-09-02

The Star Colonel rejected three script-side stop rules for DEF-ADVR-50 with the words "hard criteria is no good, because I want criteria to be generative; those rules feel awfully complicated". The decision keeps one unconditional numeric bound, `maxRounds`, and requires one schema field with a reason that the judging agent writes (`feedback_generative_loop_criteria.md`).

This campaign is the counterexample that tests the remaining judgment stop. `FANOUT_STOP` is the one existing judgment stop and it never fired, although 33 of 34 findings were fix-induced and five of six classes spiral (`state-r27.json` .rulings; `01-inventory.json`). A count threshold on the fix-induced share would have fired, but a severity threshold could not discriminate because every round tally was `CRITICAL:0` under the materiality cap. The trajectory definition and the stop window's scope caused the miss; the window arithmetic was never reached. All six changes are fields, definitions or return shapes with reasons; no severity, count or ratio is added. The 2026-09-02 decision removed thresholds from the stop, and this campaign finds that the stop's input definition failed while its arithmetic was never reached.

## 7. Limits

- The campaign ran its own constructed script. `review.js` is a near-verbatim copy of the shipped worked example (`meta.name` `review-column-stats-dialog`, `LOOP_CONTRACT` 4), wrapped in `review-final*.js`; the shipped `adversarial-loop.js` was not the script that ran (`02-audit.json` .loop)
- Conclusions about the shipped adjudicator are inferences from recorded rulings. The shipped agent type is recorded on every finding-bearing round, but the exact plugin build resolved at run time is UNKNOWN (`02-audit.json` .adjudication.personaInvoked)
- `trajectoryReason` is logged only and never persisted, so the adjudicator's reasons for judging rounds 16-27 converging are UNKNOWN (`review.js:530`; `adversarial-loop.js:533`)
- Whether the AST graph gap changed any individual ruling is UNKNOWN (`03-mechanisms.json` class 6)
- Whether the stale bar guarantee changed any individual ruling is UNKNOWN (`03-mechanisms.json` class 1)
- The round-stopped values in section 5 are counterfactual projections. The record cannot prove that a different field would have changed the model's ruling
- The history counts 37 lens reports. Round 15 reports 5 findings against 4 surviving titles and grid round 3 reports 6 against 3, so four reports are lens duplicates; the 34 inventory items are 33 lens-derived findings plus item 10, a deferred root cause from `state-r27.json` deferred[24] that is not a lens report. The duplicate reports have no separate recorded title, so their content is UNKNOWN (`01-inventory.json` summary)
- Several findings have no defect id in the record (`defects: []` in `01-inventory.json` items 0, 1, 3, 6, 8, 9, 10, 19, 25-29 and 30-33). The record is silent on whether a defect was tracked elsewhere for them
- The prior root-cause inventory's stale claims are corrected here: the two round-27 lint-selector findings are FIXED by patch 59, and `DEF-STATS-52-NARROW-STRIP` is REJECTED in `docs/defects.md:388` and `JOURNAL.md` entry 102 although `state-r27.json` still lists it as deferred under the proposed id `DEF-STATS-46-NARROW-STRIP` (`01-inventory.json` correctionsToPriorInventory)
- The finding-bearing scope is statistics rounds 15-27 and grid rounds 3-4. Statistics rounds 7, 14 and 23 had zero findings, and grid round 5 shipped with zero findings
- Whether any adjudicator-planned change before round 16 answered a `material=false` finding is UNKNOWN; the adjudicator's own plan files `plan-r6.json` and `plan-r8.json` do not carry the answered findings' material flags (`02-audit.json` .adjudication.materialFalseFindingsFixed)
