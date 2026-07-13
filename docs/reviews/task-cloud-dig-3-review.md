# Task 3 Review — resolve-summary-key + makeDigHandler (Approved, converged after 1 fix round)

Dual review of `239d465` (base `417d587`); fix `9b32836`; focused money-path re-review of the fix delta.
Diff: `lib/dig/cloud/resolve-summary-key.ts` (`resolveSummaryMdKey`), `lib/job-queue/dig-handler.ts` (`makeDigHandler`), + their tests.

Money/auth-critical task (version guard + `PermanentTranscriptError`→`NonRetryableError` re-charge invariant) → full dual review (Claude task-reviewer + Codex adversarial).

## Round 1 — both reviewers

### Claude task-reviewer — ✅ Spec compliant, Task quality Approved (0 Critical)
Confirmed: version guard runs FIRST before any I/O (`dig-handler.ts:79-81`); `PermanentTranscriptError`→`NonRetryableError` verified against a **real** instance via `jest.requireActual` (stronger than a mock); named-risk (a) `worker-runner.ts:64` retries anything not `NonRetryableError` — both guards load-bearing and correct; named-risk (c) key precedence + `assertCloudSummaryMdKey` identical to `serve-summary-core.ts:56-64` (H1 blob-reachability holds for promoted case); happy-path does real substring assertions on the written buffer; `jest.clearAllMocks()` verified benign (top of `beforeEach`, clears history not the module-scope `jest.fn(impl)` implementations). 2 Important + 2 Minor (below).

### Codex adversarial — 0 Blocking, 1 High, 1 Medium
- **High** `dig-handler.ts` — transcript byte cap not applied to the dig prompt input. `summaryCore` truncates via `truncateSegmentsToByteCap(rawSegments, caps.transcriptInputBytes)` at `summary-core.ts:77` *after* `resolveTranscriptSegments`; the dig handler's caps only bound the transcribe fallback, so `window.transcriptWindow` reached `generateDig → buildIndexedTranscript` uncapped → unbounded paid Gemini input. **CONFIRMED real** (traced summary-core.ts:77 vs the dig path).
- **Medium** — `resolveTranscriptTokens` fed full-video `segments` while `generateDig` prompted with `window.transcriptWindow`; violates the same-list contract documented at `transcript-timestamps.ts:49`. **CONFIRMED** (low real-world blast radius since DIG v8 removed `[[TS:i]]` tokens, but the coherence contract binds).
- Codex explicitly confirmed the money-critical stale-version + `PermanentTranscriptError` paths are correct and the version guard precedes reads/generation/writes.

## Findings & dispositions

### High + Medium (Codex) — FIXED (`9b32836`), one coherent change
Cap the section window once and feed that single capped list to BOTH `generateDig` and `resolveTranscriptTokens` (`dig-handler.ts:86-88`), matching the summary input discipline and the `transcript-timestamps.ts:49` same-list contract. `windowForSection` preserves absolute offsets, so timestamps stay correct and full `video.durationSeconds` remains the correct clamp. New non-vacuous test proves it: seeds 400 large in-window segments, **asserts the un-truncated transcript exceeds `MAX_TRANSCRIPT_INPUT_BYTES`** (sanity), then asserts the window `generateDig` received is ≤ cap AND strictly fewer segments.

### Important #1 (Claude — docstring) — FIXED (`9b32836`, docstring-only)
`resolveSummaryMdKey`'s docstring overclaimed parity with `loadSummaryForServe` (which gates on `status==='promoted'`). A strict status gate here would break the legitimate top-level-`summaryMd` fallback (no-artifact videos have no status). Docstring rewritten to state it resolves the KEY only; the dig **trigger** owns the promoted-status gate. No behavior change.

### Minors (Claude) — FIXED (`9b32836`)
Section-not-found test now asserts `generateDig`/`promote` never called; happy-path asserts the `'summarizing'` phase.

### Deferred (rolled up for whole-branch triage — both reviewers Approved; NOT T3 defects)
- **CLOUD_CAPS DRY:** `dig-handler.ts` hand-copies `summary-handler.ts`'s unexported `CLOUD_CAPS` literal (brief-authorized). Extract a shared `buildCloudCaps()`/exported const in `lib/gemini-cost.ts` — touches already-merged `summary-handler` → own re-review. Fast follow-up.
- **generateDig cost surface (Claude ⚠️b):** `generateDig` uses `DEEPDIVE_MODEL=gemini-2.5-pro` (not `PRICED_MODEL` flash), takes no output cap and no `ctx.signal`. This is the spec's **deliberate** dig cost model (flat `dig_est_cents=150` + `max_attempts=1` + global daily `spend_ledger` cap, spec §money; §6 step 7 specifies `generateDig(window, videoId, lang)` with no caps), mirroring local `digSection` — not a defect. Missing signal = the already-tracked "abort doesn't stop billing" limitation (`summary-handler.ts:206-209`). Consider a `generate.ts` signal-plumbing follow-up.
- **Cross-task check for T5/T6:** the dig trigger MUST gate on `loadSummaryForServe` promoted-status before enqueue (plan Global Constraint). `resolveSummaryMdKey` intentionally does not gate on status; the trigger is the sole promoted-status gate. Verify when building T5/T6.

## Re-review (fix delta `239d465..9b32836`) — Codex, money path
0 Blocking / High / Medium / Low. Verified: capped list applied before `generateDig` and passed to `resolveTranscriptTokens`; cap uses `transcriptInputBytes`; offsets remain absolute; docstring change comment-only; truncation test carries both the over-cap sanity check and the bound/fewer-segments assertions.

## Disposition
Converged after 1 fix round (money-path re-review clean). Tests: dig-handler + resolve-summary-key 9/9 (incl. new truncation proof), full suite 2098/2098, tsc clean. 3 items deferred to whole-branch triage.
