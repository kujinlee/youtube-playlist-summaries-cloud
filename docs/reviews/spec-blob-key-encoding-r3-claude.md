# Adversarial design review — cloud blob key encoding (backlog #36), round 3, Claude half

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` (draft **v3**)
**Branch:** `fix/cloud-blob-key-encoding` @ `ca856de`
**Reviewer:** Claude (round-3 Claude half). Not the author of the round-1 or round-2 Claude reviews.
**Date:** 2026-08-14

**Verdict: NOT CONVERGED** — 3 Blocking, 2 High, 2 Medium, 1 Low.

Everything labelled *measured* below was run, not recalled: the v3 encoder transcribed verbatim from
§3.2 and driven against the live local stack (`http://127.0.0.1:54321`, `artifacts` bucket, service
role — the probe refuses any host that is not `127.0.0.1`/`localhost` and removed all 3 objects it
wrote; `residual under probe root: []`), and filesystem behaviour against this machine's APFS root
volume. Node v22.14.0.

**The central claim, judged.** §3.5 asserts that moving canonicalization to ingress *dissolves* five
round-2 findings. Two separate things are true and the spec conflates them:

- **Returning the encoder to raw-byte hashing (§3.2) genuinely dissolves most of them.** With raw
  hashing, byte-different keys are different physical objects, so byte-exact comparison and physical
  identity agree exactly as they do on master. That is a real architectural improvement and I could
  not break it on the Supabase backend.
- **Ingress canonicalization (§3.5) is doing much less than the spec credits it with, and where it is
  load-bearing it does not reach.** It does not reach the one receiver that is *not* a cloud row —
  the local vault, which §3.5 line 390 explicitly excludes — and that is where site 3 of its own
  table lives (B1). And the evidence apparatus offered to prove any of it is inert (B2, B3).

**The ingress enumeration itself is complete, and I am saying so rather than inventing a fourth
site.** I enumerated every writer of a `summaryMd` value into a cloud row:
`summary-handler.ts:157`, `sync-run.ts:279`/`:399`/`:430`, and `reconcile-serial.ts:295-296` (whose
`newBase` comes from `describeDivergence`). Those are exactly §3.5's three points. `dig-handler.ts:55`,
`resolve-summary-key.ts:14`, `serve-summary-core.ts:56`, `MODEL_KEY` (`model-store.ts:31`),
`pdf-path.ts:20` and `digSectionKey` (`dig-blob-key.ts`) all *derive* from a key already in the row.
`dig-section.ts:106` — the only writer of `digDeeperMd` — is the local path
(`path.join(outputFolder, …)`), and `sanitizeAdditiveVideo` nulls `digDeeperMd` at `sync-run.ts:133`,
so a cloud row cannot acquire one except from `reconcile-serial.ts:306`. The fourth ingress point is
not there. **The hole is not a missing site; it is a missing direction.**

---

## Summary of findings

| # | Sev | One line |
|---|---|---|
| B1 | **Blocking** | §3.5's site 3 (`sync-run.ts:206`) is **not** dissolved. Ingress canonicalizes the *sender's* key, but on a cloud→local additive create the *receiver* is the vault, which §3.5:390 refuses to canonicalize — so the byte-exact collision guard still misses, and `LocalFsBlobStore.promote`'s `renameSync` silently overwrites a paid vault summary. Measured on APFS. Unreachable on master; the slice is what makes it reachable |
| B2 | **Blocking** | Behavior 16 — the only money-observable falsifier §10 offers for §3.5 — is **vacuous again**. Measured live: the whole NFD write→serve round trip succeeds with ingress canonicalization removed, because raw hashing (§3.2) plus the §3.6 NFC belt make the NFD path self-consistent. §7's "drop NFC from any one of the three ingress points → 16" survives for all three, and "drop the NFC belt → 16" survives too. The same shape as round-2 B2, which v3 claims to have fixed |
| B3 | **Blocking** | §6 behavior 3 — "NFC and NFD forms of one segment encode to the **same** physical key" — is **false under v3** (measured) and was not updated when §3.2 went back to raw hashing. Implementing §6 as written re-introduces v2's NFC hashing and with it all five round-2 findings. §6 row 3 and §7's mutation row 5 demand opposite code |
| H1 | High | Behavior 20's check script enforces the **v2** architecture. §3.5 says every downstream comparison is correct *without being modified*; the script fails a comparison that is not wrapped in the canonicalizer. Its stated FAILS-IF is not an instance of its own rule, and its vocabulary omits `baseName` (ingress point 1) and `digDeeperMd` |
| H2 | High | §3.6's `assertCloudSummaryMdKey` NFC belt has no reachable beneficiary I could construct, and it destroys the only *runtime* observation that would falsify §3.5's invariant. It also validates a different string from the one `base`/`MODEL_KEY`/`pdfRelPath` are built from, falsifying the guard's own docstring |
| M1 | Medium | §3.5 point 1's "NFC it at mint" has two readings that produce **different bases**, not different normalizations, because `slugify` maps combining marks to `-`. Measured: NFD `café` → slug `cafe`, NFC `café` → slug `café`. Only one reading addresses the reason the sentence gives |
| M2 | Medium | §3.5's ⚠ APFS note is **verified** (measured) but understates the non-APFS case: the cloud→local Class-A transfer rewrites the local **index row's key** (`sync-run.ts:399`), not merely creating a duplicate file. The risk is not in §10 |
| L1 | Low | §7's mutation "widen `SAFE` to include `=` → behavior 4" cannot be killed by the sampling property test §7 assigns to behavior 4; it needs a crafted preimage |

