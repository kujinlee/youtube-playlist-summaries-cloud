# Stage 1C — Supabase Adapters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship async, transactional `SupabaseMetadataStore` + `SupabaseBlobStore` on the 1B schema, behind capability contracts, verified against a local Supabase stack — while the personal local workflow stays byte-for-byte unchanged and default.

**Architecture:** Extend the 1A `lib/storage/` seam. Make `MetadataStore` async + intent-specific (retire whole-index `writeIndex`); add a new `BlobStore` contract. Provide local impls (wrap today's FS/`index-store` behavior) and Supabase impls (Postgres rows + Storage objects, RLS-isolated). A single `getStorageBundle()` selects the backend; cloud is reached only via tests in 1C (routes stay local, guarded by `getPrincipalFromSession()`).

**Tech Stack:** TypeScript, Next.js (App Router), `@supabase/supabase-js` ^2.109, `@supabase/ssr`, Postgres (local Supabase CLI stack), Jest + ts-jest, Zod.

## Global Constraints

- **Next.js APIs differ from training data** — read `node_modules/next/dist/docs/` before writing framework code (per `AGENTS.md`).
- **Local behavior is frozen:** the local bundle must reproduce today's `-data` layout and `playlist-index.json` semantics byte-for-byte. The existing ~1505-test unit suite staying green is a required regression gate.
- **`tsc --noEmit` is a required gate** on every task that touches the async conversion (F1).
- **Serial field is `serialNumber`** (integer, in `videos.data`), not `serial`.
- **`Principal.id` → `owner_id`; `Principal.indexKey` → `playlist_key`.** The `PlaylistIndex.outputFolder` *field* keeps its name (local concept); only the `Principal` field is renamed.
- **RLS:** user ops use the authenticated/anon client (RLS applies). Every new RPC carries an explicit owner guard mirroring `reorder_videos` (0005).
- **Supabase Storage `move` is copy+delete (non-atomic)** — `promote` must be idempotent.
- **Source-of-truth blobs (MD, slides) never regenerate on miss** → `repair_needed`. Derived caches (HTML, PDF) regenerate.
- **No new runtime deps.** `@supabase/supabase-js` is already present.
- **Integration tests** live in `tests/integration/`, run via `npm run test:integration` (`--runInBand`), use `tests/integration/helpers/clients.ts` (`adminClient`, `newUser`, `signInAs`, `anonSession`). They require a running local stack (`npx supabase start && npx supabase status -o env > .env.test.local`).

---

## Canonical Signatures (used across tasks — keep consistent)

```ts
// lib/storage/principal.ts
export interface Principal { readonly id: string; readonly indexKey: string; }
export const LOCAL_PRINCIPAL_ID = 'local';
export function localPrincipal(indexKey: string): Principal;

// lib/storage/metadata-store.ts
export interface MetadataStore {
  readIndex(p: Principal): Promise<PlaylistIndex>;
  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
  claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }>;
  upsertVideo(p: Principal, video: Video): Promise<void>;
  updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
  bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void>;
  reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void>;
  deleteVideo(p: Principal, videoId: string): Promise<void>;  // rollback a reserved-but-failed video (post-T4-review fix)
}

// lib/storage/blob-store.ts
export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';
export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }
export interface BlobStore {
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;
}

// lib/storage/empty-index.ts
export function emptyPlaylistIndex(p: Principal): PlaylistIndex;   // { playlistUrl:'', outputFolder: p.indexKey, videos: [] }

// lib/storage/resolve.ts
export function getPrincipal(indexKey: string): Principal;         // local sentinel; runs assertOutputFolder
export function getPrincipalFromSession(session: { userId: string | null }, indexKey: string): Principal; // cloud; hard-fails
export function getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): { metadataStore: MetadataStore; blobStore: BlobStore };

// Supabase impls take an injected RLS-scoped client:
export class SupabaseMetadataStore implements MetadataStore { constructor(client: SupabaseClient) {} }
export class SupabaseBlobStore implements BlobStore { constructor(client: SupabaseClient, bucket: string) {} }
export const ARTIFACTS_BUCKET = 'artifacts';
```

---

# Phase 1 — Async interface + local parity (no cloud yet)

### Task 1: Rename `Principal.outputFolder` → `indexKey`

**Files:**
- Modify: `lib/storage/principal.ts`
- Modify: `lib/storage/resolve.ts:13-16` (`getPrincipal`)
- Modify: `lib/storage/local/local-metadata-store.ts` (uses `principal.outputFolder`)
- Test: `tests/lib/storage/principal.test.ts` (create if absent)

**Interfaces:**
- Produces: `Principal { id, indexKey }`, `localPrincipal(indexKey)`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/storage/principal.test.ts
import { localPrincipal, LOCAL_PRINCIPAL_ID } from '@/lib/storage/principal';

test('localPrincipal carries the raw indexKey and the local sentinel id', () => {
  const p = localPrincipal('/Users/me/data/playlist');
  expect(p.id).toBe(LOCAL_PRINCIPAL_ID);
  expect(p.indexKey).toBe('/Users/me/data/playlist');
});
```

- [ ] **Step 2: Run — expect FAIL** (`indexKey` does not exist yet)

Run: `npx jest tests/lib/storage/principal.test.ts`
Expected: FAIL (type error / undefined `indexKey`).

- [ ] **Step 3: Rename the field**

```ts
// lib/storage/principal.ts
export interface Principal {
  readonly id: string;
  readonly indexKey: string;   // local: on-disk data root; cloud: playlist_key (YouTube list-id)
}
export const LOCAL_PRINCIPAL_ID = 'local';
export function localPrincipal(indexKey: string): Principal {
  return { id: LOCAL_PRINCIPAL_ID, indexKey };
}
```

Update `lib/storage/local/local-metadata-store.ts` — replace every `principal.outputFolder` with `principal.indexKey`. Update `lib/storage/resolve.ts:15` `return localPrincipal(outputFolder)` (rename the local variable to `indexKey` for clarity; keep the raw string — do NOT `path.resolve`).

- [ ] **Step 4: Run tests + type-check**

Run: `npx jest tests/lib/storage && npx tsc --noEmit`
Expected: PASS, no type errors.

- [ ] **Step 5: Commit**

```bash
git add lib/storage/ tests/lib/storage/principal.test.ts
git commit -m "refactor(storage): rename Principal.outputFolder -> indexKey"
```

---

### Task 2: `emptyPlaylistIndex` helper + relax `PlaylistIndexSchema.playlistUrl`

**Files:**
- Create: `lib/storage/empty-index.ts`
- Modify: `types/index.ts:80` (`PlaylistIndexSchema.playlistUrl`)
- Test: `tests/lib/storage/empty-index.test.ts`, `tests/lib/types/playlist-index-empty.test.ts`

**Interfaces:**
- Produces: `emptyPlaylistIndex(p: Principal): PlaylistIndex`.

- [ ] **Step 1: Write the failing tests**

```ts
// tests/lib/storage/empty-index.test.ts
import { emptyPlaylistIndex } from '@/lib/storage/empty-index';
import { localPrincipal } from '@/lib/storage/principal';
import { PlaylistIndexSchema } from '@/types';

test('emptyPlaylistIndex is a schema-valid empty index carrying indexKey as outputFolder', () => {
  const idx = emptyPlaylistIndex(localPrincipal('/data/pl'));
  expect(idx).toEqual({ playlistUrl: '', outputFolder: '/data/pl', videos: [] });
  expect(() => PlaylistIndexSchema.parse(idx)).not.toThrow();   // '' must be accepted
});
```

- [ ] **Step 2: Run — expect FAIL** (`''` fails `z.string().url()`; module missing)

Run: `npx jest tests/lib/storage/empty-index.test.ts`
Expected: FAIL.

- [ ] **Step 3: Relax the schema + add the helper**

```ts
// types/index.ts — replace line 80
  playlistUrl: z.union([z.string().url(), z.literal('')]),   // '' = absent-index sentinel (empty read)
```

```ts
// lib/storage/empty-index.ts
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex } from '@/types';

/** The exact shape lib/index-store.readIndex returns for an absent index file,
 *  produced identically by local and cloud MetadataStore impls. */
