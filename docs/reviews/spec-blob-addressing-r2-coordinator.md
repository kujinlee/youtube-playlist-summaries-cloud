# Stable blob addressing — round 2, coordinator's own pass

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` @ `f2d4d3a`
**Date:** 2026-08-06
**Scope:** JOB B only — defects the round-1 **fixes** introduced. Written before either reviewer
reported. Every finding below is in text **I wrote in the last hour**, which is the point of the round.

---

## BLOCKING

### C1 — The `check` constraint makes four of the six slot kinds unrepresentable

**Defect.** I wrote `check (kind = case when slot like 'dig:%' then 'dig' else 'summary' end)` next to a
**mandatory** composite FK into `video_generations`. §2 defines six slot kinds: `summary`, `model`,
`dig:<sectionId>`, `digDeeper`, `pdf:<kind>`, `slide:<id>`. The rule is wrong for four of them:

| Slot | What the check forces | Reality |
|---|---|---|
| `model` | `kind='summary'` | A magazine model is a **separate paid Gemini call** (`generateMagazineModel`), not part of the summarize run — it has its own generation |
| `digDeeper` | `kind='summary'` | A paid **dig** artifact (`lib/dig/generate.ts`) |
| `pdf:<kind>` | `kind='summary'` + an FK to a generation | A deterministic **free re-render**; §4.1 even proposes content-hash addressing for it |
| `slide:<id>` | `kind='summary'` + an FK to a generation | §4 puts assets **outside generations entirely**, deliberately, so no generation id exists to reference |

**Failure scenario.** The `slide` slot cannot be inserted at all: the FK is `not null` by virtue of the
columns, and there is no generation to point at. A design that puts assets outside generations and then
requires every manifest row to name one contradicts itself in the same section.

**Change.** `kind` must be a first-class enum over the artifact taxonomy (`summary | model | dig |
digDeeper | render | asset`), the slot→kind mapping must be a table not a `case`, and the generation FK
must be **nullable** — free re-renders and assets have no generation. Then re-derive Codex B1's guard:
it is the *paid* kinds that need the FK.

---

### C2 — The composite FK has no target, so the schema does not create

**Defect.** `foreign key (workspace_id, video_id, generation_id, kind) references video_generations
(workspace_id, video_id, generation_id, kind)` requires a **unique constraint on that exact 4-tuple**.
`video_generations`'s primary key is the 3-tuple `(workspace_id, video_id, generation_id)`.

**Failure scenario.** `ERROR: there is no unique constraint matching given keys for referenced table
"video_generations"`. The migration fails outright.

**Change.** Add `unique (workspace_id, video_id, generation_id, kind)` to `video_generations` — trivially
satisfied, since `generation_id` is already unique within `(workspace, video)` — or carry `kind` only on
the generation and drop it from the artifact row. State which.

---

### C3 — `alter table playlists add column workspace_id uuid not null` cannot run

**Defect.** I wrote the column as `not null` with no default on a table that has rows in production.

**Failure scenario.** `ERROR: column "workspace_id" contains null values`. And the ordering problem is
deeper than a default: every existing **owner** needs a workspace row before any playlist can reference
one, and `handle_new_user()` only fires for *future* users.

**Change.** Specify the three-step migration explicitly: (1) create `workspaces` and insert one row per
existing `profiles` row; (2) add `playlists.workspace_id` **nullable**, backfill from the owner; (3) set
`not null`. §10 covers the *blob* migration and says nothing about this *schema* migration, which is a
separate and equally mandatory step.

---

## HIGH

### C4 — "Every document fact `not null`" contradicts §5.2's own `card jsonb` shape

**Defect.** My H2 fix says card completeness becomes "a schema fact, not a convention — every document
fact `not null` on `video_generations`." But §5.2 defines the card as a single `card jsonb` column that
is explicitly **NULL for a dig generation**. `not null` cannot apply to members of a jsonb value, and a
blanket `not null` on the column breaks dig generations.

**Failure scenario.** Either the constraint is unenforceable (jsonb members) or dig generations cannot be
inserted. The fix reads as closed and is not.

**Change.** Pick one: promote the document facts to real columns on `video_generations` (nullable only
where `kind='dig'`, enforced by a `check (kind <> 'summary' or (tldr is not null and ...))`), or keep the
jsonb and enforce completeness with a `check (kind <> 'summary' or card ?& array[...])`. The second is
cheaper and still a schema fact.

### C5 — The sweeper's "second root set" is a full-bucket scan with no cost stated

**Defect.** I added "objects with **no** manifest row at all" as a second GC root so orphans are
collectable rather than invisible. That requires enumerating **every object in the bucket** and
differencing it against the manifest — `list` is paginated (`supabase-blob-store.ts:137`, limit/offset)
and the local stack already holds 973 objects.

**Failure scenario.** Not incorrect, but unbounded and unspecified: no batch size, no resumability, no
statement of how a partial scan avoids concluding "no manifest row" from a *failed* listing — which is
root-cause shape #1 aimed squarely at the delete path. A `list` that errors must never read as "these
objects are unreferenced."

**Change.** Bound it: scan by workspace prefix, with a durable cursor, and state that a failed page
**aborts the sweep** rather than collecting what it did see.

---

## Note

All five findings are in text written during the round-1 fix pass, and three of them (C1, C2, C3) mean
the schema as written **does not run**. That is the round-2 thesis from `dev-process.md` — *"a Blocking
fix is itself a new, unreviewed design"* — demonstrated on my own work, in the same session that quoted
the rule.
