# Stage 2c — Cloud Doc Consumption (Frontend) — Design Spec

**Status:** Draft for approval (2026-07-11)
**Sub-project:** 2 (Frontend), slice **2c** (revised — see Reslice note)
**Depends on:** Stage 2a (cloud shell/library — merged), Stage 2b (cloud ingest — spec
approved, produces the summaries this slice consumes), Stage 1E/1F (worker summary +
authorized doc serving + share tokens — merged).

---

## 0. Reslice note

The original "2c doc lifecycle" (view/generate HTML·PDF·deep-dive) was found during
exploration **not** to be a clean frontend slice: cloud **PDF** and **deep-dive
generation** are local-only (in-memory-SSE, local filesystem) and need substantial new
backend (Supabase blob storage, durable serverless-safe jobs, and for deep-dive Gemini
charging + guardrails). Those are split out into a **separate deferred backend slice**
(cloud doc generation), which gets its own full spec + dual-review cycle.

**This spec (2c) is the CONSUMPTION half only** — viewing, downloading, and sharing the
summary docs that Stage 2b ingest already produces. It is genuinely frontend over
already-merged backend, with two minor read-model touches (§2). It also absorbs the
old "2d share + downloads UI."

---

## 1. Goal & scope

A signed-in cloud user can, per video: **view** the summary (magazine HTML), **download**
it (Markdown or HTML), and **share** it via a tokened public link (create with a TTL,
copy, revoke).

**In scope**
- Cloud `VideoMenu`: **View summary** (new tab), **Download Markdown**, **Download HTML**,
  **Share…** — all gated on summary readiness.
- `ShareDialog`: TTL selector → Create → URL + Copy → Revoke.
- A typed **`summaryReady`** field on the cloud Video DTO to gate the above.

