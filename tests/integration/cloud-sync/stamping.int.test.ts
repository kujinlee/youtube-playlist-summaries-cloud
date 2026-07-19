// tests/integration/cloud-sync/stamping.int.test.ts
//
// Stage 3 Cloud Sync (§5.7), Task 3. Integration suite for migration 0021's stamping
// behavior: per-field annotationsEditedAt on update_video_annotations/merge_video_data,
// corrections allowlisting, the 3/4-key-no-p_edited_at overload-resolution guard, and
// persist_summary's mdGeneratedAt/mdCorrectionsHash passthrough.
//
// Runs against local Supabase (jest.integration.config.ts). Uses the shared integration
// harness to create an owner session + a playlist + a video row.
import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';

describe('0021 stamping RPCs', () => {
  it('update_video_annotations stamps only the changed Class-B field, not archived', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_set: { personalNote: 'hi', archived: true }, p_clear: [],
      p_edited_at: '2026-07-17T10:00:00.000Z',
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.annotationsEditedAt?.personalNote).toBe('2026-07-17T10:00:00.000Z');
    expect(row.annotationsEditedAt?.personalScore).toBeUndefined();
    expect(row.annotationsEditedAt?.corrections).toBeUndefined();
    expect(row.personalNote).toBe('hi');
    expect(row.archived).toBe(true);
  });

  it('a clear stamps the timestamp while removing the value', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx, { personalNote: 'old' });
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId, p_set: {}, p_clear: ['personalNote'],
      p_edited_at: '2026-07-17T11:00:00.000Z',
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.personalNote).toBeUndefined();
    expect(row.annotationsEditedAt?.personalNote).toBe('2026-07-17T11:00:00.000Z');
  });

  it('corrections is now allowlisted (was dropped) and stamps its own timestamp', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId,
      p_set: { corrections: 'fix name' }, p_clear: [], p_edited_at: '2026-07-17T12:00:00.000Z',
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.corrections).toBe('fix name');
    expect(row.annotationsEditedAt?.corrections).toBe('2026-07-17T12:00:00.000Z');
  });

  it('resolves the 4-key call (no p_edited_at) unambiguously — no PGRST203 overload (Blocking ④)', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    // Call EXACTLY as SupabaseMetadataStore does today — WITHOUT p_edited_at. Must not error
    // with "could not choose the best candidate function"; must stamp with now().
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId, p_set: { personalNote: 'x' }, p_clear: [],
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.personalNote).toBe('x');
    expect(row.annotationsEditedAt?.personalNote).toBeDefined();
    // Same for merge_video_data's 3-key call:
    await ctx.rpc('merge_video_data', { p_playlist_id: playlistId, p_video_id: videoId, p_fields: { corrections: 'z' } });
    expect((await ctx.readVideoData(playlistId, videoId)).annotationsEditedAt?.corrections).toBeDefined();
  });

  it('an archived-only write leaves annotationsEditedAt absent (Medium — no empty {}) ', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('update_video_annotations', {
      p_playlist_id: playlistId, p_video_id: videoId, p_set: { archived: true }, p_clear: [],
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.annotationsEditedAt).toBeUndefined();
    expect(row.archived).toBe(true);
  });

  it('merge_video_data does NOT stamp annotationsEditedAt for a non-Class-B (MD-finalize) write', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.rpc('merge_video_data', {
      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
    });
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.annotationsEditedAt).toBeUndefined();
  });

  it('persist_summary stamps mdGeneratedAt + mdCorrectionsHash', async () => {
    const ctx = await makeOwnerContext();
    const { playlistId, videoId } = await seedVideo(ctx);
    await ctx.persistSummary(playlistId, videoId, {
      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
      ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
      overallScore: 4, docVersion: { major: 3, minor: 3 }, processedAt: '2026-07-17T13:00:00.000Z',
    }, 'committed');
    const row = await ctx.readVideoData(playlistId, videoId);
    expect(row.mdGeneratedAt).toBe('2026-07-17T13:00:00.000Z');
    expect(row.mdCorrectionsHash).toBe('h1');
  });
});
