# Spec review — cloud blob key encoding (backlog #36), ROUND 5, Claude half

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` **v5**, commit `6e331d5`.
**Branch:** `fix/cloud-blob-key-encoding`. **Date:** 2026-08-14.

**Verdict: NOT CONVERGED.** 1 Blocking, 5 High, 3 Medium, 2 Low.

Everything load-bearing below is either a `file:line` quote or a probe I ran this session. Probe
scripts are at
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/a00a513a-4135-416e-bbf4-48c0416ca19d/scratchpad/{apfs-probe.mjs,sb-probe.mjs,slug-probe.mjs}`.
The Supabase probe asserted `NEXT_PUBLIC_SUPABASE_URL` matched `127.0.0.1`/`localhost` before doing
anything, and removed all four objects it created (`leftover entries: 0`).

The rewrite is a real improvement — §3.3, §3.6 and the behavior-22 deletion all check out, and the
`exists()` idea is strictly better than v4's `aliasesUnicodeNormalization` flag. What it did not fix is
the pattern that produced the last four rounds: **the spec keeps enumerating the write entrances and
keeps missing one**, and **the rows it nominates as its own falsifiers cannot be constructed from the
inputs they name**.

---

## Measurements this review rests on

| # | Probe | Result |
|---|---|---|
| P1 | `statSync` of the NFC name after writing the NFD name, on `/tmp` **and** on the `$HOME` volume | `YES (alias)` both. `readdir` returns the NFD form; `rename` of the NFC name replaces the NFD file's content |
| P2 | Supabase `move()` onto an existing destination (local stack) | `409 "The resource already exists"` — destination **not** overwritten. `copy()` likewise 409. `upload({upsert:true})` **does** overwrite |
| P3 | Storage charset re-check | `003_café.md` **NFC and NFD both `400 Invalid key`**; `003_x~y.md` 400; `003_한국어.md` 400; **`003_my file.md` `ok`** |
| P4 | Full BMP sweep: for every `cp < 0x10000`, does `003_${slugify('a'+chr(cp)+'b')}.md` fail `CLOUD_SUMMARY_MD_KEY`? | **0 rejects** against the current guard, **0** against the `\p{M}`-widened one. `slugify` emitted nothing outside `[\p{L}\p{N}-]` across the whole BMP |
| P5 | `slugify('a'.repeat(59) + '\u{20000}')` | length 60, last UTF-16 unit `d840`, `isWellFormed() === false` — an **unpaired surrogate**, and `CLOUD_SUMMARY_MD_KEY.test('003_…\uD840.md') === false` |
| P6 | `Buffer.from('003_x\uD840.md','utf8')` vs `Buffer.from('003_x\uD850.md','utf8')` | byte-identical (`…78 efbfbd 2e…`) → identical sha256 → **identical physical key** for two different logical keys |

---

## Blocking

### B1 — `transferClassA` is a THIRD write entrance, and the spec names two

**Evidence.** §2.6 names one entrance (`sync-run.ts:263`). §3.5 says the servability precondition runs
"at job start, before the Gemini call, and on the sync path before the blob write" — singular. There
are two writes on the sync path, not one:

- `sync-run.ts:263` — `copyAdditiveVideo`'s `toBlob.putStaged(toP, video.summaryMd, …)` (the one named).
- `sync-run.ts:381` / `:394` — `transferClassA`'s `loser.blob.putStaged(loser.p, key, …)` then
  `await loser.blob.put(loser.p, key, staged, 'text/markdown')`, where `const key = winnerVideo.summaryMd`
  (`:379`), and the receiver record is finalized with `summaryMd: key` (`:399`).

The caller's own comment at `sync-run.ts:722-723` states it plainly: *"the Class-A transfer, which
writes the winner's summaryMd key onto the loser"*.

**Failure scenario.** A two-sided video whose local side wins Class A. `winnerVideo.summaryMd` is a raw
vault filename — §2.5 establishes those enter the index unfiltered (`pipeline.ts:135-138` reads raw
`readdirSync` bytes, `:105` writes them in as `summaryMd`), so it is not `slugify` output and can be
anything the filesystem allows. Say `003_내 요약.md`, or `003_café.md` in NFD.