**Out of scope (deferred / unchanged)**
- **Cloud PDF + deep-dive generation** — the separate backend slice.
- **Obsidian** — inherently local (filesystem vault); stays gated off in cloud.
- **Share listing / multiple-shares management** — there is no share-**list** route, so
  the dialog cannot discover shares created in a *previous* session. 2c therefore lets a
  user **create** a fresh link and **revoke the one created in the current dialog session**
  (whose id it holds in state); Copy reflects that link. A share made earlier elsewhere is
  not shown or revocable here. A full share-management surface (list all, per-share
  history, revoke-any) is deferred to the later slice. **Consequence:** repeated Create
  calls mint multiple valid tokens; that is acceptable for 2c (each link independently
  serves/expires; bulk cleanup is the deferred slice's job).
- **Ask-Gemini / Edit corrections / Re-summarize** — not doc-consumption; out of scope.
- **Cloud E2E harness** — documented-skip, shared 2a backlog item.

---

## 2. Backend touches (minor; session-client, owner-scoped, NO service role, NO generation)

1. **`summaryReady?: boolean` on the cloud Video DTO.** Derived
   `artifacts.summaryMd.status === 'promoted'`, populated by the existing owner-scoped
   `listVideos` **serveCloud** select. The field is **optional** → the local app is
   unaffected (it never sets or reads it; only `cloudMode` UI reads it). This exposes to
   the client the readiness the serving route already enforces server-side
   (`committed` → 503, not `promoted` → 404).
2. **Share `id` in the create response.** Revoke is by share id
   (`POST /api/share/<id>/revoke`), but `POST /api/share` currently returns
   `{ token, url, expiresAt }`. **Planning must confirm** whether the id is already
   returned; if not, add it to the response (session-client, owner-scoped; the row is
   the caller's own). No new table, no service role.

Both are read-model/response-shape additions — no generation, no charging, no guardrail
surface.

---

## 3. Architecture & data flow

Everything hangs off the cloud `VideoMenu`, whose Stage 2a `cloudMode` allowlist
currently permits only *Watch on YouTube* + *Archive/Unarchive*. 2c widens that allowlist
with readiness-gated items and adds one overlay (`ShareDialog`).

- **View / Download** are plain links (`<a>`), no client round-trip beyond the navigation
  itself — the `serveCloud` route renders/serves on demand. View opens a new tab; Download
  uses the route's `download=1` (browser save).
- **Share** is a client round-trip: `createShare` → `POST /api/share` (the created share's
  id + `<origin>/s/<token>` are held in dialog state); `revokeShare` →
  `POST /api/share/<id>/revoke` targets that held id only. The URL is shown + copied.
- **Readiness** (`summaryReady`) gates all four actions; sharing an unpromoted doc would
  produce a link that `/s` 404s on, so the gate is correct.

---

## 4. Components

| Component | Responsibility |
|---|---|
| `VideoMenu.tsx` *(extend cloud allowlist)* | Add **View summary** (link, `target=_blank`), **Download Markdown**, **Download HTML** (download links), **Share…** (opens dialog). All hidden-or-disabled per `summaryReady`. |
| `ShareDialog.tsx` *(new, `components/cloud/`)* | TTL selector (7d / 30d / Never, **default 30d**) → Create → show URL + Copy → Revoke. Overlay; full dismissal paths. |
| `lib/client/api.ts` *(extend)* | `createShare(playlistId, videoId, ttl)`, `revokeShare(shareId)`; URL builder `summaryHref(playlistId, videoId, {format?, download?})`. `401 → UnauthorizedError` (2a). |

---

## 5. Actions matrix

| Action | Trigger | Target | Gate |
|---|---|---|---|
| View summary | menu link, `target=_blank` | `GET /api/html/[id]?playlist=<uuid>&type=summary` | `summaryReady`; else disabled "Finalizing…" |
| Download Markdown | menu link (`download`) | `GET /api/html/[id]?playlist=<uuid>&type=summary&format=md&download=1` | `summaryReady` |
| Download HTML | menu link (`download`) | `GET /api/html/[id]?playlist=<uuid>&type=summary&format=html&download=1` | `summaryReady` |
| Create share | ShareDialog **Create** | `POST /api/share {playlistId, videoId, ttlDays}` | `summaryReady` |
| Copy link | ShareDialog **Copy** | clipboard (fallback: select-text) | after create |
| Revoke share | ShareDialog **Revoke** | `POST /api/share/<id>/revoke` | when an active share exists |

**TTL mapping:** 7d → `ttlDays: 7`; 30d → `ttlDays: 30` (default); Never → `ttlDays: 'never'`.

---

## 6. UI Design (wireframe + tokens)

```
Cloud VideoMenu (⋯)                    ShareDialog
┌───────────────────────┐   ┌─ Share "How Transformers Work" ──── ✕ ┐
│ Watch on YouTube  ↗   │   │ Link expires:  ( 7d ) (•30d ) ( Never )│
│ ───────────────────── │   │ ┌────────────────────────────────────┐ │
│ View summary      ↗   │   │ │ https://app…/s/<43-char token>     │ │ (readonly; empty
│ Download Markdown ⭳   │   │ └────────────────────────────────────┘ │  before Create)
│ Download HTML     ⭳   │   │            [ Revoke ]  [ Copy ]  [Close]│
│ Share…                │   │ ⚠ inline error (role=alert)             │
│ ───────────────────── │   └─────────────────────────────────────────┘
│ Archive               │   Before Create: field shows "No link yet" + [ Create link ].
└───────────────────────┘   After Create: URL populated, Copy + Revoke enabled.

  If !summaryReady:  View summary / Download * / Share…  render DISABLED with a
                     "Finalizing…" hint (the summary is still being made by ingest).
```

**Tokens:** reuse the 2a set (`--border`, `--text`, `--text-muted`, `--bg`,
`--bg-elevated`, `--accent`); `--danger` for the inline error; modal backdrop
`rgba(0,0,0,.4)`.

**Accessibility:** `ShareDialog` is `role="dialog"` + `aria-modal="true"`, focus-trapped,
initial focus on the TTL radio group, focus restored to the ⋯ trigger on close; error line
`role="alert"`; a transient "Copied ✓" via `aria-live="polite"` on copy. Disabled menu
items carry the "Finalizing…" hint via `title` + `aria-disabled`.

---

## 7. URL Contracts

| Component | Link text | Full URL |
|---|---|---|
| VideoMenu | View summary | `/api/html/[id]?playlist=<uuid>&type=summary` (new tab) |
| VideoMenu | Download Markdown | `/api/html/[id]?playlist=<uuid>&type=summary&format=md&download=1` |
| VideoMenu | Download HTML | `/api/html/[id]?playlist=<uuid>&type=summary&format=html&download=1` |
| ShareDialog | (Create) | `POST /api/share` body `{ playlistId, videoId, ttlDays }` |
| ShareDialog | (Revoke) | `POST /api/share/<shareId>/revoke` |
| ShareDialog | shown/copied share URL | `<origin>/s/<token>` (from the create response) |

---

## 8. Overlay Dismissal — `ShareDialog`

| Mechanism | Result |
|---|---|
| Backdrop click | Close — **disabled while a create/revoke request is in flight** |
| Escape | Close (same in-flight guard) |
| ✕ / Close button | Close |
| After Create (200) | **Stays open** (user must copy) — not a dismissal |
| After Copy | Stays open (transient "Copied ✓"); user closes manually |
| Create / revoke error | Stays open — inline `role="alert"` |

---

## 9. Error handling

- `createShare` / `revokeShare`: `401 → UnauthorizedError → router.replace('/login')`
  (2a pattern); other non-2xx → inline dialog error (form stays open).
- View / Download are `summaryReady`-gated, so the promotion-race (`503`/`404`) is largely
  avoided; a rare stale-flag click just surfaces the route's error in the opened tab —
  acceptable.
- Clipboard write failure → fall back to selecting the URL text so the user can copy
  manually (no thrown error surfaced).

---

## 10. Testing

- **Unit**
  - `summaryHref` builder — every `format`/`download` combination; assert **every** query
    param (`playlist`, `type`, `format`, `download`), per the E2E link-assertion rule.
  - `createShare` / `revokeShare` — status→error mapping (incl. `401 → UnauthorizedError`);
    TTL → `ttlDays` (7/30/`'never'`).
  - `summaryReady` derivation from artifact status.
- **Component**
  - `VideoMenu` cloud — ready state (View/Download/Share present, links carry exact
    hrefs); not-ready state (disabled + "Finalizing…"); local mode unaffected (field
    ignored).
  - `ShareDialog` — create success (URL shown, Copy/Revoke enabled); each error status;
    copy success + clipboard-failure fallback; revoke; **all dismissal paths** (§8);
    in-flight-disabled backdrop/Escape.
- **Integration (real Supabase, `signInAs`)**
  - share create + revoke round-trip; `summaryReady` reflected by `listVideos` serveCloud
    (promoted vs committed artifact).
- **E2E** — documented-skip, consistent with the 2a cloud-E2E harness gap.

Mock boundaries per `docs/dev-process.md`: `lib/gemini.ts` / `lib/youtube.ts` at the lib
boundary; E2E at the route level.

---

## 11. Global constraints (carried from the project)

- **Session-client-only** for user-facing read/write; **service role never** used from a
  user-facing store. Share create/revoke go through the existing session routes; the
  `summaryReady` select is session-client, owner-scoped.
- **`merge_video_data` left unchanged.**
- **Local app untouched and must stay green** — 2c adds only cloud components + one
  optional DTO field the local app ignores.
- **Share-serve never charges** — unchanged; 2c adds only create/copy/revoke UI, no serve
  path change.
- **No guardrail weakening** — 2c is display/link-only for docs; it changes no threshold
  and bypasses no gate.

---

## 12. Iterative dual-review flags

Per `docs/dev-process.md`, these get the iterative dual-review treatment during
implementation:
- **Share create/revoke** — a money-adjacent, multi-tenant surface (owner-scoped RLS,
  token generation); verify no cross-owner leakage and that revoke targets only the
  caller's own share id.
- **`summaryReady` gate + DTO field** — a read-model change threading through
  `listVideos` serveCloud and the menu; verify it never leaks non-owner artifact state
  and that the local path is truly unaffected.
