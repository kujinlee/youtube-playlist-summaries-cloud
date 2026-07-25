# Local Validation Findings — First Real Run of the Cloud Stack (2026-07-13)

First end-to-end run of the merged cloud stack against **local Supabase** (`STORAGE_BACKEND=supabase`),
signing in via Google OAuth and ingesting real playlists. None of this code had ever been executed
before — every finding below is a boundary/real-data issue that the 2,141 mocked unit tests could not catch.

Environment: app on `localhost:3001`, worker under Node 22, local Supabase (migrations 0001–0018).

---

## Priority-ranked defects

### P0 — BUG-1: `complete_job` RPC param dropped → **whole pipeline fails at the finish line**
- **Symptom:** every summary/dig job shows `dead_letter`, "0 done · N failed", with an *empty* `jobs.error`.
- **Root cause:** `lib/storage/supabase/supabase-job-queue.ts:70` passes `p_result: result`. Handlers
  (e.g. `summary-handler`) return `undefined`. `JSON.stringify` drops `undefined`-valued keys, so PostgREST
  receives only `{p_job_id, p_worker_id, p_lease_token}` and can't resolve the 4-arg
  `complete_job(p_job_id, p_worker_id, p_lease_token, p_result jsonb)` (migration 0008) → `PGRST202`.
  The job's work (transcript, Gemini summary, blob upload, `persist_summary`) **all succeed**; only the
  terminal "mark complete" RPC throws, so the job is recorded as failed.
- **Fix (one line):** `p_result: result ?? null`.
- **Test gap:** no integration test exercises a real handler→`complete_job` round-trip with an `undefined`
  result against real PostgREST. Add one.

### P1 — BUG-2: cloud-only `maxItems` on the magazine schema → Gemini rejects it → **View Summary / PDF fail**
- **Symptom:** `GET /api/html/[id]?type=summary` → 500 "generating, retry shortly"; `GET /api/pdf/[id]` →
  500/503 "internal error". Independent of BUG-1 (serve-time in the Next.js route, not the worker).
- **Root cause:** `lib/gemini.ts:512-520` — **same model (flash) as local, different schema.** The local
  path sends `MAGAZINE_RESPONSE_SCHEMA` as-is (`sections` array, `minItems:1`, no upper bound). The **cloud**
  path clones it and adds `maxItems: MAGAZINE_MAX_SECTIONS` (= 200) as a cost/abuse bound. That large bound
  on the OUTER `sections` array — whose items contain an inner `bullets` array bounded `minItems:3,maxItems:7`
  of 2-required-string objects — explodes Gemini's structured-output constraint-"state" count past its
  serving limit → `400 The specified schema produces a constraint that has too many states for serving`.
  So the clamp whose comment says *"generous — never rejects a real doc"* makes Gemini reject **every** doc.
  Pro would reject the identical schema too; it is not a flash-capability issue. Introduced in the 1F-a cloud
  serve slice; never caught because no test submits the schema to the live Gemini endpoint.
- **Fix:** drop the schema-level `maxItems` clone (keep local & cloud on the bare schema). It is redundant:
  output is already bounded by `magazineOutputTokens` (`maxOutputTokens`), and the section count is validated
  post-parse (`gemini.ts:553`). No model change.

### P2 — BUG-3: `/api/videos` sort crashes on missing title
- **Symptom:** `GET /api/videos?playlist=…` → 500 for the whole list.
- **Root cause:** `app/api/videos/route.ts:28` → `a.title.toLowerCase()` throws when a video has no title.
- **Fix:** null-guard/coalesce title in `sortVideos` (define ordering for undefined — the dev-process
  "list/table UI: what do missing values do" rule).

### P2 — BUG-4: Supabase Storage "Invalid key" for non-ASCII (Korean) titles
- **Symptom:** `Invalid key: …/003_돈-버는-방식은-정해져-있다-수익-모델-15종` → job fails.
- **Root cause:** blob key is `${padSerial}_${slugify(title)}`; `slugify` passes Korean characters through,
  but Supabase Storage object keys must be a restricted (ASCII-ish) charset.
- **Fix:** make the storage key ASCII/allowed-charset safe (transliterate or percent-encode/hash the title
  component), preserving human readability where possible.

### P3 — BUG-5: worker swallows handler errors (observability)
- **Symptom:** a failing job logged nothing to stdout and left `jobs.error` empty — the BUG-1 error was
  invisible until instrumented by hand.
- **Root cause:** `lib/job-queue/worker-runner.ts` catch path sends the message to `fail_job` but never
  logs it; on some transitions `jobs.error` ends up empty.
