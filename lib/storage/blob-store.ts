import type { Principal } from '@/lib/storage/principal';

export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';

export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }

export interface BlobStore {
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
