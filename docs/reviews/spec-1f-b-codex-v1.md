# Codex Adversarial Review — Stage 1F-b Share Tokens spec (v1)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · run from coordinator (read-only sandbox).
**Verdict:** 1 Blocking, 3 High, 4 Medium, 2 Low/Verified.

**Blocking**

- **Charge-free share serving has no safe reusable resolver.**  
  Scenario: implement `/s/<token>` by reusing `resolveMagazineModel` because the spec points at `serve-doc.ts` / `isFresh`; model is absent or stale; `resolveMagazineModel` calls `reserve_serve_model` and then Gemini, writes the model, and touches `spend_ledger`. That violates B7/B8/B18.  
  Concern: `docs/...share-tokens-design.md:36-37,85,137`; code: `lib/html-doc/serve-doc.ts:52-91`, `supabase/migrations/0012_serve_model_charge.sql:27-100`.  
  Fix: add a separate `readFreshMagazineModel(...)` helper that only does `readModelEnvelope + isFresh` and returns `{ok|not_ready}`. Export `isFresh` only if needed, but do not let share code import `resolveMagazineModel`.

**High**

- **Revocation is not immediate for in-flight share requests.**  
  Scenario: valid `/s/<token>` request selects the live token at step 2; owner revokes it; the request continues through blob reads/render and still returns 200. This contradicts “revocation takes effect immediately” and B10/B14.  
  Concern: `docs/...share-tokens-design.md:83-86,117,121,154`.  
  Fix: re-check `share_tokens` after blob/model reads and just before returning 200. Also re-check promoted status if “un-promote/delete takes effect immediately” is required.

- **Service-role index resolution is unsafe if it uses the existing metadata store.**  
  Scenario: share token row has owner A + playlist UUID; route resolves `playlist_key`, then uses `SupabaseMetadataStore.readIndex(principal)` under `service_role`; that method selects playlist by `playlist_key` only. Since `playlist_key` is unique per owner, not global, a collision can 500 via `maybeSingle()` or become a confused-deputy bug if later changed to `limit(1)`.  
  Concern: `docs/...share-tokens-design.md:84,88`; code: `lib/storage/supabase/supabase-metadata-store.ts:13-26`, warning in `lib/storage/resolve.ts:66-83`, schema uniqueness in `supabase/migrations/0001_core_schema.sql:17`.  
  Fix: do not use `readIndex` for share serving under `service_role`. Resolve by `playlist_id AND owner_id`, then read videos by that playlist UUID and assert `videos.owner_id = owner_id`.

- **“Read-only service_role” is asserted but not mechanically enforced.**  
  Scenario: route builds a normal service-role `SupabaseBlobStore`; that object exposes `put/delete/promote`. A later refactor accidentally calls `resolveMagazineModel`, and the share path writes a model after charging.  
  Concern: `docs/...share-tokens-design.md:38,85,126`; code: `lib/storage/supabase/supabase-blob-store.ts:18-63`.  
  Fix: use a narrow read-only interface/client in the share route: `get`, no `put/delete/promote`, and tests that no write methods/RPCs are called.

**Medium**

- **`share: true` render mode does not exist today.**  
  Scenario: implementation follows `renderMagazineHtml(parsed, model, { nonce, dig:false, share:true })`; TypeScript rejects it, or implementer drops `share:true`; current output still includes `source-md`, `video-id`, channel, URL, timestamp links, theme/print controls.  
  Concern: `docs/...share-tokens-design.md:44,86,129`; code: `lib/html-doc/render.ts:56-60,63-69,104-128`.  
  Fix: define a real `share?: boolean` render option and explicit tests for B22. Decide whether video URL/channel/source filename/video-id are allowed in shared output.

- **Definer RPC accepts caller-chosen token hashes without validation.**  
  Scenario: authenticated owner bypasses the Next route and calls `create_share_token` directly with a low-entropy or malformed `p_token_hash`, creating guessable or unusable links for their own doc. Not cross-tenant, but it breaks the “256-bit random token” invariant at the DB boundary.  
  Concern: `docs/...share-tokens-design.md:72-73,108,131`.  
  Fix: add `octet_length(p_token_hash)=32` in the RPC/table, and preferably move token generation/hash into a server-only route or RPC that does not accept arbitrary hashes from clients.

- **TTL math allows ambiguous or hostile values.**  
  Scenario: direct RPC call with `p_ttl_days = -1` returns a plaintext URL that is already expired; huge values can overflow or create effectively permanent links despite default-expiry intent.  
  Concern: `docs/...share-tokens-design.md:72-73,111-112`.  
  Fix: constrain TTL: `null/0 = never`, otherwise `1 <= ttl_days <= max_allowed_days`.

- **Anonymous valid-token traffic can still amplify storage/DB cost.**  
  Scenario: leaked valid token is hammered; each request can do token lookup, playlist/video reads, MD blob read, model blob read, render. No Gemini charge, but still service-role DB/storage egress.  
  Concern: `docs/...share-tokens-design.md:46,147-148`.  
  Fix: add at least coarse per-token/IP rate limiting or CDN/WAF throttling before launch; cache is intentionally disabled, so every hit reaches origin.

**Low / Verified**

- **SHA-256 without salt/HMAC is acceptable for 256-bit random bearer tokens.**  
  With `crypto.randomBytes(32)` and base64url, offline inversion of leaked hashes is not realistic. HMAC would help mainly against accidental low-entropy tokens, which should be blocked by DB/RPC validation.

- **Malformed vs unknown token timing is not a meaningful secret oracle by itself.**  
  Malformed tokens intentionally stop before DB; unknown well-formed tokens do one indexed lookup. The important part is preserving identical 404s for unknown/expired/revoked/unpromoted before blob reads.
