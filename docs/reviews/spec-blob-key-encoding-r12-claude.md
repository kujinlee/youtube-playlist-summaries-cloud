# Round 12 — Claude adversarial review, spec v13 (backlog #36, cloud blob key encoding)

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` in the working tree
(**v13**), branch `fix/cloud-blob-key-encoding`. Phase 1 — no code written; every finding is about the
design.

**Verdict: NOT CONVERGED** — 2 High, 2 Medium, 7 Low.

**Escalation counter (read this before reading it later):** three of the findings (H2, M1, M2) are
caused by **v13's own fixes** to §3.6/§3.6.4. Under `review-method.md:45-49` that makes this **round 2
of the new FIX cycle on §3.6**, and the rule as written ("two consecutive rounds") fires **now**. The
brief's phrasing ("two more rounds like round 11") reads as needing a third. I am recording the count,
not adjudicating it. My own recommendation is **FIX, not a second REDESIGN**, for the same reason
round 11 gave and for one new one: I attacked R1's central safety property directly — *"the write
physically cannot clobber, on either backend"* — and **measured it true on both**. All three findings
are again specification-completeness (*which branch does the rule cover*, *which lines of the adapter
change*, *is this universal actually universal*), not mechanism. H1 is **not** a §3.6 finding and does
not touch the counter.

---

## How this was measured

All probes under `/tmp`, no tracked file modified. Node `~/.nvm/versions/node/v22.14.0/bin/node`
(v22.14.0). Supabase probes asserted `new URL(API_URL).hostname ∈ {127.0.0.1, localhost}` and refused
otherwise; every object created was removed and the prefix verified empty (10 objects, 0 remaining).
Character classes written with escapes only. I typed literal bidi characters into my first probe file
**and again into the first draft of L2 in this document** — the fourth and fifth instances of the class
this spec has now shipped three times. Both were caught by a sweep, not by reading; the sweep is
`unicodedata.category(ch) in {Cc,Cf,Cs,Co,Cn}` over the file, and it is worth being a check script,
because reading provably does not catch it.

---

## What HELD — stated first, because it is the load-bearing result

The brief's highest-value item was the v13 predicate. **It survives both directions.**

**Direction A — does v13 reject anything the shipped guard accepts? Zero.** Reproduced independently
of the coordinator's 19 cases:

| Sweep | Result |
|---|---|
| every codepoint `0..0x10FFFF` × 4 structural positions (first / second / last / whole name) | **0 regressions** |
| adjacency: all 3,799 `\p{L}\p{N}` codepoints that are **not** NFKC-stable, squared (14.4M pairs) | **0 regressions** |
| the same 3,799 at end-of-name (the joint, where v11 broke) | **0 regressions** |
| total lengths 4, 128, **129, 130, 131**, 132 | 129–131 accepted, 132 rejected — behavior 17b holds |
| `'a'` + 64 astral letters + `.md` = 68 code points / 132 UTF-16 units | **accepted** — behavior 24 holds |

**And a stronger statement than the spec makes.** I swept `NFKC(name + '.md') === NFKC(name) + '.md'`
over all 1,114,112 codepoints: **0 violations**. `.` is a starter (ccc = 0), so the joint is a valid
normalization boundary for every input. That is the *proof* of v13's thesis, not merely evidence for
it: inspecting the name is **provably equivalent** to inspecting the glued key, minus exactly the `..`
the fold manufactures at the joint. §3.4 argues this case-by-case (`003_lesson-⒈` vs `001_a．．b`) and
leaves a reader wondering what else the split might hide. Nothing does. Worth putting in the spec —
it retires the question permanently instead of re-answering it each round.

**Behavior 27 holds.** Full codepoint space × 8 title shapes (including `'x'.repeat(59) + c`, the
`slice(60)` boundary) through `${padSerial(7)}_${slugify(title)}.md`: **0 outputs fail the predicate**.

**R1's no-clobber property holds on both backends — measured, not reasoned.**

| Probe | Result |
|---|---|
| `linkSync(tmp, <NFC path>)` over an NFD occupant on APFS | `EEXIST`; occupant bytes intact |
| `linkSync` through a **case** alias (`Case.md` / `case.md`) | `EEXIST`; occupant intact |
| Supabase `move()` onto an occupied destination | `409 The resource already exists`; **occupant intact**, staging source intact |
| Supabase `upload(upsert:false)` onto an occupied destination | `409`; occupant intact |

**R4's subset claim re-derives.** On this volume: U+212B `Å` and U+00C5 `Å` alias (full canonical
equivalence); U+FF21 `Ａ` and `A` do **not** (not NFKC). NFC-equality is a proper subset. ✔

**Premises re-derived this round** — `[VERIFIED]` at current head:

- **P1** `003_한국어.md` → `400 Invalid key`. ✔
- **P2** 255-char segment accepted; 256 → **`500`**; 5 × 200-char segments (~1000 total) accepted. ✔
- **§4's five characters**: space, `(`, `)`, `+`, `=` all accepted; `%` and `~` rejected `400`. ✔
- **P3** the only non-test `storage.from(` write path is `supabase-blob-store.ts:20`; the recorded
  falsifier `scratchpad/b3-raw.ts:22` is download-only and `.gitignore:68` is `scratchpad/`. ✔
- **P5** exactly 2 callers — `serve-summary-core.ts:61`, `resolve-summary-key.ts:16`. ✔
- **P6** no URL/href/redirect/fetch is built from `summaryMd`/`mdKey`/`base`/`baseName` anywhere in
  non-test source. ✔
- **§3.6.4 credential 1**: `summary-core.ts:103` writes `` `video_id: "${videoId}"` `` unconditionally
  into the frontmatter array; `pipeline.ts:148-149` is `if (!videoId || indexedIds.has(videoId)) continue`.
  Both halves hold. ✔
- **`promote`'s four non-test callers**: `sync-run.ts:268`, `summary-handler.ts:178`,
  `write-dig-section-blob.ts:50`, `consistency.ts:37`. Exactly four. ✔
- **`resolve.ts:81-87`** hard-returns `new SupabaseBlobStore(...)` with no backend branch — the
  round-11 adjudication (Claude right, Codex wrong about the failure) is confirmed. ✔
- **The tripwire** at `tests/lib/dig/write-dig-section-blob-promote.test.ts:67-74` is `it.failing`
  exactly as cited. ✔
- **`envelope.sourceMd` genuinely names the summary key** — two production writers, `generate.ts:51`
  (`sourceMd: video.summaryMd`) and `serve-doc.ts:175` (`parsed.sourceMd ?? \`${base}.md\``, with
  `parsed.sourceMd` set from `mdKey` at `serve-summary-core.ts:103` / `app/s/[token]/route.ts:77`),
  plus `serial-provenance.ts:16` rewriting it on rename. `ModelEnvelopeSchema.sourceMd` is
  `z.string().min(1)` — **required**, not optional — so an envelope that parses always carries one.
  Brief item 4's "what if it lacks `sourceMd`" has a clean answer: that envelope never reaches
  `kind: 'envelope'`. ✔

