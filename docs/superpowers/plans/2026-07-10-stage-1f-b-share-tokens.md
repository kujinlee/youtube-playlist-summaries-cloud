# Stage 1F-b — Share Tokens Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a summary-doc owner mint an opaque capability link (`/s/<token>`) that grants unauthenticated read-only access to exactly one rendered summary HTML doc, without ever spending the owner's money.

**Architecture:** A new generate-free leaf module (`read-model.ts`) makes "the share path never generates/charges" structural — importing it into the anonymous route cannot pull in the Gemini/reserve code. A `force`-RLS `share_tokens` table with four `SECURITY DEFINER` RPCs (create/revoke/revoke-all/list) owns all writes; the anonymous `/s/[token]` route validates the token and does a read-only, token-gated `service_role` fetch of exactly one doc's blobs, guarded against confused-deputy by resolving on the global `(playlist_id, owner_id)`.

**Tech Stack:** Next.js (route handlers), Supabase (Postgres + storage, RLS + definer RPCs), TypeScript (strict), Zod, jest + ts-jest (unit), real-DB integration (`--runInBand`). No ESLint in this repo — static guards are jest grep tests.

**Spec:** `docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md` (v4 CONVERGED). Behaviors B1–B24 in spec §6 are the test contract.

## Global Constraints

- **Never charges (D2/D13):** the share path calls NO `reserve_serve_model` RPC, NO `generateMagazineModel`, and never touches `spend_ledger`/`serve_model_charge`. Proven by B18 (rows unchanged + zero-call spy on `SupabaseClient.prototype.rpc`), B18b (a **jest grep guard** — the repo has NO ESLint, so `no-restricted-imports` is unavailable; the guard greps share sources for forbidden imports/`.rpc('reserve_serve_model')`), B18c (`read-model.ts` module graph never reaches `@/lib/gemini`).
- **Token hash storage:** `share_tokens.token_hash` is **`text` holding the lowercase hex of the SHA-256** (64 chars), NOT `bytea`. Reason: a Node `Buffer` passed as a `bytea` RPC arg / `.eq()` filter over PostgREST serializes as a JSON object, not a Postgres bytea — mint and lookup would silently break. Hex-text is the faithful "SHA-256-hashed at rest" storage (spec D6) with a format CHECK.
- **One privileged surface (D4/D16):** the anonymous route is the only new `service_role` user; it uses a **runtime `get`-only wrapper** `{ get: store.get.bind(store) }`, never a full `SupabaseBlobStore` on the serve path.
- **Confused-deputy guard (D15):** resolve the doc by global `playlist_id AND owner_id` (never `readIndex`, which keys on per-owner-unique `playlist_key`) and assert the resolved `owner_id` equals the token row's. Copy `getWorkerStorageBundle` (`lib/storage/resolve.ts:71`).
- **Token (D5/D6):** 256-bit `crypto.randomBytes(32)`, base64url, in the URL; stored SHA-256-hashed (32 bytes). Plaintext generated in the mint route, returned once, never stored/logged.
- **Expiry (D7):** owner-set at mint (omitted→30d, `'never'`→null, `1..365`→days, else 400), enforced in BOTH the route (UX 400) AND the definer RPC (`p_expiry IS NULL OR (p_expiry > now() AND p_expiry <= now() + make_interval(days => 365) + interval '1 hour')` — the +1h grace absorbs clock skew).
- **Coarse denial (D11):** invalid/expired/revoked/unknown/unpromoted/missing-MD/corrupt-MD all → the same **404**; malformed token → 404 before any DB call; a valid-token-but-model-absent/stale → **"not ready"** (503-class). Never a 500 leak.
- **Headers (D10):** any 200 share serve sets `Content-Security-Policy: buildSummaryCsp(nonce)`, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`.
- **Writes only via definer RPCs (D9):** `share_tokens` is `force`-RLS, `service_role`-only grants; `authenticated` gets no direct `INSERT/UPDATE`.
- **Next.js:** read the relevant guide under `node_modules/next/dist/docs/` before writing route handlers (per AGENTS.md — this is not the Next.js in your training data).
- **`gh` two-remotes footgun:** any `gh` command MUST pass `--repo kujinlee/youtube-playlist-summaries-cloud`.
- **Dev-process §8 re-review triggers:** Tasks 1, 2, 6, 7 (leaf-module refactor of merged code; money/RLS definer RPCs; confused-deputy isolation; money-invariant runtime proof) each get per-task iterative re-review to convergence.

---

## File Structure

**Create:**
- `lib/html-doc/constants.ts` — `GENERATOR_VERSION` (moved out of `render.ts` so the read helper is a true leaf).
- `lib/html-doc/read-model.ts` — leaf: `readFreshMagazineModel(...)` + `isFresh(...)`. Imports ONLY `./constants`, `./model-store`, `@/lib/storage/blob-store` (types). Never `@/lib/gemini`/`gemini-cost`/`serve-doc`.
- `lib/share/token.ts` — `generateShareToken()` → `{ token, tokenHash }`, `hashShareToken(token)` → `Buffer`.
- `lib/share/ttl.ts` — `resolveExpiry(ttlDays)` → `{ ok: true, expiresAt: Date | null } | { ok: false }`.
- `lib/share/serve.ts` — `getShareServeContext(serviceClient, token)` → resolve + confused-deputy guard → `ShareServeContext | { status: 'denied' }`.
- `supabase/migrations/0013_share_tokens.sql` — table + 4 definer RPCs.
- `app/api/share/route.ts` — `POST` mint.
- `app/api/share/[id]/revoke/route.ts` — `POST` revoke one.
- `app/api/share/revoke-all/route.ts` — `POST` revoke all for a doc.
- `app/s/[token]/route.ts` — `GET` anonymous serve.
- Tests: `tests/lib/html-doc/read-model.test.ts`, `tests/lib/share/token.test.ts`, `tests/lib/share/ttl.test.ts`, `tests/lib/html-doc/render-share.test.ts`, `tests/integration/share-tokens-rpc.test.ts`, `tests/integration/share-serve.test.ts`, `tests/api/share-mint-route.test.ts`, `tests/lib/share/import-guard.test.ts`.

**Modify:**
- `lib/storage/blob-store.ts` — add `export type ReadOnlyBlobStore = Pick<BlobStore, 'get'>`.
- `lib/html-doc/model-store.ts` — widen `readModelEnvelope` param to `ReadOnlyBlobStore`.
- `lib/html-doc/render.ts` — `import { GENERATOR_VERSION } from './constants'; export { GENERATOR_VERSION };` (import for local use at `:112` AND re-export for back-compat); add `share?: boolean` option + strip logic.
- `lib/html-doc/serve-doc.ts` — import `GENERATOR_VERSION` from `./constants`, `readFreshMagazineModel` from `./read-model`; use the helper at both read sites (`:52`, `:66`).

**Reuse (do not recreate):** `tests/integration/helpers/seed.ts` already exports `seedPlaylist(svc, ownerId)`, `seedPromotedVideo(svc, {ownerId, playlistId, videoId?, base?, status?})`, and `seedSummaryBlob(svc, ownerId, playlistKey, base, md)` — all matching the real `0001` schema. Compose these; do NOT write a new seed helper.

---

## Task 1: `read-model.ts` leaf extraction + `ReadOnlyBlobStore` (never-charges structural refactor)

**§8 re-review trigger — touches merged 1F-a code.** Deliverable: a generate-free `readFreshMagazineModel` both the owner path (`serve-doc.ts`) and (later) the share route call; the owner path's behavior is unchanged.

**Files:**
- Create: `lib/html-doc/constants.ts`, `lib/html-doc/read-model.ts`, `tests/lib/html-doc/read-model.test.ts`
- Modify: `lib/storage/blob-store.ts`, `lib/html-doc/model-store.ts:50-54`, `lib/html-doc/render.ts:9`, `lib/html-doc/serve-doc.ts:5,32-36,52-54,66-67`
- Test: `tests/lib/html-doc/read-model.test.ts`

**Interfaces:**
- Produces:
  - `lib/html-doc/constants.ts`: `export const GENERATOR_VERSION = 'magazine-skim v2'`
  - `lib/storage/blob-store.ts`: `export type ReadOnlyBlobStore = Pick<BlobStore, 'get'>`
  - `lib/html-doc/read-model.ts`:
    - `export function isFresh(envelope: { sourceSections: string[]; generatorVersion?: string }, titles: string[]): boolean`
    - `export async function readFreshMagazineModel(args: { blobStore: ReadOnlyBlobStore; principal: Principal; base: string; titles: string[] }): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }>`
- Consumes: `readModelEnvelope` (`model-store.ts`), `MagazineModel` (`./types`), `Principal` (`@/lib/storage/principal`).

- [ ] **Step 1: Write the failing test** (`tests/lib/html-doc/read-model.test.ts`)

```ts
import { readFreshMagazineModel, isFresh } from '@/lib/html-doc/read-model';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import * as modelStore from '@/lib/html-doc/model-store';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';

