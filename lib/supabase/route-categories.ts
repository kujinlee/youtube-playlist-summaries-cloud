export type RouteCategory = 'public' | 'anon-allowed' | 'authenticated';

const PUBLIC_EXACT = ['/', '/about', '/login'];
/** OAuth callback + auth-error must be reachable pre-session — classify any /auth/* as public.
 *  `/s/<token>` share links are public by design: the route (app/s/[token]/route.ts) authorizes
 *  ENTIRELY via the share token (getShareServeContext on a service client) and never reads the
 *  user session, so the middleware must not gate it — otherwise a logged-out share recipient is
 *  redirected to /login and never sees the doc. (Pre-existing gap: route-level tests bypass
 *  middleware; fixed here alongside the Stage 2a middleware work.) */
const PUBLIC_PREFIX = ['/auth', '/s'];
const ANON_ALLOWED = ['/try'];

export function classifyRoute(pathname: string): RouteCategory {
  if (PUBLIC_EXACT.includes(pathname)) return 'public';
  if (PUBLIC_PREFIX.some((p) => pathname === p || pathname.startsWith(p + '/'))) return 'public';
  if (ANON_ALLOWED.some((p) => pathname === p || pathname.startsWith(p + '/'))) return 'anon-allowed';
  return 'authenticated';
}

/** Codex H1: an anon-allowed route auto-provisions an anonymous session on first use. */
export function needsAnonProvision(category: RouteCategory, hasUser: boolean): boolean {
  return category === 'anon-allowed' && !hasUser;
}
