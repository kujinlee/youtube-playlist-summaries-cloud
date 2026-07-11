import { NextResponse, type NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { getSupabaseEnv } from '@/lib/supabase/env';
import { classifyRoute, needsAnonProvision } from '@/lib/supabase/route-categories';

export async function middleware(request: NextRequest) {
  // Stage 2a T9: local mode is a no-op — must run before ANY Supabase env read /
  // createServerClient call, since local deployments may have no Supabase env at all.
  if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase') return NextResponse.next({ request });

  const response = NextResponse.next({ request });
  const { url, anonKey } = getSupabaseEnv();
  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (list) => list.forEach(({ name, value, options }) => response.cookies.set(name, value, options)),
    },
  });
  const { data: { user } } = await supabase.auth.getUser();     // refreshes the session
  const pathname = request.nextUrl.pathname;
  let category = classifyRoute(pathname);

  // Stage 2a T9: cloud mode gates the app root behind auth. This is a middleware-level
  // override, not a change to `classifyRoute`/PUBLIC_EXACT — local mode still relies on
  // '/' being 'public' there, so PUBLIC_EXACT is left untouched (spec §3.2 / plan T9).
  if (pathname === '/') category = 'authenticated';

  // Codex H1: auto-provision an anonymous session on first visit to an anon-allowed route.
  if (needsAnonProvision(category, !!user)) {
    await supabase.auth.signInAnonymously();                    // sets cookies on `response`
    return response;
  }

  // Stage 2a T9: an already-authenticated (non-anonymous) user visiting /login has nothing
  // to do there. Anonymous users (provisioned at /try) must still be able to reach /login
  // to sign in with Google and upgrade to a real account (pre-merge fix, whole-branch review).
  if (pathname === '/login' && user && !user.is_anonymous) {
    const redirect = request.nextUrl.clone();
    redirect.pathname = '/';
    return NextResponse.redirect(redirect);
  }

  if (category === 'authenticated' && !user) {
    if (pathname.startsWith('/api/')) {
      // API clients get JSON 401, not a redirect to an HTML page. Copy ONLY the cookies
      // getUser() scheduled on `response` (stale-token clears) — NOT the whole header set,
      // which carries the internal `x-middleware-next` continuation signal (review M6).
      const res = NextResponse.json({ error: 'authentication required' }, { status: 401 });
      for (const c of response.cookies.getAll()) res.cookies.set(c);
      return res;
    }
    // Stage 2a T9: unauth PAGE routes now redirect to /login (was '/').
    const redirect = request.nextUrl.clone();
    redirect.pathname = '/login';
    return NextResponse.redirect(redirect);
  }
  return response;
}

export const config = { matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'] };
