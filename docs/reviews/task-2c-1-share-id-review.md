# Claude Task Review — Stage 2c Task 1 (share `id` in create response)

**Reviewer:** Claude (independent subagent). **Diff:** `6a6b9d4..e07b0be`. **Date:** 2026-07-11.
**Verdict: Spec ✅ · Quality Approved.** §12 money-adjacent multi-tenant surface — reviewed adversarially.

## Migration `0017`
Verified line-by-line vs `0013`: owner check, hash-format check (`!~ '^[0-9a-f]{64}$'`), TTL bound (`make_interval(days=>365)+interval '1 hour'`), and promoted predicate all **byte-preserved**. Only diffs: `v_id uuid` decl, `returning share_tokens.id into v_id`, `return query select v_id, p_expiry`. `RETURNING` qualified `share_tokens.id` (required — `id` is now an OUT var that would shadow the column). Return type `table(id uuid, expires_at timestamptz)`; `p_expiry` echo preserved. `drop function if exists …(uuid,text,timestamptz,text)` present; both `revoke all … from public` AND `grant execute … to authenticated` re-applied. SECURITY DEFINER + `search_path=public` + `auth.uid()` preserved. No service_role. `merge_video_data` untouched.

## Route
`const row = Array.isArray(data) ? data[0] : null` correctly reads the table-returning array; `data[0]` on `[]` → undefined → falsy → 404 (no crash). 401-on-no-user unchanged. Coarse-404 on `error || !row`. Returns `{ id, token, url, expiresAt: row.expires_at }`, 201. Session client only.

## Tests
- RED genuine (integration: old scalar RPC → `row` null → `toMatchObject` fails right; route: `body.id` undefined).
- Integration keeps row-exists + per-row `owner_id` assertions; count `1→2` correct & necessary (Step-1 test now issues two mints (a)+(b)); both rows owner-scoped. Disclosed deviation is the only defensible reading of the brief.
- Route `beforeEach` default now `data: [{ id, expires_at: <ISO string> }]` (string keeps `typeof body.expiresAt==='string'` alive); added `expect(body.id)`; 64-hex `p_token_hash` + token-leak assertions preserved; 404-on-rpc-error still `{data:null,error}` → 404. No weakened assertions.

## Multi-tenant / money check
Never-charges leaf (token creation spends nothing). Isolation rests on `auth.uid()` + promoted predicate + coarse-404, all unchanged. `row.id` is the caller's own just-inserted row — no new surface.

⚠️ Cannot verify from diff: the atomic-deploy assumption (migration + route ship together) — a documented/accepted deploy-ordering decision (Codex plan-review H3), not a code defect. **Resolved by controller** (accepted at plan gate).

Nothing missing, nothing extra (exactly the 4 brief files).
