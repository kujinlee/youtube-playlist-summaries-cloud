import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { localPrincipal } from '@/lib/storage/principal';

// ---------------------------------------------------------------------------
// Mock storage builder
// ---------------------------------------------------------------------------

/**
 * Builds a minimal mock of the Supabase Storage bucket interface, recording
 * every upload, download, remove, and move call.
 */
function mockStorage(overrides: {
  downloadError?: boolean;
  removeError?: boolean;
  moveError?: boolean;
  uploadError?: boolean;
} = {}) {
  const calls: Array<{ method: string; args: unknown[] }> = [];
  let lastUpload: { path: string; body: unknown; opts: unknown } | null = null;
  let lastDownload: { path: string } | null = null;
  let lastRemove: { paths: string[] } | null = null;
  let lastMove: { from: string; to: string } | null = null;

  const bucket = {
    calls,
    get lastUpload() { return lastUpload; },
    get lastDownload() { return lastDownload; },
    get lastRemove() { return lastRemove; },
    get lastMove() { return lastMove; },

    upload(path: string, body: unknown, opts: unknown) {
      calls.push({ method: 'upload', args: [path, body, opts] });
      lastUpload = { path, body, opts };
      const error = overrides.uploadError ? new Error('upload failed') : null;
      return Promise.resolve({ data: error ? null : {}, error });
    },

    download(path: string) {
      calls.push({ method: 'download', args: [path] });
      lastDownload = { path };
      if (overrides.downloadError) {
        return Promise.resolve({ data: null, error: new Error('not found') });
      }
      const bytes = Buffer.from('hello');
      // Return a minimal Blob-like with arrayBuffer()
      const data = { arrayBuffer: () => Promise.resolve(bytes.buffer) };
      return Promise.resolve({ data, error: null });
    },

    remove(paths: string[]) {
      calls.push({ method: 'remove', args: [paths] });
      lastRemove = { paths };
      const error = overrides.removeError ? new Error('remove failed') : null;
      return Promise.resolve({ data: null, error });
    },

    move(from: string, to: string) {
      calls.push({ method: 'move', args: [from, to] });
      lastMove = { from, to };
      const error = overrides.moveError ? new Error('move failed') : null;
      return Promise.resolve({ data: null, error });
    },
  };

  return bucket;
}

function clientWith(bucket: ReturnType<typeof mockStorage>) {
  return {
    storage: {
      from(_bucketName: string) { return bucket; },
    },
  };
}

const p = localPrincipal('listX');  // id='local', indexKey='listX'

// ---------------------------------------------------------------------------
// put — object key derivation
// ---------------------------------------------------------------------------
describe('put', () => {
  test('object key is <owner>/<indexKey>/<logicalKey>', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.put({ id: 'owner-1', indexKey: 'listX' }, 'a/b.md', Buffer.from('x'), 'text/markdown');
    expect(storage.lastUpload!.path).toBe('owner-1/listX/a/b.md');
  });

  test('uploaded with upsert:true and correct contentType', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.put(p, 'docs/readme.md', Buffer.from('y'), 'text/plain');
    expect((storage.lastUpload!.opts as any).upsert).toBe(true);
    expect((storage.lastUpload!.opts as any).contentType).toBe('text/plain');
  });

  test('throws on upload error', async () => {
    const storage = mockStorage({ uploadError: true });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await expect(store.put(p, 'x.md', Buffer.from('x'), 'text/markdown')).rejects.toThrow('upload failed');
  });

  test('rejects absolute key', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await expect(store.put(p, '/abs/key.md', Buffer.from('x'), 'text/markdown')).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// get — null on 404
// ---------------------------------------------------------------------------
describe('get', () => {
  test('returns Buffer on success', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    const result = await store.get(p, 'docs/file.md');
    expect(result).toBeInstanceOf(Buffer);
  });

  test('returns null when storage returns an error (404)', async () => {
    const storage = mockStorage({ downloadError: true });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    const result = await store.get(p, 'docs/missing.md');
    expect(result).toBeNull();
  });

  test('downloads from correct object key', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.get({ id: 'owner-1', indexKey: 'listX' }, 'nested/file.md');
    expect(storage.lastDownload!.path).toBe('owner-1/listX/nested/file.md');
  });
});

