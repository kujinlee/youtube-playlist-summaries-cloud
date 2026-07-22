import { NextResponse, type NextRequest } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';

// Task 5 review (Important): the createServerSupabase factory cannot forward the
// anti-cache headers @supabase/ssr wants, so a response carrying auth Set-Cookie
// must set them here — else a CDN/proxy could cache the session cookie and serve
// it to another user.
function noStore(res: NextResponse): NextResponse {
  res.headers.set('Cache-Control', 'private, no-store, no-cache, must-revalidate, max-age=0');
  return res;
}

// Behind a reverse proxy (Fly), `request.url`'s host is the server's INTERNAL bind address
// (`0.0.0.0:3000`), not the public origin. A redirect built from it sends the browser to an
// unreachable address — the 2026-07-22 first-login failure, where OAuth succeeded but the
// post-exchange redirect landed on `https://0.0.0.0:3000`. Fly sets `x-forwarded-host` /
// `x-forwarded-proto` to the public values; prefer those, and fall back to the request origin for
// local dev (no proxy). This is Supabase's documented callback pattern.
export function publicOrigin(request: NextRequest): string {
  const host = request.headers.get('x-forwarded-host');
  if (!host) return request.nextUrl.origin;
  const proto = request.headers.get('x-forwarded-proto') ?? 'https';
  return `${proto}://${host}`;
}

// Only ever redirect to a PATH on our own origin. A `next` that is an absolute or protocol-relative
// URL (`?next=https://evil.com`, `?next=//evil.com`) would otherwise be an open redirect straight
// out of the auth flow — worth hardening in a route that just minted a session.
export function safeNext(nextParam: string | null): string {
  const n = nextParam ?? '/';
  return n.startsWith('/') && !n.startsWith('//') ? n : '/';
}

export async function GET(request: NextRequest) {
  const origin = publicOrigin(request);
  const code = request.nextUrl.searchParams.get('code');
  const next = safeNext(request.nextUrl.searchParams.get('next'));
  if (code) {
    const cookieStore = await cookies();
    const supabase = createServerSupabase(cookieStore as unknown as CookieStore);
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return noStore(NextResponse.redirect(new URL(next, origin)));
  }
  // Codex M4: no code, or a failed exchange, must NOT redirect as if successful.
  return noStore(NextResponse.redirect(new URL('/auth/auth-error', origin)));
}
