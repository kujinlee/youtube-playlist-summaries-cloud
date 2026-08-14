# Round 9 — Claude adversarial review, cloud blob key encoding (backlog #36)

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` **in the working
tree (v9)**, branch `fix/cloud-blob-key-encoding`, at `fe6ab50`. Not a pinned commit.

**Verdict: NOT CONVERGED** — 0 Blocking, 3 High, 5 Medium, 7 Low.

**Read the two summary lines first, because they point in opposite directions.**

1. **§3.4 is done.** Round-8 B1 is genuinely fixed, and I could not break the replacement. A sweep of
   all 1 114 112 codepoints in **both** directions found **zero** false admissions and **zero** false
   rejections except a single length discrepancy (H3). The premise collapse survived a second
   independent attack. §3.1/§3.2/§3.3 round-trip against live Storage, including the `=h…`
   **directory** case that no previous round measured.
2. **§3.6 is not.** All three Highs are in it, and all three were introduced by the round-8 fixes to
   it. §3.6 has now produced a finding in rounds 6, 7, 8 and 9, each caused by the last round's
   repair. `docs/review-method.md:45-49` says two consecutive such rounds escalates from FIX to
   REDESIGN; that threshold was crossed at round 8 and no rule acted on it (M5).

| # | Severity | One line |
|---|---|---|
| H1 | High | §3.6 states the deciding question and names two primitives — **measured, neither can answer it** |
| H2 | High | §3.6 prescribes a `put`-shaped `wx` for a writer whose durable write is `promote()`; taken literally it deletes the stage→verify→promote protocol |
| H3 | High | The guard's length bound silently narrows 131 → 128, and §4's gate has no length term, so the one pre-deploy check cannot see it |
| M1 | Medium | §3.5's "there is no unservable class left" is falsified by a key shape the repo asserts is supported |
| M2 | Medium | The `utf16le` mutation row is vacuous as specified — round-8 M2, unfixed |
| M3 | Medium | Round-8 M5 unfixed: §3.4 and §7 still credit a containment check that is not on the widened path |
| M4 | Medium | Behavior 18c's atomicity claim cannot hold for `transferClassA`, which is required to overwrite |
| M5 | Medium | Recurrence: §3.6 is on its fourth consecutive fix-induced round; the stop condition already fired |
| L1–L7 | Low | P3's provenance, the share-path bypass, `⁄`/`∕`, behavior-17 coverage, behavior 9's reachability, the injectivity wording, `copy()` |

---

## What I verified, and could not break

Recorded first so the Highs are not mistaken for doubt about the design's core.

### `isServableSummaryKey` — total sweep, both directions

Probe: `/tmp/r9probe/t1.mjs`, `t2.mjs`, `t3.mjs`, run under Node 22 with the predicate transcribed
verbatim from spec §3.4 lines 133–143.

| Attack | Result |
|---|---|
| Every enumerated behavior (16 and 17, plus the two the ⚠ box names) | **13/13 correct.** `001_intro.md`, `275_google-okf.md`, `0007_한국어.md`, `0007_café.md` (NFD), emoji, space all pass; `nested/foo.md`, `%2f`, `／`, control char, 200-char base, `℀.md`, `001_a．．b.md` all rejected |
| **All 1 114 112 codepoints**: is any *admitted* codepoint's NFC/NFD/**NFKD**/NFKC form containing `/`, `\` or `..`? | **NONE.** The NFKC pass closes the class completely — including the forms it does *not* itself check |
| Raw ASCII separators admitted | **0** |
| **The other direction** — any single-codepoint base accepted by the *current* shipped guard and rejected by v9? | **NONE** (charset). The only discrepancy in the entire codepoint space is length — H3 |
| Lone surrogate in a key (`.normalize()` throw / DoS) | Safe: `normalize` does not throw; key admitted |
| `..md`, `...md`, `‥.md` (U+2025), `a․․b.md` (U+2024) | all rejected; `.hidden.md`, `.md.md` admitted (correct — no separator) |

Round-8 L1 (the hand-typed homoglyph list missing 6 of 7) is not merely fixed for those seven — it is
closed for the whole codepoint space. This is the strongest result in the review.

### The premise collapse survives a second, different attack

Round 8 traced the consumers. I attacked the *seam* instead, against live local Storage
(`/tmp/r9probe/storage.mjs` — asserts the host is `127.0.0.1` before connecting, exits 2 otherwise;
removed all 5 objects it created and verified the root lists 0 entries afterwards).

```
logical  : 0007_한국어-제목입니다.md          raw upload    -> 400 Invalid key      (P1 reproduced)
physical : 0007_=hi4JIePovJCqD2On6xzXU5H.md   encoded upload -> ok
§3.3 dig DIRECTORY named `0007_=hxSknNtD17Tx8FTVSOQy69z`   -> upload ok
       list(that dir)    -> ["sec-1.r3.md"]
       list(parent)      -> ["0007_=hxSknNtD17Tx8FTVSOQy69z"]