export function emptyPlaylistIndex(p: Principal): PlaylistIndex {
  return { playlistUrl: '', outputFolder: p.indexKey, videos: [] };
}
```

- [ ] **Step 4: Run tests + full suite** (schema change is global)

Run: `npx jest tests/lib/storage/empty-index.test.ts && npm test`
Expected: PASS; no regressions from the schema relaxation.

- [ ] **Step 5: Commit**

```bash
git add lib/storage/empty-index.ts types/index.ts tests/lib/storage/empty-index.test.ts
git commit -m "feat(storage): emptyPlaylistIndex helper + allow '' playlistUrl for empty reads"
```

---

### Task 3: Async + reshape `MetadataStore` + `LocalFsMetadataStore`

**Files:**
- Modify: `lib/storage/metadata-store.ts` (interface)
- Modify: `lib/storage/local/local-metadata-store.ts` (impl)
- Modify: `lib/index-store.ts` (add `nextSerial`-aware helpers if not present; see Step 3)
- Test: `tests/lib/storage/local-metadata-store.test.ts`

**Interfaces:**
- Consumes: `emptyPlaylistIndex` (Task 2), `Principal.indexKey` (Task 1).
- Produces: the async `MetadataStore` (7 methods, canonical signatures). `LocalFsMetadataStore` implementing them via `index-store`.

Reference — current local reconcile/serial logic to preserve: `lib/pipeline.ts:388-398` (membership archive/restore), `lib/pipeline.ts:317` (`nextSerial(readIndex().videos)`), `lib/serial-*.ts` (`nextSerial`).

- [ ] **Step 1: Write failing tests** (behavior parity for the new methods)

```ts
// tests/lib/storage/local-metadata-store.test.ts
import fs from 'fs'; import os from 'os'; import path from 'path';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

const store = new LocalFsMetadataStore();
function tmp() { return fs.mkdtempSync(path.join(os.tmpdir(), 'lms-')); }

test('readIndex on an empty folder returns the empty index shape', async () => {
  const p = localPrincipal(tmp());
  await expect(store.readIndex(p)).resolves.toEqual({ playlistUrl: '', outputFolder: p.indexKey, videos: [] });
});

test('claimVideoSlot appends position (0-based) and serialNumber (1-based)', async () => {
  const p = localPrincipal(tmp());
  await store.setPlaylistMeta(p, { playlistUrl: 'https://youtube.com/playlist?list=X' });
  const a = await store.claimVideoSlot(p, 'vid00000001');
  const b = await store.claimVideoSlot(p, 'vid00000002');
  expect(a).toEqual({ position: 0, serialNumber: 1 });
  expect(b).toEqual({ position: 1, serialNumber: 2 });
});

test('bulkUpdateVideoFields merges fields, preserves array order', async () => {
  const p = localPrincipal(tmp());
  await store.claimVideoSlot(p, 'vid00000001');
  await store.upsertVideo(p, { id: 'vid00000001', youtubeUrl: 'https://youtu.be/vid00000001' } as any);
  await store.bulkUpdateVideoFields(p, [{ videoId: 'vid00000001', fields: { playlistIndex: 5 } as any }]);
  const idx = await store.readIndex(p);
  expect(idx.videos[0].playlistIndex).toBe(5);
});

test('reconcilePlaylistMembership archives absent, restores present', async () => {
  const p = localPrincipal(tmp());
  await store.claimVideoSlot(p, 'vid00000001');
  await store.upsertVideo(p, { id: 'vid00000001', youtubeUrl: 'https://youtu.be/vid00000001', archived: true, removedFromPlaylist: true } as any);
  await store.reconcilePlaylistMembership(p, ['vid00000001']);   // now present again
  const idx = await store.readIndex(p);
  expect(idx.videos[0].archived).toBe(false);
  expect(idx.videos[0].removedFromPlaylist).toBe(false);
});
```

- [ ] **Step 2: Run — expect FAIL** (methods not defined / not async)

Run: `npx jest tests/lib/storage/local-metadata-store.test.ts`
Expected: FAIL.

- [ ] **Step 3: Rewrite interface + local impl**

```ts
// lib/storage/metadata-store.ts
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';

export interface MetadataStore {
  readIndex(p: Principal): Promise<PlaylistIndex>;
  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
  claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }>;
  upsertVideo(p: Principal, video: Video): Promise<void>;
  updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
  bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void>;
  reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void>;
  deleteVideo(p: Principal, videoId: string): Promise<void>;  // rollback a reserved-but-failed video (post-T4-review fix)
}
```

```ts
// lib/storage/local/local-metadata-store.ts
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import * as indexStore from '@/lib/index-store';
import { nextSerial } from '@/lib/serial-assign';   // confirm exact export path via `grep -rn "export function nextSerial" lib`

/** Behavior-preserving local impl. Sync index-store calls wrapped in resolved Promises;
 *  the new transactional methods replicate today's pipeline logic against the JSON file. */
export class LocalFsMetadataStore implements MetadataStore {
  async readIndex(p: Principal): Promise<PlaylistIndex> {
    return indexStore.readIndex(p.indexKey);
  }
  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
    const idx = indexStore.readIndex(p.indexKey);
    indexStore.writeIndex(p.indexKey, {
      ...idx,
      playlistUrl: meta.playlistUrl,
      outputFolder: p.indexKey,
      ...(meta.playlistTitle ? { playlistTitle: meta.playlistTitle } : {}),
    });
  }
  async claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }> {
    const idx = indexStore.readIndex(p.indexKey);
    const position = idx.videos.length;
    const serialNumber = nextSerial(idx.videos);   // 1-based next serial from existing videos
    // reserve the slot with a minimal valid Video (id present); real data arrives via upsertVideo
    indexStore.upsertVideo(p.indexKey, { id: videoId, serialNumber } as Video);
    return { position, serialNumber };
  }
  async upsertVideo(p: Principal, video: Video): Promise<void> {
    indexStore.upsertVideo(p.indexKey, video);
  }
  async updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void> {
    indexStore.updateVideoFields(p.indexKey, id, fields);
  }
  async bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void> {
    for (const { videoId, fields } of patches) indexStore.updateVideoFields(p.indexKey, videoId, fields);
  }
  async reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void> {
    const present = new Set(currentPlaylistIds);
    const idx = indexStore.readIndex(p.indexKey);
    for (const v of idx.videos) {
      const inPlaylist = present.has(v.id);
      indexStore.updateVideoFields(p.indexKey, v.id, {
        archived: !inPlaylist, removedFromPlaylist: !inPlaylist,
      } as Partial<Video>);
    }
  }
}
export const localMetadataStore = new LocalFsMetadataStore();
```

> Confirm `nextSerial`'s exact module before importing: `grep -rn "function nextSerial" lib`. If serial-assignment currently lives inline in `pipeline.ts`, extract it to `lib/serial-assign.ts` (pure function `nextSerial(videos: Video[]): number`) as part of this task and update `pipeline.ts` to import it — so both pipeline and the store share one implementation (DRY).

- [ ] **Step 4: Run tests + type-check**

Run: `npx jest tests/lib/storage/local-metadata-store.test.ts && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/storage/metadata-store.ts lib/storage/local/local-metadata-store.ts lib/serial-assign.ts tests/lib/storage/local-metadata-store.test.ts
git commit -m "feat(storage): async transactional MetadataStore + local impl parity"
```

---

### Task 4: Convert all consumers to `await` + new methods (+ delayed-async fake)

**Files (modify — `store.` call sites):**
- `lib/pipeline.ts` (lines ~178, 199, 283-284, 290, 317, 358, 388-398, 406, 417)
- `lib/archive.ts:16,66,86`
- `lib/summary-audit.ts:19`, `lib/timestamp-audit.ts:36`, `lib/timestamp-repair.ts:22`
- `lib/serial-migrate-exec.ts:11,18,72,147`
- `lib/playlists/backfill-titles.ts:32,36`
- `lib/html-doc/generate.ts:21,79`, `rerender.ts:34,103`, `batch.ts:57`, `ensure.ts:30,47,66`
- `lib/dig/dig-section.ts:23,105`
- `app/api/videos/[id]/regenerate/route.ts`, `review/route.ts`, `quick-view/route.ts`
- Create: `tests/lib/storage/delayed-async-fake.ts` (test util), `tests/lib/pipeline-async.test.ts`

**Interfaces:**
- Consumes: async `MetadataStore` (Task 3).

Conversion rules (apply verbatim):
- Every `store.readIndex(principal)` → `await store.readIndex(principal)`; propagate `async` up each call chain.
- `store.writeIndex(principal, {...existing, playlistUrl, outputFolder, ...title})` (`pipeline:284`, `backfill-titles:36`) → `await store.setPlaylistMeta(principal, { playlistUrl, playlistTitle })`. In `backfill-titles`, read `playlistUrl` from the already-loaded index and pass it.
- `pipeline:317` `const serial = nextSerial(...)` + later `upsertVideo` for a NEW video → `const { serialNumber } = await store.claimVideoSlot(principal, videoId)`; build the `Video` with `serialNumber`; then `await store.upsertVideo(principal, video)` to fill full data.
- `pipeline:388-398` reconcile loop → `await store.reconcilePlaylistMembership(principal, [...positionMap.keys()])` (the current playlist ids). Delete the per-video archive/restore loop.
- `pipeline:417` `store.writeIndex(principal, {...afterReconcile, videos: videosWithIndex})` → build `patches` = videos mapped to `{ videoId: v.id, fields: { playlistIndex, videoPublishedAt, addedToPlaylistAt } }` (only the three computed fields) → `await store.bulkUpdateVideoFields(principal, patches)`.
- `serial-migrate-exec:18` `store.writeIndex(...videos)` → `await store.bulkUpdateVideoFields(principal, videos.map(v => ({ videoId: v.id, fields: { serialNumber: v.serialNumber } })))`.
- API route handlers are already `async` — add `await` at each store call.

- [ ] **Step 1: Write the delayed-async fake + a pipeline async test (RED)**

```ts
// tests/lib/storage/delayed-async-fake.ts
import type { MetadataStore } from '@/lib/storage/metadata-store';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';

