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
- **Design tokens that EXIST (use ONLY these; jest/jsdom cannot catch an invalid CSS var, so a wrong token ships an unstyled component — this is the exact defect the 2b review caught):** `--surface-base`, `--surface-raised`, `--surface-overlay`, `--border`, `--border-strong`, `--text-primary`, `--text-secondary`, `--text-muted`, `--accent`, `--success`, `--warning`, `--danger` (all in `app/globals.css`). Modal backdrop uses literal `rgba(0,0,0,.4)` (matches `NewPlaylistModal`). **The spec §6 token names `--bg`, `--bg-elevated`, `--text` are WRONG (do not exist) — they map to `--surface-base`, `--surface-raised`, `--text-primary` respectively. `NewPlaylistModal.tsx` already uses the correct set; copy from it, not from spec §6.**

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

**Context the brief cannot know:** Postgres cannot `CREATE OR REPLACE` a function across a return-type change, so the migration must `DROP FUNCTION` then `CREATE`. Dropping a function also drops its `GRANT EXECUTE`, so the grant to `authenticated` (from `0013:86`) **must be re-applied** in `0017`. The `RETURNING` clause is qualified as `share_tokens.id` to avoid ambiguity with the new `id` OUT column. Logic (owner check, hash-format check, TTL bound, promoted predicate, insert) is otherwise byte-identical to `0013`. The whole migration runs in one transaction, so the RPC is never *missing* mid-migration.

**Deploy-ordering note (Codex H3 — accepted as documented):** the return type changes scalar→row, so the route change and the migration are a matched pair. **Deploy migration `0017` and the route change together in a single atomic deploy** (this project applies migrations + app code together, not as a rolling blue-green with live share-create traffic). During a hypothetical version-skew window, new-route-vs-old-RPC returns 404 on every create, and old-route-vs-new-RPC reads `data` as an array — both self-heal once both halves land. If a future rolling-deploy model is ever adopted, prefer a versioned RPC name (`create_share_token_v2`) instead of DROP+CREATE. For the current atomic-deploy model, no version-skew window exists.

**Caller audit (Codex M1 / Claude L3 — accepted):** `grep -rn create_share_token` returns exactly three non-defining sites: `app/api/share/route.ts` (migrated in this task), `tests/integration/share-tokens-rpc.test.ts`, and `tests/api/share-mint-route.test.ts`. In `share-tokens-rpc.test.ts`, only the **"returns expires_at"** test (≈`:15-28`) *reads* the RPC return; the other ~10 calls are seeding calls that ignore `data` and need no change. **Keep** that test's existing row-exists/owner assertions (`:26-28`) — only the return-shape assertion changes.

- [ ] **Step 1: Write the failing integration test (RPC returns id)**

Open `tests/integration/share-tokens-rpc.test.ts`. Find the `create_share_token` happy-path call (it currently reads `data` as the scalar expiry). Change that assertion block to expect a single-row result carrying `id` and `expires_at`:

