# Architecture Review — 2026-08-25

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** A blob's address stops moving when a title or a serial number changes. This review asks whether M4's *composition* is sound, not whether its statements are correct.

**Trigger:** `docs/dev-process.md` Phase 6, second arming condition — *four adversarial rounds without
convergence*. It fired at round 4, was **deliberately overruled by the user**, and re-fired at round 5
on a standing condition v5 wrote for itself: *"if round 5 returns new Blockings caused by v5's own
fixes, Phase 6 fires and is not argued again."* Round 5 returned three, two by execution.

**Subsystem:** `workspace_videos` and the corrections path — `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/{01,03,04}.sql`, `supabase/migrations/0001`, `0021`, `0026`, and `lib/storage/supabase/`.

**Branch:** `docs/m4-plan` @ `f82be30` (plan **v5.1**).

**Method.** Read `CONTEXT.md` and every ADR status line first, then the plan, then all ten review
halves for rounds 1–5, then the schema by hand. Every claim below cites `file:line` and was opened.
**ADRs are not re-litigated** — finding 1 assesses a *gap between* ADR-0006/0007 and what M4 built,
not the ADRs' content.

---

## The one-paragraph answer

**Five rounds produced eleven Blocking/High findings, and nine of them are one architectural defect
wearing nine faces: `corrections` is paid, user-authored content that was given WORKSPACE scope while
its source of truth stayed PLAYLIST scope, and it was placed OUTSIDE the append-only generation model
that this architecture uses for exactly that kind of content.** Every reviewer attacked a symptom —
the `distinct on` that drops a correction, the orphan a delete strands, the rollback that cannot
restore it, the assertion that can only count — and every fix was locally right. None could succeed,
because the many-to-one has no reconciler and the content has no lifecycle. **This is the composition
defect the trigger exists to find, and per-round review was structurally incapable of naming it.**

---

## Finding 1 — 🔴 Blocking. A workspace-scoped row denormalizes a playlist-scoped truth, and nothing reconciles the collapse

**The two cardinalities, both read:**

| Table | Primary key | Scope |
|---|---|---|
| `videos` | `primary key (playlist_id, video_id)` `[0001_core_schema.sql:30]` | **per playlist** |
| `workspace_videos` | `primary key (workspace_id, video_id)` `[03_generations.sql:64]` | **per workspace** |

