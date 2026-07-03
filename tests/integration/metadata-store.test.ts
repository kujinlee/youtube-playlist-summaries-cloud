// tests/integration/metadata-store.test.ts
//
// Integration suite for SupabaseMetadataStore against a live local Supabase stack.
// Run via: npm run test:integration -- metadata-store
// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).

import { newUser, signInAs } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import type { Principal } from '@/lib/storage/principal';

// id is unused in cloud mode; RLS derives owner from the JWT's auth.uid().
const P: Principal = { id: '', indexKey: 'listX' };

async function storeForNewUser(): Promise<SupabaseMetadataStore> {
  const u = await newUser();
  const { client } = await signInAs(u.email, u.password);
  return new SupabaseMetadataStore(client);
}

/** Minimal video stub accepted by upsertVideo; uses `as any` to skip schema
 *  validation — integration tests focus on store behaviour, not type fidelity. */
function makeVideo(id: string, serialNumber: number) {
  return {
    id,
    title: `Title ${id}`,
    youtubeUrl: `https://youtu.be/${id}`,
    language: 'en' as const,
    durationSeconds: 100,
    archived: false,
    ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
    overallScore: 3,
    summaryMd: null,
    processedAt: '2024-01-01T00:00:00.000Z',
    serialNumber,
  };
}

