/**
 * The dev-login gate helper (#13). Returns true ONLY when the Supabase URL points at the
 * local dev stack (localhost / 127.0.0.1). Fail-closed: absent, malformed, or any other
 * host → false. Keyed on the URL host (NOT NODE_ENV) so a local prod-build stays enabled
 * while hosted prod (…supabase.co) is always off.
 */
export function isLocalSupabaseUrl(url: string | undefined | null): boolean {
  if (!url) return false;
  try {
    const host = new URL(url).hostname;
    return host === 'localhost' || host === '127.0.0.1';
  } catch {
    return false;
  }
}
