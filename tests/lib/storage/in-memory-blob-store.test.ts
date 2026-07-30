import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import { localPrincipal } from '@/lib/storage/principal';

const p = localPrincipal('/data/pl1');
const other = localPrincipal('/data/pl2');
const buf = (s: string) => Buffer.from(s, 'utf-8');

describe('InMemoryBlobStore', () => {
  // The point of the adapter: it satisfies the whole interface, so a caller that
  // starts using a second method is a compile error rather than a runtime crash.
  it('satisfies BlobStore without a cast', () => {
    const store: BlobStore = new InMemoryBlobStore();
    expect(typeof store.tryGet).toBe('function');
  });

  describe('read/write (behaviors 1-3, 9-11)', () => {
    it('stores and returns bytes', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'a.md', buf('hello'), 'text/markdown');
      expect((await s.get(p, 'a.md'))?.toString()).toBe('hello');
    });

    it('overwrites on repeat put', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'a.md', buf('one'), 'text/markdown');
      await s.put(p, 'a.md', buf('two'), 'text/markdown');
      expect((await s.get(p, 'a.md'))?.toString()).toBe('two');
    });

    it('returns null for an absent key', async () => {
      expect(await new InMemoryBlobStore().get(p, 'nope.md')).toBeNull();
    });

    it('reports existence', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'a.md', buf('x'), 'text/markdown');
      expect(await s.exists(p, 'a.md')).toBe(true);
      expect(await s.exists(p, 'b.md')).toBe(false);
    });

    it('deletes, and deleting an absent key is a no-op', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'a.md', buf('x'), 'text/markdown');
      await s.delete(p, 'a.md');
      expect(await s.get(p, 'a.md')).toBeNull();
      await expect(s.delete(p, 'ghost.md')).resolves.toBeUndefined();
    });
  });

  describe('tryGet — absent vs unreadable (behaviors 4-8)', () => {
    it('distinguishes present, absent and unreadable', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'a.md', buf('x'), 'text/markdown');
      expect(await s.tryGet(p, 'a.md')).toEqual({ ok: true, bytes: buf('x') });
      expect(await s.tryGet(p, 'gone.md')).toEqual({ ok: false, reason: 'absent' });

      s.failReads('a.md', new Error('storage 503'));
      const read = await s.tryGet(p, 'a.md');
      expect(read.ok).toBe(false);
      expect(read.ok === false && read.reason).toBe('unreadable');
    });

    // A proves-absence adapter (local FS) rethrows every non-ENOENT errno, so a
    // failed read must NOT look like "absent" to a caller using plain get().
    it('throws from get() on a faulted read when provesAbsence is true', async () => {
      const s = new InMemoryBlobStore({ provesAbsence: true });
      await s.put(p, 'a.md', buf('x'), 'text/markdown');
      s.failReads('a.md', new Error('EIO'));
      await expect(s.get(p, 'a.md')).rejects.toThrow('EIO');
    });

    // Supabase swallows every download failure into null — which is exactly why it
    // cannot prove absence, and why the serve path double-charged.
    it('collapses a faulted read to null when provesAbsence is false', async () => {
      const s = new InMemoryBlobStore({ provesAbsence: false });
      await s.put(p, 'a.md', buf('x'), 'text/markdown');
      s.failReads('a.md', new Error('503'));
      expect(await s.get(p, 'a.md')).toBeNull();
    });

    it('reports provesAbsence as configured, defaulting to the local semantics', () => {
      expect(new InMemoryBlobStore().provesAbsence).toBe(true);
      expect(new InMemoryBlobStore({ provesAbsence: false }).provesAbsence).toBe(false);
    });
  });

  describe('staging and promote (behaviors 12-15)', () => {
    it('putStaged does not publish the final key', async () => {
      const s = new InMemoryBlobStore();
      const ref = await s.putStaged(p, 'a.md', buf('staged'), 'text/markdown');
      expect(ref.finalKey).toBe('a.md');
      expect(await s.get(p, ref.tempKey)).not.toBeNull();
      expect(await s.get(p, 'a.md')).toBeNull();
    });

    it('promote publishes and clears the temp', async () => {
      const s = new InMemoryBlobStore();
      const ref = await s.putStaged(p, 'a.md', buf('staged'), 'text/markdown');
      await s.promote(ref);
      expect((await s.get(p, 'a.md'))?.toString()).toBe('staged');
      expect(await s.get(p, ref.tempKey)).toBeNull();
    });

    it('promote is idempotent when the temp is already gone', async () => {
      const s = new InMemoryBlobStore();
      const ref = await s.putStaged(p, 'a.md', buf('staged'), 'text/markdown');
      await s.promote(ref);
      await expect(s.promote(ref)).resolves.toBeUndefined();
      expect((await s.get(p, 'a.md'))?.toString()).toBe('staged');
    });

    // ---- Behavior 14: the divergence the architecture review verified. ----
    // These two tests are the executable record of a real seam bug: the same
    // promote() call produces DIFFERENT final bytes on the two shipped adapters.
    // lib/cloud-sync/sync-run.ts works around it at one call site; the other
    // writers do not know about it.
    it('promote OVERWRITES an existing final under local semantics', async () => {
      const s = new InMemoryBlobStore({ promoteSemantics: 'overwrite' });
      await s.put(p, 'a.md', buf('OLD'), 'text/markdown');
      const ref = await s.putStaged(p, 'a.md', buf('NEW'), 'text/markdown');
      await s.promote(ref);
      expect((await s.get(p, 'a.md'))?.toString()).toBe('NEW');
      expect(await s.get(p, ref.tempKey)).toBeNull();
    });

    it('promote SKIPS an existing final under Supabase semantics, keeping the old body', async () => {
      const s = new InMemoryBlobStore({ promoteSemantics: 'create-if-absent' });
      await s.put(p, 'a.md', buf('OLD'), 'text/markdown');
      const ref = await s.putStaged(p, 'a.md', buf('NEW'), 'text/markdown');
      await s.promote(ref);
      expect((await s.get(p, 'a.md'))?.toString()).toBe('OLD');
      expect(await s.get(p, ref.tempKey)).toBeNull();
    });
  });

  describe('list and deletePrefix (behaviors 16-20)', () => {
    it('lists keys under a prefix and returns [] for an absent one', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'dig/base/65.r9.md', buf('a'), 'text/markdown');
      await s.put(p, 'dig/base/1000.r9.md', buf('b'), 'text/markdown');
      await s.put(p, 'other.md', buf('c'), 'text/markdown');

      const keys = await s.list(p, 'dig/base/');
      expect(keys.sort()).toEqual(['dig/base/1000.r9.md', 'dig/base/65.r9.md']);
      expect(await s.list(p, 'nothing/here/')).toEqual([]);
      expect((await s.list(p, '')).sort()).toEqual(
        ['dig/base/1000.r9.md', 'dig/base/65.r9.md', 'other.md'],
      );
    });

    it('deletePrefix removes everything under the prefix and tolerates an absent one', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'dig/base/1.md', buf('a'), 'text/markdown');
      await s.put(p, 'dig/base/2.md', buf('b'), 'text/markdown');
      await s.put(p, 'keep.md', buf('c'), 'text/markdown');

      await s.deletePrefix(p, 'dig/base/');
      expect(await s.list(p, 'dig/base/')).toEqual([]);
      expect(await s.get(p, 'keep.md')).not.toBeNull();
      await expect(s.deletePrefix(p, 'absent/')).resolves.toBeUndefined();
    });
  });

  describe('safety (behaviors 21-22)', () => {
    it.each([
      ['leading slash', '/etc/passwd'],
      ['parent traversal', 'a/../../secret.md'],
      ['null byte', 'a\0.md'],
    ])('rejects an unsafe key: %s', async (_label, key) => {
      const s = new InMemoryBlobStore();
      await expect(s.put(p, key, buf('x'), 'text/markdown'))
        .rejects.toMatchObject({ statusCode: 400 });
    });

    it('isolates principals holding the same logical key', async () => {
      const s = new InMemoryBlobStore();
      await s.put(p, 'a.md', buf('mine'), 'text/markdown');
      await s.put(other, 'a.md', buf('theirs'), 'text/markdown');
      expect((await s.get(p, 'a.md'))?.toString()).toBe('mine');
      expect((await s.get(other, 'a.md'))?.toString()).toBe('theirs');
      expect(await s.list(p, '')).toEqual(['a.md']);
    });
  });

  describe('fault injection (behaviors 23-24)', () => {
    it('fails promote on demand', async () => {
      const s = new InMemoryBlobStore();
      const ref = await s.putStaged(p, 'a.md', buf('x'), 'text/markdown');
      s.failPromote(new Error('promote exploded'));
      await expect(s.promote(ref)).rejects.toThrow('promote exploded');
      expect(await s.get(p, 'a.md')).toBeNull();
    });

    it('fails put on demand for a matching key', async () => {
      const s = new InMemoryBlobStore();
      s.failWrites('models/x.json', new Error('put exploded'));
      await expect(s.put(p, 'models/x.json', buf('x'), 'application/json'))
        .rejects.toThrow('put exploded');
      await expect(s.put(p, 'fine.md', buf('x'), 'text/markdown')).resolves.toBeUndefined();
    });
  });
});
