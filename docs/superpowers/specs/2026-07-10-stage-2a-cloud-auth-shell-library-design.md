# Stage 2a — Cloud Auth, Shell & Library — Design Spec

**Status:** Draft **v4** — round-3 addressed (new High I1: `update_video_annotations` RPC security model pinned — SECURITY INVOKER + `auth.uid()` owner + UUID + SQL allowlist); awaiting round-4 spot re-review of the RPC
**Date:** 2026-07-10
**Sub-project:** 2 (Frontend), slice **2a** — first slice
**Depends on:** Sub-project 1 (backend) merged through Stage 1G (PR #10, `4d5b597`)
**Review trail:** `docs/reviews/spec-2a-{codex,claude}-v1.md`, `-v2-rereview.md`, `-v3-rereview.md`

---

## 1. Context & Product Vision

This app ships as **one codebase, two coexisting apps**, selected by the `STORAGE_BACKEND` env var:

- **Local app** — single user, filesystem storage (`outputFolder`, native folder picker, Obsidian vault links). **Already built. Stays. Not retired by this work.**
- **Cloud app** — multi-tenant, Supabase storage, auth-gated per owner (RLS isolation, per-owner cost guardrails, share tokens). **To be built** — Sub-project 2.

A future **Sync bridge** (Stage 3) lets a user **download** cloud→local and **upload** local→cloud (files, video metadata, and configuration), resolving conflicts by **newer-version-wins** per video. Sync is out of scope for 2a but shapes one data-model decision here (§7.1).

**Why the current UI needs this work:** the existing frontend is a complete, well-tested *local-desktop* app (~20 component tests, 10 Playwright specs, working SSE streams) built entirely on the local filesystem model. It has **no authentication UI** for signing in, no owner/playlist cloud model, and it never calls the cloud API routes.

Separately, Sub-project 1 was **never completed for the read/list surface**: the cloud migration built the write/generate/serve/share paths, but the library **read** routes (`/api/videos`, `/api/playlists/recent`) were left on the Stage-1C local path and throw in `supabase` mode. 2a closes that gap (Phase A) as a prerequisite for the library UI (Phase B).

---

## 2. Goal & Scope

**Goal:** A multi-tenant user can sign in with Google, see a sidebar of their playlists, open one, and browse/sort/filter/annotate its videos — all against Supabase, owner-isolated.

### In scope (2a)

**Phase A — Backend read layer (cloud branches; backend-first):**
- Surface the existing `videos.updated_at` column as `Video.updatedAt` + an ON UPDATE trigger (§7.1).
- `MetadataStore.listPlaylists(ownerId)` + Supabase impl (explicit owner filter).
- `GET /api/playlists` cloud route.
- Cloud branch on `GET /api/videos`.
- Cloud branch on `GET /api/videos/[id]/quick-view`.
- Cloud branch on `POST /api/videos/[id]/review` (rating/note writes **incl. clear**).
- Cloud branch on `POST /api/videos/[id]/archive` (archived flag, §7.2).

**Phase B — Cloud frontend:**
- Google-OAuth login page + session gating (**extend** the existing `middleware.ts`).
- Cloud app shell: header/account menu, playlist sidebar, main library pane.
- Scope-aware API client seam (§3.4) so shared leaf components work in both modes.
- Library: reuse presentational components retargeted to the cloud scope; list + sort + filter + quick-view + **annotate** (rate / note / archive).
- Empty states (no playlists; playlist with no videos yet).

### Out of scope (later slices)
- **2b** — Cloud ingest (playlist URL → `/api/jobs` queue → SSE progress). In 2a, "+ New playlist" is a **disabled affordance** (§5).
- **2c** — Doc lifecycle: generate/view magazine HTML, PDF, deep-dive; corrections; serve-budget/stale UX. In 2a the row-menu doc/PDF/deep-dive/corrections/Obsidian/Ask-Gemini items are **hidden** in cloud (§5).
- **2d** — Share tokens + downloads UI (+ decide Obsidian's fate in cloud).
- **Stage 3** — Sync.
- **Local app changes** — none. The local shell keeps its folder picker, path routes, and Obsidian links unchanged.
- **Share/anon routes** (`/s/*`, `/try`) — 2a must **not** change their middleware classification or break anonymous access (§3.2, §12). *(Note: `/s/*` currently falls through to `authenticated` in `classifyRoute`; whether anon share reaches it is a pre-existing concern outside 2a — 2a only guarantees not to regress it.)*

### Non-goals
- No password/magic-link/GitHub auth (Google OAuth only).
- No account self-service beyond sign-out (no profile edit, no delete-account) in 2a.
- No flat cross-playlist library view (nav is per-playlist, §3.3).

---

## 3. Architecture

### 3.1 Dual-mode shell dispatch
`STORAGE_BACKEND` is a server env, fixed per deployment. `app/page.tsx` becomes a **thin server component** that reads the mode (and, in cloud mode, the session) and renders one of two client shells:
- `local` → the existing client page, extracted into `components/local/LocalApp.tsx` (`'use client'`; no behavior change).
- `supabase` → the new `components/cloud/CloudApp.tsx` (`'use client'`).

**Acceptance criteria (client/server boundary):** `app/page.tsx` has **no `'use client'`**; it imports no client-only hooks; it passes only **serializable** props to the shells (e.g. `{ mode, session: { userId, email } | null }`); it does not import server-only Supabase modules (`lib/supabase/server.ts`, `service.ts`) into any client component. The `'use client'` boundary lives in `LocalApp`/`CloudApp`. Leaf presentational components are shared by both shells.

**Server session read is READ-ONLY (N2).** `app/page.tsx` (an RSC) must read the session **without** mutating cookies: the middleware already refreshed the session on the same request, so the page calls `getUser()` through a server client whose cookie `setAll` is a **no-op / try-catch** (Next.js forbids cookie writes during RSC render — reusing the route-handler `createServerSupabase` factory unguarded would throw a 500 on a token-refresh write). Do not reuse the route factory here; use a read-only page-scoped client.

### 3.2 Auth & session gating (cloud only) — **extend the existing `middleware.ts`**
There is already a merged `middleware.ts` (Stage 1F-b) with a `public` / `anon-allowed` / `authenticated` model in `lib/supabase/route-categories.ts`. It refreshes the session, auto-provisions **anonymous** sessions for `anon-allowed` routes (`/try`), returns **JSON 401** for unauth `/api/*`, and redirects unauth `authenticated` **page** routes to `/`. It is **not** env-guarded and unconditionally calls `getSupabaseEnv()` (throws on missing vars). 2a **modifies** this file — it does not create a new one. Required edits:

1. **Local-mode short-circuit (first line, before any env read):**
   `if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase') return NextResponse.next({ request });`
   → local deployments need no Supabase env and never 500 in middleware.
2. **Make `/login` public:** add `'/login'` to `PUBLIC_EXACT` in `route-categories.ts`.
3. **Gate `/` in cloud mode:** in the cloud path, treat `pathname === '/'` as `authenticated` (a middleware-level override; do **not** remove `/` from `PUBLIC_EXACT`, which local relies on). Unauth `/` → redirect `/login`; authed `/` → render `CloudApp`. *(N5: an anonymous session minted by the anon-provision path counts as "authed" for this gate and renders `CloudApp` at `/` with an empty library — `listPlaylists(anonId)` returns nothing, no data leak. Accepted, matching the existing "anon counts as user" pattern; documented rather than special-cased.)*
4. **Redirect target for unauth `authenticated` *page* routes = `/login`** (was `/`). The existing `/api/*` → **JSON 401** branch is unchanged (client fetches must keep getting 401, never a 302).
5. **Authed user on `/login` → redirect `/`.**
6. **Preserve** the anon-provision branch and `anon-allowed` handling verbatim; do not touch `/try` or `/s/*` classification.

- **Provider:** Supabase Google OAuth via the existing browser factory `lib/supabase/client.ts` `createClient()`.
- **Login (`/login`):** "Continue with Google" → `supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: '${origin}/auth/callback?next=/' } })`.
- **Callback:** the existing `app/auth/callback/route.ts` exchanges the code. **Bug to fix:** it currently defaults `next` to `/library`, which does not exist → change the default to `/` (and login passes `?next=/` explicitly). On failure → existing `/auth/auth-error`.
- **Sign-out:** account menu → `supabase.auth.signOut()` → redirect `/login`.

### 3.3 URL / navigation model
- Single-page shell; active playlist is a **query param**: `/?playlist=<uuid>`.
- `/` with no param → library home (sidebar + "pick a playlist" empty pane).
- Playlist identity in the URL is the **playlist UUID** (`playlists.id`). The UUID is resolved to `playlist_key` server-side via `resolveOwnedPlaylistKey` (`lib/storage/serve-playlist.ts`), which asserts `owner_id === auth.uid()` and returns null for unknown/foreign (→ route 404).

### 3.4 Scope-aware API client (the key seam)
New module `lib/client/api.ts` (browser) centralizes request construction from the **current scope**, provided via a `ScopeProvider` React context at the shell level:
- Local scope = `{ mode: 'local', outputFolder, baseOutputFolder }`.
- Cloud scope = `{ mode: 'cloud', playlistId: <uuid> }`.

It exposes typed calls the components use instead of building URLs inline: `listPlaylists()`, `listVideos(scope, sort)`, `getQuickView(scope, videoId)`, `saveAnnotation(scope, videoId, patch)`, `setArchived(scope, videoId, archived)`. Cloud calls send `?playlist=<uuid>` (or `{ playlist }` in the body); local calls send `outputFolder`.

**Acceptance criteria (wrong-scope rejection — mirrors the exemplar `app/api/html/[id]/route.ts`):** the client **throws before fetch** on a missing or wrong-mode scope field (cloud call without `playlistId`, local call without `outputFolder`). Server-side, **every dual route rejects the wrong-mode param** (cloud branch 400 on `outputFolder`; local branch 400 on `playlist`). Leaf components (`StarRating`, `NoteCell`, `VideoQuickView` — all of which currently build URLs inline) are refactored to call the client via context; a test asserts **no component emits a raw `outputFolder` request in cloud mode**.

---

## 4. Phase A — Backend read layer

All cloud branches follow the `serveLocal` / `serveCloud` pattern from `app/api/html/[id]/route.ts`: dispatch on `STORAGE_BACKEND`; cloud branch uses `createServerSupabase(cookies)` → `auth.getUser()` (401) → `resolveOwnedPlaylistKey(sessionClient, playlistId, user.id)` (404 if null) → `getPrincipalFromSession({ userId }, playlistKey)` → `getStorageBundle({ supabaseClient })`. **Session client only** — service-role clients are never accepted by these user-facing read/write stores (see §7.3). Local branch unchanged.

| # | Item | File(s) | Notes |
|---|---|---|---|
| A1 | `updatedAt` surfaced + ON UPDATE trigger | `types/index.ts`, new migration, `supabase-metadata-store.ts`, `local-metadata-store.ts` | §7.1 — schema section; §8 iterative dual review |
| A2 | `listPlaylists(ownerId)` | `metadata-store.ts` (interface), `supabase-metadata-store.ts`, `local-metadata-store.ts` | Supabase: `.from('playlists').select('id, playlist_key, playlist_url, playlist_title, created_at').eq('owner_id', ownerId).order('playlist_title', {nullsFirst:false}).order('created_at')` on **session** client (explicit owner filter, RLS also scopes). **Select must include `created_at`** (N4) — it is both ordered-by and returned. Blank title → display fallback to `playlist_url` host or "Untitled playlist". Local: wrap existing `listRecentPlaylists`. Returns `{ id, playlistKey, playlistUrl, playlistTitle, createdAt }[]`. `videoCount` deferred (YAGNI). |
| A3 | `GET /api/playlists` | `app/api/playlists/route.ts` (new) | Cloud: auth + `listPlaylists(user.id)`. Local: `?root=<path>` → existing recent-provider. |
| A4 | `GET /api/videos` cloud branch | `app/api/videos/route.ts` | Refactor to serveLocal/serveCloud. Cloud: `?playlist=<uuid>` → `readIndex` → reuse `sortVideos`. **Skip** `recoverOrphanedVideos` (filesystem). Validate `sortColumn` (existing whitelist) **and** `sortOrder ∈ {asc,desc}` (default `asc`). Reject `outputFolder` param in cloud (400). |
| A5 | `GET /api/videos/[id]/quick-view` cloud branch | `app/api/videos/[id]/quick-view/route.ts` | Cloud: `?playlist=<uuid>` → `readIndex` → the one video's `{ tldr, takeaways, tags }`. **Match the local availability gate: 404 unless `video.summaryMd && video.tldr`** (parity with `quick-view route:27`). |
| A6 | `POST /api/videos/[id]/review` cloud branch (incl. clear) | route + **new** `update_video_annotations` RPC | Cloud: body `{ playlist:<uuid>, personalScore?, personalNote? }`. Same validation as local. **Do NOT overload the shared `merge_video_data` RPC (N1):** it is used by pipeline/serve callers that legitimately write JSON `null` meaning *set-null* (e.g. `app/api/videos/[id]/regenerate/route.ts:71` `summaryHtml:null`; `lib/storage/supabase/consistency.ts`, `lib/html-doc/generate.ts`) and must keep that semantics; making it delete-on-null or raise-on-0-rows would silently regress every caller. Instead add a **dedicated** `update_video_annotations(p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[])` RPC with the **established safe write model (I1) — `SECURITY INVOKER SET search_path = public`** (matching every `0007` write RPC, e.g. `0007:26,56,85,107`), so `videos` RLS filters the UPDATE regardless of args. It is **UUID-addressed, never `playlist_key`** (unique only per-owner — `resolve.ts:66`); the owner is derived **inside** the function from `auth.uid()` and guarded `where owner_id = auth.uid() and playlist_id = p_playlist_id and video_id = p_video_id` (**no client-suppliable `p_owner`**). The route/store resolve the playlist UUID under the session client exactly as the existing merge path does (`requirePlaylistId`). It applies `data = (data || p_set) - p_clear` with `p_set`/`p_clear` **sliced in SQL to the annotation-key allowlist** `{personalScore, personalNote, archived}` (defense-in-depth, I2), and **always issues the UPDATE even if the sliced payload is empty** (so `row_count` reflects row existence, not payload emptiness — I3), returning affected `row_count`. Set writes go in `p_set`; a `null` score / `""` note goes in `p_clear` (removes the key). **Missing/foreign-video → 404 (H3):** `row_count = 0` → typed not-found → route 404 (parity with local `review route:63`). `merge_video_data` is left unchanged. |
| A7 | `POST /api/videos/[id]/archive` cloud branch | route + `update_video_annotations` RPC | Cloud: body `{ playlist:<uuid>, action:'archive'\|'unarchive' }` → `update_video_annotations(p_playlist_id, videoId, p_set:{archived:true\|false}, p_clear:[])` (§7.2). Same `SECURITY INVOKER` + `auth.uid()` owner guard + UUID addressing as A6. Missing/foreign-video → 404 via the same `row_count` path. |

**Auth/session/RLS infrastructure already exists** (`lib/supabase/{server,client,service}.ts`, RLS `owner_id = auth.uid()`); no new infra.

---

## 5. Phase B — Cloud frontend

| Component | New/Reuse/Retire | Responsibility (2a) |
|---|---|---|
| `app/page.tsx` | Rework → thin **server** dispatch (§3.1) | Read mode + session; render `LocalApp` or `CloudApp` with serializable props. |
| `middleware.ts` | **Modify existing** (§3.2) | Local no-op short-circuit; `/login` public; cloud `/` gated; unauth pages → `/login`; keep anon-provision + `/api` 401. |
| `lib/supabase/route-categories.ts` | Modify | Add `/login` to `PUBLIC_EXACT`. Do not alter `/`, `/auth`, `/try`, `/s`. |
| `app/auth/callback/route.ts` | Fix | Default `next` `/library` → `/`. |
| `app/login/page.tsx` | New | "Continue with Google" (`signInWithOAuth`, `redirectTo=…/auth/callback?next=/`). |
| `components/cloud/CloudApp.tsx` | New (`'use client'`) | Cloud shell: `ScopeProvider`, header/account menu, sidebar, library pane. |
| `components/cloud/PlaylistSidebar.tsx` | New | Fetch `/api/playlists`; list; active from `?playlist`; "+ New playlist" **disabled** affordance (§ below). |
| `components/cloud/AccountMenu.tsx` | New | Email + Sign out (dropdown). |
| `components/local/LocalApp.tsx` | Extract from current `page.tsx` (`'use client'`) | Local shell, unchanged behavior. |
| `lib/client/api.ts` + `ScopeProvider` | New | Scope-aware data-access seam (§3.4). |
| `VideoList`, `VideoRow`, `FilterBar`, `StarRating`, `NoteCell`, `Badge`, `VideoQuickView` | Reuse (retarget data calls to the client seam) | List/sort/filter/quick-view/annotate. Markup unchanged; inline `fetch`/`outputFolder` URL-building moves into the client. |
| `VideoMenu` | Reuse, **cloud item allowlist** | Cloud 2a menu shows **only**: "Open on YouTube" + "Archive/Unarchive". Hidden in cloud: Obsidian, Ask Gemini, View/Generate HTML, Resummarize, View/Save PDF, Corrections (all → 2b/2c). Rating/note stay inline (StarRating/NoteCell), not in the menu. |
| `Header` (folder picker), `PlaylistPicker`, `ChannelPlaylistPanel`, obsidian-path logic | Local-only (not used by `CloudApp`) | Untouched; local shell keeps them. |

**"+ New playlist" (2a stub):** a **disabled** button with tooltip "Adding playlists comes with ingest (2b)." It performs no navigation and **calls no ingest route** (asserted by test). No `/?new=1` URL, no overlay.

**Library behaviors in 2a:** sort (existing `SortColumn`s, `sortOrder` whitelisted), filter (`FilterBar`), Show-Archive toggle (archived rows greyed), quick-view expand, rate (`StarRating`), personal note (`NoteCell`), archive/unarchive, **clear rating/note**. **Excluded:** generate/view HTML·PDF·deep-dive, corrections, re-ingest, share.

---

## 6. Data flow (cloud)

```
Google OAuth → /auth/callback?next=/ (session cookie) → middleware admits /
  → CloudApp mounts, ScopeProvider(mode=cloud)
  → PlaylistSidebar: GET /api/playlists            → render playlists
  → user clicks a playlist → URL ?playlist=<uuid>
  → Library: GET /api/videos?playlist=<uuid>&sortColumn=&sortOrder=  → render VideoList
  → rate/clear:  POST /api/videos/[id]/review  { playlist:<uuid>, personalScore:1..5|null }
  → note/clear:  POST /api/videos/[id]/review  { playlist:<uuid>, personalNote:string|"" }
  → archive:     POST /api/videos/[id]/archive { playlist:<uuid>, action }
  → quickview:   GET  /api/videos/[id]/quick-view?playlist=<uuid>   (404 if no summary)
```

---

## 7. Data-model & schema decisions

### 7.1 Versioning signals for Sync's newer-wins — schema change, iterative dual review

Sync (Stage 3) decides "which copy of a video is newer" per video via a **whole-record** comparator. Two signals:

- **`docVersion {major, minor}`** — doc-format / generator version. **Already exists.** Stamped on (re)generation + HTML render (`lib/pipeline.ts:266`, `summary-handler.ts:162`, `html-doc/ensure.ts:66`); not touched by rating/note edits. Higher = newer document. (Absent ⇒ `{1,0}`.)
- **`Video.updatedAt` (ISO-8601)** — whole-record last-write time. **Sourced from the existing relational `videos.updated_at` column** (`0001_core_schema.sql:29`), which the write RPCs already bump (`merge_video_data` `0007:94`, `_bulk` `0007:117`, `reconcile_membership` `0007:61,68`, `persist_summary` `0009:152`). 2a makes it authoritative and visible:
  - **New migration:** add an `ON UPDATE` trigger to `videos` that sets `updated_at = now()` on every row update — closing the gap where `SupabaseMetadataStore.upsertVideo` (a direct `.update({data})`, `supabase-metadata-store.ts:83`) does **not** bump it and no trigger exists.
  - **`readIndex` surfaces it:** select `updated_at` and map it into the returned `Video.updatedAt` (today `readIndex` selects only `data`, `supabase-metadata-store.ts:22`). Add `updatedAt?: string` to `VideoSchema`.
  - **Cloud writes ignore client-supplied `updatedAt`** (strip it from write payloads); the DB column/trigger is the single source of truth. *(N6, for 2b: the whole-record writer `SupabaseMetadataStore.upsertVideo` does `.update({ data: video })` and would round-trip a surfaced `updatedAt` back into `data` jsonb — harmless in 2a since the column wins on read, but 2b must drop `updatedAt` from `data` before that write.)*
  - **Local store:** stamp `data.updatedAt = new Date().toISOString()` **per-video, inside `updateVideoFields`/`upsertVideo` only** — **never** at the `writeIndex` whole-file level (N3): `index-store.writeIndex` rewrites the entire playlist file, so stamping there would re-stamp *every* video on any single edit and destroy the per-video newer-wins signal. Surfaced uniformly as `Video.updatedAt`.

**Comparator (Stage 3), lexicographic — `docVersion` primary, `updatedAt` tiebreak:** higher `docVersion` wins; if equal, more recent `updatedAt` wins. Cases: same-doc edit → same `docVersion`, newer `updatedAt` → edit wins; regen with a newer generator → higher `docVersion` wins; regen with an *older* generator recently → lower `docVersion` loses despite newer `updatedAt`.

**Scope decision (was ambiguous; now committed):** **whole-record newer-wins only.** The earlier "field-partitioned merge (annotations by `updatedAt`)" option is **dropped** — it is unsound with a single whole-record clock, because generation and membership writes (`persist_summary`, `reconcile_membership`) bump `updated_at` while preserving annotations, so `updatedAt` cannot serve as a clean *annotation-recency* signal. A future field-partitioned merge would require a **separate per-field annotation clock**; that is explicitly out of scope and noted for Stage 3, not assumed. `docVersion` + `updatedAt` are sufficient for the whole-record comparator.

Terminology: **`videos.updated_at`** = the DB column (authoritative source, cloud). **`Video.updatedAt`** = the model field surfaced from it (cloud) or stamped in `data` (local). They are the same logical value, one per layer.

Touches write RPCs / a trigger / both stores → §8 iterative dual-review (`docs/dev-process.md`).

### 7.2 Archive = `data.archived` flag (not membership) — with a Sync note
The cloud archive flips the **`archived` boolean** on `Video` via the dedicated `update_video_annotations` RPC (§4 A7) — distinct from `reconcile_membership` (YouTube-playlist membership) and from the shared `merge_video_data`. **Local vs cloud divergence (Sync hazard, Stage 3):** local archive also **moves files** to `archived/` and clears cached HTML (`lib/archive.ts:99-108`); cloud archive is a pure state flag. Recorded now so Stage 3's Sync: (a) treats `archived` as an annotation/state flag, not a doc-content version; (b) when applying a cloud `archived` change to local, performs the corresponding file move **and** invalidates local cached HTML; (c) does **not** let the archive write's `updatedAt` bump decide doc-artifact freshness. 2a implements only the cloud flag flip; the Sync reconciliation is Stage 3.

### 7.3 Service-role never on user-facing read/write stores
`listPlaylists`, `readIndex`-backed reads, and the review/archive writes run on the **session** client only (RLS-scoped, `owner_id = auth.uid()`), with `resolveOwnedPlaylistKey` asserting ownership. Rationale: `playlist_key` is unique only **per owner** (`resolve.ts:66` warns service-role workers must resolve by UUID). Passing a service client to `SupabaseMetadataStore` for these paths would bypass RLS and could cross owners on a colliding `playlist_key`. Acceptance: documented invariant + a cross-owner-denial test per route (§12).

---

## 8. UI Design

### 8.1 Wireframes

**Login (`/login`):**
```
┌──────────────────────────────────────────┐
│            YouTube Summaries             │
│         Your playlist library,           │
│              in the cloud                │
│      ┌──────────────────────────┐        │
│      │  ⟳  Continue with Google │        │
│      └──────────────────────────┘        │
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
│ (disabled)│  │ …                                       │  │
│           │  └─────────────────────────────────────────┘  │
└───────────┴───────────────────────────────────────────────┘
```

**Empty — no playlists yet:**
```
│ PLAYLISTS │   You have no playlists yet.                    │
│           │   Adding playlists comes with ingest (2b).      │
│ + New     │   [ + New playlist ] (disabled, tooltip)        │
```

**Empty — playlist selected, no videos yet:**
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
Formalize the current ad-hoc zinc dark theme (`--background:#09090b`, `--foreground:#fafafa`; components hardcode `zinc-900/800`, `blue/green/amber`) into semantic tokens in `app/globals.css` `@theme`. 2a introduces the tokens and uses them in all **new** cloud components.

| Token | Value | Tailwind ref | Use |
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
- **Language badge** (`Badge`): `EN` → `--accent` bg; `KO` → `--warning` bg; uppercase pill, `--text-primary`.
- **Rating pills** (USE/DPT/ORI/RCN/CMP/OVR): `--surface-overlay` bg, `--text-secondary` label, `--text-primary` value; OVR emphasized.
- **Archived row:** `--text-muted` + reduced opacity; visible only when Show-Archive is on.
- **Active sidebar item:** left border `--accent`, `--surface-overlay` bg, `--text-primary`.
- **Disabled "+ New playlist":** `--text-muted`, `cursor-not-allowed`, tooltip.

---

## 9. URL Contracts

| Component | Link / action | Full URL (all params) |
|---|---|---|
| Login button | Start Google OAuth | `signInWithOAuth({ provider:'google', options:{ redirectTo:'${origin}/auth/callback?next=/' } })` |
| OAuth return | Code exchange | `GET /auth/callback?code=<code>&next=/` → session, redirect to `next` (default `/`) |
| OAuth error | Failure landing | `GET /auth/auth-error` |
| PlaylistSidebar item | Select playlist | client nav → `/?playlist=<uuid>` |
| PlaylistSidebar "+ New" | Disabled | no navigation, no request |
| AccountMenu "Sign out" | End session | `supabase.auth.signOut()` → redirect `/login` |
| Sidebar data | List playlists | `GET /api/playlists` |
| Library data | List videos | `GET /api/videos?playlist=<uuid>&sortColumn=<col>&sortOrder=<asc\|desc>` |
| StarRating / NoteCell | Save/clear annotation | `POST /api/videos/<id>/review` body `{ playlist:<uuid>, personalScore?:1..5\|null, personalNote?:string }` (null/`""` clears) |
| VideoMenu Archive | Toggle archived | `POST /api/videos/<id>/archive` body `{ playlist:<uuid>, action:'archive'\|'unarchive' }` |
| VideoQuickView | Load preview | `GET /api/videos/<id>/quick-view?playlist=<uuid>` (404 if no summary) |

---

## 10. Overlay Dismissal

| Component | Mechanism | Expected result |
|---|---|---|
| AccountMenu dropdown | Click outside | Close, no action |
| AccountMenu dropdown | `Escape` | Close, no action |
| AccountMenu dropdown | Select "Sign out" | Sign out + redirect `/login` (menu closes) |
| VideoMenu (row ☰) | Click outside | Close (`onClose`), no action |
| VideoMenu (row ☰) | `Escape` | Close, no action |
| VideoMenu (row ☰) | Select an item | Run action + close |
| VideoQuickView | Toggle/collapse control | Collapse the inline preview |

*(2a introduces no full-screen modal. Archive is a direct toggle — no confirm dialog. "+ New" is disabled — no overlay.)*

---

## 11. Error handling

| Condition | Behavior |
|---|---|
| No session, cloud **page** route | Middleware → redirect `/login` |
| No session / expired, cloud `/api/*` | Middleware → JSON `401`; client clears + redirects `/login` |
| Playlist UUID unknown/foreign | Route → `404` (`resolveOwnedPlaylistKey` null) |
| Video id not in playlist | Route → `404` (RPC row_count 0 → typed not-found) |
| OAuth failure / no code | `/auth/auth-error` |
| Empty library | Sidebar empty state (§8.1) |
| Playlist has no videos | Main-pane empty state (§8.1) |
| Quick-view for un-summarized video | `404` (parity with local) |
| `/api/videos` cloud without `playlist` (or with `outputFolder`) | `400` |
| Annotation validation (score/note bounds) | `400` (reuse local validation) |
| Local mode, any route | Middleware no-op; no auth |

---

## 12. Testing strategy

- **TDD** per `docs/dev-process.md`; per-task Claude + Codex dual review; **§8 iterative review on A1 (`updatedAt` trigger/RPC/schema)** and every RLS-touching route.
- **Phase A integration (real Supabase):** for A2–A7 — 401 unauth; **cross-owner denial per route** (owner B with a valid UUID owned by A → 404, not just unknown UUID); owner-scoped success; validation; **clear rating/note in cloud** removes the key via the dedicated `update_video_annotations` RPC; **missing-video → 404**; **quick-view availability gate**; `sortOrder` whitelist; `updatedAt` present on reads and **bumped by the trigger on every write path** (incl. `upsertVideo`); wrong-mode param rejected (cloud rejects `outputFolder`, local rejects `playlist`). **Shared-RPC regression (N1):** assert existing `merge_video_data` callers that write JSON `null` as set-null (`regenerate/route.ts:71` `summaryHtml:null`; `consistency.ts`; `generate.ts`) still store `null` (key present, not deleted) — `merge_video_data` is unchanged. Cloud branches must not regress local branches.
- **Auth/middleware:** local-mode middleware **no-op** (no Supabase env needed, no 500); unauth `/login` **renders** (not redirected); authed `/login` → `/`; unauth cloud page → `/login`; unauth cloud `/api/*` → JSON 401; **OAuth callback `next=/`** lands on `/` (not `/library`); **anon `/try` still reachable** and **`/s/*` classification unchanged** by the `/login` `PUBLIC_EXACT` edit (2a neither alters nor tests `/s/*` gating — pre-existing, out of scope §2).
- **Phase B components (`@testing-library/react`):** `PlaylistSidebar` (list, active state, disabled "+ New" makes no request, blank-title fallback), `AccountMenu` (sign-out + dismissal paths), login page; retargeted library via a mocked `lib/client/api.ts`; **no component emits a raw `outputFolder` request in cloud mode**. Migrate the ~20 existing component tests to the scope seam where they assert `outputFolder` URLs.
- **E2E (Playwright):** cloud flow — signed-in session fixture → list playlists → open playlist → sort/filter → rate → clear rating → archive → Show-Archive. Migrate relevant existing specs; keep local specs green.
- **Local test churn (L1):** local metadata-store / `index-store` JSON assertions must use field matchers, **not exact snapshots**, to tolerate the dynamic `data.updatedAt` now stamped per-video.
- **Mocking boundaries:** Gemini/YouTube at lib boundary; E2E at route level.

---

## 13. Open items to confirm at plan time
- A6/A7 use a **dedicated `update_video_annotations` RPC** (N1); the shared `merge_video_data` is left unchanged (it has callers writing JSON `null` as set-null). **Security model is pinned (I1), not deferred: `SECURITY INVOKER SET search_path = public`, owner derived from `auth.uid()` (no client `p_owner`), UUID-addressed (`p_playlist_id`), annotation-key allowlist enforced in SQL.** (`SECURITY DEFINER` is explicitly rejected here — under definer a spoofable owner arg is a cross-tenant write.) Plan detail: the exact SQL body + the empty-payload-still-UPDATEs guard (I3).
- A1 trigger vs. explicit per-RPC stamping: recommend the **ON UPDATE trigger** (catches every path, incl. `upsertVideo`); confirm no RPC relies on setting `updated_at` to a non-`now()` value.
- `listPlaylists` `videoCount`: deferred (YAGNI) unless the sidebar design later needs it.

---

## 14. Dependencies & sequencing
- **Precedes:** 2b (ingest), 2c (doc lifecycle), 2d (share/downloads), Stage 3 (sync).
- **Requires (already merged):** cloud auth/session plumbing, RLS, `SupabaseMetadataStore`, `resolveOwnedPlaylistKey`, `getPrincipalFromSession`, the existing `middleware.ts` + `route-categories.ts`, the `playlists`/`videos` schema (incl. `videos.updated_at`).
- **Local app:** untouched; must stay green throughout.
- **Must not regress:** anonymous share (`/s/*`) and `/try` access; the existing middleware anon-provision path.
