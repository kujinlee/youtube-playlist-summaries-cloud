# Round 17 (Claude) — verification of the round-16 DISSOLUTION

**Subject:** `docs/adr/0007-artifacts-are-an-append-only-log.md` (711 lines, coordination only).
**Branch** `fix/adr-0007-round-13-findings`, **HEAD `9301405`**. **Surface:** `git diff 5de5ac3..HEAD`.
**Scope:** the round-16 claim that the GC floor needs no successor, and the four reconciliation edits
around it. Render addressing, and rounds 14/15/16's "could not break" lists, were not re-reviewed.

## MEASUREMENT — the executable schema DID run

Docker + the local Supabase Postgres were available and every claim below marked **MEASURED** was
executed against them inside a rollback transaction.

- `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` → `✅ schema verified
  (rolled back)`, `ALL_STATEMENTS_OK`, all assertions green.
- A separate probe (`01+03+04` + my own DO blocks, rolled back) produced T1–T6 below. No repo-tracked
  file was modified; `git status` shows only this new review file.

```
T1  COMPLETE row insertable with ONLY produced_at (no card/md_hash/doc_version_major): [model dig digDeeper]
T1  REFUSED: [<none>]
T2  summary with ONLY produced_at: REFUSED 23514 (gen_card_complete)
T3  model with NO produced_at: REFUSED 23514 (gen_complete_has_produced_at)
T4  record_artifact with NO pre-existing generation row: RAISED P0001
    "video_artifacts: cannot mark summary as recorded — generation gGHOST is <absent>"
T5  record against an ALREADY-COMPLETE generation: completed_by_another ; md_hash updated? f
T6  re-record with a DIFFERENT source set, join table under a BEFORE UPDATE OR DELETE trigger:
    INSERT ACCEPTED, no raise ; source rows now: 2 (union, not replace, not raise)
```

---

## VERDICT: **NOT CONVERGED** — 1 Blocking, 4 High, 3 Medium, 1 Low

**The dissolution's CONCLUSION is correct and I could not break it.** Nothing creates a
`video_generations` row before or during a paid call, so `video_generations_collectable` cannot return
one, so round 9's B1 window is genuinely closed by the deletions. Round 16 was right to withdraw all
three covers. What does not hold is the ADR's account of *why* — and one consequence of the same
deletion that the ADR does not name.

---

## BLOCKING

### B1 — Nothing inserts the `video_generations` row at record time, and the ADR never says what does. MEASURED unreachable.

**Claim.** The ADR's load-bearing sentence is *"the row is born **complete, at record time**, and there
is no instant during the paid call at which it exists"* `[docs/adr/0007…:463-464]`. It names no writer.
As the ADR leaves the schema, **no writer exists**, and every paid record raises.

**Evidence.**

- `reserve_artifact_slot` is the only non-fixture INSERT into `video_generations`
  `[VERIFIED: schema/04_artifacts.sql:307-313]`. Confirmed by grep across the repo: every other
  `insert into video_generations` is in `05_assert.sql`. The ADR deletes that function
  `[VERIFIED: docs/adr/0007…:389]`.
- `record_artifact`'s generation write is an **UPDATE**, not an insert
  `[VERIFIED: schema/04_artifacts.sql:556-565]`, gated on **two things this ADR deletes**:
  `and g.state = 'pending'` `[:564]` and `and g.reserved_by = p_token` `[:565]`. The ADR deletes both
  the `pending` state and the `reserved_by` column `[VERIFIED: docs/adr/0007…:389-390]`. As written the
  function would not even resolve `g.reserved_by` after the column drop.
- The artifact row FKs the generation `[VERIFIED: schema/04_artifacts.sql:85-86]`, and
  `video_artifacts_generation_complete` raises when the parent is absent
  `[VERIFIED: schema/04_artifacts.sql:1013-1026]`.
- **MEASURED (T4):** `record_artifact` for a paid slot whose generation row does not exist →
  `[P0001] video_artifacts: cannot mark summary as recorded — generation gGHOST is <absent>`. Not a
  race, not an attacker: the ordinary first record of a fresh generation.

