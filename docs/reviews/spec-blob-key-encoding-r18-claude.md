# Round 18 — Claude adversarial review, cloud blob key encoding (backlog #36)

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` **v20**, working tree,
branch `fix/cloud-blob-key-encoding` (`4c8bde0`). Phase 1 — no code written.

**Scope honoured.** §3.1–§3.4 and §3.6 were not re-reviewed. §3.4's `isServableSummaryKey` body was read
once, as the definition needed to decide whether behavior 26d3 is constructible — a question the brief
asks. Nothing was gone looking for there and nothing is filed there.

---

## THE TWO JUDGEMENTS

### 1. The armed falsifier **FIRED** — twice, and one of the two is a live Blocking

The falsifier: *a guarded value with a producer §3.5.1b's rewritten table does not name.*

- **Row 6** trips it textually. `mdKey` is produced by a `??` — two producers — and the row says
  **"One"**, naming the *fallback* arm as though it were the only one. The document cites that exact
  line by number thirty rows earlier (`lib/share/serve.ts:47`, spec `:542`). Consequence is contained
  (Medium), because the guard sits below the `??`.
- **Row 1** trips it consequentially, and this is the Blocking. Row 1 is recorded **BLIND** — *"refusing
  identically regardless of origin is the seam's entire purpose"* — while v20's own round-17 B1 fix
  requires one producer (`reconcileCloudBase` on arm B) to be **let through**. The seam refuses it
  anyway. The round-17 Blocking is therefore **not fixed**, and the fix made the failure more expensive.

### 2. This spec is **NOT** ready to leave Phase 1

Not for polish — for finding 1, which is the round-17 Blocking still open by a different door, with
paid blobs now duplicated at a dead base on every run as a new side effect.

**And the brief's stated consequence of firing is the right one.** Three hand-built versions of
§3.5.1b, each verified row-by-row by two reviewers, each shipped with a missed producer. The table asks
the *right* question now — the operand question is correct, and finding 1 was found by mechanically
obeying it. What does not work is **filling it in by hand**. What is owed is a **script**, not a fourth
table:

> For each row, take the `file:line` the row cites for the guarded value, resolve the defining
> expression, and **fail if that expression contains `?:`, `??`, `||`, a default parameter, a `catch`
> that substitutes, or a `switch` with `default` while the row's producer count says "One"**.

That is syntax, not judgement. It would have caught row 6 in one second, and it satisfies this
project's own standing rule — *before adding a rule here, ask whether it can be a script*
(`docs/dev-process.md`, "Keeping this file short"). A prose table cannot be ratcheted; a script can.

---

## FINDINGS, most severe first

---

## B1 — **Blocking**: on arm B the SEAM refuses the very write round-17 B1's fix lets through. The paid summary is still stranded, and now every run copies it to a dead base first

**Classification:** `mechanism`. **Caused by v20's own fix:** YES.

### The two rules, quoted

The seam rule (`§3.5.1`, spec `:737-738`), and row 1 of the rebuilt table (spec `:1006`):

> **In the Supabase adapter, refuse any patch that sets `summaryMd` or `artifacts.summaryMd.status =
> 'promoted'` to a key failing `isServableSummaryKey`.** Then **the entrance count stops mattering**

> | 1 | **The metadata seam** — `videoDataPayload` | `payload.summaryMd`, `payload.artifacts.summaryMd.key` | **Many, deliberately unenumerated** — every caller of the three write methods | **BLIND.** Refusing identically regardless of origin *is the seam's entire purpose* … |

Round-17 B1's fix (spec `:832-833`), and behavior **26d2** (spec `:1808`):

> ```ts
> if (isServableSummaryKey(`${oldBase}.md`) && !isServableSummaryKey(`${newBase}.md`))
>   return { ok: false, reason: 'unservable-base', key: `${newBase}.md`, origin };
> ```

> | 26d2 | **ARM B — the local row has a serial but NO MD, and the cloud key is ALREADY unservable → the relocation PROCEEDS**, so `reconcileClassA` → `copyToLocal` stays reachable and the paid summary can still hydrate into the vault. |

`reconcileCloudBase` is listed in §3.5.1's own entrance table (spec `:719`) as writing through
`updateVideoFields` (`reconcile-serial.ts:324`) — i.e. **through the seam**. There is no exemption
anywhere in the document.

### Trace — arm B, old base unservable, new base unservable

Preconditions are the ones round-17 B1 itself establishes: `localVideo.serialNumber != null`,
`localVideo.summaryMd == null`, `cloudVideo.summaryMd` unservable and diverged from local's serial.

```
reconcile-serial.ts:183   d = describeDivergence(lv, cv)   → arm B, diverged
                :186      newBase = d.to!                  → cloud key renumbered, still unservable
   [v20 in-memory guard]  isServableSummaryKey(old)=false   → conjunct false → NO refusal, proceed
                :254-278  paidKeysUnder + plan              → MD, model, every dig, digDeeperMd
                :281-290  cloud.blob.copy(...) × N          ← EVERY PAID BLOB IS COPIED
                :293-301  patch = { summaryMd: `${newBase}.md`,
                                    artifacts: { summaryMd: { key: `${newBase}.md`,
                                                              status: 'promoted' } }, … }
                :324      cloud.store.updateVideoFields(...)  ← THE SEAM. Unservable key. REFUSES.
                :325-328  catch → { ok:false, reason:'metadata-failed', cause }
