# Architecture Review — 2026-08-14

**Trigger:** `docs/dev-process.md` Phase 6, second arming condition — *four adversarial review rounds
without convergence* (added 2026-08-09, bought with twelve of them on the blob-addressing spec).
The subject is the four non-converging rounds on
`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` (backlog **#36** 🔴 — *a
non-ASCII video title destroys the paid summary*).

**Subsystem:** key addressing across `lib/storage/`, `lib/cloud-sync/`, `lib/html-doc/`, `lib/dig/`
and the worker persist path.

**Branch:** `fix/cloud-blob-key-encoding` @ `6e331d5` (spec **v5**).

**Method.** Read `CONTEXT.md` and `docs/adr/0006`, `0007` first, then the spec and all eight review
halves (`docs/reviews/spec-blob-key-encoding-r{1,2,3,4}-{codex,claude}.md`), then the code by hand.
Every claim below cites `file:line` and was opened. Anything I could not open is labelled **LEAD**.
**ADRs are not re-litigated** — finding 7 assesses the *parking decision*, not ADR-0006's content.

---

## The one-paragraph answer

**The architecture is sound and the churn was a specification problem.** I checked this rather than
conceded it: v5's central move — *delete the Unicode equivalence; two byte strings are two keys* — is
correct, the eight comparison sites really are correct unmodified under it, and the round-4 Claude
reviewer reached the same conclusion by independent probe (`spec-blob-key-encoding-r4-claude.md:502-510`,
*"I would not send this to a Phase 6 architecture review looking for [a different shape]"*). I agree.
**But one architectural cause is real and it is what made four rounds necessary:** *"is this key
acceptable?"* is answered by four independent predicates at four layers, and the strictest of them
runs **only on the read path** — so the one that mattered was being enforced, in practice, by an
accident of Supabase's `400 InvalidKey`. That is an instance of a pattern this subsystem uses **five
times**: safety carried by *"nothing currently calls that"* or *"nothing currently produces that
shape."* Each instance is individually correct and individually documented. Nobody counts them, and no
instrument in this repo can. That count is the composition defect.

---

## Findings

| # | Finding | Class |
|---|---|---|
| 1 | Four predicates answer *"is this key acceptable?"*; the strictest runs only on reads | **structural** |
| 2 | `base` — the load-bearing address root — has no owner: 16 inline derivations, 3 definitions | **structural** |
| 3 | The eight comparison sites are **not** the defect; a shared `sameKey()` would be a regression | *no change* |
| 4 | `normalizeLogicalKey` — a surviving key-equivalence relation, zero external callers, known-wrong | **structural** (cheap) |
| 5 | The vocabulary the slice turns on is absent from `CONTEXT.md`; the durable rule has no home | **structural** |
| 6 | A guard whose correctness argument is a claim about another module, with no mechanical link | **structural** |
| 7 | Parking ADR-0006/0007 still matches the evidence; its **stated reason** no longer does | **structural** (one sentence) |
| 8 | Five live safety arguments of the form *"safe because nothing does X yet"*, uncounted | **structural** — the composition defect |

---

## 1. Four predicates answer "is this key acceptable?", and the strictest one runs only on reads

### The evidence

| Predicate | Where | What it admits |
|---|---|---|
| `assertLogicalKey` | `lib/storage/blob-store.ts:87-91` | everything except a leading `/`, a `..` segment, and NUL. **No charset. No length.** |
| `assertCloudSummaryMdKey` | `lib/html-doc/assert-cloud-summary-md-key.ts:14` | `/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` — one path component, no `\p{M}` |
| Supabase Storage's own charset | measured, spec §2.1 | ASCII alnum + `-_.()+=` and space; **rejects every non-ASCII letter** |
| `SAFE` / `LIMIT` (new) | spec §3.2 | `/^[A-Za-z0-9._-]+$/`, 255 per segment |

Now the part that matters. `assertCloudSummaryMdKey` has exactly two non-test callers, and **both are
reads**:

