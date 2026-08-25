---
status: accepted 2026-08-25 (user decision, Phase 6) — narrows ADR-0006's shared-body scope. The
  shared body stands: ARTIFACTS are workspace-scoped and append-only. What is narrowed is what rides
  along with them — `corrections` does not. This ADR does NOT re-open ADR-0006 or ADR-0007; it
  records which side of their boundary one column sits on, a question neither ADR answered because
  neither was asked it.
  ⚠ ACCEPTED IS NOT IMPLEMENTED. `workspace_videos.corrections` exists in the spec schema and has
  never run as a migration, so this is a decision about what M4 promotes, taken BEFORE the schema
  executes for the first time. Zero production rows carry it.
---

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** A blob's address stops moving when a title or a serial number changes.

# ADR-0011 — Corrections stay per-playlist; only artifacts are shared

## Context

M4 promotes `workspace_videos`, the workspace-scoped row that makes a video's artifacts shareable
across the playlists in one workspace (ADR-0006). It also carries two columns that are **not**
artifacts: `corrections` and `corrections_hash` `[03_generations.sql:52,61]`.

Those two columns produced **nine of the eleven Blocking/High findings across five adversarial review
rounds**, and no fix converged. The architecture review of 2026-08-25 established why: a workspace
row was denormalizing a playlist-scoped truth, and the schema says so in its own voice —

> `03_generations.sql:218` — *"`workspace_videos.corrections_hash` is a **DENORMALIZED COPY**; the
> truth lives in `videos.data`."*

`videos` is keyed `(playlist_id, video_id)` `[0001_core_schema.sql:30]`; `workspace_videos` is keyed
`(workspace_id, video_id)` `[03:64]`. **N rows collapse to 1, and there is no merge rule** — because
`corrections` is free text (`types/index.ts:74` is `z.string().optional()`), so there is nothing to
merge *on*.

## Decision

**`corrections` is per-playlist. It lives in `videos.data`, where it already lives, and
`workspace_videos` carries neither the value nor its hash.**

Artifacts remain workspace-scoped and append-only. ADR-0006 and ADR-0007 are unchanged.

## Why not the alternative

The considered option was **give `corrections` the generation treatment** — append-only rows keyed by
source, last-wins on read. It preserves cross-playlist sharing of corrections and makes every
outstanding finding expressible.

It was rejected because **nobody has asked for corrections to be shared across playlists**, and it
adds a second append-only lifecycle to maintain in order to deliver an unrequested feature. This
decision **subtracts**; the alternative adds. If sharing is ever wanted, ADR-0011 is the thing to
supersede, and backlog **#23** (`{from,to}` pairs) is the prerequisite that would make union — rather
than last-wins — actually possible.

## Consequences

### What this dissolves — four findings, no fix required

| Finding | Why it goes away |
|---|---|
| **r3 H3** — the `distinct on` backfill silently drops a correction `[03:89-95]` | nothing to collapse; the seed becomes a plain `select distinct workspace_id, video_id` |
| **r4 M2** (raised to High) — delete strands paid corrections, re-add resurrects them | the workspace row never held them |
| **r5 B1** — T9's rollback cannot restore corrections | `0028` drops no user-authored content; the lossless property becomes true as stated |
| **r5 B3** — the abort guard and the seeding instruction were mutually exclusive | there is no collision to guard, seed, or record |

⚠ **The user's 2026-08-25 record-and-warn decision is therefore MOOT and is withdrawn** — it answered
"what should happen when two playlists' corrections collide in one workspace row", and after this ADR
no workspace row holds corrections. It is recorded here so that a reader of plan v5.1 does not
implement a guard for a state that cannot occur.

### What this removes from the schema

Two columns `[03:52,61]`, the backfill's corrections clause `[03:89-95]`, the derive trigger's
corrections columns `[03:183-185]`, the function `sync_corrections_to_workspace_video()`
`[03:227-236]`, and **two of the nine live-table triggers** `[03:253,258]`.

**M4 therefore attaches SEVEN triggers to live tables, not nine.** Every count in the plan and its
review trail that says "nine" is stale from this ADR forward.

⚠ `corrections_hash_of()` and `no_corrections_hash()` **survive** — see the ranking below.

### ⭐ The consequence that is NOT a simplification — and it is the interesting one

`04_artifacts.sql:717` and `:777` rank generations by

```sql
(g.card->>'mdCorrectionsHash' = wv.corrections_hash) desc,
```

— *"prefer the generation whose card says it reflects the corrections currently in force."* With
`wv.corrections_hash` gone, **that comparison has no right-hand side, and it must not simply be
deleted.**

The resolution follows from the decision and is a genuine improvement:

> **The card's `mdCorrectionsHash` stamp STAYS — it is an immutable fact about what the generation
> reflects. The COMPARISON moves to the reader, who supplies the hash of the playlist they are
> actually viewing.**

This dissolves the inconsistency the architecture review's finding 2 identified: an **immutable**
stamp inside a frozen generation was being compared against a **mutable** denormalized value, so a
generation could keep claiming to reflect corrections that had since been overwritten, with nothing
detecting it.

**"Is this generation corrections-current?" was never a property of the generation. It is a relation
between a generation and a viewer**, and once a shared artifact can be viewed from two playlists with
different corrections, it has two different answers at once. Storing it as a ranking term inside a
workspace-scoped view was the category error. Moving the comparison to the reader makes the ambiguity
disappear — the reader always knows which playlist they are in.

⚠ **This is the one place where (a) costs work rather than saving it.** The ranking term must move
out of the view, and the serve path must pass the viewing playlist's corrections hash. **Nothing
consumes it today** — `record_artifact` and `video_artifacts_current` have **zero callers** in
`lib/ app/ worker/` (searched, r5-codex), so this is free to do now and expensive at M5.

### What must be re-checked, not assumed

Three ratchets inventory these objects and will need their entries updated, not their logic changed:
`check-guard-coverage.py:58,132`, `check-vocabulary-collisions.py:49`, `check-sentinel-meanings.py:9,48`.
⚠ `check-sentinel-meanings.py:9` names `workspace_videos.corrections_hash` **in its docstring** as a
worked example of a nullable-column meaning; deleting the column without updating that line leaves a
ratchet explaining itself with an object that no longer exists.

## What would falsify this

- A user asks for corrections made in one playlist to appear in another **within the same workspace**.
  That is the feature this ADR declines to build, and the request is the signal to supersede it.
- Backlog **#23** ships `{from,to}` pairs, making corrections *unionable*. Union removes the "no merge
  rule" objection that is half this decision's basis, and the alternative becomes cheap enough to
  reconsider.
- A consumer of `video_artifacts_current` appears that cannot supply a viewing playlist. Then the
  ranking term cannot move to the reader and must be solved another way.
