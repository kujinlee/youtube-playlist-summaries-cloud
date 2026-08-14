# Adversarial design review — cloud blob key encoding (backlog #36), round 1, Claude half

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` (draft v1)
**Branch:** `fix/cloud-blob-key-encoding` @ `fff99b8`
**Reviewer:** Claude (the Claude half of the round-1 dual adversarial design review)
**Date:** 2026-08-14

**Verdict: NOT CONVERGED** — 1 Blocking, 3 High, 3 Medium, 2 Low.

Storage behaviour in this review was **measured**, not reasoned about: throwaway probes against the
local stack (`http://127.0.0.1:54321`, `artifacts` bucket, service role), each refusing to run unless
the host is `127.0.0.1`/`localhost`, each removing every object it created. Where a number below is
labelled *measured*, it came from one of those runs.

---

## Summary of findings

| # | Sev | One line |
|---|---|---|
| B1 | **Blocking** | NFC normalization makes two distinct logical keys one physical object, and the relocation path's "don't delete the destination" guard is byte-exact — the cleanup deletes the object the row now points at |
| H1 | High | §4's no-migration proof is unsound: `LIMIT = 96` is *below* the 131-character key the system's own boundary validator admits, so an ASCII key that Storage accepts can still be re-addressed |
| H2 | High | §2.2's measured bound is wrong. The limit is **255 characters per path segment**, not 267 for the whole path — and the wrong number is the *only* recorded reason for rejecting the reversible encodings, one of which measurably fits |
| H3 | High | `encodeSegment` is undefined on the empty string, and **both** production prefix shapes (`''` and `dig/{base}/`) contain an empty segment. Both resulting failures are silent (measured) |
| M1 | Medium | §3.3's fail-closed guard inspects the **leaf**; a hashed *intermediate* segment slips past it and becomes a silently-dropped dig section — the guard's own failure class |
| M2 | Medium | §6 behaviors 3 and 4 contradict each other as universally quantified properties, so the property test §7 leans on cannot be written as specified |
| M3 | Medium | The §4 gate's runnability is asserted, not established, and its subject includes segments the encoder never touches |
| L1 | Low | Totality's `head == ''` branch is outside §2.1's measured table. Measured here: it holds |
| L2 | Low | §3.4's "all three adapters can be tested against the same contract" is false for `list()` |

---

## B1 — Blocking. NFC normalization aliases two logical keys onto one physical object, and the guard that stops a relocation deleting its own destination is byte-exact

### What the spec says

§2.5 argues NFC normalization into the encoding contract, and the argument it gives is one-directional:

> Without normalization, NFC and NFD forms of one title produce **two different physical keys** — one
> video, two objects, or a read that misses an object that exists.

§3.2 then lists **Injective** as one of the encoder's four properties, and §6 behavior 3 requires
"NFC and NFD forms of one title encode to the **same** physical key". The spec never analyses the
direction those two sentences jointly create: *two different logical keys, one physical object.*

### Why that is dangerous here specifically

The seam's own comparison helpers are Unicode-naive. `normalizeLogicalKey` splits on `/` and drops
empty and `.` segments — nothing else:

```ts
// lib/storage/blob-store.ts:96-98
export function normalizeLogicalKey(key: string): string {
  return key.split('/').filter((seg) => seg !== '' && seg !== '.').join('/');
}
```

and `copyBlob`'s same-key short-circuit is built on it:

```ts
// lib/storage/blob-store.ts:134
if (normalizeLogicalKey(from) === normalizeLogicalKey(to)) return { ok: true, already: true };
```

So under the proposed design, `copyBlob(p, '003_<NFD>.md', '003_<NFC>.md')`:

1. the short-circuit does **not** fire — the two strings differ byte-wise;
2. `tryGet(from)` reads physical object *P*;
3. `tryGet(to)` reads the **same** physical object *P* — the adapter NFC-normalizes both;
4. `dst.bytes.equals(src.bytes)` is trivially true, so it returns `{ ok: true, already: true }`
   (`blob-store.ts:143-149`). No write happens, and nothing anywhere reports an anomaly.

`reconcileCloudBase` then treats that as a completed copy and proceeds to its cleanup phase:

```ts
// lib/cloud-sync/reconcile-serial.ts:357-361
let cleanupFailures = 0;
for (const { from, to } of plan) {
  if (to === from) continue;
  try { await cloud.blob.delete(cloud.p, from); } catch { cleanupFailures += 1; }
}
```

`to === from` is byte-exact. `'003_<NFD>.md' !== '003_<NFC>.md'`, so the loop deletes `from` —
**which is the object the row it just wrote now points at.** The same happens to `models/<base>.json`
and to every dig blob enumerated by `paidKeysUnder` (`reconcile-serial.ts:95-104`).

Outcome: the cloud row advertises `artifacts.summaryMd = { key, status: 'promoted' }`
(`reconcile-serial.ts:296`), verified present at `:351`, and **every blob it names is gone** — the
summary the user paid Gemini for, the magazine model, and every paid dig section. The function
returns `{ ok: true, action: 'relocated', copied: 0, cleanupFailures: 0 }`. The sync report says
success.

The ordering comment at `reconcile-serial.ts:23-27` states the intended invariant exactly —
"copy every blob (sources RETAINED) → the copies are verified by `copyBlob` → advance the metadata →
delete the old base best-effort … any failure after it is leftovers, not loss". Under an alias, the
copy phase never copies anything and the cleanup phase is not leftovers, it is loss.

This is the same shape as the defect that produced this project's worst incident: a guard whose
operand is in a different equivalence class from the thing it guards. The storage layer becomes
normalization-insensitive; every comparison above it stays byte-exact.

### Reachability — traced, not assumed

The chain needs a local index whose `summaryMd` is in a different normalization from the cloud row's.
That path exists in production code:

```ts
// lib/pipeline.ts:135-138  (recoverOrphanedVideos)
files = fs.readdirSync(outputFolder).filter(
  (f) => f.endsWith('.md') && !f.includes('-deep-dive'),
);
```
```ts
// lib/pipeline.ts:105  (reconstructVideo)
const summaryMd = file;
```

`file` is the raw `readdirSync` entry — **the on-disk bytes**, whatever normalization the filesystem
holds — and it is written straight into the index by `store.upsertVideo` (`lib/pipeline.ts:154`). The
project has already measured that vault files and index strings disagree this way:

```ts
// lib/serial-migrate-exec.ts:24-28
 * Why: filenames can be stored on disk in a different Unicode normalization than the
 * string in the index (Korean slugs are sometimes mixed/NFD), so a byte-exact
 * `fs.existsSync` can miss a file that is genuinely present.
```

with a regression test built on a Korean title (`tests/lib/serial-migrate-normalization.test.ts`) and
the commit the spec itself cites (`08797e4`).

From there, `describeDivergence` compares the two bases byte-exactly:

```ts
// lib/cloud-sync/reconcile-serial.ts:151-155
const from = baseOf(cloudVideo.summaryMd);
const to = localVideo.summaryMd ? baseOf(localVideo.summaryMd) : ...;
return from === to ? { diverged: false } : { diverged: true, from, to };
```

A pure-normalization difference reports **diverged**, and `reconcileCloudBase` runs the relocation
above. Note that a relocation between two canonically-equivalent bases is a *no-op the system does not
need to perform at all* — it is pure downside.

I am stating reachability honestly: this needs a vault file in a non-canonical normalization for a
video that also exists in the cloud. That is narrow. It is also precisely the condition this project
has already hit once on the local side, and the consequence is silent, irreversible loss of paid
artifacts, so the severity is set by consequence.

### Why the existing "already: true" design does not save it

`already: true` is documented (`blob-store.ts:22-24`) as "the destination was PROVEN to hold
byte-identical content", and it exists so a partial relocation can resume. Under an alias it is
*technically true and semantically wrong*: the destination holds identical content because it **is**
the source. Nothing in `CopyResult` can express that difference, which is why the fix has to be
upstream of `copyBlob`.

### Fix

Make the **logical** key space NFC-normalized too, so that "physically the same object" and
"logically the same key" stay the same equivalence relation. Concretely, all four:

1. `normalizeLogicalKey` (`blob-store.ts:96`) NFC-normalizes each segment. That makes `copyBlob`'s
   short-circuit fire and return `{ ok: true, already: true }` *before any I/O*, which is the correct
   answer.
