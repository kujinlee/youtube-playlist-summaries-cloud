---
name: m4-superseded-trail
description: "FIRES-WHEN: citing superseded M4 history — The four SUPERSEDED dated M4 blocks, kept verbatim for the trail — fork (a) and the fingerprint-vs-behaviour verdict, the 0028-cannot-be-a-migration finding, Phase 6 having ALREADY RUN twice, and the extract-and-execute decision. History, NOT current state: read [[anchor-name-and-stable-id-handoff]] for what is true now"
metadata:
  type: project
---

> Split out of [[anchor-name-and-stable-id-handoff]] because that file had grown past the per-file read limit and its tail was being truncated. Bodies below are VERBATIM and were already marked superseded when written. **Nothing here is current state.**

**(superseded) WHERE M4 STOOD 2026-08-26 06:40 — FORK (a) DECIDED; step 1 shipped.**

**Branch `docs/m4-round7` @ `ef498b0`, pushed, tree clean, NO PR yet.** Master `74f450b` (PR #154 =
rounds 5+6). **`0027` STILL DOES NOT EXIST.**

⛔⛔ **CORRECTION I MADE THREE TIMES AND MUST NOT MAKE AGAIN: PHASE 6 HAS RUN — TWICE.**
- **#1** `docs/reviews/architecture-review-2026-08-25.md` (17:54, on the v5.1 sequence). Produced
  **ADR-0011** and, as its finding 3, **`check-live-schema.py` itself**.
- **#2** `docs/reviews/architecture-review-2026-08-25b.md` (mine, on the v2 sequence).
I kept saying "fired at round 4, never ran" while quoting #1's finding 3 in the gate's own docstring.
**I was tracking the TRIGGER and never asked whether the ARTIFACT existed.** See
[[it-already-exists-under-a-name-i-didnt-search]].

**⭐ PHASE 6 #2's ANSWER, and the user CHOSE FORK (a) at 21:56:**

> M4 built a **FINGERPRINT COMPARATOR** where the risk is **BEHAVIOURAL**. A fingerprint must
> ENUMERATE what to compare and be COMPARABLE ACROSS ENVIRONMENTS; **all nine Blocking/High findings
> in rounds 4-7 live in one of those two obligations.** An assertion carries neither.

**Fork (a) = split by question.** Manifest keeps STRUCTURE · behaviour → `05_assert.sql` ·
per-environment privilege → `check-anon-exposure.py`.

**✅ STEP 1 DONE (`ef498b0`) and it is the proof of the whole thesis.** `05_assert.sql` held **104
`raise exception`s and ZERO `@RE-RUNNABLE` markers** — 2,239 lines of security assertion that had
never executed. Marked the anon-TRUNCATE block (`:754-764`, needs NO fixture). MEASURED:

    correct schema                      assertion exit 0   GREEN
    grant truncate ... to anon          assertion exit 1   CAUGHT
    same DB, check-live-schema          exit 0             blind — BY DESIGN now

**Round 7 filed that hole as BLOCKING and I was about to add a 14th column to the digest — while the
assertion had been sitting there since round 6 with the measurement written above it.**
⚠ I also nearly shipped a live gate with NO CALLER (3rd time for this repo) — `run-schema-assertions.sh`
was in no suite. Wired in the SAME commit; suite is now **TEN gates**, 8/10 skipped in `pre` and
SAYING so, red on 3 and 4 only (pre-existing, verified by both r7 halves).

**⏭ REMAINING FORK (a) STEPS, IN ORDER:**
1. `proargdefaults` → add `pg_get_function_arguments` to the fn digest. **Fork-independent** (it is
   structure). r7 B1: identity args are byte-identical across a default change; `record_artifact` has
   7 defaults in 13 params, silently writing a different `doc_version_major`/`produced_at`.
2. Remove privileges from the digest entirely (`REL_GRANTEES`/`FN_GRANTEES`/`REL_PRIVS`, `_rel_priv`,
   `_fn_priv`); regenerate the manifest.
3. Per-environment privilege → `check-anon-exposure.py`: add the five M4 tables to `MONEY_TABLES`
   (it has NONE today, which made my r6 coverage comment FALSE), and fix its hard-coded db `postgres`.
4. **Extend the FUNCTION revokes to `service_role`** — the r6 rule is HALF-APPLIED (relations only),
   which is the direct cause of r7 codex B1: removing the explicit `record_artifact` EXECUTE grant is
   a production write outage the gate exits 0 over.
5. Mark the fixture-bearing assertion blocks once the seed corpus supplies their fixtures.
6. ADRs: revoke-before-grant as a schema-wide rule; the `service_role`/`slot_kind` M5 trap.