- `lib/html-doc/serve-summary-core.ts:61` — the serve path, which throws **409 `corrupt summary key`**
- `lib/dig/cloud/resolve-summary-key.ts:16` — returns `null`, so the dig path sees no summary at all

There is **no write-path caller.** The key is minted at `lib/job-queue/summary-handler.ts:96`
(`` `${padSerial(serial)}_${slugify(payload.title)}` ``) with no assertion, and it is *adopted* from a
foreign replica at `lib/cloud-sync/sync-run.ts:263` — `putStaged(toP, video.summaryMd, …)`, the
sender's key verbatim — also with no assertion.

### Why it costs you

The strictest predicate in the system runs **after** the bytes are durable, the row says
`status: 'promoted'` (`sync-run.ts:279`), and, on the worker path, after Gemini has been paid. A
predicate whose only enforcement point is downstream of durability cannot prevent corrupt durable
state; it can only report it. What was *actually* gating writes was Supabase's `400`, enforcing a
**different and narrower** set — and the spec's own §3.5 says so: *"Making everything storable dropped
the only thing checking it."* Round 4 named the frame (`r4-claude.md:52-58`): *the slice removes a
barrier that was accidentally doing safety work.*

Four rounds each moved a Unicode-normalization equivalence to a different layer. **That was the wrong
axis.** The problem was never *where the equivalence lives*; it was that the acceptance predicate has
no owner, so removing one layer's constraint silently removed another layer's guarantee. v4 finally
deleted the equivalence — correct — and immediately produced a Blocking of exactly this shape
(`r4-claude.md:78`).

### The minimal structural change — move, do not add

Call the predicate that already exists at the two sites that already exist: the mint
(`summary-handler.ts:96`) and the adopt (`sync-run.ts:263`, before the blob write). The two read-side
calls then become redundant assertions rather than the only gate. This is spec v5 §3.5's change 2;
what this review adds is **why it is architectural rather than a patch** — and therefore why it must
not be dropped if v5 is edited again.

> **FAILS IF:** a video whose `summaryMd` fails `assertCloudSummaryMdKey` reaches a cloud row with
> `status: 'promoted'` by any path.

**Structural.**

---

## 2. `base` is the address root, and it has no owner

`CONTEXT.md:53` states the stake plainly: *"Most blobs are located by deriving their key from the base
rather than by following a stored pointer, which is what makes the base's stability load-bearing:
**change a base and every blob addressed through it becomes unreachable**, including paid ones."*

### The evidence — 16 non-test sites, three definitions

**Definition A — whole key minus `.md`:** `lib/cloud-sync/reconcile-serial.ts:85` (`baseOf`),
`lib/job-queue/dig-handler.ts:57`, `lib/cloud-sync/sync-run.ts:448`,
`lib/html-doc/serve-summary-core.ts:71`, `lib/html-doc/ensure.ts:35`, `lib/html-doc/generate.ts:49`,
`lib/html-doc/rerender.ts:42`, `lib/serial-migrate.ts:34`, `lib/archive.ts:73`,
`app/s/[token]/route.ts:69`, `:78`, `:112`.

**Definition B — `basename()` first, then minus `.md`:** `lib/pdf/pdf-path.ts:26`,
`lib/html-doc/build-doc-html.ts:97`.

**Definition C — dig-deeper-suffix-aware:** `lib/pdf/pdf-path.ts:21-23`,
`lib/html-doc/build-doc-html.ts:90-92`.

(`components/VideoMenu.tsx:53` is display-only and excluded.)

Construction is scattered the same way, **including where a constructor already exists**:

- `MODEL_KEY` is a real function (`lib/html-doc/model-store.ts:32`) and is bypassed by
  `lib/serial-migrate.ts:35` and `lib/cloud-sync/sync-run.ts:475`, both of which hand-write
  `` `models/${base}.json` ``.
- `digBlobKey` is a real function (`lib/dig/cloud/dig-blob-key.ts:22`) and is bypassed by
  `reconcile-serial.ts:102`, `:119`, `:120`, `lib/dig/cloud/load-dig-for-serve.ts:32` and
  `app/api/videos/[id]/dig-state/route.ts:47`, all of which hand-write `` `dig/${base}/` ``.
