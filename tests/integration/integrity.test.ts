import { newUser, signInAs, anonSession } from './helpers/clients';

async function ownedPlaylist(email: string, password: string, key: string) {
  const { client, userId } = await signInAs(email, password);
  const { data } = await client.from('playlists')
    .insert({ owner_id: userId, playlist_key: key, playlist_url: `https://youtube.com/playlist?list=${key}` })
    .select('id').single();
  return { client, userId, playlistId: data!.id };
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

    // Reverse to [C,B,A] via an RPC that upserts all three in one transaction.
    // Plain multi-statement upsert over PostgREST is not transactional, so reorder
    // uses a SECURITY INVOKER function that runs under the caller's RLS. Implementer:
    // add supabase/migrations/0005_reorder_helper.sql defining reorder_videos(jsonb)
    // as SECURITY INVOKER; it performs the updates inside one transaction so the
    // deferred unique constraint is checked at COMMIT.
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
    await client.from('playlists')
      .insert({ owner_id: userId, playlist_key: 'PLanon', playlist_url: 'https://youtube.com/playlist?list=PLanon' });
    const mine = await client.from('playlists').select('owner_id');
    expect(mine.data).toEqual([{ owner_id: userId }]);

    const other = await newUser();
    const O = await ownedPlaylist(other.email, other.password, 'PLother');
    const cross = await client.from('playlists').select('*').eq('id', O.playlistId);
    expect(cross.data).toEqual([]);
  });
});
