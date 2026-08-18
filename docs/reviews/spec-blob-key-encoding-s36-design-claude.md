# §3.6 — DESIGN REVIEW of the vault write protocol (Claude half)

**Subject:** §3.6 of `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` (**v10**),
working tree, branch `fix/cloud-blob-key-encoding`. Phase 1, no code written.
**Trigger:** `docs/review-method.md:45-46` — four consecutive rounds of §3.6 findings caused by the
previous round's fixes. This is a design review, not a defect hunt.

Premise tags per `review-method.md:80-90`. Everything marked `[VERIFIED]` was read from the current
working tree **this round**; everything marked `[MEASURED]` was run on real APFS this round (probe
transcripts in the appendix; all scratch under `/tmp`, removed).

---

## Verdict in one table

| The brief asked for | Answer |
|---|---|
| **1. A name for the problem** | **Namespace ownership.** The sender proposes a name; the receiver owns the namespace and addresses it by *alias class*, not by byte key. It is a resumable-create + replication problem, not a mutual-exclusion problem — and four rounds designed a lock |
| **2. Recommended shape** | **Attempt the write that cannot clobber; classify only if it fails.** Three rules, each answered by something the writer *already holds*: the seam (`promote` never overwrites — on every adapter), the bytes (additive create), the record (Class-A) |
| **3. Cost** | One adapter behaviour change (`LocalFsBlobStore.promote`), one argument added to `transferClassA`, one 3-line name-equality helper lifted from existing code, ~6 tests. **No new `BlobStore` method.** No change to §3.1–§3.5 |
| **4. Strongest argument against** | Content identity is not key identity: two different logical keys can hold identical bytes, and my additive rule would call that "already done" where `readdir` would not |
| **5. Keep v10's `readdir` + `link`/`unlink`?** | **`readdir`: REPLACE.** It is a second, contradictory identity function for a namespace that already has one, it is stale by construction on the path that creates the divergence, and it makes a false refusal on the money path. **`link`/`unlink`: KEEP**, re-motivated — not as an identity test (it is not one) but as the no-clobber durable write that makes `promote` mean the same thing on both adapters |

---

## 0. The one measurement that decides this

Everything below turns on this, and no round measured it:

> **`[MEASURED]` On APFS, overwriting through an alias PRESERVES the existing directory entry's name
> and replaces only the bytes.** Create `003_팔란티어.md` in NFD, then `renameSync(tmp, <NFC path>)`
> — the stored name is still NFD and the content is the new bytes. `LocalFsBlobStore.put` is exactly
> `writeFileSync(tmp)` + `renameSync(tmp, dest)` `[VERIFIED: lib/storage/local/local-blob-store.ts:18]`,
> and `promote` is `renameSync(from, to)` `[VERIFIED: :61]`. So both local durable writes have this
> property today.

Two consequences, in opposite directions.

**Good news, free:** user decision ① — *the vault wins; local filenames keep their Unicode* — is
already upheld by the filesystem itself, on every existing write path, with zero code. Nothing in
this spec threatens it.

**The decisive one:** *the stored name is not evidence of who owns the bytes.* After any overwrite
through an alias, the directory entry carries the name of a writer that no longer owns the content.
And the protocol produces exactly that state on its own money path:

| Step | State |
|---|---|
| Vault holds video X's summary, stored NFD (`recoverOrphanedVideos` adopts the on-disk bytes verbatim: `summaryMd = file` `[VERIFIED: lib/pipeline.ts:104,137,148]`) | disk **NFD**, local row **NFD** |
| Cloud minted the same video from the YouTube title: `${padSerial(serial)}_${slugify(title)}.md` `[VERIFIED: lib/job-queue/summary-handler.ts:96,157]` | cloud row **NFC** |
| Class-A transfer cloud→local: `put(loser, key=NFC)` then the record update sets `summaryMd: key` `[VERIFIED: lib/cloud-sync/sync-run.ts:394, 399, 430, 432]` | disk **NFD** (name preserved, `[MEASURED]`), local row **NFC** |
| A later run reaches §3.6's identity test at the same key | `readdir` returns **NFD**, the key is **NFC** → v10 behavior 18b concludes *"a different logical key that merely aliases"* → **REFUSE** |

That refusal is wrong: it is the same video's own file. And its consequence is round-8 H1 verbatim —
*every Class-A transfer for that video throws, forever* — re-entering through the credential chosen
to prevent it. **Round 9's fix reintroduces round 8's finding**, which would have made this the fifth
consecutive round of the escalation pattern. It is arriving before implementation only because the
rule fired.

