jest.mock('@/lib/youtube', () => ({ ...jest.requireActual('@/lib/youtube'), fetchPlaylistVideos: jest.fn() }));
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import * as youtube from '@/lib/youtube';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
import { enqueuePlaylist } from '@/lib/job-queue/producer';
import type { VideoMeta } from '@/types';

const fetchMock = jest.mocked(youtube.fetchPlaylistVideos);
const vmeta = (id: string, dur = 100): VideoMeta =>
  ({ videoId: id, title: id, youtubeUrl: `https://youtu.be/${id}`, durationSeconds: dur });

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

// T13: producer.enqueuePlaylist moved from a 3-arg (bundle, principal, url) signature that
// enqueued through the session-client `bundle.jobQueue` to a 5-arg (bundle, enqueuer, principal,
// url, ctx) signature that enqueues through a service-role `Enqueuer` — the two-client split
// (T10/T11) plus the new 7-bucket ProducerCounts. Re-baselined below against that shape.
test('producer fans out real jobs (via the service-role Enqueuer) that are then pollable via listByPlaylist', async () => {
  process.env.STORAGE_BACKEND = 'supabase'; process.env.YOUTUBE_API_KEY = 'k';
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const key = `PL-${randomUUID()}`; const url = `https://www.youtube.com/playlist?list=${key}`;
  fetchMock.mockResolvedValueOnce([vmeta('v1'), vmeta('v2'), vmeta('v3', 0)]); // v3 skipped (duration<=0)
  const bundle = { metadataStore: new SupabaseMetadataStore(ca) } as any;
  const enqueuer = new SupabaseEnqueuer(svc);
  const ctx = { ownerId: userId, enqueueIp: null };
  const res = await enqueuePlaylist(bundle, enqueuer, { id: userId, indexKey: key }, url, ctx);
  expect(res.counts).toEqual({
    enqueued: 2, joined: 0, skipped: 1, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0,
  });
  const queue = new SupabaseJobQueue(ca);
  const rows = await queue.listByPlaylist(res.playlistId!);
  expect(rows.map(r => r.videoId).sort()).toEqual(['v1', 'v2']);
});
