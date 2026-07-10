# Claude Re-Review (Round 3) — Stage 1F-b Share Tokens spec v3

**Reviewer:** Claude (opus), independent · **Date:** 2026-07-10 · scope: verify round-2 fixes closed + hunt for defects the v3 fixes introduced.
**Verdict:** PART A — all round-2 findings **genuinely FIXED** (verified against code). PART B — **0 new Blocking, 0 new High**; 4 Low (B-L5 borderline Medium). **CONVERGED — this round is the gate.**

## PART A — round-2 findings verified
- **B-H1 (High) — helper location → FIXED.** Traced the full transitive closure of `read-model.ts`'s graph (`read-model → {model-store, render} → {types, theme, nav, local-blob-store → blob-store → principal}`): grep for `gemini|reserve_|gemini-cost|spend_ledger|serve_model_charge` over every node = **zero hits**. B18c satisfiable. No import cycle (`render.ts`/`model-store.ts` don't import `serve-doc`/`read-model`). Both `serve-doc.ts` read sites (`:52-54`, `:66-67`) preserved; `ResolveResult` semantics unchanged.
- **Codex High (RPC TTL) → FIXED.** §4.2 RPC bound `p_expiry IS NULL OR (p_expiry > now() AND p_expiry <= now()+365d)`; D7 both-sides; B5c.
- **Pick get-only → FIXED.** D16 runtime wrapper `{ get: store.get.bind(store) }`; `get()` pure (`supabase-blob-store.ts:23-27`).
- **D14 overclaim → FIXED.** D8 "within one request boundary"; D14 mandatory; step-5 re-checks liveness AND promoted.
- **Entropy wording → FIXED.** D6 route=256-bit, direct-RPC weak = owner-self-harm out of scope.
- **B18b guard → FIXED.** ESLint no-restricted-imports + reserve string grep + B18c graph + B18 runtime spies.
- **mdKey precedence, footer strip → FIXED.** §4.3 `artifacts.summaryMd.key ?? video.summaryMd`; §4.5/B22 assert MD-key string absent.
- **D15 belt-and-suspenders → VERIFIED.** `0001:18` `unique(id, owner_id)` + `0001:32` composite FK `(playlist_id, owner_id) → playlists(id, owner_id)` genuinely forbid a video's owner differing from its playlist's.

## PART B — new defects (none Blocking/High)
### Low
- **B-L5 (borderline Medium) — RPC 365d bound can spuriously reject a legit max-TTL mint under app↔DB clock skew.** Route computes `now_app+365d`; RPC rejects unless `<= now_db+365d`. Normally `now_db ≥ now_app` (RPC runs after), so it passes; but if the app clock leads the DB clock beyond route→RPC latency, a `ttlDays:365` mint (B5b-permitted) raises. Fails safe (rejects, never over-grants), owner-only. **Fix:** grace margin `+ interval '1 hour'` on the RPC bound, or clamp route a hair below 365; add an exact-365 boundary test.
- **B-L6 — `MAX_SHARE_TTL_DAYS=365` duplicated (SQL literal + TS constant), no single source; migration append-only → hand-sync drift.** **Fix:** cross-reference comments + an integration test asserting the RPC rejects `now()+366d`.
- **B-L7 — B18c "does not transitively import any `reserve_*`" is category-confused** (reserve is an RPC string, not a JS module). Graph walk sees only `@/lib/gemini`. **Fix:** reword B18c to "graph never reaches `@/lib/gemini`/`@/lib/gemini-cost`/`serve-doc`"; leave the `reserve_serve_model` string to B18b's grep.
- **B-L8 — `read-model.ts` imports the whole `render.ts` just for `GENERATOR_VERSION`.** Harmless (subtree gemini-free) but couples a read helper to the renderer. **Optional fix:** extract `GENERATOR_VERSION` to a tiny `lib/html-doc/constants.ts` (or `generator-version.ts`), making `read-model.ts` a true leaf.

### Internal-consistency sweep — no defects
D14 step-5 promoted re-check vs step-3 assert = intended TOCTOU double-check (not contradictory); B13 "step-3 or step-5" correct. TTL story (D7/B5b/B5c/§4.2/§4.4) consistent. Helper arg `{blobStore, principal, base, titles}` maps cleanly to `readModelEnvelope(principal, base, blobStore)` + `isFresh(envelope, titles)`.

## Convergence signal
**CONVERGED.** Full re-review of v3 (fix verification + fresh defect hunt over revised artifact + real code) → no new Blocking/High, only Low nits with trivial fixes. Per dev-process, this round is the gate. Recommend applying B-L5 (grace margin) + B-L7 (reword B18c) since near-free; B-L6/B-L8 optional. Then user spec-approval → `writing-plans`.
