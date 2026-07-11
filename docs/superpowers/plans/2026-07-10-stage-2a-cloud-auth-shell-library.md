# Stage 2a — Cloud Auth, Shell & Library — Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A multi-tenant user signs in with Google, sees a sidebar of their playlists, opens one, and browses/sorts/filters/annotates its videos against Supabase — while the local filesystem app keeps working unchanged.

**Architecture:** Dual-mode (`STORAGE_BACKEND` local|supabase). Phase A finishes the cloud read/write API layer (owner-scoped list/read routes + a dedicated annotation RPC) left on the local path by Sub-project 1; Phase B builds the cloud auth + shell + library UI, sharing the existing presentational components via a scope-aware API client. All cloud routes follow the merged `serveLocal`/`serveCloud` dual-branch pattern in `app/api/html/[id]/route.ts`.

**Tech Stack:** Next.js App Router, TypeScript, Supabase (`@supabase/ssr`, Postgres RLS), Tailwind v4, Jest + ts-jest, @testing-library/react, Playwright.

**Spec:** `docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md` (CONVERGED). Read it first.
**Plan review:** `docs/reviews/plan-2a-{codex,claude}.md` — this v2 addresses all High + Medium.

## Global Constraints

- **Session client only** for user-facing read/write stores; RLS `owner_id = auth.uid()`. Service-role never on these paths.
- **`merge_video_data` is LEFT UNCHANGED.** Annotation writes use a **new `update_video_annotations` RPC**.
- **`update_video_annotations`:** `SECURITY INVOKER SET search_path = public`; owner from `auth.uid()` (no client `p_owner`); UUID-addressed `p_playlist_id`; annotation-key allowlist `{personalScore, personalNote, archived}` enforced in SQL; always issues the UPDATE; `row_count = 0` → 404. **Must include `revoke all … from public; grant execute … to authenticated;`** (matches every `0007` RPC — `0007:43,73,97,121`).
- **Every cloud route validates `?playlist` UUID format BEFORE any DB call** (`UUID_RE`, per `app/api/html/[id]/route.ts:37`) → 400 on malformed (else Postgres `invalid input syntax for type uuid` → 500).
- **Cloud route flow (mirror `app/api/html/[id]/route.ts:40-51`):** `createServerSupabase(cookies)` → `auth.getUser()` (401) → `UUID_RE` guard (400) → `resolveOwnedPlaylistKey(supabase, playlistId, user.id)` (404 if null) → `getPrincipalFromSession({userId}, playlistKey)` → `getStorageBundle({ supabaseClient: supabase })`. Reject wrong-mode param (cloud 400 on `outputFolder`; local 400 on `playlist`).
- **Cloud integration tests** set `process.env.STORAGE_BACKEND = 'supabase'` in `beforeAll` and authenticate via `tests/integration/helpers/clients.ts` `signInAs()` (real JWT → `auth.uid()`), per `tests/integration/html-serve-isolation.test.ts:9-13`.
- **Versioning:** whole-record newer-wins; `docVersion` primary, `updatedAt` tiebreak. `updatedAt` from `videos.updated_at` (cloud, via ON UPDATE trigger) surfaced into `Video.updatedAt`; per-video stamp in the local store (never `writeIndex`).
- **Local app UNTOUCHED and must stay green.**
- **Middleware EXTENDED, not replaced:** local no-op short-circuit before env read; `/login` public; cloud `/` gated → `/login`; preserve anon-provision + `/api/*` JSON 401.
- **Trailers on every commit:** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01JEDFvzMp4257ao7qtZM7Px`.
- **§8 iterative dual review** on T1 (trigger/schema) and T7 (RPC/RLS).

## File Structure
Phase A: `supabase/migrations/0015_video_updated_at_trigger.sql` (new), `…/0016_update_video_annotations.sql` (new), `types/index.ts`, `lib/storage/metadata-store.ts`, `lib/storage/supabase/supabase-metadata-store.ts`, `lib/storage/local/local-metadata-store.ts`, `lib/index-store.ts`, `app/api/playlists/route.ts` (new), `app/api/videos/route.ts`, `…/[id]/quick-view/route.ts`, `…/[id]/review/route.ts`, `…/[id]/archive/route.ts`.
Phase B: `middleware.ts`, `lib/supabase/route-categories.ts`, `app/auth/callback/route.ts`, `lib/supabase/page-session.ts` (new), `app/login/page.tsx` (new), `lib/client/api.ts` + `lib/client/scope.tsx` (new), `app/page.tsx`, `components/local/LocalApp.tsx` (new), `components/cloud/{CloudApp,PlaylistSidebar,AccountMenu}.tsx` (new), `components/{StarRating,NoteCell,VideoQuickView,VideoList,VideoRow,VideoMenu}.tsx`, `app/globals.css`.

**Migration numbering:** tip is `0014`. Each migration task re-runs `ls supabase/migrations/ | tail -1` immediately before creating its file and numbers off the committed tip (T1 → `0015`; T7 → `0016`, which depends on T1 already committed).

---

## PHASE A — Backend read/write layer

### Task 1: `updatedAt` — trigger + schema + cloud read surface (§8 iterative review)
**Files:** Create `supabase/migrations/0015_video_updated_at_trigger.sql`; Modify `types/index.ts`, `lib/storage/supabase/supabase-metadata-store.ts` (`readIndex`); Test `tests/integration/video-updated-at.test.ts`, `tests/lib/types.test.ts`.
**Interfaces — Produces:** `Video.updatedAt?: string` (ISO); `readIndex` populates it from the DB column.
- [ ] **Step 1 (RED):** `tests/integration/video-updated-at.test.ts` (set `STORAGE_BACKEND='supabase'` in `beforeAll`, seed via admin client): after a `merge_video_data` write AND a direct `.update({data})` (upsert path, no explicit `updated_at`), assert `videos.updated_at` advanced both times; and `readIndex` returns `video.updatedAt === updated_at`.
- [ ] **Step 2:** Run `npm run test:integration -- --runInBand video-updated-at` → FAIL (no trigger).
- [ ] **Step 3:** Migration:
```sql
-- 0015_video_updated_at_trigger.sql
create or replace function set_videos_updated_at() returns trigger
  language plpgsql set search_path = public as $$
