# Cloud blob keys — encode at the storage seam so a title in any language can be stored (backlog #36)

**Status:** draft **v10**, awaiting user approval. **Branch:** `fix/cloud-blob-key-encoding`.
**Origin:** backlog **#36** 🔴, found 2026-08-12 by the first real M3 acceptance run against prod v6.

**Review trail — nine dual rounds plus a Phase 6 architecture review.**
`docs/reviews/spec-blob-key-encoding-r{1..9}-{codex,claude}.md`,
`docs/reviews/architecture-review-2026-08-14.md`.

> ## ⛔ §3.6 IS ESCALATED FROM FIX TO REDESIGN — read this before reviewing it (round-9 M5)
>
> `review-method.md:45-49`: *"if a component produces findings caused by the PREVIOUS round's fixes in
> two consecutive rounds, it escalates from FIX to REDESIGN, and the next round is a design review —
> not another defect hunt."*
>
> | Round | Finding in §3.6 | Caused by |
> |---|---|---|
> | 6 | M1 — the guard must pin ordering | the original check-then-write |
> | 7 | Blocking 1 — a **second** vault writer the guard must cover | round-6's guard |
> | 8 | H1 — the rule contradicts the code it governs; M4 — ordering unresolvable | round-7's two-writer note |
> | 9 | H1, H2, M4 | **round-8's two-writer table and its `wx` choice** |
>
> **The condition fired at round 8 and nothing acted on it** — which is the exact failure the
> retrospective that produced the rule describes (`blob-addressing-retrospective-2026-08-09.md`): *"the
> evidence was already being collected and no rule acted on it."* Every §3.6 fix below is applied on
> its merits and each has a **measured** primitive behind it, but **the next §3.6 pass is a design
> review of the vault write protocol** — who the writers are, what identity each carries, which
> coordination pattern this is — not another defect hunt.
>
> **§3.1–§3.5 have converged and stayed converged.** Both round-9 halves say so independently, and the
> Claude half is explicit: *"If §3.6 did not exist I would say CONVERGED."* Do not let §3.6's churn
> re-open them.

> **v8 is much smaller than v2–v7, because a premise they all shared was false.** The user asked, on
> reading v7: *"why does the cloud need ASCII-servable?"* It does not. Two separable constraints had
> been welded into one word:
>
> | Constraint | Real? | Met by |
> |---|---|---|
> | **Storable** — Supabase rejects non-ASCII object keys | Yes, external, measured | **The encoder, completely** — the physical key is hashed ASCII, so the logical key may be anything |
> | **A single path component** — no `/`, `%2f`, `／`, control chars, not over-long | Yes, ours | A **denylist**. Nothing to do with ASCII, letters, or readability |
>
> Everything v3–v7 built — the repair, the refusal, the `videoId` fallback, the branded type, the
> manufactured divergence — existed to serve the second constraint *as if it were the first*. §3.4
> replaces it with the check the guard's own docstring says it wanted, and all of that machinery is
> **deleted**.

---

## 1. Purpose and premises

Make a video title in any language storable **and servable** in the cloud, without changing vault
filenames and without migrating anything in the bucket.

**User decisions (2026-08-14), not reopened:** ① the vault wins — local filenames keep their Unicode;
② no refund, no ledger reconciliation — the ~156¢ stays recorded; ③ **an unreadable vault filename is
not acceptable**, which is what surfaced the false premise above.

### 1.1 Premises this design rests on

Each is labelled by **how it was established**, and each carries the observation that would falsify it.
Seven rounds were spent on premises that were stated as facts, so they are now stated as premises.

| # | Premise | Provenance | Falsified by |
|---|---|---|---|
| P1 | Storage rejects every non-ASCII object key | **MEASURED** (§2.1, 3 rounds) | any non-ASCII key uploading `ok` |
| P2 | Storage's limit is 255 per path **segment**, not per path | **MEASURED** (§2.2, re-derived twice) | a path >255 total with all segments ≤255 being *rejected* |
| P3 | Every **write** reaches Storage through `SupabaseBlobStore` | **QUOTED** — the only non-test **write** call site is `supabase-blob-store.ts:20` | a second non-test **write** call site |
| P4 | `list()` never needs to invert the encoding | **QUOTED** — all 3 callers pass `dig/${base}/` and read `{sectionId}.r{V}.md` leaves | a caller consuming a leaf it did not supply the prefix for |
| P5 | The serve guard's requirement is *single path component*, not ASCII | **QUOTED** — its own docstring; and it has exactly 2 callers | a downstream consumer that breaks on a non-ASCII but separator-free key |
| P6 | No URL is built from the key | **MEASURED** (grep, §3.4) — the only URI from a filename is the local Obsidian link, already `encodeURIComponent`'d | a URL built by string interpolation from `summaryMd`/`base` |
| P7 | The key reaching HTML is escaped | **QUOTED** — `render.ts:106`, `:114`, both via `esc()` | an unescaped interpolation |
| P8 | A vault filename is always a single path component | **Structural** — POSIX forbids `/` in a component | n/a |