**⚠ TWO TOOLING FAILURES MEASURED, BOTH "COMPLETED ≠ DELIVERED":**
- `codex-review.py` **overwrote a real review with a summary of itself**, because my r7 prompt said
  "any tracked file EXCEPT YOUR REVIEW FILE". Fixed BOTH ends: prompt says *YOUR FINAL MESSAGE IS THE
  REVIEW*; `classify()` now rejects a message NAMING ITS OWN OUTPUT FILE (self-test 15→17). Re-run
  gave 199 lines, 0 self-refs. Gap note kept at `plan-m4-v2-r7-codex-FIRST-RUN-GAP.md`.
- The Phase 6 subagent went idle **twice** delivering nothing; I wrote #2 myself, which dev-process
  requires of the coordinator anyway.
**Rule: a task reporting "completed" is NOT evidence its deliverable exists. Read the artifact.**

**Verdict page (not tracked, survives): `~/explainers/2026-08-25-brief-phase6-verdicts.html`**, served
at `http://127.0.0.1:7391/latest`. Carries the fork decision AND a correction the user caught: my
"fix TRUNCATE regardless of the fork" was wrong — under (a) the fix is to RUN the existing assertion,
not to add a column. 4 of 6 findings changed status when I re-derived my own review.

---

**(superseded) WHERE M4 STANDS 2026-08-25 15:05 — PR #150 IS MERGED. ROUND 3 DONE, NOT CONVERGED.**

**PR #150 MERGED by user instruction, squash `1706930`, on master.** CI `verify` green, 24 commits.
The branch touched **no production code path** (empty diff vs `app/ lib/ components/ worker/
supabase/migrations/`) — it is plan + scripts + rollback + reviews. **`0027` DOES NOT EXIST YET**;
M4-α has not started.

**✅ r3 B2 CLOSED — user chose (a). PR #152 MERGED, squash `903004d`.**
The gate used to name **29 of 161** objects (18%) and reported *"M4 is PRESENT as expected"*, exit 0,
over a DB with **all seven own-table guard triggers dropped**. It now compares against
`docs/superpowers/specs/m4/live-manifest.txt` — **161 objects DERIVED BY EXECUTION** by
`scripts/gen-m4-manifest.py` (clone pre-M4 → apply → `after EXCEPT before`). Set algebra:
present = `MANIFEST ⊆ live`, absent = `MANIFEST ∩ live = ∅`.

⛔ **Not by parsing SQL** — that reproduces the defect: `grep -c "^create trigger"` undercounts by
one because `art_summary_has_no_source_trg` is a **`create constraint trigger`**.
⛔ **The generator fails closed if the baseline already has M4** — the manifest is a *diff*, so an
applied `0027` would yield a manifest that passes over any database at all.
**Mutations 5/5**, the fifth being *all seven own-table guards dropped → `--expect-present` FAILS*.
Self-tests: gate **20/20**, builder **22/22**, `gen-m4-manifest.py --check` is the staleness ratchet.

⚠ **Bounded:** this is NOT a proof that `db push --linked` is atomic. §4's one-transaction property
is still **NOT VERIFIED** — a partial apply is now *detectable*, not impossible.

**Round 3 verdict: NOT CONVERGED. Round 4 is due on the fixes.** Halves + adjudication in
`docs/reviews/plan-m4-v2-r3-{codex,claude,coordinator}.md`.

Round 3's lesson, worth keeping: **the defect class shifted.** r2 was *"the code has never run"*;
r3 is *"the code runs, and the claims about what it covers are wider than the code"* — every r3
finding sat in a **seam between artifacts**, where nothing executes. Both halves reproduced every
measurement; what was wrong was what I said about them. See [[quote-the-code-dont-characterise-it]].

**ALL FOUR EXTRACTION ARTIFACTS ARE DONE AND EXECUTED.** Embedded code **336 → 148 lines**.

| Artifact | State |
|---|---|
| `scripts/check-live-schema.py` | ✅ **16/16** self-test. Now also fails on `ADR0011_REMOVED` in BOTH polarities |
| `scripts/mutate-live-schema-check.sh` | ✅ **3/3** mutations caught |
| `scripts/build-m4-schema.py` | ✅ **NEW, 14/14.** Builds the post-ADR-0011 schema; replaces `cat 01 03 04` |
| `supabase/rollback/rollback_0027_stable_blob_addressing.sql` | ✅ **PROVEN**: 161 objects, LEFTOVER 0, DESTROYED 0, `skipping` 0 |
| `scripts/run-schema-assertions.sh` | ✅ all **four** outcomes executed (2/2/0/1) |
| `docs/superpowers/specs/m4/seed-assertion-corpus.sql` | ✅ runs; self-asserting; 3 mutations |