```ts
// After signInAs(userA) and seeding a promoted video (existing helpers in this file).
// KEEP the original row-exists / owner assertions (share-tokens-rpc.test.ts:26-28);
// only the return-shape assertion changes from scalar to a single row.

// (a) 'never' expiry → returns a row with id + expires_at: null
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

// (b) non-null expiry round-trips (Codex M2): returned expires_at echoes the input.
// Use a SECOND distinct token hash — token_hash is UNIQUE.
const iso = new Date(Date.now() + 7 * 864e5).toISOString();
const { data: data2, error: err2 } = await userAClient.rpc('create_share_token', {
  p_playlist_id: playlistId, p_video_id: videoId, p_expiry: iso, p_token_hash: tokenHash2,
});
expect(err2).toBeNull();
const row2 = Array.isArray(data2) ? data2[0] : data2;
expect(row2.id).toMatch(/^[0-9a-f-]{36}$/i);
expect(new Date(row2.expires_at).getTime()).toBeCloseTo(new Date(iso).getTime(), -3); // ~seconds
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

Open `tests/api/share-mint-route.test.ts`. **Critical (Claude M3):** this file's `beforeEach` default mock (`:19`) currently resolves the rpc to a **scalar** ISO string:
```ts
mockRpc = jest.fn(async () => ({ data: new Date(Date.now() + 30 * 864e5).toISOString(), error: null }));
```
After the route change (`Array.isArray(data) ? data[0] : null`), a scalar default yields `row = null` → 404, so **every happy-path test that does not override the mock breaks**. Change the default to a **single-row array** — and keep `expires_at` a **STRING** (not null), because the existing "201" test (`:37`) asserts `typeof body.expiresAt === 'string'`; a null would break it. The mock variable is named **`mockRpc`** (not `rpc`):

```ts
// beforeEach default (line 19): scalar → single-row array, expires_at stays an ISO string
mockRpc = jest.fn(async () => ({
  data: [{ id: 'share-uuid-1', expires_at: new Date(Date.now() + 30 * 864e5).toISOString() }],
  error: null,
}));
```

Then, in the existing "201 returns { token, url, expiresAt }" test (`:30-40`), **add** an `id` assertion alongside the existing ones (do NOT replace the whole body with a strict `toEqual` — the expiry is a live timestamp):

```ts
expect(res.status).toBe(201);
const body = await res.json();
expect(body.id).toBe('share-uuid-1');
expect(typeof body.token).toBe('string');
expect(body.url).toMatch(/^\/s\/.+/);
expect(typeof body.expiresAt).toBe('string');   // unchanged — still holds with the string expiry
```

Keep the existing error-path assertions (400 missing fields, 400 invalid ttl, 401 no user) unchanged. The rpc-error/denial path already mocks `{ data: null, error: {...} }` (`:58`) → `row = null` → still 404, correct as-is.

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
- Modify: `lib/storage/supabase/supabase-metadata-store.ts` — `readIndex` mapping (~`:45`) AND `stripComputed` (~`:14`)
- Test: `tests/lib/supabase-metadata-store-summary-ready.test.ts` *(create)*

**Interfaces:**
- Consumes: `VideoSchema` / `type Video` (`types/index.ts:47-83`); `readIndex` mapping in `SupabaseMetadataStore` (`lib/storage/supabase/supabase-metadata-store.ts:25-47`), which already derives the cloud-only `updatedAt` at `:45`.
- Produces: `Video.summaryReady?: boolean` — `true` iff the cloud row's `data.artifacts.summaryMd.status === 'promoted'`, else `false`; `undefined` on the local path. Tasks 6/7 gate on it.

**Context the brief cannot know:** `artifacts` is NOT a typed field on `VideoSchema` — it lives only in the DB `videos.data` jsonb and is read via ad-hoc casts (`app/api/html/[id]/route.ts:55`, `lib/share/serve.ts:44`). The canonical readiness predicate `artifacts.summaryMd.status === 'promoted'` is used at those sites + `lib/job-queue/summary-handler.ts:87`. `BlobStatus` = `'pending' | 'committed' | 'promoted' | 'repair_needed'` (`lib/storage/blob-store.ts:3`). serveLocal (`app/api/videos/route.ts:94-128`) and serveCloud (`:134-176`) are separate functions but share the `Video` type via `sortVideos`; the local store (`LocalMetadataStore.readIndex`) has no `artifacts`, so making the field `.optional()` and deriving it only cloud-side leaves local `undefined` — identical to the `updatedAt` precedent.

**Invariant to preserve (Claude M2 — REQUIRED):** `summaryReady` is a **read-computed** key exactly like `updatedAt` — derived from the DB row on read, never a source-of-truth field in `videos.data`. `stripComputed<T>(v)` (`supabase-metadata-store.ts:14`) strips `updatedAt` before **every** write to `videos.data` (it guards `upsertVideo`, `updateVideoFields`, `bulkUpdateVideoFields`) precisely so a read-surfaced computed key can never round-trip into the jsonb. `summaryReady` **must be added to `stripComputed`** too. No current caller round-trips a `readIndex`-sourced `Video` back to a write, so nothing breaks today — but omitting it silently breaks the stated invariant and risks a future write baking a stale `summaryReady` into `videos.data` (where the serving route would then read a lie). This is a required step, not optional polish.

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

In `lib/storage/supabase/supabase-metadata-store.ts` (~`:45`), replace the `videos:` mapping with:

```ts
      videos: (rows ?? []).map((r) => ({
        ...(r.data as Video),
        updatedAt: r.updated_at as string,
        summaryReady:
          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
            .artifacts?.summaryMd?.status === 'promoted',
      })),
