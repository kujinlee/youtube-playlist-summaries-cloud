# Round 14 — Claude adversarial review of spec **v16** (backlog #36)

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` in the working tree
(v16, commit `87e2186`), branch `fix/cloud-blob-key-encoding`. Phase 1 — no code written.

**Verdict: NOT CONVERGED.** 1 Blocking, 1 High, 1 Medium, 3 Low.

| Classification | Findings |
|---|---|
| **mechanism** (a redesign removes it) | **B1** |
| **branch-coverage** (the rule governs a branch it does not own, and does not state it) | **H1**, **M1**, L1, L3 |
| **stale cross-reference** | L2 |
| **caused by v16's own fixes** | B1 (§3.5), H1 (§3.6.4), M1 (§3.5) |

**Counter reading, stated precisely because the brief asks for it.** v16's fixes produced a mechanism
defect (**B1**) — but it is in **§3.5's enforcement placement**, not in §3.6's write protocol. §3.6
produced one fix-induced finding (**H1**) and it is **branch-coverage**: a writer of the new credential
was not enumerated; the credential itself is sound and survives `remap`. So §3.6.1b's diagnosis is
confirmed a second time and the §3.6 override stands; the escalation that fires this round is
**§3.5's "call `isServableSummaryKey` at each call site"**, which has now missed an entrance in three
consecutive versions. The redesign it asks for is small and local (one enforcement point) and does not
reopen §3.6.

Everything below was read from the current head. `LEAD` marks anything not read.

---

## B1 — Blocking. `reconcileCloudBase` is a THIRD route to the same durable state, and it DELETES the servable copy on the way

**Classification: mechanism. Caused by v16's own fix** (26c declares the entrance set closed at two).

Round-13 H2's lesson was *"guarding only the one we were thinking about"*. v16 guards two entrances —
the adopt path and `transferClassA` — and behavior 26c calls `transferClassA` *"the **second** entrance
to the same durable state"*. §2.5 of this same document enumerates **four** write entrances, and the
fourth one writes the row exactly like the other two, with no guard on any version of this design:

```ts
// lib/cloud-sync/reconcile-serial.ts:293-296   (the metadata phase of a base relocation)
const patch: Record<string, unknown> = {
  serialNumber: localVideo.serialNumber,
  summaryMd: `${newBase}.md`,
  artifacts: { summaryMd: { key: `${newBase}.md`, status: 'promoted' } },
```

and `newBase` is **the vault filename, verbatim**:

```ts
// lib/cloud-sync/reconcile-serial.ts:152-154   (describeDivergence)
const to = localVideo.summaryMd
  ? baseOf(localVideo.summaryMd)
  : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber));