**Why this is Blocking and not an implementation detail.** It is round 15's B3(a) one level up, and the
ADR states that standard itself: *"`record_artifact` is the ONLY writer of provenance… **Drop the
column and leave the RPC unchanged and `video_artifact_sources` is always empty**"*
`[docs/adr/0007…:591-596]`, followed by *"Consequences to write into the implementing slice, not
discover in it"* `[:656]`. Delete the only INSERT and leave the RPC unchanged, and **no generation row
is ever created**. The ADR's headline claim then holds for a degenerate reason — no row exists during
the call because no row exists ever — which is round 16's own B1 ("the marker had no row to be written
to") reproduced by the change that removed it.

**Fix (additive, one paragraph).** State in Consequences that `record_artifact` **INSERTs** the
generation row, born `complete`, before the artifact insert that FKs it — it already takes every
column needed (`p_card`, `p_md_hash`, `p_doc_version_major`, `p_produced_at`, `p_kind`)
`[VERIFIED: schema/04_artifacts.sql:468-473]`. Say explicitly that the `where g.state = 'pending' and
g.reserved_by = p_token` UPDATE `[:556-565]` is **replaced**, not merely unfenced, and that the
`on conflict do nothing` + `completed_by_another` branch `[:576-583]` is what makes a second writer
safe (MEASURED T5: a record against an already-complete generation returns `completed_by_another` and
does not overwrite `md_hash`). Two statements in one transaction; the FK ordering forces generation
first.

---

## HIGH

### H1 — "the four completeness constraints … demand `card`, `md_hash`, `doc_version_major` and `produced_at`" is true for `summary` ONLY. For `model`, `dig` and `digDeeper` a COMPLETE row is insertable before the paid call. MEASURED.

**Claim.** The ADR says record-time creation is *"**forced** by this ADR's own deletions, not chosen"*
`[docs/adr/0007…:443-444]`, resting on: *"the four completeness constraints … demand `card`, `md_hash`,
`doc_version_major` and `produced_at` — every one of which is derived from the Gemini output"*
`[:451-454]`. Three of the four are also gated on `kind <> 'summary'`.

**Evidence.**

- `gen_complete_has_produced_at` `[VERIFIED: schema/03_generations.sql:394]` ranges over all kinds.
  `gen_card_complete` `[:395-396]`, `gen_summary_has_format` `[:409-410]` and `gen_summary_has_hash`
  `[:411-412]` are each `state <> 'complete' or **kind <> 'summary'** or …`.
- **MEASURED (T1):** a `model`, `dig` or `digDeeper` row inserted with **only** `produced_at` — `state`
  defaulting to `'complete'` `[VERIFIED: schema/03_generations.sql:291]` — is **accepted for all
  three**, refused for none. **(T2)** the same shape for `summary` → `[23514] gen_card_complete`.
  **(T3)** `produced_at` is required for every kind — and `produced_at` is knowable before any Gemini
  call; `record_artifact` itself defaults it to `now()` `[VERIFIED: schema/04_artifacts.sql:473]`.
- The repo already does this: `05_assert.sql:138-139` inserts `gDIG`/`gMODEL` **complete** with `card`
  and `md_hash` NULL, and `verify-schema.sh` runs it green.
- The block-quoted *"both doors were locked"* measurement the ADR leans on `[:456-461]` cites
  `[VERIFIED: schema/03_generations.sql:271-283]`, whose second door is `gen_card_complete` — a
  summary-only constraint. It is quoted as if it ranged over every paid kind.

**Why it matters.** The ADR **deletes** the GC floor predicate `[:428-429]` on the strength of "forced".
For `summary` it is forced; for `model`, `dig` and `digDeeper` it is merely conventional — and `model`
is the kind with no job, no staging, and its own serve-path lease. An implementer who inserts an early
generation row for `model` reopens round 9's measured B1 window with no floor left to catch it and no
assertion that would go red. This is the "name what the rule ranges over" error the ADR records at
round 13 B1, round 14 H3, round 15 H3 and round 16 M1 `[:197-210]` — a fifth instance, in the paragraph
that *is* the load-bearing argument of round 16.

