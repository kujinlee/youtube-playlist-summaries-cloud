// tests/lib/cloud-sync/local-stamping.test.ts
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { Video } from '@/types';

// assertOutputFolder requires the path to be within the home directory (macOS os.tmpdir()
// resolves outside home) — create isolated sub-dirs under home instead, mirroring
// tests/lib/storage/local-metadata-store.test.ts's established pattern.
async function tmpRoot(): Promise<string> {
  return fs.mkdtemp(path.join(os.homedir(), 'cs-local-'));
}

afterEach(async () => {
  const dirs = (await fs.readdir(os.homedir())).filter((d) => d.startsWith('cs-local-'));
  await Promise.all(dirs.map((d) => fs.rm(path.join(os.homedir(), d), { recursive: true, force: true })));
});
const v = (id: string): Video => ({
  id, title: 'T', youtubeUrl: `https://youtu.be/${id}`, language: 'en', durationSeconds: 1,
  archived: false, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 },
  overallScore: 3, summaryMd: null, processedAt: '2026-07-17T00:00:00.000Z',
});

describe('local per-field annotation stamping', () => {
  it('stamps only the edited field on the user path', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoAnnotations(p, 'a', { personalNote: 'hi' }, []);
    const idx = await localMetadataStore.readIndex(p);
    const rec = idx.videos.find((x) => x.id === 'a')!;
    expect(rec.annotationsEditedAt?.personalNote).toBeDefined();
    expect(rec.annotationsEditedAt?.personalScore).toBeUndefined();
  });

  it('writes the SOURCE timestamp on the sync path (opts.editedAt), not now()', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoAnnotations(p, 'a', { personalNote: 'hi' }, [], { editedAt: '2020-01-01T00:00:00.000Z' });
    const idx = await localMetadataStore.readIndex(p);
    expect(idx.videos.find((x) => x.id === 'a')!.annotationsEditedAt?.personalNote).toBe('2020-01-01T00:00:00.000Z');
  });

  it('a clear stamps the timestamp and removes the value', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, { ...v('a'), personalNote: 'old' });
    await localMetadataStore.updateVideoAnnotations(p, 'a', {}, ['personalNote'], { editedAt: '2021-01-01T00:00:00.000Z' });
    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
    expect(rec.personalNote).toBeUndefined();
    expect(rec.annotationsEditedAt?.personalNote).toBe('2021-01-01T00:00:00.000Z');
  });

  // PRODUCTION PATH: local personalNote/corrections edits flow through updateVideoFields
  // (the review + regenerate routes), NOT updateVideoAnnotations (shape-parity only —
  // local-metadata-store.ts:62-66). This is where the stamp must actually live.
  it('updateVideoFields stamps annotationsEditedAt for a Class-B field (corrections)', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoFields(p, 'a', { corrections: 'fix' });
    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
    expect(rec.corrections).toBe('fix');
    expect(rec.annotationsEditedAt?.corrections).toBeDefined();
  });
  it('updateVideoFields does NOT stamp annotationsEditedAt for a non-Class-B field', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
    expect(rec.annotationsEditedAt).toBeUndefined();
  });

  // The sync loser-write path for corrections goes through updateVideoAnnotations — its allowlist
  // must include 'corrections' or the value is silently dropped (round-2 N3).
  it('updateVideoAnnotations allowlists corrections and stamps it with the source ts', async () => {
    const root = await tmpRoot();
    const p = localPrincipal(root);
    await localMetadataStore.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PL1' });
    await localMetadataStore.upsertVideo(p, v('a'));
    await localMetadataStore.updateVideoAnnotations(p, 'a', { corrections: 'fix' }, [], { editedAt: '2022-01-01T00:00:00.000Z' });
    const rec = (await localMetadataStore.readIndex(p)).videos.find((x) => x.id === 'a')!;
    expect(rec.corrections).toBe('fix');
    expect(rec.annotationsEditedAt?.corrections).toBe('2022-01-01T00:00:00.000Z');
  });
});