---

## 1. What this problem actually is

`review-method.md:56-68` gives a design review three questions. Answering them is most of the work.

### 1.1 What already serves this concern?

**Two things, both in production, and §3.6 mentions neither.**

**(a) The vault already has an identity function for filenames, and it is NFC-equality — not byte
equality.** `[VERIFIED: lib/serial-migrate-exec.ts:31-45]`

```ts
export function findByNormalizedName(dir: string, relPath: string): string | null {
  const targetNfc = path.basename(relPath).normalize('NFC');
  ...
  for (const entry of entries) {
    if (entry.normalize('NFC') === targetNfc) return path.join(scanDir, entry);
  }
```

`resolveOnDisk` calls it as the fallback for exactly the state §3.6 is about — *"the index string may
differ from the on-disk bytes by Unicode normalization"* `[VERIFIED: :53-59]` — and
`tests/lib/serial-migrate-normalization.test.ts:47-53` locks the behaviour in. **Under the identity
function this codebase already ships, "a different logical key that merely aliases" is not a different
key at all: it is the same file, found.** v10 proposes the exact opposite rule (`readdir` byte
comparison) for the same directory. Two mechanisms, one concern — the shape
`scripts/check-vocabulary-collisions.py` exists to catch.

**(b) The classification v10 needs already exists, written once, with the lesson attached.**
`[VERIFIED: lib/storage/blob-store.ts:22-24, 143-153]`

```
 *  `already: true` means the destination was PROVEN to hold byte-identical content. It is not a
 *  convenience: without it, a fail-closed `destination-exists` would deadlock every retry after a
 *  partial multi-blob relocation, permanently — the first blob would abort every subsequent run.
```

v10 re-derives this protocol for the additive path and **drops that clause**. Behavior 18 says
`copyAdditiveVideo` refuses an occupied alias; 18c says the occupancy test and the write are one
operation (`link`), which yields `EEXIST` and no name information. So a crash in the window between
`promote` `[VERIFIED: sync-run.ts:268]` and `upsertVideo` `[VERIFIED: :286]` — receiver has the file,
no row — makes the next run take the additive path again, hit `EEXIST`, and refuse. **Every run,
forever.** Today's `renameSync` promote self-heals that window silently. v10 converts a self-healing
crash window into a permanently stranded paid artifact, and the codebase had already written down why.

### 1.2 Which coordination pattern is this?

Not mutual exclusion. Two different patterns wearing one table:

| Writer | Pattern | The question it needs answered |
|---|---|---|
| `copyAdditiveVideo` | **idempotent create / resumable** | *"has this already been done?"* — a question about **content**, not names |
| `transferClassA` | **replication (last-writer-wins)** | *"is this address mine to overwrite?"* — a question about the **record**, not names |

Neither question is *"which byte-form created this directory entry?"* Four rounds hunted a credential
for a question no writer asks. `review-method.md:66-68` already names this failure for the previous
spec — *"one four-minute read (`sync-run.ts:380-394` — sync replicates, it does not produce) would
have ended the credential search on day one."* Same file, same lesson, one layer down.

### 1.3 Who are the writers, and what identity does each carry?

v10's table has two rows. `[VERIFIED]` today there are **four**, and one of them is a *delete*:

| # | Writer | Identity it carries | In v10's table? |
|---|---|---|---|
| 1 | `copyAdditiveVideo` `sync-run.ts:263-268` | none (no receiver row yet) — only the bytes | yes |
| 2 | `transferClassA` `sync-run.ts:381-394` | the loser's record, held by the caller `[VERIFIED: :781, :792 — both `lv` and `cv` are in scope]` | yes |
| 3 | `companionTransfer` → `writeModelEnvelope(loser…)` `sync-run.ts:464` → `put(models/${base}.json)` `[VERIFIED: lib/html-doc/model-store.ts:32,46-52]`, **and `loser.blob.delete(models/${base}.json)` at `sync-run.ts:475`** | `base = winnerVideo.summaryMd.replace(/\.md$/,'')` `[VERIFIED: :448]` | **no** |
| 4 | `reconcile-serial.ts:282,293` — copy old base → new base, then re-point the row | the row being relocated | **no** |

Writer 3 matters: after the encoder, `base` can be non-ASCII, so on a local receiver a **delete** is
addressed by a name that resolves through the alias — and the model is a paid artifact. The
exposure is created by this change on the same argument the brief uses for §3.6 itself.

