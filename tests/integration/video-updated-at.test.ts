// tests/integration/video-updated-at.test.ts
//
// Task 1 (Stage 2a, §8): a BEFORE UPDATE trigger on `videos` must bump
// `updated_at` on EVERY row update — not just the RPC paths (merge_video_data,
// merge_video_data_bulk, reconcile_membership) that already set it explicitly.
// The gap this closes: SupabaseMetadataStore.upsertVideo() does a direct
// `.update({ data })` with no `updated_at` in the payload, so before the
// trigger exists that path leaves `updated_at` stale.
//
// This test drives BOTH write paths against a real Supabase instance and
// asserts `updated_at` advances each time, then asserts `readIndex` (the
// cloud read surface) exposes the column as `Video.updatedAt`.
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';
import { getStorageBundle } from '@/lib/storage/resolve';
import type { Video } from '@/types';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getUpdatedAt(playlistId: string, videoId: string): Promise<string> {
  const { data, error } = await svc
    .from('videos')
    .select('updated_at')
    .eq('playlist_id', playlistId)
    .eq('video_id', videoId)
    .single();
  if (error) throw error;
  return data!.updated_at as string;
}

it('trigger bumps videos.updated_at on the merge_video_data RPC path AND the direct upsertVideo(.update) path; readIndex surfaces it as Video.updatedAt', async () => {
  const a = await newUser();
  const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
  const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId });
  const { client: aClient } = await signInAs(a.email, a.password);
  const bundle = getStorageBundle({ supabaseClient: aClient });
  const principal = { id: a.user.id, indexKey: playlistKey };

  const t0 = await getUpdatedAt(playlistId, videoId);

  // --- Path 1: updateVideoFields → merge_video_data RPC (already sets updated_at explicitly;
  // this proves the trigger is idempotent alongside it, per the brief). ---
  await sleep(1100);
  await bundle.metadataStore.updateVideoFields(principal, videoId, { title: 'Updated via RPC' });
  const t1 = await getUpdatedAt(playlistId, videoId);
  expect(new Date(t1).getTime()).toBeGreaterThan(new Date(t0).getTime());

  // --- Path 2: upsertVideo → direct `.update({ data })` with NO updated_at in the payload.
  // Before the trigger exists, this leaves updated_at stale at t1. ---
  await sleep(1100);
  const { data: row, error: rowErr } = await svc
    .from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
  if (rowErr) throw rowErr;
  await bundle.metadataStore.upsertVideo(principal, row!.data as unknown as Video);
  const t2 = await getUpdatedAt(playlistId, videoId);
  expect(new Date(t2).getTime()).toBeGreaterThan(new Date(t1).getTime());

  // --- readIndex surfaces the column as Video.updatedAt, matching the DB value exactly. ---
  const index = await bundle.metadataStore.readIndex(principal);
  const v = index.videos.find((x) => x.id === videoId);
  expect(v?.updatedAt).toBe(t2);
});
