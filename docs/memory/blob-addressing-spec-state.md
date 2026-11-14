---
name: blob-addressing-spec-state
description: "FIRES-WHEN: citing the stable blob addressing SPEC rounds (PRs #51–#58) or its schema harness — HISTORY: the spec's schema was promoted as migration 0027 (M4, PR #155); current state lives in anchor-name-and-stable-id-handoff"
metadata: 
  node_type: memory
  type: project
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-08T20:25:22.188Z
---

**CURRENT STATE: this file is HISTORY.** The spec's schema was promoted into
`supabase/migrations/0027_stable_blob_addressing.sql` by M4 (PR #155, `c517faa`, 2026-08-27) and applied
to production. For where the work stands now, read [[anchor-name-and-stable-id-handoff]]. The spec-side
harness still exists: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/` holds `schema/`,
`verify-schema.sh` (runs in a rollback against local Postgres, each assertion naming its guard) and
`mutate-schema.py` (three outcomes RED / GREEN / INVALID — a two-outcome harness reports its own broken edit
as an untested guard).

**Rules this spec taught, still live:**
- **Every function pins its `search_path`** (except `assert_raises`, the labelled exception) — the same bug
  class appeared four times in one day, the last reached from a definer function *through a CHECK
  constraint*. Don't remove a pin to "simplify".
- **A rule can be overturned by a change that never mentions it** (r7 B1: item 3's freeze trigger silently
  restored as a rejection the 2026-08-07 decision [[reservation-guards-spending-not-recording]] had removed;
  measured as `[23505]` on a worker that merely restarted).
- **Interactions are where the defects are:** every r7 Blocking/High was between two items and in none
  individually, while both reviewers confirmed the instruments' counts as true.
- **Classify guards SHAPE vs SEQUENCE before another review round** — it found two defects seven rounds
  missed ([[guard-classification-shape-vs-sequence]]).
- **Stacked PRs:** retarget the child FIRST, then merge and delete the parent — see
  [[a-stacked-pr-dies-with-its-base-branch]] (recovery recipe there; it was learned here).
- Read `3fb6970` before trusting any verification claim from round 5 or earlier
  ([[test-harness-can-launder-failures]]).

## History (2026-08-06 .. 08-08)
- **PR #51 `a4a410b`** — spec + spec-adjacent SQL, 57 assertions; merged NOT CONVERGED after six rounds
  (7 → 8 → 10 → 6 → 7 → 8 Blocking) because nothing in it runs.
- **Item 1, `detached` fencing — PR #52 `7e26f58`:** of four bypasses, 2 fixed, 1 closed by
  `art_detached_is_dig`, 1 never a defect ([[detached-dig-retention-decision]]).
- **Item 2, corrections — PR #53 `610a31c`:** nullable column conflated "no corrections" with "never
  computed" → NOT NULL + backfill + anti-drift trigger ([[defined-not-derived-constants]]).
- **Item 4, reservations — PR #54 `ccc7eb7`:** `reserve_artifact_slot` / `renew_artifact_lease` /
  `record_artifact`; the reviewer's fix DECLINED on purpose. 73 assertions, 22/22 mutations.
- **Item 3, generation-write API — PR #55 `1cd884a`:** a cloud summarize could not reserve a slot at all
  (`[23503]` one way, `[23514] gen_card_complete` the other, the paid Gemini call between). `state`
  (`pending|complete`, default complete = fail-closed). 89 assertions, 35/35. Task #25 dissolved with zero
  schema change (third finding from reasoning about a NAME, not the constraints).
  See [[unsatisfiable-ordering-is-the-tell]], [[what-mutation-testing-proves]].
- **Round 7 — PR #56 `aad6aee`:** 2B/3H/5M; 98 assertions, 41/41.
- **Guard classification — PR #57 `0b27094`:** free renders could never be overwritten; §8's retention
  sweep could never run. Also split `dev-process.md` 576 → 190. 103 assertions, 44/44, 32 guards.
- **Round 8 — PR #58 `dc92859`:** 3B/5H/6M; 119 assertions, 58/58, 38 guards. Left open then: two Lows and
  `persist_summary` merge semantics ([[worker-vs-sync-fencing-gap]]).
- **Round 9:** ownership fence on `(worker_id, job_id)` ([[a-fence-wrong-both-ways-asks-the-wrong-credential]]);
  producers at all four workspace-chain levels; GC floor `state = 'complete'`; 5-minute `produced_at` skew;
  divergent `blob_key` raises. Later rounds through r17 are summarised in the M4 roadmap spine.
