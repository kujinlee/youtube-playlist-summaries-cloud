# Cloud blob keys — encode at the storage seam so a title in any language can be stored (backlog #36)

**Status:** draft **v4**, awaiting user approval. **Branch:** `fix/cloud-blob-key-encoding`.
**Origin:** backlog **#36** 🔴, filed 2026-08-12 by the first real M3 acceptance run against prod
release v6. Earlier sighting: `docs/local-validation-findings.md` §BUG-4, filed P2 during local
validation and correctly diagnosed there — it became 🔴 only when the acceptance run showed the
failure lands *after* the Gemini charge.

**Review trail — two dual rounds, four halves, all four NOT CONVERGED.**

| Round | Reviewer | Findings |
|---|---|---|
| 1 | [codex](../../reviews/spec-blob-key-encoding-r1-codex.md) | 1 Blocking, 1 Medium, 1 Low |
| 1 | [claude](../../reviews/spec-blob-key-encoding-r1-claude.md) | 1 Blocking, 3 High, 3 Medium, 2 Low |
| 2 | [codex](../../reviews/spec-blob-key-encoding-r2-codex.md) | 1 Blocking |
| 2 | [claude](../../reviews/spec-blob-key-encoding-r2-claude.md) | 2 Blocking, 1 High, 2 Medium, 1 Low |

| 3 | [codex](../../reviews/spec-blob-key-encoding-r3-codex.md) | 1 Blocking, 1 Medium |
| 3 | [claude](../../reviews/spec-blob-key-encoding-r3-claude.md) | 3 Blocking, 2 High, 2 Medium, 1 Low |

> ⚠ **v4 DELETES the mechanism that produced every round's findings. Read this before anything else.**
>
> v1 put a Unicode-normalization equivalence in the encoder. v2 moved it to the storage seam and
> enumerated four comparison sites to match; round 2 found four more. v3 moved it to ingress and
> enumerated three entry points; round 3 found a fourth, plus a way to **destroy a vault file that
> master cannot reach**.
>
> **The decisive evidence is round-3 B2, measured live: the whole NFD write→serve round trip succeeds
> with canonicalization REMOVED.** Every mutation §7 named to prove it load-bearing survived. A
> mechanism whose deletion changes nothing observable is not doing anything — while costing eight
> comparison sites, two incomplete enumerations, two vacuous falsifiers, and a new data-loss path.
>
> I applied *"delete the mechanism rather than patch the second instance"* twice and got it wrong both
> times, because I kept deleting the mechanism's **location**. The thing to delete is the
> **equivalence itself**. This system is byte-exact end to end and always has been; nothing asked for
> a Unicode equivalence and, measured, nothing needs one.
>
> **With exactly one real exception, which round-3 B1 found: APFS aliases NFC and NFD.** There *is* an
> equivalence in this system — in the local filesystem — and `findByNormalizedName`
> (`serial-migrate-exec.ts:26`) already encodes that knowledge. §3.5 now puts it there and nowhere
> else.

> ⚠ **v3 changed the architecture, because round 2 showed v2 was patching one decision repeatedly.**
> Five of round 2's findings — Codex's Blocking, Claude's B2, H1 and M1, plus a sixth comparison site
> found by a mechanical sweep — are all consequences of *one* v2 choice: putting the
> normalization-equivalence at the **storage seam**, in a system that is byte-exact everywhere above
> it. Each round then discovered another site that had not got the memo, and the hand-enumeration
> failed **twice** (v2 named four; round 2 found a fifth, a sixth, a seventh and an eighth).
>
> Per `docs/plugins.md`' own rule — *when two review rounds find the same bug shape through different
> paths, delete the mechanism rather than patch the second instance* — v3 **moves canonicalization to
> the ingress boundary** (§3.5). Every key that reaches cloud reasoning is canonical by construction,
> so every existing byte-exact comparison is correct without being touched, and the encoder goes back
> to being a pure function of raw bytes.
>
> **Round 3 must attack that claim specifically**, because "this dissolves five findings" is exactly
> the kind of assertion that has been wrong before in this repo.

> **In one paragraph:** every blob key is `${padSerial(serial)}_${slugify(title)}`, and `slugify`
> keeps any Unicode letter. Supabase Storage rejects any object key containing a non-ASCII character,
> so a Korean-titled video's summary cannot be written — but only *after* Gemini has been called and
> billed. This slice moves the storage-safety concern into the Supabase adapter, which maps a
> **logical key** (what the vault, the database and the sync path speak) to a **physical key** (what
> Storage will accept). Everything above the seam keeps speaking Unicode.

> ⚠ **v1 justified its central choice with a measurement of the wrong subject, and v2 says so
> plainly.** v1 reported "maximum object key length is 267 characters" and used it to prove that every
> reversible encoding was impossible. The real limit is **255 characters per path *segment*** with no
> whole-path bound (§2.2). v1's probe varied one segment under a fixed 12-character prefix, so it
> could only ever discover a segment bound — no possible outcome of that experiment distinguished the
> two hypotheses. Reversible encoding was in fact available. The design in §3 survives, but **for
> different reasons**, and §2.3/§8.1 are rewritten rather than patched.

---

## 1. Purpose

Make a video title in any language storable in the cloud, without changing the filenames in the
user's Obsidian vault, and without a migration of anything already in the bucket.

**Two user decisions fixed this design and are not reopened here** (2026-08-14):

