# Stage 2c — Cloud Doc Consumption (Frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a signed-in cloud user view, download (MD/HTML), and share (create/copy/revoke a tokened link) the summary doc that Stage 2b ingest produced — all frontend over already-merged backend, plus two minor read-model touches.

**Architecture:** Everything hangs off the existing shared `components/VideoMenu.tsx`, whose Stage 2a `cloudMode` gate currently permits only *Watch on YouTube* + *Archive*. 2c widens the cloud branch with four readiness-gated items (View summary, Download Markdown, Download HTML, Share…) and adds one overlay (`ShareDialog`, owned by `VideoRow`). View/Download are plain `<a>` links to the existing `serveCloud` html route; Share is a client round-trip to the existing session-client share routes. A new `summaryReady` DTO flag (derived cloud-side from `artifacts.summaryMd.status === 'promoted'`) gates all four.

**Tech Stack:** Next.js (see `AGENTS.md` — read `node_modules/next/dist/docs/` before touching routes), TypeScript, Zod (`types/index.ts` schemas), React + `@testing-library/react`, jest + ts-jest, Supabase (Postgres RPC migrations under `supabase/migrations/`), real-Supabase integration tests.

## Global Constraints

Copied verbatim from spec §11–§12. Every task's requirements implicitly include this section.

- **Session-client-only** for user-facing read/write; **service role is NEVER used from a user-facing store.** Share create/revoke go through the existing session routes; the `summaryReady` select is session-client, owner-scoped.
- **`merge_video_data` is left unchanged.**
- **Local app untouched and must stay green** — 2c adds only cloud components + one **optional** DTO field the local path never sets or reads.
- **Share-serve never charges** — unchanged; 2c adds only create/copy/revoke UI, no serve-path change.
- **No guardrail weakening** — 2c is display/link-only for docs; it changes no threshold and bypasses no gate.
- **Iterative dual-review flags (§12):** Task 1 (share create/revoke — money-adjacent multi-tenant RPC/token surface) and Task 2 (`summaryReady` read-model change threading through `listVideos` serveCloud) get the iterative dual-review treatment: re-review the revised artifact after any Blocking/High fix until a round returns no new Blocking/High.
- **Backend touches are read-model / response-shape only** — no doc generation, no charging, no new table, no guardrail surface. Cloud PDF + deep-dive generation and full share-management (list/revoke-any) are explicitly deferred (spec §1).

**Resolved planning hooks (spec §2):**
1. `summaryReady?: boolean` — derived, added to the shared `VideoSchema` as `.optional()` and populated **only** in the cloud store mapping (`SupabaseMetadataStore.readIndex`); local path never sets it. (Task 2)
2. `POST /api/share` does **NOT** currently return the share `id` — the `create_share_token` RPC returns a scalar `timestamptz`. 2c **adds** the id via a new migration (`0017`) that redefines the RPC to `returns table(id, expires_at)` and threads it through the route. (Task 1)

---

## File Structure

**Backend (read-model / response-shape only):**
- `supabase/migrations/0017_share_token_id_return.sql` *(create)* — redefine `create_share_token` to also return the new row's `id`.
- `app/api/share/route.ts` *(modify)* — read the id+expiry row, add `id` to the 201 response.
- `types/index.ts` *(modify)* — add `summaryReady: z.boolean().optional()` to `VideoSchema`.
- `lib/storage/supabase/supabase-metadata-store.ts` *(modify)* — derive `summaryReady` in `readIndex` mapping.

**Client seam (`lib/client/api.ts`, extend):**
- `summaryHref(playlistId, videoId, opts?)` — pure URL builder for the serveCloud html route.
- `createShare(playlistId, videoId, ttl)` / `revokeShare(shareId)` — POST helpers mirroring `saveAnnotation` + `handle<T>`.

**Components:**
- `components/cloud/ShareDialog.tsx` *(create)* — TTL selector → Create → URL + Copy → Revoke overlay; all dismissal paths + a11y.
- `components/VideoMenu.tsx` *(modify)* — add cloud-branch View/Download/Share items, gated on `summaryReady`; new `onShare?` prop.
- `components/VideoRow.tsx` *(modify)* — own `showShare` state, mount `ShareDialog`, restore focus to the ☰ trigger on close.

**Tests migrated (return-shape change, Task 1):**
- `tests/integration/share-tokens-rpc.test.ts` — RPC now returns a row, not a scalar.
- `tests/api/share-mint-route.test.ts` — response now includes `id`; mock returns `[{ id, expires_at }]`.

---

## Task 1: Backend — share `id` in the create response

**Why first:** the client seam (Task 4) and `ShareDialog` (Task 5) depend on `createShare` returning `id`, which does not exist until the RPC + route return it. This is a §12-flagged money-adjacent multi-tenant surface → iterative dual-review after any Blocking/High fix.

**Files:**
- Create: `supabase/migrations/0017_share_token_id_return.sql`
- Modify: `app/api/share/route.ts:20-27`
- Migrate: `tests/integration/share-tokens-rpc.test.ts`, `tests/api/share-mint-route.test.ts`

**Interfaces:**
- Consumes: existing `create_share_token(p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash text)` (migration `0013_share_tokens.sql:22-46`), currently `returns timestamptz`; `generateShareToken()`, `resolveExpiry()` (unchanged).
- Produces: `POST /api/share` 201 response `{ id: string; token: string; url: string; expiresAt: string | null }`. The RPC now `returns table(id uuid, expires_at timestamptz)` (single row). Task 4's `createShare` relies on this shape.

**Context the brief cannot know:** Postgres cannot `CREATE OR REPLACE` a function across a return-type change, so the migration must `DROP FUNCTION` then `CREATE`. Dropping a function also drops its `GRANT EXECUTE`, so the grant to `authenticated` (from `0013:86`) **must be re-applied** in `0017`. The `RETURNING` clause is qualified as `share_tokens.id` to avoid ambiguity with the new `id` OUT column. Logic (owner check, hash-format check, TTL bound, promoted predicate, insert) is otherwise byte-identical to `0013`.

