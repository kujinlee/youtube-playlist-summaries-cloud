export type RouteCategory = 'public' | 'anon-allowed' | 'authenticated';

const PUBLIC = ['/', '/about'];
const ANON_ALLOWED = ['/try'];

export function classifyRoute(pathname: string): RouteCategory {
  if (PUBLIC.includes(pathname)) return 'public';
  if (ANON_ALLOWED.some((p) => pathname === p || pathname.startsWith(p + '/'))) return 'anon-allowed';
  return 'authenticated';
}

/** Codex H1: an anon-allowed route auto-provisions an anonymous session on first use. */
export function needsAnonProvision(category: RouteCategory, hasUser: boolean): boolean {
  return category === 'anon-allowed' && !hasUser;
}
