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

### P2 — BUG-6: cloud playlists show "Untitled playlist" (title never fetched)
- **Symptom:** every cloud playlist in the sidebar renders "Untitled playlist".
- **Root cause:** the cloud ingest path (`producer.ts:90` → `resolvePlaylistId(playlistUrl)`) creates the
  `playlists` row but never calls `fetchPlaylistTitle` / sets `playlist_title` (the column exists,
  migration 0001). The LOCAL path does (`pipeline.ts:195`). The sidebar falls back to
  `p.playlistTitle ?? 'Untitled playlist'`.
- **Fix:** in the cloud enqueue path fetch the YouTube playlist title (`lib/youtube.ts:114
  fetchPlaylistTitle`) and persist it to `playlists.playlist_title`; backfill existing null rows.

## Feature requests (design items, not bugs)

- **Delete a playlist.** `app/api/playlists/route.ts` is GET-only; no delete route or UI. The
  videos→playlists FK is `on delete cascade` (DB rows cascade for free), but **Storage blobs
  (summaries/PDFs) would orphan** — a delete feature must also remove the owner's blob objects for that
  playlist (and decide whether to cancel in-flight jobs). Needs: owner-scoped `DELETE` route + blob
  cleanup + sidebar control + confirmation. Small feature, one design decision (blob cleanup).
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
