// tests/integration/blob-store.test.ts
//
// Integration suite for SupabaseBlobStore + storage RLS + consistency helpers
// against a live local Supabase stack.
// Run via: npm run test:integration -- blob-store
// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).

import { newUser, signInAs } from './helpers/clients';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { writeArtifact, resolveMissing } from '@/lib/storage/supabase/consistency';
import type { Principal } from '@/lib/storage/principal';

// Allow extra time for real network calls to the local stack.
jest.setTimeout(20_000);

/** Spin up a new isolated user + a BlobStore scoped to their JWT. */
async function blobForNewUser() {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  return { blob: new SupabaseBlobStore(client, 'artifacts'), client, userId };
}

/** Minimal video stub accepted by upsertVideo; uses `as any` to skip schema
 *  validation — integration tests focus on store behaviour, not type fidelity. */
function makeVideo(id: string, serialNumber: number) {
  return {
    id,
    title: `Title ${id}`,
    youtubeUrl: `https://youtu.be/${id}`,
    language: 'en' as const,
    durationSeconds: 100,
    archived: false,
    ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
    overallScore: 3,
    summaryMd: null,
    processedAt: '2024-01-01T00:00:00.000Z',
    serialNumber,
  };
}

// ---------------------------------------------------------------------------
// 1. put/get round-trip; get absent → null
// ---------------------------------------------------------------------------
test('put/get round-trip; get absent → null', async () => {
  const { blob, userId } = await blobForNewUser();
  const p: Principal = { id: userId, indexKey: 'listX' };

  await blob.put(p, 'a/b.md', Buffer.from('hi'), 'text/markdown');

  const got = await blob.get(p, 'a/b.md');
  expect(got?.toString()).toBe('hi');

  // absent key → null (get() coerces all download errors to null)
  expect(await blob.get(p, 'nope.md')).toBeNull();
});

// ---------------------------------------------------------------------------
// 2. object key layout: stored as ${userId}/${indexKey}/${key}
// ---------------------------------------------------------------------------
test('object key layout: stored path is userId/indexKey/key', async () => {
  const { blob, client, userId } = await blobForNewUser();
  const p: Principal = { id: userId, indexKey: 'listX' };

  await blob.put(p, 'a/b.md', Buffer.from('layout-check'), 'text/markdown');

  // List the prefix the user owns; RLS permits because split_part(name,'/') = auth.uid().
  const { data, error } = await client.storage
    .from('artifacts')
    .list(`${userId}/listX/a`);

  expect(error).toBeNull();
  const names = (data ?? []).map((o) => o.name);
  expect(names).toContain('b.md');
});

// ---------------------------------------------------------------------------
// 3. Storage RLS: user B cannot read or write under user A's prefix
//    Cross-user read denial manifests as null (get() coerces all errors to null).
//    Cross-user write denial manifests as a thrown error from put().
// ---------------------------------------------------------------------------
test('Storage RLS: user B cannot read/write A prefix (read → null; write → throws)', async () => {
  const { blob: a, userId: aId } = await blobForNewUser();
  const aP: Principal = { id: aId, indexKey: 'listX' };
  await a.put(aP, 'secret.md', Buffer.from('s'), 'text/markdown');

  const { blob: b } = await blobForNewUser();

  // Read denied → get() returns null (RLS error coerced to null; no data leaked).
  expect(await b.get(aP, 'secret.md')).toBeNull();

  // Write denied → put() throws.
  await expect(
    b.put(aP, 'x.md', Buffer.from('x'), 'text/markdown'),
  ).rejects.toBeTruthy();
});

// ---------------------------------------------------------------------------
// 4. Storage RLS list isolation (F5): user B listing A's prefix sees zero objects.
// ---------------------------------------------------------------------------
test('Storage RLS list isolation (F5): user B listing A prefix returns no objects', async () => {
  const { blob: a, userId: aId } = await blobForNewUser();
  const aP: Principal = { id: aId, indexKey: 'listX' };
  await a.put(aP, 'a/b.md', Buffer.from('s'), 'text/markdown');

  const { client: bClient } = await blobForNewUser();

  // B lists A's prefix — RLS policy filters to rows where split_part(name,'/',1)=auth.uid();
  // B's uid ≠ A's uid, so zero rows are returned.
  const { data } = await bClient.storage
    .from('artifacts')
    .list(`${aId}/listX`);

  expect(data ?? []).toHaveLength(0);
});