- **On master this fails LOUDLY**: `putStaged` → Storage `400 Invalid key` (P3 confirms both NFD and NFC
  accented Latin, and Hangul, are rejected) → `transferClassA` throws → per-video error in
  `report.errors`, no baseline advanced.
- **After this slice** the encoder makes it storable, the write succeeds, and the cloud row is finalized
  with `summaryMd: '003_내 요약.md'` and `status: 'promoted'`. `serve-summary-core.ts:61` then throws and
  `:63` returns **409 `corrupt summary key`**; `resolve-summary-key.ts:16` returns `null`, so the dig path
  sees no summary at all.

That is the spec's own §3.5 warning box — *"a durable row advertising `status: 'promoted'`, a real
object, real spend, and a 409 the user finds by opening the document — **which is the exact shape of
backlog #36 itself**"* — reproduced at a site the spec does not cover. The user's paid summary is
unreachable in the cloud and there is no error anywhere.

**Second half of the same finding.** `sync-run.ts:394`'s `put()` is an unconditional overwrite by
design (`:387-393` explains why: Supabase `promote` is create-if-absent, so the loser's stale body would
survive). On the local receiver that is `writeFileSync` + `renameSync` (`local-blob-store.ts:15-20`),
which P1 shows crosses the NFC/NFD alias. §3.4 closes the aliasing hole on the **additive** path only
and says so; it does not mention that the two-sided transfer writes to the same filesystem with the same
alias and no guard at all. Narrower than the additive case (it needs the local index to hold a *different*
video whose key aliases this one), but it is the same hole and the spec asserts the class is closed.

**Fix.** Enumerate the write entrances from the code, not from memory — `grep -n "putStaged\|\.put(" lib/cloud-sync/`
returns `263`, `381`, `394`. Put the servability precondition at the seam or at a single choke point both
paths pass through, so a fourth entrance cannot be added without tripping it. Then say explicitly whether
`transferClassA`'s overwrite is in or out of §3.4's scope, with the reason.

---

## High

### H1 — the injectivity contract is measured FALSE; behavior 4 as written cannot pass

**Evidence.** §3.2: *"`encodeSegment` is **injective over all valid logical segments as raw JS strings**"*,
and behavior 4: *"injective over **arbitrary** logical segments (not a normalized subset)"* — the word
"arbitrary" is doing deliberate work, since round 1's M2 was about exactly this being narrowed.

P6, measured: `'003_x\uD840.md'` and `'003_x\uD850.md'` are different JS strings whose UTF-8 encodings
are byte-identical (`30 30 33 5f 78 ef bf bd 2e 6d 64` — Node maps every unpaired surrogate to U+FFFD).
`sha256(utf8(s))` therefore agrees, `head` (`003_x`) and `ext` (`.md`) agree, so `encodeSegment` maps them
to the **same physical key**. Injectivity over raw JS strings is false.

And unpaired surrogates are producible by this codebase, not a theoretical input. P5: `slugify`'s
`.slice(0, 60)` (`lib/slugify.ts:6`) cuts UTF-16 code units, so a title of 59 ASCII letters followed by an
astral **letter** (CJK Ext-B `U+20000`, Deseret, mathematical alphanumerics — all `\p{L}`, so they survive
the `[^\p{L}\p{N}]+` replacement) slugs to a 60-unit string ending in a lone high surrogate;
`isWellFormed()` is `false`. Two different astral letters at that position give two different lone
surrogates with identical UTF-8 (P6, third line).

**Failure scenario.** The property test behavior 4 mandates fails. `fc.string()` generates lone
surrogates, so this surfaces on the first run — and the likely reaction is to quietly quantify the
property over well-formed strings, which is the *"stated three ways / narrowed to a subset"* move rounds
1–4 kept catching. I could not construct a live data-loss path (a collision also needs matching `head`,
which for the summary key embeds the serial, and two videos cannot share a serial), so this is High, not
Blocking. But an injectivity claim is either true or it is not a contract.