2. `reconcileCloudBase`'s cleanup (`reconcile-serial.ts:359`) compares
   `normalizeLogicalKey(to) === normalizeLogicalKey(from)`, not raw strings.
3. `describeDivergence` (`reconcile-serial.ts:151-155`) compares NFC-normalized bases, so a
   normalization-only difference is `agreed` and no relocation is attempted.
4. The relocation plan's collision check (`reconcile-serial.ts:262-276`) puts **NFC-normalized**
   destinations in its `destinations` Set, so two sources aliasing onto one destination is caught as
   `ambiguous-mapping` rather than silently sequenced.

Then state the resulting contract in the spec: *canonically-equivalent logical keys are the same
logical key.* That single sentence is what §3.2's "Injective" should say, and it is what makes B1,
M2 and the `already: true` ambiguity all disappear at once.

**What observation would make this FAIL?** Integration test: relocate a cloud base that differs from
local's **only** by Unicode normalization (`003_팔란티어-대체될까.md` NFD vs NFC), then assert (a)
`blobStore.get(p, newKey)` returns the original bytes, (b) `models/<newBase>.json` and every
`dig/<newBase>/*.md` still read, (c) the spend ledger did not move. Against the spec as written, (a)
returns `null`.

---

## H1 — High. §4's no-migration proof is unsound, and `LIMIT = 96` is the unsound half

§4 claims:

> **The set of keys the encoding changes is exactly the set Storage would have rejected.**

That is false as stated. Writing it out:

- set the encoder changes = `¬SAFE ∪ (SAFE ∧ len > 96)`
- set Storage rejects = `non-ASCII ∪ (segment len > 255)` *(measured — see H2)*

`SAFE ∧ 96 < len ≤ 255` is in the first set and not in the second. §4 says "a key outside that set was
refused at upload and therefore **is not in the bucket**" — for the length half, that inference does
not hold.

The spec's own block quote half-sees this ("a segment that is `SAFE` but longer than `LIMIT` would
also be re-addressed and orphaned") and then dismisses it with "Nothing in the codebase can produce
one — `slugify` caps at 60". **That is not what the codebase says.** The boundary validator the serve
path actually runs admits far more:

```ts
// lib/html-doc/assert-cloud-summary-md-key.ts:14
const CLOUD_SUMMARY_MD_KEY = /^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u;
```

That is up to **131 characters** — and it is called on the key read from the database at serve time
(`lib/html-doc/serve-summary-core.ts:61`), and on the dig path
(`lib/dig/cloud/resolve-summary-key.ts:16`). So the system's own contract for an admissible cloud
summary key is 131 chars, while the encoder's identity branch stops at 96. A 100-character ASCII key
is servable today and would be re-addressed — orphaned — by this change. `assertLogicalKey`
(`blob-store.ts:87-91`) imposes no length bound at all, and the sync path pushes the *sender's* key
verbatim (`lib/cloud-sync/sync-run.ts:263`), i.e. a key minted on a machine this deploy has never
seen.

`LIMIT = 96` is described as "far below any observed bound", which is true and is the problem: it is
also below the bound the application itself enforces. The identity branch's length condition must be
at least as wide as every logical key the system admits, or §4's proof needs a *different* argument.

**Fix.** Set `LIMIT` to a value ≥ the widest logical key the codebase's own validators admit — 200 is
comfortable (still 55 below the measured 255-per-segment ceiling, and the hash escape still exists for
anything longer). Then §4's set inclusion is genuinely `¬SAFE ⊆ Storage-rejects`, which *is* provable
from §2.1. Update the §4 gate's length threshold to the same constant, and import it from the encoder
module rather than typing it into the SQL.

**What observation would make this FAIL?** A unit test asserting `encodeSegment` is identity on the
longest key `CLOUD_SUMMARY_MD_KEY` admits (a 128-char base + `.md`), plus a `check-*` script asserting
the SQL gate's literal equals the encoder's exported `LIMIT`.

---

## H2 — High. §2.2's central measurement is wrong: the limit is 255 per path **segment**, not 267 per path — and that wrong number is the sole recorded reason for rejecting the reversible encodings

§2.2 states, as a bisected measurement:

> **maximum accepted object key length is 267; the first rejection is at 268.**

**Measured, same local stack, `artifacts` bucket, service role.** Binary search on total key length,
for keys built with 1, 2 and 4 path segments below a 39-character root:

```
segments=1: max accepted total key length = 295, first rejection at 296
segments=2: max accepted total key length = 551, first rejection at 552
segments=4: max accepted total key length = 1063, first rejection at 1064
single segment of 255 chars -> accepted
single segment of 256 chars -> REJECTED 500
```

All three fit `root + n × (1 + 255)` exactly. Direct confirmation that there is no whole-path bound at
267:

```
seg 255 + seg 10  (total 306 chars)   -> accepted
seg 256 + seg 10  (total 307 chars)   -> REJECTED 500
four segs of 200 each (total 843)     -> accepted
```

**The limit is 255 characters per path segment. There is no whole-path limit up to at least 1063.**
(The 500-on-overflow half of §2.2 reproduces exactly, and the retry hazard it describes is real.)

### Why this matters beyond a wrong number

§2.2's budget table exists to produce the figure **149**, and §2.3 uses 149 — and only 149 — to rule
out every reversible encoding:

> Reversibility at current slug lengths is not achievable. This is what sent the design to §3.

Against the real constraint, the owner uuid, the playlist id and `_staging/<uuid>/` are **separate
segments** and consume none of the filename's budget. The budget for the filename segment is 255.
Re-running §2.3's own worst case:

```
slug bytes 180 -> base64url chars 240 -> segment `003_<b64>.md` = 247 chars
base64url(180-byte Hangul slug) as ONE segment -> accepted
```

**Measured.** The base64url row of §2.3's table — the one marked "no" — fits, with 8 characters to
spare. Punycode (~180) fits comfortably. §8.1's rejection of quoted-printable ("requires capping
non-ASCII vault filenames at ~24 characters, from 60 — a real cost to the user's data") is computed
from 149 and does not survive the correction either.

This does **not** make §3's design wrong. The hashing encoder is total, bounded and cheap, and §3.3's
prefix re-attachment genuinely removes the need for reversibility. But the spec's *recorded reason*
for the central architectural choice is a mis-measurement, and §2 is titled "What was measured". Per
this project's own rule — a check beats a claim only when it reads the thing the claim is about — a
number attributed to the wrong subject (whole path vs. segment) that then drives a design fork is the
defect class, not a typo.

**Fix.** Replace §2.2's bound with the per-segment measurement and the probe that produced it; redo
the §2.3 table against 255; and either (a) keep §3 and say plainly that reversibility was available
and was declined for its own reasons (`list()` never needs it, §3.3), or (b) reopen §8.1 knowingly.
Do not carry 149 or 267 forward — §10's "the 267 bound differs on prod's storage-api version" risk row
should become "the bound is per-segment; the design is insensitive because its worst case is ~70".

---

## H3 — High. `encodeSegment` is undefined on the empty segment, and both production prefix shapes contain one

§3.2 defines the identity test as `SAFE = /^[A-Za-z0-9._-]+$/` — one **or more** characters. `''`
therefore fails `SAFE` and takes the hash branch. §3.4 says only "`deletePrefix()`: encode the prefix"
and §3.3 step 1 says "encode `prefix` → physical prefix", with no rule for how a prefix is split.

Both production prefix shapes split to a trailing empty segment:

| Caller | Prefix | Naive split |
|---|---|---|
| `app/api/playlists/[id]/route.ts:79` | `''` | `['']` |
| `lib/cloud-sync/reconcile-serial.ts:102`, `lib/dig/cloud/load-dig-for-serve.ts:33`, `app/api/videos/[id]/dig-state/route.ts:47` | `dig/${base}/` | `['dig', base, '']` |

The existing code tolerates the trailing slash by stripping it **after** concatenation
(`supabase-blob-store.ts:131` and `:143`, both `.replace(/\/$/, '')`), so an encoder inserted before
that concatenation inherits an input shape nobody wrote a rule for.

**Both failures are silent — measured:**

```
list of absent folder    -> [] len=0        (no error)
remove of absent object  -> ok, removed=0   (no error)
```

Consequences:

