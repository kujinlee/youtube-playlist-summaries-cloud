# Cloud blob keys — encode at the storage seam so a title in any language can be stored (backlog #36)

**Status:** draft **v6**, awaiting user approval. **Branch:** `fix/cloud-blob-key-encoding`.
**Origin:** backlog **#36** 🔴, found 2026-08-12 by the first real M3 acceptance run against prod v6.
Earlier sighting: `docs/local-validation-findings.md` §BUG-4, filed P2 during local validation — it
became 🔴 only when the acceptance run showed the failure lands *after* the Gemini charge.

**Review trail — four dual rounds, eight halves, all NOT CONVERGED.** Full findings on disk at
`docs/reviews/spec-blob-key-encoding-r{1,2,3,4}-{codex,claude}.md`.

| Round | Codex | Claude |
|---|---|---|
| 1 | 1B, 1M, 1L | 1B, 3H, 3M, 2L |
| 2 | 1B | 2B, 1H, 2M, 1L |
| 3 | 1B, 1M | 3B, 2H, 2M, 1L |
| 4 | 0B, 1H | 1B, 3H, 3M, 2L |

> **v5 is a REWRITE, not a fifth layer of edits.** Round 4 found nine items, and **five were stale
> strata** left by four rounds of surgical editing — the encoder's central property stated three
> different ways, a §7 test advertised as the primary guard that cannot fail, and two `### 3.5`
> headings, the first being present-tense analysis of a design v4 had deleted. My own edits had become
> the leading source of findings. Round 4 also recorded, explicitly, that the slice is **not
> mis-scoped** — "a bounded gap, not a mis-scope".
>
> **Four rounds, one mistake, repeated.** v1 put a Unicode-normalization equivalence in the encoder;
> v2 moved it to the storage seam and listed four comparison sites (round 2 found four more); v3 moved
> it to ingress and listed three entry points (round 3 found a fourth, plus a vault-destroying path);
> v4 deleted it. Each time I invoked *"delete the mechanism, don't patch the second instance"* and each
> time I deleted the mechanism's **location**. The deletion is now confirmed by independent probe in
> round 4.

---

## 1. Purpose

Make a video title in any language storable **and servable** in the cloud, without changing the
filenames in the user's Obsidian vault, and without migrating anything already in the bucket.

**Two user decisions, fixed 2026-08-14, not reopened:**

1. **The vault wins.** Local filenames keep their Unicode; the cloud key is what changes. Same call
   `reconcile-serial.ts:18` already made — *"LOCAL IS AUTHORITATIVE … cloud blob keys are invisible."*
2. **No refund, no ledger reconciliation.** The ~156¢ on the two dead-lettered prod jobs stays
   recorded. The money genuinely left; `ever_metered = t` is PR #22's guard behaving correctly.

---

## 2. What was measured

Probes ran against the **local** Supabase stack only; each refuses to run unless the URL is
`127.0.0.1`/`localhost`, and cleans up. Rounds 3 and 4 re-derived every number independently.

**2.1 Charset.** Accepted: ASCII alphanumerics, `-`, `_`, `.`, space, `(`, `)`, `+`, `=`, and a
leading `=`. Rejected `400 InvalidKey`: **every non-ASCII letter** — Hangul, Japanese, Cyrillic, and
**accented Latin** (`cafe-résumé-año`, `ß`, `ø`) — plus emoji, `~` and `%`. The defect is far wider
than "Korean"; a `résumé` destroys a paid summary identically, and `%` rules out percent-encoding.

**2.2 Length: 255 characters per path SEGMENT.** No whole-path bound up to at least 1216. A 1014-char
path is accepted; a 267-char path with one 256-char segment is rejected. Over-length returns **`500
Internal`**, not `400` — indistinguishable from a transient fault, so a retrying caller retries
something that can never succeed.

