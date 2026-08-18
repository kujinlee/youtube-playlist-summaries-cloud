# Round 11 — adversarial review, Claude half (first adversarial pass on the redesigned §3.6)

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` (**v11**, working
tree), branch `fix/cloud-blob-key-encoding`. Phase 1 — no code written.

Premise tags per `review-method.md:80-90`. `[VERIFIED: file:line]` = read from the working tree this
round. `[MEASURED]` = run this round; probes are pure string/APFS work under `/tmp`, cleaned up, no
Supabase connection made and none needed.

| | Count |
|---|---|
| **Blocking** | 1 |
| **High** | 2 |
| **Medium** | 4 |
| **Low** | 4 |
| Caused by the round-10 redesign itself | H1, M1, M2, L1 (+L4) |
| Caused by the round-9 fixes folded into v10 (§3.4/§3.5) | **B1**, M3, M4, L2 |

**Verdict: NOT CONVERGED.**

**The headline is not where the brief expected it.** Brief item 2 predicted a Blocking in R1's
`promote` contract change; it is not there — I enumerated every caller and **no production caller
relied on `promote` overwriting on the local adapter** (§A below). The Blocking is in §3.4/§3.5, the
sections the spec header declares *"have converged and stayed converged."* They converged at **v9**.
The v10 fold-ins re-opened them, and this is their first adversarial pass.

---

## B1 (Blocking) — `slugify` can produce a key the new predicate REJECTS, so the mint path can produce a video that can never be ingested, and a paid summary that can never be served

**Where the design says otherwise, in two places:**

- §3.5 table, row 1: the servability refusal can be deleted because there is *"no unservable class
  **the mint path can produce**"*.
- §3.4 box: keeping the bound at 131 *"makes the guard a **strict widening in every dimension**"*.

**Both are false. Measured.**

`[VERIFIED: lib/slugify.ts:1-7]`

```ts
export function slugify(title: string): string {
  return title.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 60);
}
```

`slugify` **preserves** every `\p{N}` character. `[MEASURED — probe 2, full sweep of U+0000–U+10FFFF]`
there are **21** characters that are `\p{L}`/`\p{N}` (so they survive `slugify`) and whose **NFKC
form ends in `.`**:

```
U+2488 ⒈ -> "1."   U+2489 ⒉ -> "2."   …   U+249A ⒚ -> "19."   U+249B ⒛ -> "20."   U+1F100 🄀 -> "0."
```

When one of them is the **last** character of the slug, the `.md` suffix completes a `..`:

```
title  "Lesson ⒈"
key    003_lesson-⒈.md
NFKC   003_lesson-1..md          ← contains ".."
CURRENT guard (shipped today, assert-cloud-summary-md-key.ts:14):  ACCEPTS
v11    isServableSummaryKey:                                        REJECTS
```

`[MEASURED — probe 1]` sweeping every codepoint × 4 title shapes produced **63** slugify-derived keys
that the v11 predicate rejects; all of them are this class.

**Two consequences, either one Blocking under the brief's calibration:**

1. **The video can never be ingested on cloud.** §3.5 adds the guard call at the mint
   (`summary-handler.ts:96`). `[VERIFIED: lib/job-queue/summary-handler.ts:96]`
   `const baseName = \`${padSerial(serial)}_${slugify(payload.title)}\`;` — a refusal here fails the
   summary job every attempt, and the v6 `videoId` **repair that would have rescued it was deleted in
   the same section** (§3.5 table, row 2). User decision ③ forbids re-introducing the unreadable
   `003_dQw4w9WgXcQ.md` filename, so there is no repair left at all.
2. **Or, without the mint guard, a paid summary that can never be served.** The encoder makes the key
   storable, `persistSummary(..., 'promoted')` advertises it `[VERIFIED: summary-handler.ts:179]`, and
   `assertCloudSummaryMdKey`'s replacement then 409s the serve path forever
   `[VERIFIED: lib/html-doc/serve-summary-core.ts:61]`.