- **Fix:** `console.error`/structured-log the handler error (id + kind + message) before calling `fail`,
  and verify `fail_job` persists the message through to a terminal `dead_letter`.

### P1 — BUG-7: Gemini structured-output silently truncates JSON string values at the first internal `"`
- **Symptom:** a rendered summary shows degenerate one-word content. Concrete repro (video `mrCfMJBOur0`,
  "The Great Bond Car Wreck", playlist `0d6f76b5-…`): the magazine section **"5. The End of 'Exorbitant
  Privilege'"** renders its gold `.lead` as just **"The"** and its first bullet as just **"The"**. The
  `.md` callout is hit too — `TL;DR: This video analyzes the global bond market's` and takeaway
  `Developed economies are losing their` are both cut mid-sentence.
- **Root cause:** every truncation lands exactly where a **literal double-quote** belongs in the prose
  (`"exorbitant privilege"`, `"slow-motion car wreck"`, `"debasement trade"`, …); apostrophes/single-quotes
  (`UK's`, `haven't`) always survive. Both the summary call (`lib/gemini.ts:322-323`) and the magazine
  transform (`:513-519`) use `responseMimeType:'application/json'` **+ `responseSchema`** (grammar-constrained
  decoding). When the model emits a bare `"` inside a string without escaping it as `\"`, the constrained
  decoder treats that `"` as the **string-closing** delimiter, drops the intended continuation, and coerces
  the remainder back to valid JSON → a **structurally-valid but semantically-truncated** value like
  `"lead": "The "`. It is stochastic per field: the long `summary` markdown field escaped its quotes and
  survived in the winning attempt while the short `tldr`/`takeaways`/`lead`/`bullets[].text` fields did not.
- **Why nothing caught it (every guard passes on truncated-but-valid JSON):**
  `assertNotTruncated` (`gemini.ts:231`) inspects only `finishReason` → it is `STOP` ("complete");
  `JSON.parse` (`gemini.ts:258`) succeeds (valid JSON); Zod `z.string().min(1)` (`types.ts:41`) passes
  (`"The "` is non-empty); `trimToWords` (`gemini.ts:399`) doesn't cut (7 words < 25). The quality loop
  `scoreSummary` (`gemini.ts:298`) ranks only the `summary` field, so an attempt with a great body but a
  quote-truncated TL;DR still wins. So the bad `tldr`/`takeaways` get written into the `.md`, and the
  magazine transform independently mangles + caches its `lead`/`bullets` in `models/…json`; the render
  (`render.ts`) faithfully displays the garbage.
- **Leading-candidate fix (needs live-Gemini verification):** drop `responseSchema` from these two calls,
  keep `responseMimeType:'application/json'` + the existing post-parse Zod validation. Gemini's
  *unconstrained* JSON mode escapes internal quotes correctly, and structure is already re-validated by Zod
  post-parse, so nothing is lost. (`responseSchema` is already a suspect surface — BUG-2 above kept it only
  after removing its `maxItems`.) Verify against real Gemini with a `RUN_LIVE_GEMINI=1` gated test asserting
  quote-bearing prose survives without the schema.
- **Scope:** money-path generation + **shared local/cloud code** → own Phase-1 spec + TDD slice + full
  dual-adversarial review per `docs/dev-process.md`. Not a one-liner.
- **Data note:** a code fix does NOT heal already-corrupted artifacts. The cached `models/…json` self-heals
  on a `GENERATOR_VERSION` bump or section-title drift; the `.md` callout truncation only clears on
  re-ingestion of the affected videos.
- **Test gap:** no test feeds quote-bearing prose through the real (unmocked) Gemini structured-output path;
  the mocks return clean strings, so this entire failure mode is invisible to the 2,200+ unit tests.

---

## Environment / config findings (not code defects — matter for deploy)

- **Worker doesn't load `.env.local`** — it's a plain `ts-node` process; env must be injected explicitly.
- **Worker requires Node 22+** — `@supabase/supabase-js` `createClient` needs native WebSocket; crashes on
  Node 20. README says "Node 18+" (stale for the worker).