**Fix.** Either (a) narrow the contract honestly — *"injective over well-formed logical segments; the
encoder rejects a segment where `s.isWellFormed()` is false"* — with a matching guard, or (b) hash
`Buffer.from(s, 'utf16le')`, which is lossless on lone surrogates and makes the unqualified claim true.
(b) is one word of code and keeps behavior 4 stateable as written; I recommend it. Either way, say which,
because a property test that has to be weakened to pass is the artifact this project has burned two
rounds on already.

### H2 — `exists()` fails OPEN on the Supabase receiver, and the spec only reasons about the local one

**Evidence.** §3.4: *"The guard must consult `toBlob.exists(toP, key)` rather than scanning index rows …
`exists()` on the aliasing backend answers correctly because the filesystem resolves the alias itself."*

That sentence is true and I verified it (P1: `statSync` of the NFC name finds the NFD file, on both
volumes tested; `local-blob-store.ts:36-39` returns `false` only on `ENOENT` and rethrows every other
errno, and `provesAbsence = true` at `:10`). The **cloud→local** direction is correct.

The **local→cloud** direction gets no analysis at all. `SupabaseBlobStore.exists` is
`supabase-blob-store.ts:78-80`:

```ts
async exists(p: Principal, key: string): Promise<boolean> {
  return (await this.get(p, key)) !== null;
}
```

and `get` at `:35` is `if (error) return null` — the comment at `:29-34` says it *"Swallows EVERY
failure, not just 404: network, 5xx, timeout and RLS denial"*, and `:10` sets `provesAbsence = false`.
The seam already forbids this method for exactly this use. `blob-store.ts:125`:

> *"Note it reads exclusively through `tryGet` — never `exists()` or `get()`, both of which collapse a
> transient failure into the same answer as genuine absence on the Supabase backend."*

and `blob-store.ts:47-48`: *"**Use this instead of `get` before any irreversible or billable decision.**"*
The additive blob write is irreversible. §3.4 adopts the one probe the codebase documents as unsafe here.

**Failure scenario.** Local-only video, cloud receiver, a transient 5xx or an RLS blip on the `exists`
download. The guard reads `false`, passes, and the write proceeds. Measured consequence (P2): Supabase
`move()` onto an occupied destination returns `409 "The resource already exists"` and does **not**
overwrite — so no cloud object is destroyed, which is why this is High and not Blocking. But
`supabase-blob-store.ts:113` and `:121` then treat a present destination as **success**, remove the temp,
and return; `sync-run.ts:271-273` sets `artifacts = { summaryMd: { key, status: 'promoted' } }`. The
receiver row now advertises a promoted summary whose bytes belong to a different video. §3.4 claims this
guard *"also closes a pre-existing byte-exact instance of the same hole"* — on the Supabase side it
closes it only when the network cooperates.

**Second half.** "rather than scanning index rows" reads as a replacement, and the row scan it replaces
is `sync-run.ts:204-210`, which checks **serial** collision as well as key collision — the A1 guard whose
own comment (`:196-201`) records that dropping the key half destroyed a summary. On Supabase the row
scan is the *reliable* check (`readIndex` throws on failure) and `exists()` is the unreliable one; the
spec swaps them on the backend where the swap is backwards. The local-side motive — *"a real vault file
with no index row … precisely what `recoverOrphanedVideos` exists to adopt"* — is filesystem-only:
`recoverOrphanedVideos` is `lib/pipeline.ts:129`, called from `app/api/videos/route.ts:121`, and
`:146` notes it is *"filesystem-only"*. Nothing analogous exists on the cloud side.

**Fix.** Keep the row scan **and** add the store probe; make the store probe `tryGet` (or a new
`tryExists`) so `unreadable` throws instead of reading as absence, matching `copyBlob`'s rule. State the
two directions separately — that asymmetry is the whole content of the guard.

### H3 — §3.5's stated FAILS IF names three observations that are all unconstructible

**Evidence.** §3.5: *"**FAILS IF:** a title yielding a key with a space, `~`, or an emoji is enqueued and
no error is raised before `generateSummary` is called."*

