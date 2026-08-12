import crypto from 'crypto';
import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobRead, BlobStore, CopyResult, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey, copyBlob } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

export class SupabaseBlobStore implements BlobStore {
  /** `get` swallows EVERY download failure into null (see the note on it below) and `exists` is
   *  defined in terms of `get`, so this backend can never prove an object is absent. */
  readonly provesAbsence = false;

  constructor(private client: SupabaseClient, private bucket: string) {}

  /** Server-side owner prefix — never a client absolute path. */
  private objectKey(p: Principal, key: string): string {
    assertLogicalKey(key);
    return `${p.id}/${p.indexKey}/${key}`;
  }

  private b() { return this.client.storage.from(this.bucket); }

  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
    if (error) throw error;
  }

  async get(p: Principal, key: string): Promise<Buffer | null> {
    const { data, error } = await this.b().download(this.objectKey(p, key));
    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
    // so a null here does NOT prove the object is absent. Callers that treat "no bytes" as a
    // semantic fact (e.g. "this replica holds no MD") must corroborate it against the record that
    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately
    // left as-is: shared with already-merged read paths where absent-vs-unreadable is immaterial.
    // Note the LOCAL blob store differs — it returns null only on ENOENT and throws otherwise.
    if (error) return null;
    return Buffer.from(await data.arrayBuffer());
  }

  /** The honest read — but read the limits below before treating `absent` as a fact.
   *
   *  Supabase reports a missing object as a StorageApiError carrying `statusCode: "404"`.
   *
   *  ⚠ CORRECTED 2026-08-11 (M1.4 gate B3). This comment used to conclude "so a 404 IS provable
   *  absence", and listed RLS denial among the cases that come back as `unreadable`. **Both halves
   *  are false.** Measured against hosted Supabase, an object that EXISTS but is hidden by row-level
   *  security returns the byte-identical error to one that never existed:
   *
   *      exists, policy dropped  {message:"Object not found", name:"StorageApiError", status:400, statusCode:"404"}
   *      genuinely absent        {message:"Object not found", name:"StorageApiError", status:400, statusCode:"404"}
   *
   *  RLS makes the row invisible, so the API cannot say more — and the original claim was verified
   *  only against a missing object, never against a denied one. Checking one direction of a
   *  two-directional question is how it survived.
   *
   *  So: `unreadable` still means "definitely could not read it" (5xx, timeout, thrown transport
   *  error), and callers must never treat it as absence. But `absent` means only "404-shaped", which
   *  on this backend is **absent OR denied**. It is not proof, which is why `provesAbsence` is
   *  `false` here. A caller that spends money on `absent` must corroborate it — see the precondition
   *  on `resolveMagazineModel` (`lib/html-doc/serve-doc.ts`), whose safety comes from an upstream
   *  read of the same folder, not from this classification. */
  async tryGet(p: Principal, key: string): Promise<BlobRead> {
    try {
      const { data, error } = await this.b().download(this.objectKey(p, key));
      if (error) {
        const code = String((error as { statusCode?: string | number }).statusCode ?? '');
        if (code === '404') return { ok: false, reason: 'absent' };
        return { ok: false, reason: 'unreadable', cause: error };
      }
      return { ok: true, bytes: Buffer.from(await data.arrayBuffer()) };
    } catch (e) {
      // download() throws rather than returning `error` on a transport failure — also unprovable.
      return { ok: false, reason: 'unreadable', cause: e };
    }
  }

  async exists(p: Principal, key: string): Promise<boolean> {
    return (await this.get(p, key)) !== null;
  }

  async delete(p: Principal, key: string): Promise<void> {
    const { error } = await this.b().remove([this.objectKey(p, key)]);
    if (error) throw error;
  }

  /** Delegates to the shared `copyBlob`.
   *
   *  Deliberately NOT built on this bucket's `copy`/`move`: those cannot classify the outcome.
   *  `exists()` here is `get() !== null` and `get()` swallows every download failure — 5xx,
   *  timeout, RLS denial — into the same `null` as a genuine 404, so a preflight built on them
   *  would report `source-absent` for a transient blip and let the caller delete a paid artifact.
   *  `copyBlob` reads exclusively through `tryGet`, which is the honest probe on this backend.
   *
   *  Note also that `promote()` above treats "destination already present" as SUCCESS, which is
   *  the exact opposite of `copy`'s fail-closed rule. Both are correct for their own job; the
   *  point is that the difference is now written down instead of being discovered later. */
  async copy(p: Principal, from: string, to: string): Promise<CopyResult> {
    return copyBlob(this, p, from, to);
  }

  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    assertLogicalKey(key); // validate before building tempKey — reject '/absolute' before any upload
    const tempKey = `_staging/${crypto.randomUUID()}/${key}`; // per-attempt-unique (ports local-blob-store)
    await this.put(p, tempKey, bytes, contentType);
    return { principal: p, tempKey, finalKey: key };
  }

  async promote(ref: StagedRef): Promise<void> {
    const from = this.objectKey(ref.principal, ref.tempKey);
    const to = this.objectKey(ref.principal, ref.finalKey);
    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    if (await this.exists(ref.principal, ref.finalKey)) {
      await this.b().remove([from]).catch(() => {});
      return;
    }
    const { error } = await this.b().move(from, to);
    if (error) {
      // A concurrent promoter (worker job retry / re-run of the same MD key) may have won the race: destination-exists / source-missing.
      // Re-check the final; treat a present final as success, else rethrow.
      if (await this.exists(ref.principal, ref.finalKey)) {
        await this.b().remove([from]).catch(() => {});
        return;
      }
      throw error;
    }
  }

  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    assertLogicalKey(prefix);
    const root = `${p.id}/${p.indexKey}/${prefix}`.replace(/\/$/, '');
    const objectPaths = await this.collectObjectPaths(root);
    for (let i = 0; i < objectPaths.length; i += 1000) {
      const batch = objectPaths.slice(i, i + 1000);
      const { error } = await this.b().remove(batch);
      if (error) throw error;
    }
  }

  async list(p: Principal, prefix: string): Promise<string[]> {
    assertLogicalKey(prefix);
    const ownerRoot = `${p.id}/${p.indexKey}/`;
    const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
    const full = await this.collectObjectPaths(dirPath); // returns full object paths (or [] if absent)
    return full.map((f) => f.slice(ownerRoot.length)); // strip owner root → logical key
  }

  /** Recursively walks a Supabase Storage "directory" (non-recursive `.list`, paginated at
   *  100/page) and returns every file's full object path. Folder entries surface with
   *  `id === null` and are descended into; file entries (`id !== null`) are collected. */
  private async collectObjectPaths(dirPath: string): Promise<string[]> {
    const paths: string[] = [];
    const limit = 100;
    let offset = 0;
    for (;;) {
      const { data, error } = await this.b().list(dirPath, { limit, offset });
      if (error) throw error;
      const entries = data ?? [];
      for (const entry of entries) {
        const entryPath = `${dirPath}/${entry.name}`;
        if (entry.id === null) {
          paths.push(...(await this.collectObjectPaths(entryPath)));
        } else {
          paths.push(entryPath);
        }
      }
      if (entries.length < limit) break;
      offset += limit;
    }
    return paths;
  }
}