**This is the structural finding.** §3.6 is written as an *enumeration of writers with a rule each*,
and this spec has already learned twice that enumeration fails here: the branded `CloudSummaryKey`
was deleted because *"round 7 measured that it did not enumerate them anyway"* (§3.5), and the
homoglyph denylist was replaced with NFKC folding because *"a hand-typed homoglyph list cannot be
complete"* (§3.4). §2.5 records the writer count as *"1, 1, 1, 1, 2, 3 across six rounds."* It is now
4. **A rule that must be restated per writer will keep churning in a codebase that keeps growing
writers.** The fix is one invariant at the seam plus one question per *pattern* — two rules, not four.

---

## 2. Recommended shape — *attempt the write that cannot clobber; classify only if it fails*

Four rules. None of them asks the filesystem which name created an entry.

### R1 — the seam: `promote` never overwrites an existing final object. On every adapter.

This is not a new contract. It is **the contract already written down**, which one adapter violates:

- `[VERIFIED: lib/html-doc/model-store.ts:43]` — *"(The staged→promote protocol is **create-if-absent**
  and stays on the BlobStore for the worker's multi-blob MD commit…)"*
- `[VERIFIED: lib/storage/supabase/supabase-blob-store.ts:112-116]` — Supabase already conforms:
  *"Idempotent: if final already present, ensure temp gone and return."*
- `[VERIFIED: lib/storage/local/local-blob-store.ts:58-62]` — LocalFs does **not**: `renameSync`
  overwrites, and `[MEASURED]` it overwrites *through the alias* while keeping the old stored name.

So R1 converges two adapters that already disagree about what `promote` means — which is the named
remedy for architecture-review finding #2, quoted in the seam's own docstring
`[VERIFIED: lib/storage/blob-store.ts:116-124]`. **Cost: negative.** v10's `link` + `unlink` is
exactly the right primitive for it, and round-9 H2's reasoning for choosing `link` over `wx` (the
staged→verify protocol survives) is correct and survives here unchanged.

`[MEASURED]` `linkSync` returns `EEXIST` through an NFC/NFD alias and through a case alias, so on
APFS the no-clobber property holds against the *whole* alias class, not just the byte key.

### R2 — additive create: write first, classify only on failure

```
putStaged → verify staged hash (unchanged, sync-run.ts:263-267)
promote                                  // R1: cannot clobber, on either backend
read back the FINAL key, hash it
   equal to the body   → SUCCESS   (we wrote it, or it was already there → crash-resume heals)
   different           → REFUSE    (throw; nothing was touched — the occupant is intact)
   unreadable          → REFUSE    (keeps v10's `unreadable ⇒ occupied` rule, which is right)
```

`[MEASURED]` on real APFS, all three branches, with an NFD occupant and an NFC write and vice versa —
transcript in the appendix. Case 1 (same bytes under the aliasing form) → proceeds, file untouched,
stored name preserved. Case 2 (foreign occupant, different bytes) → refuses, victim intact.

Three properties v10's shape does not have:

1. **It is ordering-proof without an atomicity claim.** Round-6 M1 said check-then-write cannot be
   made correct. Correct — so don't. The write goes *first* and physically cannot clobber; the read
   is only deciding how to *report*. There is no TOCTOU window because nothing is destroyed by losing
   the race.
2. **It is adapter-independent.** The additive path runs in **both** directions
   `[VERIFIED: sync-run.ts:618-627]`. v10's rule is expressed in `readdir` and `link`, which the
   Supabase receiver does not have — so v10 leaves the local→cloud direction on today's behaviour,
   where `promote` treats an existing final as success `[VERIFIED: supabase-blob-store.ts:113-116]`
   and the row then advertises `promoted` over **someone else's bytes**
   `[VERIFIED: sync-run.ts:279, 298-303]`. R2 closes that with the same three lines.
3. **It answers the resumability question**, which name identity structurally cannot.

*Optional strengthening (see §4):* on the "equal" branch, also require the occupant's `video_id`
frontmatter to match `[VERIFIED: lib/pipeline.ts:148 — every vault summary carries one]`. That is a
strictly more precise credential than `readdir`, because it answers *"whose summary is this?"* rather
than a proxy for it.

### R3 — Class-A transfer: the identity question is answered by the loser's record

`transferClassA` is *required* to overwrite `[VERIFIED: sync-run.ts:386-394]`, so R1 does not apply —
it keeps `put`. The deciding question, *"is the occupant this same logical key?"*, is the wrong
question; the right one is **"is this address the loser's own?"**, and the caller is already holding
the answer:

