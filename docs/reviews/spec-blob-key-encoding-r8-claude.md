# Round 8 — Claude adversarial review, cloud blob key encoding (backlog #36)

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` **in the working
tree (v8)**, branch `fix/cloud-blob-key-encoding`. Not a pinned commit.

**Verdict: NOT CONVERGED** — 1 Blocking, 2 High, 5 Medium, 5 Low.

**Read this first, because the headline is not the Blocking.** The round was called to attack the
premise collapse, and *the premise collapse survives*. I went looking for the consumer that breaks on
a non-ASCII but separator-free key — the one that would justify the allowlist after all — across
every path the brief named and several it did not. **There is none, and I traced each one.** The
Blocking below is a one-character typo in the replacement regex, mechanical to fix. Removing it
leaves a design whose central claim I could not break.

Counts by severity, most severe first.

| # | Severity | One line |
|---|---|---|
| B1 | Blocking | The §3.4 regex, as written, rejects **every existing key** and admits **only control characters** |
| H1 | High | Behavior 18 requires `copyToLocal` to refuse a write that `sync-run.ts:386-394` requires it to perform |
| H2 | High | The mutation table was deleted with the machinery, but 6 of its 10 entries target mechanisms v8 **keeps** |
| M1 | Medium | "That is the whole fix" is false for the headline case — Korean already passes the current guard |
| M2 | Medium | The `utf16le` mechanism survives; the only behavior that could falsify it was dropped |
| M3 | Medium | `copy()` is asserted unchanged with no behavior exercising it across the new seam |
| M4 | Medium | §3.6's ordering ⚠ is unresolvable as specified — and an atomic primitive exists, measured |
| M5 | Medium | §3.4/§7 credit a containment check that does not run on the path being widened |
| L1 | Low | The homoglyph denylist is hand-typed and misses 6 of the 7 codepoints that fold to a separator |
| L2 | Low | Both regexes admit 33 C0/DEL codepoints the prose promises are rejected |
| L3 | Low | The percent-encoding rule is a comment beside the code block, not in it |
| L4 | Low | The two dead-lettered prod videos lost their disposition when the repair was deleted |
| L5 | Low | Integration fixtures write **physical** keys directly and will bypass the encoder |

---

## What I verified, and could not break

Recorded first so the fixes below are not mistaken for doubt about the collapse.

### The premise holds: no consumer breaks on a non-ASCII, separator-free key

Every consumer the brief named, plus the ones it did not, traced to a total function:

| Consumer | Behaviour on a non-ASCII key | Evidence |
|---|---|---|
| `Content-Disposition` (the classic break — a raw non-ASCII byte in a header value throws) | **Safe.** `asciiSafe` maps every codepoint outside `\x20-\x7e` to `_`; `encodeRFC5987` percent-encodes every UTF-8 byte outside its allowlist | `file-response.ts:5-11`, `:13-24`, `:53` |
| HTML interpolation | **Safe.** `esc()` escapes `& < > "`, and the key appears only in double-quoted attributes and text | `render.ts:48-54`, `:106`, `:114`; `render-dig-deeper.ts:487` (`esc(path.basename(mdPath))`) |
| Any URL | **None exists.** The only URI built from a filename is the Obsidian link, already `encodeURIComponent`'d | `VideoMenu.tsx:39`; `htmlViewHref` (`:55`) is keyed on `video.id`, not the md key |
| `MODEL_KEY(base)` → `models/{base}.json` | Pure interpolation, no charset assumption | `model-store.ts:32` |
| `pdfCacheKey(base)` | Rejects only `/ \ \0 ..` — charset-agnostic | `pdf-render-version.ts:18` |
| `pdfRelPath` | `path.basename` + `.replace(/\.md$/, '')` — charset-agnostic | `pdf-path.ts:16-30` |
| PDF renderer | `page.setContent(html)` — no temp file named from the base | `generate-doc-pdf.ts:91` |
| Postgres | **No CHECK constraint on any key column.** `doc_key` is `playlist_id \|\| '/' \|\| video_id`, not the md key | `0012_serve_model_charge.sql:53`, `0014:47`, `0020:213` |
| Local filesystem | Already full of Unicode for the app's whole life; `abs()` is `path.join` | `local-blob-store.ts:12` |

So the guard's allowlist protects nothing that is not already protected. **§3.4's core claim is
correct**, and §3.5's deletions follow from it.

### Premises re-measured against the live local stack

Probes ran against `http://127.0.0.1:54321` only, asserted the hostname before connecting, and
removed every object they created (verified empty afterwards). Scripts under the session scratchpad.