1. **The vault wins.** Local filenames keep their Unicode; the cloud key is what changes. This is the
   same call `lib/cloud-sync/reconcile-serial.ts:18` already made — *"LOCAL IS AUTHORITATIVE; local
   filenames live in the user's Obsidian vault, where a rename breaks hand-made wiki-links and
   bookmarks that nothing can repair; cloud blob keys are invisible."*
2. **No refund, no ledger reconciliation.** The ~156¢ spent on the two dead-lettered prod jobs stays
   recorded. The money genuinely left; `ever_metered = t` is PR #22's durable guard behaving
   correctly. The ledger stays the honest record of what was spent.

---

## 2. What was measured

All storage probes ran against the **local** Supabase stack. Each probe script refuses to run unless
the URL is `127.0.0.1`/`localhost`, and cleans up the objects it wrote.

### 2.1 The accepted character set — the defect is far wider than "Korean"

| Accepted | Rejected — `400 InvalidKey` |
|---|---|
| `003_hello-world.md` | `003_돈-버는-방식은-정해져-있다.md` (Hangul) |
| `003_Upper_Case.md` | `003_日本語のタイトル.md` (Japanese) |
| `003_a(b)c.md` | `003_privet-привет.md` (Cyrillic) |
| `003_a+b=c.md` | **`003_cafe-résumé-año.md` (accented Latin)** |
| `003_a b.md` | `003_strasse-ß-ø.md` |
| `=hJ8kQ2m….md` (leading `=`, with ext) | `003_party-🎉.md` |
| `=hJ8kQ2m…` (leading `=`, no ext) | `003_a~b.md` |
| `=` as a whole segment | `003_a%20b.md` |

**Every non-ASCII letter is refused, including French, Spanish, German and Portuguese.** The backlog
filed this as "non-ASCII (Korean)"; a `résumé` in a title destroys a paid summary identically. Any fix
scoped to Korean, or to transliteration of one script, is scoped wrong. `%` is rejected, which rules
out percent-encoding.

The three `=`-leading rows were added in v2 (round-1 **L1**): §3.2 claims the encoder is *total*, and
the empty-`head` branch produces exactly those shapes, so the table had to cover them rather than
leave a universally quantified claim resting on cases it omitted. Measured: all three accepted, in
filename *and* folder position, surviving `list()`, `download()` and `move()`.

### 2.2 The length limit — 255 characters per SEGMENT, and it fails as a 500

⚠ **This section is corrected in v2. v1 stated "maximum object key length is 267".** That number was
`_probe36len/` (12 chars) + a 255-character segment, i.e. the segment bound wearing a path bound's
label. Re-measured, with an experiment capable of returning the other answer:

| Result | Total path length | Case |
|---|---|---|
| ACCEPTED | 266 | one segment of 255 |
| REJECTED `500` | 267 | one segment of **256** |
| **ACCEPTED** | **1014** | **4 segments × 250** |
| ACCEPTED | 1216 | 6 segments × 200 |
| REJECTED `500` | 278 | 2 segments, first is 256 |

**The limit is 255 characters per path segment. There is no whole-path bound up to at least 1216.**
The owner uuid, the playlist key and `_staging/<uuid>/` are separate segments and consume none of the
filename's budget — so the "149 characters remaining" budget table in v1 described nothing real and
is deleted.

Over-length does **not** produce `400 InvalidKey`. It produces:

```
{"statusCode":"500","error":"Internal","message":"Internal Server Error","code":"InternalError"}
```

A `500` is indistinguishable from a transient fault, so a retrying caller retries something that can
never succeed. That hazard is real and reproduces; it matters on the serve path, where
`max_serve_attempts = 5`.

### 2.3 Reversible encoding was available — v1 said otherwise, from the wrong budget

v1 ruled out every reversible scheme against a phantom 149-character budget. Against the real
255-per-segment ceiling, measured:

```
base64url of a 60-char Hangul slug (180 bytes) -> 240 chars -> `003_<b64>.md` = 247 chars -> ACCEPTED
```

Punycode (~180) fits comfortably. So reversibility was never impossible; it was **8 characters short
of the ceiling in the worst case**. §3 still chooses hashing, but §8.1 now records that as a decision
with reasons rather than a forced move.

### 2.4 Supabase user metadata — measured, then found unnecessary

| Question | Answer |
|---|---|
| Does `upload({ metadata })` persist? | **Yes** |
| Does `list()` return it? | **No** — only `eTag, size, mimetype, cacheControl, lastModified, contentLength, httpStatusCode` |
| Does `info()` return it? | **Yes**, one call per object |
| Do `move()` / `copy()` preserve it? | **Yes**, both |

Mechanically viable. **Declined** — see §8.2 — because §3.3 removes the need for it entirely.

### 2.5 What the local side did, and the bug it did hit

`LocalFsBlobStore.abs()` is `path.join(p.indexKey, key)` — **identity, no encoding**. APFS and ext4
accept arbitrary UTF-8 filenames, so Korean names have always worked locally. Local limits are 255
bytes per component; Supabase's is 255 characters per segment — similar in shape, which is why the
wall was invisible from the local side, and why the three Unicode-aware guards (§5) were written
believing Unicode keys are legitimate. Against the only backend anyone had tested, they were right.

The local side did hit one real bug with Korean names, and it is load-bearing here. Commit `08797e4`:

> The serial-number backfill could leave files unprefixed after a single `--apply`: a Korean-titled
> file stored in a non-canonical Unicode normalization was skipped on the first pass and only renamed
> on a second `--apply`.

Fixed by `findByNormalizedName` (`lib/serial-migrate-exec.ts:26`), whose comment states the reason:
*"`existsSync` is only NFC↔NFD tolerant on APFS (and byte-exact on Linux)."* Regression test:
`tests/lib/serial-migrate-normalization.test.ts`, built on the Korean title `팔란티어-대체될까`.

**And non-canonical normalization genuinely enters the index.** `recoverOrphanedVideos` writes a raw
`readdirSync` entry — the on-disk bytes, in whatever normalization the filesystem holds — straight in
as `summaryMd`:

```ts
// lib/pipeline.ts:135-138
files = fs.readdirSync(outputFolder).filter((f) => f.endsWith('.md') && !f.includes('-deep-dive'));
// lib/pipeline.ts:105
const summaryMd = file;
```

> An earlier draft of the v2 fix proposed simply *dropping* NFC from the encoder, on the strength of a
> grep showing no cloud path derives a key from a directory scan. **That grep was scoped to
> `lib/storage/supabase`, `lib/cloud-sync`, `lib/dig/cloud` and `app/api`, and missed `lib/pipeline.ts`.**
> The narrow check was reported as a broad conclusion. §3.5 carries the fix that survives.

### 2.6 The second entrance the backlog did not name

`lib/cloud-sync/sync-run.ts:263` pushes the **sender's** key verbatim into the receiver's blob store:

```ts
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
```

`slugify` is never called on this path. Any existing vault summary with a non-ASCII title fails
identically the moment it syncs to cloud. This is an **addressing-contract** defect with two
entrances. Fixing it at the seam closes both; fixing it in the cloud ingest pipeline would close one.

---

## 3. The design

### 3.1 The seam already has the vocabulary

`lib/storage/blob-store.ts` does not promise that a key is a storage path. It documents **logical
keys**: `list()` is *"List logical keys (relative to the owner root)"*, `deletePrefix` takes a
*"logical prefix"*. This slice uses that latitude; the interface shape is unchanged.

### 3.2 The encoding

Per **non-empty path segment**:

```
SAFE  = /^[A-Za-z0-9._-]+$/          // exactly what existing keys use
LIMIT = 255                           // the measured per-segment ceiling (§2.2)

encodeSegment(s):
  if s === '':                            return ''                // §3.2.1
  if SAFE.test(s) && s.length <= LIMIT:   return s                 // identity
  head = leading run of [A-Za-z0-9._-] in s, truncated to 32
  ext  = trailing /\.[A-Za-z0-9]{1,8}$/ of s, else ''
  return `${head}=h${base64url(sha256(utf8(s))).slice(0, 22)}${ext}`
```

> ⚠ **v3: the encoder hashes the RAW segment. v2 hashed `NFC(s)`, and that was the root of five
> round-2 findings.** Round-2 **M1** measured the immediate defect — the encoder *branched* on the raw
> segment (`SAFE.test(s)`) but *hashed* the normalized one, so the two equivalence relations §3.5
> claimed to have merged still differed, with exactly one counterexample in all of Unicode (U+212A
> KELVIN SIGN, whose NFC form is ASCII `K`). The deeper problem is §3.5. Normalization is now handled
> at ingress, so **everything reaching this function is already canonical** and the encoder needs no
> opinion about Unicode at all.

`SAFE ⊂ ASCII`, so `LIMIT` may be compared against `String.length` (UTF-16 code units) without a
code-unit-vs-character discrepancy — the identity branch is only ever taken by ASCII segments, where
the two agree. Round-2 **L1**: v2 relied on this silently, and §2.2's "255 characters" was itself
measured with ASCII only. Non-ASCII segments never reach the length test, because `SAFE` rejects them
first.

`003_돈-버는-방식은-정해져-있다.md` → `003_=hJ8kQ2m….md`.

**`LIMIT = 255`, not v1's 96.** Round-1 **H1**: 96 is below the **131** characters the system's own
boundary validator admits (`assert-cloud-summary-md-key.ts:14`, `/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u`),
and `assertLogicalKey` imposes no bound at all while `sync-run.ts:263` accepts a key minted on a
machine this deploy has never seen. A 100-character ASCII key is servable today and v1 would have
re-addressed it. Setting `LIMIT` to the measured ceiling is stronger than the reviewer's suggested
200: it makes `{SAFE ∧ len > LIMIT}` empty *within the set of storable keys*, so the length half of
§4's proof becomes unconditional (§4).

Four properties, each a test in §7:

- **Total.** Every input produces an accepted key. No logical key can be unstorable.
- **Bounded.** Worst case 32 + 2 + 22 + 9 = 65 characters, against a 255 ceiling.
- **Identity on everything storable that exists.** See §4.
- **Injective over NFC-normalized logical keys.** Stated precisely in §3.2.2 — v1 said "injective"
  flatly, which contradicted its own behavior 3 (round-1 **M2**).

#### 3.2.1 Empty segments are preserved, never encoded

Round-1 **H3**. `SAFE` requires one *or more* characters, so `''` would take the hash branch — and
**both** production prefix shapes split to a trailing empty segment: `''` → `['']`, and
`dig/${base}/` → `['dig', base, '']`. Both resulting failures are silent, measured: `list` of an
absent folder returns `[]` with no error, and `remove` of an absent object reports success with
`removed=0`.