> **Round-9 L1 — P3's falsifier was met, and the premise still holds.** There *is* a second
> `client.storage.from(` outside tests: `scratchpad/b3-raw.ts:22`, a gitignored (`.gitignore:68`)
> read-only ops script that only `download`s. So the premise as *meant* ("every write") is true and the
> premise as *written* ("the only call site") was false. Recorded rather than quietly reworded, because
> the falsifier column did its job: it is the first row in this table to fire.

---

## 2. What was measured

Probes ran against the **local** stack only; each refuses to run unless the URL is
`127.0.0.1`/`localhost`, and cleans up.

**2.1 Charset.** Accepted: ASCII alphanumerics, `-`, `_`, `.`, **space**, `(`, `)`, `+`, `=`, leading
`=`. Rejected `400 InvalidKey`: **every non-ASCII letter** — Hangul, Japanese, Cyrillic, accented Latin
(`café` in *both* NFC and NFD) — plus emoji, `~`, `%`. The defect is far wider than "Korean".

**2.2 Length: 255 per path SEGMENT.** No whole-path bound to at least 1216 (a 1014-char path is
accepted; a 267-char path with one 256-char segment is rejected). Over-length returns **`500`**, not
`400` — indistinguishable from a transient fault.

> ⚠ v1 reported "267, whole path": a 12-char prefix plus a 255-char segment. The probe varied one
> segment under a fixed prefix, so **no outcome of it could distinguish the two hypotheses**.

**2.3 Reversible encoding was available** (base64url of a worst-case Hangul slug is 247 of 255) —
declined on merits (§6.1), not impossible as v1 claimed.

**2.4 The local side.** `LocalFsBlobStore.abs()` is `path.join(indexKey, key)` — identity. APFS aliases
NFC/NFD (`wx` → `EEXIST`; `rename` overwrites). Raw `readdirSync` bytes enter the index as `summaryMd`
(`pipeline.ts:135-138`, `:105`).

**2.5 Four write entrances.** `slugify` runs on exactly one; the other three take a key verbatim:
worker mint (`summary-handler.ts:96`), additive create (`sync-run.ts:263`), Class-A transfer
(`sync-run.ts:379-399`), base reconciliation (`reconcile-serial.ts:282`/`:293`). The spec named 1, 1,
1, 1, 2, 3 across six rounds — see §3.4 for why that no longer matters.

---

## 3. The design

### 3.1 Encode at the seam

`SupabaseBlobStore` maps **logical** keys to **physical** ones; `LocalFsBlobStore` and
`InMemoryBlobStore` are identity. The interface already speaks of logical keys.

### 3.2 The encoder

Per **non-empty** segment; empty segments pass through, so a trailing `/` survives and `''` → `''`.
`list`/`deletePrefix` throw on a prefix not ending on a segment boundary.

```
SAFE = /^[A-Za-z0-9._-]+$/     LIMIT = 255      // the measured ceiling (P2)

encodeSegment(s):
  if s === '':                            return ''
  if SAFE.test(s) && s.length <= LIMIT:   return s
  head = leading [A-Za-z0-9._-] run of s, truncated to 32
  ext  = trailing /\.[A-Za-z0-9]{1,8}$/ of s, else ''
  return `${head}=h${base64url(sha256(utf16le(s))).slice(0, 22)}${ext}`
```

**`utf16le`, not `utf8`** — Node maps every unpaired surrogate to U+FFFD, so two different lone
surrogates hash identically. Reachable: `slugify`'s `.slice(0, 60)` cuts UTF-16 code units, so an
astral letter at the boundary yields a lone surrogate.

**Contract:** total; bounded (65 chars); and **injective on the identity branch, collision-*resistant*
on the hash branch** — the two branches are provably disjoint because `=` ∉ `SAFE`, but 22 base64url
characters is a 132-bit truncation of SHA-256, not an injection (round-9 L6; task #96 recorded this
overclaim and v9 still stated it flat).
No opinion about Unicode — NFC and NFD are different keys naming different objects. `SAFE ⊂ ASCII`, so
`String.length` is sound. `=` is the marker: Storage accepts it and `slugify` cannot emit it.

### 3.3 `list()` re-attaches the caller's prefix (P4)

Encode the prefix, enumerate, strip the **physical** prefix, prepend the **logical** one. No inversion,
which is what makes a hash legal. The `=h` marker guard applies to the **physical remainder only** —
never the caller's own prefix, or a logical key legitimately containing `=` strands a video every run.

