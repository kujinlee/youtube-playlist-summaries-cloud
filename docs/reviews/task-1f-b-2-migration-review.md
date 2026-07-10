# Claude Task Review — 1F-b Task 2 (0013 share_tokens migration + 4 definer RPCs)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · Commit `b2dbd42`.

## (A) Spec compliance: ✅ PASS
- All 4 RPC signatures match the plan (`create_share_token(uuid,text,timestamptz,text)`, `revoke_share_token(uuid)→boolean`, `revoke_all_share_tokens(uuid,text)→integer`, `list_share_tokens(uuid,text)→table`). Migration byte-identical to the plan's embedded SQL.
- **text-vs-bytea is a sanctioned override** (plan Global Constraints, not a violation): spec §4.1/§4.2 said `bytea/octet_length=32`, but the plan deliberately uses `text` hex + `^[0-9a-f]{64}$` CHECK to dodge the PostgREST Buffer-serialization footgun. Security property (hashed at rest, plaintext never stored, D6/B24) fully preserved.
- D9/B23: `force` RLS + `service_role`-only DML, no anon/authenticated policy. D7/B5c TTL bound verbatim (+1h grace). D6/B24 hash CHECK on table + RPC; list returns no hash. Grants complete; correctly grants to `authenticated` only (not `anon`) — management is owner-only.

## Security boundary — SOLID (verified)
1. **B23 direct-DML denial** — two layers: no `authenticated` DML grant + `force` RLS with zero policies.
2. **Definer safety** — all 4 `security definer set search_path=public`, `auth.uid()` null-checked, every mutation/read filtered by `owner_id = v_owner`. No cross-owner path.
3. **Ownership+promoted gate** — join is *stronger* than 0012 (adds `p.owner_id = v.owner_id`), plus `where p.owner_id = v_owner`. No mint-for-unowned/unpromoted.
4. **TTL** — rejects past + >~1yr, accepts null + route-legit 365d.
No Critical findings; no migration code change required.

## (B) Code quality: Approved with test fixes (all in the test file, not the migration)
### Important
- **Revoke ownership-isolation test confounded** (`:74-88`): owner revokes before non-owner attempts, so `revoked_at is null` alone returns 0 — the `owner_id` filter is never the discriminator (would pass even if that filter were deleted). Fix: non-owner revokes a LIVE token first (assert false + revoked_at still null), then owner revokes.
- **Owned-but-unpromoted mint untested** (B2 promoted branch): only the not-owned branch is covered. Fix: seed a `committed` doc, `create_share_token` → error + no row.
### Minor
- B23 tests only INSERT — add UPDATE/SELECT/DELETE direct-DML denial. Non-owner create test never asserts "no row". `list` owner-scoping untested. No `revoke_all=0` / revoke idempotency test.
### ⚠️ Unverifiable from files
- Did not run the live integration suite (RED→GREEN evidence in the implementer's report/commit). `signInAs` assumed to yield an anon-key + user-JWT `authenticated` session (required for the RLS tests to be meaningful).

## Disposition
Spec ✅ + Quality Approved. Migration correct as-is; the Important + Minor test gaps strengthened in a follow-up commit before marking the task complete. (Codex concurred: 0 Blocking/High, same test gaps ranked Medium/Low.)