**Why it survived ten rounds:** §3.4's NFKC-both-forms pass and §3.5's *"the mint path can produce
nothing unservable"* were written into their own sections in different rounds and never cross-derived
against each other — `review-method.md:174-177` Step 2, which this spec ran on §3.6 and not on
§3.4/§3.5. §3.4's premise is *"`slugify` emits only letters, numbers and `-`"*, which is true and
irrelevant: the fold happens **after** slugify, and it turns a legal `\p{N}` into a `.`.

**Fix.** `s.includes('..')` is an over-approximation *of its own stated requirement*. §3.4's
requirement is **a single path component**; with every separator form already rejected on the line
above, a `..` inside a single component cannot traverse anything —
`path.join(indexKey, '003_a..b.md')` is one file. Two options:

- **Principled:** test traversal per `/`-separated segment (`seg === '.' || seg === '..'`), exactly as
  `assertLogicalKey` already does `[VERIFIED: lib/storage/blob-store.ts:87-91]`. This also dissolves
  §3.4's `001_a．．b.md` rejection — which is a **choice (I)**, not a safety property (P). If you keep
  it, say that it is a choice.
- **Minimal:** run the fold-and-substring tests against the key with its trailing `.md` removed.

**And add the falsifier.** Behavior: *"a title ending in U+2488–U+249B or U+1F100 ingests and serves
200"*; mutation: *"fold the whole key including `.md`"* must turn it red. §5 currently has no
behavior at all for the mint/adopt guard calls (see M4).

---

## H1 (High) — R1 never says what `promote` DOES when the final object exists, and the two readings give opposite outcomes. **Caused by the round-10 redesign.**

R1: *"`promote` never overwrites an existing final object … Implement with `link` + `unlink`."*

`[MEASURED — probe 3, real APFS]`

```
linkSync onto an NFD occupant via the NFC key   EEXIST
staged temp still present after the failed link  true
occupant bytes untouched                         OCCUPANT-BYTES
```

`linkSync` **throws**. So an implementer must choose, and R1 does not say:

| Reading | Consequence |
|---|---|
| `promote` rethrows `EEXIST` | **R2's classification is unreachable.** `copyAdditiveVideo` throws at `sync-run.ts:268` and never reaches the read-back, so the crash-resume window — promote landed, `upsertVideo` at `:286` did not — refuses on **every subsequent run, forever**. That is precisely the defect §3.6.1 quotes `copyBlob`'s `already: true` docstring against `[VERIFIED: lib/storage/blob-store.ts:22-24]`, re-entering through R1 |
| `promote` swallows and returns | correct — and it must still remove the temp and `rmdir` the `_staging/<uuid>/` |

**No listed observable distinguishes them.** Behavior 18d (*"`promote` never overwrites an existing
final object — on all three adapters"*) passes under both readings, and so does the mutation row
*"replace `link` with `rename`"*.

Note the shape: R1's whole justification is that `SupabaseBlobStore` already conforms
`[VERIFIED: lib/storage/supabase/supabase-blob-store.ts:112-116]` — and Supabase conforms by
**silently returning**, not by throwing. So the intended reading is almost certainly "swallow"; it is
simply not written, in the one sentence that decides whether R2 exists.

**Fix.** State it: *"`promote` resolves without writing when the final object already exists (matching
`SupabaseBlobStore`), and still removes the staging temp and its directory."* Split behavior 18d into
*"the occupant's bytes are unchanged"* **and** *"`promote` resolves rather than throwing"*, and give
each its own mutation.

---

## H2 (High) — §3.6.4's reason 3 rests on a premise this spec falsifies two sections earlier. The conclusion survives, on a **different and stronger** credential the spec never cites. **Caused by the round-10 redesign.**

This is the brief's item 1. The `[ASSUMPTION]` was re-verified. It does not hold as written.

**What reason 3 claims:** *"Vault names are `${padSerial(serial)}_${slugify(title)}.md`, so two
different videos cannot alias without a serial collision — which the serial-coherence slice exists to
prevent."*

**Falsified by §3.5 of the same document, and by the code.**
`[VERIFIED: lib/pipeline.ts:129-160]` `recoverOrphanedVideos` adopts **any** `*.md` in the playlist
root carrying a `video_id` frontmatter field, and `[VERIFIED: lib/pipeline.ts:104]` `summaryMd = file`
— the on-disk bytes, verbatim, whatever they are. And the serial is not allocated, it is **parsed**:

```ts
// lib/pipeline.ts:106-107
const serialMatch = file.match(/^(\d+)_/);
const serialNumber = serialMatch ? parseInt(serialMatch[1], 10) : undefined;
```

`recoverOrphanedVideos` performs **no collision check** before `upsertVideo`
`[VERIFIED: pipeline.ts:151-154]`. So for adopted rows the naming premise is false and the
serial-coherence work is not the guard reason 3 says it is. `review-method.md:87` — *"a safety fence,
credential, or invariant may not be designed on an `[ASSUMPTION]`"* — applies exactly here.

**The conclusion is nonetheless right, for a better reason. Two credentials, both verified:**

1. **Every summary body embeds its own video id.** `[VERIFIED: lib/ingestion/summary-core.ts:101-116]`
   ```ts
   const frontmatterLines = [ '---', 'tags:', …, `video_id: "${videoId}"`, … ];
   ```
   unconditionally, plus `**URL:** ${youtubeUrl}` on the meta line. And
   `[VERIFIED: lib/pipeline.ts:148-149]` `recoverOrphanedVideos` **refuses to adopt a file that does
   not carry one**. Therefore **two different videos' summary bodies can never be byte-identical**, and
   R2's content-equality test is transitively an *ownership* test. The harm §3.6.4 describes — a row
   advertising `promoted` at a file another key's owner may later rewrite or delete — requires two
   owners, hence two videos, hence different bytes.
2. **`ensureReceiverSlot` already refuses the collision, before any blob write.**
   `[VERIFIED: lib/cloud-sync/sync-run.ts:203-213]` it throws `serial collision` when the receiver
   index holds the sender's `serialNumber` **or** the sender's `summaryMd`, and it runs at `:240`,
   *before* `putStaged` at `:263`. Aliasing filenames must share the numeric prefix (digits do not
   alias under canonical equivalence or case folding), so the serial half catches every aliasing
   collision that has a receiver row at all.

**So: the `video_id`-frontmatter escape hatch (§3.6.4 item 4) is NOT required** — and the reason is
that the fact it would read is *already inside the bytes R2 compares*. That is a stronger result than
"accepted residual", and it costs zero code.

