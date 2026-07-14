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
  const { error } = await svc.from('share_tokens').insert({ token_hash: tokenHash, owner_id: ownerId,
    playlist_id: playlistId, video_id: videoId, expires_at: new Date(Date.now() + 864e5).toISOString(), ...over });
  if (error) throw error; // surface FK/constraint violations instead of silently minting nothing
  return token;
}

describe('getShareServeContext', () => {
  it('resolves a live token to the doc coordinates', async () => {
    const u = await newUser(); const { playlistId, playlistKey, videoId, base } = await seedDoc(u.user.id);
    const token = await mintDirect(u.user.id, playlistId, videoId);
    const ctx = await getShareServeContext(svc, token);
    expect(ctx).toMatchObject({ ownerId: u.user.id, playlistKey, playlistId, videoId, mdKey: `${base}.md` });
  });
  // Point at a REAL, owner-matching, PROMOTED doc (0019's composite FK rejects a fake/mismatched
  // playlist_id+owner_id pair on insert — see share-tokens-cascade.test.ts behavior 3) so a
  // 'denied' result can only come from the token liveness pre-check (revoked_at/expires_at): if
  // that pre-check didn't short-circuit BEFORE the playlist/video read, this doc would resolve
  // fine (it genuinely exists and is promoted), so the test would fail instead of accidentally
  // passing via a "not found" fallthrough.
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
  // 0019's composite (playlist_id, owner_id) FK now makes the OLD version of this test
  // impossible to construct honestly: a row with owner_id=A, playlist_id=B's-playlist is
  // rejected AT INSERT (proven separately in share-tokens-cascade.test.ts behavior 3 — "a
  // share_token owner_id must match its playlist owner_id"). That closes the playlist-level
  // confused-deputy path at the DB layer. share_tokens.video_id has NO FK, though, so the
  // residual attack surface is at the video level — the two tests below exercise the D15 guard
  // (lib/share/serve.ts's `.eq('playlist_id', …).eq('owner_id', …)` scoping on both the
  // playlist AND video lookups) against fixtures that insert cleanly under the FK.
  it("resolves owner A's token to A's own doc — not owner B's — even when both playlists use the identical video_id (D15)", async () => {
    const a = await newUser(); const b = await newUser();
    const collideId = `v-${randomUUID()}`; // same YouTube video_id can legitimately appear in two owners' playlists
    const { playlistId: aPlaylistId, playlistKey: aPlaylistKey } = await seedPlaylist(svc, a.user.id);
    await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId: aPlaylistId, videoId: collideId, title: "Owner A's Doc" });
    const { playlistId: bPlaylistId } = await seedPlaylist(svc, b.user.id);
    await seedPromotedVideo(svc, { ownerId: b.user.id, playlistId: bPlaylistId, videoId: collideId, title: "Owner B's Doc" });

    const token = await mintDirect(a.user.id, aPlaylistId, collideId); // valid insert: a owns aPlaylistId (satisfies 0019 FK)
    const ctx = await getShareServeContext(svc, token);
    expect(ctx).toMatchObject({ ownerId: a.user.id, playlistKey: aPlaylistKey, title: "Owner A's Doc" });
  });
  it("denies a token whose video_id belongs to a different owner's playlist (video_id has no FK; D15 scoping must still isolate it)", async () => {
    const a = await newUser(); const b = await newUser();
    const { playlistId: aPlaylistId } = await seedPlaylist(svc, a.user.id); // A's own playlist — valid FK target
    const { playlistId: bPlaylistId } = await seedPlaylist(svc, b.user.id);
    const { videoId: bVideoId } = await seedPromotedVideo(svc, { ownerId: b.user.id, playlistId: bPlaylistId }); // B's doc

    // Valid insert (a owns aPlaylistId, satisfying the 0019 FK) but video_id is copied from B's doc,
    // which does not exist under A's playlist — the D15 video lookup must not fall through to B's row.
    const token = await mintDirect(a.user.id, aPlaylistId, bVideoId);
    expect(await getShareServeContext(svc, token)).toEqual({ status: 'denied' });
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
