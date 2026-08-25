# M4 plan — round 4 COORDINATOR adjudication

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` (v4 + the three r4-codex fixes, `3f634bb`)
**Halves:** `plan-m4-promote-schema-r4-codex.md` (**CONVERGED**, 0B/0H/2M/1L) · `plan-m4-promote-schema-r4-claude.md` (**NOT CONVERGED**, 2B/2H/4M/4L)

**Anchor:** stable-blob-addressing
**ADR:** ADR-0006

---

## Verdict: NOT CONVERGED. Round 4 is the FOURTH non-converging round → **Phase 6 fires.**

Rounds 1, 2 and 3 were all NOT CONVERGED. `docs/dev-process.md` Phase 6 fires *"per milestone — **or after 4
review rounds without convergence**, whichever comes first"*, and that trigger was bought with twelve rounds
on the blob-addressing reservation protocol. **It is armed and it has fired.** M4 does not exit Phase 2.

---

## The halves disagree, and that is the finding

`dual-review-disagreement-is-the-signal` records that when the halves split, the finding-reviewer was right
3 times out of 3. That pattern holds again: **every one of Claude's four Blocking/High findings survived
hand-verification by the coordinator.** Codex's CONVERGED was a defensible verdict *about the migration* —
it verified the SQL, re-ran the production measurement independently, and confirmed the T1 translation. It
is not a verdict about the **plan**, because both Blockings are about what the plan does not contain.

`dual-review-halves-are-not-redundant` is the governing memory: a single CONVERGED is never proof.

---

## Coordinator hand-verification — every load-bearing claim, checked, not trusted

| Claim | Verdict | How |
|---|---|---|
| B2/H1: plan enumerates 9 triggers on live tables | **CONFIRMED, and the layer split is right.** 15 triggers exist across `01/03/04`; 9 are on `profiles`/`playlists`/`videos`/`jobs`, 6 on new empty tables | `awk` over `create trigger` in all three files |
| B1: the plan has no rollback section | **CONFIRMED.** The only two `rollback` hits are a different sense (`:4`, "outside a review's rollback") and a description of `verify-schema.sh` | `grep -niE "rollback\|down-migration\|0028\|recover\|backup"` |
| B2: `test:integration` is absent from the plan | **CONFIRMED.** Zero hits for `test:integration`, `test:e2e`, `integration`, `e2e`, `test suite` | `grep -niE` over the plan |
| B2: `test:integration` is not in CI | **CONFIRMED.** `.github/workflows/ci.yml:6-10` says so in its own words | read |
| H1: committing 0027 auto-applies M4 on every dev machine | **CONFIRMED verbatim.** `tests/integration/global-setup.ts:43-51` runs `npx supabase migration up` and **throws** rather than skip | read |
| H2: LOCAL default ACL is `anon=Dxtm` | **CONFIRMED.** `postgres\|public\|r` → `anon=Dxtm/postgres` | `pg_default_acl` on the local container |
| H2: `workspaces` is the only new table with no revoke | **CONFIRMED decisively.** 5 tables created, 4 revoked. `01_workspaces.sql` has **0** revokes vs **8** in `03` and **12** in `04` | `grep -hoiE "^create table…"` vs `"^revoke…"` |
| H2: PRODUCTION default ACL is `anon=arwdDxtm` | **NOT INDEPENDENTLY RE-VERIFIED.** `CLAUDE_RO_DATABASE_URL` is not in the coordinator's shell env. The local half matches the reviewer exactly, and r4-codex independently reached production earlier in this same round, so prod access was real — but this specific string is the reviewer's measurement, not mine. **Re-measure before acting on the severity.** |

---

## ⚠ ONE REVIEWER CLAIM IS FALSE — and correcting it makes B1 WORSE, not better

**B1 states:** *"Measured: `npx supabase migration --help` lists exactly `list`, `new`, `repair`, `squash`,
`up`. **There is no `down`.**"*

**That is wrong.** Measured by the coordinator on the **same CLI version the reviewer named, 2.115.0**:

```
SUBCOMMANDS
  list  new  repair  squash  up  down  fetch
```

`down` exists. `fetch` exists. The reviewer's enumeration omitted two subcommands.

**B1's conclusion survives, and hardens.** `supabase migration down --help` reads *"**Resets** applied
migrations up to the last n versions"*, and it accepts `--linked`, `--db-url` and `--project-ref` — so it
can be pointed at production. "Reset" in this CLI's vocabulary (cf. `supabase db reset`) is
drop-and-recreate, not an inverse migration. ⚠ **NOT EXECUTED** — verifying that by running it is exactly
the thing nobody should do to find out.

So the corrected finding is strictly more dangerous than the original:

> "There is no way back" makes an implementer hand-write `0028`.
> "There *is* a `down` command" invites one to run it on production and destroy the data it was meant to save.

**A false premise arguing for the right conclusion is the most expensive kind to leave standing**, because
nobody re-examines a finding they already agree with. The rollback task B1 asks for is still required; the
plan must additionally state that `supabase migration down` is **not** the rollback mechanism.

---

## A defect the coordinator found that NEITHER half reported

`plan:120` still asserted *"removes the case for a maintenance window at this data size"* — **verbatim the
claim that `plan:167-173` explicitly retracts** as *not* the position, in the fix for r4-codex's own Medium.

Codex found the overstatement and cited it at `:110-113, :151-159`. The fix was applied *at the cited
lines*. Both reviewer and coordinator were correct about the location named and silent about the second
copy. `true-about-the-name-silent-about-the-layer`, applied to a **fix** rather than a finding:

> **A finding cites where the reviewer SAW the problem, not where it LIVES.**
> The fix for a claim-level defect is a `grep` for the claim, not an edit at the citation.

Corrected in this commit, with the amendment trail left in place.

---

## Open, not folded

The four Blocking/High findings are **NOT folded into a v5**, deliberately. Phase 6 has fired; per
`dev-process.md` the next step is an architecture review that reads `CONTEXT.md` + `docs/adr/` and asks what
per-round review is structurally blind to — not a fifth patch. `gates-detect-defects-not-design` is the
memory: *"is this correct?" is local and always patchable*, and four rounds of local patching is precisely
the signal the trigger was built to catch.

**Coordinator's own open finding, raised but NOT filed** (filing is the user's step): the plan's
*"`05_assert.sql` is NEVER a migration"* exclusion (`:54`, `:123-125`) is **prose only**. `grep -rn "05_assert"
scripts/ .github/ .claude/hooks/` returns three hits, all comments, none asserting that `supabase/migrations/`
is free of `execute p_sql` or `delete from profiles`. Given the payload, that exclusion is a one-line
mechanical check away from being a gate.