**⛔ THE FINDING THAT JUSTIFIED THE WHOLE EXTRACTION — `0028` CANNOT BE A MIGRATION.**
MEASURED with two throwaway migrations (9998 creates a table, 9999 drops it): `supabase migration up`
applies **every** pending file in ascending order in **ONE pass**, later wins. A rollback filed as
`0028` runs straight after `0027` on every fresh DB — `db push` to prod, `db reset`, and
`tests/integration/global-setup.ts`. **The pair composes to a NO-OP: production gets an empty
milestone.** The plan committed both into `supabase/migrations/`. It now lives in
`supabase/rollback/` (`schema_paths = []`, never replayed). See [[a-test-that-cannot-fail]].

**⭐ TWO GATES WERE MEASURING THE WRONG SUBJECT, and both were found by RUNNING, not reading:**
1. `check-live-schema.py` reported **"ABSENT as expected"** over a DB still carrying
   `sync_corrections_to_workspace_video()` + both `videos_corrections_sync_*` triggers — its
   inventory is post-ADR-0011, so it was blind to anything ADR-0011 deletes. Same shape as the
   `cascade` residue it exists to catch. See [[a-mechanism-can-be-silently-overridden]].
2. `mutate-live-schema-check.sh` built M4 with `cat 01 03 04` and called it "the REAL pre-M4 schema"
   — a **pre**-ADR-0011 schema M4 will never ship. It was proving the gate against a fiction.

**⚠ "13 triggers" was a GREP ARTIFACT — the real count is 14.** `grep -c "^create trigger"` misses
`art_summary_has_no_source_trg`, declared `create constraint trigger`. **Any inventory built by
grepping `create trigger` misses every constraint trigger.** Measured inventory: 161 objects —
8 tables+views · 70 columns · **14** triggers (7 live + 7 own) · 13 functions · 1 enum · 12 indexes ·
5 policies · 38 constraints. See [[a-convention-catches-what-you-read]].