sync-run.ts     :739      !rec.ok
                :754-756  throw `base reconciliation failed for <id>: metadata-failed`
                :812      caught per-video → report.errors → NO writeVideoBaseline
                :771      reconcileClassA          ← NEVER REACHED
                :793      copyToLocal / transferClassA ← NEVER REACHED
```

`:358-361` (cleanup) is never reached either, so the copies are permanent. `copy` returns `already` on
re-runs, so this is not unbounded growth — but it is a full duplicate set of paid artifacts at a base
nothing will ever advertise, on a row that re-fires forever.

### Why this is Blocking

Round-17 B1's stated harm was: *"the refusal's entire effect is to block the paid summary's last
remaining route to the user — **permanently**"*. That harm is **unchanged** by v20. `copyToLocal` is
still never reached, for the same reason (a throw at `:756` above `:771`), only now the throw is
`metadata-failed` instead of `unservable-base`. A paid summary remains unreachable through every
product path, and the operator message no longer even names the cause.

**And it is a regression against v19 on cost.** v19 refused in memory and copied nothing. v20 copies
every paid blob — MD, model, N digs, digDeeperMd — and *then* refuses. That is precisely the outcome
§3.5.1 placement 2 exists to prevent, in its own words (spec `:793-794`):

> so **no blob is copied and nothing is deleted**, rather than relying on the seam to reject after the
> copy.

The document states the failure mode and then implements it. Placement 2 was justified as a *strictly
earlier* form of the seam's refusal; v20 made it **narrower** than the seam, and a guard narrower than
the one it front-runs is not a front-run.

### Behavior 26d2 is unsatisfiable as written

26d2 is an `integration` row. Written against the real `SupabaseMetadataStore` with the seam guard in
place, *"the relocation PROCEEDS"* is false — `updateVideoFields` throws. The row will go red on a
correct implementation of the rest of the design. It is falsifiable (good) and the design fails it.

### Why `mechanism`, not `branch-coverage`

Test: *can a redesign remove it?* **Yes.** One rule — "an unservable key must not become a cloud
advertisement" — is currently stated in two places with **different predicates**, and the design has no
account of which wins. This is the shape memory already records as *two mechanisms for one concern*.
A redesign that gives the rule one home dissolves it.

### Proposed fix — make the conjunct discriminate refuse-vs-**skip**, not refuse-vs-proceed

The relocation's purpose is to keep the cloud's derived-blob addresses in step with local's serial.
When the resulting key cannot be advertised, there is nothing to keep in step. So:

| old base | new base | outcome |
|---|---|---|
| servable | servable | **relocate** (today's normal path) |
| servable | unservable | **refuse** — protect a working advertisement (this is 26d3, and it stays) |
| unservable | servable | **relocate** — a genuine repair; the seam accepts it. *No behavior row covers this cell today* |
| unservable | unservable | **SKIP** — return `{ ok: true, action: 'skipped-unservable' }`. No copy, no seam write, and `reconcileClassA` → `copyToLocal` runs, which is exactly what round-17 B1 wants |

The skip must be **visible, not silent**: push the unrepaired divergence into `report.errors`, the same
shape the corrections-unresolved path already uses at `sync-run.ts:713-716`. A new `ok: true` action is
a closed-union addition, the same mechanical change round-15 M3 already validated for the refusal
variant.

This never asks the seam to accept an unservable key, so **row 1 stays BLIND and stays true** — which
is the design's strongest claim and worth preserving. 26d2 must be rewritten to assert *the relocation
is SKIPPED and hydration proceeds*, and a fourth row added for the unservable→servable repair cell.

---

## M1 — **Medium**: row 6's `mdKey` has TWO producers (a `??`), and the row names the fallback arm as "One"

**Classification:** `branch-coverage`. **Caused by v20's own fix:** YES (the producer column is new in v20).

```ts
// lib/share/serve.ts:44-48 — read to the end of the expression.
const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
  .artifacts?.summaryMd;