| Premise | Result |
|---|---|
| **P1** Storage rejects every non-ASCII key | ✅ **Reproduced.** Hangul, NFC `café`, NFD `café`, emoji → `400 Invalid key`. ASCII baseline `ok` |
| **P2** 255 per **segment**, not per path | ✅ **Reproduced at the exact boundary.** 254 `ok`, 255 `ok`, **256 → `500`**, 257/300 → `500`. A path of **2030 chars** across 8 segments of 250 → `ok`. Both halves confirmed, including that over-length returns `500` not `400` |
| §3.2's marker `=` is storable | ✅ `0007_=hAbC….md` `ok`; **leading** `=hAbC….md` `ok`; base64url `-` and `_` `ok` |
| §4's "five characters `SAFE` excludes that Storage accepts" | ✅ space, `(`, `)`, `+`, `=` all `ok` — the §4 migration gate is genuinely needed |
| §3.2's 65-char worst case | ✅ `ok` — 65 ≪ 255, ample headroom |
| **§2.4** APFS aliases NFC/NFD | ✅ Wrote NFC, read it back through the **NFD** path: `"ORIGINAL-NFC"` |
| **§2.4** `rename` overwrites the alias | ✅ `renameSync(tmp, NFD)` left one dir entry and the **NFC** path now reads `"INTRUDER-NFD"` |
| **P3** one Storage call site | ✅ `supabase-blob-store.ts:20` is the only `client.storage.from(` outside tests |
| **P4** `list()` never inverts | ✅ 3 callers: `reconcile-serial.ts:102`, `dig-state/route.ts:47` (both literal `dig/${base}/`), `load-dig-for-serve.ts:34` (via a `prefix` variable, then suffix-filtered) |
| **P5** the guard has exactly 2 callers | ✅ `serve-summary-core.ts:61`, `resolve-summary-key.ts:16` |
| §3.2's lone-surrogate reachability | ✅ `slugify` keeps `\p{L}` (astral letters included) and ends `.slice(0, 60)` on **UTF-16 code units** — `slugify.ts:1-7`. The `utf16le` choice is justified |

**P2's falsifier is now genuinely discharged.** v1's defective probe varied one segment under a fixed
prefix; mine varied segment count independently of segment length, so a whole-path bound would have
shown up as the 8×250 case failing. It passed at 2030 characters.

---

## B1 — Blocking: the §3.4 regex rejects every key that exists today

**Spec §3.4, line 132:**

```ts
const CLOUD_SUMMARY_MD_KEY = /^(?!.*\.\.)[^/\\ -／⁄∕]{1,128}\.md$/u;
```

Inside the class, between `` (U+0020) and `／` (U+FF0F), sits a `-`. ECMAScript parses that as a
**range**: `U+0020–U+FF0F`, 65 264 codepoints. Negated, the class admits only `U+0000–U+001F` and
`U+FF10–U+10FFFF`. Every ASCII letter, every digit, `_`, and all of Hangul (U+AC00–U+D7A3, below
U+FF0F) are **excluded**.

Measured, running the regex verbatim (7 of 23 cases wrong, every one a false rejection):

```
want   v8         cur    key
PASS   FAIL   << pass   "001_intro.md"        plain ASCII key, tests/lib/pdf/pdf-path.test.ts:13
PASS   FAIL   << pass   "275_google-okf.md"   real prod-shaped key, pdf-path.test.ts:9
PASS   FAIL   << pass   "0007_한국어.md"       Korean — the entire point of backlog #36
PASS   FAIL   << FAIL   "0007_café.md"        NFD accented Latin (behavior 15)
PASS   FAIL   << FAIL   "0007_😀.md"          emoji / astral (behavior 16)
PASS   FAIL   << FAIL   "0007_a b.md"         space in title (behavior 16)

ASCII codepoints admitted by the v8 class: [0..31]
  -> 32 of 128, and every one of them is a C0 control character.
```

**Failure scenario.** Ship this and `assertCloudSummaryMdKey` throws 409 for every video in the
bucket. `serve-summary-core.ts:61-64` returns `409 corrupt summary key` before the blob read;
`resolve-summary-key.ts:16` returns `null`, so dig resolution fails too. Every paid summary in prod
becomes unreachable — strictly worse than #36, which destroys non-ASCII summaries only. By the
brief's own rule ("a paid artifact … unreachable is Blocking"), Blocking.

**Fix.** Do not write a range where a list is meant, and per L1 do not hand-type the homoglyphs:

```ts
// Separators in every form. `-` first inside the class so it cannot open a range.
const SEP = /[/\\ ／⁄∕＼﹨℀℁℅℆]/u;
```

with the trailing set **derived** (L1) rather than typed, and control characters excluded explicitly
(L2). Add a unit case asserting `001_intro.md` passes — behavior 17 lists only rejections, which is
why a regex that rejects everything would have gone green.

---

## H1 — High: behavior 18 tells `copyToLocal` to refuse a write it is required to perform

**§5 behavior 18:** *"A cloud→local write aliasing an existing vault file with no index row throws
and leaves the file untouched — via **both** `copyAdditiveVideo` and `copyToLocal`."*

`copyToLocal` (`sync-run.ts:791-793`) is not an additive create. It is the two-sided Class-A transfer,
and overwriting the receiver's file at the winner's key is its **specified, deliberate** semantics:

```
// sync-run.ts:386-393
// A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
// promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
// .promote() is create-if-absent … so on the cloud winner-copy path the loser's stale
// body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
await loser.blob.put(loser.p, key, staged, 'text/markdown');   // :394
```

A guard that makes `copyToLocal` throw when the destination is occupied throws **every time**, because
on the two-sided path the destination is occupied by definition — that is what "two-sided" means.
Implemented as written, behavior 18 breaks every cloud→local Class-A transfer: no local row ever
receives a newer cloud body, and `writeVideoBaseline` never advances.

§3.6 records round-7 Blocking 1 as a ⚠ but supplies no criterion separating the two cases:

- **must refuse** — the vault file at this key belongs to a *different* video (or to no index row at
  all, the `recoverOrphanedVideos` case), so writing destroys someone else's paid artifact;
- **must proceed** — the vault file at this key is *this* video's own diverged body, which the
  Class-A decision has just ruled the loser.

The distinguishing fact is available (the receiver's index row for `videoId` and whether its
`summaryMd` aliases the key), but the spec does not name it. Until it does, behavior 18 is not
implementable as stated.

**Fix.** Split behavior 18. For `copyAdditiveVideo`, "occupied ⇒ throw" is right — there is no
receiver row, so any occupant is foreign. For `copyToLocal`, the guard must be "occupied **by a key
that no receiver row claims** ⇒ throw", and the spec must say so in §3.6 rather than leaving it ⚠.

---

## H2 — High: the mutation table was deleted with the machinery it did not belong to

v8 has **no mutation list**. v7 §6 had one, on its third attempt, and the spec itself explains why
that number matters: *"Round-2 B2 killed v2's mutation list … Round-3 B2 killed v3's by measurement."*

Six of v7's ten mutations target mechanisms **v8 keeps**:

| v7 mutation | v8 behavior it must turn red | Still present in v8? |
|---|---|---|
| `hash(NFC(s))` instead of `hash(s)` | 3 (NFC/NFD encode differently) | ✅ kept |
| Widen `SAFE` to include `=` | 4 (injectivity; *"a sampling property test cannot kill this"*) | ✅ kept |
| Apply the `list()` marker check to the caller's prefix | 10 | ✅ kept |
| Encode empty segments | 11 and 12 | ✅ kept |
| The additive guard consults index rows instead of the blob store | 18 | ✅ kept |
| Drop the `adopt` throw / brand / servability | 19, 21, 24, 25, 26 | ❌ correctly gone |

Four entries died with the machinery. Six did not, and went with them.