> ⚠ v1 reported "267 characters, whole path". That was a 12-character prefix plus a 255-character
> segment — the right measurement, the wrong subject, and it was used to eliminate three alternatives
> in a section titled *What was measured*. The probe varied one segment under a fixed prefix, so no
> outcome of it could distinguish the two hypotheses.

**2.3 Reversible encoding was available.** base64url of a worst-case Hangul slug is 247 characters
against a 255 ceiling — accepted. v1 claimed it impossible from the phantom budget in §2.2. §7.1
records why hashing is still chosen.

**2.4 Supabase user metadata.** `upload({metadata})` persists; `list()` does **not** return it;
`info()` does, one call per object; `move()`/`copy()` preserve it. Viable, and declined (§7.2).

**2.5 The local side.** `LocalFsBlobStore.abs()` is `path.join(indexKey, key)` — identity, no
encoding — so Korean vault filenames have always worked. **APFS aliases NFC and NFD** (measured twice:
`wx` creation of the other form returns `EEXIST`; `rename` overwrites). Non-canonical normalization
genuinely enters the index: `pipeline.ts:135-138` reads raw `readdirSync` bytes and `:105` writes them
in as `summaryMd`. Commit `08797e4` and `tests/lib/serial-migrate-normalization.test.ts` record the
local-side bug this already caused.

**2.6 A second entrance.** `sync-run.ts:263` pushes the **sender's** key verbatim into the receiver's
blob store; `slugify` is never called there. Any existing vault summary with a non-ASCII title fails
identically on sync. This is an addressing-contract defect with two entrances.

---

## 3. The design

### 3.1 Encode at the seam

`blob-store.ts` already documents **logical keys** (`list()`: *"List logical keys"*; `deletePrefix`:
*"logical prefix"*). Nothing above the seam was ever promised that logical and physical are the same
string. `SupabaseBlobStore` maps between them; `LocalFsBlobStore` and `InMemoryBlobStore` are identity.

### 3.2 The encoder

Per **non-empty** path segment:

```
SAFE  = /^[A-Za-z0-9._-]+$/     // exactly what existing keys use
LIMIT = 255                      // the measured per-segment ceiling (§2.2)

encodeSegment(s):
  if s === '':                            return ''
  if SAFE.test(s) && s.length <= LIMIT:   return s
  head = leading run of [A-Za-z0-9._-] in s, truncated to 32
  ext  = trailing /\.[A-Za-z0-9]{1,8}$/ of s, else ''
  return `${head}=h${base64url(sha256(utf16le(s))).slice(0, 22)}${ext}`
```

> ⚠ **`utf16le`, not `utf8` — round-5 H1 measured the UTF-8 version non-injective.** Node maps every
> unpaired surrogate to U+FFFD, so `'003_x\uD840.md'` and `'003_x\uD850.md'` have **byte-identical**
> UTF-8 (`…78 ef bf bd 2e…`) and therefore the same hash and the same physical key. That is
> reachable, not theoretical: `slugify`'s `.slice(0, 60)` (`lib/slugify.ts:6`) cuts UTF-16 **code
> units**, so 59 ASCII letters followed by an astral letter — CJK Extension B, ordinary in Chinese and
> Japanese names, and `\p{L}` so it survives the strip — yields a lone high surrogate. `utf16le` is
> lossless on lone surrogates, so injectivity holds as stated.

`003_돈-버는-방식은-정해져-있다.md` → `003_=hJ8kQ2m….md`.

**Contract — one statement, no precondition:** `encodeSegment` is **injective over all valid logical
segments as raw JS strings**, **total** (every input yields an accepted key), and **bounded** (worst
case 65 chars). It hashes the **raw** segment and has no opinion about Unicode: NFC and NFD forms of a
title are different keys naming different objects. `SAFE ⊂ ASCII`, so comparing `LIMIT` against
`String.length` is sound — non-ASCII never reaches the length test.

