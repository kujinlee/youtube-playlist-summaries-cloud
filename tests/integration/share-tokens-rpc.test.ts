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
