# Adversarial design review — cloud blob key encoding (backlog #36), round 4, Claude half

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` (draft **v4**)
**Branch:** `fix/cloud-blob-key-encoding` @ `20acdb7`
**Reviewer:** Claude (round-4 Claude half). Not the author of the round-1/2/3 Claude reviews.
**Date:** 2026-08-14

> ⚠ **Which bytes these line numbers refer to.** The spec was edited in the working tree *while this
> review was running* — a partial round-4 fix rewriting §3.2.2 (`git diff`: 18 insertions,
> 9 deletions vs `20acdb7`). Every `spec:NNN` citation below was re-verified against the **working
> tree as of the end of this review**, not against `20acdb7`. The concurrent edit does not dissolve
> any finding here; it makes H2 sharper, and H2 says why.

**Verdict: NOT CONVERGED** — 1 Blocking, 3 High, 3 Medium, 2 Low.

Everything labelled *measured* was run, not recalled: §3.2's encoder transcribed verbatim and driven
against the live local stack (`http://127.0.0.1:54321`, `artifacts` bucket, service role — each probe
refuses any host that is not `127.0.0.1`/`localhost` and removed every object it wrote,
`residual under probe root: []`), a full sweep of the 2501 `\p{M}` codepoints, and this machine's APFS
in a temp dir. Node v22.14.0.

---

## First: round-3 B2 reproduces. v4's premise holds.

The brief's item 1 is the load-bearing one, so I ran it before reading further. Under the **v4** world
— raw-byte hashing, no canonicalization anywhere, `CLOUD_SUMMARY_MD_KEY` widened to `\p{M}`:

```
NFC = 30 30 33 5f 63 61 66 e9 2e 6d 64
NFD = 30 30 33 5f 63 61 66 65 301 2e 6d 64
encode(NFC) = 003_caf=hFWAbLG4cfrk4vnNWSoWjal.md
encode(NFD) = 003_cafe=hOW3J8pKhOv-IbHnShk7-Xm.md
SAME PHYSICAL KEY? false
master guard  raw NFC=true  raw NFD=false
v4 guard      raw NFC=true  raw NFD=true

putStaged  -> ACCEPT      promote(move) -> OK
serve guard(raw NFD, v4 widened) -> true
serve get(raw NFD) -> PAID-SUMMARY-BODY

MODEL_KEY physical = models/003_cafe=h-jWwBE5k3kD4bGFlNI1a8V.json   put -> ACCEPT   get -> {"m":1}
pdf       physical = pdfs/003_cafe=hCkRhd74cJnf1_y6hgkjPMW.pdf      put -> ACCEPT
dig       physical = dig/003_cafe=hevrhFVg0OQooAStO4ft-mr/1234.r1.md
list(dig/{base}/) -> ["1234.r1.md"]
```

An NFD key writes, stages, promotes, serves and lists correctly with nothing canonicalized. The
deletion is sound and I could not break it on the Supabase backend. **Everything below is about what
the deletion did not finish accounting for, not about the deletion.**

**The frame worth stating once.** Supabase's `400 InvalidKey` was doing two jobs. One was bad — it is
why backlog #36 exists. The other was accidental safety: it made it *impossible* for a cloud row to
hold a non-ASCII summary key, which is why every downstream consumer could be narrow without anyone
noticing. v4 removes the barrier and accounts for **one** consequence (§3.5.1, the vault-overwrite
path round-3 B1 found) while §9 explicitly declines to account for the other (B1 below). Both of my
top two findings are that same shape: *the slice removes a barrier that was accidentally doing safety
work.* That is a bounded gap, not a mis-scope — see the Verdict.

---

## Summary of findings

