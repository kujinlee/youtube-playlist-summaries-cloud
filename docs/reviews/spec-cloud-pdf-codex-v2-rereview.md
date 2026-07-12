# Codex adversarial RE-REVIEW — Cloud Summary PDF spec v2 (round 2)

**Model:** gpt-5.5 · **Date:** 2026-07-11 · **Target:** spec v2 + ADR 0003.
**Counts:** (A) fixes confirmed 6, partial 1. (B) new findings: **Blocking 0, High 1, Medium 1, Low 2.**
**Round is NOT clean** (1 new High) → round 3 required after addressing.

## (A) Round-1 fixes — verification

1. **Nonce-free hash input (B1): CONFIRMED complete.** Hashes `renderMagazineHtml(..., {nonce:
   undefined})` and renders Chromium from the same string. `nonce: undefined` is safe —
   `nonceAttr` returns `''`, no `nonce="undefined"` emitted (`render.ts:56,105,108`;
   `theme.ts:79`). **No other per-request nondeterminism** in `renderMagazineHtml`,
   `parseSummaryMarkdown`, or `MagazineModel`; `generatedAt` lives only in the persisted envelope
   and is not rendered (`serve-doc.ts:87`).
2. **`PDF_RENDER_VERSION` salt (H1/H4): CONFIRMED.**
3. **Two-stage seam preserving `format=md` (H2/H3): CONFIRMED.** `loadSummaryForServe` stops before
   resolve; html route short-circuits md before Stage 2; parity test mandated.
4. **Concurrency cap + single-flight, saturated→503 (H1/H3): CONFIRMED** — but see new High B-1.
5. **Typed `PdfRendererUnavailable`→503 (H2): CONFIRMED.**
6. **Put-atomicity gate + ADR corrected (B2): CONFIRMED** (ADR now says `promote`=copy+delete,
   non-atomic; real fallback = staging keys + atomic manifest pointer).
7. **Medium/Low cluster:** single `get`, timeout writes/returns nothing, `X-Magazine-Stale`,
   `components/VideoMenu.tsx`, softened money invariant — CONFIRMED. **base/key validation — NOT
   genuinely fixed** (timing; see new Medium B-2).

## (B) New findings introduced by the fixes

**B-1 (HIGH) — Single-flight/semaphore cleanup unspecified → permanent-busy after failure.**
If `generateDocPdf` throws/times out and the impl doesn't `inFlight.delete(cacheKey)` + release the
semaphore in `finally`, then: all future requests for `K` await/observe a stale rejected promise
forever, and one failure permanently reduces capacity until process restart.
**Fix:** mandate `try/finally` around both guards — always release the semaphore and always
`inFlight.delete(cacheKey)` after settle. Tests: leader timeout/error clears the map + releases the
slot; next request retries; same-key waiters get 503 on leader failure, not a poison entry.

**B-2 (MEDIUM) — mdKey basename validation happens too late; base-with-slash slips into storage.**
Corrupt `summaryMd.key="nested/foo.md"`: the revised order reads the blob first, and
`assertLogicalKey` allows slashes, so `get(principal, "nested/foo.md")` runs before the basename
check; `base="nested/foo"` → `models/nested/foo.json`, `pdfs/nested/foo…pdf` (the nesting M1 meant
to stop).
**Fix:** a dedicated `assertCloudSummaryMdKey(mdKey)` (single path component, `.md` suffix, non-empty
base, no slash/backslash/`..`/NUL) called **immediately after selecting `mdKey`, before any blob/
model/PDF storage op.**

**B-3 (LOW) — ADR still shows the obsolete key format.** `docs/adr/0003…:45` reads
`pdfs/{base}.{sha256(html).slice}.pdf` (no `PDF_RENDER_VERSION`, not nonce-free). **Fix:** update to
`pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(htmlNonceFree).slice(0,16)}.pdf`.

**B-4 (LOW) — "never serves a stale PDF" is absolute despite 64-bit hash truncation.** Two different
nonce-free HTML strings for the same base could collide on 16 hex chars (negligible, not zero).
**Fix:** say "collision-negligible," or key on the full SHA-256 if the absolute claim matters.