begin new.updated_at = now(); return new; end $$;
drop trigger if exists trg_videos_updated_at on videos;
create trigger trg_videos_updated_at before update on videos
  for each row execute function set_videos_updated_at();
```
- [ ] **Step 4:** `readIndex`: change videos select `.select('data')` → `.select('data, updated_at')`; map `{ ...(r.data as Video), updatedAt: r.updated_at }`. Add `updatedAt: z.string().datetime().optional()` to `VideoSchema`.
- [ ] **Step 5:** `npx supabase db reset && npm run test:integration -- --runInBand video-updated-at` + `tests/lib/types.test.ts` (valid with/without `updatedAt`) → PASS.
- [ ] **Step 6:** Full suite: `npx tsc --noEmit`; `npm test`; integration. No regression.
- [ ] **Step 7:** Commit `feat(2a): videos.updated_at trigger + Video.updatedAt surfaced`.

### Task 2: Local per-video `updatedAt` stamp
**Files:** Modify `lib/index-store.ts` (`updateVideoFields`, `upsertVideo`); Test `tests/lib/index-store-updated-at.test.ts`.
- [ ] **Step 1 (RED):** after `indexStore.updateVideoFields(key, id, {personalScore:4})` the touched video has ISO `updatedAt`; a **sibling** video is unchanged (pins N3 — never stamp at `writeIndex`).
- [ ] **Step 2:** `npx jest index-store-updated-at` → FAIL.
- [ ] **Step 3:** In `lib/index-store.ts` `updateVideoFields` and `upsertVideo`, set `updatedAt: new Date().toISOString()` on the single mutated video. Do NOT touch `writeIndex`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5 (broadened audit — M3):** run `npm test` AND `npm run test:integration -- --runInBand`; **audit every suite asserting exact video JSON** (`toEqual` on a Video) — pipeline, summary-handler, `tests/integration/metadata-store.test.ts`, backfill, reconcile, local-store — and switch exact snapshots to field matchers (`expect.objectContaining` / omit `updatedAt`). All green.
- [ ] **Step 6:** Commit `feat(2a): local per-video updatedAt stamp`.

### Task 3: `listPlaylists(ownerId)` store method — CLOUD-ONLY
**Files:** Modify `lib/storage/metadata-store.ts` (interface), `supabase-metadata-store.ts`, `local-metadata-store.ts`; Test `tests/integration/list-playlists.test.ts`.
**Interfaces — Produces:** `listPlaylists(ownerId: string): Promise<PlaylistSummary[]>`, `PlaylistSummary = { id: string; playlistKey: string; playlistUrl: string; playlistTitle: string | null; createdAt: string }`. **Cloud-only** — the local impl throws (H1: `listRecentPlaylists` needs a filesystem root, not an ownerId, and returns a different shape; the local sidebar is not rendered in 2a).
- [ ] **Step 1 (RED):** integration (`STORAGE_BACKEND='supabase'`, `signInAs`): seed two owners, incl. a null-title playlist and a `playlist_key` colliding across owners; assert `listPlaylists(A)` returns only A's rows, ordered by title (nulls last) then `created_at`, incl. `createdAt`; owner B's identical key is excluded.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (Supabase):**
```ts
async listPlaylists(ownerId: string): Promise<PlaylistSummary[]> {
  const { data, error } = await this.client.from('playlists')
    .select('id, playlist_key, playlist_url, playlist_title, created_at')
    .eq('owner_id', ownerId)
    .order('playlist_title', { nullsFirst: false }).order('created_at');
  if (error) throw error;
  return (data ?? []).map((r) => ({ id: r.id, playlistKey: r.playlist_key,
    playlistUrl: r.playlist_url, playlistTitle: r.playlist_title, createdAt: r.created_at }));
}
```
- [ ] **Step 4 (local):** `LocalFsMetadataStore.listPlaylists` = `throw new Error('listPlaylists is cloud-only')` (mirrors `resolvePlaylistId` at `local-metadata-store.ts:45`). Add `listPlaylists` to the `MetadataStore` interface. No local unit test (nothing calls it locally).
- [ ] **Step 5:** Run → PASS. Full suite. Commit `feat(2a): MetadataStore.listPlaylists (cloud-only, owner-filtered)`.

### Task 4: `GET /api/playlists` route (cloud + local)
**Files:** Create `app/api/playlists/route.ts`; Test `tests/integration/playlists-route.test.ts`.
- [ ] **Step 1 (RED):** cloud (`STORAGE_BACKEND='supabase'`, `signInAs`): unauth → 401; authed → own playlists JSON `{ playlists }`; another owner's playlists absent. Local: `?root=<path>` returns `listRecentPlaylists(root)` output (unchanged behavior).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `serveLocal`/`serveCloud` dispatch. Cloud: `createServerSupabase` → `getUser()` (401) → `getStorageBundle({supabaseClient}).metadataStore.listPlaylists(user.id)` → `{ playlists }`. **Local: delegate directly to `listRecentPlaylists(root)`** (do NOT go through the store's cloud-only method); require `?root`, keep the existing within-home guard.
- [ ] **Step 4:** Run → PASS. Full suite. Commit `feat(2a): GET /api/playlists route`.

### Task 5: `GET /api/videos` cloud branch
**Files:** Modify `app/api/videos/route.ts`; Test `tests/integration/videos-route-cloud.test.ts`.
- [ ] **Step 1 (RED, `STORAGE_BACKEND='supabase'`, `signInAs`):** cloud unauth → 401; **malformed `?playlist` → 400** (UUID guard, before DB); **`?outputFolder` present in cloud → 400**; missing `?playlist` → 400; foreign (valid but unowned) UUID → 404; owned → `{ videos, playlistUrl, playlistTitle }` sorted (same response shape as local `videos/route.ts:115` — L1); `sortOrder` not in `{asc,desc}` → defaults `asc`. Local branch unchanged (existing tests green).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Refactor into `serveLocal(request)` (current body verbatim) and `serveCloud(request)`. Cloud follows the Global-Constraints route flow (getUser → UUID_RE → resolveOwnedPlaylistKey → getPrincipalFromSession → getStorageBundle) → `readIndex` → reuse `sortVideos` (validate `sortColumn` via the existing whitelist AND `sortOrder ∈ {asc,desc}`) → return `{ videos, playlistUrl: index.playlistUrl, playlistTitle: index.playlistTitle }`. Do NOT call `recoverOrphanedVideos`. Reject `outputFolder` (400).
- [ ] **Step 4:** Run → PASS. Full suite. Commit `feat(2a): /api/videos cloud branch`.

### Task 6: `GET /api/videos/[id]/quick-view` cloud branch
**Files:** Modify `app/api/videos/[id]/quick-view/route.ts`; Test `tests/integration/quickview-route-cloud.test.ts`.
- [ ] **Step 1 (RED):** cloud unauth → 401; malformed UUID → 400; `outputFolder` in cloud → 400; foreign → 404; owned video with `summaryMd && tldr` → `{tldr,takeaways,tags}`; owned video missing `summaryMd`/`tldr` → 404 (parity with local `quick-view route:27`). Local unchanged.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Cloud branch (full route flow) → `readIndex` → find the video → apply `summaryMd && tldr` gate (404 else the three fields).
- [ ] **Step 4:** Run → PASS. Full suite. Commit `feat(2a): quick-view cloud branch`.

### Task 7: `update_video_annotations` RPC + store method + review cloud branch (§8 iterative review)
**Files:** Create `supabase/migrations/0016_update_video_annotations.sql`; Modify `lib/storage/metadata-store.ts`, `supabase-metadata-store.ts`, `local-metadata-store.ts`, `app/api/videos/[id]/review/route.ts`; Test `tests/integration/annotations-rpc.test.ts`, `tests/integration/review-route-cloud.test.ts`.
**Interfaces — Produces:** `updateVideoAnnotations(p: Principal, videoId: string, set: Partial<Pick<Video,'personalScore'|'personalNote'|'archived'>>, clear: ('personalScore'|'personalNote')[]): Promise<{ found: boolean }>`.
- [ ] **Step 0:** `ls supabase/migrations/ | tail -1` → confirm tip is `0015` (T1 committed) → number this `0016`.
- [ ] **Step 1 (RED):** RPC tests (`STORAGE_BACKEND='supabase'`, `signInAs`): (a) set `personalScore` then clear (JSON-null) → key removed; (b) mixed set-note + clear-score in one call; (c) missing video → `found:false`; (d) **cross-owner:** owner B with A's `playlist_id` → 0 rows (`found:false`), A unmodified; (e) a non-allowlisted key in `p_set` (`summaryMd`) is NOT written; (f) an existing `merge_video_data` write of `summaryHtml:null` still stores `null` (merge unchanged). Route tests: cloud set/clear round-trip; missing → 404; malformed UUID → 400; `outputFolder` → 400; validation bounds → 400.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Migration (mirrors `merge_video_data` security model + the project's revoke/grant):
```sql
-- 0016_update_video_annotations.sql
create function update_video_annotations(
  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[]
) returns integer language plpgsql security invoker set search_path = public as $$
declare
  allow text[] := array['personalScore','personalNote','archived'];
  v_set jsonb := '{}'::jsonb; k text; n integer;
