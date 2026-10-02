---
name: guard-coverage-scope-merged
description: "FIRES-WHEN: citing PR #298 or the guard-ratchet scope fix — ⭐ MERGED PR #298 (squash 31fc8a72) — the guard ratchet saw 41 guards while ignoring 14 on tables IT BUILDS. Root cause: CATALOG_SQL's four clauses read THREE different scopes, so a table entering through one stayed invisible to the others — 4th occurrence. Now OWNED/FOREIGN, 55 guards, and the enumeration finally has a falsifier"
metadata:
  type: project
---

**Merged 2026-09-14, squash `31fc8a72`.** Closes half of backlog #29; the other half is sized there.

## What was wrong, and why it kept happening

`check-guard-coverage.py` exists so that **adding a guard forces a classification decision**. It
printed *"every guard classified"* over 41 while five guards on `video_artifact_sources` — a table
**M4's own `04_artifacts.sql` creates and the gate BUILDS** — were outside its query, and nine keys
beyond that.

⛔ **Root cause: `CATALOG_SQL` had FOUR clauses reading THREE scopes** — CHECKs on `TABLES`,
FKs/triggers on `TRIGGER_TABLES`, unique indexes on `TABLES` **and only if named `%_uq`**. A table
entering through one clause stayed invisible to the others. Round 9 widened triggers and left FKs;
round 11 fixed FKs and left the rest; my first commit widened one and my own commit message called it
*"the third time"* while committing the fourth.

⚠ The `_uq` filter was a **NAMING CONVENTION ACTING AS A SCOPE RULE**: a unique constraint on
`video_generations` — already in scope — was invisible purely for declining to be called `_uq`.

## The shape that now holds

    OWNED_TABLES    workspaces, workspace_videos, video_generations, video_artifacts,
                    video_artifact_sources        — M4 creates them, ALL FOUR clauses apply
    FOREIGN_TABLES  videos, jobs, playlists, profiles — M4 adds only triggers and FKs, so only
                    those two clauses. Their PKs and CHECKs predate M4 and belong to no gate yet.

**41 → 55 guards.** Nine keys classified from their WRITERS (`pg_get_constraintdef`, then the insert
that can hit them), not from their names. See [[a-measurement-is-only-as-good-as-its-corpus]].

## ⭐ The finding worth remembering beyond this repo

**The enumeration — the component wrong FOUR times — was the one part with no falsifier.** All 16
self-test cases and all 5 mutations drove `evaluate`, the rule engine. Nothing ever tested which
tables the query asked about. Now `clause_scopes()` + `clause_predicates()` + `scope_problems()`:
pure functions that read which table set and which predicates each clause carries, and refuse when
they disagree — **checkable with no database, because the SQL is a formatted string**.

⚠ Three rounds were needed to get that check right, each finding the previous round's repair:
r1 the array, r2 the predicates (`_uq` can return with the array unchanged), r3 the JOIN
(`join pg_class c on … like '%_uq'` sits BEFORE the `where` the pin read). I predicted `or` and
nesting; both were already caught; the one that worked came from a direction I had not enumerated.

## Stated rather than hidden

* **Three of four new SEQUENCE keys are in `MUTATION_EXEMPT`** — the first entries ever, against a
  comment saying "empty by design". I wrote the mutations, ran them, and all three went **GREEN**:
  the corpus cannot reach those paths (a profile cannot be inserted twice; a retry short-circuits
  before re-inserting the generation). Each carries the measured reason. Codex tried to invalidate
  one and could not.
* **25 CHECK constraints on the MONEY tables remain outside this gate** (`guardrail_config` 13,
  `spend_ledger`, `usage_counters`, …). That is a scope decision, named in the code and in #29 — the
  success line now says *"every BLOB-ADDRESSING SCHEMA guard"*, because "every guard" turned a
  decision into an invisible gap.

Related: [[schema-gates-in-ci-merged]] (the slice whose merge fired #29's trigger),
[[a-mutation-loses-its-binding]] (3 anchors orphaned here),
[[a-second-implementation-of-one-rule-drifts]] (the fix copied its own locator).
