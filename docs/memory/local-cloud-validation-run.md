---
name: local-cloud-validation-run
description: "FIRES-WHEN: needing to run the cloud stack locally — How to run the cloud stack locally (local Supabase) + two deploy-relevant findings surfaced on first run"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

First-ever run of the merged cloud stack, against **local Supabase** (no hosted accounts). This is "step 1" before Stage 3 Sync — [[frontend-subproject-design-state]].

**How to run it locally:**
- `supabase start` (Docker) → local Supabase at `http://127.0.0.1:54321`, Studio `:54323`. Migrations 0001–0018 already applied; `artifacts` bucket exists (migration 0007).
- `.env.local` (gitignored) holds the 3 Supabase vars (standard local CLI keys — public, not secrets) + `STORAGE_BACKEND=supabase` + Gemini/YouTube keys reused from `../youtube-playlist-summaries-official-plugins/.env.local`.
- App: `npm run dev` → **port 3001** (3000 is taken by the user's other local app). Redirects to `/login` (auth gate). Local email signup works with no confirmation (`enable_confirmations=false`).
- Worker: `npm run worker`.

**Two deploy-relevant findings (worker only; the Next.js app is fine):**
1. **Worker doesn't load `.env.local`.** It's a plain `ts-node` process (Next auto-loads env, the worker doesn't). Must inject env explicitly: `set -a; source .env.local; set +a; npm run worker` — or a dotenv loader / host env injection at deploy.
2. **Worker needs Node 22+.** On Node 20 (the machine default, `v20.18.2`), `@supabase/supabase-js` `createClient` crashes initializing RealtimeClient — "Node.js 20 detected without native WebSocket support." Ran it under nvm `v22.14.0` (native WebSocket) → clean. Alternative: inject `ws` (installed, 8.20.1) as the realtime transport. README says "Node 18+" — stale for the worker.

Both are candidates to fix before/at the Fly.io deploy slice (own spec+gate). Neither is a code defect in the merged slice; they're runtime/packaging gaps the validation surfaced (same spirit as the deferred T12 deploy verification).

**Code defects the run surfaced — full list in `docs/local-validation-findings.md`:**
- **P0 BUG-1 (whole pipeline broken):** `lib/storage/supabase/supabase-job-queue.ts:70` passes `p_result: result` where handlers return `undefined`; `JSON.stringify` drops the undefined key → PostgREST gets 3 params → `complete_job` 4-arg (migration 0008) not found → `PGRST202` → every job `dead_letter` despite the work succeeding. Fix: `p_result: result ?? null`. Mocked unit tests never hit real PostgREST param-dropping.
- **P1 BUG-2:** magazine structured-output schema too complex for gemini-2.5-flash → `400 too many states for serving` → View Summary/PDF fail. Separate from BUG-1 (serve-time, not worker).
- **P2 BUG-3 (videos-sort NPE) — ✅ FIXED + MERGED (PR #18, merge commit 55ce4bf, 2026-07-14).**
  Branch `fix/videos-list-observability`: `sortVideos` now sorts incomplete/missing-key rows LAST
  (uniform for title/overall/ratings/duration/language/videoType/audience), so the list never 500s.
  Bundled a codebase observability sweep: `logError` (lib/dev-logger) wired into 11 route 5xx paths
  that previously swallowed the real error. Dual review converged 0B/0H over 2 rounds
  (`docs/reviews/videos-list-observability-review.md`); 2232 tests, tsc exit 0. NOTE: earlier
  `tsc | tail && echo` masked exit code — always check `tsc; echo $?`. Original bug detail below:
  `app/api/videos/route.ts:28`
  `a.title.toLowerCase()` (and `overallScore`/`ratings`/`durationSeconds` accesses) throw on a video row that
  lacks those fields → **uncaught TypeError → whole `/api/videos` list 500s** → UI "request failed with status
  500" + "No videos to show" (hides the videos that DID complete). Triggered by ANY title-less row: a
  reserved-but-incomplete slot (`{id, serialNumber}` only) from an in-flight OR failed/dead-lettered video.
  PR #16 did NOT touch this file (git: last touched by 2a `f6404a2`); the memory line below conflated this with
  PR #16's login env-inlining fix. **Live repro:** a Korean-title video hit BUG-4 (Invalid storage key) →
  dead-lettered → left a title-less slot row → the whole playlist list 500s permanently until that row is
  removed or sortVideos is guarded. Fix: guard every field access in `sortVideos` for incomplete videos
  (sort last, as it already does for serialNumber/personalScore/channel). Small TDD slice.
- **P2 BUG-4:** `slugify` keeps Korean chars → Supabase Storage "Invalid key".
- **P3 BUG-5:** worker-runner swallows handler errors (no stdout log; empty `jobs.error`).
- **Already fixed this session (uncommitted):** `lib/supabase/client.ts` dynamic `process.env[name]` → browser bundle undefined → login threw; fixed to static `NEXT_PUBLIC_*`.
- Feature request: paged/batched ingestion for playlists >50 (own spec).

**✅ MERGED — PR #16 (merge commit `1118898`) into master, 2026-07-14. Fix branch `fix/cloud-run-blockers` (`68cd23a` fix + `12f17c3` triage-doc):** BUG-1 + BUG-2 + BUG-3 fixed via TDD (RED watched before GREEN). BUG-1: `p_result: result ?? null` (unit JSON-serialization test + integration real-PostgREST test that throws the exact PGRST202 when reverted). BUG-2: removed the cloud `maxItems` schema clone + dead `MAGAZINE_MAX_SECTIONS` const (unit test inverted + opt-in `RUN_LIVE_GEMINI=1` live-gate test that real Gemini accepts). BUG-3: static `NEXT_PUBLIC_*` refs + smoke test. Dual review (Claude + Codex gpt-5.5) CONVERGED 0 Blocking/High — `docs/reviews/cloud-run-blockers-review.md`. Unit 2146/2146, integration 355 passed, tsc clean. **Push/PR/merge is a human gate — not done.** Still-open: BUG-4 (Storage Korean-key), BUG-5 (worker error observability), deploy findings, paged-ingestion feature.

Uncommitted working-tree change (local-only, intentionally NOT committed): `supabase/config.toml` (local Google OAuth: site_url→3001, redirect allowlist, `[auth.external.google]` + `skip_nonce_check`). Google creds in gitignored `.env.supabase.local`.

**LOCAL guardrail_config state (re-verified 2026-07-14, live query).** A prior session
already restored everything **cost- and velocity-relevant** to production defaults. Live vs
default now: `daily_cap_cents` 500 ✓default, `velocity_per_ip_hourly` 15 ✓, `captcha_soft_threshold`
5 ✓, `per_owner_serve_daily_cents` 60 ✓, all `*_est_cents`/`*_max_attempts` ✓. **Only two values
remain relaxed:** `max_free_users` 100→10000000 and `max_queue_depth` 200→10000000 — both are
intentional shared-integration-test-DB accommodations (`max_free_users` counts the 1264+ leftover
test profiles → default 100 would block all new signups; `max_queue_depth` accommodates leftover
test jobs). **Recommendation: leave those two as-is** — restoring to 100/200 re-trips the gates
during integration runs, and neither is a cost/security risk. The stale earlier claim ("6 values
relaxed incl. daily_cap→100000") is WRONG now. The `restore-local-guardrails.sql` file is EMPTY
(0 bytes) — non-functional; ignore it. Full clean slate if ever needed: `supabase db reset` (wipes
ALL local data incl. account → re-sign-in + re-configure OAuth).

**Reservation-release = documented design limitation, NOT a bug (code-confirmed 2026-07-14).**
Symptom: "New playlist" modal showed "The service is at capacity" (503 from `POST /api/jobs`
via `enqueue_preflight`). Cause: `spend_ledger` for the current UTC day had `reserved_cents=9150`
(=$91.50, ~61 jobs × 150¢ from the validation run) ≥ `daily_cap_cents=500`; `actual_cents=0`
(nothing really spent). Root cause is INTENTIONAL & documented — `0011_cost_guardrails.sql:40`:
`reserved_cents ... "charged spend (never released in 1D)"`. Code proves it: NO decrement of
`spend_ledger.reserved_cents` anywhere (add-only); `actual_cents` never written (no settle path);
`complete_job`/`fail_job` (0008) don't touch the ledger. `enqueue_preflight` caps on
`reserved+actual ≥ daily_cap_cents` for the **current UTC day** → self-heals only at UTC-midnight
rollover (fresh ledger row). Design is fail-SAFE (over-counts spend, never under → money-safety
invariant holds); cost = UX lockout on enqueue/retry/fail bursts within one UTC day. **Do NOT
launch a debugging investigation** — it's intended behavior. Evidence frozen at
`scratchpad/reservation-leak-evidence-592db35.txt`. **Reset applied this session:** today's
`spend_ledger.reserved_cents→0` + 4 stuck `active` jobs→`cancelled`; ingest reopened. **Open as a
FUTURE FEATURE (not a bugfix):** reserve→settle→release lifecycle so failed/cancelled attempts
return budget and `actual_cents` tracks real spend — money-path slice, needs full dual-review.
**TRACKED** in `docs/local-validation-findings.md` (Feature-requests section) with a firm trigger:
**resolve BEFORE the Fly.io deploy / before any real traffic** (global fuse + reserve-only + low
default cap → cheap-failure bursts self-DoS all users at ~$0 real spend; ~3 gens/day exhaust the
$5 cap). Cheaper middle option recorded: **release-only** (decrement reserved on terminal fail/cancel,
skip actual-accounting) fixes the self-DoS with a smaller change. No other planned phase (generation,
sync, deploy) currently owns it — must be explicitly scoped at deploy time.
