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

/**
 * CSP for the INTERACTIVE cloud dig-deeper doc — the summary CSP plus `connect-src 'self'`.
 * The injected poll engine (digCloudScript) drives the whole feature via same-origin fetch:
 * POST /api/videos/<id>/dig/<sec>?playlist=…, GET /api/videos/<id>/dig-state?playlist=…, and a
 * re-fetch of location.href for the section swap. Under `default-src 'none'` with no connect-src,
 * every one of those is blocked and the doc is inert in a real browser — so this variant adds
 * exactly `connect-src 'self'` (same-origin only) and nothing else. The static summary/share docs
 * keep buildSummaryCsp (no connect-src) since they never fetch.
 */
export function buildDigCsp(nonce: string): string {
  return [
    "default-src 'none'",
    `script-src 'nonce-${nonce}'`,
    `style-src 'nonce-${nonce}'`,
    "img-src 'none'",
    "connect-src 'self'",   // the dig poll engine fetches same-origin /api/... and location.href
    "base-uri 'none'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'none'",
  ].join('; ');
}