```

- [ ] **Step 5: Add `summaryReady` to `stripComputed` (write-side invariant)**

In the same file (~`:14`), extend `stripComputed` so `summaryReady` (like `updatedAt`) can never round-trip into `videos.data`:

```ts
function stripComputed<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
  return rest;
}
```

Also update the block comment above it (which currently explains only `updatedAt`) to note that `summaryReady` is likewise a read-computed key derived from `artifacts.summaryMd.status` and must never persist to the jsonb.

- [ ] **Step 6: Write + run the strip test (mirror the existing `updatedAt` strip test)**

Find the existing test that asserts `updatedAt` is stripped before a write (search `tests/` for `stripComputed` or the `updatedAt` write-strip assertion, e.g. in a `supabase-metadata-store` write test). Add a sibling assertion — pass a `Video` carrying `summaryReady: true` (and `updatedAt`) into `upsertVideo`, capture the payload written to `videos.data`, and assert **neither** `summaryReady` **nor** `updatedAt` appears:

```ts
// with the store's write path mocked to capture the persisted `data`:
await store.upsertVideo(principal, { ...videoFixture, updatedAt: 'x', summaryReady: true } as any);
const persisted = capturedInsert.data;         // the object written to videos.data
expect(persisted).not.toHaveProperty('summaryReady');
expect(persisted).not.toHaveProperty('updatedAt');
```

Run: `npx jest supabase-metadata-store` — the derivation test and the strip test both pass.

- [ ] **Step 7: Migrate existing exact-shape `readIndex` assertions (Codex R2-H2 — REQUIRED)**

The derivation adds a **concrete `false`** for artifacts-absent rows (`undefined?.summaryMd?.status === 'promoted'` → `false`, NOT `undefined`). `updatedAt` is currently `undefined` in these fixtures and `toEqual` ignores undefined props — but a concrete `false` is **not** ignored, so any existing exact `toEqual` on `idx.videos` breaks. Before running the suite, grep and migrate:

```bash
grep -rn "idx.videos).toEqual\|\.videos).toEqual" tests/
```

Known site: `tests/lib/storage/supabase-metadata-store.test.ts:159` —
```ts
// before:
expect(idx.videos).toEqual([{ id: 'v1' }, { id: 'v2' }]);
// after (rows have no artifacts → summaryReady: false):
expect(idx.videos).toEqual([{ id: 'v1', summaryReady: false }, { id: 'v2', summaryReady: false }]);
```
Update every exact-shape `readIndex` assertion the grep finds the same way (add `summaryReady: false`, or `true` if that fixture's `data.artifacts.summaryMd.status === 'promoted'`). Do NOT weaken a `toEqual` to `toMatchObject` to dodge it — the point is that the shape genuinely changed.

- [ ] **Step 8: Confirm local path untouched + full regression**

Run: `npx jest && npx tsc --noEmit`
Expected: full unit suite green (including all existing local-store and serveLocal tests — they must still pass unchanged, proving the local path is unaffected); 0 type errors.

- [ ] **Step 9: Commit**

```bash
git add types/index.ts lib/storage/supabase/supabase-metadata-store.ts \
        tests/lib/supabase-metadata-store-summary-ready.test.ts
git commit -m "feat(2c): derive cloud-only summaryReady (promoted); strip it before writes"
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

