jest.mock('@/lib/youtube', () => ({ ...jest.requireActual('@/lib/youtube'), fetchPlaylistVideos: jest.fn() }));
import { randomUUID } from 'crypto';
import { newUser, signInAs } from './helpers/clients';
import * as youtube from '@/lib/youtube';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { enqueuePlaylist } from '@/lib/job-queue/producer';
import type { VideoMeta } from '@/types';

const fetchMock = jest.mocked(youtube.fetchPlaylistVideos);
const vmeta = (id: string, dur = 100): VideoMeta =>
  ({ videoId: id, title: id, youtubeUrl: `https://youtu.be/${id}`, durationSeconds: dur });

test('producer fans out real jobs that are then pollable via listByPlaylist', async () => {
  process.env.STORAGE_BACKEND = 'supabase'; process.env.YOUTUBE_API_KEY = 'k';
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const key = `PL-${randomUUID()}`; const url = `https://www.youtube.com/playlist?list=${key}`;
  fetchMock.mockResolvedValueOnce([vmeta('v1'), vmeta('v2'), vmeta('v3', 0)]); // v3 skipped
  const queue = new SupabaseJobQueue(ca);
  const bundle = { metadataStore: new SupabaseMetadataStore(ca), blobStore: {} as any, jobQueue: queue };
  const res = await enqueuePlaylist(bundle as any, { id: userId, indexKey: key }, url);
  expect(res.counts).toEqual({ enqueued: 2, joined: 0, skipped: 1, failed: 0 });
  const rows = await queue.listByPlaylist(res.playlistId!);
  expect(rows.map(r => r.videoId).sort()).toEqual(['v1', 'v2']);
});
