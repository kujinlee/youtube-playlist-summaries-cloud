# Claude Adversarial Review — Stage 1F-c Downloads Plan

**Reviewer:** Claude (opus) · **Date:** 2026-07-10.
**Verdict:** 0 Blocking, 1 High, 2 Medium, 2 Low. Money/isolation/header-injection cores sound and match real code.

## High
- **H1 — `seedPromotedVideo` writes no `title`, so the title-derived filename tests (C8/C13/C14/C21) would be vacuous or unwritable.** `seed.ts:23-47` `data` blob has no `title`; `readIndex` doesn't zod-validate (`supabase-metadata-store.ts:33`), so `video.title`/`ctx.title` = undefined → `filename*` silently falls back to base. C21 (hostile CRLF/quote title) can't be seeded via the helper at all. **Fix:** add optional `title?` to `seedPromotedVideo` (write `data.title`, default `'My Doc Title'`), or use custom `svc.from('videos').insert` for those cases (C21 needs a custom insert regardless). **Mitigation (why not Blocking):** the injection/encoding safety is fully covered at the UNIT level in Task 1's `file-response.test.ts` (CRLF/quote/`;`/unicode asserted directly) — the security property is tested; route-level C21 is redundant. Test-completeness defect, not a shipped bug.

## Medium
- **M1 — leaf-assertion regex `not.toMatch(/from ['"]@\//)` misses bare side-effect `@/` imports** (`import '@/lib/gemini';`), dynamic imports, and require; and Task 1 Step 6's sanity claim ("leaf assertion fires on a bare import") is factually wrong (no `from`). The whole guard still fails via the forbidden scan, but the leaf assertion — described as "the real protection" — has a blind spot. **Fix:** `not.toMatch(/['"]@\//)` (the file legitimately imports nothing) or `/\b(?:from\s+|import\s*\(?\s*|require\s*\(\s*)['"]@\//`; add planted negative controls (bare/dynamic/require); correct Step 6 wording. *(Codex flagged the same as its only Medium.)*
- **M2 — C16 (cross-owner isolation) and C12 (share md missing-blob) not in Task 4's explicit test list.** Verification item 5 + self-review require them. Code inherits isolation correctly (md branch reuses the unchanged confused-deputy guard + D12 re-check) — no break introduced — but the md format isn't explicitly proven isolated. **Fix:** add a C16 test (`format=md` AND `format=html`, B's token → A's doc → 404) + a C12 `format=md` missing-blob 404.

## Low
- **L1 — `_req`→`req` rename inconsistent with the snippet** (Task 4 Step 3 says rename but code reads `_req.url`). **Fix:** drop the rename, keep `_req.url` (a `_`-prefixed param that's now used compiles fine).
- **L2 — the "IDENTITY COHERENCE" comment is orphaned when `base` moves up** (Task 3). Cosmetic; move the comment with the declaration or leave a pointer.

## Verified clean (both reviewers)
Money — MD never charges on either path (owner branch before `resolveMagazineModel:75`, share before `readFreshMagazineModel:54`); html-via-fileResponse runs the money path exactly once before wrapping; B18 money proof genuinely extends to `format=md` (new cases inside the afterEach/afterAll spy+ledger block). Non-200 branches stay off `fileResponse` (always-200). Owner gains `nosniff` but NOT `Referrer-Policy`; share keeps `no-referrer`. Filename injection/undici safety: `asciiSafe` collapses all ≥0x80 → provably printable-ASCII `filename=`; `encodeRFC5987` allowlist == RFC 5987 attr-char, `-` at edge, UTF-8 bytes → `%HH`; whole Content-Disposition is ASCII. D12 share re-check read-only, no double-charge. `video.title` typed; `getShareServeContext` already selects `vid.data`. `file-response.ts` is a true leaf.

## Plan-fix list (apply as plan v2 before SDD)
1. seed `title` (H1) — Task 2/3/4 test setup; C21 custom insert.
2. leaf-assertion regex + Step 6 wording + planted controls (M1) — Task 1.
3. add C16 + C12 tests (M2) — Task 4.
4. `_req` consistency (L1) — Task 4.
5. move IDENTITY COHERENCE comment (L2) — Task 3.
