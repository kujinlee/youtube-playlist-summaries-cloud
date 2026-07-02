import { NextResponse, type NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { getSupabaseEnv } from '@/lib/supabase/env';
import { classifyRoute, needsAnonProvision } from '@/lib/supabase/route-categories';

export async function middleware(request: NextRequest) {
  const response = NextResponse.next({ request });
  const { url, anonKey } = getSupabaseEnv();
  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (list) => list.forEach(({ name, value, options }) => response.cookies.set(name, value, options)),
    },
  });
  const { data: { user } } = await supabase.auth.getUser();     // refreshes the session
  const category = classifyRoute(request.nextUrl.pathname);

  // Codex H1: auto-provision an anonymous session on first visit to an anon-allowed route.
  if (needsAnonProvision(category, !!user)) {
    await supabase.auth.signInAnonymously();                    // sets cookies on `response`
    return response;
  }

  if (category === 'authenticated' && !user) {
    const redirect = request.nextUrl.clone();
    redirect.pathname = '/';
    return NextResponse.redirect(redirect);
  }
  return response;
}

export const config = { matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'] };
