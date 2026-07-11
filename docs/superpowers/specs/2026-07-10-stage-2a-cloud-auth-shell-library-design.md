# Stage 2a — Cloud Auth, Shell & Library — Design Spec

**Status:** Draft for user review (brainstorming gate)
**Date:** 2026-07-10
**Sub-project:** 2 (Frontend), slice **2a** — first slice
**Depends on:** Sub-project 1 (backend) merged through Stage 1G (PR #10, `4d5b597`)

---

## 1. Context & Product Vision

This app ships as **one codebase, two coexisting apps**, selected by the `STORAGE_BACKEND` env var:

- **Local app** — single user, filesystem storage (`outputFolder`, native folder picker, Obsidian vault links). **Already built. Stays. Not retired by this work.**
- **Cloud app** — multi-tenant, Supabase storage, auth-gated per owner (RLS isolation, per-owner cost guardrails, share tokens). **To be built** — Sub-project 2.

A future **Sync bridge** (Stage 3) lets a user **download** cloud→local and **upload** local→cloud (files, video metadata, and configuration), resolving conflicts by **newer-version-wins** per video. Sync is out of scope for 2a but shapes one data-model decision here (§7.1).

**Why the current UI needs this work:** the existing frontend is a complete, well-tested *local-desktop* app (~20 component tests, 10 Playwright specs, working SSE streams) but it is built entirely on the local filesystem model. It has **no authentication UI** (the `app/auth/callback` route is orphaned), no owner/playlist cloud model, and it never calls the cloud API routes. The cloud backend is effectively invisible to it.

Separately, Sub-project 1 was **never completed for the read/list surface**: the cloud migration built the write/generate/serve/share paths, but the library **read** routes (`/api/videos`, `/api/playlists/recent`) were left on the Stage-1C local path and throw in `supabase` mode. 2a closes that gap (Phase A) as a prerequisite for the library UI (Phase B).

---

## 2. Goal & Scope

**Goal:** A multi-tenant user can sign in with Google, see a sidebar of their playlists, open one, and browse/sort/filter/annotate its videos — all against Supabase, owner-isolated.

### In scope (2a)

**Phase A — Backend read layer (cloud branches; backend-first):**
- New `updatedAt` field on `Video`, bumped on every write, in both stores (§7.1).
- `MetadataStore.listPlaylists(ownerId)` + Supabase impl.
- `GET /api/playlists` cloud route.
- Cloud branch on `GET /api/videos`.
- Cloud branch on `GET /api/videos/[id]/quick-view`.
- Cloud branch on `POST /api/videos/[id]/review` (rating/note writes).
- Cloud branch on `POST /api/videos/[id]/archive` (archived flag, §7.2).

**Phase B — Cloud frontend:**
- Google-OAuth login page + session gating (middleware).
- Cloud app shell: header/account menu, playlist sidebar, main library pane.
- Scope-aware API client seam (§3.4) so shared leaf components work in both modes.
- Library: reuse presentational components (`VideoList`, `VideoRow`, `FilterBar`, `StarRating`, `Badge`, `VideoQuickView`) retargeted to the cloud scope; list + sort + filter + quick-view + **annotate** (rate / note / archive).
- Empty states (no playlists; playlist with no videos yet).

### Out of scope (later slices)
- **2b** — Cloud ingest (playlist URL → `/api/jobs` queue → SSE progress). In 2a, "+ New playlist" and any re-ingest action are **stubs**.
- **2c** — Doc lifecycle: generate/view magazine HTML, PDF, deep-dive; serve-budget/stale UX. In 2a, the row-menu items that generate or open docs are **hidden/disabled**.
- **2d** — Share tokens + downloads UI (+ decide Obsidian's fate in cloud).
- **Stage 3** — Sync.
- **Local app changes** — none. The local shell keeps its folder picker, path routes, and Obsidian links unchanged.

### Non-goals
- No password/magic-link/GitHub auth (Google OAuth only).
- No account self-service beyond sign-out (no profile edit, no delete-account) in 2a.
- No flat cross-playlist library view (nav is per-playlist, §3.3).

---

## 3. Architecture

### 3.1 Dual-mode shell dispatch
`STORAGE_BACKEND` is a server env, fixed per deployment. `app/page.tsx` becomes a **thin server component** that reads the mode (and, in cloud mode, the session) and renders one of two shells:
- `local` → the existing client page, extracted verbatim into `components/local/LocalApp.tsx` (no behavior change).
- `supabase` → the new `components/cloud/CloudApp.tsx`.

Leaf presentational components are **shared** by both shells. This keeps one component library and one test surface, and makes the local/cloud split a single dispatch point rather than a fork.

### 3.2 Auth (cloud only)
- **Provider:** Supabase Google OAuth via the existing browser factory `lib/supabase/client.ts` `createClient()`.
- **Login:** `/login` page with a single "Continue with Google" action → `supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: '${origin}/auth/callback' } })`.
- **Callback:** the existing `app/auth/callback/route.ts` exchanges the code for a session cookie. On error → existing `app/auth/auth-error/page.tsx`.
- **Session gate:** a new `middleware.ts` (using `@supabase/ssr`) refreshes the session on every request and, in cloud mode, redirects unauthenticated requests for app routes to `/login` and authenticated requests for `/login` to `/`. Middleware is a **no-op in local mode** (matcher guarded by env, or the redirect logic short-circuits when `STORAGE_BACKEND !== 'supabase'`).
- **Sign-out:** account menu → `supabase.auth.signOut()` → redirect `/login`.

### 3.3 URL / navigation model
- Single-page shell; active playlist is a **query param**: `/?playlist=<uuid>`.
- `/` with no param → library home (sidebar + "pick a playlist" empty pane).
- Playlist identity in the URL is the **playlist UUID** (`playlists.id`), consistent with `/api/html/[id]?playlist=<uuid>`. The UUID is resolved to `playlist_key` server-side via `resolveOwnedPlaylistKey` (`lib/storage/serve-playlist.ts`), which also asserts ownership.

### 3.4 Scope-aware API client (the key seam)
New module `lib/client/api.ts` (browser) centralizes request construction from the **current scope**:
- Local scope = `{ mode: 'local', outputFolder, baseOutputFolder }`.
- Cloud scope = `{ mode: 'cloud', playlistId: <uuid> }`.

It exposes typed calls the components use instead of building URLs inline, e.g. `listVideos(scope, sort)`, `getQuickView(scope, videoId)`, `saveAnnotation(scope, videoId, patch)`, `setArchived(scope, videoId, archived)`, `listPlaylists()`. Cloud calls send `?playlist=<uuid>` (or `{ playlist }` in the body); local calls send `outputFolder`. The scope is provided via React context (`ScopeProvider`) at the shell level, so leaf components (`StarRating`, `VideoQuickView`, `VideoMenu`) drop their inline `fetch` + `outputFolder` URL-building and call the client. **Presentational markup is unchanged**; only the data-access lines move.

---

## 4. Phase A — Backend read layer

All cloud branches follow the established `serveLocal` / `serveCloud` pattern from `app/api/html/[id]/route.ts`: dispatch on `STORAGE_BACKEND`; cloud branch calls `createServerSupabase(cookies)` → `auth.getUser()` (401 if none) → `resolveOwnedPlaylistKey(client, playlistId, user.id)` (404 if null) → `getPrincipalFromSession({ userId }, playlistKey)` → `getStorageBundle({ supabaseClient })`. Local branch is unchanged.

| # | Item | File(s) | Notes |
|---|---|---|---|
| A1 | `updatedAt` field + bump-on-write | `types/index.ts`, both metadata stores + RPCs | §7.1 — its own schema section; iterative dual review |
| A2 | `listPlaylists(ownerId)` | `lib/storage/metadata-store.ts` (interface), `.../supabase/supabase-metadata-store.ts`, `.../local/local-metadata-store.ts` | Supabase: `.from('playlists').select('id, playlist_key, playlist_url, playlist_title').order('playlist_title')` on session client (RLS auto-scopes to owner). Local: wrap existing `listRecentPlaylists`. Returns `{ id, playlistKey, playlistUrl, playlistTitle, videoCount? }[]`. |
| A3 | `GET /api/playlists` | `app/api/playlists/route.ts` (new) | Cloud: auth + `listPlaylists`. Local: `?root=<path>` → existing recent-provider. |
| A4 | `GET /api/videos` cloud branch | `app/api/videos/route.ts` | Refactor to serveLocal/serveCloud. Cloud: `?playlist=<uuid>` → `readIndex` → reuse existing `sortVideos`. **Skip** `recoverOrphanedVideos` (filesystem). |
| A5 | `GET /api/videos/[id]/quick-view` cloud branch | `app/api/videos/[id]/quick-view/route.ts` | Cloud: `?playlist=<uuid>` → `readIndex` → select the one video's `{ tldr, takeaways, tags }`. |
| A6 | `POST /api/videos/[id]/review` cloud branch | `app/api/videos/[id]/review/route.ts` | Cloud: body `{ playlist: <uuid>, personalScore?, personalNote? }` → `updateVideoFields` (RPC `merge_video_data`, already cloud-ready). Same validation as local. |
| A7 | `POST /api/videos/[id]/archive` cloud branch | `app/api/videos/[id]/archive/route.ts` | Cloud: body `{ playlist: <uuid>, action: 'archive'\|'unarchive' }` → `updateVideoFields({ archived })` (§7.2). |

**Auth/session/RLS infrastructure already exists** (`lib/supabase/{server,client,service}.ts`, RLS `owner_id = auth.uid()`); no new infra.

---

## 5. Phase B — Cloud frontend

| Component | New/Reuse/Retire | Responsibility (2a) |
|---|---|---|
| `app/page.tsx` | Rework → thin server dispatch | Read mode + session; render `LocalApp` or `CloudApp`. |
| `middleware.ts` | New | Session refresh + `/login` gating (cloud only). |
| `app/login/page.tsx` | New | "Continue with Google". |
| `components/cloud/CloudApp.tsx` | New | Cloud shell: `ScopeProvider`, header/account menu, sidebar, library pane. |
| `components/cloud/PlaylistSidebar.tsx` | New | Fetch `/api/playlists`; list; active from `?playlist`; "+ New" stub (→ 2b). |
| `components/cloud/AccountMenu.tsx` | New | Email + Sign out (dropdown). |
| `components/local/LocalApp.tsx` | Extract from current `page.tsx` | Local shell, unchanged behavior. |
| `lib/client/api.ts` + `ScopeProvider` | New | Scope-aware data-access seam (§3.4). |
| `VideoList`, `VideoRow`, `FilterBar`, `StarRating`, `Badge`, `VideoQuickView` | Reuse (retarget data calls to the client seam) | List/sort/filter/quick-view/annotate. Markup unchanged. |
| `VideoMenu` | Reuse (2a: hide/disable generate/PDF/deep-dive items) | 2a keeps only Archive/Unarchive + Corrections-note; doc actions land in 2b/2c. |
| `Header` (folder picker), `PlaylistPicker`, `ChannelPlaylistPanel`, obsidian-path logic | Local-only (not used by `CloudApp`) | Untouched; local shell keeps them. |

**Library behaviors in 2a:** sort (all existing `SortColumn`s), filter (`FilterBar`), Show-Archive toggle (archived rows greyed), quick-view expand, rate (`StarRating` → review route), personal note, archive/unarchive. **Excluded:** generate/view HTML·PDF·deep-dive, re-ingest, share — deferred.

---

## 6. Data flow (cloud)

```
Google OAuth → /auth/callback (session cookie) → middleware admits /
  → CloudApp mounts, ScopeProvider(mode=cloud)
  → PlaylistSidebar: GET /api/playlists            → render playlists
  → user clicks a playlist → URL ?playlist=<uuid>
  → Library: GET /api/videos?playlist=<uuid>&sortColumn=&sortOrder=  → render VideoList
  → rate:    POST /api/videos/[id]/review  { playlist:<uuid>, personalScore }
  → note:    POST /api/videos/[id]/review  { playlist:<uuid>, personalNote }
  → archive: POST /api/videos/[id]/archive { playlist:<uuid>, action }
  → quickview: GET /api/videos/[id]/quick-view?playlist=<uuid>
```

---

## 7. Data-model & schema decisions

### 7.1 Versioning signals for Sync's newer-wins — schema change, iterative dual review

Sync (Stage 3) decides "which copy of a video is newer" per video. **Two** signals govern it:

- **`docVersion {major, minor}`** — the doc-format / generator version. **Already exists.** Stamped to `CURRENT_DOC_VERSION` on (re)generation and HTML render (`lib/pipeline.ts:266`, `lib/job-queue/summary-handler.ts:162`, `lib/html-doc/ensure.ts:66`); **not** touched by rating/note/archive edits. Higher = newer generator = newer document. (Optional; absent ⇒ `{1,0}`, oldest.)
- **`updatedAt: string (ISO-8601 datetime)`** — **NEW.** Last-write timestamp, **stamped on every write** (annotations *and* generation) in both stores. Cloud stamps it server-side (DB clock, authoritative) in the `merge_video_data` / `merge_video_data_bulk` / upsert RPCs so concurrent clients can't skew it. Local: `local-metadata-store` write paths. Optional; absent ⇒ oldest (back-compat).

**Comparator (Stage 3), lexicographic — `docVersion` primary, `updatedAt` tiebreak:** compare `docVersion` first (higher wins); if equal, compare `updatedAt` (more recent wins). This matches the intended semantics:
- Same doc, a more recent rating/note edit → same `docVersion`, newer `updatedAt` → the **edited copy wins**.
- Regenerated with a **newer** generator → **higher `docVersion` wins** (usually newer `updatedAt` too).
- Regenerated recently but with an **older** generator → **lower `docVersion` loses despite a newer `updatedAt`** — an old-format doc is still older even if generated more recently.

**2a action:** add `updatedAt` now (Phase A). `docVersion` already exists, so introducing `updatedAt` now hands Stage 3 **both** comparator keys with **no backfill**. Touches write RPCs / idempotency and both stores → §8 iterative dual-review treatment (`docs/dev-process.md`).

**Deferred to Stage 3 (signals already stored — no 2a backfill either way):** whole-record replacement vs. field-partitioned merge. Whole-record (the literal "newer version overrides older") is simplest but can **drop a newer *annotation*** that sits on the lower-`docVersion` side when the higher-`docVersion` copy wins. A field-partitioned merge (doc fields by `docVersion`+recency; annotation fields — `personalScore`/`personalNote`/`archived` — by `updatedAt`) avoids that loss. 2a stores all three signals (`docVersion`, `processedAt`, `updatedAt`), so Stage 3 can pick either.

*(Plan-phase sub-question retained: `updatedAt` ISO datetime vs. a monotonic `revision` integer. Recommendation: `updatedAt` ISO datetime, DB-clock-stamped — human-readable, sufficient for last-writer-wins, and cheap.)*

### 7.2 Archive = `data.archived` flag (not membership)
Local archive moves files to `archived/`. The cloud analog is the **`archived` boolean already on `Video`**, set via the existing `updateVideoFields({ archived })` path (RPC-backed, cloud-ready). This is distinct from `reconcilePlaylistMembership` (which tracks whether a video is still in the YouTube playlist). The `/api/videos/[id]/archive` cloud branch therefore flips the flag; no file move, no membership change.

---

## 8. UI Design

### 8.1 Wireframes

**Login (`/login`):**
```
┌──────────────────────────────────────────┐
│                                          │
│            YouTube Summaries             │
│         Your playlist library,           │
│              in the cloud                │
│                                          │
│      ┌──────────────────────────┐        │
│      │  ⟳  Continue with Google │        │
│      └──────────────────────────┘        │
│                                          │
└──────────────────────────────────────────┘
```

**App shell (`/?playlist=<uuid>`):**
```
┌───────────────────────────────────────────────────────────┐
│ YouTube Summaries                        [ you@email ▾ ]   │  ← Header + AccountMenu
├───────────┬───────────────────────────────────────────────┤
│ PLAYLISTS │  ▸ ML Talks                                    │
│───────────│  ┌─────────────────────────────────────────┐  │
│ ▸ ML Talks│  │ FilterBar  [sort ▾] [min★] [☐ Archive] │  │
│   Cooking │  ├─────────────────────────────────────────┤  │
│   Rust    │  │ #  Title            [EN] USE DPT … OVR ☰│  │
│           │  │ 1  How LLMs train   [EN]  4   3  … 3.8 ☰│  │
│ + New     │  │ 2  Attention…       [KO]  5   4  … 4.2 ☰│  │
│ playlist  │  │ …                                       │  │
│           │  └─────────────────────────────────────────┘  │
└───────────┴───────────────────────────────────────────────┘
```

**Empty — no playlists yet:**
```
│ PLAYLISTS │   You have no playlists yet.                    │
│           │   Add one to get started.                       │
│ + New     │   [ + New playlist ]   (→ 2b)                    │
```

**Empty — playlist selected, no videos yet (ingest pending):**
```
│ ▸ ML Talks│   No videos here yet.                            │
│           │   Ingestion may still be running. (→ 2b/2c)      │
```

**Account menu (dropdown):**
```
[ you@email ▾ ]
   ┌───────────────┐
   │ you@email     │
   │───────────────│
   │ Sign out      │
   └───────────────┘
```

### 8.2 Design tokens
Formalize the current ad-hoc zinc dark theme (today: `--background:#09090b`, `--foreground:#fafafa`, components hardcode `zinc-900/800`, `blue/green/amber`) into semantic tokens in `app/globals.css` `@theme`. Components migrate hardcoded zinc classes to these over time; 2a introduces the tokens and uses them in all **new** cloud components.

| Token | Value (hex) | Tailwind ref | Use |
|---|---|---|---|
| `--surface-base` | `#09090b` | zinc-950 | app background |
| `--surface-raised` | `#18181b` | zinc-900 | sidebar, cards, rows |
| `--surface-overlay` | `#27272a` | zinc-800 | dropdowns, menus, hover |
| `--border` | `#27272a` | zinc-800 | default borders |
| `--border-strong` | `#3f3f46` | zinc-700 | focus/active borders |
| `--text-primary` | `#fafafa` | zinc-50 | headings, values |
| `--text-secondary` | `#a1a1aa` | zinc-400 | labels, captions |
| `--text-muted` | `#71717a` | zinc-500 | disabled, hints |
| `--accent` | `#3b82f6` | blue-500 | primary actions, active nav |
| `--success` | `#22c55e` | green-500 | done/positive |
| `--warning` | `#f59e0b` | amber-500 | pending/attention |
| `--danger` | `#ef4444` | red-500 | destructive, errors |

### 8.3 Component specs
- **Language badge** (`Badge`): `EN` → `--accent` bg; `KO` → `--warning` bg; uppercase, pill, `--text-primary`.
- **Rating pills** (USE/DPT/ORI/RCN/CMP/OVR): `--surface-overlay` bg, `--text-secondary` label, `--text-primary` value; OVR emphasized.
- **Archived row:** `--text-muted` + reduced opacity; only visible when Show-Archive is on.
- **Active sidebar item:** left border `--accent`, `--surface-overlay` bg, `--text-primary`.
- **Sort header:** active column shows a directional arrow and `--text-primary`; others `--text-secondary`.

---

## 9. URL Contracts

| Component | Link / action | Full URL (all params) |
|---|---|---|
| Login button | Start Google OAuth | `supabase.auth.signInWithOAuth({ provider:'google', options:{ redirectTo:'${origin}/auth/callback' } })` |
| OAuth return | Code exchange | `GET /auth/callback?code=<code>` (existing route) → sets session, redirects `/` |
| OAuth error | Failure landing | `GET /auth/auth-error` (existing) |
| PlaylistSidebar item | Select playlist | `GET /?playlist=<uuid>` (client nav; sets query param) |
| PlaylistSidebar "+ New playlist" | Stub (→ 2b) | `/?new=1` placeholder (opens a "coming in ingest" stub; no ingest in 2a) |
| AccountMenu "Sign out" | End session | `supabase.auth.signOut()` → client redirect `/login` |
| Sidebar data | List playlists | `GET /api/playlists` |
| Library data | List videos | `GET /api/videos?playlist=<uuid>&sortColumn=<col>&sortOrder=<asc\|desc>` |
| StarRating / note | Save annotation | `POST /api/videos/<id>/review` body `{ playlist:<uuid>, personalScore?:1..5\|null, personalNote?:string }` |
| VideoMenu Archive | Toggle archived | `POST /api/videos/<id>/archive` body `{ playlist:<uuid>, action:'archive'\|'unarchive' }` |
| VideoQuickView | Load preview | `GET /api/videos/<id>/quick-view?playlist=<uuid>` |

---

## 10. Overlay Dismissal

| Component | Mechanism | Expected result |
|---|---|---|
| AccountMenu dropdown | Click outside | Close menu, no action |
| AccountMenu dropdown | `Escape` | Close menu, no action |
| AccountMenu dropdown | Select "Sign out" | Sign out + redirect `/login` (menu closes) |
| VideoMenu (row ☰) | Click outside | Close (`onClose`), no action |
| VideoMenu (row ☰) | `Escape` | Close, no action |
| VideoMenu (row ☰) | Select an item | Run action + close |
| VideoQuickView | Toggle/collapse control | Collapse the inline preview |

*(2a introduces no full-screen modal. Archive is a direct toggle — no confirm dialog. Corrections/doc overlays are 2c.)*

---

## 11. Error handling

| Condition | Behavior |
|---|---|
| No session (cloud, app route) | Middleware → redirect `/login` |
| Session expires mid-use | API route → `401` → client clears + redirect `/login` |
| Playlist UUID unknown/foreign | Route → `404` (via `resolveOwnedPlaylistKey` null) |
| OAuth failure | `/auth/auth-error` |
| Empty library | Sidebar empty state (§8.1) |
| Playlist has no videos | Main-pane empty state (§8.1) |
| `/api/videos` in cloud without `playlist` | `400` "playlist is required" |
| Annotation validation (score/note bounds) | `400`, message (reuse existing local validation) |

---

## 12. Testing strategy

- **TDD** per `docs/dev-process.md`; per-task Claude + Codex dual review; §8 iterative review on **A1 (`updatedAt` schema/RPC)** and any RLS-touching route.
- **Phase A:** integration tests (real Supabase, `test:integration`) for A2–A7 cloud branches — auth 401, foreign-playlist 404, owner-scoped success, validation, and `updatedAt` bump-on-write. Cloud branches must not regress the local branches (existing tests stay green).
- **Phase B:** component tests (`@testing-library/react`) for `PlaylistSidebar`, `AccountMenu`, login page, and the retargeted library via the scope client (mock `lib/client/api.ts`). Migrate the ~20 existing component tests to the scope seam where they assert `outputFolder` URLs.
- **E2E (Playwright):** cloud flow — signed-in session fixture → list playlists → open playlist → sort/filter → rate → archive → Show-Archive. Migrate relevant existing specs; keep local specs.
- **Mocking boundaries** (`docs/dev-process.md`): Gemini/YouTube at lib boundary; E2E at route level.

---

## 13. Open items to confirm at plan time
- A1: `updatedAt` (ISO datetime, DB-stamped) vs `revision` int — recommended `updatedAt` (§7.1).
- Exact shell dispatch mechanism (`page.tsx` server component vs a route group) — decide in plan; both keep leaf components shared.
- Whether `listPlaylists` returns `videoCount` (extra join/RPC) in 2a or defers it — recommend defer (YAGNI) unless the sidebar needs it.

---

## 14. Dependencies & sequencing
- **Precedes:** 2b (ingest), 2c (doc lifecycle), 2d (share/downloads), Stage 3 (sync).
- **Requires (already merged):** cloud auth/session plumbing, RLS, `SupabaseMetadataStore`, `resolveOwnedPlaylistKey`, `getPrincipalFromSession`, the `playlists`/`videos` schema.
- **Local app:** untouched; must stay green throughout.
