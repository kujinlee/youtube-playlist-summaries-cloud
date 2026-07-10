# Codex Adversarial Review — 1F-b Task 6 (getShareServeContext, confused-deputy)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 0 Blocking, 0 High, 2 Medium, 1 Low. Cross-tenant isolation confirmed holds; read-only confirmed.

No Blocking or High findings. Cross-tenant isolation in `getShareServeContext` holds: playlist resolution is constrained by `id + owner_id`, video resolution is constrained by `playlist_id + video_id + owner_id`, and returned coordinates are built from the token owner plus that owner-scoped playlist row. The function is read-only: no `.rpc`, `.insert`, `.update`, or `.delete` in [lib/share/serve.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/share/serve.ts:18).

**Medium**

[lib/share/serve.ts:24](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/share/serve.ts:24) - Expiry is enforced with the app server clock and JS parsing, not the DB clock required by the spec’s `expires_at > now()` bound. If the app clock is behind Postgres, an expired bearer token can remain valid until the app clock catches up; if `expires_at` ever parses to `NaN`, the condition fails open. Fix by pushing liveness into the DB predicate or a small resolver RPC using server-side `now()`: token hash match plus `revoked_at is null` plus `(expires_at is null or expires_at > now())`.

[tests/integration/share-serve.test.ts:30](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-serve.test.ts:30) - The “denies an expired token before resolving” test is vacuous for the before-read property. A resolver that reads playlist/video first and denies later would still pass. Same gap for revoked at [tests/integration/share-serve.test.ts:35](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-serve.test.ts:35). Fix with a mocked Supabase query builder that records table access, or with tokens pointing at non-existent/mismatched playlist/video and assertions that only `share_tokens` is queried for expired/revoked/unknown cases.

**Low**

[tests/integration/share-serve.test.ts:23](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-serve.test.ts:23) - The test suite does not directly prove the confused-deputy guard. It proves the happy path by construction, but never forces `share_tokens.owner_id != playlists.owner_id`. Since `share_tokens` has no composite FK to playlists, a service-role insert can manufacture that mismatch, and the resolver is the defense. Add a test with owner A token row referencing owner B’s playlist/video; expected result is `{ status: 'denied' }`, and it must not return B’s `playlistKey` or `mdKey`.

Everything else I checked matches the stated security intent: DB errors throw, missing/revoked/expired/unpromoted all return the same coarse `{ status: 'denied' }`, promoted gating requires `artifacts.summaryMd.status === 'promoted'`, and `mdKey` precedence matches the owner path: `artifacts.summaryMd.key ?? data.summaryMd`.
