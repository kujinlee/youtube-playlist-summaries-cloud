import type { Principal } from '@/lib/storage/principal';

export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';

export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }

/** The honest result of a blob read: bytes, PROVABLY absent, or "the read failed and we cannot tell".
 *  `get` collapses the last two into `null`, which is safe for a cache read and NOT safe for anything
 *  that spends money or deletes data — see `tryGet`. */
export type BlobRead =
  | { ok: true; bytes: Buffer }
  | { ok: false; reason: 'absent' }
  | { ok: false; reason: 'unreadable'; cause: unknown };

/** The honest result of a blob copy.
 *
 *  Granular on purpose. A caller must never be able to collapse "could not read" into "absent" —
 *  that conflation produced a Blocking, three Highs, and a live 6¢→12¢ double charge in the
 *  Stage 3 cloud-sync review. `phase` exists so a write/verify failure cannot be mistaken for a
 *  precondition failure either.
 *
 *  `already: true` means the destination was PROVEN to hold byte-identical content. It is not a
 *  convenience: without it, a fail-closed `destination-exists` would deadlock every retry after a
 *  partial multi-blob relocation, permanently — the first blob would abort every subsequent run. */
export type CopyResult =
  | { ok: true; already: boolean }
  | { ok: false; reason: 'source-absent' }
  | { ok: false; reason: 'source-unreadable'; cause: unknown }
  | { ok: false; reason: 'destination-exists' }
  | { ok: false; reason: 'destination-unreadable'; cause: unknown }
  | { ok: false; reason: 'failed'; phase: 'write' | 'verify'; cause: unknown };

export interface BlobStore {
  /** Copy `from` → `to` within one principal, **retaining the source**.
   *
   *  Deliberately a copy and not a rename. A multi-blob relocation must be
   *  copy → verify → update metadata → delete sources, so the sources have to survive until the
   *  metadata is coherent. Supabase `move()` is copy+delete and non-atomic, and `fs.renameSync` is
   *  atomic per object but not across N — so a destructive rename would bake an unrecoverable
   *  ordering into the seam.
   *
   *  Never overwrites: a destination holding different bytes is `destination-exists`, and the
   *  caller decides. Implementations MUST delegate to `copyBlob` so the semantics cannot drift
   *  apart the way `promote()` did (architecture review finding #2). */
  copy(p: Principal, from: string, to: string): Promise<CopyResult>;
  /** Like `get`, but distinguishes *absent* from *could not be read*.
   *
   *  **Use this instead of `get` before any irreversible or billable decision.** Treating an
   *  unreadable read as "absent" is the defect class that produced a Blocking and three Highs in the
   *  Stage 3 cloud-sync review, and a live double-charge on the serve path: a transient Storage 5xx
   *  made an EXISTING magazine model look missing, so the serve path reserved and regenerated it —
   *  6¢ → 12¢ for a model already in the bucket (`tests/integration/serve-model-unreadable.test.ts`).
   *
   *  Required, not optional, so the compiler forces every implementation to answer the question
   *  rather than letting a caller quietly inherit the ambiguous `get`. */
  tryGet(p: Principal, key: string): Promise<BlobRead>;
  /** True iff a `null` from `get` (or `false` from `exists`) PROVES the object does not exist —
   *  i.e. the backend distinguishes "absent" from "could not be read". The local FS store returns
   *  null only on ENOENT and rethrows every other errno, so it proves absence; the Supabase store
   *  swallows network/5xx/timeout/RLS failures into the same null, so it cannot.
   *
   *  Read it before treating "no bytes" as a semantic fact ("this replica holds no MD", "this
   *  sender has no model"): on a backend that cannot prove absence, acting on that reading
   *  destroys data on a transient blip (see the B1 and H1 guards in lib/cloud-sync/sync-run.ts).
   *  Optional, and absent means FALSE — an unknown backend is assumed unable to prove absence, so
   *  callers stay fail-closed by default. */
  readonly provesAbsence?: boolean;
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;
  /** Recursively delete every object under a logical prefix. Best-effort/idempotent —
   *  an absent prefix is not an error. `prefix === ''` targets the whole playlist root
   *  (`<owner>/<indexKey>/`), not above it. */
  deletePrefix(p: Principal, prefix: string): Promise<void>;
  /** List logical keys (relative to the owner root) under a prefix. Absent prefix → []. */
  list(p: Principal, prefix: string): Promise<string[]>;
}

