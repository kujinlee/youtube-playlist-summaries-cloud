# Codex Adversarial Review — Stage 1F-c Downloads Plan

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 0 Blocking, 0 High, 1 Medium (leaf-assertion regex). Money-path + route insertion points + filename encoding verified sound.

No Blocking/High findings. The plan’s money-path and route insertion points check out against the real code.

**Medium**
- Task 1 Step 5, import-guard leaf assertion: [docs/superpowers/plans/2026-07-10-stage-1f-c-downloads.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-c-downloads.md:187)
  Code shown:
  ```ts
  expect(src).not.toMatch(/from ['"]@\//);
  ```
  Exact failure: this only catches named/default imports like `import x from '@/...'`. It does not catch bare side-effect imports, dynamic imports, or `require`, e.g.:
  ```ts
  import '@/lib/storage/resolve';
  await import('@/lib/gemini');
  require('@/lib/gemini-cost');
  ```
  That violates D10’s “imports nothing from `@/`” leaf guarantee. The current helper code shown is pure, so this is not an immediate runtime money bug, but the guard being shipped is weaker than the invariant it claims to enforce.

  Fix:
  ```ts
  expect(src).not.toMatch(/\b(?:from\s+|import\s*(?:\(\s*)?|require\s*\(\s*)['"]@\//);
  ```
  Add planted negative controls for bare import, dynamic import, and require from a harmless `@/` path, not just `@/lib/gemini`.

**Verified**
- Owner MD branch is inserted after blob read and before `parseSummaryMarkdown` / `resolveMagazineModel`, so `format=md` short-circuits before charge/model work. Real current model call is [app/api/html/[id]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/html/[id]/route.ts:75).
- Share MD branch is inserted after read-only blob read and before parse / `readFreshMagazineModel`, with the re-check before response. Real current read-model call is [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:54).
- HTML routes through `fileResponse` only on the final 200 path; non-200 owner/share branches are not accidentally forced to status 200.
- Owner HTML helper call omits `referrerPolicy`, so owner gains `nosniff` but no `Referrer-Policy`; share passes `no-referrer`.
- `video.title` is actually typed: [types/index.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/types/index.ts:49).
- `getShareServeContext` already selects `vid.data`, so adding `title` from `vid.data.title` needs no extra query.
- `renderMagazineHtml` already supports `share?: boolean`, and `generateNonce` / `buildSummaryCsp` exist with the expected signatures.
- Filename encoding logic is header-injection safe as written: ASCII fallback uses sanitized base, `filename*` is ASCII-only percent-encoded UTF-8, CR/LF/quote/semicolon do not survive literally.
tokens used