**Fix.** Restate it as an invariant with an owner rather than a schema consequence: *"no generation row
is created before its paid call completes. For `summary` the completeness constraints enforce this;
for `model`/`dig`/`digDeeper` **nothing does**, so the implementing slice must either extend the
constraints to those kinds or carry the invariant as an asserted rule."* Either is cheap; the current
sentence is the only thing that is not honest.

### H2 — "the orphan sweeper's existing mechanism" does not exist, and the claim is placed in the table of what ALREADY serves each concern.

**Claim.** The ADR says the orphan blob is covered by *"§8's grace period, which is the orphan
sweeper's existing mechanism"* `[docs/adr/0007…:27-28]`, *"the orphan sweeper's own mechanism, not a
new one"* `[:494-495]`, and writes it into the concern table as *"Orphan **blobs** in that window are
covered by §8's reinstated grace period"* with the evidence column reading `round 8 + round 16`
`[:101]`.

**What is TRUE (verified first, because half the ADR's premise here is sound).** §8's grace period does
survive in the spec text and IS reinstatable: *"**Grace period — mandatory.** A blob written but not
yet published is unreferenced and must never be collected… a minimum age (hours, not minutes) is the
standard defense"* `[VERIFIED: docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1995-1996]`,
plus consequence 2 `[:2101-2104]`. It was narrowed, not deleted, by rule 19's knock-on (a)
`[VERIFIED: …-design.md:891-893]` — exactly as the ADR says.

**What is FALSE.**

- **There is no orphan sweeper.** §8's own opening: *"There is no GC of superseded blobs anywhere…
  Without a manifest **nothing can tell you what is unreferenced**, so GC is currently impossible"*
  `[VERIFIED: …-design.md:1949-1953]`, and §8 closes by calling its remaining items *"the two OPEN
  items"* `[VERIFIED: …-design.md:2124-2130]`. `grep -rniE "orphan.?sweep|garbage.?collect|collectOrphan"`
  over `lib/ worker/ app/ scripts/ tests/` returns **zero hits**.
- **The age predicate is not expressible through the seam it would run on.** `BlobStore.list(p,
  prefix): Promise<string[]>` returns keys only `[VERIFIED: lib/storage/blob-store.ts:79]`, and the
  interface has no `stat`, mtime or metadata method at all `[VERIFIED: lib/storage/blob-store.ts:33-80]`.
  "An age predicate on the blob" `[docs/adr/0007…:400, :493-494]` needs a new seam method on all three
  adapters.
- Every other row of that table cites shipped code by `file:line`. This row cites two review rounds,
  because there is nothing to cite.

**Why High rather than Blocking.** The hazard and the mitigation are both unbuilt and land in the same
unwritten slice, so nothing is live-broken. But the ADR trades an **executable, in-schema,
mutation-scored** guard (`video_generations_collectable`'s predicate, deleted at `[:428-429]`; assertion
at `05_assert.sql:1428-1445`, mutation at `mutate-schema.py:410-413`) for **prose in a section the spec
itself marks OPEN** — and describes the trade using the word "existing". That is the ADR's own
diagnosis at `[:256-259]`: *"an instrument whose success line claims more than its input covers"*.

**Fix.** Say "§8's **specified but unimplemented** grace period", move the concern-table row's evidence
to `…-design.md:1995-1996` with an explicit *not implemented* marker, and record the seam gap
(`BlobStore` exposes no object age) as a **blocking precondition of the implementing slice**, beside
the `countTokens`/upload timeouts already named there `[:506-509]`.

### H3 — The round-16 re-record rule says "or raise", and nothing raises. MEASURED.

**Claim.** Round 16 H2 replaced "replace" with: *"**A re-record must present the SAME source set, or
raise.** An omitted `p_source_generation_id` carries the recorded set forward unchanged."*
`[docs/adr/0007…:607-608]`. The only enforcement the ADR names is *"That trigger branch moves onto
`video_artifact_sources`"* `[:622]`, referring to the provenance branch of the append-only trigger
`[VERIFIED: schema/04_artifacts.sql:969-973]`, which is installed `before update or delete`
`[VERIFIED: schema/04_artifacts.sql:995-997]`.

**Evidence.** A re-record naming a **different** source is an **INSERT** of a new
`(artifact_id, source_generation_id)` row. An INSERT fires no `before update or delete` trigger, so the
result is a silent **union** — neither the same set nor a raise.

**MEASURED (T6):** join table under a `before update or delete` trigger that raises unconditionally;
first record inserts `{gA}`, re-record inserts `{gB}` → *"INSERT ACCEPTED, no raise; source rows now:
2"*.

The schema already recorded exactly this rule twice: *"a constraint governs STATES, a trigger governs
TRANSITIONS, and an INSERT is a state with no transition"* `[VERIFIED: schema/04_artifacts.sql:1010-1012]`,
and the `art_detached_is_dig` note *"an INSERT written straight to state='detached' fires NO trigger"*
`[VERIFIED: schema/04_artifacts.sql:126-127]`. The round-16 fix asserts an invariant and assigns it to
the one mechanism shape that structurally cannot see the operation that violates it — "a guard that
never started", the signature this ADR names three times.

**Fix.** Name the enforcer and the site: either a comparison inside `record_artifact` (presented set vs
recorded set, raise on difference) or a **`before insert`** trigger on `video_artifact_sources`
rejecting an insert for an artifact that already has sources. One sentence; without it the rule is
unimplementable as specified.

### H4 — Deleting `pending` also falsifies rule 19's MONEY property, and the ADR names only the GC knock-on.

**Claim.** The ADR identifies one consequence of losing the record-first order: *"Delete `pending` and
that state returns. §8's grace period is REINSTATED"* `[docs/adr/0007…:487-495]` — knock-on (a). Rule
19's resolution bought **two other things**, both on the money path, and both are silently reversed.

**Evidence.** §5.1's rule-19 resolution reads: *"`record_artifact` inserts the row in state `pending`
**BEFORE** the bytes are written, then flips it to `recorded` after a verified write"*, yielding
*"**bytes ⊆ records** — … 'No record' *entails* 'no bytes'"* and *"**A crash before recording leaves
nothing — no bytes, no row, no orphan — so spending again is correct rather than a double-charge**"*
`[VERIFIED: …-design.md:864-887]`. It was adopted against a MEASURED defect: *"Slot absent, no key to
probe, serve path spends again, `g8` is minted, and `g7`'s paid bytes sit unreferenced. Measured cost…
**6¢ → 12¢** (`serve-model-unreadable.test.ts`)"* `[VERIFIED: …-design.md:860-863]`.

The ADR removes `pending`, so the row cannot precede the bytes — it says so itself: *"The bytes are
written before any row references them"* `[:487]`. Under generation-derived keys each attempt mints a
fresh id, so a crash after the blob write leaves paid bytes at a key **no later attempt can name**, and
the next attempt spends again. That is the same shape rule 19 was rewritten to remove, reintroduced by
this deletion — and the design spec's sentence *"a crash before recording leaves nothing"* is now
false and left standing.

**Honest bound, stated because the ADR should state it and does not.** The residual is bounded, not
unbounded: `max_serve_attempts` = 5 `[VERIFIED: 0012_serve_model_charge.sql:21]` for `model`,
`summary_max_attempts` = 1 for summaries `[VERIFIED: schema/04_artifacts.sql:263-270]`, and the concern
table already calls `model` spend *"bounded, not exclusion"* `[docs/adr/0007…:102]`. So this is a
**named residual**, not a hole — but a paid-call-sized one that the ADR's own falsifier list
(*"a paid kind whose spend is not bounded by a mechanism named in the concern table"* `[:677]`) exists
to surface.

**Fix.** Add the second and third knock-ons beside (a): state that `bytes ⊆ records` no longer holds
for the crash-after-bytes case, that §5.1's *"a crash before recording leaves nothing"* must be
corrected in the same slice, and name the bound that makes the residual acceptable.

---

## MEDIUM

### M1 — The deleted collectable predicate has a paired assertion and a paired mutation; the ADR retires neither.

The ADR removes `and g.state = 'complete'` from the view `[docs/adr/0007…:428-429]`. That predicate has
an executable assertion — *"not collectable while pending, and visible after"*
`[VERIFIED: 05_assert.sql:1428-1445]` — and a named mutation, *"B1: the collectable floor drops
`state = complete` (GC buries in-flight paid work)"* `[VERIFIED: mutate-schema.py:410-413]`, whose
anchor is the exact line being deleted. Left in place the mutation's anchor no longer matches and the
harness reports **INVALID**, which this project has already measured reads as *untested* rather than
*retired*. The ADR applied the right standard to the sibling case — *"(c) The four executable
assertions are REWRITTEN, not deleted — `05_assert.sql:166`, `:354-356`, `:360-362`, `:453`"*
`[:624-626]` — and did not apply it here. **Fix:** name both sites and their fate.

### M2 — `video_generations.state` becomes single-valued and its fate is unstated, while two load-bearing consumers read it.

The Consequences delete *"the `pending` **artifact** state"* `[:390]`. The round-16 argument then relies
on the **generation** `pending` state being unreachable `[:424-425]`, which is correct — but the ADR
never says whether `video_generations.state` and its `check (state in ('pending','complete'))`
`[VERIFIED: schema/03_generations.sql:291-292]` survive. Two consumers depend on the answer:
`video_artifacts_generation_complete` tests `v_state is distinct from 'complete'`
`[VERIFIED: schema/04_artifacts.sql:1023]` — and after B1's fix that guard is the **only** thing left
standing between a record and a missing generation — and the four completeness constraints are all
written `state <> 'complete' or …`. Drop the column and all five break; keep it and it is a
one-valued column whose meaning is now "always". **Fix:** one sentence saying which.

### M3 — The grace-period sizing enumerates three of the four paid kinds' pass constants, and mis-states why they are exported.

*"computed per kind from `SUMMARY_MAX_PASSES` / `TRANSCRIBE_MAX_PASSES` / `MAGAZINE_MAX_PASSES` — all
three already exported from `lib/gemini-cost.ts` for exactly this purpose"* `[docs/adr/0007…:504-506]`.
`dig` and `digDeeper` are paid kinds `[VERIFIED: schema/04_artifacts.sql:94-95]` with a cloud producer
`[VERIFIED: lib/job-queue/dig-handler.ts:100]`, and their constant is `DIG_GENERATE_MAX_PASSES`
`[VERIFIED: lib/gemini-cost.ts:51]` — omitted. A grace period shorter than a dig's worst case collects
paid dig bytes mid-call, which is the failure the reinstatement exists to prevent. Separately, the
file's own header says those constants are *"exported for the guard test"*
`[VERIFIED: lib/gemini-cost.ts:25]`, not for this purpose. This sentence is what replaced round 16's
dissolved "per-kind bound arithmetic", and it is an enumeration missing a member — the failure mode the
deleted text explicitly warned about. **Fix:** add `DIG_GENERATE_MAX_PASSES`; drop "for exactly this
purpose".

---

## LOW

### L1 — Front matter undercounts the rounds it answers.

*"revised: 2026-08-09. Rounds 13, 14, 15 — three DESIGN reviews, all answered here… See
docs/reviews/spec-blob-addressing-r1{3,4,5}-coordinator.md"* `[docs/adr/0007…:4, :14]`. The body answers
round 16 throughout (B1, H1, H2, M1, M2, M3, L1, L2 are all cited), and
`docs/reviews/spec-blob-addressing-r16-coordinator.md` exists in this same commit. **Fix:** `r1{3,4,5,6}`,
"four DESIGN reviews".

---

## What I could NOT break

Recorded so round 18 does not re-spend the effort.

- **The dissolution itself.** Nothing produces a `video_generations` row before or during a paid call
  once `reserve_artifact_slot` is deleted; `video_generations_collectable`
  `[VERIFIED: schema/04_artifacts.sql:878-900]` can only return rows that exist; round 9's B1 window is
  genuinely closed by subtraction. Withdrawing all three covers (per-kind table, `serve_model_charge`
  lease, `in_flight_until`) is correct. B1 and H1 attack the ADR's *account* of this, not the result.
- **"the only production INSERT".** Verified by grep across the whole repo: `04_artifacts.sql:308` is
  the only one; all others are fixtures in `05_assert.sql`. `video_generations` appears nowhere in
  `supabase/migrations/` or in any `.ts`, so "production" here correctly means "the spec's non-fixture
  writer".
- **The `model` serve path has the same ordering as `summary`.** `resolveMagazineModel` →
  `reserve_serve_model` `[VERIFIED: lib/html-doc/serve-doc.ts:74]` → `generateMagazineModel` `[:112]` →
  `writeModelEnvelope` `[:117]` → `settle_serve_model`. Blob first, and no `video_generations` write
  anywhere in the call graph. The dissolution holds for `model`; B1 applies to it identically.
- **Round 16 M1's restated bound is arithmetically right.** `least(5 + 1, 4) = 4` does revive an
  exhausted merged key; the clamp to `K - 1` leaves **exactly one** remaining attempt, so "at most one
  extra paid magazine call per merged key, once" is exact; and re-run idempotency holds because after
  the first pass each key has one row so `count(*) = 1` and the clamp does not fire `[:195-204]`.
- **§8's grace period text survives and is genuinely reinstatable** — see H2's "what is TRUE". The
  premise that it was dropped on a rule-19 assumption these deletions falsify is accurate
  `[VERIFIED: …-design.md:891-893]`.
- **The "four findings, one deletion" claim** `[:477-483]`. Round 16's H1 (bound computed for
  `MAGAZINE_MAX_PASSES` = 3 while `SUMMARY_MAX_PASSES` = 12 — verified at
  `lib/gemini-cost.ts:27, :29`), M2, M3 and L2 do all dissolve with the marker rather than needing
  fixes.