**One plausible-looking concern I killed rather than filed.** A 131-code-point Korean key is 387 UTF-8
bytes; APFS accepts it (measured: 128 Hangul + `.md` wrote fine), because its limit is 255 UTF-16
units, not bytes. There is no ENAMETOOLONG class here on macOS. *(ext4 is 255 **bytes** — see L8.)*

---

## H1 — High. The only `slugify` output §3.4 newly admits is the **lone-surrogate** class, and that class does not survive the local filesystem. Behavior 16's "the vault filename stays readable" is false for the case it names.

**Not caused by the round-10 redesign or by v12/v13's predicate fixes.** §3.4's widening dates from v8
and §3.2's `utf16le` decision from v9; §3.4/§3.5 got their first adversarial pass at round 11. This is
a §3.4/§3.2/§5 finding and does **not** touch the §3.6 escalation counter.

**Measured, both halves.**

*Half 1 — what the widening actually buys the mint path.* Over the full codepoint space × 8 title
shapes, the current shipped guard `/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` rejects **93,231**
`slugify` outputs, and **every single one is ill-formed UTF-16** (`key.isWellFormed() === false`) — a
lone surrogate left by `slugify`'s `.slice(0, 60)` cutting an astral letter. v13 rejects **0**. So for
the **mint** path the entire behavioural delta of the §3.4 widening is *"lone-surrogate keys are now
servable"*. (For the **adopt** path the delta is the NFD/space/emoji class §3.4's round-8 M1 precision
already names; a `readdir` string is always well-formed, so adopt never produces this class.)