if (artifact?.status !== 'promoted') return denied;
const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;   // ← TWO producers
if (!mdKey) return denied;
```

- **Producer A** (taken first): `vid.data.artifacts.summaryMd.key`.
- **Producer B** (fallback): `vid.data.summaryMd` — the *only* one row 6 names.

Row 6 (spec `:1011`) reads:

> | 6 | **The share guard** | `mdKey` from `getShareServeContext` (`lib/share/serve.ts:13`) | **One** — the cloud row's `summaryMd` | BLIND |

The two can genuinely differ, and the repo already documents that: `tests/lib/dig/cloud/resolve-summary-key.test.ts:5` seeds
`{ summaryMd: '0001_old.md', artifacts: { summaryMd: { key: '0001_new.md' } } }`, and
`tests/lib/storage/supabase-metadata-store-summary-ready.test.ts:90-92` seeds the legacy shape —
`artifacts.summaryMd = { status: 'promoted' }` with **no key** and the real key only at top level, which
is producer B being taken in earnest. §4 performs no migration, so that shape persists in prod.

**Why Medium and not Blocking.** §3.4 places the guard *"inside `getShareServeContext`, **before**
`mdKey` is returned"* (spec `:546`) — i.e. **below** the `??`. Both arms are therefore refused
identically and the *verdict* BLIND is correct. What is wrong is the **evidence**: the row asserts
blindness from a producer count of one, and the count is wrong. That is the failure mode round 17 was
supposed to have retired — a confident, verifiable, incomplete answer — recurring in the rebuilt
instrument, on a line this document already cites by number at `:542`.

**Fix.** Row 6: *Producers* → **TWO** (`lib/share/serve.ts:47`) — `artifacts.summaryMd.key`, else the
top-level `summaryMd`; *Blind or dependent* → **BLIND, and structurally so: the guard sits below the
`??`, so it tests whichever arm won.** That sentence is the actual argument, and it is stronger than
the count it replaces.

---

## M2 — **Medium**: round-17 M2 asked for the adopt location to be stated ONCE. v20 stated it **zero** times where it points, and left three statements of the retired site

**Classification:** `stale cross-reference`. **Caused by v20's own fix:** YES (the dangling pointer is new).

§3.5.1 placement 3 now reads (spec `:881-882`):

> 3. **The adopt path is guarded in the CALLER — see §3.5.1b row 4, which is the ONE place this location
>    is stated.**

Row 4 (spec `:1009`) in full:

> | 4 | **The adopt** | `video.summaryMd` of the one-sided video | **TWO**, and here provenance coincides with direction: the sender is local (vault name) or cloud (cloud key), per `presentIsLocal` (`sync-run.ts:620`) | **DEPENDENT** ← round-16 **B1**. Cloud receiver only |

**Row 4 states no location.** v19's row 4 did (`~~copyAdditiveVideo~~ → the caller, sync-run.ts:624-627`);
the v20 rewrite replaced that column with *Value guarded*, and the location went with it. The pointer
now resolves to nothing.

Meanwhile the retired site survives in three places, two of them affirmative present-tense directives:

| Line | Text | Status |
|---|---|---|
| `:623` | "The adopt refusal (`sync-run.ts:236-238`, **above `ensureReceiverSlot`** …)" | stale |
| `:667-669` | "Move the adopt guard **above** `ensureReceiverSlot`, next to the existing WB-H1 check at `sync-run.ts:236-238` … **That part stands.**" | stale, and reaffirmed |
| `:1043` | §3.5.2 row 1, *Where the refusal lands*: "**the adopt guard**, above `ensureReceiverSlot` (`sync-run.ts:236-238`)" | stale, in a live per-branch table |

The correct location — **above `sync-run.ts:626`** — appears at `:959-960` and in behavior 26f
(`:1801`), so it is stated twice and pointed at once, at a row that does not have it.

`:667-669` is the sharp one: §3.5.1 at `:944` says *"'Apply the guard only when the receiver is the
cloud' is **not implementable** at `sync-run.ts:236-238` as the function stands"*. The document
instructs the implementer to put the guard at a site it elsewhere calls unimplementable, and appends
*"That part stands."* This bullet has now been corrected at rounds 13, 15 and 17 and is wrong again.

**Fix.** Put the location in **row 4's Placement cell** (`**The adopt** — the caller, above
`sync-run.ts:626``) so the pointer resolves, and make `:623`, `:667-669` and `:1043` all say
"see §3.5.1b row 4" with no line number of their own. `:667-669` sits inside a round-13 historical box,
so it should be marked as the round-13 decision **superseded by round-16 B1 / round-17 M1**, not left
reading as current.

---

## L1 — **Low**: `origin`'s predicate is not the ternary's predicate. Two copies of one condition, and they disagree on the empty string

**Classification:** `branch-coverage`. **Caused by v20's own fix:** YES.

The arm selector (`reconcile-serial.ts:152-154`) tests **truthiness**:

```ts
const to = localVideo.summaryMd
  ? baseOf(localVideo.summaryMd)                                        // arm A: a VAULT filename
  : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber)); // arm B: the CLOUD key, renumbered
