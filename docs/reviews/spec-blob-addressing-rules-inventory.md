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


---

# Invariant evaluation — are the 12 chosen rules still reasonable?

**Asked 2026-08-06 (user):** *"I don't want to move rules lightly, as current code is based on them —
but if some invariants become too restrictive, we need to re-evaluate their value."* Exactly the right
framing: the question is not *is this rule true* but **is what it buys still worth what it forbids.**

Verdict: **8 sound, 3 need refinement, 1 relaxation candidate.** None should be dropped.

## Sound — keep as written

| # | What it buys | What it forbids | Verdict |
|---|---|---|---|
| 9 | The whole thesis | any address component that changes in normal operation | **Keep.** Note it is already *precisely* scoped, not absolute: §4 admits the workspace segment is mutable in principle (ownership transfer) and accepts it because rule 10 means no one reads it |
| 10 | Revocability | the cheap pure predicate | **Keep.** Cost measured at 0.118 ms. Worth naming what is lost: a predicate with no table dependency cannot be broken by a bad row; this one can |
| 13 | No CAS, no race, no limbo | pinning an old generation as current | **Keep** — pinning is re-addable as one nullable column, and as a *human gesture* rather than a race |
| 14 | Resolving touches no blob | detecting a vanished body at resolve time | **Keep.** A missing body now surfaces as a loud 404 at serve time instead of a silent demotion. Louder is better |
| 16 | Failure lands on *collectable*, never *pinned* | — | **Keep** |
| 17 | Orphans are classifiable with no row to consult | future key shapes that hide their own kind | **Keep**, and note rule 15 **widens** it: the key must now reveal *paid/free* **and** *artifact/source* |
| 18 | "Delete" means delete | — | **Keep.** Correctness, not policy |
| 19 | The 6¢→12¢ defect | — | **Keep.** Scope narrowed usefully by rule 14: the blob read now happens only on the **spend** path, never on resolve |

## Needs refinement — the rule is right, the wording is wrong

### Rule 11 — "access by membership, never identity" has an undocumented third mode

**Share tokens are neither.** `lib/share/serve.ts:19-24` reads `revoked_at` off `share_tokens` through
`serviceClient`, bypassing RLS entirely. That is a **capability**: a bearer grant, revocable by setting
a column. It satisfies the rule's *spirit* — revocability — while violating its letter, and it is in
production today.

**Refine to:** *access is granted by membership **or by an explicit revocable capability**, never by
identity.* The load-bearing property was always **revocability**, not membership specifically. Stating
it as "membership" makes the existing share path look like a violation, which invites someone to
"fix" a design that is already correct.

### Rule 12 — a generation is not necessarily paid

§2 defines it as *"one production run of a **paid** artifact."* Backlog #23 makes corrections a
deterministic `{from,to}` replacement — which produces **new bytes with no Gemini call**. Under rule 12
that is a new generation, and a free one. The same is true of a re-render at a bumped format version.

**Refine to:** *one production run that yields a new body*, with **paid** an attribute of the run, not
part of the definition. This matters beyond wording: §8's retention keys on paid-vs-free, so a
definition that implies every generation is paid would retain free re-renders for 90 days.

### Rule 15 — sound, but it has an unstated accumulation cost

Assets are sources, so the age sweeper never collects them. A user who digs a hundred sections and
abandons them keeps those frames until they delete the video. **Accepted, but say so:** this is the one
place the design knowingly trades storage for safety, and it is the right trade only because the bytes
are unrecreatable (ADR-0005). If assets ever become recreatable, revisit this rule first.

## Relaxation candidate — worth a decision, not a default

### Rule 20 — "attach only when unambiguous in both directions" assumes attachment is binary

The justification is §6's: *"a wrong attachment silently mislabels paid content … **the user cannot
tell it is wrong**."* The whole argument rests on the *silently*. Codex then showed an ordinary
section split leaves a paid dig stranded, and §6.2's `detached` state keeps it alive but invisible.

> **⟳ ROUND 6 — the user decision of 2026-08-06 STRENGTHENS this candidate rather than settling it.**
> §6.2's "a detached dig is never deleted" was retired: a detached dig now runs §8's ordinary 90-day
> clock from `detached_at`. So the cost of leaving a dig unattached is no longer "alive but invisible",
> it is **invisible, then collected** — the stranded dig is destroyed on a timer the user never sees.
> That removes the fallback this rule was quietly leaning on. Re-read the trade with that in mind:
> "attached with provenance" now competes against *losing* the content, not merely hiding it.

**The unexamined assumption is that a dig is either attached or not.** A third state —
**attached with provenance** (*"this detail was written for an earlier version of this section"*) —
removes the word the objection depends on. The user *can* tell, so mislabelling is no longer the risk;
what remains is a judgment about clutter, which is a product question rather than a correctness one.