a segment with NO safe head -> physical name STARTS with `=`:  `=hifWxP3GxQdOB0wRCwDkfms`
       as a leaf -> ok    as a DIRECTORY -> ok    list(it) -> ["child.md"]
worst case encoded length -> 65 chars exactly (spec claims <= 65) -> upload ok
```

The `=h…` **directory** case is new: §3.3's whole re-attachment mechanism runs through it and no
previous round measured it. It works.

Consumers I re-derived by reading rather than trusting round 8:

- `copyBlob` (`blob-store.ts:126-173`) reads **only** through `store.tryGet` / `store.put` — both at
  the encoding seam — so §3.7's "`copy()` needs no change" is correct *provided* the encoder lives in
  `objectKey` (see L7). Its short-circuit note is also right: `reconcile-serial.ts:282` is the one
  non-test caller.
- `pdfCacheKey` (`pdf-render-version.ts:18`) rejects `/ \ \0 ..` and is otherwise charset-agnostic.
- `pdfRelPath` (`pdf-path.ts:16-28`) is `path.basename` + `.replace(/\.md$/,'')` — charset-agnostic.
- `Principal.indexKey` is the **YouTube list-id** in the cloud (`principal.ts` header comment), so
  §3.7's decision not to encode the owner/index segments does not leave a second non-ASCII hole.
- P4 holds: exactly 3 `list()` callers (`reconcile-serial.ts:102`, `dig-state/route.ts:47`,
  `load-dig-for-serve.ts:32-34`), all passing `dig/${base}/` and consuming a leaf under it.
- P5 holds: exactly 2 callers of the guard (`serve-summary-core.ts:61`, `resolve-summary-key.ts:16`).

### APFS, measured (`/tmp/r9probe/apfs.mjs`)

| Primitive, against a file created under its **NFC** name, attacked via the **NFD** path | Result |
|---|---|
| `writeFileSync(NFD, {flag:'wx'})` / `openSync(NFD,'wx')` / `openSync(NFD,'wx+')` | **EEXIST** — §3.6's claim confirmed |
| **`linkSync(tmp, NFD)`** | **EEXIST** — a no-clobber *rename-shaped* primitive exists (H2) |
| `renameSync(tmp, NFD)` — what `promote()` does today | **OK.** Directory keeps the **NFC** entry; reading via the NFC path returns the intruder's bytes |
| Case-only alias (`Case.md` vs `case.md`) under `wx` | EEXIST |
| Normalization preservation | APFS is normalization-**preserving**: created NFD → `readdir` returns NFD |

> **Methodology note, and it is the spec's own lesson.** My first occupancy probe produced garbage
> because the editor stored both the "NFC" and the "NFD" source literals as **NFC** — hex-identical.
> That is the third instance this round of *"the source does not show what it means"*, the class §3.4's
> ⚠ box was written about. Every probe below builds its forms with `.normalize()`, never from a
> literal. **The spec's own code blocks and any test fixtures should do the same** — an NFC/NFD test
> pair written as two literals in a `.ts` file can silently become one string.

---

## H1 — High: §3.6 poses the deciding question and hands the caller no primitive that can answer it

**Spec §3.6, lines 209–222.** The section says the guard

> "must read `tryGet`, treating `unreadable` as **occupied**"

then gives the two-writer table, then states:

> "The distinguishing question is not 'is it occupied?' but **'is the occupant this same logical
> key?'**"

then the ⚠ resolves ordering with `wx` and concludes:

> "`LocalFsBlobStore` gains a no-clobber write; both vault writers use it; **the caller decides on
> `EEXIST` per the table above**."

**Measured** (`/tmp/r9probe/occ3.mjs`, forms built with `.normalize()`, write target = logical key
NFD):

```
CASE 1 — occupant IS the same logical key (NFD).   §3.6: transferClassA must WRITE
   tryGet(NFD).ok = true    readdir = [ 'NFD' ]    wx = EEXIST
