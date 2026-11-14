---
name: local-cloud-validation-run
description: "FIRES-WHEN: needing to run the cloud stack locally (local Supabase + app + worker), or a local enqueue says 'at capacity' — the recipe, the two worker gotchas, and the local guardrail state"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**The rule — running the cloud stack locally:**
- `supabase start` (Docker) → local Supabase at `http://127.0.0.1:54321`, Studio `:54323`.
  `npm run test:integration` applies pending migrations itself ([[integration-suite-does-not-apply-migrations]]).
- `.env.local` (gitignored) holds the 3 local Supabase vars (standard local CLI keys, not secrets),
  `STORAGE_BACKEND=supabase`, and the Gemini/YouTube keys.
- App: `npm run dev`. ⚠ The port is NOT pinned in `package.json` (`"dev": "next dev"`); this memory
  recorded **3001** on 2026-07-14 (3000 is the owner's other app) while [[local-manual-test-env]]
  uses **3100** — check the running server, do not assume. Local email signup needs no confirmation;
  `/dev-login` exists (see [[local-manual-test-env]]).
- **Worker: `set -a; source .env.local; set +a; npm run worker` under Node 22+.** The worker is plain
  `ts-node` and does NOT auto-load `.env.local` (Next does). On Node 20 `@supabase/supabase-js`
  crashes building RealtimeClient ("Node.js 20 detected without native WebSocket support") — use nvm
  `v22.14.0`, or inject `ws` as the realtime transport.

**Why:** both worker gotchas look like code defects and are not; they cost the first run.

**How to apply:** if a local "New playlist" returns **"The service is at capacity"** (503 from
`enqueue_preflight`), check today's `spend_ledger` row before debugging — see the 2026-07-14 entry
below; the 1D reserve-only behaviour that caused it was the documented design at the time (the
reservation-release money-path slice merged 2026-07-17 as PR #22, per `docs/roadmap-to-launch.md`).

**Local `guardrail_config` (re-verified 2026-07-14):** everything cost-relevant at production
defaults, except two deliberate test-DB relaxations — leave them: `max_free_users` 100→10000000
(1264+ leftover test profiles would block signup) and `max_queue_depth` 200→10000000.
`restore-local-guardrails.sql` is EMPTY (0 bytes) — ignore it. Full clean slate: `supabase db reset`
(wipes the local account; re-sign-in and re-configure OAuth after).

Uncommitted, local-only by intent: `supabase/config.toml` local Google OAuth (site_url, redirect
allowlist, `[auth.external.google]` + `skip_nonce_check`); creds in gitignored `.env.supabase.local`.

## History (condensed) — the first local run, 2026-07-14

First-ever run of the merged cloud stack (before Stage 3 Sync, [[frontend-subproject-design-state]]).
Full defect list: `docs/local-validation-findings.md`.
- **BUG-1 (P0, every job dead-lettered):** `supabase-job-queue.ts` passed `p_result: result` with
  `undefined`; `JSON.stringify` dropped the key → PostgREST saw 3 params → `PGRST202`. Fix
  `result ?? null`. Mocked unit tests never hit real PostgREST param-dropping.
- **BUG-2 (P1):** magazine structured-output schema too complex for gemini-2.5-flash (`400 too many
  states for serving`).
- **BUG-3:** `lib/supabase/client.ts` read `process.env[name]` dynamically → undefined in the browser
  bundle → login threw; fixed to static `NEXT_PUBLIC_*`. BUG-1/2/3 fixed and merged in PR #16
  (`1118898`).
- **videos-sort NPE:** `sortVideos` threw on title-less reserved/dead-lettered rows → the whole
  `/api/videos` list 500'd. Fixed in PR #18 (`55ce4bf`); sorts incomplete rows last, plus `logError`
  in 11 route 5xx paths. ⚠ `tsc | tail && echo` masked the exit code — check `tsc; echo $?`.
- **BUG-4:** `slugify` kept Korean → Storage "Invalid key" (later backlog #36, closed 2026-08-17).
  **BUG-5:** worker-runner swallowed handler errors.
- **"At capacity" was the 1D design, not a bug:** `spend_ledger.reserved_cents=9150` (~61 jobs ×
  150¢) ≥ `daily_cap_cents=500`, `actual_cents=0`; nothing decremented `reserved_cents`
  (`0011_cost_guardrails.sql:40`), so it self-healed only at UTC midnight. Reset that session:
  today's `reserved_cents→0` + 4 stuck `active` jobs → `cancelled`. Evidence:
  `scratchpad/reservation-leak-evidence-592db35.txt`. The release lifecycle was required before any
  real traffic.