---

## B1 — Blocking. Ingress canonicalizes the sender; the receiver of a cloud→local additive create is the vault, which §3.5 refuses to canonicalize — and the collision guard there overwrites a paid summary

§3.5's own site table names this site and claims ingress closes it:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:368
| `sync-run.ts:206` — additive collision guard | fails **open**: the guard's own comment says a key collision here *destroys a summary* via promote-as-rename (found by mechanical sweep) |
```

and then, four lines above the fix it is supposed to be part of:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:390-391
**What this does NOT change: the vault.** Canonicalization applies to the key entering the *cloud
record*, never to a file on disk. §1 decision 1 holds — no vault file is renamed.
```

Those two sentences are in tension, because **the additive create runs in both directions.**

```ts
// lib/cloud-sync/sync-run.ts:618-627
const presentIsLocal = lv != null;
...
const from: Side = presentIsLocal ? localSide : cloudSide;
const to: Side = presentIsLocal ? cloudSide : localSide;
const body = await readMdBody(from.blob, from.p, present);
await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
```

When the video is **cloud-only**, `to` is `localSide`: the receiver store is the local index and the
receiver blob store is `LocalFsBlobStore`. So the guard §3.5 lists as a "cloud-sync comparison site"
is, on this branch, comparing a canonical cloud key against **vault rows that §3.5 has just promised
not to canonicalize**:

```ts
// lib/cloud-sync/sync-run.ts:203-213
if (video.serialNumber != null || video.summaryMd) {
  const holder = idx.videos.find((v) =>
    (video.serialNumber != null && v.serialNumber === video.serialNumber) ||
    (video.summaryMd != null && v.summaryMd === video.summaryMd));
  if (holder) { throw new Error(`serial collision: ...`); }
}
```

The guard's own comment already names the exact shape that defeats the serial disjunct:

```ts
// lib/cloud-sync/sync-run.ts:199-202
// A legacy receiver row carrying `003_alpha.md` with NO serialNumber — exactly the shape
// `backfillOrder` exists to repair — passes a serial-only check, and the blob write below then
// puts the sender's body straight over it: on the local FS adapter promote is a rename, which
// overwrites, so a summary is destroyed. (Found by the branch adversarial pass.)
```

### The failure, end to end

State:
- Vault (macOS, APFS) holds `003_café.md` in **NFD** — video **B**'s paid summary. Its local index row
  carries that key verbatim and **no `serialNumber`** (the legacy shape the comment names; the raw
  `readdirSync` bytes reach `summaryMd` via `lib/pipeline.ts:135-138` → `:105`, which §2.5 already
  establishes as load-bearing).
- Cloud holds video **A** with `summaryMd = '003_café.md'` in **NFC** — canonical, exactly as §3.5's
  invariant requires — and a promoted blob. A is not in the local index.

Run a sync:

1. A is one-sided → `copyAdditiveVideo(to = localSide, …)`.
2. `ensureReceiverSlot`: B has `serialNumber == null`, so the serial disjunct is false; the key
   disjunct is `v.summaryMd === video.summaryMd`, i.e. NFD `===` NFC → **false**. No holder. Proceed.
3. `putStaged` then `promote` at `sync-run.ts:263`/`:268`:

```ts
// lib/storage/local/local-blob-store.ts:58-62
async promote(ref: StagedRef): Promise<void> {
  const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
  if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
  fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
}
```

with `abs` an identity map (`local-blob-store.ts:12`, `path.join(p.indexKey, key)`) — §3.4 keeps it
that way deliberately.

**Measured on this machine's APFS root volume:**

```
files after promote: 1 [ '30 30 33 5f 63 61 66 65 301 2e 6d 64' ]   // still the NFD name
video B's file now holds: VIDEO-A-BODY-FROM-CLOUD
```

`renameSync` to the NFC name resolved to the existing NFD file and replaced its contents. The
directory still shows **one** file, still spelled NFD. **B's paid summary is gone**, B's index row
still points at that filename, and it now serves A's body. `report.created += 1`. Nothing throws.

Note this is the same APFS property the spec relies on *favourably* in its ⚠ note at line 394-397
("On APFS that resolves to the existing file"). It resolves to the existing file in both directions;
one of them is a silent overwrite of paid content.