- **`CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false`** disables the audio-transcription fallback, so a captionless
  video has no recovery path (not today's cause — captions worked).
- **Client env inlining (already fixed this session):** `lib/supabase/client.ts` read `process.env[name]`
  dynamically → `undefined` in the browser bundle → login threw. Fixed to static `NEXT_PUBLIC_*` refs.
  (Uncommitted, needs the proper workflow.)

### P2 — BUG-6: cloud playlists show "Untitled playlist" (title never fetched) — ✅ DONE (PR #17, `592db35`)
- **Symptom:** every cloud playlist in the sidebar renders "Untitled playlist".
- **Root cause:** the cloud ingest path (`producer.ts:90` → `resolvePlaylistId(playlistUrl)`) creates the
  `playlists` row but never calls `fetchPlaylistTitle` / sets `playlist_title` (the column exists,
  migration 0001). The LOCAL path does (`pipeline.ts:195`). The sidebar falls back to
  `p.playlistTitle ?? 'Untitled playlist'`.
- **Fix:** in the cloud enqueue path fetch the YouTube playlist title (`lib/youtube.ts:114
  fetchPlaylistTitle`) and persist it to `playlists.playlist_title`; backfill existing null rows.

## Feature requests (design items, not bugs)

- **Delete a playlist.** — ✅ DONE (PR #17, `592db35`): full hard-delete (DB cascade + recursive
  blob cleanup + share-token cascade + job cancellation), owner-scoped/RLS-safe, confirm modal.

- **Reservation-release lifecycle (cost ledger phase 2).** — **DEFERRED; trigger = before Fly.io
  deploy / before any real traffic.** Surfaced 2026-07-14 when a local validation run tripped
  "The service is at capacity" on `POST /api/jobs`.
  - **What's there today:** `spend_ledger` is a *reserve-only* daily fuse. `enqueue_job`
    (`0011_cost_guardrails.sql:113`) adds a worst-case `reserved_cents` at admission; the cap check is
    `reserved + actual + est <= daily_cap_cents` for the current UTC day. But there is **no release and
    no settle path** — no code ever decrements `spend_ledger.reserved_cents` (add-only) and
    `actual_cents` is never written (`0011:40` comment: *"never released in 1D"*). `complete_job` /
    `fail_job` (`0008`) don't touch the ledger. Reservations only clear at UTC-midnight rollover
    (a fresh ledger row).
  - **Why it's acceptable so far:** fail-safe — over-counts, never under-counts, so the money-safety
    invariant holds with zero real-money risk. Self-heals daily.
  - **Why it must be fixed before traffic:** the fuse is *global*, and cheap failures consume worst-case
    budget that never returns. With the shipped defaults (`daily_cap_cents=500`, `summary_est_cents=150`)
    only ~3 generations/day — success *or* failure — exhaust the whole system's budget until UTC
    midnight. A Gemini outage or retry burst self-DoSes all users at ~$0 real spend. Reserve-only + a
    safe-low cap are in direct tension: real traffic needs the release path for the cap to be sustainable.
  - **Design (for the future Phase-1 spec):** two-phase reserve→settle→release. On terminal transition,
    atomically `reserved -= est` and (on success) `actual += real_cost`; (on cheap failure/cancel/lease
    expiry) `reserved -= est`, `actual += 0`. The *sum* `reserved + actual` is the invariant to protect —
    the settle step **must be atomic** or a crash between "called Gemini" and "recorded actual" reintroduces
    the under-count/overspend the fuse structurally prevents (this is why phase 2 was deferred, not rushed).
  - **Cheaper middle option:** **release-only** (decrement `reserved` on terminal failure/cancel, skip
    real-`actual` accounting) kills the self-DoS footgun with a smaller money-path change; defer full
    spend-accounting until real-spend reporting/billing is actually needed.
  - **Scope:** money-path feature → own Phase-1 spec + plan + full dual-adversarial review (per
    `docs/dev-process.md`). Touches: `complete_job`/`fail_job`/`sweep_expired_leases` (0008/0009),
    the serve-charge reserve sites (0012/0014), and a settlement path that reconciles `jobs.reserved_cents`
    → `spend_ledger`. Evidence snapshot from the triage run: `scratchpad/reservation-leak-evidence-*.txt`
    (git-ignored). **Not a bug — a documented, fail-safe scope deferral with a firm trigger.**
- **Paged / batched ingestion for playlists > 50.** Current hard cap rejects large playlists. Proposed:
  ingest in pages (default 5–10, user-selectable up to e.g. 30), with a "next batch" control. Its own
  Phase-1 spec + gate.

---

## Meta

The four P0–P2 defects share one theme: **the real external service / real data behaves differently than
the mock** (PostgREST param serialization, Gemini serving limits, a null title, Storage key rules). This is
the inherent blind spot of mocking and exactly what a live run exists to surface. The closest guard would be
an integration layer that runs real handlers against real local Supabase + a smoke-render of the magazine
schema against the live Gemini endpoint.
