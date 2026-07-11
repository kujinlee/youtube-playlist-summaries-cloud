// tests/integration/annotations-rpc.test.ts
//
// Integration suite for the update_video_annotations RPC (Stage 2a Task 7) against a
// REAL local Supabase stack. Run via: npm run test:integration -- annotations-rpc
// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
//
// This RPC is a DISTINCT write path from merge_video_data (unchanged): it allowlists
// writable keys IN SQL and derives the owner solely from auth.uid() (no p_owner param).
// Exercised here via SupabaseMetadataStore.updateVideoAnnotations, the store method
// Task 7 adds — this proves the store→RPC wiring, not just the raw SQL.

import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import type { Principal } from '@/lib/storage/principal';

const svc = adminClient();

async function storeForUser(email: string, password: string): Promise<SupabaseMetadataStore> {
  const { client } = await signInAs(email, password);
  return new SupabaseMetadataStore(client);
}

describe('update_video_annotations RPC (via SupabaseMetadataStore.updateVideoAnnotations)', () => {
  // (a) set personalScore then clear (JSON-null) → key removed
  it('set personalScore then clear → key removed', async () => {
    const a = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId });
    const store = await storeForUser(a.email, a.password);
    const p: Principal = { id: a.user.id, indexKey: playlistKey };

    const setRes = await store.updateVideoAnnotations(p, videoId, { personalScore: 4 }, []);
    expect(setRes).toEqual({ found: true });
    let idx = await store.readIndex(p);
    expect((idx.videos.find((v) => v.id === videoId) as any).personalScore).toBe(4);

    const clearRes = await store.updateVideoAnnotations(p, videoId, {}, ['personalScore']);
    expect(clearRes).toEqual({ found: true });
    idx = await store.readIndex(p);
    const v = idx.videos.find((vv) => vv.id === videoId) as any;
    expect('personalScore' in v).toBe(false);
  });

  // (b) mixed set-note + clear-score in one call
  it('mixed set-note + clear-score in one call', async () => {
    const a = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId });
    const store = await storeForUser(a.email, a.password);
    const p: Principal = { id: a.user.id, indexKey: playlistKey };

    await store.updateVideoAnnotations(p, videoId, { personalScore: 2 }, []);
    const res = await store.updateVideoAnnotations(p, videoId, { personalNote: 'great video' }, ['personalScore']);
    expect(res).toEqual({ found: true });

    const idx = await store.readIndex(p);
    const v = idx.videos.find((vv) => vv.id === videoId) as any;
    expect(v.personalNote).toBe('great video');
    expect('personalScore' in v).toBe(false);
  });

  // (c) missing video → found:false
  it('missing video → found:false', async () => {
    const a = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
    const store = await storeForUser(a.email, a.password);
    const p: Principal = { id: a.user.id, indexKey: playlistKey };
    void playlistId;

    const res = await store.updateVideoAnnotations(p, 'no-such-video', { personalScore: 3 }, []);
    expect(res).toEqual({ found: false });
  });

  // (d) cross-owner: owner B with A's playlist_id → 0 rows (found:false), A unmodified
  it('cross-owner: B using A\'s playlist_id/indexKey gets found:false; A unmodified', async () => {
    const a = await newUser();
    const b = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId });
    await svc.from('videos').update({ data: { id: videoId, serialNumber: 1, language: 'en', personalScore: 3 } })
      .eq('playlist_id', playlistId).eq('video_id', videoId);

    const storeB = await storeForUser(b.email, b.password);
    // B addresses A's playlist by the SAME indexKey (playlist_key) — requirePlaylistId
    // resolves playlist_key → id under B's SESSION client; RLS on `playlists` scopes
    // that lookup to B's own rows, so B cannot even resolve A's playlist_key to A's id.
    const pB: Principal = { id: b.user.id, indexKey: playlistKey };
    await expect(storeB.updateVideoAnnotations(pB, videoId, { personalScore: 9 } as any, []))
      .rejects.toThrow(); // requirePlaylistId throws: playlist not found for indexKey (RLS-scoped)

    // A's data is unmodified regardless
    const { data: row, error } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect(error).toBeNull();
    expect((row!.data as any).personalScore).toBe(3);
  });

  // (d2) cross-owner via a DIRECT RPC call bypassing requirePlaylistId's RLS-scoped lookup:
  // proves the RPC's own `owner_id = auth.uid()` WHERE guard independently, using the
  // REAL playlist_id UUID (not routed through the store, which would fail earlier on the
  // playlist_key lookup as in the previous test).
  it('cross-owner (direct RPC): B calling with A\'s real playlist_id UUID → 0 rows, A unmodified', async () => {
    const a = await newUser();
    const b = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId });
    await svc.from('videos').update({ data: { id: videoId, serialNumber: 1, language: 'en', personalScore: 3 } })
      .eq('playlist_id', playlistId).eq('video_id', videoId);

    const { client: bClient } = await signInAs(b.email, b.password);
    const { data, error } = await bClient.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId, p_set: { personalScore: 9 }, p_clear: [],
    });
    expect(error).toBeNull();
    expect(data).toBe(0); // 0 rows updated — owner_id = auth.uid() guard rejects B

    const { data: row } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect((row!.data as any).personalScore).toBe(3); // A unmodified
  });

  // (e) non-allowlisted key in p_set (e.g. summaryMd) is NOT written
  it('non-allowlisted key in p_set is not written', async () => {
    const a = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId });
    const store = await storeForUser(a.email, a.password);
    const p: Principal = { id: a.user.id, indexKey: playlistKey };

    const res = await store.updateVideoAnnotations(
      p, videoId, { personalScore: 3, summaryMd: 'hacked.md' } as any, [],
    );
    expect(res).toEqual({ found: true });

    const idx = await store.readIndex(p);
    const v = idx.videos.find((vv) => vv.id === videoId) as any;
    expect(v.personalScore).toBe(3);
    // summaryMd was already seeded (seedPromotedVideo sets it); assert the RPC's value
    // ('hacked.md') never overwrote it — the allowlisted-only slice silently drops it.
    expect(v.summaryMd).not.toBe('hacked.md');
  });

  // (f) an existing merge_video_data write of summaryHtml:null still stores null
  // (regression guard: merge_video_data itself is UNCHANGED by this migration).
  it('merge_video_data (unchanged) still stores an explicit null for summaryHtml', async () => {
    const a = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId });
    const store = await storeForUser(a.email, a.password);
    const p: Principal = { id: a.user.id, indexKey: playlistKey };

    await store.updateVideoFields(p, videoId, { summaryHtml: null } as any);

    const idx = await store.readIndex(p);
    const v = idx.videos.find((vv) => vv.id === videoId) as any;
    expect(v.summaryHtml).toBeNull();
  });
});
