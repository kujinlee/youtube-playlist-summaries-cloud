# Claude Re-Review (Round 2) — Stage 1F-b Share Tokens spec v2

**Reviewer:** Claude (opus), independent · **Date:** 2026-07-10 · scope: verify v1 findings genuinely closed + hunt for defects the v2 fixes introduced.
**Verdict:** PART A — all v1 Blocking/High genuinely fixed; 2 Mediums PARTIAL (owner-self-harm residual). PART B — **1 new High (B-H1)**, 3 Medium, 4 Low. NOT converged (a new High mandates another round).

## PART A — v1 findings verified
All v1 Blocking + High **FIXED** and confirmed against code:
- **Blocking (no charge-free resolver) → FIXED** by D13 + B18/B18b (but see B-H1 on *where* the helper lives).
- **Revocation in-flight → FIXED** by D14/B10b (residual window µs, `no-store`-bounded).
- **Unsafe service-role resolution → FIXED, over-determined:** `videos` has composite FK `(playlist_id, owner_id) → playlists(id, owner_id)` (`0001:32`), so a video's owner cannot differ from its playlist's owner; `readIndex` correctly avoided.
- **Read-only not enforced → FIXED:** `Pick<BlobStore,'get'>`, `get()` is a pure download (`supabase-blob-store.ts:23-27`). (Codex notes the runtime-wrapper nuance — see B-M/agreement.)
- **Referer leak → FIXED:** `Referrer-Policy: no-referrer` (D10/B21).
- **share:true / strip-set → FIXED:** §4.5 real option, additive, won't break existing render tests.
- **GENERATOR_VERSION, DoS, `?? 30` null, owner-match → FIXED** (§9, D12, §4.4, D15).
- PARTIAL: **TTL hostile values** and **caller-chosen hash entropy** — residual is owner-self-harm via direct RPC (see B-M1/B-M3).

## PART B — new defects

### High
**B-H1 — D13/§1 co-locate `readFreshMagazineModel` in `serve-doc.ts`, which itself imports `generateMagazineModel` (`serve-doc.ts:7`) and calls `reserve_serve_model` (`:58`) — directly contradicting B18b and defeating the structural "never charges" guarantee.** If the helper lives in `serve-doc.ts`, the share route's import of it pulls the Gemini/reserve module into the share graph; B18b's grep for `generateMagazineModel` in the helper module trips (unpassable), or gets weakened to only scan the route file (re-importing `resolveMagazineModel` then one line away, ungated). **Fix:** put `readFreshMagazineModel` + `isFresh` in a **new leaf module** `lib/html-doc/read-model.ts` that imports only `readModelEnvelope`/`GENERATOR_VERSION`, never `@/lib/gemini` or any `reserve_*`. `serve-doc.ts` imports the helper from there; the share route imports only `read-model.ts`. State the module boundary so B18b is satisfiable and the share bundle is provably generate-free.

### Medium
- **B-M1 — TTL trust boundary moved to the wrong side:** the RPC now takes an unvalidated `p_expiry timestamptz`; `MAX_SHARE_TTL_DAYS` is enforced only in the route, so a direct `authenticated` RPC call (`'9999-12-31'`) bypasses D7. Owner-self-harm only, but contradicts D7/§4.2's "one testable place" and regresses the exact v1 Codex Medium (which asked to bound TTL in the RPC/table). **Fix:** DB-side guard `p_expiry is null OR (p_expiry > now() AND p_expiry <= now() + MAX_SHARE_TTL_DAYS*interval)`. (Codex ranks this **High** — adopt High.)
- **B-M2 — B18b import-grep doesn't cover the `.rpc('reserve_serve_model')` string, and the share route builds its own `service_role` client** — a dev can charge with zero forbidden *imports*. Also `reserve_serve_model` is a DB RPC, not a JS symbol, so "must not import reserve_serve_model" is category-confused. B18 runtime row-unchanged is the real backstop. **Fix:** B18b = ESLint `no-restricted-imports` on `app/s/**` + share helpers (forbid `resolveMagazineModel`/`generateMagazineModel`) **plus** a grep for the RPC string `reserve_serve_model`/`.rpc(`; reword D13; lean on B18 runtime spies as the guarantee.
- **B-M3 — token-hash entropy unenforced at the DB boundary:** 32-byte CHECK ≠ 256-bit entropy; a direct-RPC caller can hash a weak token. Owner-self-harm. **Fix:** weaken D6's absolute "256-bit random ⇒ not enumerable" to "route-generated tokens are 256-bit random; a direct-RPC caller can only self-weaken their own links (out of threat scope)."

### Low
- **B-L1** — `resolveMagazineModel`'s in-flight re-read (`serve-doc.ts:66`) is a second `readModelEnvelope+isFresh` site the refactor should route through `readFreshMagazineModel` (or accept duplication explicitly) — the two-call-site drift smell H1 fixed.
- **B-L2** — §4.3 step 3 must specify `mdKey = artifacts.summaryMd.key ?? video.summaryMd` (the owner path's H-2 precedence, `route.ts:55-58`), else the share path can drift.
- **B-L3** — strip-set footer ambiguity: say whether share mode drops the whole `<footer>` or only the `<code>${sourceMd}</code>`, so B22 is exact.
- **B-L4** — D14 "re-assert promoted if required" is vague; commit to re-reading the video row at step 5 or state un-promote is eventual (next request) — don't hedge.

## Convergence signal
**Not converged** — a new High (B-H1) created by the v1 Blocking fix meeting the new B18b test. After B-H1 (leaf module) + B-M1 (DB-side TTL) + B-M2 (guard rewording) close, re-run the dual pass scoped to: (a) the helper module is provably Gemini-free and B18/B18b hold; (b) the DB-side TTL/hash guards introduced no new RPC-contract drift.