Left unstated, that yields `deletePrefix(p, '')` silently deleting nothing when a playlist is
removed — and since the DB rows are gone by then (`app/api/playlists/[id]/route.ts:75`), **nothing
would ever reference those blobs again** — and `list(p, 'dig/{base}/')` returning `[]` for every
playlist, making every paid dig section invisible product-wide.

**Rule: encoding applies to non-empty segments; empty segments pass through.** A trailing `/`
survives encoding, and `''` encodes to `''`.

**And a prefix must end on a segment boundary.** Round-2 **M2**: encoding is defined per segment, but
`list` and `deletePrefix` take an arbitrary string. A prefix that stops mid-segment (`dig/ba`) would
have `ba` encoded as though it were a whole segment, matching nothing — returning `[]` or deleting
nothing, silently, which is H3's failure class re-entering through the door H3's fix left open.
**`list`/`deletePrefix` assert the prefix is empty or ends in `/`**, and throw otherwise. All three
production callers pass `dig/${base}/` (§3.3), so this is a precondition they already satisfy.

#### 3.2.2 The encoder is injective, full stop — because canonicalization happens upstream

v2 said the encoder was "injective on NFC-normalized logical keys", which is a property of a function
composed with something the caller might not have applied. v3 makes it unconditional: **the encoder is
injective on its input**, and §3.5 guarantees every input is already canonical.

That is a strictly stronger and simpler contract, and it is what makes behavior 4 stateable as a plain
property test rather than one quantified over a precondition the production code might not meet.

The two branches cannot collide structurally: a hashed segment contains `=`, which `SAFE` forbids.
`=` is the marker because Storage accepts it (§2.1) and `slugify` can never emit it.

> **Encoding is per segment, so related keys hash independently.** The summary key's segment is
> `003_돈….md` while the dig prefix's segment is `003_돈…` — different strings, different hashes.
> Nothing may assume the physical dig prefix is a substring of the physical summary key. Every
> consumer relying on that relationship (`remap()`, `MODEL_KEY`, `pdfRelPath`) works on **logical**
> keys and is unaffected.

### 3.3 `list()` does not invert the encoding

All three production `list()` callers pass a logical prefix they already hold and read back leaves
that are pure ASCII:

| Caller | Prefix passed | Leaf shape |
|---|---|---|
| `lib/cloud-sync/reconcile-serial.ts:102` | `dig/${base}/` | `{sectionId}.r{V}.md` |
| `lib/dig/cloud/load-dig-for-serve.ts:33` | `dig/${base}/` | `{sectionId}.r{V}.md` |
| `app/api/videos/[id]/dig-state/route.ts:47` | `dig/${base}/` | `{sectionId}.r{V}.md` |

`dig-state/route.ts:50` pins the leaf shape — it parses with `/\/(\d+)\.r\d+\.md$/`. A dig section is
identified by an **integer** (`startSec`), never a heading slug. Both round-1 reviewers verified this
table independently.

So `list(p, prefix)`: encode the prefix, enumerate physical objects beneath it, strip the **physical**
prefix from each result, prepend the **logical** prefix the caller supplied, return. Correct by
construction; no inversion.

**Fail-closed guard, on every segment.** Round-1 **M1**: v1 checked only the leaf, but
`collectObjectPaths` recurses into folders (`supabase-blob-store.ts:159-165`) and the returned
relative key can contain intermediate directory segments. A hashed *intermediate* segment would slip
past a basename-only check, the caller would `get()` it, the adapter would hash the already-hashed
segment, the read would 404, and `load-dig-for-serve.ts:39` would `continue` — silently dropping a
paid dig section, which is the exact outcome the guard exists to prevent. **The marker check applies
to every segment of the relative path the adapter is about to return, and throws.** Unreachable today
(dig blobs are flat), which is why it must be loud if it ever becomes reachable.

### 3.4 Where the change lands

`SupabaseBlobStore` — `objectKey()` (:15) is the single funnel for `put`/`get`/`tryGet`/`delete`/
`promote`/`putStaged`; `deletePrefix` (:131) and `list` (:143-145) encode their prefix, and `list`
re-attaches the caller's logical prefix and applies the §3.3 guard. `copy()` needs no change — it
delegates to `copyBlob`, which re-enters through `tryGet`/`put` with logical keys (verified:
`blob-store.ts:126-131` takes `Pick<BlobStore, 'tryGet' | 'put'>`).

`LocalFsBlobStore` and `InMemoryBlobStore` implement **identity**: both back ends accept Unicode, and
the vault must keep its names (§1).

> Round-1 **L2**: v1 claimed "all three adapters can be tested against the same contract". False for
> `list()` — given a non-ASCII *leaf*, local and in-memory return it while Supabase throws (§3.3).
> **Shared contract:** `put`/`get`/`tryGet`/`copy`/`promote`/`delete` round-trips, and `list` on a
> prefix whose leaves are ASCII. **Deliberately backend-specific:** `list` on a prefix whose leaves
> are not ASCII.

### 3.5 One equivalence relation, not two — the B1 fix

Both round-1 reviewers found the same Blocking. If the physical layer identifies NFC/NFD variants but
every comparison above it stays byte-exact, then `reconcileCloudBase` copies old→new (a no-op,
because they are the same object, reported as `{ok: true, already: true}`), advances the metadata, and
reaches its cleanup:

