# Cloud blob keys — encode at the storage seam so a title in any language can be stored (backlog #36)

**Status:** draft v1, awaiting user approval. **Branch:** `fix/cloud-blob-key-encoding`.
**Origin:** backlog **#36** 🔴, filed 2026-08-12 by the first real M3 acceptance run against prod
release v6. Earlier sighting: `docs/local-validation-findings.md` §BUG-4, filed P2 during local
validation and correctly diagnosed there — it became 🔴 only when the acceptance run showed the
failure lands *after* the Gemini charge.

> **In one paragraph:** every blob key is `${padSerial(serial)}_${slugify(title)}`, and `slugify`
> keeps any Unicode letter. Supabase Storage rejects any object key containing a non-ASCII character,
> so a Korean-titled video's summary cannot be written — but only *after* Gemini has been called and
> billed. This slice moves the storage-safety concern into the Supabase adapter, which maps a
> **logical key** (what the vault, the database and the sync path speak) to a **physical key** (what
> Storage will accept). Everything above the seam keeps speaking Unicode and is unchanged.

> ⚠ **Correction carried from the design discussion.** The brainstorm concluded with "add a
> precondition that checks storability before spending". **That guard is now deliberately NOT in this
> design**, because the chosen encoding is *total* — no logical key can fail to encode — so the
> precondition could never fire. An assertion that cannot fail is the defect
> `scripts/check-gate-falsifiability.py` exists to catch, and filing one here would have been a
> second instance of it. The protection it was meant to give is instead a **property test on the
> encoder** (§7), which can fail and does mean something. See §9.

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

13 candidate keys, uploaded to the `artifacts` bucket:

| Accepted | Rejected — `400 InvalidKey` |
|---|---|
| `003_hello-world.md` | `003_돈-버는-방식은-정해져-있다.md` (Hangul) |
| `003_Upper_Case.md` | `003_日本語のタイトル.md` (Japanese) |
| `003_a(b)c.md` | `003_privet-привет.md` (Cyrillic) |
| `003_a+b=c.md` | **`003_cafe-résumé-año.md` (accented Latin)** |
| `003_a b.md` | `003_strasse-ß-ø.md` |
| | `003_party-🎉.md`, `003_a~b.md`, `003_a%20b.md` |

**Every non-ASCII letter is refused, including French, Spanish, German and Portuguese.** The backlog
filed this as "non-ASCII (Korean)"; a `résumé` in a title destroys a paid summary identically. Any
fix scoped to Korean, or to transliteration of one script, is scoped wrong.

Also note `%` is **rejected**, which rules out percent-encoding — the obvious reversible scheme.

### 2.2 The length limit — 267 characters, and it fails as a 500

Bisected: **maximum accepted object key length is 267; the first rejection is at 268.** Over-length
does **not** produce `400 InvalidKey`. It produces:

```
{"statusCode":"500","error":"Internal","message":"Internal Server Error","code":"InternalError"}
```

A `500` is indistinguishable from a transient fault, so a retrying caller will retry something that
can never succeed. This matters on the serve path specifically, where `max_serve_attempts = 5`.

The budget this leaves for a logical key:

| Component | Chars |
|---|---|
| owner uuid + `/` | 37 |
| YouTube playlist id + `/` | 35 |
| `_staging/` + uuid + `/` (every write is staged) | 46 |
| **Fixed overhead** | **118** |
| **Remaining, of 267** | **149** |

> The design below is **insensitive to the exact bound** — its worst-case key is ~70 characters — so
> a local-only measurement is sufficient to justify it. The number is recorded because it is what
> ruled out the reversible alternatives, not because anything depends on its precise value.

### 2.3 Why every reversible encoding was ruled out

A 60-character Korean slug is 180 UTF-8 bytes. Encoded into the accepted charset:

| Scheme | Result | Fits 149? |
|---|---|---|
| quoted-printable (`=HH`) | 540 | no |
| base64url | 240 | no |
| punycode | ~180 | no |
| information-theoretic floor | ~135 | only with zero margin, before dig nesting |

Reversibility at current slug lengths is not achievable. This is what sent the design to §3.

### 2.4 Supabase user metadata — measured, then found unnecessary

Investigated as "Approach B": store the logical name in object metadata and recover it on `list()`.

| Question | Answer |
|---|---|
| Does `upload({ metadata })` persist? | **Yes** |
| Does `list()` return it? | **No** — only `eTag, size, mimetype, cacheControl, lastModified, contentLength, httpStatusCode` |
| Does `info()` return it? | **Yes**, one call per object |
| Do `move()` / `copy()` preserve it? | **Yes**, both |

