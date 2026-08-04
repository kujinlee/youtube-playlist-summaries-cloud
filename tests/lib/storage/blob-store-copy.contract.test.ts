/**
 * `BlobStore.copy` — the CONTRACT, run against every adapter.
 *
 * Behaviors table rows 1–8b, docs/superpowers/plans/2026-07-31-serial-coherence-sync.md.
 *
 * WHY A SHARED CONTRACT SUITE: row 5 is "identical result for identical state — no
 * adapter-specific semantics". That is not a nice-to-have here. Architecture-review finding #2
 * exists because `promote()` means *overwrite* on local and *create-if-absent* on Supabase, and
 * nothing ever asserted otherwise — so three production writers still assume uniformity that was
 * never true. A per-adapter test file would have let `copy` acquire the same drift. Running one
 * table against every adapter makes divergence a test failure instead of a four-week discovery.
 *
 * WHY `copy` AND NOT `rename`: a multi-blob relocation must be
 * copy → verify → update metadata → delete sources, so sources have to survive until the metadata
 * is coherent. Supabase `move()` is copy+delete and non-atomic; `fs.renameSync` is atomic per
 * object but not across N. A destructive rename would bake the unsafe ordering into the seam.
 * (Codex review of the behaviors table, High #3 + Medium #10.)
 */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import { LocalFsBlobStore } from '@/lib/storage/local/local-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { BlobStore } from '@/lib/storage/blob-store';
import { copyBlob } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

interface Adapter {
  name: string;
  make(): { store: BlobStore; p: Principal; other: Principal };
  /** Fault injection is only available on the in-memory adapter. */
  faults: boolean;
}

const tmpDirs: string[] = [];
function tmpPrincipal(): Principal {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'copy-contract-'));
  tmpDirs.push(dir);
  return localPrincipal(dir);
}

const ADAPTERS: Adapter[] = [
  {
    name: 'InMemoryBlobStore',
    faults: true,
    make: () => ({
      store: new InMemoryBlobStore(),
      p: localPrincipal('/idx-a'),
      other: localPrincipal('/idx-b'),
    }),
  },
  {
    name: 'LocalFsBlobStore',
    faults: false,
    make: () => ({ store: new LocalFsBlobStore(), p: tmpPrincipal(), other: tmpPrincipal() }),
  },
];

afterAll(() => {
  for (const d of tmpDirs) fs.rmSync(d, { recursive: true, force: true });
});

describe.each(ADAPTERS)('BlobStore.copy contract — $name', (adapter) => {
  const put = (s: BlobStore, p: Principal, k: string, body: string) =>
    s.put(p, k, Buffer.from(body), 'text/markdown');

  // Row 1 — the source must SURVIVE. This is the whole reason copy replaced rename.
  it('copies and RETAINS the source', async () => {
    const { store, p } = adapter.make();
    await put(store, p, 'a.md', 'BODY');

    const res = await store.copy(p, 'a.md', 'b.md');

    expect(res).toEqual({ ok: true, already: false });
    expect((await store.get(p, 'b.md'))?.toString()).toBe('BODY');
    expect((await store.get(p, 'a.md'))?.toString()).toBe('BODY');
  });

  // Row 2 — never a silent success.
  it('reports source-absent rather than succeeding vacuously', async () => {
    const { store, p } = adapter.make();
    const res = await store.copy(p, 'missing.md', 'b.md');

    expect(res).toEqual({ ok: false, reason: 'source-absent' });
    expect(await store.exists(p, 'b.md')).toBe(false);
  });

  // Row 3 — fail-closed. This is the promote divergence's exact shape: the destination holds
  // content someone paid Gemini to produce, and an overwrite destroys it.
  it('refuses to overwrite a destination holding DIFFERENT bytes, touching neither', async () => {
    const { store, p } = adapter.make();
    await put(store, p, 'a.md', 'NEW');
    await put(store, p, 'b.md', 'PAID EXISTING CONTENT');

    const res = await store.copy(p, 'a.md', 'b.md');

    expect(res).toEqual({ ok: false, reason: 'destination-exists' });
    expect((await store.get(p, 'b.md'))?.toString()).toBe('PAID EXISTING CONTENT');
    expect((await store.get(p, 'a.md'))?.toString()).toBe('NEW');
  });

  // Row 3b — the finding that saves the design. Strict fail-closed on destination-exists would
  // deadlock EVERY retry after a partial run, permanently: the first attempt copies blob 1 of 3
  // and dies, and every subsequent attempt aborts on blob 1 forever. Proven-identical bytes are
  // "already copied", not a collision. (Codex Medium #9.)
  it('treats a destination holding IDENTICAL bytes as already-copied', async () => {
    const { store, p } = adapter.make();
    await put(store, p, 'a.md', 'SAME');
    await put(store, p, 'b.md', 'SAME');

    const res = await store.copy(p, 'a.md', 'b.md');

    expect(res).toEqual({ ok: true, already: true });
  });

  // Row 7 — idempotent no-op, compared after normalization so `a/./b` cannot alias.
  it('short-circuits a same-key copy', async () => {
    const { store, p } = adapter.make();
    await put(store, p, 'a.md', 'BODY');

    expect(await store.copy(p, 'a.md', 'a.md')).toEqual({ ok: true, already: true });
    expect((await store.get(p, 'a.md'))?.toString()).toBe('BODY');
  });

  // Row 6 — validation precedes all I/O.
  it('rejects an invalid key before doing any I/O', async () => {
    const { store, p } = adapter.make();
    await put(store, p, 'a.md', 'BODY');

    await expect(store.copy(p, 'a.md', '/abs.md')).rejects.toThrow();
    await expect(store.copy(p, '../esc.md', 'b.md')).rejects.toThrow();
    expect(await store.exists(p, 'b.md')).toBe(false);
  });

  // Row 8 — a copy is owner-scoped; it cannot leak into another principal's namespace.
  it('stays within the principal', async () => {
    const { store, p, other } = adapter.make();
    await put(store, p, 'a.md', 'MINE');

    await store.copy(p, 'a.md', 'b.md');

    expect(await store.exists(other, 'b.md')).toBe(false);
    expect(await store.exists(other, 'a.md')).toBe(false);
  });
});

