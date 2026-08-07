# Stable blob addressing — round 4, coordinator's own pass (JOB 1)

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` @ `51bb71b`
**Date:** 2026-08-06. Written before either reviewer reported.
**Scope:** JOB 1 only — sweeping each *physical* rule across **every** site rather than the site where
it was learned. That framing was added this round because rounds 2 and 3 each fixed a physical
constraint at one site and had it recur at a sibling. It found two more before the round even started.

---

## BLOCKING

### J1-1 — Physical rule 4, THIRD recurrence, at a site I wrote and never swept

```
spec:504   alter table videos add column workspace_id uuid not null references workspaces(id);
```

`videos` is the core table and is always populated, so this **aborts**: *column "workspace_id" contains
null values.* Identical to the `playlists` statement I fixed in round 2 (spec:394 now documents exactly
why it fails) and to the `workspace_videos` and `jobs` statements round 3 caught.

**What makes it worth more than a one-line fix:** it sits in the **same edit** as the
`workspace_videos` block, four lines below a paragraph explaining this precise failure, and it survived
a cross-derivation pass *and* a full review round. Fixing a physical rule where you met it does not
generalise, even when you have just written down that it doesn't.

**Change.** Three-phase, matching the `playlists` treatment already in §5.0:
add nullable → backfill (`from playlists p where p.id = videos.playlist_id`) → `set not null`.

---

### J1-2 — `video_generations` is where SIX fixes went to prose and never reached the DDL

The block at spec:1069-1078 is the original round-1 draft. Every subsequent decision about this table
was written as narrative elsewhere and **never applied here**:

| Fix, and where the prose says it | Present in the DDL? |
|---|---|
| `kind` becomes the `artifact_kind` enum, widened beyond `summary｜dig` (spec:663) | ❌ still `kind text not null -- 'summary' \| 'dig'` |
| `unique (workspace_id, video_id, generation_id, kind)` (spec:660) | ❌ absent |
| FK to `workspace_videos` (spec:509) | ❌ absent |
| Card completeness `check (kind <> 'summary' or card ?& array[…])` (round 2) | ❌ absent |
| A lifecycle marker — `body_collected` (round 1 H7) | ❌ absent |
| `doc_version_major`, which rule 13's ordering **ranks on** | ❌ the column does not exist |

**The consequence is not cosmetic.** The composite FK in `video_artifacts` (spec:613-614) references
`video_generations (workspace_id, video_id, generation_id, kind)` — and the unique constraint that FK
requires **exists only in an English sentence**. So round-2's C2 was never actually fixed for this
table; it was *described*. That is why round 3 MEASURED the `video_artifacts` DDL failing to create:
the reviewer ran what was written, and what was written had never been updated.

Rule 13's ordering is worse than absent — it ranks on `doc_version_major`, a column no table in the
spec defines. The ordering is unimplementable as specified.

**Why this shape is the dangerous one.** Round 3 established *"where the prose and the DDL disagree,
the DDL is the fix and the prose is a claim."* This is that failure **at table scope** rather than at
field scope: six separate fixes, one table, none applied. Each was individually reviewed and accepted,
because reviewers read the prose the fix was written in and not the block it should have edited.

**Change.** Rewrite the `video_generations` block as real DDL carrying all six, then re-run the JOB 1
sweep against the rewritten block — it will be new, and new DDL is exactly what the physical rules
bite.

---

## Note on method

Both findings came from `grep`-ing the spec for *the shape of a rule* rather than reading the spec for
*correctness*: every `add column`, then every `foreign key`, then asking which target each one needs.
That took minutes and found two Blocking, one of which had survived a review round and a
cross-derivation pass.

**The generalisation for the inventory:** an I rule is checked by *thinking*; a P rule is checked by
*enumerating*. They need different verification methods, and the inventory currently records only the
classification, not the method that goes with each class.
