# Round 17 — Claude adversarial review of the cloud blob key encoding spec (backlog #36, v19)

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` as it stands in the
working tree of `fix/cloud-blob-key-encoding` (v19, 1771 lines). Phase 1 — no code written.

**Verdict: NOT CONVERGED. The armed falsifier FIRED.**

| Severity | Count |
|---|---|
| Blocking | 1 |
| High | 0 |
| Medium | 2 |
| Low | 4 |

Classification split: `mechanism` **0** · `branch-coverage` **2** · `stale cross-reference` **4** ·
unclassifiable-by-the-taxonomy **1** (an unstated implementation cost). Caused by v19's own fixes: **4
of 7** (B1, M1, M2, L1).

---

## ⛔ THE FALSIFIER FIRED — and this is the third instance, one table row from the second

> Round 16 armed: *fires to REDESIGN if round 17 produces another finding of the form "a placement is
> stated for ONE BRANCH/DIRECTION of the path it sits on".*

**B1 below is that finding.** §3.5.1b row 3 states placement 3 (`reconcileCloudBase`) has **One**
branch. The guard's own subject — `newBase` — has **two producers**, `reconcile-serial.ts:152-154`,
and the design is written for one of them. On the other, the refusal (a) protects nothing, (b) blocks
the last recovery route for a paid artifact, and (c) emits the "rename your vault file" repair for a
vault file that **does not exist** — which is, verbatim, the mirror-image diagnosis round-16 B1 made
about `copyAdditiveVideo`.

The escalation is owed. I record the specific reason it is owed rather than the count alone:

**§3.5.1b asks the wrong question in its "Branches" column.** For six of seven rows it answers a
question about *direction* — *which side is the receiver?* Round-16 B1 and 26c3 were both direction
defects, so answering the direction question felt total. It is not the general question. The general
question is *"what are the branches of the value this guard tests?"* — and for row 3 the direction is
genuinely hard-wired (`cloud: cloudSide` at `sync-run.ts:731`, verified) while the **name being
tested** is not. The table's own closing rule — *"a placement is not specified until you have named
which branch of its path it applies to"* — was applied to the receiver and not to the operand.

That is a redesign-shaped observation, not a fourth repair: the prophylactic §3.5.1b was written
specifically to pre-empt a third instance, it enumerated all seven placements, and a third instance
survived it. Whatever replaces the table has to enumerate branches of the **guarded value**, not
branches of the **call site**.

---

## B1 — Blocking — `reconcileCloudBase`'s `unservable-base` refusal is specified for one of `newBase`'s two producers; on the other it strands the paid artifact it exists to protect

**Classification:** `branch-coverage` · **caused by v19's own fix** (and by round 16's, see the LEAD
note at the end of this finding).

### The two producers

```ts
// lib/cloud-sync/reconcile-serial.ts:150-155   describeDivergence
if (localVideo.serialNumber == null || !cloudVideo.summaryMd) return { diverged: false };
const from = baseOf(cloudVideo.summaryMd);
const to = localVideo.summaryMd
  ? baseOf(localVideo.summaryMd)                                        // ← arm A: the vault filename
  : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber)); // ← arm B: the CLOUD key, renumbered
