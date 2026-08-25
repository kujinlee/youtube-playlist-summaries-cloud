# M4 plan v5 — round 5 COORDINATOR adjudication

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema.md` (v5, `6bf3726`)
**Halves:** `…-r5-codex.md` (**NOT CONVERGED**, 1B/1H/1M/2L) · `…-r5-claude.md` (**NOT CONVERGED**, 3B/3H/5M/5L)

**Anchor:** stable-blob-addressing · **ADR:** 0006, 0007

---

## ⛔ THE STANDING CONDITION IS MET. PHASE 6 FIRES, AND IS NOT ARGUED AGAIN.

v5 wrote its own trigger, when Phase 6's four-round count was overruled:

> *"if round 5 returns **new Blockings caused by v5's own fixes**, Phase 6 fires and is not argued again."*

**Both halves answer the primary question YES, independently.** Codex: one Blocking in T9. Claude:
**three Blockings, all in text that is new in v5**, two of them established by **execution** rather
than reading. This is not a close call and there is no version of the argument I made last time that
survives it.

**I made these defects.** v5 was written by the coordinator in one sitting, ran eight green ratchets,
and was committed and pushed **without a review** — the gap the user caught by asking. The ratchets
check documentation integrity; they say nothing about whether a plan is right.

---

## The three v5-introduced Blockings, coordinator-verified

### B2 — the gate I wrote for T9 asserts the OPPOSITE of what is observable ⭐ worst of the three

T9's gate: *"`0028` applies, and the six schema gates go **red** afterwards — proving it removed the
schema."*

**Verified by reading the gates.** Five of six never read an applied schema; they **rebuild it from
the spec files** inside their own rolled-back transaction:

```
verify-schema.sh:10        SQL=$(printf 'begin;\n'; cat "$DIR"/0*.sql; …'rollback;\n')
check-guard-coverage.py:195-206   sql = "begin;\n" + every SCHEMA.glob("0*.sql") + … + "rollback;"
```

With `0027` applied, re-executing that DDL hits `relation "workspaces" already exists` under
`ON_ERROR_STOP=1`. So the true polarity is **`0027` applied → RED; `0028` applied → GREEN**, and my
gate claims the reverse. Run literally it would report **red as success** — worse than an
unfalsifiable gate, because someone would act on it.

The reviewer's replacement is right and needs no rewrite: after `0028`, assert `pg_class` holds none
of the five tables and `information_schema.columns` has no `workspace_id` on the three live tables.

### B1 — T9's "lossless" property is false, and the counterexample is four sections above it in the same file

Codex reached this via the grep proving only *no direct artifact caller*. The sharper form, which the
coordinator verified: the corrections sync is **one-way** `videos.data → workspace_videos`
(`03_generations.sql:227-234`), so in normal operation corrections stay derivable. **But after a
playlist delete the `videos` rows are gone and the `workspace_videos` row survives holding
corrections that exist nowhere else**, and nothing cascades them away. `0028` would delete paid
content.

**That orphan is item 4 of v5's own must-not-skip block.** v5 filed it as a product question (Open
Questions) and wrote T9 as a rollback task, and never noticed that the first falsifies the second.
**Two individually-defensible changes, in one document, contradicting each other — a composition
defect, which is precisely what Phase 6 exists for and what I claimed round 4 had not produced.**

### B3 — T2's abort guard and T4's seeding instruction cannot both be satisfied

Both sentences are new in v5. If T4 seeds the collision it demands, T2's guard aborts `0027` and no
assertion runs; if it does not, T4's own complaint stands. **MEASURED** by the reviewer at
`CONFLICTING_GROUPS=1`.

And the part that matters more: with the guard removed, the backfill discards a paid correction and
`05_assert.sql:65-70` **still passes**, because both sides count *videos having some corrections*.
So T4's seeding does not un-vacuum the assertion — it makes it **actively false-negative**. The real
fix is r3 H3's, two rounds old: compare **values**, not counts.

---

## What the reviewers REFUTED — recorded, because it is load-bearing

| Claim | Outcome |
|---|---|
| T10 is "a decision wearing a checkbox" (coordinator's own worry, put in the prompt) | **REFUTED.** `test:integration` genuinely exercises trigger-bearing paths — `worker-persistence-rpcs.test.ts:17-18`, `job-queue-schema.test.ts:88-90` |
| The `0028` drop order may not be expressible | **REFUTED by execution** — expressible without `cascade`, first attempt |
| `0027` breaks existing write paths | **REFUTED, measured** — it does not |
| T2's new order is unsatisfiable | **REFUTED** — a decision dependency, not an unsatisfiable one |
| T3's five-table list is incomplete | **REFUTED** — the five are the complete set |
| T6 names the wrong command | **REFUTED** — `db push --linked` is correct for this repo today |

⚠ **Still NOT VERIFIED, and must not be repeated as fact:** `db push --linked`'s one-transaction
property (help-checked, never a real remote push); `supabase migration down`'s drop-and-recreate
behaviour (inferred from CLI wording, deliberately not executed); production's `arwdDxtm` default
ACL (no `claude_ro` in the coordinator's environment).

---

## Hygiene

The Claude half was told to attempt real rollback SQL and to leave the shared stack untouched.
**Verified by the coordinator afterwards:** 0 stray M4 tables, 0 stray `workspace_id` columns, no
scratch databases, row counts unchanged at `playlists=5124 videos=3547`. Clean —
`an-instrument-that-edits-the-repo-corrupts-its-peers` did not recur.

## Not folded

**No v6.** Phase 6 runs first. Folding these findings into a sixth revision is the move that produced
the third one — and this round proved that a revision written to close findings can introduce worse
ones than it closes.

**Also pending, and NOT a review finding:** the user's design decision that T2 should **record and
warn** rather than abort on a corrections collision, on the grounds that the pre-M4 state is already
divergent (corrections live per-playlist in `videos.data` with no sync at all). That decision
independently dissolves half of B3 and belongs in whatever supersedes v5.