```ts
// lib/cloud-sync/reconcile-serial.ts:357-361
for (const { from, to } of plan) {
  if (to === from) continue;
  try { await cloud.blob.delete(cloud.p, from); } catch { cleanupFailures += 1; }
}
```

`to === from` is byte-exact, so it deletes `from` — **the object the row it just wrote now points
at**. Summary, magazine model and every paid dig section, gone, while the function returns
`{ok: true, action: 'relocated', cleanupFailures: 0}` and the sync report says success. Reachable via
§2.5's `recoverOrphanedVideos` path.

### 3.5 Canonicalize at INGRESS, not at the seam — v3's architectural change

**v2's fix was to make the seam's equality NFC-aware and update "four sites". That was the wrong
place, and round 2 proved it by finding four more sites:**

| Site | Failure mode under v2 |
|---|---|
| `reconcile-serial.ts:196` — occupancy `holder` check | fails **open**: two videos' bases alias onto one physical object (Codex r2 Blocking; Claude r2 H1b) |
| `reconcile-serial.ts:117-137` — `remap` | fails **closed**: `unmappable-key` → `sync-run.ts:756` throws → the video is stranded on **every** run, forever (Claude r2 H1a) |
| `sync-run.ts:206` — additive collision guard | fails **open**: the guard's own comment says a key collision here *destroys a summary* via promote-as-rename (found by mechanical sweep) |
| `reconcile-serial.ts:102` — `paidKeysUnder` prefix | correct only by a load-bearing coupling to §3.3 that was written down nowhere (Claude r2 H1c) |

Hand-enumeration failed twice on the same question. A seventh site is not the finding; **the list is
the finding.**

**v4 introduces NO equivalence at all.** Keys are byte strings, as they have always been. Every one of
the eight comparison sites is correct *as written*, unmodified, because two different byte strings are
two different keys — which is what the whole system already assumed. There is no ingress list, no
canonicalizer, no `normalizeLogicalKey` change, and no check script for any of it.

Round-3 **B2** is why this is safe rather than reckless. Measured live: with canonicalization removed,
an NFD key writes, stores and **serves** correctly, because the encoder hashes raw bytes and so the
write address and the read address are derived from the same string. Self-consistency was never in
question; only *cross-representation recognition* was, and nothing needs it.

#### 3.5.1 The one real equivalence: the local filesystem

Round-3 **B1**, measured on APFS. The additive create runs in **both directions**
(`sync-run.ts:618-627`): when a video is cloud-only, `to` is `localSide` and the receiver blob store is
`LocalFsBlobStore`. The collision guard at `sync-run.ts:203-213` compares keys byte-exactly, so a cloud
key in one normalization does not match a vault row in the other — the guard passes, and
`LocalFsBlobStore.promote`'s `renameSync` **overwrites a paid vault summary**. APFS is what makes the
two names the same file.

This is unreachable on master (a non-ASCII key cannot be stored today, so no cloud row can hold one)
and **this slice is what makes it reachable** — so it is ours to close.

**The equivalence belongs to the backend, and the backend declares it.** This seam already has exactly
this idiom: `provesAbsence` (`blob-store.ts:60-67`) exists because *"the local FS store returns null
only on ENOENT … the Supabase store swallows … so it cannot"* — a capability difference stated by each
adapter rather than assumed by callers. Add its sibling:

```ts
/** True when two logical keys differing only by Unicode normalization name the SAME object on this
 *  backend. APFS/HFS+ normalize filenames, so the local store aliases them; Supabase Storage is a
 *  byte-exact Postgres index and does not. Optional; absent means FALSE (byte-exact), so an unknown
 *  backend stays conservative. */
readonly aliasesUnicodeNormalization?: boolean;
```

`LocalFsBlobStore` sets it `true`; `SupabaseBlobStore` and `InMemoryBlobStore` leave it absent. The
additive collision guard asks the **receiver's** store, so the check matches the filesystem it is about
to write to:

```ts
const sameKey = (a: string, b: string) =>
  to.blob.aliasesUnicodeNormalization ? a.normalize('NFC') === b.normalize('NFC') : a === b;
```

**Nothing else changes, and nothing is canonicalized on write.** The vault keeps its bytes (§1
decision 1); the cloud keeps its bytes; only this one *comparison*, on the one backend that actually
aliases, is normalization-aware.

> ⚠ **Linux vaults.** `aliasesUnicodeNormalization = true` is correct for APFS/HFS+ and *conservative*
> on ext4, where the two names are genuinely different files: the guard would refuse a write that
> would have been safe. Refusing is the right direction — it throws a named `serial collision` instead
> of silently overwriting. Recorded as accepted.

### 3.6 What does not change

- `lib/slugify.ts` — untouched. Vault filenames keep full-length Unicode.
- `video.summaryMd`, `artifacts.summaryMd.key` — still the logical name.
- `lib/cloud-sync/sync-run.ts` — still copies the key verbatim; §2.6 is fixed underneath it.
- `remap()` — still operates on logical keys only.