A workspace contains many playlists — that is its definition (`CONTEXT.md:36`: *"A user-chosen
grouping of playlists: two playlists in the same workspace share one copy of a video's artifacts"*).
So **N `videos` rows map to 1 `workspace_videos` row**, and `corrections` is copied across that
collapse. The schema states the direction in its own voice:

> `03_generations.sql:218` — *"`workspace_videos.corrections_hash` is a **DENORMALIZED COPY**; the
> truth lives in `videos.data`."*

**This single fact generates the entire defect series.** Each round found the shadow it cast:

| Round | Finding | Why it is this defect |
|---|---|---|
| r3 H3 | the `distinct on` backfill silently drops a correction `[03:89-95]` | N→1 with no merge rule; `distinct on` *is* the collapse |
| r4 M2 (→High) | delete strands the orphan; re-add resurrects it `[03:48, 0001:32, 03:183-187]` | the copy outlives the rows it was copied from |
| r5 B1 | T9's rollback cannot restore corrections | a copy whose source is gone is not derivable |
| r5 B3 | `05_assert.sql:65-70` compares **counts**, passes while discarding paid content | counts are all you *can* compare without a per-source identity |
| r5 B3 (first horn) | the abort guard and the seeding instruction were mutually exclusive | you cannot both forbid the collapse and require testing it |

**Five rounds, five fixes, all locally correct, none able to work.** A merge rule cannot be written
because there is nothing to merge on (finding 2). A lifecycle cannot be written because the row has
no owner among the playlists it summarizes.

**⚠ This is NOT a criticism of ADR-0006/0007.** The shared *body* is accepted design and correct:
artifacts genuinely are workspace-scoped, and `video_generations` `[03:358]` gives them
`primary key (workspace_id, video_id, generation_id)` — append-only, frozen, never overwritten. The
defect is that **`corrections` was carried along into workspace scope without being given that
model**, because it is user-authored rather than model-produced and therefore did not look like an
artifact. It is one `text` column updated by a plain `update` `[03:227-234]`.

**Direction (not a patch — Phase 6 proposes shape, and the choice is the user's):** either
**(a) return `corrections` to playlist scope** and let the workspace row carry only genuinely shared
artifacts — which dissolves r3 H3, r4 M2, r5 B1 and r5 B3 at once and costs the cross-playlist
sharing of corrections nobody has yet asked for; or **(b) give `corrections` the generation
treatment** — append-only rows keyed by their source, last-wins on read rather than on write, which
preserves sharing and makes every one of those findings expressible. **(a) is far cheaper and
subtracts rather than adds; (b) is right if corrections are meant to be shared.** The user's
2026-08-25 record-and-warn decision is compatible with both and settles neither.

---

## Finding 2 — 🟠 High. The architecture's own vocabulary already classifies `corrections`, and the classification was never applied

`CONTEXT.md:44` defines a **source-of-truth blob** as one that *"cannot be recreated for free… If a
source blob goes missing, the system enters **repair needed** — it must surface the gap, never
silently regenerate."*

`corrections` is stronger than that: it is **user-authored**, so it cannot be recreated **at any
price** — and it is **paid**, metered by `0026_record_correction_spend.sql`. It is the most
irreplaceable content class in the system.

**It has none of the protections the glossary defines for that class.** No manifest entry
(`CONTEXT.md:60` — the artifact manifest is *"the single source of truth for which copy is current"*),
no `repair needed` state, no promotion, no generation identity. It is free text —
`types/index.ts:74` is `z.string().optional()`; the column is `corrections text` `[03:52]`.

**The consequence is a live inconsistency in the accepted design, not just in M4.** `CONTEXT.md:58`
defines the **card** as carrying *"the stamps saying which format version and **which corrections the
body reflects**"* — an **immutable** stamp inside a frozen generation, pointing at a **mutable**
value. Overwrite the corrections and the generation still claims to reflect them. Nothing detects it;
`corrections_hash` is recomputed on write `[03:232]`, never compared against a generation's stamp.

**This is the finding I would not have reached from the plan.** It required reading the glossary
against the schema, which is the one thing per-round review never does.

---

## Finding 3 — 🟠 High. The gates cannot observe an applied schema, and nobody has named that axis

Round 5 B2 caught the symptom: T9's rollback gate asserted the schema gates go **red** after `0028`,
when the true polarity is the reverse. The architectural fact underneath:

**Five of six schema gates never read a live database.** They *rebuild* the schema from spec files
inside their own rolled-back transaction — `verify-schema.sh:10`
(`SQL=$(printf 'begin;\n'; cat "$DIR"/0*.sql; …'rollback;\n')`), `check-guard-coverage.py:195-206`,
and the same shape in `check-sentinel-meanings.py` and `check-vocabulary-collisions.py`.

So the entire gate suite answers *"is the SPEC internally consistent?"* — never *"does the DEPLOYED
schema match it?"* For a milestone whose whole purpose is **making the spec execute for the first
time**, that is the wrong question, and no instrument in the repo asks the right one. r3 B2 found the
*path* axis and the *transport* axis; **this is a third, and it is unnamed: the SUBJECT axis —
built-from-source vs introspected-from-live.**

**Direction:** M4 needs one gate that introspects `pg_class` / `information_schema` on the live stack.
It is cheap (round 5's Claude half wrote the query while proving `0028` is expressible) and it is the
only gate that could ever confirm M4-β actually happened.

---

## Finding 4 — 🟡 Medium. Three decisions made this milestone exist only in a document scheduled for replacement

Phase 6 asks: *what did we decide this milestone that isn't written down?* Three things, all made
2026-08-24/25, none in an ADR:

1. **Corrections collide → record-and-warn, never abort** (user decision). Currently only in plan
   `v5.1` `[:51-55]` — a document five revisions deep that this review recommends superseding. It is
   a durable policy about **paid content**, which is ADR material.
2. **Phase 6's trigger may be overruled by the user, against a written standing condition.** That
   happened, the condition fired, and the mechanism worked — but it exists nowhere except two commit
   messages and the plan header. It is a genuine process improvement and it will be lost.
3. **`.claude/skills/*` are symlinks into `.agents/skills/`** (PR #151). Load-bearing — three skills
   were unloadable for days — and recorded only in a commit message.

---

## What I checked and did NOT find — recorded so round 6 does not re-pay for it

| Hypothesis | Outcome |
|---|---|
| ADR-0006/0007's shared-body design is itself wrong | **REFUTED.** Artifacts are correctly workspace-scoped and correctly append-only `[03:358]`. The defect is what was carried along, not the design |
| `workspace_videos` is redundant with `videos` | **REFUTED.** It is the FK parent that makes artifacts addressable per workspace `[03:96-97]` — load-bearing |
| The nine triggers are excessive | **REFUTED.** Each derives one column on one table; r5 measured that `0027` does not break existing write paths |
| `test:integration` is decorative here | **REFUTED** by r5 — it exercises trigger-bearing paths (`worker-persistence-rpcs.test.ts:17-18`, `job-queue-schema.test.ts:88-90`) |
| The `0028` rollback may be inexpressible | **REFUTED by execution** (r5 L1) — expressible without `cascade`, first attempt |

**Still NOT VERIFIED, and must not be repeated as fact:** `db push --linked`'s one-transaction
property (help-checked only); `supabase migration down`'s drop-and-recreate behaviour (inferred from
CLI wording, deliberately not executed); production's `arwdDxtm` default ACL (no `claude_ro` in this
environment).

---

## Disposition

**M4 does not proceed to a v6.** Findings 1 and 2 are design questions that a sixth revision would
patch around, exactly as the previous five did. The order is: **settle finding 1's (a)-or-(b) with the
user**, record it and finding 4's three decisions as ADRs, then rewrite the plan from that decision
rather than amending v5.1.

**Finding 3 is independent and can start immediately** — it is one query and it unblocks any future
claim that M4-β actually applied.

⚠ **This review is verified against `f82be30`.** The plan moved twice today while reviews of it were
being adjudicated; a finding here is a claim about that commit, not about whatever the file says when
you read this.
