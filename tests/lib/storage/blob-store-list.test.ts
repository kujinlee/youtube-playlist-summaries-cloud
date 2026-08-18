import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { encodeSegment } from '@/lib/storage/supabase/encode-segment';
import type { Principal } from '@/lib/storage/principal';
import fs from 'fs';
import os from 'os';
import path from 'path';

describe('localBlobStore.list', () => {
  let dir: string;
  let p: Principal;
  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), 'bloblist-'));
    p = { id: 'owner', indexKey: dir } as Principal;
  });
  afterEach(() => fs.rmSync(dir, { recursive: true, force: true }));

  it('returns logical keys under a prefix', async () => {
    await localBlobStore.put(p, 'dig/base/65.r3.md', Buffer.from('a'), 'text/markdown');
    await localBlobStore.put(p, 'dig/base/120.r3.md', Buffer.from('b'), 'text/markdown');
    await localBlobStore.put(p, 'models/base.json', Buffer.from('{}'), 'application/json');
    const keys = await localBlobStore.list(p, 'dig/base/');
    expect(keys.sort()).toEqual(['dig/base/120.r3.md', 'dig/base/65.r3.md']);
  });

  it('returns [] for an absent prefix', async () => {
    expect(await localBlobStore.list(p, 'dig/nope/')).toEqual([]);
  });
});

// The production path — the tenant-isolation seam (spec §11.2: cross-tenant enumeration is the
// worst-case leak). Mock Supabase Storage `.list`; assert enumeration is scoped to THIS owner's
// root and the returned keys are logical (owner root fully stripped, never leaked).
describe('SupabaseBlobStore.list (owner-scoped)', () => {
  function fakeClient(entriesByDir: Record<string, Array<{ name: string; id: string | null }>>) {
    const list = jest.fn(async (dirPath: string) => ({ data: entriesByDir[dirPath] ?? [], error: null }));
    return { client: { storage: { from: () => ({ list }) } }, list };
  }

  it('lists under the owner root, recurses folders, returns logical keys only', async () => {
    const p = { id: 'owner1', indexKey: 'pl-key' } as Principal;
    const root = 'owner1/pl-key/dig/base';
    const { client, list } = fakeClient({
      [root]: [{ name: '65.r9.md', id: 'f1' }, { name: 'nested', id: null }], // folder → recurse
      [`${root}/nested`]: [{ name: '120.r9.md', id: 'f2' }],
    });
    const store = new SupabaseBlobStore(client as never, 'artifacts');
    const keys = await store.list(p, 'dig/base/');
    expect(keys.sort()).toEqual(['dig/base/65.r9.md', 'dig/base/nested/120.r9.md']); // owner root stripped
    expect(list).toHaveBeenCalledWith('owner1/pl-key/dig/base', expect.anything()); // scoped to this owner
    for (const k of keys) expect(k.startsWith('owner1/')).toBe(false); // no owner id leaks into a logical key
  });

  it('returns [] for an absent prefix (every dir empty)', async () => {
    const p = { id: 'o', indexKey: 'k' } as Principal;
    const { client } = fakeClient({});
    const store = new SupabaseBlobStore(client as never, 'artifacts');
    expect(await store.list(p, 'dig/nope/')).toEqual([]);
  });
});