begin
  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    if k = any(allow) then v_set := v_set || jsonb_build_object(k, p_set->k); end if;
  end loop;
  update videos
     set data = (data || v_set) - (select coalesce(array_agg(c),'{}') from unnest(coalesce(p_clear,'{}')) c where c = any(allow))
   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function update_video_annotations(uuid, text, jsonb, text[]) from public;
grant execute on function update_video_annotations(uuid, text, jsonb, text[]) to authenticated;
```
- [ ] **Step 4:** `SupabaseMetadataStore.updateVideoAnnotations`: `requirePlaylistId(p)` → `rpc('update_video_annotations', { p_playlist_id, p_video_id, p_set: set, p_clear: clear })` → `{ found: (data ?? 0) > 0 }`. Local impl: apply set/clear (allowlist keys) to the in-file video (interface-shape; not on a local runtime path). Review route `serveCloud` (full route flow): same validation as local; `null` score / `""` note → `clear`, rest → `set`; `found:false` → 404; reject `outputFolder`.
- [ ] **Step 5:** `npx supabase db reset && npm run test:integration -- --runInBand annotations-rpc review-route-cloud` → PASS.
- [ ] **Step 6:** Full suite + confirm regression (f) green. `npx tsc --noEmit`; `npm test`; integration.
- [ ] **Step 7:** Commit `feat(2a): update_video_annotations RPC + review cloud branch`.

### Task 8: `POST /api/videos/[id]/archive` cloud branch
**Files:** Modify `app/api/videos/[id]/archive/route.ts`; Test `tests/integration/archive-route-cloud.test.ts`.
- [ ] **Step 1 (RED):** cloud `{playlist, action:'archive'}` → `data.archived=true`; `'unarchive'` → false; missing → 404; foreign → 404; malformed UUID → 400; `outputFolder` in cloud → 400; unauth → 401; local branch unchanged.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Cloud branch (full route flow) → `updateVideoAnnotations(principal, videoId, { archived: action === 'archive' }, [])`; `found:false` → 404.
- [ ] **Step 4:** Run → PASS. Full suite. Commit `feat(2a): archive cloud branch (flag via annotation RPC)`.

---

## PHASE B — Cloud frontend

### Task 9: Middleware auth gating + callback fix
**Files:** Modify `middleware.ts`, `lib/supabase/route-categories.ts`, `app/auth/callback/route.ts`; Test `tests/integration/middleware-2a.test.ts` (`.test.ts`).
- [ ] **Step 1 (RED):** local mode (unset `STORAGE_BACKEND`): middleware **no-op**, does NOT read Supabase env (env absent → no throw). Cloud: unauth `/` → redirect `/login`; unauth `/login` → 200 renders; authed `/login` → `/`; unauth `/api/videos` → JSON 401 (not 302); `/try` anon-provision preserved; `/s/*` classification unchanged. Callback `?next=/` → `/`; callback no-next default → `/`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** `route-categories.ts`: add `'/login'` to `PUBLIC_EXACT`. `middleware.ts`: first line `if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase') return NextResponse.next({ request });`. Cloud path: treat `pathname === '/'` as `authenticated`; unauth authenticated **page** → redirect `/login` (keep the `/api/*` JSON-401 branch first); authed `/login` → `/`; preserve `needsAnonProvision`. `callback/route.ts`: `?? '/library'` → `?? '/'`.
- [ ] **Step 4:** Run → PASS. Full suite. Commit `feat(2a): cloud middleware gating + callback fix`.

### Task 10: Scope-aware API client + `ScopeProvider`
**Files:** Create `lib/client/api.ts`, `lib/client/scope.tsx`; Test `tests/components/client-api.test.tsx`.
**Interfaces — Produces:** `type Scope = {mode:'local';outputFolder:string;baseOutputFolder:string} | {mode:'cloud';playlistId:string}`; `ScopeProvider`, `useScope()`; `class UnauthorizedError extends Error`; fns `listPlaylists()`, `listVideos(scope,sort)`, `getQuickView(scope,videoId)`, `saveAnnotation(scope,videoId,patch)`, `setArchived(scope,videoId,archived)`.
- [ ] **Step 1 (RED):** cloud scope builds `/api/videos?playlist=<uuid>&sortColumn=&sortOrder=`; local builds `?outputFolder=`; a cloud call with no `playlistId` **throws before fetch**; a 401 response → throws `UnauthorizedError`; body shapes for `saveAnnotation`/`setArchived` match §9 URL Contracts.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement the client (URL/body per §9; throw on missing/wrong-mode scope; map 401 → `UnauthorizedError`) + `ScopeProvider` context.
- [ ] **Step 4:** Run → PASS. Commit `feat(2a): scope-aware api client + ScopeProvider`.

### Task 11: `/login` page (Google OAuth)
**Files:** Create `app/login/page.tsx`; Test `tests/components/login-page.test.tsx`.
- [ ] **Step 1 (RED):** renders "Continue with Google"; click calls `createClient().auth.signInWithOAuth({ provider:'google', options:{ redirectTo: '${location.origin}/auth/callback?next=/' } })` (mock `createClient`).
- [ ] **Step 2:** FAIL → **Step 3:** implement (client component, tokens from T12). **Step 4:** PASS. Commit `feat(2a): /login Google OAuth page`.

### Task 12: `app/page.tsx` thin server dispatch + LocalApp extraction + design tokens
**Files:** Create `lib/supabase/page-session.ts`, `components/local/LocalApp.tsx`, `components/cloud/CloudApp.tsx` (skeleton); Modify `app/page.tsx`, `app/globals.css`; Test `tests/components/page-dispatch.test.tsx` (**`tests/components/`** so Jest picks up `.tsx` — H2).
- [ ] **Step 1 (RED):** `app/page.tsx` has no `'use client'`; local mode renders `LocalApp`; cloud mode + session renders `CloudApp` with serializable `{ session:{userId,email} }`; `page-session` helper's `setAll` is a no-op (no throw in render).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Move the entire current `app/page.tsx` client body verbatim into `components/local/LocalApp.tsx` (`'use client'`). New server `app/page.tsx`: read mode; in cloud mode read session via `lib/supabase/page-session.ts` (a `createServerClient` whose `setAll` is a try-catch/no-op — trust middleware refresh; `getUser()` only); render `<LocalApp/>` or `<CloudApp session={…}/>`. Add §8.2 design tokens to `app/globals.css` `@theme`. `CloudApp` is a skeleton shell (wired T13–T15).
- [ ] **Step 4:** Run → PASS. Full suite; **re-point existing tests** that imported `app/page.tsx` (e.g. `PageIntegration`) to `components/local/LocalApp.tsx`. Commit `feat(2a): dual-mode page dispatch + LocalApp extraction + tokens`.

### Task 13: `PlaylistSidebar`
**Files:** Create `components/cloud/PlaylistSidebar.tsx`; Test `tests/components/playlist-sidebar.test.tsx`.
- [ ] **Step 1 (RED):** fetches via `apiClient.listPlaylists` (mocked); renders titles (null-title → "Untitled playlist" / url-host fallback); a click sets the URL to **`/?playlist=<uuid>`** (assert the nav href — L2, spec §9); active item from `?playlist`; empty list → onboarding empty state; "+ New playlist" is **disabled** and makes **no request** (assert no fetch).
- [ ] **Step 2–4:** RED → implement (uses `useScope`, tokens) → PASS. Commit `feat(2a): PlaylistSidebar`.

### Task 14: `AccountMenu`
**Files:** Create `components/cloud/AccountMenu.tsx`; Test `tests/components/account-menu.test.tsx`.
- [ ] **Step 1 (RED):** shows email; "Sign out" calls `signOut()` then redirects `/login`; **dismissal (one block per path, §10):** click-outside closes, Escape closes, selecting an item closes.
- [ ] **Step 2–4:** RED → implement → PASS. Commit `feat(2a): AccountMenu`.

### Task 15: Retarget leaf components + cloud VideoMenu allowlist + CloudApp wiring + 401 handling
**Files:** Modify `components/{StarRating,NoteCell,VideoQuickView,VideoList,VideoRow,VideoMenu,cloud/CloudApp}.tsx`; migrate affected `tests/components/*`.
- [ ] **Step 1 (RED):** in cloud scope, `StarRating`/`NoteCell` save via `apiClient.saveAnnotation` (assert **no raw `outputFolder` request**); `VideoQuickView` loads via `apiClient.getQuickView`; **`VideoRow`** forwards no local `outputFolder` in cloud mode (H3 — it threads props to the leaves); `VideoMenu` in cloud shows **only** "Open on YouTube" + "Archive/Unarchive" (doc/PDF/deep-dive/corrections/Obsidian/Ask-Gemini hidden); `CloudApp` renders sidebar + `VideoList` for `?playlist`, wires sort/filter/Show-Archive/rate/clear/archive; **"no videos yet" empty state** renders for an empty list (M4); an `apiClient` call rejecting `UnauthorizedError` makes `CloudApp` redirect to `/login` (H5).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Replace inline `fetch`/`outputFolder` URL-building in `StarRating`/`NoteCell`/`VideoQuickView` (and the `outputFolder` threading in `VideoRow`/`VideoList`) with `useScope()` + `apiClient` (markup unchanged); gate `VideoMenu` items on `scope.mode === 'cloud'`; wire `CloudApp` (incl. empty-state + a top-level `UnauthorizedError` → `router.replace('/login')`). Migrate existing component tests asserting `outputFolder` URLs to the scope client (mock `lib/client/api.ts`).
- [ ] **Step 4:** Run → PASS. Full suite. Commit `feat(2a): retarget leaf components + cloud VideoMenu + CloudApp wiring + 401 redirect`.

### Task 16: E2E cloud flow (Playwright)
**Files:** Create `tests/e2e/cloud-library.spec.ts`; Modify `playwright.config.ts` (add a cloud project); Test-only.
- [ ] **Step 1:** Add a **`cloud` Playwright project** whose `webServer` runs the dev server with `STORAGE_BACKEND=supabase` (H4 — the default project starts local; without this the spec never hits `CloudApp`). Seed a Supabase session (auth cookie via `signInAs`-equivalent, or route-level mock per project convention).
- [ ] **Step 2:** E2E: signed-in → list playlists → open one → sort/filter → rate → **clear rating** → archive → toggle Show-Archive; assert sidebar/list render and annotation persists.
- [ ] **Step 3:** Run the cloud project green; keep local specs green. Commit `test(2a): cloud library E2E`.

---

## Verification (end of stage)
1. `npx tsc --noEmit` — 0 errors.
2. `npm test` — full unit suite green.
3. `npx supabase db reset && npm run test:integration -- --runInBand` — green (migrations 0001→0016 apply clean).
4. Local app unchanged: existing local component/E2E specs green.
5. T1 & T7 each carry `docs/reviews/task-2a-N-*-{review,codex}.md`; all High/Important addressed.
6. Cross-owner denial, clear-annotation, missing-video-404, malformed-UUID-400, wrong-scope-400, middleware local-no-op, `/login` redirects, OAuth `next=/`, 401→`/login` redirect — all have passing tests.
7. `superpowers:finishing-a-development-branch` → final whole-branch review → PR to `master` (`--repo kujinlee/youtube-playlist-summaries-cloud`) → **human merge gate**.

## Self-Review (v2)
- **Spec coverage:** A1–A7 → T1–T8; middleware/callback → T9; client seam + `UnauthorizedError` → T10; login → T11; dispatch/tokens → T12; sidebar (+nav href) → T13; account menu → T14; leaf retarget + VideoRow + menu allowlist + empty-state + 401 redirect → T15; cloud E2E → T16; tokens → T12; URL Contracts → T10/T13/T15; Overlay Dismissal → T14/T15. No gap.
- **Type consistency:** `PlaylistSummary`, `Scope`, `UnauthorizedError`, `updateVideoAnnotations(set,clear)` used consistently across T3/T7/T8/T10/T13/T15.
- **Plan-review High/Medium:** all addressed (H1 local cloud-only; H2 test path; H3 VideoRow; H4 cloud Playwright project; H5 401 redirect; M1 revoke/grant; M2 UUID guard; M3 test-churn audit; M4 empty-state; route-flow/STORAGE_BACKEND/signInAs spelled out).