test('videoId with reserved chars is percent-encoded in the path', () => {
  // proves encodeURIComponent(videoId) is actually load-bearing
  const href = summaryHref(PID, 'a/b?c#d', { format: 'md', download: true });
  expect(href.startsWith('/api/html/a%2Fb%3Fc%23d?')).toBe(true);
  const url = new URL(href, 'https://app.test');
  expect(url.pathname).toBe('/api/html/a%2Fb%3Fc%23d');
  expect(url.searchParams.get('format')).toBe('md');   // query intact, not swallowed by the '?'
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

**Tokens (REAL names — the spec §6 list is wrong; see Global Constraints):** `--surface-base` (dialog body), `--surface-raised`/`--surface-overlay` (elevated field/panel), `--border`, `--text-primary`, `--text-muted`, `--accent`; `--danger` for the error line; backdrop `rgba(0,0,0,.4)`. Use **only** tokens that exist in `app/globals.css` — `--bg`, `--bg-elevated`, `--text` do NOT exist. Copy the exact token usage from `NewPlaylistModal.tsx` (`--surface-base`, `--text-primary`, `--text-muted`, `--border`, `--accent`, `--danger`).

> **Implementer:** model structure + focus-trap + in-flight-guard on `components/cloud/NewPlaylistModal.tsx` (Stage 2b) — it already implements `role="dialog"`, `aria-modal`, a focus trap, a `submittingRef` synchronous in-flight guard, and backdrop/Escape dismissal disabled while submitting. Reuse that skeleton; do NOT invent a new modal pattern. A synchronous in-flight ref (like `submittingRef`) must guard BOTH create and revoke so a double-click cannot fire two requests.
>
> **Focus restore is the CALLER's job — drop the modal's self-restore (Claude M4).** `NewPlaylistModal` restores focus itself via `useEffect(() => { …; return () => returnFocusRef.current?.focus(); }, [])` capturing `document.activeElement` at mount. Task 7 (`VideoRow`) restores focus to the ☰ trigger in `onClose`. If you keep the modal's self-restore, on close the modal's unmount cleanup focuses the *stale* captured element, overriding the trigger and **failing Task 7's `toHaveFocus()` test**. When adapting the skeleton, **remove the self-restore cleanup** so `VideoRow` is the sole focus-restore owner. Keep the initial-focus-into-the-dialog effect (focus the TTL group on mount).

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

test('TTL 7d → createShare called with 7', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('radio', { name: /7d/i }));
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => expect(api.createShare).toHaveBeenCalledWith('p1', 'v1', 7));
});

test('rapid double-click Create fires createShare exactly once (synchronous in-flight guard)', async () => {
  let resolve!: (v: api.CreateShareResult) => void;
  const spy = jest.spyOn(api, 'createShare').mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  const btn = screen.getByRole('button', { name: /create link/i });
  fireEvent.click(btn);
  fireEvent.click(btn);   // second click while first is pending
  expect(spy).toHaveBeenCalledTimes(1);
  await act(async () => { resolve({ id: 's1', token: 't', url: '/s/t', expiresAt: null }); });
});

test('rapid double-click Revoke fires revokeShare exactly once', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  let resolve!: (v: { revoked: boolean }) => void;
  const spy = jest.spyOn(api, 'revokeShare').mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  const rb = screen.getByRole('button', { name: /revoke/i });
  fireEvent.click(rb);
  fireEvent.click(rb);
  expect(spy).toHaveBeenCalledTimes(1);
  await act(async () => { resolve({ revoked: true }); });
});

test('backdrop + Escape are inert while REVOKE is in flight', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 't', url: '/s/t', expiresAt: null });
  let resolve!: (v: { revoked: boolean }) => void;
  jest.spyOn(api, 'revokeShare').mockReturnValue(new Promise((r) => { resolve = r; }));
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));   // revoke pending
  fireEvent.click(screen.getByTestId('share-dialog-backdrop'));
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(baseProps.onClose).not.toHaveBeenCalled();
  await act(async () => { resolve({ revoked: true }); });
});

test('a11y: initial focus lands in the dialog; Tab from the last focusable wraps to the first', () => {
  // The trap is a manual keydown handler (mirroring NewPlaylistModal:29-41): it only wraps when
  // document.activeElement === last (Tab) or === first (Shift+Tab). jsdom does NOT move focus on a
  // Tab keydown by itself, so the test must FOCUS the last element first to exercise the wrap branch —
  // otherwise the handler is a no-op and the assertion is vacuous.
  render(<ShareDialog {...baseProps} />);
  const dialog = screen.getByRole('dialog');
  expect(dialog.contains(document.activeElement)).toBe(true);        // initial focus inside dialog
  // Query focusables in DOM order using the SAME selector family the trap handler uses, so the
  // test's notion of first/last matches the handler's:
  const focusables = dialog.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  last.focus();
  fireEvent.keyDown(dialog, { key: 'Tab' });
  expect(document.activeElement).toBe(first);                        // wrapped to first (not <body>)
});

