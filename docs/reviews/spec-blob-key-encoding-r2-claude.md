# Adversarial design review — cloud blob key encoding (backlog #36), round 2, Claude half

**Subject:** `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` (draft **v2**)
**Branch:** `fix/cloud-blob-key-encoding` @ `a7853eb`
**Reviewer:** Claude (round-2 Claude half). Not the author of the round-1 Claude review.
**Date:** 2026-08-14

**Verdict: NOT CONVERGED** — 2 Blocking, 1 High, 2 Medium, 1 Low.

Storage behaviour below is **measured** against the local stack (`http://127.0.0.1:54321`, `artifacts`
bucket, service role). The probe refused to run unless the host was `127.0.0.1`/`localhost` and removed
every object it wrote (verified: `residual under _probe36r2 : []`). Unicode facts were measured with
`node --version v22.14.0` over the full code-point range, not recalled.

**Round 1's ten findings: all ten are genuinely applied, not merely narrated.** I checked each against
the code it names, and H2's correction in particular (255/segment, no whole-path bound) reproduces
exactly. The `LIMIT = 255` choice is *better* than round 1's suggested 200 for the reason §3.2 gives —
see "Verified" below. So this review is entirely about what v2's own fixes introduced, and what both
round-1 reviewers missed.

---

## Summary of findings

| # | Sev | One line |
|---|---|---|
| B1 | **Blocking** | The slice makes a decomposed non-ASCII key **storable but not servable**: `assertCloudSummaryMdKey` rejects NFD accented Latin (measured), so the paid summary 409s at serve while sync reports success. Today the same input fails **loudly** at upload |
| B2 | **Blocking** | Behavior 16 — the sole falsifier for §3.5, the slice's highest-risk change — is made **vacuous by §3.5's own fix 3**, and the mutation §7 names ("remove NFC from `normalizeLogicalKey` → 16 red") **survives**. The scenario where fixes 1 and 2 are load-bearing has no behavior at all |
| H1 | High | §3.5 enumerates the comparison sites **by hand and the list is incomplete**. `remap` (`reconcile-serial.ts:117-137`) stays byte-exact and fails **closed** into a permanent per-video stranding; the occupancy `holder` check (`:193-196`) stays byte-exact and fails **open**, letting two videos' bases alias onto one physical object |
| M1 | Medium | §3.2.2's contract is false as a universal. `encodeSegment` branches on the **raw** segment but hashes **NFC(s)**, so the two equivalence relations §3.5 claims to have merged still differ. Measured: exactly one counterexample exists in all of Unicode (U+212A) |
| M2 | Medium | Encoding is defined per **segment**, but `list`/`deletePrefix` take an arbitrary string prefix. A prefix not ending on a segment boundary silently returns `[]` / deletes nothing — H3's failure class, re-entering through a door H3's fix left open |
| L1 | Low | §2.2's "255 **characters**" was measured with ASCII only, and `LIMIT` is compared against `String.length` (UTF-16 code units). Harmless — but only because `SAFE ⊂ ASCII`, which the spec never says |

---

## B1 — Blocking. After this slice a decomposed non-ASCII key is storable and **unservable**: the paid summary 409s, and sync reports success

### The measurement

`CLOUD_SUMMARY_MD_KEY` admits only `\p{L}` and `\p{N}` after the first character:

```ts
// lib/html-doc/assert-cloud-summary-md-key.ts:14
const CLOUD_SUMMARY_MD_KEY = /^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u;
```

A combining mark is `\p{Mn}` — neither. Measured:

```
'003_café.md'  NFC  len 11  passes  true
'003_café.md'  NFD  len 12  passes  FALSE
'0007_팔란티어-대체될까.md' NFC true / NFD true   (Hangul jamo are \p{Lo})
```

**So the guard admits one member of a canonical-equivalence class and rejects the other** — and the
rejected half is precisely the accented-Latin set §2.1 goes out of its way to promote to first class
(*"a `résumé` in a title destroys a paid summary identically"*). Korean, the case every behavior in §6
names, is the one script where the defect does **not** appear.

### The chain, end to end

1. §2.5 establishes as a load-bearing premise that a non-canonical normalization enters the index:
   `lib/pipeline.ts:135-138` reads raw `readdirSync` bytes and `:105` writes them in as `summaryMd`.
   B1 of round 1 was rated Blocking on exactly this reachability, so it is available here too.
