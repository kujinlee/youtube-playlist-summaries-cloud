# Round 13 — Claude adversarial review of spec **v15** (backlog #36)

Subject: `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` in the working tree
(v15, commit `c86fab9`), branch `fix/cloud-blob-key-encoding`. Phase 1 — no code written.

**Result: 2 High, 3 Medium, 3 Low. NOT CONVERGED.**

| | mechanism | branch-coverage | neither (stale cross-reference) |
|---|---|---|---|
| **caused by a §3.6 fix** | H1 | M2 | M1 |
| not fix-induced | H2 | M3 | — |

**The §3.6 escalation falsifier FIRED** — on H1, by the letter of its own wording (*"a credential is
stale"*). §"Adjudication" below argues what is actually owed, because a mechanical whole-§3.6 redesign
would be poor value and the finding does not touch R1–R4.

Premise tags follow `review-method.md`. Everything below labelled **MEASURED** was run this round, on
this checkout, against a temp dir under `/tmp` and/or Node v22.14.0; every object created was removed.
No probe touched Supabase (nothing here needed it — the two live questions were filesystem and
codepoint questions). No tracked file was modified.

---

## H1 — Blocking-adjacent: `sourceMd` is **stale by construction** after a cloud base relocation, so §3.6.4's new required credential refuses the ship it exists to permit — and the refusal is sticky and costs money

`mechanism` · `caused by a §3.6 fix` (the credential was adopted in v12 as the fix for round-11 M1;
v15 restated it per outcome) · **this is the finding that fires the falsifier**

**The rule (v15, §3.6.4, spec:964):**

> | **envelope present** (ship-overwrite, and every `delete`) | **require** `canonicallyEqualName(envelope.sourceMd, base + '.md')`; refuse otherwise | the two destructive outcomes; the bytes name their own owner |

**The credential does not track the address on the cloud path.** `reconcileCloudBase` relocates every
paid artifact from an old base to a new one by **byte copy**, and the model envelope is one of them
(`reconcile-serial.ts:98`, `:118`):

```ts
// reconcile-serial.ts:98  (paidKeysUnder)
const keys = [`${base}.md`, MODEL_KEY(base)];
// reconcile-serial.ts:118 (remap)
if (key === MODEL_KEY(oldBase)) return MODEL_KEY(newBase);
```

```ts
// reconcile-serial.ts:~328 — the copy loop
const res = await cloud.blob.copy(cloud.p, from, to);
```

`copy` delegates to `copyBlob`, which reproduces bytes (`blob-store.ts:156`). **MEASURED (grep over
the file): `reconcile-serial.ts` contains zero occurrences of `sourceMd` and does not import
`lib/serial-provenance.ts`.** The only importer of `rewriteEnvelopeSourceMd` in the repo is
`lib/serial-migrate-exec.ts` — the **local** Phase-B migration. So:

- **Local** relocation rewrites `sourceMd` (`serial-provenance.ts:16`, asserted at
  `tests/lib/serial-migrate-exec.test.ts:201` — *"rewritten to new md basename"*).
- **Cloud** relocation does not. The relocated envelope at `models/<newBase>.json` keeps
  `sourceMd: "<oldBase>.md"`, permanently, until someone pays for a re-serve
  (`serve-doc.ts:174-182` is the only writer that refreshes it).

**The failure scenario, every link quoted:**

1. Serials diverge for video X. `reconcileCloudBase` returns `relocated` (`sync-run.ts:758`); the
   cloud row is patched to `summaryMd: ${newBase}.md` (`reconcile-serial.ts:~341`) and
   `models/<newBase>.json` now holds the old envelope bytes.
2. `cv` is re-read (`sync-run.ts:765`), Class A runs, `decision.action === 'copyToCloud'`, and
   `transferClassA` commits the local body to the cloud (`sync-run.ts:782`).
3. `companionTransfer` runs (`sync-run.ts:801`) with `base = winnerVideo.summaryMd.replace(/\.md$/, '')`
   = `newBase` (`sync-run.ts:448`).
4. `readModelSide(loser = cloud, base = newBase)` reads `models/<newBase>.json` → parses →
   `kind: 'envelope'` (`sync-run.ts:489-493`).
5. `decideCompanion` → `ship` (sender matches the winner hash, receiver does not — `companion.ts:125`).
6. **v15's rule then requires `canonicallyEqualName("<oldBase>.md", "<newBase>.md")` → false → refuse.**

**What that costs.** The ship was correct — the sender's model *is* built from the body that just
became authoritative. Refusing it leaves the cloud holding a model built from the pre-relocation body,
and the refusal is **sticky** by the mechanism v15 itself names one paragraph earlier: the Class-A body
has landed, so the next run's `reconcileClassA` returns `'skip'` and the companion step is gated on
`decision.action !== 'skip'` (`sync-run.ts:800`) — it never runs again. The serve path's drift guard
compares section titles and `generatorVersion`, never `sourceMdHash` (`companion.ts:41-46`), so a
prose-only change is **served as fresh forever**; and where the drift guard *does* fire, recovery is an
owner re-serve, which reserves and charges (`serve-doc.ts:118-182`).

The `delete` branch inherits the same defect in the other direction: a receiver model that is
`provablyStale` (`companion.ts:151-153`) but relocated is now un-deletable.

**This is a regression, not a restatement.** Today `companionTransfer` ships unconditionally and the
receiver gets the right model. v15's fix converts a correct write into a permanent refusal. It is the
same failure v15's own note describes for v14's per-call rule — *"A fix that costs money in the common
case, introduced by a fix"* (spec:972) — re-entering through a different door **in the fix that closed
it**.

**Why `mechanism` and not `branch-coverage`.** The rule is fully stated for this branch; nothing is
unenumerated. What fails is the credential: `sourceMd` is a *name recorded at generation time* and the
system has a writer that moves the object without updating it. `review-method.md:62` lists *"the
credential is stale"* as a mechanism symptom, and §3.6.3 of this very spec declined Codex's
`lookupStoredKey` on exactly this ground — *"it wraps a credential that §3.6.0 measures to be stale by
construction."* The same sentence now applies to `sourceMd`.

**Proposed fix (local, and the reason a whole-§3.6 redesign is not owed).** Either:

- **(a)** make the credential sound — have `reconcileCloudBase` rewrite the envelope's `sourceMd` when
  it remaps `MODEL_KEY`, which is what `serial-migrate-exec.ts` already does on the local side. One
  call to `rewriteEnvelopeSourceMd` inside the copy loop, plus a behavior asserting it; or
- **(b)** accept `canonicallyEqualName(envelope.sourceMd, base + '.md')` **or** `sourceMdHash` equal to
  the receiver's own current body — i.e. treat a hash match as an ownership proof, which is the
  credential §3.6.4 credential-1 already establishes is transitively an ownership test.

(a) is preferable: it restores the invariant the rule assumes rather than adding a second predicate.
Either way §3.6 needs a stated invariant — *"every writer that moves `models/<base>.json` must rewrite
`sourceMd`"* — and `remap` (`reconcile-serial.ts:117-135`), which already fails closed on unrecognised
shapes, is the natural place to enforce it.

---

## H2 — §3.5's adopt guard is placed **after** a durable write, so "nothing is durable yet" is false and the refusal is bypassed on the very next run

`mechanism` (wrong enforcement point) · **not** fix-induced by v15 (the call sites came in v10) ·
**§3.5, not §3.6 — this one does not bear on the escalation counter**

**The claim (spec:518-521, :507-509):**

> Call `isServableSummaryKey` at the mint (`summary-handler.ts:96`) and at the adopt
> (`sync-run.ts:263`, **before** the blob write), **where a refusal costs nothing because nothing is
> durable yet.**
> …The adopt refusal (`sync-run.ts:263`) is per-video, caught, and **advances no baseline**, so it
> **re-fires on every subsequent run, forever**, until a human renames the vault file.

**Both halves are false, and the function says so twelve lines above the chosen line.** `:263` sits
inside `copyAdditiveVideo`, and `ensureReceiverSlot` has already run at `:240`:

```
// sync-run.ts:240
const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
```

`ensureReceiverSlot` calls `to.claimVideoSlot(...)` (`sync-run.ts:214`), and on the cloud store that is
a durable insert — `supabase-metadata-store.ts:87`: *"claimVideoSlot: RPC appends a reservation row and
returns the persisted serial."*

The function's own H-R2-1 comment, at `sync-run.ts:230-235`, is the precedent that was not followed:

> H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
> first left a BARE receiver row behind on the throw…

**And the bare row is what defeats the "forever" claim.** With a receiver row present, the next run no
longer takes the additive path at all:

- `sync-run.ts:618` — `if (!lv || !cv)` is now **false** (both sides have a row) → the two-sided branch.
- The B1 guard at `:697` does not fire: `cv.summaryMd` is null on a bare row.
- `reconcileClassA` sees local-has-MD / cloud-has-none → `copyToCloud` → `transferClassA`
  (`sync-run.ts:780-782`), which writes `key` with a plain `put` (`:394`) and sets
  `artifacts: { summaryMd: { key, status: 'promoted' } }` (`:430`) — **with no servability guard
  anywhere on that path.**

So the unservable key reaches the cloud advertised as `promoted` on run 2, and the serve guard 409s
forever — the exact end state §3.5 says the call site prevents. The guard fires once and is then routed
around.

**Not a regression** (today the same key lands on run 1 instead of run 2), but the design presents this
call site as the closure of the only reachable producer of unservable keys, and **behavior 26 would go
green over an open hole** — a one-run integration test cannot see run 2. That is the shape
`review-method.md` calls out: *"a GREEN gate that tests the wrong schema is worse than a red one."*

**Proposed fix.** Two lines, both mechanical:

1. Move the adopt guard **above** `ensureReceiverSlot`, next to the existing WB-H1 check at
   `sync-run.ts:236-238`. Then no row is created, the video stays one-sided, and the refusal genuinely
   re-fires every run as §3.5 claims.
2. Add the same guard to `transferClassA` (or to the `copyToCloud`/`copyToLocal` call sites), because
   the Class-A path is a second entrance to the same durable state and §2.5 already lists it as write
   entrance 3. Behavior 26 should then be split: *refuses on the additive path* **and** *the refusal
   survives a second run*.

---

## M1 — v15 dropped `promoteIfAbsent`'s discriminant and left two places requiring it

`neither mechanism nor branch-coverage` — a **stale cross-reference** · **caused by v15's own fix**,
in §3.6

v15 changed the signature (spec:649):

```
promoteIfAbsent(ref): Promise<void>        // RESOLVES when the final exists; never throws EEXIST
```

and justified it (spec:652-655): *"a discriminant nobody reads is decoration… Either give it a consumer
or drop it — dropped."* Two statements of the old contract survive the edit:

- **spec:659** — *"…leave the occupant untouched, remove the staging temp and `rmdir` its
  `_staging/<uuid>/`, and **return `'already-exists'`**."*
- **spec:1075, behavior 18d2** — *"**`promoteIfAbsent` RESOLVES `'already-exists'` rather than
  throwing**…"* — and 18d2 is a **contract** row, i.e. the thing an implementer writes a test against.

Verified by diff: `git show c86fab9^:…` line 563 was `promoteIfAbsent(ref): 'created' |
'already-exists'`; lines 568 and 928 are byte-identical to today's 659 and 1075. v15 edited the
signature only.

**Why this is not a mechanism defect** — and the distinction matters this round. Nothing about the
shape is wrong; the correct contract is stated correctly in the signature and in the surrounding prose
(*"It RESOLVES when the final object exists — it does not throw"*). Two sentences describe a superseded
shape. A redesign cannot help; deleting six words can. **`review-method.md`'s discriminator lists
*"two requirements contradict"* under `mechanism`, and this case shows that symptom also has a purely
editorial cause** — worth noting, because reading the discriminator literally here would trigger a
redesign for a copy-edit.

**It is also a repeat of a lesson this section already learned, one round later.** §3.6.3's round-12
Medium (spec:854-861) is precisely this: *"when a decision is reversed, grep for every place that
stated the old one — a rewritten section does not rewrite its own cross-references."* v15 reversed a
decision in §3.6.2 and did not grep §3.6.2 or §5.

**Fix.** Delete `, and return 'already-exists'` at spec:659; reword 18d2 to *"`promoteIfAbsent`
**resolves** when the final object already exists rather than throwing `EEXIST`"*.

---

## M2 — the `sourceMd` refusal has no stated OUTCOME, and `companionTransfer` is contractually forbidden to throw

`branch-coverage` · **caused by v15's own fix** (the three-row table is new in v15), in §3.6 —
**this is the round's evidence FOR the branch-coverage diagnosis**

§3.6.4's table says *"**require** `canonicallyEqualName(...)`; refuse otherwise"* and behavior 18j says
*"`companionTransfer` **refuses** to ship or delete"*. Neither says what "refuse" **is**: throw, return
an `error`, or silently no-op.

That branch is owned, and the answer is not free. `companionTransfer`'s own docstring
(`sync-run.ts:441-443`):

> Every companion write is BEST-EFFORT and never throws (M-R6-1): the caller must still advance the
> baseline, because transferClassA has already committed the winner body durably.

and the call site (`sync-run.ts:800-806`):

```ts
const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
// M-R6-1 — companion failures are reported, never thrown: the Class-A commit above is
// durable, so the baseline below MUST still advance (re-running would not retry the ship).
if (c.error) report.errors.push({ videoId: id, message: c.error });
```

An implementer who reads "refuse" as "throw" is caught by the per-video `catch` at `sync-run.ts:812`,
which **skips `writeVideoBaseline` at `:811`**. The baseline then never advances for that video, the
run reports an error every time, and — because `reconcileClassA` now returns `'skip'` — nothing ever
retries the companion step. That is M-R6-1's stickiness, reintroduced.

**Fix.** State the outcome per branch, in the table:
`return { shareNeedsOwnerServe: true, error: 'companion refused: receiver envelope sourceMd names <x>, not <y>' }`
— never a throw. Add it to 18j and to 18j2's sibling, and add a mutation row *"make the sourceMd
refusal throw"* → must turn red on a behavior that asserts the baseline still advances.

**Why `branch-coverage` and not `mechanism`:** the error/throw contract is a branch of
`companionTransfer` that this design governs and does not own. No redesign deletes it; the remedy is
to name the outcome. Exactly the class §3.6.1b predicts, in the fix §3.6.1b was written alongside.

---

## M3 — behaviors 18d2 and 18d3 cannot both pass: `rmdir` on a nested staging key is `ENOTEMPTY`

`branch-coverage` · not v15-induced (both rows date from v12, and round 12 passed over them), §3.6

- **18d2** requires `promoteIfAbsent` to remove *"the staging temp **and** its `_staging/<uuid>/`
  directory"*, and spec:659 spells it `rmdir`.
- **18d3** requires *"`promoteIfAbsent` creates missing parent directories, so a nested
  `dig/<base>/<n>.r<V>.md` key works on first write"*, and the adapter table row says the same
  (spec:668).

`LocalFsBlobStore.putStaged` builds `tempKey = '_staging/' + uuid + '/' + key`
(`local-blob-store.ts:53`), so a nested key stages at `_staging/<uuid>/dig/<base>/<n>.r<V>.md` and the
intermediate directories survive the `unlink`.

**MEASURED** (temp dir under `/tmp`, removed afterwards):

```
C rmdir _staging/<uuid> after nested unlink -> ENOTEMPTY
C rmdir flat case: OK
```

So on the one branch 18d3 exists to exercise, 18d2's cleanup throws — out of `promoteIfAbsent`, i.e.
out of `copyAdditiveVideo`, after the promote is durable. Same class as the Supabase-409 note in
§3.6.2: a cleanup failure surfacing as a per-video sync error.

**Fix.** Say `fs.rmSync(dirname_of('_staging/<uuid>'), { recursive: true, force: true })` (or prune
upward to the uuid dir), and make 18d3 stage a nested key **and** assert the `_staging/<uuid>/` tree is
gone, so the two rows are exercised together instead of separately.

---

## L1 — the ENOENT parenthetical describes a short-circuit `promote` does not have

`branch-coverage`, §3.6, not v15-induced. spec:682-684:

> *(`linkSync` with a **missing source** returns `ENOENT`, not `EEXIST` — `promote:60` short-circuits
> that case today and `promoteIfAbsent` must too, even though R2 always stages first.)*

`local-blob-store.ts:60` is `if (!fs.existsSync(from) && fs.existsSync(to)) return;` — it short-circuits
**source-missing AND destination-present** only. Source-missing **and** destination-missing falls
through to `renameSync` and throws `ENOENT` (**MEASURED**: `fs.linkSync` with a missing source →
`ENOENT`). Four branches exist (source × destination present/absent); the sentence names one and
implies two. Low because R2 always stages first, which the sentence itself concedes — but "must too" is
ambiguous about which of the two the implementer owes.

**Fix.** One row: `source absent + final present → resolve`; `source absent + final absent → throw
ENOENT (a fault; unreachable from R2)`.

---

## L2 — 18f and 18d4 pull in opposite directions on `promote`

§3.6.2 says the orphaned `_staging/<uuid>/` is *"Not attributable to this change… **Worth fixing here**;
not caused here."* Behavior **18f** then asserts *"`promote` leaves no orphaned `_staging/<uuid>/`
**directory** behind"* — a change to `promote` — while **18d4** asserts *"`promote` is **unchanged** —
its existing callers' behaviour is byte-identical before and after this slice"*, and the mutation table
carries *"Change `promote` to create-if-absent on local → **18d4**"*. Both cannot be literally true.
18f's parenthetical *"(`unlink` removes only the file)"* also reads as if it were about
`promoteIfAbsent`, which does the unlinking; `promote` uses `renameSync`.

**Fix.** Decide: either scope 18d4 to *"`promote`'s **success/failure semantics** are unchanged"* and
keep 18f, or drop 18f to a follow-up. As written an implementer must break one contract test to pass
the other.

---

## L3 — the `slugify` repair leaves already-mojibake vault files unaddressed, and the spec does not say so

§3.2's repair is correct and I could not break it (see below), but the class it removes has an
installed base: a video ingested **before** the repair has a row whose `summaryMd` holds the lone
surrogate and a disk entry holding `U+FFFD`. **MEASURED — `findByNormalizedName` cannot bridge them**
(`serial-migrate-exec.ts:42` compares NFC forms; `\uD840` and `�` are different in every normal
form), so those files stay orphaned after the fix, and the repaired `slugify` would produce a *third*
name on any re-derivation. The spec's *"today those titles already produce mojibake vault filenames"*
is true and is the right argument for the repair; it just leaves the existing rows unmentioned.

**Fix.** One sentence in §3.7 or §7: pre-repair mojibake vault files are not migrated; they remain
exactly as broken as today, and the guard's `isWellFormed()` check will refuse the *row's* key if such a
video is re-served — which is the loud failure, not a silent one.

---

## What I attacked and could NOT break

Recorded because a thirteenth round should say what held, and because three of these are the brief's
own hardest items.

### The `slugify` one-line repair (brief item 2) — sound, independently re-derived

**MEASURED**, Node v22.14.0, full codepoint space (excluding surrogates) × 7 title shapes including
three that force the cut to land on the target character:

```
ill-formed slugs, OLD slugify : 93231
ill-formed slugs, NEW slugify : 0
NEW slug keys failing isServableSummaryKey : 0
```

The 93,231 figure reproduces the spec's exactly. Four sub-questions the brief asked:

- **Does it change any currently well-formed filename?** No — the trim is guarded by `isWellFormed()`,
  so a well-formed slug is returned unchanged by construction.
- **Is `slice(0, -1)` sufficient — can ill-formedness sit anywhere but the tail?** No. **MEASURED**:
  a lone surrogate in the *input* is scrubbed by `slugify`'s own
  `.replace(/[^\p{L}\p{N}]+/gu, '-')` — under `/u` a surrogate is a code point in category `Cs`, so it
  matches the negated class (`slugify('a\uD800b')` → `'a-b'`). Swept all 2048 surrogate code points ×
  5 positions: **0** remain ill-formed after the repair. The only producer is the `.slice(0, 60)` cut of
  a valid astral pair, which is always at the tail. This matters — it is the one way the repair could
  have been incomplete, and the spec's sweep does not say it covered surrogate *inputs*.
- **`isWellFormed` availability.** Runtime: present on Node 20.18.2 **and** 22.14.0 (**MEASURED**);
  production and CI are both pinned to Node 22 (`Dockerfile` header, `.github/workflows/ci.yml:37`).
  Types: `tsconfig.json` sets `"lib": ["dom", "dom.iterable", "esnext"]`, and **MEASURED** — a probe
  file using `s.isWellFormed()` and `[...k].length` passes `npx tsc --noEmit -p tsconfig.json` clean.
  (The probe was created outside the tracked tree's git index and deleted; `git status` is clean.)
- **The second `slugify` consumer the spec never mentions.** `lib/output-folder.ts:78` builds a
  **directory** name from `slugify(title)`. This is *not* a problem, and the reason is worth recording
  so the next reader does not have to re-derive it: `resolveOutputFolder` resolves an existing playlist
  by **playlist id**, not by folder name (`output-folder.ts:25-49`, `:65-66`), so a changed slug cannot
  orphan an existing playlist folder. `lib/pipeline.ts:237` uses it for the vault filename, which is the
  case §3.2 covers.

### The round-12 H1 measurement, reproduced exactly

```
A readdir after 1st write: ["003_x�.md"]
A entries: 1
A read via key1: BODY-2          <- key1's content is gone
A readdir entries well-formed?: true
```

Both halves hold: the U+FFFD collapse **and** the claim underpinning the guard's backstop status —
`readdir` strings are always well-formed, so after the producer repair the class is unreachable from
either entrance (brief item 3). The guard/producer pair is coherent, not mutually-unreachable: the
guard's `isWellFormed()` branch is reachable in a unit test (behavior 16c) and correctly *unreachable*
in integration, which is what a backstop is.

### The §3.4 predicate, both directions (brief item 6)

Full codepoint sweep × 4 key shapes, comparing the shipped guard
`/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` against the v15 predicate:

```
CURRENT accepts but v15 REJECTS : 0
v15 newly ADMITS                : 3,876,146
lone-surrogate keys accepted by CURRENT : 0   (so isWellFormed() rejects nothing live)
C1-containing keys accepted by CURRENT  : 0   (so the C1 widening rejects nothing live)
total length 4 / 129 / 130 / 131 : accepted by both;  132: rejected by both
68 code points / 132 UTF-16 units (astral) : accepted by both   (round-11 M3 fix correct)
```

Both v15 additions are strictly non-regressive against the shipped guard, and the round-11 B1 class
(`003_lesson-⒈.md`) is admitted. `s.includes('..')` on the **name** still rejects `001_a．．b.md`.
P5 re-verified: exactly two callers today — `serve-summary-core.ts:61` and
`resolve-summary-key.ts:16`.

### R2, R3, R4 branch enumeration (brief item 1)

Applying §3.6.1b's own discipline to the rules other than the two I filed against:

- **`BlobRead`'s four cases** (`blob-store.ts:10-13`) — R2 states an outcome for all four. **Total.**
- **`decideCompanion`'s outcomes** — the §3.6.4 table is keyed on the *receiver read*, which is total
  over `envelope | none | unknown`, and every outcome (`ship` ×2, `deleteReceiverModel`, `noop`) maps
  into it: `provablyStale` requires `kind === 'envelope'` (`companion.ts:151-152`), and `noop` writes
  nothing. **Total** — the only gap is M2's unnamed refusal outcome.
- **`copyToLocal` vs `transferClassA`** — R3's `summaryMd`-null branch is stated (round-11 L3) and the
  loser record is genuinely in scope at **both** sites: `copyToCloud` at `sync-run.ts:780-782` with
  `cv` re-read after relocation at `:765`; `copyToLocal` at `:791-793` with `lv`. The proposed
  signatures line up with the real ones (`transferClassA(winner, loser, winnerVideo, videoId)` today,
  `+ loserVideo`).
- **`SupabaseBlobStore.promote`'s three success paths** — `:113`, `:117`, `:121` confirmed by reading;
  v15's correction is right, and its Medium grading (self-heals next run) is right.
- **R1's no-clobber** — **MEASURED**: `linkSync` returns `EEXIST` through an NFC/NFD alias **and** a
  case alias; `ENOENT` on a missing source. Holds.
- **R4** — `findByNormalizedName` (`serial-migrate-exec.ts:31-45`) is NFC-equality on the **basename**,
  no case folding, so `a.normalize('NFC') === b.normalize('NFC')` is a proper subset of the measured
  volume relation (canonical equivalence ∪ case folding) and lifting one predicate is safe. R3 passes
  whole logical keys and `findByNormalizedName` passes basenames; the shared predicate is pure string
  comparison, so no conflict.

**So the brief's prediction is mostly borne out: applying §3.6.1b's discipline finds few remaining
unenumerated branches.** The two I did find (M2, M3) are both branch-coverage, and neither is a rule
that cannot be satisfied on *any* branch. That is real evidence **for** the branch-coverage diagnosis —
which is why H1 matters: it is not a branch problem at all.

---

## Adjudication: the falsifier fired, and what is actually owed

**It fired.** H1 is a §3.6 finding, it was introduced by a §3.6 fix (the `sourceMd` credential, adopted
in v12 to close round-11 M1), and *"a credential is stale"* is the falsifier's own first-named mechanism
symptom, matched verbatim and by measurement. Recording it as *not* fired would be the round-8 failure
the override paragraph explicitly warns against. **Record it as fired.**

**But the redesign it nominally buys should be scoped to what fired, not to §3.6 as a whole**, and I say
so as the reviewer who found it rather than leaving the coordinator to infer it:

- H1 does **not** touch R1–R4. `promoteIfAbsent`, R2's write-then-classify, R3's loser-record question
  and R4's subset predicate are all untouched by it; I attacked each above and each held.
- H1 is confined to the **third residual** — a credential bolted onto `companionTransfer` — and it has a
  one-line remedy the local path already implements.
- Everything else this round is branch-coverage or editorial, exactly as §3.6.1b predicted.

**Recommendation: a design pass on the third residual's credential only** (*what proves that
`models/<base>.json` belongs to `base`?* — `sourceMd`, `sourceMdHash`, or an invariant enforced at
`remap`), plus the four fixes above. Not a fifth rewrite of the vault write protocol.

**One methodological note the round produced, worth carrying into `review-method.md`.** M1 is a
contradiction between two requirements — the discriminator's third mechanism symptom — with a purely
editorial cause and a six-word fix. *"Two requirements contradict"* is therefore not a sufficient
mechanism test on its own; the deeper test in the same section (**can a redesign remove it?**) is the
one that separates M1 from H1, and it is the one that should be quoted when the discriminator is
applied. The discriminator's own list can produce a false REDESIGN if read as a checklist.

---

NOT CONVERGED