- **`deletePrefix(p, '')`** — the playlist delete's blob cleanup targets
  `<owner>/<indexKey>/=h<hash>`, which does not exist, removes nothing, and reports success. The DB
  rows are already gone at that point (`app/api/playlists/[id]/route.ts:75`), so **nothing will ever
  reference or clean those objects again.** The route's `catch` (`:80-83`) accepts "invisible
  orphans" on *failure*; this is a silent 100% no-op that never reaches the catch.
- **`list(p, 'dig/{base}/')`** — returns `[]` for every playlist. `load-dig-for-serve.ts:33-35`
  serves the doc with every section un-dug; `dig-state/route.ts:47-56` reports
  `{ sectionIds: [] }`; `paidKeysUnder` (`reconcile-serial.ts:102`) omits every dig from the
  relocation plan, so a relocation strands paid digs at the old base. Paid dig content becomes
  invisible across the whole product.

  To be precise about money: this does **not** double-charge. `lib/dig/cloud/enqueue-dig-core.ts:37-39`
  dedups on the exact blob key via `exists()`, which goes through `objectKey()` and is encoded
  correctly, so a re-dig short-circuits with no charge. The defect is paid content becoming
  unreachable, not re-billed.

**There is already a falsifier in the suite**, which is the good news and the reason this is High
rather than Blocking — `tests/lib/storage/blob-store-list.test.ts:47-49` pins the physical dirPath:

```ts
const keys = await store.list(p, 'dig/base/');
expect(keys.sort()).toEqual(['dig/base/65.r9.md', 'dig/base/nested/120.r9.md']);
expect(list).toHaveBeenCalledWith('owner1/pl-key/dig/base', expect.anything());
```

A naive implementation goes red there. But the spec is the artifact under review, it specifies
`encodeSegment` precisely enough that "one or more" is load-bearing, and it should not be relying on
an unrelated test to catch its own unstated case.

**Fix.** State the rule in §3.2/§3.4: *encoding applies to non-empty segments; empty segments are
preserved, so a trailing `/` survives encoding and an empty prefix encodes to the empty string.*
(Equivalently: run the prefix through `normalizeLogicalKey` first, encode, then re-append the trailing
`/` if the caller supplied one.) Add to §6: "`deletePrefix(p, '')` removes every object under the
playlist root, including non-ASCII-keyed ones" and "`list(p, 'dig/{base}/')` and
`list(p, 'dig/{base}')` return the same set".

---

## M1 — Medium. §3.3's fail-closed guard inspects the leaf; a hashed intermediate segment slips past it

§3.3:

> If a returned **leaf** itself carries the `=h` marker, the adapter cannot name it and **throws**.

But `collectObjectPaths` recurses into folders, and the returned relative key can contain intermediate
directory segments:

```ts
// lib/storage/supabase/supabase-blob-store.ts:159-165
const entryPath = `${dirPath}/${entry.name}`;
if (entry.id === null) {
  paths.push(...(await this.collectObjectPaths(entryPath)));
} else {
  paths.push(entryPath);
}
```

and the contract test pins that this reaches callers:

```ts
// tests/lib/storage/blob-store-list.test.ts:43-48
[root]: [{ name: '65.r9.md', id: 'f1' }, { name: 'nested', id: null }], // folder → recurse
...
expect(keys.sort()).toEqual(['dig/base/65.r9.md', 'dig/base/nested/120.r9.md']);
```

If `nested` were non-ASCII it would come back hashed. A guard applied to the basename only lets
`dig/base/=hXXXX/120.r9.md` through as a "logical" key. The caller then does
`blobStore.get(p, key)` (`load-dig-for-serve.ts:38`), the adapter re-encodes the already-hashed
segment (hash of a hash), the read 404s, and:

```ts
// lib/dig/cloud/load-dig-for-serve.ts:39
if (!bytes) continue; // listed-but-vanished race → skip
```

The section is silently dropped — "an invisible dig section, i.e. paid content vanishing", which is
exactly what §3.3 says the guard exists to prevent, re-entering through the guard's own wording.
Unreachable today (dig blobs are flat: `dig/{base}/{sectionId}.r{V}.md`), which is precisely the
argument §3.3 gives for why the guard must be loud.