- `` `pdfs/${base}` `` at `lib/pdf/pdf-path.ts:28` and `lib/pdf/pdf-render-version.ts:22`;
  `` `htmls/${base}.html` `` at `lib/html-doc/generate.ts:65` and `lib/html-doc/rerender.ts:72`.

### Why it costs you — the cost is already on disk

`remap()` (`reconcile-serial.ts:116-139`) is a **hand-maintained inverse** of that scattered
construction. Its own comment states the obligation it creates: *"Every shape below is enumerated
deliberately; a new base-addressed artifact must be added here, and until it is, the reconciliation
refuses to move the record at all."* That is the same failure the spec named in round 2 — *"Hand
enumeration failed twice on the same question. A seventh site is not the finding; **the list is the
finding**"* — living in production code rather than in a document.

The three definitions **disagree**, and the disagreement is already written down as a comment rather
than fixed: `reconcile-serial.ts:127-131` explains that `dig-section.ts:83` builds a name from
`path.basename(summaryMdName)`, so a video whose `summaryMd` is `raw/275_x.md` gets a bare
`275_x-dig-deeper.md`, and comparing whole keys "refuses that pair and strands the video where the old
code could move it."

**Bound, honestly:** the divergence only bites on a multi-segment key. That shape is supported and
tested (`tests/lib/pdf/pdf-path.test.ts:9`, `build-doc-html.ts:88-97` derives a `relDir` from it), but
I **could not find a live producer** — `recoverOrphanedVideos` reads a non-recursive `readdirSync`
(`lib/pipeline.ts:135-138`) so it yields bare filenames. So: the structure is a finding; the liveness
is a **LEAD**.

### The minimal structural change

One module owns `base`: `baseOf(key)` plus the constructors that already exist (`MODEL_KEY`,
`digBlobKey`) plus the two that do not (`pdfKey`, `htmlKey`). Then delete the 16 inline derivations
and the 9 inline constructions. This is not a new layer — two of the four constructors are already
there and are simply not the only way. When they are, `remap()`'s enumeration can be derived from the
constructor set rather than maintained by hand, and a *ninth derived-address site* becomes impossible
in the way the brief hoped a ninth comparison site would.

**Structural.**

---

## 3. The eight comparison sites are not the architectural defect — and a shared helper would be a regression

The brief asks whether eight byte-exact *"are these the same key?"* sites with no shared helper is the
real defect, and what makes a ninth impossible. **Answer: no, and nothing needs to.**

Under v5 there is **no key equivalence relation at all**. Byte-exactness is therefore *correct* at
every site, not merely tolerated — spec §3.4: *"Every existing byte-exact comparison stays correct,
because two different byte strings genuinely are two different keys."* I re-derived the site list to
check the premise, and there are more than eight (`blob-store.ts:134`; `reconcile-serial.ts:117`,
`:118`, `:120`, `:133`, `:155`, `:196`, `:316`, `:351`, `:359`; `sync-run.ts:206`, `:300`) — which
strengthens rather than weakens the conclusion, because all of them are correct.

A `sameKey(a, b)` helper would introduce the single place where an equivalence relation *can* be
reintroduced by whoever next decides two keys "obviously" name the same file. Rounds 1–3 are three
proofs that this is a live temptation. **Prefer the deletion:** the property that makes site N+1 safe
is *"this system has no key equality other than bytes"*, and the way to make that durable is to write
it down (finding 5) and delete the one equivalence still standing (finding 4) — not to give it a
home.

*No change recommended.*

---

## 4. `normalizeLogicalKey` — a key-equivalence relation still standing, with zero external callers

### The evidence

- Defined at `lib/storage/blob-store.ts:96-98`.
- Used at `lib/storage/blob-store.ts:134` — `copyBlob`'s same-key short-circuit.
- **That is the only reference anywhere.** `grep -rn "normalizeLogicalKey" lib app worker tests`
  returns nothing outside `blob-store.ts`.
