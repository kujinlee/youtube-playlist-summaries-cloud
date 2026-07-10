# Claude Task Review — 1F-b Task 7 (anon /s/[token] route + money proof + guards)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · Commit `40baf3c`.

## (A) Spec compliance: ✅ PASS
- **D4/D16** bounded read-only service_role: `createServiceClient()` wrapped `{ get: fullStore.get.bind(fullStore) }`; `readModelEnvelope` genuinely widened to `ReadOnlyBlobStore` so no unsafe cast — write methods unreachable at runtime (B19).
- **D11** coarse-404: malformed → 404 before any client/DB call; expired/revoked/unknown/unpromoted/MD-missing/parse-throw all → identical 404, no 500.
- **D13/B18c** generate-free leaf: transitive graph-walk guard (subpath-safe).
- **D14/B10b** mandatory pre-response re-check (`route.ts:45-46`).
- **D15** confused-deputy owner-scoped; fails closed on unparseable expiry.
- **D10/B21/B22** every 200 → no-store + Referrer-Policy:no-referrer + nonce CSP + share:true/dig:false.

## (B) Code quality: Approved (no Critical/Important)
### Money invariant (B18) — GENUINE
Traced all 9 paths (valid/expired/revoked/unknown/malformed/not-ready/MD-missing/corrupt/in-flight-revoke): none reach a charging RPC/generator. Route imports no serve-doc/gemini/gemini-cost; getShareServeContext is select-only; readFreshMagazineModel = one blob read + pure isFresh. Spy is real: `rpc` on `SupabaseClient.prototype`, `createServiceClient()` returns an instance inheriting it → the spy intercepts the route's own client. `afterEach` asserts no `reserve_serve_model` after every case; `afterAll` byte-compares full ledger row sets + asserts zero `generateMagazineModel`. Three legs (runtime spy + static grep B18b + graph-walk B18c).
### Confinement guard — correctly scoped, NOT weakened
`ALLOWED_SERVICE_IMPORTERS` is exact-path (`path.resolve === app/s/[token]/route.ts`); new reachers still flagged; fixtures prove `reachesService` catches side-effect/`@/`-alias imports.
### In-flight revoke (B10b) — genuine simulation
`jest.mock('@/lib/share/serve')` counts calls; on the 2nd (the re-check) revokes then delegates to the real resolver; `hookFired===true` only if call #1 succeeded → proves happy path reached the re-check and it caught the revoke. jest.mock (vs spyOn) justified (SWC non-configurable exports).
### Import guard — widening correct, non-vacuous (fs-walk asserts route present).

### Minor (all → fixed in follow-up)
- Misleading test comment (43-char token vs 64-char hash). Cosmetic.
- Denial/notReady responses omit `no-store`/Referrer-Policy — a cached 503 not-ready could outlive materialization. Low-risk (owner route same), hardened.
- B18b grep doesn't cover the route's transitive render/parse/csp imports — defense-in-depth only (runtime B18 catches actual leaks).
- Ledger `toEqual` without ORDER BY — added `.order()` for determinism.
- (+ Codex: import-guard subpath gap; B8 stale-model + B10b un-promote route coverage; confinement test should prove it FLAGS an unauthorized reacher — all fixed in follow-up.)

⚠️ Did not execute the suite; happy-path model-match confirmed by static trace.

## Disposition
Spec ✅ + Quality Approved. The two highest-risk surfaces (money invariant, confinement guard) are both genuine and correctly scoped. Minors + Codex Mediums (guard subpath hardening, stale/un-promote coverage, confinement-flag test, no-store on denials) folded into a follow-up commit.