2. `lib/cloud-sync/sync-run.ts:263` pushes that key verbatim into the cloud blob store, and `:279`
   writes it into the row: `sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } }`.
   `transferClassA` does the same at `:399`/`:430`.
3. Under **v2** the write now *succeeds*. `encodeSegment('003_café.md')`: not `SAFE`,
   `head = '003_cafe'`, `ext = '.md'` → `003_cafe=h<22>.md`. Measured accepted (`=h` leading, with
   extension → ACCEPT).
4. Serve:

```ts
// lib/html-doc/serve-summary-core.ts:56-64
const mdKey = artifact?.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
if (!mdKey) return { ok: false, status: 404, error: 'not found' };
try { assertCloudSummaryMdKey(mdKey); }
catch { return { ok: false, status: 409, error: 'corrupt summary key' }; }
```

→ **409 `corrupt summary key`.** `lib/dig/cloud/resolve-summary-key.ts:16` returns `null` for the same
key, so the dig path treats the video as having no summary at all.

### Why this is a regression the slice introduces, not one it fails to fix

Measured today: `upload('003_café.md')` → `REJECT 400 Invalid key`. So on master the sync **throws**
at `putStaged`, the row is never written, and the failure lands in `report.errors`. After this slice the
same input produces a durable row advertising `status: 'promoted'`, a real object in the bucket, real
Gemini spend, and a 409 the user only discovers by opening the document. **The slice converts a loud
failure into a silent paid-but-unreachable summary** — which is the exact shape of backlog #36 itself.

§3.6 asserts the opposite in one line:

> The three Unicode-aware guards (§5) — still correct; they validate *logical* keys.

That is the claim this finding falsifies. §3.2.2 newly declares that *"canonically-equivalent logical
keys are … the same logical key"*; §5's guards do not implement that relation, and §3.6 never checks.
§9's totality argument has the same seam: *"every logical key produces an accepted physical key"* is a
property of the **storage** map, and the observable promise (behavior 14: "the summary is **readable**")
depends on a second boundary the spec declares unchanged.

### Fix

Canonicalize the key **where it enters the cloud record**, so the DB holds the canonical representative
of the class the seam already identifies: NFC the `summaryMd` key in `sanitizeAdditiveVideo` /
`transferClassA` (`sync-run.ts:263`, `:279`, `:399`, `:430`) and in the worker persist. As a belt, have
`assertCloudSummaryMdKey` test `mdKey.normalize('NFC')` so an already-stored row is servable. Both are
consistent with §3.5's own principle; neither touches the vault (§1 decision 1 — the vault filename is
not what changes here).

**What observation would make this FAIL?** Integration test: sync a video whose `summaryMd` is
`003_café.md` in **NFD**, then `GET` the summary and assert 200 with the right bytes, and assert the
ledger did not move. Against v2 as written it returns **409**. Add the accented-Latin NFD case to
behaviors 14 and 15 — every language-specific behavior in §6 currently says "Korean", which is the one
script that cannot expose this.

---

## B2 — Blocking. §3.5's fix 3 makes behavior 16 vacuous, and the mutation §7 names to prove otherwise survives

§10 states, correctly, that §3.5 is the highest-risk part of the slice, and names its entire mitigation:

> | §3.5 changes key *equality* on two money paths | Behavior 16 + the comparison-agreement test; mutation-checked |

Behavior 16 is *"Relocating a base that differs from local's only by normalization loses nothing"*, and
§6 calls it "the B1 falsifier". **Under v2 that relocation cannot happen.** §3.5 fix 3 changes
`describeDivergence` to compare NFC-normalized bases, and `reconcileCloudBase` gates everything on it:

```ts
// lib/cloud-sync/reconcile-serial.ts:183-184
const d = describeDivergence(localVideo, cloudVideo);
if (!d.diverged) return { ok: true, action: 'agreed' };
```

For a base that differs *only* by normalization, fix 3 returns `diverged: false`, so the function
returns at `:184`. `paidKeysUnder` (`:254`), the plan and its collision Set (`:261-278`), the copy loop
(`:281-290`) and the cleanup loop (`:357-361`) never execute. Behavior 16 will observe
`action: 'agreed'`, zero copies, zero deletes, an unmoved ledger — and pass, having exercised **none of
fixes 1, 2 or 4**.

