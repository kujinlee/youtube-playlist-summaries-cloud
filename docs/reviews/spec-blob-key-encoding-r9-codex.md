<!-- codex-review: model=gpt-5.5 -->

**Findings**

Medium — share serving still bypasses the summary-key guard while deriving `base` from `mdKey`.

Evidence: [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:120)

```ts
/** A single path component. Rejects separators in every form, control characters,
 *  traversal, and over-long keys. Says nothing about ASCII, letters, or readability. */
export function isServableSummaryKey(key: string): boolean {
```

Owner/dig serve go through that boundary:

```ts
assertCloudSummaryMdKey(mdKey);
```

[lib/html-doc/serve-summary-core.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-summary-core.ts:61)

But share context returns the key without the guard:

```ts
const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
if (!mdKey) return denied;
```

[lib/share/serve.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/share/serve.ts:47)

and the route then derives from it:

```ts
mdBytes = await readOnly.get(principal, ctx.mdKey);
```

```ts
const base = ctx.mdKey.replace(/\.md$/, '');
```

[app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:50), [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:78)

Concrete failure scenario: a promoted row with `artifacts.summaryMd.key = "nested/foo.md"` is rejected by owner serve as corrupt, but share serve reads `nested/foo.md` and probes `models/nested/foo.json`. I do not see a non-ASCII break or money loss here, so this is not Blocking, but it leaves the security-relevant guard non-uniform.

Proposed fix: call `isServableSummaryKey` / `assertCloudSummaryMdKey` in `getShareServeContext` before returning `mdKey`, mapping failure to share’s coarse denial.

Low — the predicate admits bidi controls into vault filenames.

Evidence: [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:137)

```ts
for (const s of [key, key.normalize('NFKC')]) {
  if (s.includes('/') || s.includes('\\') || s.includes('..')) return false;
  if (/[\x00-\x1f\x7f]/.test(s)) return false;   // C0 + DEL
  if (/%2f|%5c/i.test(s)) return false;
}
```

Verbatim local filenames enter the index:

```ts
const summaryMd = file;
```

[lib/pipeline.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/pipeline.ts:104)

and sync copies that key verbatim:

```ts
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
```

[lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:263)

Probe result: `isServableSummaryKey("001_safe\u202Efdp.md") === true`. That does not become `/`, `\`, `..`, or a URL escape under NFKC/NFD/NFKD, but it is a filesystem/display spoofing surprise when hydrated into a vault.

Proposed fix: reject bidi controls specifically, e.g. `[\u202A-\u202E\u2066-\u2069]`, in both raw and NFKC passes. Do not reject all `Cf`; ZWJ and variation selectors are legitimate in some visible text/emoji titles.

**Checked**

I ran the v9 predicate against ASCII, Hangul, Japanese, NFC/NFD accented Latin, spaces, emoji, lone surrogate, slash/backslash, `%2f/%5c`, fullwidth slash, `℀`, folded dot-dot, C0/DEL, bidi, ZWJ, variation selectors, and combining overlays. I also scanned all Unicode scalar values admitted by the predicate for NFD/NFKD forms introducing `/`, `\`, `..`, C0/DEL, or `%2f/%5c`; no misses found.

APFS probe confirmed the ordering premise: `writeFileSync(alias, { flag: 'wx' })` returns `EEXIST` for an NFC/NFD alias, while `renameSync` overwrites it.

No Blocking or High findings. The central design holds; remaining items are follow-ups.

CONVERGED