The spec knows the class is reachable and *requires* it:

> §3.2 — *"`slugify`'s `.slice(0, 60)` cuts UTF-16 code units, so an astral letter at the boundary
> yields a lone surrogate."*
> Behavior **16** — *"a title with … an astral letter at the `slice(60)` boundary ingests and serves
> 200 — no fallback, no refusal, **and the vault filename stays readable**."*

*Half 2 — what the local filesystem does with it.* Probe in `/tmp` on APFS:

```
wrote key        "003_x\ud840.md"
readdir returned "003_x�.md"          <- U+FFFD REPLACEMENT CHARACTER
readdir === key ?  false
then wrote       "003_x\ud850.md"          (a DIFFERENT lone high surrogate)
directory now holds 1 file
read through key1 -> "BBB"                 <- key2's body. key1's content is GONE
```

Node encodes every unpaired surrogate as U+FFFD when it converts a JS string to a path — the *exact*
behaviour §3.2 cites as its reason for hashing with `utf16le` instead of `utf8`. §3.2 applies that
lesson to the **encoder** and nothing applies it to `LocalFsBlobStore`, which §3.1 and §2.4 declare to
be **identity**:

> §2.4 — *"**MEASURED.** `LocalFsBlobStore.abs()` is `path.join(indexKey, key)` — identity."*

That premise is a statement about **path construction** (`local-blob-store.ts:12`), and the spec reads
it as a statement about **storage**. It is false at the storage layer for exactly the class §3.4 newly
admits. Same shape as round-11 M3: *the measurement was right for the input it was taken on.*

**Consequences, with the caller named for each.**

1. **Behavior 16 is falsified as written.** The vault filename is `003_x…�.md`. That is mojibake in a
   filename — the readability decision ③ exists to protect. It is milder than `003_dQw4w9WgXcQ.md`,
   but the behavior asserts the opposite of what happens, so it would pass only if written against a
   BMP title, which is how the analogous round-11 M3 survived.
2. **The vault's identity function cannot find its own file.** R4 lifts `findByNormalizedName`
   (`serial-migrate-exec.ts:31-45`) into *the* one vault-name identity predicate. The cloud row holds
   `003_x\uD840.md`; `readdir` yields `003_x�.md`; `canonicallyEqualName` NFC-compares them and
   returns **false**. `resolveOnDisk`'s whole purpose — *"the index string may differ from the on-disk
   bytes by Unicode normalization"* (`:53-59`) — does not cover replacement-character substitution.
3. **A permanent Class-A refusal, i.e. round-8 H1's exact consequence.** Reachable chain, every link
   in this repo: the cloud mints `003_x\uD840.md` (`summary-handler.ts:96`, in-memory, never
   round-tripped through a filesystem) → sync writes it to the vault, disk name becomes
   `003_x�.md` → the local index is later rebuilt from disk and `recoverOrphanedVideos` sets
   `summaryMd = file` verbatim (`pipeline.ts:104`), i.e. the U+FFFD form → next sync,
   `canonicallyEqualName(loserVideo.summaryMd, key)` is **false**, R3 takes the probe branch,
   `tryGet` resolves through the same encoding and reports the address **occupied**, and R3 throws
   *"occupied by something we do not own"* — for that video, on every run, forever. §3.6.0 exists to
   prevent precisely this shape.
4. **Cloud and local disagree about how many artifacts exist.** §3.2's `utf16le` hashing deliberately
   gives `\uD840` and `\uD850` **different** physical cloud keys (behavior 22). The local side maps
   them to one file. Behavior 22 has no local counterpart.

**Fix — a choice, and I recommend the first.**

