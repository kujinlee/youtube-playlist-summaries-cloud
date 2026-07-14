import {
  writeArtifact,
  resolveMissing,
  isSourceKind,
  type ArtifactKind,
} from '@/lib/storage/supabase/consistency';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';

// ---------------------------------------------------------------------------
// isSourceKind
// ---------------------------------------------------------------------------
describe('isSourceKind', () => {
  test.each<ArtifactKind>(['summaryMd', 'slide', 'modelJson'])('%s is a source kind', (k) => {
    expect(isSourceKind(k)).toBe(true);
  });

  test.each<ArtifactKind>(['html', 'pdf'])('%s is NOT a source kind', (k) => {
    expect(isSourceKind(k)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Mock helpers
// ---------------------------------------------------------------------------

const p: Principal = { id: 'owner-1', indexKey: 'listX' };

/**
 * Creates a mock BlobStore that records call order and allows controlling
 * the result of exists().
 */
function makeMockBlob(opts: { tempExists?: boolean } = {}) {
  const order: string[] = [];
  let stagedRef: StagedRef | null = null;

  const blob: BlobStore = {
    async put() {},
    async get() { return null; },
    async exists(_p, key) {
      order.push(`exists(${key})`);
      // Return true for the temp key to simulate successful staging
      return opts.tempExists !== false;
    },
    async delete() {},
    async deletePrefix() {},
    async list() { return []; },
    async putStaged(principal, key, _bytes, _contentType) {
      order.push('putStaged');
      stagedRef = { principal, tempKey: `_staging/${key}`, finalKey: key };
      return stagedRef;
    },
    async promote(ref) {
      order.push(`promote(${ref.finalKey})`);
    },
  };

  return { blob, order, getStagedRef: () => stagedRef };
}

/**
 * Creates a mock MetadataStore that records updateVideoFields calls in order.
 */
function makeMockMeta() {
  const order: string[] = [];
  const calls: Array<{ id: string; fields: unknown }> = [];

  const meta: Pick<MetadataStore, 'updateVideoFields'> = {
    async updateVideoFields(_p, id, fields) {
      const status = (fields as any)?.artifacts;
      const statusStr = status ? JSON.stringify(status) : '';
      order.push(`updateVideoFields(${id},${statusStr})`);
      calls.push({ id, fields });
    },
  };

  return { meta: meta as MetadataStore, order, calls };
}

// ---------------------------------------------------------------------------
// writeArtifact — ordered-write sequence
// ---------------------------------------------------------------------------
describe('writeArtifact', () => {
  test('follows ordered sequence: putStaged → exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)', async () => {
    const { blob, order: blobOrder } = makeMockBlob();
    const { meta, order: metaOrder } = makeMockMeta();

    // Interleave blob and meta calls into one ordered log
    const combined: string[] = [];
    const origPutStaged = blob.putStaged.bind(blob);
    const origExists = blob.exists.bind(blob);
    const origPromote = blob.promote.bind(blob);
    const origUpdateVideoFields = meta.updateVideoFields.bind(meta);

    blob.putStaged = async (...args) => { combined.push('putStaged'); return origPutStaged(...args); };
    blob.exists = async (...args) => { combined.push('exists'); return origExists(...args); };
    blob.promote = async (...args) => { combined.push('promote'); return origPromote(...args); };
    meta.updateVideoFields = async (...args) => {
      const fields = args[2] as any;
      const status = fields?.artifacts ? Object.values(fields.artifacts)[0] as any : null;
      combined.push(`updateVideoFields(${status?.status ?? '?'})`);
      return origUpdateVideoFields(...args);
    };

    await writeArtifact({
      meta,
      blob,
      principal: p,
      videoId: 'vid-1',
      kind: 'summaryMd',
      key: 'summaries/vid-1.md',
      bytes: Buffer.from('content'),
      contentType: 'text/markdown',
    });

    expect(combined).toEqual([
      'putStaged',
      'exists',
      'updateVideoFields(committed)',
      'promote',
      'updateVideoFields(promoted)',
    ]);
  });

  test('passes correct key and status to updateVideoFields', async () => {
    const { blob } = makeMockBlob();
    const { meta, calls } = makeMockMeta();

    await writeArtifact({
      meta,
      blob,
      principal: p,
      videoId: 'vid-2',
      kind: 'slide',
      key: 'slides/vid-2.html',
      bytes: Buffer.from('<html>'),
      contentType: 'text/html',
    });

    expect(calls).toHaveLength(2);
    const [committed, promoted] = calls;
    expect((committed.fields as any).artifacts.slide.key).toBe('slides/vid-2.html');
    expect((committed.fields as any).artifacts.slide.status).toBe('committed');
    expect((promoted.fields as any).artifacts.slide.status).toBe('promoted');
  });

  test('throws if staged upload is not verified (exists returns false)', async () => {
    const { blob } = makeMockBlob({ tempExists: false });
    const { meta } = makeMockMeta();

    await expect(writeArtifact({
      meta,
      blob,
      principal: p,
      videoId: 'vid-3',
      kind: 'summaryMd',
      key: 'summaries/vid-3.md',
      bytes: Buffer.from('x'),
      contentType: 'text/markdown',
    })).rejects.toThrow('staged upload not verified');
  });

  test('calls exists with the temp key from putStaged', async () => {
    const { blob } = makeMockBlob();
    const { meta } = makeMockMeta();

    // Intercept exists to capture what key was passed
    let existsKey: string | null = null;
    const origExists = blob.exists.bind(blob);
    blob.exists = async (principal, key) => { existsKey = key; return origExists(principal, key); };

    await writeArtifact({
      meta,
      blob,
      principal: p,
      videoId: 'vid-4',
      kind: 'html',
      key: 'html/vid-4.html',
      bytes: Buffer.from('<html>'),
      contentType: 'text/html',
    });

    expect(existsKey).toBe('_staging/html/vid-4.html');
  });
});

// ---------------------------------------------------------------------------
// resolveMissing
// ---------------------------------------------------------------------------
describe('resolveMissing', () => {
  test('source kind → markRepair called, regenerate NOT called, returns repair_needed', async () => {
    const markRepair = jest.fn().mockResolvedValue(undefined);
    const regenerate = jest.fn().mockResolvedValue(undefined);

    const result = await resolveMissing({ kind: 'summaryMd', regenerate, markRepair });

    expect(result).toBe('repair_needed');
    expect(markRepair).toHaveBeenCalledTimes(1);
    expect(regenerate).not.toHaveBeenCalled();
  });

  test('slide (source kind) → markRepair called, returns repair_needed', async () => {
    const markRepair = jest.fn().mockResolvedValue(undefined);
    const regenerate = jest.fn().mockResolvedValue(undefined);

    const result = await resolveMissing({ kind: 'slide', regenerate, markRepair });

    expect(result).toBe('repair_needed');
    expect(markRepair).toHaveBeenCalledTimes(1);
    expect(regenerate).not.toHaveBeenCalled();
  });

  test('modelJson (source kind) → markRepair called, returns repair_needed', async () => {
    const markRepair = jest.fn().mockResolvedValue(undefined);
    const regenerate = jest.fn().mockResolvedValue(undefined);

    const result = await resolveMissing({ kind: 'modelJson', regenerate, markRepair });

    expect(result).toBe('repair_needed');
    expect(markRepair).toHaveBeenCalledTimes(1);
    expect(regenerate).not.toHaveBeenCalled();
  });

  test('cache kind (html) → regenerate called, markRepair NOT called, returns regenerated', async () => {
    const markRepair = jest.fn().mockResolvedValue(undefined);
    const regenerate = jest.fn().mockResolvedValue(undefined);

    const result = await resolveMissing({ kind: 'html', regenerate, markRepair });

    expect(result).toBe('regenerated');
    expect(regenerate).toHaveBeenCalledTimes(1);
    expect(markRepair).not.toHaveBeenCalled();
  });

  test('cache kind (pdf) → regenerate called, returns regenerated', async () => {
    const markRepair = jest.fn().mockResolvedValue(undefined);
    const regenerate = jest.fn().mockResolvedValue(undefined);

    const result = await resolveMissing({ kind: 'pdf', regenerate, markRepair });

    expect(result).toBe('regenerated');
    expect(regenerate).toHaveBeenCalledTimes(1);
    expect(markRepair).not.toHaveBeenCalled();
  });
});
