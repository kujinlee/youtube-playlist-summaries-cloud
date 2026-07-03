import { newUser, signInAs, anonSession } from './helpers/clients';

async function ownedPlaylist(email: string, password: string, key: string) {
  const { client, userId } = await signInAs(email, password);
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: userId, playlist_key: key, playlist_url: `https://youtube.com/playlist?list=${key}` })
    .select('id').single();
  // Codex I1: assert the seed insert succeeded, so downstream CHECK/isolation assertions
  // prove the constraint — not a silently-failed seed (and give a clear message on failure).
  if (error || !data) throw new Error(`ownedPlaylist seed insert failed: ${error?.message}`);
  return { client, userId, playlistId: data.id };
}

describe('integrity + reordering', () => {
  it('rejects a video whose data.id != video_id', async () => {
    const u = await newUser();
    const { client, userId, playlistId } = await ownedPlaylist(u.email, u.password, 'PLint1');
    const { error } = await client.from('videos')
      .insert({ playlist_id: playlistId, owner_id: userId, video_id: 'v0', position: 0, data: { id: 'MISMATCH' } });
    expect(error).not.toBeNull();
  });

  it('rejects a video whose data has no id', async () => {
    const u = await newUser();
    const { client, userId, playlistId } = await ownedPlaylist(u.email, u.password, 'PLint2');
    const { error } = await client.from('videos')
      .insert({ playlist_id: playlistId, owner_id: userId, video_id: 'v0', position: 0, data: { title: 'x' } });
    expect(error).not.toBeNull();
  });

  it('allows a full reorder within one transaction (deferrable position constraint)', async () => {
    const u = await newUser();
    const { client, userId, playlistId } = await ownedPlaylist(u.email, u.password, 'PLreorder');
    const mk = (id: string, pos: number) =>
      ({ playlist_id: playlistId, owner_id: userId, video_id: id, position: pos, data: { id } });
    await client.from('videos').insert([mk('A', 0), mk('B', 1), mk('C', 2)]);

    // Reverse to [C,B,A] via reorder_videos, which UPDATEs all three in ONE transaction
    // (Codex M2: it updates existing rows, not upserts). Plain multi-statement writes over
    // PostgREST are not transactional, so the reorder uses a SECURITY INVOKER function that
    // runs under the caller's RLS and performs the updates in one transaction — the deferred
    // unique constraint is checked only at COMMIT, so the transient duplicate position (C→0
    // while A is still 0) is allowed. Against a NON-deferrable constraint this would fail on
    // the first UPDATE — so a green here proves the deferral is in effect.
    const { error } = await client.rpc('reorder_videos', {
      items: [{ video_id: 'C', position: 0 }, { video_id: 'B', position: 1 }, { video_id: 'A', position: 2 }],
      p_playlist_id: playlistId,
    });
    expect(error).toBeNull();

    const { data } = await client.from('videos').select('video_id,position')
      .eq('playlist_id', playlistId).order('position');
    expect(data).toEqual([
      { video_id: 'C', position: 0 }, { video_id: 'B', position: 1 }, { video_id: 'A', position: 2 },
    ]);
  });
});

describe('anonymous isolation', () => {
  it('an anon session sees only its own rows', async () => {
    const { client, userId } = await anonSession();
    const anonInsert = await client.from('playlists')
      .insert({ owner_id: userId, playlist_key: 'PLanon', playlist_url: 'https://youtube.com/playlist?list=PLanon' });
    expect(anonInsert.error).toBeNull();               // Codex I2: prove the anon row was really created
    const mine = await client.from('playlists').select('owner_id');
    expect(mine.data).toEqual([{ owner_id: userId }]);

    const other = await newUser();
    const O = await ownedPlaylist(other.email, other.password, 'PLother');
    const cross = await client.from('playlists').select('*').eq('id', O.playlistId);
    expect(cross.data).toEqual([]);
  });
});
