# Round 15 — Claude adversarial review of spec **v17** (backlog #36)

Subject: `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` in the **working tree**
(v17, commit `d5c8bf4`). Branch `fix/cloud-blob-key-encoding`. Phase 1 — no code written.

**Verdict: NOT CONVERGED.** 0 Blocking, 2 High, 3 Medium, 3 Low.

| Classification | Count |
|---|---|
| mechanism | 1 (H1) |
| branch-coverage | 3 (M1, M2, M3) |
| stale cross-reference | 4 (H2, L1, L2, L3) |

Caused by v17's own fixes: **H1, H2** (and L2 partly). Everything else predates v17.

---

## The headline: v17 replaced three enumerations with three derivations. **Two are sound; the third is not a derivation.**

| Derivation | Result this round |
|---|---|
| Guard call sites → **refuse at the metadata seam** | ✅ **HOLDS.** I enumerated every production write to `videos.data` in cloud mode independently. There is no fourth advertisement path. Details below |
| Bidi code points → **the full `Bidi_Control` property** | ✅ **HOLDS, MEASURED.** Exactly 12 code points; the spec's escaped class has **0 misses and 0 over-matches** across the whole codepoint space |
| Envelope writers → **`writeModelEnvelope` REQUIRES `videoId`** | ❌ **DOES NOT HOLD.** There are **two** writer functions, `writeModelEnvelope` and `writeModelEnvelopeWithin`, and the production serve path calls the second. A repo tripwire *forbids* collapsing them. This is the entrance-list failure again, one name deep — H1 |

---

## Brief item 1 — is the seam actually a seam? **YES. Verified by enumeration, no fourth path.**

This was the highest-value item and it is the one place I most expected to find a Blocking. I did not.

**Every production write that can reach `videos.data` in cloud mode:**

| Writer | Reaches the row via | Guarded by v17? |
|---|---|---|
| `copyAdditiveVideo` | `SupabaseMetadataStore.upsertVideo` (`sync-run.ts:286` → `supabase-metadata-store.ts:115-123`) | ✅ seam |
| `transferClassA` | `updateVideoFields` (`sync-run.ts:432` → `:133-147`) | ✅ seam |
| `reconcileCloudBase` | `updateVideoFields` (`reconcile-serial.ts:324`) | ✅ seam + in-memory refusal |
| worker **mint** | `persist_summary` RPC (`worker-persistence.ts:22`, called at `summary-handler.ts:177`, `:179`) | ✅ own call site at `:96` |
| `claim_video_slot` / `reserve_video_slot` | RPC, bare reservation — no `summaryMd` | n/a |
| `update_video_annotations` | server-side allowlist ({personalScore, personalNote, corrections, archived}) | n/a |
| `reconcile_membership` | archived / removedFromPlaylist only | n/a |
| `serviceClient.from('videos').delete()` | `summary-handler.ts:132` — a **delete**, not an advertisement | n/a |
| `writeArtifact` | `consistency.ts:33`, `:39` | **zero production callers** — re-verified this round |

I specifically hunted for the shapes the brief named:

- **An RPC that patches the row:** the only ones are `merge_video_data`, `merge_video_data_bulk`,
  `update_video_annotations`, `persist_summary`, `claim_video_slot`, `reserve_video_slot`,
  `reconcile_membership`. All but `persist_summary` (and the two reservation RPCs, which write no key)
  are reached only through `SupabaseMetadataStore`.
- **A service-role write:** `summary-handler.ts:132` is the only direct `from('videos')` mutation
  outside the adapter, and it is a guarded delete (`.is('data->>summaryMd', null)`).
- **`pipeline.ts` / `serial-migrate-exec.ts`, which do write `summaryMd`:** both call
  `getStorageBundle()` with **no client**, and `resolve.ts:56` throws under `STORAGE_BACKEND=supabase`
  (`'supabase backend requires an authenticated client'`). They are structurally local-only.

So v17's central claim is correct as far as *entrances* go. The residual is not an entrance — it is a
**method** of the seam itself (M1).

---

## H1 — `writeModelEnvelope` is ONE OF TWO writer functions, and the serve path is contractually barred from using it. `mechanism`, caused by v17.

**Evidence.**