return from === to ? { diverged: false } : { diverged: true, from, to };
```

`reconcileCloudBase` then takes `const newBase = d.to!` (`:186`), and the guard §3.5.1 placement 2
prescribes sits "in memory, before the copy phase, alongside its existing `target-occupied` /
`unsupported-artifacts` refusals (`:197`, `:214`)" — i.e. downstream of `:186`, so it tests `newBase`
whichever arm produced it.

The spec states the credential for arm A only, three times:

- §3.5.1: *"`newBase` is the **vault filename, verbatim** (`:152-154`)"* (spec:662)
- §3.5.1 placement 2 / behavior 26d: the message must say *"the offending name is a **local vault
  filename** while the error is reported against a **cloud** video"* and *"the file must be renamed"*
  (spec:766, :781-782, :1660)
- §3.5.1b row 3: **"One."** (spec:892)

`applySerial` (`lib/serial-filename.ts:20-24`) strips any existing `NNN_` prefix from the **cloud**
basename and applies **local's** serial. On arm B the offending characters are the cloud slug's; there
is no vault file anywhere in the derivation.

### Reachability — established by the spec's own text, not by me

Arm B requires `localVideo.serialNumber != null && localVideo.summaryMd == null`. The spec already
asserts this state exists, in §3.6.2's round-11 L3 note: *"**`summaryMd` is optional.** The
additive-hydration path reaches `copyToLocal` with a loser that has none (`sync-run.ts:701-708`)."*

Two independent production sources, verified:

1. `lib/pipeline.ts:235` — `claimVideoSlot` reserves the serial **before** `writeSummaryDoc`, and
   `LocalMetadataStore.claimVideoSlot` inserts `{ id, serialNumber } as Video`
   (`lib/storage/local/local-metadata-store.ts:51`). Any interruption before the `upsertVideo` at the
   end of the loop leaves exactly this row. The serial is allocated by local's own `nextSerial`, so it
   has no reason to match the serial embedded in the cloud key.
2. `ensureReceiverSlot` on a **local** receiver (`sync-run.ts:240` → `:214`). `sync-run.ts:230-235`
   documents this bare-row outcome at length as a state the codebase has actually observed.

And the cloud row must carry an unservable `summaryMd`. That is §3.5's own reachability table
(spec:569): `recoverOrphanedVideos` adopts a hand-placed or externally-renamed `*.md` verbatim
(`pipeline.ts:104`, `:137`), sync copies it to cloud and advertises `promoted`. v19 closes that for
**new** rows; §4 explicitly performs **no migration**, so existing ones persist. Take the spec's own
example key, `notes..part2.md`: name `notes..part2` contains `..` → `isServableSummaryKey` rejects it.

### The failure

```
cloud row:  summaryMd = "notes..part2.md"   (unservable today; serve/download/PDF/dig all 409)
local row:  serialNumber = 5, summaryMd = null
```

`describeDivergence` → `from = "notes..part2"`, `to = "005_notes..part2"` → diverged.
`reconcileCloudBase` reaches the new guard, `isServableSummaryKey("005_notes..part2.md")` is false,
and it returns `{ ok:false, reason:'unservable-base', key }`.

`sync-run.ts:739-757` turns that into a `throw`, caught per-video at `:812`, **no baseline**. And
`reconcileClassA` is at `:771` — *after* the throw. So:

```
:729  reconcileCloudBase  → refuse → :756 throw      ← the new guard fires here
:771  reconcileClassA     → NEVER REACHED
:791  copyToLocal / transferClassA → NEVER REACHED
```

`reconcileClassA` with `!lHas && cHas` returns `copyToLocal` (`reconcile-class-a.ts:23`), and
`transferClassA` would write the cloud body into the vault with `loser.blob.put` — **unguarded, by
design**, per §3.4 and decision ①. That hydration is the paid summary's only remaining route to the
user, and every run now throws before it. Permanently: no baseline advances, and the state is
self-reproducing.

**This is round-16 B1's harm, arriving through a different door.** B1 was graded Blocking for exactly
this: *"a paid summary unreachable through every product path, with no in-product repair — a re-serve
cannot run, because the serve path refuses before it reserves."* Every clause holds here.

**And the refusal buys nothing on this arm.** The stated justification for placement 2 is that the
relocation *"copies every paid blob to the unservable base, writes the row, verifies, and **deletes
the sources**"* — i.e. it turns a **servable** artifact into an unreachable one. On arm B the old base
was *already* unservable; the relocation only renumbers it. Nothing servable is endangered, and the
refusal's whole cost is the blocked hydration.

**Third, the repair message is wrong in the way B1 named.** Behavior 26d requires the message to name
the manual repair. On arm B it will say the cloud video is blocked by a local vault filename that must
be renamed. There is no such file. §3.5.1's own diagnosis of B1 — *"'rename' is not an operation the
user has"* — applies unchanged.

### Fix

Two parts, both small:

1. **Scope the refusal to the case it was designed for: refuse only when the relocation would destroy
   a working advertisement.** Guard on the *old* base as well as the new:

   ```
   if (isServableSummaryKey(`${oldBase}.md`) && !isServableSummaryKey(`${newBase}.md`))
       return { ok: false, reason: 'unservable-base', key: `${newBase}.md`, … };
   ```

   When the old base is already unservable, relocate as today — nothing servable is at risk, and the
   Class-A hydration downstream stays reachable. (Note this *keeps* the refusal on arm B in the one
   case that matters: a servable cloud key whose renumbering pushes it past 131 code points, which
   `applySerial` can do by widening the prefix or adding one where the key had none.)

2. **Make the message name the right subject per arm.** Carry the producer in the variant
   (`origin: 'vault-filename' | 'cloud-key'`, or simply `localVideo.summaryMd != null`) and have
   `sync-run.ts`'s explicit `unservable-base` branch say either *"rename `<vault file>`"* or *"the
   cloud key `<key>` cannot be relocated; it is unservable and has no local counterpart to rename."*
   Behavior 26d must gain a second row asserting the arm-B message, or the mutation
   *"return `metadata-failed` instead of `unservable-base`"* stays green against half the branch set.

3. **§3.5.1b row 3's "Branches" cell must read TWO**, and the table's rule must be restated against
   the *guarded value*, not the receiver.

> **LEAD, labelled as one — where this was introduced.** `docs/reviews/spec-blob-key-encoding-r16-claude.md`
> contains the sentence *"`newBase` is derived from `localVideo.summaryMd`, `reconcile-serial.ts:152-154`,
> so it is the local vault name"*, quoting only the first arm of a ternary it cites by line range. v19
> encoded that reading into placement 2, behavior 26d and §3.5.1b row 3. Round-14 Claude quoted the same
> three lines with the same one-arm gloss (*"`newBase` is **the vault filename, verbatim**"*). Two
> reviewers and the coordinator read past the `:` of a ternary they had pasted in full. I have not
> re-read every round, so treat the attribution as a lead; the code claim is verified.

---

## M1 — Medium — behavior 26f cannot observe the state it asserts, and its mutation stays green

**Classification:** `branch-coverage` · **caused by v19's own fix.**

```
| 26f | The adopt guard is in the CALLER (`sync-run.ts:624-627`), not inside `copyAdditiveVideo`
       — asserted by the refusal happening with no `ensureReceiverSlot` call at all …   (spec:1654)