- `.copy(` has exactly **one** non-test caller: `lib/cloud-sync/reconcile-serial.ts:282`.
- Round 4 measured the short-circuit returning `{ok:true, already:true}` for two keys that are one
  inode on APFS (`r4-claude.md:372-395`). Spec §3.6 records this and clears it **because it is
  unreachable.**

### Why it costs you

"Unreachable" is precisely the property that decays, and this subsystem has already been bitten by an
argument of that shape (finding 8). The repo's own standard is ADR-0007's: *"an unreachable permission
in the one trigger that makes history immutable is a fail-open branch waiting for someone to
reintroduce the state. Delete both branches."*

### The change — delete, do not document

Remove the short-circuit at `:134` and `normalizeLogicalKey` with it. `copyBlob` without it reads
source and destination through `tryGet`, finds identical bytes, and returns `{ok:true, already:true}`
anyway — the same answer for one extra round-trip. The one behavioural difference is when `from ===
to` and the object is **absent**: today `{ok:true, already:true}`, after `source-absent`. That case is
unreachable from the one caller (`remap` only produces `to === from` when `oldBase === newBase`, which
`describeDivergence` at `:155` has already excluded), and `source-absent` is the more honest answer
anyway. The related byte-exact guard at `reconcile-serial.ts:359` (`if (to === from) continue;`) can go
with it.

**Structural, and cheap.**

---

## 5. The vocabulary the whole slice turns on is not in `CONTEXT.md`

`lib/storage/blob-store.ts:74-79` uses **"logical key"** and **"logical prefix"** as defined terms.
`CONTEXT.md`'s *Addressing* section defines **Base**, **Serial number**, **Slug**, **Conditional
write**, **Generation**, **Card**, **Slot**, **Artifact manifest**, **Authoritative**, **Membership**,
**Lease fencing** — and has **no entry for Key**. The word appears once, inside Base's definition, by
contrast: *"Distinct from a key, which is one concrete blob's full path."* There is no **logical
key** / **physical key** entry at all, and after this slice those are two different strings with a
mapping between them.

**On the brief's item 4 — the four named candidates are already durable, and I checked each:** the
per-segment 255 limit is in v5 §2.2 and exported as `LIMIT` in §3.2; the APFS aliasing property is in
§2.5; the `\p{M}` sweep result is in §3.5 and §8; *"Supabase's 400 was incidentally enforcing
servability"* is in §3.5.2. None of them is stranded in a review file. The concern was right in kind
and wrong in target.

**What genuinely has no durable home is the rule, not the measurements:**

> **NFC and NFD are different keys naming different objects. This system has no key equality other
> than bytes.**

That is a domain decision binding every module that touches a key, and it currently lives in a slice
spec that will be superseded. Task **#91** (*write ADR-0009: logical keys are Unicode, physical keys
are ASCII, the seam owns the mapping*) is filed and pending — good. `CONTEXT.md` is not, and it is the
file every future agent reads first. The ADR carries the decision; the glossary carries the words.

**Structural.**

---

## 6. A guard whose correctness argument is a claim about another module, with nothing linking them

`lib/html-doc/assert-cloud-summary-md-key.ts:2-6` justifies its allowlist by asserting a property of a
different file: *"`slugify` (lib/slugify.ts) emits ONLY unicode letters/numbers and `-` — it replaces
every other character … with `-`."*

That is true today (`lib/slugify.ts:3-4`). Three things follow, and all three are measured:

1. **Nothing links them.** `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts` never imports
   `slugify`; it hardcodes shapes, and `:10-11` even *restates* the producer's 60-character cap in a
   comment rather than deriving it.
2. **The numbers already disagree.** The regex admits 128 characters (`{0,127}`); the producer's
   worst case is `padSerial` + `_` + `slugify`'s 60-char cap ≈ 65. Two bounds, no relationship.
3. **The premise stopped holding when sync shipped, and nothing noticed.** `sync-run.ts:263` writes
   the *sender's* key, which reached the local index as raw `readdirSync` bytes
   (`lib/pipeline.ts:105`, `:135-138`) — not from `slugify`. *"Every key comes from slugify"* became
   false at that commit, and the guard's stated justification went with it.

