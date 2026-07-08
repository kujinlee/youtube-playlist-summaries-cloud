// tests/integration/worker-storage-bundle.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { readVideo, reserveVideoSlot, persistSummary } from '@/lib/storage/worker-persistence';
jest.setTimeout(20_000);

async function seedPlaylist(client: any, ownerId: string, playlistKey?: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: playlistKey ?? `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

test('getWorkerStorageBundle resolves the principal for the owning user', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const admin = adminClient();
  const playlistKey = `k-${randomUUID()}`;
  const pl = await seedPlaylist(client, userId, playlistKey);

  const bundle = await getWorkerStorageBundle(admin, userId, pl);

  expect(bundle.ownerId).toBe(userId);
  expect(bundle.playlistId).toBe(pl);
  expect(bundle.principal.id).toBe(userId);
  expect(bundle.principal.indexKey).toBe(playlistKey);
  expect(bundle.blobStore).toBeTruthy();
});

test('getWorkerStorageBundle rejects when ownerId does not own playlistId', async () => {
  const owner = await newUser();
  const { client: ownerClient, userId: ownerId } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(ownerClient, ownerId);

  const attacker = await newUser();
  const { userId: attackerId } = await signInAs(attacker.email, attacker.password);

  const admin = adminClient();
  await expect(getWorkerStorageBundle(admin, attackerId, victimPl)).rejects.toThrow();
});

test('two owners sharing one playlist_key each resolve their own row by playlistId (B1 regression)', async () => {
  const sharedKey = `shared-${randomUUID()}`;
  const admin = adminClient();

  const u1 = await newUser();
  const { client: c1, userId: owner1 } = await signInAs(u1.email, u1.password);
  const pl1 = await seedPlaylist(c1, owner1, sharedKey);

  const u2 = await newUser();
  const { client: c2, userId: owner2 } = await signInAs(u2.email, u2.password);
  const pl2 = await seedPlaylist(c2, owner2, sharedKey);

  const bundle1 = await getWorkerStorageBundle(admin, owner1, pl1);
  const bundle2 = await getWorkerStorageBundle(admin, owner2, pl2);

  expect(bundle1.ownerId).toBe(owner1);
  expect(bundle1.playlistId).toBe(pl1);
  expect(bundle1.principal.id).toBe(owner1);
  expect(bundle1.principal.indexKey).toBe(sharedKey);

  expect(bundle2.ownerId).toBe(owner2);
  expect(bundle2.playlistId).toBe(pl2);
  expect(bundle2.principal.id).toBe(owner2);
  expect(bundle2.principal.indexKey).toBe(sharedKey);

  // Cross-check: resolving owner1 against playlist2's id must fail (not owned by owner1).
  await expect(getWorkerStorageBundle(admin, owner1, pl2)).rejects.toThrow();
});

test('readVideo returns the persisted row by (playlistId, videoId) and is owner-safe under a shared playlist_key', async () => {
  const sharedKey = `shared-${randomUUID()}`;
  const admin = adminClient();

  const u1 = await newUser();
  const { client: c1, userId: owner1 } = await signInAs(u1.email, u1.password);
  const pl1 = await seedPlaylist(c1, owner1, sharedKey);

  const u2 = await newUser();
  const { client: c2, userId: owner2 } = await signInAs(u2.email, u2.password);
  const pl2 = await seedPlaylist(c2, owner2, sharedKey);

  const vid = randomUUID();
  await reserveVideoSlot(admin, owner1, pl1, vid);
  await persistSummary(admin, owner1, pl1, vid, { id: vid, title: 'Shared-key video' }, 'committed');

  const found = await readVideo(admin, pl1, vid);
  expect(found).not.toBeNull();
  expect(found!.id).toBe(vid);
  expect(found!.title).toBe('Shared-key video');

  // Same video_id text does not exist under the other owner's playlist row.
  const notFound = await readVideo(admin, pl2, vid);
  expect(notFound).toBeNull();
});

test('readVideo returns null when no row exists for (playlistId, videoId)', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId);
  const admin = adminClient();

  const result = await readVideo(admin, pl, randomUUID());
  expect(result).toBeNull();
});
