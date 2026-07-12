# Plan Adversarial Review — Cloud Dig Generation (Round 1)

Dual review of `docs/superpowers/plans/2026-07-12-cloud-dig-generation.md` (+ spec).
Codex `gpt-5.5` (coordinator Bash, sandbox-disabled) + independent Claude reviewer. Both grounded in real code.

## Consolidated findings (deduped, most-severe first)

### BLOCKING
- **B1 (Claude) — Unparseable summary fixtures.** `parseSummaryMarkdown` requires `▶ [M:SS–M:SS](…?t=<sec>s)` (`lib/html-doc/parse.ts:16,23,32` — `▶` prefix + trailing `s`). Every plan fixture uses `[02:12](…?t=132)` → `timeRange:null` → `sections.find(startSec===132)` never matches → **every** Task 3/5/7 test fails at GREEN as a fake "section not found." Fix: all fixtures → `▶ [2:12–2:20](https://youtu.be/VID?t=132s)` (and a `t=0s` line in the concurrency fixture).
- **B2 (Codex) — Completed job masks a missing blob.** Blob absent + a `completed` dig row exists (wrong-key promote, storage repair/delete, prior bug) → `enqueue_job` JOINs the completed row (no charge, no work) → route returns `202 enqueued` for a job that never runs. Fix: in `enqueueDig`, on `res.joined && res.status==='completed'` re-check the blob → present ⇒ 200 ready; absent ⇒ 409 repair-needed. Test the completed-row-no-blob case.
- **B3 (Codex) — Stale queued job writes new-version blob without a new-version charge.** `dig-8` job charged+queued; deploy bumps `DIG_GENERATOR_VERSION`→9; worker uses the runtime constant → writes `.r9.md` → future trigger dedups r9 → v9 never charged. Fix: handler rejects `job.version !== digJobVersion()` (mirror `summary-handler.ts:74-76`). Old-job-after-bump regression test.

### HIGH
- **H1 (Codex High / Claude Med) — Handler vs trigger `base` divergence.** Trigger dedups on `load.base` = `artifacts.summaryMd.key ?? video.summaryMd`; handler derives from `video.summaryMd` only. If they diverge, handler writes a different key than the trigger deduped → repeated re-charge / repair-blocking. Fix: handler resolves the summary key/base the same way (shared helper `resolveSummaryKey(data)`), require promoted artifact, validate with `assertCloudSummaryMdKey`.
- **H2 (Codex + Claude) — `PermanentTranscriptError` not wrapped `NonRetryableError`.** `worker-runner.ts:64` classifies retryable by `!(e instanceof NonRetryableError)`; the raw permanent error is retryable → dead_letter (and re-charges Gemini if `dig_max_attempts>1`). `summary-handler.ts:126-136` wraps it; dig must too. Test with the real class asserting `NonRetryableError`.
- **H3 (Codex High / Claude Med) — Anon detection via `user.is_anonymous`.** If `getUser()` doesn't surface it, a genuine anon → `isAnonymous=false` → RPC PJ001 → **429** not spec **403**. Authoritative source is `profiles.is_anonymous` (read by `enqueue_job` itself). Fix: derive anon from `profiles.is_anonymous` via the session client.

### MEDIUM
- **M1 (Claude) — `ensureGuardrailHeadroom` import path.** No `./helpers/guardrails`; it's exported from `./helpers/clients`. Fix imports in Tasks 1 & 7.
- **M2 (Codex + Claude) — `digSectionKey('a/b')` doesn't throw.** `assertLogicalKey` allows interior slashes → the Task 2 `slash` test fails. Fix: single-component base guard in `digSectionKey`.
- **M3 (Codex) — Version-aware integration test weak.** Only seeds an old blob, no old completed job row. Fix: seed a completed `dig-8` row + old blob, assert `dig-9` enqueues+charges; add the completed-row-no-blob repair test (B2).
- **M4 (Codex M / Claude L) — Concurrency test near-tautological.** Direct handler calls with distinct keys can't fail against a shared-doc regression. Fix: add concurrent same-section `enqueueDig` → exactly one charged row.
- **M5 (Codex + Claude) — committed→503 vs spec 409.** `loadSummaryForServe` returns 503 (finalizing) / 404 (absent), never 409 "not committed." Fix: correct spec §5.2/§11 to the real semantics (503 finalizing / 404 absent / 409 repair) and pin with a test.

### LOW
- **L1 (Codex) — Migration verify wording.** State the exact live target `(owner_id, playlist_id, video_id, section_id, job_kind, job_version)` partial index (0009). (Both reviewers confirmed ON CONFLICT matches this — §9.1 resolution holds.)
- **L2 (Claude) — Quota is 5/MONTH not 5/day.** `usage_counters.period_start = date_trunc('month')`. Fix mislabeling in spec/plan Global Constraints.
- **L3 (Claude) — Note spec §6 `digging` phase.** Plan correctly reuses the 3 legal phases; add a one-line reconciliation note (DB CHECK rejects `digging`).
- **L4 (Claude) — Prefer explicit `jest.spyOn(SupabaseClient.prototype,'rpc')`** over `admin.constructor.prototype`.
- **L5 (Codex) — Thread abort into `generateDig`.** Deferred (accepted): `dig_max_attempts=1` + 60s internal timeout bound exposure; threading a signal touches shared local dig code. Record for a later hardening pass.
- **L6 (Claude) — GC-vs-completed-job constraint.** Record for the future GC slice: deleting a dig blob while its completed job row survives re-creates the B2 mask.

## Confirmed correct by BOTH reviewers (no change)
- §9.1 version resolution: live `jobs_idem_active` includes `job_version` (0009:12); est/attempts dispatch already routes `dig`→`dig_est_cents`/`dig_max_attempts` (0011:74-75); `loadSummaryForServe` never reaches `resolveMagazineModel`. Version bump → new slot (re-charge); same-version completed → JOIN no charge.
- Migration ON CONFLICT `(owner_id, playlist_id, video_id, section_id, job_kind, job_version)` matches the live index; 8-arg signature + grants correct.
- Auth: no service-role tenant read; non-owner → 404 via `resolveOwnedPlaylistKey`; 400-before-401 holds.
- Handler wiring signatures (`generateDig`, `readVideo`, `windowForSection`, `resolveTranscriptSegments`, `putStaged`) all match; skipping `resolveSlideTokens` safe in-slice.
- `Enqueuer.enqueue` payload widening does not break summary (jsonb passthrough).
- TOCTOU enqueue dedup benign — atomic INSERT-or-JOIN guarantees one charge.

## Disposition
Round 1 returned Blocking → per dev-process Iterative Re-Review, revise + re-review to convergence. All Blocking/High + Medium to be addressed in the plan (and spec for M5/L2). L5/L6 deferred with rationale.