```

```
| Move the adopt guard back INSIDE `copyAdditiveVideo` (sniffing the store type …) | 26f |  (spec:1714)
```

`ensureReceiverSlot` is a module-private `async function` at `sync-run.ts:164`; the file's only export
is `runSync` (`:547`). It is not spyable. Its sole externally visible effect is
`to.claimVideoSlot(...)` at `:214`, on the injected `MetadataStore` — which a test *can* observe.

**But the mutant produces the same observation.** The placement the mutation restores is
`sync-run.ts:236-238`, which is **above** `ensureReceiverSlot` (`:240`) — that is the whole point of
round-13 H2. A guard there also refuses before `claimVideoSlot`. So:

| Placement | `claimVideoSlot` called? | 26f as written |
|---|---|---|
| caller, `:624-627` (v19) | no | passes |
| inside, `:236-238` (the mutant) | **no** | **passes** |

26f is the vacuous-falsifier shape §5's own round-9 M2 note describes — *"not 'the mutation survives'
but 'the input is unconstructible'"*, here *'the observable does not discriminate'*. This document has
now shipped three of these (round-9 M2's `utf16le` row, the `\p{Bidi_Control}` row already marked
UNMUTATABLE, and this).

**Fix — and it forces a decision the spec currently leaves open.** The one thing the two placements
*do* differ on is the sender-side MD read: `const body = await readMdBody(from.blob, from.p, present)`
at `sync-run.ts:626` runs before `copyAdditiveVideo` is entered. So:

- pin the placement to **before `:626`** (the spec says only *"at `sync-run.ts:624-627`"*, which
  admits a position after the read), and
- reword 26f to assert **no `get` on the sender's blob store for the summary key**, which the mutant
  cannot satisfy.

If the guard is instead intended to sit after `:626`, then there is no observable difference between
the two placements at all and 26f should be deleted rather than made to look like a falsifier.

---

## M2 — Medium — three surviving references put the adopt guard at the location v19 itself calls unimplementable

**Classification:** `stale cross-reference` · **caused by v19's own fix.**

v19 moved the adopt guard from `sync-run.ts:236-238` to the caller. Three statements still say the old
place, and none of them is inside the box that corrects it:

| Line | Text |
|---|---|
| 596 | *"The adopt refusal (`sync-run.ts:236-238`, **above `ensureReceiverSlot`** — round-15 L1: this bullet still said `:263`…)"* |
| 786 | §3.5.1 placement 3 headline: *"**The adopt path keeps its call site above `ensureReceiverSlot`** (`sync-run.ts:236-238`)"* |
| 921 | §3.5.2 table, "Where the refusal lands": *"**the adopt guard**, above `ensureReceiverSlot` (`sync-run.ts:236-238`)"* |

Against spec:845, in the same section: *"'Apply the guard only when the receiver is the cloud' **is not
implementable at `sync-run.ts:236-238` as the function stands**, and a fix that cannot be written is
not a fix."*

**Why Medium rather than Low.** §3.5.2 is *the* per-caller state table — the artifact an implementer
consults for "where does this refusal land". Following it puts the guard inside `copyAdditiveVideo`,
where the side is unknowable, which is round-16 B1 reproduced exactly. And line 596 is the *third*
version of the same sentence to be stale: round-13 H2 corrected `:263`, round-15 L1 corrected it again,
v19 moved it a third time and missed it. **The bullet is not the defect; the fact that a location is
restated in four places is.** State it once, in §3.5.1b, and have the other three point at the row.

---

## L1 — Low — §3.5.2 row 4 still describes the caller behaviour v19 deleted

**Classification:** `stale cross-reference` · **caused by v19's own fix.**

spec:924 — *"Returns a refusal variant → **generic throw** at `sync-run.ts:735-757` → `:812` → no
baseline → re-fires. ✅ clean"* — against spec:780-783, which resolves round-16 M1 by giving
`sync-run.ts` **an explicit `unservable-base` branch** and deleting the "no change to the caller"
claim. The word *generic* is the residue of the deleted design. Same sweep as M2.

## L2 — Low — the implementation cost of `ModelEnvelopeWriteSchema` is not stated, though the precedent for stating it is in this document

**Classification:** not cleanly one of the three; an omitted consequence of a stated rule.

Row 7 of §3.5.1b is verified correct (see "What held" below), but making `videoId` required on
`serialize`'s parameter type breaks every call site that builds an envelope literal. Enumerated over
the repo (`writeModelEnvelope` / `writeModelEnvelopeWithin`, production **and** test):

| Location | Call sites | Distinct envelope literals/fixtures to edit |
|---|---|---|
| `lib/html-doc/generate.ts:50`, `serve-doc.ts:174`, `cloud-sync/sync-run.ts:464` | 3 | 3 (production; all three have the id in scope — verified) |
| `tests/lib/html-doc/rerender.test.ts` | 14 | 2 (`envelope()` helper + the literal at `:210`) |
| `tests/lib/html-doc/model-store.test.ts` | 8 | 1 (`ENVELOPE`) |
| `tests/lib/model-store-cloud.test.ts` | 3 | 1 |
| `tests/integration/serve-doc-materialize.test.ts` | 5 | 5 |
| `tests/integration/share-route.test.ts` | 4 | 4 |
| `tests/integration/html-download.test.ts` | 2 | 2 |
| `tests/integration/pdf-cloud.test.ts` | 1 | 1 |
| `tests/e2e/cloud.setup.ts` | 1 | 1 |
| **total** | **41** | **~20** |

The spec states exactly this class of cost for the other seam change — round-12 Low, *"the rollout is
wider than three adapters"*, naming `FailPromoteBlobStore`, `UnreadableModelBlobStore` and the object
literal at `consistency.test.ts:38-59`. The `serialize` change has no equivalent paragraph. Not a
defect in the mechanism; a predictable implementation interruption that the plan should carry.

Two facts worth stating alongside it, both verified and both **in the design's favour**:
`companionTransfer` has `winnerVideo.id` in scope (`sync-run.ts:445`), so 18j6's "stamp the receiver's
`videoId`" compiles; and because `decideCompanion` returns a *read* `ModelEnvelope`, `tsc` will
**force** the stamp at `sync-run.ts:464` rather than merely inviting it.

## L3 — Low — "THREE placements stay outside the seam" is four

**Classification:** `stale cross-reference` (a count).

spec:747 says three, and lists mint / `reconcileCloudBase` / adopt. §3.5.1b row 6 lists a fourth
placement of the same predicate outside the seam — the share guard inside `getShareServeContext`
(`lib/share/serve.ts:13`) — and behavior 21 asserts it. Round-15 H2 was the identical defect one round
earlier (*"v17 said two"*). Nothing is missing from the design; only the number is wrong. Say "the
placements §3.5.1b enumerates" and stop counting.

## L4 — Low — half of the 18j7 mutation row has no observable

**Classification:** `branch-coverage`.

spec:1700 — *"Strip unknown fields in the relocation copy **(or in `rewriteEnvelopeSourceMd`'s JSON
round-trip)`** | **18j7**"*. Behavior 18j7 is scoped to *"After a **cloud base relocation** the copied
envelope still carries the SAME `videoId`"* — `reconcile-serial.ts:282`. `rewriteEnvelopeSourceMd`
(`lib/serial-provenance.ts:13-17`, written at `lib/serial-migrate-exec.ts:141`) is the **local** serial
migration; nothing in §5 observes it. Mutating that half leaves 18j7 green. Either give the local
round-trip its own behavior or drop it from the row.

