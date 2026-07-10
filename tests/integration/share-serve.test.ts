import { randomUUID } from 'crypto';
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
  // Point at NON-EXISTENT playlist/video coordinates (no seedDoc) so a 'denied' result can only
  // come from the token liveness pre-check (revoked_at/expires_at), proving it short-circuits
  // BEFORE any playlist/video read — not from a later "not found" fallthrough.
  it('denies an expired token before resolving', async () => {
    const u = await newUser();
    const token = await mintDirect(u.user.id, randomUUID(), randomUUID(), { expires_at: new Date(Date.now() - 864e5).toISOString() });
    expect(await getShareServeContext(svc, token)).toEqual({ status: 'denied' });
  });
  it('denies a revoked token', async () => {
    const u = await newUser();
    const token = await mintDirect(u.user.id, randomUUID(), randomUUID(), { revoked_at: new Date().toISOString() });
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
  it("denies owner A's token pointing at owner B's doc (confused-deputy, D15)", async () => {
    const a = await newUser(); const b = await newUser();
    const { playlistId, videoId } = await seedDoc(b.user.id);       // B's promoted doc
    const token = await mintDirect(a.user.id, playlistId, videoId); // A owns the token, B owns the coords
    const ctx = await getShareServeContext(svc, token);
    expect(ctx).toEqual({ status: 'denied' });                      // must deny, and leak no B coords
  });
  it('returns the doc title from the video row (for download filenames)', async () => {
    const u = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, u.user.id);
    // seedPromotedVideo writes data.title? — set it explicitly so the assertion is meaningful:
    const videoId = 'v-titletest';
    await svc.from('videos').insert({
      playlist_id: playlistId, owner_id: u.user.id, video_id: videoId, position: 5,
      data: { id: videoId, title: 'My Doc Title', language: 'en', summaryMd: 'v-titletest.md',
              docVersion: 1, artifacts: { summaryMd: { key: 'v-titletest.md', status: 'promoted' } } },
    });
    const { token, tokenHash } = generateShareToken();
    await svc.from('share_tokens').insert({ token_hash: tokenHash, owner_id: u.user.id,
      playlist_id: playlistId, video_id: videoId, expires_at: new Date(Date.now() + 864e5).toISOString() });
    const ctx = await getShareServeContext(svc, token);
    expect(ctx).toMatchObject({ ownerId: u.user.id, playlistKey, mdKey: 'v-titletest.md', title: 'My Doc Title' });
  });
});
