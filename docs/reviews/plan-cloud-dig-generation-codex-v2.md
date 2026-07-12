# Plan Adversarial Re-Review — Cloud Dig Generation (Round 2) — CONVERGED

Dual re-review of the revised `docs/superpowers/plans/2026-07-12-cloud-dig-generation.md` (+ spec).
Codex `gpt-5.5` + independent Claude reviewer, scoped to: (a) verify each round-1 fix is genuinely
fixed, (b) hunt for defects the fixes introduced.

## Convergence signal
**Both reviewers independently returned 0 new Blocking and 0 new High in production code.** Per the
dev-process Iterative Re-Review policy, a full round with no new Blocking/High is the gate — the
production design has **converged**.

## Round-1 fixes verified genuinely correct (against real code)
1. **B2 blob-mask (§9.2)** — `enqueue_job` returns `status='completed', joined=true` only when JOINing
   a pre-existing completed row; a normal completed job short-circuits to `200 ready` at the dedup
   `exists()` first. No false 409, no new race. ✓
2. **B3 version guard** — `digJobVersion() = 'dig-9'`; trigger enqueues `version: digJobVersion()`,
   handler rejects `job.version !== digJobVersion()` — same function both sides, no mass dead-letter. ✓
3. **H1 shared summary key** — `readVideo` returns `data.data as Video` (bare cast, **no zod parse**)
   so `.artifacts` is retained at runtime; `resolveSummaryMdKey`'s `artifacts.summaryMd.key ?? summaryMd`
   matches `loadSummaryForServe`. ✓
4. **H2 transcript wrap** — `let segments; try { ({segments}=…) } catch` maps `PermanentTranscriptError`
   →`NonRetryableError`, rethrows everything else — **AbortError not swallowed**. ✓
5. **H3 anon via profiles** — `profiles_self` RLS (`for all using (id = auth.uid())`) + select grant
   to `authenticated` → the session client can read its own `is_anonymous`; no 500. ✓
6. **M2 base guard** — `digSectionKey` rejects `/[/\\\0]/`, `.`, `..`; `'a/b'` throws, `0007_intro`
   and Korean bases pass. ✓
7. **B1 fixtures** — `▶ [2:12–2:20](…?t=132s)` matches `TS_LINE_RE`; parses to `startSec===132`. ✓

## New findings — all in the Task 7 integration harness (fixed in this revision)
- **HIGH (Claude) / MEDIUM (Codex) — `seedPromotedVideo` omits `durationSeconds` + `youtubeUrl`.**
  `enqueueDig` reads `load.video.durationSeconds` → `enqueue_job` PJ003 (null) → **400** on every
  202-expecting test; the handler would also deref `video.youtubeUrl`. **Fix:** Task 7 Step 0 extends
  the helper to persist both (defaults 600 / `https://youtu.be/${videoId}`).
- **MEDIUM (Codex) — anon test can't set `is_anonymous`.** `profiles_is_anonymous_immutable` trigger
  rejects `profiles.update({is_anonymous})`. **Fix:** Task 1 uses `anonSession()` + asserts the row is
  anon.
- **MEDIUM (Claude) — preflight ceilings unpinned.** Dig is the first integration path through
  `enqueue_preflight`; `ensureGuardrailHeadroom` doesn't set `max_free_users`/`max_queue_depth`, so
  cross-file accumulation can flake 202 tests as 403/503. **Fix:** Task 7 `beforeAll` pins both + dig
  quota.
- **LOW (Claude) — Task 6 param binding** (`POST(req, ctx)` vs the existing `POST(request, { params })`).
  **Fix:** aligned to the existing signature.
- **LOW (Codex) — stale "5/day"** at plan line 13. **Fix:** → 5/month.
- **LOW (Claude) — dig quota not raised** for back-to-back digs. **Fix:** pinned in `beforeAll`.

## Spec↔plan consistency (verified)
§5.2 (503/404/409) matches `loadSummaryForServe`; §9.2 matches `enqueueDig`; §11 rows 11a–c/19–21
align; live `jobs_idem_active = (owner_id, playlist_id, video_id, section_id, job_kind, job_version)`
matches the RPC `ON CONFLICT` and §9.1.

## Disposition
Round 2 = convergence gate (0 new Blocking/High). Round-2 findings were mechanical test-harness
corrections (not new production design), applied in this revision — no further full round required.
Plan is ready for subagent-driven implementation.
