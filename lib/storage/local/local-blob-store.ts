import fs from 'fs'; import path from 'path'; import crypto from 'crypto';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

/** Byte-for-byte the current -data layout: physical path = join(indexKey, key). */
export class LocalFsBlobStore implements BlobStore {
  /** get/exists below return null/false ONLY on ENOENT and rethrow every other errno, so a null
   *  here genuinely means the object is not there. */
  readonly provesAbsence = true;

  private abs(p: Principal, key: string): string { assertLogicalKey(key); return path.join(p.indexKey, key); }

  // contentType unused locally but required by the BlobStore interface (cloud impls will use it)
  async put(p: Principal, key: string, bytes: Buffer, _contentType: string): Promise<void> {
    const dest = this.abs(p, key); fs.mkdirSync(path.dirname(dest), { recursive: true });
    const tmp = dest + '.' + crypto.randomUUID() + '.tmp';
    try { fs.writeFileSync(tmp, bytes); fs.renameSync(tmp, dest); }
    catch (e) { try { fs.unlinkSync(tmp); } catch {} throw e; }
  }

  async get(p: Principal, key: string): Promise<Buffer | null> {
    try { return fs.readFileSync(this.abs(p, key)); }
    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
  }

  async exists(p: Principal, key: string): Promise<boolean> {
    try { fs.statSync(this.abs(p, key)); return true; }
    catch (e: any) { if (e.code === 'ENOENT') return false; throw e; }
  }

  async delete(p: Principal, key: string): Promise<void> {
    try { fs.unlinkSync(this.abs(p, key)); } catch (e: any) { if (e.code !== 'ENOENT') throw e; }
  }

  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    assertLogicalKey(key);  // validate before building tempKey — a leading '/' on key wouldn't appear on tempKey
    const tempKey = `_staging/${crypto.randomUUID()}/${key}`;
    await this.put(p, tempKey, bytes, contentType);
    return { principal: p, tempKey, finalKey: key };
  }

  async promote(ref: StagedRef): Promise<void> {
    const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
    fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
  }

  // '' → path.join(indexKey, '') === indexKey, i.e. the playlist's own index dir (intended
  // target, not above it). force:true makes an absent path a no-op (ENOENT-safe).
  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    assertLogicalKey(prefix);
    await fs.promises.rm(path.join(p.indexKey, prefix), { recursive: true, force: true });
  }

  async list(p: Principal, prefix: string): Promise<string[]> {
    assertLogicalKey(prefix);
    const root = path.join(p.indexKey, prefix);
    let entries: string[];
    try {
      entries = await fs.promises.readdir(root, { recursive: true }) as string[];
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === 'ENOENT') return [];
      throw e;
    }
    const out: string[] = [];
    for (const rel of entries) {
      const full = path.join(root, rel);
      if ((await fs.promises.stat(full)).isFile()) {
        out.push(path.posix.join(prefix.replace(/\/$/, ''), rel.split(path.sep).join('/')));
      }
    }
    return out;
  }
}

export const localBlobStore = new LocalFsBlobStore();
