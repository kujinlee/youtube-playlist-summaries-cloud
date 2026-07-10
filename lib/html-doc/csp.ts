import crypto from 'crypto';

/** ≥128-bit base64 nonce, one per response. */
export function generateNonce(): string {
  return crypto.randomBytes(16).toString('base64');
}

/** Strict, owner-private summary CSP — nonce-based, no unsafe-*. */
export function buildSummaryCsp(nonce: string): string {
  return [
    "default-src 'none'",
    `script-src 'nonce-${nonce}'`,
    `style-src 'nonce-${nonce}'`,
    "img-src 'none'",       // summary emits no images, only external YouTube links
    "base-uri 'none'",
    "object-src 'none'",
    "frame-ancestors 'none'", // block clickjacking of an owner-private doc
    "form-action 'none'",
  ].join('; ');
}
