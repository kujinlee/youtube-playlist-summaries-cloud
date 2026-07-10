import { adminClient, newUser, signInAs, anonSession } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { resolveOwnedPlaylistKey } from '@/lib/storage/serve-playlist';
import { getStorageBundle } from '@/lib/storage/resolve';

const svc = adminClient();
const MD = `# T\n**Channel:** C | **Duration:** 1:00\n\n## 1. Intro\nbody\n`;

// getStorageBundle({ supabaseClient }) selects the Supabase stores only when STORAGE_BACKEND==='supabase'
// (else it returns the local FS bundle). The route runs under the supabase backend, so pin it here too.
const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

/** Seed an owner + one promoted doc (DB row via helper + the MD blob at {owner}/{key}/{base}.md). */
async function seedOwnerDoc(ownerId: string) {
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId, base } = await seedPromotedVideo(svc, { ownerId, playlistId });
  await seedSummaryBlob(svc, ownerId, playlistKey, base, MD);
  return { playlistId, playlistKey, videoId };
}

it('B8/B9: an owner (registered OR anon) passes BOTH RLS gates for the 200 path (owner-assert + video visible)', async () => {
  // HONEST SCOPE (F7): this test drives the two REAL RLS enforcement points the 200 path depends on —
  // resolveOwnedPlaylistKey (owner-assert) and readIndex (video-row RLS). It does NOT call GET, so it
  // does not itself assert HTTP 200; the 200/404 STATUS MAPPING is proven by the mocked route test
  // (Task 7 Step 1, `res.status === 200`). The two layers together cover B9 without either overclaiming.
  // registered
  const a = await newUser();
  const aDoc = await seedOwnerDoc(a.user.id);
  const { client: aClient } = await signInAs(a.email, a.password);
  expect(await resolveOwnedPlaylistKey(aClient, aDoc.playlistId, a.user.id)).toBe(aDoc.playlistKey);
  const aIndex = await getStorageBundle({ supabaseClient: aClient })
    .metadataStore.readIndex({ id: a.user.id, indexKey: aDoc.playlistKey });
  expect(aIndex.videos.find((v) => v.id === aDoc.videoId)).toBeTruthy(); // own video visible → both RLS gates pass

  // anon owner — identical path (auth.uid() is the anon uid)
  const { client: anonClient, userId: anonId } = await anonSession();
  const anonDoc = await seedOwnerDoc(anonId);
  expect(await resolveOwnedPlaylistKey(anonClient, anonDoc.playlistId, anonId)).toBe(anonDoc.playlistKey);
  const anonIndex = await getStorageBundle({ supabaseClient: anonClient })
    .metadataStore.readIndex({ id: anonId, indexKey: anonDoc.playlistKey });
  expect(anonIndex.videos.find((v) => v.id === anonDoc.videoId)).toBeTruthy();
});

it('B10: a foreign owner is blocked BOTH directions (playlist-assert null + RLS-invisible video → 404)', async () => {
  const a = await newUser();
  const b = await newUser();
  const aDoc = await seedOwnerDoc(a.user.id);
  const bDoc = await seedOwnerDoc(b.user.id);
  const { client: aClient } = await signInAs(a.email, a.password);
  const { client: bClient } = await signInAs(b.email, b.password);

  // (1) B on A's playlistId → owner-assert returns null → route 404.
  expect(await resolveOwnedPlaylistKey(bClient, aDoc.playlistId, b.user.id)).toBeNull();
  // (2) Even handed A's playlist_key directly, B's session sees NO video (RLS row-invisible) → route 404.
  const bSeesA = await getStorageBundle({ supabaseClient: bClient })
    .metadataStore.readIndex({ id: b.user.id, indexKey: aDoc.playlistKey });
  expect(bSeesA.videos.find((v) => v.id === aDoc.videoId)).toBeUndefined();
  // (3) Symmetric: A cannot see B's doc.
  expect(await resolveOwnedPlaylistKey(aClient, bDoc.playlistId, a.user.id)).toBeNull();
  const aSeesB = await getStorageBundle({ supabaseClient: aClient })
    .metadataStore.readIndex({ id: a.user.id, indexKey: bDoc.playlistKey });
  expect(aSeesB.videos.find((v) => v.id === bDoc.videoId)).toBeUndefined();
});
