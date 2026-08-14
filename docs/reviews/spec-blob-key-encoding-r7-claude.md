# Round 7 — Claude adversarial review, cloud blob key encoding (backlog #36)

Subject: `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` **v7, working tree**
(not a pinned commit). Branch `fix/cloud-blob-key-encoding`, HEAD `d09b015`.

**1 Blocking, 2 High, 3 Medium, 2 Low. NOT CONVERGED.**

The headline for the user, up front: **the branded type does not do the thing §3.5.1 says it does, and
I measured that rather than reasoned about it.** It is still worth adopting — it makes the factory call
mandatory and the mint/adopt distinction explicit at every site that uses the summary seam — but it
enumerates *calls to the branded function*, not *writes of a summary key*. A fifth entrance compiles
clean. Separately, and independently of the type, I found a path that overwrites a paid vault file.

## Probes run this round

| Probe | File | Result |
|---|---|---|
| Branding, 12 constructions, `tsc --strict` | `…/scratchpad/brandprobe/probe.ts` | exit 0 — the three `@ts-expect-error` cases fired |
| **Negative control** — same file, `@ts-expect-error` on the 8 lines claimed to compile | `…/scratchpad/brandprobe/negcheck.ts` | **8 × `TS2578: Unused '@ts-expect-error' directive`** — i.e. all 8 genuinely produce no error |
| Storage charset for the §3.2 marker shape (local `127.0.0.1:54321`, service role, cleaned up) | `…/scratchpad/probe-marker.mjs` | `003_=hJ8kQ2m….md` **accepted**; `003_돈-버는-방식은.md` **REJECTED** (`Invalid key`); `=hAAAA.md` accepted; 3 objects removed |