Mechanically viable. **Declined** — see §8.2 — because §3 removes the need for it entirely.

### 2.5 What the local side did, and the bug it did hit

`LocalFsBlobStore.abs()` is `path.join(p.indexKey, key)` — **identity, no encoding**. APFS and ext4
accept arbitrary UTF-8 filenames, so Korean names have always worked locally. Local limits are **255
bytes per path component**; Supabase's is **267 characters for the whole path**. Different unit,
different scope — which is why the wall was invisible from the local side, and why the three
Unicode-aware guards (§5) were written believing Unicode keys are legitimate. Against the only
backend anyone had tested, they were right.

The local side did hit one real bug with Korean names, and it is load-bearing here. Commit
`08797e4`, *"fix(serial): make backfill migration converge in one pass + tolerate filename
normalization"*:

> The serial-number backfill could leave files unprefixed after a single `--apply`: a Korean-titled
> file stored in a non-canonical Unicode normalization was skipped on the first pass and only renamed
> on a second `--apply`.

Fixed by `findByNormalizedName` (`lib/serial-migrate-exec.ts:26`), whose comment states the reason:
*"`existsSync` is only NFC↔NFD tolerant on APFS (and byte-exact on Linux)."* Regression test:
`tests/lib/serial-migrate-normalization.test.ts`, built on the Korean title `팔란티어-대체될까`.

**Consequence for this design.** macOS normalizes filenames for you; Supabase Storage is a Postgres
row with a byte-exact index and does not. Without normalization, NFC and NFD forms of one title
produce **two different physical keys** — one video, two objects, or a read that misses an object
that exists. A miss reads as 404-shaped, which `tryGet` classifies `absent`, which is precisely the
conflation that already cost this project a Blocking, three Highs and a live 6¢→12¢ double charge
(`docs/adr/0008`, `provesAbsence`). **NFC normalization is therefore part of the encoding contract,
not a defensive extra** — and `lib/cloud-sync/content-hash.ts:12` already applies the same rule to
content, so this makes keys consistent with bodies rather than introducing a new concept.

### 2.6 The second entrance the backlog did not name

`lib/cloud-sync/sync-run.ts:263` pushes the **sender's** key verbatim into the receiver's blob store:

```ts
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
```

`slugify` is never called on this path. Any existing vault summary with a non-ASCII title fails
identically the moment it syncs to cloud. This is an **addressing-contract** defect with two
entrances, not an ingest defect. Fixing it at the seam closes both at once; fixing it in the cloud
ingest pipeline would have closed one.

---

## 3. The design

### 3.1 The seam already has the vocabulary

`lib/storage/blob-store.ts` does not promise that a key is a storage path. It documents **logical
keys**: `list()` is *"List logical keys (relative to the owner root)"*, `deletePrefix` takes a
*"logical prefix"*. Nothing above the seam has ever been told logical and physical are the same
string. This slice makes the Supabase adapter use that latitude; the interface is unchanged.

### 3.2 The encoding

Per **path segment**, after NFC normalization:

```
SAFE  = /^[A-Za-z0-9._-]+$/          // exactly what existing keys use
LIMIT = 96                            // per segment; far below any observed bound

encodeSegment(s):
  n = s.normalize('NFC')
  if SAFE.test(n) && n.length <= LIMIT:  return n            // identity
  head = leading run of [A-Za-z0-9._-] in n, truncated to 32
  ext  = trailing /\.[A-Za-z0-9]{1,8}$/ of n, else ''
  return `${head}=h${base64url(sha256(utf8(n))).slice(0, 22)}${ext}`
```

`003_돈-버는-방식은-정해져-있다.md` → `003_=hJ8kQ2m….md`.

Four properties, each of which is a test in §7:

- **Total.** Every input produces an accepted key. No logical key can be unstorable.
- **Bounded.** Worst case is 32 + 2 + 22 + 9 = 65 characters per segment, against a 149 budget.
- **Identity on everything that exists.** A key already made only of `SAFE` characters is emitted
  unchanged. See §4.
- **Injective.** The two branches cannot collide, structurally: a hashed segment contains `=`, which
  `SAFE` forbids, so no identity-encoded segment can ever equal a hashed one. Within the hashed
  branch, injectivity is SHA-256 over the full normalized segment (the truncated `head` is
  decoration; it is not what distinguishes two keys).

`=` is the marker because Storage accepts it (§2.1) and `slugify` can never emit it — it maps every
non-alphanumeric to `-`.