// ---------------------------------------------------------------------------
// exists
// ---------------------------------------------------------------------------
describe('exists', () => {
  test('returns true when get returns Buffer', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    expect(await store.exists(p, 'file.md')).toBe(true);
  });

  test('returns false when get returns null', async () => {
    const storage = mockStorage({ downloadError: true });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    expect(await store.exists(p, 'file.md')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// delete
// ---------------------------------------------------------------------------
describe('delete', () => {
  test('removes the correct object key', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.delete({ id: 'owner-1', indexKey: 'listX' }, 'file.md');
    expect(storage.lastRemove!.paths).toEqual(['owner-1/listX/file.md']);
  });

  test('throws on remove error', async () => {
    const storage = mockStorage({ removeError: true });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await expect(store.delete(p, 'file.md')).rejects.toThrow('remove failed');
  });
});

// ---------------------------------------------------------------------------
// putStaged — staging key, returned ref
// ---------------------------------------------------------------------------
describe('putStaged', () => {
  test('uploads to _staging/<uuid>/<key> prefixed with owner/indexKey', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await store.putStaged({ id: 'owner-1', indexKey: 'listX' }, 'a/b.md', Buffer.from('x'), 'text/markdown');
    // object key = owner-1/listX/_staging/<uuid>/a/b.md — uuid-prefixed, per-attempt-unique
    expect(storage.lastUpload!.path).toMatch(/^owner-1\/listX\/_staging\/[0-9a-f-]{36}\/a\/b\.md$/);
  });

  test('returns StagedRef with correct tempKey and finalKey', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    const ref = await store.putStaged(p, 'my/file.md', Buffer.from('x'), 'text/plain');
    expect(ref.tempKey).toMatch(/^_staging\/[0-9a-f-]{36}\/my\/file\.md$/);
    expect(ref.finalKey).toBe('my/file.md');
    expect(ref.principal).toBe(p);
  });

  test('rejects absolute key before uploading', async () => {
    const storage = mockStorage();
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    await expect(store.putStaged(p, '/absolute/path.md', Buffer.from('x'), 'text/markdown')).rejects.toThrow();
    // Ensure upload was never called
    expect(storage.calls.filter((c) => c.method === 'upload')).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// promote — idempotency + move
// ---------------------------------------------------------------------------
describe('promote', () => {
  test('calls move with correct from and to object keys', async () => {
    // download returns null (final doesn't exist) → move should be called
    const storage = mockStorage({ downloadError: true });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    const ref = {
      principal: { id: 'owner-1', indexKey: 'listX' },
      tempKey: '_staging/a/b.md',
      finalKey: 'a/b.md',
    };
    await store.promote(ref);
    expect(storage.lastMove!.from).toBe('owner-1/listX/_staging/a/b.md');
    expect(storage.lastMove!.to).toBe('owner-1/listX/a/b.md');
  });

  test('idempotent: when final already exists, move is NOT called and temp is removed', async () => {
    // download succeeds → final exists; move should NOT be called
    const storage = mockStorage();  // downloadError: false → exists returns true
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    const ref = {
      principal: { id: 'owner-1', indexKey: 'listX' },
      tempKey: '_staging/a/b.md',
      finalKey: 'a/b.md',
    };
    await store.promote(ref);
    expect(storage.calls.filter((c) => c.method === 'move')).toHaveLength(0);
    // Temp should be best-effort removed
    expect(storage.calls.filter((c) => c.method === 'remove')).toHaveLength(1);
  });

  test('throws on move error', async () => {
    const storage = mockStorage({ downloadError: true, moveError: true });
    const store = new SupabaseBlobStore(clientWith(storage) as any, 'artifacts');
    const ref = {
      principal: p,
      tempKey: '_staging/file.md',
      finalKey: 'file.md',
    };
    await expect(store.promote(ref)).rejects.toThrow('move failed');
  });
});