### Why the slice is what makes this reachable

On master, A cannot exist: `upload('003_café.md')` is rejected `400 Invalid key` (§2.1, re-measured in
round 2), so no cloud row is ever written with a non-ASCII summary key. The encoding is what makes A
representable. This is the same conversion round-2 B1 identified — a loud failure becoming a silent
paid-artifact loss — relocated from the serve boundary to the vault.

### Why ingress canonicalization cannot fix it as specified

The guard compares a **canonical sender key** against **non-canonical receiver rows**. §3.5's
invariant is scoped to "keys that reach cloud reasoning"; the local index is explicitly outside it.
Canonicalizing both operands of the comparison would work — but that is precisely the per-comparison
patching v3 deleted, and it is the shape H1 says the check script would demand.

### Fix

Two candidates, both stateable as gates:

1. **Make the receiver-side guard normalization-insensitive where the receiver's filesystem is**
   — compare `NFC(v.summaryMd) === NFC(video.summaryMd)` at `sync-run.ts:206` **only** on the local
   receiver branch, and say in §3.5 that the vault's *comparisons* are canonical even though its
   *filenames* are not. This is one site, in one direction, with a written reason — not an
   enumeration.
2. **Or make the guard ask the filesystem instead of the row.** The thing that actually collides is
   an inode, not a string: have the local additive path refuse when `LocalFsBlobStore` reports the
   final key already exists and is not this video's. That is the credential the honest caller has and
   the impostor does not, and it is immune to the next normalization surprise.

**What observation would make it FAIL?** Integration test on the local adapter: a receiver row with
`serialNumber: null` and `summaryMd` = NFD `003_café.md`, a real file at that name holding known
bytes, a one-sided cloud video with the NFC key; run the sync; assert it **throws `serial collision`**
and the vault file still holds B's bytes. Against v3 as written it returns success and the bytes are
A's. Mutation: remove the fix → red.

---

## B2 — Blocking. Behavior 16 is vacuous again, and I measured it: the NFD path is self-consistent with ingress canonicalization removed

§10 names behavior 16 as the measurement that turns §3.5's claim from argument into evidence:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:639
| §3.5's ingress canonicalization is claimed to dissolve five round-2 findings | **Round 3 must attack
this claim specifically.** … it is an argument, not a measurement, until behaviors 16 and 19–20 exist |
```

and §6 asserts the new version cannot be short-circuited the way v2's was:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:530-531
v3's version asserts an observable the user cares about — the summary serves — through a path that
cannot be short-circuited by the fix under test.
```

**It can.** I transcribed §3.2's encoder verbatim (raw hashing, per the v3 note at :220-227) and ran
both worlds against live Storage:

```
NFC = 30 30 33 5f 63 61 66 e9 2e 6d 64
NFD = 30 30 33 5f 63 61 66 65 301 2e 6d 64
encode(NFC) = 003_caf=hFWAbLG4cfrk4vnNWSoWjal.md
encode(NFD) = 003_cafe=hOW3J8pKhOv-IbHnShk7-Xm.md
SAME PHYSICAL KEY?  false

--- Scenario A: ingress canonicalization ON (row holds NFC) ---
UPLOAD ACCEPT   .../003_caf=hFWAbLG4cfrk4vnNWSoWjal.md
serve reads row key NFC -> {"ok":true,"body":"PAID-SUMMARY-BODY"}

--- Scenario B: MUTANT — drop NFC at ingress point 2 (row holds NFD) ---
UPLOAD ACCEPT   .../003_cafe=hOW3J8pKhOv-IbHnShk7-Xm.md
serve reads row key NFD -> {"ok":true,"body":"PAID-SUMMARY-BODY"}

--- putStaged/promote on the raw NFD key ---
UPLOAD ACCEPT   .../_staging/<uuid>/003_cafe=hOW3J8pKhOv-IbHnShk7-Xm.md
move -> OK
download promoted -> {"ok":true,"body":"STAGED-BODY"}
```

Behavior 16 is *"A video whose `summaryMd` is `003_café.md` in NFD syncs, and the summary then SERVES
200 with the right bytes, ledger unmoved"* (§6 line 518). Trace it under the mutant:

- `copyAdditiveVideo` stages and promotes at the **raw NFD** key → `encodeSegment(NFD)` → an accepted
  physical object (measured above, including the `_staging/<uuid>/` → `move` promote).
- The row is written with the raw NFD key (`sync-run.ts:279`).
- `serve-summary-core.ts:61-64` calls `assertCloudSummaryMdKey(mdKey)` — which under §3.6's belt tests
  `mdKey.normalize('NFC')`. Measured: `guard NFC(NFD): true`. **Passes.**
- `blobStore.get(principal, mdKey)` with the raw NFD key → `objectKey` → `encodeSegment(NFD)` → the
  **same physical object that was written**. 200, right bytes, ledger unmoved.