**Fix.** Apply the marker check to **every segment** of the relative path the adapter is about to
return, not the basename. **What observation would make this FAIL?** A unit test with a mocked client
returning a folder entry whose name carries `=h`, asserting `list()` throws.

---

## M2 — Medium. §6 behaviors 3 and 4 are contradictory, so the property test §7 leans on cannot be written as specified

| # | Behavior |
|---|---|
| 3 | NFC and NFD forms of one title encode to the **same** physical key |
| 4 | Two different logical keys never share a physical key |

The NFD and NFC forms of one title **are** two different logical keys — that is the whole content of
behavior 3. As universally quantified statements over logical keys, 3 falsifies 4. §7 then says
"Property tests carry the weight … Behaviors 1, 4 and 5 are universally quantified", so the property
test for 4 will either be written over NFC-normalized inputs — in which case it does not test the
claim as written, and its passing means less than it appears to — or it will fail.

§3.2's "Injective" bullet has the same defect: it argues injectivity from the `=` marker and SHA-256
over "the full normalized segment", and never says that normalization is a deliberate
non-injectivity in the map from logical keys.

This is not cosmetic. **B1 is exactly what behavior 4 would have caught if it were stateable**, and
the reason it was not caught is that the two properties were written down as if both were true.

**Fix.** Restate: *the encoder is injective on NFC-normalized logical keys; canonically-equivalent
logical keys are deliberately identified, and the seam treats them as the same logical key* (the B1
fix). Then behavior 4's property test quantifies over NFC-normalized inputs honestly, and a separate
behavior asserts that the seam's comparison helpers agree with the encoder about which keys are the
same.

---

## M3 — Medium. The §4 gate's runnability is asserted, and its subject is wider than the encoder's

Two problems with the gate as written.

**(a) It has not been shown to be runnable.** §4 says "Run against **prod** before deploy. Put the SQL
in a file (`docs/plugins.md`, and the `claude_ro` recipe in memory)." The spec does not record that the
named credential can read `storage.objects` — a schema outside `public` with its own grants. Per
`CLAUDE.md`, *"Cannot run" is a FAILURE, never a pass*; a gate whose credential turns out to lack
`SELECT` will produce zero rows or an error at exactly the moment it is being used to authorise a
deploy, and zero rows is the pass condition. The proof in §4 is load-bearing for "no migration is
needed", so if the gate cannot run, the no-migration claim is unproven, not satisfied.

**(b) Its subject is wider than the encoder's.** The gate checks *every* path segment of
`storage.objects.name`, but `objectKey` encodes only `key`:

```ts
// lib/storage/supabase/supabase-blob-store.ts:15-18
private objectKey(p: Principal, key: string): string {
  assertLogicalKey(key);
  return `${p.id}/${p.indexKey}/${key}`;
}
```

`p.id` (owner uuid) and `p.indexKey` (playlist key) are never encoded. A gate that flags them reports
a Blocking for a segment this change cannot re-address.

