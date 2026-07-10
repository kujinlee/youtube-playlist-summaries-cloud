# Claude Adversarial Review — Stage 1F-b Implementation Plan (v1)

**Reviewer:** Claude (opus), independent · **Date:** 2026-07-10.
**Verdict:** 2 Blocking, 3 High, 2 Medium, 1 Low (all buildability/correctness; the never-charges + confused-deputy designs verified sound).

## Blocking
- **B1 — `export { GENERATOR_VERSION } from './constants'` breaks `render.ts`'s own compile.** A re-export creates no local binding, but `render.ts:112` uses the value locally in the non-share `<meta generator>` branch → `TS2304`. **Fix:** `import { GENERATOR_VERSION } from './constants'; export { GENERATOR_VERSION };`
- **B2 — the repo has NO ESLint infra** (no `lint` script, no `eslint*` dep, no config file). Task 7 Step 5's `no-restricted-imports` and the `npm run lint` gate (Step 6 + Verification §4) are unbuildable. The money invariant survives (grep guard B18b + module-graph B18c + runtime B18 stand). **Fix:** descope the ESLint half of B18b to the grep guard only; delete `npm run lint` from Step 6 + Verification §4; update B18b / Success-Criterion-2 wording. (Or add eslint as explicit scope — not recommended for this slice.)

## High
- **H1 — the route's own comment (`// NEVER import: … resolveMagazineModel, generateMagazineModel`) trips its own import-guard regex** `/\bresolveMagazineModel\b/` applied to raw file text → the guard fails on `app/s/[token]/route.ts` itself. **Fix:** reword the comment to not contain the forbidden identifiers, or scope the regexes to import/call syntax.
- **H2 — `seedPromotedDoc` inserts non-existent/omitted columns** (`title` should be `playlist_title`; `playlist_url` is NOT NULL, omitted) → every integration test errors at seed. **Fix:** `seed.ts` ALREADY EXISTS with `seedPlaylist` + `seedPromotedVideo` + `seedSummaryBlob` matching the real schema — delete the invented helper and compose those.
- **H3 — `git ls-files` sees only tracked files**, so `import-guard.test.ts` scans an empty set before the Step-7 commit → vacuous pass, and the "add a bad import to confirm it fails" sanity check won't fail. **Fix:** enumerate via filesystem glob; assert `shareSources.length > 0` and that the route file is present.

## Medium
- **M1 — `ARTIFACTS_BUCKET` import path wrong** (`@/lib/storage/supabase/constants` doesn't exist). Real: `@/lib/supabase/storage-env` (see `resolve.ts:11`, `seed.ts:4`). tsc break → arguably Blocking.
- **M2 — the `render-share` test model fixture is not a valid `MagazineModel`** (`{heading, body}` but `render.ts:92/98` read `m.bullets[].text` / `m.lead`) → throws before any assertion. **Fix:** `sections: [{ lead: 'l', bullets: [{label,text}×3] }]`.

## Low
- **L1 — `isFresh` import into `serve-doc.ts` is dead** after the refactor (both read sites use `readFreshMagazineModel`). `tsconfig` lacks `noUnusedLocals` so tsc won't fail; cosmetic. **Fix:** import only `readFreshMagazineModel`.

## Verified correct (no action)
Owner-path B1/B2/B3 semantics preserved by the two `readFreshMagazineModel` substitutions; `GENERATOR_VERSION` still imported for `writeModelEnvelope`; `ReadOnlyBlobStore = Pick<BlobStore,'get'>` correct + `localBlobStore` assignable; migration 0013 promoted predicate matches `0012:44-47`; grants/revokes complete; `force`-RLS + service_role-only + definer/`auth.uid()` mirror 0012 (B23 holds); **no money path** on the share route (getShareServeContext is select-only; readFreshMagazineModel never generates; double-resolve for D14 stays read-only — no double-charge); `createServiceClient()`/`createServerSupabase` signatures match; `SupabaseBlobStore(client, bucket)` + `get(principal, key)` + the get-only wrapper sound; `parseSummaryMarkdown` can throw (Task 7 try/catch justified); confused-deputy guard resolves by id then asserts owner (never `readIndex`/`playlist_key`).

**Net:** none is a money hole or isolation break — the security designs are sound; all findings stop an implementer following the plan literally (tsc B1/M1, missing lint infra B2, self-failing guards H1/H3, broken seed H2, crashing fixture M2).