```

The fix's `origin` (spec `:842`) tests **nullity**: *"`origin` is `localVideo.summaryMd != null ?
'vault-filename' : 'cloud-key'`"*.

`Video.summaryMd` is `z.string().nullable()` (`types/index.ts:56`), so `''` is a legal value. On `''`
the ternary takes **arm B** (falsy) while `origin` reports **`'vault-filename'`** (`'' != null`) — the
message would tell the operator to rename a vault file whose name is the empty string, for a value that
came from the cloud key. No producer emits `''` today, which is why this is Low and not higher.

**Fix — and it removes the predicate rather than repairing it.** The arm is known *inside*
`describeDivergence`, which is the only place it is decided. Return it:

```ts
{ diverged: boolean; from?: string; to?: string; origin?: 'vault-filename' | 'cloud-key' }
```

`reconcileCloudBase` then reads `d.origin` alongside `d.to`. One predicate, one place, and the two can
no longer drift. `describeDivergence` has three call sites (`reconcile-serial.ts:183`,
`sync-run.ts:712`, `sync-run.ts:735`); the added field is optional to all three.

---

## L2 — **Low**: the fix gave the guard a SECOND operand, `oldBase`, and §3.5.1b names it nowhere

**Classification:** `branch-coverage`. **Caused by v20's own fix:** YES.

The rule the table states about itself (spec `:1021-1023`):

> A placement is not specified until you have named **the value it guards and every producer of that
> value**

Row 3's *Value guarded* column names exactly one value: **`newBase`**. The guard v20 introduces has
**two** operands:

```ts
if (isServableSummaryKey(`${oldBase}.md`) && !isServableSummaryKey(`${newBase}.md`))
```

`oldBase = d.from! = baseOf(cloudVideo.summaryMd)` (`reconcile-serial.ts:151`, `:185`) — one producer,
uniform, so nothing is *wrong* downstream. But the instrument built one round ago to enumerate guarded
values omits an operand of the guard that motivated it, in the same version. Filed because the table's
value is that it is complete; the moment it is selectively complete it returns the same confident,
useless answer §3.5.1b's own closing note describes.

**Fix.** Row 3 *Value guarded* → **`newBase` (`:186`) and `oldBase` (`:185`)**; *Producers* → the two
arms of `:152-154` for `newBase`, **one** (`baseOf(cloudVideo.summaryMd)`) for `oldBase`.

---

## L3 — **Low**: the "outside the seam" paragraph cites a record-literal field instead of the write call, and names one pipeline write where there are two

**Classification:** `stale cross-reference`. **Caused by v20's own fix:** NO (pre-existing; L5's new box sits directly above it).

Spec `:730-735`:

> the **local** pipeline (`pipeline.ts:265`) is not a cloud advertisement … *(Round-15 L3: `:157` is the
> `summaryMd` field of the record literal, not the persist call. The claim was right, the line was not.)*

`pipeline.ts:265` is `summaryMd: \`${baseName}.md\`` — **the record-literal field**. The write is
`await store.upsertVideo(principal, video)` at **`:284`**. That is verbatim the defect the same sentence
corrects for `summary-handler.ts:157`, committed one clause later about a different file.

