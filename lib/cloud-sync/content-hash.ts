import { createHash } from 'crypto';

/**
 * Canonical MD-body normalization for cross-backend hashing (§5.2):
 * LF line endings + exactly one trailing newline + Unicode NFC.
 * Local-file storage (may carry CRLF / trailing blank lines) and Postgres
 * jsonb storage (LF only) must produce byte-identical output here.
 */
export function canonicalizeMd(md: string): string {
  const lf = md.replace(/\r\n?/g, '\n');
  const trimmed = lf.replace(/\n+$/, '');
  return `${trimmed.normalize('NFC')}\n`;
}

/** SHA-256 hex of the canonicalized MD body (§5.2). NOT over human fields. */
export function mdHash(md: string): string {
  return createHash('sha256').update(canonicalizeMd(md), 'utf8').digest('hex');
}
