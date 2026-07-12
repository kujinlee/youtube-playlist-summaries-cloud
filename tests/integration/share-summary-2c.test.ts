// tests/integration/share-summary-2c.test.ts
//
// Stage 2c Task 8 — real-Supabase integration guard proving:
//   1. share create + revoke round-trip for the owner (idempotent second revoke)
//   2. owner isolation (a non-owner's revoke is a silent no-op, no error leak)
//   3. SupabaseMetadataStore.readIndex's `summaryReady` DTO reflection under real RLS
//      (promoted → true; committed/artifacts-absent → false)
//
// Run: npx supabase db reset && npm run test:integration -- share-summary-2c --runInBand

import { createHash, randomBytes } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import type { Principal } from '@/lib/storage/principal';

const svc = adminClient();
// token_hash is stored as lowercase hex TEXT (not bytea).
const hexHash = () => createHash('sha256').update(randomBytes(32)).digest('hex');

async function seedDoc(ownerId: string, status?: 'promoted' | 'committed') {
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId } = await seedPromotedVideo(svc, { ownerId, playlistId, status });
  return { playlistId, playlistKey, videoId };
}

describe('share-summary-2c integration', () => {
  test('share create + revoke round-trip (owner A): idempotent second revoke', async () => {
    const u = await newUser();
    const { client: userAClient } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);

    const { data, error } = await userAClient.rpc('create_share_token', {
      p_playlist_id: playlistId,
      p_video_id: videoId,
      p_expiry: null, // 'never'
      p_token_hash: hexHash(),
    });
    expect(error).toBeNull();
    // Task 1 contract: create_share_token returns BOTH id and expires_at — assert the full row
    // shape so a regression that drops expires_at (returning only {id}) fails this test.
    expect(data?.[0]).toMatchObject({ id: expect.any(String), expires_at: null });
    const shareId = data![0].id as string;
    expect(shareId).toMatch(/^[0-9a-f-]{36}$/i);

    const { data: revoked, error: revokeErr } = await userAClient.rpc('revoke_share_token', {
      p_id: shareId,
    });
    expect(revokeErr).toBeNull();
    expect(revoked).toBe(true);

    // second revoke of the same id — already revoked → false, no error
    const { data: revokedAgain, error: revokeAgainErr } = await userAClient.rpc(
      'revoke_share_token',
      { p_id: shareId },
    );
    expect(revokeAgainErr).toBeNull();
    expect(revokedAgain).toBe(false);
  });

  test('owner isolation: user B cannot revoke user A\'s share (silent no-op, no error leak)', async () => {
    const ownerA = await newUser();
    const userB = await newUser();
    const { client: clientA } = await signInAs(ownerA.email, ownerA.password);
    const { client: clientB } = await signInAs(userB.email, userB.password);
    const { playlistId, videoId } = await seedDoc(ownerA.user.id);

    const { data, error } = await clientA.rpc('create_share_token', {
      p_playlist_id: playlistId,
      p_video_id: videoId,
      p_expiry: null,
      p_token_hash: hexHash(),
    });
    expect(error).toBeNull();
    const shareId = data![0].id as string;

    const { data: revokedByB, error: bErr } = await clientB.rpc('revoke_share_token', {
      p_id: shareId,
    });
    expect(bErr).toBeNull();
    expect(revokedByB).toBe(false);

    // A's share is untouched by B's no-op — A can still revoke it for real.
    const { data: revokedByA, error: aErr } = await clientA.rpc('revoke_share_token', {
      p_id: shareId,
    });
    expect(aErr).toBeNull();
    expect(revokedByA).toBe(true);
  });

  test('summaryReady reflection via SupabaseMetadataStore.readIndex under real RLS', async () => {
    const u = await newUser();
    const { client } = await signInAs(u.email, u.password);
    const { playlistId, playlistKey, videoId: promotedId } = await seedDoc(u.user.id, 'promoted');

    const store = new SupabaseMetadataStore(client);
    const p: Principal = { id: '', indexKey: playlistKey };

    // seed a second, committed video onto the SAME playlist for direct comparison.
    const { videoId: committedId } = await seedPromotedVideo(svc, {
      ownerId: u.user.id,
      playlistId,
      status: 'committed',
      videoId: 'v-committed-2c',
      position: 2,
    });

    const idx = await store.readIndex(p);
    const promotedVideo = idx.videos.find((v) => v.id === promotedId);
    const committedVideo = idx.videos.find((v) => v.id === committedId);

    expect(promotedVideo?.summaryReady).toBe(true);
    expect(committedVideo?.summaryReady).toBe(false);
  });
});
