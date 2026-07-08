import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { JobQueue } from '@/lib/storage/job-queue';
import { localPrincipal, type Principal } from '@/lib/storage/principal';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { validateStorageEnv, ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { assertOutputFolder } from '@/lib/index-store';

export interface StorageBundle {
  metadataStore: MetadataStore;
  blobStore: BlobStore;
  jobQueue?: JobQueue; // cloud-only; undefined for the local bundle
}

const LOCAL_BUNDLE: StorageBundle = { metadataStore: localMetadataStore as MetadataStore, blobStore: localBlobStore as BlobStore };

/** Resolve a request's outputFolder into a Principal, running the local
 *  home-dir containment guard (behavior identical to today's assertOutputFolder).
 *  CRITICAL (Codex Blocking): preserve the RAW outputFolder string — do NOT
 *  path.resolve it. index-store uses the raw string for the index file path;
 *  assertOutputFolder resolves only internally for its guard check. Resolving
 *  here would change the persisted index.outputFolder value and the arguments
 *  observed by existing mocked-function assertions. */
export function getPrincipal(outputFolder: string): Principal {
  assertOutputFolder(outputFolder); // guards; resolves internally, returns void
  const indexKey = outputFolder;    // raw string preserved; renamed for Principal field clarity
  return localPrincipal(indexKey);
}

/**
 * @deprecated Use getStorageBundle() instead, which co-selects a matched
 *   {metadataStore, blobStore} pair from STORAGE_BACKEND. Calling this shim
 *   and resolving blobStore independently risks mixing local and cloud stores.
 */
export function getMetadataStore(): MetadataStore {
  return localMetadataStore;
}

/** Return a co-selected StorageBundle {metadataStore, blobStore, jobQueue?} from
 *  STORAGE_BACKEND. Never mixes local and cloud stores.
 *  - 'local' (default): returns the local singletons; jobQueue is undefined
 *    (the local backend has no job queue in Stage 1E-a).
 *  - 'supabase': validates env (fail-fast), requires ctx.supabaseClient (routes
 *    are not wired in Stage 1C — passing no client throws), then returns
 *    Supabase impls including a SupabaseJobQueue. */
export function getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): StorageBundle {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'local') return LOCAL_BUNDLE; // jobQueue stays undefined
  if (backend === 'supabase') {
    validateStorageEnv(); // fail-fast on missing env
    if (!ctx?.supabaseClient) throw new Error('supabase backend requires an authenticated client (routes not wired in 1C)');
    return {
      metadataStore: new SupabaseMetadataStore(ctx.supabaseClient),
      blobStore: new SupabaseBlobStore(ctx.supabaseClient, ARTIFACTS_BUCKET),
      jobQueue: new SupabaseJobQueue(ctx.supabaseClient),
    };
  }
  throw new Error(`unknown STORAGE_BACKEND: ${backend}`);
}

/** Resolve a worker-facing storage bundle for a (ownerId, playlistId) pair.
 *  UUID-BOUND ON PURPOSE: playlist_key is unique PER OWNER, not globally, so a
 *  service_role worker must resolve the playlist by its UUID and assert
 *  ownership explicitly here — never look the row up by playlist_key (that
 *  path could silently return another owner's row when keys collide). */
export async function getWorkerStorageBundle(
  serviceClient: SupabaseClient, ownerId: string, playlistId: string,
): Promise<{ blobStore: BlobStore; principal: Principal; ownerId: string; playlistId: string }> {
  validateStorageEnv();
  const { data, error } = await serviceClient
    .from('playlists').select('playlist_key, owner_id').eq('id', playlistId).maybeSingle();
  if (error) throw error;
  if (!data || data.owner_id !== ownerId) {
    throw new Error(`getWorkerStorageBundle: playlist ${playlistId} not owned by ${ownerId}`);
  }
  return {
    blobStore: new SupabaseBlobStore(serviceClient, ARTIFACTS_BUCKET),
    principal: { id: ownerId, indexKey: data.playlist_key },
    ownerId,
    playlistId,
  };
}

/** Derive a Principal from a session. Hard-fails if the Supabase backend is
 *  active but the session has no userId — the caller must not proceed without
 *  an authenticated user in cloud mode.
 *  Routes use getPrincipal(outputFolder) in Stage 1C (local-principal path only). */
export function getPrincipalFromSession(session: { userId: string | null }, indexKey: string): Principal {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'supabase') {
    if (!session.userId) throw new Error('supabase backend: no authenticated session for principal');
    return { id: session.userId, indexKey };
  }
  return localPrincipal(indexKey);
}
