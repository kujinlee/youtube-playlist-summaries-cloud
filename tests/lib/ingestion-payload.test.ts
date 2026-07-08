import { parseIngestionPayload } from '@/lib/job-queue/ingestion-payload';

const base = { youtubeUrl: 'https://youtu.be/x', title: 'T', durationSeconds: 100, playlistIndex: 1 };

it('parses a payload with channel/dates absent', () => {
  const p = parseIngestionPayload(base);
  expect(p.channel).toBeUndefined();
  expect(p.videoPublishedAt).toBeUndefined();
});
it('rejects an empty-string date', () => {
  expect(() => parseIngestionPayload({ ...base, videoPublishedAt: '' })).toThrow();
});
it('parses valid datetimes and channel', () => {
  const p = parseIngestionPayload({ ...base, channel: 'C', videoPublishedAt: '2020-01-01T00:00:00Z',
    addedToPlaylistAt: '2020-01-02T00:00:00Z' });
  expect(p.channel).toBe('C');
});
