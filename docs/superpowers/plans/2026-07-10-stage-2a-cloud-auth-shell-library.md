# Stage 2a — Cloud Auth, Shell & Library — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A multi-tenant user signs in with Google, sees a sidebar of their playlists, opens one, and browses/sorts/filters/annotates its videos against Supabase — while the local filesystem app keeps working unchanged.

**Architecture:** Dual-mode (`STORAGE_BACKEND` local|supabase). Phase A finishes the cloud *read/write* API layer (owner-scoped list/read routes + a dedicated annotation RPC) left on the local path by Sub-project 1; Phase B builds the cloud auth + shell + library UI, sharing the existing presentational components via a scope-aware API client. All cloud routes follow the merged `serveLocal`/`serveCloud` dual-branch pattern.

**Tech Stack:** Next.js App Router, TypeScript, Supabase (`@supabase/ssr`, Postgres RLS), Tailwind v4, Jest + ts-jest, @testing-library/react, Playwright.

**Spec:** `docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md` (CONVERGED). Read it first.

## Global Constraints

- **Session client only** for user-facing read/write stores (`listPlaylists`, `readIndex` reads, review/archive writes); RLS `owner_id = auth.uid()`. Service-role never on these paths.
- **`merge_video_data` is LEFT UNCHANGED** — it has callers that write JSON `null` as *set-null* (`app/api/videos/[id]/regenerate/route.ts:71`). Annotation writes use a **new dedicated `update_video_annotations` RPC**.
- **`update_video_annotations`:** `SECURITY INVOKER SET search_path = public`; owner from `auth.uid()` (no client `p_owner`); UUID-addressed `p_playlist_id`; annotation-key allowlist `{personalScore, personalNote, archived}` enforced in SQL; always issues the UPDATE (empty payload still matches → `row_count` = row existence); `row_count = 0` → route 404.
- **Versioning:** whole-record newer-wins; comparator `docVersion` primary, `updatedAt` tiebreak. `updatedAt` sourced from the existing `videos.updated_at` column (cloud) via an ON UPDATE trigger, surfaced into `Video.updatedAt` on read; stamped per-video in the local store (never at `writeIndex`).
- **Local app UNTOUCHED and must stay green** — every cloud change is an additive `serveCloud` branch; existing local tests must keep passing.
- **Middleware is EXTENDED, not replaced.** Local-mode short-circuit before any Supabase env read; `/login` public; cloud `/` gated → `/login`; preserve anon-provision + `/api/*` JSON 401.
- **Wrong-scope rejection:** cloud routes 400 on `outputFolder`; local routes 400 on `playlist`; client seam throws before fetch on missing/wrong-mode scope.
- **Trailers on every commit:** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01JEDFvzMp4257ao7qtZM7Px`.
- **§8 iterative dual review** applies to T1 (trigger/schema) and T7 (RPC/RLS).

---

## File Structure

**Phase A (backend):**
- `supabase/migrations/00NN_video_updated_at_trigger.sql` — NEW: ON UPDATE trigger on `videos`.
- `supabase/migrations/00NN_update_video_annotations.sql` — NEW: the annotation RPC.
- `types/index.ts` — add `updatedAt?` to `VideoSchema`.
- `lib/storage/metadata-store.ts` — add `listPlaylists` + `updateVideoAnnotations` to the interface.
- `lib/storage/supabase/supabase-metadata-store.ts` — impl both; surface `updated_at` in `readIndex`.
- `lib/storage/local/local-metadata-store.ts` + `lib/index-store.ts` — impl `listPlaylists`; per-video `updatedAt` stamp; `updateVideoAnnotations` (local set/clear).
- `app/api/playlists/route.ts` — NEW cloud list route.
- `app/api/videos/route.ts`, `.../[id]/quick-view/route.ts`, `.../[id]/review/route.ts`, `.../[id]/archive/route.ts` — add `serveCloud` branches.

**Phase B (frontend):**
- `middleware.ts`, `lib/supabase/route-categories.ts`, `app/auth/callback/route.ts` — auth gating.
- `lib/supabase/page-session.ts` — NEW read-only RSC session helper.
- `app/login/page.tsx` — NEW.
- `lib/client/api.ts`, `lib/client/scope.tsx` — NEW scope-aware client + `ScopeProvider`.
- `app/page.tsx` — thin server dispatch.
- `components/local/LocalApp.tsx` — extracted from current `app/page.tsx`.
- `components/cloud/CloudApp.tsx`, `PlaylistSidebar.tsx`, `AccountMenu.tsx` — NEW.
- `components/{StarRating,NoteCell,VideoQuickView,VideoList,VideoMenu}.tsx` — retarget to the client seam.
- `app/globals.css` — design tokens.

**Migration numbering:** run `ls supabase/migrations/ | tail -1` to get the next `00NN`. Current tip is `0014`; T1 = `0015`, T7 = `0016` (confirm at task start).

---

## PHASE A — Backend read/write layer

### Task 1: `updatedAt` — trigger + schema + cloud read surface (§8 iterative review)

**Files:**
- Create: `supabase/migrations/0015_video_updated_at_trigger.sql`
- Modify: `types/index.ts` (VideoSchema)
- Modify: `lib/storage/supabase/supabase-metadata-store.ts` (`readIndex`)
- Test: `tests/integration/video-updated-at.test.ts`, `tests/lib/types.test.ts`

**Interfaces:**
- Produces: `Video.updatedAt?: string` (ISO datetime); `readIndex` returns each video with `updatedAt` populated from the DB column.

- [ ] **Step 1: Write the failing migration test.** In `tests/integration/video-updated-at.test.ts`: after a `merge_video_data` write AND a direct `.update({data})` (upsertVideo path) to a video row, assert `updated_at` advanced both times; and that `readIndex` returns `video.updatedAt` equal to the row's `updated_at` (ISO). Use the admin client to seed a playlist+video, capture `updated_at`, wait, write, re-read.

```ts
// tests/integration/video-updated-at.test.ts (essence)
const before = (await svc.from('videos').select('updated_at').eq('video_id', vid).single()).data!.updated_at;
await svc.from('videos').update({ data: { ...video, title: 'x' } }).eq('video_id', vid); // upsert path, no explicit updated_at
const after = (await svc.from('videos').select('updated_at').eq('video_id', vid).single()).data!.updated_at;
expect(new Date(after).getTime()).toBeGreaterThan(new Date(before).getTime()); // trigger fired
```

- [ ] **Step 2: Run → FAIL** (`npm run test:integration -- --runInBand video-updated-at`). Expected: `after` == `before` (no trigger yet).

- [ ] **Step 3: Write the migration.**

```sql
-- 0015_video_updated_at_trigger.sql
create or replace function set_videos_updated_at() returns trigger
  language plpgsql set search_path = public as $$