- [ ] **Step 1: Write the failing integration test (RPC returns id)**

Open `tests/integration/share-tokens-rpc.test.ts`. Find the `create_share_token` happy-path call (it currently reads `data` as the scalar expiry). Change that assertion block to expect a single-row result carrying `id` and `expires_at`:

```ts
// After signInAs(userA) and seeding a promoted video (existing helpers in this file):
const { data, error } = await userAClient.rpc('create_share_token', {
  p_playlist_id: playlistId,
  p_video_id: videoId,
  p_expiry: null,               // 'never'
  p_token_hash: tokenHash,      // 64-char lowercase hex from generateShareToken()
});
expect(error).toBeNull();
const row = Array.isArray(data) ? data[0] : data;
expect(row).toMatchObject({ id: expect.any(String), expires_at: null });
expect(row.id).toMatch(/^[0-9a-f-]{36}$/i);   // uuid
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx supabase db reset && npm run test:integration -- share-tokens-rpc --runInBand`
Expected: FAIL — the current RPC returns a scalar timestamptz, so `row.id` is `undefined`.

- [ ] **Step 3: Write the migration**

Create `supabase/migrations/0017_share_token_id_return.sql`:

```sql
-- supabase/migrations/0017_share_token_id_return.sql
-- Stage 2c: create_share_token now also returns the new row's id so the cloud consumption UI
-- can revoke the share it just created (POST /api/share/<id>/revoke) without a share-list route.
-- Return type changes from scalar timestamptz to table(id, expires_at) → DROP + CREATE (Postgres
-- cannot CREATE OR REPLACE across a return-type change). DROP also drops GRANT EXECUTE, so the
-- grant to authenticated is re-applied below. Ownership/hash/TTL/promoted logic is unchanged.
drop function if exists create_share_token(uuid, text, timestamptz, text);

create function create_share_token(
  p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash text
) returns table(id uuid, expires_at timestamptz) language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_promoted boolean;
  v_id uuid;
begin
  if v_owner is null then raise exception 'create_share_token: unauthenticated'; end if;
  if p_token_hash !~ '^[0-9a-f]{64}$' then raise exception 'create_share_token: bad hash format'; end if;
  if not (p_expiry is null
          or (p_expiry > now() and p_expiry <= now() + make_interval(days => 365) + interval '1 hour')) then
    raise exception 'create_share_token: expiry out of bounds';
  end if;
  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    into v_promoted
    from videos v join playlists p on p.id = v.playlist_id and p.owner_id = v.owner_id
    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
  if v_promoted is distinct from true then
    raise exception 'create_share_token: denied';  -- not owned or not promoted → coarse 404
  end if;
  insert into share_tokens (token_hash, owner_id, playlist_id, video_id, expires_at)
    values (p_token_hash, v_owner, p_playlist_id, p_video_id, p_expiry)
    returning share_tokens.id into v_id;
  return query select v_id, p_expiry;
end $$;

revoke all on function create_share_token(uuid, text, timestamptz, text) from public;
grant execute on function create_share_token(uuid, text, timestamptz, text) to authenticated;
```

- [ ] **Step 4: Run the integration test — verify it passes**

Run: `npx supabase db reset && npm run test:integration -- share-tokens-rpc --runInBand`
Expected: PASS.

- [ ] **Step 5: Write the failing route test (response includes id)**

Open `tests/api/share-mint-route.test.ts`. Update the mocked `supabase.rpc` to return the new row shape and assert `id` is in the 201 body:

```ts
// The rpc mock must now resolve to { data: [{ id, expires_at }], error: null }:
rpc.mockResolvedValue({ data: [{ id: 'share-uuid-1', expires_at: null }], error: null });
// ...POST /api/share with a valid body...
expect(res.status).toBe(201);
const body = await res.json();
expect(body).toEqual({
  id: 'share-uuid-1',
  token: expect.any(String),
  url: expect.stringMatching(/^\/s\/.+/),
  expiresAt: null,
});
```

Keep the existing error-path assertions (400 missing fields, 400 invalid ttl, 401 no user, 404 on rpc error) unchanged **except** that the rpc-error path's mock must be `{ data: null, error: {...} }` → still 404.

- [ ] **Step 6: Run it — verify it fails**

Run: `npx jest share-mint-route`
Expected: FAIL — route still returns `{ token, url, expiresAt }` without `id`.

- [ ] **Step 7: Modify the route**

In `app/api/share/route.ts`, replace lines 21-27:

```ts
  const { data, error } = await supabase.rpc('create_share_token', {
    p_playlist_id: body.playlistId, p_video_id: body.videoId,
    p_expiry: expiry.expiresAt ? expiry.expiresAt.toISOString() : null,
    p_token_hash: tokenHash,
  });
  const row = Array.isArray(data) ? data[0] : null;
  if (error || !row) return json({ error: 'not found' }, 404); // coarse — unowned/unpromoted/bounds
  return json({ id: row.id, token, url: `/s/${token}`, expiresAt: row.expires_at }, 201);
```

- [ ] **Step 8: Run route test — verify it passes**

Run: `npx jest share-mint-route`
Expected: PASS.

- [ ] **Step 9: Full regression + types**

Run: `npx jest && npx tsc --noEmit`
Expected: unit suite green; 0 type errors. Then `npx supabase db reset && npm run test:integration -- share --runInBand` — share integration green.

- [ ] **Step 10: Commit**

```bash
git add supabase/migrations/0017_share_token_id_return.sql app/api/share/route.ts \
        tests/integration/share-tokens-rpc.test.ts tests/api/share-mint-route.test.ts
git commit -m "feat(2c): create_share_token returns id; POST /api/share includes id"
```

---

## Task 2: `summaryReady` DTO field (cloud-derived, local-unaffected)

**Why:** all four cloud menu items are gated on readiness. §12-flagged (read-model change threading through serveCloud; must not leak non-owner artifact state; local path must be truly unaffected) → iterative dual-review after any Blocking/High fix.

