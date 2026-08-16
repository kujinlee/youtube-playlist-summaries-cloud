# Cloud blob keys — encode at the storage seam so a title in any language can be stored (backlog #36)

**Status:** draft **v18**, awaiting user approval. **Branch:** `fix/cloud-blob-key-encoding`.
**Origin:** backlog **#36** 🔴, found 2026-08-12 by the first real M3 acceptance run against prod v6.

**Review trail — fourteen dual rounds, a Phase 6 architecture review, a round-10 DESIGN review, and a
credential design pass.**
`docs/reviews/spec-blob-key-encoding-r{1..9,11..15}-{codex,claude}.md`,
`docs/reviews/spec-blob-key-encoding-r10-codex-design.md`,
`docs/reviews/spec-blob-key-encoding-s36-design-claude.md`,
`docs/reviews/spec-blob-key-encoding-credential-design-pass.md`,
`docs/reviews/architecture-review-2026-08-14.md`.
*(Ignore `…-r5-codex-STALE-v4-brief.md` — dispatched against a pinned commit and reviewed a dead version.)*

> ## v18 IN ONE SENTENCE — the same fix, applied twice, to the two rules that were still counting
>
> Round 15 was the first round where **both halves independently found the same defect shape**: v17
> replaced three enumerations with three derivations, and **two of the three were not derivations** —
> they named a function (`writeModelEnvelope`) and a pair of methods (`upsertVideo`,
> `updateVideoFields`), each of which turned out to be one member of a larger set.
>
> | v17 attached the rule to | Missed | v18 attaches it to |
> |---|---|---|
> | `writeModelEnvelope` | `writeModelEnvelopeWithin` — the **cloud serve path**, which a repo tripwire *forbids* merging with it | **`serialize()`** — private, and the only path from an envelope to bytes |
> | `upsertVideo` + `updateVideoFields` | `bulkUpdateVideoFields` — a third adapter method that merges arbitrary fields into `videos.data` | **`videoDataPayload()`** (renamed from `stripComputed`) — private, and the only constructor of what lands in `videos.data` |
>
> Both replacements are **private functions with no callers outside their module**, enumerated over the
> whole repo. That is the difference between the two columns: the right-hand rule is satisfied by
> **construction** — a fourth writer added next year cannot reach the durable state without passing
> through it — while the left-hand rule is satisfied by **remembering**. The third derivation
> (`\p{Bidi_Control}`) held under measurement and v18 only fixes its *wording*, which claimed a
> derivation over a hand-typed class.
>
> **The falsifier for round 16, carried forward from round 15's escalation override:** if round 16
> produces another finding of the form *"the derivation does not reach writer/method/caller N"*, the
> pattern is that this document keeps choosing enforcement points by **name** instead of by
> **dominance**, and a wider redesign is owed rather than a fourth repair. Round 15 already contained
> **two** instances of that shape in one round, which is why the override was recorded as narrow.

> ## ⛔ §3.6 WAS ESCALATED FROM FIX TO REDESIGN, AND THE REDESIGN RAN (round-9 M5 → round 10)
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
> **⚠ CORRECTED AT ROUND 11 — "§3.1–§3.5 have converged and stayed converged" was a claim about V9,
> and v11 printed it over v10's text.** The 131 bound, the bidi rejection, the §3.5 unservable-class
> correction, the two new mint/adopt call sites and the share-path guard were all folded in **after**
> round 9 and had **no** adversarial pass until round 11 — which immediately returned a **Blocking**
> (B1), a Medium falsifying a `MEASURED` claim (M3), and a Medium finding the fix unverifiable (M4).
>
> The accurate statement: **§3.1–§3.3 have converged and stayed converged since v9.** §3.4 and §3.5
> were reviewed for the first time at round 11. Do not let §3.6's churn re-open §3.1–§3.3.
>
> ### Escalation counter after round 11 — READ THIS BEFORE READING IT LATER
>
> Round 11 was §3.6's first adversarial pass **as redesigned**. Findings caused by the round-10
> redesign: Codex's `promote`-contract Blocking, and Claude's H1, M1, M2, L1. Under
> `review-method.md:45-49` that is **round 1 of a NEW fix cycle on §3.6** — two more like it re-arms
> FIX→REDESIGN.
>
> **But they are specification-COMPLETENESS defects, not mechanism defects**, and the distinction has
> to be recorded now, before the counter is read by someone who was not here: *what does the primitive
> do on `EEXIST`*, *which read primitive and is the classification total*, *which branch does the
> residual actually cover*, *which adjacent `mkdir` was dropped*. **None says R1–R4 is the wrong
> shape** — the shape was attacked directly and held. That argues for FIX, and specifically **against**
> a second REDESIGN.
>
> The genuinely load-bearing round-11 result is the correction above: **§3.4/§3.5 had never been
> adversarially reviewed at all**, and their first pass returned a Blocking.
>
> **The escalation paid for itself immediately.** Round 10 measured that v10's own §3.6 fix — the
> `readdir` byte-comparison — **would have refused a video's own file on the money path**, which is
> round-8 H1 re-entering through the credential chosen to prevent it. A fifth defect hunt would have
> shipped it. §3.6 is now rewritten, not patched; see §3.6.0.

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

**2.5 Write entrances — the count has been wrong in every version so far.** `slugify` runs on exactly
one; the rest take a key verbatim: worker mint (`summary-handler.ts:96`), additive create
(`sync-run.ts:263`), Class-A transfer (`sync-run.ts:379-399`), base reconciliation
(`reconcile-serial.ts:282`/`:293`), and — found at round 10 — `companionTransfer`'s model **write and
DELETE** (`sync-run.ts:464`, `:475`). The spec named **1, 1, 1, 1, 2, 3, 4** across seven rounds.