- **(a) Refuse ill-formed UTF-16 in `isServableSummaryKey`**: `if (!key.isWellFormed()) return false;`
  (Node ≥ 20). One line, total, no enumeration. It costs the astral-boundary title *nothing the
  current guard does not already cost it* — that key is 409'd in production today — so it is not a
  regression against shipped behaviour, and it makes §3.1's identity premise true again. Behavior 16
  then splits: the space/emoji/NFD half stays, and the astral-boundary half becomes *"refused at the
  mint before money moves"* (§3.5's mint call site, `summary-handler.ts:96`, already the right place).
- **(b) Make `slugify` not emit lone surrogates** — cut on code points, not UTF-16 units. This is the
  honest fix and it dissolves the class at the source, but `slugify` is shared with the local path and
  changes vault filenames, so it belongs with **backlog #46**, which already owns exactly that
  constraint.
- **Whichever is chosen, §2.4/§3.1 must stop calling `LocalFsBlobStore` "identity" without
  qualification**, and behavior 16's *"the vault filename stays readable"* must be corrected or split.

---

## H2 — High. §3.6.4's new `sourceMd` requirement is **unsatisfiable on the `ship` branch**, which `companion.ts` itself calls the common case.

**Caused by v13's own fix.** v11 accepted the third residual in one sentence; round-11 M1 falsified it;
v13's answer is *"Decision: require it."* This is the first review of that decision.

The rule (spec §3.6.4, lines 812-814):

> **Decision: require it.** Before any companion **ship or delete**, require
> `canonicallyEqualName(receiverModel.envelope.sourceMd, \`${base}.md\`)`. If the envelope names a
> different logical key, refuse and leave the model untouched.

`decideCompanion` returns `ship` on two branches, and only one of them has a receiver envelope:

```ts
// lib/cloud-sync/companion.ts:113-125
if (senderMatch && receiverMatch) { … return { kind: 'ship', envelope: senderMatch }; }  // has one
if (senderMatch) return { kind: 'ship', envelope: senderMatch };                          // MAY NOT
```

Branch 2 fires whenever the sender holds a model built from the winning MD and the receiver's read is
`none` or `unknown` — i.e. **there is no `receiverModel.envelope` at all**, so `.sourceMd` cannot be
read. And this is not an edge: `companion.ts:46` says so in its own words —

> *"`unknown` is the COMMON outcome: a cloud video that was never HTML-served has no model blob, and
> the Supabase backend cannot prove that 404."*

Implemented literally, the companion **ship** step therefore refuses in the majority case and a
receiver that has no model never gets one. The consequence is the one `companionTransfer`'s own M-R6-1
comment describes as sticky (`sync-run.ts:456-462`): the Class-A body has already landed, so the next
run's `reconcileClassA` returns `'skip'` and the companion step never runs again. The share stays
unrenderable until an owner re-serve, which **reserves and charges**.

Note the `delete` half of the rule is fine: `provablyStale` requires `receiverModel.kind === 'envelope'`
(`companion.ts:151-152`), so the delete branch always holds an envelope. The rule is correct for
delete, correct for overwriting an existing receiver model, and **undefined for shipping into an empty
address** — which is the only branch where nothing can be destroyed.

**Fix.** State the rule per *outcome*, not per *call*:

- receiver envelope present → require `canonicallyEqualName(envelope.sourceMd, base + '.md')`; refuse
  otherwise. (Covers delete and overwrite — the two destructive outcomes.)
- receiver `none` → **ship**. Nothing is being destroyed; there is no owner to contradict.
- receiver `unknown` → the read failed and cannot prove absence. Today's code ships here. Whichever
  way this goes it must be *decided in the spec*, because it is the common case and it is the one
  branch where "refuse" and "proceed" have genuinely different costs (a refused ship costs an owner
  re-serve; a wrong ship overwrites a model that may belong to another key). My recommendation: ship,
  and record it as a named residual — it is exactly today's behaviour, so it is not a regression, and
  refusing on `unknown` would make the ship branch dead on the Supabase receiver, which can *never*
  return `none` (`companion.ts:149-150` already relies on that asymmetry for a different flag).