## L5 — Low — a fourth `MetadataStore` caller writes `summaryMd`, and §3.5.1's enumeration does not mention it

**Classification:** `stale cross-reference` (an incomplete enumeration under a completeness caption).

§3.5.1's table is captioned *"Every sync-side entrance writes the advertisement through a
`MetadataStore` method — **verified by enumeration, not asserted**"*, and its companion note lists what
is *"outside the seam, and correctly so"*. Neither mentions:

```ts
// lib/serial-migrate-exec.ts:130,146
if (op.field !== 'model') fieldUpdates[op.field] = op.to;   // op.field can be 'summaryMd' (:131)
…
if (Object.keys(fieldUpdates).length > 0) await store.updateVideoFields(principal, plan.id, fieldUpdates);
```

Harmless today and it does not touch the mechanism: `runPhaseB` resolves its store with
`getStorageBundle()` and no client, which throws under `STORAGE_BACKEND=supabase`
(`lib/storage/resolve.ts:56`) — the same structural argument §3.5.1 already makes for
`bulkUpdateVideoFields`. Worth one row precisely *because* the seam design makes the count irrelevant:
the table should either be complete or stop saying "verified by enumeration".

---

## What HELD under independent verification

Recorded because a clean result is a result. Every line reference below was opened and read.

**§3.5.1b, row by row:**