test('revoke no-op ({revoked:false}) still clears the held share (acceptable for 2c)', async () => {
  jest.spyOn(api, 'createShare').mockResolvedValue({ id: 's1', token: 'tok', url: '/s/tok', expiresAt: null });
  jest.spyOn(api, 'revokeShare').mockResolvedValue({ revoked: false });  // already-revoked / non-owned
  render(<ShareDialog {...baseProps} />);
  fireEvent.click(screen.getByRole('button', { name: /create link/i }));
  await waitFor(() => screen.getByRole('button', { name: /revoke/i }));
  fireEvent.click(screen.getByRole('button', { name: /revoke/i }));
  await waitFor(() => expect(screen.queryByDisplayValue(/\/s\/tok$/)).not.toBeInTheDocument());
});
```

> **Honest test note (Codex R2-M2 — 2b act-flush precedent):** the two rapid-double-click tests assert `createShare`/`revokeShare` is called exactly once, but RTL cannot fully *isolate* the synchronous `inFlightRef` from ordinary state-based button-disable: `fireEvent.click` runs inside `act()`, which flushes the first click's `setState` (disabling the button) before the second event dispatches, so the test can pass with state-disable alone and no ref. Keep both tests (they guard the observable "one request per intent" contract) AND still implement the synchronous `inFlightRef` — it closes the sub-frame window between the click handler firing and React committing the disabled state, which state-disable alone leaves open. This is a correctness-by-construction requirement (same conclusion the 2b whole-branch review reached for the Refresh/modal spend paths), not something RTL can prove here. Note share-create does **not** charge, so this is defense-in-depth (duplicate tokens are explicitly acceptable per spec §1), not a money-gate.

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
- A single synchronous `inFlightRef` (mirror `submittingRef`) blocks a second create AND a second revoke, and gates backdrop/Escape while either request is pending.
- **Initial focus** lands inside the dialog on mount (the TTL group / default-checked 30d radio). **Do NOT** include the modal's self focus-restore cleanup — `VideoRow` (Task 7) owns restoring focus to the ☰ trigger (see the M4 note above).
- **Revoke resolution:** clear the held share on any *resolved* revoke regardless of the `{ revoked }` boolean — `{ revoked: false }` (already-revoked / non-owned id) is a 200, not an error, and 2c treats it as "the link is gone." Only a *thrown* error (non-2xx) shows the inline alert.

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

Add `onShare?: () => void` to `VideoMenuProps` (`components/VideoMenu.tsx:8-19`). Inside the `cloudMode` branch (after *Watch on YouTube*, before *Archive*), render the four items. **Match the existing menu markup EXACTLY** — existing items are `<li role="none"><a className={itemClass}>…</a></li>` / `<button>` with **no `role="menuitem"`** (the *Watch on YouTube* `<li>` at `VideoMenu.tsx:59-63` is the template). **Do NOT add `role="menuitem"` to the new anchors** — an `<a href>` with an explicit `role="menuitem"` is no longer exposed as a `link`, which breaks the Step-1 `getByRole('link')` assertions (Claude M1). Ready/disabled fork:

```tsx
const ready = video.summaryReady === true;
const pid = scope.mode === 'cloud' ? scope.playlistId : '';   // cloudMode branch → always cloud scope
// View summary
ready ? (
  <li role="none"><a className={itemClass} href={summaryHref(pid, video.id)}
         target="_blank" rel="noopener noreferrer" onClick={onClose}>View summary ↗</a></li>
) : (
  <li role="none"><span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>View summary ↗</span></li>
)
// Download Markdown / HTML: same fork; anchors add the `download` attribute + the format/download opts;
//   disabled → <span aria-disabled title="Finalizing…"> (NO href).
// Share… (button, not a link — so role is fine to omit; match existing button items):
ready ? (
  <li role="none"><button type="button" className={itemClass}
        onClick={() => { onShare?.(); onClose(); }}>Share…</button></li>
) : (
  <li role="none"><span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>Share…</span></li>
)
```

Reuse the existing `itemClass` string this menu already applies to its `<a>`/`<button>` items; for the muted/disabled variant use the real `--text-muted` token (see Global Constraints — do NOT use `--text`/`--bg`). **`pid` guard (L1):** these items live inside the `cloudMode` branch where `scope.mode === 'cloud'`, so `scope.playlistId` is defined; do not call `summaryHref` outside that branch.

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
