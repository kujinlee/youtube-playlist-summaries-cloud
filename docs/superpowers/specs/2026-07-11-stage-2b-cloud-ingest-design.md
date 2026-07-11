# Stage 2b — Cloud Ingest (Frontend) — Design Spec

**Status:** Draft for approval (2026-07-11)
**Sub-project:** 2 (Frontend), slice **2b**
**Depends on:** Stage 2a (cloud auth + shell + library — merged, PR #11), Stage 1D/1E (job queue + cost guardrails — merged)

---

## 1. Goal

Let a signed-in cloud user **create content**, not just browse it: enter a YouTube
playlist URL, enqueue it for ingestion through the existing cloud job queue, and
watch progress to completion — with every guardrail outcome (rate limit, capacity,
per-video blocks) surfaced clearly. Plus a **Refresh** action to re-ingest an existing
cloud playlist and pick up newly-added videos.

This slice is **frontend + thin client wiring only**. The backend (`POST`/`GET
/api/jobs`, producer fan-out, guardrail RPCs, workers) already exists and is
unchanged. The one possible backend touch is surfacing `playlist_key` in the
playlist DTO if 2a does not already (see §10).

---

## 2. Scope

**In scope**
- "+ New playlist" modal → `POST /api/jobs` → navigate to the new playlist.
- State-derived **progress banner** on the playlist page, polling `GET /api/jobs`.
- **Guardrail feedback**: preflight rejections (Phase-1 non-2xx) inline in the modal;
  per-video bucket outcomes (Phase-1 200) as a one-time summary notice.
- **Refresh/sync** an existing cloud playlist (re-POST `/api/jobs`; idempotent join).
- Un-disable the sidebar "+ New playlist" affordance.

**Out of scope (deferred, recorded)**
- **Cancel** an in-progress cloud ingest — needs new backend (cloud cancel route +
  worker cooperation). Deferred to a later slice.
- **CAPTCHA / challenge** — `challengeRequired` is surfaced as a soft, non-blocking
  notice only; no challenge is built (the enqueue already succeeds when it is set).
- **Single-video ingest** — the backend contract is playlist-URL only.
- **Cloud E2E harness** — documented-skip, consistent with the 2a cloud-E2E gap
  (shared backlog item; not 2b work).

---

## 3. Blocking vs non-blocking (dev-process async-op gate)

**Non-blocking.** The minutes-long worker phase never blocks the UI. The only modal
overlay is the brief create form (Phase 1); once submitted it closes and the user
keeps browsing — switching playlists, rating, filtering — while workers run. Progress
is a dismissible banner, not a full-screen overlay. Justification for the one overlay
(the create modal): a focused single-field form with explicit dismissal paths is
standard and does not obstruct any concurrent task; it is dismissed the instant the
POST returns.

---

## 4. Architecture & data flow

Cloud ingest is **two phases**; the UI models both.

### Phase 1 — submit (synchronous)
`NewPlaylistModal` → `apiClient.createIngest(playlistUrl)` → `POST /api/jobs
{playlistUrl}`.

The route runs preflight + the enqueue fan-out and returns
`ProducerResult { playlistId, jobs, counts, dailyCapReached?, challengeRequired }`.
- **Preflight rejections fail here** (non-2xx) — shown inline; the modal stays open.
- **Per-video blocks come back inside a 200** as `counts` buckets — shown as a
  one-time summary notice after navigation.

### Phase 2 — track (polling)
On the target playlist page, `IngestProgressBanner` polls `GET
/api/jobs?playlistId=<uuid>` → `{ jobs, rollup }` via the existing
`pollUntilTerminal` helper (`lib/job-queue/poll-client.ts`, exponential backoff
2s→10s, 10-min cap, 5 consecutive-error tolerance). `rollup` gives
`{ completed, total, terminal, failed, dead_letter, cancelled, ... }` — i.e. "N of M
done". On each progress change the video list re-fetches so completed rows appear
incrementally (mirrors the local app's "Saved"-triggered refetch). Polling ends at
`rollup.terminal`.

### The banner is **state-derived, not submit-scoped**
The banner does **not** depend on "did I just submit." Whenever a playlist page mounts,
it queries that playlist's job rollup; if there are non-terminal jobs, the banner shows
and polls. Consequences:
- Navigate away and back → progress resumes from server truth.
- The **Refresh** action → banner reappears naturally (new active jobs exist).
- An ingest started elsewhere (another device/session) shows correctly.

Rationale: workers run **out-of-process**, so the Supabase `jobs` table is the single
source of truth. (This is also why the local app's in-memory `subscribeJob` SSE cannot
be reused for cloud — it can only see the local single-process registry.)

---

## 5. Components

All new components under `components/cloud/`.

| Component | Responsibility | Depends on |
|---|---|---|
| `NewPlaylistModal.tsx` | URL field, submit, submitting state, inline guardrail errors, dismissal paths. | `apiClient.createIngest`, `useScope`, router |
| `IngestProgressBanner.tsx` | State-derived; polls `GET /api/jobs`, renders N/M + bar, re-fetches list on progress, resolves on terminal. | `apiClient.getJobStatus` + `pollUntilTerminal` |
| `IngestSummaryNotice.tsx` | One-time, dismissible summary of `ProducerResult` bucket counts (+ soft `challengeRequired` line). | pure formatter |
| `PlaylistSidebar.tsx` *(modify)* | Un-disable "+ New playlist"; `onClick` opens modal. | modal open-state |
| `CloudApp.tsx` *(modify)* | Own modal open-state; mount banner + notice on the playlist page; Refresh action on playlist header. | above |

### Client seam — `lib/client/api.ts` (extends the 2a scope-aware client)
- `createIngest(playlistUrl: string): Promise<ProducerResult>` → `POST /api/jobs`.
  Maps non-2xx → typed errors (see §6); `401` → `UnauthorizedError` (2a redirect
  pattern). Cloud-scope only (throws before fetch in local scope, per 2a).
- `getJobStatus(playlistId: string): Promise<{ jobs: PlaylistJobRow[]; rollup: Rollup }>`
  → `GET /api/jobs?playlistId=<uuid>`. Wrapped by `pollUntilTerminal(fetchRows)`.

### Pure formatter — `formatIngestSummary(counts, dailyCapReached, challengeRequired): string`
Deterministic, unit-tested per bucket combination. Lives beside the notice component
(or in `lib/client/`), no I/O.

---

## 6. Error & guardrail matrix (the heart of the slice)

### Phase 1 — POST non-2xx → inline in modal, **form stays open**

| Status | Cause (route) | User copy |
|---|---|---|
| 400 | missing / invalid `playlistUrl` | "Enter a valid YouTube playlist URL." |
| 401 | no session (should not happen when signed in) | redirect `/login` via `UnauthorizedError` |
| 403 | `!verdict.admitted` | "This account can't ingest right now." |
| 422 | `PlaylistTooLargeError {limit, found}` | "That playlist has {found} videos; the limit is {limit}. Try a smaller one." |
| 429 | `verdict.velocityExceeded` (+ `Retry-After`) | "You're adding playlists too quickly — try again in {retryAfter}s." |
| 502 | `PlaylistFetchError` | "Couldn't reach YouTube for that playlist. Try again." |
| 503 | `verdict.atCapacity` \| `AllEnqueueFailedError` | "The service is at capacity. Try again shortly." |
| 500 | internal | "Something went wrong. Try again." |

`Retry-After` is read from the response header (backend sends a fixed `60`).

### Phase 1 — 200 `ProducerResult` → close modal, navigate to `/?playlist=<playlistId>`, show `IngestSummaryNotice`

Summary composed from `counts` (all buckets: `enqueued, joined, skipped, failed,
quotaBlocked, capBlocked, tooLong`):

- Base: `Queued {enqueued}`.
- Append when > 0, in order:
  - `· {joined} already in progress`
  - `· {skipped} skipped (no captions)`
  - `· {tooLong} too long (>30 min)`
  - `· {quotaBlocked} blocked (quota)`
  - `· {capBlocked} blocked (daily cap reached)` — shown when `capBlocked > 0` **or**
    `dailyCapReached`
  - `· {failed} failed`
- `challengeRequired: true` → append a soft, non-blocking second line: "You're adding
  playlists quickly." (informational; **no** challenge flow).

**Navigation rule:** navigate whenever `playlistId !== null` — a playlist exists to
show, and the `IngestSummaryNotice` explains the outcome even when `enqueued + joined
=== 0` (e.g. "Queued 0 · 2 too long (>30 min) · 3 skipped (no captions)"). The banner
simply won't appear in that case (no non-terminal jobs to poll).

**Edge — `playlistId === null`:** nothing could be created/resolved from that playlist
(necessarily `enqueued + joined === 0`). The modal **stays open** and shows "No videos
could be ingested from that playlist." No navigation, no banner, no summary notice.

### Phase 2 — polling outcomes
- `rollup.terminal` with `failed + dead_letter > 0` → banner resolves to a mixed
  state: "N done · M failed" (not a clean success).
- Poll transport errors are tolerated by `pollUntilTerminal` (5 consecutive errors →
  give up; 10-min overall cap). On give-up the banner shows "Lost connection to
  progress updates — reload to retry." and stops.

---

## 7. UI Design

### Wireframe

```
┌─ Sidebar ────────────┐   ┌─ Playlist page (/?playlist=<uuid>) ──────────────┐
│ ML Talks             │   │ ⟳ Ingesting 12 of 42…  ▓▓▓▓▓▓░░░░░░  [dismiss ✕] │ ← IngestProgressBanner (non-terminal)
│ Rust Deep Dives      │   ├──────────────────────────────────────────────────┤
│ …                    │   │ ✓ Queued 42 · 3 skipped (no captions) · 2 too    │ ← IngestSummaryNotice (one-time, dismissible)
│ ┌──────────────────┐ │   │   long (>30 min)                          [✕]    │
│ │ + New playlist   │ │   ├──────────────────────────────────────────────────┤
│ └──────────────────┘ │   │ [video rows — refreshed as jobs complete]        │
└──────────────────────┘   └──────────────────────────────────────────────────┘

        ┌─ NewPlaylistModal ────────────────────────┐
        │ New playlist                          ✕   │
        │ ┌───────────────────────────────────────┐ │
        │ │ https://youtube.com/playlist?list=…   │ │
        │ └───────────────────────────────────────┘ │
        │ ⚠ That playlist has 80 videos; limit is 50│ ← inline error (form stays open)
        │                       [ Cancel ] [ Add ▸ ]│ ← [Add] shows spinner while submitting
        └───────────────────────────────────────────┘
```

### Progress banner states
| State | Render |
|---|---|
| Non-terminal | ⟳ spinner · "Ingesting {completed} of {total}…" · bar `width: {completed/total*100}%` · dismiss ✕ (hides banner locally; does not stop the ingest) |
| Terminal, all done | ✓ "Ingest complete — {total} videos" · auto-dismiss after a short delay, or on ✕ |
| Terminal, mixed | ⚠ "{completed} done · {failed} failed" · persists until ✕ |
| Poll gave up | ⚠ "Lost connection to progress updates — reload to retry." · persists until ✕ |

### Design tokens
Reuse the 2a token set (`app/globals.css`): `--surface-base`, `--surface-raised`,
`--surface-overlay`, `--border`, `--border-strong`, `--text-primary`, `--text-secondary`,
`--text-muted`, `--accent`, `--success`, `--warning`, `--danger`. No new tokens are added.
- Progress bar: track = `--border`; fill = `--accent`.
- `--danger` — Phase-1 error text / mixed-terminal warning.
- `--warning` — soft `challengeRequired` notice.
- Modal backdrop: `rgba(0,0,0,.4)`.

Accessibility: progress banner uses `role="progressbar"` with
`aria-valuenow/aria-valuemin/aria-valuemax`; Phase-1 error line uses `role="alert"`;
modal uses `role="dialog"` + `aria-modal="true"`, focus-trapped, initial focus on the
URL field, focus restored to the "+ New playlist" button on close.

---

## 8. URL Contracts

| Component | Action | Full URL / target |
|---|---|---|
| Sidebar "+ New playlist" | opens modal | *(none — no navigation, no request)* |
| `NewPlaylistModal` | submit success (200 + `playlistId`) | `router.push('/?playlist=<playlistId>')` (`playlistId` from `ProducerResult`) |
| Refresh (⟳) on playlist header | re-POST | *(no navigation — stays on `/?playlist=<uuid>`; issues `POST /api/jobs {playlistUrl}`)* |
| `NewPlaylistModal` | submit | `POST /api/jobs` body `{ playlistUrl }` |
| `IngestProgressBanner` poll | fetch | `GET /api/jobs?playlistId=<uuid>` |

---

## 9. Overlay Dismissal — `NewPlaylistModal`

| Mechanism | Expected result |
|---|---|
| Backdrop click | Close, discard input — **disabled while submitting** |
| Escape key | Close (same submitting guard) |
| ✕ button | Close |
| Cancel button | Close |
| Successful submit (200 + non-null `playlistId`) | Auto-close + navigate to `/?playlist=<playlistId>` (summary notice explains the outcome) |
| Error (non-2xx) or 200 with `playlistId === null` | **Stays open** — message shown inline (not a dismissal) |

---

## 10. Refresh dependency (verify in planning)

Refresh reconstructs the playlist URL from its YouTube id:
`https://www.youtube.com/playlist?list=<playlist_key>`, then calls
`apiClient.createIngest(url)`. This requires the client to have the playlist's
`playlist_key`. **Planning must confirm** the 2a `listPlaylists` DTO surfaces
`playlist_key`; if it does not, add a one-field addition to the DTO + its RLS-safe
select (session client, owner-scoped — no service role). This is the only candidate
backend touch in 2b.

---

## 11. Testing

- **Unit**
  - `formatIngestSummary` — every bucket combination, `dailyCapReached`,
    `challengeRequired`, and the base "Queued N" case.
  - `createIngest` — status → typed-error mapping for each row in §6, including
    `Retry-After` extraction and `422 {limit, found}` passthrough; `401` →
    `UnauthorizedError`.
  - `getJobStatus` + `pollUntilTerminal` wiring (rollup passthrough).
- **Component**
  - `NewPlaylistModal` — submit success; each error status; **all six dismissal paths**
    (§9); submitting-disabled state (backdrop/Escape guarded, buttons disabled);
    the 200-with-`playlistId===null` stay-open path; and the 200-with-`playlistId`-set
    but zero-queued navigate-and-summarize path.
  - `IngestProgressBanner` — non-terminal → polls → terminal (all-done); mixed
    terminal (failed count); terminal/empty rollup → hidden; poll give-up state.
  - `IngestSummaryNotice` — renders each bucket clause + soft challenge line; dismiss.
  - Sidebar "+ New playlist" — enabled, opens modal, focus behavior.
- **Integration (real Supabase, `signInAs`)**
  - `GET /api/jobs` polling + banner against seeded jobs (POST path already covered by
    1D/2a integration).
- **E2E** — documented-skip, consistent with the 2a cloud-E2E harness gap (same
  2nd-webserver + seeded-session blocker). Un-skipping is the shared backlog item.

Mock boundaries per `docs/dev-process.md`: mock `lib/gemini.ts` / `lib/youtube.ts` at
the lib boundary; E2E mocks at the API-route level; no real API calls in unit/component
tests.

---

## 12. Global constraints (carried from the project)

- **Session-client-only** for user-facing read/write; **service role never** used from
  a user-facing store. (The enqueue path's service-role use is confined to the existing
  `/api/jobs` POST route — 2b does not add service-role calls.)
- **`merge_video_data` left unchanged.**
- **Local app untouched and must stay green** — 2b adds only cloud components; the local
  ingest path (`/api/ingest` + in-memory SSE) is not modified.
- **Dual-backend discipline** — 2b touches only cloud components + the cloud client
  seam; no change to `serveLocal` behavior.
- **No guardrail weakening** — 2b is display-only for guardrail outcomes; it never
  changes thresholds or bypasses a gate.

---

## 13. Iterative dual-review flags

Per `docs/dev-process.md`, these areas get the iterative dual-review treatment during
implementation:
- The **guardrail error matrix** (§6) — money/guardrail-adjacent surface; every status
  and bucket must map to correct copy and the correct open/close behavior.
- The **state-derived banner** (§4) — a polling state machine with terminal/mixed/
  give-up branches and cross-navigation resumption.
