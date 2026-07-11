# Dual Review — Stage 2a Task 8 (archive cloud branch)

**Date:** 2026-07-11 · **Diff:** `871f27f..55fa71b`

## Codex (gpt-5.5) — Spec FAIL / Changes-needed · 0 Blocking/High · 1 Medium
Verified: serveLocal byte-preserved (still `archiveVideo`/`unarchiveVideo`, `{ok:true}`); guard order correct for object bodies; reuses Task-7 `updateVideoAnnotations` (no new RPC); tests re-read `data.archived`; `signInAs`+`STORAGE_BACKEND='supabase'`.
- **Medium (REAL — fixed):** cloud body validation throws **500 on a valid non-object JSON body** (`1`, `"x"`, `true`): `body` is cast `Record<string,unknown>|null`, a primitive is truthy, then `'outputFolder' in body` → `TypeError` before the `action` 400. Fix: coerce non-object → null so it falls through to 400.

## Claude (opus) — Spec PASS / Approved · 0 Critical/Important
Independently ran the suites (archive-route-cloud 10/10; archive.test.ts local 5/5 — serveLocal byte-identical via `git show`); verified guard order, RPC reuse, response parity, non-vacuous archive/unarchive re-reads + cross-owner. **Missed the non-object-body 500** (reviewed the object-body path only). Minors: UUID_RE dup; malformed-UUID test not spy-instrumented.

## Controller adjudication
Codex's Medium is a **real, verified** crash path (I reproduced the logic: primitive body → `in` on primitive throws → 500). Claude's PASS doesn't override a verified defect. The **same pattern exists in the T7 review `serveCloud` (`:117-119`)** — I introduced it there this stage too — so the fix covers BOTH cloud routes. The pre-existing LOCAL review parse (`:16-17,:57`) has the same latent pattern but predates 2a → left untouched (local-unchanged invariant); noted for backlog.

**Disposition:** 0 Blocking/High. Medium (non-object body → 500) FIXED in both archive + review cloud routes with RED→GREEN tests (non-object body → 400). Deferred nits (whole-branch): UUID_RE dedup; malformed-UUID spy. Impl `55fa71b`; fix commit follows.