- **No residue.** `in_flight_until`, "covering mechanism", "per-kind successor" and "option C" appear
  only inside historical narration `[:8-11, :431-439, :466, :477, :504]`. No section still assumes a
  cover, a marker, or a vacated-but-replaced floor. The four reconciliation edits (front matter,
  the "nothing survives to coordinate writers" paragraph `[:24-28]`, the concern-table row `[:101]`,
  the ADDED/REINSTATED block `[:393-402]`) are mutually consistent with the body; their defects are
  H2's, not incoherence.
- **Citations spot-checked and sound:** `lib/job-queue/summary-handler.ts:173-179` (staged-write:
  `putStaged` → `exists` → persist → `promote`), `lib/html-doc/serve-doc.ts:112`/`:117`,
  `lib/html-doc/model-store.ts:51`, `lib/gemini-cost.ts:27, :29`, `schema/03_generations.sql:291`,
  `schema/04_artifacts.sql:85-86, :307-313, :556-565, :878-900, :969-973, :1013-1026`.
- **Not re-reviewed** (per brief): the freeze trigger, B3's `source_generation_id` coverage,
  `count(*) > 1` correctness, migration idempotency, round 15's reconciliation edits 1/3/4/5, new-tag
  citation integrity, the rounds 14/15 lists, and render addressing.

---

## Blocking reason

**B1.** As the ADR leaves the schema, nothing INSERTs the `video_generations` row, `record_artifact`'s
generation write is an UPDATE gated on two deleted things, and a paid record raises
`[P0001] … generation … is <absent>` — MEASURED. The ADR's central sentence ("the row is born complete,
at record time") names no writer. The dissolution survives; its mechanism must be written down.