The cloud ingest key is `lib/job-queue/summary-handler.ts:96`:
`const baseName = \`${padSerial(serial)}_${slugify(payload.title)}\``, and `slugify`
(`lib/slugify.ts:1-7`) replaces `[^\p{L}\p{N}]+` with `-`. A space, a `~` and an emoji are all outside
`[\p{L}\p{N}]`, so **no title can put any of the three into the key.** P4 confirms it exhaustively: across
the entire BMP, `slugify` emitted nothing outside `[\p{L}\p{N}-]`, and **zero** characters produced a key
that `CLOUD_SUMMARY_MD_KEY` rejects — in either its current or its `\p{M}`-widened form.

So the one gate in v5 that carries an explicit `FAILS IF:` names a failing observation that cannot occur.
Behavior 19 (*"A title yielding an unservable key raises before `generateSummary` is called"*) is
unconstructible from the same input class, and the mutation row *"Remove the servability precondition →
19"* therefore survives. §5 designates 19 as one of the three falsifiers for §3.4 and §3.5. This is the
round-4 defect — *"a §7 test advertised as the primary guard that cannot fail"* — recurring inside the
rewrite that exists to remove it.

The precondition itself is not vacuous: P5 gives the one reachable falsifier, the lone-surrogate slug from
an astral-letter title, whose key `CLOUD_SUMMARY_MD_KEY` genuinely rejects. The spec does not name it.

Related, and worth correcting in §3.5 because the argument is doing load-bearing work: *"Supabase's `400`
was incidentally enforcing a different constraint … *would `assertCloudSummaryMdKey` accept this key?*"*
The two character sets are **incomparable**, not nested. P3: Storage rejects `café` (which the guard
accepts) and accepts `003_my file.md` (which the guard rejects, since a space is outside
`[\p{L}\p{M}\p{N}_-]`). The `400` was never checking servability; a vault filename with a space is
already storable-but-unservable **today**, before any change on this branch.

**Fix.** Replace the FAILS IF with the construction that works — *"FAILS IF a title of 59 ASCII letters
followed by U+20000 is enqueued and no error is raised before `generateSummary`"* — and write behavior 19
against it. Restate §3.5's motive as "the two charsets are incomparable; the sync path already leaks
unservable keys and the encoder widens the ingest path to match", which is true and still justifies the
precondition.

### H4 — behavior 16 is unconstructible for the same reason, and the `\p{M}` widening has no ingest-path beneficiary

**Evidence.** Behavior 16: *"An **NFD accented-Latin** titled video syncs and then **serves 200**"*.
An NFD *title* cannot produce an NFD key. `café` in NFD is `c a f e` + U+0301; U+0301 is `\p{Mn}`, so
`slugify`'s `[^\p{L}\p{N}]+` replaces it with `-` and the trailing strip removes it — the slug is `cafe`,
pure ASCII, `SAFE`, identity-encoded, and servable today with or without this branch. The spec records
this itself in §8: *"`slugify` maps combining marks to `-`, so NFD `café` slugs to `cafe` and NFC to
`café` — **different bases**"*. §3.5's `003_café.md` example and behavior 16 contradict that row.

P4 quantifies the consequence: **zero** BMP characters in a title yield a key the *un-widened* guard
rejects. The `\p{M}` widening in §3.5 item 1 changes nothing on the ingest path. Its only reachable
beneficiary is a vault **filename** carrying combining marks — from a vault copied off HFS+, created by
another tool, or hand-renamed — reaching the cloud through `sync-run.ts:263` or `:381` (B1).

The widening is still correct and I have no objection to it. The defect is that its justification and its
test both describe a path that cannot produce the input.

**Fix.** Restate behavior 16 as *"a video whose vault **filename** is `003_café.md` in NFD"* and construct
the fixture by planting the file, not by choosing a title. Same for §3.5 item 1's motivating example.

### H5 — the precondition strands the only video that can reach it, permanently, and §1's purpose is then false

**Evidence.** §1: *"Make a video title in any language storable **and servable**"*. §3.5 asserts
servability at job start and offers no remediation for a failure.