### 3.4 The serve guard asserts what it actually requires — and that is the whole fix

`CLOUD_SUMMARY_MD_KEY` allowlists `[\p{L}\p{N}_-]`. Its docstring states the requirement plainly: the
key must be **a single path component**, so that `models/{base}.json` and `pdfs/{base}.pdf` are safe —
rejecting `nested/foo.md`, `%2f`, `／`, control characters, over-long. It says the allowlist was chosen
because *"`slugify` … never emits anything outside the allowed class"* — true when written, retired by
sync (Phase 6 safety-argument **d**).

**Replace the allowlist with the requirement — as a PREDICATE, not a regex:**

```ts
/** A single path component. Rejects separators in every form, control characters,
 *  traversal, and over-long keys. Says nothing about ASCII, letters, or readability. */
export function isServableSummaryKey(key: string): boolean {
  // 131 = the CURRENT guard's ceiling, preserved deliberately — see the bound note below.
  if (key.length <= 3 || key.length > 131 || !key.endsWith('.md')) return false;
  // Check the RAW form and the compatibility-FOLDED form. `℀` folds to `a/c`, `＼` to `\`,
  // `．．` to `..`. A hand-typed homoglyph denylist cannot be complete; NFKC closes that class.
  for (const s of [key, key.normalize('NFKC')]) {
    if (s.includes('/') || s.includes('\\') || s.includes('..')) return false;
    if (/[\x00-\x1f\x7f]/.test(s)) return false;         // C0 + DEL
    if (/%2f|%5c/i.test(s)) return false;                // percent-encoded separators
    if (/[\u202a-\u202e\u2066-\u2069]/.test(s)) return false;  // bidi overrides/isolates
  }
  return true;
}
```

> **The length bound — round-9 H3, and it is the only place v9 was NARROWER than the code it replaces.**
> Measured across the entire codepoint space, the current guard
> (`/^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u`, total length **4–131**) and v9's predicate (total
> **4–128**) differed in exactly one respect: **total lengths 129, 130 and 131 are served today and
> would have 409'd after the change.** No character was newly rejected.
>
> Worse, **the §4 pre-deploy gate could not have seen it** — its predicate is a character class with no
> length term, and §7's risk row was charset-only. The one mechanism whose entire job is *"no existing
> key breaks"* was silent on the only way this change could break one.
>
> Fixed by keeping the bound at **131**, which makes the guard a **strict widening in every
> dimension** — the property §3.4 always claimed and did not have. A behaviour that is a strict
> widening needs no migration argument at all, which is worth more than three characters of tidiness.

> **Bidi controls — round-9 Codex Low.** `001_safe\u202Efdp.md` passed v9: it is not a separator, not
> traversal, and no normal form of it becomes one, so the sweep below is still correct. But it renders
> as a different filename than it is, and this key becomes a **vault filename** on the cloud→local
> path. Rejected specifically — **not** all of `Cf`, because ZWJ and variation selectors are load-bearing
> in legitimate emoji titles, which the encoder must keep supporting.

> **⚠ Precision on "NFKC closes the class" — round-9 L3.** True for the *folding* homoglyphs. It is a
> **narrowing** for `⁄` (U+2044) and `∕` (U+2215), whose NFKC forms are themselves, so both are
> admitted where v8's hand-written denylist named them. That is correct on the merits — the full sweep
> found no normal form of either containing `/` — but do not read completeness into the word "closes".

> ⚠ **v8 wrote this as a regex, and the regex was INVERTED — round-8 B1.** In
> `[^/\\ -／⁄∕]`, the `-` between `\\` and `／` is a **range** (`U+005C`–`U+FF0F`), not a literal. The
> negated class therefore **rejected every existing key and admitted only control characters** — the
> exact inverse of its purpose, in the one line carrying the whole security argument.
>
> Same footgun class as a backtick inside a double-quoted shell string, which has bitten this repo
> twice: **a character whose meaning changes with its position, in a context where it reads as a
> literal.**
>
> **And v9 shipped a third instance of the class in the very same line** (fixed here): the C0 check
> was written with **raw control bytes** in the file rather than `\x00`-`\x1f` escapes, so it rendered
> as `/[ -]/` — a two-character class that any reader, or any copy-paste into the implementation,
> would have taken at face value. Invisible characters and position-sensitive ones fail identically:
> **the source does not show what it means.** Character classes in this spec are written with escapes
> only.
>
> It is a predicate now for two reasons, not one. The bug lived in the character class; and a
> hand-typed homoglyph list **cannot be complete** — round-8 Codex measured `U+2100 ℀ → a/c`,
> `U+2101 ℁`, `U+2105 ℅`, `U+2106 ℆`, `U+FE68 ﹨`, `U+FF3C ＼`, plus the dot-folds `U+2024`, `U+FE52`,
> `U+FF0E` (so `001_a．．b.md` folds to `001_a..b.md`), and the Claude half independently found the
> list missed **6 of the 7**. Folding with NFKC and checking **both** forms closes the class instead
> of enumerating it — the same lesson the write entrances taught.

