import { createHash } from 'crypto';

/** The physical alphabet Supabase Storage accepts, measured in §2.1. */
export const SAFE = /^[A-Za-z0-9._-]+$/;
/** Measured Storage ceiling, per path SEGMENT and not per path (§2.2, premise P2). */
export const LIMIT = 255;

const HEAD = /^[A-Za-z0-9._-]+/;
const EXT = /\.[A-Za-z0-9]{1,8}$/;

/**
 * Map ONE logical path segment to a physical one. Total, deterministic, never inverted —
 * `list()` re-attaches the caller's logical prefix instead (§3.3), which is what makes a
 * one-way hash legal here.
 *
 * utf16le, NOT utf8: Node maps every unpaired surrogate to U+FFFD on the way to a utf8
 * buffer, so two DIFFERENT lone surrogates would hash to the same physical key and one
 * video's blob would overwrite another's. Reachable because `slugify`'s slice cuts UTF-16
 * code units (§3.2).
 */
export function encodeSegment(s: string): string {
  if (s === '') return '';
  if (SAFE.test(s) && s.length <= LIMIT) return s;
  const head = (HEAD.exec(s)?.[0] ?? '').slice(0, 32);
  const ext = EXT.exec(s)?.[0] ?? '';
  const digest = createHash('sha256').update(Buffer.from(s, 'utf16le')).digest('base64url');
  return `${head}=h${digest.slice(0, 22)}${ext}`;
}