// ---------------------------------------------------------------------------
// 5. _staging prefix works under RLS: first segment still = userId → RLS permits.
// ---------------------------------------------------------------------------
test('putStaged writes under _staging/; promote makes final key readable', async () => {
  const { blob, userId } = await blobForNewUser();
  const p: Principal = { id: userId, indexKey: 'listX' };

  const ref = await blob.putStaged(p, 'a/b.md', Buffer.from('staged'), 'text/markdown');

  // Staged object exists at _staging/a/b.md; final key not yet written.
  expect(await blob.exists(p, ref.tempKey)).toBe(true);
  expect(await blob.exists(p, ref.finalKey)).toBe(false);

  await blob.promote(ref);

  // Final key now readable; staged object gone (moved, not copied).
  const got = await blob.get(p, 'a/b.md');
  expect(got?.toString()).toBe('staged');
  // After promote, temp key is gone.
  expect(await blob.exists(p, ref.tempKey)).toBe(false);
});

// ---------------------------------------------------------------------------
// 6. promote idempotency: second call when final already exists → no throw; final still readable.
// ---------------------------------------------------------------------------
test('promote idempotent: second call with final already promoted → no throw, final readable', async () => {
  const { blob, userId } = await blobForNewUser();
  const p: Principal = { id: userId, indexKey: 'listX' };

  const ref = await blob.putStaged(p, 'c/d.md', Buffer.from('idem'), 'text/markdown');

  // First promote: temp → final.
  await blob.promote(ref);
  expect(await blob.get(p, 'c/d.md')).not.toBeNull();

  // Second promote: final already exists → best-effort remove temp (no-op), no throw.
  await expect(blob.promote(ref)).resolves.toBeUndefined();

  // Final still readable after second call.
  const got = await blob.get(p, 'c/d.md');
  expect(got?.toString()).toBe('idem');
});

// ---------------------------------------------------------------------------
// 7. consistency writeArtifact ordered write end-to-end.
// ---------------------------------------------------------------------------
test('writeArtifact: blob readable at final key + metadata artifacts.summaryMd.status === promoted', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const p: Principal = { id: userId, indexKey: 'listX' };

  const meta = new SupabaseMetadataStore(client);
  const blob = new SupabaseBlobStore(client, 'artifacts');

  // Seed: playlist → slot → video row.
  await meta.setPlaylistMeta(p, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
  await meta.claimVideoSlot(p, 'vidAAAAAAAA');
  await meta.upsertVideo(p, makeVideo('vidAAAAAAAA', 1) as any);

  // writeArtifact: putStaged → verify temp → updateVideoFields(committed) → promote → updateVideoFields(promoted).
  await writeArtifact({
    meta,
    blob,
    principal: p,
    videoId: 'vidAAAAAAAA',
    kind: 'summaryMd',
    key: 'summaries/vidAAAAAAAA.md',
    bytes: Buffer.from('# Summary'),
    contentType: 'text/markdown',
  });

  // Blob must be readable at the final key.
  const got = await blob.get(p, 'summaries/vidAAAAAAAA.md');
  expect(got?.toString()).toBe('# Summary');

  // Metadata must reflect promoted status.
  const idx = await meta.readIndex(p);
  const video = idx.videos[0] as any;
  expect(video.artifacts?.summaryMd?.status).toBe('promoted');
  expect(video.artifacts?.summaryMd?.key).toBe('summaries/vidAAAAAAAA.md');
});

// ---------------------------------------------------------------------------
// 8. resolveMissing: source kind → repair_needed, no regenerate; cache kind → regenerated.
// ---------------------------------------------------------------------------
test('resolveMissing: source kind → repair_needed (regenerate not called); cache kind → regenerated', async () => {
  let regen = 0;

  // summaryMd is a SOURCE kind → must not regenerate; must markRepair.
  const sourceResult = await resolveMissing({
    kind: 'summaryMd',
    regenerate: async () => { regen++; },
    markRepair: async () => {},
  });
  expect(sourceResult).toBe('repair_needed');
  expect(regen).toBe(0);

  // html is a CACHE kind → must call regenerate.
  const cacheResult = await resolveMissing({
    kind: 'html',
    regenerate: async () => { regen++; },
    markRepair: async () => {},
  });
  expect(cacheResult).toBe('regenerated');
  expect(regen).toBe(1);
});

// ---------------------------------------------------------------------------
// 9. arrayBuffer real-runtime: round-trip test (test 1) already exercises this.
//    Documented here: get() calls data.arrayBuffer() from the real supabase-js
//    download response; the round-trip test above confirms the bytes are decoded
//    correctly (Buffer.from('hi') → toString() === 'hi').
// ---------------------------------------------------------------------------