Then a Korean, Japanese, accented, spaced or emoji title all pass — they are single path components,
and the encoder makes them storable. `nested/foo.md`, `001_a．．b.md` and `℀.md` all fail.

> **⚠ Precision — round-8 M1. This is NOT "the whole fix" for the headline case.** Korean
> **already passes** the current allowlist, because Hangul is `\p{L}`. What the widening admits is
> **NFD accented Latin** (combining marks are `\p{Mn}`), spaces, and emoji. The Korean case is fixed
> by the **encoder** (§3.2); the guard fixes a different, adjacent set. v8 stated both in one sentence
> — the same conflation, in miniature, that this whole version exists to undo.

**Why local was always fine, and what this proves.** The identical derived-key construction runs on the
local path — `MODEL_KEY(base)` at `reconcile-serial.ts:98`/`:118` and `serve-doc.ts:114`, `pdfRelPath`
at `app/api/videos/[id]/pdf/route.ts:84`, all shared code — with **no allowlist**, full of Korean
filenames, for the app's entire life. The allowlist was an over-approximation, free when `slugify` was
the only producer.

**What protects each side — named per path, because round-8 M5 and round-9 M3 both caught this
sentence crediting the wrong one.** They are *not* the same backstop:

| Path | Backstop | Where |
|---|---|---|
| **Cloud** serve | `assertLogicalKey` only | `blob-store.ts:87-91` — rejects a leading `/`, a `..` segment, `\0` |
| **Local** pipeline | `assertIndexRelPathWithin` (resolved-path containment) | `build-doc-html.ts:77`, `:104`, `:105`; `rerender.ts:50`; `pdf/route.ts:85` |

The containment check is a **local-filesystem** guard and is not on the cloud serve path at all. Saying
so plainly matters because §7 asks for a security reviewer at the PR, and previous drafts sent that
reviewer looking for a backstop that is not there.

**And the guard is not uniform — round-8 Codex Medium, round-9 Codex M1 and L2.** `lib/share/serve.ts:47`
returns `mdKey` with **no** guard call, and `app/s/[token]/route.ts:78` then derives
`const base = ctx.mdKey.replace(/\.md$/, '')` — exactly the derivation the guard's docstring calls
itself "the hard boundary before". v10 adds the call there (behavior 21), mapping failure to share's
coarse denial.

> Worth stating why this is a **Low-severity fix to a Medium-severity observation**: the share path has
> derived model keys from unguarded `mdKey`s for the app's entire life without incident. That is not an
> argument for leaving it — it is the *same* argument §3.4 makes about the local path, and it is
> evidence **for** this design's thesis rather than against it.

**Verified, not assumed** (P6, P7): no URL is built from the key — the only URI from a filename is the
local Obsidian link, already `encodeURIComponent`'d (`VideoMenu.tsx:39`) — and the key reaching HTML
goes through `esc()` (`render.ts:106`, `:114`). The allowlist protects nothing already unprotected.

### 3.5 What this DELETES

Everything below existed to serve a constraint that was not real. All of it goes:

| Deleted | Why it existed | Why it can go |
|---|---|---|
| The servability **refusal** (v5) | unservable keys had to be stopped | no unservable class **the mint path can produce** — see the correction below |
| The `videoId` **repair** (v6) | the refusal made videos permanently un-ingestible | nothing to repair — and it produced the unreadable filenames the user rejected |
| The **branded `CloudSummaryKey`** (v7) | to enumerate the four write entrances | nothing per-entrance to enforce; and round 7 **measured** that it did not enumerate them anyway |
| `check-key-brand.py` | to close the brand's cast escape | no brand |
| The manufactured **divergence** (round-7 H2) | mint repaired one side only | no repair |

The four write entrances (§2.5) still exist. Three of them need no per-entrance policy. **The fourth
sentence v9 wrote here was false, and it was the sentence justifying all five deletions.**

