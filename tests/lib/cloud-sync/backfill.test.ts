import { deriveClassASignals, deriveHumanSnapshot } from '@/lib/cloud-sync/backfill';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import type { Video } from '@/types';

const legacy: Video = {
  id: 'a', title: 'T', youtubeUrl: 'https://youtu.be/a', language: 'en', durationSeconds: 1,
  archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: '001_title.md', processedAt: '2026-01-01T00:00:00.000Z', // KEY, not body
  personalNote: 'note', updatedAt: '2026-02-02T00:00:00.000Z',
  // no mdGeneratedAt / mdCorrectionsHash / annotationsEditedAt
};
const BODY = '# S\n\nbody\n';

it('hashes the MD BODY, not the summaryMd key (Blocking ①)', () => {
  const s = deriveClassASignals(legacy, BODY);
  expect(s.mdHash).toBe(mdHash(BODY));
  expect(s.mdHash).not.toBe(mdHash('001_title.md')); // must NOT hash the filename
  expect(s.summaryMdKey).toBe('001_title.md');
});

it('backfills mdGeneratedAt from processedAt and flags it', () => {
  const s = deriveClassASignals(legacy, BODY);
  expect(s.mdGeneratedAt).toBe('2026-01-01T00:00:00.000Z');
  expect(s.backfilled).toBe(true);
  expect(s.docVersionMajor).toBe(1); // absent docVersion ⇒ pre-feature major 1
});

it('mdHash is null when there is no MD body', () => {
  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
  expect(s.mdHash).toBeNull();
  expect(s.summaryMdKey).toBeNull();
});

it('uses real signals (not backfilled) when present', () => {
  const s = deriveClassASignals({ ...legacy, mdGeneratedAt: '2026-03-03T00:00:00.000Z', mdCorrectionsHash: 'h', docVersion: { major: 3, minor: 3 } }, BODY);
  expect(s.backfilled).toBe(false);
  expect(s.mdGeneratedAt).toBe('2026-03-03T00:00:00.000Z');
  expect(s.docVersionMajor).toBe(3);
});

it('backfills a present human field with a provisional flagged timestamp', () => {
  const snap = deriveHumanSnapshot(legacy);
  expect(snap.personalNote.value).toBe('note');
  expect(snap.personalNote.editedAt).toBe('2026-02-02T00:00:00.000Z');
  expect(snap.personalNote.backfilled).toBe(true);
  expect(snap.personalScore.value).toBeUndefined();
});
