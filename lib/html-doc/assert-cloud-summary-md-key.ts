/** A cloud summary md key must be a SINGLE path component ending in `.md` with a non-empty base.
 *  `assertLogicalKey` alone permits embedded slashes, so a corrupt `nested/foo.md` would build
 *  nested `models/…`/`pdfs/…` keys. Reject before any storage op. (Spec round-2 Medium.) */
export function assertCloudSummaryMdKey(mdKey: string): void {
  const bad = typeof mdKey !== 'string' || mdKey.length === 0 ||
    mdKey.includes('/') || mdKey.includes('\\') || mdKey.includes('\0') || mdKey.includes('..') ||
    !mdKey.endsWith('.md') || mdKey.slice(0, -3).length === 0;
  if (bad) throw Object.assign(new Error(`invalid cloud summary md key: ${mdKey}`), { statusCode: 409 });
}