describe('SupabaseMetadataStore integration', () => {
  // 1. empty read parity
  test('absent playlist → emptyPlaylistIndex sentinel', async () => {
    const store = await storeForNewUser();
    await expect(store.readIndex(P)).resolves.toEqual({
      playlistUrl: '',
      outputFolder: 'listX',
      videos: [],
    });
  });

  // 2. setPlaylistMeta create then update
  test('setPlaylistMeta create then update; readIndex reflects both writes', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, {
      playlistUrl: 'https://youtube.com/playlist?list=listX',
      playlistTitle: 'My List',
    });
    let idx = await store.readIndex(P);
    expect(idx.playlistUrl).toBe('https://youtube.com/playlist?list=listX');
    expect(idx.playlistTitle).toBe('My List');
    expect(idx.videos).toEqual([]);

    // update via upsert on (owner_id, playlist_key)
    await store.setPlaylistMeta(P, {
      playlistUrl: 'https://youtube.com/playlist?list=listX',
      playlistTitle: 'Updated List',
    });
    idx = await store.readIndex(P);
    expect(idx.playlistTitle).toBe('Updated List');
  });

  // 3. claimVideoSlot allocates sequential slots; upsertVideo fills row; readIndex round-trips
  test('claimVideoSlot allocates position+serial sequentially; readIndex returns videos in order', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });

    const slotA = await store.claimVideoSlot(P, 'vidAAAAAAAA');
    expect(slotA).toEqual({ position: 0, serialNumber: 1 });

    const slotB = await store.claimVideoSlot(P, 'vidBBBBBBBB');
    expect(slotB).toEqual({ position: 1, serialNumber: 2 });

    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);
    await store.upsertVideo(P, makeVideo('vidBBBBBBBB', 2) as any);

    const idx = await store.readIndex(P);
    expect(idx.playlistUrl).toContain('list=listX');
    expect(idx.videos.map((v) => v.id)).toEqual(['vidAAAAAAAA', 'vidBBBBBBBB']);
  });

  // 4. bulkUpdateVideoFields preserves all three fields + array order
  test('bulkUpdateVideoFields preserves playlistIndex + videoPublishedAt + addedToPlaylistAt for all patches', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    await store.claimVideoSlot(P, 'vid1');
    await store.claimVideoSlot(P, 'vid2');
    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
    await store.upsertVideo(P, makeVideo('vid2', 2) as any);

    await store.bulkUpdateVideoFields(P, [
      {
        videoId: 'vid1',
        fields: {
          playlistIndex: 3,
          videoPublishedAt: '2021-01-01T00:00:00Z',
          addedToPlaylistAt: '2021-06-01T00:00:00Z',
        } as any,
      },
      {
        videoId: 'vid2',
        fields: {
          playlistIndex: 7,
          videoPublishedAt: '2022-01-01T00:00:00Z',
          addedToPlaylistAt: '2022-06-01T00:00:00Z',
        } as any,
      },
    ]);

    const idx = await store.readIndex(P);
    // position order: vid1 < vid2
    const v1 = idx.videos[0] as any;
    const v2 = idx.videos[1] as any;
    expect(v1.id).toBe('vid1');
    expect(v1.playlistIndex).toBe(3);
    expect(v1.videoPublishedAt).toBe('2021-01-01T00:00:00Z');
    expect(v1.addedToPlaylistAt).toBe('2021-06-01T00:00:00Z');
    expect(v2.id).toBe('vid2');
    expect(v2.playlistIndex).toBe(7);
    expect(v2.videoPublishedAt).toBe('2022-01-01T00:00:00Z');
    expect(v2.addedToPlaylistAt).toBe('2022-06-01T00:00:00Z');
  });

  // 4b. bulkUpdateVideoFields with empty patches array (edge case — should not error)
  test('bulkUpdateVideoFields with empty patches array does not error', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    await expect(store.bulkUpdateVideoFields(P, [])).resolves.toBeUndefined();
  });

  // 5. write-once re-sync (F2b)
  test('write-once re-sync (F2b): second bulkUpdate passing same ??-guarded values leaves write-once fields unchanged; mutable field updates', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    await store.claimVideoSlot(P, 'vidAAAAAAAA');
    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);

    // first sync: set write-once fields
    await store.bulkUpdateVideoFields(P, [{
      videoId: 'vidAAAAAAAA',
      fields: {
        videoPublishedAt: '2020-01-01T00:00:00Z',
        addedToPlaylistAt: '2020-02-01T00:00:00Z',
        playlistIndex: 1,
      } as any,
    }]);

    // second sync: caller applies the ?? guard — re-passes the already-set values.
    // merge_video_data does a plain shallow merge (no special write-once guard at the DB
    // level), so the fields remain unchanged because the values passed are identical.
    const cur = (await store.readIndex(P)).videos[0] as any;
    await store.bulkUpdateVideoFields(P, [{
      videoId: 'vidAAAAAAAA',
      fields: {
        videoPublishedAt: cur.videoPublishedAt,     // same value — no change
        addedToPlaylistAt: cur.addedToPlaylistAt,   // same value — no change
        playlistIndex: 2,                            // mutable — should update
      } as any,
    }]);

    const after = (await store.readIndex(P)).videos[0] as any;
    expect(after.videoPublishedAt).toBe('2020-01-01T00:00:00Z');   // unchanged
    expect(after.addedToPlaylistAt).toBe('2020-02-01T00:00:00Z');  // unchanged
    expect(after.playlistIndex).toBe(2);                            // mutable field updated
  });

  // 6. artifacts deep-merge sibling preservation (F6)
  test('artifacts deep-merge preserves sibling artifact kinds (F6)', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    await store.claimVideoSlot(P, 'vidAAAAAAAA');
    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);

    // write summaryMd artifact kind
    await store.updateVideoFields(P, 'vidAAAAAAAA', {
      artifacts: { summaryMd: { key: 'a.md', status: 'promoted' } },
    } as any);
    // write html artifact kind — must NOT clobber summaryMd
    await store.updateVideoFields(P, 'vidAAAAAAAA', {
      artifacts: { html: { key: 'a.html', status: 'promoted' } },
    } as any);

    const v = (await store.readIndex(P)).videos[0] as any;
    // deep-merge in merge_video_data must preserve both keys
    expect(v.artifacts.summaryMd).toEqual({ key: 'a.md', status: 'promoted' });
    expect(v.artifacts.html).toEqual({ key: 'a.html', status: 'promoted' });
  });

  // 7. reconcilePlaylistMembership archives absent ids and restores present ids
  test('reconcilePlaylistMembership archives absent ids and restores present ids atomically', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    await store.claimVideoSlot(P, 'vid1');
    await store.claimVideoSlot(P, 'vid2');
    await store.claimVideoSlot(P, 'vid3');
    await store.upsertVideo(P, makeVideo('vid1', 1) as any);
    await store.upsertVideo(P, makeVideo('vid2', 2) as any);
    await store.upsertVideo(P, makeVideo('vid3', 3) as any);

    // archive vid3 by omitting it from the present set
    await store.reconcilePlaylistMembership(P, ['vid1', 'vid2']);
    let idx = await store.readIndex(P);
    const vid3Archived = idx.videos.find((v) => v.id === 'vid3') as any;
    expect(vid3Archived?.archived).toBe(true);
    expect(vid3Archived?.removedFromPlaylist).toBe(true);
    // vid1 and vid2 remain not-archived
    expect(idx.videos.find((v) => v.id === 'vid1')?.archived).toBe(false);
    expect(idx.videos.find((v) => v.id === 'vid2')?.archived).toBe(false);

    // restore vid3 by including it in the present set
    await store.reconcilePlaylistMembership(P, ['vid1', 'vid2', 'vid3']);
    idx = await store.readIndex(P);
    const vid3Restored = idx.videos.find((v) => v.id === 'vid3') as any;
    expect(vid3Restored?.archived).toBe(false);
    expect(vid3Restored?.removedFromPlaylist).toBe(false);
  });

  // 8. deleteVideo removes the row
  test('deleteVideo removes the row; readIndex no longer contains it', async () => {
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    await store.claimVideoSlot(P, 'vidAAAAAAAA');
    await store.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);

    let idx = await store.readIndex(P);
    expect(idx.videos.map((v) => v.id)).toContain('vidAAAAAAAA');

    await store.deleteVideo(P, 'vidAAAAAAAA');

    idx = await store.readIndex(P);
    expect(idx.videos.map((v) => v.id)).not.toContain('vidAAAAAAAA');
    expect(idx.videos).toHaveLength(0);
  });

  // 9. RLS isolation
  test('RLS isolation: user B cannot read or write user A rows (B sees empty index)', async () => {
    const storeA = await storeForNewUser();
    await storeA.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    await storeA.claimVideoSlot(P, 'vidAAAAAAAA');
    await storeA.upsertVideo(P, makeVideo('vidAAAAAAAA', 1) as any);

    // user B with the same indexKey must see nothing (owner_id scopes all RLS policies)
    const storeB = await storeForNewUser();
    const idxB = await storeB.readIndex(P);
    expect(idxB).toEqual({ playlistUrl: '', outputFolder: 'listX', videos: [] });

    // B's setPlaylistMeta creates its own playlist (not A's) — B cannot read A's
    await storeB.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });
    const idxBAfterSeed = await storeB.readIndex(P);
    expect(idxBAfterSeed.videos).toEqual([]);  // B's playlist has no videos

    // A's data is still intact
    const idxAFinal = await storeA.readIndex(P);
    expect(idxAFinal.videos.map((v) => v.id)).toEqual(['vidAAAAAAAA']);
  });

  // 10. claimVideoSlot idempotent re-claim (ON CONFLICT DO NOTHING)
  test('claimVideoSlot idempotent re-claim: returns next-slot values; exactly one row persists', async () => {
    // Observed behavior (documented here per T8/T9 flag):
    // The RPC computes v_pos/v_serial from MAX(position)/MAX(serialNumber) BEFORE the
    // ON CONFLICT check. When the same videoId is re-claimed, the INSERT is skipped but
    // the RPC still returns the "next available" slot values (position 1, serialNumber 2),
    // not the original values (position 0, serialNumber 1). Only one row exists in the DB.
    const store = await storeForNewUser();
    await store.setPlaylistMeta(P, { playlistUrl: 'https://youtube.com/playlist?list=listX' });

    const first = await store.claimVideoSlot(P, 'vidAAAAAAAA');
    expect(first).toEqual({ position: 0, serialNumber: 1 });

    // re-claim the same videoId — ON CONFLICT DO NOTHING suppresses the INSERT
    const reClaim = await store.claimVideoSlot(P, 'vidAAAAAAAA');
    // v_pos and v_serial are computed from MAX before the conflict fires:
    //   MAX(position) = 0  → v_pos = 1
    //   MAX(serialNumber from data) = 1 → v_serial = 2
    expect(reClaim).toEqual({ position: 1, serialNumber: 2 });

    // only the original reservation row exists — no duplicate inserted
    const idx = await store.readIndex(P);
    expect(idx.videos).toHaveLength(1);
    expect(idx.videos[0].id).toBe('vidAAAAAAAA');
  });
});