**Files:**
- Modify: `types/index.ts` (`VideoSchema`, near the `updatedAt` field ~`:76-81`)
- Modify: `lib/storage/supabase/supabase-metadata-store.ts:45` (`readIndex` mapping)
- Test: `tests/lib/supabase-metadata-store-summary-ready.test.ts` *(create)*

**Interfaces:**
- Consumes: `VideoSchema` / `type Video` (`types/index.ts:47-83`); `readIndex` mapping in `SupabaseMetadataStore` (`lib/storage/supabase/supabase-metadata-store.ts:25-47`), which already derives the cloud-only `updatedAt` at `:45`.
- Produces: `Video.summaryReady?: boolean` — `true` iff the cloud row's `data.artifacts.summaryMd.status === 'promoted'`, else `false`; `undefined` on the local path. Tasks 6/7 gate on it.

**Context the brief cannot know:** `artifacts` is NOT a typed field on `VideoSchema` — it lives only in the DB `videos.data` jsonb and is read via ad-hoc casts (`app/api/html/[id]/route.ts:55`, `lib/share/serve.ts:44`). The canonical readiness predicate `artifacts.summaryMd.status === 'promoted'` is used at those sites + `lib/job-queue/summary-handler.ts:87`. `BlobStatus` = `'pending' | 'committed' | 'promoted' | 'repair_needed'` (`lib/storage/blob-store.ts:3`). serveLocal (`app/api/videos/route.ts:94-128`) and serveCloud (`:134-176`) are separate functions but share the `Video` type via `sortVideos`; the local store (`LocalMetadataStore.readIndex`) has no `artifacts`, so making the field `.optional()` and deriving it only cloud-side leaves local `undefined` — identical to the `updatedAt` precedent.

- [ ] **Step 1: Write the failing derivation test**

Create `tests/lib/supabase-metadata-store-summary-ready.test.ts`. Mock the Supabase client's row fetch so `readIndex` maps three rows — promoted, committed, and artifacts-absent — and assert the derived flag:

```ts
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
// Use the file's existing test-client mocking pattern (mirror tests already covering readIndex,
// e.g. tests that assert updatedAt mapping). Seed rows via the mocked select:
const rows = [
  { data: { id: 'a', /* ...valid Video fields... */ artifacts: { summaryMd: { status: 'promoted' } } }, updated_at: '2026-07-11T00:00:00.000Z' },
  { data: { id: 'b', /* ... */ artifacts: { summaryMd: { status: 'committed' } } }, updated_at: '2026-07-11T00:00:00.000Z' },
  { data: { id: 'c', /* ... (no artifacts) */ }, updated_at: '2026-07-11T00:00:00.000Z' },
];
// ...wire rows into the mocked client, call store.readIndex(principal)...
expect(index.videos.find((v) => v.id === 'a')!.summaryReady).toBe(true);
expect(index.videos.find((v) => v.id === 'b')!.summaryReady).toBe(false);
expect(index.videos.find((v) => v.id === 'c')!.summaryReady).toBe(false);
```

> **Implementer note:** reuse the exact client-mock helper already used by the sibling `readIndex` tests in this directory; do not invent a new mocking style. The `data` objects must be valid `Video` shapes so any Zod parse in the path passes — copy a fixture from an existing store test.

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest supabase-metadata-store-summary-ready`
Expected: FAIL — `summaryReady` is `undefined` (field not derived yet).

- [ ] **Step 3: Add the optional schema field**

In `types/index.ts`, inside `VideoSchema` (immediately after the `updatedAt` field), add:

```ts
  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
  // Optional → the local path never sets it (same back-compat pattern as updatedAt). Gates the
  // cloud View/Download/Share menu items; the serving route enforces the same predicate server-side.
  summaryReady: z.boolean().optional(),
```

- [ ] **Step 4: Derive it in the cloud store mapping**

In `lib/storage/supabase/supabase-metadata-store.ts:45`, replace the `videos:` mapping with:

```ts
      videos: (rows ?? []).map((r) => ({
        ...(r.data as Video),
        updatedAt: r.updated_at as string,
        summaryReady:
          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
            .artifacts?.summaryMd?.status === 'promoted',
      })),
```

- [ ] **Step 5: Run the derivation test — verify it passes**

Run: `npx jest supabase-metadata-store-summary-ready`
Expected: PASS.

- [ ] **Step 6: Confirm local path untouched + full regression**

Run: `npx jest && npx tsc --noEmit`
Expected: full unit suite green (including all existing local-store and serveLocal tests — they must still pass unchanged, proving the local path is unaffected); 0 type errors.

- [ ] **Step 7: Commit**

```bash
git add types/index.ts lib/storage/supabase/supabase-metadata-store.ts \
        tests/lib/supabase-metadata-store-summary-ready.test.ts
git commit -m "feat(2c): derive cloud-only summaryReady from promoted artifact status"
```

---

## Task 3: `summaryHref` client URL builder (pure)

**Files:**
- Modify: `lib/client/api.ts` (add exported function)
- Test: `tests/lib/client-summary-href.test.ts` *(create)*

**Interfaces:**
- Consumes: nothing (pure).
- Produces: `summaryHref(playlistId: string, videoId: string, opts?: { format?: 'md' | 'html'; download?: boolean }): string`. Tasks 5/6 use it for View/Download links.

**Context:** the cloud html serve route accepts `playlist` (uuid, required), `type=summary` (required), `format` ∈ {`html`,`md`} (default `html`), `download=1`. Param order from `URLSearchParams` insertion: `playlist`, `type`, `format`, `download`. Existing inline precedent: local `VideoMenu.tsx:52`; deep-link builder `lib/html-doc/nav.ts:9-35`.

- [ ] **Step 1: Write the failing test (assert EVERY param)**

Create `tests/lib/client-summary-href.test.ts`:

```ts
import { summaryHref } from '@/lib/client/api';

const PID = '11111111-1111-1111-1111-111111111111';
const VID = 'abc123XYZ_0';