Scratchpad root:
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/a00a513a-4135-416e-bbf4-48c0416ca19d/scratchpad/`

The storage probe is a **checked, no finding**: §3.2's encoder output shape is storable and the raw
Korean segment it replaces is not, so the encoder is load-bearing. §2.1–2.3 hold on this axis.

---

## Blocking 1 — §3.4's collision guard covers ONE of the two entrances that write into the vault, and its own refusal routes the next run down the unguarded one

**Severity: a paid vault file, with the user's corrections in it, is overwritten.**

§3.4 (spec:184–190) scopes the guard to one call site:

```md
The additive create runs in **both directions** (`sync-run.ts:618-627`). When a video is cloud-only,
the receiver is the vault and the receiver blob store is `LocalFsBlobStore`.
```

But the additive create is not the only thing that writes a cloud-authored key into the vault.
`lib/cloud-sync/sync-run.ts:791-793`:

```ts
} else if (decision.action === 'copyToLocal') {
  winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
  winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
```

and `transferClassA` writes with `lib/cloud-sync/sync-run.ts:379`, `:381`, `:394`:

```ts
const key = winnerVideo.summaryMd;
const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
…
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

The `put` at `:394` is a **deliberate unconditional overwrite** — its own comment (`:387-393`) says so:
*"A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`."* There is
no `tryGet` guard, and §3.4 does not extend one here. §3.5.1 does list this site as entrance 3, but for
the **servability** rule only; the **aliasing** rule of §3.4 is not applied to it.

§2.5 establishes the hazard: *"**APFS aliases NFC and NFD**"*. So `put` at a key in one normal form
lands on the inode of a file named in the other.

**The reachable chain.** Codex round-6 **M1 is unaddressed in v7** — §3.4 still gives the guard as a
snippet with no insertion point, while `lib/cloud-sync/sync-run.ts:240` claims the receiver row
*before* the `:263` write:

```ts
const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
```

1. **Run 1.** Cloud-only video, vault holds an orphan `0003_café.md` in **NFD**, cloud key is **NFC**.
   `ensureReceiverSlot` creates the local row; the §3.4 guard (placed with the write, as the spec
   leaves open) fires and throws. Caught at `:812` → `report.errors`, no baseline. **But the bare local
   row survives.**
2. **Run 2.** Both replicas now hold the video → the two-sided path. The local row has a serial and no
   MD, so `describeDivergence` (`reconcile-serial.ts:152-154`) takes the
   `baseOf(applySerial(cloudVideo.summaryMd, …))` branch — cloud keeps its own NFC slug, the bases
   "agree", nothing is remapped.
3. `reconcileClassA` sees `la.mdHash == null`, `ca.mdHash != null` → `copyToLocal` → `transferClassA`
   → `loser.blob.put(localP, '0003_café.md' NFC, …)` → **APFS resolves it to the NFD inode and the
   user's paid vault summary is overwritten.**

Step 3 is guarded by nothing, and the code comment at `:701-706` states the opposite of what is true
on an aliasing filesystem:

```
//    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
//    nothing can be destroyed and no false agreement about competing bodies is possible
```

That sentence is correct on a byte-exact filesystem and false on APFS — which is precisely the
condition §3.4 was written to handle. A second, guard-independent route to the same state exists (a
summary-less receiver row from a legitimate `summaryMd == null` additive create, plus the orphan vault
file that `recoverOrphanedVideos` exists to adopt), so this does not rest solely on the ordering bug —
but the ordering bug is the certain one.

**Fix (two sentences of spec, not a redesign):**

1. Pin the insertion point, as Codex M1 asked: the guard runs **before `ensureReceiverSlot`**, on
   `toBlob`, so a refusal leaves no receiver row at all.
2. Apply the same `tryGet` / fail-closed-on-`unreadable` guard in `transferClassA` whenever the loser's
   store has `provesAbsence === true` and the loser's own row does **not** already advertise `key` —
   i.e. guard the case where the key arrives from the winner rather than from the loser's own record.
   Add a behavior mirroring **17** for the Class-A hydration path; behavior 17 as written covers only
   *"a cloud→local additive create"*.

---

## High 1 — MEASURED: the branded type does not enumerate write entrances. §3.5.1's central claim and behavior 25 are both false as written

§3.5.1 (spec:287-289) claims:

```md
The summary write path takes `CloudSummaryKey`, not `string`. Every entrance must therefore call the
factory to obtain one, so **`tsc` enumerates the sites** — and a fifth entrance does not compile.
That is the one thing six rounds proved cannot be done by reading.
```

**Where the brand cannot go.** `BlobStore.put`/`putStaged` must keep `key: string`, because nine
non-summary callers use them: `lib/pdf/generate-doc-pdf.ts:96`, `lib/html-doc/rerender.ts:73`,
`lib/html-doc/generate.ts:70`, `lib/html-doc/model-store.ts:52` and `:97`, `lib/dig/slides.ts:188`,
`lib/dig/cloud/write-dig-section-blob.ts:46`, `lib/storage/supabase/consistency.ts:27`,
`lib/pipeline.ts:57`. So the brand can only sit on a **narrower** seam — and that is the defect: adding
a `putSummaryStaged(p, key: CloudSummaryKey, …)` does not remove `put`, `putStaged` or `copy`.

**Measured, not argued.** `probe.ts` models exactly that shape. `negcheck.ts` marks the lines claimed
to compile with `@ts-expect-error`; `tsc --strict` reported **`TS2578: Unused '@ts-expect-error'` on all
eight**, proving each produces no error:

| Construction | Probe line | Compiles? |
|---|---|---|
| **A fifth entrance:** `blob.put(p, \`${base}.md\`, bytes, 'text/markdown')` | 46 | **yes** |
| **Entrance 4:** `blob.copy(p, from, to)` | 56 | **yes** |
| Key laundered through `any` | 78 | yes |
| A DB/row type *declared* as `CloudSummaryKey` | 86 | yes |
| `JSON.parse(text).summaryMd` | 93 | yes |
| A zod-shaped schema declared to output the brand | 100 | yes |
| `k as unknown as K` where `type K = CloudSummaryKey` (no forbidden text) | 107 | yes |
| `launder<T extends string>(s: string): T` — **no cast at the call site at all** | 114 | yes |

What the brand *does* enforce (also measured, `probe.ts` exit 0): a bare `string` cannot reach the
branded parameter; string operations strip the brand; a `Record<string, unknown>` round trip yields
`unknown`, which is not assignable. **The brand is a real gate at the point of use. It is not a
discovery mechanism.**

**Entrance 4 is structurally out of its reach**, which matters because entrance 4 is the one round 6
found and the one §3.5.1 was written for. It writes no bytes through `put`:

`lib/cloud-sync/reconcile-serial.ts:282`
```ts
const res = await cloud.blob.copy(cloud.p, from, to);
```
`lib/cloud-sync/reconcile-serial.ts:293-296`
```ts
const patch: Record<string, unknown> = {
  serialNumber: localVideo.serialNumber,
  summaryMd: `${newBase}.md`,
  artifacts: { summaryMd: { key: `${newBase}.md`, status: 'promoted' } },
```

`copy(p, from: string, to: string)` and `Record<string, unknown>` both accept plain strings. Nothing
about the type system makes `reconcileCloudBase` call the factory; it remains a convention — exactly
what §3.5.1 says it is replacing.

**Behavior 25 is not writable, and it is the FOURTH vacuous falsifier in this spec's history**
(rounds 2, 3 and 5 each produced one; §5's own ⚠ says so). Behavior 25 reads:

```md
| 25 | A summary write cannot be called with a bare `string` — **`tsc --noEmit` fails** on a fifth
       entrance that skips the factory | type test |
```

A fifth entrance that *skips the factory* calls `put`, which compiles. The only test anyone can
actually write passes a bare string **to the branded function** — which asserts that a brand is a
brand. The paired mutation in §6 (*"Widen the write signature from `CloudSummaryKey` back to `string`"*)
kills that narrow test, so the mutation table goes green while the claim stays false. This is the
mutation-harness failure mode already in the project's memory: a surviving-or-killed mutation says
something about the test, never about the claim above it.

**Fix — three parts, none of them "drop the type":**

1. **Correct the sentence.** The brand enforces the invariant at every site that *uses the summary
   seam*, and makes the mint/adopt choice explicit and reviewable there. It does not find new sites.
2. **Name the signature.** §3.5.1 must say what changes: a new
   `putSummaryStaged(p: Principal, key: CloudSummaryKey, bytes: Buffer): Promise<StagedRef>` on
   `BlobStore` (all three adapters), used by entrances 1–3; and state explicitly that **entrance 4
   cannot use it** and must therefore call `toCloudSummaryKey` before building both `plan` and `patch`.
3. **Replace behavior 25 with a falsifiable enumerator.** A check script is the honest instrument here,
   as it was for `check-vocabulary-collisions.py`. `scripts/check-summary-writes.py` **FAILS IF** an
   argument expression ending in `.md` reaches `put`, `putStaged` or `copy` anywhere outside the
   factory's own module and an explicit allowlist of the four blessed sites. That has a statable
   failing observation; behavior 25 does not.

---

## High 2 — §3.5's mint repair manufactures a permanent divergence that §3.5.1's adopt-refusal then declines to reconcile, on every run, forever

The two v7 rules are individually reasonable and compose into a stuck state the spec never names.

§3.5's repair rewrites the **cloud** base:

```
if (!accepts(assertCloudSummaryMdKey, `${base}.md`))  base = `${padSerial(serial)}_${videoId}`
```

§1 decision 1 keeps the **local** vault filename as the unrepresentable slug. So the two replicas now
hold different bases *by design*. `lib/cloud-sync/reconcile-serial.ts:147-156` compares them
byte-exactly and reports divergence forever:

```ts
const from = baseOf(cloudVideo.summaryMd);
const to = localVideo.summaryMd
  ? baseOf(localVideo.summaryMd)
  : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber));
return from === to ? { diverged: false } : { diverged: true, from, to };
```

`reconcileCloudBase` then tries to move cloud **toward the local key** (`:186`, `const newBase = d.to!`)
— which is the unservable one — and §3.5.1's table says entrance 4 must **refuse** it (`illegal —
refuse`). `lib/cloud-sync/sync-run.ts:754-756` turns that refusal into a throw:

```ts
throw new Error(rec.reason === 'target-occupied'
  ? `serial collision: ${id} needs serial ${rec.want} on cloud, already held by ${rec.heldBy}`
  : `base reconciliation failed for ${id}: ${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}`);
```

caught at `:812` into `report.errors`. The throw is at `:756`, **before** Class A at `:771` — so that
video's edits stop propagating in either direction, permanently, and the user sees the same error on
every sync run with no action that clears it.

**The trigger is behavior 19's own input.** Round-5 P4 swept the BMP and found zero mint-path
refusals, so the *only* constructible input is P5's 59 ASCII letters + `U+20000` — the same one
behaviors 19 and 22 use. Behavior 19 asserts the video *"ingests and the summary **serves 200**"* and
stops one step before the damage: nothing asserts what the next sync run does with it.

§3.5.1's justification for the refusal does not hold on this entrance:

```md
**Why a fallback is illegal on 2–4:** the replica must agree with the sender about the key, so
repairing one side would diverge them.
```

Entrances 2 and 3 replicate a key **from a sender**. Entrance 4 does not — it *chooses a new address*
(`newBase`), and the local key is a **preference**, not a contract. There is no sender to disagree
with. That is the brief's question 2, and I think the answer is that **entrance 4 is neither mint nor
adopt**, and forcing it into `adopt` is what produces the stuck state.

**Fix (recommended):** give the factory a third context —
`{ kind: 'remap'; serial: number; videoId: string }` — whose fallback is **legal**, for the stated
reason that a remap picks its own address. `reconcileCloudBase` then relocates to
`${padSerial(localVideo.serialNumber)}_${videoId}.md` when the local key is unservable: the bases still
disagree textually, but the cloud row is servable and the relocation *completes*, so `describeDivergence`
stops firing on the moved-to base and Class A resumes. Add a behavior: *ingest the behavior-19 title,
sync, and assert the video reconciles once and then syncs cleanly on the second run* — that is the
falsifier behavior 19 stops short of.

If the user prefers the refusal, that is a legitimate call, but §3.5.1 must then say plainly that this
video is permanently excluded from sync and errors on every run, and §8 must carry the risk row —
because *"the loud failure master already produces, preserved deliberately"* is not accurate here.
Master produces no cloud summary at all for this title; the per-run permanent error is **new**.

---

## Medium 1 — Codex round-6 M2 stands verbatim, and the rule it names is unenforceable

spec:155:

```md
**A prefix must end on a segment boundary.** `list`/`deletePrefix` throw otherwise; a mid-segment
prefix would encode `ba` as a whole segment and match nothing, silently.
```

spec:390:

```md
| 12 | `list(p, 'dig/{base}/')` and `list(p, 'dig/{base}')` return the same set | unit |
```

Unchanged from v6. Beyond the contradiction Codex already reported: the rule cannot be implemented as
stated. `dig/003_x` is textually a complete segment whether the real segment is `003_x` or `003_xyz`,
so the seam has no observation that distinguishes a mid-segment prefix from a full one. The only
enforceable predicate is the one Codex proposed: `prefix === '' || prefix.endsWith('/')`. Adopt it and
delete behavior 12 (all three production callers pass a trailing slash — `reconcile-serial.ts:102`,
`load-dig-for-serve.ts:34`, `dig-state/route.ts:47`).

## Medium 2 — `check-key-brand.py`'s failure condition is a text grep that four measured constructions dodge, and the budget precedent is not parity

spec:314-317:

```md
⚠ **The escape hatch must be closed.** `as CloudSummaryKey` defeats the whole mechanism.
`scripts/check-key-brand.py` **FAILS IF** a cast to `CloudSummaryKey` appears outside
`toCloudSummaryKey`'s own module. The budget brand carries the identical exposure and has held, so
this is parity, not a new risk.
```

Probe cases E1, E2, E4, E5 and E6 all obtain the brand with **no `as CloudSummaryKey` text**: `any`, a
declared row/zod type, `k as unknown as K` through a local alias, and a generic launder function with
no cast at the call site at all.

"Parity" is the part I'd push back on hardest. `lib/serve-budget.ts:81` brands **constants declared
once in one module** — a grep over that module is complete by construction. A key is a **value** that
arrives from Postgres, zod and the sync payload, through code that is **already `any` on the branded
entrances**: `lib/cloud-sync/sync-run.ts:272` (`const sanitized: any`), `:397` (`const wv: any`),
`:398` (`const completeTuple: any`), and `lib/cloud-sync/reconcile-serial.ts:293`
(`Record<string, unknown>`). The row write that advertises the key —
`sync-run.ts:279`, `sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } }`
— goes through one of them, so the brand does not reach the metadata half of the invariant at all.

**Fix:** state the script's failure condition as what it can observe, and add to the slice's scope:
narrow the three `any` annotations at `sync-run.ts:272`/`:397`/`:398` and type the `patch` at
`reconcile-serial.ts:293`, or record explicitly that the brand covers the blob write only and the row
write is covered by the runtime `assertCloudSummaryMdKey` instead.

## Medium 3 — Codex round-6 M1 (guard ordering) is unaddressed

Folded into **Blocking 1**, but recorded separately so the round-6 ledger is honest: v7 changed nothing
in §3.4, and the insertion point is still unspecified.

## Low 1 — citation drift in three places

- §3.3's table cites `load-dig-for-serve.ts:33`; `:33` is `const suffix = …`, the `list` call is `:34`.
- §3.5 cites `resolve-summary-key.ts:16` without its directory — it is `lib/dig/cloud/resolve-summary-key.ts:16`
  (content verified correct: `try { assertCloudSummaryMdKey(key); } catch { return null; }`).
- §3.5.1's table gives entrance 1's Site as `summary-handler.ts:96`; `:96` builds `baseName`, the row
  write is `:157` and the blob write is `:172-173`. One entrance, three sites the repair must reach
  coherently — worth listing all three, since a repair applied at `:172` only would leave `:157`
  advertising the unrepaired key.

Verified correct: `serve-summary-core.ts:56-64`, `supabase-blob-store.ts:78-80`, `slugify.ts:6`,
`reconcile-serial.ts:102`, `dig-state/route.ts:47` and `:50`, `assert-cloud-summary-md-key.ts:14`
(already widened to `\p{M}` in the working tree), `reconcile-serial.ts:282`/`:293`, `sync-run.ts:263`,
`sync-run.ts:379-399`.

## Low 2 — the local writer is a summary-key writer the table does not mention

`lib/pipeline.ts:57` and `:265` write `${baseName}.md` from the same `slugify`. They are correctly out
of scope (their output only ever reaches the cloud by adoption at entrances 2–4), but §2.6's *"at least
four"* invites the next reviewer to find them and call it a fifth. One sentence saying why they are
excluded costs less than round 8 rediscovering them.

---

## Checked, no finding

- **§3.2's marker shape is storable and the segment it replaces is not** — probed directly against
  local Storage this round (table at the top). The encoder is load-bearing.
- **A mint repair does not ripple into the model/PDF keys through `summaryCore`.**
  `lib/ingestion/summary-core.ts:60`: *"baseName is accepted in the input shape … but is"* inert —
  the only consumers are the caller's own `:157`/`:172`.
- **The brand genuinely blocks the bare-string case, string derivation, and `Record` round trips**
  (probe A, E7, E8 — all three `@ts-expect-error` directives were consumed).
- **No fifth cloud write entrance exists in the tree today.** I enumerated every assignment to
  `summaryMd`/`artifacts.summaryMd.key` across `lib/`, `app/`, `worker/`, `scripts/`; the cloud sites
  are exactly the four in §3.5.1's table.
- **`video.summaryMd` does not need to change type.** `types/index.ts:56` is
  `summaryMd: z.string().nullable()`; leaving it unbranded is what *forces* entrances 2–4 to call the
  factory at the point of use. §3.6 is right to leave it alone, and the brief's question 4 has no
  ripple to report.

---

**NOT CONVERGED** — 1 Blocking, 2 High.