**Not changing it unilaterally** — it reverses a decision made deliberately today ("leave unattached,
don't guess"), and that decision is defensible. Flagging it because the rule's *stated reason* no
longer fully applies once a UI can carry provenance.


---

# Round-3 amendments to the inventory

**Rule 19 restated — determinacy, not absence.** *"A spend requires a determinate negative from every
layer that could hold the artifact; an indeterminate answer from any layer is `busy`."* The old form
("slot absent AND blob provably absent") was **vacuous**: the slot is absent exactly when no record
exists, and with no record there is no key to probe. Resolved by the record-first write order, which
makes *bytes ⊆ records* hold by construction, so "no record" *entails* "no bytes" without a probe.

> **⟳ ROUND 4 (J2-2) — "by construction" is true only over the keys this design addresses.** Two
> classes sit outside the containment: the **pre-migration corpus** (temporarily, until §10 records
> it — the set starts 100% exempt) and **`_staging/<uuid>/<key>`**, the atomic-write temp prefix of
> all three blob stores (permanently, by construction — a staged byte exists precisely so that it is
> not yet the artifact). The money guard is unaffected, because it needs the containment only at the
> fresh `<ws>/videos/<v>/<gen>/…` key it is about to spend on, and neither exception can be that key.
> **§8's sweeper is the consumer that cannot take the unqualified sentence** — under it, an unrecorded
> blob reads as garbage, which would collect a live staging blob mid-promote and the entire
> pre-migration corpus on the first run.
>
> **⟳ ROUND 5 (B4/H4) — and record-first was still not sufficient, for a different reason.** *bytes ⊆
> records* makes "no record ⇒ no bytes" true; it does **not** make "a record ⇒ only one writer" true.
> Two writers minting different generation ids both inserted `pending` and both paid Gemini
> (MEASURED, `count(*) = 2`) — the guard's `busy` branch was never reached. Record-first inherited its
> mutual exclusion from a primary key that round 4 removed for unrelated and correct reasons. Now
> enforced by `video_artifacts_inflight_uq`, landed together with a reclaim, because the index alone
> converts a dead lease from a soft `busy` into a permanently dead slot.

**Rule 14 gains a floor — staleness RANKS, it never GATES.** Eligibility-to-be-**served** is
`state = 'recorded'`; it cannot empty a non-empty set. Corrections-currency and format move
into the *ordering* for eligibility-to-be-**current**. Without this, a free user gesture (typing a
correction) made every generation stale at once and deleted the visible summary.

> **⟳ ROUND 5 (H3) — "full stop" was wrong, and the correction is subtle enough to be worth stating
> precisely.** The floor is `state = 'recorded'` **and** `not body_collected`, and the second conjunct
> is not staleness — it is **byte existence**. A collected body has no bytes, so serving it would be
> root-cause shape #4, and gating on it is therefore legitimate under rule 14 rather than an exception
> to it. **The honest statement of rule 14 is: no rule that is not about byte existence may gate.**
>
> That was still not enough on its own. MEASURED: the summary slot went **2 rows → 0** when GC
> collected both generations — round 3's A-2 failure ("the summary vanishes from the page") reached
> through GC instead of through corrections. §8 stated no rule protecting the current generation. It
> is now enforced by `forbid_collecting_current()` rather than written as a sentence the sweeper must
> remember, because "the sweeper must remember" is exactly the rule that holds until the day it does
> not, on the one path with no undo.
>
> **Still open (C5):** a free render has no generation, so the `body_collected` filter exempts it
> structurally — the PDF of a collected body keeps serving. The §8 rule must also be *"collecting a
> body collects the renders derived from it."*

**Rule 13's ordering is the project's existing hierarchy, not flat recency** — matching
`reconcile-class-a.ts:41-50` and the Stage 3 principle *"reconciled by format, not recency."* Every
rung is a replica-independent recorded fact, which is what makes `current` a deterministic function of
the generation set — and therefore what makes sync convergent without a tiebreak protocol.

> **⟳ ROUNDS 4–5 — the tuple has changed twice since this was written, and both changes were forced
> by a measurement rather than an argument.** It is now, in `schema/04_artifacts.sql`:
>
> `(source_current, corrections_current, doc_version_major, card→mdGeneratedAt, produced_at, generation_id)`
>
> - `created_at` is **gone** (round 4 J2-3): it defaulted to `now()`, so it was clock-derived, and a
>   clock read is not a replica-independent recorded fact. The claim in this very paragraph was false
>   while `created_at` was in the tuple.
> - `source_current` was **added** (round 4 J2-4) as the top rung — and required a second view,
>   because the summary's own ranking is an input to the ranking of everything derived from it.
> - the recency rung is the **card's `mdGeneratedAt`**, not `produced_at` (round 5 B3). MEASURED: the
>   two ranked opposite winners on the same pair, which is precisely the oscillation this paragraph
>   claims is impossible. `produced_at` survives as a lower rung.
>
> **The paragraph's conclusion is now true. It was not true when it was written**, and it took two
> rounds and two measurements to make the words match the schema — which is the case for keeping this
> inventory current rather than treating it as a record of what was once decided.

**Rule 15 is WITHDRAWN.** Assets are not a cloud concern at all: nothing writes them to the bucket and
sync does not copy them. Every asset finding across three rounds is withdrawn rather than fixed. Its
invalidation condition lives in the ADR-0005 amendment (2026-08-06).

**Rules 12 and 13 are CLOUD invariants, not system-wide ones.** They are Postgres schema properties and
the local backend is a filesystem with no manifest, no generations and no sweeper. Four round-3
findings shared this root.

## New entry — how a PHYSICAL rule fails

**Rule 4** (`add column … not null` aborts on a populated table) was in this inventory, classified
correctly as physical, and **still recurred twice after being fixed once** — `playlists` in round 2,
then `workspace_videos` and `jobs` in round 3.

> **A physical rule applies to every SITE, not to the site where you learned it.** Classification is
> not enough; a P rule needs a **sweep** across every place its shape could occur. The I/H rules did not
> behave this way, because an invariant is stated once and read once, while a physical constraint is
> re-encountered every time you write DDL.

This is the inventory's own blind spot, found by the round it was written to make cheaper.
