// tests/integration/cloud-sync/cloud-stamping.int.test.ts
//
// Stage 3 Cloud Sync (§5.7), Task 4. Store-layer mirror of Task 3's stamping.int.test.ts (which
// hit the 0021 RPCs directly) — this drives SupabaseMetadataStore itself (the real production
// call site) with an RLS-scoped user session client, confirming it forwards `corrections` and
// `opts.editedAt` through to update_video_annotations.
import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';

describe('SupabaseMetadataStore — Class-B stamping passthrough', () => {
  it('cloud store forwards corrections + sync timestamp through the RPC', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    const store = new SupabaseMetadataStore(ctx.userClient); // user-session client, RLS-scoped
    await store.updateVideoAnnotations(ctx.principal, videoId, { corrections: 'fix' }, [], { editedAt: '2019-05-05T00:00:00.000Z' });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.corrections).toBe('fix');
    expect(row.annotationsEditedAt?.corrections).toBe('2019-05-05T00:00:00.000Z');
  });

  it('cloud store forwards opts.editedAt through updateVideoFields (merge_video_data)', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    const store = new SupabaseMetadataStore(ctx.userClient);
    await store.updateVideoFields(ctx.principal, videoId, { corrections: 'fixed via regenerate' }, { editedAt: '2018-03-03T00:00:00.000Z' });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.corrections).toBe('fixed via regenerate');
    expect(row.annotationsEditedAt?.corrections).toBe('2018-03-03T00:00:00.000Z');
  });

  it('updateVideoAnnotations defaults to now() when opts is omitted (user-edit path)', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    const store = new SupabaseMetadataStore(ctx.userClient);
    const before = Date.now();
    await store.updateVideoAnnotations(ctx.principal, videoId, { personalNote: 'hi' }, []);
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.personalNote).toBe('hi');
    const stamped = Date.parse(row.annotationsEditedAt?.personalNote);
    expect(stamped).toBeGreaterThanOrEqual(before - 1000);
  });
});