```ts
// caller passes the loser's record — available at both call sites (sync-run.ts:781, :792)
if (!canonicallyEqualName(loserVideo.summaryMd, key)) {
  const dest = await loser.blob.tryGet(loser.p, key);   // only on this branch
  if (dest.ok || dest.reason === 'unreadable') throw …; // occupied by something we do not own
}
await loser.blob.put(loser.p, key, staged, 'text/markdown');   // unchanged
```

- **Common path costs nothing and has no window**: when the loser's row already names this address,
  no probe runs at all.
- **A legitimately re-keyed transfer still works**: when the bases diverged, the destination is a
  *fresh* address, so the probe finds it free and the write proceeds.
- **No atomicity is claimed.** Round-9 M4's "residual window, accepted" survives, but scoped honestly:
  the probe runs only on the uncommon branch, and the window it leaves is *identical to today's
  unconditional overwrite*. This is a strict improvement, not a fence.

And it deletes behavior 18b: there is nothing left for a byte-comparison to decide.

### R4 — one name-equality function, and it must be a SUBSET of the filesystem's relation

`[MEASURED]` on this volume the alias relation is **canonical equivalence ∪ case folding**:

| Probe | Result |
|---|---|
| NFD entry, NFC lookup | same file (`ino` equal) |
| `Å` U+212B vs `Å` U+00C5 (canonical singleton) | same file — so it is full canonical equivalence, not just NFC/NFD |
| `Ａ` U+FF21 vs `A` (compatibility only) | **different** files — so it is *not* NFKC |
| `Case.md` vs `case.md` | **same file** — the default macOS volume folds case |

So `a.normalize('NFC') === b.normalize('NFC')` is a **proper subset** of what the filesystem treats as
equal, and that asymmetry is the design rule:

> **Being narrower than the filesystem costs availability (a loud refusal). Being wider costs data.
> Never model the filesystem's relation exactly — it is a per-volume property, not a code property**
> (a case-sensitive APFS volume, or Linux CI, has a different one).

NFC-equality is safe in both directions for a *refusal* decision, and it is the rule
`findByNormalizedName` already ships. Lift it into one exported predicate and have
`findByNormalizedName` call it, so the codebase has **one** identity function for vault names.

### Which seam owns what

| Question | Owner | Why |
|---|---|---|
| *"Are these bytes the ones I meant?"* | `BlobStore` (`tryGet` + hash — already there) | content identity is the only identity a blob store has, on any backend |
| *"Is this address mine?"* | `sync-run` (the record) | ownership is a fact about the record, and the record is not in the store |
| *"Do these two names collide?"* | one vault-name module | a property of two strings — it needs no I/O at all |

This is the direct answer to the brief's option 1: **no new seam primitive, and the Supabase adapter
is never asked a question it has no answer to.** The `BlobStore` interface never learns about Unicode.

---

## 3. What it costs

| Change | Size | Notes |
|---|---|---|
| `LocalFsBlobStore.promote`: `renameSync` → `link` + `unlink` | ~4 lines | Also leaves the `_staging/<uuid>/` **directory** behind (`[MEASURED]` — `unlink` removes the file only); add the `rmdir`. v10 does not mention this |
| `InMemoryBlobStore.promote` must match | ~2 lines | contract test in the `tests/lib/storage/consistency.test.ts` style |
| `copyAdditiveVideo`: read-back + classify after `promote` | ~6 lines | one extra `get` per created video per sync — a network round trip on the cloud receiver |
| `transferClassA`: one added parameter + the R3 branch | ~6 lines | both call sites already hold the loser's record |
| `canonicallyEqualName` lifted, `findByNormalizedName` refactored onto it | ~5 lines | net **fewer** identity rules than today |
| §3.6 rewritten around 2 patterns instead of 4 writers | — | plus one line covering writer 3's model `delete` |
| Tests | ~6 | see below |
| **Not needed** | | no `BlobStore` method, no `readdir` at the seam, no Supabase-side answer to an aliasing question, no changes to §3.1–§3.5 |

**Adapters affected:** `LocalFsBlobStore`, `InMemoryBlobStore` (`promote` only). `SupabaseBlobStore`
is **unchanged** — it already conforms to R1.

