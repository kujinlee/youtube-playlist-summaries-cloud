# Codex Adversarial Re-Review — Stage 2c Plan (round 2)

**Model:** gpt-5.5. **Date:** 2026-07-11. **Artifact:** plan v2 (2b6b24f). **Verdict: NOT converged (round 2) — 2 High; both fixed in v2.1.**

**BLOCKING**
None found.

**HIGH**
1. [Task 5 / Tokens](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:534>)  
   Problem: Plan repeats nonexistent tokens: `--bg`, `--bg-elevated`, `--text`. Actual tokens are in [app/globals.css](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/globals.css:16>): `--surface-base`, `--surface-raised`, `--surface-overlay`, `--text-primary`, etc. This same issue was already caught/fixed in 2b.  
   Fix: Replace token list and snippets with real 2a tokens. Do not add globals.

2. [Task 5 / ShareDialog tests](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:647>)  
   Problem: The plan requires a synchronous in-flight guard for BOTH create and revoke, but tests only assert backdrop/Escape during create. They do not assert double-click create, double-click revoke, or backdrop/Escape during revoke.  
   Fix: Add tests proving one create call for rapid double-click, one revoke call for rapid double-click, and backdrop/Escape inert while revoke is pending.

3. [Task 1 / deployment compatibility](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:101>)  
   Problem: `DROP + CREATE` is correct for Postgres return-type change and `db reset` order is fine, but the plan ignores live deploy ordering. New route against old scalar RPC returns 404 for all share creates; old route against new table RPC returns `expiresAt` as an array.  
   Fix: Either document an atomic migration+deploy requirement, or safer: create a new RPC name, e.g. `create_share_token_v2`, then migrate route callers.

**MEDIUM**
1. [Task 1 / caller audit](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:46>)  
   Problem: “Tests migrated” lists only two files, but grep shows many direct `create_share_token` calls in [tests/integration/share-tokens-rpc.test.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-tokens-rpc.test.ts:21>). Most ignore `data`, so they likely survive, but the plan does not explicitly audit them.  
   Fix: Add a grep-audit step. State which callers require assertion updates and which are unaffected because they ignore return data.

2. [Task 1 / RPC coverage](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:76>)  
   Problem: The revised happy-path RPC test uses `p_expiry: null`, so it only proves `expires_at: null`. It drops coverage that a non-null expiry round-trips.  
   Fix: Keep or add a second assertion with a real expiry and expect returned `expires_at` close to the input.

3. [Task 5 / TTL tests](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:572>)  
   Problem: Component tests cover default `30` and `Never`, but not explicit `7d`. The client seam covers `7` only through an error-mapping test, not UI mapping.  
   Fix: Add `TTL 7d -> createShare(..., 7)` component test.

4. [Task 5 / a11y tests](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:524>)  
   Problem: Plan requires initial focus on TTL group and focus trap, but tests do not assert either.  
   Fix: Add assertions for initial focused radio/group and Tab/Shift+Tab cycling inside dialog.

**LOW**
1. [Task 6 / URL tests](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:722>)  
   Problem: Tests use a video id with no escapable characters, so `encodeURIComponent(videoId)` is not actually protected.  
   Fix: Add a `summaryHref` unit case with a video id containing reserved chars and assert encoded pathname.

2. [Task 6 / menu roles](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:774>)  
   Problem: Suggested snippet adds `role="menuitem"` inconsistently with current `VideoMenu`, whose anchors/buttons do not set it. Not a functional bug, but avoid mixed semantics.  
   Fix: Either update all menu items consistently or follow existing markup.

**Sound Areas**
- The `DROP + CREATE` return-type change is technically correct; `CREATE OR REPLACE` would fail.
- `RETURNING share_tokens.id INTO v_id` is correctly qualified.
- Grants are restored for `authenticated`.
- `returns table(...)` should produce an array from supabase-js; `data[0]` is the right route shape.
- `summaryReady` in `SupabaseMetadataStore.readIndex` reaches `/api/videos` `serveCloud` consumers, and owner scoping remains through session client + playlist ownership/RLS.
- `VideoSchema` is non-strict; adding optional `summaryReady` is not a strict-parse break.
tokens used
124,448
**BLOCKING**
None found.

**HIGH**
1. [Task 5 / Tokens](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:534>)  
   Problem: Plan repeats nonexistent tokens: `--bg`, `--bg-elevated`, `--text`. Actual tokens are in [app/globals.css](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/globals.css:16>): `--surface-base`, `--surface-raised`, `--surface-overlay`, `--text-primary`, etc. This same issue was already caught/fixed in 2b.  
   Fix: Replace token list and snippets with real 2a tokens. Do not add globals.

2. [Task 5 / ShareDialog tests](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:647>)  
   Problem: The plan requires a synchronous in-flight guard for BOTH create and revoke, but tests only assert backdrop/Escape during create. They do not assert double-click create, double-click revoke, or backdrop/Escape during revoke.  
   Fix: Add tests proving one create call for rapid double-click, one revoke call for rapid double-click, and backdrop/Escape inert while revoke is pending.

3. [Task 1 / deployment compatibility](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:101>)  
   Problem: `DROP + CREATE` is correct for Postgres return-type change and `db reset` order is fine, but the plan ignores live deploy ordering. New route against old scalar RPC returns 404 for all share creates; old route against new table RPC returns `expiresAt` as an array.  
   Fix: Either document an atomic migration+deploy requirement, or safer: create a new RPC name, e.g. `create_share_token_v2`, then migrate route callers.

**MEDIUM**
1. [Task 1 / caller audit](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:46>)  
   Problem: “Tests migrated” lists only two files, but grep shows many direct `create_share_token` calls in [tests/integration/share-tokens-rpc.test.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-tokens-rpc.test.ts:21>). Most ignore `data`, so they likely survive, but the plan does not explicitly audit them.  
   Fix: Add a grep-audit step. State which callers require assertion updates and which are unaffected because they ignore return data.

2. [Task 1 / RPC coverage](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:76>)  
   Problem: The revised happy-path RPC test uses `p_expiry: null`, so it only proves `expires_at: null`. It drops coverage that a non-null expiry round-trips.  
   Fix: Keep or add a second assertion with a real expiry and expect returned `expires_at` close to the input.

3. [Task 5 / TTL tests](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-11-stage-2c-cloud-doc-consumption.md:572>)  
   Problem: Component tests cover default `30` and `Never`, but not explicit `7d`. The client seam covers `7` only through an error-mapping test, not UI mapping.  
   Fix: Add `TTL 7d -> createShare(..., 7)` component test.


---

## Round-3 confirmation pass (Codex, v2.1→v2.2)

Codex confirmation on the three v2.1 fixes: (1) exact-shape store test migration CONFIRMED-FIXED; (2) route-test string-expiry mock + id assertion CONFIRMED-FIXED; (4) double-click honest note CONFIRMED-FIXED. (3) a11y Tab-trap test: still-broken *selector mismatch* — the test's querySelectorAll included disabled controls + [tabindex] while the NewPlaylistModal handler uses 'button:not([disabled]), input:not([disabled]), [href], textarea, select'. **Fixed in v2.2**: test now uses the identical selector (Copy/Revoke render disabled pre-Create, so the :not([disabled]) exclusion matters). No Blocking/High remained. **CONVERGED.**