The mutation §7 prescribes therefore does not kill it:

> Remove NFC from `normalizeLogicalKey` and behavior 16 must go red.

With fix 3 in place, removing NFC from `normalizeLogicalKey` changes nothing observable in behavior 16 —
`copyBlob` is never called. Per this project's own rule, a guard whose mutation survives is untested, and
untested is indistinguishable from does-nothing. The one artifact offered as proof that round 1's
Blocking is fixed proves nothing about the three sites that would have to catch it.

### Fixes 1 and 2 are not redundant — there is a reachable case, and it has no behavior

I looked for a plan pair `{from, to}` that is byte-different but canonically equal while the bases
themselves diverge. `remap` produces one, because the `digDeeperMd` branch rewrites the **basename** and
preserves the **directory**:

```ts
// lib/cloud-sync/reconcile-serial.ts:133-137
if (path.posix.basename(key) === `${path.posix.basename(oldBase)}-dig-deeper.md`) {
  const dir = path.posix.dirname(key);
  const moved = `${path.posix.basename(newBase)}-dig-deeper.md`;
  return dir === '.' ? moved : `${dir}/${moved}`;
}
```

Take cloud `summaryMd = 'raw/003_café(NFD).md'` and local `summaryMd = '003_café(NFC).md'` — the `raw/`
layout is real and supported, per the comment at `:128-131`. Then
`NFC(oldBase) = 'raw/003_café' ≠ '003_café' = NFC(newBase)`, so the video **is** diverged and the copy
phase runs. For `digDeeperMd = 'raw/003_café(NFD)-dig-deeper.md'`, `remap` yields
`to = 'raw/003_café(NFC)-dig-deeper.md'` — **byte-different from `from`, canonically equal to it, and the
same physical object under the encoder.**

- With fixes 1 + 2: `copyBlob` short-circuits `{ok: true, already: true}` before any I/O, cleanup skips.
  Correct.
- Without them (i.e. under the mutation): `copyBlob` reads the same object twice, `dst.bytes.equals(src.bytes)`
  is trivially true (`blob-store.ts:147-148`), metadata advances with `patch.digDeeperMd = to` (`:306`),
  and cleanup at `:358-360` sees `to !== from` and **deletes the object the row now points at** — the paid
  dig-deeper markdown, which `paidKeysUnder`'s comment at `:94` exists specifically to protect.

That is B1 intact, one artifact narrower. It is the case behavior 16 must cover, and behavior 16 as
written is the one case fix 3 removes.

### Fix

Restate behavior 16 as the scenario above (bases diverge by **more** than normalization; a remapped pair
within the plan is canonically equal but byte-different), assert the dig-deeper blob still reads and the
ledger did not move, and keep the ledger assertion on the M3.1-A pattern. Then correct §7's mutation
list: "remove NFC from `normalizeLogicalKey`" must go red on **that** behavior, and add a second
mutation — "remove NFC from `describeDivergence`" — with its own behavior asserting a normalization-only
divergence reports `agreed` and performs no I/O. Two fixes, two mutations, two behaviors; today three
fixes share one behavior that reaches none of them.

Note the interaction with B1: the natural fix for B1 (canonicalize the key entering the cloud record)
makes normalization-only divergence rarer, and any future decision to have `describeDivergence` report
it again re-arms this path with fixes 1 and 2 as the only guard. They must be independently proven now.

---

## H1 — High. §3.5 enumerates the comparison sites by hand, and the enumeration is incomplete

§3.5's fix is "**Four sites**". `reconcile-serial.ts` contains at least three more comparisons that ask
the same question — "are these two keys the same?" — and stay byte-exact.

**(a) `remap`, and it fails CLOSED into a permanent stranding.** `reconcile-serial.ts:117-137` compares
with `===`, `startsWith` and `path.posix.basename(...) === ...`. If a row's `digDeeperMd` is in a
different normalization from its own `summaryMd` — reachable by the same §2.5 mechanism, since
`digDeeperMd` is derived from `path.basename(summaryMdName)` at generation time while `summaryMd` can
later be replaced by a `readdirSync` form — then:

```ts
// reconcile-serial.ts:264-265
const to = remap(from, oldBase, newBase);
if (to == null) return { ok: false, reason: 'unmappable-key', key: from };
```

