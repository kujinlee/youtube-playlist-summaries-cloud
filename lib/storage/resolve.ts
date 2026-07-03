import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import { localPrincipal, type Principal } from '@/lib/storage/principal';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { validateStorageEnv, ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { assertOutputFolder } from '@/lib/index-store';

const LOCAL_BUNDLE = { metadataStore: localMetadataStore as MetadataStore, blobStore: localBlobStore as BlobStore };

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

/** The active MetadataStore. Local-only for now; use getStorageBundle() for
 *  env-selected access (Stage 1C). Kept for backward-compat with existing callers. */
export function getMetadataStore(): MetadataStore {
  return localMetadataStore;
}

/** Return a co-selected {metadataStore, blobStore} bundle from STORAGE_BACKEND.
 *  Never mixes local and cloud stores.
 *  - 'local' (default): returns the local singletons.
 *  - 'supabase': validates env (fail-fast), requires ctx.supabaseClient (routes
 *    are not wired in Stage 1C — passing no client throws), then returns Supabase impls. */
export function getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): { metadataStore: MetadataStore; blobStore: BlobStore } {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'local') return LOCAL_BUNDLE;
  if (backend === 'supabase') {
    validateStorageEnv(); // fail-fast on missing env
    if (!ctx?.supabaseClient) throw new Error('supabase backend requires an authenticated client (routes not wired in 1C)');
    return {
      metadataStore: new SupabaseMetadataStore(ctx.supabaseClient),
      blobStore: new SupabaseBlobStore(ctx.supabaseClient, ARTIFACTS_BUCKET),
    };
  }
  throw new Error(`unknown STORAGE_BACKEND: ${backend}`);
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