> **Encoding is per segment, so related keys hash independently and that is correct.** The summary
> key's segment is `003_돈….md` while the dig prefix's segment is `003_돈…` — different strings, hence
> different hashes. Nothing may assume the physical dig prefix is a substring of the physical summary
> key, the way the logical ones are related. Every consumer that relies on that relationship
> (`remap()`, `MODEL_KEY`, `pdfCacheKey`) works on **logical** keys and is unaffected; the constraint
> is only that nothing new starts deriving one physical key from another.

### 3.3 `list()` does not invert the encoding

This is the step that makes a non-reversible encoding legal, and it is the whole reason §2.3 stopped
being a constraint.

**All three production `list()` callers pass a logical prefix they already hold, and read back leaves
that are pure ASCII:**

| Caller | Prefix passed | Leaf shape |
|---|---|---|
| `lib/cloud-sync/reconcile-serial.ts:102` | `dig/${base}/` | `{sectionId}.r{V}.md` |
| `lib/dig/cloud/load-dig-for-serve.ts:34` | `dig/${base}/` | `{sectionId}.r{V}.md` |
| `app/api/videos/[id]/dig-state/route.ts:47` | `dig/${base}/` | `{sectionId}.r{V}.md` |

`dig-state/route.ts:50` proves the leaf shape — it parses with `/\/(\d+)\.r\d+\.md$/`. A dig section
is identified by an **integer** (`startSec`), never by a heading slug. The only non-ASCII component of
these keys is `base`, and `base` arrives *in the caller's prefix*.

So `list(p, prefix)`:

1. encode `prefix` → physical prefix,
2. enumerate physical objects beneath it,
3. strip the **physical** prefix from each result,
4. prepend the **logical** prefix the caller supplied,
5. return.

Correct by construction. No inversion anywhere.

**Fail-closed guard.** If a returned leaf itself carries the `=h` marker, the adapter cannot name it
and **throws**. It must never silently drop the entry: a dropped leaf is an invisible dig section,
i.e. paid content vanishing, which is #36's own failure class re-entering through the fix. No
production path can reach this today (only tests call `list(p, '')`), which is exactly why it needs
to be loud if one ever does.

### 3.4 Where the change lands

`SupabaseBlobStore` only. `objectKey()` is the single funnel for `put`/`get`/`tryGet`/`delete`/
`promote`/`putStaged`, so encoding there covers six of the eight methods:

| Site | Change |
|---|---|
| `objectKey()` (:15) | encode each segment of `key` |
| `deletePrefix()` (:131) | encode the prefix |
| `list()` (:143-145) | encode the prefix; re-attach the caller's logical prefix to results; guard per §3.3 |
| `copy()` | none — delegates to `copyBlob`, which re-enters through `tryGet`/`put` |

`LocalFsBlobStore` and `InMemoryBlobStore` implement **identity**: both back ends accept Unicode, and
the local vault must keep its names (§1). The encoder is a pure module so all three adapters can be
tested against the same contract.

### 3.5 What does not change

Nothing above the seam. Specifically, and deliberately:

- `lib/slugify.ts` — untouched. Vault filenames keep full-length Unicode.
- `video.summaryMd`, `artifacts.summaryMd.key` — still the logical (possibly Unicode) name.
- `lib/cloud-sync/sync-run.ts` — still copies the key verbatim; §2.6 is fixed underneath it.
- `lib/cloud-sync/reconcile-serial.ts` `remap()` — still operates on logical keys only.
- The three Unicode-aware guards (§5) — still correct, because they validate *logical* keys.

---

## 4. Why no migration is needed, and why that is provable

**The set of keys the encoding changes is exactly the set Storage would have rejected.** A key made
only of `SAFE` characters and within `LIMIT` is emitted byte-identically; a key outside that set was
refused at upload and therefore **is not in the bucket**. No existing object can change address.

This is a proof, not an expectation — but it rests on one premise that must be **verified before
deploy, not assumed**: that no key already in the bucket falls outside `SAFE`. Storage accepts space,
`(`, `)`, `+`, `=` (§2.1), which `SAFE` excludes, so such a key would be re-addressed and orphaned.
Nothing in the codebase can emit those characters, but "nothing can emit it" is a claim about the
code, and the bucket is the subject.

**Gate — FAILS IF:** `select name from storage.objects where bucket_id = 'artifacts'` returns any row
having a path segment that either does not match `^[A-Za-z0-9._-]+$` **or exceeds `LIMIT` (96)
characters**. Run against **prod** before deploy. Put the SQL in a file (`docs/plugins.md`, and the
`claude_ro` recipe in memory).