`=` is the marker because Storage accepts it and `slugify` — which maps every non-alphanumeric to `-`
— can never emit it. The two branches cannot collide: a hashed segment contains `=`, which `SAFE`
forbids.

**Empty segments pass through**, so a trailing `/` survives and `''` encodes to `''`. Both production
prefix shapes (`''` and `dig/${base}/`) contain a trailing empty segment, and both failure modes are
silent — `list` of an absent folder returns `[]`, `remove` of an absent object reports success. Left
unstated, `deletePrefix(p, '')` would silently delete nothing on playlist deletion, after the DB rows
are already gone.

**A prefix must end on a segment boundary.** `list`/`deletePrefix` throw otherwise; a mid-segment
prefix would encode `ba` as a whole segment and match nothing, silently.

**Encoding is per segment, so related keys hash independently.** `003_돈….md` and the dig prefix
`003_돈…` are different strings with different hashes. Consumers relying on that relationship
(`remap()`, `MODEL_KEY`, `pdfRelPath`) all work on **logical** keys and are unaffected; nothing may
derive one physical key from another.

### 3.3 `list()` re-attaches the caller's prefix; it never inverts

All three production callers pass a logical prefix they hold and read back ASCII leaves:

| Caller | Prefix | Leaf |
|---|---|---|
| `reconcile-serial.ts:102` | `dig/${base}/` | `{sectionId}.r{V}.md` |
| `load-dig-for-serve.ts:33` | `dig/${base}/` | `{sectionId}.r{V}.md` |
| `dig-state/route.ts:47` | `dig/${base}/` | `{sectionId}.r{V}.md` |

`dig-state/route.ts:50` pins the leaf shape (`/\/(\d+)\.r\d+\.md$/`) — a dig section is an **integer**
(`startSec`), never a heading slug. So `list(p, prefix)` encodes the prefix, enumerates, strips the
**physical** prefix, prepends the **logical** one, and returns. Correct by construction. This is what
makes a non-reversible encoding legal.

**Fail-closed guard, on the physical remainder only.** If a segment *the adapter did not receive from
the caller* carries the `=h` marker, `list()` throws rather than returning a key it cannot name —
silently dropping one would make a paid dig section invisible. The guard must **not** apply to the
caller's own prefix: a logical key legitimately containing `=` (Storage accepts it) would otherwise
make `paidKeysUnder` throw and strand the video on every run.

### 3.4 The one real equivalence: the local filesystem

The additive create runs in **both directions** (`sync-run.ts:618-627`). When a video is cloud-only,
the receiver is the vault and the receiver blob store is `LocalFsBlobStore`. The collision guard
compares keys byte-exactly, so a cloud key in one normalization does not match a vault file in the
other — the guard passes and `promote`'s `renameSync` **overwrites a paid vault summary**. APFS makes
the two names one file. Unreachable on master; **this slice is what makes it reachable**.

**Ask the filesystem, not the index.** The guard must consult the receiver's blob store rather than
scanning index rows: a real vault file with no index row — precisely what `recoverOrphanedVideos`
exists to adopt — passes a row-based check, and the filesystem resolves the alias itself. This also
closes a pre-existing byte-exact instance of the same hole.

⚠ **Use `tryGet`, not `exists` — round-5 H2.** `exists()` is not the same question on the two
backends. `LocalFsBlobStore.exists` is `statSync`-based with `provesAbsence = true`; but
`SupabaseBlobStore.exists` is `get() !== null` (`supabase-blob-store.ts:78-80`) and `get` *"swallows
EVERY failure … network, 5xx, timeout and RLS denial"* (`:29-33`), so on the cloud receiver a
transient fault reads as **"nothing there"** and the write proceeds. That is the absent-vs-unreadable
conflation that already cost this project a Blocking, three Highs and a live 6¢→12¢ double charge —
arriving through a door this slice would have built.

**The guard reads `tryGet` and fails CLOSED on `unreadable`:**