> ### ⚠ Correction — the UNSTORABLE class is empty; the UNSERVABLE class is not
>
> v9 said *"every key any of them can produce is now acceptable, and the encoder makes every one
> storable."* The second clause is true. The first is not, and it is **the same welding of two
> constraints into one word that this whole version exists to undo**, recurring one section after the
> box that undoes it. Found three ways in one round: by the coordinator reading Phase 6 finding 1
> against v9, by round-9 Claude M1, and (from the far end) by round-9 Codex M1.
>
> `isServableSummaryKey` rejects a non-empty class: `..`, C0/DEL, bidi controls, over-length, and
> anything not ending `.md`. So *"unstorable"* became empty; *"unservable"* merely got smaller.
>
> **The reachable instances, with the producer named for each** — because *"what caller reaches this
> state?"* is what separates a Blocking from a note:
>
> | Shape | Producer | Reachable? |
> |---|---|---|
> | `raw/275_x.md` — a **nested** `summaryMd` | `reconcile-serial.ts:127-131` calls the `raw/` layout *"real and supported"*, and `tests/lib/pdf/pdf-path.test.ts` + `reconcile-serial.test.ts:409-416` exercise it | **No production producer found** — the claim is a code comment, not a call site |
> | `notes..part2.md`, a C0 character, or >131 chars | `recoverOrphanedVideos` adopts **any** `*.md` carrying a `video_id` frontmatter field and sets `summaryMd = file` verbatim (`pipeline.ts:137`, `:104`); `sync-run.ts:263` then copies it to cloud verbatim and `:279` advertises `promoted` | **Yes, but only via a hand-placed or externally-renamed vault file** |
>
> **The conclusion is still "delete the refusal"** — the v5 refusal rejected *unstorable* keys and
> produced the unreadable `003_dQw4w9WgXcQ.md` filenames decision ③ rejects. What is wrong is the
> universal, not the deletion.
>
> **But this is exactly Phase 6 finding 1**, which v9 also deleted without noticing: *"a predicate whose
> only enforcement point is downstream of durability cannot prevent corrupt durable state; it can only
> report it."* The acceptance predicate runs **after** the bytes are durable and the row says
> `promoted`. Note this is **not a regression** — the current shipped guard already rejects all of the
> above and is already read-only, so every consequence here is live in production today. v9's error was
> asserting the hole closed.
>
> **v10's answer is two call sites, not machinery.** Call `isServableSummaryKey` at the mint
> (`summary-handler.ts:96`) and at the adopt (`sync-run.ts:263`, **before** the blob write), where a
> refusal costs nothing because nothing is durable yet. That is finding 1's *"move, do not add"*, and it
> is one line each — not the v5 refusal, which is still deleted.

### 3.6 The one real equivalence: the local filesystem

The additive create runs in **both** directions (`sync-run.ts:618-627`); when a video is cloud-only the
receiver is the vault, where APFS aliases NFC/NFD and `promote`'s `renameSync` overwrites. The
collision guard must consult the **receiver's blob store**, not index rows — a real vault file with no
index row is exactly what `recoverOrphanedVideos` adopts — and must read `tryGet`, treating
`unreadable` as **occupied**, because `SupabaseBlobStore.exists` is `get() !== null` and cannot prove
absence.

⚠ **Round-8 H1 — behavior 18 as written contradicts the code it governs.** `copyToLocal`
(`sync-run.ts:386-394`) is *required* to write the winner's bytes onto the loser; a guard that makes
it refuse breaks Class-A sync. The two writers need different rules, and v8 gave them one:

| Writer | Rule |
|---|---|
| `copyAdditiveVideo` — creating a row that does not exist | **Refuse** on an occupied alias. Nothing is owed to that key yet |
| `copyToLocal` / `transferClassA` — replacing a row that does | **Write**, because replacing is the point. Refuse only when the occupant is a *different* logical key that merely aliases |

The distinguishing question is not "is it occupied?" but **"is the occupant this same logical key?"**

> ### ⚠ Round-9 H1 — and NEITHER primitive §3.6 previously named can answer that question
>
> v9 named `tryGet` and, for ordering, `wx`. Measured (write target = logical key in NFD, occupant
> created under the aliasing form):
>
> ```
> CASE 1 — occupant IS the same logical key (NFD).    Table says: WRITE
>    tryGet(NFD).ok = true    wx = EEXIST    readdir = [ 'NFD' ]
> CASE 2 — occupant is a DIFFERENT logical key (NFC), merely aliasing.   Table says: REFUSE
>    tryGet(NFD).ok = true    wx = EEXIST    readdir = [ 'NFC' ]
> ```
>
> **Both named primitives are byte-identical across the branch the table says decides the outcome**,
> because both resolve *through* the alias. An implementer following v9 gets `EEXIST` and must pick a
> branch with no information — and both readings are defects this trail has already paid for: *refuse*
> restores round-8 H1 (every Class-A transfer throws, since the destination is occupied by definition),
> *write* clobbers the victim, which is the entire reason this section exists.
>
> **The credential that works is `readdir`**, because APFS is normalization-**preserving**: it returns
> the byte sequence the file was created with.
>
> > On `EEXIST`, read the receiver directory (`fs.readdirSync(dirname)`) and compare each entry
> > **byte-for-byte** against the logical key. An exact match ⇒ the same logical key. No exact match but
> > the path resolves ⇒ a *different* key aliasing this one. Then apply the table.
>
> It reaches past the `BlobStore` interface into `LocalFsBlobStore` — which is the real finding, and why
> the next pass on this section is a design review: the interface is addressed by **logical key**, the
> filesystem is addressed by **alias class**, and four rounds have been spent searching for a credential
> that reconciles them without saying out loud that the interface has none.
>
> Keep `tryGet`'s *unreadable ⇒ occupied* rule. It is right, and it answers a **different** question —
> *"can I prove absence?"* — which the Supabase receiver cannot (`provesAbsence = false`).
>
> Write behavior 18b's fixture with `.normalize('NFC')` / `.normalize('NFD')`, **never** as two source
> literals: two visually identical literals in a test file are exactly the invisible-character problem
> this spec has now hit three times.