```ts
// lib/html-doc/model-store.ts:34-37 — the ONE function both writers share
function serialize(envelope: ModelEnvelope): Buffer {
  ModelEnvelopeSchema.parse(envelope);
  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
}
// :46-53   export async function writeModelEnvelope(principal, base, envelope, blobStore)
// :66-101  export async function writeModelEnvelopeWithin(timeoutMs, principal, base, envelope, blobStore)
```

The three production writers:

| Writer | Calls | Reached by v17's rule? |
|---|---|---|
| `lib/html-doc/generate.ts:50` (local generate) | `writeModelEnvelope` | ✅ |
| `lib/cloud-sync/sync-run.ts:464` (the sync ship) | `writeModelEnvelope` | ✅ |
| **`lib/html-doc/serve-doc.ts:174` (the cloud serve path)** | **`writeModelEnvelopeWithin`** | ❌ |

And they **cannot** be collapsed — this repo has a test that forbids it:

```ts
// tests/lib/html-doc/serve-bounded-import-guard.test.ts:104-110
const BANNED = [ …,
  { unbounded: /\bwriteModelEnvelope\b/, bounded: 'writeModelEnvelopeWithin',
    why: 'awaits the Supabase upload with no bound at all' } ];
```

**Failure scenario.** An implementer follows §3.6.4 literally: add `videoId` as a required parameter of
`writeModelEnvelope`. `tsc` then forces `generate.ts` and `sync-run.ts` to supply it. `serve-doc.ts`
compiles unchanged, because it calls the other function. Every model the **cloud serve path** writes —
the busiest writer, and the one that spends money — carries no `videoId`. `companionTransfer` reads that
receiver envelope and takes the **legacy "proceed, cannot prove ownership"** row of §3.6.4's table
forever, so the guard added to stop `loser.blob.delete(models/${base}.json)` (`sync-run.ts:475`) from
destroying a **paid** artifact is inert on exactly the path that produces those artifacts. Behavior 18j5
names `serve-doc.ts` as covered; the mechanism it cites (*"because `writeModelEnvelope` requires the
parameter"*) does not reach it, so 18j5 would be satisfied by hand-editing one call site — the thing v17
exists to stop.

It also **falsifies the migration argument**: §3.6.4's *"any re-serve rewrites the envelope through
`serve-doc.ts:174` with `videoId`, so the 7 legacy prod envelopes close without a migration"* is the
sentence that lets this ship without a backfill, and it is only true if the serve writer is changed.

**Fix.** Put the requirement where **both** writers already pass: `serialize()`. Give the module a
write-time schema (`videoId: z.string().min(1)`) distinct from the read-time `ModelEnvelopeSchema`
(where it stays optional for legacy reads), and have `serialize` validate against the write schema. Then
`writeModelEnvelopeWithin` is covered by construction, the count of writer *functions* stops mattering,
and the mutation row *"Make `writeModelEnvelope`'s `videoId` parameter optional"* becomes *"relax the
write-time schema"*. Behavior 18j5 should assert the property **through `serve-doc.ts` specifically**,
because that is the writer the current wording misses.

**Classification.** `mechanism` — a redesign of the *enforcement point* (one level down, into the shared
`serialize`) dissolves it entirely, which is the repaired discriminator's test. Caused by v17's fix.

**But it does NOT argue for a wider redesign of §3.6.4, and I want to be explicit about that.** The
credential itself — `envelope.videoId === row.videoId`, two immutable ASCII ids — is untouched by this
finding and I verified it survives the case round-13 H1 killed `sourceMd` on: `reconcileCloudBase`
byte-copies the envelope (`reconcile-serial.ts:98`, `:118` → `copy`), so `videoId` travels inside the
JSON and behavior 18j3 holds. The defect is that the *requirement* was attached to a function name
rather than to a point that dominates the writers — the same selection error as the entrance list, not a
wrong shape for ownership. **Falsifier for this judgement:** if round 16 produces another
*"the derivation does not reach writer N"* finding, then the pattern is that this document keeps choosing
enforcement points by name instead of by dominance, and *that* is the redesign owed.

---

## H2 — the spec contradicts itself on whether the ADOPT call site survives, and one reading recreates the state H-R2-1 forbids. `stale cross-reference`, caused by v17.

**Evidence — three places say the adopt guard exists, one says it does not:**

- §3.5.1:624 — *"**Two placements stay outside the seam**, each for a stated reason"* → the mint and
  `reconcileCloudBase`. The adopt guard is **not** among them, under a heading that reads
  *"⛔ ONE ENFORCEMENT POINT"*.
- Behavior **26** (:1251) — *"The adopt refuses a non-servable key **before `ensureReceiverSlot`** — no
  receiver row is created"*.
- Behavior **26b** (:1252) and mutation rows :1302, :1303 — *"Remove the adopt guard call"*,
  *"Move the adopt guard back BELOW `ensureReceiverSlot`"*.
- §3.5:531 — *"Call `isServableSummaryKey` at the mint … **and on the adopt path**."*

**Failure scenario for the §3.5.1 reading.** With no adopt call site, the refusal for the additive path
lands at the seam — `to.upsertVideo` (`sync-run.ts:286`). By then:

- `ensureReceiverSlot` has run at `:240` and `claimVideoSlot` did a **durable insert**
  (`supabase-metadata-store.ts:91-110`), and
- the MD blob has been staged, verified and **promoted** at `:263-268`.

That is precisely the state `sync-run.ts:230-235` says must never be created:

> *H-R2-1 (round 2) — this guard MUST run BEFORE `ensureReceiverSlot`, not after. Claiming the slot
> first left a BARE receiver row behind on the throw…*

Run 2 is then two-sided, so `copyAdditiveVideo` is never called again; and every run re-stages and
re-promotes an orphan blob at the unservable key. It is **not data loss** — I traced it: run 2 takes
`reconcileCloudBase` → early `agreed` (`reconcile-serial.ts:179`, `cloudVideo.summaryMd` is null) →
`reconcileClassA` → `copyToCloud` → `transferClassA` → **the seam refuses at `:432`**, throws, no
baseline. So v17's seam *does* close round-13 H2's run-2 route, which is the real strength of this
version. But behavior 26's assertion *"no receiver row is created"* would be **false**, and the run
accumulates a bare row plus one orphan blob per sync.

**Fix.** Say three placements, not two, and give the adopt guard its reason in the same list: it is not
redundant with the seam, it is the thing that keeps the seam's refusal from happening *after*
`claimVideoSlot`'s durable insert. Then behaviors 26/26b and the two mutation rows are consistent with
the prose.

---

## M1 — the seam has THREE data-writing methods and the rule names two. `branch-coverage`.

`SupabaseMetadataStore.bulkUpdateVideoFields` (`supabase-metadata-store.ts:153-163`) patches
`videos.data` through `merge_video_data_bulk`, with the same `stripComputed` treatment as its two
guarded siblings. §3.5.1's entrance table and behavior 26c cover only `upsertVideo` and
`updateVideoFields`.

**Reachability, checked before grading:** its two production callers are `pipeline.ts:339`
(playlistIndex / dates) and `serial-migrate-exec.ts:14` (serialNumber only), and both are local-only
per the `getStorageBundle()` argument above. **No caller passes `summaryMd` today**, so this is a hole
by construction, not a live defect — Medium, not High.

It matters because the design's whole claim is *"the entrance count stops mattering"*, and it stops
mattering only for the methods the guard is installed on. The count did not disappear; it moved from
4 entrances to N adapter methods. Add `bulkUpdateVideoFields` to the rule and to behavior 26c, or state
in one sentence why a method that merges arbitrary `fields` into `videos.data` is exempt.

*(A redesign that pushed the refusal into SQL — `merge_video_data`, `merge_video_data_bulk`,
`persist_summary`, or a CHECK on `videos.data` — would dissolve both M1 and the mint's exemption. I am
not calling that owed: it is a placement refinement of the same shape, and the mint's exemption has a
real justification (`refuse before money`) that SQL would not serve as cleanly.)*

---

## M2 — "refuse in the adapter" still has no stated OUTCOME, and the three callers behave differently. `branch-coverage`.

This was brief item 2 and it is not answered anywhere in v17. Per caller:

| Caller | Where the seam refusal lands | What is already durable | Net state |
|---|---|---|---|
| `copyAdditiveVideo` | `upsertVideo`, `sync-run.ts:286` | bare receiver row (`:240`) **and** a promoted blob (`:268`) | see H2 — this is why the adopt guard must survive |
| `transferClassA` | `updateVideoFields`, `:432` | **`loser.blob.put(loser.p, key, staged, …)` already ran at `:394`** | orphan blob at the unservable key on the loser; the loser's row still points at its old key, so nothing is lost. Throw → caught at `:812` → `report.errors`, no `writeVideoBaseline` → re-fires every run |
| `reconcileCloudBase` | in-memory, before the copy phase | nothing | clean refusal — see M3 |

Two things follow that the spec should state:

1. **The design's own principle is not applied uniformly.** §3.5.1 justifies `reconcileCloudBase`'s
   in-memory refusal with *"so no blob is copied and nothing is deleted, rather than relying on the seam
   to reject after the copy"* — and then relies on exactly that for `transferClassA`, where the blob
   `put` at `:394` precedes the row write at `:432`. The consequence is benign (an orphan, not a loss),
   but it should be a stated accepted residual, not a silence, because it is the same sentence's
   reasoning reaching the opposite conclusion twelve lines apart.
2. **Behavior 26c is direction-dependent for `transferClassA` and does not say so.** On `copyToLocal`
   the loser is the **local** store (`sync-run.ts:791-793`), which has no seam guard at all — correctly,
   per §3.4. A test written against `copyToLocal` would pass vacuously. 26c must name `copyToCloud`.

`companionTransfer`'s never-throw contract (`sync-run.ts:441-443`) is **not** at risk from the seam —
it writes a blob, not the row — and the `videoId` refusal already returns `{ shareNeedsOwnerServe, error }`
per §3.6.4's table. Under H1's fix (a required field in the write-time schema) a missing `videoId` is a
compile error, not a runtime throw; and the ship at `:464` is inside a `try/catch` that returns an error
anyway. That branch is sound.

---

## M3 — `reconcileCloudBase`'s new refusal needs a `SerialReconcileResult` variant, and the spec names none. `branch-coverage`.

`SerialReconcileResult` (`reconcile-serial.ts:69-81`) is a closed union, and the caller
(`sync-run.ts:735-757`) dispatches on `rec.reason` with a generic tail:

```ts
throw new Error(rec.reason === 'target-occupied'
  ? `serial collision: …`
  : `base reconciliation failed for ${id}: ${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}`);
```

So a new variant **works mechanically** — it falls into the generic throw, is caught per-video at `:812`,
advances no baseline, and re-fires cleanly. Brief item 3 is answered: not stuck, and 26d's placement
"alongside `target-occupied` / `unsupported-artifacts`" is correct — those are at `:197` and `:214`,
after `describeDivergence` at `:183` computes `newBase`, so the value being judged is in scope. ✅

What is missing: the spec names neither the `reason` string nor the message. Behavior 26 requires the
**adopt** error to *"name the manual repair"*; behavior 26d requires no such thing — and this is the case
an operator is *least* able to diagnose, because the offending name is a **local vault filename** while
the error is reported against a **cloud** video. Name the variant (e.g. `{ ok:false, reason:'unservable-base', key }`
— note `key` makes the existing `'key' in rec` branch produce a usable message) and give 26d the same
"names the repair" clause 26 has.

---

## Brief item 5 — behavior 26d IS writable as a test. ✅

*"refused IN MEMORY: no blob is copied, the old base is intact, nothing is deleted"* has three
independently observable assertions: the returned `SerialReconcileResult` is the refusal variant; the
cloud blob store received **zero** `copy` calls (or `list(dig/${newBase}/)` is empty and
`MODEL_KEY(newBase)` absent); and every old-base key still reads back. All three are already exercised
by the existing harness — `tests/lib/cloud-sync/reconcile-serial.test.ts:107-119` asserts exactly this
shape for the relocated case. Unlike round-13 H2 and round-14 B1, this behavior can observe the state it
claims.

---

## Brief item 6 — §3.4/§3.5 measured, and they hold. ✅

Ran under `~/.nvm/versions/node/v22.14.0/bin/node` (v22.14.0). No repo file touched; probes in `/tmp`.
No live Supabase was contacted — nothing in this round needed it.

**Bidi_Control:**

```
Bidi_Control count: 12  U+061C U+200E U+200F U+202A U+202B U+202C U+202D U+202E U+2066 U+2067 U+2068 U+2069
spec class misses: 0   over-matches: 0
```

The spec's escaped class is exactly the property. Round-14 L1 is genuinely closed.

**The §3.4 predicate, transcribed verbatim from v17** — 15/15 cases as the behaviors claim, including
`003_lesson-⒈.md` **accepted** (17d/23), `001_a．．b.md` **rejected** (17), `℀.md` rejected,
`003_x\ud840.md` rejected (16c), C1 rejected (16c), Korean / NFD-accented / space / `U+1F100` accepted.
Length bound: 4→131 accepted, 3 and 132 rejected (17b). Astral key of **68 code points / 132 UTF-16
units** → accepted, so the predicate counts code points (24).

**Behavior 27 and 16b, swept:** every code point × 4 title shapes, slugified with the §3.2 repair and
composed into the key the mint actually builds (`${padSerial(serial)}_${slug}.md`, `summary-handler.ts:96`,
`:172`) —

```
checked 4448256   ill-formed slugs remaining 0   FAILING keys: 0   bare-slug keys failing: 0
```

I deliberately swept the **composed** key rather than the bare slug, because §3.2's cited sweep was of
slug outputs and the guard sees `NNN_<slug>.md`. Both are clean.

---

## L1 — §3.5:518 still puts the adopt refusal at `sync-run.ts:263`. `stale cross-reference`.

Round-13 H2 (:534-563) moved it above `ensureReceiverSlot` (`:236-238`). The §3.5 bullet
(*"The adopt refusal (`sync-run.ts:263`) is per-video, caught, and advances no baseline"*) is written in
the present tense as a current cost, not as history, and states the location the same section later
proves wrong. Six words.

## L2 — §7's risk row (:1355) is a v10-era sentence under a v17 design. `stale cross-reference`.

*"v10 adds the mint and adopt call sites"* — v17 adds a seam refusal plus two (or three, per H2)
placements outside it. Same fix as L1: when a decision is reversed, grep for every sentence stating the
old one.

## L3 — §3.5.1:615 cites the mint's persist as `summary-handler.ts:157`. Nit.

`:157` is the `summaryMd: \`${baseName}.md\`` field of the record literal; the `persist_summary` calls
are at `:177` and `:179`. The claim is right, the line is not.

---

## Escalation counter, stated honestly

The brief asks whether a *fourth* mechanism defect in §3.5/§3.6 means the shape is still wrong.

**H1 is a mechanism defect and it is fix-induced.** By the letter of the counter, that arms REDESIGN.
I am recording an **override**, with a falsifier, because the repaired discriminator's actual test —
*can a redesign remove it?* — points somewhere narrower than a redesign of §3.6.4:

- The **credential** (`envelope.videoId === row.videoId`) is not what failed. I checked the case that
  killed its predecessor: relocation byte-copies the envelope, so `videoId` survives `remap` and 18j3
  holds. No reshaping of ownership removes H1.
- What failed is **where the requirement was attached** — a function name, when two functions write and
  a repo tripwire forbids merging them. Moving it into the `serialize()` both writers already call
  removes the finding completely, and it is a five-line change inside one module.
- The other two derivations v17 introduced were attacked head-on this round and **held**, one of them by
  measurement over 4.4M inputs and a total sweep of the codepoint space.

**Falsifier:** fires to REDESIGN if round 16 produces another fix-induced finding of the form *"the
derivation does not reach writer/method/caller N"* — H1 and M1 are already two instances of that shape
in one round, which is why this override is narrow and not comfortable.

---

## What I did not find

No Blocking. No money loss, no orphaned or unreachable paid artifact, and no un-ingestible video
introduced by v17. The seam is real, the predicate is measured correct, and round-14's B1 is genuinely
closed by structure rather than by a fourth call site. Fifteen rounds in, that is worth saying plainly:
**the shape is right; the third derivation is not yet a derivation, and four sentences describe a design
that changed underneath them.**

NOT CONVERGED
