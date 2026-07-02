import { NextResponse, type NextRequest } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase } from '@/lib/supabase/server';

// Task 5 review (Important): the createServerSupabase factory cannot forward the
// anti-cache headers @supabase/ssr wants, so a response carrying auth Set-Cookie
// must set them here — else a CDN/proxy could cache the session cookie and serve
// it to another user.
function noStore(res: NextResponse): NextResponse {
  res.headers.set('Cache-Control', 'private, no-store, no-cache, must-revalidate, max-age=0');
  return res;
}

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get('code');
  const next = request.nextUrl.searchParams.get('next') ?? '/library';
  if (code) {
    const cookieStore = await cookies();
    const supabase = createServerSupabase(cookieStore as never);
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return noStore(NextResponse.redirect(new URL(next, request.url)));
  }
  // Codex M4: no code, or a failed exchange, must NOT redirect as if successful.
  return noStore(NextResponse.redirect(new URL('/auth/auth-error', request.url)));
}