> The length half of that gate is not decoration. `encodeSegment` hashes on *either* condition, so a
> segment that is `SAFE` but longer than `LIMIT` would also be re-addressed and orphaned. Checking
> only the charset would have proved half of what §4 claims. Nothing in the codebase can produce one
> — `slugify` caps at 60, so the longest emitted segment is ~67 — but that is again a claim about the
> code, and the bucket is the subject.

### 4.1 ⛔ The gate CANNOT RUN today — `claude_ro` is denied on schema `storage`

Attempted 2026-08-14. `select … from storage.objects` as `claude_ro` returns:

```
ERROR:  permission denied for schema storage
```

**This is the same shape as the `supabase_migrations` denial** fixed on 2026-08-12: the read-only
role built to answer questions about prod cannot reach the one object the question is about. Two
grants fix it permanently. They require `postgres` (the schema is owned by it and `claude_ro` is not
superuser), so **the user must run them in the Supabase SQL editor**:

```sql
grant usage on schema storage to claude_ro;
grant select on storage.objects to claude_ro;
```

Until then §4 is **unverified**, and this slice must not be deployed to prod on the assumption that it
is a zero-migration change. It does **not** block writing the plan or the implementation.

> ⚠ **The first version of this gate reported a false PASS, and that is worth recording.** Run without
> `ON_ERROR_STOP=1`, `psql` printed the "VIOLATIONS (must be zero rows)" header, produced no rows
> because the query had *errored*, and continued — output that reads exactly like a clean result. The
> gate must therefore be run with `-v ON_ERROR_STOP=1` and its **exit code checked**, so a denial is a
> loud failure rather than an empty success. Per the project rule: *"Cannot run" is a FAILURE, never a
> pass.* A gate that cannot distinguish "no violations" from "I was not allowed to look" is worse than
> no gate, because it manufactures confidence. The working runner is in the plan's task for this gate.

---

## 5. The three guards that blessed Unicode keys

These are not bugs and are **not changed**, but the spec records why they exist so the next reader
does not "fix" them:

- `lib/html-doc/assert-cloud-summary-md-key.ts:6` — explicitly blesses `0007_한국어.md`.
- `lib/html-doc/build-doc-html.ts:18` — Unicode-aware "so Korean-slug filenames are admitted".
- `lib/serial-migrate-exec.ts:26` — the NFC-normalizing directory scan.

Each is internally correct and validates faithfully what `slugify` produces. What none could check is
whether that shape is **acceptable to the system on the other side of the seam**. A validator written
from the producer's contract always agrees with the producer; only a call to the consumer finds this
class of defect. After this slice they are correct *and* their subject is correct: they validate
logical keys, and logical keys really are Unicode.

---

## 6. Behaviors

| # | Behavior | Verified by |
|---|---|---|
| 1 | A pure-ASCII logical key encodes to itself, byte-identically | unit + property |
| 2 | A non-ASCII logical key encodes to an accepted physical key | unit + integration (real Storage) |
| 3 | NFC and NFD forms of one title encode to the **same** physical key | unit |
| 4 | Two different logical keys never share a physical key | property |
| 5 | Every encoded segment is ≤ 65 chars, and the worst-case full path ≤ 200 | property |
| 6 | `put` then `get` on a Korean key round-trips the bytes | integration |
| 7 | `putStaged` → `promote` on a Korean key lands at the right final address | integration |
| 8 | `list(p, 'dig/{korean base}/')` returns **logical** keys | integration |
| 9 | `list()` throws on a leaf it cannot name, rather than dropping it | unit |
| 10 | `deletePrefix` on a Korean base removes exactly that base's objects | integration |
| 11 | `copy()` of a Korean-based dig blob to a new base works end to end | integration |
| 12 | Local and in-memory adapters are identity — a Korean key stays Korean on disk | unit |
| 13 | A Korean-titled video ingests end to end and the summary is readable | integration |
| 14 | A Korean-titled video syncs local → cloud (§2.6) without failing | integration |

---

## 7. Testing

TDD per `docs/process-checklists.md`. The encoder is a pure function, so most of this is fast and
offline; behaviors 2, 6–8, 10, 11, 13, 14 need the live local Supabase stack.

**Property tests carry the weight.** Behaviors 1, 4 and 5 are universally quantified — they are the
real content of "total, bounded, identity, injective" — and a handful of examples would not establish
them. This is also where the deleted precondition's protection actually lives (§9).

