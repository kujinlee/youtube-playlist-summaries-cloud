import { createServerClient } from '@supabase/ssr';
import { getSupabaseEnv } from './env';

export type CookieStore = {
  getAll(): { name: string; value: string }[];
  set(name: string, value: string, options?: Record<string, unknown>): void;
};

/** RLS-scoped to the request's session. Never uses the service role. */
export function createServerSupabase(cookies: CookieStore) {
  const { url, anonKey } = getSupabaseEnv();
  return createServerClient(url, anonKey, {
    cookies: {
      getAll: () => cookies.getAll(),
      setAll: (list, _headers) =>
        list.forEach(({ name, value, options }) =>
          cookies.set(name, value, options as Record<string, unknown>),
        ),
    },
  });
}
