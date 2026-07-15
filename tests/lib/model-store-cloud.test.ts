import { ModelEnvelopeSchema, readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

const P: Principal = { id: 'owner-1', indexKey: 'pk-1' };
const envelope = {
  sourceMd: 'a.md', generatedAt: '2026-07-09T00:00:00.000Z', sourceSections: ['A'],
  generatorVersion: 'magazine-skim v2',
  model: { sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] },
};

function fakeStore(): BlobStore & { blobs: Map<string, Buffer> } {
  const blobs = new Map<string, Buffer>();
  const k = (p: Principal, key: string) => `${p.id}/${p.indexKey}/${key}`;
  return {
    blobs,
    async put(p, key, bytes) { blobs.set(k(p, key), bytes); },
    async get(p, key) { return blobs.get(k(p, key)) ?? null; },
    async exists(p, key) { return blobs.has(k(p, key)); },
    async delete(p, key) { blobs.delete(k(p, key)); },
    async deletePrefix(p, prefix) {
      const pfx = k(p, prefix).replace(/\/$/, '');
      for (const key of [...blobs.keys()]) {
        if (key === pfx || key.startsWith(`${pfx}/`)) blobs.delete(key);
      }
    },
    async putStaged(p, key, bytes): Promise<StagedRef> { const tempKey = `_staging/uuid/${key}`; blobs.set(k(p, tempKey), bytes); return { principal: p, tempKey, finalKey: key }; },
    async promote(ref) { const from = k(ref.principal, ref.tempKey); const to = k(ref.principal, ref.finalKey); const b = blobs.get(from)!; blobs.set(to, b); blobs.delete(from); },
    async list() { return []; },
  };
}

it('schema accepts generatorVersion', () => {
  expect(ModelEnvelopeSchema.safeParse(envelope).success).toBe(true);
});

it('writeModelEnvelope (plain put) round-trips under a cloud principal', async () => {
  const store = fakeStore();
  await writeModelEnvelope(P, 'a', envelope, store);
  expect(store.blobs.has('owner-1/pk-1/models/a.json')).toBe(true);
  const read = await readModelEnvelope(P, 'a', store);
  expect(read?.generatorVersion).toBe('magazine-skim v2');
});

it('writeModelEnvelope overwrites an existing final via upsert (put, no staging)', async () => {
  const store = fakeStore();
  const promote = jest.spyOn(store, 'promote');
  await writeModelEnvelope(P, 'a', envelope, store);
  await writeModelEnvelope(P, 'a', { ...envelope, generatorVersion: 'magazine-skim v3' }, store); // overwrites
  const read = await readModelEnvelope(P, 'a', store);
  expect(read?.generatorVersion).toBe('magazine-skim v3'); // last write wins (upsert)
  expect(promote).not.toHaveBeenCalled();                  // no staging path for the model
  expect([...store.blobs.keys()].some((x) => x.includes('_staging'))).toBe(false);
});

it('readModelEnvelope returns null for a schema-invalid envelope (treated as absent)', async () => {
  const store = fakeStore();
  await store.put(P, 'models/a.json', Buffer.from('{"bad":true}'), 'application/json');
  expect(await readModelEnvelope(P, 'a', store)).toBeNull();
});
