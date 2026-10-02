---
name: schema-gates-in-ci-merged
description: "FIRES-WHEN: citing PR #297 or the schema gates in CI — ⭐ MERGED PR #297 (squash 3168f028) — the 15 schema gates run in CI on a database built from the repo in 14s; 93s job, ZERO added wall clock. 4 review rounds, 24 findings, EVERY round found its defects in the previous round's FIXES. Nightly prod-drift is built but its cron is deliberately UNARMED pending a secret"
metadata:
  type: project
---

**Merged 2026-09-14, squash `3168f028`.** `.github/workflows/schema-gates.yml` + `scripts/ci/`.

## What exists now

    scripts/ci/start-schema-db.sh      builds the gates' database in a container, 14s
                                       27 migrations + 3 fixtures, asserts M4 PRESENT
    scripts/ci/{storage,auth}-service-fixture.sql, seed-corpus.sql
    scripts/check-storage-independence.py   holds the storage fixture to its own claim
    job `schema-gates`   path-filtered, per push/PR, 93s in CI, runs BESIDE verify
    job `prod-drift`     production drift — the only genuinely scheduled subject

**Run it locally:** `scripts/ci/start-schema-db.sh m4_schema_gates` then
`PGCONTAINER=m4_schema_gates M4_PHASE=post scripts/check-schema-gates.sh`.

## ⛔ THE ONE THING WAITING ON A HUMAN

`prod-drift` needs repository secret **`CLAUDE_RO_DATABASE_URL`**. Its cron is **deliberately not
armed** — arming an alarm that cannot pass produces a nightly red until someone adds the credential,
and backlog #56 measured that as how a gate gets switched off. The job still REFUSES loudly (rc=2)
whenever it runs without the secret; it is simply not scheduled. **To arm: uncomment the two lines in
the trigger block.** `workflow_dispatch` works meanwhile, and all four steps were driven locally.

## The sizing I inherited was wrong in both directions — check estimates like this

    "≈1 day, mostly Supabase roles"   the IMAGE ships roles, auth/extensions/storage, auth.users
    "~232s roughly doubles CI"        jobs run in PARALLEL; measured 93s against a 5-8 min critical path
    "backlog #56 measured that"       #56 measured a gate disabled for firing on DOCS-ONLY commits

Nightly was also wrong for gate 12, which guards REPO CODE: a nightly red arrives a day late, on
whoever pushes next. See [[a-retrospective-number-needs-provenance]].

## Four image-vs-stack gaps, each found by a gate REFUSING rather than passing

    storage.buckets/objects absent   0007 aborts, taking 4 PUBLIC functions with it
    auth.users lacks is_anonymous    21 cols vs 35; exactly 1 is read by our code
    auth.uid() reads only the legacy singular GUC, not the JSON PostgREST sets
                                     -> owner cannot read own row: RLS SILENTLY off
    empty database                   one tenant makes cross-tenant assertions vacuous

⚠ `pg_isready` IS NOT A READINESS SIGNAL for `supabase/postgres` — the init phase runs a temporary
server that answers yes and then shuts down, and **the image's own HEALTHCHECK uses it**, which rules
out a `services:` block. Wait for `PostgreSQL init process complete` in the logs, then a query.

## ⭐ EVERY ROUND FOUND ITS DEFECTS IN THE PREVIOUS ROUND'S FIXES — 4 rounds, 24 findings

r1 claude 2B/1H/5M/4L · r1 codex 1H/1M/1L · r2 codex 1H/1M · r2 claude 3M/2L · r3 codex 1M.
Zero overlapping findings between halves across every round. One guard's population widened
**12 → 21 → 27 → 30**, each step bought by a measured miss. This is the evidence base for
alternating rounds on the DELTA rather than one concurrent pair on a frozen tree —
see [[a-filed-finding-s-proposed-fix-is-a-hypothesis]] and [[dual-review-what-it-catches]].

Related: [[a-stated-bound-outlives-its-hole]] (PR #296, the branch before this one),
[[an-instrument-that-edits-the-repo-corrupts-its-peers]] (I committed another session's WIP here).