const tick = () => new Promise((r) => setTimeout(r, 5));

/** Wraps the local store but resolves each method AFTER a real macrotask, exposing any
 *  consumer that reads a store value without awaiting (F1). */
export function delayedStore(inner: MetadataStore = new LocalFsMetadataStore()): MetadataStore {
  const wrap = <T>(fn: () => Promise<T>) => tick().then(fn);
  return {
    readIndex: (p) => wrap(() => inner.readIndex(p)),
    setPlaylistMeta: (p, m) => wrap(() => inner.setPlaylistMeta(p, m)),
    claimVideoSlot: (p, v) => wrap(() => inner.claimVideoSlot(p, v)),
    upsertVideo: (p, v) => wrap(() => inner.upsertVideo(p, v)),
    updateVideoFields: (p, i, f) => wrap(() => inner.updateVideoFields(p, i, f)),
    bulkUpdateVideoFields: (p, x) => wrap(() => inner.bulkUpdateVideoFields(p, x)),
    reconcilePlaylistMembership: (p, ids) => wrap(() => inner.reconcilePlaylistMembership(p, ids)),
  };
}
```

**Enumerate behaviors first** (per the per-task checklist) — the delayed-async fake must exercise:

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | A missed `await` throws | `.videos`/`.map`/`.length`/`.has` on an unresolved Promise | test fails loudly (regression caught) |
| 2 | Full sync completes under delay | run pipeline with `delayedStore()` | index has each video with `serialNumber` + `playlistIndex` set |
| 3 | Re-run is idempotent | run the same sync twice | no duplicate video entries; `alreadyIndexed` skip path taken |

**Reuse the existing harness:** `tests/lib/pipeline.test.ts` (60 KB) already mocks `lib/gemini` + `lib/youtube` and drives the pipeline entrypoint. Copy its mock setup verbatim; the only change is injecting `delayedStore()` as the store. Do NOT invent mock shapes — mirror `pipeline.test.ts`.

```ts
// tests/lib/pipeline-async.test.ts
// ... copy the lib/gemini + lib/youtube jest.mock(...) blocks and the pipeline import
//     from tests/lib/pipeline.test.ts (same fixtures, same entrypoint) ...

// Task 4: pipeline imports `localMetadataStore` directly → jest.mock that module to return delayedStore().
// Task 7 (later): pipeline switches to getStorageBundle() → change the mock target to '@/lib/storage/resolve'.
jest.mock('@/lib/storage/local/local-metadata-store', () => {
  const { delayedStore } = require('../lib/storage/delayed-async-fake'); // tests/lib/storage/delayed-async-fake.ts
  return { localMetadataStore: delayedStore() };
});

test('sync under a delayed store completes and stamps serialNumber + playlistIndex', async () => {
  const outputFolder = /* tmp dir as in pipeline.test.ts */;
  await runPipeline(/* same args as pipeline.test.ts happy-path */);      // entrypoint from pipeline.test.ts
  const idx = readIndexFromDisk(outputFolder);
  expect(idx.videos.length).toBeGreaterThan(0);
  expect(idx.videos.every(v => typeof v.serialNumber === 'number')).toBe(true);
  expect(idx.videos.every(v => typeof v.playlistIndex === 'number')).toBe(true);
});

test('re-running the sync does not duplicate videos (alreadyIndexed skip)', async () => {
  const outputFolder = /* tmp dir */;
  await runPipeline(/* args */); const first = readIndexFromDisk(outputFolder).videos.length;
  await runPipeline(/* same args */); const second = readIndexFromDisk(outputFolder).videos.length;
  expect(second).toBe(first);
});
```

> The fake lives at `tests/lib/storage/delayed-async-fake.ts` (Step 1). `pipeline-async.test.ts` sits at `tests/lib/pipeline-async.test.ts`, so the relative import is `../lib/storage/delayed-async-fake`.

- [ ] **Step 2: Run — expect FAIL** (consumers still sync)

Run: `npx jest tests/lib/pipeline-async.test.ts`
Expected: FAIL (or type errors on un-awaited Promises).

- [ ] **Step 3: Apply the conversion rules** across every file listed. Work file-by-file; after each file run its targeted test (`npx jest <file>`).

- [ ] **Step 4: Full suite + type gate**

Run: `npx tsc --noEmit && npm test`
Expected: PASS (the whole existing suite — this is the regression proof for the async sweep).

- [ ] **Step 5: Commit**

```bash
git add lib/ app/ tests/lib/storage/delayed-async-fake.ts tests/lib/pipeline-async.test.ts
git commit -m "refactor(storage): await MetadataStore across all consumers; drop writeIndex usage"
```

---

# Phase 2 — BlobStore + local impl + extraction

### Task 5: `BlobStore` interface + `LocalFsBlobStore`

**Files:**
- Create: `lib/storage/blob-store.ts`, `lib/storage/local/local-blob-store.ts`
- Test: `tests/lib/storage/local-blob-store.test.ts`

**Interfaces:**
- Produces: `BlobStore`, `BlobStatus`, `StagedRef`, `LocalFsBlobStore`, `localBlobStore`.

- [ ] **Step 1: Failing tests**

```ts
// tests/lib/storage/local-blob-store.test.ts
import fs from 'fs'; import os from 'os'; import path from 'path';
import { LocalFsBlobStore } from '@/lib/storage/local/local-blob-store';
import { localPrincipal } from '@/lib/storage/principal';

const store = new LocalFsBlobStore();
const p = () => localPrincipal(fs.mkdtempSync(path.join(os.tmpdir(), 'lbs-')));

test('put then get round-trips; get on absent key is null', async () => {
  const pr = p();
  await store.put(pr, 'a/b.md', Buffer.from('hi'), 'text/markdown');
  expect((await store.get(pr, 'a/b.md'))?.toString()).toBe('hi');
  expect(await store.get(pr, 'missing.md')).toBeNull();
});

test('put writes atomically under indexKey (byte-for-byte layout)', async () => {
  const pr = p();
  await store.put(pr, 'models/x.json', Buffer.from('{}'), 'application/json');
  expect(fs.existsSync(path.join(pr.indexKey, 'models/x.json'))).toBe(true);
});

