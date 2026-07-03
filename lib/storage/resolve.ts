import type { MetadataStore } from '@/lib/storage/metadata-store';
import { localPrincipal, type Principal } from '@/lib/storage/principal';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { assertOutputFolder } from '@/lib/index-store';

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

/** The active MetadataStore. Local-only for now; env-selected once the
 *  Supabase implementation lands (Stage 1C). */
export function getMetadataStore(): MetadataStore {
  return localMetadataStore;
}