test('view link: playlist + type only, new-tab target', () => {
  const url = new URL(summaryHref(PID, VID), 'https://app.test');
  expect(url.pathname).toBe(`/api/html/${VID}`);
  expect(url.searchParams.get('playlist')).toBe(PID);
  expect(url.searchParams.get('type')).toBe('summary');
  expect(url.searchParams.get('format')).toBeNull();
  expect(url.searchParams.get('download')).toBeNull();
});

test('download markdown: format=md & download=1', () => {
  const url = new URL(summaryHref(PID, VID, { format: 'md', download: true }), 'https://app.test');
  expect(url.searchParams.get('playlist')).toBe(PID);
  expect(url.searchParams.get('type')).toBe('summary');
  expect(url.searchParams.get('format')).toBe('md');
  expect(url.searchParams.get('download')).toBe('1');
});

test('download html: format=html & download=1', () => {
  const url = new URL(summaryHref(PID, VID, { format: 'html', download: true }), 'https://app.test');
  expect(url.searchParams.get('format')).toBe('html');
  expect(url.searchParams.get('download')).toBe('1');
  expect(url.searchParams.get('type')).toBe('summary');
  expect(url.searchParams.get('playlist')).toBe(PID);
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest client-summary-href`
Expected: FAIL with "summaryHref is not a function" / not exported.

- [ ] **Step 3: Implement**

Add to `lib/client/api.ts` (near the other exported helpers):

```ts
/** Builds the serveCloud summary-doc URL. View = no opts; downloads set format + download=1. */
export function summaryHref(
  playlistId: string,
  videoId: string,
  opts?: { format?: 'md' | 'html'; download?: boolean },
): string {
  const params = new URLSearchParams();
  params.set('playlist', playlistId);
  params.set('type', 'summary');
  if (opts?.format) params.set('format', opts.format);
  if (opts?.download) params.set('download', '1');
  return `/api/html/${encodeURIComponent(videoId)}?${params.toString()}`;
}
```

- [ ] **Step 4: Run test — verify it passes**

Run: `npx jest client-summary-href`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/client/api.ts tests/lib/client-summary-href.test.ts
git commit -m "feat(2c): summaryHref client URL builder for cloud doc serve"
```

---

## Task 4: `createShare` / `revokeShare` client seam

**Files:**
- Modify: `lib/client/api.ts` (add exported functions + types)
- Test: `tests/lib/client-share-api.test.ts` *(create)*

**Interfaces:**
- Consumes: `handle<T>` (`lib/client/api.ts:16-25`, throws `UnauthorizedError` on 401), `UnauthorizedError` (`:11`). Task 1's `POST /api/share` 201 `{ id, token, url, expiresAt }` and `POST /api/share/<id>/revoke` 200 `{ revoked }`.
- Produces:
  - `type ShareTtl = 7 | 30 | 'never'`
  - `interface CreateShareResult { id: string; token: string; url: string; expiresAt: string | null }`
  - `createShare(playlistId: string, videoId: string, ttl: ShareTtl): Promise<CreateShareResult>`
  - `revokeShare(shareId: string): Promise<{ revoked: boolean }>`
  Task 5 (`ShareDialog`) consumes both.

**Context:** mirror `saveAnnotation` (`api.ts:88-106`): `fetch` with `method: 'POST'`, `headers: { 'Content-Type': 'application/json' }`, `body: JSON.stringify(...)`, then `handle<T>(res)`. `ttl` passes straight through as `ttlDays` (the route maps `'never'` → null expiry, 7/30 → days). Revoke is bodyless. The dialog composes the full public URL as `window.location.origin + result.url` — `url` here is the path `/s/<token>`.

- [ ] **Step 1: Write the failing tests**

Create `tests/lib/client-share-api.test.ts`:

```ts
import { createShare, revokeShare, UnauthorizedError } from '@/lib/client/api';

const PID = 'p-uuid';
const VID = 'abc123XYZ_0';

afterEach(() => { (global.fetch as jest.Mock)?.mockReset?.(); });

function mockFetch(status: number, body: unknown) {
  global.fetch = jest.fn().mockResolvedValue({
    status, ok: status >= 200 && status < 300,
    json: async () => body,
  }) as unknown as typeof fetch;
}

test('createShare posts playlistId/videoId/ttlDays and returns id+url', async () => {
  mockFetch(201, { id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  const res = await createShare(PID, VID, 30);
  expect(global.fetch).toHaveBeenCalledWith('/api/share', expect.objectContaining({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ playlistId: PID, videoId: VID, ttlDays: 30 }),
  }));
  expect(res).toEqual({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
});

test('createShare forwards ttl "never" as ttlDays', async () => {
  mockFetch(201, { id: 's2', token: 't', url: '/s/t', expiresAt: null });
  await createShare(PID, VID, 'never');
  expect(global.fetch).toHaveBeenCalledWith('/api/share', expect.objectContaining({
    body: JSON.stringify({ playlistId: PID, videoId: VID, ttlDays: 'never' }),
  }));
});

test('createShare maps 401 → UnauthorizedError', async () => {
  mockFetch(401, { error: 'authentication required' });
  await expect(createShare(PID, VID, 7)).rejects.toBeInstanceOf(UnauthorizedError);
});

test('createShare maps non-2xx → Error(body.error)', async () => {
  mockFetch(404, { error: 'not found' });
  await expect(createShare(PID, VID, 7)).rejects.toThrow('not found');
});

test('revokeShare posts to /api/share/<id>/revoke (bodyless) and returns revoked', async () => {
  mockFetch(200, { revoked: true });
  const res = await revokeShare('s-uuid-1');
  expect(global.fetch).toHaveBeenCalledWith('/api/share/s-uuid-1/revoke', { method: 'POST' });
  expect(res).toEqual({ revoked: true });
});

test('revokeShare maps 401 → UnauthorizedError', async () => {
  mockFetch(401, { error: 'authentication required' });
  await expect(revokeShare('s1')).rejects.toBeInstanceOf(UnauthorizedError);
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest client-share-api`
Expected: FAIL — functions not exported.

- [ ] **Step 3: Implement**

Add to `lib/client/api.ts`:

```ts
export type ShareTtl = 7 | 30 | 'never';

export interface CreateShareResult {
  id: string;
  token: string;
  url: string;                 // path only: '/s/<token>' — caller prefixes window.location.origin
  expiresAt: string | null;
}

export async function createShare(
  playlistId: string,
  videoId: string,
  ttl: ShareTtl,
): Promise<CreateShareResult> {
  const res = await fetch('/api/share', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ playlistId, videoId, ttlDays: ttl }),
  });
  return handle<CreateShareResult>(res);
}

export async function revokeShare(shareId: string): Promise<{ revoked: boolean }> {
  const res = await fetch(`/api/share/${encodeURIComponent(shareId)}/revoke`, { method: 'POST' });
  return handle<{ revoked: boolean }>(res);
}
```

- [ ] **Step 4: Run — verify it passes**

Run: `npx jest client-share-api`
Expected: PASS.

> Note the revoke test uses a plain id (`s-uuid-1`) so `encodeURIComponent` is a no-op; real uuids need no escaping either. Keep `encodeURIComponent` for defense.

- [ ] **Step 5: Commit**

```bash
git add lib/client/api.ts tests/lib/client-share-api.test.ts
git commit -m "feat(2c): createShare/revokeShare client seam (401 → UnauthorizedError)"
```

---

## Task 5: `ShareDialog` component

**Files:**
- Create: `components/cloud/ShareDialog.tsx`
- Test: `tests/components/share-dialog.test.tsx` *(create)*

**Interfaces:**
- Consumes: `createShare`, `revokeShare`, `UnauthorizedError`, `CreateShareResult`, `ShareTtl` (Task 4); `useRouter` from `next/navigation` for the 401 redirect (mirror the 2a/2b pattern — `router.replace('/login')`).
- Produces: default export `ShareDialog` with props:
  ```ts
  interface ShareDialogProps {
    playlistId: string;
    videoId: string;
    videoTitle: string;
    onClose: () => void;
  }
  ```
  Task 7 mounts it.

**Behavior (spec §5/§8/§9):**
- TTL radio group: `7d`→`7`, `30d`→`30` (**default selected**), `Never`→`'never'`. Initial focus lands on the TTL group.
- **Before create:** URL field shows placeholder "No link yet"; primary button reads **Create link**. Copy + Revoke disabled/absent.
- **Create** → `createShare(playlistId, videoId, ttl)`; while in flight, disable Create + backdrop + Escape. On success: hold `{ id, url }` in state, populate the readonly URL field with `window.location.origin + url`, enable **Copy** + **Revoke**. Dialog **stays open**.
- **Copy** → `navigator.clipboard.writeText(fullUrl)`; on success show transient "Copied ✓" via an `aria-live="polite"` region; on failure select the URL text (`inputRef.current.select()`) — no thrown error. Dialog stays open.
- **Revoke** → `revokeShare(id)`; while in flight, disable backdrop + Escape. On success clear the held share (URL field back to "No link yet", Copy/Revoke disabled). Dialog stays open.
- **Errors:** `UnauthorizedError` → `router.replace('/login')`. Any other error from create/revoke → inline `role="alert"` line; dialog stays open.
- **Dismissal (§8):** backdrop click, Escape, ✕/Close button → `onClose()`; backdrop + Escape are **disabled while a create/revoke request is in flight**. Create-success and Copy do NOT dismiss.
- **Repeated Create** mints a fresh token; state replaces the held id/url with the newest (spec §1 accepts multiple valid tokens; Revoke targets only the currently-held id).
- **a11y:** `role="dialog"` + `aria-modal="true"`, focus-trapped; focus restore to the trigger is the caller's job (Task 7); error line `role="alert"`; disabled state via `aria-disabled`.

**Tokens (spec §6):** `--border`, `--text`, `--text-muted`, `--bg`, `--bg-elevated`, `--accent`; `--danger` for the error line; backdrop `rgba(0,0,0,.4)`. Use only these — no invented tokens.

> **Implementer:** model structure + focus-trap + in-flight-guard on `components/cloud/NewPlaylistModal.tsx` (Stage 2b) — it already implements `role="dialog"`, `aria-modal`, a focus trap, a `submittingRef` synchronous in-flight guard, and backdrop/Escape dismissal disabled while submitting. Reuse that skeleton; do NOT invent a new modal pattern. A synchronous in-flight ref (like `submittingRef`) must guard BOTH create and revoke so a double-click cannot fire two requests.

- [ ] **Step 1: Write the failing component tests**

Create `tests/components/share-dialog.test.tsx`. Mock the client seam and router:

```tsx
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import ShareDialog from '@/components/cloud/ShareDialog';
import * as api from '@/lib/client/api';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));

const baseProps = { playlistId: 'p1', videoId: 'v1', videoTitle: 'How Transformers Work', onClose: jest.fn() };

beforeEach(() => { jest.restoreAllMocks(); replace.mockReset(); baseProps.onClose = jest.fn(); });

test('before create: shows "No link yet" + Create link; default TTL 30d selected', () => {
  render(<ShareDialog {...baseProps} />);
  expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  expect(screen.getByRole('radio', { name: /30d/i })).toBeChecked();
  expect(screen.getByRole('button', { name: /create link/i })).toBeEnabled();
});

test('create success: URL populated, Copy + Revoke enabled, stays open', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(screen.getByDisplayValue(/\/s\/tok$/)).toBeInTheDocument());
  expect(api.createShare).toHaveBeenCalledWith('p1', 'v1', 30);
  expect(screen.getByRole('button', { name: /copy/i })).toBeEnabled();
  expect(screen.getByRole('button', { name: /revoke/i })).toBeEnabled();
  expect(baseProps.onClose).not.toHaveBeenCalled();
});

test('TTL Never → createShare called with "never"', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('radio', { name: /never/i }));
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(api.createShare).toHaveBeenCalledWith('p1', 'v1', 'never'));
});

test('create error → inline role=alert, stays open', async () => {
  jest.spyOn(api, 'createShare').mockRejectedValue(new Error('bad request'));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/bad request/i));
  expect(baseProps.onClose).not.toHaveBeenCalled();
});

test('create 401 → router.replace(/login)', async () => {
  jest.spyOn(api, 'createShare').mockRejectedValue(new api.UnauthorizedError('unauthorized'));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
});

test('copy success → clipboard write + "Copied" live region', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  const writeText = jest.fn().mockResolvedValue(undefined);
  Object.assign(navigator, { clipboard: { writeText } });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /copy/i }));
  fireEvent.click(screen.getByRole('button', { name: /copy/i }));
  await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining('/s/tok')));
  await waitFor(() => expect(screen.getByText(/copied/i)).toBeInTheDocument());
});

test('copy failure → falls back to selecting URL text, no throw', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  const writeText = jest.fn().mockRejectedValue(new Error('denied'));
  Object.assign(navigator, { clipboard: { writeText } });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /copy/i }));
  const input = screen.getByDisplayValue(/\/s\/tok$/) as HTMLInputElement;
  const select = jest.spyOn(input, 'select');
  fireEvent.click(screen.getByRole('button', { name: /copy/i }));
  await waitFor(() => expect(select).toHaveBeenCalled());
});

test('revoke success → clears held share, back to "No link yet"', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  jest.spyOn(api, 'revokeShare').mockResolvedValue({ revoked: true });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));
  await waitFor(() => expect(api.revokeShare).toHaveBeenCalledWith('s1'));
  await waitFor(() => expect(screen.queryByDisplayValue(/\/s\/tok$/)).not.toBeInTheDocument());
});

test('dismissal: ✕/Close, Escape, backdrop all call onClose', () => {
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /close/i }));
  expect(baseProps.onClose).toHaveBeenCalledTimes(1);

  baseProps.onClose = jest.fn();
  render(<ShareDialog {...baseProps} />);
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(baseProps.onClose).toHaveBeenCalledTimes(1);

  baseProps.onClose = jest.fn();
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByTestId('share-dialog-backdrop'));
  expect(baseProps.onClose).toHaveBeenCalledTimes(1);
});

test('backdrop + Escape are inert while create is in flight', async () => {
  let resolve!: (v: api.CreateShareResult) => void;
  jest.spyOn(api, 'createShare').mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  // in flight now:
  fireEvent.click(screen.getByTestId('share-dialog-backdrop'));
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(baseProps.onClose).not.toHaveBeenCalled();
  await act(async () => { resolve({ id: 's1', token: 't', url: '/s/t', expiresAt: null }); });
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest share-dialog`
Expected: FAIL — component does not exist.

- [ ] **Step 3: Implement `components/cloud/ShareDialog.tsx`**

Implement per the Behavior/a11y/Tokens spec above, reusing the `NewPlaylistModal` skeleton (focus trap, `aria-modal`, in-flight ref guarding BOTH create and revoke, backdrop/Escape disabled in flight). Requirements the tests pin:
- `role="dialog"` + `aria-modal="true"`; title references `videoTitle`.
- TTL radios named 7d/30d/Never; 30d default `checked`.
- Backdrop element carries `data-testid="share-dialog-backdrop"`.
- Primary button label "Create link"; Copy + Revoke buttons.
- Full URL = `window.location.origin + result.url`, shown in a readonly input.
- Copy: `navigator.clipboard.writeText(fullUrl)` → transient "Copied ✓" in an `aria-live="polite"` region; on reject → `inputRef.current?.select()`.
- Error line `role="alert"` shows `err.message`; `UnauthorizedError` → `router.replace('/login')` (import from `@/lib/client/api`).
- A synchronous `inFlightRef` (mirror `submittingRef`) blocks a second create/revoke and gates backdrop/Escape.

- [ ] **Step 4: Run — verify it passes**

Run: `npx jest share-dialog`
Expected: PASS (all blocks).

- [ ] **Step 5: Full regression**

Run: `npx jest && npx tsc --noEmit`
Expected: green; 0 type errors.

- [ ] **Step 6: Commit**

```bash
git add components/cloud/ShareDialog.tsx tests/components/share-dialog.test.tsx
git commit -m "feat(2c): ShareDialog — create/copy/revoke overlay with all dismissal paths"
```

---

## Task 6: `VideoMenu` cloud items (View / Download / Share, readiness-gated)

**Files:**
- Modify: `components/VideoMenu.tsx` (add cloud-branch items + `onShare?` prop)
- Test: `tests/components/video-menu-cloud-2c.test.tsx` *(create)*

**Interfaces:**
- Consumes: `summaryHref` (Task 3); `Video.summaryReady` (Task 2); existing `useScope()` (`VideoMenu.tsx:44`, gives `scope.playlistId` in cloud mode); existing `cloudMode` boolean (`:49`).
- Produces: `VideoMenuProps` gains `onShare?: () => void`. Task 7 passes it.

**Behavior (spec §4/§5/§6):** in `cloudMode`, after *Watch on YouTube* and before *Archive*, render four items:
- **View summary** — anchor `href={summaryHref(scope.playlistId, video.id)}` `target="_blank" rel="noopener noreferrer"`.
- **Download Markdown** — anchor `href={summaryHref(scope.playlistId, video.id, { format: 'md', download: true })}` with the `download` attribute.
- **Download HTML** — anchor `href={summaryHref(scope.playlistId, video.id, { format: 'html', download: true })}` with `download`.
- **Share…** — button `onClick={() => { onShare?.(); onClose(); }}`.

When `!video.summaryReady`: render all four **disabled** — as a non-interactive `<span>` (not an anchor/active button) with `aria-disabled="true"` and `title="Finalizing…"`. Local mode (`!cloudMode`) is completely unchanged (the field is ignored).

> **Guard:** `scope.playlistId` is only present in cloud mode; these items render inside the `cloudMode` branch, so it is always defined there. Do not call `summaryHref` in local mode.

- [ ] **Step 1: Write the failing tests**

Create `tests/components/video-menu-cloud-2c.test.tsx`. Render `VideoMenu` inside a cloud `ScopeProvider` (mirror how existing `VideoMenu` cloud tests set scope — reuse that wrapper/helper):

```tsx
// ready state:
test('cloud + summaryReady: View/Download/Share render with exact hrefs', () => {
  renderCloud(<VideoMenu {...cloudProps} video={{ ...video, summaryReady: true }} onShare={onShare} />);
  const view = screen.getByRole('link', { name: /view summary/i });
  expect(view).toHaveAttribute('target', '_blank');
  expect(view).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=summary`);

  const md = screen.getByRole('link', { name: /download markdown/i });
  expect(md).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=summary&format=md&download=1`);
  expect(md).toHaveAttribute('download');

  const html = screen.getByRole('link', { name: /download html/i });
  expect(html).toHaveAttribute('href', `/api/html/${video.id}?playlist=${PID}&type=summary&format=html&download=1`);

  fireEvent.click(screen.getByRole('button', { name: /share/i }));
  expect(onShare).toHaveBeenCalledTimes(1);
});

test('cloud + NOT ready: the four items are disabled with "Finalizing…" and no href', () => {
  renderCloud(<VideoMenu {...cloudProps} video={{ ...video, summaryReady: false }} onShare={onShare} />);
  const view = screen.getByText(/view summary/i);
  expect(view).toHaveAttribute('aria-disabled', 'true');
  expect(view).toHaveAttribute('title', 'Finalizing…');
  expect(screen.queryByRole('link', { name: /view summary/i })).not.toBeInTheDocument();
  // Share disabled → clicking does nothing
  const share = screen.getByText(/share/i);
  fireEvent.click(share);
  expect(onShare).not.toHaveBeenCalled();
});

test('local mode: 2c items absent, existing menu unchanged', () => {
  renderLocal(<VideoMenu {...localProps} video={{ ...video, summaryReady: undefined }} />);
  expect(screen.queryByText(/view summary/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/download markdown/i)).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: /watch on youtube/i })).toBeInTheDocument();
});
```

Assert **every** query param on each link (per the E2E link-assertion rule) — the hrefs above list them all: `playlist`, `type`, and for downloads `format` + `download`.

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest video-menu-cloud-2c`
Expected: FAIL — items not rendered / `onShare` prop unknown.

- [ ] **Step 3: Implement**

Add `onShare?: () => void` to `VideoMenuProps` (`components/VideoMenu.tsx:8-19`). Inside the `cloudMode` branch (after *Watch on YouTube*, before *Archive*), render the four items. Suggested helper for the ready/disabled fork within cloud:

```tsx
const ready = video.summaryReady === true;
const pid = scope.mode === 'cloud' ? scope.playlistId : '';
// View summary
ready ? (
  <li><a role="menuitem" href={summaryHref(pid, video.id)} target="_blank" rel="noopener noreferrer"
         onClick={onClose}>View summary ↗</a></li>
) : (
  <li><span aria-disabled="true" title="Finalizing…" className="/* muted token */">View summary ↗</span></li>
)
// Download Markdown / HTML: same fork, anchors carry `download`; disabled → span with the same title.
// Share…:
ready ? (
  <li><button type="button" role="menuitem" onClick={() => { onShare?.(); onClose(); }}>Share…</button></li>
) : (
  <li><span aria-disabled="true" title="Finalizing…">Share…</span></li>
)
```

Match the existing menu's markup/class conventions (see the *Watch on YouTube* `<li>` at `VideoMenu.tsx:59-63`). Use only the spec §6 tokens for the muted/disabled look.

- [ ] **Step 4: Run — verify it passes**

Run: `npx jest video-menu-cloud-2c`
Expected: PASS. Also run the existing `VideoMenu` suite to confirm no regressions: `npx jest VideoMenu`.

- [ ] **Step 5: Full regression**

Run: `npx jest && npx tsc --noEmit`
Expected: green; 0 type errors.

- [ ] **Step 6: Commit**

```bash
git add components/VideoMenu.tsx tests/components/video-menu-cloud-2c.test.tsx
git commit -m "feat(2c): cloud VideoMenu — View/Download/Share gated on summaryReady"
```

---

## Task 7: `VideoRow` wiring — mount `ShareDialog`, restore focus

**Files:**
- Modify: `components/VideoRow.tsx`
- Test: `tests/components/video-row-share-2c.test.tsx` *(create)*

**Interfaces:**
- Consumes: `ShareDialog` (Task 5); `VideoMenu`'s new `onShare` prop (Task 6); `useScope()` for `playlistId`.
- Produces: no external interface change (VideoRow props unchanged).

**Behavior:** mirror the existing corrections wiring (`onEditCorrections={() => setShowCorrections(true)}` → `{showCorrections && <CorrectionsPanel .../>}`):
- Add `const [showShare, setShowShare] = useState(false);`.
- Add a ref for the ☰ menu trigger button (`components/VideoRow.tsx:98-107`): `const menuTriggerRef = useRef<HTMLButtonElement>(null)`, attach to that button.
- Pass `onShare={() => { setMenuOpen(false); setShowShare(true); }}` to `VideoMenu`.
- Read scope: `const scope = useScope(); const playlistId = scope.mode === 'cloud' ? scope.playlistId : '';`.
- Render when open:
  ```tsx
  {showShare && (
    <ShareDialog
      playlistId={playlistId}
      videoId={video.id}
      videoTitle={video.title}
      onClose={() => { setShowShare(false); menuTriggerRef.current?.focus(); }}
    />
  )}
  ```
- Focus restore: on close, focus returns to `menuTriggerRef`.

> ShareDialog only mounts in cloud mode in practice (the Share… item only appears in cloud), but VideoRow reads scope unconditionally — `playlistId` is `''` in local mode and the dialog is never opened there. Keep `useScope()` unconditional (it is already under `ScopeProvider`).

- [ ] **Step 1: Write the failing test**

Create `tests/components/video-row-share-2c.test.tsx`. Render a `VideoRow` in a cloud `ScopeProvider` with a table wrapper (mirror existing VideoRow cloud tests):

```tsx
test('cloud: Share… opens ShareDialog; closing restores focus to the ☰ trigger', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  renderCloudRow({ ...video, summaryReady: true });

  fireEvent.click(screen.getByRole('button', { name: /menu/i }));       // open ☰
  fireEvent.click(screen.getByRole('button', { name: /share/i }));      // Share…
  expect(await screen.findByRole('dialog')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /close/i }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  expect(screen.getByRole('button', { name: /menu/i })).toHaveFocus();  // focus restored
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest video-row-share-2c`
Expected: FAIL — no dialog opens / focus not restored.

- [ ] **Step 3: Implement the wiring** in `components/VideoRow.tsx` per the Behavior block (import `useRef` from `react` and `ShareDialog` from `./cloud/ShareDialog`; the ☰ button is at `:98-107`).

- [ ] **Step 4: Run — verify it passes**

Run: `npx jest video-row-share-2c`
Expected: PASS. Also `npx jest VideoRow` — no regressions.

- [ ] **Step 5: Full regression**

Run: `npx jest && npx tsc --noEmit`
Expected: green; 0 type errors.

- [ ] **Step 6: Commit**

```bash
git add components/VideoRow.tsx tests/components/video-row-share-2c.test.tsx
git commit -m "feat(2c): VideoRow mounts ShareDialog; focus restored to menu trigger"
```

---

## Task 8: Integration — real-Supabase round-trip + `summaryReady` reflection

**Files:**
- Create: `tests/integration/share-summary-2c.test.ts`

**Interfaces:**
- Consumes: the real Supabase test harness (`signInAs` / session-client helpers used by existing `tests/integration/share-tokens-rpc.test.ts` and the 2b `jobs-poll-banner.test.ts`); `SupabaseMetadataStore.readIndex` (Task 2); `create_share_token` / `revoke_share_token` RPCs via each user's session client.
- Produces: no code — an end-to-end guard proving owner isolation + the readiness DTO reflection under real RLS.

**Behavior to assert:**
1. **Share create + revoke round-trip (owner A):** A signs in, seeds a *promoted* video, creates a share (RPC returns `{ id, expires_at }`), then revokes by that id → `revoked: true`. A second revoke of the same id → `revoked: false` (already revoked).
2. **Owner isolation:** user B (separate session client) attempts `revoke_share_token(A_share_id)` → `revoked: false` (RLS scopes by `auth.uid()`; B cannot revoke A's share). No error leak.
3. **`summaryReady` reflection:** through `SupabaseMetadataStore.readIndex` for owner A, a video whose `artifacts.summaryMd.status === 'promoted'` yields `summaryReady === true`; a `committed` (or artifacts-absent) video yields `summaryReady === false`.

- [ ] **Step 1: Write the integration test** using the existing real-Supabase helpers (copy the `signInAs` + seeding scaffolding from `tests/integration/share-tokens-rpc.test.ts`). Assert the three behaviors above. Include `expect(error).toBeNull()` on the happy-path RPC calls (mirror the 2b integration hardening).

- [ ] **Step 2: Run — verify it passes against a fresh DB**

Run: `npx supabase db reset && npm run test:integration -- share-summary-2c --runInBand`
Expected: PASS.

- [ ] **Step 3: Full integration suite (no regressions)**

Run: `npx supabase db reset && npm run test:integration -- --runInBand`
Expected: all green (the `0017` migration applied cleanly; existing share + producer + serve integration tests still pass).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/share-summary-2c.test.ts
git commit -m "test(2c): integration — share round-trip, owner isolation, summaryReady reflection"
```

---

## Verification (end of stage)

1. `npx tsc --noEmit` — 0 errors.
2. `npx jest` — full unit suite green (grows with 2c tests).
3. `npx supabase db reset && npm run test:integration -- --runInBand` — all green (including `0017` migration + Task 8).
4. **Local app untouched:** `git diff master -- components/local app/api/ingest` is empty; all existing local-store / serveLocal / VideoMenu-local tests pass unchanged.
5. **Spec coverage:** View (§5), Download MD/HTML (§5), Share create/copy/revoke (§5/§8), `summaryReady` gate (§2/§3), URL contracts (§7 — every param asserted in Tasks 3/6), overlay dismissal (§8 — all paths + in-flight guard in Task 5), error handling (§9 — 401 redirect, inline errors, clipboard fallback).
6. Each 2c task has both `docs/reviews/task-2c-N-<name>-review.md` (Claude) and `-codex.md` (Codex) saved; all High/Important findings addressed; §12-flagged Tasks 1 & 2 re-reviewed to convergence after any High fix.
7. Whole-branch dual review CLEAN → `superpowers:finishing-a-development-branch` → PR to `master` (use `--repo kujinlee/youtube-playlist-summaries-cloud`; two-remotes footgun).

## Self-Review notes (author)

- **Spec coverage:** every §4 component + §5 action + §7 URL + §8 dismissal maps to a task (5/6 above). No orphan requirements.
- **Type consistency:** `CreateShareResult` (id/token/url/expiresAt) is produced by Task 1's route, typed in Task 4, consumed in Task 5 — names match. `summaryReady` optional-boolean produced in Task 2, gated in Tasks 6/7. `ShareTtl` (7|30|'never') from Task 4 used by Task 5's TTL mapping.
- **No placeholders:** all SQL, route, builder, and test code is literal; component internals (Tasks 5/7) give exact prop/behavior/testid contracts the tests pin, with `NewPlaylistModal` named as the skeleton to reuse (DRY — no re-derived modal pattern).
- **Ordering:** backend id (T1) → DTO flag (T2) → pure builder (T3) → client seam (T4) → dialog (T5) → menu (T6) → row wiring (T7) → integration (T8). Each task's Consumes are satisfied by an earlier task.