Also lost: **the money-guard method.** v7 said *"15, 16, 19 assert the ledger did not move, using the
M3.1-A pattern (PR #98) — measure spend, do not assert an intention."* v8 behavior 14 says "ledger
unmoved" and specifies nothing. #36 is a money-path defect; this project has a recorded history of
money guards that were present and inert.

**Fix.** Restore a mutation table containing the six surviving entries, and restore the one sentence
naming the money-guard pattern on behavior 14.

---

## M1 — Medium: "and that is the whole fix" is false for the case in the title

§3.4's heading: *"The serve guard asserts what it actually requires — and that is the whole fix."*

Measured against the **current, unmodified** guard (`assert-cloud-summary-md-key.ts:14`):

```
"0007_한국어.md"   current allowlist: pass
"0007_café.md"    current allowlist: FAIL   (NFD: U+0301 is \p{M}, not \p{L}/\p{N})
"0007_😀.md"      current allowlist: FAIL
"0007_a b.md"     current allowlist: FAIL
```

Korean **already passes**. `slugify` emits only `[\p{L}\p{N}-]` (`slugify.ts:1-7`), and the allowlist
is `[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}`, so every CJK slug the mint path produces is admitted today.
What destroys a Korean summary is **P1 — Storage's 400** — which the *encoder* fixes, not the guard.

The guard widening is real and needed, but for a narrower set than the section claims: NFD-accented
Latin, emoji, astral, and titles with spaces. Getting this wrong matters because §3.5 justifies five
deletions from this sentence, and because behaviors 16/17 are introduced as *"the pair that
matters"* — a reader will conclude the guard carries the fix. It does not; §3.1/§3.2 do.

**Fix.** Retitle §3.4 to what it does ("the guard stops rejecting four classes it never needed to")
and state plainly that the encoder is what makes any of it storable.

## M2 — Medium: the `utf16le` mechanism outlived its only falsifier

§3.2 keeps both the mechanism and its reachability argument (*"`slugify`'s `.slice(0, 60)` cuts UTF-16
code units, so an astral letter at the boundary yields a lone surrogate"* — which I confirmed against
`slugify.ts:1-7`). v7 behavior **22** was the test:
`encodeSegment('003_x\uD840.md') !== encodeSegment('003_x\uD850.md')`. v8 dropped it. Behavior 4
(injectivity, "property + crafted preimage") will not reach it — a property generator over well-formed
strings does not emit lone surrogates, which is exactly why v7 wrote 22 separately.

**Fix.** Restore behavior 22.

## M3 — Medium: `copy()` is asserted unchanged with nothing exercising it

§3.7: *"`copy()` needs no change."* v7 behavior **13** — *"`copy()` of a Korean-based dig blob to a new
base works end to end"* — was dropped, and v8's list has no `copy()` entry at all. `copy()` is on a
live path: `reconcile-serial.ts:118` remaps `MODEL_KEY(oldBase) → MODEL_KEY(newBase)`, which
post-encoder means encoding both sides of the same call. "Needs no change" is plausible and untested.

**Fix.** Restore behavior 13.

## M4 — Medium: §3.6's ordering ⚠ cannot be closed by the mechanism §3.6 names

§3.6 requires the guard to "read `tryGet`" and separately requires that "the `tryGet` check and the
write must not be separable by a concurrent writer". Those are in tension: check-then-write **is** the
separable pattern, and the `BlobStore` interface offers no atomic alternative —

```
// local-blob-store.ts:15-20 — put
const tmp = dest + '.' + crypto.randomUUID() + '.tmp';
fs.writeFileSync(tmp, bytes); fs.renameSync(tmp, dest);     // overwrites

// local-blob-store.ts:58-62 — promote
fs.renameSync(from, to);                                    // overwrites
```

**But a primitive does exist, and I measured it:** on APFS,
`open(path.join(dir, NFD), 'wx')` against a file created under its **NFC** name returns **`EEXIST`**.
Exclusive create sees through the aliasing that is the whole reason §3.6 exists. The spec notes `wx →
EEXIST` in §2.4 and then does not use it.

**Fix.** For the local receiver, specify `putIfAbsent` on the seam backed by `wx` (atomic, and it
detects the alias). `tryGet` with `unreadable ⇒ occupied` remains right for the Supabase receiver,
where no atomic create exists — and stating the split is what closes round-6 M1 instead of restating
it as a ⚠.

## M5 — Medium: the containment check credited as the backstop does not run on this path

§3.4: *"What protects both sides is `assertLogicalKey` plus the resolved-path containment check."*
§7: *"The resolved-path containment check remains the real backstop."*

`assertIndexRelPathWithin` runs at `build-doc-html.ts:77`, `:104`, `:105`; `rerender.ts:50`;
`app/api/videos/[id]/pdf/route.ts:85` — **all local-filesystem paths**. It is not on the cloud serve
path. There, after the guard, the only check is:

```ts
// blob-store.ts:87-91
export function assertLogicalKey(key: string): void {
  if (key.startsWith('/') || key.split('/').includes('..') || key.includes('\0')) {
```

which rejects a leading `/`, `..` segments and `\0` — and nothing else. That is sufficient (nothing
downstream is charset-sensitive, per the table above), but the spec's stated reason for sufficiency
names a check that is not there. This is the same defect class the previous seven rounds were made of,
and it is in the risk row that says the widening *"needs a security reviewer at the PR"* — the
reviewer will look for a backstop that is not on the path.

**Fix.** Say `assertLogicalKey` on the cloud path, `assertIndexRelPathWithin` on the local pipeline.

## L1 — Low: the homoglyph list is hand-typed and mostly wrong

Exhaustive sweep over all 1 114 112 codepoints, NFC/NFD/NFKC/NFKD, for anything folding into a string
containing `/` or `\`:

```
U+2100 "℀"  NFKC -> "a/c"    <-- admitted by the intended denylist
U+2101 "℁"  NFKC -> "a/s"    <-- admitted
U+2105 "℅"  NFKC -> "c/o"    <-- admitted
U+2106 "℆"  NFKC -> "c/u"    <-- admitted
U+FE68 "﹨" NFKC -> "\"      <-- admitted
U+FF0F "／" NFKC -> "/"      (named by the spec)
U+FF3C "＼" NFKC -> "\"      <-- admitted
raw separators admitted: 0
```

The spec names three (`／⁄∕`); only one of them folds, and it misses six that do. **Inert today** —
nothing NFKC-normalizes a key (`.normalize(` appears only at `serial-migrate-exec.ts:33,42` and
`content-hash.ts:12`, all **NFC**, which produces none of the above), hence Low.

But this is a typed vocabulary that will silently stop matching. **Derive it**: reject any codepoint
whose NFKC form contains `/` or `\`, computed at module load. Same shape as
`scripts/check-vocabulary-collisions.py`'s concern, and the same lesson as the project's
"hardcode only what fails loudly" note.

## L2 — Low: 33 control codepoints are admitted, against the prose

The guard's docstring (`assert-cloud-summary-md-key.ts:8-9`) and §3.4's own comment
(`// … no control chars, bounded`) both promise control characters are rejected. Measured, **both**
the written regex and my reconstruction of the intended one admit all of `U+0000–U+001F` **and**
`U+007F`. `assertLogicalKey` catches `\0` downstream; the other 32 reach the blob store. Harmless
today (they are `¬SAFE`, so the encoder hashes them), but the comment claims a property the code does
not have.

## L3 — Low: the percent-encoding rule is prose, not code

```ts
const CLOUD_SUMMARY_MD_KEY = /…/u;
// plus: reject any percent-encoded separator (%2f, %5c) case-insensitively.
```

A requirement written as a comment next to the thing that does not implement it is the shape that
loses requirements. (Defense-in-depth only: `%` is `¬SAFE`, so such a key is hashed, and P6 holds —
nothing decodes it.) Put it in the predicate.

## L4 — Low: the two dead-lettered prod videos lost their disposition

v7 §8 carried *"The two dead-lettered prod jobs stay unrecovered | Accepted by decision (§1)."* v8's
three decisions (①②③) do not mention them, and v8 §3.5 deletes the `videoId` repair on the grounds
that there is *"nothing to repair"*. There are two real prod videos in that state — the ones that
produced #36. Post-fix they are re-ingestible, but the spec should say that rather than lose the row.

## L5 — Low: integration fixtures write physical keys and will bypass the encoder

`tests/integration/helpers/seed.ts:62` and `tests/integration/serve-md-unreadable-no-charge.test.ts:82`
call `svc.storage.from(...)` directly with `${uid}/${playlistKey}/${base}.md`. Post-encoder that is a
**physical** address. For the ASCII fixtures it stays identity; for behaviors 6, 7, 8, 14, 15 and 16 —
all non-ASCII — the fixture would seed an address the app never reads. It fails loud (404, not a
wrong answer), hence Low, but §5 should say the non-ASCII fixtures seed **through** the seam.

---

## Convergence

**NOT CONVERGED**, on B1 alone. B1 is one character and the spec is otherwise the strongest version of
this document: the collapse is right, the premises table is honest, and P1/P2/§2.4 all reproduced
under independent probes including at the exact 255/256 boundary that v1 got wrong.

If B1, H1 and H2 are fixed I would expect round 9 to converge. The Mediums are accuracy repairs to
sentences, not redesigns; M4 is the only one with a design decision in it, and the decision is already
measured (`wx` → `EEXIST`).

Two notes on calibration. **B1 would have gone green** under §5 as written: behavior 17 lists five
things the guard must reject and behavior 16 asserts a serve, but no unit behavior asserts that a
plain ASCII key still passes the guard — a regex rejecting the universe satisfies every rejection
case. That is the same shape as this project's recorded "a green suite can describe an unreachable
world". And **H2 is the round's real risk**: v8 deleted correctly and then deleted six paces past the
line, which is the failure mode a collapse-shaped revision has, symmetric to the over-building of
v5–v7.

*Codex gap: none — this is the Claude half of a dual round.*