There is also a **second** pipeline write of a full record carrying `summaryMd`:
`recoverOrphanedVideos` at `pipeline.ts:151-153` — `reconstructVideo(...)` then
`store.upsertVideo(principal, video)`. §3.5's own reachability table already names
`recoverOrphanedVideos` as a *producer* of unservable keys (spec `:596`); the enumeration paragraph
does not name it as a *writer*.

Both are harmless for the reason L5 already gives, and I verified it rather than taking it: `pipeline`
resolves its store through `getStorageBundle()` with **no client** (`pipeline.ts:131`, `:186`), which
throws under `STORAGE_BACKEND=supabase` (`resolve.ts:56`).

**Fix.** Cite `pipeline.ts:284` and `:153` — the calls — and say "two local writes", or drop the line
numbers entirely and keep the structural argument, which is the part that is load-bearing.

---

# WHAT I CHECKED AND FOUND SOUND — the brief's other questions, answered

Recorded because a review that only lists defects gives no information about the rest.

### The rollout table's `41` / `~20` — **RE-COUNTED, EXACT**

Enumerated over the whole repo with `python3` + `os.walk` + `re` (never grep), counting `writeModelEnvelope`
and `writeModelEnvelopeWithin` **call sites** and excluding imports, comments and raw-byte seeds:

| Location | Calls (counted) | Spec | Literals (counted) | Spec |
|---|---|---|---|---|
| `generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464` | 3 | 3 | 3 | 3 |
| `tests/lib/html-doc/rerender.test.ts` (`:77,91,117,124,130,137,148,162,180,199,208,210,222,223`) | 14 | 14 | 2 | 2 |
| `tests/lib/html-doc/model-store.test.ts` (`:36,43,79,86,117,132,142,149`) | 8 | 8 | 1 | 1 |
| `tests/lib/model-store-cloud.test.ts` (`:46,55,56`) | 3 | 3 | 1 | 1 |
| `tests/integration/serve-doc-materialize.test.ts` (`:144,201,231,247,267`) | 5 | 5 | 5 | 5 |
| `tests/integration/share-route.test.ts` (`:82,192,223,285`) | 4 | 4 | 4 | 4 |
| `tests/integration/html-download.test.ts` (`:257,282`) | 2 | 2 | 2 | 2 |
| `tests/integration/pdf-cloud.test.ts` (`:266`) | 1 | 1 | 1 | 1 |
| `tests/e2e/cloud.setup.ts` (`:114`) | 1 | 1 | 1 | 1 |
| **total** | **41** | **41** ✅ | **20** | **~20** ✅ |

No defect. Two nuances, neither wrong: `serve-doc.ts:174` and four of the `model-store.test.ts` calls
are `writeModelEnvelopeWithin`, correctly counted together since both reach `serialize` (`model-store.ts:52`, `:73`);
`model-store.test.ts:149` passes `as never` so `tsc` will not force it, which is why "1 literal" for
that file is defensible.

### Behavior 26f's rewritten observable — **it now discriminates**

```ts
// sync-run.ts:65-68 — readMdBody
if (!video.summaryMd) return null;
const buf = await blob.get(p, video.summaryMd);   // ← the observable
```

The 26f scenario has an unservable `summaryMd` (that is what triggers the refusal), so `readMdBody` at
`sync-run.ts:626` **does** call `get` on the sender's blob store. Correct placement (above `:626`)
refuses before it; the mutant (`:236-238`, inside `copyAdditiveVideo`) refuses after it. The two
placements differ on exactly this call. Nothing else touches the sender's blob store for that key on
the path from `:610` to `:626` — `enumerateVideoIds` and `readVideo` are `readIndex` only. `from.blob`
is a `Side` field supplied through `SyncDeps`, so it is a constructible/spyable object in an
integration harness. **Observable, and discriminating.** v19's `ensureReceiverSlot` observable was
correctly diagnosed as non-discriminating.

### Behavior 26d3 — **constructible, MEASURED not asserted**

I transcribed §3.4's `isServableSummaryKey` and `lib/serial-filename.ts`'s `applySerial` verbatim and
ran them on Node v22.14.0 (`isWellFormed` and `\p{Bidi_Control}` need v22):