```ts
const occupied = await to.blob.tryGet(toP, key);
if (occupied.ok) throw new Error(`key collision: ${key} already held`);
if (!occupied.ok && occupied.reason === 'unreadable') throw occupied.cause;  // never treat as free
```

Both directions of the additive create are covered: on the local receiver `absent` is proof
(`provesAbsence = true`), and on the cloud receiver `absent` is only 404-shaped — but the write that
follows is a `putStaged` → `promote`, and **round-5 P2 measured that Supabase `move()` refuses an
existing destination with `409`** rather than overwriting, so the cloud side cannot silently clobber
even if the read was wrong. The destructive case is the local one, where the read is trustworthy.

Nothing is canonicalized on write, on either side. No `normalizeLogicalKey` change, no ingress list,
no canonicalizer. Every existing byte-exact comparison stays correct, because two different byte
strings genuinely are two different keys.

### 3.5 Servability is the precondition — storability is not

`CLOUD_SUMMARY_MD_KEY` (`assert-cloud-summary-md-key.ts:14`) admits `[\p{L}\p{N}_-]` after the first
character. A combining mark is `\p{Mn}`, so `003_café.md` **passes in NFC and fails in NFD** — and
the serve path returns **409 `corrupt summary key`** (`serve-summary-core.ts:56-64`) while
`resolve-summary-key.ts:16` returns `null`, so the dig path sees no summary at all.

**Two changes, and they are not alternatives:**