**Behavior 16 is green with ingress point 2 removed.** The mutation §7 row 1 names —

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:551
| Drop NFC from any one of §3.5's three ingress points | 16 (serve 200), and 19 |
```

— survives. And it survives for the other two points for a simpler reason: behavior 16 is an
**additive one-sided sync**, so it never runs the worker (`summary-handler.ts:96`, point 1) and never
reaches `reconcileCloudBase` / `describeDivergence` (point 3, `reconcile-serial.ts:151-155`). Behavior
16 executes **zero of the three ingress points as load-bearing code.**

Worse, §7 row 6 is the mirror image:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:556
| Drop the `assertCloudSummaryMdKey` NFC belt | 16 |
```

With ingress canonicalization *in place* the row holds NFC, and `guard raw NFC: true` (measured) —
so dropping the belt changes nothing and **that mutation survives too**. The two mechanisms mask each
other: behavior 16 only goes red if you remove **both**. Removing either alone is invisible.

This is the identical defect round-2 B2 raised, and which §6 line 526-531 says v3 fixed: *"a mutation
that names a **mechanism** proves nothing when a sibling mechanism hides it."* The sibling here is
the belt, introduced by round 2's own fix.

### What behavior 16 *is* good for, and what is missing

Behavior 16 is a genuinely valuable test — it is the falsifier for **v2's** B1 (storable-but-
unservable), and it would go red against v2. Keep it. It is simply not evidence about §3.5.

**Fix.** §3.5's invariant needs a falsifier whose observable is *the state of the cloud row*, because
that is what the invariant is about, and it must not be maskable by a self-consistent alternative
universe:

- **16a (worker, point 1):** ingest a video whose title's slug is non-canonical; assert the persisted
  `videos.data->>'summaryMd'` is byte-equal to its own NFC form. Fails if point 1 is dropped;
  cannot be masked, because the assertion is on the stored bytes, not on a round trip.
- **16b (sync, point 2):** additive-sync an NFD key; assert the **cloud row** holds the NFC form —
  not merely that the serve returns 200.
- **16c (divergence, point 3):** two-sided video, local NFD vs cloud NFC, run the sync **twice**;
  assert `action: 'agreed'` on both runs and `copied === 0`. Without point 3 the first run performs a
  real relocation (raw hashing makes them distinct objects, so it copies and deletes) — observable as
  `action: 'relocated'`, and the ledger assertion stays on the M3.1-A pattern.

Then re-derive §7's rows against those, one mutation per mechanism, and check them by *running* the
mutant rather than by reasoning about it — the two masking pairs above both look correct on paper.

---

## B3 — Blocking. §6 behavior 3 is false under v3, and implementing §6 as written re-creates v2's encoder

§3.2's v3 note is unambiguous about what changed:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:220-221
> ⚠ **v3: the encoder hashes the RAW segment. v2 hashed `NFC(s)`, and that was the root of five
> round-2 findings.**
```

```
encodeSegment(s):
  ...
  return `${head}=h${base64url(sha256(utf8(s)))...}`     // :218 — utf8(s), not utf8(NFC(s))
```

§6 was not updated:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:505
| 3 | NFC and NFD forms of one segment encode to the **same** physical key | unit |
```

**Measured: `SAME PHYSICAL KEY? false`** — `003_caf=hFWAbLG4cfrk4vnNWSoWjal.md` vs
`003_cafe=hOW3J8pKhOv-IbHnShk7-Xm.md`. (Note even the `head` runs differ: NFD's leading
`[A-Za-z0-9._-]` run swallows the base `e`, NFC's stops at `f`. So this is not a near-miss that a
loose assertion might tolerate.)

Behavior 3 is not a stale sentence in prose — §6 is the behavior table §7 turns into tests, and §7
assigns it "unit". A TDD implementer writing behavior 3 red-first has exactly one way to make it
green: hash `NFC(s)`. That is v2's encoder, and §3.2's own note says it is *"the root of five round-2
findings"*, including Codex's r2 Blocking (two videos' bases aliasing onto one physical object) and
round-1's B1 (cleanup deleting the object the row now points at — paid summary, model and every dig
section).

The contradiction is internal and mechanical: **§6 row 3 and §7 row 5 demand opposite code.**

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:555
| Hash `NFC(s)` instead of `s` in the encoder | 22 (U+212A) |
```

§7 lists hashing `NFC(s)` as the *mutation*. §6 lists its result as the *required behavior*. One of
them is wrong, and the tests will encode whichever the implementer reads first.

Row 4 has the same staleness, one step milder:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:506
| 4 | The encoder is injective **on NFC-normalized** logical keys | property |
```

against §3.2.2's heading — *"The encoder is injective, full stop"* (:276) — and §7's retained v2
sentence at :539-541, *"Behavior 4 quantifies over **NFC-normalized** inputs — stating it that way is
what makes it writable at all"*. §3.2.2 exists specifically to say that qualifier is gone.

