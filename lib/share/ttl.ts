export const MAX_SHARE_TTL_DAYS = 365;
const DAY_MS = 86_400_000;

/** Route-side TTL contract (spec §4.4): omitted → 30d; 'never' → null; integer 1..365 → that
 *  many days; anything else → invalid (route returns 400). The RPC re-validates the bound. */
export function resolveExpiry(
  ttlDays: number | 'never' | undefined,
): { ok: true; expiresAt: Date | null } | { ok: false } {
  if (ttlDays === undefined) return { ok: true, expiresAt: new Date(Date.now() + 30 * DAY_MS) };
  if (ttlDays === 'never') return { ok: true, expiresAt: null };
  if (typeof ttlDays === 'number' && Number.isInteger(ttlDays) && ttlDays >= 1 && ttlDays <= MAX_SHARE_TTL_DAYS) {
    return { ok: true, expiresAt: new Date(Date.now() + ttlDays * DAY_MS) };
  }
  return { ok: false };
}