`unmappable-key` propagates to `sync-run.ts:756-757`, which **throws**, and no baseline is advanced. The
video errors on **every** run, forever, with no exit but hand-editing the index — the "stranded on every
run" outcome the M-R2-2 comment at `sync-run.ts:690-693` was written to prevent.

**(b) The occupancy guard, and it fails OPEN.**

```ts
// reconcile-serial.ts:193-196
const holder = cloudIndex.find((v) =>
  v.id !== cloudVideo.id &&
  (v.serialNumber === localVideo.serialNumber ||
    (v.summaryMd != null && baseOf(v.summaryMd) === newBase)));
```

Once the seam identifies canonically-equivalent bases, another cloud video holding the NFD form of
`newBase` occupies the **same physical address space** and this check does not see it, so
`target-occupied` is not returned and the relocation proceeds. `copyBlob` then fails closed with
`destination-exists` (`blob-store.ts:149`) — so this is a stranding rather than a loss — but the refusal
arrives as `copy-failed` at an arbitrary key instead of the actionable `serial collision: … held by …`
message the guard exists to produce, and the guard's stated purpose ("it stops `transferClassA` writing
the winner's key onto this row, which is the write that does the orphaning", `:188-192`) is no longer
guaranteed to fire before that write.

**(c) `paidKeysUnder`'s prefix** (`:102`, `` blob.list(p, `dig/${base}/`) ``) is built from the cloud
row's exact bytes. Correct *because* the new `list()` re-attaches the caller's own logical prefix, but
that is now a load-bearing coupling between §3.3 and this line, and it is written down nowhere.

There is one more outside this file: `sync-run.ts:206`,
`(video.summaryMd != null && v.summaryMd === video.summaryMd)` in the additive serial-collision check.

**Fix.** Stop enumerating. Export one canonicalization from the seam — the same function the encoder
uses to decide equality — and route every key comparison in `reconcile-serial.ts` and `sync-run.ts`
through it. Then add a `scripts/check-*.py` in the shape this repo already uses (e.g.
`check-vocabulary-collisions.py`): fail if a `===`, `!==`, `startsWith` or `Set<string>` in
`lib/cloud-sync/` has a `summaryMd`/`base`/`Key`-named operand and is not wrapped in that function.
**What observation would make it FAIL?** Add a raw `cv.summaryMd === lv.summaryMd` to
`reconcile-serial.ts` and the script must go red. A hand-written list of four sites is not a guard; it is
a snapshot that the next person to add a comparison will not read.

---

## M1 — Medium. §3.2.2's contract is false as a universal: the encoder branches on the raw segment but hashes the NFC one

§3.2.2 states:

> The encoder is injective **on NFC-normalized logical keys**. Canonically-equivalent logical keys are
> deliberately identified, and the seam treats them as *the same logical key* everywhere.

The encoder does not implement that. §3.2's pseudocode tests `SAFE.test(s)` on the **raw** `s` and hashes
`NFC(s)`. So a segment whose raw form is not `SAFE` but whose NFC form **is** takes the hash branch,
while its canonical equal takes the identity branch — two physical objects for one logical key, in
contradiction of the sentence above and of §3.5's headline ("One equivalence relation, not two").

**Measured, exhaustively.** I scanned every code point U+0080–U+10FFFF (surrogates skipped) for
`NFC(ch)` matching `^[A-Za-z0-9._-]+$`:

```
FULL SCAN non-ASCII whose NFC is SAFE-ASCII: [["212a","K"]]     // U+212A KELVIN SIGN → 'K'
SAFE ascii changed by NFC: 0
```

Exactly one: U+212A (canonical singleton decomposition to U+004B). So `003_K.md` with U+212A hashes,
`003_K.md` with ASCII `K` is identity — and after §3.5 fix 1, `normalizeLogicalKey` calls them **equal**,
which means `copyBlob`'s short-circuit at `blob-store.ts:134` returns `{ok: true, already: true}` for a
copy that never happened and a destination that does not exist. That is B1's failure mode with the
operands swapped, introduced by B1's fix.

**Reachability is low and I am stating it honestly:** `slugify` lowercases first, and
`'K'.toLowerCase()` is ASCII `'k'` (measured), so `lib/slugify.ts` can never emit U+212A; the only
entrance is a verbatim sender key (`sync-run.ts:263`) from a vault filename that did not come from
`slugify`. Medium, not Blocking, for that reason.