Also stale in the same sweep: §7's *"A separate test asserts the seam's comparison helpers agree with
the encoder about which keys are the same — that is the §3.5 contract"* (:543-544). Under v3
`normalizeLogicalKey` (`blob-store.ts:96-98`) is byte-exact and the encoder is byte-exact, so that
test is trivially true for every input and can never fail. It is a passing test that measures nothing.

**And nothing else guards raw hashing.** Behavior 22 (§6:524, *"`encodeSegment` is identity-preserving
for U+212A … raw-branch and raw-hash agree"*) does not detect the mutation: under `hash(NFC(s))`,
`'003_KK.md'` still takes the hash branch and still produces an output distinct from the identity
output for ASCII `'003_K.md'`. Only an exact golden-value assertion (`… === '003_K=h' +
b64url(sha256(utf8(raw))).slice(0,22) + '.md'`) kills it, and "identity-preserving … raw-branch and
raw-hash agree" does not say that. So the single change that dissolves the five round-2 findings has
**no behavior that goes red when it is reverted.**

### Fix

- **Rewrite behavior 3** to the property v3 actually holds and that a reader will otherwise assume the
  opposite of: *"NFC and NFD forms of one segment encode to **different** physical keys — the seam
  identifies nothing that the caller has not already identified."* Its mutation is §7 row 5.
- **Drop the qualifier from behavior 4** to match §3.2.2, and delete the v2 sentence at §7:539-541.
- **Replace behavior 22** with the golden-value assertion, or delete it: round-2 M1's U+212A
  counterexample was a property of v2's `normalizeLogicalKey` NFC-equality, which v3 removes. Keeping
  a behavior for a dissolved defect is how a test suite stops describing the system (cf.
  `docs/reviews/` on detached-dig retention: retiring the rule dissolved the finding).
- **Delete or restate the comparison-agreement test** (§7:543-544); as written it cannot fail.

---

## H1 — High. Behavior 20's check script enforces the v2 architecture, and its stated FAILS-IF is not an instance of its own rule

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:401-406
add **`scripts/check-key-canonicalization.py`**: fail if a key-valued expression
(`summaryMd`, `baseOf(…)`, `newBase`, `oldBase`, `mdKey`) crosses into `lib/cloud-sync/` or the cloud
metadata write path without passing the exported canonicalizer, outside an explicit allowlist.
**FAILS IF:** a raw `cv.summaryMd === lv.summaryMd` is added to `reconcile-serial.ts` and the script
stays green.
```

Three problems, in increasing order of consequence.

**(a) The FAILS-IF is not reachable from the rule.** The rule is about a value *crossing into*
`lib/cloud-sync/`. In `cv.summaryMd === lv.summaryMd`, both operands are already inside
`lib/cloud-sync/` and neither crosses anything. A script implementing the stated rule stays green on
the stated counterexample. This is the shape the project's own instrument already names — *a
checklist item can be an unfalsifiable guard*: the criterion and the guard describe different
subjects, so ticking one says nothing about the other.

**(b) If it *is* implemented to catch that comparison, it enforces v2 and contradicts §3.5.** Four
paragraphs earlier the spec states the opposite:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:374-376
**v3 puts canonicalization where keys ENTER cloud reasoning.** Then every comparison downstream is
comparing two canonical values, so all eight sites are correct *without being modified* …
```

Under v3, a raw `cv.summaryMd === lv.summaryMd` in `reconcile-serial.ts` is **correct code**. A script
that reddens on it is asking every comparison to be wrapped in the canonicalizer — the per-site
patching v3 deleted — and its allowlist would have to contain every existing byte-exact comparison in
the file, i.e. the hand-written list §3.5 says is *"the finding"*.

**(c) The vocabulary omits the two identifiers that matter.** `baseName` — the variable at ingress
point 1 (`summary-handler.ts:96`, `const baseName = \`${padSerial(serial)}_${slugify(payload.title)}\``)
— is not in the list, and neither is `digDeeperMd`, which `paidKeysUnder` (`reconcile-serial.ts:99-100`)
feeds into `remap`'s basename comparison at `:133`. So the mutation "drop NFC from ingress point 1"
leaves the script green (wrong vocabulary) *and* behavior 16 green (B2) *and* behavior 19 green unless
the test constructs an NFD-jamo title.

**Fix.** State the invariant the way v3 actually holds it, and guard *that*: **a value assigned to a
cloud row's `summaryMd`/`artifacts.summaryMd.key` must be a call to the exported canonicalizer or a
value derived from one.** That is an ingress check over four literal write sites
(`summary-handler.ts:157`, `sync-run.ts:279`/`:399`/`:430`, `reconcile-serial.ts:295-296`), which is
small enough to be exact rather than heuristic. **FAILS IF:** the NFC call is removed from any one of
them, or a fifth writer of that field is added and not routed through it. Add `baseName` and
`digDeeperMd` to the vocabulary. Note this check is *static*; combined with H2 there is currently no
runtime observation of the invariant at all.

---

## H2 — High. The `assertCloudSummaryMdKey` NFC belt has no reachable beneficiary, masks ingress failures, and validates a different string from the one used downstream

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:430-432
**v3 fixes it in both directions:** §3.5's ingress canonicalization means the DB holds the NFC
representative, so the guard sees the form it admits; and as a belt, `assertCloudSummaryMdKey`
tests `mdKey.normalize('NFC')` so a row already written stays servable.
```

**Which row?** I tried to construct the beneficiary and could not:

- A cloud row whose `summaryMd` is **non-ASCII** cannot have been written on master. Every write
  reaches Storage through the seam (§9, verified in round 1 by both halves), and `upload` of a
  non-ASCII key is rejected `400 InvalidKey` (§2.1). In `summary-handler.ts` the `putStaged` at
  `:170` throws before `persist_summary`; in `copyAdditiveVideo` the `putStaged` at `sync-run.ts:263`
  throws before `upsertVideo` at `:286`. So such rows do not exist — that *is* backlog #36.
- A cloud row whose `summaryMd` is **ASCII** is already NFC (NFC is the identity on ASCII;
  re-measured in round 2, "SAFE ascii changed by NFC: 0"). The belt is a no-op for it.

So the only rows the belt makes servable are ones written **after** this slice ships — i.e. rows that
exist *because ingress canonicalization failed*. Its sole reachable effect is to hide a violation of
§3.5's invariant, which is exactly the mechanism that makes behavior 16 inert (B2). For a
pre-existing non-ASCII row the belt changes a 409 `corrupt summary key` into a 409 `repair needed`
(`serve-summary-core.ts:65`, the blob is absent) — the same status, a better message, and no
servability gained.

**Second, smaller problem: it validates a string that is then not used.** The guard's docstring states
its job:

```ts
// lib/html-doc/assert-cloud-summary-md-key.ts (docstring)
It is the hard boundary before `models/{base}.json` / `pdfs/{base}.pdf` keys are built
```

but the caller builds from the raw key:

```ts
// lib/html-doc/serve-summary-core.ts:61-71
try { assertCloudSummaryMdKey(mdKey); } catch { return { ok: false, status: 409, error: 'corrupt summary key' }; }
const mdBytes = await bundle.blobStore.get(principal, mdKey);
...
const base = mdKey.replace(/\.md$/, '');
```

With the belt, the validated subject is `NFC(mdKey)` and the built subject is `mdKey`. I checked the
dangerous direction and it is **not** exploitable — NFC has only canonical decompositions, so it can
neither introduce nor remove `/`, `\0` or `%`, and `resolveSummaryMdKey` (`resolve-summary-key.ts:16`)
returns the raw key on the same basis. But the length bound *is* evadable (NFC composes 2 code points
into 1, so a raw key well over the regex's 131 admits), and the docstring's claim becomes false. A
guard that no longer governs the string it protects is the kind of line that gets trusted later.

**Fix.** Invert it. If §3.5's invariant is real, the runtime boundary should **assert it**, not
tolerate its violation: reject a key that is not already NFC (`mdKey !== mdKey.normalize('NFC')` →
409), which gives the invariant a failing observation at runtime and makes behavior 16 non-vacuous for
ingress point 2 for free. If instead the belt stays, §3.6 must name the row it rescues — and if none
can be named, per this project's own rule that is not a belt, it is a suppressed alarm.

---

## M1 — Medium. "NFC it at mint" has two readings that produce different **bases**, not different normalizations

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:381-382
1. **Worker persist** — `lib/job-queue/summary-handler.ts:96` mints `baseName` from `slugify(title)`,
   whose input is a YouTube API string of unknown normalization. NFC it at mint.
```

"it" can be the `baseName` or the `title`, and the two are not equivalent, because `slugify` is
normalization-**destroying**, not normalization-preserving:

```ts
// lib/slugify.ts
return title.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 60);
```

A combining mark is `\p{Mn}` — neither `\p{L}` nor `\p{N}` — so it is replaced by `-`. Measured:

```
slugify(NFC 'Café')  -> 'café'
slugify(NFD 'Café')  -> 'cafe'      // U+0301 → '-', then trailing '-' stripped
```

Those two are not canonically equivalent; NFC applied *afterwards* cannot merge them. So:

- **NFC(baseName)** satisfies the invariant (the output is canonical) but does **nothing** about the
  reason the sentence gives — "an input of unknown normalization". Two ingests of the same video with
  the title arriving in different normalizations still mint two different bases.
- **NFC(title)** addresses that, and still satisfies the invariant.

Korean — the script every behavior in §6 names — hides the difference: Hangul conjoining jamo are
`\p{Lo}`, so `slugify` **keeps** them and the two forms stay canonically equivalent. Accented Latin,
which §2.1 went out of its way to promote to first class, is where they diverge. This is the third
time in this spec that a claim checked only against Korean has been wrong for accented Latin
(round-2 B1, §2.1's own correction, and this).

**Fix.** Say which: `slugify(title.normalize('NFC'))`, i.e. canonicalize the **input**, and state that
it is the input because `slugify` erases the distinction. Behavior: two ingests of one title in the
two normalizations produce the **same** `baseName` — which is red under the `NFC(baseName)` reading
and green under the other, so it distinguishes them.

---

## M2 — Medium. The APFS note is verified, but the non-APFS consequence is understated and is not in §10

The note:

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:394-397
> ⚠ **Known property, stated rather than discovered:** a cloud→local sync writes the local file under
> the canonical key. On APFS that resolves to the existing file (macOS normalizes filenames), so a
> vault with an NFD name gains nothing new. On a case-sensitive, non-normalizing Linux vault it would
> create a second file.
```

**The APFS half is correct — I measured it rather than accepting it:**

```
wrote NFD file. readdir raw codepoints: [ '30 30 33 5f 63 61 66 65 301 2e 6d 64' ]
existsSync(NFC form): true
readFile(NFC form): ORIGINAL-NFD-BODY
after writing NFC, readdir entries: 1   [ '30 30 33 5f 63 61 66 65 301 2e 6d 64' ]
```

APFS is normalization-**insensitive** for lookup and normalization-**preserving** for storage: the NFC
write hit the existing file and the on-disk name stayed NFD. Verified, not conceded.

**The other half is understated.** `transferClassA` does not only write a file — it writes the
**local index row's key**:

```ts
// lib/cloud-sync/sync-run.ts:379, :399, :432
const key = winnerVideo.summaryMd;
...
const completeTuple: any = { summaryMd: key, ... };
await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
```

`loser` is the local side whenever the cloud wins Class A. So on a non-normalizing filesystem the
outcome is not "a second file" — it is: the local row now advertises the NFC key, the original NFD
file is orphaned (with the user's wiki-links pointing at it), and every derivation from
`basename(summaryMd)` moves with the row while the paid companion does not —
`lib/dig/batch.ts:35` (`companionRel = basename(video.summaryMd, '.md') + '-dig-deeper.md'` when
`digDeeperMd` is null) and `lib/pdf/pdf-path.ts:19-20`.

It is genuinely accepted-not-solved territory, and the vault is macOS in practice. But the note lives
only in §3.5 prose; **§10's risk table does not carry it**, and §10 is where a reader looks for what
this slice knowingly leaves broken.

**Fix.** Add a §10 row: *"On a non-normalizing local filesystem, a cloud-wins Class-A transfer
re-keys the local index row and orphans the NFD file and its dig-deeper companion. Accepted; APFS is
insensitive (measured 2026-08-14)."* If it is ever not accepted, the fix is `findByNormalizedName`
(`serial-migrate-exec.ts:26`), which the note already points at.

---

## L1 — Low. §7's `=`-widening mutation cannot be killed by the property test it is assigned to

```md
docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:552
| Widen `SAFE` to include `=` | 4 (injectivity) |
```

§7 assigns behavior 4 to a property test (*"Property tests carry the weight for 1, 4 and 5"*). The
collision that widening `SAFE` creates requires the identity branch to emit a string the hash branch
also emits — e.g. the literal input `003_caf=hFWAbLG4cfrk4vnNWSoWjal.md`, which is the hash output for
`003_café.md`. A generator sampling random Unicode segments will never produce a 22-character
base64url digest of another sampled input. The mutation survives an honest property test.

**Fix.** Make behavior 4's guard **structural**, which is what §3.2.2 actually argues: *"a hashed
segment contains `=`, which `SAFE` forbids"* (:285-287). Assert that directly — `SAFE` rejects `=`
**and** every hash-branch output contains `=` — plus one unit test with the crafted preimage pair
above. Both go red on the mutation, deterministically.

---

## Verified — checked by hand or by probe, not conceded

- **The ingress enumeration is complete for `summaryMd`.** Every writer into a cloud row is one of
  §3.5's three points (list and reasoning at the top of this review). I specifically checked
  `claimVideoSlot`/`persist_summary` (the coalesce at 0021:135 resolves between two values that are
  both canonical under the invariant), `applySerial` (`serial-filename.ts:20-26` — pure string
  surgery on an already-canonical key), `backfillOrder` (`serial-assign.ts:8` — orders videos, mints
  no key), `digSectionKey`, `MODEL_KEY`, `pdfRelPath`, the share path (`share/serve.ts:44-45` — read
  only) and `scripts/cloud-sync.ts` (constructs adapters, writes no key). **B1 is not a fourth
  ingress point; it is the third point applied in the reverse direction.**
- **Raw-byte hashing genuinely dissolves round-2's aliasing findings on the Supabase backend.**
  Measured: `encode(NFC) !== encode(NFD)`. So the occupancy `holder` check (`reconcile-serial.ts:193-196`),
  the plan's collision `Set` (`:262-276`) and the `to === from` cleanup skip (`:358-360`) are all
  comparing keys whose byte-equality and physical-equality now agree — the same relation master has.
  Codex's r2 Blocking and Claude r2 H1b are genuinely gone, and gone by construction rather than by
  enumeration. This is the good part of v3 and I want it recorded as such.
- **`copyBlob`'s short-circuit is safe again.** `normalizeLogicalKey` (`blob-store.ts:96-98`) stays
  byte-exact and v3 drops the v2 change to it, so `blob-store.ts:134` and the encoder agree. Round-2
  M1's U+212A counterexample was a property of that v2 change and does not survive its removal.
- **The `=h` marker and the `_staging` promote path work end to end on a hashed key.** Measured:
  upload of `_staging/<uuid>/003_cafe=h….md` ACCEPT, `move()` to the final hashed key OK, download of
  the promoted object returns the staged bytes.
- **APFS is normalization-insensitive and normalization-preserving** (measured; §3.5's note is right,
  and it is also what makes B1 silent).
- **Behavior 17's arithmetic.** `CLOUD_SUMMARY_MD_KEY` is `^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$` →
  1 + 127 = 128-char base + `.md` = 131 characters, comfortably inside `LIMIT = 255`, so the identity
  branch covers the longest admissible key. §3.2's `LIMIT = 255` and §4's vacuous length half hold.
- **Behavior 5's bound.** 32 (head) + 2 (`=h`) + 22 (digest) + 9 (`\.[A-Za-z0-9]{1,8}`) = 65. Correct.
- **§4's no-migration argument is unaffected by anything above** — it is about bucket object names,
  all of which are ASCII, and NFC is the identity on ASCII. §4.1's "cannot run" is correctly recorded
  as a failure rather than a pass.

## What I checked that would have found a defect of each class, and what I did not

- *A missing ingress point* (the brief's item 1): enumerated every `summaryMd` writer across `lib/`,
  `app/`, `scripts/`, `worker/` and traced each derived-key builder back to its source row. Found no
  missing site — found a missing **direction** (B1).
- *Something that depended on the raw bytes* (item 2): measured APFS lookup, write and `renameSync`
  across normalization forms; traced the cloud→local `transferClassA` and additive-create branches.
  Found B1 and M2.
- *Existing rows* (item 3): reasoned from the write ordering in `summary-handler.ts:170` and
  `sync-run.ts:263`/`:286` that a cloud row with a non-ASCII key cannot exist on master, and
  re-derived that NFC is the identity on ASCII. That is what makes H2's belt beneficiary-less.
- *Behavior 16's vacuity* (item 4): did not reason about it — **ran both worlds against live
  Storage**, including the `_staging` → `move` promote, and traced the serve path statement by
  statement through `serve-summary-core.ts:56-71`. Found B2.
- *A residual raw-vs-normalized split* (item 5): checked the encoder's branch/hash agreement, the
  belt, `normalizeLogicalKey`, `resolveSummaryMdKey` and the `base`/`MODEL_KEY`/`pdfRelPath`
  derivations. The encoder is consistent; the **belt** is the residual split (H2), and §6/§7 disagree
  about which relation the encoder implements (B3).
- *Guards that cannot fail*: read §7's seven mutations against the code each would change and asked
  what observable moves. Three do not move one (B2 ×2, L1), and one guards a dissolved defect (B3).
- **Not checked:** the §4 gate against a real bucket (still blocked, §4.1 — `claude_ro` cannot read
  schema `storage`; treat §4 as NOT RUN); prod's storage-api version; whether `check-docs.py` /
  `check-gate-falsifiability.py` would already flag H1's FAILS-IF (I read the rule, not the scripts);
  and any behaviour of a case-sensitive non-normalizing filesystem — M2's Linux half is reasoned from
  `LocalFsBlobStore`'s identity `abs()`, not measured, and is labelled accordingly.

---

## Verdict

**NOT CONVERGED**

v3's central move is right, and I want that separated from the findings: hashing raw bytes puts the
seam's equality back in agreement with every comparison above it, and that — not §3.5 — is what
dissolves round 2's aliasing findings. §3.5 is a second, worthwhile change whose scope has one hole
(B1: the receiver of an additive create can be the vault, which §3.5 declines to canonicalize), and
whose entire evidence apparatus is currently inert: behavior 16 passes with or without it (B2,
measured), the check script guards the previous architecture (H1), the belt suppresses the runtime
observation that would catch a violation (H2), and §6 still instructs the implementer to build v2's
encoder (B3).

The pattern across three rounds is worth naming, because it is the same one every time: **each
version's falsifier is written against the version being replaced.** v2's behavior 16 tested v1's
bug; v3's tests v2's. The fix is not another round of the same shape — it is to write the falsifier
for the *invariant* (what the cloud row must contain) rather than for the *symptom* (whether a
document happens to serve).
