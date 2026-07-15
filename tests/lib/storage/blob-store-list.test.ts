import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
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