This is the direct generalisation of what four rounds kept re-finding, and it matches the repo's own
recorded lesson (memory `hardcode-only-what-fails-loudly`): a check configured from a **derived** fact
must derive it, because a vocabulary that silently stops matching is worse than no check.

**Change:** a property test feeding `slugify` output into `assertCloudSummaryMdKey`, so the coupling
fails loudly when either side moves — and finding 1's write-time enforcement, which makes the premise
irrelevant rather than merely tested.

**Structural.**

---

## 7. Parking ADR-0006/0007 still matches the evidence. Its stated reason does not.

*Assessing the parking decision, not the ADRs.*

`docs/roadmap-to-launch.md:678-680` gives the reason: *"everything it currently fixes is a defect **in
itself**, not in the running product, and the roadmap's stated goal is M3 acceptance."*

**Backlog #36 falsifies that sentence.** ADR-0006's address is
`<workspace>/videos/<videoId>/<generationId>/…` — derived from immutable identity, containing no
title. Under it this bug cannot exist. And it is emphatically a defect *in the running product*:
`docs/backlog.md` row 36 records it destroying a paid summary against **prod release v6**, repeatably,
ledger 450¢ → 606¢, with 2 of 4 videos in the test playlist Korean-titled.

**The decision still holds, and this slice is evidence for it.** v5 §7.4 declines the ADR-0006-shaped
fix ("opaque keys addressed by `videoId`") on its merits: it re-addresses every object and needs a
full prod migration over live paid artifacts, and the roadmap's own unpark trigger requires backlog
#26 (the per-kind attempt ceiling ADR-0007 deleted) closed *first*. Four spec rounds cost days; that
migration has no rollback. Parking was right, and a targeted fix was reachable without it — which is
what "parked, not blocked" is supposed to mean.

**The change is one sentence**, not a decision: amend the reason to say *"…not in the running product
— except backlog #36, which ADR-0006 would have prevented and which is being fixed independently."*
By this repo's own standard (ADR-0007: *"a reason that has stopped being true is worse than no reason,
because it reads as settled"*), leaving it invites the next reader to believe a claim the evidence has
already refuted.

**Structural** (documentation, one sentence, load-bearing).

---

## 8. The composition defect: five live safety arguments of the form "safe because nothing does X yet"

This is what per-task review is structurally blind to, and it is the answer to the brief's question 5.

Apply one lens — *a constraint enforced by an accident of another layer, which a locally correct change
removes* — and the subsystem returns five instances. Every one is correct. Every one is documented.
**Nobody counts them.**

| # | The argument | Where it is written | What retires it |
|---|---|---|---|
| a | Supabase's `400 InvalidKey` made a non-ASCII cloud summary key impossible, so every downstream consumer could be narrow | nowhere until round 4 named it (`r4-claude.md:52-58`); now spec §3.5 | **this slice** — and it cost four rounds |
| b | The `unsupported-artifacts` refusal is unreachable because *"`writeArtifact` … has zero production callers"* | `reconcile-serial.ts:207-209` | anyone giving `writeArtifact` a caller |
| c | `copyBlob`'s short-circuit is wrong on an aliasing backend but *"`.copy(` has exactly one non-test caller"* | spec §3.6; measured `r4-claude.md:372-395` | a second `.copy(` caller — see finding 4 |
| d | `assertCloudSummaryMdKey`'s allowlist is sufficient because *"`slugify` emits ONLY unicode letters/numbers"* | `assert-cloud-summary-md-key.ts:2-6` | sync, which already retired it — see finding 6 |
| e | `video_artifacts_inflight_uq` is *"the only thing stopping two paid model producers today"*; deleting it without the `doc_key` re-key is a money regression | ADR-0007, *"The coupling that makes the deletion safe"*; task **#45** | the ADR-0007 implementation slice |

Two of these have already fired: **(a)** produced backlog #36 and four non-converging rounds; **(d)**
was retired silently by a feature (sync) that had no reason to know it existed. **(e)** is tracked and
armed. **(b)** and **(c)** are live and unguarded.