test('putStaged + promote makes the final key readable', async () => {
  const pr = p();
  const ref = await store.putStaged(pr, 'out.html', Buffer.from('<x>'), 'text/html');
  expect(await store.get(pr, 'out.html')).toBeNull();     // not visible before promote
  await store.promote(ref);
  expect((await store.get(pr, 'out.html'))?.toString()).toBe('<x>');
});

test('rejects traversal keys', async () => {
  await expect(store.put(p(), '../escape', Buffer.from('x'), 'text/plain')).rejects.toThrow();
});
```

- [ ] **Step 2: Run — expect FAIL**

Run: `npx jest tests/lib/storage/local-blob-store.test.ts` → FAIL.

- [ ] **Step 3: Implement**

```ts
// lib/storage/blob-store.ts
import type { Principal } from '@/lib/storage/principal';
export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';
export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }
export interface BlobStore {
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;
}
export function assertLogicalKey(key: string): void {
  if (key.startsWith('/') || key.split('/').includes('..') || key.includes('\0')) {
    throw Object.assign(new Error(`invalid blob key: ${key}`), { statusCode: 400 });
  }
}
```

```ts
// lib/storage/local/local-blob-store.ts
import fs from 'fs'; import path from 'path'; import crypto from 'crypto';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

/** Byte-for-byte the current -data layout: physical path = join(indexKey, key). */
export class LocalFsBlobStore implements BlobStore {
  private abs(p: Principal, key: string): string { assertLogicalKey(key); return path.join(p.indexKey, key); }
  async put(p: Principal, key: string, bytes: Buffer): Promise<void> {
    const dest = this.abs(p, key); fs.mkdirSync(path.dirname(dest), { recursive: true });
    const tmp = dest + '.' + crypto.randomUUID() + '.tmp';
    try { fs.writeFileSync(tmp, bytes); fs.renameSync(tmp, dest); }
    catch (e) { try { fs.unlinkSync(tmp); } catch {} throw e; }
  }
  async get(p: Principal, key: string): Promise<Buffer | null> {
    try { return fs.readFileSync(this.abs(p, key)); }
    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
  }
  async exists(p: Principal, key: string): Promise<boolean> { return (await this.get(p, key)) !== null; }
  async delete(p: Principal, key: string): Promise<void> {
    try { fs.unlinkSync(this.abs(p, key)); } catch (e: any) { if (e.code !== 'ENOENT') throw e; }
  }
  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    const tempKey = `_staging/${crypto.randomUUID()}/${key}`;
    await this.put(p, tempKey, bytes, contentType);
    return { principal: p, tempKey, finalKey: key };
  }
  async promote(ref: StagedRef): Promise<void> {
    const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
    fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
  }
}
export const localBlobStore = new LocalFsBlobStore();
```

- [ ] **Step 4: Run tests** → PASS. `npx jest tests/lib/storage/local-blob-store.test.ts`

- [ ] **Step 5: Commit**

```bash
git add lib/storage/blob-store.ts lib/storage/local/local-blob-store.ts tests/lib/storage/local-blob-store.test.ts
git commit -m "feat(storage): BlobStore contract + LocalFsBlobStore (temp->rename, staged/promote)"
```

---

### Task 6: Route source-of-truth blob writes through `BlobStore`

**Files (modify — replace direct FS writes with `blobStore.put`, reads with `blobStore.get`):**
- `lib/pipeline.ts:103` (summary MD)
- `lib/html-doc/model-store.ts:34-39` (model JSON)
- `lib/html-doc/generate.ts:63-70`, `lib/html-doc/rerender.ts:68-72` (HTML)
- `lib/pdf/generate-doc-pdf.ts:24,61-62` (PDF)
- `lib/dig/slides.ts:171` (slide images)
- Test: extend each module's existing test to assert the blob is written via the store (inject a fake `BlobStore`).

**Interfaces:**
- Consumes: `BlobStore` (Task 5). Each module obtains it via a parameter/accessor — pass `blobStore` in, defaulting to `localBlobStore`, so tests inject a fake and Task 7 can swap the bundle.

Rules:
- Compute the **logical key** in the calling module exactly as today's relative path. **Verify each against the current code — do not guess:**
  - MD `` `${baseName}.md` `` (`pipeline.ts:103`)
  - model JSON `` `models/${id}.json` `` (`html-doc/model-store.ts`)
  - HTML `htmlFilename` (`html-doc/generate.ts`, `rerender.ts`)
  - PDF `` `${baseName}.pdf` `` (`pdf/generate-doc-pdf.ts`)
  - **slide image `` `assets/${videoId}/${assetName}` `` where `assetName` = `` `${sectionId}-${sec}-${end}.jpg` `` (F8 — `dig/slides.ts:158,163,175`, `dig-section.ts:67` writes under `<outputFolder>/assets/<videoId>/`). NOT `${videoId}/slide-NN.png`. The `assets/` prefix is load-bearing: `render-dig-deeper.ts` markdown refs and its containment check both require it.**
  Physical mapping is the store's job (`LocalFsBlobStore` = `join(indexKey, key)`).
- Keep **scratch/cache on direct FS** — do NOT touch `lib/dig/slide-crop-cache.ts` or `.cache` writes.
- Local behavior must be byte-for-byte identical → the existing module tests must stay green.
- In 1C, consumers use `blobStore.put`/`get` only (not `putStaged`/`promote` — the staged flow is cloud-only, tested in Task 12). This keeps the extraction behavior-preserving.

- [ ] **Step 1:** For each module, write/extend a test that injects a fake `BlobStore` and asserts `.put` is called with the expected **logical key** and bytes. (RED)
- [ ] **Step 2:** Run the targeted tests → FAIL.
- [ ] **Step 3:** Replace the FS write with `await blobStore.put(principal, key, Buffer.from(content), contentType)` (and reads with `get`). Thread `principal`/`blobStore` into each function signature where missing (default `localBlobStore`).
- [ ] **Step 4:** Run each module's test + full suite: `npx tsc --noEmit && npm test` → PASS (byte-for-byte parity).
- [ ] **Step 5: Commit**

```bash
git add lib/pipeline.ts lib/html-doc/ lib/pdf/ lib/dig/slides.ts tests/
git commit -m "refactor(storage): route source-of-truth blob writes through BlobStore"
```

---

# Phase 3 — Backend selection seam

### Task 7: `getStorageBundle()` + `STORAGE_BACKEND` + `getPrincipalFromSession()`

**Files:**
- Modify: `lib/storage/resolve.ts`
- Modify: consumers that fetch a store — replace `localMetadataStore`/`localBlobStore` imports with `getStorageBundle()` (`pipeline`, `archive`, `html-doc/*`, `dig/*`, audits, routes).
- Create: `lib/supabase/storage-env.ts` (fail-fast validation)
- Test: `tests/lib/storage/resolve.test.ts`

**Interfaces:**
- Produces: `getStorageBundle(ctx?)`, `getPrincipalFromSession(session, indexKey)`; `getPrincipal(indexKey)` unchanged (local).

- [ ] **Step 1: Failing tests**

```ts
// tests/lib/storage/resolve.test.ts
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';

afterEach(() => { delete process.env.STORAGE_BACKEND; });

test('defaults to the local bundle', () => {
  const { metadataStore, blobStore } = getStorageBundle();
  expect(metadataStore).toBeInstanceOf(LocalFsMetadataStore);
  expect(blobStore).toBeDefined();
});

test('supabase backend without a client throws (routes not wired in 1C)', () => {
  process.env.STORAGE_BACKEND = 'supabase';
  process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://x'; process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'k';
  expect(() => getStorageBundle()).toThrow(/authenticated client/);
});

test('supabase backend with missing env fails fast', () => {
  process.env.STORAGE_BACKEND = 'supabase';
  delete process.env.NEXT_PUBLIC_SUPABASE_URL;
  expect(() => getStorageBundle({ supabaseClient: {} as any })).toThrow(/Missing required env/);
});

test('getPrincipalFromSession hard-fails when cloud backend but no session', () => {
  process.env.STORAGE_BACKEND = 'supabase';
  expect(() => getPrincipalFromSession({ userId: null }, 'listX')).toThrow(/no authenticated/i);
});
```

- [ ] **Step 2: Run — FAIL.** `npx jest tests/lib/storage/resolve.test.ts`

- [ ] **Step 3: Implement**

```ts
// lib/supabase/storage-env.ts
import { getSupabaseEnv } from './env';
export const ARTIFACTS_BUCKET = 'artifacts';
export function validateStorageEnv(): void { getSupabaseEnv(); }  // throws on missing URL/anon key
```

```ts
// lib/storage/resolve.ts (additions)
import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { validateStorageEnv, ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { localPrincipal, type Principal } from '@/lib/storage/principal';

const LOCAL_BUNDLE = { metadataStore: localMetadataStore as MetadataStore, blobStore: localBlobStore as BlobStore };

export function getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): { metadataStore: MetadataStore; blobStore: BlobStore } {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'local') return LOCAL_BUNDLE;
  if (backend === 'supabase') {
    validateStorageEnv();                       // fail-fast on missing env
    if (!ctx?.supabaseClient) throw new Error('supabase backend requires an authenticated client (routes not wired in 1C)');
    return {
      metadataStore: new SupabaseMetadataStore(ctx.supabaseClient),
      blobStore: new SupabaseBlobStore(ctx.supabaseClient, ARTIFACTS_BUCKET),
    };
  }
  throw new Error(`unknown STORAGE_BACKEND: ${backend}`);
}

export function getPrincipalFromSession(session: { userId: string | null }, indexKey: string): Principal {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') {
    if (!session.userId) throw new Error('supabase backend: no authenticated session for principal');
    return { id: session.userId, indexKey };
  }
  return localPrincipal(indexKey);
}
```

Update consumers: `const { metadataStore, blobStore } = getStorageBundle();` at each entry point that currently imports the local singletons. (Routes stay on `getPrincipal(indexKey)` — do NOT wire `getPrincipalFromSession` into routes in 1C.)

> This step forward-references `SupabaseMetadataStore`/`SupabaseBlobStore` (Tasks 9-10). If executing strictly in order, create stub classes that **implement every interface method** (an empty-constructor class does NOT satisfy `MetadataStore`/`BlobStore` — `tsc` fails, F1). Each method throws. Fill them in Tasks 9-10. Note the stub in the commit message.
>
> ```ts
> // lib/storage/supabase/supabase-metadata-store.ts (stub — replaced in Task 9)
> import type { SupabaseClient } from '@supabase/supabase-js';
> import type { MetadataStore } from '@/lib/storage/metadata-store';
> const NI = () => { throw new Error('not implemented — stub for Task 7; filled in Task 9'); };
> export class SupabaseMetadataStore implements MetadataStore {
>   constructor(_client: SupabaseClient) {}
>   readIndex = NI as MetadataStore['readIndex'];
>   setPlaylistMeta = NI as MetadataStore['setPlaylistMeta'];
>   claimVideoSlot = NI as MetadataStore['claimVideoSlot'];
>   upsertVideo = NI as MetadataStore['upsertVideo'];
>   updateVideoFields = NI as MetadataStore['updateVideoFields'];
>   bulkUpdateVideoFields = NI as MetadataStore['bulkUpdateVideoFields'];
>   reconcilePlaylistMembership = NI as MetadataStore['reconcilePlaylistMembership'];
> }
> // lib/storage/supabase/supabase-blob-store.ts (stub — replaced in Task 10): same pattern for
> // put/get/exists/delete/putStaged/promote (6 methods), constructor(_client, _bucket).
> ```

- [ ] **Step 4:** `npx tsc --noEmit && npm test` → PASS.
- [ ] **Step 5: Commit**

```bash
git add lib/storage/resolve.ts lib/supabase/storage-env.ts lib/ app/ tests/lib/storage/resolve.test.ts
git commit -m "feat(storage): getStorageBundle backend selection + getPrincipalFromSession guard"
```

---

# Phase 4 — Supabase implementations

### Task 8: Migration `0007_storage_bucket_rls.sql` + transactional RPCs

**Files:**
- Create: `supabase/migrations/0007_storage_and_rpcs.sql`
- Test: `tests/integration/storage-policy.test.ts` (asserts bucket + policy exist; full cross-user tests in Task 12)

**Interfaces:**
- Produces: `artifacts` private bucket + `storage.objects` RLS; RPCs `claim_video_slot(p_playlist_id uuid, p_video_id text)`, `reconcile_membership(p_playlist_id uuid, p_present text[])`, `merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)`, and `merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)`.

- [ ] **Step 1: Write the SQL**

```sql
-- supabase/migrations/0007_storage_and_rpcs.sql

-- Private bucket for all artifacts.
insert into storage.buckets (id, name, public) values ('artifacts', 'artifacts', false)
  on conflict (id) do nothing;

-- storage.objects RLS: first path segment must equal auth.uid(); service_role full access.
-- name is like '<owner_id>/<playlist_key>/<key>'. split_part(name,'/',1) = owner segment.
-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
create policy "artifacts_owner_rw" on storage.objects
  for all to authenticated, anon
  using (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text)
  with check (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text);
create policy "artifacts_service_all" on storage.objects
  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');

-- claim_video_slot: append a reservation row under a playlist row-lock; returns position + serial.
create function claim_video_slot(p_playlist_id uuid, p_video_id text)
  returns table(position int, serial_number int)
  language plpgsql security invoker set search_path = public as $$
declare v_pos int; v_serial int;
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
    for update;
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  select coalesce(max(v.position) + 1, 0),
         coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial
    from videos v where v.playlist_id = p_playlist_id;

  insert into videos (playlist_id, owner_id, video_id, position, data)
    select p_playlist_id, pl.owner_id, p_video_id, v_pos,
           jsonb_build_object('id', p_video_id, 'serialNumber', v_serial)
      from playlists pl where pl.id = p_playlist_id
    on conflict (playlist_id, video_id) do nothing;   -- idempotent claim

  return query select v_pos, v_serial;
end $$;
revoke all on function claim_video_slot(uuid, text) from public;
grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;

-- reconcile_membership: single-transaction archive/restore by playlist membership.
create function reconcile_membership(p_playlist_id uuid, p_present text[])
  returns void language plpgsql security invoker set search_path = public as $$
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  update videos set data = data || jsonb_build_object(
      'archived', not (video_id = any(p_present)),
      'removedFromPlaylist', not (video_id = any(p_present)))
    where playlist_id = p_playlist_id;
end $$;
revoke all on function reconcile_membership(uuid, text[]) from public;
grant execute on function reconcile_membership(uuid, text[]) to authenticated, service_role;

-- merge_video_data: owner-guarded jsonb field merge. ARTIFACTS-AWARE (F6): the top-level
-- `artifacts` object is deep-merged one level (so writing one artifact kind never clobbers
-- sibling kinds); every other key is a plain shallow merge. Write-once fields (videoPublishedAt/
-- addedToPlaylistAt) are preserved by the caller passing the already-`??`-guarded value (F2b);
-- the accompanying integration test (Task 11) proves re-sync does not overwrite them.
create function merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  update videos set
    data = (data || (p_fields - 'artifacts'))
      || case when p_fields ? 'artifacts'
           then jsonb_build_object('artifacts',
                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
           else '{}'::jsonb end,
    updated_at = now()
   where playlist_id = p_playlist_id and video_id = p_video_id;
end $$;
revoke all on function merge_video_data(uuid, text, jsonb) from public;
grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;

-- merge_video_data_bulk: apply merge_video_data semantics to many videos in ONE transaction.
-- p_patches = jsonb array of { "video_id": text, "fields": jsonb }.
create function merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
declare it jsonb;
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  for it in select * from jsonb_array_elements(p_patches) loop
    update videos set
      data = (data || ((it->'fields') - 'artifacts'))
        || case when (it->'fields') ? 'artifacts'
             then jsonb_build_object('artifacts',
                    coalesce(data->'artifacts', '{}'::jsonb) || ((it->'fields')->'artifacts'))
             else '{}'::jsonb end,
      updated_at = now()
     where playlist_id = p_playlist_id and video_id = it->>'video_id';
  end loop;
end $$;
revoke all on function merge_video_data_bulk(uuid, jsonb) from public;
grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;
```

- [ ] **Step 2: Apply + verify** (requires local stack)

Run: `npx supabase db reset` then `npx supabase status`
Expected: reset applies `0001→0007` with no SQL error.

- [ ] **Step 3: Write the policy-presence test (RED then GREEN)**

```ts
// tests/integration/storage-policy.test.ts
import { adminClient } from './helpers/clients';
test('artifacts bucket exists and is private', async () => {
  const { data } = await adminClient().storage.getBucket('artifacts');
  expect(data?.public).toBe(false);
});
```

- [ ] **Step 4: Run** `npm run test:integration -- storage-policy` → PASS.
- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0007_storage_and_rpcs.sql tests/integration/storage-policy.test.ts
git commit -m "feat(db): 0007 artifacts bucket + storage RLS + claim_video_slot/reconcile RPCs"
```

---

### Task 9: `SupabaseMetadataStore` (unit-tested with a mocked client)

**Files:**
- Create: `lib/storage/supabase/supabase-metadata-store.ts`
- Test: `tests/lib/storage/supabase-metadata-store.test.ts` (mock `SupabaseClient`)

**Interfaces:**
- Consumes: `MetadataStore` (Task 3), `emptyPlaylistIndex` (Task 2), RPCs (Task 8).
- Produces: `class SupabaseMetadataStore implements MetadataStore { constructor(client: SupabaseClient) }`.

Implementation contract (map to §3.2 of the spec). Use the injected client's query builder / `.rpc()`; resolve `playlist_id` from `(owner via RLS, playlist_key = p.indexKey)`.

- [ ] **Step 1: Failing unit tests** — assert each method issues the right call. Example:

```ts
// tests/lib/storage/supabase-metadata-store.test.ts
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';

function mockClient(overrides: any = {}) { /* build a chainable stub recording calls */ }

