import { getSupabaseEnv } from './env';

export const ARTIFACTS_BUCKET = 'artifacts';

/** Throws with /Missing required env/ if NEXT_PUBLIC_SUPABASE_URL or
 *  NEXT_PUBLIC_SUPABASE_ANON_KEY are absent. Called by getStorageBundle()
 *  as a fail-fast gate before constructing any Supabase client. */
export function validateStorageEnv(): void { getSupabaseEnv(); }
