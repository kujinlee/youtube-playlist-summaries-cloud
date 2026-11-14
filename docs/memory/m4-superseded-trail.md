---
name: m4-superseded-trail
description: "FIRES-WHEN: citing superseded M4 history (2026-08-25/26) — fork (a) and the fingerprint-vs-behaviour verdict, why a rollback cannot be a migration, Phase 6 having ALREADY RUN twice, extract-and-execute. History, NOT current state: read [[anchor-name-and-stable-id-handoff]] for what is true now"
metadata:
  type: project
---

**The rule: nothing here is current state.** M4 merged 2026-08-27 (PR #155, `c517faa`) and `0027`
went to prod the same day — current facts live in [[anchor-name-and-stable-id-handoff]]. This file is
the condensed trail of the four superseded "where M4 stands" blocks (2026-08-25 11:0x → 2026-08-26
06:40), kept for the lessons that still apply:

1. **A rollback filed in `supabase/migrations/` is a NO-OP milestone.** `supabase migration up`
   applies every pending file in one ascending pass (measured with throwaway 9998/9999), so a
   `0028` rollback runs straight after `0027` on `db push`, `db reset` and
   `tests/integration/global-setup.ts`. Rollbacks live in `supabase/rollback/` (never replayed).
2. **Check whether the ARTIFACT exists, not whether the TRIGGER fired.** I said "Phase 6 never ran"
   three times while it had run twice (`docs/reviews/architecture-review-2026-08-25.md` → ADR-0011
   and `check-live-schema.py`; `…-2026-08-25b.md`). See [[it-already-exists-under-a-name-i-didnt-search]].
3. **Code in a plan's prose is unexecuted code.** At round 2, 8 of 8 distinct Blocking findings sat in
   fenced blocks never run (48 blocks / 336 lines). Decision: extract and execute; embedded code went
   336 → 148 lines. See [[extract-and-run-a-plans-code]].
4. **A grep inventory misses `create constraint trigger`** — "13 triggers" was really 14.
   See [[a-convention-catches-what-you-read]].
5. **A task reporting "completed" is not evidence its deliverable exists — read the artifact.**
6. **A finding cites where the reviewer SAW a problem, not where it LIVES** — fix a claim-level
   defect with a `grep` for the claim, not an edit at the citation
   ([[true-about-the-name-silent-about-the-layer]]).

## History (condensed)

**2026-08-25 11:0x — Phase 6 fired.** PR #150 (plan v4), round 4 split: Codex CONVERGED (0B/0H) vs
Claude NOT (2B/2H/4M/4L); fourth non-converging round → Phase 6, findings deliberately not folded into
a v5 ([[gates-detect-defects-not-design]]). Round-4 findings: no rollback section; no behavioural suite
in the gate list (`test:integration` excluded by `ci.yml:6-10`); committing `0027` IS M4-α unseeded on
every dev machine (`global-setup.ts:43-51` throws, not skips); `workspaces` the only new table with no
revoke. ⚠ B1's premise was false in the dangerous direction: `supabase migration down` exists on CLI
2.115.0 but *resets* and takes `--linked`, so it can be aimed at prod. M4's load-bearing facts then:
it ALTERs playlists/videos/jobs; the `workspace_videos` backfill's `distinct on` could silently drop a
paid correction (measured 0 in prod); `05_assert.sql` must never be a migration (`delete from
profiles`). Also PR #151: three `.claude/skills/*` symlinks into `.agents/skills/` were missing
(`ls | head -20`, `[:12]`, `sort -u` habits).

**2026-08-25 14:10 — ADR-0011.** Phase 6 #1 found nine of eleven Blocking/High across five rounds
were ONE defect: `corrections` given workspace scope while its truth stayed playlist scope. Owner
accepted option (a), corrections stay per-playlist — dissolved four findings with no code, live-table
triggers 9 → 7. Plan v2 (`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md`).
Measured: five of six schema gates rebuild from spec files, so the existing suite is pre-migration in
its entirety. The `$?`-after-a-pipe bug fired four times that day; "fixed at one of two sites" three.

**2026-08-25 15:05 — PR #150 merged** (`1706930`, no production code path). PR #152 (`903004d`):
the live-schema gate had named 29 of 161 objects and said "present" with all seven own-table guard
triggers dropped; it now compares to a manifest of **161 objects DERIVED BY EXECUTION**
(`scripts/gen-m4-manifest.py`: clone pre-M4 → apply → `after EXCEPT before`), failing closed if the
baseline already has M4. Mutations 5/5. Two gates had measured the wrong subject (blind to what
ADR-0011 deletes; mutation harness built a pre-ADR-0011 schema). Round 3: NOT CONVERGED, and the
defect class shifted from "code never ran" to "claims wider than the code". Dead code noted:
`corrections_hash_of`, `no_corrections_hash` with zero callers (revoked, not exposure).

**2026-08-26 06:40 — fork (a) chosen by the owner at 21:56 (08-25).** Phase 6 #2's answer: M4 built
a FINGERPRINT COMPARATOR where the risk is BEHAVIOURAL — all nine Blocking/High in rounds 4-7 sat in
the fingerprint's two obligations (enumerate; compare across environments). Fork (a) splits by
question: manifest = structure, behaviour → `05_assert.sql`, per-environment privilege →
`check-anon-exposure.py`. Step 1 (`ef498b0`) proved it: `05_assert.sql` held 104 `raise exception`s
and ZERO `@RE-RUNNABLE` markers; marking the anon-TRUNCATE block caught `grant truncate … to anon`
(exit 1) where `check-live-schema` was blind by design. `run-schema-assertions.sh` had no caller —
wired the same commit (suite TEN gates). Remaining steps then: `pg_get_function_arguments` in the fn
digest (`record_artifact` has 7 defaults in 13 params); privileges out of the digest; M4 tables into
`MONEY_TABLES`; FUNCTION revokes extended to `service_role` (r7 codex B1); fixture-bearing assertion
blocks; ADRs for revoke-before-grant and the `service_role`/`slot_kind` trap. `codex-review.py` once
overwrote a review with a summary of itself — `classify()` now rejects a message naming its own
output file (self-test 15→17). Verdict page: `~/explainers/2026-08-25-brief-phase6-verdicts.html`.

See [[the-control-refuted-the-premise]], [[a-mocked-boundary-tests-the-contract-you-imagined]],
[[quote-the-code-dont-characterise-it]], [[a-mechanism-can-be-silently-overridden]],
[[a-test-that-cannot-fail]].
