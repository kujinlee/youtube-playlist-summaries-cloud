import crypto from 'crypto';
import type { BlobRead, BlobStore, CopyResult, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey, copyBlob } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

/**
 * A complete in-memory `BlobStore` for tests.
 *
 * Exists because there wasn't one: tests substituted at the *module* level
 * (`jest.mock('@/lib/storage/resolve')`) or built partial fakes cast through
 * `as unknown as`, which cannot fail when a caller starts using a method the fake
 * never implemented. This adapter satisfies the whole interface, so that becomes a
 * compile error. See `docs/reviews/architecture-review-2026-07-30.md` §3.
 *
 * ## It models BOTH shipped adapters, because they disagree
 *
 * `promote()` is not uniform. When the staged temp AND the final key both exist:
 *
 *   - `LocalFsBlobStore` does `fs.renameSync(from, to)` -> final gets the NEW body.
 *   - `SupabaseBlobStore` does `if (exists(final)) { remove(temp); return; }`
 *     -> final KEEPS ITS OLD BODY.
 *
 * `lib/cloud-sync/sync-run.ts` found this and worked around it at one call site.
 * Picking one semantic here would bake the disagreement into the suite as a truth,
 * so it is a constructor option and both are asserted in the tests.
 *
 * `provesAbsence` is configurable for the same reason: it decides whether a failed
 * read throws (local rethrows every non-ENOENT errno) or collapses to `null`
 * (Supabase swallows all download failures). That collapse is the defect class
 * behind the live 6c -> 12c double-charge documented on `BlobStore.tryGet`.
 */
export interface InMemoryBlobStoreOptions {
  /** How `promote` behaves when the final key already exists. Default `'overwrite'` (local). */
  promoteSemantics?: 'overwrite' | 'create-if-absent';
  /** Whether a `null` read proves absence. Default `true` (local). */
  provesAbsence?: boolean;
}

interface StoredBlob { bytes: Buffer; contentType: string; }

export class InMemoryBlobStore implements BlobStore {
  readonly provesAbsence: boolean;
  private readonly promoteSemantics: 'overwrite' | 'create-if-absent';

  private readonly blobs = new Map<string, StoredBlob>();
  private readonly readFaults = new Map<string, unknown>();
  private readonly writeFaults = new Map<string, unknown>();
  private readonly deleteFaults = new Map<string, unknown>();
  private promoteFault: unknown | undefined;

  constructor(opts: InMemoryBlobStoreOptions = {}) {
    this.promoteSemantics = opts.promoteSemantics ?? 'overwrite';
    this.provesAbsence = opts.provesAbsence ?? true;
  }

  // ---- fault injection (replaces the hand-forwarding decorators in tests/integration/helpers) ----

  /** Make reads of `key` fail. `tryGet` reports `unreadable`; `get` throws or returns
   *  null depending on `provesAbsence`, mirroring the two real adapters. */
  failReads(key: string, cause: unknown = new Error('blob read failed')): void {
    this.readFaults.set(key, cause);
  }

  /** Make `put`/`putStaged` of `key` throw. */
  failWrites(key: string, cause: unknown = new Error('blob write failed')): void {
    this.writeFaults.set(key, cause);
  }

  /** Make `delete` of `key` throw. Cleanup after a relocation is best-effort, so a caller has to
   *  be able to prove it SURVIVES a delete failure rather than undoing durable work. */
  failDeletes(key: string, cause: unknown = new Error('blob delete failed')): void {
    this.deleteFaults.set(key, cause);
  }

  /** Make the next and subsequent `promote` calls throw. */
  failPromote(cause: unknown = new Error('promote failed')): void {
    this.promoteFault = cause;
  }

  /** Drop all armed faults. */
  clearFaults(): void {
    this.readFaults.clear();
    this.writeFaults.clear();
    this.deleteFaults.clear();
    this.promoteFault = undefined;
  }

  // ---- helpers ----