**Why no instrument sees this.** This repo has ratchets for guards
(`scripts/check-guard-coverage.py`), sentinel meanings (`check-sentinel-meanings.py`), duplicate
coordination vocabulary (`check-vocabulary-collisions.py`), docs (`check-docs.py`) and architecture
findings (`check-arch-findings.py`). Each inspects a *declared inventory*. A safety argument of this
shape declares nothing — it is a sentence in a comment asserting a fact about the rest of the
repository. It is the shape the repo's own memory already named: *"Every instrument here is opt-in, so
they share ONE blind spot."*

### The change — apply a move this repo has already made, four more times

**Do not build a new mechanism.** ADR-0007's T4 already solved exactly this for one case: it could not
express the invariant as a constraint, so *"the structural fact is the guard, so the structural fact is
what is tested — an assertion now fails if a second inserter ever appears."*

Give **(b)** and **(c)** the same treatment: a test asserting the caller count that the safety argument
rests on, failing loudly when it changes. `(c)` is better served by deleting the short-circuit outright
(finding 4) — a deleted branch needs no assertion. `(d)` gets the property test in finding 6. `(a)` is
what finding 1 closes.

The general rule this subsystem has now paid for twice, stated so it can be applied without me:

> **When a safety argument is *"X is unreachable"* or *"nothing produces that shape"*, the argument
> names a fact about code that will change. Either delete the thing being protected, or assert the
> fact — but never let the sentence be the only guard, because a sentence cannot go red.**

**Structural — and it is the highest-value item in this review.**

---

## LEADs — not findings

- **`Principal.indexKey` is a tenant path segment and is validated by neither adapter.**
  `SupabaseBlobStore.objectKey` (`lib/storage/supabase/supabase-blob-store.ts:15-18`) calls
  `assertLogicalKey(key)` and interpolates `p.id` and `p.indexKey` unchecked;
  `LocalFsBlobStore.abs` (`lib/storage/local/local-blob-store.ts:12`) does the same. Spec §3.6 relies
  on that asymmetry deliberately (it is why ADR-0008 survives), so the gap is now load-bearing in the
  other direction. Every caller I traced passes a `playlist_key` read back from an owned DB row
  (`app/api/playlists/[id]/route.ts:60`, `app/api/videos/route.ts:167`,
  `lib/storage/resolve.ts:83`), so it is a stored value, not raw request input — **but I did not trace
  the insert path that puts it there.** Worth ten minutes before the PR.
- **Multi-segment `summaryMd` keys (`raw/275_x.md`) have no producer I could find** — see finding 2's
  bound. If one exists, finding 2 is live rather than latent.
- **`provesAbsence` (`blob-store.ts:57-67`) is an optional backend-capability boolean whose absence
  means `false`.** One flag is not a pattern; this slice nearly added a second
  (`aliasesUnicodeNormalization`, `r4-claude.md:403-425`) and v5 correctly dropped it. **Trigger:** the
  day a second flag is genuinely needed, the answer is one capability record with no defaults, not a
  second optional boolean — otherwise the seam is re-implementing *"which backend am I?"* one property
  at a time.

---

## What this review does **not** say

- It does not argue for unparking ADR-0006/0007, or against any content of either ADR.
- It does not argue the slice is mis-scoped. Round 4 recorded *"a bounded gap, not a mis-scope"*
  (`r4-claude.md:502-510`) and I verified the premise it rests on rather than accepting it.
- It does not propose a `DocKey` value object or branded key types. The repo's branding precedent
  (`lib/serve-budget.ts:81-83`, `Budget<Site>`) exists to make *arithmetic between two bounded
  resources* fail to compile — a genuinely unrepresentable-state problem. Keys have the opposite
  shape: the six roles the brief names (vault filename, DB column, blob address, sync payload field,
  serve-path token, derived-address root) hold **the same string** deliberately, and the slice's whole
  correctness argument depends on that. Branding them would force casts at every seam and buy nothing,
  because the confusion that actually cost four rounds was never *which role* — it was **which
  predicate** (finding 1) and **which derivation** (finding 2). Fix those; leave the type alone.