Behavior **18j** needs the same split — as written it only exercises the "names a different key" case
and would pass with the ship-into-empty branch broken.

---

## M1 — Medium. R1's adapter table is wrong about Supabase in two ways, and cites the lines that do **not** change.

**Caused by v13's own fix** (`promoteIfAbsent` is new in v13).

Spec §3.6.2:

> | `SupabaseBlobStore` | its existing `promote` body already is this (`:112-116`) |
>
> *"`SupabaseBlobStore` already behaves this way, and it conforms by **silently returning**, which is
> the evidence for the intended reading."*

`:112-116` is the **first** short-circuit. The rest of the method is:

```ts
// lib/storage/supabase/supabase-blob-store.ts:117-126
const { error } = await this.b().move(from, to);
if (error) {
  if (await this.exists(ref.principal, ref.finalKey)) { await this.b().remove([from]).catch(() => {}); return; }
  throw error;                                        // <-- does NOT resolve
}
```

**(1) It throws where R1 requires it to resolve.** I measured that `move()` onto an occupied
destination returns `409 The resource already exists`, so this branch *is* the Supabase EEXIST path.
It resolves only if the `exists()` re-check succeeds — and `exists` is `get() !== null`
(`:78-80`), on the one backend this codebase documents as unable to prove absence
(`provesAbsence = false`, `:8-10`). `SupabaseBlobStore.copy`'s own docstring (`:87-97`) refuses to build
a preflight on those primitives for exactly this reason; `promote` is built on them twice. A transient
5xx at that moment throws a 409 out of `copyAdditiveVideo` at `sync-run.ts:268`, R2's classification
never runs, and the run reports a per-video error. This self-heals next run (unlike round-11 H1's
permanent strand), which is why it is Medium and not High — but it is the same defect round-11 H1
fixed for the local adapter, left standing on the other one, under a sentence saying it is already
handled.

**(2) It cannot return the discriminant.** `promote` returns `void`; `promoteIfAbsent` is specified as
`'created' | 'already-exists'`. Supabase has three success paths (`:113` short-circuit, `:117` move
succeeded, `:121` move-errored-but-final-present) mapping to `already-exists / created / already-exists`.
The adapter must change. "No change needed" is not a tenable row.

**And a note that argues for simplifying, not patching:** R2 never reads the discriminant. Its
pseudocode branches entirely on the `tryGet` read-back:

```
promoteIfAbsent
tryGet(FINAL key)
   ok, hash equals → SUCCESS   |   ok, hash differs → REFUSE
   'unreadable'    → REFUSE    |   'absent'         → REFUSE
```

No caller in the spec consumes `'created' | 'already-exists'`. The load-bearing property is
**resolves-rather-than-throws**; the discriminant is decoration, and behavior 18d2 tests the property
while the return type invites an implementer to trust the label. Either give it a consumer or make it
`Promise<void>` with the resolve-on-EEXIST contract stated. (Also: `linkSync` with a **missing source**
returns `ENOENT`, not `EEXIST` — measured. `LocalFsBlobStore.promote:60` short-circuits that case
today; `promoteIfAbsent` as specified does not, so the two primitives differ on a case `promote`
deliberately handles. Not reachable from R2, which always stages first — but the adapter table should
say so rather than leave it to be rediscovered.)

---

## M2 — Medium. §3.6.4 credential 2 carries a **universal**, and the universal is false. This document's fourth.

**Caused by v13's own fix** (credential 2 is new in v13; v11's naming premise was the one round 11
falsified).

> §3.6.4 — *"Aliasing filenames must share the numeric prefix (digits do not alias under canonical
> equivalence or case folding), so the serial half catches **every** aliasing collision that has a
> receiver row at all."*

`ensureReceiverSlot`'s guard is a **disjunction** and both disjuncts can miss (`sync-run.ts:203-206`):

```ts
if (video.serialNumber != null || video.summaryMd) {
  const holder = idx.videos.find((v) =>
    (video.serialNumber != null && v.serialNumber === video.serialNumber) ||
    (video.summaryMd != null && v.summaryMd === video.summaryMd));
```

