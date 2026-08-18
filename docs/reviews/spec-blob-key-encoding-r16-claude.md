# Round 16 — Claude adversarial review of the cloud blob key encoding spec (backlog #36), v18

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` in the **working
tree** (v18, 1577 lines), branch `fix/cloud-blob-key-encoding`. Phase 1, no code written.
**Reviewer:** Claude half of the round-16 dual pass. **Date:** 2026-08-15.

---

## THE ARMED FALSIFIER — the answer first

> *Fires to REDESIGN if round 16 produces another fix-induced finding of the form "the derivation
> does not reach writer/method/caller N".*

**IT DOES NOT FIRE. Both dominating points hold under attack, and I could not construct a third
instance of that shape.** I attacked both by independent enumeration over the whole repo (python +
`os.walk`, never `grep` — see *Method*), and both survived:

| Claim | Verdict | What I found |
|---|---|---|
| `serialize()` (`lib/html-doc/model-store.ts:34`) is the only path from a `ModelEnvelope` to bytes | **HOLDS** | Module-private `function` declaration, not exported. Exactly two production callers, both in the same module (`:52`, `:73`). No production code writes `models/<base>.json` from an envelope *value* by any other route |
| `stripComputed()` → `videoDataPayload()` (`lib/storage/supabase/supabase-metadata-store.ts:19`) is the only constructor of what lands in `videos.data` through this adapter | **HOLDS** | Module-private, three call sites (`:119`, `:143`, `:160`), zero references anywhere else in the repo including tests. I enumerated every other route to `videos.data` — none can set `summaryMd` or `artifacts.summaryMd` (evidence below) |

**But this round is NOT CONVERGED.** I found one **Blocking** defect of a *different and opposite*
shape: an enforcement point that reaches a caller the rule was never written for — **over-reach, not
under-reach**. That distinction is the whole point, so I state it plainly: the pattern round 15
diagnosed ("choosing enforcement points by name instead of by dominance") is **not** what produced
B1. A wider redesign is **not** owed. A fourth repair is — and it is a small, well-specified one.

---

## Method (so a later reader can tell what was measured from what was read)

- `grep` on this machine is ugrep and silently returns nothing; every enumeration below was done with
  `python3` + `os.walk` + `re` over the whole repo (excluding `node_modules`, `.git`, `.next`,
  `dist`, `coverage`), or by reading the file with the Read tool. Scratch scripts live in the session
  scratchpad, not the repo.
- Node v22.14.0 (`~/.nvm/versions/node/v22.14.0/bin/node`) for the Unicode measurements.
- **No Supabase connection was opened.** Nothing in this round needed one; the two dominance claims
  are static-reachability claims and the SQL was read from `supabase/migrations/`. Stated rather than
  left silent: the RPC bodies below are **QUOTED from the migration files**, not executed. If you
  want them proven against the live local stack, that is a separate measurement and it did **NOT
  RUN**.
- I modified no tracked file. This document is my only write.

---

## Findings, most severe first

### B1 — BLOCKING. The adopt guard is direction-agnostic, and on `copyToLocal` it removes the LAST route to an already-unservable paid artifact

**Classification: `branch-coverage`** (by the repaired test: *can a redesign remove it?* — **no**.
The two directions are owned by `runSync`'s additive branch, not by this design; any placement,
under any shape, still has to answer *"which receiver?"*. A new shape cannot delete the branch, only
fail to mention it — which is the defect in hand, and it is §3.6.1b's own class).
**Caused by v18's own fixes: partially.** The placement is round-13 H2's (`above ensureReceiverSlot`).
What is new in v18 is **§3.5.2**, the per-caller outcome table, which asks the direction question for
`transferClassA` and **not** for `copyAdditiveVideo` — one row away, in the same table.

**The rule, as written.** §3.5.1 placement 3 (spec:739-746) and §3.5.2 row 1 (spec:759):

> 3. **The adopt path keeps its call site above `ensureReceiverSlot`** (`sync-run.ts:236-238`) …
> | `copyAdditiveVideo` | **the adopt guard**, above `ensureReceiverSlot` (`sync-run.ts:236-238`) |
> **nothing** | Video stays one-sided. … re-fires identically every run **until a human renames the
> vault file**. ✅ intended |

Neither sentence names a direction. Behavior 26 (spec:1462) does not either.

**The code the rule lands in serves BOTH directions.** `lib/cloud-sync/sync-run.ts:618-627`:

```ts
if (!lv || !cv) {
  const present = (lv ?? cv)!;
  const presentIsLocal = lv != null;
  …
    const from: Side = presentIsLocal ? localSide : cloudSide;
    const to: Side   = presentIsLocal ? cloudSide : localSide;
    const body = await readMdBody(from.blob, from.p, present);
    await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
```

`copyAdditiveVideo` is **one function**, and `sync-run.ts:236-238` — the WB-H1 check the adopt guard
is to sit beside — runs on every call regardless of which side `to` is. So the guard fires on the
**cloud→local hydration** path too.

**Failure scenario, concrete.**

1. A cloud video today holds an unservable `summaryMd` — say `notes..part2.md`, a 140-code-point
   name, or one carrying a bidi control. §3.5's own reachability table (spec:539) already names the
   producer: `recoverOrphanedVideos` adopts any `*.md` with a `video_id` field verbatim
   (`pipeline.ts:104`, `:137`), and today's **unguarded** `copyAdditiveVideo` copies it to cloud and
   advertises `promoted` (`sync-run.ts:263`, `:279`). This state exists in the wild today; the spec
   says so.
2. The local side loses its copy — a second machine, a fresh vault, or the user deleted the file.
   The video is now **one-sided (cloud only)**.
3. **Today**, sync hydrates it back: `copyAdditiveVideo(to = localSide)` stages and promotes the MD
   into the vault (`sync-run.ts:263-268`). `LocalFsBlobStore` has no servability guard — correctly,
   per §3.4 — and `assertLogicalKey` (`blob-store.ts:87-91`) accepts all three example keys, since
   none has a leading `/`, a `..` *segment*, or `\0`. The user gets their paid summary back as a file.
4. **After this design**, the adopt guard refuses at `sync-run.ts:236-238` before
   `ensureReceiverSlot`, throws, is caught per-video at `:812`, advances no baseline, and **re-fires
   every run, forever.**

And every other route is already closed, or is closed by this same version:

| Route | State |
|---|---|
| owner serve / MD download / HTML download (`/api/html/[id]`) | 409 today — `loadSummaryForServe` calls `assertCloudSummaryMdKey` at `serve-summary-core.ts:61` before reading the blob |
| PDF (`/api/pdf/[id]:45`), dig-state (`dig-state/route.ts:38`), dig enqueue (`enqueue-dig-core.ts:28`) | same gate, 409 today |
| **share link** | **works today** — `lib/share/serve.ts:47` returns `mdKey` with no guard call (§3.4 says so). **v18 closes it** by putting the call inside `getShareServeContext` |
| **cloud→local sync** | **works today. B1 closes it.** |

So v18 closes the two remaining routes to that artifact in the same version — one deliberately
(share, graded "a Low-severity fix to a Medium-severity observation", spec:498-501) and one by
accident (this). The net result is a **paid summary that is unreachable through every product path**,
with no in-product repair: a re-serve cannot run because the serve path refuses before it reserves
(spec:641 says exactly this about the round-14 B1 case).

**Why Blocking and not High.** The brief's rule: *"a paid artifact or vault file lost, orphaned,
**unreachable** or double-charged is Blocking."* It is unreachable, and it becomes so *because of
this change* — today's behaviour recovers it. I record the argument for High so the coordinator can
adjudicate: nothing is **deleted**, the cloud blob survives, and a human with DB + Storage access
could rename it. I still grade Blocking, for consistency with round-14 B1, which was graded Blocking
on the *same* precondition class (a hand-placed or externally-renamed vault file) and whose harm was
also "unreachable, recovery costs money".

**It also contradicts a user decision.** Decision ① (spec:112) is *"the vault wins — local filenames
keep their Unicode"*, and §3.4's central thesis is that the local path never needed this guard and
has run without one, full of Korean filenames, for the app's entire life (spec:466-470). A guard that
refuses to write a name **into the vault** is the opposite of that decision.

**Also: the stated repair is wrong in that direction.** §3.5.2 says the refusal re-fires *"until a
human renames the vault file"*. On cloud→local there **is no vault file** — the offending name is a
cloud key, and "rename" is not an operation the user has. This is the same defect §3.5.1 flags for
`reconcileCloudBase` ("the offending name is a *local vault filename* while the error is reported
against a *cloud* video", spec:736-738), mirrored.

**Fix.** Scope the adopt guard to the **cloud receiver**, and say so in three places:

- §3.5.1 placement 3: *"…and it applies only when the receiver is the cloud. `copyAdditiveVideo` runs
  in both directions (`sync-run.ts:624-627`); on `copyToLocal` the receiver is the vault, which §3.4
  argues at length must not be guarded, and refusing there strands a paid cloud artifact that has no
  other route."*
- §3.5.2 row 1: split into the two directions, and drop *"until a human renames the vault file"* from
  the direction where no vault file exists.
- Behavior **26** must name the **local→cloud** direction, exactly as **26c3** already does for
  `transferClassA`, plus a sibling **26e**: *"a cloud→local additive hydration of an unservable key
  SUCCEEDS — the vault is not guarded."* Without it, a test written against the wrong direction
  passes vacuously; **with the fix but without 26e, the regression is invisible.**
- Mutation row: *"apply the adopt guard in both directions"* → must turn **26e** red.

Mechanically the direction is already available at the call site (`presentIsLocal` at
`sync-run.ts:620`), so this is a parameter, not a redesign.

---

### M1 — MEDIUM. `unservable-base`: "no change to the caller" and "the message names the manual repair" cannot both be true

**Classification: `branch-coverage`** (redesign cannot remove it — you still have to decide what the
operator reads). **Caused by v18's own fixes: YES.** Both the variant and behavior 26d's new clause
are v18 additions (round-15 M3).

**The two requirements**, twelve lines apart (spec:730-738):

> …so a variant carrying `key` produces a usable message with **no change to the caller**.
>
> **And it must name the manual repair, which behavior 26d did not require.** … Give 26d the same clause.

and behavior 26d (spec:1468): *"…the result is `{ ok:false, reason:'unservable-base', key }`, **and
the message names the manual repair**"*.

**The caller, quoted.** `lib/cloud-sync/sync-run.ts:754-756`:

```ts
throw new Error(rec.reason === 'target-occupied'
  ? `serial collision: ${id} needs serial ${rec.want} on cloud, already held by ${rec.heldBy}`
  : `base reconciliation failed for ${id}: ${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}`);
```

With no caller change the operator sees exactly:

```
base reconciliation failed for dQw4w9WgXcQ: unservable-base at 003_....md
```

That **does** name the offending filename (the `key` half of the design is verified correct — `newBase`
is derived from `localVideo.summaryMd`, `reconcile-serial.ts:152-154`, so it is the local vault name).
It does **not** name the repair. Behavior 26d therefore goes **red** against the mechanism the same
section prescribes. An implementer resolves the contradiction by guessing.

**The precedent is already in the file and the spec does not invoke it.** `job-in-flight` got its own
caller branch for precisely this reason (`sync-run.ts:749-753`): *"Say so in the user's words, because
the action is 'Re-run once it finishes', not 'something is broken'."*

**Fix.** Drop *"no change to the caller"* and specify the branch, next to `job-in-flight`:

```ts
if (rec.reason === 'unservable-base') {
  throw new Error(
    `base reconciliation refused for ${id}: the local vault filename ${rec.key} cannot be served ` +
    `from the cloud. Rename that file in the vault and re-run the sync.`);
}
```

**Verified while there, and not a finding:** adding a member to `SerialReconcileResult`
(`reconcile-serial.ts:69-81`) breaks nothing. It is consumed in exactly one place — `sync-run.ts:739-757`
— via `if`/`else`, with no exhaustive `switch` and no `never`-assertion. The spec's "verified that a
new variant works mechanically" claim is correct.

---

### L1 — LOW, stale cross-reference. §3.5 still says "the mint and adopt call sites", and round 15 fixed the twin sentence in §7 and missed this one

**Classification: `stale cross-reference`. Caused by v18's own fixes: no — it is the *residue* of
round-15 L2's fix, which was applied in one of the two places.**

spec:548-551:

> **The honest form carries no universal at all:** the encoder makes every key storable;
> `isServableSummaryKey` rejects a specific, enumerated class; **the mint and adopt call sites** exist
> so that class is refused *before* anything is durable or paid.

Two claims, both now false:

1. **The enumeration is three versions dead.** v18 has *four* enforcement points — the
   `videoDataPayload` seam plus three stated placements (§3.5.1). This is verbatim the sentence
   round-15 L2 caught in §7's risk table, where it **was** fixed (spec:1575 now reads *"v18 guards it
   at two dominating points … plus three stated placements outside it"*).
2. **"before anything is durable or paid" is contradicted by §3.5.2's own second row** (spec:760): on
   `transferClassA` the seam refuses **after** `loser.blob.put(...)` at `sync-run.ts:394`, leaving the
   accepted orphan blob. §3.5.2 states that asymmetry explicitly and calls it *"accepted, not
   overlooked"* — and then §3.5 above it still asserts the opposite as a general property.

**Fix.** Rewrite the clause to: *"…and the seam plus the three stated placements (§3.5.1) refuse it
before the row can advertise it — with one stated exception, `transferClassA`, whose refusal lands
after the blob `put` and leaves the accepted orphan of §3.5.2."*

This is the third time in this document that *"when a decision is reversed, grep for every place that
stated the old one"* (its own §3.6.3 lesson, spec:1116-1123) has been the finding.

---

### L2 — LOW, stale cross-reference. `serialize()` is not "the only path from an envelope to bytes"; the invariant survives, the sentence does not

**Classification: `stale cross-reference`** (an over-broad universal, not a mechanism gap).
**Caused by v18's own fixes: YES** — the sentence is new in v18.

spec:1306 and spec:24:

> `// lib/html-doc/model-store.ts:34 — the only path from an envelope to bytes`
> …**`serialize()`** — private, and **the only path from an envelope to bytes**

Two production writers put bytes into a `models/<base>.json` object without calling `serialize`:

| Writer | Evidence | Does it construct an envelope? |
|---|---|---|
| cloud base relocation — **byte copy** | `reconcile-serial.ts:98` (`MODEL_KEY(base)` is in `paidKeysUnder`), `:118` (`remap`), `:282` `cloud.blob.copy(cloud.p, from, to)` | No — copies bytes |
| local serial migration — **direct `fs.writeFileSync`** | `serial-migrate-exec.ts:141`: `fs.writeFileSync(modelTargetAbs, rewriteEnvelopeSourceMd(fs.readFileSync(modelTargetAbs,'utf8'), mdNewName))`, and `serial-provenance.ts:14-18` is `JSON.parse → obj.sourceMd = … → JSON.stringify` | No — field-preserving JSON round-trip, bypassing the BlobStore seam entirely |

**Neither can violate the `videoId` invariant**, and that is why this is Low, not a third instance of
the round-15 shape: both are *transforms of an already-conforming envelope*, and both preserve
unknown fields, so neither can produce an envelope lacking `videoId` that did not already lack one.
The property the design needs — *"no writer can produce `models/<base>.json` without `videoId`"* — is
intact. The sentence asserting how it is intact is wrong, and it is the sentence a future reviewer
will trust instead of re-deriving.

This document has now had **four** universals falsified (§3.4 lists three, spec:392-398). This is the
fourth, and the pattern is identical: a universal about inputs nobody enumerated.

**Fix.** *"`serialize` is the only path from a `ModelEnvelope` **value** to bytes. Two other
production writers move envelope **bytes** — `reconcile-serial.ts:282`'s relocation copy and
`serial-migrate-exec.ts:141`'s local `sourceMd` rewrite — and neither constructs an envelope, so both
preserve `videoId` by construction. A writer that builds an envelope cannot avoid `serialize`; a
writer that copies one cannot break it."* Add a behavior: **18j7 — after a cloud base relocation the
copied envelope still carries the same `videoId`** (18j3 asserts the ship still succeeds, which is
the consequence, not the credential).

---

### L3 — LOW, stale cross-reference. The predicate ships a comment containing an em-dash written as a source escape

`isServableSummaryKey`, spec:302 — the raw bytes of the line, read with `repr()`:

```
'    if (/\\p{Bidi_Control}/u.test(s)) return false;            // the PROPERTY \\u2014 see the note below'
```

i.e. the file literally contains the six characters `\u2014` inside a `//` comment, where they are
not an escape — they are six literal characters that will be copy-pasted into `lib/html-doc/…` and
read by a human as `the PROPERTY \u2014 see the note below`. The spec's rule (spec:445-448) is that **character classes** are written with
escapes because *"the source does not show what it means"*; applying it to prose inverts the rule —
here the source shows something that means nothing. Trivial, and recorded only because this
document's own history says invisible-vs-literal confusion has shipped four times.

**Fix.** Write the em-dash.

---

## Verified under attack, and deliberately NOT findings

Recorded so a later round does not re-derive them, and so the calibration is legible.

1. **`videoDataPayload` dominance — the complete set of `videos.data` writers.** Enumerated over the
   whole repo. Every raw `from('videos')` outside tests: `summary-handler.ts:132` (a `DELETE`),
   `share/serve.ts:39` (a `SELECT`), `worker-persistence.ts:36` (a `SELECT`), and the adapter itself
   (`:40` select, `:118` the `upsertVideo` update, `:186` delete). Every RPC that touches
   `videos.data`, read from the migrations:
   - `merge_video_data` (`0021:62-88`), `merge_video_data_bulk` (`0007:102-120`) — both **can** set
     `summaryMd` and deep-merge `artifacts`. Both reached only through `updateVideoFields` /
     `bulkUpdateVideoFields`, hence through `videoDataPayload`.
   - `update_video_annotations` (`0021:19-48`) — SQL-side allowlist
     `array['personalScore','personalNote','corrections','archived']`, applied key-by-key. **Cannot**
     set `summaryMd`. This is a fourth potential entrance that the spec never mentions and that turns
     out to be closed *in SQL* — worth a sentence in §3.5.1's "outside the seam" note, not a finding.
   - `claim_video_slot` (`0023:39-104`) — `data = data || jsonb_build_object('serialNumber', v_serial)`
     and an insert carrying only the reservation. **Cannot** set `summaryMd`.
   - `reconcile_membership` (`0007:52-79`) — archive/restore only.
   - `persist_summary` (`0021:99`) — **can**, and is outside `MetadataStore`, exactly as the spec
     states (spec:664). Covered by placement 1.
2. **The mint's guard placement is sound.** `summary-handler.ts:96` computes `baseName`; `:157` and
   `:172` derive `${baseName}.md`; `:177`/`:179` persist it. One derivation, one value — a guard at
   `:96` genuinely covers what `persist_summary` writes. `persistSummary` has no other production
   caller.
3. **The "structurally local-only" claim for `bulkUpdateVideoFields` is TRUE, and I verified the
   mechanism the spec cites.** `resolve.ts:50-63`: `getStorageBundle()` under
   `STORAGE_BACKEND=supabase` **throws** (`'supabase backend requires an authenticated client'`)
   when called with no `ctx`. Both callers — `pipeline.ts:339` and `serial-migrate-exec.ts:14` — call
   it with no argument. Payloads checked: `pipeline.ts:331-338` is
   `{playlistIndex, videoPublishedAt, addedToPlaylistAt}`; `serial-migrate-exec.ts:14-17` is
   `{serialNumber}`. Neither carries `summaryMd`. §3.5.2 owes them no row.
   *(`serial-migrate-exec.ts:146`'s `updateVideoFields` **does** set `summaryMd` — `fieldUpdates[op.field] = op.to`
   at `:125` — but by the same argument it is local-only, so §3.4's "local is not guarded" covers it.)*
4. **Attack 2's type-level sub-question: no blindness.** The guard is a *runtime* inspection of the
   payload and all three call shapes carry the fields at runtime — `upsertVideo` gets a whole `Video`
   with `artifacts` attached (`sync-run.ts:272-285` builds `sanitized: any` and sets
   `sanitized.artifacts` at `:279`); `updateVideoFields` gets `completeTuple as Partial<Video>` with
   `artifacts` at `sync-run.ts:430`; `reconcileCloudBase` gets `patch as Partial<Video>` with
   `artifacts` at `reconcile-serial.ts:296`. `<T extends object>` is not an obstacle — `stripComputed`
   already does `v as any` (`:20`).
   **One precision the spec should state:** `artifacts` is **not a member of the `Video` type** (it is
   read via casts at `supabase-metadata-store.ts:53-55` and `sync-run.ts:299`). So the two dominating
   points are **not** enforced the same way: `serialize`'s dominance is **type-level** (`tsc` rejects a
   fourth writer that does not take `ModelEnvelopeWrite`), while `videoDataPayload`'s is **privacy-level
   only** (a fourth adapter method that builds its payload inline compiles fine; it simply cannot
   exist without someone editing this module). Both are real construction arguments; they are not the
   same strength, and §3.5.1 presents them as the same ("the same shape as `serialize()` in §3.6.4",
   spec:704). Worth one clarifying sentence.
5. **Attack 3, read→write: exactly ONE instance, and it is covered.** Every `readModelEnvelope` caller
   in `lib/`: `rerender.ts:43` (read-only — writes HTML at `:73`, never an envelope),
   `read-model.ts:36`/`:64` (read-only), `build-doc-html.ts:124` (read-only),
   `load-dig-for-serve.ts:30` (read-only), `sync-run.ts:490` → `decideCompanion` → **`writeModelEnvelope`
   at `:464`** — the one read→write path, and the spec addresses it (stamp the receiver's `videoId`,
   spec:1331-1332; behavior 18j6). The type split makes it a **compile error** rather than a
   convention: `decision.envelope` is `ModelEnvelope` (`companion.ts:26`) and `writeModelEnvelope`
   would take `ModelEnvelopeWrite`. `winnerVideo.id` is in scope at the call site
   (`companionTransfer(winner, loser, winnerMdHash, winnerVideo)`), so the stamp is available.
   **The split schema is sound and 18j5b covers the read side correctly.**
6. **Each writer's `videoId` source, checked by reading.** `generate.ts:11`/`:50` has `videoId` as a
   parameter and `video` in scope; `serve-doc.ts:174` writes a **fresh object literal** and `videoId`
   is an explicit param already used for the reserve RPC at `:119` — the spec's claim is accurate.
7. **The `\p{Bidi_Control}` derivation.** MEASURED on Node v22.14.0 over the whole codepoint space:
   **exactly 12** code points — `061C, 200E, 200F, 202A–202E, 2066–2069` — including the three v9
   missed. §3.4's fix and behavior 17e are correct, and 17e's *derive-don't-count* wording is right.
8. **v18's zero-`Cc`/`Cf` claim is TRUE.** MEASURED over the whole 1577-line file: 0 characters in
   category `Cc` or `Cf` other than `\n`; 0 tabs; 0 CR. The five-times-shipped invisible-character
   defect is not present in v18. (L3 above is the mirror-image slip, not this one.)
9. **`SerialReconcileResult` has one consumer and no exhaustive switch** — see M1.
10. **`isServableSummaryKey`'s control-character class.** `/[\x00-\x1f\x7f-\x9f]/` has no `u` flag
    while the bidi test does. Checked: it is still correct, because surrogates (`D800–DFFF`) fall
    outside the class and the C1 range is BMP. Not a finding.

---

## Classification split

| Finding | Severity | mechanism / branch-coverage / stale cross-reference | Caused by v18's own fixes? |
|---|---|---|---|
| B1 — adopt guard is direction-agnostic | **Blocking** | branch-coverage | Partly — placement is round-13's; v18's new §3.5.2 asked the direction question one row away and not here |
| M1 — `unservable-base` message vs "no caller change" | Medium | branch-coverage | **Yes** |
| L1 — §3.5's "mint and adopt call sites" | Low | stale cross-reference | No — residue of round-15 L2's partial fix |
| L2 — `serialize` "the only path from an envelope to bytes" | Low | stale cross-reference | **Yes** |
| L3 — literal `\u2014` in the predicate comment | Low | stale cross-reference | **Yes** |

**mechanism: 0.** Nothing found this round says the shape is wrong. The two dominating points were
attacked head-on, by independent enumeration, and both held.

---

## What this means for the escalation

Round 15's override was recorded narrowly because that round contained **two** instances of
*"the derivation does not reach writer N"*. Round 16 contains **zero**. The one Blocking is its
**inverse** — an enforcement point that reaches a caller the rule was never written for — and it is a
branch of a function this design does not own (`copyAdditiveVideo` runs in two directions because
`runSync` calls it in two directions). By §3.6.1b's own argument, *"a redesign cannot help here,
because the branches are not owned by this design."*

**So: FIX, not REDESIGN. The falsifier did not fire, and I am not manufacturing one to avoid saying
so.** The honest summary of v18 is that it made the right structural move twice and then failed to
ask the direction question of one of the four resulting placements.

**A falsifier for round 17, in the same spirit:** fires to REDESIGN if round 17 produces another
finding of the form *"a placement is stated for one branch/direction of the path it sits on"* — that
would be the **third** (26c3 was the first, B1 the second), and it would mean the placements are still
being chosen against function *names* rather than against the *branch set* §3.6.1b demands. The cheap
prophylactic, and the thing I would do before round 17: **write out all four placements × every branch
of the path each sits on, as a table, and give each cell an outcome.** Three of the four have exactly
one branch. One has two, and that is B1.

NOT CONVERGED
