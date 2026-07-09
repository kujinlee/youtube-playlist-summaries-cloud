# Task 1D-10 Review — Producer two-client split + guardrail buckets

**Impl:** 3b95727 · **Fix:** 1c243ea · **Base:** c41267d · Dual review (Claude SDD + Codex adversarial) → re-review CONVERGED.

## Spec Compliance: ✅ Full (SDD task reviewer, sonnet)

- Signature `enqueuePlaylist(sessionBundle, enqueuer: Enqueuer, principal, playlistUrl, ctx{ownerId,enqueueIp})`; `ProducerCounts` 7 fields; `JobFanoutResult |= {videoId, blocked}`; `ProducerResult` optional `challengeRequired?`/`dailyCapReached?` (challengeRequired never set by producer — route wires in T11).
- Disjoint-sum invariant hand-traced on the 7-item mixed test: `failed` computed over loop-only set, `tooLong = preBlocked + tooLongInLoop`.
- VOD/too_long pre-block reads from original `VideoMeta[]` (IngestionPayload lacks the field); absent/`'none'` → not blocked.
- Error paths: Quota→continue, DailyCap→cap-block-remaining+break+dailyCapReached, PJ003 in-loop→tooLong, other→failed (no raw leak).
- DECISION-1 honored: `JobQueue.enqueue`/`SupabaseJobQueue.enqueue` retained with `TODO(1d-T13)` (deletion deferred to T13; see ledger).
- Scope respected (5 files; route.ts + integration untouched).

## Codex Adversarial (frontier) — 1 High + 1 Medium, both fixed

- **High:** `Map<videoId, VideoMeta>` recovery could read wrong vm on duplicate videoId (bypassing live/upcoming pre-block). Not a live bug (real YouTube data = one liveBroadcastContent per id) but deviated from the plan's zip-by-position (round-3 L). **Fixed (1c243ea):** removed the Map; each enqueueable item carries `vm: videos[i]` positionally. Re-review traced the discriminating `['live','live','none']` same-id case — correct by construction.
- **Medium:** `AllEnqueueFailedError` threw on `created+joined===0 && failed>0` even in mixed guardrail-blocked+error cases, masking quota info as a generic 503. **Fixed:** narrowed to `created===0 && joined===0 && failed>0 && quotaBlocked===0 && capBlocked===0 && counts.tooLong===0` (throws only when genuine errors are the sole cause). Pure-error still throws; mixed/all-blocked return bucketed result.

## Re-review: CONVERGED
Both findings genuinely fixed (not reworded); disjoint-sum invariant re-verified; no fix-introduced regressions. producer 23/23 green.

## Deferred (whole-branch triage)
- Minor: `getGuardrailConfig()` uncached — one DB round-trip per enqueue (perf pass, later).

**Verdict: Approved.**