**Fix.** Scope the gate's predicate to segments **after** the first two; import the length threshold
from the encoder rather than typing `96` into the SQL (see H1); and add an explicit precondition step
that the gate's own credential can read the table — e.g. `select count(*) from storage.objects where
bucket_id = 'artifacts'` must return a number, and an error or a permission denial means *the gate has
NOT run*, not that it passed.

---

## L1 — Low. Totality's `head == ''` branch is outside §2.1's measured table

§3.2 claims **Total** — "every input produces an accepted key" — but §2.1's accepted/rejected table
contains no key beginning with `=`, and `head` is empty whenever a segment has no leading run of
`[A-Za-z0-9._-]` (e.g. a bare `한국어.md`, which encodes to `=hXXXXXXXXXXXXXXXXXXXXXX.md`).

**Measured** — all accepted:

```
leading "=" segment, with ext (=hJ8kQ...md)   -> accepted
bare "=h..." segment, no ext                  -> accepted
"=" as whole segment                          -> accepted
```

So totality holds. Worth adding these three rows to §2.1 rather than leaving a universally quantified
claim resting on a table that omits the branch. (No production key can reach the empty-`head` branch
today: summary keys start with `padSerial`, dig leaves are integers, and `digDeeperMd` starts with the
base — but "no production key can" is the claim §4 itself declines to accept elsewhere.)

---

## L2 — Low. "All three adapters can be tested against the same contract" is false for `list()`

§3.4 closes with:

> `LocalFsBlobStore` and `InMemoryBlobStore` implement **identity** … The encoder is a pure module so
> all three adapters can be tested against the same contract.

For `list()` they cannot. Given a Korean key, `LocalFsBlobStore.list` (`local-blob-store.ts:71-89`)
and `InMemoryBlobStore.list` (`in-memory-blob-store.ts:188-198`) return it; `SupabaseBlobStore.list`
under §3.3's fail-closed guard **throws**. `tests/lib/dig/write-dig-section-blob-promote.test.ts:81`
already calls `list(principal, '')` and filters `_staging/`, which is a shape that would diverge.

Low because no production caller passes `''` — I verified §3.3's claim and it is correct: the only
three `blobStore.list` callers in `lib/`, `app/`, `worker/` and `scripts/` all pass `dig/${base}/`.
But the shared-contract sentence should say *which* behaviors are shared (`put`/`get`/`copy`/
`promote` round-trips) and which are deliberately backend-specific (`list` on a prefix whose leaves
are not ASCII).

---

## Where the spec is right — verified, not conceded

- **§9 / question 1: no production path reaches Storage outside the adapter.** The only
  `client.storage.from(` in non-test code is `lib/storage/supabase/supabase-blob-store.ts:20`. No
  signed URLs, no public URLs, no SQL touching `storage.objects` outside
  `supabase/migrations/0007_storage_and_rpcs.sql` (RLS policies only). `worker/main.ts` reaches
  storage through `lib/storage/*` and `scripts/cloud-sync.ts` constructs a `SupabaseBlobStore`.
  The totality argument's premise holds.
- **§3.3's caller table is accurate.** Three `list()` callers, all passing `dig/${base}/`:
  `reconcile-serial.ts:102`, `load-dig-for-serve.ts:33`, `dig-state/route.ts:47`. The leaf-shape claim
  is pinned by `dig-state/route.ts:50` (`/\/(\d+)\.r\d+\.md$/`), and a dig section really is
  identified by an integer.
- **Question 2: nothing derives one physical key from another.** `remap`
  (`reconcile-serial.ts:116-139`), `MODEL_KEY` (`model-store.ts:31`) and `pdfRelPath`
  (`lib/pdf/pdf-path.ts:20-30`) all operate on logical keys. The one physical→logical derivation is
  `list()`'s `f.slice(ownerRoot.length)` (`supabase-blob-store.ts:145`), which §3.3 correctly
  replaces.
- **§2.1's marker choice.** Measured: `=` is accepted by Storage in a filename segment, in a *folder*
  segment, and survives `list()`, `download()` and `move()` (the `promote` path). A hashed dig folder
  with an ASCII leaf lists correctly. Non-ASCII is rejected `400 InvalidKey` in every form I tried,
  including accented Latin — §2.1's "the defect is far wider than Korean" is right.
- **§2.6's second entrance is real.** `lib/cloud-sync/sync-run.ts:263` pushes the sender's key
  verbatim; `slugify` is not called on that path. Fixing at the seam does close both entrances.
- **ADR-0008 survives.** The money guard's corroboration argument (`lib/html-doc/serve-doc.ts:99-113`)
  depends on the MD key and the model key living under the same `${p.id}/${p.indexKey}/` grant.
  `objectKey` encodes only `key`, so both physical keys stay under that prefix and the grant
  granularity argument is unaffected.
- **§9's deletion of the storability precondition is correct reasoning.** Given a total encoder and
  a single funnel, the precondition has no failing observation. Relocating the protection to a
  property test is the right move — provided the property is stateable, which M2 says it currently
  is not.

---

## Verdict

**NOT CONVERGED**

B1 must be fixed before implementation begins: as specified, this change introduces a path that
silently destroys every paid artifact for a video, and it does so through the exact guard
(`if (to === from) continue`) that was written to prevent it. H1 and H2 both say the same thing about
§2 and §4 — two of the three numbers this design is justified by (267/149, and `LIMIT = 96`) do not
survive contact with the subject they describe. H3 is a specification hole in the two prefix shapes
production actually uses.