**Mutation testing**, per this project's standing practice: each guard must be shown to fail when
the thing it protects is broken. Specifically — remove the NFC normalization and behavior 3 must go
red; widen `SAFE` to include `=` and behavior 4 must go red; remove the `list()` marker guard and
behavior 9 must go red. A guard whose mutation survives is untested, and "untested" is
indistinguishable from "does nothing".

Behavior 5 asserts **200**, not the measured 267. The bound the encoder must satisfy is a property of
the encoder; 267 is a property of today's storage-api and belongs in this document, not in the code.
Testing against 200 leaves visible headroom and means a future storage-api that tightens the limit
does not silently invalidate the suite.

**Money guard.** Behaviors 13 and 14 must assert that the ledger did not move, using the pattern from
M3.1-A (PR #98) — measure spend, do not assert an intention.

---

## 8. Alternatives considered and declined

### 8.1 Quoted-printable / any reversible encoding, with a length cap on the slug

Recommended earlier in the design discussion, then withdrawn. It requires capping non-ASCII vault
filenames at ~24 characters (from 60) to fit the 149-character budget — a real cost to the user's
data — and that cost bought a property (reversibility) that §3.3 then showed is not required.

### 8.2 Opaque keys plus Supabase user metadata

Measured and viable (§2.4), and it preserves full-length vault names. Declined on three counts:

1. **One extra round trip per object on every `list()`**, because `list()` does not return user
   metadata and `info()` is per-object. One of the three callers is `load-dig-for-serve`, on the
   deadline-bounded **money path** whose bounding took seven review rounds (#46, PR #67).
2. **A new failure state:** an object that exists but whose name cannot be recovered — a third value
   in the subsystem where absent-vs-unreadable has already cost a Blocking, three Highs and a live
   double charge.
3. **It buys nothing §3 does not.** Once `list()` re-attaches the caller's prefix, the logical name
   never needs recovering from Storage at all.

### 8.3 ASCII-ify `slugify` globally

What the backlog first imagined. Contradicts decision 1 in §1: the slug is also the vault filename,
so this renames the user's files, and it degrades the measured title to the slug `15`.

### 8.4 Opaque stable keys addressed by `videoId`

Closest to the ⏸ **parked** stable-blob-addressing work (ADR-0006/0007). It would change the address
of **every** object in the bucket, requiring a full prod migration, and the roadmap says in terms:
*"Do not resume it by momentum."* Named here so the overlap is recorded rather than stumbled into.

---

## 9. The precondition that is deliberately absent

The brainstorm concluded that the highest-value change was a precondition checking storability
*before* Gemini is called, converting a post-money failure into a pre-money one. **That reasoning was
right about the defect and wrong about this fix.**

The encoding in §3.2 is **total**: every logical key produces an accepted physical key. If every
write reaches Storage through the seam — which §3.4 establishes — then no unstorable key can exist,
and a precondition asking "is this key storable?" has no observation that would make it fail. Per
`docs/dev-process.md`, that is not a gate; it is a decision wearing a checkbox. Adding it would have
been a fresh instance of the exact defect `scripts/check-gate-falsifiability.py` was built to catch,
inside the fix for a defect found the same way.

The protection is therefore relocated, not dropped:

- **totality** becomes property test 5 (behavior table §6), which *can* fail and would fail loudly if
  someone later narrowed the encoder;
- **the "500 looks transient" hazard** (§2.2) becomes moot on the write path, because over-length is
  now unreachable — but it remains true of Storage generally, and is recorded here as a known
  property rather than being fixed speculatively.

---

## 10. Risks and open items

| Risk | Handling |
|---|---|
| A key already in prod uses ` `, `(`, `)`, `+` or `=`, or a segment over 96 chars, and would be re-addressed | §4 gate, run against prod **before deploy**. Blocking if it returns rows. ⛔ **Currently unrunnable** — needs two grants from the user, §4.1 |
| The 267 bound differs on prod's storage-api version | Design is insensitive (worst case ~70 chars). Not a blocker; do not hardcode 267 in the encoder |
| Bucket browsing gets harder for non-ASCII titles | Accepted. The `head` run keeps `003_` visible and the DB row holds the readable name |
| SHA-256 truncated to 22 base64url chars (~132 bits) | Collision risk negligible, and scoped within one owner + playlist prefix |
| The two dead-lettered prod jobs stay unrecovered | Accepted by decision (§1). Regenerating costs a third charge; not done automatically |

**Not in scope:** the render-cache addressing question (backlog #25), the parked blob-addressing
schema, and any change to `slugify` or to vault filenames.
