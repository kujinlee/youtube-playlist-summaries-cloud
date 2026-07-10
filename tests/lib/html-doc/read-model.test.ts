// NOTE on mocking technique: the plan's Step 1 draft used `jest.spyOn(modelStore, 'readModelEnvelope')`
// (a namespace-import spy). That throws `TypeError: Cannot redefine property` under this repo's
// SWC-compiled Jest transform (repro'd against the pre-existing, unmodified model-store.ts — not
// something this task introduced; no test in the repo uses that pattern). The repo's established
// convention for mocking a sibling lib module (see tests/lib/html-doc/serve-doc-mapping.test.ts) is a
// full `jest.mock(..., () => ({...}))` factory, used below. Assertions/interfaces are unchanged.
import { readFreshMagazineModel, isFresh } from '@/lib/html-doc/read-model';
import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';

jest.mock('@/lib/html-doc/model-store', () => ({ readModelEnvelope: jest.fn() }));
import { readModelEnvelope } from '@/lib/html-doc/model-store';
const mockReadModelEnvelope = readModelEnvelope as jest.Mock;

const principal = { id: 'owner-1', indexKey: 'pl-key' };
const fakeModel = { title: 'T', dek: 'd', sections: [] } as any;
const titles = ['A', 'B'];
const roStore: ReadOnlyBlobStore = { get: async () => null };

function envelope(over: Partial<any> = {}) {
  return { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A', 'B'],
    generatorVersion: GENERATOR_VERSION, model: fakeModel, ...over };
}

describe('isFresh', () => {
  it('true when titles match and version matches', () => {
    expect(isFresh(envelope(), titles)).toBe(true);
  });
  it('false when a title differs', () => {
    expect(isFresh(envelope({ sourceSections: ['A', 'C'] }), titles)).toBe(false);
  });
  it('false when generatorVersion differs', () => {
    expect(isFresh(envelope({ generatorVersion: 'old' }), titles)).toBe(false);
  });
});

describe('readFreshMagazineModel', () => {
  afterEach(() => mockReadModelEnvelope.mockReset());

  it('returns ok with the model when a fresh envelope exists', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope());
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'ok', model: fakeModel });
  });

  it('returns not_ready when the envelope is absent', async () => {
    mockReadModelEnvelope.mockResolvedValue(null);
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });

  it('returns not_ready when the envelope is stale (version bump)', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope({ generatorVersion: 'old' }));
    const r = await readFreshMagazineModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'not_ready' });
  });
});

import { readFileSync } from 'fs';
import { join } from 'path';

describe('B18c — read-model.ts is a generate-free leaf', () => {
  it('imports nothing that could charge or generate', () => {
    const src = readFileSync(join(process.cwd(), 'lib/html-doc/read-model.ts'), 'utf-8');
    const imports = [...src.matchAll(/from ['"]([^'"]+)['"]/g)].map((m) => m[1]);
    for (const bad of ['@/lib/gemini', '@/lib/gemini-cost', './serve-doc', '@/lib/html-doc/serve-doc']) {
      expect(imports).not.toContain(bad);
    }
    // constants.ts (the GENERATOR_VERSION source) must itself import nothing.
    const consts = readFileSync(join(process.cwd(), 'lib/html-doc/constants.ts'), 'utf-8');
    expect(consts).not.toMatch(/\bimport\b/);
  });
});