test('readIndex returns emptyPlaylistIndex when no playlist row', async () => {
  const client = mockClient({ playlistRow: null });
  const store = new SupabaseMetadataStore(client as any);
  const idx = await store.readIndex(localPrincipal('listX'));
  expect(idx).toEqual({ playlistUrl: '', outputFolder: 'listX', videos: [] });
});

test('claimVideoSlot calls the claim_video_slot RPC and returns position+serialNumber', async () => {
  const client = mockClient({ rpc: { claim_video_slot: { position: 2, serial_number: 3 } } });
  const store = new SupabaseMetadataStore(client as any);
  await expect(store.claimVideoSlot(localPrincipal('listX'), 'vid1')).resolves.toEqual({ position: 2, serialNumber: 3 });
});

test('bulkUpdateVideoFields merges each patch (data || fields) in one call batch', async () => { /* assert update calls */ });
test('reconcilePlaylistMembership calls reconcile_membership RPC with present ids', async () => { /* ... */ });
test('setPlaylistMeta upserts on (owner_id, playlist_key)', async () => { /* ... */ });
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement** (representative; complete all 7 methods)

```ts
// lib/storage/supabase/supabase-metadata-store.ts
import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import { emptyPlaylistIndex } from '@/lib/storage/empty-index';

export class SupabaseMetadataStore implements MetadataStore {
  constructor(private client: SupabaseClient) {}

  private async playlistId(p: Principal): Promise<string | null> {
    const { data } = await this.client.from('playlists').select('id').eq('playlist_key', p.indexKey).maybeSingle();
    return data?.id ?? null;
  }

  async readIndex(p: Principal): Promise<PlaylistIndex> {
    const { data: pl } = await this.client.from('playlists')
      .select('playlist_url, playlist_title, id').eq('playlist_key', p.indexKey).maybeSingle();
    if (!pl) return emptyPlaylistIndex(p);
    const { data: rows } = await this.client.from('videos')
      .select('data').eq('playlist_id', pl.id).order('position', { ascending: true });
    return {
      playlistUrl: pl.playlist_url,
      outputFolder: p.indexKey,
      ...(pl.playlist_title ? { playlistTitle: pl.playlist_title } : {}),
      videos: (rows ?? []).map((r) => r.data as Video),
    };
  }

  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
    const { error } = await this.client.from('playlists').upsert(
      { playlist_key: p.indexKey, playlist_url: meta.playlistUrl, playlist_title: meta.playlistTitle ?? null },
      { onConflict: 'owner_id,playlist_key' });
    if (error) throw error;
  }

  async claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }> {
    const id = await this.requirePlaylistId(p);
    const { data, error } = await this.client.rpc('claim_video_slot', { p_playlist_id: id, p_video_id: videoId });
    if (error) throw error;
    const row = Array.isArray(data) ? data[0] : data;
    return { position: row.position, serialNumber: row.serial_number };
  }

  async upsertVideo(p: Principal, video: Video): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.from('videos')
      .update({ data: video }).eq('playlist_id', id).eq('video_id', video.id);
    if (error) throw error;
  }

  async updateVideoFields(p: Principal, videoId: string, fields: Partial<Video>): Promise<void> {
    const id = await this.requirePlaylistId(p);
    // Server-side jsonb merge via the artifacts-aware merge_video_data RPC (Task 8) — avoids a
    // read-modify-write race (F4) and deep-merges the `artifacts` sub-object (F6).
    const { error } = await this.client.rpc('merge_video_data', { p_playlist_id: id, p_video_id: videoId, p_fields: fields });
    if (error) throw error;
  }

  async bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('merge_video_data_bulk', { p_playlist_id: id, p_patches: patches });
    if (error) throw error;
  }

  async reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('reconcile_membership', { p_playlist_id: id, p_present: currentPlaylistIds });
    if (error) throw error;
  }

  // Rollback a reserved-but-failed video (post-T4-review fix). Owner-scoped by RLS; no RPC needed.
  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.from('videos').delete().eq('playlist_id', id).eq('video_id', videoId);
    if (error) throw error;
  }

  private async requirePlaylistId(p: Principal): Promise<string> {
    const id = await this.playlistId(p);
    if (!id) throw new Error(`playlist not found for indexKey=${p.indexKey}`);
    return id;
  }
}
```

