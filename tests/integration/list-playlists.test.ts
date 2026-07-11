// tests/integration/list-playlists.test.ts
//
// Task 3 (Stage 2a): MetadataStore.listPlaylists(ownerId) is CLOUD-ONLY — it powers a
// future sidebar (T4 route) that lists all of an owner's playlists. This test seeds TWO
// owners via the admin client, including (a) a playlist with a NULL title and (b) a
// playlist_key that COLLIDES across the two owners (playlist_key is unique per-owner,
// not globally), then asserts:
//   - owner A's listPlaylists(A.id) returns ONLY A's rows (owner B's colliding-key
//     playlist is excluded, even though the key matches).
//   - ordering is by playlist_title (nulls last), then created_at.
//   - each row carries createdAt (mapped from the created_at column).
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

async function seed(ownerId: string, playlistKey: string, playlistTitle: string | null) {
  const { data, error } = await svc.from('playlists').insert({
    owner_id: ownerId,
    playlist_key: playlistKey,
    playlist_url: `https://youtube.com/playlist?list=${playlistKey}`,
    playlist_title: playlistTitle,
  }).select('id, created_at').single();
  if (error) throw error;
  return { id: data!.id as string, createdAt: data!.created_at as string };
}

it("listPlaylists(ownerId) returns only that owner's rows, ordered by title (nulls last) then created_at, with createdAt on each row", async () => {
  const a = await newUser();
  const b = await newUser();
  const collidingKey = `PL-collide-${randomUUID()}`;

  // Owner A: four playlists — titles chosen to sort Alpha < Beta < Zeta, plus one with a
  // NULL title (must sort last), so ordering is unambiguous under any collation.
  const aAlpha = await seed(a.user.id, `PL-a-alpha-${randomUUID()}`, 'Alpha Playlist');
  const aColliding = await seed(a.user.id, collidingKey, 'Beta Playlist');
  const aZeta = await seed(a.user.id, `PL-a-zeta-${randomUUID()}`, 'Zeta Playlist');
  const aNull = await seed(a.user.id, `PL-a-null-${randomUUID()}`, null);

  // Owner B: a playlist whose playlist_key COLLIDES with A's colliding-key playlist
  // (allowed — playlist_key is unique per-owner via a composite (owner_id, playlist_key)
  // constraint, not globally), plus one unrelated playlist.
  await seed(b.user.id, collidingKey, "B's Colliding Playlist");
  await seed(b.user.id, `PL-b-other-${randomUUID()}`, 'Some Other B Playlist');

  // Query as owner A's authenticated session (not the admin/service client) — this is
  // the real call path (RLS owner_id=auth.uid() scopes it; the store's explicit
  // .eq('owner_id', ownerId) is defense-in-depth on top of that).
  const { client: aClient } = await signInAs(a.email, a.password);
  const store = new SupabaseMetadataStore(aClient);
  const result = await store.listPlaylists(a.user.id);

  // Only A's 4 rows come back, in title order (nulls last); B's colliding-key playlist —
  // despite sharing playlist_key with A's — is excluded entirely.
  expect(result.map((r) => r.id)).toEqual([aAlpha.id, aColliding.id, aZeta.id, aNull.id]);

  for (const row of result) {
    expect(typeof row.createdAt).toBe('string');
  }
  expect(result.find((r) => r.id === aNull.id)?.playlistTitle).toBeNull();
  expect(result.find((r) => r.id === aColliding.id)?.playlistKey).toBe(collidingKey);
  expect(result.find((r) => r.id === aColliding.id)?.playlistTitle).toBe('Beta Playlist'); // A's own title, not B's
  expect(result.find((r) => r.id === aColliding.id)?.createdAt).toBe(aColliding.createdAt);
});