⚠ **Round-6 M1 / round-8 M4 — ordering, and it is not fixable by check-then-write.** Between
`tryGet` and the write, a vault file can appear at the alias. The occupancy test and the write must be
**one operation**. A separate check-then-write cannot be made correct here, so the spec must not ask
for one.

> ### ⚠ Round-9 H2 — but `wx` is the wrong operation to make no-clobber, and v9 named it for both writers
>
> v9 said *"`LocalFsBlobStore` gains a no-clobber write; **both vault writers use it**."* The additive
> writer's durable write is not a `put`. It is a three-step protocol (`sync-run.ts:261-270`):
>
> ```ts
> // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
> const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
> const staged = await toBlob.get(toP, ref.tempKey);
> if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) { throw ... }
> await toBlob.promote(ref);
> ```
>
> A direct `writeFileSync(dest, bytes, {flag:'wx'})` collapses all four lines into one, so **the
> read-back hash verification disappears** — on a vault write, for a paid artifact, with the row then
> advertising `promoted`. Nothing in v9 told the implementer to preserve it, because v9 never mentioned
> the protocol existed.
>
> **The spec never had to choose between them.** Measured: `linkSync` is atomic, fails `EEXIST`, and
> sees through the NFC/NFD alias exactly as `wx` does. `renameSync` — what `promote` does today — is the
> only one of the three that silently overwrites.
>
> | Writer | Durable write today | No-clobber form |
> |---|---|---|
> | `copyAdditiveVideo` (`sync-run.ts:263-268`) | `putStaged` → verify → `promote` (rename) | **`promote` → `link` + `unlink`.** Staging and the hash verify survive unchanged |
> | `transferClassA` (`sync-run.ts:381-394`) | `putStaged` → verify → `put` (deliberate overwrite) | **keep `put`** — see the residual window below |
>
> §2.4 measured *"`wx` → `EEXIST`"* as a **fact about aliasing**. v9 promoted it to *the chosen write
> primitive* without asking whether the writers' shape admits it. That promotion — a measurement doing
> work it was not measured for — is the same move as the 255-vs-267 error, one layer up.

