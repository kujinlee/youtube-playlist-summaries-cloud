import crypto from 'crypto';
import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

export class SupabaseBlobStore implements BlobStore {
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
    if (error) return null;   // 404 → null
    return Buffer.from(await data.arrayBuffer());
  }

  async exists(p: Principal, key: string): Promise<boolean> {
    return (await this.get(p, key)) !== null;
  }

  async delete(p: Principal, key: string): Promise<void> {
    const { error } = await this.b().remove([this.objectKey(p, key)]);
    if (error) throw error;
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
