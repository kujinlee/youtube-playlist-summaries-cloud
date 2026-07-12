/** A cloud summary md key must be a SINGLE path component matching the shape the ingestion
 *  pipeline produces: `${padSerial(serial)}_${slugify(title)}.md`. `slugify` (lib/slugify.ts)
 *  emits ONLY unicode letters/numbers and `-` — it replaces every other character (slashes,
 *  whitespace, control chars, dots, `%`, homoglyph separators) with `-` — and the serial prefix
 *  is digits + `_`. So this guard ALLOWLISTS exactly that shape (unicode-aware: a Korean/CJK base
 *  like `0007_한국어.md` legitimately passes) with a length bound, rather than denylisting known-bad
 *  characters. It is the hard boundary before `models/{base}.json` / `pdfs/{base}.pdf` keys are
 *  built: a corrupt `nested/foo.md`, an encoded (`%2f`) or homoglyph (`／`) separator, embedded
 *  whitespace/control chars, or an over-long key cannot match the pattern and is rejected with a
 *  409. `assertLogicalKey` alone only rejects a leading `/` and `..` segments, so `nested/foo.md`
 *  slips past it — this guard closes that gap. (Spec round-2 Medium; allowlist hardening per Task-2
 *  Codex review — provably no regression vs `slugify`'s output, which never emits anything outside
 *  the allowed class.) */
const CLOUD_SUMMARY_MD_KEY = /^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u;

export function assertCloudSummaryMdKey(mdKey: string): void {
  if (typeof mdKey !== 'string' || !CLOUD_SUMMARY_MD_KEY.test(mdKey)) {
    throw Object.assign(new Error(`invalid cloud summary md key: ${mdKey}`), { statusCode: 409 });
  }
}