CASE 2 — occupant is a DIFFERENT logical key (NFC) that merely aliases.  §3.6: REFUSE
   tryGet(NFD).ok = true    readdir = [ 'NFC' ]    wx = EEXIST
```

`tryGet` returns `{ok:true}` in both. `wx` returns `EEXIST` in both. **The two primitives §3.6 names
are byte-identical across the branch the table says decides the outcome.** Only `readdir` — which
`LocalFsBlobStore.list` uses (`local-blob-store.ts:76`) — distinguishes them, because APFS stores the
created byte sequence verbatim.

**Failure scenario.** An implementer follows §3.6, gets `EEXIST`, and must pick one branch with no
information:

- **refuse** → every cloud→local Class-A transfer throws, because on the two-sided path the
  destination is occupied by definition (`sync-run.ts:386-394`: *"A two-sided Class-A transfer must
  OVERWRITE the loser's existing (divergent) blob at `key`"*). That is round-8 H1, restored verbatim.
- **write** → the aliasing vault file of a *different* video is clobbered, which is the entire reason
  §3.6 exists. Measured above: `renameSync`/`put` through the alias leaves the victim's directory
  entry and the intruder's bytes.

So behavior 18b — *"refuses only a different key that merely aliases"* — is **not implementable from
the spec as written**. This is the same shape as round-8 H1 (a rule the code cannot satisfy), one
level down: the rule is now correct, and the mechanism named to evaluate it is not.

**Fix.** Name the identity test explicitly, because it is neither of the two the section names:

> On `EEXIST`, read the receiver directory (`fs.readdirSync(dirname)`) and compare each entry
> **byte-for-byte** against the logical key. An exact match ⇒ same logical key. No exact match, but
> the path resolves ⇒ a *different* key aliasing this one. Then apply the table.

State that `tryGet` and `exists` cannot make this distinction on an aliasing filesystem, since both
resolve through the alias. Keep `tryGet`'s `unreadable ⇒ occupied` rule — it is right, and it answers
a different question (*"can I prove absence?"*, which the Supabase receiver cannot). And write
behavior 18b's fixture with `.normalize('NFC')` / `.normalize('NFD')`, never as two source literals.

---

## H2 — High: `wx` is a `put`-shaped primitive prescribed for a writer whose durable write is `promote()`

**Spec §3.6:227-229:** *"`fs.writeFileSync(dest, bytes, { flag: 'wx' })` … `LocalFsBlobStore` gains a
no-clobber write; **both vault writers use it**."*

The additive writer's durable write is not a `put`. It is a three-step protocol
(`sync-run.ts:261-270`):

```ts
// stage → verify (readable + hashes) → promote — never advertise promoted before durable.
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
const staged = await toBlob.get(toP, ref.tempKey);
if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
  throw new Error(`additive staged MD verify failed for ${video.id}`);
}
await toBlob.promote(ref);
```

and `promote` on local is `fs.renameSync(from, to)` (`local-blob-store.ts:58-62`). A direct
`writeFileSync(dest, bytes, {flag:'wx'})` replaces all four lines with one, so the **read-back hash
verification disappears** — on the vault write path, for a paid artifact, with the receiver row then
advertising `status:'promoted'` (`sync-run.ts:279`). The spec does not mention the protocol, so
nothing tells the implementer to preserve it.

**The spec did not have to choose between them, and I measured the alternative:**

```
linkSync(tmp, NFD)  against a file created as NFC   ->  EEXIST
```

`fs.linkSync` is atomic, fails `EEXIST`, and **sees through the NFC/NFD alias** exactly as `wx` does.
So `promote` can become no-clobber as `link(from, to)` + `unlink(from)` with `putStaged` → verify →
`promote` completely intact. `renameSync` is the only one of the three that silently overwrites.

**Fix.** Say *which operation* becomes no-clobber, per writer:

| Writer | Durable write today | No-clobber form |
|---|---|---|
| `copyAdditiveVideo` (`sync-run.ts:263-268`) | `putStaged` → verify → `promote` (rename) | `promote` → `link` + `unlink`. Staging and the hash verify survive unchanged |
| `transferClassA` (`sync-run.ts:381-394`) | `putStaged` → verify → `put` (deliberate overwrite) | keep `put`; see M4 |

And record the measurement, because "`wx` → `EEXIST`" in §2.4 is now doing work it was never
measured for: it was measured as a *fact about aliasing*, and §3.6 promoted it to *the chosen write
primitive* without asking whether the writers' shape admits it.

---

## H3 — High: the length bound narrows 131 → 128, and the §4 gate has no length term

| | Bound | Total key length |
|---|---|---|
| Current guard, `assert-cloud-summary-md-key.ts:14` | `[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md` → base 1–128 | **4–131** |
| v9 predicate, §3.4:134 | `key.length <= 3 \|\| key.length > 128` | **4–128** (base 1–125) |

**Measured** (`/tmp/r9probe/t3.mjs`) — this is the *only* discrepancy between the two in the entire
codepoint space:

```
total key lengths accepted today, rejected by v9: 129, 130, 131   (bases of 126, 127, 128 chars)
charset codepoints accepted today, rejected by v9: NONE
```

The spec never mentions the change; §3.4's prose is entirely about *widening*.

**And the pre-deploy gate cannot see it.** §4's gate predicate is `^[A-Za-z0-9._-]+$` per segment —
character class only, no length term:

```
total=131   §4 gate flags it? false    CURRENT serves it? true    v9 serves it? false
```

§7's risk row is charset-only too (*"An existing prod key uses ` `, `(`, `)`, `+` or `=`"*). So the
one mechanism whose entire job is *"no existing key breaks"* is silent on the one way this change can
break one.

**Failure scenario.** An existing summary at a 126–128-char base returns `409 corrupt summary key`
from `serve-summary-core.ts:61-64` — before the blob read, so no repair path — and
`resolve-summary-key.ts:16` returns `null`, so dig resolution fails too. The §4 gate passes green.

**Why High and not Blocking.** I could not construct a producer. The mint path yields
`padSerial(n) + '_' + slugify(title)[:60] + '.md'` ≈ 68 chars (`serial-filename.ts:6`,
`slugify.ts:6`). The only entrance that takes an arbitrary name is `recoverOrphanedVideos`, which
adopts **any** `*.md` in the output folder carrying a `video_id` frontmatter field and sets
`summaryMd = file` verbatim (`pipeline.ts:137`, `:104`, `:151`); sync then copies that verbatim to the
cloud (`sync-run.ts:263`, `:279`). That requires a hand-placed or externally-renamed vault file.
Per `docs/review-method.md:29-33` ("what caller reaches this state?") that is not Blocking — but the
gate is exactly the instrument that would settle it, and it does not ask.

**Fix.** One of:
- keep the bound (`key.length > 131`) and say so — the simplest, and it makes the guard a strict
  widening in every dimension; **or**
- add a length term to the §4 gate SQL (`length(segment) > 128`) and add the risk row.

Either way, state in §3.4 that the bound moved and in which direction.

---

## M1 — Medium: "there is no unservable class left" is falsified by a shape the repo calls supported

§3.5 deletes five mechanisms, and the first row's justification is:

> | The servability **refusal** (v5) | unservable keys had to be stopped | **there is no unservable class left** |

`reconcile-serial.ts:127-131`:

```
//  - But not on the whole key either: `dig-section.ts:83` builds the name from
//    `path.basename(summaryMdName)`, so a video whose `summaryMd` is `raw/275_x.md` gets a BARE
//    `275_x-dig-deeper.md`. … The `raw/` layout is real and supported (tests/lib/pdf/pdf-path.test.ts,
//    and buildDocHtml derives `relDir` from exactly these fields).
```

exercised at `tests/lib/pdf/pdf-path.test.ts:9,17,27` and
`tests/lib/cloud-sync/reconcile-serial.test.ts:409-416` (`summaryMd: 'raw/007_alpha.md'`,
`artifacts.summaryMd.key: 'raw/007_alpha.md'`, `status: 'promoted'`).

`assertLogicalKey` admits `raw/275_x.md` (`blob-store.ts:88` rejects only a leading `/`, a `..`
segment, and `\0`), so `copyAdditiveVideo` writes it and advertises it promoted — and
`isServableSummaryKey('raw/275_x.md')` is **false**, so cloud serve 409s. That is an unservable class,
still there.

**Medium, not High: I found no producer.** Outside tests, nothing writes a `raw/`-prefixed
`summaryMd`; the claim that the layout is "real and supported" is a code comment, not a call site.
So the right conclusion is probably still *delete the refusal* — but the sentence justifying five
deletions should not be a false universal.

**Fix.** Narrow it: *"no unservable class the mint path can produce"*, and add one row recording the
nested-`summaryMd` case as a pre-existing gap that this design neither creates nor closes.

## M2 — Medium: the `utf16le` mutation row is vacuous as specified (round-8 M2, unfixed)

§5's restored table: *"Drop `utf16le` back to `utf8` → must turn red on **4** (lone-surrogate
collision)."* The mechanism is real — measured (`/tmp/r9probe/t4.mjs`):

```
utf16le: 003_x=hhF5ygckhL1ktSLYpRKkxxd.md / 003_x=hf4zxMMMuIfiimSGsqNRKFB.md   distinct? true
utf8   : 003_x=hlaPXAty8NJEj4FE00WS_y9.md / 003_x=hlaPXAty8NJEj4FE00WS_y9.md   distinct? FALSE
```

But behavior 4 is *"`encodeSegment` is injective over arbitrary segments | property + crafted
preimage"*, and both inputs are **ill-formed UTF-16**. Property generators emit well-formed strings;
the only crafted preimage §5 names is the `=`-marker one (which I confirmed **is** constructible and
deterministic — same probe). Nothing in §5 names a lone-surrogate input, so the mutation has no
observable that can go red.

Round-8 M2 asked for v7's behavior 22 back. v9 restored the *table* (H2) and not the behavior the
table points at — a fix that moved the gap rather than closing it.

**Fix.** Restore behavior 22: `encodeSegment('003_x\uD840.md') !== encodeSegment('003_x\uD850.md')`,
and point the mutation row at 22 instead of 4.

## M3 — Medium: round-8 M5 unfixed — the credited backstop is not on the widened path

§3.4:182 — *"What protects both sides is `assertLogicalKey` plus the resolved-path containment
check."* §7:330 — *"The resolved-path containment check remains the real backstop."*

`assertIndexRelPathWithin` runs at `build-doc-html.ts:77`, `:104`, `:105`; `rerender.ts:50`;
`app/api/videos/[id]/pdf/route.ts:85` — all local-filesystem paths. On the cloud serve path the only
post-guard check is `assertLogicalKey` (`blob-store.ts:87-91`). That is *sufficient*, but §7 also says
the widening *"needs a security reviewer at the PR"*, and that reviewer will go looking for a backstop
that is not there.

**Fix.** `assertLogicalKey` on the cloud path; `assertIndexRelPathWithin` on the local pipeline. Two
words.

## M4 — Medium: behavior 18c cannot hold for `transferClassA`

Behavior 18c: *"The occupancy test and the write are **one operation** (`wx`) — an alias appearing
between them cannot be clobbered."* §3.6 asserts it for "both vault writers".

On the Class-A path the destination is occupied **by definition** (`sync-run.ts:386-394`), so `wx`
returns `EEXIST` every time and the actual write is a separate, clobbering
`loser.blob.put(loser.p, key, staged, ...)` at `:394`. The sequence is `wx` → EEXIST → identity check
(H1) → overwrite: three operations, not one. Behavior 18c is achievable only for
`copyAdditiveVideo`, and the mutation row *"Replace the `wx` write with check-then-write → 18c"* is
likewise satisfiable only for the additive half.

**Fix.** Scope 18c to `copyAdditiveVideo`. For `transferClassA`, state the residual window
explicitly and why it is accepted — do not leave a claim of atomicity the code cannot make.

## M5 — Medium: §3.6 is on its fourth consecutive fix-induced round; the stop condition already fired

| Round | Finding in §3.6 | Caused by |
|---|---|---|
| 6 | M1 — the guard must pin ordering | the original check-then-write |
| 7 | Blocking 1 — a **second** vault writer the guard must cover | round-6's guard |
| 8 | H1 — the rule contradicts the code it governs; M4 — ordering unresolvable as specified | round-7's two-writer note |
| **9** | **H1** (no primitive answers the question), **H2** (`wx` vs `promote`), **M4** (18c's scope) | **round-8's two-writer table and its `wx` choice** |

`docs/review-method.md:45-49`:

> **If a component produces findings caused by the PREVIOUS round's fixes in two consecutive rounds,
> it escalates from FIX to REDESIGN, and the next round is a design review — not another defect hunt.**

That fired at round 8. Meanwhile §3.1–§3.5 have converged and stayed converged, and the retrospective
this rule came from (`docs/reviews/blob-addressing-retrospective-2026-08-09.md`) describes exactly
this pattern: one component churning while its siblings hold.

**Two things I checked before recommending anything:**

- **§3.6 cannot simply be split out.** It is genuinely coupled to this change: today the cloud cannot
  hold a non-ASCII key (P1), so a cloud→local additive create cannot carry one into the vault and no
  NFC/NFD alias can arise from that path. After the encoder, it can. §3.6 belongs in this spec.
- **The recurring rule is a *choice*, not a constraint** (`review-method.md:145-160`, step 1). The
  choice is *"the receiver's blob store is the collision authority"* (§3.6:209). The `BlobStore`
  interface has no primitive that can answer *"whose key is this file?"* — the interface is addressed
  by logical key and the filesystem is addressed by alias class, and the whole four-round search has
  been for a credential that reconciles them. `readdir` (H1) does, and it reaches *past* the
  `BlobStore` interface into `LocalFsBlobStore`.

**Recommendation.** Fix H1/H2/M4 as stated — they are concrete and the primitives are measured — but
run the next §3.6 pass as a **design review** of the vault write protocol (who the writers are, what
identity each carries, which coordination pattern this is), not another defect hunt. Everything
outside §3.6 is ready.

---

## Lows

**L1 — P3's provenance is falsified as written.** P3 reads *"QUOTED — the only `client.storage.from(`
outside tests is `supabase-blob-store.ts:20`"*, falsified by *"a second call site"*. There is one:
`scratchpad/b3-raw.ts:22` — `user.storage.from(ARTIFACTS_BUCKET).download(k)`. It is gitignored
(`.gitignore:68`) and read-only, so the **premise** ("every *write* reaches Storage through
`SupabaseBlobStore`") holds — but the falsifier as stated is met. Restate the provenance as *"the only
non-test **write** call site"* and note the read-only ops script.

**L2 — the guard is described as a boundary it does not uniformly hold.** The guard's docstring
(`assert-cloud-summary-md-key.ts:6-8`) calls it *"the hard boundary before `models/{base}.json` /
`pdfs/{base}.pdf` keys are built"*. The share path derives exactly that without it:
`lib/share/serve.ts:47` returns `mdKey` unguarded, `app/s/[token]/route.ts:50` reads the blob and
`:78` derives `const base = ctx.mdKey.replace(/\.md$/, '')`. P5's *"exactly 2 callers"* is accurate;
the boundary claim is not. Raised by round-8 Codex as a Medium and not addressed. **Low here because
it is evidence *for* the design's thesis** — the share path has derived model keys from unguarded
`mdKey`s for the app's whole life without incident, which is the same argument §3.4 makes about the
local path. One sentence in §3.4 turns an unaddressed finding into supporting evidence.

**L3 — NFKC does not "close the class" for `⁄` (U+2044) and `∕` (U+2215).** Measured: their NFKC is
themselves, so v9 admits both; v8's intended denylist named both. Correct on the merits — the full
sweep found no normal form of either containing `/` — but the ⚠ box says folding *"closes the class
instead of enumerating it"*, which is true for the folding homoglyphs and is a **narrowing** for these
two. Say so, so the next reader does not read completeness into it.

**L4 — the NFKC mutation row cites evidence that behavior 17 does not contain.** Row: *"Skip the
NFKC-folded pass → **17** (`℀.md`, `001_a．．b.md` admitted)"*. Behavior 17 lists `nested/foo.md`,
`%2f`, `／`, a control char, a 200-char base. Measured: the mutation **does** turn 17 red — but via
`／`, not via either codepoint the row names. Not vacuous; imprecise in a table whose whole purpose is
that its observables are real. Add `℀.md` and `001_a．．b.md` to behavior 17.

**L5 — behavior 9's throw is unreachable from every production caller, and it fires on a paid read
path.** `digSectionKey` (`dig-blob-key.ts:13,22`) builds `dig/${base}/${sectionId}.r${V}.md` with
`sectionId: number`, so every dig leaf matches `\d+\.r\d+\.md` — always `SAFE`, never `=h`-marked. No
production `list()` can meet an un-nameable remainder. Fine as a seam backstop; worth one line saying
so, because an uncaught throw inside `load-dig-for-serve.ts:34` would 500 a paid doc rather than
degrade.

**L6 — §3.2's "injective" is collision-resistance.** The Contract says *"injective over arbitrary
logical segments as raw JS strings"* flat. It is a 22-char base64url truncation of SHA-256 = 132 bits;
the identity and hash branches are provably disjoint (`=` ∉ `SAFE`), but the hash branch is not
injective, it is collision-*resistant*. Task #96 already recorded this as "the injectivity overclaim"
and v9 still states it unqualified. One qualifier.

**L7 — `copy()`'s correctness now depends on where the encoder lives, and only §3.1 implies it.**
§3.7 asserts *"`copy()` needs no change"*. That is true because `copyBlob` (`blob-store.ts:126-173`)
touches Storage only through `store.tryGet` and `store.put`. It stops being true if the encoder is
placed anywhere but inside `objectKey` (`supabase-blob-store.ts:15-18`). §3.7 should say *why* it needs
no change, and round-8 M3's behavior 13 (`copy()` of a Korean-based dig blob end to end) is still
absent — `reconcile-serial.ts:282` encodes both sides of the same call on a paid-artifact relocation.

**Also still open from round 8, unaddressed in v9 and not re-graded here:** L4 (the two dead-lettered
prod videos lost their disposition when the `videoId` repair was deleted) and L5 (integration fixtures
at `tests/integration/helpers/seed.ts:62` and
`tests/integration/serve-md-unreadable-no-charge.test.ts:82` write **physical** keys directly, so the
non-ASCII fixtures for behaviors 6/7/8/14/15/16 would seed an address the app never reads).

---

## Convergence

**NOT CONVERGED.** Three Highs, all in §3.6, all introduced by round 8's fixes to §3.6.

I want to be explicit about the calibration, because the brief asks for it. **If §3.6 did not exist I
would say CONVERGED.** §3.4 withstood a total sweep in both directions; §3.1–§3.3 round-trip against
live Storage including a case no round had measured; the premise collapse survived a second,
differently-aimed attack; §1.1's premises are honest and P3–P5 re-verified this round. What is left
outside §3.6 is five Mediums that are sentence repairs and one missing behavior.

I am not withholding convergence for polish. H1 is a rule with no evaluable mechanism, and both
default readings of it are defects this review trail has already paid for. H2 silently deletes a
verification step on a vault write path. H3 is a one-character bound change that the pre-deploy gate
is structurally unable to catch. None is expensive to fix — H1 and H2 both have a measured primitive
waiting (`readdir`, `linkSync`).

The one thing I would not do is fix them and dispatch round 10 as another defect hunt. The stop
condition in `review-method.md` fired at round 8 on this exact component, and the reason it went
unnoticed is the reason it was written down: *"the evidence was already being collected and no rule
acted on it."*

*Probe scripts: `/tmp/r9probe/{pred,t1,t2,t3,t4,apfs,occ3,storage}.mjs`. The Storage probe asserted
`127.0.0.1` before connecting and verified its root listed 0 entries after cleanup. No tracked file in
the repo was modified by this review other than this document.*

*Codex gap: none — this is the Claude half of a dual round.*
