# Codex Re-Review (Round 2) — Stage 1F-b Share Tokens spec v2

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 0 new Blocking, 1 new High (RPC TTL bypass), 3 Medium, 1 Low. NOT converged.

**PART A — v1 Findings Verification**

| v1 finding | Status | Evidence |
|---|---:|---|
| BLOCKING: charge-free share serving had no safe reusable resolver | FIXED | v2 adds D13: exported `readFreshMagazineModel(...)`, `isFresh` export, `resolveMagazineModel` refactor, and share import ban in [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:48>) / B18b at line 141. This is a clean extraction target from current `resolveMagazineModel` read-first branch: [serve-doc.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:52>). |
| HIGH: revocation not immediate for in-flight requests | PARTIAL | v2 adds D14 and B10b: post-read liveness re-check before 200 at [spec:49](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:49>) and [spec:132](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:132>). This fixes revoke-before-step-5, but “immediate” still overclaims because revoke-after-step-5-before-bytes is still possible. |
| HIGH: service_role index resolution unsafe | FIXED | D15/§4.3 require resolving by `playlist_id AND owner_id`, never `readIndex`: [spec:50](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:50>), [spec:90](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:90>). This matches the safe worker pattern in [resolve.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/resolve.ts:71>). |
| HIGH: read-only service_role not mechanically enforced | PARTIAL | v2 specifies `ReadOnlyBlobStore = Pick<BlobStore,'get'>` at [spec:91](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:91>). That helps at TypeScript call sites, but `Pick` alone is not a runtime read-only view if a full `SupabaseBlobStore` is retained; current store exposes writes at [supabase-blob-store.ts:18](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:18>). |
| HIGH: bearer token in URL leaks via Referer | FIXED | D10/B21 and route contract mandate `Referrer-Policy: no-referrer`: [spec:45](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:45>), [spec:145](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:145>). |
| MEDIUM: `share:true` render mode absent / strip-set unspecified | FIXED | §4.5 adds real `share?: boolean` and enumerates stripped fields: [spec:99](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:99>). Current render emits exactly those metas/footer today: [render.ts:112](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/render.ts:112>) and [render.ts:126](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/render.ts:126>). Existing render tests exist: [render.test.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/html-doc/render.test.ts:27>). |
| MEDIUM: `create_share_token` accepted caller-chosen hash | PARTIAL | v2 adds 32-byte validation at [spec:59](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:59>) and [spec:79](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:79>), but the RPC still accepts caller-chosen 32-byte hashes. A direct authenticated caller can create a hash of a low-entropy but correctly shaped token. |
| MEDIUM: TTL math hostile values | PARTIAL | Route contract is fixed at [spec:97](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:97>), but the RPC accepts concrete `p_expiry timestamptz` and line 79 explicitly says max-bound enforcement lives in the route only. Direct RPC callers can bypass it. |
| MEDIUM: never-expiry unreachable via `?? 30` | FIXED | §4.4 explicitly distinguishes omitted from `'never'`: [spec:97](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:97>), with B5 at [spec:125](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:125>). |
| MEDIUM: DoS amplification understated | FIXED | D12 and §9 now honestly account for valid-token infra cost and name pre-launch rate-limit/cache hardening: [spec:47](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:47>), [spec:166](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:166>). |

**PART B — New Defects**

**Blocking**

None found.

**High**

1. Direct RPC callers can bypass `MAX_SHARE_TTL_DAYS`.
Scenario: an authenticated owner calls `create_share_token(..., p_expiry := '9999-01-01', p_token_hash := sha256(token))` directly. The spec says the max bound is only resolved in the Next route, while the RPC inserts `expires_at = p_expiry`: [spec:79](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:79>). That contradicts D7/B5b’s bounded-expiry invariant at [spec:42](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:42>) and [spec:126](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:126>).
Fix: enforce in the definer RPC too: `p_expiry is null OR (p_expiry > now() AND p_expiry <= now() + make_interval(days => MAX_SHARE_TTL_DAYS))`. Keep route validation for UX, but DB/RPC must be the trust boundary.

**Medium**

1. Direct RPC callers can still mint low-entropy share tokens.
Scenario: caller picks a valid-length path token like 43 base64url chars, hashes it, and calls `create_share_token`. `octet_length(token_hash)=32` proves SHA-256 shape, not 256-bit randomness. v2 still grants the RPC to `authenticated`: [spec:76](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:76>).
Fix: either move token generation fully into a server-only route backed by service-role insert, or have the RPC generate and return plaintext once. If keeping caller-supplied hash, weaken the invariant from “opaque 256-bit random token” to “route-generated tokens are 256-bit; direct RPC callers can self-weaken their own links.”

2. `Pick<BlobStore,'get'>` is not a mechanical read-only boundary by itself.
Scenario: implementation writes `const ro: ReadOnlyBlobStore = new SupabaseBlobStore(...)`; the runtime object still has `put/delete/promote`, and the same route may still hold the service-role client. Current class exposes writes: [supabase-blob-store.ts:18](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:18>).
Fix: specify an actual wrapper object: `const readOnlyBlobStore = { get: full.get.bind(full) }`, and keep `readFreshMagazineModel` typed against that wrapper. Test that helper receives an object with only `get`.

3. D14 still overclaims “immediate” revocation/un-promote semantics.
Scenario: request passes step 5, then owner revokes before response bytes leave. It still returns 200. Also §4.3 says re-assert promoted “if required” at [spec:92](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:92>), while D14 makes it mandatory at [spec:49](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:49>).
Fix: change wording to “final pre-response re-check closes revoke-before-final-check races” and make promoted re-check mandatory if B13 is meant to cover mid-flight un-promote.

**Low**

1. B18b grep/lint import guard is easy to route around.
Scenario: share route imports `getSharedModel()` from another helper, and that helper imports `resolveMagazineModel`. A local grep over only route + helper names can pass while the transitive dependency charges. B18 money-invariant tests reduce the blast radius, but B18b as written is weak: [spec:153](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:153>).
Fix: use an ESLint `no-restricted-imports` rule scoped to `app/s/**` and share helpers, plus a dependency graph check or focused runtime spies proving no reserve/Gemini calls.

Convergence signal: no new Blocking findings, but there is one new High around RPC TTL bypass.
