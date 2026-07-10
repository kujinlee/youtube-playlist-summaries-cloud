# Whole-Branch Holistic Review — Stage 1F-b (share tokens)

**Range:** `master` 288f591 .. HEAD · 7 SDD tasks + per-task dual-review trail.
**Reviewers:** Claude (opus) + Codex (gpt-5.5), independent holistic passes.
**Verification:** `tsc` clean; unit 1792/1792; integration 216/218 (+2 pre-existing skips). DB-free set + tsc reproduced green in-review.

## Verdict: READY TO MERGE (both passes: 0 Critical/Blocking, 0 High, 0 Medium)

Money bounded end-to-end, service_role isolated + confined, the 1F-a owner charging path preserved verbatim, interfaces aligned across all seven tasks, no existing consumer regresses.

## What holds end-to-end (verified by both reviewers)

1. **Money bounded (central invariant).** The anon lifecycle `route → getShareServeContext → readFreshMagazineModel` has NO reachable edge to `reserve_serve_model` / `generateMagazineModel` / `spend_ledger` / `serve_model_charge`. `route.ts` makes no `.rpc` call; `serve.ts` is `.select()`-only; `read-model.ts` is a genuine generate-free leaf (returns `not_ready`→503 on absent/stale). Enforced by three independent legs: runtime `SupabaseClient.prototype.rpc` spy + byte-compared ledger snapshots across every branch (B18), static grep guard with planted subpath negative-controls (B18b), transitive import-graph walk (B18c).
2. **Owner path preserved.** The Task-1 `serve-doc.ts` refactor (merged 1F-a code) delegates freshness to `readFreshMagazineModel` but leaves the reserve→generate→writeModelEnvelope→charge sequence and the status switch (denied/in_flight/attempts_exhausted/at_capacity/reserved) untouched. No regression to already-shipping money behavior.
3. **Isolation holds against a forged token row.** `getShareServeContext` resolves by the GLOBAL `(id, owner_id)` (never `playlist_key`) + re-asserts owner on both playlist and video; the confused-deputy test mints A-owner/B-coords directly via service_role and is denied with no B leak (load-bearing — proven by negative control). Blob reads scoped `{id: ownerId, indexKey: playlistKey} + mdKey` through the same key-guarded store as the owner route.
4. **service_role confined.** `ALLOWED_SERVICE_IMPORTERS` is exact-path (not prefix); the confinement test now writes an unauthorized reacher under `app/` and asserts `findServiceImporters()` flags it. `/s/[token]` is the only new service_role entrypoint.
5. **No interface drift / no regression.** tsc clean; `readFreshMagazineModel`/`getShareServeContext`/`ReadOnlyBlobStore`/`generateShareToken`(hex)/RPC arg types all line up; `render.ts`'s `share?` opt defaults false so the four other callers emit owner metas unchanged; `GENERATOR_VERSION` re-exported for back-compat.
6. **Auth boundary intact.** mint/revoke/revoke-all session-only (401 gate) via definer RPCs; `reserve_serve_model` untouched. `token_hash` consistently 64-char lowercase hex across token helper / migration / RPCs / route / tests.

## Findings
- **Critical/High/Medium:** none (both passes).
- **Low (Codex) — FIXED before PR:** a corrupted persisted `artifacts.summaryMd.key` (e.g. `../x.md`) made `assertLogicalKey` throw during the anon blob read with no catch → 500 instead of coarse 404. Fixed: catch statusCode-400 (bad key) → `notFound()`, rethrow genuine infra errors. (share-route 12/12 still green after fix.)

## Minor follow-ups (non-blocking — recorded for a future slice / 1G)
- `app/api/share/route.ts` — TTL 400 validation runs before the 401 auth check (cosmetic; owner-independent input, no leak).
- `app/api/share/route.ts` — all `create_share_token` errors collapse to 404 (coarse-by-design for unowned/unpromoted/bounds, but a transient infra error also shows as 404 to the owner; consider server-side logging of genuine errors).
- `lib/share/serve.ts` — the `pl.owner_id !== tok.owner_id` / `vid.owner_id !== tok.owner_id` re-asserts are unreachable given the `.eq('owner_id')` filters (harmless defense-in-depth).
- Migration divergence note: `0013 create_share_token` join adds `p.owner_id = v.owner_id` that `0012 reserve_serve_model` omits — 0013 is strictly stricter (no gap), worth a note if ever reconciled.
- Spec §9 pre-existing 1G follow-ups still stand: anonymous-route rate-limit / HTML cache; GENERATOR_VERSION-bump staleness heal-at-mint; orphaned token-row GC; token-entropy-at-DB (owner-self-harm) residual.
