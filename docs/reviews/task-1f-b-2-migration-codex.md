# Codex Adversarial Review — 1F-b Task 2 (0013 share_tokens migration + RPCs)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 0 Blocking, 0 High, 4 Medium, 1 Low (all test-integrity; migration security boundary confirmed correct).

**Blocking**
None.

**High**
None. The migration’s core security boundary holds: `share_tokens` is force-RLS, no anon/authenticated table grants or policies are added, DML is service-role-only, and all four RPCs are `SECURITY DEFINER set search_path = public` with `auth.uid()`-derived owner checks.

**Medium**
- `tests/integration/share-tokens-rpc.test.ts:83-87` — revoke ownership isolation test is vacuous. The owner revokes first, then the foreign user revokes an already-revoked token. If `revoke_share_token` were missing `owner_id = v_owner`, the foreign call would still return `false` because `revoked_at is null` is already false.
  Fix: have the foreign user attempt revoke before the owner; assert it returns `false` and service-role inspection shows `revoked_at` is still null, then owner revokes.

- `tests/integration/share-tokens-rpc.test.ts:99-105` — B23 test claims `INSERT/UPDATE` but only tests `INSERT`. It does not prove authenticated `UPDATE`, `DELETE`, or `SELECT` are denied, including the important “can I read `token_hash` directly?” case.
  Fix: seed a token via RPC/service role, then from an authenticated client attempt `select('*')`, `update({ revoked_at: ... })`, and `delete()`. Assert denied/no rows and verify the service-role row is unchanged.

- `tests/integration/share-tokens-rpc.test.ts:31-39` — ownership/promoted gate test only covers foreign ownership, not owned-but-unpromoted. A regression that checks ownership but forgets `status = 'promoted'` would pass this suite.
  Fix: seed an owned video with `status: 'committed'`, call `create_share_token`, expect an error, and assert no row was inserted.

- `tests/integration/share-tokens-rpc.test.ts:90-96` — `revoke_all_share_tokens` only has the owner happy path. It does not prove another user cannot revoke all tokens for a doc they do not own.
  Fix: seed owner A’s tokens, call `revoke_all_share_tokens` as owner B with A’s `(playlist_id, video_id)`, expect `0`, and service-role assert A’s tokens remain live.

**Low**
- `tests/integration/share-tokens-rpc.test.ts:64-71` — malformed hash test proves the RPC guard, not the table CHECK backstop. If the CHECK disappeared but the RPC guard remained, this test would still pass.
  Fix: add a service-role direct insert with a bad `token_hash` and assert the CHECK rejects it.

**Confirmed**
- `supabase/migrations/0013_share_tokens.sql:16-18` has RLS enabled + forced and only grants table DML to `service_role`.
- `0013:24,49,60,72` all four RPCs use `SECURITY DEFINER set search_path = public`.
- `0013:26-34,50-55,61-65,73-79` derive/null-check `auth.uid()` and owner-scope writes/reads.
- `0013:36-41` requires owned `(playlist_id, video_id)` and promoted summary before minting.
- `0013:32-34` rejects past and materially-over-365-day expiries while allowing route-computed 365-day mints.
- `0013:8,30` enforce lowercase hex-64 hashes.
- `0013:70-79` list returns only id/timestamps, never `token_hash`.
- `0013:9,19` has the expected `profiles(id) on delete cascade` FK and owner index.