1. **Widen the guard to admit `\p{M}`** — `/^[\p{L}\p{N}][\p{L}\p{M}\p{N}_-]{0,127}\.md$/u`. Its job
   is to keep the key a single safe path component; it was never meant to have an opinion about normal
   forms, and `é` and `e`+U+0301 are the same character to every user and to APFS. **Verified safe by
   exhaustive sweep (round 4): no `\p{M}` codepoint normalizes under NFC/NFD/NFKC/NFKD into `/`, `\`,
   `%`, whitespace, a control or `.`, and ZWJ is not admitted.**
2. **Repair an unservable key; do not refuse it.** Supabase's `400` was incidentally enforcing a
   constraint that *does* have a failing observation — *"would `assertCloudSummaryMdKey` accept this
   key?"* — and making everything storable dropped the only thing checking it. But the answer is a
   **fallback, not a gate**:

   ```
   if (!accepts(assertCloudSummaryMdKey, `${base}.md`))  base = `${padSerial(serial)}_${videoId}`
   ```

   `videoId` is a YouTube id — always ASCII `[A-Za-z0-9_-]{11}`, always `SAFE`, always servable — so
   the fallback cannot itself fail.

> ⚠ **Round-5 H5: the refusal version was worse than the bug.** A title whose slug cannot be
> represented — 59 ASCII letters then an astral letter, i.e. an ordinary Chinese or Japanese name —
> fails deterministically, so *every retry fails identically*, and §1 decision 1 fixes the vault
> filename so the user cannot edit their way out. A gate there converts *"paid and lost"* into
> **"permanently un-ingestible"**, and §1's stated purpose (*"storable **and servable**"*) would be
> contradicted by the spec's own outcome. **A refusal is only a fix if there is a way out.** The
> fallback gives one: the video ingests, the money buys something the user receives, and the readable
> slug is the only thing lost — for the rare title that cannot be represented at all.
>
> **This also explains three vacuous falsifiers in a row** (rounds 2, 3 and 5): the spec kept writing
> gates for a state that should never have been a failure. Round-5 **P4** proves it exhaustively — a
> full BMP sweep found **zero** codepoints where `slugify` output fails the guard, widened or not. The
> mint path has no reachable refusal; it has a rare **repair**.
>
> **FAILS IF** (constructible, from round-5 **P5**): ingest a title of 59 ASCII letters + `U+20000`.
> Without the fallback the key ends in a lone surrogate and `CLOUD_SUMMARY_MD_KEY.test(…) === false`;
> with it, the summary serves 200 at `${padSerial(serial)}_${videoId}.md`.

**Where the check runs — every write entrance, and there are three.** Rounds 1–5 each found the spec
naming one fewer than exists; §3.5 previously said "the sync path" as though it had one write:

| Entrance | Site |
|---|---|
| Worker mint | `summary-handler.ts:96`, immediately after `baseName` |
| Sync — additive create | `sync-run.ts:263` (`copyAdditiveVideo` → `putStaged`) |
| Sync — **Class-A transfer** | `sync-run.ts:379-399` (`const key = winnerVideo.summaryMd` → `putStaged`/`put` → `summaryMd: key`) — **round-5 B1** |

The Class-A path is the one that keeps being missed, and it is the dangerous one: `winnerVideo.summaryMd`
is a **raw vault filename** (`pipeline.ts:135-138`/`:105` put `readdirSync` bytes straight into the index),
so it is not `slugify` output and can be anything the filesystem allows. On master it fails loudly at
Storage's `400`; after this slice it would store and then 409 at serve.

⚠ **On the sync entrances the fallback is not available** — the key must match the sender's, or the
replica diverges. There, an unservable adopted key is a genuine **refusal**: `NonRetryableError`, a
per-video entry in `report.errors`, no baseline advanced. That is the same loud failure master already
produces, preserved deliberately.

⚠ **Mechanics on the mint path, both currently unstated.** The check runs *after* `reserveVideoSlot`
(`summary-handler.ts:95` — the key needs the serial), so a throw there must (a) be a
`NonRetryableError`, or a deterministic failure burns `max_attempts` holding a worker slot each cycle,
and (b) delete the bare reserved row, mirroring the `PermanentTranscriptError` rollback at `:129-137`.
With the fallback in place this path should not throw at all — but if it ever does, it must do so the
way the rest of the handler does.

### 3.6 What does not change

`lib/slugify.ts`; `video.summaryMd` and `artifacts.summaryMd.key` (still the logical name);
`sync-run.ts`'s verbatim key copy (§2.6 is fixed underneath it); `remap()`. **ADR-0008 survives** —
`objectKey` encodes only `key`, so both physical keys stay under the same `${p.id}/${p.indexKey}/`
grant that the money guard's corroboration argument depends on (verified in rounds 1 and 2).

`copy()` needs no change: it delegates to `copyBlob`, which re-enters through `tryGet`/`put` with
logical keys. ⚠ Its same-key short-circuit **is** wrong on an aliasing backend — measured
`{ok:true, already:true}` for two keys that are one inode — but is **unreachable**, because `.copy(`
has exactly one non-test caller and it is `cloud.blob`. Recorded so the reason is the real one.

---

## 4. Why no migration is needed, and how far that is proven

The encoder changes a key iff it is `¬SAFE` or longer than `LIMIT`. With `LIMIT = 255`:

- **The length half is vacuous within the bucket** — a segment over 255 was rejected at upload and is
  not there. Hashing such a key is a fix, not a re-addressing.
- **The charset half is a subset of "rejected" except for five characters.** Storage accepts space,
  `(`, `)`, `+` and `=`, which `SAFE` excludes. A key using one is storable today and *would* be
  re-addressed.

**So: no migration is needed iff no existing object name uses a character outside `SAFE`.** Nothing in
the codebase can emit one, but that is a claim about the code and the bucket is the subject.

**Gate — FAILS IF** any `storage.objects` row in `bucket_id = 'artifacts'` has a path segment **after
the first two** not matching `^[A-Za-z0-9._-]+$`. (The first two are `p.id` and `p.indexKey`, which
`objectKey` never encodes.)

### 4.1 ⛔ The gate cannot run — `claude_ro` is denied on schema `storage`

`ERROR: permission denied for schema storage`, measured 2026-08-14. Same shape as the
`supabase_migrations` denial fixed 2026-08-12. **The user must run:**

```sql
grant usage on schema storage to claude_ro;
grant select on storage.objects to claude_ro;
```

Until then §4 is **unverified** and this must not deploy on a zero-migration assumption. It does not
block the plan or the implementation.

> ⚠ The first runner reported a **false pass**: without `ON_ERROR_STOP=1`, `psql` printed the
> "must be zero rows" header, returned nothing because the query had errored, and continued. Run it
> with `-v ON_ERROR_STOP=1` and check the exit code. *"Cannot run" is a FAILURE, never a pass.*

---

## 5. Behaviors

| # | Behavior | By |
|---|---|---|
| 1 | A `SAFE` key ≤ `LIMIT` encodes to itself, byte-identically | unit + property |
| 2 | A non-ASCII key encodes to an accepted physical key | unit + integration |
| 3 | NFC and NFD forms of one segment encode to **different** keys, each round-tripping to itself | unit |
| 4 | `encodeSegment` is injective over **arbitrary** logical segments (not a normalized subset) | property + crafted preimage |
| 5 | Every encoded segment ≤ 65 chars; identity segments ≤ 255 | property |
| 6 | `put` → `get` on a Korean key round-trips the bytes | integration |
| 7 | `putStaged` → `promote` on a Korean key lands at the right final address | integration |
| 8 | `list(p, 'dig/{korean base}/')` returns **logical** keys | integration |
| 9 | `list()` throws on a physical-remainder segment it cannot name | unit |
| 10 | `list()` does **not** throw when the caller's own prefix contains `=` | unit |
| 11 | `deletePrefix(p, '')` removes every object under the playlist root | integration |
| 12 | `list(p, 'dig/{base}/')` and `list(p, 'dig/{base}')` return the same set | unit |
| 13 | `copy()` of a Korean-based dig blob to a new base works end to end | integration |
| 14 | Local and in-memory adapters are identity — a Korean key stays Korean on disk | unit |
| 15 | A Korean-titled video ingests end to end and the summary is readable | integration |
| 16 | An **NFD accented-Latin** titled video syncs and then **serves 200** with the right bytes, ledger unmoved | integration |
| 17 | A cloud→local additive create whose key aliases an existing **vault file with no index row** throws and leaves the file untouched | integration, real FS |
| 18 | `encodeSegment` is identity on the longest key `CLOUD_SUMMARY_MD_KEY` admits | unit |
| 19 | A title of **59 ASCII letters + `U+20000`** ingests and the summary **serves 200** at the `${padSerial}_${videoId}.md` fallback | integration |
| 21 | An **adopted** `summaryMd` containing a space, `~`, an emoji or an over-long component is **refused before `putStaged`**, on both sync entrances, with no baseline advanced | integration |
| 22 | `encodeSegment('003_x\uD840.md') !== encodeSegment('003_x\uD850.md')` — lone surrogates stay distinct | unit |
| 23 | The collision guard treats an `unreadable` receiver read as **occupied**, never as free | unit |
| 20 | The §4 gate's SQL predicate derives from the encoder module | check script |

Behaviors **16**, **17**, **19**, **21** and **23** are the falsifiers for §3.4 and §3.5. Each asserts
a **user-visible observable** — the summary serves, the vault file survives, the sync refuses loudly.

> ⚠ **Every input above is now one round 5 proved constructible, because three earlier falsifiers were
> not.** Round-5 **P4** swept the entire BMP and found **zero** codepoints where `slugify` output fails
> `CLOUD_SUMMARY_MD_KEY` — widened or not — so every behavior phrased as *"a title containing a space
> / `~` / an emoji"* tested nothing: `slugify` maps all of them to `-` before the guard sees them. The
> only constructible mint-path input is **P5**'s astral letter at the `slice(0, 60)` boundary, and
> behaviors 19 and 22 now use exactly that. The genuinely unservable keys arrive by **adoption**, not
> by minting — hence behavior 21.

---

## 6. Testing

TDD per `docs/process-checklists.md`. The encoder is pure; 2, 6–8, 11, 13, 15–17, 19 need the live
local stack, and 17 needs a real APFS temp dir.

**Mutations — third attempt; the first two were both defective, which is the point.**

| Mutation | Must turn red |
|---|---|
| `hash(NFC(s))` instead of `hash(s)` in the encoder | 3 |
| The additive guard consults index rows instead of `toBlob.exists` | **17** |
| Revert `\p{M}` in `CLOUD_SUMMARY_MD_KEY` | **16** |
| Remove the servability precondition | **19** |
| Widen `SAFE` to include `=` | 4 (crafted preimage; a sampling property test cannot kill this) |
| Apply the `list()` marker check to the caller's prefix | 10 |
| Encode empty segments | 11 and 12 |

Round-2 B2 killed v2's mutation list (a sibling mechanism short-circuited the scenario). Round-3 B2
killed v3's **by measurement** — the NFD round trip succeeded with every named mutation applied,
because the mechanism they targeted was not load-bearing. **A surviving mutation is evidence about the
code, not about the test**, and read correctly the second time it said *delete this mechanism*.

**Money guard**: 15, 16, 19 assert the ledger did not move, using the M3.1-A pattern (PR #98) —
measure spend, do not assert an intention.

---

## 7. Alternatives declined

**7.1 A reversible encoding.** Available (§2.3): base64url of a worst-case Hangul slug is 247 of 255.
Declined on merits — 8 characters of margin that depends on `slugify`'s 60-char cap, versus hashing's
65-char worst case; and §3.3 shows `list()` never needs inversion. Cost: a Korean video's object is not
self-describing in the bucket. v1 declined this as *impossible*, from the wrong budget.

**7.2 Opaque keys + Supabase user metadata.** Measured viable (§2.4). Declined: `list()` does not
return user metadata, so recovering N names costs N `info()` calls — one caller is
`load-dig-for-serve`, on the deadline-bounded money path whose bounding took seven rounds (#46). Adds
a new failure state (an object that exists but cannot be named) to the subsystem where
absent-vs-unreadable already cost a Blocking, three Highs and a live double charge. And §3.3 removes
the need.

**7.3 ASCII-ify `slugify` globally.** Contradicts decision 1: the slug is also the vault filename, and
it degrades the measured title to the slug `15`.

**7.4 Opaque keys addressed by `videoId`.** Closest to the ⏸ parked stable-blob-addressing work
(ADR-0006/0007). Changes every object's address, requiring a full prod migration; the roadmap says
*"Do not resume it by momentum."*

---

## 8. Risks

| Risk | Handling |
|---|---|
| An existing prod key uses ` `, `(`, `)`, `+` or `=` | §4 gate before deploy; Blocking if it returns rows. ⛔ **unrunnable** — §4.1 |
| Four versions have each claimed to dissolve the last round's findings | v4's deletion is confirmed by **independent probe** (round 4), not argument — but this row stays until behaviors 16/17/19 exist |
| `\p{M}` widens a security-relevant guard | Exhaustive sweep found no mark normalizing into a separator; containment check remains the real traversal backstop. Worth a security reviewer at the PR |
| `slugify` maps combining marks to `-`, so NFD `café` slugs to `cafe` and NFC to `café` — **different bases** | Not a defect here (nothing is canonicalized); recorded so it is not rediscovered |
| The 255 bound differs on prod's storage-api version | Design is insensitive (worst case 65). One exported constant only |
| The two dead-lettered prod jobs stay unrecovered | Accepted by decision (§1) |

**Not in scope:** render-cache addressing (backlog #25), the parked blob-addressing schema, and any
change to `slugify` or to vault filenames.