> `merge_video_data` + `merge_video_data_bulk` are defined as first-class content in Task 8's `0007` migration (artifacts-aware deep merge, owner-guarded). No retroactive migration edit is needed — Task 8 ships them.

- [ ] **Step 4: Run unit tests + `tsc`** → PASS.
- [ ] **Step 5: Commit**

```bash
git add lib/storage/supabase/supabase-metadata-store.ts supabase/migrations/0007_storage_and_rpcs.sql tests/lib/storage/supabase-metadata-store.test.ts
git commit -m "feat(storage): SupabaseMetadataStore (Postgres, transactional RPCs)"
```

---

### Task 10: `SupabaseBlobStore` + `consistency.ts` (unit-tested with mocked storage)

**Files:**
- Create: `lib/storage/supabase/supabase-blob-store.ts`, `lib/storage/supabase/consistency.ts`
- Test: `tests/lib/storage/supabase-blob-store.test.ts`, `tests/lib/storage/consistency.test.ts`

**Interfaces:**
- Produces: `SupabaseBlobStore implements BlobStore`; `writeArtifact(...)` ordered-write helper + `classifyMissing(kind)`.

- [ ] **Step 1: Failing unit tests** — key derivation, null-on-absent, idempotent promote, ordered-write status transitions. Example:

```ts
test('object key is <owner>/<indexKey>/<logicalKey>', async () => {
  const storage = mockStorage();
  const store = new SupabaseBlobStore(clientWithStorage(storage) as any, 'artifacts');
  await store.put({ id: 'owner-1', indexKey: 'listX' }, 'a/b.md', Buffer.from('x'), 'text/markdown');
  expect(storage.lastUpload.path).toBe('owner-1/listX/a/b.md');
});

test('get returns null when storage 404s', async () => { /* ... */ });
test('promote is idempotent when final already exists and temp is gone', async () => { /* ... */ });
```