> ### ⚠ Round-9 M4 — and `transferClassA` cannot have the atomicity 18c claims
>
> On the Class-A path the destination is occupied **by definition** (`sync-run.ts:386-394`: *"a two-sided
> Class-A transfer must OVERWRITE the loser's existing (divergent) blob"*). So `wx` returns `EEXIST`
> every time and the real write is a separate, clobbering `put` at `:394`. That is three operations —
> test, identify, overwrite — not one.
>
> **Behavior 18c is therefore scoped to `copyAdditiveVideo` only.** For `transferClassA` the residual
> window is stated rather than papered over: between the identity check and the overwrite, a *different*
> logical key could appear at the alias and be clobbered. **Accepted**, because the alternative is
> refusing a transfer the protocol requires to succeed, and because reaching it needs a concurrent vault
> writer creating an aliasing filename during a sync run. Do not leave a claim of atomicity the code
> cannot make.

### 3.7 Unchanged

`lib/slugify.ts`; `summaryMd` as the logical name; the verbatim key copy in sync; `remap()`.
**ADR-0008 survives** — `objectKey` encodes only `key`, so both physical keys stay under the same
grant.

**`copy()` needs no change — and the reason is a placement constraint, not a property of `copy()`**
(round-9 L7). `copyBlob` (`blob-store.ts:126-173`) touches Storage only through `store.tryGet` and
`store.put`, so it inherits the encoding for free. **That stops being true the moment the encoder is
placed anywhere but inside `objectKey` (`supabase-blob-store.ts:15-18`)** — which §3.1 implies and
nothing states. Stated here because `reconcile-serial.ts:282` encodes *both sides of the same call* on
a paid-artifact relocation. Its short-circuit remains wrong on an aliasing backend but still has one
non-test caller, `cloud.blob` — one of the five *"safe because nothing does X yet"* arguments Phase 6
counted, and unguarded.

---

## 4. No migration, and how far that is proven

The encoder changes a key iff `¬SAFE` or longer than `LIMIT = 255`. The length half is vacuous — such a
key was rejected at upload and is not in the bucket. The charset half is a subset of "rejected" **except
for five characters** Storage accepts and `SAFE` excludes: space, `(`, `)`, `+`, `=`.

**No migration is needed iff no existing object name uses a character outside `SAFE`.**

**Gate — FAILS IF** any `storage.objects` row in `artifacts` has a path segment **after the first two**
not matching `^[A-Za-z0-9._-]+$`.

### 4.1 ⛔ The gate cannot run — `claude_ro` is denied on schema `storage`

Needs, from the user: `grant usage on schema storage to claude_ro;` and
`grant select on storage.objects to claude_ro;`. Until then §4 is **unverified**; blocks deploy, not
the plan. Run with `-v ON_ERROR_STOP=1` and check the exit code — the first runner reported a **false
pass** because an errored query printed a header and no rows.

---

## 5. Behaviors

| # | Behavior | By |
|---|---|---|
| 1 | A `SAFE` key ≤ `LIMIT` encodes to itself byte-identically | unit + property |
| 2 | A non-ASCII key encodes to an accepted physical key | unit + integration |
| 3 | NFC and NFD forms encode to **different** keys, each round-tripping | unit |
| 4 | `encodeSegment` is injective over arbitrary segments | property + crafted preimage |
| 5 | Every encoded segment ≤ 65 chars; identity segments ≤ 255 | property |
| 6 | `put` → `get` on a Korean key round-trips | integration |
| 7 | `putStaged` → `promote` on a Korean key lands correctly | integration |
| 8 | `list(p, 'dig/{korean base}/')` returns logical keys | integration |
| 9 | `list()` throws on a physical-remainder segment it cannot name | unit |
| 10 | `list()` does **not** throw when the caller's prefix contains `=` | unit |
| 11 | `deletePrefix(p, '')` removes everything under the playlist root | integration |
| 12 | `list(p, 'dig/{base}/')` == `list(p, 'dig/{base}')` | unit |
| 13 | Local and in-memory adapters are identity | unit |
| 14 | **A Korean-titled video ingests and serves 200; ledger unmoved** | integration |
| 15 | **An NFD accented-Latin title ingests and serves 200** | integration |
| 16 | **A title with a space, an emoji, or an astral letter at the `slice(60)` boundary ingests and serves 200** — no fallback, no refusal, and the vault filename stays readable | integration |
| 17 | `nested/foo.md`, `%2f`, `／`, `℀.md`, `001_a．．b.md`, a control char, a bidi override, and a 200-char base are all **rejected** by the guard | unit |
| 17b | Total key lengths **129, 130 and 131 are ACCEPTED** — the bound did not narrow (round-9 H3) | unit |
| 18 | `copyAdditiveVideo` refuses an **occupied alias** (vault file, no index row) — the file survives untouched | integration, real FS |
| 18b | The identity test is `readdir` byte-comparison: `transferClassA` **writes** when the occupant is the same logical key and refuses a *different* key that merely aliases. **Fixture forms built with `.normalize()`, never as two literals** | integration, real FS |
| 18c | For `copyAdditiveVideo` only: the occupancy test and the durable write are **one operation** (`link`), and `putStaged` → verify → `promote` is intact — the read-back hash check still runs | integration, real FS |
| 19 | The collision guard treats an `unreadable` receiver read as **occupied** | unit |
| 20 | The §4 gate's SQL predicate derives from the encoder module | check script |
| 21 | The **share** path rejects a non-servable `mdKey` before deriving `base` from it, as coarse denial (round-9 Codex M1) | integration |
| 22 | `encodeSegment('003_x\uD840.md') !== encodeSegment('003_x\uD850.md')` — two **distinct lone surrogates** encode differently (restored; round-8 M2, still open in v9) | unit |

Behaviors **16** and **17** are the pair that matters: 16 says the guard stopped rejecting what it never
needed to, 17 says it still rejects what it was built for.


**Mutations — restored, and scoped to what v9 KEEPS.** Round-8 H2: v8 deleted the mutation table
along with the machinery it had been written for, and 6 of its 10 entries targeted mechanisms v9
still relies on. Each row names an **observable**, because three earlier tables named mechanisms and
all three were measured vacuous.

**Every row below is `PROVISIONAL` until the mutation has been applied and the named behavior observed
RED** — the rule this spec's own history bought (`process-checklists.md`, *"A nominated falsifier is
provisional until it has been run red"*). At spec time there are no tests to mutate, so no row here may
be reported as verified; that happens in Phase 3.

| Mutation | Must turn red | Status |
|---|---|---|
| `hash(NFC(s))` instead of `hash(s)` in the encoder | 3 | PROVISIONAL |
| Drop `utf16le` back to `utf8` | **22**, not 4 — see below | PROVISIONAL |
| Widen `SAFE` to include `=` | 4 (crafted preimage — confirmed constructible and deterministic, round 9) | PROVISIONAL |
| Skip the NFKC-folded pass in `isServableSummaryKey` | 17 (`℀.md`, `001_a．．b.md` — now listed *in* 17) | PROVISIONAL |
| Narrow the length bound from 131 to 128 | **17b** | PROVISIONAL |
| Drop the bidi-control rejection | 17 | PROVISIONAL |
| Revert the guard to the `\p{L}\p{N}` allowlist | 15 (NFD accented Latin 409s) | PROVISIONAL |
| Replace `link` with `rename` in the additive promote | 18c | PROVISIONAL |
| Skip the read-back hash verify before promote | 18c | PROVISIONAL |
| Use `tryGet` instead of `readdir` for the identity test | **18b** — measured: `tryGet` cannot distinguish the branch | PROVISIONAL |
| Make `copyAdditiveVideo` write instead of refuse | 18 | PROVISIONAL |
| Drop the guard call on the share path | 21 | PROVISIONAL |
| Apply the `list()` marker check to the caller's prefix | 10 | PROVISIONAL |
| Encode empty segments | 11 and 12 | PROVISIONAL |

> **Round-9 M2 — the `utf16le` row was vacuous, and v9's fix moved the gap instead of closing it.**
> Round 8 asked for behavior 22 back. v9 restored the *table* and not the behavior the table points at,
> leaving the row aimed at behavior 4 (*"injective … property + crafted preimage"*). Both lone-surrogate
> inputs are **ill-formed UTF-16**: property generators emit well-formed strings, and the only crafted
> preimage §5 named was the `=`-marker one. So the mechanism was real and measured —
> `utf8` collides where `utf16le` does not — and **no observable in the spec could go red.** Behavior 22
> is restored above and the row now points at it.
>
> This is the second failure mode from the rule: not *"the mutation survives"* but *"the input is
> unconstructible"*. It is why the check has to be applied per row.

> **Round-9 L5 — behavior 9 is unreachable from production, deliberately.** `digSectionKey`
> (`dig-blob-key.ts:13,22`) builds `dig/${base}/${sectionId}.r${V}.md` from a `number`, so every dig leaf
> matches `\d+\.r\d+\.md` — always `SAFE`, never `=h`-marked. No production `list()` can meet an
> un-nameable remainder. Kept as a seam backstop, and noted here because an uncaught throw inside
> `load-dig-for-serve.ts:34` would **500 a paid doc** rather than degrade.

## 6. Alternatives declined

**6.1 A reversible encoding.** Available (247 of 255) — declined for headroom (hashing is 65 worst
case, insensitive to `slugify`'s cap) and because `list()` never needs inversion. Cost: a Korean
video's object is not self-describing in the bucket.

**6.2 Supabase user metadata.** Measured viable; declined — `list()` does not return it, so recovering
N names costs N `info()` calls on the deadline-bounded money path, and it adds an object-exists-but-
cannot-be-named state.

**6.3 ASCII-ify `slugify`.** Contradicts decisions ① and ③.

**6.4 Opaque `videoId` keys.** Closest to the ⏸ parked ADR-0006/0007; changes every address, needs a
full migration.

## 7. Risks

| Risk | Handling |
|---|---|
| An existing prod key uses ` `, `(`, `)`, `+` or `=` | §4 gate before deploy. ⛔ unrunnable — §4.1 |
| An existing prod key is **129–131 characters** | **Dissolved, not gated** — v10 keeps the bound at 131, so the guard is a strict widening in every dimension (round-9 H3). This row exists because v9 would have needed a gate the §4 SQL structurally could not provide: its predicate is a character class with no length term |
| Widening the guard is security-relevant | It is a **denylist of separators**, strictly narrower in what it permits through than the local path already permits. The backstops are named per path in §3.4 — `assertLogicalKey` on cloud, `assertIndexRelPathWithin` on local; they are **not** the same guard. **Needs a security reviewer at the PR** |
| A key that syncs and stores can still be unservable | Real, pre-existing, and **not closed by the encoder** — see the §3.5 correction. v10 adds the mint and adopt call sites; the `raw/` nested-`summaryMd` shape stays an open pre-existing gap with no known producer |
| A ninth premise is wrong | §1.1 exists so the next reviewer attacks the premises first — that is where seven rounds were spent. P3's falsifier has already fired once (round-9 L1) |
