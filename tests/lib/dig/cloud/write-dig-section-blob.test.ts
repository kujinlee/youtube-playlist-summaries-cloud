import { writeDigSectionBlob } from '@/lib/dig/cloud/write-dig-section-blob';
import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import type { StagedRef } from '@/lib/storage/blob-store';

function fakeBlobStore() {
  const calls: string[] = [];
  const staged = new Map<string, Buffer>();
  return {
    calls,
    put: jest.fn(),
    get: jest.fn(),
    delete: jest.fn(),
    exists: jest.fn(async (_p: unknown, k: string) => { calls.push(`exists:${k}`); return staged.has(k); }),
    putStaged: jest.fn(async (principal: unknown, key: string, bytes: Buffer): Promise<StagedRef> => {
      const tempKey = `${key}.staging`; staged.set(tempKey, bytes); calls.push(`putStaged:${key}`);
      return { principal: principal as any, tempKey, finalKey: key };
    }),
    promote: jest.fn(async (ref: StagedRef) => { calls.push(`promote:${ref.finalKey}`); }),
  };
}

const principal = { id: 'u1', indexKey: 'PLxyz' };

it('writes the per-section doc via staged→promote and returns the key', async () => {
  const bs = fakeBlobStore();
  const key = await writeDigSectionBlob({
    blobStore: bs as any, principal, base: '0007_intro', videoId: 'vid1', sectionId: 132,
    startSec: 132, title: 'Encoder attention', language: 'en',
    sourceVideoUrl: 'https://youtu.be/vid1?t=132',
    bodyMarkdown: 'Prose. [[SLIDE:2:12|2:20|heat-map]] More prose.\n', generatedAt: '2026-07-12T18:04:11.522Z',
  });
  expect(key).toBe(`dig/0007_intro/132.r${DIG_GENERATOR_VERSION}.md`);
  // staged before promote, and exists() verified the staged blob between them
  expect(bs.calls).toEqual([
    `putStaged:${key}`, `exists:${key}.staging`, `promote:${key}`,
  ]);
  const written = (bs.putStaged.mock.calls[0][2] as Buffer).toString('utf-8');
  expect(written).toContain('slides: []');
  expect(written).toContain(`genVersion: ${DIG_GENERATOR_VERSION}`);
  expect(written).toContain('sectionId: 132');
  expect(written).toContain('[[SLIDE:2:12|2:20|heat-map]]'); // token preserved verbatim, NOT resolved/stripped
});

it('throws if the staged upload cannot be verified (no promote)', async () => {
  const bs = fakeBlobStore();
  bs.exists = jest.fn(async (_p: unknown, _k: string) => false);
  await expect(writeDigSectionBlob({
    blobStore: bs as any, principal, base: 'b', videoId: 'v', sectionId: 1, startSec: 1,
    title: 't', language: 'en', sourceVideoUrl: 'u', bodyMarkdown: 'x', generatedAt: 'now',
  })).rejects.toThrow(/staged dig upload not verified/);
  expect(bs.promote).not.toHaveBeenCalled();
});