```ts
// tests/lib/storage/consistency.test.ts
test('source-blob missing after commit yields repair_needed, no regenerate callback', async () => { /* ... */ });
test('cache-blob missing after commit invokes the regenerate callback', async () => { /* ... */ });
```

- [ ] **Step 2: Run — FAIL.**

- [ ] **Step 3: Implement**

```ts
// lib/storage/supabase/supabase-blob-store.ts
import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

export class SupabaseBlobStore implements BlobStore {
  constructor(private client: SupabaseClient, private bucket: string) {}
  private objectKey(p: Principal, key: string): string { assertLogicalKey(key); return `${p.id}/${p.indexKey}/${key}`; }
  private b() { return this.client.storage.from(this.bucket); }

  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
    if (error) throw error;
  }
  async get(p: Principal, key: string): Promise<Buffer | null> {
    const { data, error } = await this.b().download(this.objectKey(p, key));
    if (error) return null;                       // 404 → null
    return Buffer.from(await data.arrayBuffer());
  }
  async exists(p: Principal, key: string): Promise<boolean> { return (await this.get(p, key)) !== null; }
  async delete(p: Principal, key: string): Promise<void> {
    const { error } = await this.b().remove([this.objectKey(p, key)]);
    if (error) throw error;
  }
  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    const tempKey = `_staging/${key}`;            // full object path adds owner/indexKey prefix
    await this.put(p, tempKey, bytes, contentType);
    return { principal: p, tempKey, finalKey: key };
  }
  async promote(ref: StagedRef): Promise<void> {
    const from = this.objectKey(ref.principal, ref.tempKey);
    const to = this.objectKey(ref.principal, ref.finalKey);
    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    const finalExists = await this.exists(ref.principal, ref.finalKey);
    if (finalExists) { await this.b().remove([from]).catch(() => {}); return; }
    const { error } = await this.b().move(from, to);
    if (error) throw error;
  }
}
```

```ts
// lib/storage/supabase/consistency.ts
import type { BlobStore } from '@/lib/storage/blob-store';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';

export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';
const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];
export const isSourceKind = (k: ArtifactKind) => SOURCE_KINDS.includes(k);

/** Ordered write: putStaged → verify → commit row (status:committed) → promote (status:promoted). */
export async function writeArtifact(opts: {
  meta: MetadataStore; blob: BlobStore; principal: Principal; videoId: string;
  kind: ArtifactKind; key: string; bytes: Buffer; contentType: string;
}): Promise<void> {
  const ref = await opts.blob.putStaged(opts.principal, opts.key, opts.bytes, opts.contentType);
  if (!(await opts.blob.exists(opts.principal, ref.tempKey))) throw new Error('staged upload not verified');
  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
    artifacts: { [opts.kind]: { key: opts.key, status: 'committed' } },
  } as any);
  await opts.blob.promote(ref);
  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
  } as any);
}

/** Read-time classification of a missing blob. */
export async function resolveMissing(opts: {
  kind: ArtifactKind; regenerate: () => Promise<void>;
  markRepair: () => Promise<void>;
}): Promise<'regenerated' | 'repair_needed'> {
  if (isSourceKind(opts.kind)) { await opts.markRepair(); return 'repair_needed'; }
  await opts.regenerate(); return 'regenerated';
}
```

- [ ] **Step 4: Run unit tests + `tsc`** → PASS.
- [ ] **Step 5: Commit**

```bash
git add lib/storage/supabase/supabase-blob-store.ts lib/storage/supabase/consistency.ts tests/lib/storage/supabase-blob-store.test.ts tests/lib/storage/consistency.test.ts
git commit -m "feat(storage): SupabaseBlobStore + ordered-write consistency helper"
```

---

# Phase 5 — Integration tests (real local stack)

### Task 11: Integration — `SupabaseMetadataStore` (CRUD, transactional, RLS)

**Files:**
- Create: `tests/integration/metadata-store.test.ts`

**Interfaces:**
- Consumes: `signInAs`/`newUser`/`anonSession` (`tests/integration/helpers/clients.ts`), `SupabaseMetadataStore`.

Setup per test: `newUser()` → `signInAs()` → `new SupabaseMetadataStore(client)`; seed a playlist via `setPlaylistMeta`.

- [ ] **Step 1: Write the tests**

```ts
// tests/integration/metadata-store.test.ts
import { newUser, signInAs } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';

async function storeForNewUser() {
  const u = await newUser(); const { client } = await signInAs(u.email, u.password);
  return new SupabaseMetadataStore(client);
}
const P = { id: '', indexKey: 'listX' };   // id unused (RLS derives owner from JWT)

test('empty read parity', async () => {
  const s = await storeForNewUser();
  await expect(s.readIndex(P)).resolves.toEqual({ playlistUrl: '', outputFolder: 'listX', videos: [] });
});

test('setPlaylistMeta create then update; claimVideoSlot allocates position+serial; readIndex round-trips', async () => {
  const s = await storeForNewUser();
  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX', playlistTitle: 'T' });
  const a = await s.claimVideoSlot(P, 'vidAAAAAAAA');
  expect(a).toEqual({ position: 0, serialNumber: 1 });
  await s.upsertVideo(P, { id: 'vidAAAAAAAA', youtubeUrl: 'https://youtu.be/vidAAAAAAAA', serialNumber: 1 } as any);
  const idx = await s.readIndex(P);
  expect(idx.playlistUrl).toContain('list=listX');
  expect(idx.videos.map(v => v.id)).toEqual(['vidAAAAAAAA']);
});

test('bulkUpdateVideoFields preserves all three fields + array order', async () => { /* per spec §8 case 5 */ });

test('write-once fields survive re-sync (F2b): second bulkUpdate with the ??-guarded value does not overwrite', async () => {
  const s = await storeForNewUser();
  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
  await s.claimVideoSlot(P, 'vidAAAAAAAA');
  await s.upsertVideo(P, { id: 'vidAAAAAAAA', youtubeUrl: 'https://youtu.be/vidAAAAAAAA', serialNumber: 1 } as any);
  // first sync sets the write-once fields
  await s.bulkUpdateVideoFields(P, [{ videoId: 'vidAAAAAAAA', fields: { videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-02-01T00:00:00Z', playlistIndex: 1 } as any }]);
  // second sync: caller re-applies the ?? guard → passes the SAME existing value → no overwrite
  const cur = (await s.readIndex(P)).videos[0];
  await s.bulkUpdateVideoFields(P, [{ videoId: 'vidAAAAAAAA', fields: { videoPublishedAt: cur.videoPublishedAt, addedToPlaylistAt: cur.addedToPlaylistAt, playlistIndex: 2 } as any }]);
  const after = (await s.readIndex(P)).videos[0];
  expect(after.videoPublishedAt).toBe('2020-01-01T00:00:00Z');   // unchanged
  expect(after.addedToPlaylistAt).toBe('2020-02-01T00:00:00Z');  // unchanged
  expect(after.playlistIndex).toBe(2);                            // mutable field updated
});

test('artifacts deep-merge preserves sibling kinds (F6)', async () => {
  const s = await storeForNewUser();
  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
  await s.claimVideoSlot(P, 'vidAAAAAAAA');
  await s.upsertVideo(P, { id: 'vidAAAAAAAA', youtubeUrl: 'https://youtu.be/vidAAAAAAAA', serialNumber: 1 } as any);
  await s.updateVideoFields(P, 'vidAAAAAAAA', { artifacts: { summaryMd: { key: 'a.md', status: 'promoted' } } } as any);
  await s.updateVideoFields(P, 'vidAAAAAAAA', { artifacts: { html: { key: 'a.html', status: 'promoted' } } } as any);
  const v = (await s.readIndex(P)).videos[0] as any;
  expect(v.artifacts.summaryMd).toEqual({ key: 'a.md', status: 'promoted' });  // NOT clobbered
  expect(v.artifacts.html).toEqual({ key: 'a.html', status: 'promoted' });
});

test('reconcilePlaylistMembership is atomic archive/restore', async () => { /* per §8 case 6 */ });

test('RLS isolation: user B cannot read or write user A rows', async () => {
  const a = await storeForNewUser();
  await a.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
  await a.claimVideoSlot(P, 'vidAAAAAAAA');
  const b = await storeForNewUser();
  await expect(b.readIndex(P)).resolves.toEqual({ playlistUrl: '', outputFolder: 'listX', videos: [] }); // B sees nothing
});
```