- the serial half needs the **receiver row** to carry a `serialNumber`;
- the key half is **byte equality**, which aliasing forms fail by construction.

The falsifier is named in that function's own comment, twelve lines above the guard
(`sync-run.ts:199-202`): *"A legacy receiver row carrying `003_alpha.md` with **NO** serialNumber —
exactly the shape `backfillOrder` exists to repair."* For such a row the serial half cannot fire (the
receiver's is `null`), and if the sender's key is the NFC form of the receiver's NFD one the key half
cannot fire either. `ensureReceiverSlot` does not throw, and execution reaches `putStaged` at `:263`.

**The residual still stays dissolved** — credential 1 (`video_id` in every produced body) carries the
conclusion on its own, and R2's read-back then refuses: `promoteIfAbsent` returns `already-exists`
through the alias, `tryGet` reads the occupant, hashes differ, REFUSE. So the *design* is safe. What is
wrong is the **sentence**, and this document has now had four universals falsified — *"every key any
entrance can produce is acceptable"*, *"no unservable class the mint path can produce"*, *"a strict
widening in every dimension"*, and this one. All four were written in the same voice as the measured
facts beside them.

**Fix.** Restate credential 2 with its scope: *"`ensureReceiverSlot` catches every aliasing collision
against a receiver row that carries a `serialNumber`; for a legacy no-serial row (`sync-run.ts:199-202`)
it does not, and R2's byte-comparison is what refuses there."* Then the credential says something true
and names the mechanism that actually covers the gap. If a stronger guard is wanted, the cheap version
is comparing `canonicallyEqualName(v.summaryMd, video.summaryMd)` in the `find` at `:206` instead of
`===` — one call, and it makes the key half alias-aware, which is what the sentence claims today.

---

## Low

**L1 — the C0 check misses C1.** `/[\x00-\x1f\x7f]/` rejects C0 and DEL. **MEASURED: 32 codepoints in
`\p{gc=Cc}` — U+0080–U+009F — are newly admitted** where the current guard rejects them. The
predicate's own docstring says it *"Rejects separators in every form, **control characters**,
traversal, and over-long keys."* Fix: `/[\x00-\x1f\x7f-\x9f]/`.

**L2 — the bidi rejection misses the bidi MARKS.** `[\u202a-\u202e\u2066-\u2069]` covers overrides and
isolates. **U+200E LRM, U+200F RLM and U+061C ALM are newly admitted** (measured). They carry the same
"renders as a different filename than it is" justification §3.4 gives for the overrides, and rejecting
them does not touch the ZWJ / variation-selector carve-out the spec correctly protects. Fix:
`[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]`. Low because the whole bidi item entered as a round-9
Codex Low.

**L3 — the share-path derivation count is wrong for the ninth time.** §3.4 says
`app/s/[token]/route.ts` derives `base` **twice**, `:69` and `:78`. There are **three**:
`:69` (md-download filename), `:78` (`readTitleStableModel`), and **`:112`** (the html `fileResponse`).
This is evidence *for* the chosen fix, not against it — putting the call inside `getShareServeContext`
covers all three by construction, which is the stated reason for choosing it. Fix the number, or
better, delete it: the sentence is stronger without a count.

**L4 — §7 still asserts a claim §3.4 retracted.** Risk row 2 reads *"v10 keeps the bound at 131, so the
guard is **a strict widening in every dimension** (round-9 H3)."* §3.4 retracts that sentence in bold
(*"Round 11 falsified that TWICE, independently — the claim is retracted, not repaired"*). The row's
**conclusion** is still right (the bound did not narrow, so no gate is needed), but §7 is the register
a security reviewer reads at the PR, and it is carrying the retracted universal verbatim.

**L5 — the §5 behaviors table is broken Markdown from row 20 onward.** The *"All fixtures with two
normalization forms…"* paragraph (lines 899-901) terminates the table; rows 20, 21, 23, 24, 25, 26, 27
and 22 that follow it render as literal pipe-delimited text, not table rows. §5 is the artifact Phase 3
implements from. Move the paragraph below the table (or after row 22).