begin new.updated_at = now(); return new; end $$;

drop trigger if exists trg_videos_updated_at on videos;
create trigger trg_videos_updated_at
  before update on videos
  for each row execute function set_videos_updated_at();
```

- [ ] **Step 4: Surface the column in `readIndex`.** In `supabase-metadata-store.ts` `readIndex`, change the videos select from `.select('data')` to `.select('data, updated_at')` and map: `{ ...(r.data as Video), updatedAt: r.updated_at }`. Add `updatedAt: z.string().datetime().optional()` to `VideoSchema` in `types/index.ts`.

- [ ] **Step 5: Run migration test + a `tests/lib/types.test.ts` case** asserting `VideoSchema.parse({...valid, updatedAt: '2026-07-10T00:00:00Z'})` succeeds and that `updatedAt` is optional (absent parses). `npx supabase db reset && npm run test:integration -- --runInBand video-updated-at` → PASS.

- [ ] **Step 6: Full suite** — `npx tsc --noEmit`; `npm test`; `npm run test:integration -- --runInBand`. Confirm no regression (the trigger is idempotent with RPCs that also set `updated_at = now()`).

- [ ] **Step 7: Commit** `feat(2a): videos.updated_at ON UPDATE trigger + Video.updatedAt surfaced`.

### Task 2: Local per-video `updatedAt` stamp

**Files:**
- Modify: `lib/index-store.ts` (`updateVideoFields`, `upsertVideo`)
- Test: `tests/lib/index-store-updated-at.test.ts`

- [ ] **Step 1: Failing test** — after `indexStore.updateVideoFields(key, id, {personalScore: 4})`, the touched video has an ISO `updatedAt`; a *sibling* video in the same index is **unchanged** (no re-stamp). This pins N3 (never stamp at `writeIndex`).
- [ ] **Step 2: Run → FAIL** (`npx jest index-store-updated-at`).
- [ ] **Step 3: Implement** — in `lib/index-store.ts` `updateVideoFields` and `upsertVideo`, set `updatedAt: new Date().toISOString()` on the single mutated video record before persisting. Do **not** touch `writeIndex`.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Full suite** — fix any local-store snapshot tests to use field matchers, not exact JSON (L1). `npm test`.
- [ ] **Step 6: Commit** `feat(2a): local per-video updatedAt stamp`.

### Task 3: `listPlaylists(ownerId)` store method

**Files:**
- Modify: `lib/storage/metadata-store.ts` (interface), `supabase-metadata-store.ts`, `local-metadata-store.ts`
- Test: `tests/integration/list-playlists.test.ts`, `tests/lib/local-list-playlists.test.ts`

**Interfaces:**
- Produces: `listPlaylists(ownerId: string): Promise<PlaylistSummary[]>` where `PlaylistSummary = { id: string; playlistKey: string; playlistUrl: string; playlistTitle: string | null; createdAt: string }`.

- [ ] **Step 1: Failing integration test** — seed two owners each with playlists (incl. one null-title, and a colliding `playlist_key` across owners); assert owner A's `listPlaylists(A)` returns only A's rows, ordered by title (nulls last) then `created_at`, and includes `createdAt`.
- [ ] **Step 2: Run → FAIL** (method absent).
- [ ] **Step 3: Implement Supabase.**

```ts
async listPlaylists(ownerId: string): Promise<PlaylistSummary[]> {
  const { data, error } = await this.client
    .from('playlists')
    .select('id, playlist_key, playlist_url, playlist_title, created_at')
    .eq('owner_id', ownerId)
    .order('playlist_title', { nullsFirst: false })
    .order('created_at');
  if (error) throw error;
  return (data ?? []).map((r) => ({
    id: r.id, playlistKey: r.playlist_key, playlistUrl: r.playlist_url,
    playlistTitle: r.playlist_title, createdAt: r.created_at,
  }));
}
```

- [ ] **Step 4: Implement local** — wrap `listRecentPlaylists`; map to `PlaylistSummary` (synth `createdAt` from file mtime; `id` = playlist_key locally).
- [ ] **Step 5: Run both → PASS.** Full suite. Commit `feat(2a): MetadataStore.listPlaylists (owner-filtered)`.

### Task 4: `GET /api/playlists` cloud route

**Files:** Create `app/api/playlists/route.ts`; Test `tests/integration/playlists-route.test.ts`
- [ ] **Step 1: Failing test** — unauth → 401; authed owner → own playlists JSON; local mode `?root=` unchanged.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — `serveLocal`/`serveCloud` dispatch on `STORAGE_BACKEND`. Cloud: `createServerSupabase(cookies)` → `getUser()` (401) → `getStorageBundle({supabaseClient}).metadataStore.listPlaylists(user.id)` → `{ playlists }`. Local: keep the existing `?root` recent-provider behavior (move it here or delegate).
- [ ] **Step 4: Run → PASS.** Full suite. Commit `feat(2a): GET /api/playlists cloud route`.

### Task 5: `GET /api/videos` cloud branch

**Files:** Modify `app/api/videos/route.ts`; Test `tests/integration/videos-route-cloud.test.ts`
- [ ] **Step 1: Failing tests** — cloud: unauth 401; foreign playlist UUID → 404 (`resolveOwnedPlaylistKey` null); owned → sorted `videos`; `?outputFolder` present in cloud → 400; `sortOrder` not in {asc,desc} → defaults asc (no crash). Local branch unchanged (existing tests still green).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — refactor into `serveLocal(request)` (current body) and `serveCloud(request)`. Cloud: `getUser()` → `resolveOwnedPlaylistKey(supabase, playlistId, user.id)` (404 if null) → `getPrincipalFromSession({userId}, playlistKey)` → `readIndex` → reuse existing `sortVideos` (validate `sortColumn` via existing whitelist AND `sortOrder ∈ {asc,desc}`). Do NOT call `recoverOrphanedVideos`. Reject `outputFolder` (400).
- [ ] **Step 4: Run → PASS.** Full suite. Commit `feat(2a): /api/videos cloud branch`.

### Task 6: `GET /api/videos/[id]/quick-view` cloud branch

**Files:** Modify `app/api/videos/[id]/quick-view/route.ts`; Test `tests/integration/quickview-route-cloud.test.ts`
- [ ] **Step 1: Failing tests** — cloud owned video with summary → `{tldr,takeaways,tags}`; video without `summaryMd && tldr` → 404 (parity with local `:27`); foreign → 404; unauth → 401.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — cloud branch: resolve as T5, `readIndex`, find the video, apply the `summaryMd && tldr` gate → 404 else return the three fields.
- [ ] **Step 4: Run → PASS.** Full suite. Commit `feat(2a): quick-view cloud branch`.

### Task 7: `update_video_annotations` RPC + store method + review cloud branch (§8 iterative review)

**Files:**
- Create: `supabase/migrations/0016_update_video_annotations.sql`
- Modify: `lib/storage/metadata-store.ts` (interface), `supabase-metadata-store.ts`, `local-metadata-store.ts`, `app/api/videos/[id]/review/route.ts`
- Test: `tests/integration/annotations-rpc.test.ts`, `tests/integration/review-route-cloud.test.ts`

**Interfaces:**
- Produces: `updateVideoAnnotations(p: Principal, videoId: string, set: Partial<Pick<Video,'personalScore'|'personalNote'|'archived'>>, clear: ('personalScore'|'personalNote')[]): Promise<{ found: boolean }>`.

- [ ] **Step 1: Failing RPC tests** — (a) set `personalScore` then clear it (JSON-null path) → key removed; (b) mixed set note + clear score in one call; (c) missing video → `found:false`; (d) **cross-owner:** owner B calling with A's `playlist_id` → 0 rows (`found:false`), A's data unmodified; (e) a non-allowlisted key in `p_set` (e.g. `summaryMd`) is **not** written; (f) an existing `summaryHtml:null` written via `merge_video_data` still stores null (merge unchanged).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Write the migration** (mirrors `merge_video_data`'s security model; allowlist enforced in SQL):

```sql
-- 0016_update_video_annotations.sql
create function update_video_annotations(
  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[]
) returns integer language plpgsql security invoker set search_path = public as $$
declare
  allow text[] := array['personalScore','personalNote','archived'];
  v_set jsonb := '{}'::jsonb;
  k text;
  n integer;
