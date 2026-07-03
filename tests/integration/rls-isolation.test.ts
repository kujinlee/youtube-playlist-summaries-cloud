// tests/integration/rls-isolation.test.ts
import { newUser, signInAs } from './helpers/clients';

async function seedPlaylistWithVideos(email: string, password: string, key: string) {
  const { client, userId } = await signInAs(email, password);
  const { data: pl, error: e1 } = await client.from('playlists')
    .insert({ owner_id: userId, playlist_key: key, playlist_url: `https://youtube.com/playlist?list=${key}` })
    .select('id').single();
  expect(e1).toBeNull();
  const rows = [0, 1].map((i) => ({
    playlist_id: pl!.id, owner_id: userId, video_id: `v${i}`, position: i, data: { id: `v${i}` },
  }));
  const { error: e2 } = await client.from('videos').insert(rows);
  expect(e2).toBeNull();
  return { client, userId, playlistId: pl!.id };
}

describe('RLS isolation', () => {
  it('B cannot see A\'s profiles, playlists, or videos (0 rows, not error) (Codex H5)', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLaaa');
    const b = await newUser();
    const { client: bClient } = await signInAs(b.email, b.password);

    // profiles isolation (spec §7 requires all three tables)
    const prof = await bClient.from('profiles').select('*').eq('id', A.userId);
    expect(prof.error).toBeNull();
    expect(prof.data).toEqual([]);

    const pl = await bClient.from('playlists').select('*').eq('id', A.playlistId);
    expect(pl.error).toBeNull();
    expect(pl.data).toEqual([]);

    const vids = await bClient.from('videos').select('*').eq('playlist_id', A.playlistId);
    expect(vids.error).toBeNull();                    // spec §7: "0 rows, not error" (Codex I-1)
    expect(vids.data).toEqual([]);
  });

  it('B update AND delete on A\'s invisible rows affect 0 rows (no error) (Codex H6)', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLbbb');
    const b = await newUser();
    const { client: bClient } = await signInAs(b.email, b.password);

    const upd = await bClient.from('videos').update({ position: 99 })
      .eq('playlist_id', A.playlistId).select();
    expect(upd.error).toBeNull();
    expect(upd.data).toEqual([]);                    // invisible → 0 affected

    const del = await bClient.from('videos').delete()
      .eq('playlist_id', A.playlistId).select();
    expect(del.error).toBeNull();
    expect(del.data).toEqual([]);                    // invisible → 0 deleted

    // A's rows are untouched (verified from A's own client)
    const stillThere = await A.client.from('videos').select('video_id')
      .eq('playlist_id', A.playlistId).order('position');
    expect(stillThere.data).toEqual([{ video_id: 'v0' }, { video_id: 'v1' }]);
  });

  it('with-check violation on a VISIBLE own row errors (owner_id reassignment) (Codex H6)', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLwc');
    const b = await newUser();
    const { userId: bId } = await signInAs(b.email, b.password);

    // A tries to hand its own (visible) video to B → with_check(owner_id=auth.uid()) fails
    const reassign = await A.client.from('videos').update({ owner_id: bId })
      .eq('playlist_id', A.playlistId).eq('video_id', 'v0').select();
    expect(reassign.error).not.toBeNull();           // visible row + bad with_check ⇒ error, not 0 rows

    // the rejected write left no partial change — owner_id is still A (Codex M-1)
    const after = await A.client.from('videos').select('owner_id')
      .eq('playlist_id', A.playlistId).eq('video_id', 'v0').single();
    expect(after.data?.owner_id).toBe(A.userId);
  });

  it('cross-owner FK attack: B inserts video with playlist_id=A is rejected', async () => {
    const a = await newUser();
    const A = await seedPlaylistWithVideos(a.email, a.password, 'PLccc');
    const b = await newUser();
    const { client: bClient, userId: bId } = await signInAs(b.email, b.password);

    // owner_id=B, playlist_id=A: composite FK (playlist_id, owner_id) has no match → rejected
    const asB = await bClient.from('videos')
      .insert({ playlist_id: A.playlistId, owner_id: bId, video_id: 'x', position: 0, data: { id: 'x' } });
    expect(asB.error).not.toBeNull();

    // owner_id=A (spoof): the FK PASSES here — (A.playlistId, A.userId) is a valid playlists
    // row — so only the with_check(owner_id=auth.uid()) rejects B claiming owner_id=A (Codex M-2)
    const asA = await bClient.from('videos')
      .insert({ playlist_id: A.playlistId, owner_id: A.userId, video_id: 'y', position: 0, data: { id: 'y' } });
    expect(asA.error).not.toBeNull();
  });
});