| Row | Verdict |
|---|---|
| 1 — metadata seam | **HOLDS.** `stripComputed` is defined once (`supabase-metadata-store.ts:19`) and is the sole payload constructor for all three data-writing methods — `:119`, `:143`, `:160`, exactly as quoted. `updateVideoAnnotations` (`:269`) writes `videos.data` through a **SQL-side allowlist** that excludes `summaryMd`, so it is not a fourth hole. The adapter is only ever the cloud store: `scripts/cloud-sync.ts:65-70` wires `local: localMetadataStore` / `cloud: new SupabaseMetadataStore`, and `getStorageBundle` returns it only under `STORAGE_BACKEND=supabase`, where there is no vault. One branch ✅ |
| 2 — the mint | **HOLDS.** `reserveVideoSlot` at `summary-handler.ts:95`, `baseName` at `:96`, `summaryCore` (the Gemini call) at `:101` — all three exact. `getWorkerStorageBundle` hard-returns `new SupabaseBlobStore(...)` with no backend branch (`resolve.ts:81-86`). One branch ✅ |
| 3 — `reconcileCloudBase` | **FAILS — see B1.** The *direction* claim is correct (`cloud: cloudSide` hard-wired at `sync-run.ts:731`; one production caller, `:730`; `reconcile-serial.ts` mutates only the cloud replica). The *branch* claim is not: `newBase` has two producers |
| 4 — the adopt | **HOLDS as a branch claim.** `presentIsLocal` at `:620`, `to` at `:625`, `copyAdditiveVideo(...)` at `:627`; `copyAdditiveVideo` has exactly **one** caller repo-wide (enumerated with `os.walk` + `re`, not grep). TWO branches, correctly stated. The *observability* of the new placement is M1 |
| 5 — `transferClassA` | **HOLDS.** `:782` `transferClassA(localSide, cloudSide, …)`, `:793` `transferClassA(cloudSide, localSide, …)`. TWO ✅ |
| 6 — the share guard | **HOLDS.** `getShareServeContext` at `lib/share/serve.ts:13`; `mdKey` produced at `:47` and returned at `:53` with no guard; both `base` derivations confirmed at `app/s/[token]/route.ts:69` and `:78`. Share tokens are cloud-only. One branch ✅ |
| 7 — `serialize` | **HOLDS, and the local-satisfiability argument is exactly right.** `serialize` at `model-store.ts:34`, consumed at `:52` and `:73`. Three production writers and no more (`generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464`). `runHtmlDoc(videoId: string, …)` at `generate.ts:11-12`, `video` resolved at `:23` — local *can* satisfy the write schema. `serve-doc.ts` has `videoId` as an explicit param at `:48`, destructured `:70`. No read→write envelope round-trip exists outside `sync-run.ts:464` (`rerender.ts:43` and `read-model.ts:36`/`:64` read only). The cost of the change is L2, not a defect |