```

The only key validation on that path is `assertLogicalKey` (`:267-268`), which per §3.4's own table
rejects a leading `/`, a `..` segment and `\0` — nothing about length, C0/C1, bidi, or the `.md`
suffix. `reconcileCloudBase` runs at `sync-run.ts:729-757`, i.e. **before** the Class-A transfer where
v16 puts its new guard (`:780-793`).

**The caller that reaches it — and it is the same producer that justifies behavior 26.** §3.5's own
reachability table names it: *"a hand-placed or externally-renamed vault file"*.

1. Video V is minted in the cloud (`summary-handler.ts:96`) as `003_ok-title.md` — servable, served,
   paid for.
2. The user drops (or an external tool writes) a vault `.md` for V with an unservable name — over 131
   code points, a C1 character, an NFD name whose code-point count exceeds the bound. V is not yet in
   the local index, so `recoverOrphanedVideos` adopts it and sets `summaryMd = file` verbatim
   (`pipeline.ts:104`, `:151-153`) with the serial parsed from the filename (`:106-107`).
3. Sync now sees V on **both** sides. `copyAdditiveVideo` is never called — `sync-run.ts:618`'s
   `if (!lv || !cv)` is false — **so the adopt guard behavior 26 places at the top of that function is
   bypassed entirely.**
4. `reconcileCloudBase` finds a divergence, copies every paid blob to the unservable base
   (`:281-290`), writes the row above, verifies it (`:345-353`), and then **deletes the sources**
   (`:358-361`).

End state: the paid summary is unreachable through every cloud route — serve, download and share all
run `isServableSummaryKey` and 409 — and the servable copy at the old base has been deleted. There is
no in-product repair: a re-serve cannot run, because the serve path refuses before it reserves.

**Severity, stated honestly.** The bytes are not destroyed — they exist at an unservable cloud address
and in the vault — and an operator can recover by renaming the vault file and re-syncing. It is also
**not a regression**: the same relocation happens today. It is graded Blocking on the brief's stated
calibration (*"a paid artifact … unreachable is Blocking"*) and because v16's central claim — §3.5's
*"the mint and adopt call sites exist so that class is refused **before anything is durable or paid**"*
— is false on a path §2.5 already lists. The adjudicator has what they need to grade it lower.

**Why this is mechanism and not another missing call site.** §2.5 already wrote the rule this violates:

> *"**A rule that must be restated per writer will keep churning in a codebase that keeps growing
> writers.**"*

That sentence retired the branded `CloudSummaryKey` and the homoglyph denylist. `isServableSummaryKey`
is now on its **third** enumeration (v10: mint + adopt; v16: + `transferClassA`; this round: +
`reconcileCloudBase`), and §3.4 applied the correct fix to the *share* path one section earlier —
*"put the call inside `getShareServeContext` … so both derivations are covered **by construction**
rather than by enumeration — this document has now been wrong about a count eight times."*

**Proposed fix — one enforcement point, and it also resolves M1.** Every sync-side entrance writes the
advertisement through a `MetadataStore` method:

| Entrance | Write |
|---|---|
| `copyAdditiveVideo` | `to.upsertVideo(toP, sanitized)` — `sync-run.ts:286` |
| `transferClassA` | `loser.store.updateVideoFields(...)` — `sync-run.ts:432` |
| `reconcileCloudBase` | `cloud.store.updateVideoFields(...)` — `reconcile-serial.ts:324` |

Refuse a patch that sets `summaryMd` / `artifacts.summaryMd.status = 'promoted'` to a key failing
`isServableSummaryKey` **in the Supabase adapter**, and the entrance count stops mattering. The mint
keeps its own call site regardless — it must sit between `reserveVideoSlot` and the Gemini call for the
money reason §3.5 already gives (`summary-handler.ts:95`, `:101`). Putting it on the *cloud* adapter
only is also the correct answer to M1 below: §3.4's whole argument is that the local path never needed
this guard. `reconcileCloudBase` should additionally refuse **in memory, before the copy phase**,
alongside its existing `target-occupied` / `unsupported-artifacts` refusals (`:197`, `:214`) — that
function's own stated pattern, *"the smallest correct behaviour: it cannot half-move anything"* — so no
blob is copied and nothing is deleted.

**Behaviors owed:** a cloud row whose base is relocated onto an unservable vault name is **refused**,
no blob is copied, and the old base is **intact**; plus a mutation *"remove the relocation guard"* →
red on it. Behavior 26c's wording (*"the second entrance"*) must stop asserting a count.

---

## H1 — High. The new `videoId` credential is never written by the LOCAL envelope writer, and the sync ship ERASES it from cloud envelopes that have one

**Classification: branch-coverage. Caused by v16's own fix** — the credential is new in v16.

§3.6.4 and the credential design pass both state the writer set as two:

> *"**Both writers verified:** `serve-doc.ts:174` … `sync-run.ts:464` …"*
> *"**Self-healing:** any re-serve rewrites the envelope through `serve-doc.ts:174` with `videoId`, so
> the 7 legacy prod envelopes close without a migration."*

**There is a third writer, and it is the one that produces every envelope in the vault:**

```ts
// lib/html-doc/generate.ts:50-60   (runHtmlDoc — the LOCAL generate path)
await writeModelEnvelope(principal, base, {
  sourceMd: video.summaryMd,
  generatedAt: new Date().toISOString(),
  sourceSections: parsed.sections.map((s) => s.title),
  generatorVersion: GENERATOR_VERSION,
  model,
  sourceMdHash: mdHash(md),
}, resolvedBlob);
```

`videoId` is `runHtmlDoc`'s **first parameter** (`generate.ts:11-12`), so the omission is one line — but
as written, v16 leaves it out. Its callers are the real local ingest path (`pipeline.ts:297`) and
`ensure.ts:53`, `:56`, `:60`. `rerender.ts` only *reads* the envelope (`:43`) and never rewrites it,
so nothing else on the local side can heal it.

**Two consequences, both undermining the section's own claims.**

1. **Local envelopes never carry the credential — not "legacy", permanently.** The `copyToLocal`
   direction is exactly where `companionTransfer` runs its destructive
   `loser.blob.delete(models/${base}.json)` (`sync-run.ts:475`) against a **paid local Gemini
   transform** — the cost `companion.ts:34-35` names in its own docstring. The rule's legacy branch is
   *"no `videoId` ⇒ proceed"*, so the guard designed to protect that artifact is **inert in that
   direction forever**. §3.6.4's third residual is closed in one direction, not closed.

2. **The ship erases the credential.** `decideCompanion` returns `{ kind: 'ship', envelope: senderMatch }`
   with the **sender's** envelope object (`companion.ts:118`, `:125`), and `companionTransfer` writes it
   verbatim (`sync-run.ts:464`). On `copyToCloud` the sender is the vault, so a cloud envelope that
   *did* carry `videoId` (written by `serve-doc.ts:174`) is overwritten by one that does not. §3.6.4's
   *"`sync-run.ts:464` ships `decision.envelope` wholesale, so it propagates **correct by
   construction**"* is a **fourth universal** in a document that has had three falsified: it is correct
   by construction only if every producer stamps the field.

**Fix:** add `videoId` at `generate.ts:50` (available at `:12`); widen behavior 18j5 to *"every envelope
**writer** stamps `videoId`"* and add the local half to it — `tests/lib/cloud-sync/model-writer-hash.test.ts`
already drives the real `runHtmlDoc` and is the natural home; add the mutation *"stop writing `videoId`
in `runHtmlDoc`"* → red. State in §3.6.4 that a ship from a sender with no `videoId` **removes** the
receiver's, or require the ship to preserve a receiver `videoId` it matched.

---

## M1 — Medium. Both newly-guarded functions run in BOTH directions, and the spec scopes neither

**Classification: branch-coverage. Partly caused by v16's own fix** (the `transferClassA` guard is new).

`copyAdditiveVideo` is called with `to` = either side (`sync-run.ts:624-627`) and `transferClassA` is
called as `copyToCloud` **and** `copyToLocal` (`:782`, `:793`). Behaviors 26 and 26c name the functions
and never the receiver, so as written the refusal also fires when the **vault** is the receiver.

That contradicts §3.4's own load-bearing argument — *"Why local was always fine … the identical
derived-key construction runs on the local path … with **no allowlist**, full of Korean filenames, for
the app's entire life"* — and it converts a cloud-serve requirement into a vault-availability refusal:
a cloud row already carrying an unservable key would never be replicated into the vault, per-video
error on every run, forever, with no automated repair. The vault is the one place that key works.

Reachability is limited (it needs a cloud row that already carries such a key, which after the mint and
adopt guards means a pre-existing row), which is why this is Medium and not High. **Fix:** state the
rule **per direction** — the guard governs the **cloud receiver** only — which falls out for free if B1's
fix puts the assertion on the Supabase adapter.

---

## L1 — Low. The bidi class rejects 9 of the 12 Bidi_Control code points; three pass

**Classification: branch-coverage (an enumerated class that is incomplete).** Not fix-induced — the
class dates to v9.

§3.4's predicate rejects `U+202A`–`U+202E` and `U+2066`–`U+2069`. MEASURED on Node 22, character
classes constructed from code points so no literal bidi character appears in the probe
(`/tmp/bidi-probe2.mjs`):

```
Bidi_Control total: 12 | missed by the spec class: U+061C U+200E U+200F
```

`U+200E`/`U+200F` (LRM/RLM) and `U+061C` (ALM) reorder rendering in a mixed-direction name, which is
the stated reason the class exists (*"it renders as a different filename than it is, and this key
becomes a **vault filename** on the cloud→local path"*). They are not caught by the C0/C1 class either
(verified: `false` for `U+061C`). The producer is the adopt path, not the mint — MEASURED,
`slugify('ab' + String.fromCharCode(0x200f) + 'cd') === 'ab-cd'`, since `[^\p{L}\p{N}]+` replaces `Cf`
(written as an escape, never a literal — the defect this spec has shipped four times).

**Fix:** `/\p{Bidi_Control}/u` — a Unicode-derived property, valid in V8, exactly 12 code points. This
is the same move §3.4 already made for homoglyphs (*"a hand-typed list cannot be complete; NFKC closes
that class"*), applied to the one class in the predicate still hand-typed. ZWJ and variation selectors
are unaffected: neither is `Bidi_Control`.

---

## L2 — Low. Three stale cross-references left by v16's own edits

**Classification: stale cross-reference.** Round 13 found four; the remedy is the grep, not a redesign.

| Line | Says | Superseded by |
|---|---|---|
| **513** | *"The adopt refusal (`sync-run.ts:263`) is per-video, caught, and advances no baseline, so it re-fires on every subsequent run, forever"* | the H2 box **16 lines below** (`:529-561`), which moves the guard above `ensureReceiverSlot` (≈`:236`) and says both halves of this sentence were false at `:263`. The claim becomes true **after** the move; the location does not |
| **1254** (§7) | *"**v10** adds the mint and adopt call sites"* | v16 moved the adopt site and added a third at `transferClassA` |
| **1156** (26c) | *"the **second** entrance to the same durable state"* | §2.5's four entrances — see **B1** |

---

## L3 — Low. §3.6.4's "Closes … in full" overstates what the credential can be asked

`readModelSide` (`sync-run.ts:489-493`) turns an unreadable envelope into `unknown` on Supabase
(`provesAbsence === false`), and `decideCompanion` ships on `unknown` (`companion.ts:125`). So on a
cloud receiver the ownership question **cannot be asked at all** whenever the read fails — the common
transient case — and the ship proceeds. Combined with the legacy branch and H1, the credential's
coverage is: *cloud receiver, envelope readable, envelope written by `serve-doc`*.

This is today's behaviour and no regression; the defect is that §5's *"Closes: round-13 H1 in full"* and
the third residual's framing do not say it. **Fix:** extend the *"Does NOT close"* paragraph — which
already handles the addressing half honestly — with the two branches where the credential is
unavailable rather than negative.

---

## What I attacked and found holding

Recorded so the trail shows where the effort went, per the brief's *"the design holds is a real answer"*.

- **The credential is NOT stale by construction.** `remap` re-addresses the envelope
  (`reconcile-serial.ts:118`: `MODEL_KEY(oldBase) → MODEL_KEY(newBase)`) and `copy` moves bytes; nothing
  on that path rewrites envelope contents, so an `videoId` that is present survives relocation, `copyBlob`
  and re-serve unchanged. This is the property `sourceMd` lacked and the replacement genuinely has it.
- **The moved adopt guard works as claimed.** `ensureReceiverSlot`'s first act is a durable
  `setPlaylistMeta` (`sync-run.ts:185`) before `claimVideoSlot` (`:214`), so above it is the only correct
  placement, and the first statement of `copyAdditiveVideo` (`:236`) is before everything durable. On a
  throw the caller's `catch` at `:812` skips `writeVideoBaseline` at `:634`, so run 2 re-reads
  `manifest.videos[id]` as undefined, `!lv || !cv` is still true, and the refusal re-fires. **Behavior
  26b is writable** — `runSync` is callable repeatedly (`tests/integration/cloud-sync/sync-run.int.test.ts`
  calls it 3×, `additive-serial-coherence.test.ts` 15×), so it is falsifiable, not decorative. It is B1's
  route, not run 2, that gets around the guard.
- **The refusal-never-throws rule is right and load-bearing.** `companionTransfer`'s error return is
  caught by `sync-run.ts:805` and the baseline still advances at `:811`; a throw would hit `:812` and
  make it sticky exactly as §3.6.4's warning box says.
- **§3.4's predicate.** Code-point counting via `[...key]`, `slice(0, -3)` on an ASCII suffix, the
  name-not-the-glued-key fold, and `isWellFormed` (present on Node 22, absent on the Node 20 on PATH —
  worth one line in the implementation plan, not a finding) all check out.

---

CONVERGED / NOT CONVERGED →

NOT CONVERGED