**Tests** (replacing v10's 18/18b/18c/19):

| Behaviour | Kind |
|---|---|
| Additive: occupant is byte-identical under the aliasing form → **succeeds**, file untouched, stored name preserved (the crash-resume case v10 stalls on) | integration, real FS |
| Additive: occupant has different bytes → **refuses**, occupant intact | integration, real FS |
| Additive on the **cloud** receiver: final already holds different bytes → **refuses** instead of advertising `promoted` | integration |
| `promote` never overwrites — on all three adapters | contract |
| Class-A: loser's row names this address → **overwrites** (Class-A sync still works: round-8 H1 stays fixed) | integration |
| Class-A: loser's row names a different address and the destination is occupied → **refuses**; and unoccupied → **writes** | integration |
| Fixtures built with `.normalize('NFC'/'NFD')`, never two literals — v10's rule, kept verbatim | — |

**What it makes impossible:** clobbering a vault file the receiver's record does not own, on either
backend, *without ever knowing which normalization created it*; a receiver advertising `promoted` over
bytes it did not write; and a crash between `promote` and the row write permanently stranding a paid
artifact.

**What it deliberately does not do:** tell you which logical key an occupant was created under. That
question is unanswerable after the first overwrite (§0) and no writer needs it.

---

## 4. The strongest argument against my own recommendation

**Content identity is not key identity.** R2 treats "the destination already holds exactly these
bytes" as "already done". Two *different* logical keys can hold byte-identical content — the same
summary adopted under two filenames, say. R2 would then let the receiver's row advertise `promoted`
pointing at a file created for another key; if that other key's owner later rewrites or deletes it,
our row silently loses its blob. v10's `readdir` test would catch that case exactly, because it
recovers the pre-image. **My shape trades an exact credential for an approximate one.**

Three reasons I still recommend it, and one concession:

1. **The exact credential is exact about the wrong thing.** §0 measures that the stored name stops
   tracking ownership after the first overwrite-through-alias — and the protocol performs that
   overwrite itself. An exact answer to a question whose answer has decayed is worse than an
   approximate answer to the right one, because it is trusted.
2. **The failure modes are not symmetric.** R2's bad case is a *shared* file — no bytes are lost, and
   the divergence is visible on the next run. v10's bad cases are a *permanently stranded* video
   (§1.1b) and a *false refusal on the money path* (§0). Losing availability forever is worse than
   sharing an inode.
3. **The premise requires two summaries with identical bytes and different names.** Vault summary
   names are `${padSerial(serial)}_${slugify(title)}.md` `[VERIFIED: summary-handler.ts:96]`, so two
   *different videos* cannot alias without a serial collision — which the serial-coherence work exists
   to prevent. `[ASSUMPTION]` I did not re-verify the serial invariant this round; if it is weaker
   than I believe, this argument weakens, not the other two.
4. **Concession:** if that residual is judged unacceptable, the strengthening in R2 closes it *more*
   tightly than `readdir` — compare the occupant's `video_id` frontmatter, which names the owner
   directly instead of proxying it through a byte form. It costs one parse and stays
   adapter-independent. I would take it if the cost of a wrong "already" is judged to be money.

A second, smaller objection: **R3 adds a refusal where today there is none**, so a state that used to
sync (badly) now throws. It is per-video, caught by the caller, leaves no partial state, and
self-heals once the address is free — but it is a new operator-visible failure, and §3.6 should say
what an operator does about it.

---

## 5. Explicit verdict on v10's `readdir` + `link`/`unlink`

### `readdir` byte-comparison (behaviors 18b, 19's identity half, and the matching mutation row): **REPLACE.**

1. **It is stale by construction on the path that creates the divergence.** `[MEASURED]` overwriting
   through an alias preserves the old stored name, so after any Class-A transfer the entry carries the
   *loser's* original form while the content and the record are the winner's. The test then reports
   "a different logical key" for a video's own file, and refuses **every future Class-A transfer for
   it** — round-8 H1, re-entering through the credential chosen to prevent it (§0).
2. **It is a second, contradictory identity function for a namespace that already has one.**
   `findByNormalizedName` treats NFC-equal names as the same file, in production, on the same
   directory `[VERIFIED: serial-migrate-exec.ts:42]`.
3. **It answers a question no writer asks** once each writer uses what it already holds — the bytes
   (additive) or the record (Class-A). §1.2.
4. **It is adapter-specific**, so the rule it supports simply does not exist in the local→cloud
   direction of the same code path, where a real hole is open today (§2 R2, point 2).
5. **It is exact about a relation the spec models wrongly.** `[MEASURED]` the volume folds case as
   well as normalization, so a case-differing occupant is byte-unequal but the *same file* — and the
   same code changes meaning on a case-sensitive volume. The in-process test must be a deliberate
   *subset* of the filesystem's relation (R4), which a byte comparison is not reasoning about at all.

### `link` / `unlink` (behavior 18c's write half): **KEEP** — re-motivated.

Round-9 H2 chose `link` over `wx` for the right reason: it preserves `putStaged` → verify → `promote`,
so the read-back hash check survives. That reasoning stands. What changes is what the primitive is
*for*: not *"the occupancy test and the write in one operation"* (it is not an occupancy test — it
returns `EEXIST` and no identity), but **the no-clobber durable write that makes `promote` obey the
create-if-absent contract the codebase already documents** `[VERIFIED: model-store.ts:43]`. Same code,
honest motivation, and it now also covers the cloud receiver because Supabase already behaves that way.

Also keep, unchanged: `tryGet`'s *unreadable ⇒ occupied* rule (v10 is right that it answers a
different question), and the `.normalize()`-built-fixtures rule.