```
no prefix -> 003_ (+4)      cloudKey len=131 servable=true   newKey len=135 servable=false   guard fires = true
999_ -> 1000_ (+1)          cloudKey len=131 servable=true   newKey len=132 servable=false   guard fires = true
short key, no length pressure  cloudKey len=12 servable=true newKey len=12  servable=true    guard fires = false
```

Both mechanisms the spec names — *"widening the prefix or adding one where the key had none"* — reach
the cell. 26d3 is a real, writable row, not a fourth unfalsifiable one. (Script in the session
scratchpad; nothing was written to the repo.)

### Behavior 18j8 — **writable**

`rewriteEnvelopeSourceMd` (`lib/serial-provenance.ts:14-18`) is pure: `JSON.parse` → set `sourceMd` →
`JSON.stringify`. A unit test passes a JSON string carrying `videoId` and asserts it survives; the
paired mutation (reconstruct only known fields) turns it red. Called at `serial-migrate-exec.ts:141`,
as stated. *(Nit, not filed: the spec cites `serial-provenance.ts:13-17`; `:13` is the doc comment and
the function body ends at `:18`.)*

### Round-17 L5's fourth caller — **the structural argument holds, verified**

`serial-migrate-exec.ts:125` writes `fieldUpdates[op.field] = op.to` where `op.field` can be
`'summaryMd'` (`:126`), and calls `store.updateVideoFields` at `:146`. `runPhaseB` resolves its store
through `getStorageBundle()` with no client (`:70`), which throws under `STORAGE_BACKEND=supabase`
(`resolve.ts:56`). Harmless for exactly the stated reason. The enumeration is not *complete* — see L3 —
but the two additions are local by the same construction.

### Rows 2, 4, 5, 7 — **derived independently, all correct**

- **Row 2** (mint): `baseName = \`${padSerial(serial)}_${slugify(payload.title)}\`` (`summary-handler.ts:96`).
  One producer, no fallback. BLIND vacuously. ✅
- **Row 4** (adopt): `present = (lv ?? cv)!` (`sync-run.ts:619`) — the `??` **is** the two producers the
  row names, and they coincide with direction via `presentIsLocal` (`:620`). DEPENDENT, cloud receiver
  only. ✅
- **Row 5** (`transferClassA`): `key = winnerVideo.summaryMd` (`:379`); `winnerVideo` is `lv` at `:782`
  or `cv` at `:793`, and those are the only two call sites. TWO, cloud loser only. ✅
- **Row 7** (`serialize`): production writers of a model envelope are exactly three —
  `generate.ts:50`, `serve-doc.ts:174`, `sync-run.ts:464` (enumerated over the repo). `runHtmlDoc(videoId: string, …)`
  takes the id as its first parameter, so the local path can satisfy the requirement. BLIND on purpose. ✅

### Row 1's BLIND, on the question the brief asked

Every production caller of the three write methods was enumerated. Only the sync entrances, the
(zero-caller) `writeArtifact`, and the structurally-local `pipeline` / `serial-migrate-exec` can carry
`summaryMd` or `artifacts.summaryMd.key` at all; `regenerate`, `review`, `backfill`, `archive`,
`html-doc/ensure`, `html-doc/generate` and `dig-section` carry none of them.
`updateVideoAnnotations` bypasses `stripComputed` entirely but its server-side allowlist is
`{personalScore, personalNote, corrections, archived}`. So the *"many, deliberately unenumerated"*
half of row 1 is accurate. **It is the BLIND half that fails, and only for one producer** — arm B of
`reconcileCloudBase`, per finding B1.

---

## Classification summary

| # | Severity | Classification | Caused by v20's own fixes? |
|---|---|---|---|
| B1 | Blocking | `mechanism` | **yes** |
| M1 | Medium | `branch-coverage` | **yes** |
| M2 | Medium | `stale cross-reference` | **yes** |
| L1 | Low | `branch-coverage` | **yes** |
| L2 | Low | `branch-coverage` | **yes** |
| L3 | Low | `stale cross-reference` | no |

**1 Blocking, 0 High, 2 Medium, 3 Low. Five of six were introduced by v20's own fixes** — which is
itself the round-9 M5 escalation signal, and is why the "different instrument, not a fourth table"
conclusion above is the honest one rather than a rhetorical flourish.

CODEX GAP: none — this is the Claude half of a dual round; the Codex half is dispatched separately.

NOT CONVERGED