> ⚠ **v2 claimed "the three Unicode-aware guards (§5) — still correct". Round-2 B1 falsified that,
> and it was the most dangerous line in the document.** `CLOUD_SUMMARY_MD_KEY`
> (`assert-cloud-summary-md-key.ts:14`) admits `\p{L}` and `\p{N}` only, and a combining mark is
> `\p{Mn}` — neither. Measured: `003_café.md` **passes in NFC and fails in NFD**. So under v2 a
> decomposed accented-Latin key became *storable but unservable*: a durable row advertising
> `status: 'promoted'`, a real object in the bucket, real Gemini spend, and a **409 `corrupt summary
> key`** at `serve-summary-core.ts:56-64` that the user discovers only by opening the document.
> `resolve-summary-key.ts:16` returns `null` for the same key, so the dig path sees no summary at all.
>
> **On master the same input fails LOUDLY** — `upload('003_café.md')` is rejected `400 Invalid key`,
> sync throws at `putStaged`, and the error lands in `report.errors`. v2 would have converted a loud
> failure into a silent paid-but-unreachable summary, **which is the exact shape of backlog #36
> itself**. Note also that Korean — the script every behavior in §6 named — is the one script where
> this cannot appear, because Hangul jamo are `\p{Lo}`.
>
> **v4 fixes it at the guard, which is where the defect is.** `CLOUD_SUMMARY_MD_KEY` admits
> `[\p{L}\p{N}_-]`; it must also admit `\p{M}` (combining marks):
>
> ```ts
> const CLOUD_SUMMARY_MD_KEY = /^[\p{L}\p{N}][\p{L}\p{M}\p{N}_-]{0,127}\.md$/u;
> ```
>
> This guard's job — stated in its own docstring — is to reject slashes, encoded and homoglyph
> separators, whitespace, control characters and over-long keys, so that `models/{base}.json` and
> `pdfs/{base}.pdf` are built from a single safe path component. **It was never meant to have an
> opinion about Unicode normal forms**, and having one is the whole defect: `é` and `e` + U+0301 are
> the same character to every user and to APFS, and a combining mark cannot introduce a separator.
>
> ⚠ **v3 proposed instead to test `mdKey.normalize('NFC')` as a "belt". Round-3 H2 killed that**: it
> has no reachable beneficiary once ingress canonicalization exists, it validates a *different string*
> from the one `base`/`MODEL_KEY`/`pdfRelPath` are then built from — falsifying the guard's own
> docstring — and it destroys the only runtime observation that would ever falsify the invariant it
> was propping up. Widening the character class asserts exactly what is true and nothing more.
- **ADR-0008's money guard survives.** Its corroboration argument depends on the MD key and the model
  key living under the same `${p.id}/${p.indexKey}/` grant. `objectKey` encodes only `key`, so both
  physical keys stay under that prefix (verified in round 1 by both halves).

---

## 4. Why no migration is needed, and exactly how far that is proven

The encoder changes a key iff it is `¬SAFE` **or** longer than `LIMIT`. With `LIMIT = 255`:

- **The length half is now vacuous within the bucket.** A segment over 255 characters was rejected at
  upload (§2.2) and is not there. Hashing such a key is a *fix*, not a re-addressing. v1's `LIMIT = 96`
  is what made this half unsound (round-1 **H1**).
- **The charset half is a strict subset of "rejected" *except* for five characters.** Storage accepts
  space, `(`, `)`, `+` and `=` (§2.1), which `SAFE` excludes. A key using one of those is storable
  today and *would* be re-addressed.

So the proof is: **no migration is needed iff no existing object name uses a character outside
`SAFE`.** Nothing in the codebase can emit one — `slugify` maps every non-alphanumeric to `-`, uuids
and `_staging` are alphanumeric — but that is a claim about the code, and the bucket is the subject.

**Gate — FAILS IF:** any `storage.objects` row in `bucket_id = 'artifacts'` has a path segment
**after the first two** that does not match `^[A-Za-z0-9._-]+$`.

> Round-1 **M3(b)**: the segment predicate must skip `p.id` (owner uuid) and `p.indexKey` (playlist
> key). `objectKey` encodes only `key` (`supabase-blob-store.ts:15-18`), so flagging those two would
> report a Blocking for segments this change cannot re-address. The length half of v1's gate is
> **dropped** — it is vacuous per above.

### 4.1 ⛔ The gate CANNOT RUN today — `claude_ro` is denied on schema `storage`

Attempted 2026-08-14: `select … from storage.objects` as `claude_ro` returns
`ERROR: permission denied for schema storage`. Same shape as the `supabase_migrations` denial fixed
2026-08-12. Two grants fix it permanently; they need `postgres`, so **the user must run them**:

```sql
grant usage on schema storage to claude_ro;
grant select on storage.objects to claude_ro;
```

Until then §4 is **unverified**, and this slice must not be deployed to prod on the assumption that it
is a zero-migration change. It does **not** block writing the plan or the implementation.

> ⚠ **The first version of this gate reported a false PASS.** Run without `ON_ERROR_STOP=1`, `psql`
> printed the "VIOLATIONS (must be zero rows)" header, produced no rows because the query had
> *errored*, and continued — output indistinguishable from a clean result. The gate must run with
> `-v ON_ERROR_STOP=1` and its **exit code checked**. Per the project rule: *"Cannot run" is a
> FAILURE, never a pass.* A gate that cannot distinguish "no violations" from "I was not allowed to
> look" manufactures confidence. (Round-1 **M3(a)** raised the same point independently.)

---

## 5. The three guards that blessed Unicode keys

Not bugs, and **not changed**:

- `lib/html-doc/assert-cloud-summary-md-key.ts:6` — explicitly blesses `0007_한국어.md`.
- `lib/html-doc/build-doc-html.ts:18` — Unicode-aware "so Korean-slug filenames are admitted".
- `lib/serial-migrate-exec.ts:26` — the NFC-normalizing directory scan.

Each validates faithfully what `slugify` produces. What none could check is whether that shape is
**acceptable to the system on the other side of the seam**. A validator written from the producer's
contract always agrees with the producer; only a call to the consumer finds this class of defect.

---

## 6. Behaviors

| # | Behavior | Verified by |
|---|---|---|
| 1 | A `SAFE` logical key ≤ `LIMIT` encodes to itself, byte-identically | unit + property |
| 2 | A non-ASCII logical key encodes to an accepted physical key | unit + integration |
| 3 | NFC and NFD forms of one segment encode to **different** physical keys, and each round-trips to itself | unit |
| 4 | The encoder is injective **on NFC-normalized** logical keys | property |
| 5 | Every encoded segment is ≤ 65 chars; identity segments are ≤ 255 | property |
| 6 | `put` then `get` on a Korean key round-trips the bytes | integration |
| 7 | `putStaged` → `promote` on a Korean key lands at the right final address | integration |
| 8 | `list(p, 'dig/{korean base}/')` returns **logical** keys | integration |
| 9 | `list()` throws on **any segment** it cannot name, rather than dropping it | unit |
| 10 | `deletePrefix(p, '')` removes every object under the playlist root, including non-ASCII-keyed | integration |
| 11 | `list(p, 'dig/{base}/')` and `list(p, 'dig/{base}')` return the same set | unit |
| 12 | `copy()` of a Korean-based dig blob to a new base works end to end | integration |
| 13 | Local and in-memory adapters are identity — a Korean key stays Korean on disk | unit |
| 14 | A Korean-titled video ingests end to end and the summary is readable | integration |
| 15 | A Korean-titled video syncs local → cloud (§2.6) without failing | integration |
| 16 | **A video whose `summaryMd` is `003_café.md` in NFD syncs, and the summary then SERVES 200 with the right bytes, ledger unmoved** | integration |
| 17 | `encodeSegment` is identity on the longest key `CLOUD_SUMMARY_MD_KEY` admits (128-char base + `.md`) | unit |
| 18 | The §4 gate's SQL predicate is derived from the encoder module, not typed | check script |
| 19 | **A cloud→local additive create whose key differs from an existing vault row only by normalization throws `serial collision` and leaves the vault file untouched** | integration, real FS |
| 20 | `LocalFsBlobStore.aliasesUnicodeNormalization === true`; Supabase and in-memory are falsy | unit |
| 21 | `list`/`deletePrefix` throw on a prefix that does not end on a segment boundary | unit |
| 22 | `encodeSegment` is identity-preserving for U+212A (round-2 M1's sole counterexample): raw-branch and raw-hash agree | unit |

**Behavior 16 is rewritten, and why matters.** v2's version — *"relocating a base that differs only by
normalization loses nothing"* — was the sole falsifier for the highest-risk change, and round-2 **B2**
showed it was **vacuous**: v2's own fix 3 made `describeDivergence` report `agreed`, so no relocation
ran and the test exercised nothing. The mutation §7 named to prove otherwise (*remove NFC from
`normalizeLogicalKey` → 16 goes red*) **survived**. v3's version asserts an observable the user cares
about — the summary serves — through a path that cannot be short-circuited by the fix under test.

---

## 7. Testing

TDD per `docs/process-checklists.md`. The encoder is pure, so most of this is offline; behaviors 2, 6–8,
10, 12, 14–16 need the live local Supabase stack.

**Property tests carry the weight** for 1, 4 and 5. Behavior 4 quantifies over **NFC-normalized**
inputs — stating it that way is what makes it writable at all (round-1 **M2**: v1's behaviors 3 and 4
contradicted each other, and *B1 is exactly what behavior 4 would have caught had it been stateable*).
A separate test asserts the seam's comparison helpers agree with the encoder about which keys are the
same — that is the §3.5 contract, and it is the real guard against B1's whole class.

**Mutation testing**, per standing practice — **and v2's mutation list was itself defective**, which is
why this one names the observable each mutation must break rather than the mechanism:

| Mutation | Must turn red |
|---|---|
| `aliasesUnicodeNormalization` → falsy on `LocalFsBlobStore` | **19** (vault file overwritten) |
| The additive guard compares `a === b` instead of asking the receiver store | **19** |
| Widen `SAFE` to include `=` | 4 (needs a crafted preimage — see below) |
| Restrict the `list()` marker check to the leaf | 9 |
| Encode empty segments | 10 and 11 |
| Hash `NFC(s)` instead of `s` in the encoder | 3 and 22 (U+212A) |
| Revert `\p{M}` in `CLOUD_SUMMARY_MD_KEY` | **16** (NFD summary 409s at serve) |

**This table is the third attempt, and the previous two were both defective — which is the point.**
Round-2 **B2** killed v2's list (a sibling mechanism short-circuited the scenario). Round-3 **B2**
killed v3's list *by measurement*: the NFD round trip succeeded with every named mutation applied,
because the mechanism they targeted was not load-bearing. **A surviving mutation is not a weak test;
it is evidence about the code**, and read correctly the second time it said "delete this mechanism",
which is what v4 does.

Each row above now names an **observable a user would notice** — a vault file destroyed, a summary
409ing — and targets a mechanism whose removal is the *only* way to produce it. Round-3 **L1** also
applies: behavior 4's `=`-widening mutation cannot be killed by a sampling property test and needs a
crafted preimage, so it is written as an example-based test, not left to random inputs.

Behavior 5 asserts **65** and **255**, both properties of the encoder and of the measured ceiling. The
per-segment ceiling belongs in this document and in one exported constant — not typed into the SQL
gate (behavior 18).

**Money guard.** Behaviors 14–16 must assert the ledger did not move, using the M3.1-A pattern (PR #98)
— measure spend, do not assert an intention.

---

## 8. Alternatives considered and declined

### 8.1 A reversible encoding (base64url / quoted-printable / punycode)

⚠ **v1 declined this as impossible. It is not** — §2.3 measures base64url of a worst-case Hangul slug
at 247 characters against a 255 ceiling. v1's "cap non-ASCII vault filenames at ~24 characters" was
arithmetic on a budget that does not exist, and that cost to the user's data was never real.

Declined in v2 **on its merits**:

- **Headroom.** 247 of 255 is 8 characters of margin, and it depends on `slugify`'s 60-character cap
  staying at 60. Hashing is 65 characters worst case — 190 to spare — and is insensitive to that cap.
- **Reversibility buys nothing here.** §3.3 shows `list()` never needs to invert, because the caller
  supplies the only non-ASCII part of the answer.

The cost is debuggability: a Korean video's object is no longer self-describing in the bucket. The
`head` run keeps `003_` visible and the DB row holds the readable name.

### 8.2 Opaque keys plus Supabase user metadata

Measured and viable (§2.4). Declined: `list()` does not return user metadata, so recovering N names
costs N `info()` calls — one caller is `load-dig-for-serve`, on the deadline-bounded money path whose
bounding took seven review rounds (#46, PR #67). It also adds a new failure state (an object that
exists but cannot be named) to the subsystem where absent-vs-unreadable has already cost a Blocking,
three Highs and a live double charge. And §3.3 removes the need.

### 8.3 ASCII-ify `slugify` globally

Contradicts decision 1 in §1: the slug is also the vault filename, so this renames the user's files,
and it degrades the measured title to the slug `15`.

### 8.4 Opaque stable keys addressed by `videoId`

Closest to the ⏸ **parked** stable-blob-addressing work (ADR-0006/0007). Changes the address of every
object in the bucket, requiring a full prod migration, and the roadmap says *"Do not resume it by
momentum."* Named so the overlap is recorded rather than stumbled into.

---

## 9. The precondition that is deliberately absent

v1's brainstorm concluded that the highest-value change was a precondition checking storability
*before* Gemini is called. **That reasoning was right about the defect and wrong about this fix.**

The encoding is **total**: every logical key produces an accepted physical key. Every write reaches
Storage through the seam — verified in round 1 by both halves: the only `client.storage.from(` in
non-test code is `supabase-blob-store.ts:20`, with no signed URLs, no public URLs, and no SQL touching
`storage.objects` outside `0007_storage_and_rpcs.sql`. So no unstorable key can exist, and a
precondition asking "is this key storable?" has no observation that would make it fail. Per
`docs/dev-process.md` that is not a gate; adding it would have been a fresh instance of the defect
`scripts/check-gate-falsifiability.py` exists to catch.

The protection is relocated, not dropped: totality becomes property test 5, which *can* fail and would
if someone later narrowed the encoder. (Round 1 confirmed this reasoning, conditional on M2 — behavior
4 being stateable, which §3.2.2 now makes it.)

---

## 10. Risks and open items

| Risk | Handling |
|---|---|
| An existing prod key uses ` `, `(`, `)`, `+` or `=` and would be re-addressed | §4 gate before deploy. Blocking if it returns rows. ⛔ **Currently unrunnable** — needs two grants, §4.1 |
| The 255-per-segment bound differs on prod's storage-api version | Design is insensitive (worst case 65). Do not hardcode it anywhere but the one exported constant |
| **v4 claims deleting canonicalization dissolves the whole class.** Three versions have each claimed to dissolve the previous round's findings and been wrong | Round 4 must attack it. The difference this time is that the claim rests on a **measurement** (round-3 B2: the NFD round trip succeeds without it), not an argument. Verify that measurement independently before trusting it |
| `\p{M}` in `CLOUD_SUMMARY_MD_KEY` widens a security-relevant guard | Combining marks cannot introduce a path separator, and the resolved-path containment check remains the real traversal backstop (`build-doc-html.ts:18`). Behavior 17 pins the length bound. Worth a security reviewer's eye at the PR |
| Round-3 **M1**: `slugify` maps combining marks to `-`, so NFD `café` slugs to `cafe` while NFC slugs to `café` — **different bases**, not different normalizations | Not a v4 defect (v4 canonicalizes nothing), but it means an NFD-titled video and an NFC-titled one get genuinely different slugs. Recorded; no action |
| Bucket browsing gets harder for non-ASCII titles | Accepted (§8.1). `head` keeps `003_` visible; the DB row holds the readable name |
| SHA-256 truncated to 22 base64url chars (~132 bits) | Negligible, and scoped within one owner + playlist prefix |
| The two dead-lettered prod jobs stay unrecovered | Accepted by decision (§1) |

**Not in scope:** render-cache addressing (backlog #25), the parked blob-addressing schema, and any
change to `slugify` or to vault filenames.