  /** Owner-scoped physical key. NUL separators cannot collide with a logical key,
   *  because `assertLogicalKey` rejects NUL. */
  private physical(p: Principal, key: string): string {
    assertLogicalKey(key);
    return `${p.id}\0${p.indexKey}\0${key}`;
  }

  private ownerPrefix(p: Principal): string {
    return `${p.id}\0${p.indexKey}\0`;
  }

  // ---- BlobStore ----

  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    const phys = this.physical(p, key);
    if (this.writeFaults.has(key)) throw this.writeFaults.get(key);
    this.blobs.set(phys, { bytes: Buffer.from(bytes), contentType });
  }

  async get(p: Principal, key: string): Promise<Buffer | null> {
    const phys = this.physical(p, key);
    if (this.readFaults.has(key)) {
      // Local rethrows every non-ENOENT errno; Supabase swallows into null. That
      // difference is the whole reason `provesAbsence` exists.
      if (this.provesAbsence) throw this.readFaults.get(key);
      return null;
    }
    const hit = this.blobs.get(phys);
    return hit ? Buffer.from(hit.bytes) : null;
  }

  async tryGet(p: Principal, key: string): Promise<BlobRead> {
    const phys = this.physical(p, key);
    if (this.readFaults.has(key)) {
      return { ok: false, reason: 'unreadable', cause: this.readFaults.get(key) };
    }
    const hit = this.blobs.get(phys);
    return hit ? { ok: true, bytes: Buffer.from(hit.bytes) } : { ok: false, reason: 'absent' };
  }

  async exists(p: Principal, key: string): Promise<boolean> {
    const phys = this.physical(p, key);
    if (this.readFaults.has(key)) {
      if (this.provesAbsence) throw this.readFaults.get(key);
      return false;
    }
    return this.blobs.has(phys);
  }

  async delete(p: Principal, key: string): Promise<void> {
    if (this.deleteFaults.has(key)) throw this.deleteFaults.get(key);
    this.blobs.delete(this.physical(p, key));
  }

  /** Delegates to the shared `copyBlob`, exactly as the two real adapters do — so a divergence
   *  between this double and production is impossible by construction, not by discipline. */
  async copy(p: Principal, from: string, to: string): Promise<CopyResult> {
    return copyBlob(this, p, from, to);
  }

  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    assertLogicalKey(key);   // validate before building tempKey, as the local store does
    const tempKey = `_staging/${crypto.randomUUID()}/${key}`;
    await this.put(p, tempKey, bytes, contentType);
    return { principal: p, tempKey, finalKey: key };
  }

  async promote(ref: StagedRef): Promise<void> {
    if (this.promoteFault !== undefined) throw this.promoteFault;

    const from = this.physical(ref.principal, ref.tempKey);
    const to = this.physical(ref.principal, ref.finalKey);
    const staged = this.blobs.get(from);
    const finalExists = this.blobs.has(to);

    if (!staged) {
      if (finalExists) return;                       // already promoted - idempotent
      throw new Error(`promote: staged blob missing for ${ref.finalKey}`);
    }

    if (finalExists && this.promoteSemantics === 'create-if-absent') {
      // Supabase: the move is SKIPPED, so the final keeps its old body. The temp is
      // still dropped, which is what makes the stale body survive silently.
      this.blobs.delete(from);
      return;
    }

    this.blobs.set(to, staged);
    this.blobs.delete(from);
  }

  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    assertLogicalKey(prefix);
    const full = this.ownerPrefix(p) + prefix;
    for (const k of [...this.blobs.keys()]) {
      if (k.startsWith(full)) this.blobs.delete(k);
    }
  }

  async list(p: Principal, prefix: string): Promise<string[]> {
    assertLogicalKey(prefix);
    const owner = this.ownerPrefix(p);
    const full = owner + prefix;
    const out: string[] = [];
    for (const k of this.blobs.keys()) {
      if (k.startsWith(full)) out.push(k.slice(owner.length));
    }
    return out;
  }
}