| # | Sev | One line |
|---|---|---|
| B1 | **Blocking** | v4 makes **every** logical key storable but leaves `CLOUD_SUMMARY_MD_KEY` narrow, so a vault filename outside `[\p{L}\p{M}\p{N}_-]` turns a **loud sync error** into a cloud row advertising `status: 'promoted'` that **409s when the user opens it**. Measured against real Storage for four shapes. §9 asks "is this key *storable*?" (correctly unfalsifiable) instead of "is this key *servable*?" (falsifiable, and exactly what the 400 was enforcing) |
| H1 | High | §3.5.1 took the **weaker** of the two fixes round-3 B1 offered. The guard asks the **row**, so a real vault file at an aliasing name with **no index row** — precisely what `recoverOrphanedVideos` exists to adopt — passes it, and `renameSync` overwrites a paid summary. Asking `toBlob.exists` closes this *and* the pre-existing byte-exact instance |
| H2 | High | The encoder's central property is stated **three ways** in v4 and the behavior table is on the wrong side. §3.2.2:301 says injective on raw, "not over a normalized subset"; §3.2:275, §6 row 4:574 and §7:608 all still say **NFC-normalized**. §6 is what becomes the test, so the property test excludes the NFD inputs the slice exists to support |
| H3 | High | §7:611-612 — *"the real guard against B1's whole class"* — is a test that **cannot fail** under v4. `normalizeLogicalKey` is byte-exact and the encoder is injective on raw, so "the comparison helpers agree with the encoder" is trivially true for every input. v3 residue advertised as the primary guard |
| M1 | Medium | §3.3's fail-closed marker check is stated over the **caller's own logical prefix** as well as the physical remainder. A key legitimately containing `=` (Storage accepts `=`; re-measured) makes `list` throw on a prefix the caller supplied → `paidKeysUnder` (`reconcile-serial.ts:102`) throws → the video is stranded on **every** run. Round-2 H1a's fails-closed shape re-entering |
| M2 | Medium | **Two `### 3.5` headings** (spec:373, :393). The first is a present-tense Blocking analysis of the design v4 deleted, ending "Reachable via §2.5's `recoverOrphanedVideos` path". The second's heading says "Canonicalize at INGRESS" while its body says "v4 introduces NO equivalence at all". `check-docs.py` exits 0 on it (run) |
| M3 | Medium | Brief item 3, answered by measurement: `copyBlob`'s short-circuit **is** wrong on the aliasing backend — measured `{ok:true, already:true}` for two keys that are one inode — but it is **not reachable**, because `.copy(` has exactly one non-test caller and it is `cloud.blob`. §3.4 clears `copy()` for a reason that does not cover aliasing; write the real reason down |
| L1 | Low | §3.5.1's snippet writes `to.blob.aliasesUnicodeNormalization`, but the guard lives in `ensureReceiverSlot` (`sync-run.ts:164-167`) whose `to` is a `MetadataStore` with no `.blob` |
| L2 | Low | Behavior 22 guards a **dissolved** defect (round-2 M1 was a property of v2's `normalizeLogicalKey`, which v4 removes). Behavior 3 kills the `hash(NFC(s))` mutation on its own. r3-B3 asked for 22 to be replaced or deleted; not applied |

---

## B1 — Blocking. Totality without servability: v4 converts a loud sync failure into a paid summary that is unreachable in the cloud and a record that says otherwise

§3.2 promises the encoder is **Total** — *"Every input produces an accepted key. No logical key can be
unstorable"* (spec:272). §9 then reasons from that to delete the precondition:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:695-696
So no unstorable key can exist, and a
precondition asking "is this key storable?" has no observation that would make it fail.
```

**That sentence is true and it is the defect.** The question a gate here must ask is not *storable* but
*servable*, and `CLOUD_SUMMARY_MD_KEY` (`assert-cloud-summary-md-key.ts:14`) — even widened — is far
narrower than "everything". The two sets used to be kept in rough agreement by Storage's own `400`.
v4 makes the storable set universal and leaves the servable set where it was.

### Measured, against real Storage

Uploading each key twice — once as master does (raw) and once as v4 does (encoded) — and testing both
guards:

```
key                          | master-upload | v4-upload | v4-guard | verdict
003_hello.md                 | ok            | ok        | true     | servable
003_café.md                  | REJ 400       | ok        | true     | servable      <- the fix working
003_café.md (NFD)            | REJ 400       | ok        | true     | servable      <- \p{M} working
003_한국어.md                 | REJ 400       | ok        | true     | servable
003_½-price.md               | REJ 400       | ok        | true     | servable
003_돈 버는 방식.md            | REJ 400       | ok        | false    | *** LOUD -> SILENT ***
003_a~b.md                   | REJ 400       | ok        | false    | *** LOUD -> SILENT ***
003_party-🎉.md              | REJ 400       | ok        | false    | *** LOUD -> SILENT ***
003_re—dash.md               | REJ 400       | ok        | false    | *** LOUD -> SILENT ***
003_my talk.md               | ok            | ok        | false    | already 409 on master
003_a(b).md / 003_a=b.md     | ok            | ok        | false    | already 409 on master
```

### The failure, end to end

The vector is the one §2.5 already establishes as load-bearing — `recoverOrphanedVideos` writing a raw
`readdirSync` entry straight in as `summaryMd` (`pipeline.ts:135-138` → `:105`). A Korean user renames
a summary in Obsidian to `003_돈 버는 방식.md`; the next ingest adopts the on-disk name into the local
row. Then a sync:

1. One-sided → `copyAdditiveVideo(to = cloudSide, …)` (`sync-run.ts:626`).
2. `toBlob.putStaged(toP, video.summaryMd, …)` (`sync-run.ts:263`) — **under v4 this succeeds**
   (measured: `ok`). On master it is `REJ 400`, the throw propagates to the per-video catch at
   `sync-run.ts:812-813`, and the user gets `report.errors` naming the video.
3. `promote`, then `upsertVideo` with `artifacts = { summaryMd: { key, status: 'promoted' } }`
   (`sync-run.ts:~250`), and the post-write verification passes — it checks
   `art.key === video.summaryMd`, which is true.
4. `report.created += 1`. **No error anywhere.**
5. The user opens the document. `loadSummaryForServe` calls `assertCloudSummaryMdKey(mdKey)`
   (`serve-summary-core.ts:61`) → **409 `corrupt summary key`**. `resolveSummaryMdKey`
   (`resolve-summary-key.ts:16`) returns `null`, so the dig path sees no summary at all.

This is the exact shape §3.6 calls *"the most dangerous line in the document"* when round-2 B1 found it
for combining marks — *"v2 would have converted a loud failure into a silent paid-but-unreachable
summary, **which is the exact shape of backlog #36 itself**"*. v4 fixes the combining-mark instance by
widening the guard and leaves the rest of the class open.

**Scoped honestly, in two directions.** (a) The *worker* path cannot reach this: `summary-handler.ts:96`
mints `${padSerial(serial)}_${slugify(title)}`, and `slugify` (`lib/slugify.ts`) emits only
`\p{L}\p{N}` and `-`, so its output always passes the guard — including the empty-slug case `0007_.md`,
which the existing test already pins. The vector is the sync path only. (b) v4 **widens** an existing
hole rather than creating one: four shapes (` `, `(`, `)`, `=`, `%`) are already storable-and-409 on
master. But the hole goes from five ASCII characters to *all of Unicode outside `\p{L}\p{M}\p{N}_-`*,
and it goes from "characters no vault file plausibly has" to "the scripts this slice exists to
support, plus a space".

**What is NOT lost:** the vault copy is intact, and no money moves — the guard runs before
`resolveMagazineModel` (stage 2 of `serve-summary-core.ts`), and `resolveSummaryMdKey` returning null
means no dig is ever enqueued. The consequence is a paid artifact unreachable in the cloud product
behind a record that advertises `promoted`, with the failure moved from sync time to open time.

### Fix

Give the servability question the falsifier the storability question could not have. At the two writers
of a cloud row's `summaryMd` — `sync-run.ts:263`/`:279` (additive) and `:379`/`:399` (Class A) — refuse
a key `assertCloudSummaryMdKey` rejects, and throw, so the per-video catch at `sync-run.ts:812` puts it
in `report.errors` exactly where master puts it. One predicate, reusing the guard that already defines
the answer; no new vocabulary, no enumeration.

**What observation would make it FAIL?** Integration: a local row whose `summaryMd` is `003_a~b.md`
with a real body; run the sync; assert `report.errors` names the video **and** no cloud row exists with
`artifacts.summaryMd.status === 'promoted'`. Against v4 as written the sync reports `created: 1`, the
row says `promoted`, and the serve returns 409. Mutation: remove the refusal → red.

> §9 should be rewritten rather than deleted: its reasoning about *storability* is correct and worth
> keeping, and the correction is that it answered a different question from the one that matters.

---

## H1 — High. §3.5.1 asks the row; the thing that collides is an inode, and the orphaned vault file has no row

Round-3 B1 offered two fixes and said which credential each rests on:

> 1. Make the receiver-side guard normalization-insensitive where the receiver's filesystem is …
> 2. **Or make the guard ask the filesystem instead of the row.** The thing that actually collides is
>    an inode, not a string … That is the credential the honest caller has and the impostor does not,
>    and it is immune to the next normalization surprise.

v4 took (1), via `aliasesUnicodeNormalization` (spec:448-449), and records no reason for preferring it.
The guard it lands in reads the **index**, not the disk:

```ts
// lib/cloud-sync/sync-run.ts:204-210
const holder = idx.videos.find((v) =>
  (video.serialNumber != null && v.serialNumber === video.serialNumber) ||
  (video.summaryMd != null && v.summaryMd === video.summaryMd));
if (holder) { throw new Error(`serial collision: ...`); }
```

So the guard only sees a collision the **index already knows about**. A real `.md` file sitting in the
vault with **no index row** is invisible to it — and that file is not hypothetical: it is exactly the
population `recoverOrphanedVideos` exists to adopt (`pipeline.ts:127-140`), i.e. a paid summary that
has not yet been re-indexed.

Measured on this machine's APFS:

```
readdir raw: 30 30 33 5f 63 61 66 65 301 2e 6d 64     (an NFD file)
existsSync(NFC form of an NFD file): true
statSync ino equal: true
```

Cloud-only video A arrives with the NFC key; the vault holds the NFD file for un-indexed video B. No
holder (no row for B) → `putStaged` → `LocalFsBlobStore.promote`'s `renameSync`
(`local-blob-store.ts:58-62`, with `abs()` an identity map at `:12`) resolves the NFC name to B's
existing inode and replaces its contents. **B's paid summary is gone, silently.** The
`aliasesUnicodeNormalization` comparison never runs, because there is nothing to compare against.

Note the byte-exact instance of this (an orphan file at *exactly* the incoming key) is pre-existing on
master — but the aliasing instance is new, because a cloud row cannot hold a non-ASCII key today, and
option (2) closes **both** for the price of the one it was already going to cost.

### Fix

Add the filesystem credential alongside the row check: refuse the additive create when
`toBlob.exists(toP, video.summaryMd)` is true. `LocalFsBlobStore.exists` is `statSync`
(`local-blob-store.ts:36-39`), which is APFS-insensitive, so it catches the alias without any
normalization vocabulary at all; and `ensureReceiverSlot` has already returned `null` for a row that
exists, so a file present with no row is unambiguously an orphan. Keep `aliasesUnicodeNormalization`
if you want the row check too — it is not wrong, it is just not sufficient — but then say in §3.5.1
why the row is being asked at all when the inode is available.

**What observation would make it FAIL?** Integration on the real FS: an NFD vault file with known
bytes and **no index row**, plus a one-sided cloud video at the NFC key; run the sync; assert it throws
and the file still holds its original bytes. Against v4 as written it returns `created: 1` and the file
holds the cloud body. Mutation: drop the `exists` check → red. (§6 behavior 19 covers only the
*indexed* case, so it stays green through this scenario — worth checking, because a behavior that
passes is what makes the gap invisible.)

---

## H2 — High. Three statements of the encoder's central property, and §6 — the one that becomes a test — is the stale one

§3.2.2 was rewritten in v4 and is unambiguous:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:301-305
#### 3.2.2 The encoder is injective on RAW input — no precondition, no upstream contract
**The contract is: `encodeSegment` is injective over all valid logical segments, as raw JS strings.**
No caller must have normalized anything first; behavior 4's property test quantifies over arbitrary
segments, not over a normalized subset.
```

Three other places were not:

```md
:275   - **Injective over NFC-normalized logical keys.** Stated precisely in §3.2.2 …
:574   | 4 | The encoder is injective **on NFC-normalized** logical keys | property |
:608   **Property tests carry the weight** for 1, 4 and 5. Behavior 4 quantifies over **NFC-normalized**
:609   inputs — stating it that way is what makes it writable at all (round-1 **M2** …)
```

§3.2's own bullet cites §3.2.2 as its authority and then says the opposite of it. §6 row 4 is what §7
turns into a test.

**Consequence.** A property test quantified over NFC-normalized inputs normalizes each sample before
feeding it in, so **no NFD input is ever sampled** — and NFD inputs are precisely (a) what behavior 3
asserts must produce distinct keys, and (b) what this whole slice exists to support (behavior 16). The
single property v4 rests on — *the encoder is injective on raw bytes, so the write address and the
read address are derived from the same string* — is the one the property test is scoped to skip.

It also re-creates the contradiction §7:609 cites round-1 M2 for: behaviors 3 and 4 disagree about
which relation the encoder implements, in the same table, again.

Round-3 B3's second bullet asked for exactly this — *"Drop the qualifier from behavior 4 to match
§3.2.2, and delete the v2 sentence at §7:539-541"*. Its **first** bullet (rewrite row 3) was applied;
this one was not.

> **It then happened a second time, in front of me.** While this review was running, §3.2.2 was
> rewritten in the working tree — its new heading is *"The encoder is injective on RAW input"* and it
> now adds a ⚠ note reading *"Round-4 H1 caught this section still asserting v3's contract after §3.5
> had been rewritten — stale text from a targeted edit, and the most dangerous kind."* The edit fixed
> **the section the finding named** and left :275, :574 and :608 untouched — the two of which become
> the property test. The note diagnoses the pattern correctly in the same commit that re-enacts it.
> This is why the fix has to be *"grep the document for the qualifier"*, not *"edit §3.2.2"*.

**Fix.** Delete the qualifier at :275, :574 and :608-610; state behavior 4 as *"the encoder is
injective on arbitrary raw segments"* and let the generator emit NFD, NFC and mixed forms.
**FAILS IF:** the generator normalizes its samples and the NFC/NFD pair from behavior 3 is unreachable
by behavior 4's test.

---

## H3 — High. §7's "real guard against B1's whole class" cannot fail

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:611-612
A separate test asserts the seam's comparison helpers agree with the encoder about which keys are the
same — that is the §3.5 contract, and it is the real guard against B1's whole class.
```

Under v4 there is no §3.5 contract of that kind — §3.5 now says *"v4 introduces NO equivalence at
all"* (spec:409). And the two subjects the test compares are both byte-exact:

```ts
// lib/storage/blob-store.ts:96-98
export function normalizeLogicalKey(key: string): string {
  return key.split('/').filter((seg) => seg !== '' && seg !== '.').join('/');
}
```

plus an encoder that §3.2.2 declares injective on raw input. "The comparison helpers agree with the
encoder about which keys are the same" is therefore true for every input in the language, and no code
change short of breaking injectivity can redden it. It is v3 residue, and it is the sentence that
tells the implementer which test is load-bearing.

This is the project's own named defect — *a checklist item can be an unfalsifiable guard* — sitting in
the paragraph that assigns the weight.

**Fix.** Delete the sentence. If something is to replace it, the honest replacement is the *structural*
assertion §3.2.2 already argues (spec:315-316): `SAFE` rejects `=`, **and** every hash-branch output
contains `=`. Both go red on the `=`-widening mutation deterministically, which is also what round-3
L1 asked for and what §7's last paragraph already half-adopts.

---

## M1 — Medium. §3.3's fail-closed check inspects the caller's own prefix, and a `=` in a logical key strands the video forever

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:352-353
**The marker check applies to every segment of the relative path the adapter is about to return, and
throws.**
```

`list` returns *the caller's logical prefix* re-attached to the physical remainder (spec:344-346), so
"every segment of the relative path" includes segments the caller supplied and can already name. The
guard's job — the adapter must never return a key it cannot name — is about the remainder only.

Reachable, and `=` is storable on master (re-measured: `003_a=b.md` uploads `ok`). A cloud row whose
`summaryMd` is `003_a=b.md`, diverged from local:

- `paidKeysUnder` → `blob.list(p, 'dig/003_a=b/')` (`reconcile-serial.ts:102`) — **no try/catch**
- the returned key `dig/003_a=b/1234.r1.md` has `=` in segment 2 → the §3.3 guard throws
- the throw escapes `reconcileCloudBase`, is caught per-video at `sync-run.ts:812`, no baseline
  advances → **the video is stranded on every run, forever**

That is round-2 H1a's fails-closed shape (`unmappable-key` → stranded) re-entering through the guard
introduced to fix a fails-open one. It is narrow (needs a divergence) and the video is already
unservable on master, but "unservable" and "blocks its own sync in perpetuity" are different states.

**Fix.** Apply the marker check to the physical remainder the adapter derived, not to the prefix the
caller passed. **FAILS IF:** `list(p, 'dig/003_a=b/')` throws for a caller that supplied that prefix.

---

## M2 — Medium. Two `### 3.5` sections, the first describing a hazard v4 deleted, in the present tense

```
spec:373  ### 3.5 One equivalence relation, not two — the B1 fix
spec:393  ### 3.5 Canonicalize at INGRESS, not at the seam — v3's architectural change
spec:418  #### 3.5.1 The one real equivalence: the local filesystem
```

The first (373-390) walks through `reconcileCloudBase` copying old→new as a no-op, advancing metadata
and then deleting `from` — *"Summary, magazine model and every paid dig section, gone … Reachable via
§2.5's `recoverOrphanedVideos` path."* Under v4 that is **not reachable**: the encoder hashes raw
bytes, so NFC and NFD are distinct physical objects (measured: `SAME PHYSICAL KEY? false`), the copy is
real and `to === from` is the right skip. The section is a live-tense Blocking analysis of a design
that no longer exists, sharing a number with the section that replaced it.

The second's heading still announces v3's change while its body opens *"v4 introduces NO equivalence at
all"*. §3.5.1 is nested under it, and §3.5 is the section every round's findings have come from.

`scripts/check-docs.py` does not catch it — run: `Documentation integrity OK`, exit 0. So this needs a
human edit, not a ratchet.

**Fix.** Renumber, and demote the 373 block to a dated "what v1/v2 got wrong" note or drop it — the
review trail table at spec:11-19 already carries the history.

---

## M3 — Medium. `copyBlob`'s short-circuit is wrong on the aliasing backend but is not reachable — write the real reason down

Brief item 3 asks whether `copyBlob`, `exists`, `promote` or `deletePrefix` should consult
`aliasesUnicodeNormalization`. Measured, per site:

- **`copyBlob` — genuinely wrong, not reachable.** On APFS, `copy(p, NFD, NFC)` does not take the
  `normalizeLogicalKey(from) === normalizeLogicalKey(to)` short-circuit (`blob-store.ts:134`, byte-
  exact → false), reads the source, then reads the destination — which is *the same inode*. Measured:
  `tryGet(to)` returns bytes equal to the source, so `copyBlob` returns `{ok: true, already: true}`.
  A caller that then advances metadata and deletes the source deletes the destination. **Not
  reachable:** `.copy(` has exactly one non-test caller in `lib/`, `app/`, `worker/`, `scripts/` —
  `reconcile-serial.ts:282`, `cloud.blob.copy(...)` — and `reconcileCloudBase` is only ever called with
  `cloudSide` (`sync-run.ts:730-733`), which is byte-exact.
- **`exists` — no.** All five non-test callers are cloud-path staging/dig-enqueue checks
  (`summary-handler.ts:174`, `consistency.ts:29`, `write-dig-section-blob.ts:47`,
  `enqueue-dig-core.ts:39`/`:58`).
- **`promote` — this is H1**, and the right credential there is `exists`, not the flag.
- **`deletePrefix` — no.** Aliasing resolves to the directory the caller meant to delete.

§3.4 clears `copy()` with *"it delegates to `copyBlob`, which re-enters through `tryGet`/`put` with
logical keys"* — which is a correct statement about **encoding** and says nothing about **aliasing**.
The sentence reads as a general clearance and is not one.

**Fix.** One line in §3.4: *"`copy()` is also safe from the local store's normalization aliasing, but
only because it has no local caller (`reconcile-serial.ts:282` is the sole call site and it is
cloud-only). A local `copy` caller must consult `aliasesUnicodeNormalization` or the short-circuit will
report `already: true` for two names of one inode."* That is the kind of fact that gets rediscovered
expensively; it costs a sentence now.

---

## L1 — Low. The `sameKey` snippet names a field the guard's scope does not have

```md
spec:448-449
const sameKey = (a: string, b: string) =>
  to.blob.aliasesUnicodeNormalization ? a.normalize('NFC') === b.normalize('NFC') : a === b;
```

The comparison it replaces is in `ensureReceiverSlot`:

```ts
// lib/cloud-sync/sync-run.ts:164-167
async function ensureReceiverSlot(
  to: MetadataStore, toP: Principal,
  playlistMeta: { playlistUrl: string; playlistTitle?: string }, video: Video,
): Promise<{ serialNumber: number } | null> {
```

`to` there is a `MetadataStore` — no `.blob`. The blob store arrives separately as `toBlob` on
`copyAdditiveVideo` (used at `:263`, `:268`); only the caller at `:620-626` has a `Side` with `.blob`.
Say the receiver blob store must be threaded into `ensureReceiverSlot`, or the implementer will read
the snippet as compiling code.

## L2 — Low. Behavior 22 guards a dissolved defect

```md
spec:592
| 22 | `encodeSegment` is identity-preserving for U+212A (round-2 M1's sole counterexample):
      raw-branch and raw-hash agree | unit |
```

Round-2 M1's U+212A counterexample was a property of **v2's** `normalizeLogicalKey` NFC-equality, which
v4 does not have. And §7's `hash(NFC(s))` mutation is already killed by behavior 3 without it: under
the mutant, `encode(NFC)` and `encode(NFD)` become equal, so row 3's *"encode to **different** physical
keys"* goes red. Round-3 B3 asked for 22 to be replaced with a golden-value assertion or deleted;
neither happened. Keeping a behavior for a dissolved defect is how a suite stops describing the
system — the same call this project made on detached-dig retention.

---

## Verified — checked by hand or by probe, not conceded

- **Round-3 B2 reproduces independently** (top of this review). The NFD write→stage→promote→serve→list
  round trip succeeds under v4 with nothing canonicalized.
- **Brief item 4 — the `\p{M}` widening is SAFE, and I swept it rather than reasoning about it.** All
  **2501** `\p{M}` codepoints are newly admitted by the widening. Of those: **0** contain any of
  `/ \ NUL . % : ~ space` raw, and **0** do under `NFC`, `NFD` **or** `NFKC` — so a combining mark
  cannot introduce a separator or a traversal through any normalization something downstream might
  apply. A leading combining mark is still rejected (the first class stays `[\p{L}\p{N}]`). Against the
  existing suite (`tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`): **18/18** rejection cases
  still rejected (including `nested/foo.md`, `%2f`, U+FF0F, U+2044, U+2215, NUL, newline, tab,
  leading-space, too-long) and **5/5** acceptance cases still accepted. §10's "worth a security
  reviewer's eye" is discharged for separators and traversal. Two residues, neither a finding: 256
  invisible variation selectors are admitted (Mn) — a visual-confusable, not an aliasing risk, since
  v4 keeps keys byte-exact so confusables are distinct objects; and `{0,127}` counts UTF-16 code
  units, so 131 code units of marks render as ~2 characters — not new, master's `\p{L}` already admits
  2-code-unit astral letters.
- **Behavior 17's arithmetic and the identity branch.** The longest key the widened guard admits is
  128 + `.md` = 131 characters; that key is `SAFE` and ≤ `LIMIT`, so `encodeSegment` is identity on it.
- **ADR-0008's grant argument survives.** Measured: the model and PDF physical keys land at
  `models/003_cafe=h….json` and `pdfs/003_cafe=h….pdf` under the same `${p.id}/${p.indexKey}/` prefix
  as the MD, because `objectKey` encodes only `key` (`supabase-blob-store.ts:15-18`).
- **Relocation between two representations is correct under v4** (brief item 2). Local NFD vs cloud
  NFC → `describeDivergence` diverged → `reconcileCloudBase` copies MD + model + digs to genuinely
  distinct physical objects, advances metadata, and the `to === from` skip at `reconcile-serial.ts:359`
  correctly does not fire. Nothing is lost; the cost is N copies, once. This is the case the deleted
  §3.5 (spec:373-390) claims is fatal, and it is not, for exactly the reason v4 gives.
- **§3.3's `list()` caller table is complete.** Non-test `blobStore.list` callers are exactly
  `reconcile-serial.ts:102`, `load-dig-for-serve.ts:34`, `dig-state/route.ts:47` — all `dig/${base}/`,
  all reading ASCII leaves. No production caller passes `''`.
- **The worker path cannot reach B1.** `slugify` (`lib/slugify.ts`) emits only `\p{L}\p{N}` and `-`, so
  `${padSerial}_${slug}.md` always passes the guard, including the empty-slug case the existing test
  pins.
- **The money path is clean for B1's scenario.** `assertCloudSummaryMdKey` runs at
  `serve-summary-core.ts:61`, before `resolveMagazineModel` (stage 2), and `resolveSummaryMdKey`
  returns `null` so no dig is enqueued. Nothing charges.
- **§7's mutation table, row by row.** `\p{M}` revert → 16 red (measured: master guard rejects raw
  NFD). `hash(NFC(s))` → 3 red (NFC/NFD collapse to one key). Encode empty segments → 10 and 11 red
  (`deletePrefix('')` targets `…/=h<hash>` and finds nothing; `dig/b/` and `dig/b` diverge). Flag falsy
  / `a === b` → 19 red *for the indexed case only* (see H1). `SAFE ∪ {=}` → 4 only with the crafted
  preimage §7 now correctly requires. The table is materially better than v2's and v3's; the gaps are
  H2 (row 4's scope), H3 (a test that cannot fail) and the absence of any row for the guard being
  widened **further** — measured: over-widening to `\p{S}` is caught by the existing suite (U+2044,
  U+2215), over-widening to `\p{Zs}` is **not** (the suite's only space case is leading).
- **`check-docs.py` runs green** on the spec as committed (exit 0), so M2 is not something a ratchet
  will surface.

**Not checked:** the §4 gate against a real bucket — still blocked (§4.1, `claude_ro` denied on schema
`storage`); per the project rule, **treat §4 as NOT RUN**, not as passing. Prod's storage-api version.
Linux/ext4 behaviour — every filesystem claim here is APFS, measured; the ext4 half of §3.5.1's ⚠ note
is reasoned from `LocalFsBlobStore`'s identity `abs()`, not measured, and the spec labels it as
accepted.

---

## Verdict

**NOT CONVERGED** — 1 Blocking, 3 High, 3 Medium, 2 Low.

**On whether the slice is mis-scoped: it is not, and I want that stated plainly given the round-4
trigger.** v4's central move is correct and I verified it rather than accepting it. Deleting the
Unicode equivalence is the right answer, it was reached the right way (a measurement that said "this
mechanism is not load-bearing" was read as "delete it" rather than "move it"), and three rounds of
findings genuinely dissolve — the eight comparison sites really are correct unmodified, because two
byte strings really are two keys. The slice's boundary is also right: an encoder at the seam, one flag
for the one backend that aliases, one guard widened, one migration gate. Nothing here argues for a
different shape, and I would not send this to a Phase 6 architecture review looking for one.

What is not finished is narrower and nameable. **Supabase's `400 InvalidKey` was doing safety work
nobody had written down**, and v4 removes it. §3.5.1 accounts for one consequence — the cloud→local
direction that round-3 B1 measured. §9 declines to account for the other, and its reasoning is
subtly right about the wrong question: *storability* has no falsifier once the encoder is total, but
*servability* does, and it is the property the 400 was accidentally enforcing. B1 and H1 are both
instances of that one omission, on the two sides of the seam, and both close with a single refusal
against a credential that already exists in the codebase (`assertCloudSummaryMdKey`, `blob.exists`).

The remaining Highs are documentation-of-the-falsifier problems, not design problems: v4 rewrote
§3.2.2 and §6 row 3 correctly and left three sentences from v2/v3 saying the opposite, one of which
tells the implementer that a test which cannot fail is the primary guard. That is the pattern round 3
named — *each version's falsifier is written against the version being replaced* — surviving in the
sentences nobody re-read because the section around them changed.

I would expect v5 to converge.
