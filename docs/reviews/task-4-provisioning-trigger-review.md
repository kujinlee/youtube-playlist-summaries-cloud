# Task 4 Review — Provisioning trigger + is_anonymous guard (0003_provisioning.sql)

**Reviewer:** Claude (sonnet), fresh subagent — security-critical by-eye review (Docker down)
**Commit:** c3bb215 | **Verdict:** SPEC ✅ / QUALITY approved

## Security-critical checks — all PASS (verified by reading)
1. **SECURITY DEFINER + `set search_path = ''`** both present on `handle_new_user` (without DEFINER the insert into RLS-forced `profiles` would abort signup).
2. **Schema qualification under empty search_path:** `insert into public.profiles` qualified; no unqualified non-catalog references (`coalesce`/`raise` are pg_catalog built-ins). `new`/`old` are record fields, not object refs.
3. **Trigger timing:** `AFTER INSERT ON auth.users FOR EACH ROW` — profiles row exists in the same txn before any app write.
4. **is_anonymous source:** `coalesce(new.is_anonymous, false)` — Google (null)→false, anon→true.
5. **Immutability guard:** `BEFORE UPDATE`, `is distinct from` (NULL-safe, not `<>`), returns `new` when unchanged (other-column updates unblocked), raises only on a flip. INSERT unaffected.
6. **Ownership reasoning sound:** migration functions owned by `postgres` (superuser) → SECURITY DEFINER bypasses RLS on profiles; no `ALTER … OWNER`/`REVOKE` undermines it.
7. **Tests:** (a) email signup via `newUser`/`admin.createUser` (same auth.users path as Google) → one row is_anonymous=false; (b) anon → true via real RLS path; (c) `pg_proc.prosecdef` asserts DEFINER; (d) client flip rejected with matching message.

Additive only; tsc clean; default suite 1505 green (integration excluded).

## Findings (Minor)
- **M1 (FIXED):** `guard_is_anonymous` trigger target `before update on profiles` unqualified → qualified to `public.profiles` for consistency (worked already via default search_path).
- **M2 (FIXED):** `pg_proc` DEFINER assertion lacked a schema discriminant → added `and pronamespace = 'public'::regnamespace` (same hardening as the Task 2 pg_class query; a same-named function elsewhere can't skew the security assertion).
- **M3 (accepted):** live RED→GREEN deferred (Docker down) — documented, not a defect.

No Critical/Important. Live `db reset` green deferred.
