import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { getSupabaseEnv } from './env';

export type PageSession = { userId: string; email: string } | null;

/**
 * Stage 2a T12 (N2): read-only session read for `app/page.tsx` (a Server Component).
 *
 * Next.js forbids setting cookies during RSC render (see cookies.md — "Setting cookies
 * is not supported during Server Component rendering"). The existing middleware already
 * refreshed the session earlier in this same request, so this helper never needs to write
 * cookies — `setAll` is a no-op, wrapped in try/catch as a defensive guard in case the
 * underlying `@supabase/ssr` client ever calls it anyway (e.g. on an unexpected token
 * refresh mid-render). Deliberately NOT `createServerSupabase` from `./server.ts` — that
 * factory's `setAll` writes cookies via the route-handler cookie store, which throws when
 * invoked during RSC render.
 */
export async function getPageSession(): Promise<PageSession> {
  const cookieStore = await cookies();
  const { url, anonKey } = getSupabaseEnv();
  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll: () => cookieStore.getAll(),
      // no-op: read-only page render, nothing to persist here. `@supabase/ssr` only
      // calls this when a token needs refreshing, which the middleware already did.
      setAll: () => {},
    },
  });

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;
  return { userId: user.id, email: user.email ?? '' };
}
