# Stage 1E-b Plan — Claude Adversarial Review (round 1)

**Reviewer:** Claude (Opus), read-only, verified against `0001`/`0007`/`0008`, `lib/**`, `types/index.ts`, tests, and `@google/generative-ai@0.24.1`.
**Target:** `docs/superpowers/plans/2026-07-07-stage-1e-b-worker-summary-handler.md`.
**Date:** 2026-07-07.
**Verdict:** revise — 2 Blocking + 2 High.

## Blocking
1. **The `sweep_expired_leases` backoff rewrite breaks three existing passing tests that no task fixes.** `tests/integration/job-queue-worker.test.ts` re-claims immediately after `sweep` (L37 fencing, L51 fencing, L75 crash-loop dead-letters). Today's sweep requeues with no backoff (immediately re-claimable). The new sweep sets `run_after = now()+10s`, so the immediate re-claim returns nothing → assertions fail. Task 10 only hardens the *`fail_job`* test, never these three. They stay RED from Task 1 onward. *Fix:* update these three (reset `run_after=now()` between sweep/claim, or assert on id) inside Task 1.
2. **Tasks 1 & 2 gates ("`npm run test:integration` → all green") are unsatisfiable until Task 3.** Task 1 drops `enqueue_job(text,…)` and creates `enqueue_job(uuid,…)`, but the adapter + raw `enqueueScoped` helpers in four job-queue test files still call the old signature (PostgREST resolves by arg names → no match → every enqueue errors); the composite FK also needs each fixture to seed a playlist. So Tasks 1–2 commit a red suite. *Fix:* fold the adapter + fixture updates into Task 1, or gate Tasks 1–2 on the new targeted test + `tsc` only and defer full-suite-green to the adapter task.

## High
1. **The idempotency-skip read has no home, and the natural substitute reintroduces the `playlist_key` ambiguity this slice exists to kill.** `getWorkerStorageBundle` returns no `metadataStore`; `worker-persistence.ts` exposes only reserve/persist. The reach-for `SupabaseMetadataStore.readIndex` resolves by `.eq('playlist_key', …).maybeSingle()` with no owner filter → for a service_role worker where two owners share a `playlist_key`, it throws. *Fix:* add a `playlist_id`-keyed `readVideo(client, playlistId, videoId)` helper, specified in the seam task.
2. **`generateSummary`'s outer catch destroys the `AbortError` identity Task 5 asserts.** `generateSummary` wraps every error in `throw new Error('Gemini summary failed: '+cause)` (gemini.ts L272), so an `AbortError` from the abort-aware `generateJson` exits as a generic `Error` — Task 5's "rejects promptly (`AbortError`)" fails a name/`instanceof` check. Also step 1's "hang" mock never rejects on `signal`, so the test times out rather than proving promptness. *Fix:* re-throw abort unwrapped from `generateSummary`; make the test mock reject when `signal` fires.

## Medium
- **docVersion object-vs-string** (same as Codex H3) — specify `docVersionKey(data.docVersion) === job.version`. Test (b) has teeth (catches it).
- **Reserve idempotency tested only sequentially**; no concurrent test and no distinct "crash-between-stage-and-promote" test (spec §10 lists it separately). The property holds (the `playlists` `for update` serializes reservers — verified).
- **Task 3 step 5 fixture wording** says "update every JobKey literal," but the breakers are raw `rpc('enqueue_job', …)` `enqueueScoped` helpers, not literals — an executor will miss them; they also need a seeded playlist.

## Low
- `slug` → real helper is `slugify` (`lib/slugify.ts`); `padSerial` (`lib/serial-filename.ts`). The cloud handler correctly drops the fs `existsSync` collision loop (serial makes names unique).
- `VideoSchema.playlistIndex` is `.int().positive()`; YouTube positions are 0-indexed → a payload `playlistIndex: 0` fails `parse` on read. Latent 1E-c producer-contract mismatch.
- Spec §4.1 lists modifying `metadata-store.ts`/`supabase-metadata-store.ts`; the plan instead adds `worker-persistence.ts` and never touches them (cleaner, but that's why H1's read has no home).
- Both RPCs are `security invoker` (per Global Constraints), diverging from spec §8's `security definer` — works (service_role bypasses RLS; the `owner_id = p_owner_id` check still rejects a mismatch). `AbortSignal.any` needs Node ≥20.3. `setPhase` as a raw `jobs` UPDATE sits outside the "lifecycle is RPC-only" convention → prefer the `set_progress_phase` RPC.

## Verified OK (checked, actually fine — the load-bearing SQL is sound)
- `drop function enqueue_job(text,int,text,text,jsonb)` matches 0008 exactly; new `revoke/grant (uuid,text,int,text,text,jsonb)` matches the new arity.
- `on conflict (…)` arbiter exactly matches the re-keyed partial-unique-index predicate (aliased `j`).
- Composite FK `references playlists(id, owner_id)` backed by existing `unique(id, owner_id)`; both jobs cols NOT NULL — this is what rejects the attacker-enqueue.
- Sweep backoff formula byte-identical to `fail_job`; `j.attempts` in scope in `update jobs j … from expired e`.
- `reserve_video_slot` is genuinely idempotent and never returns another video's serial (playlists row-lock serializes; post-conflict re-read returns the winner's serial) — unlike `claim_video_slot`.
- `persist_summary`: status-only update preserves prior `artifacts.summaryMd.key` via the `coalesce(subquery)` on the pre-update row; sibling artifact kinds survive; `row_count=0` raise doesn't misfire (UPDATE counts matched rows; `updated_at=now()` always changes the row); mismatched owner rejected even for service_role.
- `@google/generative-ai@0.24.1` `SingleRequestOptions.signal` exists; its doc confirms "client-only … still charged" — matches decision 8.
- The built `Video` supplies every required schema field; reserved serial ≥1 satisfies `.positive()`.
- supabase-js surfaces plpgsql `raise exception` as `res.error != null` (0-row + owner-mismatch tests have teeth).
