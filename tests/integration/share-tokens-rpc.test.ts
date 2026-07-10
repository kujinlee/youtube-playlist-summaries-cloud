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

  it('create_share_token denies an owned-but-unpromoted doc (B2 promoted branch) and inserts nothing', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(svc, u.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId, status: 'committed' });
    const { error } = await client.rpc('create_share_token', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash(),
    });
    expect(error).not.toBeNull(); // owned but not promoted → still denied
    const { data: rows } = await svc.from('share_tokens')
      .select('id').eq('playlist_id', playlistId).eq('video_id', videoId);
    expect(rows).toHaveLength(0); // no row inserted despite ownership
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

  it('the share_tokens CHECK constraint backstops the hash format even for service_role direct inserts', async () => {
    const u = await newUser();
    const { playlistId, videoId } = await seedDoc(u.user.id);
    for (const badHash of ['xyz', 'a'.repeat(63)]) {
      const { error } = await svc.from('share_tokens').insert({
        token_hash: badHash, owner_id: u.user.id, playlist_id: playlistId, video_id: videoId,
      });
      expect(error).not.toBeNull();
    }
  });

  it('list_share_tokens never exposes token_hash', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    await client.rpc('create_share_token', { p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });
    const { data: listed } = await client.rpc('list_share_tokens', { p_playlist_id: playlistId, p_video_id: videoId });
    expect(listed).toHaveLength(1);
    expect(Object.keys((listed as any[])[0])).not.toContain('token_hash');
  });

  it('list_share_tokens is owner-scoped — a non-owner sees an empty list for another owner\'s doc', async () => {
    const owner = await newUser(); const other = await newUser();
    const { client: ownerClient } = await signInAs(owner.email, owner.password);
    const { client: otherClient } = await signInAs(other.email, other.password);
    const { playlistId, videoId } = await seedDoc(owner.user.id);
    await ownerClient.rpc('create_share_token', { p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });
    const { data: listed, error } = await otherClient.rpc('list_share_tokens', {
      p_playlist_id: playlistId, p_video_id: videoId,
    });
    expect(error).toBeNull();
    expect(listed).toEqual([]);
  });

  it('revoke_share_token denies a non-owner on a still-live token — owner_id is the discriminator, not revoked_at', async () => {
    const owner = await newUser(); const other = await newUser();
    const { client: ownerClient } = await signInAs(owner.email, owner.password);
    const { client: otherClient } = await signInAs(other.email, other.password);
    const { playlistId, videoId } = await seedDoc(owner.user.id);
    await ownerClient.rpc('create_share_token', { p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });
    const { data: listed } = await ownerClient.rpc('list_share_tokens', { p_playlist_id: playlistId, p_video_id: videoId });
    const id = (listed as any[])[0].id;

    // Non-owner attempts to revoke a token that is still LIVE (not already revoked).
    const { data: revokedByOther, error: otherErr } = await otherClient.rpc('revoke_share_token', { p_id: id });
    expect(otherErr).toBeNull();
    expect(revokedByOther).toBe(false); // no-op

    // Prove the no-op was owner-scoping, not "already revoked" — row must still be untouched.
    const { data: rowAfterOther } = await svc.from('share_tokens').select('revoked_at').eq('id', id).single();
    expect((rowAfterOther as any).revoked_at).toBeNull();

    // The real owner can revoke the same still-live token.
    const { data: revokedByOwner, error: ownerErr } = await ownerClient.rpc('revoke_share_token', { p_id: id });
    expect(ownerErr).toBeNull();
    expect(revokedByOwner).toBe(true);

    const { data: rowAfterOwner } = await svc.from('share_tokens').select('revoked_at').eq('id', id).single();
    expect((rowAfterOwner as any).revoked_at).not.toBeNull();
  });

  it('revoke_share_token is idempotent — a second revoke on an already-revoked id returns false', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    await client.rpc('create_share_token', { p_playlist_id: playlistId, p_video_id: videoId,
      p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });
    const { data: listed } = await client.rpc('list_share_tokens', { p_playlist_id: playlistId, p_video_id: videoId });
    const id = (listed as any[])[0].id;
    const { data: first } = await client.rpc('revoke_share_token', { p_id: id });
    expect(first).toBe(true);
    const { data: second, error } = await client.rpc('revoke_share_token', { p_id: id });
    expect(error).toBeNull();
    expect(second).toBe(false);
  });

  it('revoke_all_share_tokens revokes every live token for the doc and returns the count', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    for (let i = 0; i < 3; i++) await client.rpc('create_share_token', { p_playlist_id: playlistId,
      p_video_id: videoId, p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });
    const { data: count } = await client.rpc('revoke_all_share_tokens', { p_playlist_id: playlistId, p_video_id: videoId });
    expect(count).toBe(3);
  });

  it('revoke_all_share_tokens is a no-op cross-owner — owner B cannot revoke owner A\'s tokens', async () => {
    const ownerA = await newUser(); const ownerB = await newUser();
    const { client: clientA } = await signInAs(ownerA.email, ownerA.password);
    const { client: clientB } = await signInAs(ownerB.email, ownerB.password);
    const { playlistId, videoId } = await seedDoc(ownerA.user.id);
    for (let i = 0; i < 2; i++) await clientA.rpc('create_share_token', { p_playlist_id: playlistId,
      p_video_id: videoId, p_expiry: new Date(Date.now() + 864e5).toISOString(), p_token_hash: hexHash() });

    const { data: count, error } = await clientB.rpc('revoke_all_share_tokens', {
      p_playlist_id: playlistId, p_video_id: videoId,
    });
    expect(error).toBeNull();
    expect(count).toBe(0);

    const { data: rows } = await svc.from('share_tokens')
      .select('revoked_at').eq('playlist_id', playlistId).eq('video_id', videoId);
    expect(rows).toHaveLength(2);
    for (const r of rows as any[]) expect(r.revoked_at).toBeNull();
  });

  it('revoke_all_share_tokens on a doc with no live tokens returns 0', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const { data: count, error } = await client.rpc('revoke_all_share_tokens', {
      p_playlist_id: playlistId, p_video_id: videoId,
    });
    expect(error).toBeNull();
    expect(count).toBe(0);
  });

  it('direct INSERT on share_tokens is denied for an authenticated session (B23)', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const { error } = await client.from('share_tokens').insert({
      token_hash: hexHash(), owner_id: u.user.id, playlist_id: playlistId, video_id: videoId,
    });
    expect(error).not.toBeNull();
  });

  it('direct SELECT/UPDATE/DELETE on share_tokens are all denied for an authenticated session (B23, full DML surface)', async () => {
    const u = await newUser(); const { client } = await signInAs(u.email, u.password);
    const { playlistId, videoId } = await seedDoc(u.user.id);
    const originalHash = hexHash();
    const { data: inserted, error: insertErr } = await svc.from('share_tokens').insert({
      token_hash: originalHash, owner_id: u.user.id, playlist_id: playlistId, video_id: videoId,
    }).select('id').single();
    expect(insertErr).toBeNull();
    const id = (inserted as any).id;

    const { data: selData, error: selErr } = await client.from('share_tokens').select('*').eq('id', id);
    if (selErr) expect(selErr).not.toBeNull();
    else expect(selData).toHaveLength(0);

    const { error: updErr, count: updCount } = await client.from('share_tokens')
      .update({ revoked_at: new Date().toISOString() }).eq('id', id);
    if (updErr) expect(updErr).not.toBeNull();
    else expect(updCount ?? 0).toBe(0);

    const { error: delErr, count: delCount } = await client.from('share_tokens').delete().eq('id', id);
    if (delErr) expect(delErr).not.toBeNull();
    else expect(delCount ?? 0).toBe(0);

    // Service-role verification: the row is untouched — still live, hash intact.
    const { data: row } = await svc.from('share_tokens').select('*').eq('id', id).single();
    expect(row).not.toBeNull();
    expect((row as any).token_hash).toBe(originalHash);
    expect((row as any).revoked_at).toBeNull();
  });
});
