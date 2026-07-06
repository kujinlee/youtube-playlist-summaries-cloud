import fs from 'fs';
import os from 'os';
import path from 'path';
import crypto from 'crypto';
import { writeModelEnvelope, readModelEnvelope, type ModelEnvelope } from '../../../lib/html-doc/model-store';
import { localPrincipal } from '@/lib/storage/principal';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';

let dir: string;
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
});
afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

describe('model-store', () => {
  it('writes models/<base>.json and reads it back (round-trip)', async () => {
    await writeModelEnvelope(dir, BASE, ENVELOPE);
    const p = path.join(dir, 'models', 'a-title.json');
    expect(fs.existsSync(p)).toBe(true);
    expect(await readModelEnvelope(dir, BASE)).toEqual(ENVELOPE);
  });

  it('creates the models/ directory if absent and leaves no temp file', async () => {
    await writeModelEnvelope(dir, BASE, ENVELOPE);
    const files = fs.readdirSync(path.join(dir, 'models'));
    expect(files).toEqual(['a-title.json']); // no .tmp leftovers
  });

  it('returns null and does NOT warn when the model file is absent', async () => {
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    expect(await readModelEnvelope(dir, 'missing')).toBeNull();
    expect(warn).not.toHaveBeenCalled();
    warn.mockRestore();
  });

  it('returns null on malformed JSON (and warns)', async () => {
    fs.mkdirSync(path.join(dir, 'models'), { recursive: true });
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    fs.writeFileSync(path.join(dir, 'models', 'bad.json'), '{ not json', 'utf-8');
    expect(await readModelEnvelope(dir, 'bad')).toBeNull();
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('returns null (and warns) when the envelope fails schema validation', async () => {
    fs.mkdirSync(path.join(dir, 'models'), { recursive: true });
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const bad = { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['s'], model: { sections: [{ lead: 'l', bullets: [] }] } };
    fs.writeFileSync(path.join(dir, 'models', 'bad2.json'), JSON.stringify(bad), 'utf-8');
    expect(await readModelEnvelope(dir, 'bad2')).toBeNull();
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('throws when asked to write an invalid model (write-time validation)', async () => {
    const invalid = {
      sourceMd: 'a-title.md', generatedAt: 'now', sourceSections: ['s'],
      model: { sections: [{ lead: 'l', bullets: [{ label: 'A', text: 'a' }] }] }, // <3 bullets
    } as unknown as ModelEnvelope;
    await expect(writeModelEnvelope(dir, BASE, invalid)).rejects.toThrow();
    expect(fs.existsSync(path.join(dir, 'models', 'a-title.json'))).toBe(false);
  });

  it('routes write through blobStore.put with key models/<base>.json', async () => {
    const fakePut = jest.fn(async (_p: unknown, _k: unknown, _b: unknown, _c: unknown) => {});
    const fakeBlobStore = Object.assign(Object.create(Object.getPrototypeOf(localBlobStore)), localBlobStore, { put: fakePut }) as typeof localBlobStore;
    await writeModelEnvelope(dir, BASE, ENVELOPE, fakeBlobStore);
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
    const result = await readModelEnvelope(dir, BASE, fakeBlobStore);
    expect(fakeGet).toHaveBeenCalledWith(localPrincipal(dir), 'models/a-title.json');
    expect(result).toEqual(ENVELOPE);
  });
});