**Failure scenario.** A title with astral-plane letters — CJK Extension B is ordinary in Chinese and
Japanese personal and place names — long enough that `slice(0, 60)` lands mid-pair (P5). Today: the job
runs, Gemini is charged, `putStaged` 400s, the job dead-letters — backlog #36 exactly. After this slice
with the precondition: the job raises before the charge (good, that is the point) and the video becomes
**permanently un-ingestible**, because `slugify` is deterministic and every retry produces the same
unservable key. There is no escape: §1 decision 1 fixes the vault filename, and the user cannot see or
edit the slug. The spec converts "paid and lost" into "can never be ingested", calls that done, and states
a purpose the outcome contradicts.

Two mechanical omissions in the same place: §3.5 does not say the raise must be a `NonRetryableError`
(`summary-handler.ts:52-58`, `:130` use it), so a plain throw is classified retryable and burns
`max_attempts` on a deterministic failure, holding a worker slot each cycle; and the check necessarily runs
*after* `reserveVideoSlot` (`:95` — the key needs the serial), so it leaves the bare reserved row behind,
whereas the analogous permanent failure at `:129-137` explicitly deletes it.

**Fix.** Decide what happens to a title the slug cannot represent, and write it down — the cheap answer is
a fallback key `${padSerial(serial)}_${videoId}.md` (always servable, always `SAFE`), which turns the
precondition into a repair rather than a refusal. Whatever is chosen: `NonRetryableError`, and mirror the
`:129-137` bare-row rollback.

---

## Medium

### M1 — the segment-boundary rule contradicts behavior 12, and the rewrite dropped the only predicate that could implement it

§3.2: *"**A prefix must end on a segment boundary.** `list`/`deletePrefix` throw otherwise."* Behavior 12:
*"`list(p, 'dig/{base}/')` and `list(p, 'dig/{base}')` return the same set."*

There is no observation that distinguishes a mid-segment prefix from a complete one — `dig/ba` is a valid
prefix of complete segments and also a truncation of `dig/base`, and both `list` and `deletePrefix` see
only the string. v4 stated the only implementable form of the rule
(`git show 20acdb7:…design.md`, §3.2.1): *"**`list`/`deletePrefix` assert the prefix is empty or ends in
`/`**, and throw otherwise"* — and v4 carried it as behavior 21. v5 dropped both the predicate and the
behavior row while keeping the "throw otherwise" prose, so the rule now has no test and no enforceable
statement, and the predicate that would restore it makes behavior 12 fail.

Consequence is bounded: the only production `deletePrefix` caller is
`app/api/playlists/[id]/route.ts:79` with `''`, and all three `list` callers pass a trailing slash
(§3.3's table — I verified it is complete; `grep` for `.list(` in `lib/ app/ worker/ scripts/` returns
exactly `reconcile-serial.ts:102`, `load-dig-for-serve.ts:34`, `dig-state/route.ts:47`).

**Fix.** Drop behavior 12, restore v4's predicate, restore v4's behavior 21. Nothing calls the
no-trailing-slash form.

### M2 — the sync-path precondition has no user remediation

Once §3.5 asserts servability before the sync blob write, an existing vault file named
`003_my summary.md` (P3: storable today, unservable today, syncing silently today) starts throwing per
video on **every** run and appearing in `report.errors` forever. That is the right direction, but §1
decision 1 says the vault wins and filenames are not touched, so the spec offers the user nothing to do
about it. Say what it is — rename the file, or the `videoId` fallback from H5 — and say whether existing
already-synced rows in this state are repaired or left.

### M3 — the spec does not say where the new guard goes, and the signature does not admit it

The check §3.4 describes belongs at `sync-run.ts:204-210`, inside `ensureReceiverSlot`, whose signature is
`(to: MetadataStore, toP: Principal, playlistMeta, video: Video)` (`:167-170`) — it has no `toBlob`. The
spec says neither where the call lands nor that the row scan is retained alongside it (see H2). For a
spec whose central new mechanism is one call, that is the one thing it should pin.

---

## Low

### L1 — the rewrite dropped the verification that the seam is the only funnel

