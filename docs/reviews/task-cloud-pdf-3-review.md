# Task 3 — `PDF_RENDER_VERSION` + `pdfCacheKey` — dual review trail

**Files:** `lib/pdf/pdf-render-version.ts` + test. Base 4707e72 → head 426ac5f.

## Claude code review (sonnet) — impl d13bbd8
**Spec ✅ / Approved.** Verbatim to brief. Key shape exact; `assertLogicalKey` called; deterministic/pure; explicit utf8 encoding; discipline comment specific + honest about the missed-bump blind spot. 4 non-vacuous tests. Minor: `base` safety is a caller contract (only the finished key is checked, by `assertLogicalKey`, which doesn't enforce single-segment) → "pass a note to whoever wires the first caller (Task 8) to confirm `assertCloudSummaryMdKey` runs upstream." 64-bit truncation adequate. Version-test can't catch a missed bump (accepted, documented).

## Codex adversarial review (gpt-5.5) — impl d13bbd8
0 Blocking / 0 High. **Medium:** same `base` point — `pdfCacheKey('a/b', …)` passes `assertLogicalKey` (which only rejects leading `/`, `..` segments, NUL), breaking the `pdfs/{base}` single-object contract and diverging local (`path.join` normalizes `//`) vs Supabase (literal key) cache identity. Fix: validate `base` inside `pdfCacheKey`. **Low:** shape-test regex interpolates `base` unescaped (safe now, fragile). No-finding: version-in-key present + comment honest; sha256 utf8 deterministic; 64-bit fine.

## Controller disposition + fix (426ac5f)
In the real flow the input can't occur (Task 6's `loadSummaryForServe` runs `assertCloudSummaryMdKey`, then `base = mdKey.replace(/\.md$/,'')`). But a reusable key-builder silently accepting a path-breaking `base` is a latent footgun both reviewers flagged. Added a **self-defending single-segment guard** in `pdfCacheKey` (reject `/`, `\`, `..`, NUL, empty → throws) + a 5-case reject test; escaped the shape-test regex (Codex Low). Consistent with the T1/T2 "harden the leaf" approach.

**Final:** 9/9 pdf-render-version tests; full suite 2025/2025; tsc clean. Both passes converged (0 Blocking/High); Medium addressed by the base guard, Low by regex escape.