/** A read-only view of a BlobStore — exactly the `get` method. The share serve path
 *  passes a runtime `{ get: store.get.bind(store) }` wrapper so write methods are
 *  unreachable at runtime, not merely hidden by the type (spec D16). */
export type ReadOnlyBlobStore = Pick<BlobStore, 'get'>;

export function assertLogicalKey(key: string): void {
  if (key.startsWith('/') || key.split('/').includes('..') || key.includes('\0')) {
    throw Object.assign(new Error(`invalid blob key: ${key}`), { statusCode: 400 });
  }
}

/** Canonical form of an already-validated logical key: drops empty and `.` segments so
 *  `a/./b` and `a//b` cannot alias `a/b` past the same-key short-circuit. `..` is impossible
 *  here — `assertLogicalKey` rejects it. */
export function normalizeLogicalKey(key: string): string {
  return key.split('/').filter((seg) => seg !== '' && seg !== '.').join('/');
}

/** Content type for a copied blob, derived from its key. `copy` reproduces bytes, and the
 *  adapters that care about content type (Supabase) need one at write time; the source's stored
 *  type is not retrievable through the `BlobStore` interface. Deterministic beats guessing. */
function contentTypeForKey(key: string): string {
  const ext = key.slice(key.lastIndexOf('.') + 1).toLowerCase();
  switch (ext) {
    case 'md': return 'text/markdown';
    case 'html': return 'text/html';
    case 'json': return 'application/json';
    case 'pdf': return 'application/pdf';
    case 'jpg': case 'jpeg': return 'image/jpeg';
    case 'png': return 'image/png';
    default: return 'application/octet-stream';
  }
}

/** THE one implementation of `copy`, shared by every adapter.
 *
 *  Finding #2 of the 2026-07-30 architecture review is "the commit→promote protocol has no owner":
 *  `writeArtifact` states it correctly and has zero production callers, while five writers
 *  hand-roll it and the two adapters silently disagree about what `promote()` means. This function
 *  exists so `copy` cannot repeat that. Adapters supply primitives (`tryGet`, `put`); the ORDERING
 *  and the CLASSIFICATION live here, once.
 *
 *  Note it reads exclusively through `tryGet` — never `exists()` or `get()`, both of which collapse
 *  a transient failure into the same answer as genuine absence on the Supabase backend. */
export async function copyBlob(
  store: Pick<BlobStore, 'tryGet' | 'put'>,
  p: Principal,
  from: string,
  to: string,
): Promise<CopyResult> {
  assertLogicalKey(from);                      // before ANY I/O
  assertLogicalKey(to);
  if (normalizeLogicalKey(from) === normalizeLogicalKey(to)) return { ok: true, already: true };

  const src = await store.tryGet(p, from);
  if (!src.ok) {
    return src.reason === 'absent'
      ? { ok: false, reason: 'source-absent' }
      : { ok: false, reason: 'source-unreadable', cause: src.cause };
  }

  const dst = await store.tryGet(p, to);
  if (dst.ok) {
    // Proven-identical → already copied (resumable). Different → the destination is someone's
    // paid artifact; refuse and let the caller decide.
    return dst.bytes.equals(src.bytes)
      ? { ok: true, already: true }
      : { ok: false, reason: 'destination-exists' };
  }
  if (dst.reason === 'unreadable') {
    return { ok: false, reason: 'destination-unreadable', cause: dst.cause };
  }

  try {
    await store.put(p, to, src.bytes, contentTypeForKey(to));
  } catch (cause) {
    return { ok: false, reason: 'failed', phase: 'write', cause };
  }

  // Verify-after-write: an unproven copy is not a copy. The caller is about to advance metadata
  // to point at this key and then delete the source, so "probably written" is not good enough.
  const check = await store.tryGet(p, to);
  if (!check.ok) {
    return { ok: false, reason: 'failed', phase: 'verify', cause: check.reason === 'absent'
      ? new Error(`copy verify: destination ${to} absent after write`)
      : check.cause };
  }
  if (!check.bytes.equals(src.bytes)) {
    return { ok: false, reason: 'failed', phase: 'verify', cause: new Error(`copy verify: byte mismatch at ${to}`) };
  }
  return { ok: true, already: false };
}
