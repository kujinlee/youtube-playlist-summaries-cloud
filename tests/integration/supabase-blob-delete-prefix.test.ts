// tests/integration/supabase-blob-delete-prefix.test.ts
//
// Integration coverage for SupabaseBlobStore.deletePrefix against a live local
// Supabase stack, through a SESSION-SCOPED store (not the service client) — this
// proves the RLS `.list`/`.remove` path under the `artifacts_owner_rw` storage
// policy, the same path the delete route (Task 9) will exercise.
// Run via: npm run test:integration -- supabase-blob-delete-prefix
// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).

import { newUser, signInAs } from './helpers/clients';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import type { Principal } from '@/lib/storage/principal';

jest.setTimeout(20_000);

/** Spin up a new isolated user + a session-scoped BlobStore (RLS-bound JWT client). */
async function blobForNewUser() {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  return { blob: new SupabaseBlobStore(client, 'artifacts'), client, userId };
}

test('deletePrefix(p, "") removes flat + nested objects; subsequent list is empty', async () => {
  const { blob, client, userId } = await blobForNewUser();
  const p: Principal = { id: userId, indexKey: 'listX' };

  // Flat objects.
  await blob.put(p, 'base.md', Buffer.from('# summary'), 'text/markdown');
  await blob.put(p, 'base.pdf', Buffer.from('%PDF-1.4'), 'application/pdf');
  // Nested DIG object: dig/<base>/<sectionId>.rV.md.
  await blob.put(p, 'dig/base/0.r1.md', Buffer.from('# section'), 'text/markdown');

  // Sanity: objects are readable before delete.
  expect(await blob.get(p, 'base.md')).not.toBeNull();
  expect(await blob.get(p, 'dig/base/0.r1.md')).not.toBeNull();

  await blob.deletePrefix(p, '');

  // All three gone via the BlobStore API.
  expect(await blob.get(p, 'base.md')).toBeNull();
  expect(await blob.get(p, 'base.pdf')).toBeNull();
  expect(await blob.get(p, 'dig/base/0.r1.md')).toBeNull();

  // A subsequent raw `.list` on the playlist root (same session-scoped client, proving
  // the RLS list path) returns nothing — no orphaned objects, including in the nested
  // dig/ subfolder.
  const { data: rootList, error: rootErr } = await client.storage
    .from('artifacts')
    .list(`${userId}/listX`);
  expect(rootErr).toBeNull();
  expect(rootList ?? []).toHaveLength(0);
});

test('deletePrefix on an already-empty prefix resolves without throw (idempotent)', async () => {
  const { blob, userId } = await blobForNewUser();
  const p: Principal = { id: userId, indexKey: 'listX' };

  await expect(blob.deletePrefix(p, '')).resolves.toBeUndefined();
});

test('deletePrefix does not touch another owner\'s objects under the same indexKey', async () => {
  const { blob: a, userId: aId } = await blobForNewUser();
  const { blob: b, userId: bId } = await blobForNewUser();
  const aP: Principal = { id: aId, indexKey: 'listX' };
  const bP: Principal = { id: bId, indexKey: 'listX' };

  await a.put(aP, 'base.md', Buffer.from('a'), 'text/markdown');
  await b.put(bP, 'base.md', Buffer.from('b'), 'text/markdown');

  await a.deletePrefix(aP, '');

  expect(await a.get(aP, 'base.md')).toBeNull();
  // B's object under the same logical indexKey/key, but a different owner prefix, survives.
  expect((await b.get(bP, 'base.md'))?.toString()).toBe('b');
});