v4 §9 carried: *"Every write reaches Storage through the seam — verified in round 1 by both halves: the
only `client.storage.from(` in non-test code is `supabase-blob-store.ts:20`, with no signed URLs, no
public URLs, and no SQL touching `storage.objects` outside `0007_storage_and_rpcs.sql`"*, and v4 §3.4
named `objectKey()` (`:15`) as the single funnel for `put`/`get`/`tryGet`/`delete`/`promote`/`putStaged`.
v5 has no "where the change lands" section, and that verification underpins both the totality claim in
§3.2 and the completeness of §4's gate. It is a measured fact worth one line, not 20.

### L2 — the adapter-contract divergence note was dropped

v4 recorded round-1 L2: the three adapters do **not** share a `list()` contract — given a non-ASCII
physical leaf, local and in-memory return it while Supabase throws (§3.3's fail-closed guard). v5 keeps
the guard and drops the note. Anyone writing a shared adapter contract test will rediscover it.

---

## What I checked that would have found a defect of each class, and did not

- **Aliasing / vault destruction (§3.4).** P1 on two volumes: `statSync` crosses the NFC/NFD alias, so
  `LocalFsBlobStore.exists` answers correctly in the cloud→local direction — §3.4's core claim holds.
  `LocalFsBlobStore.promote` (`local-blob-store.ts:58-62`) offers no protection of its own: `from` exists
  after staging, so `!existsSync(from)` is false and it falls straight through to `renameSync`, which P1
  shows replaces the aliased file. The §3.4 guard really is the sole defense, and behavior 17 is
  constructible as written. Findings are H2 (the other direction) and B1 (the other write site), not this.
- **Cloud-side clobber.** P2: Supabase `move()` and `copy()` both 409 onto an occupied destination; only
  `upload({upsert:true})` overwrites, and `putStaged` targets a UUID-unique temp key
  (`supabase-blob-store.ts:104`). No cloud object is destroyed by the additive path. This is why H2 is
  High and not Blocking.
- **Charset and migration reasoning (§2.1, §4).** P3 independently reproduces §2.1: accented Latin in both
  normal forms, `~` and Hangul all `400`; space `ok`. §4's gate predicate and its "first two segments"
  carve-out are right, and `putStaged`'s `_staging/<uuid>/` segments satisfy `^[A-Za-z0-9._-]+$`.
  §4.1's ⛔ is correctly marked unrunnable; I did not attempt to work around it.
- **`list()` callers (§3.3).** Enumerated independently; the table is complete and the leaf shapes hold.
  The marker guard scoped to the physical remainder is correct — a `SAFE` segment can never contain `=`,
  so the guard has no false positives, and excluding the caller's prefix is right because the adapter
  never returns those segments. Behavior 10 and its mutation are constructible. No finding.
- **`copy()` (§3.6).** Verified: `grep -rn "\.copy(" lib/ app/ worker/ scripts/` returns exactly one
  non-test caller, `reconcile-serial.ts:282`, and it is `cloud.blob` — a non-aliasing backend. §3.6's
  "unreachable, and here is the real reason" is accurate. No finding.
- **Behavior 22's deletion.** Correct. v5 hashes the raw segment and normalizes nothing, so U+212A and
  ASCII `K` are simply two strings with two hashes; the branches cannot collide because a hashed segment
  contains `=` and `SAFE` forbids it. Genuinely dissolved, not deferred.
- **The Phase 6 claim that a shared `sameKey()` would be a regression.** I agree, and v5's `exists()` is
  the stronger form of the same judgement: it asks the backend that owns the equivalence instead of
  encoding a guess about it. It is also *more* correct than v4's flag on ext4, where the two names are
  genuinely different files and `exists()` returns `false` — which is why dropping v4's "⚠ Linux vaults …
  recorded as accepted" paragraph was right, not a loss. Byte-exactness at the comparison sites stands.
- **Whether §3.5 is falsifiable at all.** P4 (exhaustive BMP sweep) says no via any BMP title; P5 finds
  the astral truncation that does reach it. So the precondition is falsifiable — H3 is about the spec
  naming the wrong observation, not about the gate being empty. Distinguishing those took the sweep.

**NOT CONVERGED**
