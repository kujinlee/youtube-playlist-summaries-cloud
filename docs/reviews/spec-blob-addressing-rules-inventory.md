# Rules inventory + cross-derivation pass — stable blob addressing

**Date:** 2026-08-06, before round 3.
**Why this exists:** the round-2 reviewer's meta-finding was that the fixes *"fail as a set — five were
written independently into different sections and none was re-derived against the others. Every
Blocking is an interaction between two fixes, not a defect in either one."* A review round is the
expensive way to discover that. This pass does it cheaply, first.

**And a second purpose (user, 2026-08-06):** *"There is no absolute rule. Almost all rules are
heuristics."* Two defects this session were caused by treating a chosen constraint as physical:
the corpus migration forced by *"the workspace id must never equal a uid"*, and the whole
publish-CAS protocol built to protect a pointer that did not need to be mutable. So every rule below
is classified by **what kind of thing it is**.

---

## Classification

- **P — Physical.** Imposed by Postgres, Supabase or the vendor. Cannot be negotiated, only worked with.
- **I — Invariant we chose.** Load-bearing, but *ours*. Changing it is a design decision with a cost,
  not an impossibility. **These are the ones that masquerade as physical.**
- **H — Heuristic.** A tuned value or a default. Expected to change; should never block a design.

| # | Rule | Kind | Notes |
|---|---|---|---|
| 1 | Storage RLS sees only `name`; policies cannot join on an artifact id | **P** | Forces the path segment to be the join key |
| 2 | A policy that raises fails the whole query, not one row | **P** | Why `text::uuid` on a segment is banned |
| 3 | An FK needs a unique constraint on the exact referenced tuple | **P** | Broke my 4-tuple FK (round-2 C2) |
| 4 | `add column … not null` fails on a populated table | **P** | Broke my one-line migration (round-2 C3) |
| 5 | `security definer` + `search_path = ''` requires schema-qualified names | **P** | Would have broken signup (round-2 Codex M2) |
| 6 | `where x = NULL` never matches | **P** | The "expect no row" trap, twice now |
| 7 | Supabase `get` cannot prove absence; local FS can | **P** | Root-cause shape #1 in one line |
| 8 | Slide assets cannot be recaptured on the host (no ffmpeg) | **P** | ADR-0005 |
| 9 | **The address must not contain mutable data** | **I** | The thesis. Everything else serves it |
| 10 | **No predicate may compare the path segment to `auth.uid()`** | **I** | ⟳ *Was stated as "the id must never equal a uid" — a P-shaped claim about a value. Restating it as an I about a predicate dissolved N-B4 and made §10 incremental.* |
| 11 | **Access is granted by membership, never by identity** | **I** | An identity grant cannot be revoked |
| 12 | **A generation is body + card, inseparably** | **I** | Q8 |
| 13 | **`current` is DERIVED, not written** | **I** | ⟳ *Round 2. Replaced "the manifest is mutable state protected by a CAS." Dissolved N-H4, M4, most of N-B3.* |
| 14 | **Eligibility is computed from recorded facts only — never a live blob read** | **I** | ⟳ *Cross-derivation. The first draft of rule 13 said "whose body is readable" and reintroduced shape #1.* |
| 15 | **Assets are sources, not artifacts** | **I** | ⟳ *Round 2. Replaced "everything in the bucket is an artifact the manifest tracks." Dissolved N-B1 and N-H9.* |
| 16 | **Unreferencing is transactional; byte deletion is best-effort** | **I** | Fails toward *collectable*, never toward *pinned* |
| 17 | **Paid/free must be derivable from the key alone** | **I** | An orphan has no row to consult |
| 18 | **An explicit delete outranks retention** | **I** | Correctness, not policy |
| 19 | **Both reads before a spend** — slot absent *and* blob provably absent | **I** | The 6¢→12¢ shape |
| 20 | Attach only when unambiguous in **both** directions | **I** | §6.1 |
| 21 | Overlap threshold **0.8** | **H** | Tunable upward only |
| 22 | Paid retention **90 days** | **H** | A duration, not a generation count |
| 23 | GC grace period "hours, not minutes" | **H** | Standard mark-and-sweep defence |
| 24 | One workspace per user *in this slice* | **H** | Explicitly a scope choice (§5.0) |

**The pattern worth keeping: every defect that cost a round came from an I misfiled as a P.** Rules 10,
13 and 15 each looked like facts about the world and were choices. Questioning each one dissolved a
cluster of findings instead of patching them individually. Rules 21–24 are openly heuristic and have
never caused a problem — visible tuning knobs are safe; invisible ones are not.

---

## Cross-derivation — every rule checked against every other

Five conflicts found, **all between rules written within hours of each other**, none of which a
single-section read would surface.

### X1 — Rule 13 vs Rule 7 (**a new defect, self-inflicted**)

The first draft of rule 13 read *"the newest generation whose card is complete **and whose body is
readable**."* A readability check at *resolve* time is a blob read per candidate, and by rule 7 the
Supabase adapter cannot prove absence. A transient 5xx would make the newest generation ineligible and
**silently demote the video to an older body**, reporting nothing — the exact failure `SlotRead` exists
to prevent, arriving through the fix that removed a different one.

**Resolved:** rule 14. Eligibility uses recorded facts only; readability is verified once by the writer
that wrote the bytes. Resolving a slot now touches no blob.

### X2 — Rule 15 vs §2's slot list and the `artifact_kind` enum

Assets became *sources* (outside the manifest), but §2 still listed `slide:<id>` as a slot and the enum
I had written an hour earlier still carried `'asset'` with a `slot_kind` mapping. **Resolved:** slot
removed, enum member removed, mapping removed.

### X3 — Rule 13 vs the corrections-CAS stack

Two review rounds produced a publish CAS, a "stored unpublished" state, a requeue protocol and a
`pending_publication` table — all to make one mutable pointer safe. Rule 13 removed the pointer.
**Resolved:** the corrections rule becomes an eligibility condition; the reasoning is kept so a reader
does not re-propose the CAS.

### X4 — `record_artifact(p_span int4range)` vs `start_sec int, end_sec int`

The RPC I specified took a range; the table I specified takes two integers. **Resolved:** two integers,
matching the columns.

### X5 — §5.2.1 "video judgments live on the video" vs §5.0.1

"The video" became ambiguous the moment `workspace_videos` split the per-playlist row from the
per-workspace entity — and under dedup, "on the video" would give one body two scores. **Resolved:**
judgments live on `workspace_videos`.

---

## What this pass does not cover

It checks rules against **rules**. It does not re-check rules against **code** — that is what round 3
is for, and it is where round 1 and round 2 both found the most. The claim here is narrower: the set is
now internally consistent, so round 3 can spend its budget on the spec-versus-reality gap rather than
on the spec versus itself.
