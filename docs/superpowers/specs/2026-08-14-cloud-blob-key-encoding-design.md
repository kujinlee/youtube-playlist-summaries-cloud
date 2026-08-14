# Cloud blob keys — encode at the storage seam so a title in any language can be stored (backlog #36)

**Status:** draft **v9**, awaiting user approval. **Branch:** `fix/cloud-blob-key-encoding`.
**Origin:** backlog **#36** 🔴, found 2026-08-12 by the first real M3 acceptance run against prod v6.

**Review trail — seven dual rounds, fourteen halves, all NOT CONVERGED, plus a Phase 6 architecture
review.** `docs/reviews/spec-blob-key-encoding-r{1..7}-{codex,claude}.md`,
`docs/reviews/architecture-review-2026-08-14.md`.

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
| P3 | Every write reaches Storage through `SupabaseBlobStore` | **QUOTED** — the only `client.storage.from(` outside tests is `supabase-blob-store.ts:20` | a second call site |
| P4 | `list()` never needs to invert the encoding | **QUOTED** — all 3 callers pass `dig/${base}/` and read `{sectionId}.r{V}.md` leaves | a caller consuming a leaf it did not supply the prefix for |
| P5 | The serve guard's requirement is *single path component*, not ASCII | **QUOTED** — its own docstring; and it has exactly 2 callers | a downstream consumer that breaks on a non-ASCII but separator-free key |
| P6 | No URL is built from the key | **MEASURED** (grep, §3.4) — the only URI from a filename is the local Obsidian link, already `encodeURIComponent`'d | a URL built by string interpolation from `summaryMd`/`base` |
| P7 | The key reaching HTML is escaped | **QUOTED** — `render.ts:106`, `:114`, both via `esc()` | an unescaped interpolation |
| P8 | A vault filename is always a single path component | **Structural** — POSIX forbids `/` in a component | n/a |

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

**Contract:** injective over arbitrary logical segments as raw JS strings; total; bounded (65 chars).
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
  if (key.length <= 3 || key.length > 128 || !key.endsWith('.md')) return false;
  // Check the RAW form and the compatibility-FOLDED form. `℀` folds to `a/c`, `＼` to `\`,
  // `．．` to `..`. A hand-typed homoglyph denylist cannot be complete; NFKC closes the class.
  for (const s of [key, key.normalize('NFKC')]) {
    if (s.includes('/') || s.includes('\\') || s.includes('..')) return false;
    if (/[\x00-\x1f\x7f]/.test(s)) return false;   // C0 + DEL
    if (/%2f|%5c/i.test(s)) return false;                // percent-encoded separators
  }
  return true;
}
```

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
filenames, for the app's entire life. What protects both sides is `assertLogicalKey` plus the
resolved-path containment check. The allowlist was an over-approximation, free when `slugify` was the
only producer.

**Verified, not assumed** (P6, P7): no URL is built from the key — the only URI from a filename is the
local Obsidian link, already `encodeURIComponent`'d (`VideoMenu.tsx:39`) — and the key reaching HTML
goes through `esc()` (`render.ts:106`, `:114`). The allowlist protects nothing already unprotected.

### 3.5 What this DELETES

Everything below existed to serve a constraint that was not real. All of it goes:

| Deleted | Why it existed | Why it can go |
|---|---|---|
| The servability **refusal** (v5) | unservable keys had to be stopped | there is no unservable class left |
| The `videoId` **repair** (v6) | the refusal made videos permanently un-ingestible | nothing to repair — and it produced the unreadable filenames the user rejected |
| The **branded `CloudSummaryKey`** (v7) | to enumerate the four write entrances | nothing per-entrance to enforce; and round 7 **measured** that it did not enumerate them anyway |
| `check-key-brand.py` | to close the brand's cast escape | no brand |
| The manufactured **divergence** (round-7 H2) | mint repaired one side only | no repair |

The four write entrances (§2.5) still exist — they simply need no per-entrance policy, because every
key any of them can produce is now acceptable, and the encoder makes every one storable.

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

⚠ **Round-6 M1 / round-8 M4 — ordering, and it is not fixable by check-then-write.** Between
`tryGet` and the write, a vault file can appear at the alias. Both round-8 halves reached the same
fix and the Claude half measured that the primitive exists: **do the occupancy test and the write in
one operation** — `fs.writeFileSync(dest, bytes, { flag: 'wx' })`, which fails `EEXIST` atomically,
and on APFS fails for an NFC/NFD alias too. `LocalFsBlobStore` gains a no-clobber write; both vault
writers use it; the caller decides on `EEXIST` per the table above.

A separate check-then-write cannot be made correct here, so the spec must not ask for one.

### 3.7 Unchanged

`lib/slugify.ts`; `summaryMd` as the logical name; the verbatim key copy in sync; `remap()`.
**ADR-0008 survives** — `objectKey` encodes only `key`, so both physical keys stay under the same
grant. `copy()` needs no change (its short-circuit is wrong on an aliasing backend but has one
non-test caller, `cloud.blob`).

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
| 17 | `nested/foo.md`, `%2f`, `／`, a control char, and a 200-char base are all **rejected** by the guard | unit |
| 18 | `copyAdditiveVideo` refuses an **occupied alias** (vault file, no index row) — the file survives untouched | integration, real FS |
| 18b | `copyToLocal`/`transferClassA` **writes** when the occupant is the same logical key, and refuses only a *different* key that merely aliases | integration, real FS |
| 18c | The occupancy test and the write are **one operation** (`wx`) — an alias appearing between them cannot be clobbered | integration, real FS |
| 19 | The collision guard treats an `unreadable` receiver read as **occupied** | unit |
| 20 | The §4 gate's SQL predicate derives from the encoder module | check script |

Behaviors **16** and **17** are the pair that matters: 16 says the guard stopped rejecting what it never
needed to, 17 says it still rejects what it was built for.


**Mutations — restored, and scoped to what v9 KEEPS.** Round-8 H2: v8 deleted the mutation table
along with the machinery it had been written for, and 6 of its 10 entries targeted mechanisms v9
still relies on. Each row names an **observable**, because three earlier tables named mechanisms and
all three were measured vacuous.

| Mutation | Must turn red |
|---|---|
| `hash(NFC(s))` instead of `hash(s)` in the encoder | 3 |
| Drop `utf16le` back to `utf8` | 4 (lone-surrogate collision) |
| Widen `SAFE` to include `=` | 4 (crafted preimage) |
| Skip the NFKC-folded pass in `isServableSummaryKey` | 17 (`℀.md`, `001_a．．b.md` admitted) |
| Revert the guard to the `\p{L}\p{N}` allowlist | 15 (NFD accented Latin 409s) |
| Replace the `wx` write with check-then-write | 18c |
| Make `copyAdditiveVideo` write instead of refuse | 18 |
| Apply the `list()` marker check to the caller's prefix | 10 |
| Encode empty segments | 11 and 12 |

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
| Widening the guard is security-relevant | It is a **denylist of separators**, strictly narrower in what it permits through than the local path already permits. The resolved-path containment check remains the real backstop. **Needs a security reviewer at the PR** |
| A ninth premise is wrong | §1.1 exists so the next reviewer attacks the premises first — that is where seven rounds were spent |