- [ ] **Step 2: Run** `npm run test:integration -- metadata-store` → iterate to GREEN (requires stack).
- [ ] **Step 3: Commit**

```bash
git add tests/integration/metadata-store.test.ts
git commit -m "test(integration): SupabaseMetadataStore CRUD + transactional + RLS isolation"
```

---

### Task 12: Integration — `SupabaseBlobStore` + Storage RLS + consistency

**Files:**
- Create: `tests/integration/blob-store.test.ts`

- [ ] **Step 1: Write the tests**

```ts
// tests/integration/blob-store.test.ts
import { newUser, signInAs } from './helpers/clients';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { writeArtifact, resolveMissing } from '@/lib/storage/supabase/consistency';

async function blobForNewUser() {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  return { blob: new SupabaseBlobStore(client, 'artifacts'), client, userId };
}

test('put/get round-trip; get absent → null', async () => {
  const { blob, userId } = await blobForNewUser();
  const p = { id: userId, indexKey: 'listX' };
  await blob.put(p, 'a/b.md', Buffer.from('hi'), 'text/markdown');
  expect((await blob.get(p, 'a/b.md'))?.toString()).toBe('hi');
  expect(await blob.get(p, 'nope.md')).toBeNull();
});

test('Storage RLS: user B cannot read/write/delete A prefix', async () => {
  const { blob: a, userId: aId } = await blobForNewUser();
  await a.put({ id: aId, indexKey: 'listX' }, 'secret.md', Buffer.from('s'), 'text/markdown');
  const { blob: b } = await blobForNewUser();
  expect(await b.get({ id: aId, indexKey: 'listX' }, 'secret.md')).toBeNull();          // read denied → null
  await expect(b.put({ id: aId, indexKey: 'listX' }, 'x.md', Buffer.from('x'), 'text/markdown')).rejects.toBeTruthy(); // write denied
});

test('Storage RLS list isolation (F5): user B listing the bucket sees none of A prefix', async () => {
  const { blob: a, userId: aId } = await blobForNewUser();
  await a.put({ id: aId, indexKey: 'listX' }, 'a/b.md', Buffer.from('s'), 'text/markdown');
  const { client: bClient } = await blobForNewUser();
  // list A's prefix via B's client → RLS filters to zero rows
  const listed = await bClient.storage.from('artifacts').list(`${aId}/listX`);
  expect(listed.data ?? []).toHaveLength(0);
});

test('promote is idempotent across a simulated copy-succeeded/delete-failed retry', async () => { /* call promote twice */ });

test('resolveMissing: source kind → repair_needed (no regenerate); cache kind → regenerate', async () => {
  let regen = 0;
  expect(await resolveMissing({ kind: 'summaryMd', regenerate: async () => { regen++; }, markRepair: async () => {} })).toBe('repair_needed');
  expect(regen).toBe(0);
  expect(await resolveMissing({ kind: 'html', regenerate: async () => { regen++; }, markRepair: async () => {} })).toBe('regenerated');
  expect(regen).toBe(1);
});
```

- [ ] **Step 2: Run** `npm run test:integration -- blob-store` → GREEN.
- [ ] **Step 3: Commit**

```bash
git add tests/integration/blob-store.test.ts
git commit -m "test(integration): SupabaseBlobStore + storage RLS + consistency"
```

---

### Task 13: Integration — concurrency (`claimVideoSlot` under load)

**Files:**
- Create: `tests/integration/concurrency.test.ts`

- [ ] **Step 1: Write the test**

```ts
// tests/integration/concurrency.test.ts
import { newUser, signInAs } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';

test('concurrent claimVideoSlot on one playlist yields distinct positions + serials', async () => {
  const u = await newUser(); const { client } = await signInAs(u.email, u.password);
  const s = new SupabaseMetadataStore(client);
  const P = { id: '', indexKey: 'listConc' };
  await s.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listConc' });
  const ids = Array.from({ length: 10 }, (_, i) => `vid${String(i).padStart(8, '0')}`);
  const slots = await Promise.all(ids.map((id) => s.claimVideoSlot(P, id)));
  const positions = slots.map((x) => x.position).sort((a, b) => a - b);
  const serials = slots.map((x) => x.serialNumber).sort((a, b) => a - b);
  expect(new Set(positions).size).toBe(10);   // no dup positions
  expect(new Set(serials).size).toBe(10);     // no dup serials
});
```

- [ ] **Step 2: Run** `npm run test:integration -- concurrency` → GREEN (row-lock serializes). If it flakes, the `FOR UPDATE` lock in `claim_video_slot` is missing/ineffective — fix the RPC, not the test.
- [ ] **Step 3: Full gates before wrap-up**

Run: `npx tsc --noEmit && npm test && npm run check:confinement && npm run test:integration`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/concurrency.test.ts
git commit -m "test(integration): concurrent claimVideoSlot allocates distinct slots"
```

---

## Self-Review (against the spec)

**Spec coverage:**
- §2 module layout → Tasks 1-10 create every listed file (`empty-index.ts` T2, `blob-store.ts`/`local-blob-store.ts` T5, `resolve.ts` T7, `supabase/*` T9-10, `0007` T8). ✓
- §3 async+transactional interface → T3 (interface+local), T4 (consumers), T9 (cloud). ✓
- §3.3 empty-read parity + schema relax → T2. ✓
- §3.4/§3.5 position vs playlistIndex, consumer conversion → T4. ✓
- §4 BlobStore + keys + extraction → T5, T6, T9/T10 keys. ✓
- §4.2 Storage RLS (F9) → T8. ✓
- §5 consistency (ordered write, idempotent promote, class-aware read) → T10 (`consistency.ts`), T12 (tests). ✓
- §6 getStorageBundle + getPrincipalFromSession + fail-fast → T7. ✓
- §7 testing (delayed-async fake F1, integration, concurrency, consistency) → T4, T11, T12, T13. ✓
- §8 edge cases → covered across T3/T11/T12 test lists (empty read, append, merge, reconcile, isolation, promote idempotency, repair_needed, fail-fast, guard). ✓
- §1.1 decision 3 (reorderVideos dropped) → interface in T3 omits it. ✓

**Placeholder scan:** unit-test bodies marked `/* ... */` in T9/T10/T11/T12 are *additional* cases beyond the fully-written examples — each has an exact spec §8 reference and a written sibling showing the pattern. The load-bearing code (interfaces, migration SQL, RPCs, helper, resolve, both impls' primary methods) is complete. Executors must fill the referenced cases before marking a task done.

**Type consistency:** `claimVideoSlot` returns `{ position, serialNumber }` everywhere (RPC returns `serial_number` → mapped in T9). `Principal.indexKey` used consistently post-T1. `BlobStore` signatures identical in `blob-store.ts`, both impls, and `consistency.ts`. `getStorageBundle(ctx?)` shape matches T7 and its consumers.

**Codex plan review resolved (`docs/reviews/plan-stage-1c-supabase-adapters-codex.md`):** F4 (merge RPCs now first-class in T8), F6 (artifacts-aware deep-merge via `jsonb ||` on the sub-object, unit-tested in T10), F8 (dig slide logical key corrected to `assets/${videoId}/${assetName}` in T6), F1 (T7 stub implements all 13 methods), F2b (write-once re-sync integration test in T11), F5 (anon documented as intentional + list-isolation test in T12), F7 (`pipeline-async.test.ts` written out with a behaviors table + 3 assertions). F2a and F3 (CHECK constraint) were Low/no-fix.

**Note for executor (F6 verification):** the artifacts deep-merge runs in Postgres, so its correctness is proven at **integration** (T11), not in T10's mocked-client unit tests. T10 asserts `writeArtifact` *calls* `updateVideoFields` with `{ artifacts: { [kind]: … } }`; T11 asserts that writing one kind preserves sibling kinds in the actual row (see the added T11 test below).