**Fix.** Delete reason 3 and the `[ASSUMPTION]` tag; replace with (1), tagged
`[VERIFIED: lib/ingestion/summary-core.ts:103]` + `[VERIFIED: lib/pipeline.ts:148-149]`, and record
(2) as the second line of defence. Record the falsifier that now matters: **any producer of a vault
`.md` that omits `video_id` frontmatter** — including a future corrections or re-render path that
rewrites the body — and note that the corrections rewrite (backlog #23) is exactly such a path in
flight. Keep item 4 as the named remedy *if that falsifier ever fires*.

---

## M1 (Medium) — §3.6.4's third residual states an argument R3 does not establish. **Caused by the round-10 redesign.**

This is the brief's item 4. The argument is: *"`base` derives from the summary the transfer has just
made authoritative, so the alias resolves to the same video's own model."*

R3 has **two** success branches, and the sentence is only true of one:

```ts
if (!canonicallyEqualName(loserVideo.summaryMd, key)) {
  const dest = await loser.blob.tryGet(loser.p, key);
  if (dest.ok || dest.reason === 'unreadable') throw …;   // (a) refuse
}                                                          // (b) fall through: address was FREE
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

- Branch **(a)** — the names match, or the probe found the address occupied and refused. Fine.
- Branch **(b)** — the names *differ* and the summary address was **free**, so the write proceeds.
  Nothing whatsoever has been established about `models/${base}.json`. `companionTransfer` then
  `put`s over it `[VERIFIED: lib/cloud-sync/sync-run.ts:464]` or `delete`s it `[VERIFIED: :475]`,
  where `base = winnerVideo.summaryMd.replace(/\.md$/, '')` `[VERIFIED: :448]`.

**A reachable chain, every link documented in this file:** two videos sharing a title (so the same
slug); serials diverged between replicas; `reconcileCloudBase` returns `agreed` **without moving**
because `localVideo.serialNumber == null` `[VERIFIED: lib/cloud-sync/reconcile-serial.ts:179]` — the
legacy/adopted-row case; and the other local video's `.md` was deleted by hand while its model
survived, a case `sync-run.ts:686-688` explicitly contemplates (*"the user moved or deleted the .md by
hand"*). The summary address is then free, R3 falls through, and the companion step overwrites or
deletes another video's paid model.

**Not graded higher because it is not a regression:** the same `put`/`delete` runs completely
unguarded today, and aliasing is not required for the harm — a byte-exact base collision does it now.
What this change adds is a *claim of safety* over that path.

**Fix.** Either extend R3's outcome (skip the companion's own address test only when branch (a)
fired), or restate the residual honestly: *"R3 establishes the address is the loser's own only on the
name-match branch; on the free-address branch the companion write and delete remain unguarded, as
today."*

---

## M2 (Medium) — R2 does not name the read primitive, and its classification is not total. **Caused by the round-10 redesign.**

R2 enumerates three outcomes: `equal` / `different` / `unreadable`. The seam returns **four**:

```ts
// lib/storage/blob-store.ts:10-13
export type BlobRead =
  | { ok: true; bytes: Buffer }
  | { ok: false; reason: 'absent' }
  | { ok: false; reason: 'unreadable'; cause: unknown };
```

**`absent` has no branch.** And the primitive is unnamed: R3's snippet uses `tryGet`, R2's prose says
only *"read back the FINAL key and hash it"*. If an implementer reaches for `get`, Supabase collapses
every failure into `null` `[VERIFIED: lib/storage/supabase/supabase-blob-store.ts:29-35]` — the exact
defect class `tryGet`'s own docstring exists to stop (*"use this instead of `get` before any
irreversible or billable decision"*, `[VERIFIED: blob-store.ts:46-56]`) — on the read that decides
whether the row advertises `promoted`.

**Fix.** Name `tryGet`. Add `absent → REFUSE`: `promote` reported success and the object is not there,
which is a fault, not a resume. Add the mutation *"classify `absent` as `equal`"* against the
cloud-receiver behavior (18c).

*(Brief item 5 answered separately: the read-back cost is fine. `runSync` is not deadline-bounded — its
only production entry is the CLI `[VERIFIED: scripts/cloud-sync.ts:65]` — and it is one extra `get`
per **created** video, not per video. A timeout on the read-back throws after a durable promote,
leaving exactly the crash-resume state R2 heals on the next run. Worth one sentence in §3.6.2.)*

---

## M3 (Medium) — "strict widening in every dimension" is false a second, independent way: the two bounds count different units

`[VERIFIED: lib/html-doc/assert-cloud-summary-md-key.ts:14]`
`/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` — under the `u` flag each atom matches one **code
point**. The v11 predicate uses `key.length`, i.e. **UTF-16 code units**.

`[MEASURED — probe 1]` smallest disagreement: `'a' + 64 astral letters + '.md'` — 68 code points, 132
code units. Current guard **accepts**; v11 **rejects**. On BMP-only keys the bound is exactly
preserved (checked over total lengths 4–143: zero disagreements), so round-9 H3's fix is right *for
the input it was tested on*.

No existing prod key can be affected — P1 means no non-ASCII key is in the bucket — which is precisely
why this belongs in the text rather than inside a claim of universality. §3.2 asks the units question
for the encoder (*"`SAFE ⊂ ASCII`, so `String.length` is sound"*) and §3.4 does not ask it for the
guard, on a predicate whose whole subject is now non-ASCII keys.

**Fix.** Say which unit you mean. If code points, `[...key].length`. Add the astral case to behavior
17b, and to the mutation row for the bound.

---

## M4 (Medium) — §3.5's two new call sites have no behavior row, no mutation row, and one of them can never fire

§5 lists 22 behaviors and 17 mutations. **None** covers *"the mint refuses a non-servable key"* or
*"the adopt refuses before the blob write"*. By this spec's own `PROVISIONAL` rule, v10's answer to
Phase 6 finding 1 is unverifiable as written.

And `[MEASURED — probe 1]`: **once B1 is fixed, no `slugify` output can fail `isServableSummaryKey`**
— swept every codepoint against four title shapes, zero failures. So the mint call site is a
**backstop no input reaches**, while §3.5 presents it as half of the answer (*"two call sites, not
machinery"*). Say which it is. (Before B1 is fixed it does fire — on videos that should be accepted.)

Two smaller things at the same site, both new and unreviewed:

- The guard at `summary-handler.ts:96` sits **after** `reserveVideoSlot` (`:95`) and **before** the
  Gemini call (`:101`), so a refusal costs no money — good, and worth stating. But a throw there leaves
  the bare reserved row that only the `PermanentTranscriptError` path rolls back
  `[VERIFIED: summary-handler.ts:126-135]`: the serial is consumed and the job retries to
  `dead_letter`.
- The adopt call at `sync-run.ts:263` is on the additive path, which runs in **both** directions
  `[VERIFIED: sync-run.ts:618-627]`. A refusal there is per-video, caught, and **advances no
  baseline** — so it re-fires on every subsequent run, forever, until a human renames the vault file.
  That is the right behaviour under decision ③, but the spec must say the error message names the
  repair, because the automated repair was deleted.

---

## L1 (Low) — R1's implementation note enumerates the `rmdir` it discovered and omits the `mkdir` that is already there; and it misattributes the orphan directory

`[MEASURED — probe 3]`

```
linkSync into a NON-EXISTENT destination dir     ENOENT
today (renameSync) leaves under _staging          ["u1"]
```

- `promote` today does `fs.mkdirSync(path.dirname(to), { recursive: true })`
  `[VERIFIED: lib/storage/local/local-blob-store.ts:61]`. Dropping it breaks every **nested** key —
  `dig/<base>/<n>.r<V>.md` `[VERIFIED: lib/dig/cloud/write-dig-section-blob.ts:45,50]` — on first write.
- The orphaned `_staging/<uuid>/` directory is **pre-existing**: `renameSync` leaves it too. Behavior
  18f's parenthetical (*"`unlink` removes only the file"*) reads as if `link`+`unlink` introduced it.
  Fixing it is still worth doing; attributing it to the change is not accurate.

## L2 (Low) — behavior 21 names one derivation; there are two

`[VERIFIED: lib/share/serve.ts:47]` returns `mdKey` with no guard call, and
`app/s/[token]/route.ts` derives `base` from it **twice**: `:69` (the md-download filename) and `:78`.
§3.4 cites only `:78`. Put the call inside `getShareServeContext` before `mdKey` is returned, so both
are covered by construction.

*(Verified while there, and not a finding: `fileResponse` handles a newly-reachable non-ASCII `base`
safely — `asciiSafe` maps everything outside printable ASCII to `_`, and `encodeRFC5987`
percent-encodes every non-attr-char byte `[VERIFIED: lib/html-doc/file-response.ts:5-24]`. No header
injection through the widened key.)*

## L3 (Low) — R3's `canonicallyEqualName` is called on a nullable field, and on a cloud loser its probe's `absent` is not provable

- `Video.summaryMd` is optional, and the additive-hydration path reaches `copyToLocal` with a loser
  that has none `[VERIFIED: sync-run.ts:701-708]`. Specify the null behaviour (`false` → take the
  probe branch, which then finds the address free and writes).
- On `copyToCloud` the loser is Supabase, where `absent` means *absent **or** denied*
  `[VERIFIED: supabase-blob-store.ts:39-62]`, `provesAbsence === false`. R3 proceeds to overwrite on
  `absent`, which is today's unconditional behaviour — not a regression, but the fence does not exist
  in that direction and §3.6.2 should not read as if it does.

## L4 (Low) — R1 converges the adapters onto the semantics this repo's own tripwire calls a defect, without saying so

`[VERIFIED: tests/lib/dig/write-dig-section-blob-promote.test.ts:58-74]` is an `it.failing` tripwire
for backlog #22 / architecture-review W2: *"a re-dug section keeps its stale body because
`SupabaseBlobStore.promote` is create-if-absent"*, deliberately written so the suite **goes red when
someone fixes it**. `InMemoryBlobStore` models both semantics precisely so the suite does not *"bake
the disagreement into the suite as a truth"* `[VERIFIED: lib/storage/testing/in-memory-blob-store.ts:15-31]`.
Behavior 18d plus the contract-level mutation row do exactly that.

Nothing breaks today — `writeDigSectionBlob` only ever sees `SupabaseBlobStore`
`[VERIFIED: lib/storage/resolve.ts:81-86]` — but #22's fix now has to live somewhere other than
`promote` (e.g. `writeDigSectionBlob` using `put`, as `model-store.ts:46-52` already does). One
sentence in §3.6.2 saying so, and 18d will not be read later as a decision nobody made.

---

## A. What I checked and found SOUND

The brief asks for this explicitly, and three of these were where a Blocking was predicted.

**Every `promote` caller enumerated (brief item 2) — R1's cost claim holds.** Four production callers:

| Caller | Adapter it can see |
|---|---|
| `lib/cloud-sync/sync-run.ts:268` (`copyAdditiveVideo`) | **local or Supabase** — the only one that reaches `LocalFsBlobStore` |
| `lib/job-queue/summary-handler.ts:178` | Supabase only — `getWorkerStorageBundle` hard-returns `new SupabaseBlobStore(...)` `[VERIFIED: lib/storage/resolve.ts:81-86]` |
| `lib/dig/cloud/write-dig-section-blob.ts:50` | Supabase only, same reason (`dig-handler.ts:59`) |
| `lib/storage/supabase/consistency.ts:37` (`writeArtifact`) | **zero production callers** `[VERIFIED: lib/storage/blob-store.ts:119]`, re-confirmed by search |

The one caller that reaches the local adapter is the one R2 redesigns. **No caller relied on `promote`
overwriting on local**, so R1 changes no existing behaviour outside the path it is written for.
`model-store.ts:43` is a comment, not a caller — the worker's MD commit is `summary-handler.ts:173-178`.

**Both `transferClassA` call sites hold the loser's record (brief item 3).** `copyToCloud` at `:780-782`
— loser is cloud, record is `cv` (`:613`, re-read after relocation at `:765`). `copyToLocal` at
`:791-793` — loser is local, record is `lv` (`:612`). And `canonicallyEqualName` compares the right two
things in both directions: the loser's own `summaryMd` against the key about to be written, which is
the winner's. R4's NFC-equality correctly resolves the §3.6.0 case (row NFD, key NFC → equal → no probe).

**§3.6.0's decisive measurement, re-verified from the READ side.** `[MEASURED — probe 3]`
`readFileSync(<NFC path>)` returns the **NFD** occupant's bytes, and `readdir` still shows the NFD
name. So R2's read-back genuinely reads the aliased occupant and can classify it — the mechanism does
what §3.6.2 claims.

**P4, P5, P6 (brief item 7).**
- **P4 holds** — exactly three production `list()` callers, all passing `dig/<base>/`:
  `reconcile-serial.ts:102`, `load-dig-for-serve.ts:34`, `app/api/videos/[id]/dig-state/route.ts:47`.
- **P5 holds** — exactly two callers of `assertCloudSummaryMdKey`:
  `lib/dig/cloud/resolve-summary-key.ts:16` and `lib/html-doc/serve-summary-core.ts:61`.
- **P6 re-verified independently.** The spec labels it `MEASURED (grep, …)` and `grep` is broken in
  this environment (ugrep, silently returns nothing), so I re-ran it with a Node walker **plus a
  self-test** (210 files scanned, 80 hits — a zero would have meant a broken search, not a clean
  result). Every URL in `lib/`, `app/`, `components/`, `worker/` is built from `videoId`,
  `playlistId`, `outputFolder`, `token` or `jobId` — never from `summaryMd`/`mdKey`/`base`. The only
  filename-derived URI is `components/VideoMenu.tsx:39`, `encodeURIComponent`'d. **P6 holds** — but its
  provenance should read `QUOTED`/`re-verified`, not `MEASURED`, because a search proves absence only
  as well as the search works, and this one did not.

**The R1→R2 shape itself.** Attacked and it held: writing first with a primitive that physically cannot
clobber, then reading only to decide how to *report*, removes the TOCTOU that four rounds of
check-then-write could not close, and it is the same three lines in both directions. Every finding
above is about **what the spec fails to say** about that shape — not about the shape.

## B. Escalation bookkeeping (the brief's rule, applied to me)

**Four of my findings are caused by the round-10 redesign itself** — H1, M1, M2, L1 (L4 is
redesign-adjacent). Under `review-method.md:45-49` that makes this **round 1 of a new FIX cycle on
§3.6**; two more rounds like it re-arm FIX→REDESIGN.

**But they are all specification-completeness defects, not mechanism defects**, and that distinction
should be recorded before the counter is read later: *what does `promote` do on EEXIST*, *which read
primitive and is the classification total*, *which branch does the residual actually cover*, *which
adjacent `mkdir` was dropped*. None of them says R1–R4 is the wrong shape. That argues for FIX, and
specifically against a second REDESIGN.

**The load-bearing bookkeeping is elsewhere.** §3.4/§3.5 are declared *"converged and stayed
converged"* in the v11 header. That claim is about **v9**. The length bound, the bidi rejection, the
`raw/`-and-adopt correction, the two new mint/adopt call sites and the share-path guard were folded in
**after** round 9 and have had **no** adversarial pass until this one — and the first one produced a
Blocking (B1), a Medium that falsifies a `MEASURED` claim (M3), and a Medium that finds the fix
unverifiable (M4). The convergence sentence needs to be scoped to v9 explicitly, or it will be read as
covering code that was never reviewed.

---

## Appendix — probes

macOS 25.5.0, Node v22.14.0, all scratch under `/tmp` (`r11-probe1.mjs`, `r11-probe2.mjs`,
`r11-apfs.mjs`, `r11-apfs2.mjs`), APFS on `/System/Volumes/Data`, temp trees removed. **No Supabase
connection was opened** — every measurement here is pure string work or local filesystem behaviour, so
the `127.0.0.1` assertion was not needed and no cloud object was created or touched. No tracked file
was modified.

**Probe 1 — slugify × the v11 predicate, full codepoint sweep + length units**

```
A. slugify-produced keys that FAIL the new predicate: 63
   e.g. { title: 'U+2488',  key: '003_⒈.md' }   { title: 'U+2489', key: '003_⒉.md' }  …
B. key = 'a' + <100 astral letters> + '.md'
   code points: 104   UTF-16 units: 204
   CURRENT guard accepts: true     v11 predicate accepts: false
   smallest disagreement: { astral chars: 64, code points: 68, units: 132 }
C. BMP ASCII disagreements over total length 4..143: NONE (bound preserved)
D. '003_팔란티어.md' NFC (11 units) and NFD (17 units): both guards accept
```

**Probe 2 — which characters survive `slugify` yet break the predicate**

```
\p{L}/\p{N} chars whose NFKC contains '/' or '\':  0
\p{L}/\p{N} chars whose NFKC ENDS IN '.':          21
  U+2488 ⒈ -> "1."   … U+249B ⒛ -> "20."   U+1F100 🄀 -> "0."
control-folding:                                    0

"Lesson ⒈"        -> 003_lesson-⒈.md      NFKC 003_lesson-1..md   CURRENT true   v11 false
"第⒈回 팔란티어 분석" -> 003_第⒈回-…-분석.md   NFKC …第1.回…          CURRENT true   v11 true   (not trailing)
```

**Probe 3 — real APFS**

```
1 readFileSync(NFC) with NFD occupant            OCCUPANT-BYTES
1 readdir                                        ["<NFD>"]
2 linkSync onto NFD occupant via NFC key         EEXIST
2 staged temp still present after failed link    true
2 occupant bytes untouched                       OCCUPANT-BYTES
3 after link+unlink, _staging tree               ["uuid-2"]
3 final content                                  NEW-BYTES
4 existsSync(NFC) with NFD occupant              true
5 linkSync into a NON-EXISTENT destination dir   ENOENT
today (renameSync) leaves under _staging          ["u1"]
```

NOT CONVERGED
