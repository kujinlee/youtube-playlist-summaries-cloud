// tests/lib/storage/blob-store-delete-prefix.test.ts
//
// Unit coverage for BlobStore.deletePrefix — both the Supabase (mocked storage
// client) and local (temp-dir fs) implementations. Covers: traversal rejection,
// empty-prefix root targeting, recursion into nested folders (dig/<base>/…),
// pagination past 100 entries, and tolerance of empty listings / absent paths.

import fs from 'fs'; import os from 'os'; import path from 'path';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { LocalFsBlobStore } from '@/lib/storage/local/local-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { Principal } from '@/lib/storage/principal';

// ---------------------------------------------------------------------------
// Supabase impl — mock storage client
// ---------------------------------------------------------------------------

type ListEntry = { name: string; id: string | null };
type ListImpl = (path: string, options: { limit: number; offset: number }) => { data: ListEntry[] | null; error: unknown };

function mockStorage(listImpl: ListImpl) {
  const listCalls: Array<{ path: string; options: { limit: number; offset: number } }> = [];
  const removeCalls: string[][] = [];

  const bucket = {
    listCalls,
    removeCalls,
    async list(p: string, options: { limit: number; offset: number }) {
      listCalls.push({ path: p, options });
      return listImpl(p, options);
    },
    async remove(paths: string[]) {
      removeCalls.push(paths);
      return { data: null, error: null };
    },
  };
  return bucket;
}

function clientWith(bucket: ReturnType<typeof mockStorage>) {
  return { storage: { from(_bucketName: string) { return bucket; } } };
}

const p: Principal = { id: 'owner-1', indexKey: 'listX' };

describe('SupabaseBlobStore.deletePrefix', () => {
  test('rejects traversal prefix before any storage op', async () => {
    const storage = mockStorage(() => ({ data: [], error: null }));
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await expect(store.deletePrefix(p, '..')).rejects.toThrow();
    await expect(store.deletePrefix(p, 'a/../b')).rejects.toThrow();
    expect(storage.listCalls).toHaveLength(0);
    expect(storage.removeCalls).toHaveLength(0);
  });

  test('empty prefix targets <owner>/<indexKey> root (no trailing slash)', async () => {
    const storage = mockStorage(() => ({ data: [], error: null }));
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.deletePrefix(p, '');
    expect(storage.listCalls[0].path).toBe('owner-1/listX');
  });

  test('recurses into nested dig/<base>/ folder and removes all objects', async () => {
    const storage = mockStorage((dirPath) => {
      if (dirPath === 'owner-1/listX') {
        return {
          data: [
            { name: 'base.md', id: 'file-1' },
            { name: 'base.pdf', id: 'file-2' },
            { name: 'dig', id: null }, // folder — non-recursive list surfaces it as id===null
          ],
          error: null,
        };
      }
      if (dirPath === 'owner-1/listX/dig') {
        return { data: [{ name: 'base', id: null }], error: null };
      }
      if (dirPath === 'owner-1/listX/dig/base') {
        return { data: [{ name: '0.r1.md', id: 'file-3' }], error: null };
      }
      return { data: [], error: null };
    });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.deletePrefix(p, '');

    const removed = storage.removeCalls.flat();
    expect(removed).toContain('owner-1/listX/base.md');
    expect(removed).toContain('owner-1/listX/base.pdf');
    expect(removed).toContain('owner-1/listX/dig/base/0.r1.md');
  });

  test('paginates past 100 objects: full page then short page, all removed', async () => {
    const fullPage: ListEntry[] = Array.from({ length: 100 }, (_, i) => ({ name: `f${i}.md`, id: `id-${i}` }));
    const shortPage: ListEntry[] = [{ name: 'f100.md', id: 'id-100' }];
    const storage = mockStorage((dirPath, options) => {
      expect(dirPath).toBe('owner-1/listX');
      if (options.offset === 0) return { data: fullPage, error: null };
      if (options.offset === 100) return { data: shortPage, error: null };
      return { data: [], error: null };
    });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.deletePrefix(p, '');

    // Two list calls: offset 0 (full page of 100) then offset 100 (short page ends pagination).
    expect(storage.listCalls.map((c) => c.options.offset)).toEqual([0, 100]);
    const removed = storage.removeCalls.flat();
    expect(removed).toHaveLength(101);
    expect(removed).toContain('owner-1/listX/f0.md');
    expect(removed).toContain('owner-1/listX/f100.md');
  });

  test('empty listing tolerated: resolves without throw, no remove call', async () => {
    const storage = mockStorage(() => ({ data: [], error: null }));
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await expect(store.deletePrefix(p, 'nope')).resolves.toBeUndefined();
    expect(storage.removeCalls).toHaveLength(0);
  });

  test('null data (no rows) tolerated: resolves without throw', async () => {
    const storage = mockStorage(() => ({ data: null, error: null }));
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await expect(store.deletePrefix(p, 'nope')).resolves.toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Local impl — real temp dir
// ---------------------------------------------------------------------------

describe('LocalFsBlobStore.deletePrefix', () => {
  const store = new LocalFsBlobStore();
  const p2 = () => localPrincipal(fs.mkdtempSync(path.join(os.tmpdir(), 'lbs-dp-')));

  afterEach(() => {
    const dirs = fs.readdirSync(os.tmpdir()).filter((d) => d.startsWith('lbs-dp-'));
    for (const d of dirs) fs.rmSync(path.join(os.tmpdir(), d), { recursive: true, force: true });
  });

  test('rejects traversal prefix', async () => {
    const pr = p2();
    await expect(store.deletePrefix(pr, '..')).rejects.toThrow();
    await expect(store.deletePrefix(pr, 'a/../../etc')).rejects.toThrow();
  });

  test('recursive removal of a nested sub-prefix', async () => {
    const pr = p2();
    await store.put(pr, 'dig/base/0.r1.md', Buffer.from('x'), 'text/markdown');
    await store.put(pr, 'dig/base/1.r1.md', Buffer.from('y'), 'text/markdown');
    expect(fs.existsSync(path.join(pr.indexKey, 'dig', 'base'))).toBe(true);

    await store.deletePrefix(pr, 'dig');

    expect(fs.existsSync(path.join(pr.indexKey, 'dig'))).toBe(false);
    // Playlist root itself is untouched by a sub-prefix delete.
    expect(fs.existsSync(pr.indexKey)).toBe(true);
  });

  test('ENOENT-safe: deleting an absent prefix resolves without throw', async () => {
    const pr = p2();
    await expect(store.deletePrefix(pr, 'never-existed')).resolves.toBeUndefined();
  });

  test("deletePrefix(p, '') removes exactly the indexKey dir (playlist root)", async () => {
    const pr = p2();
    await store.put(pr, 'base.md', Buffer.from('x'), 'text/markdown');
    expect(fs.existsSync(pr.indexKey)).toBe(true);

    await store.deletePrefix(pr, '');

    expect(fs.existsSync(pr.indexKey)).toBe(false);
    // Parent (os.tmpdir()) is untouched.
    expect(fs.existsSync(os.tmpdir())).toBe(true);
  });
});
