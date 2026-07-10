import { randomBytes, createHash } from 'crypto';

/** 256-bit opaque bearer token (base64url, unpadded) + its sha256 hash (lowercase hex) for
 *  at-rest storage. Hex (not a Buffer) because token_hash is a `text` column and a Buffer would
 *  not serialize to it over PostgREST (see Global Constraints). */
export function generateShareToken(): { token: string; tokenHash: string } {
  const token = randomBytes(32).toString('base64url');
  return { token, tokenHash: hashShareToken(token) };
}

export function hashShareToken(token: string): string {
  return createHash('sha256').update(token).digest('hex');
}
