import 'server-only';
import { createClient } from '@supabase/supabase-js';
import { getSupabaseEnv, getServiceRoleKey } from './env';

/** service_role client with BYPASSRLS. Server-only; never import from client/route code
 *  reachable by the browser. Unused in 1B. */
export function createServiceClient() {
  if (typeof window !== 'undefined') {
    throw new Error('createServiceClient() must never run in a browser (server-only)');
  }
  const key = getServiceRoleKey();
  const { url } = getSupabaseEnv();
  return createClient(url, key, { auth: { autoRefreshToken: false, persistSession: false } });
}