**Open, flagged for round 3, NOT filed** (filing is the user's step): `0027` ships
`corrections_hash_of` and `no_corrections_hash` with **zero callers** — Task 1 claimed "Task 2 keeps
a caller" and that is false. Revoked from public/anon/authenticated, so dead code not exposure.

**ROUND 3 IS RUNNING** — both halves dispatched against `2649094`. Codex →
`docs/reviews/plan-m4-v2-r3-codex.md`; Claude subagent → `…-r3-claude.md`. Its mandate is at
`scratchpad/r3-prompt.md`: attack the CLAIMS, since the code now runs.

---

**(superseded) WHERE M4 STANDS 2026-08-25 14:10**

**Phase 6 RAN and produced [[ADR-0011]] `docs/adr/0011-corrections-stay-per-playlist.md`** — accepted
by the user. Its finding: nine of eleven Blocking/High across five rounds were ONE defect —
`corrections` given WORKSPACE scope while its truth stayed PLAYLIST scope, outside the append-only
model. Option (a) chosen: corrections stay per-playlist. That **dissolved four findings with no code**
and cut M4 from 9 live-table triggers to **7**.

**The old plan (v5.1) is SUPERSEDED.** The live one is
`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` — 10 tasks, ~56 steps, written from
ADR-0011. Two review rounds done, both NOT CONVERGED; adjudications in
`docs/reviews/plan-m4-v2-r{1,2}-coordinator.md`. **Read those two before touching anything.**

**⛔ THE ROOT CAUSE FOUND AT ROUND 2, and it governs what happens next.** Every Blocking across both
rounds — **8 distinct, 0 exceptions** — was inside a fenced code block I wrote and never executed.
The plan carried **48 code blocks / 336 lines** of code as prose. The reviewers execute it; it fails
every time. **DECISION: EXTRACT AND EXECUTE** — the four executable artifacts move into the repo where
they can be run, and the plan REFERENCES them.

| Artifact | State |
|---|---|
| `scripts/check-live-schema.py` + `scripts/mutate-live-schema-check.sh` | ✅ **DONE `f0c789c`** — 10/10 self-test, green on the real stack, **mutation-proven** (cascade residue drives it RED in a scratch DB) |
| `0028` rollback SQL | ⏳ still in the plan; **its content is VALIDATED** — r2-claude executed it: forward+reverse catalog diffs 0 rows, zero silent no-ops, with a control |
| `scripts/run-schema-assertions.sh` | ⏳ still in the plan, never executed |
| `docs/superpowers/specs/m4/seed-assertion-corpus.sql` | ⏳ still in the plan, **known broken** — `auth.users` insert fires `on_auth_user_created`, duplicate key |

**Then round 3, on a plan whose code has already run.**

**Open findings not yet folded** (all in the r2 coordinator doc's table): Task 9 invokes the gate
suite without `M4_PHASE`; `05_assert` sweep misses `:1913,:1915`; "13 triggers" is a grep artifact.

**⚠ MEASURED AND BIGGER THAN THE FINDING SAID: FIVE of the six schema gates rebuild from spec files**
(`verify-schema.sh`, `mutate-schema.py`, `check-guard-coverage`, `check-sentinel-meanings`,
`check-vocabulary-collisions`). Only `check-docs` has no database. **The existing suite is a
PRE-migration suite in its entirety** — so there is no `M4_PHASE=post` arrangement in which "all six
green" is achievable, and the post-migration profile is almost all new instrumentation.

**⚠ THE $? -AFTER-A-PIPE BUG FIRED FOUR TIMES TODAY**, including twice after I documented it in this
same session. Knowing it by name does not prevent it. **Redirect to a file; never read `$?` after a
pipe.**

**⚠ "Fixed at one of two sites" fired THREE times today** (v5's `:120`, the `05_assert` sweep, the
`M4_PHASE` callers). **A fix that adds a requirement must grep for its callers in the same edit.**

---

**(SUPERSEDED — kept for the trail) WHERE M4 STOOD 2026-08-25 11:0x — Phase 6 had just fired.**
Branch `docs/m4-plan`, PR **#150**, 6 commits, pushed, NOT merged. Plan is
`docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` v4 + a measured T1.
**Round 4 SPLIT: Codex CONVERGED (0B/0H) vs Claude NOT CONVERGED (2B/2H/4M/4L).** Rounds 1-3 also
NOT CONVERGED → **fourth non-converging round → `dev-process.md` Phase 6 fires. M4 does NOT exit
Phase 2.** Adjudication + every hand-verification is in
`docs/reviews/plan-m4-promote-schema-r4-coordinator.md` — read THAT first.
**The 4 findings are deliberately NOT folded into a v5**: Phase 6 says architecture review, not a
fifth patch (`gates-detect-defects-not-design`).
⚠ **The first r4-claude dispatch never wrote its file**; a replacement did. A bounded poll exiting 0
means *I stopped looking*, never *it isn't there*.

**Round 4's four, all hand-verified by the coordinator:** B1 no rollback section exists at all ·
B2 no behavioural test suite in the gate list, for a migration taking 4 live tables from 2 triggers
to 11 (`test:integration` appears NOWHERE in the plan, and `ci.yml:6-10` excludes it) · H1 committing
`0027` **IS** M4-α unseeded on every dev machine — `tests/integration/global-setup.ts:43-51` runs
`supabase migration up` and THROWS rather than skip, so the T2→T6 order is fiction · H2 `workspaces`
is the ONLY new table with no revoke (5 created, 4 revoked; `01_workspaces.sql` has **0** vs 8 and 12).

⚠ **B1's premise is FALSE and correcting it makes B1 WORSE.** `supabase migration down` **does**
exist on CLI 2.115.0 — but it *resets* (drop-and-recreate) and takes `--linked`, so it can be aimed
at prod. *"There is no way back"* makes someone write `0028`; *"there's a `down`"* invites them to
destroy prod. **A false premise arguing for the right conclusion is the most expensive kind to leave
standing — nobody re-examines a finding they already agree with.**

**⭐ NEW, GENERAL — a finding cites where the reviewer SAW a problem, not where it LIVES.** `plan:120`
still carried the exact overstatement `plan:167-173` retracts, because Codex cited two line ranges and
I fixed it *at the citations*. **The fix for a claim-level defect is a `grep` for the claim, not an
edit at the citation.** See [[true-about-the-name-silent-about-the-layer]].

**M4's three load-bearing facts:** (1) M4 is NOT inert — it ALTERs playlists/videos/jobs, adds 9
triggers to live tables; (2) the `workspace_videos` backfill uses `distinct on` and **can silently
drop a paid correction** — MEASURED 0 in prod, but only because no video is in two playlists yet, so
T2 carries an in-transaction assertion; (3) `05_assert.sql` must NEVER be a migration — it contains
`delete from profiles` and an arbitrary-SQL executor.

**If round 4 converges on both halves, M4 exits Phase 2. If not, that is the FOURTH non-converging
round and `dev-process.md` fires Phase 6.**

**Also merged today:** PR #151 — `.claude/skills/*` are SYMLINKS into `.agents/skills/`; three were
missing so `explain-findings` had never been loadable. See
[[it-already-exists-under-a-name-i-didnt-search]] for the `ls | transform` habit that caused it —
now THREE instances (`head -20`, `[:12]`, `sort -u`).

**Still open: half (2), the generated page — backlog #59**, one card per ANCHOR, must POINT at the
roadmap for state. It now has real input. ⚠ Still a **detour** — not stable-id work; M3 is.

See [[the-control-refuted-the-premise]] and [[a-mocked-boundary-tests-the-contract-you-imagined]] —
same family: a claim correct about the thing it names, wrong about the thing it is for.
