// Server-only. The dev-login gate (#13). Two required conditions, fail-closed:
//   1. DEV_LOGIN_ENABLED === 'true'  — a server-only flag (NOT NEXT_PUBLIC_*, so never
//      build-inlined; defaults closed, so it cannot fail open on a mis-set env). Set only
//      in local .env.local; never in prod.
//   2. the runtime Supabase URL is local — defense-in-depth (closes the gate even if the
//      flag ever leaked to a prod runtime).
import 'server-only'; // mechanically forbid importing this gate from client code (build-time error)
import { isLocalSupabaseUrl } from '@/lib/supabase/is-local-url';

export function devLoginEnabled(): boolean {
  if (process.env.DEV_LOGIN_ENABLED !== 'true') return false;
  // Bracket access is a genuine RUNTIME read — Next's DefinePlugin only inlines the LITERAL
  // process.env.NEXT_PUBLIC_SUPABASE_URL, not process.env['…']. Do NOT switch to
  // getSupabaseEnv() here: it throws on a missing var (fail-open-to-500); this maps
  // undefined → false (fail-closed-to-404).
  return isLocalSupabaseUrl(process.env['NEXT_PUBLIC_SUPABASE_URL']);
}