**Fix, one line:** canonicalize before branching — `const n = NFC(s); if (SAFE.test(n) && n.length <= LIMIT) return n;` —
and hash `n`. Then `normalizeLogicalKey`'s NFC equality and the encoder's physical equality are the same
relation by construction rather than by coincidence, which is what §3.5 claims. Behavior 1 restates to
"a **NFC-normalized** `SAFE` key ≤ `LIMIT` encodes to itself, byte-identically", and §4's proof is
unaffected (every existing bucket segment is ASCII, and NFC is the identity on ASCII — measured above).
This is also what makes §7's "comparison-agreement test" writable as an actual property rather than a
pair of examples.

---

## M2 — Medium. Encoding is per **segment**; `list` and `deletePrefix` take an arbitrary string prefix, and the mismatch fails silently

§3.2 defines the encoder "per **non-empty path segment**" and §3.3 says `list(p, prefix)` should "encode
the prefix". Neither states the precondition that a prefix must end on a segment boundary. The interface
does not require it:

```ts
// lib/storage/blob-store.ts:78-79
/** List logical keys (relative to the owner root) under a prefix. Absent prefix → []. */
list(p: Principal, prefix: string): Promise<string[]>;
```

A caller passing `dig/003_` — a legitimate prefix under the current implementation, which does plain
string concatenation at `supabase-blob-store.ts:143` — gets `003_` encoded as a whole segment, producing
a physical path that matches nothing. Measured, both failure modes are silent: `list` of an absent folder
returns `[]` with no error, and `remove` of an absent object reports success (round 1 H3 measured this;
I did not re-measure it).

Unreachable today — I re-verified the caller set myself rather than inheriting it:

```
lib/cloud-sync/reconcile-serial.ts:102        blob.list(p, `dig/${base}/`)
lib/dig/cloud/load-dig-for-serve.ts:34        blobStore.list(principal, prefix)      // `dig/${base}/`
app/api/videos/[id]/dig-state/route.ts:47     blobStore.list(principal, `dig/${base}/`)
app/api/playlists/[id]/route.ts:79            blobStore.deletePrefix(principal, '')
```

All four are segment-aligned. But that is the identical argument §3.3 gives for why its own marker guard
must throw rather than be omitted — *"Unreachable today … which is why it must be loud if it ever becomes
reachable"* — and this door was left open by H3's fix, which specified the empty-segment case and stopped
there.

**Fix.** State the precondition in §3.2/§3.4 and enforce it: a prefix must be `''` or end at a segment
boundary; anything else **throws**. Add to §6: "`list(p, 'dig/003_')` throws rather than returning `[]`".
Mutation: remove the boundary check and that behavior must go red.

---

## L1 — Low. "255 characters" was measured with ASCII only, and `LIMIT` is compared against `String.length`

§2.2's ceiling reproduces exactly on my probe (`seg 255 → ACCEPT`, `seg 256 → REJECT 500`,
`4 segs × 250 → ACCEPT`), but every test string was ASCII, and §3.2 compares `s.length` — UTF-16 code
units — against it. Whether storage-api counts characters, UTF-16 units or bytes is untested and the
spec presents "255 characters" as settled.

It does not matter, but only for a reason the spec never states: `SAFE ⊆ ASCII`, so the identity branch
is only ever reached by segments where characters, code units and bytes coincide, and the hash branch
emits ASCII with a 65-character worst case. Add that sentence to §3.2, and label §2.2's unit as
"measured for ASCII segments". Also worth pairing with §10's existing risk row about prod's storage-api
version: the design is insensitive, so the risk is that someone later reuses `LIMIT` as a general
character bound.

---

## Verified — checked by hand, not conceded

- **`LIMIT = 255` is sound, and better than round 1's 200.** The identity branch's length condition must
  be at least as wide as every logical key the system admits; `CLOUD_SUMMARY_MD_KEY` admits 131 and
  `assertLogicalKey` (`blob-store.ts:87-91`) bounds nothing. At 255 the set `{SAFE ∧ len > LIMIT}` is
  empty **among storable keys**, because a 256-character segment is rejected at upload (measured), so
  §4's length half really is vacuous rather than merely unlikely. Round 1's 200 would have left a
  55-character band of ASCII keys that Storage accepts and the encoder would re-address. §3.2 is right
  to have overridden the reviewer's number.