**Other v19 claims verified:**

- The `unservable-base` explicit branch **does not contradict anything** in `sync-run.ts:739-757`.
  `SerialReconcileResult` (`reconcile-serial.ts:69-81`) is a closed union with an existing `key`-carrying
  member, and the generic tail at `:756` already interpolates `'key' in rec` — a new variant slots in
  mechanically. The only residue is L1's stale word.
- **Behaviors 26e and 18j7 are writable.** 26e observes a vault file appearing after a cloud→local
  hydrate; 18j7 observes `videoId` surviving `copyBlob`. Both need the fixture seeded *around* the seam
  guard (via the `persistSummary` RPC — `tests/integration/helpers/cloud.ts:118` — or service-role SQL),
  since `videoDataPayload` will refuse to write an unservable key. Worth one sentence in the plan; not a
  defect. Only **26f** cannot be written as claimed (M1).
- **The character hygiene claim holds. MEASURED** on Node v22.14.0 over the whole spec file: `\p{Cc}`
  excluding `\n` → **0**; `\p{Cf}` → **0**; `\p{Bidi_Control}` → **0**; `isWellFormed()` → **true**. The
  seven `\uXXXX` sequences present are escapes in prose and code fences, which is what the rule asks for.
- **Round-16's retired falsifier stays retired.** I attacked the two dominating points independently —
  `stripComputed`'s three call sites and `serialize`'s two — and found no writer reaching either durable
  state without passing through them. No `mechanism` finding this round, for the second round running.
- ~20 line references spot-checked across `sync-run.ts`, `reconcile-serial.ts`, `model-store.ts`,
  `supabase-metadata-store.ts`, `summary-handler.ts`, `serve.ts`, `generate.ts`, `serve-doc.ts`,
  `assert-cloud-summary-md-key.ts`, `local-metadata-store.ts` — **all exact**, including the 4–131
  code-point bound of `/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` and P5's "exactly 2 callers"
  (`serve-summary-core.ts:61`, `resolve-summary-key.ts:16`).

**Not run:** nothing. No measurement in this review was blocked; I touched no Supabase instance and
created no objects, because every claim under attack was answerable from the source.

---

## Phase-1 exit recommendation

**Do not exit Phase 1 on this version.** Not because of the count — three Lows and two Mediums would
converge, and I would have said so — but because B1 is a live path from a shipped design to a
permanently unrecoverable paid artifact, and because it is the third instance of a shape the round
before last armed a falsifier against.

The remedy I would take to `writing-plans` is narrow, and I do **not** think it is a rewrite of the
design:

1. Fix B1 as specified (two-part: scope the refusal to "the old base was servable", and make the
   message arm-aware). This is ~5 lines of spec and one extra behavior row.
2. Rewrite §3.5.1b's Branches column against the **guarded value**, not the receiver, and re-run it.
   That is the escalation's actual content: the previous prophylactic asked a narrower question than
   the defect class it was built for. Rows 4 and 5 survive unchanged; row 3 becomes TWO; rows 1, 2, 6
   should each restate what value they test (`payload.summaryMd`, `baseName`, `mdKey`) so the same
   question can be asked of them.
3. Fix M1 (pin the guard before `sync-run.ts:626`, reword 26f to the sender-blob-read observable) and
   M2 (one canonical statement of the adopt placement, three pointers).
4. Fold the four Lows.

Then **one** more round, aimed at §3.5.1b's rewritten table and nothing else. If the re-asked question
produces no fourth instance, the design has earned its exit; §3.1–§3.4 and §3.6 have been stable for
several rounds and I found nothing new in them.

NOT CONVERGED
