// stub — all methods filled in Task 10
import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';

const NI = (): never => { throw new Error('not implemented — stub for Task 7; filled in Task 10'); };

export class SupabaseBlobStore implements BlobStore {
  constructor(_client: SupabaseClient, _bucket: string) {}
  put = NI as unknown as BlobStore['put'];
  get = NI as unknown as BlobStore['get'];
  exists = NI as unknown as BlobStore['exists'];
  delete = NI as unknown as BlobStore['delete'];
  putStaged = NI as unknown as BlobStore['putStaged'];
  promote = NI as unknown as BlobStore['promote'];
}