- **`normalizeLogicalKey` has exactly one caller today** — `copyBlob` at `blob-store.ts:134`
  (`grep -rn normalizeLogicalKey` over the whole repo returns only its definition and that line). §3.5
  fix 1's blast radius is genuinely small; the risk is M1's, not a hidden consumer's.
- **§3.2.1's empty-segment rule is consistent with what Storage actually does.** Measured:
  `dbl/a//b`, `dbl/a/./b` and `tsl/x/` all upload with `ACCEPT`, and then
  `list('_probe36r2/dbl') → [["a","DIR"]]`, `list('_probe36r2/dbl/a') → [["b","file"]]`, with
  `download('dbl/a//b')` and `download('dbl/a/b')` both `OK` and cleanup removing 6 of the 9 paths
  requested — i.e. Storage collapses empty and `.` segments, so `storage.objects.name` can never contain
  one. That makes both the pass-through rule and §4's per-segment `+` predicate safe, and it means
  `normalizeLogicalKey`'s existing empty/`.` filtering does **not** disagree with the physical map. I
  expected a finding here and did not get one.
- **§2.1's marker rows.** Measured: `003_=hJ8kQ2mAbCdEfGhIjKlMnO.md` ACCEPT, and `=hJ8kQ2m…` as a
  **folder** segment ACCEPT. `003_café.md` (NFC) REJECT `400 Invalid key`.
- **ADR-0008's money guard survives.** `objectKey` encodes only `key`
  (`supabase-blob-store.ts:15-18`), so the MD physical key `<owner>/<pl>/003_=hX.md` and the model
  physical key `<owner>/<pl>/models/=hY.json` stay under the same first path segment, which is where the
  grant sits (`serve-doc.ts:100-106`). The corroboration ordering the comment describes is untouched.
- **§3.2.2's "related keys hash independently" note is necessary and correct.** `MODEL_KEY`
  (`model-store.ts:31`) builds `models/${base}.json`, whose non-ASCII segment is `${base}.json` — a
  different string from `${base}.md`, hence a different hash. Nothing in `remap`, `MODEL_KEY` or
  `pdfRelPath` derives one physical key from another.
- **Behavior 16 would genuinely fail against v1.** Under v1, `describeDivergence` is byte-exact →
  diverged → `copyBlob`'s short-circuit does not fire → both `tryGet`s hit one physical object →
  `already: true` → metadata advances → `to !== from` → `delete(from)` → `get(newKey)` returns null. The
  spec's claim about v1 is right. B2 is about the other half of the question: it does not pass against v2
  for the right reason.
- **§4.1's "the gate cannot run" is correctly recorded** and correctly does not block writing the plan.

## What I checked that would have found a defect of each class, and what I did not

- *Aliasing / equivalence-relation splits* (B1's class): enumerated every `normalizeLogicalKey` caller;
  read every key comparison in `reconcile-serial.ts` and the relevant span of `sync-run.ts`; scanned all
  of Unicode for a branch-vs-hash disagreement (M1). Found H1 and M1.
- *Silent no-ops* (H3's class): re-derived the caller set for `list`/`deletePrefix` from source rather
  than from the spec's table; measured Storage's `//`, `/./` and trailing-slash behaviour. Found M2.
- *Numbers attributed to the wrong subject* (H2's class): re-measured the 255/256 boundary and the `=`
  marker rows myself. Both reproduce. Found L1.
- *Guards that cannot fail*: traced behavior 16 through `reconcileCloudBase` statement by statement and
  asked what the named mutation would change. Found B2.
- **Not checked:** the §4 gate against a real bucket (still blocked — `claude_ro` cannot read schema
  `storage`, §4.1), and anything about prod's storage-api version. Both are honestly recorded in §10.

---

## Verdict

**NOT CONVERGED**

B1 and B2 are the two halves of the same omission: v2 fixed the *storage* seam thoroughly and treated the
boundary above it (`assertCloudSummaryMdKey`) and the *evidence* below it (behavior 16) as unchanged. The
result is a slice that would ship a paid summary which stores fine and cannot be served, with a falsifier
that passes because the code path it names no longer runs.