const principal = { id: 'owner-1', indexKey: 'pl-key' };
const fakeModel = { title: 'T', dek: 'd', sections: [] } as any;
const titles = ['A', 'B'];
const roStore: ReadOnlyBlobStore = { get: async () => null };

function envelope(over: Partial<any> = {}) {
  return { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A', 'B'],
    generatorVersion: GENERATOR_VERSION, model: fakeModel, ...over };
}

describe('isFresh', () => {
  it('true when titles match and version matches', () => {
    expect(isFresh(envelope(), titles)).toBe(true);
  });
  it('false when a title differs', () => {
    expect(isFresh(envelope({ sourceSections: ['A', 'C'] }), titles)).toBe(false);
  });
  it('false when generatorVersion differs', () => {
    expect(isFresh(envelope({ generatorVersion: 'old' }), titles)).toBe(false);
  });
});

describe('readFreshMagazineModel', () => {
  afterEach(() => jest.restoreAllMocks());

  it('returns ok with the model when a fresh envelope exists', async () => {
    jest.spyOn(modelStore, 'readModelEnvelope').mockResolvedValue(envelope());
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'ok', model: fakeModel });
  });

  it('returns not_ready when the envelope is absent', async () => {
    jest.spyOn(modelStore, 'readModelEnvelope').mockResolvedValue(null);
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });

  it('returns not_ready when the envelope is stale (version bump)', async () => {
    jest.spyOn(modelStore, 'readModelEnvelope').mockResolvedValue(envelope({ generatorVersion: 'old' }));
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest read-model`
Expected: FAIL — `Cannot find module '@/lib/html-doc/read-model'` / `@/lib/html-doc/constants`.

- [ ] **Step 3: Create `lib/html-doc/constants.ts`**

```ts
/** Bumped whenever the magazine model's shape or generation prompt changes, so a
 *  cached model that predates the change is treated as stale (isFresh → false).
 *  Lives in its own leaf module so the freshness helper (read-model.ts) does not
 *  import the full renderer graph. render.ts re-exports it for back-compat. */
export const GENERATOR_VERSION = 'magazine-skim v2';
```

- [ ] **Step 4: Add `ReadOnlyBlobStore` to `lib/storage/blob-store.ts`**

Append to the file (next to the `BlobStore` interface):

```ts
/** A read-only view of a BlobStore — exactly the `get` method. The share serve path
 *  passes a runtime `{ get: store.get.bind(store) }` wrapper so write methods are
 *  unreachable at runtime, not merely hidden by the type (spec D16). */
export type ReadOnlyBlobStore = Pick<BlobStore, 'get'>;
```

- [ ] **Step 5: Widen `readModelEnvelope` in `lib/html-doc/model-store.ts`**

Change the import and the signature (only the read side; `writeModelEnvelope` keeps full `BlobStore`):

```ts
import type { BlobStore, ReadOnlyBlobStore } from '@/lib/storage/blob-store';
// ...
export async function readModelEnvelope(
  principal: Principal,
  base: string,
  blobStore: ReadOnlyBlobStore = localBlobStore,
): Promise<ModelEnvelope | null> {
  // body unchanged — only calls blobStore.get(...)
```

- [ ] **Step 6: Create `lib/html-doc/read-model.ts`**

```ts
import type { MagazineModel } from './types';
import type { Principal } from '@/lib/storage/principal';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';
import { GENERATOR_VERSION } from './constants';
import { readModelEnvelope } from './model-store';

// GENERATE-FREE LEAF (spec D13/B18c): this module and its entire import graph must never
// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
// /s/[token] route therefore cannot pull in the charging code. Enforced by tests/lib/share/
// import-guard.test.ts (a jest grep guard; the repo has no ESLint).

export function isFresh(
  envelope: { sourceSections: string[]; generatorVersion?: string },
  titles: string[],
): boolean {
  const sameTitles = envelope.sourceSections.length === titles.length &&
    envelope.sourceSections.every((t, i) => t === titles[i]);
  return sameTitles && envelope.generatorVersion === GENERATOR_VERSION;
}

/** Read-only, generation-free: returns the cached model iff present AND fresh; otherwise
 *  not_ready. Never calls reserve_serve_model or generateMagazineModel. */
export async function readFreshMagazineModel(args: {
  blobStore: ReadOnlyBlobStore;
  principal: Principal;
  base: string;
  titles: string[];
}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }> {
  const { blobStore, principal, base, titles } = args;
  const existing = await readModelEnvelope(principal, base, blobStore);
  if (existing && isFresh(existing, titles)) return { status: 'ok', model: existing.model };
  return { status: 'not_ready' };
}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `npx jest read-model`
Expected: PASS (6 tests).

- [ ] **Step 8: Refactor `render.ts` to source `GENERATOR_VERSION` from constants**

In `lib/html-doc/render.ts:9`, replace the literal declaration with an **import + re-export** (a bare `export … from` creates NO local binding, but `render.ts:112` uses `GENERATOR_VERSION` locally in the non-share `<meta generator>` branch → it must be imported for local use AND re-exported for the ~10 external consumers that `import { GENERATOR_VERSION } from './render'`):

```ts
import { GENERATOR_VERSION } from './constants';
export { GENERATOR_VERSION };
```

Run: `npx tsc --noEmit && npx jest render` — expected: tsc clean (no `TS2304`); existing render tests unchanged.

- [ ] **Step 9: Refactor `serve-doc.ts` to use the leaf helper at both read sites**

Edit `lib/html-doc/serve-doc.ts`:
- Line 5: `import { GENERATOR_VERSION } from './render';` → `import { GENERATOR_VERSION } from './constants';`
- Delete the local `isFresh` (lines 32-36); add `import { readFreshMagazineModel } from './read-model';` (import ONLY `readFreshMagazineModel` — `isFresh` is unused after this refactor since both read sites go through the helper; leaving it imported is dead code).
- Replace the first read site (lines 52-54):

```ts
  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
```

- Replace the in-flight re-read (lines 66-67):

```ts
    case 'in_flight': {
      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
      return now.status === 'ok' ? now : { status: 'busy' };
    }
```

(`GENERATOR_VERSION` is still imported from `./constants` because `writeModelEnvelope` at line 89 uses it.)

- [ ] **Step 10: Run the full suite — confirm no owner-path regression**

Run: `npx tsc --noEmit && npx jest` (unit) — expected: tsc clean; all green (serve-doc's B1/B2/B3 semantics unchanged — the extraction is behavior-preserving). Then `npx jest serve-doc` specifically to confirm the owner-path tests pass.

- [ ] **Step 11: Add the B18c module-graph test** (append to `tests/lib/html-doc/read-model.test.ts`)

```ts
import { readFileSync } from 'fs';
import { join } from 'path';

describe('B18c — read-model.ts is a generate-free leaf', () => {
  it('imports nothing that could charge or generate', () => {
    const src = readFileSync(join(process.cwd(), 'lib/html-doc/read-model.ts'), 'utf-8');
    const imports = [...src.matchAll(/from ['"]([^'"]+)['"]/g)].map((m) => m[1]);
    for (const bad of ['@/lib/gemini', '@/lib/gemini-cost', './serve-doc', '@/lib/html-doc/serve-doc']) {
      expect(imports).not.toContain(bad);
    }
    // constants.ts (the GENERATOR_VERSION source) must itself import nothing.
    const consts = readFileSync(join(process.cwd(), 'lib/html-doc/constants.ts'), 'utf-8');
    expect(consts).not.toMatch(/\bimport\b/);
  });
});
```

Run: `npx jest read-model` — expected PASS.

- [ ] **Step 12: Commit**

```bash
git add lib/html-doc/constants.ts lib/html-doc/read-model.ts lib/storage/blob-store.ts \
  lib/html-doc/model-store.ts lib/html-doc/render.ts lib/html-doc/serve-doc.ts \
  tests/lib/html-doc/read-model.test.ts
git commit -m "feat(1f-b): read-model.ts generate-free leaf + ReadOnlyBlobStore (never-charges refactor)"
```

---

## Task 2: `0013_share_tokens` migration + four definer RPCs

**§8 re-review trigger — money-adjacent + RLS/definer.** Deliverable: the `share_tokens` table and `create/revoke/revoke_all/list` RPCs, with the DB-side TTL bound and hash-length CHECK.

**Files:**
- Create: `supabase/migrations/0013_share_tokens.sql`, `tests/integration/share-tokens-rpc.test.ts`
- Test: `tests/integration/share-tokens-rpc.test.ts`

**Interfaces:**
- Produces (SQL callable via PostgREST `.rpc(...)`):
  - `create_share_token(p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash text) returns timestamptz`
  - `revoke_share_token(p_id uuid) returns boolean`
  - `revoke_all_share_tokens(p_playlist_id uuid, p_video_id text) returns integer`
  - `list_share_tokens(p_playlist_id uuid, p_video_id text) returns table(id uuid, created_at timestamptz, expires_at timestamptz, revoked_at timestamptz)`
- Consumes: `profiles(id)`, `playlists(id, owner_id)`, `videos(playlist_id, video_id, owner_id, data)` (from `0001`); the `promoted` predicate mirrors `reserve_serve_model` (`0012:44`): `(v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'`.

- [ ] **Step 1: Write the failing test** (`tests/integration/share-tokens-rpc.test.ts`)

```ts
import { createHash, randomBytes } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed'; // EXISTING helpers — do not recreate

const svc = adminClient();
// token_hash is stored as lowercase hex TEXT (not bytea — see Global Constraints).
const hexHash = () => createHash('sha256').update(randomBytes(32)).digest('hex');
async function seedDoc(ownerId: string) {
  const { playlistId } = await seedPlaylist(svc, ownerId);
  const { videoId } = await seedPromotedVideo(svc, { ownerId, playlistId });
  return { playlistId, videoId };
}

describe('share_tokens RPCs', () => {
  it('create_share_token stores a row for an owned+promoted doc and returns expires_at', async () => {
    const u = await newUser();
    const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const hash = hexHash();
    const expiry = new Date(Date.now() + 30 * 864e5).toISOString();
    const { data, error } = await client.rpc('create_share_token', {
      p_playlist_id: playlistId, p_video_id: videoId, p_expiry: expiry, p_token_hash: hash,
    });
    expect(error).toBeNull();
    expect(new Date(data as string).getTime()).toBeCloseTo(new Date(expiry).getTime(), -3);
    const { data: rows } = await svc.from('share_tokens').select('*').eq('playlist_id', playlistId);
    expect(rows).toHaveLength(1);
    expect((rows![0] as any).owner_id).toBe(u.user.id);
  });

  it('create_share_token raises for a doc the caller does not own (coarse)', async () => {
    const owner = await newUser(); const other = await newUser();
    const { client: otherClient } = await signInAs(other.email, other.password);
    const { playlistId, videoId } = await seedDoc(owner.user.id);
    const { error } = await otherClient.rpc('create_share_token', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash(),
    });
    expect(error).not.toBeNull(); // raised → route maps to 404
  });

  it('create_share_token rejects a hostile expiry (past and > now+366d)', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    for (const expiry of [new Date(Date.now() - 864e5).toISOString(),
                          new Date(Date.now() + 366 * 864e5).toISOString()]) {
      const { error } = await client.rpc('create_share_token', {
        p_playlist_id: playlistId, p_video_id: videoId, p_expiry: expiry, p_token_hash: hexHash(),
      });
      expect(error).not.toBeNull();
    }
  });

  it('accepts exactly now+365d (grace margin — B-L5 boundary)', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const { error } = await client.rpc('create_share_token', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 365 * 864e5).toISOString(), p_token_hash: hexHash(),
    });
    expect(error).toBeNull();
  });

  it('rejects a malformed token hash (CHECK: not 64 hex chars)', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const { error } = await client.rpc('create_share_token', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: 'not-a-valid-hex-hash',
    });
    expect(error).not.toBeNull();
  });

  it('revoke_share_token sets revoked_at only for the owner; list never returns the hash', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    await client.rpc('create_share_token', { p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });
    const { data: listed } = await client.rpc('list_share_tokens', { p_playlist_id: playlistId, p_video_id: videoId });
    expect(listed).toHaveLength(1);
    expect(Object.keys((listed as any[])[0])).not.toContain('token_hash');
    const id = (listed as any[])[0].id;
    const { data: revoked } = await client.rpc('revoke_share_token', { p_id: id });
    expect(revoked).toBe(true);
    const other = await newUser(); const { client: otherClient } = await signInAs(other.email, other.password);
    const { data: revoked2 } = await otherClient.rpc('revoke_share_token', { p_id: id });
    expect(revoked2).toBe(false); // not owner → no-op
  });

  it('revoke_all_share_tokens revokes every live token for the doc and returns the count', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    for (let i = 0; i < 3; i++) await client.rpc('create_share_token', { p_playlist_id: playlistId,
      p_video_id: videoId, p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });
    const { data: count } = await client.rpc('revoke_all_share_tokens', { p_playlist_id: playlistId, p_video_id: videoId });
    expect(count).toBe(3);
  });

  it('direct INSERT/UPDATE on share_tokens is denied for an authenticated session (B23)', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const { error } = await client.from('share_tokens').insert({
      token_hash: hexHash(), owner_id: u.user.id, playlist_id: playlistId, video_id: videoId,
    });
    expect(error).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx supabase db reset && npm run test:integration -- --runInBand -t "share_tokens RPCs"`
Expected: FAIL — relation `share_tokens` / function `create_share_token` does not exist. (The `seedPlaylist`/`seedPromotedVideo` helpers already exist in `tests/integration/helpers/seed.ts` — do NOT recreate them.)

- [ ] **Step 3: Write the migration** (`supabase/migrations/0013_share_tokens.sql`)

```sql
-- supabase/migrations/0013_share_tokens.sql
-- Stage 1F-b share tokens (spec §4.1/§4.2). force-RLS + service_role-only grants (mirrors
-- serve_model_charge, 0012); all writes go through SECURITY DEFINER RPCs that derive the
-- owner from auth.uid() internally. MAX_SHARE_TTL_DAYS = 365 (inlined in the RPC bound).

create table share_tokens (
  id            uuid primary key default gen_random_uuid(),
  token_hash    text not null unique check (token_hash ~ '^[0-9a-f]{64}$'),  -- lowercase hex of sha256; plaintext never stored
  owner_id      uuid not null references profiles(id) on delete cascade,
  playlist_id   uuid not null,
  video_id      text not null,
  created_at    timestamptz not null default now(),
  expires_at    timestamptz,                           -- null = never
  revoked_at    timestamptz
);
alter table share_tokens enable row level security;
alter table share_tokens force row level security;      -- only BYPASSRLS roles read/write
grant select, insert, update, delete on share_tokens to service_role;  -- no anon/authenticated policy
create index share_tokens_owner_idx on share_tokens (owner_id);

-- Ownership + promoted predicate helper (inlined; same shape as reserve_serve_model, 0012:44-47).
create function create_share_token(
  p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash text
) returns timestamptz language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_promoted boolean;
begin
  if v_owner is null then raise exception 'create_share_token: unauthenticated'; end if;
  if p_token_hash !~ '^[0-9a-f]{64}$' then raise exception 'create_share_token: bad hash format'; end if;
  -- Trust-boundary TTL bound (+1h grace absorbs app/DB clock skew; still rejects > ~1 year).
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
    values (p_token_hash, v_owner, p_playlist_id, p_video_id, p_expiry);
  return p_expiry;
end $$;

create function revoke_share_token(p_id uuid) returns boolean
  language plpgsql security definer set search_path = public as $$
declare v_owner uuid := auth.uid(); v_rows int;
begin
  if v_owner is null then raise exception 'revoke_share_token: unauthenticated'; end if;
  update share_tokens set revoked_at = now()
    where id = p_id and owner_id = v_owner and revoked_at is null;
  get diagnostics v_rows = row_count;
  return v_rows > 0;
end $$;

create function revoke_all_share_tokens(p_playlist_id uuid, p_video_id text) returns integer
  language plpgsql security definer set search_path = public as $$
declare v_owner uuid := auth.uid(); v_rows int;
begin
  if v_owner is null then raise exception 'revoke_all_share_tokens: unauthenticated'; end if;
  update share_tokens set revoked_at = now()
    where owner_id = v_owner and playlist_id = p_playlist_id and video_id = p_video_id and revoked_at is null;
  get diagnostics v_rows = row_count;
  return v_rows;
end $$;

create function list_share_tokens(p_playlist_id uuid, p_video_id text)
  returns table(id uuid, created_at timestamptz, expires_at timestamptz, revoked_at timestamptz)
  language plpgsql security definer set search_path = public as $$
declare v_owner uuid := auth.uid();
begin
  if v_owner is null then raise exception 'list_share_tokens: unauthenticated'; end if;
  return query
    select t.id, t.created_at, t.expires_at, t.revoked_at from share_tokens t
    where t.owner_id = v_owner and t.playlist_id = p_playlist_id and t.video_id = p_video_id
    order by t.created_at;
end $$;

revoke all on function create_share_token(uuid, text, timestamptz, text) from public;
revoke all on function revoke_share_token(uuid) from public;
revoke all on function revoke_all_share_tokens(uuid, text) from public;
revoke all on function list_share_tokens(uuid, text) from public;
grant execute on function create_share_token(uuid, text, timestamptz, text) to authenticated;
grant execute on function revoke_share_token(uuid) to authenticated;
grant execute on function revoke_all_share_tokens(uuid, text) to authenticated;
grant execute on function list_share_tokens(uuid, text) to authenticated;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx supabase db reset && npm run test:integration -- --runInBand -t "share_tokens RPCs"`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0013_share_tokens.sql tests/integration/share-tokens-rpc.test.ts
git commit -m "feat(1f-b): share_tokens table + create/revoke/revoke-all/list definer RPCs"
```

---

## Task 3: Token crypto + TTL contract libs

**Files:**
- Create: `lib/share/token.ts`, `lib/share/ttl.ts`, `tests/lib/share/token.test.ts`, `tests/lib/share/ttl.test.ts`

**Interfaces:**
- Produces:
  - `lib/share/token.ts`: `export function generateShareToken(): { token: string; tokenHash: string }`; `export function hashShareToken(token: string): string` (lowercase hex of the SHA-256 — matches the `text` column; see Global Constraints)
  - `lib/share/ttl.ts`: `export const MAX_SHARE_TTL_DAYS = 365`; `export function resolveExpiry(ttlDays: number | 'never' | undefined): { ok: true; expiresAt: Date | null } | { ok: false }`

- [ ] **Step 1: Write the failing tests**

`tests/lib/share/token.test.ts`:

```ts
import { generateShareToken, hashShareToken } from '@/lib/share/token';
import { createHash } from 'crypto';

describe('share token crypto', () => {
  it('generates a 43-char base64url token (256-bit) and its 64-char hex sha256 hash', () => {
    const { token, tokenHash } = generateShareToken();
    expect(token).toMatch(/^[A-Za-z0-9_-]{43}$/); // 32 bytes base64url, no padding
    expect(tokenHash).toBe(createHash('sha256').update(token).digest('hex'));
    expect(tokenHash).toMatch(/^[0-9a-f]{64}$/);
  });
  it('two tokens differ', () => {
    expect(generateShareToken().token).not.toBe(generateShareToken().token);
  });
  it('hashShareToken is deterministic and matches sha256(token) hex', () => {
    const { token, tokenHash } = generateShareToken();
    expect(hashShareToken(token)).toBe(tokenHash);
  });
});
```

`tests/lib/share/ttl.test.ts`:

```ts
import { resolveExpiry } from '@/lib/share/ttl';

describe('resolveExpiry', () => {
  it('omitted → 30 days out', () => {
    const r = resolveExpiry(undefined);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.expiresAt!.getTime()).toBeGreaterThan(Date.now() + 29 * 864e5);
  });
  it("'never' → null", () => {
    expect(resolveExpiry('never')).toEqual({ ok: true, expiresAt: null });
  });
  it('a valid positive int → that many days out', () => {
    const r = resolveExpiry(7);
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.expiresAt!.getTime()).toBeGreaterThan(Date.now() + 6 * 864e5);
  });
  it('365 (max) → ok', () => { expect(resolveExpiry(365).ok).toBe(true); });
  it.each([0, -1, 366, 3.5, NaN])('rejects %p', (v) => {
    expect(resolveExpiry(v as number)).toEqual({ ok: false });
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `npx jest share/token share/ttl` — Expected FAIL (modules missing).

- [ ] **Step 3: Implement `lib/share/token.ts`**

```ts
import { randomBytes, createHash } from 'crypto';

/** 256-bit opaque bearer token (base64url, unpadded) + its sha256 hash (lowercase hex) for
 *  at-rest storage. Hex (not a Buffer) because token_hash is a `text` column and a Buffer would
 *  not serialize to it over PostgREST (see Global Constraints). */
export function generateShareToken(): { token: string; tokenHash: string } {
  const token = randomBytes(32).toString('base64url');
  return { token, tokenHash: hashShareToken(token) };
}

export function hashShareToken(token: string): string {
  return createHash('sha256').update(token).digest('hex');
}
```

- [ ] **Step 4: Implement `lib/share/ttl.ts`**

```ts
export const MAX_SHARE_TTL_DAYS = 365;
const DAY_MS = 86_400_000;

/** Route-side TTL contract (spec §4.4): omitted → 30d; 'never' → null; integer 1..365 → that
 *  many days; anything else → invalid (route returns 400). The RPC re-validates the bound. */
export function resolveExpiry(
  ttlDays: number | 'never' | undefined,
): { ok: true; expiresAt: Date | null } | { ok: false } {
  if (ttlDays === undefined) return { ok: true, expiresAt: new Date(Date.now() + 30 * DAY_MS) };
  if (ttlDays === 'never') return { ok: true, expiresAt: null };
  if (typeof ttlDays === 'number' && Number.isInteger(ttlDays) && ttlDays >= 1 && ttlDays <= MAX_SHARE_TTL_DAYS) {
    return { ok: true, expiresAt: new Date(Date.now() + ttlDays * DAY_MS) };
  }
  return { ok: false };
}
```

- [ ] **Step 5: Run to verify pass**

Run: `npx jest share/token share/ttl` — Expected PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/share/token.ts lib/share/ttl.ts tests/lib/share/token.test.ts tests/lib/share/ttl.test.ts
git commit -m "feat(1f-b): share token crypto + TTL contract libs"
```

---

## Task 4: `share:true` render mode (strip the owner-structure leak)

**Files:**
- Modify: `lib/html-doc/render.ts:59-62,104-114,126`
- Test: `tests/lib/html-doc/render-share.test.ts`

**Interfaces:**
- Produces: `renderMagazineHtml(parsed, model, { nonce?, dig?, share? })` — new optional `share?: boolean`. When `true`: no `source-md` meta, no `video-id` meta, no `generator` meta, and no footer `<code>` MD-key; the MD-key string is absent from output. Body (title/channel/URL/sections/timestamps) retained.

- [ ] **Step 1: Write the failing test** (`tests/lib/html-doc/render-share.test.ts`)

```ts
import { renderMagazineHtml } from '@/lib/html-doc/render';

const parsed = {
  title: 'V', channel: 'C', url: 'https://youtu.be/x', videoId: 'abc123',
  sourceMd: '00042_my-secret-slug.md', tldr: 'td', takeaways: [],
  sections: [{ title: 'S1', prose: 'p', timestamp: null }], sourceSectionsRaw: [],
} as any;
// MagazineSection requires `lead: string` + `bullets: Bullet[]` (types.ts:39-43) — render.ts:92/98
// read m.bullets[].text and m.lead, so a {heading,body} fixture would throw before any assertion.
const model = { title: 'V', dek: 'd', sections: [
  { lead: 'S1', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] },
] } as any;

describe('renderMagazineHtml share mode', () => {
  it('strips the MD key + video-id + generator metas when share:true', () => {
    const html = renderMagazineHtml(parsed, model, { nonce: 'n', dig: false, share: true });
    expect(html).not.toContain('00042_my-secret-slug.md'); // B22 — the owner-structure leak
    expect(html).not.toContain('name="source-md"');
    expect(html).not.toContain('name="video-id"');
    expect(html).not.toContain('name="generator"');
    expect(html).toContain('S1'); // body retained
  });
  it('non-share render still emits the metas (unchanged default)', () => {
    const html = renderMagazineHtml(parsed, model, { nonce: 'n', dig: false });
    expect(html).toContain('00042_my-secret-slug.md');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest render-share` — Expected FAIL (`share` option ignored; MD key present).

- [ ] **Step 3: Implement `share` in `render.ts`**

Change the options type (line 59):

```ts
  opts: { nonce?: string; dig?: boolean; share?: boolean } = {},
```

Add near the top of the body (after line 62):

```ts
  const share = opts.share ?? false;
```

Replace the source-md / video-id / generator meta lines (112-114) with share-gated emission:

```ts
${share ? '' : `<meta name="generator" content="${GENERATOR_VERSION}">
<meta name="source-md" content="${esc(sourceMd)}">
<meta name="video-id" content="${esc(parsed.videoId ?? '')}">`}
```

Replace the footer source (line 105) so the MD-key `<code>` is dropped in share mode:

```ts
  const footerSource = (!share && sourceMd) ? ` <code>${esc(sourceMd)}</code>` : '';
```

- [ ] **Step 4: Run to verify pass + no regression**

Run: `npx jest render` — Expected PASS (render-share green; existing render tests unaffected because `share` defaults false).

- [ ] **Step 5: Commit**

```bash
git add lib/html-doc/render.ts tests/lib/html-doc/render-share.test.ts
git commit -m "feat(1f-b): share:true render mode strips owner-structure metadata"
```

---

## Task 5: Mint + revoke + revoke-all routes

**Files:**
- Create: `app/api/share/route.ts`, `app/api/share/[id]/revoke/route.ts`, `app/api/share/revoke-all/route.ts`, `tests/api/share-mint-route.test.ts`
- Read first: `node_modules/next/dist/docs/` route-handler guide; mirror `app/api/html/[id]/route.ts` for the session-client pattern.

**Interfaces:**
- Consumes: `create_share_token`/`revoke_share_token`/`revoke_all_share_tokens` RPCs (Task 2); `generateShareToken` (Task 3); `resolveExpiry` (Task 3); `createServerSupabase` (`@/lib/supabase/server`).
- Produces: `POST /api/share` → 201 `{ token, url, expiresAt }`; `POST /api/share/[id]/revoke` → 200 `{ revoked }`; `POST /api/share/revoke-all` → 200 `{ count }`.

- [ ] **Step 1: Write the failing test** (`tests/api/share-mint-route.test.ts`)

Mock the session Supabase client at the route boundary (mirror the existing `tests/api/*` pattern). Cases:

```ts
import { POST } from '@/app/api/share/route';
// Helper makeReq(body) builds a Request; mock createServerSupabase to return a fake client
// whose auth.getUser() and rpc() are jest.fn()s. See tests/api/jobs-route-guardrails.test.ts
// for the established mocking shape in this repo.

describe('POST /api/share', () => {
  it('401 when no session', async () => { /* getUser → {user:null} */ });
  it('201 returns token + url + expiresAt once, calls create_share_token with a 32-byte hash', async () => {
    // rpc('create_share_token') → { data: <iso>, error: null }
    // assert response.status === 201; body.token matches /^[A-Za-z0-9_-]{43}$/;
    // body.url === `/s/${body.token}`; the rpc arg p_token_hash has length 32.
  });
  it('400 when ttlDays is out of range (0 / 366 / -1)', async () => { /* resolveExpiry → {ok:false} */ });
  it('404 (coarse) when the RPC raises (unowned/unpromoted)', async () => {
    // rpc → { data: null, error: {...} } → route returns 404
  });
});
```

(Write the concrete assertions following the repo's existing route-test harness. The load-bearing checks: 401/201/400/404 mapping, single plaintext exposure, 32-byte hash passed to the RPC, `url === /s/<token>`.)

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest share-mint-route` — Expected FAIL (route missing).

- [ ] **Step 3: Implement `app/api/share/route.ts`**

```ts
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { generateShareToken } from '@/lib/share/token';
import { resolveExpiry } from '@/lib/share/ttl';

const json = (b: unknown, s: number) => new Response(JSON.stringify(b), { status: s });

export async function POST(request: Request) {
  const body = await request.json().catch(() => null) as
    | { playlistId?: string; videoId?: string; ttlDays?: number | 'never' } | null;
  if (!body?.playlistId || !body?.videoId) return json({ error: 'bad request' }, 400);

  const expiry = resolveExpiry(body.ttlDays);
  if (!expiry.ok) return json({ error: 'invalid ttlDays' }, 400);

  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  const { token, tokenHash } = generateShareToken();
  const { data: expiresAt, error } = await supabase.rpc('create_share_token', {
    p_playlist_id: body.playlistId, p_video_id: body.videoId,
    p_expiry: expiry.expiresAt ? expiry.expiresAt.toISOString() : null,
    p_token_hash: tokenHash,
  });
  if (error) return json({ error: 'not found' }, 404); // coarse — unowned/unpromoted/bounds
  return json({ token, url: `/s/${token}`, expiresAt }, 201);
}
```

- [ ] **Step 4: Implement `app/api/share/[id]/revoke/route.ts`**

```ts
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
const json = (b: unknown, s: number) => new Response(JSON.stringify(b), { status: s });

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);
  const { data: revoked, error } = await supabase.rpc('revoke_share_token', { p_id: id });
  if (error) return json({ error: 'internal error' }, 500);
  return json({ revoked }, 200);
}
```

- [ ] **Step 5: Implement `app/api/share/revoke-all/route.ts`**

```ts
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
const json = (b: unknown, s: number) => new Response(JSON.stringify(b), { status: s });

export async function POST(request: Request) {
  const body = await request.json().catch(() => null) as { playlistId?: string; videoId?: string } | null;
  if (!body?.playlistId || !body?.videoId) return json({ error: 'bad request' }, 400);
  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);
  const { data: count, error } = await supabase.rpc('revoke_all_share_tokens', {
    p_playlist_id: body.playlistId, p_video_id: body.videoId,
  });
  if (error) return json({ error: 'internal error' }, 500);
  return json({ count }, 200);
}
```

- [ ] **Step 6: Run to verify pass + tsc**

Run: `npx jest share-mint-route && npx tsc --noEmit` — Expected PASS + clean.

- [ ] **Step 7: Commit**

```bash
git add app/api/share tests/api/share-mint-route.test.ts
git commit -m "feat(1f-b): mint + revoke + revoke-all share routes"
```

---

## Task 6: Share-serve resolution lib (confused-deputy guard)

**§8 re-review trigger — B19b isolation.** Deliverable: `getShareServeContext` — token → validated doc coordinates, resolving on the global `(playlist_id, owner_id)` and asserting the owner match.

**Files:**
- Create: `lib/share/serve.ts`, `tests/integration/share-serve.test.ts` (resolution half; full route in Task 7)

**Interfaces:**
- Consumes: `hashShareToken` (Task 3); `share_tokens` + `playlists` + `videos` (Task 2 / `0001`); a `service_role` `SupabaseClient`.
- Produces:
  - `export type ShareServeContext = { ownerId: string; playlistKey: string; playlistId: string; videoId: string; mdKey: string }`
  - `export async function getShareServeContext(serviceClient: SupabaseClient, token: string): Promise<ShareServeContext | { status: 'denied' }>`

- [ ] **Step 1: Write the failing test** (`tests/integration/share-serve.test.ts`)

```ts
import { adminClient, newUser } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed'; // EXISTING helpers
import { generateShareToken } from '@/lib/share/token';
import { getShareServeContext } from '@/lib/share/serve';

const svc = adminClient();

/** Seed an owned promoted doc; returns coordinates incl. the real base (seedPromotedVideo keys
 *  the MD as `${base}.md`). Pass status:'committed' for the un-promoted case. */
async function seedDoc(ownerId: string, status: 'promoted' | 'committed' = 'promoted') {
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId, base } = await seedPromotedVideo(svc, { ownerId, playlistId, status });
  return { playlistId, playlistKey, videoId, base };
}

async function mintDirect(ownerId: string, playlistId: string, videoId: string, over: Record<string, unknown> = {}) {
  const { token, tokenHash } = generateShareToken(); // tokenHash is 64-char hex TEXT
  await svc.from('share_tokens').insert({ token_hash: tokenHash, owner_id: ownerId,
    playlist_id: playlistId, video_id: videoId, expires_at: new Date(Date.now() + 864e5).toISOString(), ...over });
  return token;
}

describe('getShareServeContext', () => {
  it('resolves a live token to the doc coordinates', async () => {
    const u = await newUser(); const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId);
    const ctx = await getShareServeContext(svc, token);
    expect(ctx).toMatchObject({ ownerId: u.user.id, playlistKey, playlistId, videoId, mdKey: `${base}.md` });
  });
  it('denies an expired token before resolving', async () => {
    const u = await newUser(); const { playlistId, videoId } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId, { expires_at: new Date(Date.now() - 864e5).toISOString() });
    expect(await getShareServeContext(svc, token)).toEqual({ status: 'denied' });
  });
  it('denies a revoked token', async () => {
    const u = await newUser(); const { playlistId, videoId } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId, { revoked_at: new Date().toISOString() });
    expect(await getShareServeContext(svc, token)).toEqual({ status: 'denied' });
  });
  it('denies an unknown token', async () => {
    expect(await getShareServeContext(svc, generateShareToken().token)).toEqual({ status: 'denied' });
  });
  it('denies when the summary is no longer promoted', async () => {
    const u = await newUser(); const { playlistId, videoId } = await seedDoc(u.user.id, 'committed');
    const token = await mintDirect(u.user.id, playlistId, videoId);
    expect(await getShareServeContext(svc, token)).toEqual({ status: 'denied' });
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:integration -- --runInBand -t getShareServeContext` — Expected FAIL (module missing).

- [ ] **Step 3: Implement `lib/share/serve.ts`**

```ts
import type { SupabaseClient } from '@supabase/supabase-js';
import { hashShareToken } from './token';

export type ShareServeContext = {
  ownerId: string; playlistKey: string; playlistId: string; videoId: string; mdKey: string;
};

/** Validate a bearer token and resolve the one doc it authorizes, guarded against
 *  confused-deputy: the playlist is resolved by (id, owner_id) from the token row and the
 *  resolved owner is re-asserted (spec D15). Read-only; performs no blob reads. Returns a
 *  coarse `denied` for every invalid/expired/revoked/unknown/unpromoted case. */
export async function getShareServeContext(
  serviceClient: SupabaseClient, token: string,
): Promise<ShareServeContext | { status: 'denied' }> {
  const denied = { status: 'denied' as const };
  const hash = hashShareToken(token);

  const { data: tok, error: tokErr } = await serviceClient
    .from('share_tokens').select('owner_id, playlist_id, video_id, expires_at, revoked_at')
    .eq('token_hash', hash).maybeSingle();
  if (tokErr) throw tokErr;
  if (!tok) return denied;
  if (tok.revoked_at) return denied;
  if (tok.expires_at && new Date(tok.expires_at).getTime() <= Date.now()) return denied;

  // Resolve by the GLOBAL (id, owner_id) — never by playlist_key — AND re-assert the owner (D15).
  const { data: pl, error: plErr } = await serviceClient
    .from('playlists').select('playlist_key, owner_id')
    .eq('id', tok.playlist_id).eq('owner_id', tok.owner_id).maybeSingle();
  if (plErr) throw plErr;
  if (!pl || pl.owner_id !== tok.owner_id) return denied; // confused-deputy guard (D15)

  const { data: vid, error: vidErr } = await serviceClient
    .from('videos').select('data, owner_id')
    .eq('playlist_id', tok.playlist_id).eq('video_id', tok.video_id).eq('owner_id', tok.owner_id).maybeSingle();
  if (vidErr) throw vidErr;
  if (!vid || vid.owner_id !== tok.owner_id) return denied;

  const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
    .artifacts?.summaryMd;
  if (artifact?.status !== 'promoted') return denied;
  const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
  if (!mdKey) return denied;

  return { ownerId: tok.owner_id, playlistKey: pl.playlist_key, playlistId: tok.playlist_id, videoId: tok.video_id, mdKey };
}
```

- [ ] **Step 4: Run to verify pass**

Run: `npm run test:integration -- --runInBand -t getShareServeContext` — Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/share/serve.ts tests/integration/share-serve.test.ts
git commit -m "feat(1f-b): getShareServeContext token resolution + confused-deputy guard"
```

---

## Task 7: Anonymous `/s/[token]` serve route + money-invariant proof + import guard

**§8 re-review trigger — money-invariant (B18) + isolation (B19).** Deliverable: the anonymous serve route wiring Tasks 1/3/4/6 together, proven generation-free at runtime and by static guard.

**Files:**
- Create: `app/s/[token]/route.ts`, `tests/lib/share/import-guard.test.ts`, `tests/integration/share-route.test.ts`
- (No ESLint config — the repo has none; the static guard is the jest `import-guard.test.ts`.)

**Interfaces:**
- Consumes: `getShareServeContext` (Task 6); `createServiceClient` (`@/lib/supabase/service`); `SupabaseBlobStore` + `ARTIFACTS_BUCKET`; `readFreshMagazineModel` (Task 1, from `@/lib/html-doc/read-model`); `parseSummaryMarkdown`; `renderMagazineHtml` (share mode, Task 4); `generateNonce`/`buildSummaryCsp` (`@/lib/html-doc/csp`).
- Produces: `GET /s/[token]`.

- [ ] **Step 1: Write the failing full-route tests** (`tests/integration/share-route.test.ts`)

Cover, against a real DB + real storage (seed a promoted doc + write its MD blob + a fresh model envelope via `writeModelEnvelope` under a service-role store):

```
- B6  valid token, fresh model → 200 text/html; headers no-store + no-referrer + CSP; body has the summary, NOT the MD key.
- B7  valid token, model absent → 503-class "not ready".
- B9/B10/B12 expired/revoked/unknown → 404 (coarse) with no body.
- B11 malformed token (bad shape) → 404 before any DB call.
- B13b MD blob missing behind promoted → 404 (never 500); corrupt MD → 404.
- B10b in-flight revoke: revoke between context-resolve and response → final re-check → 404.
```

**B18 money proof — assert across EVERY case above, not just B6** (this is the money invariant): before the whole block, snapshot `spend_ledger` and `serve_model_charge` (full row sets). Install a spy on the reserve RPC via `jest.spyOn(SupabaseClient.prototype, 'rpc')` (the route builds its own service client, so spy the prototype, not an injected client). After each case, assert the spy was **never** called with `'reserve_serve_model'`; after the block, assert both tables' rows are byte-identical to the snapshot. `generateMagazineModel` is already mocked at `lib/gemini.ts` — assert that mock has **zero** calls.

Write these using the established integration harness (call the route's `GET` with a `Request` whose URL carries the token path param; assert `response.status`, headers, and body). Seed via `seedPlaylist` + `seedPromotedVideo` + `seedSummaryBlob`; seed a fresh model with `writeModelEnvelope(principal, base, envelope, serviceStore)` (a full service-role `SupabaseBlobStore`).

- [ ] **Step 2: Run to verify they fail**

Run: `npm run test:integration -- --runInBand -t "share-route"` — Expected FAIL (route missing).

- [ ] **Step 3: Implement `app/s/[token]/route.ts`**

```ts
import { createServiceClient } from '@/lib/supabase/service';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { getShareServeContext } from '@/lib/share/serve';
import { readFreshMagazineModel } from '@/lib/html-doc/read-model';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { generateNonce, buildSummaryCsp } from '@/lib/html-doc/csp';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';

// MONEY GUARD (spec B18b, enforced by tests/lib/share/import-guard.test.ts): this module must not
// import the charging/serve-doc modules and must never call the reserve RPC. (Do NOT name the
// forbidden symbols here — the guard greps this file's raw text for them.)

const TOKEN_RE = /^[A-Za-z0-9_-]{43}$/; // 32-byte base64url
const notFound = () => new Response(JSON.stringify({ error: 'not found' }), { status: 404 });
const notReady = () => new Response(JSON.stringify({ error: 'not ready, retry shortly' }), { status: 503 });

export async function GET(_req: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  if (!TOKEN_RE.test(token)) return notFound(); // malformed → before any DB call (B11)

  const svc = createServiceClient();
  const ctx = await getShareServeContext(svc, token);
  if ('status' in ctx) return notFound(); // denied — expired/revoked/unknown/unpromoted (B9/B10/B12/B13)

  const fullStore = new SupabaseBlobStore(svc, ARTIFACTS_BUCKET);
  const readOnly: ReadOnlyBlobStore = { get: fullStore.get.bind(fullStore) }; // runtime get-only (D16)
  const principal = { id: ctx.ownerId, indexKey: ctx.playlistKey };

  const mdBytes = await readOnly.get(principal, ctx.mdKey);
  if (!mdBytes) return notFound(); // MD lost behind promoted (B13b)

  let parsed;
  try { parsed = parseSummaryMarkdown(mdBytes.toString('utf-8')); }
  catch { return notFound(); } // corrupt/unparsable MD → coarse 404, never 500 (B13b)
  parsed.sourceMd = ctx.mdKey;
  const base = ctx.mdKey.replace(/\.md$/, '');
  const titles = parsed.sections.map((s) => s.title);

  const model = await readFreshMagazineModel({ blobStore: readOnly, principal, base, titles });
  if (model.status !== 'ok') return notReady(); // absent/stale — NO generation (B7/B8)

  // Mandatory pre-response re-check: closes revoke/un-promote-before-final-check (D14/B10b).
  const recheck = await getShareServeContext(svc, token);
  if ('status' in recheck) return notFound();

  const nonce = generateNonce();
  const html = renderMagazineHtml(parsed, model.model, { nonce, dig: false, share: true });
  return new Response(html, {
    status: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Content-Security-Policy': buildSummaryCsp(nonce),
      'Cache-Control': 'no-store',
      'Referrer-Policy': 'no-referrer',
    },
  });
}
```

- [ ] **Step 4: Write the import-guard test (B18b)** (`tests/lib/share/import-guard.test.ts`)

```ts
import { readFileSync, readdirSync, existsSync } from 'fs';
import { join } from 'path';

// Filesystem walk — NOT `git ls-files` (which sees only tracked files, so a new-but-uncommitted
// share source would be skipped and the guard would pass vacuously). Assert the scan is non-empty
// and includes the route, so an empty/broken scan fails loudly.
function walk(dir: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = join(dir, e.name);
    if (e.isDirectory()) return walk(p);
    return e.isFile() && p.endsWith('.ts') && !p.endsWith('.test.ts') ? [p] : [];
  });
}
const root = process.cwd();
const shareSources = [
  ...walk(join(root, 'app/s')),
  ...walk(join(root, 'lib/share')),
  join(root, 'lib/html-doc/read-model.ts'),
].filter((f) => existsSync(f));

describe('B18b — share sources never reach the charging code', () => {
  // Scoped to import/call syntax (not bare identifiers) so a comment can't false-trip the guard.
  const forbidden = [
    /from ['"][^'"]*\/serve-doc['"]/, /from ['"]@\/lib\/gemini['"]/, /from ['"]@\/lib\/gemini-cost['"]/,
    /resolveMagazineModel\s*\(/, /generateMagazineModel\s*\(/, /reserve_serve_model/, /\.rpc\s*\(/,
  ];
  it('scans a non-empty set including the serve route', () => {
    expect(shareSources.length).toBeGreaterThan(0);
    expect(shareSources.some((f) => f.endsWith('app/s/[token]/route.ts'))).toBe(true);
  });
  it.each(shareSources)('%s imports/calls nothing that charges', (file) => {
    const src = readFileSync(file, 'utf-8');
    for (const re of forbidden) expect(src).not.toMatch(re);
  });
});
```

> **No ESLint step.** The repo has no ESLint config, dependency, or `lint` script (verified). The static money guard is therefore the jest `import-guard.test.ts` above (grep-based), NOT an `no-restricted-imports` rule. Do not add ESLint for this slice.

- [ ] **Step 5: Run to verify pass + tsc**

Run: `npx jest import-guard && npm run test:integration -- --runInBand -t "share-route" && npx tsc --noEmit`
Expected: all PASS/clean. **Sanity-check the guard is not vacuous:** temporarily add `import '@/lib/gemini';` to `app/s/[token]/route.ts`, confirm `npx jest import-guard` FAILS (both the "non-empty set" expectation still passes and the per-file grep now trips), then revert and confirm it passes again.

- [ ] **Step 6: Commit**

```bash
git add "app/s/[token]/route.ts" tests/lib/share/import-guard.test.ts tests/integration/share-route.test.ts
git commit -m "feat(1f-b): anonymous /s/[token] serve route + money-invariant proof + import guard"
```

---

## Verification (end of stage)

1. `npx tsc --noEmit` — 0 errors.
2. `npx jest` — full unit suite green (grows with Tasks 1,3,4,7 unit tests).
3. `npx supabase db reset && npm run test:integration -- --runInBand` — all green (Tasks 2, 6, 7 integration).
4. `npx jest import-guard` — passes, and demonstrably FAILS on a deliberately-bad import (Task 7 Step 5 sanity check). (No `npm run lint` — the repo has no ESLint.)
5. Behaviors B1–B24 each have a covering test (map each row to its test in the per-task review).
6. Each of Tasks 1, 2, 6, 7 cleared per-task dual adversarial review (Claude + Codex) with §8 iterative re-review; reviews saved to `docs/reviews/task-1f-b-N-<name>-{review,codex}.md`.
7. Stage-complete: `superpowers:finishing-a-development-branch` → whole-branch holistic review → PR to `master` (`gh ... --repo kujinlee/youtube-playlist-summaries-cloud`; two-remotes footgun).

## Self-Review notes (author)

- **Spec coverage:** D1–D16 → Tasks: D2/D3/D13 (T1+T7), D5/D6 (T3), D7 (T2+T3), D8/D14 (T2+T7 re-check), D9 (T2), D10 (T4+T7), D11 (T6+T7), D15 (T6), D16 (T1+T7). Behaviors B1–B24 → T2 (B1–B5c,B14–B17,B23,B24), T4 (B22), T6 (B9–B13,B19b), T7 (B6–B8,B10b,B13b,B18–B21). RPCs (create/revoke/revoke-all/list) → T2. Routes (mint/revoke/revoke-all/serve) → T5/T7.
- **Resolved during plan review (Post-Plan Gate, v2):** `ARTIFACTS_BUCKET` = `@/lib/supabase/storage-env`; `videos.data` JSONB shape confirmed via existing `seedPromotedVideo` (`artifacts.summaryMd.{key,status}` + top-level `summaryMd`); repo has NO ESLint (guard is a jest grep test); `token_hash` stored as hex `text` (not `bytea`, which won't serialize over PostgREST). The `seed.ts` helpers (`seedPlaylist`/`seedPromotedVideo`/`seedSummaryBlob`) already exist and match `0001` — compose them, don't recreate.
- **Confirm during execution:** the existing `tests/api/*` mocking harness shape (Task 5); the `tests/integration/*` route-invocation harness (Task 7). Each task's first step is a failing test that surfaces any mismatch immediately.