// Faults are only injectable on the in-memory adapter; the local FS adapter has no seam for
// them and Supabase's classification is asserted separately against its mocked bucket.
describe('BlobStore.copy contract — fault paths (InMemoryBlobStore)', () => {
  const p = localPrincipal('/idx-a');

  // Row 4b — the distinction this codebase paid a Blocking, three Highs and a live 6¢→12¢
  // double charge to learn: "could not read" is NOT "absent".
  it('reports source-unreadable, never source-absent, on a transient read failure', async () => {
    const store = new InMemoryBlobStore();
    await store.put(p, 'a.md', Buffer.from('BODY'), 'text/markdown');
    store.failReads('a.md');

    const res = await store.copy(p, 'a.md', 'b.md');

    expect(res).toMatchObject({ ok: false, reason: 'source-unreadable' });
    expect(await store.exists(p, 'b.md')).toBe(false);
  });

  it('reports destination-unreadable when the destination probe fails', async () => {
    const store = new InMemoryBlobStore();
    await store.put(p, 'a.md', Buffer.from('BODY'), 'text/markdown');
    await store.put(p, 'b.md', Buffer.from('OTHER'), 'text/markdown');
    store.failReads('b.md');

    const res = await store.copy(p, 'a.md', 'b.md');

    expect(res).toMatchObject({ ok: false, reason: 'destination-unreadable' });
    // The destination must be UNTOUCHED. Read it back with the fault cleared — while the fault is
    // armed `get` throws (provesAbsence=true mirrors the local adapter rethrowing non-ENOENT),
    // so asserting on a faulted read would prove nothing about the bytes.
    store.clearFaults();
    expect((await store.get(p, 'b.md'))?.toString()).toBe('OTHER');
  });

  // Row 4 — a write failure carries its phase, so a caller can never mistake it for a
  // precondition failure and conclude the source was absent.
  it('reports failed with phase=write when the destination write throws', async () => {
    const store = new InMemoryBlobStore();
    await store.put(p, 'a.md', Buffer.from('BODY'), 'text/markdown');
    store.failWrites('b.md');

    const res = await store.copy(p, 'a.md', 'b.md');

    expect(res).toMatchObject({ ok: false, reason: 'failed', phase: 'write' });
  });
});

// Row 8b — verify-after-write.
//
// THESE TESTS EXIST BECAUSE A MUTATION FOUND THE GAP. Deleting the verify step left all 17
// other tests GREEN: every adapter's `put` is honest, so nothing exercised a write that
// "succeeds" and does not land. That is precisely the silent-failure shape this slice is about,
// and the caller is about to point metadata at the destination and then DELETE the source — so
// an unproven copy is a data-loss bug, not a cosmetic one.
//
// `copyBlob` is called directly with a hand-built pair of primitives, because the failure being
// modelled is a dishonest backend, which no real adapter can be asked to simulate.
describe('copyBlob — verify-after-write (mutation-driven)', () => {
  const p = localPrincipal('/idx-a');
  const src = Buffer.from('BODY');

  it('reports failed:verify when the write silently does not land', async () => {
    const store = {
      async tryGet(_p: Principal, key: string) {
        return key === 'a.md'
          ? { ok: true as const, bytes: src }
          : { ok: false as const, reason: 'absent' as const };   // destination never appears
      },
      async put() { /* accepted, and silently dropped — a lying backend */ },
    };

    const res = await copyBlob(store, p, 'a.md', 'b.md');

    expect(res).toMatchObject({ ok: false, reason: 'failed', phase: 'verify' });
  });

  // Stateful on purpose: the destination must read as ABSENT at the precheck (or this trips
  // `destination-exists` and never reaches the write) and as CORRUPT afterwards. That ordering
  // is the whole point — a partial/corrupt write is only observable after the fact.
  it('reports failed:verify when the destination lands with the WRONG bytes', async () => {
    let written = false;
    const store = {
      async tryGet(_p: Principal, key: string) {
        if (key === 'a.md') return { ok: true as const, bytes: src };
        return written
          ? { ok: true as const, bytes: Buffer.from('TRUNCA') }   // partial write
          : { ok: false as const, reason: 'absent' as const };
      },
      async put() { written = true; },
    };

    const res = await copyBlob(store, p, 'a.md', 'b.md');

    expect(res).toMatchObject({ ok: false, reason: 'failed', phase: 'verify' });
  });
});
