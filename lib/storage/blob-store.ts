import type { Principal } from '@/lib/storage/principal';

export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';

export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }

export interface BlobStore {
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;
}

export function assertLogicalKey(key: string): void {
  if (key.startsWith('/') || key.split('/').includes('..') || key.includes('\0')) {
    throw Object.assign(new Error(`invalid blob key: ${key}`), { statusCode: 400 });
  }
}