> **Stop treating this as a number to get right.** Two mechanisms in this spec were already deleted for
> exactly this reason — the branded `CloudSummaryKey` (*"round 7 measured that it did not enumerate
> them anyway"*, §3.5) and the homoglyph denylist (*"a hand-typed list cannot be complete"*, §3.4).
> §3.4 needs no enumeration because every key is acceptable; §3.6 needs none because it is written
> against two **patterns**, not N writers. **A rule that must be restated per writer will keep churning
> in a codebase that keeps growing writers.**

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

> ### ⛔ Round-12 H1 — and it changes §3.7: `slugify` gets a ONE-LINE repair
>
> §2.4 says *"`LocalFsBlobStore.abs()` is `path.join(indexKey, key)` — **identity**."* **That is a
> measurement about PATH CONSTRUCTION, and v14 read it as a claim about STORAGE.** It is false at the
> storage layer for exactly the class §3.4 newly admits. MEASURED on APFS:
>
> ```
> wrote key        "003_x\ud840.md"
> readdir returned "003_x\ufffd.md"        ← U+FFFD REPLACEMENT CHARACTER
> then wrote       "003_x\ud850.md"        (a DIFFERENT lone high surrogate)
> directory now holds 1 file
> read through key1 -> key2's body          ← key1's content is GONE
> ```
>
> Node encodes every unpaired surrogate as U+FFFD on the way to a path — **the exact behaviour §3.2
> cites as its reason to hash with `utf16le`.** §3.2 applied that lesson to the encoder and nothing
> applied it to the filesystem. Consequences: behavior 16's *"the vault filename stays readable"*
> asserts the opposite of what happens (it is mojibake); `canonicallyEqualName` can never match the row
> against the on-disk name; and the Class-A path then refuses permanently — round-8 H1 again.
>
> **Rejecting the class in the guard is necessary but NOT sufficient — alone it is a new Blocking.**
> MEASURED: the current shipped guard already rejects **93,231** `slugify` outputs and *every one* is
> ill-formed UTF-16. Refusing them at the mint (§3.5) without fixing the producer makes 93,231 titles
> permanently un-ingestible, with the `videoId` repair deleted and decision ③ forbidding its return.
>
> **So the producer is repaired, and it is one line:**
>
> ```ts
> // lib/slugify.ts — .slice(0, 60) cuts UTF-16 code units and can split a surrogate pair.
> const s = /* …existing… */.slice(0, 60);
> return s.isWellFormed() ? s : s.slice(0, -1);   // drop the orphaned half
> ```
>
> **MEASURED: 3,479,131 slug outputs across the full codepoint space × 4 shapes — 0 remain
> ill-formed.** This is a **defect repair, not a naming change**: today those titles already produce
> mojibake vault filenames. It is therefore *not* backlog #46 (the NFKC slice, which changes readable
> names and needs its own migration argument) — it removes a broken output no one wants.
>
> The guard's `isWellFormed()` check stays as the **backstop**: `readdir` strings are always
> well-formed, so after this repair the class is unreachable from either entrance, and the check is the
> assertion that this stays true.
>
> **⚠ Round-13 L3 — this repairs the PRODUCER, not the existing damage.** A vault file already written
> under an ill-formed key is on disk as `003_x\ufffd.md` today. The repair stops new ones; it does not
> rename old ones, and `canonicallyEqualName` still cannot match such a file to its row. Prod is
> unaffected (§4.1 measured 0 non-ASCII names in 19 objects), but **a local vault is not measured** —
> the same gap backlog #46 records. Stated here rather than left to be discovered: **forward-only, and
> the residue is a local-vault question, not a cloud one.**

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
  if (!key.endsWith('.md')) return false;
  // CODE POINTS, not UTF-16 units — the guard this replaces counts code points (it is a /u regex),
  // and this predicate's whole subject is non-ASCII keys. 131 = that guard's exact ceiling.
  const cp = [...key];
  if (cp.length <= 3 || cp.length > 131) return false;
  // Ill-formed UTF-16 (a lone surrogate) does NOT survive the local filesystem: Node encodes every
  // unpaired surrogate as U+FFFD on the way to a path, so the vault filename becomes mojibake and two
  // DIFFERENT lone surrogates collapse onto one file. Round-12 H1.
  if (!key.isWellFormed()) return false;

  // Inspect the NAME. NEVER the glued key: folding `name + '.md'` manufactures a `..` at the
  // joint out of one legal character (`⒈` is DIGIT ONE FULL STOP — it folds to `1.`).
  const name = key.slice(0, -3);
  // Raw form AND compatibility-folded form. `℀` folds to `a/c`, `＼` to `\`. A hand-typed
  // homoglyph denylist cannot be complete; NFKC closes that class.
  for (const s of [name, name.normalize('NFKC')]) {
    if (s === '' || s === '.' || s === '..') return false;   // the traversals a COMPONENT can be
    if (s.includes('/') || s.includes('\\')) return false;   // separators, in every form
    if (s.includes('..')) return false;                      // traversal-shaped, inside the name
    if (/[\x00-\x1f\x7f-\x9f]/.test(s)) return false;         // C0 + DEL + C1 (round-12 L1)
    if (/%2f|%5c/i.test(s)) return false;                    // percent-encoded separators
    if (/\p{Bidi_Control}/u.test(s)) return false;            // the PROPERTY \u2014 see the note below
  }
  return true;
}
```

> ### ⛔ Round-11 B1 — v11's `s.includes('..')` REJECTED KEYS `slugify` CAN PRODUCE
>
> `slugify` preserves every `\p{N}`. **MEASURED across the whole codepoint space: 21 characters**
> survive `slugify` *and* have an NFKC form ending in `.` — `U+2488`–`U+249B` (`⒈`…`⒛`) and `U+1F100`
> (`🄀`). As the last character of a slug, the `.md` suffix completes a `..`:
>
> ```
> title  "Lesson ⒈"
> key    003_lesson-⒈.md
> NFKC   003_lesson-1..md          ← contains ".."
> CURRENT guard (shipped today):   ACCEPTS
> v11 predicate:                   REJECTS
> ```
>
> Coordinator re-verified independently: exactly 21 codepoints, exactly 21 regressing keys.
>
> **Two Blocking consequences, and v10 created the second one by deleting its own repair.** With the
> §3.5 mint call the summary job fails on every attempt and the v6 `videoId` repair that would have
> rescued it was deleted in the same section — and decision ③ forbids bringing it back. Without the
> mint call, the encoder stores the key, `persistSummary(…, 'promoted')` advertises it, and the serve
> guard 409s **forever**.
>
> **Why it survived ten rounds.** §3.4's NFKC pass and §3.5's *"the mint path can produce nothing
> unservable"* were written in different rounds and never cross-derived — `review-method.md:174-177`
> Step 2, which this spec ran on §3.6 and not here. §3.4's premise — *"`slugify` emits only letters,
> numbers and `-`"* — is **true and irrelevant**: the fold happens *after* `slugify`, and it turns a
> legal `\p{N}` into a `.`.
>
> **The fix — and v12 got it wrong before v13 corrected it.**
>
> v12 removed the `..` test outright, reasoning that a `..` inside one component cannot traverse
> anything. True, but it answered the wrong question and it **widened the guard**: `001_a．．b.md`
> became legal, a filename nobody wants and no measurement asked for.
>
> **The user's objection is the correct diagnosis: there is no `..` in the filename at all.** The name
> is `003_lesson-⒈`, the extension is `.md`, and neither contains `..`. The `..` exists only in a
> string the guard *manufactured* by folding the two together. `003_lesson-1..md` is not a filename —
> it is scratch, scanned once and discarded.
>
> So v13 inspects **the name**, and the extension is not part of it:
>
> ```
> name  003_lesson-⒈   →  NFKC  003_lesson-1.     no "..", accepted    ← the trailing dot IS the ⒈
> name  001_a．．b       →  NFKC  001_a..b          "..", rejected       ← genuinely in the name
> ```
>
> **`..` stays rejected, `001_a．．b.md` stays rejected, and the B1 class is accepted.** Nothing is
> widened. `assertLogicalKey`'s component test (`blob-store.ts:87-91`) still applies to the whole
> logical key underneath.
>
> **The general defect, worth carrying past this spec: the guard checked a CONCATENATION instead of
> checking the parts.** `isServable(name + ext)` is a different question from `isServable(name)` —
> string operations on a joined value can see patterns present in neither piece. Same family as SQL
> injection (data glued into a query becomes syntax) and the backtick-in-a-double-quoted-shell-string
> bug this repo has hit twice. Here the manufactured "syntax" was `..`.
>
> **Not fixed here, and filed separately: `slugify` could stop emitting these characters at all.**
> MEASURED — if `slugify` normalized its input, `⒈` would become `1.`, the `.` would become `-`, and
> the slug would be a cleaner `lesson-1`; **6,672,384 swept slug outputs are NFKC-stable**, which would
> make the fold above a provable no-op. It is a separate slice because `slugify` is shared with the
> local path and changes vault filenames. See `docs/backlog.md` **#46**. **It would not replace this
> fix** — the adopt path takes vault filenames verbatim, so the guard must stay correct for input the
> mint path does not produce.

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
> Fixed by keeping the bound at **131**.
>
> **⚠ v10 then claimed this made the guard "a strict widening in every dimension". Round 11 falsified
> that TWICE, independently — the claim is retracted, not repaired.** (a) **B1** above: 21
> `slugify`-producible keys were rejected that the current guard accepts. (b) **M3, units**: the
> current guard is a `/u` regex, so each atom matches one **code point**; v11 used `key.length`, i.e.
> **UTF-16 code units**. MEASURED smallest disagreement — `'a'` + 64 astral letters + `.md` is 68 code
> points but 132 code units: accepted today, rejected by v11. Over BMP-only keys of every length 4–143
> there were **zero** disagreements, which is exactly why the defect survived: *the fix was right for
> the input it was tested on.* The predicate above now counts code points.
>
> The lesson is about the sentence, not the bound. **"Strict widening in every dimension" is a
> universal, and this document has now had three universals falsified** — *"every key any entrance can
> produce is acceptable"* (§3.5), *"no unservable class the mint path can produce"* (B1), and this one.
> A universal asserts something about inputs nobody enumerated. §3.2 asks the units question for the
> encoder (*"`SAFE ⊂ ASCII`, so `String.length` is sound"*) and §3.4 did not ask it for the guard — on
> a predicate whose entire subject is non-ASCII keys.

> ### ⚠ Round-14 L1 → round-15 Low — the fix CLAIMED a derivation and shipped an enumeration
>
> **v9's class covered 9 of the 12 `Bidi_Control` code points** — `U+061C` (ARABIC LETTER MARK),
> `U+200E` (LRM) and `U+200F` (RLM) passed. v15–v17 fixed the *coverage* by hand-typing a 12-code-point
> character class, and wrote underneath it: *"the class is now the full property, not a hand-picked
> range."* **Both halves of round 15 caught that sentence.** The class was measured equal to the
> property — 0 misses, 0 over-matches, across the whole codepoint space, on Node v22.14.0, three times
> independently — so there was never a live data-loss path here. The defect is the **claim**: a reader
> who believes the enumeration was removed will not check it, and the next Unicode release is the event
> that makes the belief wrong.
>
> **v18 writes `/\p{Bidi_Control}/u`, so the sentence becomes true.** This is the distinction from
> [`portable-practices.md`](../../portable-practices.md) — *a derivation you have to be RIGHT about is
> still a count*. `\p{Bidi_Control}` is a derivation because **Unicode owns the answer**; a hand-typed
> range that equals it today is a count that got lucky, and the comment asserting otherwise is what
> stops anyone re-checking. Unicode property escapes are ES2018 and need only the `u` flag, so there is
> no runtime cost to being right.
>
> **The test derives too — no count.** Assert *"every code point for which `/\p{Bidi_Control}/u` holds
> is rejected by the predicate"*, **not** *"exactly 12 code points are rejected"*. A 13th control added
> upstream is then covered automatically instead of turning a legitimate Unicode update into a red suite.
>

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

**And the guard is not uniform — round-8 Codex Medium, round-9 Codex M1, round-11 L2.**
`lib/share/serve.ts:47` returns `mdKey` with **no** guard call, and `app/s/[token]/route.ts` derives
`base` from it **twice** — `:69` (the md-download filename) and `:78` — exactly the derivation the
guard's docstring calls itself "the hard boundary before". v10 cited only `:78`.

**Put the call inside `getShareServeContext`, before `mdKey` is returned**, so both derivations are
covered *by construction* rather than by enumeration — this document has now been wrong about a count
eight times. Map failure to share's coarse denial.

> Verified while there, and deliberately **not** a finding: `fileResponse` already handles a
> newly-reachable non-ASCII `base` safely — `asciiSafe` maps everything outside printable ASCII to `_`
> and `encodeRFC5987` percent-encodes every non-attr-char byte (`file-response.ts:5-24`). **No header
> injection through the widened key.**

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
> **⚠ ROUND 11 FALSIFIED THE REPLACEMENT UNIVERSAL TOO.** v10 narrowed *"there is no unservable class
> left"* to *"no unservable class **the mint path can produce**"*. That is **also false** — see §3.4
> B1: 21 codepoints survive `slugify` and NFKC-fold to a trailing `.`, so the mint path could produce
> a key v11's predicate rejects. Two universals, two rounds, same section. **The honest form carries no
> universal at all:** the encoder makes every key storable; `isServableSummaryKey` rejects a specific,
> enumerated class; the mint and adopt call sites exist so that class is refused *before* anything is
> durable or paid.
>
> **And once B1 is fixed, the mint call site is a backstop no input reaches** — MEASURED: every
> codepoint against four title shapes, zero `slugify` outputs fail the predicate. Say that plainly
> rather than presenting it as half the answer. It is worth keeping: it is the assertion that the
> §3.4/§3.5 cross-derivation holds, and it goes red if either side moves.
>
> **Two things the call sites cost, neither previously stated:**
>
> - The mint guard sits **after** `reserveVideoSlot` (`summary-handler.ts:95`) and **before** the Gemini
>   call (`:101`), so a refusal **costs no money** — good. But a throw there leaves the bare reserved
>   row that only the `PermanentTranscriptError` path rolls back (`:126-135`): the serial is consumed
>   and the job retries to `dead_letter`.
> - The adopt refusal (`sync-run.ts:236-238`, **above `ensureReceiverSlot`** — round-15 L1: this bullet
>   still said `:263`, the location round-13 H2 proved wrong three subsections below) is per-video,
>   caught, and **advances no baseline**, so it **re-fires on every subsequent run, forever**, until a
>   human renames the vault file. That is the right behaviour under decision ③ — the automated repair was
>   deleted — but **the error message must name the repair**, because nothing else will.
>
> **But this is exactly Phase 6 finding 1**, which v9 also deleted without noticing: *"a predicate whose
> only enforcement point is downstream of durability cannot prevent corrupt durable state; it can only
> report it."* The acceptance predicate runs **after** the bytes are durable and the row says
> `promoted`. Note this is **not a regression** — the current shipped guard already rejects all of the
> above and is already read-only, so every consequence here is live in production today. v9's error was
> asserting the hole closed.
>
> **The answer is call sites, not machinery — but v10 through v15 put one of them in the WRONG PLACE.**
> Call `isServableSummaryKey` at the mint (`summary-handler.ts:96`) and on the adopt path. That is
> finding 1's *"move, do not add"* — not the v5 refusal, which is still deleted.
>
> ### ⛔ Round-13 H2 — `sync-run.ts:263` is AFTER a durable write, and the guard is routed around
>
> v10–v15 said the adopt guard goes at `:263` *"where a refusal costs nothing because nothing is
> durable yet"*, and that a refusal *"re-fires on every subsequent run, forever."* **Both halves are
> false, and the function says so twelve lines above the chosen line.**
>
> `ensureReceiverSlot` has already run at `:240`, and it calls `to.claimVideoSlot(...)` — on the cloud
> store a **durable insert** (`supabase-metadata-store.ts:87`). The precedent was already written at
> `sync-run.ts:230-235`:
>
> > *H-R2-1 (round 2) — this guard MUST run BEFORE `ensureReceiverSlot`, not after. Claiming the slot
> > first left a BARE receiver row behind on the throw…*
>
> **And the bare row is what defeats "forever".** With a receiver row present, run 2 no longer takes
> the additive path at all: `:618`'s `if (!lv || !cv)` is false → the two-sided branch; the B1 guard at
> `:697` does not fire (`cv.summaryMd` is null on a bare row); `reconcileClassA` sees
> local-has-MD / cloud-has-none → `copyToCloud` → `transferClassA`, which writes the key with a plain
> `put` (`:394`) and sets `status: 'promoted'` (`:430`) — **with no servability guard anywhere on that
> path.** The unservable key lands on run 2 and the serve guard 409s forever: the exact end state this
> call site is claimed to prevent.
>
> **Not a regression** — today the same key lands on run 1 instead of run 2 — but **behavior 26 would
> have gone green over an open hole**, because a one-run integration test cannot see run 2. That is
> *"a GREEN gate that tests the wrong schema is worse than a red one"*.
>
> **Fix — and v16 got the SHAPE of it wrong, which round-14 B1 then made Blocking.**
>
> Move the adopt guard **above** `ensureReceiverSlot`, next to the existing WB-H1 check at
> `sync-run.ts:236-238`: no row is created, the video stays one-sided, and the refusal genuinely
> re-fires every run. **That part stands.**
>
> v16 then added a *second call site* on `transferClassA` and behavior 26c called it *"the **second**
> entrance"*. §2.5 of this document enumerates **four**, and round 14 found the third writing the same
> durable state with no guard on any version of this design — see §3.5.1 below. **The fix was the
> pattern this document had already condemned two sections earlier.**

#### 3.5.1 ⛔ ONE ENFORCEMENT POINT — the guard moves to the metadata seam (round-14 B1)

**Round-14 B1, Blocking, classified `mechanism`: `reconcileCloudBase` is a THIRD route to the same
durable state, and it DELETES the servable copy on the way.**

```ts
// reconcile-serial.ts:293-296 — the metadata phase of a base relocation
const patch: Record<string, unknown> = {
  serialNumber: localVideo.serialNumber,
  summaryMd: `${newBase}.md`,
  artifacts: { summaryMd: { key: `${newBase}.md`, status: 'promoted' } },
```

`newBase` is the **vault filename, verbatim** (`:152-154`), validated only by `assertLogicalKey`
(`:267-268`) — which rejects a leading `/`, a `..` segment and `\0`, and says nothing about length,
C0/C1, bidi, or the `.md` suffix. It runs at `sync-run.ts:729-757`, **before** the Class-A guard v16
added at `:780-793`.

**The producer is the one §3.5's own reachability table already names** — a hand-placed or
externally-renamed vault file. The video is then **two-sided**, so `sync-run.ts:618`'s `if (!lv || !cv)`
is false, `copyAdditiveVideo` is never called, and **the adopt guard is bypassed entirely**.
`reconcileCloudBase` copies every paid blob to the unservable base, writes the row above, verifies, and
**deletes the sources** (`:358-361`). The paid summary is then unreachable through serve, download and
share, **with no in-product repair** — a re-serve cannot run, because the serve path refuses before it
reserves.

> **Why this is `mechanism` and not a fourth call site.** §2.5 already states the rule v16 violated:
> *"A rule that must be restated per writer will keep churning in a codebase that keeps growing
> writers."* That sentence retired the branded `CloudSummaryKey` and the homoglyph denylist.
> `isServableSummaryKey` was on its **third** enumeration. And §3.4 had already applied the correct fix
> to the share path one section earlier — *"put the call inside `getShareServeContext` … covered **by
> construction** rather than by enumeration."* **Per-branch discipline for the rules, per-writer
> enumeration for the guards, one section apart, in the same document.**

**THE RULE: the cloud advertisement is guarded at the seam, not at the entrances.**

Every sync-side entrance writes the advertisement through a `MetadataStore` method — **verified by
enumeration, not asserted**:

| Entrance | Row write | Method |
|---|---|---|
| `copyAdditiveVideo` | `sync-run.ts:279` | `upsertVideo` (`:286`) |
| `transferClassA` | `sync-run.ts:399`, `:430` | `updateVideoFields` (`:432`) |
| `reconcileCloudBase` | `reconcile-serial.ts:295-296` | `updateVideoFields` (`:324`) |

> Outside the seam, and correctly so: the **mint** (`lib/job-queue/summary-handler.ts:177`, `:179`)
> writes via the `persistSummary` **RPC**, not `MetadataStore`; the **local** pipeline
> (`pipeline.ts:265`) is not a cloud advertisement and §3.4 argues at length that the local path never
> needed this guard; and `consistency.ts:34`/`:40` is `writeArtifact`, which has **zero production
> callers**. *(Round-15 L3: `:157` is the `summaryMd` field of the record literal, not the persist call.
> The claim was right, the line was not.)*

**In the Supabase adapter, refuse any patch that sets `summaryMd` or `artifacts.summaryMd.status =
'promoted'` to a key failing `isServableSummaryKey`.** Then **the entrance count stops mattering** —
which is the only property that has ever survived contact with this codebase.

##### ⛔ Round-15 M1 — v17 named TWO adapter METHODS, and the adapter has THREE

The entrance count stopped mattering; the **method** count silently took its place. Both halves of
round 15 found `bulkUpdateVideoFields` (`supabase-metadata-store.ts:153-163`), which merges arbitrary
`fields` into `videos.data` through `merge_video_data_bulk` with the same treatment as its two named
siblings. **Neither half graded it above Medium, and both said why**: its only production callers are
`pipeline.ts:339` (playlistIndex / dates) and `serial-migrate-exec.ts:14` (serialNumber), both
structurally local-only — `getStorageBundle()` with no client, and `resolve.ts:56` throws under
`STORAGE_BACKEND=supabase`. **No caller passes `summaryMd` today.** A hole by construction, not a live
defect.

**Do not fix it by adding the third method to the list.** That is the move this document has now made
wrong on three different sets — write entrances, `promote` callers, envelope writers — and §2.5 already
states why: *"a rule that must be restated per writer will keep churning in a codebase that keeps
growing writers."* A list of three is a list.

**THE DOMINATING POINT ALREADY EXISTS, and it is private.** All three data-writing methods pass their
payload through one function, and nothing else calls it — **verified by enumeration over the whole
repo, and it is a `function` declaration in the module body, so it cannot be reached from outside**:

```ts
// lib/storage/supabase/supabase-metadata-store.ts:19  — the ONLY definition
function stripComputed<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'>
// :119  upsertVideo            .update({ data: stripComputed(video) })
// :143  updateVideoFields      p_fields:  stripComputed(fields)
// :160  bulkUpdateVideoFields  p_patches: …fields: stripComputed(x.fields)
```

**The refusal goes there.** Every payload that reaches `videos.data` through this adapter is
constructed by that call, so a fourth method added next year is covered *by construction* — the same
argument §3.4 already used to put the share guard inside `getShareServeContext`, and the same shape as
`serialize()` in §3.6.4. The guard inspects the payload it is handed: refuse if `summaryMd` or
`artifacts.summaryMd.key` is present and fails `isServableSummaryKey`, or if
`artifacts.summaryMd.status === 'promoted'` over an unservable key.

> **⚠ Rename it. A function called `stripComputed` that also refuses writes is a lie by name**, and
> this repo has a ratchet (`scripts/check-vocabulary-collisions.py`) built on the premise that
> vocabulary tracks mechanism. Call it **`videoDataPayload`** — *"the one function that builds what
> lands in `videos.data`"* — which describes both jobs and makes the dominance claim legible at the
> call site. The rename is the load-bearing part of this fix, not cosmetics: `stripComputed` reads as
> optional hygiene, so a future writer skipping it looks harmless.

**THREE placements stay outside the seam, each for a stated reason** *(round-15 H2: v17 said "two",
while four other places in this document — §3.5, behaviors 26/26b and two mutation rows — described an
adopt guard that the "two" excluded. One document, two incompatible instructions, which is exactly the
defect round-12 Codex found in §3.6.3)*:

1. **The mint keeps its own call site**, between `reserveVideoSlot` (`summary-handler.ts:95`) and the
   Gemini call (`:101`), because a refusal there must cost **no money** — §3.5's existing argument.
2. **`reconcileCloudBase` refuses IN MEMORY, before the copy phase**, alongside its existing
   `target-occupied` / `unsupported-artifacts` refusals (`:197`, `:214`). Its own stated pattern is
   *"the smallest correct behaviour: it cannot half-move anything"* — so **no blob is copied and
   nothing is deleted**, rather than relying on the seam to reject after the copy.

   > **Name the variant (round-15 M3).** `SerialReconcileResult` (`reconcile-serial.ts:69-81`) is a
   > **closed union**, and v17 added a refusal without adding a member. Use
   > **`{ ok: false; reason: 'unservable-base'; key: string }`** — `key` matters, because the caller's
   > generic tail already interpolates it (`sync-run.ts:735-757`: `` `…${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}` ``),
   > so a variant carrying `key` produces a usable message with **no change to the caller**. Verified
   > that a new variant works mechanically: generic throw → caught per-video at `:812` → no baseline →
   > re-fires cleanly, not stuck.
   >
   > **And it must name the manual repair, which behavior 26d did not require.** Behavior 26 demands
   > that of the *adopt* error; this is the case an operator is **least** able to diagnose, because the
   > offending name is a **local vault filename** while the error is reported against a **cloud** video.
   > Give 26d the same clause.
3. **The adopt path keeps its call site above `ensureReceiverSlot`** (`sync-run.ts:236-238`) — and it
   is **not** redundant with the seam. Its job is to make the refusal happen *before* `claimVideoSlot`'s
   **durable insert** at `:240`. Delete it and the additive refusal lands at `upsertVideo` (`:286`),
   by which time a bare receiver row exists **and** the MD blob has been staged and promoted (`:263-268`)
   — precisely the state `sync-run.ts:230-235` records as round-2 H-R2-1 and forbids. Round 15 traced
   the consequence: not data loss (run 2 goes two-sided → `transferClassA` → the seam refuses at `:432`),
   but behavior 26's *"no receiver row is created"* would be **false** and every run would accumulate a
   bare row plus one orphan blob.

**Behavior 26c's wording must stop asserting a count.** A behavior that says *"the second entrance"* is
a claim about an enumeration, and this document has been wrong about one eight times.

#### 3.5.2 What a refusal LEAVES BEHIND, per caller (round-13 M2, round-15 M2 — unfixed twice)

*"Refuse in the adapter"* named no outcome in v16 or v17. Both round-15 halves asked for this table
independently, and the round-13 finding it repeats was the same question one layer up. **A refusal is a
branch, and this document's own §3.6.1b says every rule must be stated per branch.**

| Caller | Where the refusal lands | Already durable at that moment | Net state, and does the next run re-enter cleanly? |
|---|---|---|---|
| `copyAdditiveVideo` | **the adopt guard**, above `ensureReceiverSlot` (`sync-run.ts:236-238`) | **nothing** | Video stays one-sided. Throw → caught per-video at `:812` → `report.errors`, **no `writeVideoBaseline`** → re-fires identically every run until a human renames the vault file. ✅ intended |
| `transferClassA` | the seam, `updateVideoFields` (`:432`) | **`loser.blob.put(loser.p, key, staged, …)` already ran at `:394`** | An **orphan blob** at the unservable key on the loser. The loser's row still points at its old key, so **nothing is lost and nothing is unreachable**. Throw → `:812` → no baseline → re-fires, re-writing the same orphan each run. ⚠ **accepted residual, stated below** |
| `reconcileCloudBase` | **in memory**, before the copy phase | **nothing** | Returns a refusal variant → generic throw at `sync-run.ts:735-757` → `:812` → no baseline → re-fires. ✅ clean |

**The accepted residual, stated instead of left silent (round-15 M2.1).** §3.5.1 justifies
`reconcileCloudBase`'s in-memory refusal with *"so no blob is copied and nothing is deleted, rather than
relying on the seam to reject after the copy"* — and then relies on exactly that for `transferClassA`,
twelve lines later, where the `put` at `:394` precedes the row write at `:432`. **The same sentence's
reasoning reaches the opposite conclusion in the same section.** The consequence is genuinely benign —
an orphan at a key nothing advertises, not a lost or unreachable artifact — and hoisting a guard into
`transferClassA` would be a *fourth* per-writer call site, the move this section exists to stop. So it
is **accepted, not overlooked**, and it is written down because an unstated asymmetry reads as an
oversight to the next reviewer and gets "fixed" by enumeration.

**Behavior 26c is direction-dependent and must say so.** On `copyToLocal` the loser is the **local**
store (`sync-run.ts:791-793`), which has no seam guard at all — correctly, per §3.4. A test written
against `copyToLocal` would **pass vacuously**. 26c must name `copyToCloud`.

**`companionTransfer`'s never-throw contract is not at risk.** It writes a blob, not the row
(`sync-run.ts:441-443`), and the `videoId` refusal already returns `{ shareNeedsOwnerServe, error }` per
§3.6.4's table. Under §3.6.4's fix a missing `videoId` is a **compile error**, not a runtime throw.

---

### 3.6 Namespace ownership — REDESIGNED at round 10, after the FIX→REDESIGN escalation

**This section was rewritten, not patched.** Rounds 6–9 each produced a §3.6 finding caused by the
previous round's §3.6 fix. `review-method.md`'s escalation fired at round 8; round 10 was run as a
**design review** instead of a fifth defect hunt. Both halves are on disk:
`docs/reviews/spec-blob-key-encoding-r10-codex-design.md` and `…-s36-design-claude.md`.

**The two halves disagreed**, and the disagreement was adjudicated by measurement, not by preference.

#### 3.6.0 The measurement that decided it — and it invalidates v10

> **MEASURED.** On APFS, overwriting **through an alias preserves the existing directory entry's
> name** and replaces only the bytes. Create `003_팔란티어.md` in NFD, then `renameSync(tmp, <NFC
> path>)` — which is exactly `LocalFsBlobStore.put` (`local-blob-store.ts:18`) and `promote` (`:61`) —
> and `readdir` still returns the **NFD** name while the content is the **NFC** writer's.
> Re-verified independently by the coordinator before adjudicating.

**Therefore the stored name is not evidence of who owns the bytes**, and the protocol produces exactly
that state on its own money path:

| Step | Disk | Local row |
|---|---|---|
| Vault holds video X, stored NFD (`recoverOrphanedVideos` adopts on-disk bytes verbatim, `pipeline.ts:104`) | **NFD** | NFD |
| Cloud minted the same video from the YouTube title (`summary-handler.ts:96`) | — | cloud row **NFC** |
| Class-A transfer cloud→local: `put(loser, key=NFC)`, then the record update sets `summaryMd: key` (`sync-run.ts:394`, `:399`) | **NFD** (name preserved) | **NFC** |
| A later run reaches v10's identity test at the same key | `readdir` → NFD; key → NFC ⇒ **"a different logical key" ⇒ REFUSE** | |

That refusal is **wrong — it is the same video's own file** — and its consequence is round-8 H1
verbatim: every Class-A transfer for that video throws, forever. **v10's fix reintroduces round 8's
finding**, through the very credential chosen to prevent it. It arrived before implementation only
because the escalation rule fired.

#### 3.6.1 What this problem actually is

**Namespace ownership.** The sender proposes a name; the **receiver owns the namespace** and addresses
it by *alias class*, not by byte key. It is a **resumable-create + replication** problem — and four
rounds designed a **lock**.

Two patterns wearing one table, and neither asks v10's question:

| Writer | Pattern | The question it needs answered |
|---|---|---|
| `copyAdditiveVideo` | **idempotent create / resumable** | *"has this already been done?"* — about **content** |
| `transferClassA` | **replication (last-writer-wins)** | *"is this address mine to overwrite?"* — about the **record** |

Neither is *"which byte-form created this directory entry?"* Four rounds hunted a credential for a
question no writer asks.

**Two mechanisms already serve this concern and no earlier version mentioned either:**

- **The vault already has a filename identity function, and it is NFC-equality, not byte equality** —
  `findByNormalizedName` (`serial-migrate-exec.ts:31-45`), called by `resolveOnDisk` for exactly this
  state (*"the index string may differ from the on-disk bytes by Unicode normalization"*, `:53-59`),
  locked in by `tests/lib/serial-migrate-normalization.test.ts:47-53`. **Under the rule this codebase
  already ships, v10's "different logical key that merely aliases" is not a different key at all — it
  is the same file, found.** Two mechanisms for one concern is the shape
  `scripts/check-vocabulary-collisions.py` exists to catch.
- **`copyBlob`'s `already: true` clause** (`blob-store.ts:22-24`) already records the lesson v10 drops:
  *"without it, a fail-closed `destination-exists` would deadlock every retry after a partial
  multi-blob relocation, permanently."* v10's behaviors 18/18c refuse on `EEXIST` with no name
  information, so a crash between `promote` (`sync-run.ts:268`) and `upsertVideo` (`:286`) — receiver
  has the file, no row — makes every subsequent run refuse. **Today's `renameSync` self-heals that
  window; v10 would convert it into a permanently stranded paid artifact.**

**There are FOUR vault writers, not two.** §2.5 records the count as *"1, 1, 1, 1, 2, 3 across six
rounds"*; it is now 4, and one of them is a **delete**:

| # | Writer | Identity it carries |
|---|---|---|
| 1 | `copyAdditiveVideo` (`sync-run.ts:263-268`) | none — no receiver row yet; only the bytes |
| 2 | `transferClassA` (`sync-run.ts:381-394`) | the loser's record, already in the caller's scope (`:781`, `:792`) |
| 3 | `companionTransfer` → `writeModelEnvelope` (`:464`) **and `loser.blob.delete(models/${base}.json)` (`:475`)** | `base` from the winner's `summaryMd` (`:448`) |
| 4 | `reconcile-serial.ts:282`, `:293` | the row being relocated |

**This is the structural finding.** §3.6 was written as *an enumeration of writers with a rule each*,
and this spec has already learned twice that enumeration fails here — the branded `CloudSummaryKey`
was deleted because *"round 7 measured that it did not enumerate them anyway"* (§3.5), and the
homoglyph denylist was replaced by NFKC folding because *"a hand-typed list cannot be complete"*
(§3.4). **A rule restated per writer will keep churning in a codebase that keeps growing writers.**
So: one invariant at the seam, plus one question per *pattern*.

#### 3.6.1b ⚠ EVERY RULE IN §3.6 IS STATED PER BRANCH — the discipline v15 adds

**This is the structural fix, and it targets what has actually been generating findings.** Rounds 11
and 12 produced five §3.6 findings caused by the previous round's fixes. Every one had the same shape:

| Round | Finding | Shape |
|---|---|---|
| 11 | H1 | *what does `promote` do on `EEXIST`?* — a branch of the primitive, unspecified |
| 11 | M1 | R3 has **two** success branches; the residual described one |
| 11 | M2 | `BlobRead` has **four** cases; R2 enumerated three |
| 12 | H2 | `decideCompanion` returns `ship` on **two** branches; the rule covered one |
| 12 | M1 | `SupabaseBlobStore.promote` has **three** success paths; the table described one |

**None says the mechanism is wrong.** Round 12 attacked R1–R4 head-on — no-clobber measured true on
both backends, the alias relation re-derived, `promote`'s caller set and the `resolve.ts` hard-return
confirmed — and it held. What is wrong is that a rule was written against *a function* while the
function has *branches*, and the rule silently claimed the one the author had in mind.

**So: for every rule below, the branches of the function it governs are enumerated and the rule is
stated for each.** Not prose that happens to mention them — a row per branch, with the outcome named.

> This subsystem has already learned this lesson one level up: §3.6 was rewritten against **two
> patterns** instead of N writers because the writer count had been wrong seven times running (§2.5).
> The same discipline was simply never applied to the branches *inside* each pattern.
>
> **Note what this is NOT.** A redesign cannot help here, because **the branches are not owned by this
> design** — `decideCompanion` already has two `ship` branches, `SupabaseBlobStore.promote` already has
> three success paths, `BlobRead` already has four cases. A new shape cannot delete them; it can only
> fail to mention them, which is the defect already in hand. See `review-method.md`, *"It is a
> HEURISTIC, not a fact"*, for why the escalation counter reading **2** is recorded and overridden here
> rather than obeyed or ignored.

**Escalation, recorded rather than argued away:**

> **FIX→REDESIGN counter for §3.6 = 2 (rounds 11, 12). OVERRIDDEN, with a falsifier.**
> **Fires to REDESIGN if round 13 produces a fix-induced §3.6 finding that is a MECHANISM defect —
> the rule cannot be satisfied, a credential is stale, two requirements contradict — rather than a
> branch-coverage gap.** A branch-coverage finding in round 13 confirms this diagnosis and the remedy
> above; a mechanism finding refutes it and the redesign is owed.

#### 3.6.2 The design — attempt the write that cannot clobber; classify only if it fails

**R1 — a NEW primitive, `promoteIfAbsent`. `promote` itself is not touched.**

```
promoteIfAbsent(ref): Promise<void>        // RESOLVES when the final exists; never throws EEXIST
```

> **Round-12 M1 — v14 typed this `'created' | 'already-exists'` and no caller in this spec consumes
> it.** R2 branches entirely on the `tryGet` read-back. The load-bearing property is
> **resolves-rather-than-throws**; a discriminant nobody reads is decoration that invites an
> implementer to trust the label instead of the read. Either give it a consumer or drop it — dropped.

**It RESOLVES when the final object exists — it does not throw** (round-11 H1). `linkSync` *does*
throw `EEXIST` (measured), so the adapter must catch it, leave the occupant untouched, remove the
staging temp **and its `_staging/<uuid>/` tree**, and **resolve**. Without that sentence
an implementer picks the other reading, `copyAdditiveVideo` throws at `sync-run.ts:268`, **R2's whole
classification becomes unreachable**, and the crash-resume window strands the artifact forever — the
exact defect §3.6.1 quotes `copyBlob`'s `already: true` docstring against, re-entering through R1.
`SupabaseBlobStore` already behaves this way, and it conforms by **silently returning**, which is the
evidence for the intended reading.

| Adapter | Implementation |
|---|---|
| `LocalFsBlobStore` | `mkdirSync(dirname)` — **keep it**, `promote` already does it (`:61`) and nested `dig/<base>/<n>.r<V>.md` keys need it — then `link` + `unlink` + **`rmSync(_staging/<uuid>, {recursive:true, force:true})`** |
| `SupabaseBlobStore` | **must change — `:112-116` is only the FIRST of three paths.** See below |
| `InMemoryBlobStore` | its `create-if-absent` semantics, unconditionally |

> **Round-12 Low — the rollout is wider than three adapters.** Anything that `implements BlobStore` or
> is typed as one must gain `promoteIfAbsent` or `tsc` breaks: the decorators
> `FailPromoteBlobStore` (`tests/integration/helpers/cloud.ts:168-184`) and `UnreadableModelBlobStore`
> (`tests/integration/serve-model-unreadable.test.ts:57-79`), and the object literal at
> `tests/lib/storage/consistency.test.ts:38-59`. Not a data-loss path — a predictable implementation
> interruption. **Each fault-injection wrapper must decide explicitly whether its injected `promote`
> fault also applies to `promoteIfAbsent`**; forwarding silently is a decision, and an unexamined one
> would quietly weaken a test that exists to prove a failure is handled.

**MEASURED:** `linkSync` returns `EEXIST` through an NFC/NFD alias *and* a case alias, so the
no-clobber property holds against the whole alias class. *(`linkSync` with a **missing source** returns `ENOENT`, not
`EEXIST`. `promote:60` short-circuits only the *already-promoted* case — `!exists(from) && exists(to)`
— which is **not** the same condition, so `promoteIfAbsent` must handle bare `ENOENT` explicitly rather
than inherit a short-circuit that does not cover it. Round-13 L1; unreachable from R2, which stages
first.)*

> **⚠ Round-12 M1 — v14 said Supabase "already behaves this way". It does not, on two counts.**
> `:112-116` is the first short-circuit; the method continues:
>
> ```ts
> // supabase-blob-store.ts:117-126
> const { error } = await this.b().move(from, to);
> if (error) {
>   if (await this.exists(ref.principal, ref.finalKey)) { await this.b().remove([from]).catch(() => {}); return; }
>   throw error;                                        // <-- does NOT resolve
> }
> ```
>
> **(1) It throws where R1 requires resolve.** MEASURED: `move()` onto an occupied destination returns
> `409 The resource already exists`, so this *is* the Supabase EEXIST path — and it resolves only if the
> `exists()` re-check succeeds. `exists` is `get() !== null` on the one backend documented as unable to
> prove absence (`provesAbsence = false`). A transient 5xx at that moment throws out of
> `copyAdditiveVideo`, R2's classification never runs, and the run reports a per-video error. It
> self-heals next run — which is why Medium, not High — **but it is round-11 H1's defect left standing
> on the other adapter, under a sentence saying it was already handled.**
>
> **(2) Three success paths, one row.** `:113` short-circuit, `:117` move succeeded, `:121`
> move-errored-but-final-present. The adapter changes; *"no change needed"* was never tenable. Round-9 H2's reason for choosing `link` over
`wx` — it preserves `putStaged` → verify → `promote`, so the read-back hash check survives — stands
unchanged.

> ### ⚠ v11 said "`promote` never overwrites, on every adapter". That was wrong three ways.
>
> **1. It changed a shared seam contract having verified one path.** `promote` has **four** non-test
> callers — `sync-run.ts:268`, `summary-handler.ts:178`, `write-dig-section-blob.ts:50`,
> `consistency.ts:37` (zero production callers) — and §3.6 reasoned about one.
>
> **2. The round-10 half whose other recommendation was declined had already predicted it**, in its
> cost section: *"either `promote` grows mode/intent, or a new `promoteExclusive`/`promoteIfAbsent`
> operation is added."* The coordinator adopted the other half's R1 and did not carry that caveat
> across. Recorded because it is this project's own measured lesson — *dual review halves are not
> redundant* — failing at the moment of adjudicating a dual review.
>
> **3. It pointed the convergence at the semantics this repo's own tripwire calls a DEFECT.**
> `tests/lib/dig/write-dig-section-blob-promote.test.ts:58-74` is an `it.failing` tripwire for backlog
> **#22** / architecture-review **W2**: *"a re-dug section keeps its stale body because
> `SupabaseBlobStore.promote` is create-if-absent"* — written so the suite goes **red** when someone
> fixes it, and `InMemoryBlobStore` models both semantics precisely so the suite does not *"bake the
> disagreement in as a truth"*. v11's behavior 18d would have baked it in.
>
> **What the two round-11 halves disagreed about, and the answer.** Codex called this **Blocking —
> R1 breaks paid regeneration**. Claude called it sound, because `summary-handler` and
> `writeDigSectionBlob` can **only ever see Supabase**: `getWorkerStorageBundle` hard-returns
> `new SupabaseBlobStore(...)` with no backend branch (`resolve.ts:81-86`) and is their sole non-test
> source. **Verified by the coordinator: Claude is right — R1 broke no caller.** Their stale-regeneration
> defect is pre-existing (#22) and unaffected.
>
> **So Codex was right about the remedy and wrong about the failure**, and the remedy is adopted for
> Claude's reason instead: a spec that declares *"`promote` is create-if-absent everywhere"* converts a
> tracked bug into a documented invariant and **forecloses fixing #22 in the natural direction** (make
> Supabase overwrite). With `promoteIfAbsent` separate, #22's fix stays available — most likely
> `writeDigSectionBlob` using `put`, as `model-store.ts:46-52` already does.
>
> **Not attributable to this change:** the orphaned `_staging/<uuid>/` directory. `renameSync` leaves
> it too (measured). Worth fixing here; not caused here.

**R2 — additive create: write first, classify only on failure.**

```
putStaged → verify staged hash          (unchanged, sync-run.ts:263-267)
promoteIfAbsent                          // R1: cannot clobber, on either backend; RESOLVES on EEXIST
tryGet(FINAL key)                        // tryGet, NOT get — see below
   ok, hash equals the body → SUCCESS  (we wrote it, or it was already there → crash-resume heals)
   ok, hash differs         → REFUSE   (throw; the occupant is untouched)
   'unreadable'             → REFUSE   (keeps v10's `unreadable ⇒ occupied` rule, which is right)
   'absent'                 → REFUSE   (a FAULT, not a resume: promoteIfAbsent reported success and
                                         the object is not there)
```

> **Round-11 M2 — v11 named no primitive and its classification was not total.** `BlobRead` has
> **four** cases (`blob-store.ts:10-13`) and v11 enumerated three: **`absent` had no branch.** And an
> implementer reaching for `get` instead of `tryGet` gets Supabase collapsing *every* failure into
> `null` (`supabase-blob-store.ts:29-35`) — the exact defect class `tryGet`'s docstring exists to stop
> (*"use this instead of `get` before any irreversible or billable decision"*) — on the read that
> decides whether the row advertises `promoted`.
>
> **Cost (round-11 brief item 5): acceptable, and now stated.** One extra `tryGet` per **created**
> video, not per video. `runSync` is **not** deadline-bounded — its only production entry is the CLI
> (`scripts/cloud-sync.ts:65`). A timeout on the read-back throws *after* a durable promote, leaving
> exactly the crash-resume state R2 heals on the next run.

Three properties v10's shape does not have:

1. **Ordering-proof without an atomicity claim.** Round-6 M1 said check-then-write cannot be made
   correct. Correct — so do not check first. The write goes first and *physically cannot clobber*; the
   read only decides how to **report**. Nothing is destroyed by losing the race, so there is no TOCTOU.
2. **Adapter-independent.** The additive path runs in **both directions** (`sync-run.ts:618-627`).
   v10's rule was expressed in `readdir` and `link`, which the Supabase receiver does not have — so it
   left the local→cloud direction on today's behaviour, where `promote` treats an existing final as
   success and the row then advertises `promoted` **over someone else's bytes** (`:279`). R2 closes
   that hole with the same three lines.
3. **It answers the resumability question**, which name identity structurally cannot.

**R3 — Class-A transfer: the identity question is answered by the loser's RECORD.**
`transferClassA` is required to overwrite, so R1 does not apply and it keeps `put`. The right question
is not *"is the occupant this same logical key?"* but **"is this address the loser's own?"** — and the
caller already holds the answer at both call sites:

```ts
if (!canonicallyEqualName(loserVideo.summaryMd, key)) {
  const dest = await loser.blob.tryGet(loser.p, key);      // only on this branch
  if (dest.ok || dest.reason === 'unreadable') throw …;    // occupied by something we do not own
}
await loser.blob.put(loser.p, key, staged, 'text/markdown');   // unchanged
```

The common path runs **no probe at all** and has no window. A legitimately re-keyed transfer still
works, because a diverged base makes the destination a fresh address. **No atomicity is claimed**:
round-9 M4's residual window survives, scoped honestly to the uncommon branch, and it is identical to
today's unconditional overwrite — a strict improvement, not a fence.

> **Two precisions from round-11 L3, both about what R3 does NOT establish.**
>
> - **`summaryMd` is optional.** The additive-hydration path reaches `copyToLocal` with a loser that
>   has none (`sync-run.ts:701-708`). `canonicallyEqualName(null, key)` is **`false`** → take the probe
>   branch, which finds the address free and writes.
> - **On `copyToCloud` the loser is Supabase, where `absent` means *absent or denied*** —
>   `provesAbsence === false` (`supabase-blob-store.ts:39-62`). R3 proceeds to overwrite on `absent`,
>   which is exactly today's unconditional behaviour and therefore not a regression — **but the fence
>   does not exist in that direction, and this section must not read as if it does.**
>
> Both call sites do hold the loser's record, verified: `copyToCloud` at `:780-782` (loser cloud,
> record `cv` from `:613`, re-read after relocation at `:765`), `copyToLocal` at `:791-793` (loser
> local, record `lv` from `:612`). The new signatures are
> `transferClassA(localSide, cloudSide, lv, cv, id)` and `transferClassA(cloudSide, localSide, cv, lv, id)`.

**R4 — one name-equality function, and it must be a SUBSET of the filesystem's relation.**
**MEASURED** on this volume the alias relation is **canonical equivalence ∪ case folding**: NFD/NFC
alias; `Å` U+212B and `Å` U+00C5 alias (so it is full canonical equivalence, not merely NFC/NFD);
`Ａ` U+FF21 and `A` do **not** (so it is not NFKC); `Case.md` and `case.md` **do**.

> **Being narrower than the filesystem costs availability (a loud refusal). Being wider costs data.
> Never model the filesystem's relation exactly — it is a per-volume property, not a code property.**
> A case-sensitive APFS volume, or Linux CI, has a different one.

`a.normalize('NFC') === b.normalize('NFC')` is a **proper subset**, which is safe in both directions
for a *refusal* decision, and it is the rule `findByNormalizedName` already ships. Lift it into one
exported predicate and have `findByNormalizedName` call it, so the codebase has **one** vault-name
identity function instead of two.

**Which seam owns what** — the answer to *"should `BlobStore` grow an identity primitive?"* is **no**:

| Question | Owner | Why |
|---|---|---|
| *"Are these bytes the ones I meant?"* | `BlobStore` — `tryGet` + hash, already there | content identity is the only identity a blob store has on any backend |
| *"Is this address mine?"* | `sync-run` — the record | ownership is a fact about the record, and the record is not in the store |
| *"Do these two names collide?"* | one vault-name module | a property of two strings; it needs no I/O |

**The `BlobStore` interface never learns about Unicode, and the Supabase adapter is never asked a
question it has no answer to.**

#### 3.6.3 Why the other half's recommendation was declined

The Codex half named the problem well — *"alias-aware receiver-namespace admission"* — and was right
that sync must not reach through the seam into filesystem mechanics. Its remedy was a new **required**
`BlobStore` method, `lookupStoredKey`, returning `{ storedKey, exact }`, with Supabase stipulated to
return `exact: true`.

Declined, because it **wraps a credential that §3.6.0 measures to be stale by construction**. Making
the stale answer a first-class capability propagates it to every adapter and every future caller.
R1–R4 satisfy the same "don't reach through the seam" objection differently: the seam gains a
**new uniform primitive, `promoteIfAbsent`**, while **`promote` stays byte-identical for its existing
callers** (behavior 18d4 is the tripwire).

> ⚠ **Round-12 Medium — this paragraph said the opposite until v14, and the document therefore carried
> two incompatible implementation instructions.** It still read *"the seam gets a stronger uniform
> contract (`promote` is create-if-absent everywhere)"* — v11's rejected wording, left standing when
> R1 was rewritten in v12. An implementer following **this** sentence would have changed
> `LocalFsBlobStore.promote` from overwrite to create-if-absent and reintroduced exactly the stale
> paid-artifact behaviour round 11 found. The lesson is narrow and repeatable: **when a decision is
> reversed, grep for every place that stated the old one** — a rewritten section does not rewrite its
> own cross-references.

> Two further notes recorded so they are not rediscovered. **`list()` already returns `readdir` bytes**
> (`local-blob-store.ts:76`→`:85`), so the interface was never *missing* the credential — it exposed it
> at O(whole tree). That reframes round-9 H1: the issue was never capability, and now it is moot,
> because the credential itself is the wrong one. And had identity been read off `list`, §3.3's
> prefix re-attachment would make Supabase's answer **true by construction rather than by
> observation** — a credential right for the wrong reason, the same trap as `provesAbsence`.

#### 3.6.4 The accepted residual, stated rather than hidden

**Content identity is not key identity.** R2 treats *"the destination already holds exactly these
bytes"* as *"already done"*. Two different logical keys **can** hold byte-identical content, and R2
would then let the receiver's row advertise `promoted` at a file created for another key.

**It is NOT accepted any more — round 11 dissolved it. The residual does not exist.**

v11 accepted it on three reasons, and tagged the third `[ASSUMPTION]`. Round 11 re-verified that
assumption as the brief's highest-value item and **falsified it** — then found the conclusion survives
on a **stronger credential the spec never cited**, at zero cost.

**The falsified reason.** v11 said *"vault names are `${padSerial(serial)}_${slugify(title)}.md`, so two
different videos cannot alias without a serial collision — which the serial-coherence slice
prevents."* Two independent refutations:

- `recoverOrphanedVideos` adopts **any** `*.md` carrying a `video_id` field and sets
  `summaryMd = file` verbatim (`pipeline.ts:104`, `:129-160`), and the serial is not allocated but
  **parsed** — `file.match(/^(\d+)_/)` (`:106-107`) — with **no collision check** before `upsertVideo`
  (`:151-154`). For adopted rows the naming premise simply does not hold, and §3.5 of this same
  document says so two sections earlier.
- There is **no database uniqueness on `serialNumber` at all**: it lives inside `data jsonb`, and
  `videos` constrains only `(playlist_id, video_id)` and `(playlist_id, position)`
  (`0001_core_schema.sql:23-39`).

`review-method.md:87` — *"a safety fence, credential, or invariant may not be designed on an
`[ASSUMPTION]`"* — applied exactly here, and the tag is what made it findable.

**The two credentials that actually hold, both `[VERIFIED]`:**

1. **Every summary body embeds its own video id.** `summary-core.ts:101-116` writes
   `video_id: "${videoId}"` into the frontmatter **unconditionally**, plus `**URL:** ${youtubeUrl}`;
   and `recoverOrphanedVideos` **refuses to adopt a file that lacks one** (`pipeline.ts:148-149`).
   Therefore **two different videos' summary bodies can never be byte-identical**, and R2's
   content-equality test is *transitively an ownership test*. The harm needs two owners ⇒ two videos ⇒
   different bytes.
2. **`ensureReceiverSlot` already refuses the collision before any blob write.** It throws
   `serial collision` when the receiver index holds the sender's `serialNumber` **or** its `summaryMd`
   (`sync-run.ts:203-213`), and it runs at `:240` — *before* `putStaged` at `:263`. **Scope, because
   v14 stated this as a universal and round-12 M2 falsified it:** the guard is a **disjunction** and
   both disjuncts can miss. The serial half needs the *receiver* row to carry a `serialNumber`; the key
   half is **byte** equality, which aliasing forms fail by construction. The falsifier is named in that
   function's own comment twelve lines above (`:199-202`): *"a legacy receiver row carrying
   `003_alpha.md` with **NO** serialNumber."* So credential 2 catches every aliasing collision **against
   a receiver row that carries a serial**; for a legacy no-serial row it does not, and **R2's
   byte-comparison is what refuses there** — which is why the residual stays dissolved on credential 1
   alone. *(Cheap hardening if wanted: `canonicallyEqualName` instead of `===` in the `find` at `:206`
   — one call, and it makes the key half alias-aware, which is what the sentence used to claim.)*

**So the `video_id` escape hatch is NOT required** — the fact it would read is *already inside the
bytes R2 compares*. Reasons 1 and 2 from v11 stand unchanged.

**The falsifier that now matters, recorded because it is live:** *any producer of a vault `.md` that
omits `video_id` frontmatter* — including a re-render or corrections path that rewrites the body.
**Backlog #23 (corrections as deterministic `{from,to}` pairs) is exactly such a path, in flight.**
If that falsifier ever fires, the escape hatch above is the named remedy.

**Second residual: R3 adds a refusal where today there is none**, so a state that used to sync (badly)
now throws. It is per-video, caught by the caller, leaves no partial state, and self-heals once the
address is free — but it is **operator-visible**, and the runbook must say: the receiver holds a file
at an address its record does not claim; identify the owner and re-key or remove it.

**Third: writer 3's `put`/`delete` of `models/${base}.json`** (`sync-run.ts:464`, `:475`) — a
destructive, alias-resolved operation on a **paid** artifact.

> ### ⛔ ROUND-13 H1 FIRED THE ESCALATION FALSIFIER HERE, AND THE CREDENTIAL IS REPLACED
>
> v12 adopted `sourceMd` as the ownership credential and v15 restated it per outcome. **It is stale by
> construction.** `reconcileCloudBase` relocates every paid artifact by **byte copy**, envelope
> included (`reconcile-serial.ts:98`, `:118` → `copy` → `copyBlob`). **MEASURED: that file contains
> zero occurrences of `sourceMd` and never imports `serial-provenance`.** The **local** migration
> rewrites it (`serial-provenance.ts:16`, asserted at `serial-migrate-exec.test.ts:201`); the cloud one
> does not. So after a relocation the envelope at `models/<newBase>.json` still says
> `sourceMd: "<oldBase>.md"` — permanently, until a paid re-serve — and the rule then requires
> `canonicallyEqualName("<oldBase>.md", "<newBase>.md")` → **false** → refuse. **The credential refuses
> the ship it exists to permit**, stickily, and recovery costs money.
>
> Same defect class as round 10's `readdir`: *stale by construction*. Full pass:
> `docs/reviews/spec-blob-key-encoding-credential-design-pass.md`.
>
> **The question was wrong.** *"What proves `models/<base>.json` belongs to `<base>`?"* presumes the
> fact to establish is a relationship between a file and an **address**. MEASURED asymmetry:
>
> ```
> summary body    video_id: "dQw4w9WgXcQ"        summary-core.ts:103   ← an ID
> model envelope  sourceMd:  "003_wk08-intro.md"  model-store.ts:17     ← a NAME
> ```
>
> `ModelEnvelopeSchema` carries **no stable id at all**. The summary was given an identity token; the
> model was given a **provenance** token — *what it was made from* — and then asked an **identity**
> question. `sourceMd` is not stale by accident: **it is the wrong kind of credential**, and both
> alternatives (rewrite at `remap`, or `sourceMdHash`) keep it name- or content-shaped.

**DECISION: add `videoId?: string` to `ModelEnvelopeSchema`.** Ownership becomes
`envelope.videoId === row.videoId` — two immutable ASCII ids. Relocation cannot break it because
nothing in the answer moves. Verified: `serve-doc.ts:174` already has `videoId` as an explicit param of
`resolveMagazineModel` (`:48`, destructured `:70`, already used for `docKey` and the reserve RPC);
`sync-run.ts:464` ships `decision.envelope` wholesale, so it propagates correct by construction.
`model-store.ts:25-26` records that `.strict()` was *"intentionally removed"* so a new field cannot
break an old reader.

**Stated per outcome — with the OUTCOME of a refusal named, which v15 omitted (round-13 M2):**

| Receiver envelope | Rule | On refusal |
|---|---|---|
| carries `videoId`, **differs** from the row's | **refuse** the ship/delete | `return { shareNeedsOwnerServe: true, error: 'companion refused: envelope videoId <x>, row <y>' }` |
| carries `videoId`, **matches** | proceed | — |
| **no `videoId`** (legacy) | **proceed** — cannot prove ownership. Today's behaviour, so not a regression. **Do NOT fall back to `sourceMd`**: round-13 H1 measured it stale by construction, so the fallback would reintroduce the defect for precisely the envelopes least able to survive it | — |
| absent / unreadable / schema-invalid | `readModelEnvelope` returns `null`; no ownership claim is invented | — |

> **⚠ NEVER THROW.** `companionTransfer`'s docstring (`sync-run.ts:441-443`) is explicit: *"Every
> companion write is BEST-EFFORT and never throws (M-R6-1): the caller must still advance the
> baseline."* An implementer reading "refuse" as "throw" is caught by the per-video `catch` at `:812`,
> which **skips `writeVideoBaseline` at `:811`** — the baseline never advances, the run errors every
> time, and `reconcileClassA` returns `'skip'` so nothing retries. M-R6-1's stickiness, reintroduced by
> a word. **This is the branch-coverage class §3.6.1b predicts, found in the fix §3.6.1b shipped
> alongside.**

> ### ⛔ Round-14 H1 + Codex M1 — v16 enumerated the envelope writers and got it wrong, TWICE OVER
>
> **A third production writer exists:** `lib/html-doc/generate.ts:49-60` writes an envelope with
> `sourceMd` and **no `videoId`** — the LOCAL generate path. v16 named only `serve-doc.ts:174` and
> `sync-run.ts:464`.
>
> **And worse, the sync ship ERASES the field.** `sync-run.ts:464` ships `decision.envelope` wholesale,
> which v16 called *"correct by construction"*. It is correct only when the **sender's** envelope
> carries `videoId`. A sender envelope written by `generate.ts` does not — so shipping it **overwrites a
> receiver envelope that had one** with a copy that does not, silently downgrading the receiver from
> provable ownership to the legacy branch.
>
> **This is the same enumeration failure as B1, on a different set** — write entrances (wrong seven
> times), `promote` callers, and now envelope writers.
>
> **v17's answer was `writeModelEnvelope` requires `videoId` — and round 15 made it BLOCKING, because
> that function is not the writer the money goes through.**

> ### ⛔ Round-15 Blocking — the requirement was attached to a NAME, and there are two names
>
> **Found independently by both halves.** There are two exported writers, and the cloud serve path —
> the busiest one, and the one that spends money — calls the other:
>
> | Writer | Calls | Reached by v17's rule? |
> |---|---|---|
> | `lib/html-doc/generate.ts:50` (local generate) | `writeModelEnvelope` | ✅ |
> | `lib/cloud-sync/sync-run.ts:464` (the sync ship) | `writeModelEnvelope` | ✅ |
> | **`lib/html-doc/serve-doc.ts:174` (the cloud serve path)** | **`writeModelEnvelopeWithin`** | ❌ |
>
> **And they cannot be collapsed — this repo has a test that forbids it**, which is what makes this a
> mechanism defect rather than a typo:
>
> ```ts
> // tests/lib/html-doc/serve-bounded-import-guard.test.ts:104-110
> { unbounded: /\bwriteModelEnvelope\b/, bounded: 'writeModelEnvelopeWithin',
>   why: 'awaits the Supabase upload with no bound at all' }
> ```
>
> **Failure scenario.** An implementer follows v17 literally and adds the parameter to
> `writeModelEnvelope`. `tsc` forces `generate.ts` and `sync-run.ts` to supply it; `serve-doc.ts`
> **compiles unchanged**. Every model the serve path writes carries no `videoId`, `companionTransfer`
> takes the legacy *"cannot prove ownership → proceed"* row forever, and the guard added to stop
> `loser.blob.delete(MODEL_KEY(base))` (`sync-run.ts:475`) from destroying a **paid** artifact is inert
> on exactly the path that produces those artifacts. Behavior 18j5 names `serve-doc.ts` as covered, so it
> would go **green** while the stated mechanism does not reach it — satisfiable by hand-editing one call
> site, the thing this rule exists to stop.
>
> **It also falsifies the no-migration argument.** *"Any re-serve rewrites the envelope with `videoId`"*
> is the sentence that lets the 7 legacy prod envelopes close without a backfill, and it is true only if
> the serve writer is the one that changed.

**THE FIX — attach the requirement to the point that DOMINATES the writers, not to a writer.** Both
writers already funnel through one private function, and nothing else calls it (**enumerated over the
whole repo**: `lib/dig/companion-doc.ts:123` defines an unrelated `serialize` for a different type):

```ts
// lib/html-doc/model-store.ts:34 — the only path from an envelope to bytes
function serialize(envelope: ModelEnvelope): Buffer
// :52  writeModelEnvelope        → blobStore.put(…, serialize(envelope), …)
// :73  writeModelEnvelopeWithin  → const bytes = serialize(envelope)
```

**Split the schema by direction, and let the write side carry the requirement:**

| | Schema | `videoId` | Why |
|---|---|---|---|
| **read** — `readModelEnvelope` | `ModelEnvelopeSchema` (unchanged) | `optional()` | The 7 legacy prod envelopes must still parse; §3.6.4's table has a legacy row for them |
| **write** — the parameter type of both writers, validated inside `serialize` | `ModelEnvelopeWriteSchema = ModelEnvelopeSchema.extend({ videoId: z.string().min(1) })` | **required** | No writer, present or future, can produce bytes without it |

This is stronger than either reviewer's proposed fix, and the difference is the failure mode it catches:

- **Type-level**, because `serialize` accepts only `ModelEnvelopeWrite`, so *any* writer function must
  take that type to reach it — **`tsc` catches an omission at every call site, including a fourth writer
  added later**. A required parameter on two named functions would not.
- **Runtime**, because `serialize` still `.parse()`s — an `as never` cast or a JS caller fails loud, and
  it fails **before any write**, which `writeModelEnvelopeWithin:73` already relies on.
- **The mutation row changes accordingly**: *"make the `videoId` parameter optional"* becomes
  *"relax `ModelEnvelopeWriteSchema` to `.optional()`"* — one edit, one place, and it must go red.

Each writer's source for the value, checked: `generate.ts` has the video in scope; `serve-doc.ts` has
`videoId` as an explicit param of `resolveMagazineModel` (`:48`, destructured `:70`, already used for
`docKey` and the reserve RPC); and the sync ship must **stamp the receiver's `videoId`** rather than
ship `decision.envelope` wholesale — it is shipping a model for a known video and it knows which one.

**Self-healing:** any re-serve rewrites the envelope through `serve-doc.ts:174` — **which is
`writeModelEnvelopeWithin`, and is covered because it calls `serialize`** — so the 7 legacy prod
envelopes close without a migration.

**`sourceMd` is not deleted** — it remains provenance, used by the freshness guard and the footer. It
simply stops being asked an ownership question.

**Does NOT close:** the model is still *addressed* by a mutable `base`, so relocation still happens and
`remap` still runs. Only `videos/<videoId>/<generationId>/model.json` removes that — the **parked**
`2026-08-03-stable-blob-addressing-design.md`. This buys the correctness without the migration; it does
not make that work unnecessary.
### 3.7 Unchanged — except one line of `slugify`

⚠ **`lib/slugify.ts` is NO LONGER unchanged** (round-12 H1): its `.slice(0, 60)` must not leave an
orphaned surrogate half. One line, a defect repair rather than a naming change — see §3.2. Everything
else here still holds: `summaryMd` as the logical name; the verbatim key copy in sync; `remap()`.
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

### 4.1 ✅ The gate RAN and PASSED — 2026-08-14, against prod

The two grants (`grant usage on schema storage to claude_ro;`,
`grant select on storage.objects to claude_ro;`) were applied by the user on **2026-08-14**, and the
gate was executed the same day as `claude_ro`, read-only, with `-v ON_ERROR_STOP=1`, **exit code 0**:

```
objects_total                                    19
§4 gate  (segments after the first two ∉ SAFE)   0 rows      ← PASSES
would_change under NFKC | non_ascii | total      0 | 0 | 19
```

**No migration is needed.** Every existing object name is within `SAFE`, so the encoder changes no
key already in the bucket.

> **Reachability was asserted first**, because this gate's whole failure mode is reporting a pass it
> could not have earned: query 0 returns the object count, and the run is only meaningful if that
> count is non-zero. The first attempt at this gate, before the grants, reported a **false pass**
> because an errored query printed a header and no rows.
>
> ⚠ **Scope, stated so the tick is not read as wider than it is.** 19 objects, `artifacts` bucket,
> **verified against prod as of 2026-08-14 (release v6)**. It is a claim about the bucket *today*, not
> a standing invariant — anything ingested after this date is covered by the encoder itself, which is
> the point of the design. The non-ASCII half of the result is unsurprising (Storage rejects those
> keys — that is backlog #36); **the load-bearing half is that none of the five characters Storage
> accepts but `SAFE` excludes — space, `(`, `)`, `+`, `=` — appears in any existing name.**

---

## 5. Behaviors

| # | Behavior | By |
|---|---|---|
| 1 | A `SAFE` key ≤ `LIMIT` encodes to itself byte-identically | unit + property |
| 2 | A non-ASCII key encodes to an accepted physical key | unit + integration |
| 3 | NFC and NFD forms encode to **different** keys, each round-tripping | unit |
| 4 | Identity-branch and hash-branch outputs are **disjoint** (`=` ∉ `SAFE`), and the hash branch is deterministic and collision-**resistant** at its 132-bit truncation — *not* injective over an unbounded domain, which §3.2 already retracts (round-13 Codex L1) | property + crafted marker preimage |
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
| 16 | **A title with a space, an emoji, or an astral letter at the `slice(60)` boundary ingests and serves 200** — no fallback, no refusal, and the vault filename stays readable **and well-formed on disk** (`readdir` returns the key byte-for-byte, no U+FFFD) | integration, real FS |
| 16b | `slugify` never returns ill-formed UTF-16 — the orphaned surrogate half is dropped | property |
| 16c | The guard **rejects** an ill-formed key, and C1 controls (U+0080–U+009F) as well as C0 | unit |
| 17 | `nested/foo.md`, `%2f`, `／`, `℀.md`, `001_a．．b.md`, `001_a..b.md`, a control char, a bidi override, and a 200-char base are all **rejected** by the guard | unit |
| 17e | **Every code point matching `/\p{Bidi_Control}/u` is rejected** — a derivation over the property, **not** an assertion that exactly 12 are. Includes `U+061C`, `U+200E`, `U+200F`, the three v9 missed; a 13th control added by a future Unicode release is covered automatically instead of turning an upstream update into a red suite (round-14 L1, round-15 Low) | property |
| 17d | The guard inspects the **name**, not `name + '.md'`: `003_lesson-1..md` (a trailing dot in the name) is **accepted**, and no folded-at-the-joint `..` can arise | unit |
| 17b | Total key lengths **129, 130 and 131 are ACCEPTED** — the bound did not narrow (round-9 H3) | unit |
| 18 | Additive create: the occupant is **byte-identical** under the aliasing form → **SUCCEEDS**, file untouched, stored name preserved. *(This is the crash-resume case v10 would have stalled on forever.)* | integration, real FS |
| 18b | Additive create: the occupant has **different bytes** → **REFUSES**; the occupant is intact | integration, real FS |
| 18c | Additive create on the **cloud** receiver: the final key already holds different bytes → **REFUSES** instead of advertising `promoted` over someone else's bytes | integration |
| 18c2 | Additive create when the read-back is **`absent`** → **REFUSES** (a fault, not a resume) | unit |
| 18j | `companionTransfer` **refuses** ship/delete when the receiver envelope's **`videoId`** differs from the row's — and **returns an `error`, never throws**, so the baseline still advances (round-13 M2) | integration |
| 18j2 | `companionTransfer` **ships** when the receiver read is `none` or `unknown` — no envelope, and the common case (round-12 H2) | integration |
| 18j3 | **After a cloud base relocation, the ship still succeeds** — the credential survives `remap` (round-13 H1) | integration |
| 18j4 | An envelope with **no `videoId`** (legacy) proceeds, and **`sourceMd` is not consulted** | integration |
| 18j5 | **No envelope can be serialized without `videoId`** — `serialize` validates `ModelEnvelopeWriteSchema`, so it holds for **both** writers rather than for a list of writer names. Asserted **through `serve-doc.ts` specifically** (`writeModelEnvelopeWithin`), which is the writer v17's rule missed (round-15 Blocking) | unit |
| 18j5b | **Reading a legacy envelope with no `videoId` still succeeds** — the read schema keeps it optional, so the 7 prod envelopes parse and take 18j4's branch. *(Without this, the write-side requirement would silently become a read-side one and orphan them.)* | unit |
| 18j6 | The sync ship **stamps the receiver's `videoId`**; shipping never downgrades a receiver envelope that had one to a copy that does not | integration |
| 18k | `canonicallyEqualName(null, key)` is **`false`**, so a loser with no `summaryMd` takes the probe branch (round-11 L3) | unit |
| 18d | **`promoteIfAbsent` leaves the occupant's bytes unchanged — on all three adapters** | contract |
| 18d2 | **`promoteIfAbsent` RESOLVES rather than throwing** on an already-existing final, and removes the staging temp **and its whole `_staging/<uuid>/` tree** (round-11 H1, round-13 M1/M3) | contract |
| 18d3 | `promoteIfAbsent` creates missing parent directories **and leaves no `_staging/<uuid>/` tree** — staged with a **nested** `dig/<base>/<n>.r<V>.md` key, so 18d2 and 18d3 are exercised together. **MEASURED round-13 M3: a plain `rmdir` here is `ENOTEMPTY` on exactly the branch 18d3 exists to test** | unit |
| 18d4 | `promote` is **unchanged** — its existing callers' behaviour is byte-identical before and after this slice | contract |
| 18d5 | Every `BlobStore` implementer — including the two test decorators and the object fake — implements or forwards `promoteIfAbsent`, and each fault-injection wrapper states whether its injected fault applies to it | contract |
| 18e | The `putStaged` → **verify (read-back hash)** → `promote` protocol still runs on the additive path | integration |
| 18f | **`promoteIfAbsent`** leaves no orphaned `_staging/<uuid>/` tree behind. *(Round-13 L2 / Codex M2: v15 named `promote` here, contradicting 18d4's "`promote` is unchanged" — today's `promote` leaks it too, and that pre-existing leak is out of this slice's scope.)* | unit |
| 18g | Class-A: the loser's row **names this address** → **overwrites**. *(Class-A sync still works — round-8 H1 stays fixed.)* | integration |
| 18h | Class-A: the loser's row names a **different** address and the destination is **occupied** → **REFUSES**; **unoccupied** → **writes** | integration |
| 18i | `canonicallyEqualName` is a **proper subset** of the volume's alias relation: NFC/NFD equal; `Ａ`(U+FF21) vs `A` **not** equal; and the one identity function is shared with `findByNormalizedName` | unit |
| 19 | The receiver-read guard treats an `unreadable` read as **occupied** | unit |

**All fixtures with two normalization forms are built with `.normalize('NFC')`/`.normalize('NFD')`,
never as two source literals** — v10's rule, kept verbatim, and now doubly motivated: this spec has
shipped three invisible-character defects.
| 20 | The §4 gate's SQL predicate derives from the encoder module | check script |
| 21 | The **share** path rejects a non-servable `mdKey` inside `getShareServeContext`, so **both** `base` derivations (`route.ts:69` and `:78`) are covered | integration |
| 23 | **A title ending in `U+2488`–`U+249B` or `U+1F100` ingests and serves 200** — the round-11 B1 class | integration |
| 24 | A key of 68 code points / 132 UTF-16 units (astral letters) is **ACCEPTED** — the bound counts code points (round-11 M3) | unit |
| 25 | **The mint refuses a non-servable key** — after `reserveVideoSlot`, before the Gemini call, so no money moves | integration |
| 26 | **The adopt refuses a non-servable key before `ensureReceiverSlot`** — no receiver row is created — and the error message names the manual repair | integration |
| 26b | **The refusal survives a SECOND run**: re-running sync does not route around it via the two-sided Class-A path (round-13 H2) | integration |
| 26c | **The Supabase adapter refuses** any patch setting `summaryMd` / `status:'promoted'` to a non-servable key — asserted through **each** of `copyAdditiveVideo`, `transferClassA` (on **`copyToCloud`**; see 26c3) and `reconcileCloudBase`, and stated with **no claim about how many entrances exist** | integration |
| 26c2 | **The refusal holds for `bulkUpdateVideoFields` too** — the third data-writing adapter method, which no version before v18 covered. It is reached because the guard lives in `videoDataPayload`, not because the method was added to a list (round-15 M1) | integration |
| 26c3 | **26c's `transferClassA` case is asserted on `copyToCloud`, and a `copyToLocal` variant asserts the local store is NOT guarded** — on `copyToLocal` the loser is the local store, so a test written against it would **pass vacuously** (round-15 M2.2) | integration |
| 26c4 | **After a `transferClassA` refusal the loser's row still points at its OLD key** and the old blob reads back — the accepted residual is an orphan at the unservable key, *not* a lost or unreachable artifact (§3.5.2) | integration |
| 26d | **A base relocation onto an unservable vault name is refused IN MEMORY**: no blob is copied, the old base is **intact**, nothing is deleted, the result is `{ ok:false, reason:'unservable-base', key }`, **and the message names the manual repair** — the offending name is a *local vault filename* while the error is reported against a *cloud* video (round-14 B1, round-15 M3) | integration |
| 27 | **No `slugify` output fails `isServableSummaryKey`** — the cross-derivation §3.4 and §3.5 each assumed and neither checked | property |
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
| Skip the NFKC-folded pass in `isServableSummaryKey` | 17 (`℀.md`, `／` homoglyphs) | PROVISIONAL |
| Narrow the length bound from 131 to 128 | **17b** | PROVISIONAL |
| Drop the bidi-control rejection | 17, **17e** | PROVISIONAL |
| Replace `/\p{Bidi_Control}/u` with a hand-typed class equal to it today | **17e** stays green — and that is the point: the mutation the *claim* needs is a Unicode release, which no suite can run. Kept as a stated LIMIT, not a row that passes | ⚠ UNMUTATABLE |
| Revert the guard to the `\p{L}\p{N}` allowlist | 15 (NFD accented Latin 409s) | PROVISIONAL |
| Replace `link` with `rename` in `promoteIfAbsent` | **18d** — contract level, red on **all three** adapters | PROVISIONAL |
| Make `promoteIfAbsent` rethrow `EEXIST` instead of resolving | **18d2** — and 18 (crash-resume) | PROVISIONAL |
| Drop the `mkdirSync` from `promoteIfAbsent` | 18d3 | PROVISIONAL |
| Change `promote` to create-if-absent on local | **18d4** | PROVISIONAL |
| Classify a read-back `absent` as `equal` | **18c2** | PROVISIONAL |
| Use `get` instead of `tryGet` for the read-back | 18c2 (Supabase collapses every failure to `null`) | PROVISIONAL |
| Drop the `videoId` check in `companionTransfer` (envelope-present branch) | 18j | PROVISIONAL |
| Apply the check on the `none`/`unknown` branches too | **18j2** — ship-into-empty must still ship | PROVISIONAL |
| Make the refusal **throw** instead of returning an error | 18j — and a behavior asserting the baseline advances | PROVISIONAL |
| Fall back to `sourceMd` when `videoId` is absent | **18j3** — goes red after a relocation | PROVISIONAL |
| Stop writing `videoId` in any one writer | 18j5 | PROVISIONAL |
| Route the serve path through a writer that bypasses `serialize` | **18j5** — the round-15 Blocking, reproduced as a mutation | PROVISIONAL |
| Make the sync ship copy the sender's envelope verbatim | **18j6** — the erasure | PROVISIONAL |
| Relax `ModelEnvelopeWriteSchema`'s `videoId` to `.optional()` | 18j5 — one edit, one place, and it must go red for **both** writers (v17's row named a parameter on one function, so it could not express this) | PROVISIONAL |
| Make the **read** schema require `videoId` | **18j5b** — the 7 legacy prod envelopes stop parsing, which is the migration this design exists to avoid | PROVISIONAL |
| Make `promoteIfAbsent` throw on Supabase's `409` path | 18d2 | PROVISIONAL |
| Remove the `isWellFormed()` check from the guard | **16c** | PROVISIONAL |
| Revert `slugify`'s orphaned-surrogate trim | **16b**, and 16 (mojibake on disk) | PROVISIONAL |
| Narrow the control-character class back to C0+DEL | 16c (U+0080–U+009F admitted) | PROVISIONAL |
| Fold the **glued key** instead of the name (`[key, key.normalize('NFKC')]`) | **23** (`003_lesson-⒈.md` refused) — the v12 defect | PROVISIONAL |
| Drop `s.includes('..')` from the name check | **17** (`001_a．．b.md` admitted) — the v12 over-correction | PROVISIONAL |
| Count `key.length` instead of code points | **24** | PROVISIONAL |
| Remove the mint guard call | 25 | PROVISIONAL |
| Remove the adopt guard call | 26 | PROVISIONAL |
| Move the adopt guard back BELOW `ensureReceiverSlot` | **26b** — the bare row routes run 2 around it | PROVISIONAL |
| Remove the seam refusal from `videoDataPayload` | 26c — red via **all three** entrances **and** 26c2 | PROVISIONAL |
| Guard `upsertVideo` + `updateVideoFields` only, leaving `bulkUpdateVideoFields` unguarded | **26c2** — v17's exact defect, reproduced as a mutation | PROVISIONAL |
| Assert 26c's `transferClassA` case on `copyToLocal` instead of `copyToCloud` | **26c3** — the vacuous-pass shape; without 26c3 this mutation is invisible | PROVISIONAL |
| Remove `reconcileCloudBase`'s in-memory refusal | **26d** — the copy-then-delete runs | PROVISIONAL |
| Return an existing variant (`metadata-failed`) instead of `unservable-base` | **26d** — the operator message stops naming the vault filename, which is the only actionable fact in it | PROVISIONAL |
| Skip the read-back hash verify before promote | 18e | PROVISIONAL |
| Make additive create refuse on byte-**identical** occupancy | **18** — the crash-resume regression | PROVISIONAL |
| Make additive create succeed on byte-**different** occupancy | 18b | PROVISIONAL |
| Skip the cloud receiver's post-promote read-back | 18c | PROVISIONAL |
| Drop `transferClassA`'s loser-record check | 18h | PROVISIONAL |
| Widen `canonicallyEqualName` to NFKC | 18i | PROVISIONAL |
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
| An existing prod key uses ` `, `(`, `)`, `+` or `=` | ✅ **MEASURED 2026-08-14 against prod: none does** (§4.1). Gate ran as `claude_ro`, exit 0, 0 rows |
| An existing prod key is **129–131 characters** | **Dissolved, not gated** — v10 keeps the bound at 131, so the guard is a strict widening in every dimension (round-9 H3). This row exists because v9 would have needed a gate the §4 SQL structurally could not provide: its predicate is a character class with no length term |
| Widening the guard is security-relevant | It is a **denylist of separators**, strictly narrower in what it permits through than the local path already permits. The backstops are named per path in §3.4 — `assertLogicalKey` on cloud, `assertIndexRelPathWithin` on local; they are **not** the same guard. **Needs a security reviewer at the PR** |
| A key that syncs and stores can still be unservable | Real, pre-existing, and **not closed by the encoder** — see the §3.5 correction. **v18 guards it at two dominating points** — `videoDataPayload` in the Supabase adapter (§3.5.1) plus three stated placements outside it, and `serialize` in the model store (§3.6.4) — rather than at a list of writers. *(Round-15 L2: this row still described v10's "the mint and adopt call sites", a design three versions dead.)* The `raw/` nested-`summaryMd` shape stays an open pre-existing gap with no known producer |
| A ninth premise is wrong | §1.1 exists so the next reviewer attacks the premises first — that is where seven rounds were spent. P3's falsifier has already fired once (round-9 L1) |