---

## 6. Blast radius on the rest of the spec

**§3.1–§3.5: no change.** Nothing here touches the encoder, `list()`, the serve predicate, or the
deletions. I read them for interaction and found none — the recommendation lives entirely in
`sync-run.ts` plus one adapter method.

**§5 behaviors:** 18 changes (refuse *on different bytes*, succeed on identical), 18b is **deleted**,
18c splits into "promote never overwrites" (contract, all adapters) + "the read-back hash verify still
runs", 19 keeps its `unreadable` half. Three rows are added: cloud-receiver refusal, Class-A
same-address overwrite, Class-A foreign-address refusal. Mutation rows follow the behaviours; the row
*"Use `tryGet` instead of `readdir` for the identity test"* is deleted with 18b, and
*"Replace `link` with `rename` in the additive promote"* becomes a **contract-level** mutation
(strictly stronger: it must go red on all three adapters).

**One scope addition to decide, not to skip:** writer 3's `delete(models/${base}.json)`
`[VERIFIED: sync-run.ts:475]` is a destructive, alias-resolved operation on a paid artifact with a
newly-non-ASCII `base`. Its risk is genuinely low (`base` is derived from the summary the transfer
just made authoritative, so the alias resolves to the same video's own model), but v10 does not say so
anywhere. One sentence in §3.6 stating it and why it is accepted — or `[the alternative]` extending R3's
record test to it — closes the last place where the writer enumeration is silently incomplete.

---

## Appendix — measurements

macOS 25.5.0, `/System/Volumes/Data` (APFS), Node v22.14.0, all scratch under
`/tmp/apfs-probe-s36/`, removed after the run. No Supabase connection was needed or made.

**Probe 1 — the alias relation and what overwriting does to the stored name**

```
1 existsSync(NFC) after creating NFD:                     true
1 readdir:                                                ["<NFD>"]          ← normalization-preserving
2 linkSync(NFC) ->                                        EEXIST
2 wx(NFC) ->                                              EEXIST
3 after renameSync(src -> NFC): readdir =                 ["<NFD>"]          ← NAME PRESERVED
3 content now:                                            BBB                ← BYTES REPLACED
4 realpath(NFC)===realpath(NFD):                          false              ← realpath is NOT a credential
5 existsSync(case.md) after Case.md:                      true               ← case folds too
6 existsSync(U+212B) after creating U+00C5:               true               ← full canonical equivalence
7 existsSync(A.md) after fullwidth Ａ.md:                  false              ← NOT compatibility (NFKC)
8 ino equal for both forms:                               true
```

**Probe 2 — the recommended protocol, run against real APFS**

```
CASE 1 resume (occupant NFD, write NFC, same bytes):  OK(wrote-or-already)
   file survives, stored name still NFD: ["<NFD>"] content: BODY-A
CASE 2 foreign (occupant NFC, write NFD, diff bytes): REFUSE(foreign-or-divergent occupant)
   victim untouched: SOMEONE-ELSE   stored name: ["<NFC>"]
CASE 3 fresh   (write NFD into empty dir):            OK   stored: ["<NFD>"]
   staging dir left behind by link+unlink: ["4bf352ed-…"]        ← the rmdir §3 lists
CASE 4 case-fold: link 003_alpha.md over 003_Alpha.md -> EEXIST
   | readdir byte-match for 003_alpha.md: false                  ← §5 reason 5
```

Both probes are self-contained Node scripts; the exact source is reproducible from this document's
descriptions and was run from the coordinator shell, not committed.