**L6 — a required `BlobStore.promoteIfAbsent` breaks six test doubles, five loudly and one silently.**
Brief item 2, answered by enumeration. Compile errors (good, `tsc --noEmit` is in CI):
`tests/lib/storage/consistency.test.ts:38` (object literal typed `BlobStore`),
`tests/lib/model-store-cloud.test.ts:13`, `tests/lib/html-doc/serve-doc-mapping.test.ts:64`,
`tests/integration/serve-model-unreadable.test.ts:57`, `tests/integration/helpers/cloud.ts:168` and
`:191`. **The silent one:** `tests/lib/cloud-sync/additive-serial-coherence.test.ts:87-99` is a `Proxy`
returned behind an `as BlobStore` cast, whose `:96` special case names `promote` **by string literal**
because its argument is a `StagedRef` rather than a `Principal`. `promoteIfAbsent` takes the same
`StagedRef` and would fall through to the generic branch at `:97`, which calls
`remap(stagedRef)` → `path.join(cloudRoot, undefined)` → TypeError. It fails loudly at runtime, so this
is Low — but it is a cast escape, the thing `check-key-brand.py` existed to close before §3.5 deleted
it along with the brand. Worth one line in the implementation plan.

**L7 — "Nothing is widened" is this document's fifth universal, and it is false (harmlessly).** §3.4:
*"`..` stays rejected, `001_a．．b.md` stays rejected, and the B1 class is accepted. **Nothing is
widened.**"* Measured: **`003_a..md` is newly admitted** — a name ending in a **raw literal** `.`, so
the `..` is genuinely present in the key and is not something the guard manufactured. v13's
justification (*"the `..` exists only in a string the guard manufactured by folding"*) does not cover
it. It is harmless — `003_a.` is a legal POSIX component, `assertLogicalKey`'s segment test still
applies, and no traversal is possible — so this is a wrong sentence, not a defect. Same for
`a%252fb.md` (double-encoded; the encoder hashes any segment containing `%`, so no physical key can
carry it) and `.a.md`. Fix: *"the only keys newly admitted by dropping the fold at the joint are those
whose name ends in a dot; none can traverse."*

**L8 — behaviors 18/18b/18g/18h are "integration, real FS" and the FS is not the same everywhere.**
APFS's component limit is 255 **UTF-16 units** (measured: 131 Hangul code points / 387 bytes wrote
fine); ext4's is 255 **bytes**, so the same fixture is `ENAMETOOLONG` on Linux. These suites are not in
CI today (`dev-process.md` — *"Not yet in CI: `test:integration` and `test:e2e`"*), so nothing is red
right now; the note matters when they are wired in, and §3.6.2's alias measurements are per-volume
anyway, which R4 already says in its own warning box.

---

## Counts and attribution

| Severity | Count | IDs |
|---|---|---|
| Blocking | 0 | — |
| High | 2 | H1, H2 |
| Medium | 2 | M1, M2 |
| Low | 7 | L1–L8 (L-numbers 1-8, no L-blocking) |

| Finding | Caused by |
|---|---|
| H1 | §3.4 widening (v8) + §3.2 (v9) + behavior 16 — **not** §3.6, **not** the round-10 redesign |
| H2 | **v13's own fix** (§3.6.4 third residual — *"Decision: require it"*) |
| M1 | **v13's own fix** (`promoteIfAbsent`, new in v13) |
| M2 | **v13's own fix** (§3.6.4 credential 2, new in v13) |
| L1, L2, L7 | §3.4's predicate — the v12→v13 rewrite, first review |
| L3, L4, L5, L6, L8 | pre-existing / editorial |

**Escalation:** §3.6 produced findings caused by the previous round's fixes in round 11 **and** in
round 12. `review-method.md:45-49` fires on two consecutive rounds. Recording it as **2**, not resetting
it. My recommendation remains FIX: R1–R4's shape was attacked head-on this round — the no-clobber
property was measured true on both backends, the alias relation re-derived, `promote`'s caller set and
the `resolve.ts` hard-return confirmed — and all three §3.6 findings are about *which branch the rule
covers* and *which lines of the adapter change*, not about the mechanism being wrong.

NOT CONVERGED
