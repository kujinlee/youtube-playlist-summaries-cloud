import fs from 'fs';
import os from 'os';
import path from 'path';
import crypto from 'crypto';
import { writeModelEnvelope, writeModelEnvelopeWithin, readModelEnvelope, type ModelEnvelope } from '../../../lib/html-doc/model-store';
import { localPrincipal, type Principal } from '@/lib/storage/principal';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import { putBudget } from '../../support/budget';

let dir: string;
let principal: Principal;
const BASE = 'a-title';
const ENVELOPE: ModelEnvelope = {
  sourceMd: 'a-title.md',
  generatedAt: '2026-06-17T10:30:00.000Z',
  sourceSections: ['The Foundation'],
  model: {
    sections: [
      { lead: 'Lead one.', bullets: [
        { label: 'A', text: 'a' }, { label: 'B', text: 'b' }, { label: 'C', text: 'c' },
      ] },
    ],
  },
};

beforeEach(() => {
  dir = path.join(os.homedir(), `.tmp-modelstore-${crypto.randomUUID()}`);
  fs.mkdirSync(dir, { recursive: true });
  principal = localPrincipal(dir);
});
afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

describe('model-store', () => {
  it('writes models/<base>.json and reads it back (round-trip)', async () => {
    await writeModelEnvelope(principal, BASE, ENVELOPE);
    const p = path.join(dir, 'models', 'a-title.json');
    expect(fs.existsSync(p)).toBe(true);
    expect(await readModelEnvelope(principal, BASE)).toEqual(ENVELOPE);
  });

  it('creates the models/ directory if absent and leaves no temp file', async () => {
    await writeModelEnvelope(principal, BASE, ENVELOPE);
    const files = fs.readdirSync(path.join(dir, 'models'));
    expect(files).toEqual(['a-title.json']); // no .tmp leftovers
  });

  it('returns null and does NOT warn when the model file is absent', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    expect(await readModelEnvelope(principal, 'missing')).toBeNull();
    expect(warn).not.toHaveBeenCalled();
    warn.mockRestore();
  });

  it('returns null on malformed JSON (and warns)', async () => {
    fs.mkdirSync(path.join(dir, 'models'), { recursive: true });
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    fs.writeFileSync(path.join(dir, 'models', 'bad.json'), '{ not json', 'utf-8');
    expect(await readModelEnvelope(principal, 'bad')).toBeNull();
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('returns null (and warns) when the envelope fails schema validation', async () => {
    fs.mkdirSync(path.join(dir, 'models'), { recursive: true });
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const bad = { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['s'], model: { sections: [{ lead: 'l', bullets: [] }] } };
    fs.writeFileSync(path.join(dir, 'models', 'bad2.json'), JSON.stringify(bad), 'utf-8');
    expect(await readModelEnvelope(principal, 'bad2')).toBeNull();
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('throws when asked to write an invalid model (write-time validation)', async () => {
    const invalid = {
      sourceMd: 'a-title.md', generatedAt: 'now', sourceSections: ['s'],
      model: { sections: [{ lead: 'l', bullets: [{ label: 'A', text: 'a' }] }] }, // <3 bullets
    } as unknown as ModelEnvelope;
    await expect(writeModelEnvelope(principal, BASE, invalid)).rejects.toThrow();
    expect(fs.existsSync(path.join(dir, 'models', 'a-title.json'))).toBe(false);
  });

  it('routes write through blobStore.put with key models/<base>.json', async () => {
    const fakePut = jest.fn(async (_p: unknown, _k: unknown, _b: unknown, _c: unknown) => {});
    const fakeBlobStore = Object.assign(Object.create(Object.getPrototypeOf(localBlobStore)), localBlobStore, { put: fakePut }) as typeof localBlobStore;
    await writeModelEnvelope(principal, BASE, ENVELOPE, fakeBlobStore);
    expect(fakePut).toHaveBeenCalledWith(
      localPrincipal(dir),
      'models/a-title.json',
      expect.any(Buffer),
      'application/json',
    );
    // Verify the bytes are valid JSON matching the envelope
    const buf = fakePut.mock.calls[0]?.[2] as Buffer;
    expect(JSON.parse(buf.toString('utf-8'))).toEqual(ENVELOPE);
  });

  it('routes read through blobStore.get with key models/<base>.json', async () => {
    const bytes = Buffer.from(`${JSON.stringify(ENVELOPE, null, 2)}\n`, 'utf-8');
    const fakeGet = jest.fn(async () => bytes);
    const fakeBlobStore = Object.assign(Object.create(Object.getPrototypeOf(localBlobStore)), localBlobStore, { get: fakeGet }) as typeof localBlobStore;
    const result = await readModelEnvelope(principal, BASE, fakeBlobStore);
    expect(fakeGet).toHaveBeenCalledWith(localPrincipal(dir), 'models/a-title.json');
    expect(result).toEqual(ENVELOPE);
  });
});

describe('writeModelEnvelopeWithin', () => {
  /** Same construction as the fakeBlobStore above — preserves localBlobStore's prototype. */
  const storeWith = (put: BlobStore['put']) =>
    Object.assign(Object.create(Object.getPrototypeOf(localBlobStore)), localBlobStore, { put }) as typeof localBlobStore;

  it('rejects with TimeoutError when the put exceeds the budget', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const hanging = storeWith(() => new Promise<void>(() => {}));
    await expect(
      writeModelEnvelopeWithin(putBudget(20), principal, BASE, ENVELOPE, hanging),
    ).rejects.toMatchObject({ name: 'TimeoutError' });   // identity, not "any error"
    warn.mockRestore();
  });

  // Round-1 review H2. Spec §3.5.1 accepts the late-write clobber ONLY because the timeout is
  // "logged with elapsed time and the target key, so the window in which this is possible is
  // visible in production rather than inferred. If those logs ever appear, that is the trigger to
  // promote the addressing work." The first implementation logged nothing, so the residual was
  // accepted in exchange for a detection mechanism that did not exist — and `isFresh` ignores
  // sourceMdHash, so a clobbered model is served indefinitely when titles are unchanged.
  it('LOGS the timeout with elapsed time and the target key — the residual was traded for this', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const hanging = storeWith(() => new Promise<void>(() => {}));
    await expect(
      writeModelEnvelopeWithin(putBudget(20), principal, BASE, ENVELOPE, hanging),
    ).rejects.toMatchObject({ name: 'TimeoutError' });
    const logged = warn.mock.calls.map((c) => String(c[0])).join('\n');
    warn.mockRestore();
    expect(logged).toContain('models/a-title.json');   // the target key, so the doc is identifiable
    expect(logged).toMatch(/elapsed \d+ms/);           // elapsed time, so the window is measurable
  });

  it('resolves normally when the put completes within the budget', async () => {
    const put = jest.fn(async () => {});
    await writeModelEnvelopeWithin(putBudget(5_000), principal, BASE, ENVELOPE, storeWith(put));
    expect(put).toHaveBeenCalledTimes(1);
  });

  it('validates the envelope BEFORE writing', async () => {
    const put = jest.fn(async () => {});
    await expect(
      writeModelEnvelopeWithin(putBudget(5_000), principal, BASE, { ...ENVELOPE, sourceMd: '' } as never, storeWith(put)),
    ).rejects.toThrow();
    expect(put).not.toHaveBeenCalled();   // fail loud before any write, as writeModelEnvelope does
  });
});