begin
  -- slice p_set to the allowlist (defense-in-depth; route already validates)
  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    if k = any(allow) then v_set := v_set || jsonb_build_object(k, p_set->k); end if;
  end loop;
  -- ALWAYS issue the UPDATE (even if v_set empty / p_clear empty) so row_count = row existence.
  update videos
     set data = (data || v_set) - (select coalesce(array_agg(c),'{}') from unnest(coalesce(p_clear,'{}')) c where c = any(allow))
   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
  get diagnostics n = row_count;   -- trigger bumps updated_at on match
  return n;
end $$;
```

- [ ] **Step 4: Store method + review route.** `SupabaseMetadataStore.updateVideoAnnotations`: `requirePlaylistId(p)` → `rpc('update_video_annotations', { p_playlist_id, p_video_id, p_set: set, p_clear: clear })` → `{ found: (n ?? 0) > 0 }`. Local impl: apply set/clear to the in-file video (allowlist keys). Review route `serveCloud`: same validation as local; map `null` score / `""` note into `clear`, the rest into `set`; `found:false` → 404; reject `outputFolder`.
- [ ] **Step 5: Run all → PASS.** `npx supabase db reset && npm run test:integration -- --runInBand annotations-rpc review-route-cloud`.
- [ ] **Step 6: Full suite** + confirm `merge_video_data` regression test (f) green. `npx tsc --noEmit`; `npm test`; integration.
- [ ] **Step 7: Commit** `feat(2a): update_video_annotations RPC + review cloud branch`.

### Task 8: `POST /api/videos/[id]/archive` cloud branch

**Files:** Modify `app/api/videos/[id]/archive/route.ts`; Test `tests/integration/archive-route-cloud.test.ts`
- [ ] **Step 1: Failing tests** — cloud `{playlist, action:'archive'}` sets `data.archived=true` (via `updateVideoAnnotations` set); `'unarchive'` → false; missing video → 404; foreign → 404; unauth → 401; local branch unchanged.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — cloud branch calls `updateVideoAnnotations(principal, videoId, { archived: action === 'archive' }, [])`; `found:false` → 404.
- [ ] **Step 4: Run → PASS.** Full suite. Commit `feat(2a): archive cloud branch (flag via annotation RPC)`.

---

## PHASE B — Cloud frontend

### Task 9: Middleware auth gating + callback fix

**Files:** Modify `middleware.ts`, `lib/supabase/route-categories.ts`, `app/auth/callback/route.ts`; Test `tests/integration/middleware-2a.test.ts` (or unit harness)
- [ ] **Step 1: Failing tests** — local mode (`STORAGE_BACKEND` unset): middleware is a **no-op** and does NOT read Supabase env (mock env absent → no throw). Cloud mode: unauth `/` → redirect `/login`; unauth `/login` → renders (200, no redirect); authed `/login` → `/`; unauth `/api/videos` → JSON 401 (not 302); anon-provision on `/try` preserved; `/s/*` classification unchanged. Callback with `?next=/` → redirect `/`; callback default (no next) → `/` (not `/library`).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.** `route-categories.ts`: add `'/login'` to `PUBLIC_EXACT`. `middleware.ts`: first line `if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase') return NextResponse.next({ request });`. In cloud path: treat `pathname === '/'` as `authenticated`; unauth authenticated **page** → redirect `/login` (keep the `/api/*` JSON-401 branch first); authed `/login` → `/`; preserve `needsAnonProvision`. `callback/route.ts`: change `?? '/library'` → `?? '/'`.
- [ ] **Step 4: Run → PASS.** Full suite. Commit `feat(2a): cloud middleware gating + callback default fix`.

### Task 10: Scope-aware API client + `ScopeProvider`

**Files:** Create `lib/client/api.ts`, `lib/client/scope.tsx`; Test `tests/lib/client-api.test.ts`
**Interfaces:**
- Produces: `type Scope = {mode:'local';outputFolder:string;baseOutputFolder:string} | {mode:'cloud';playlistId:string}`; `ScopeProvider`, `useScope()`; `apiClient` fns `listVideos(scope,sort)`, `getQuickView(scope,videoId)`, `saveAnnotation(scope,videoId,patch)`, `setArchived(scope,videoId,archived)`, `listPlaylists()`.
- [ ] **Step 1: Failing tests** — cloud scope builds `/api/videos?playlist=<uuid>&...`; local builds `?outputFolder=`; a cloud call with no `playlistId` **throws before fetch**; a 401 response surfaces a typed `UnauthorizedError`.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** the client (URL/body construction per §9 URL Contracts; throw on missing/wrong-mode scope; map 401→UnauthorizedError) and `ScopeProvider` context.
- [ ] **Step 4: Run → PASS.** Commit `feat(2a): scope-aware api client + ScopeProvider`.

### Task 11: `/login` page (Google OAuth)

**Files:** Create `app/login/page.tsx`; Create `lib/supabase/client` usage; Test `tests/components/login-page.test.tsx`
- [ ] **Step 1: Failing test** — renders "Continue with Google"; click calls `signInWithOAuth({provider:'google', options:{redirectTo: <origin>/auth/callback?next=/}})` (mock `createClient`).
- [ ] **Step 2: Run → FAIL.** **Step 3: Implement** (client component, tokens from T16). **Step 4: PASS.** Commit `feat(2a): /login Google OAuth page`.

### Task 12: `app/page.tsx` thin server dispatch + LocalApp extraction + design tokens

**Files:** Create `lib/supabase/page-session.ts`, `components/local/LocalApp.tsx`, `components/cloud/CloudApp.tsx` (skeleton); Modify `app/page.tsx`, `app/globals.css`; Test `tests/integration/page-dispatch.test.tsx`
- [ ] **Step 1: Failing tests** — `app/page.tsx` has no `'use client'`; local mode renders `LocalApp` (existing behavior; existing page tests re-pointed at `LocalApp` stay green); cloud mode + session renders `CloudApp` with serializable `{session:{userId,email}}`; the page-session helper's `setAll` is a no-op (no throw in render).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.** Move the entire current `app/page.tsx` client body verbatim into `components/local/LocalApp.tsx` (add `'use client'`). New `app/page.tsx` (server): read mode; in cloud mode read session via `lib/supabase/page-session.ts` (a `createServerClient` whose `setAll` is a try-catch/no-op — trust middleware refresh; call `getUser()` only); render `<LocalApp/>` or `<CloudApp session={{userId,email}}/>`. Add the §8.2 design tokens to `app/globals.css` `@theme`. `CloudApp` is a skeleton shell here (sidebar/library wired in T13–T15).
- [ ] **Step 4: Run → PASS.** Full suite; migrate the existing `PageIntegration`/component tests that imported `app/page.tsx` to `components/local/LocalApp.tsx`. Commit `feat(2a): dual-mode page dispatch + LocalApp extraction + tokens`.

### Task 13: `PlaylistSidebar`

**Files:** Create `components/cloud/PlaylistSidebar.tsx`; Test `tests/components/playlist-sidebar.test.tsx`
- [ ] **Step 1: Failing tests** — fetches via `apiClient.listPlaylists` (mocked); renders titles (null-title → "Untitled playlist" / url-host fallback); active item from `?playlist`; empty list → onboarding empty state; "+ New playlist" is **disabled** and **makes no request** (assert no fetch).
- [ ] **Step 2–4:** RED → implement (uses `useScope`, tokens) → PASS. Commit `feat(2a): PlaylistSidebar`.

### Task 14: `AccountMenu`

**Files:** Create `components/cloud/AccountMenu.tsx`; Test `tests/components/account-menu.test.tsx`
- [ ] **Step 1: Failing tests** — shows email; "Sign out" calls `signOut()` then redirects `/login`; **dismissal:** click-outside closes, Escape closes, selecting an item closes (per §10 Overlay Dismissal — one test block per path).
- [ ] **Step 2–4:** RED → implement → PASS. Commit `feat(2a): AccountMenu`.

### Task 15: Retarget leaf components to the client seam + cloud VideoMenu allowlist + CloudApp wiring

**Files:** Modify `components/{StarRating,NoteCell,VideoQuickView,VideoList,VideoMenu}.tsx`, `components/cloud/CloudApp.tsx`; migrate affected `tests/components/*`
- [ ] **Step 1: Failing tests** — in cloud scope, `StarRating`/`NoteCell` save via `apiClient.saveAnnotation` (no raw `outputFolder` request — assert); `VideoQuickView` loads via `apiClient.getQuickView`; `VideoMenu` in cloud shows **only** "Open on YouTube" + "Archive/Unarchive" (doc/PDF/deep-dive/corrections/Obsidian/Ask-Gemini hidden); `CloudApp` renders sidebar + `VideoList` for `?playlist`, wires sort/filter/Show-Archive/rate/clear/archive.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** — replace inline `fetch`/`outputFolder` URL-building in the leaf components with `useScope()` + `apiClient` calls (markup unchanged); gate `VideoMenu` items on `scope.mode === 'cloud'`; wire `CloudApp`. Migrate existing component tests asserting `outputFolder` URLs to the scope client (mock `lib/client/api.ts`).
- [ ] **Step 4: Run → PASS.** Full suite. Commit `feat(2a): retarget leaf components + cloud VideoMenu + CloudApp wiring`.

### Task 16: E2E cloud flow (Playwright)

**Files:** Create `tests/e2e/cloud-library.spec.ts`; Test-only
- [ ] **Step 1: Write E2E** — signed-in session fixture (seed a Supabase session cookie / mock at route level per project convention) → list playlists → open one → sort/filter → rate → **clear rating** → archive → toggle Show-Archive. Assert the sidebar/list render and the annotation persists.
- [ ] **Step 2: Run → confirm passing** against a seeded DB. Keep local specs green.
- [ ] **Step 3: Commit** `test(2a): cloud library E2E`.

---

## Verification (end of stage)

1. `npx tsc --noEmit` — 0 errors.
2. `npm test` — full unit suite green (grows with 2a tests).
3. `npx supabase db reset && npm run test:integration -- --runInBand` — all green (migrations 0001→0016 apply clean).
4. Local app unchanged: existing local component/E2E specs still green.
5. Each §8-flagged task (T1, T7) carried both `docs/reviews/task-2a-N-*-{review,codex}.md`; all High/Important addressed.
6. Cross-owner denial, clear-annotation, missing-video-404, wrong-scope-rejection, middleware local-no-op, `/login` redirects, OAuth `next=/` — all have passing tests.
7. Stage-complete: `superpowers:finishing-a-development-branch` → final whole-branch review → PR to `master` (use `--repo kujinlee/youtube-playlist-summaries-cloud`; two-remotes footgun) → **human merge gate**.

## Self-Review (done)

- **Spec coverage:** A1–A7 → T1–T8; middleware/callback → T9; client seam → T10; login → T11; dispatch/tokens → T12; sidebar → T13; account menu → T14; leaf retarget + menu allowlist → T15; E2E → T16; UI Design tokens → T12; URL Contracts → T10/T15; Overlay Dismissal → T14/T15. No gap.
- **Type consistency:** `PlaylistSummary`, `Scope`, `updateVideoAnnotations(set,clear)` signatures used consistently across T3/T7/T10/T13/T15.
- **Placeholder scan:** load-bearing SQL/TS shown; mechanical UI steps carry interfaces + test contracts (implementer has the spec + brief).
