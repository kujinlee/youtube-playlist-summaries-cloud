import { videoMetaToIngestionPayload } from '@/lib/job-queue/video-meta-to-payload';
import type { VideoMeta } from '@/types';

const meta = (over: Partial<VideoMeta> = {}): VideoMeta => ({
  videoId: 'v1', title: 'T', youtubeUrl: 'https://youtu.be/v1', durationSeconds: 100,
  channelTitle: 'C', videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-01-02T00:00:00Z', ...over,
});

it('maps a full meta to a schema-valid payload, videoId carried', () => {
  const r = videoMetaToIngestionPayload(meta(), 3);
  expect(r.videoId).toBe('v1');
  if (!('ok' in r)) throw new Error('expected ok');
  expect(r.ok.channel).toBe('C');
  expect(r.ok.playlistIndex).toBe(3);
  expect(r.ok.videoPublishedAt).toBe('2020-01-01T00:00:00Z');
});

it('omits absent channel/dates rather than emitting empty strings', () => {
  const r = videoMetaToIngestionPayload(meta({ channelTitle: undefined, videoPublishedAt: undefined, addedToPlaylistAt: undefined }), 1);
  if (!('ok' in r)) throw new Error('expected ok');
  expect('channel' in r.ok).toBe(false);
  expect('videoPublishedAt' in r.ok).toBe(false);
  expect('addedToPlaylistAt' in r.ok).toBe(false);
});

it('skips a non-positive or NaN duration', () => {
  expect(videoMetaToIngestionPayload(meta({ durationSeconds: 0 }), 1)).toEqual({ videoId: 'v1', skipped: 'non-positive-duration' });
  expect(videoMetaToIngestionPayload(meta({ durationSeconds: NaN }), 1)).toEqual({ videoId: 'v1', skipped: 'non-positive-duration' });
});

it('passes through valid present dates', () => {
  const r = videoMetaToIngestionPayload(meta(), 1);
  if (!('ok' in r)) throw new Error('expected ok');
  expect(r.ok.videoPublishedAt).toBe('2020-01-01T00:00:00Z');
  expect(r.ok.addedToPlaylistAt).toBe('2020-01-02T00:00:00Z');
});

it('reflects a channelTitle rename onto ok.channel', () => {
  const r = videoMetaToIngestionPayload(meta({ channelTitle: 'Renamed' }), 1);
  if (!('ok' in r)) throw new Error('expected ok');
  expect(r.ok.channel).toBe('Renamed');
});

it('passes playlistIndex through 1-indexed as given', () => {
  const r = videoMetaToIngestionPayload(meta(), 7);
  if (!('ok' in r)) throw new Error('expected ok');
  expect(r.ok.playlistIndex).toBe(7);
});

it('carries videoId on the skipped variant too', () => {
  const r = videoMetaToIngestionPayload(meta({ videoId: 'v2', durationSeconds: -5 }), 1);
  expect(r).toEqual({ videoId: 'v2', skipped: 'non-positive-duration' });
});