// Backlog #36, plan T2 — the encoder wired into the seam. Behaviors 8, 9, 10, 11, 12.
//
// ⛔ Round-2 H7. An earlier draft faked `store.list` itself, so the code under test never ran and
// these behaviors would have passed against a fixture. The helper below fakes the CLIENT and injects
// it into a REAL SupabaseBlobStore — generalising fakeClient above, which already has that shape.
describe('SupabaseBlobStore — logical/physical encoding (spec 3.1, 3.3)', () => {
  /** Holds LOGICAL keys. Builds the PHYSICAL directory layout by running the encoder over each
   *  segment — the same function `list` uses — and wires it into a real SupabaseBlobStore.
   *
   *  The keys are LOGICAL, not physical, and that distinction is the whole test: behaviors 8/12's
   *  fixture `dig/003_한국어/s1.r2.md` lives at the physical dir `dig/003_=h…/`, so a fake holding
   *  PHYSICAL paths would make `list` trivially return what it was handed. Asserted below. */
  function fakeStoreHolding(p: Principal, logicalKeys: string[]) {
    const byDir: Record<string, Array<{ name: string; id: string | null }>> = {};
    const removed: string[] = [];
    const ownerRoot = `${p.id}/${p.indexKey}`;
    for (const logical of logicalKeys) {
      const physical = logical.split('/').map(encodeSegment);
      let dir = ownerRoot;
      physical.forEach((seg, i) => {
        const leaf = i === physical.length - 1;
        (byDir[dir] ??= []);
        if (!byDir[dir].some((e) => e.name === seg)) byDir[dir].push({ name: seg, id: leaf ? 'f' : null });
        dir = `${dir}/${seg}`;
      });
    }
    const uploaded: string[] = [];
    const client = { storage: { from: () => ({
      list: async (dirPath: string) => ({ data: byDir[dirPath] ?? [], error: null }),
      remove: async (paths: string[]) => { removed.push(...paths); return { error: null }; },
      upload: async (path: string) => { uploaded.push(path); return { error: null }; },
    }) } };
    return { store: new SupabaseBlobStore(client as never, 'artifacts'), byDir, removed, uploaded };
  }

  const P = { id: 'owner1', indexKey: 'pl-key' } as Principal;

  it('behavior 8 + 12 — returns LOGICAL keys, and a trailing slash is optional', async () => {
    const base = '003_한국어';
    const { store, byDir } = fakeStoreHolding(P, [`dig/${base}/s1.r2.md`]);
    // the fake is not the subject: the layout it built is the ENCODED one
    expect(Object.keys(byDir)).toContain(`owner1/pl-key/dig/${encodeSegment(base)}`);
    expect(Object.keys(byDir)).not.toContain(`owner1/pl-key/dig/${base}`);
    expect(await store.list(P, `dig/${base}/`)).toEqual([`dig/${base}/s1.r2.md`]);
    expect(await store.list(P, `dig/${base}`)).toEqual([`dig/${base}/s1.r2.md`]);
  });

  it('behavior 9 — throws when a physical REMAINDER segment cannot be named', async () => {
    // Hand-built: the LEAF carries a marker the caller did not supply, which is unmappable.
    const byDir = { 'owner1/pl-key/dig/003_x': [{ name: 'lost=hABCDEFGHIJKLMNOPQRSTUV.md', id: 'f' }] };
    const client = { storage: { from: () => ({
      list: async (d: string) => ({ data: (byDir as Record<string, unknown[]>)[d] ?? [], error: null }),
    }) } };
    const store = new SupabaseBlobStore(client as never, 'artifacts');
    await expect(store.list(P, 'dig/003_x/')).rejects.toThrow(/cannot be mapped back/i);
  });

  it("behavior 10 — does NOT throw when the CALLER's own prefix contains `=`", async () => {
    // The marker guard applies to the physical REMAINDER only. Applying it to the caller's
    // prefix strands a video on every run.
    const { store } = fakeStoreHolding(P, ['dig/003_a=b/s1.r2.md']);
    await expect(store.list(P, 'dig/003_a=b/')).resolves.toEqual(['dig/003_a=b/s1.r2.md']);
  });

  it('an EMPTY prefix behaves exactly as it does today', async () => {
    const { store } = fakeStoreHolding(P, ['003_x.md', 'dig/003_x/s1.r2.md']);
    expect((await store.list(P, '')).sort()).toEqual(['003_x.md', 'dig/003_x/s1.r2.md']);
  });

  it('objectKey encodes PER SEGMENT, keeps the owner prefix, and keeps the traversal guard', async () => {
    // `objectKey` is PRIVATE, so it is exercised through `put`, the public method that reveals the
    // physical path it built. Round-1 B2 was exactly a lost owner prefix and a dropped traversal
    // guard, and neither is observable from `list`.
    const { store, uploaded } = fakeStoreHolding(P, []);
    await store.put(P, '003_한국어.md', Buffer.from('x'), 'text/markdown');
    expect(uploaded[0]).toBe(`owner1/pl-key/${encodeSegment('003_한국어.md')}`);
    expect(uploaded[0]).toMatch(/^[A-Za-z0-9._=/-]+$/);              // the physical path is ASCII

    await store.put(P, 'dig/003_한국어/s1.r2.md', Buffer.from('x'), 'text/markdown');
    expect(uploaded[1]).toBe(`owner1/pl-key/dig/${encodeSegment('003_한국어')}/s1.r2.md`);

    await store.put(P, '003_intro.md', Buffer.from('x'), 'text/markdown');
    expect(uploaded[2]).toBe('owner1/pl-key/003_intro.md');          // a SAFE key is IDENTITY

    await expect(store.put(P, '../x.md', Buffer.from('x'), 'text/markdown'))
      .rejects.toMatchObject({ statusCode: 400 });                   // assertLogicalKey survives
    expect(uploaded).toHaveLength(3);                                // and it uploaded nothing
  });

  it('behavior 11 — deletePrefix encodes the prefix it walks', async () => {
    const all = fakeStoreHolding(P, ['003_한국어.md', 'dig/003_한국어/s1.r2.md']);
    await all.store.deletePrefix(P, '');
    expect(all.removed).toHaveLength(2);                 // the whole playlist root
    const one = fakeStoreHolding(P, ['dig/003_한국어/s1.r2.md']);
    await one.store.deletePrefix(P, 'dig/003_한국어/');
    expect(one.removed).toHaveLength(1);                 // reached an ENCODED dir from a logical prefix
  });
});
