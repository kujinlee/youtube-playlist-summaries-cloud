# Adversarial Plan Re-Review (Round 3) — Stage 3 Cloud Sync M2a (Claude)

Re-reviewed v3 (commit cf2d902) against v10 spec + real source. Every round-2 finding traced against new code; fresh defect hunt on changed T6/T12/backfill code.

## Mandate A — Round-2 closure audit
- Codex-r2 H1 (equal-value ts drift): CLOSED (logic) — but interaction with buildBaseline opens H-R3-1. Both-cleared/diff-clear-ts converges correctly; truly-equal returns 'equal'.
- Codex-r2 H2 (token chmod-before-check): CLOSED — assertSafeParent first, ENOENT→create 0700+verify, unsafe existing rethrows. Write-path test present.
- Codex-r2 H3 (additive copies cache): CLOSED — sanitizeAdditiveVideo clears summaryHtml/digDeeperHtml/digDeeperMd (only Video-level cache pointers per types/index.ts:57-59; no artifacts/PDF on local Video).
- Codex-r2 M1 / Claude-r2 N2 (presence NPE): CLOSED — explicit if(!lv||!cv){…continue} before two-sided; present=(lv??cv)! provably non-null; below uses bare lv/cv.
- Claude-r2 N1 (sourceMdHash filename): CLOSED in load-bearing text (step 3(c) mandates mdHash(md), test asserts mdHash(BODY) & not mdHash(env.sourceMd)) — but stale header plan:588 still says mdHash(sourceMd) → L-R3-1.
- Claude-r2 N3 (local allowlist corrections): CLOSED (spec'd + test).
- Claude-r2 N4 (buildBaseline skip): PARTIALLY — advances on skip OK, but records merges wholesale incl no-write conflicts → H-R3-1.
- Claude-r2 N5 (bare regenerate hash): CLOSED for normal cases; whitespace-only edge → L-R3-2.
- N6/N7/N8 accepted/documented.
- Money path: still clean.

## Mandate B — NEW findings

### HIGH
**H-R3-1 — buildBaseline records a no-write (backfilled) Class-B conflict as an "agreed" baseline → SILENT destructive overwrite next run, defeating §5.5.** runSync always calls buildBaseline(winnerSignals, winnerMdHash, merges) and records the entire merges map into classB with no exception for no-write conflict fields.
Trace legacy backfilled both-changed conflict on personalNote: Run1 reconcileField returns {winner:'equal', value:local.value, conflict:true} → applyClassBWinners writes nothing (correct, §5.5). But buildBaseline records classB.personalNote = local.value (FALSE agreement; cloud never held it). Run2: base.personalNote=local.value → lChanged=false, cChanged=true → single-changed branch fires BEFORE the backfilled guard → {winner:'cloud', conflict:false} → applyClassBWinners OVERWRITES local's human value with cloud's, silently. Each run individually §5.5-compliant, but the N4 baseline-advance converts "log every run" into run-2 data loss. No test catches it.
Secondary: reconciledCorrectionsHash uses local's value for a corrections no-write conflict while sides diverge → Class-A currency vs arbitrary side.
Fix: buildBaseline must NOT advance a Class-B field with winner:'equal' && conflict:true — carry prior base.classB[field] forward. Add two-run regression test.

### MEDIUM
**M-R3-1 — copyAdditiveVideo has no guard for one-sided video with summaryMd===null.** readMdBody returns null → body??'' = ''; copyAdditiveVideo unconditionally does to.<blob>.put(toP, video.summaryMd(null), ...) → throw/wrong write. A one-sided ingested-not-summarized video hits this. Fix: guard put with if(video.summaryMd && mdBody!=null); still upsert metadata; test.

### LOW
- L-R3-1: stale header plan:588 still mdHash(sourceMd) — change to mdHash(md).
- L-R3-2: whitespace-only corrections param → effectiveCorrections=='' stamps mdHash('') while stored persists → mis-marked stale. Base on stored value when trimmedCorrections falsy.
- L-R3-3: additive create uses plain upsert+raw blob put, not staged→promote; local→cloud publish may not get artifacts.summaryMd.status='promoted' → summaryReady false. Money-safe; note intended servability.

**Verdict: NOT CONVERGED** — 1 new High (H-R3-1). All round-2 Blockings/Highs otherwise genuinely closed. Fix H-R3-1 (+ M-R3-1, L-R3-1), re-run dual review — baseline-advance change on the human-precious path must be re-reviewed.
