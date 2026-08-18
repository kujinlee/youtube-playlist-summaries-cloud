---
status: accepted
---

# Logical keys are Unicode, physical keys are ASCII, and the storage seam owns the mapping

A video titled `한국어 강의` was ingested, summarised by Gemini — **paid for** — and then lost, because
`lib/slugify.ts` preserves non-ASCII and Supabase Storage rejects a non-ASCII object key with
`400 InvalidKey`. The money moved before the failure. That is backlog **#36**, the last launch blocker.

**The decision: the BlobStore seam translates.** Every caller above `SupabaseBlobStore` speaks
**logical** keys — Unicode, exactly as the title produced them. Everything Storage sees is a
**physical** key in `[A-Za-z0-9._-]`. `objectKey`, `deletePrefix` and `list` are the only three places
that know both alphabets, and `encodeSegment` (`lib/storage/supabase/encode-segment.ts`) is the only
function that converts:

```
SAFE segment within LIMIT  →  itself, byte-identical
anything else              →  <head≤32>=h<22 base64url digest chars><ext>
```

No caller changes. No vault filename changes. No object already in the bucket is renamed.

## The three things that make this work, which are not obvious

**1. The encoding is one-way, and that is legal only because `list()` never inverts it.**

A SHA-256 digest cannot be decoded back to a Korean title, which would normally disqualify it as a
filename scheme — you could not enumerate a directory and recover the logical names. It is sound here
because `list()` **re-attaches the caller's own logical prefix** rather than decoding what Storage
returned. The caller already knows the prefix it asked for; only the *remainder* has to be readable,
and every remainder in this codebase is a generated `{sectionId}.r{V}.md` leaf. That is premise **P4**,
and `list()` throws rather than guesses if a remainder ever arrives carrying an `=h` marker.

**2. It hashes `utf16le`, not `utf8`, and this is a money-safety property.**

`Buffer.from(s, 'utf8')` maps every **unpaired surrogate** to `U+FFFD`. So `'x\uD840'` and `'x\uD850'` —
two genuinely different strings — would hash to the same physical key, and one video's paid summary
would silently overwrite another's. This is reachable, not theoretical: `slugify`'s slice cuts UTF-16
code units and can orphan a surrogate half. `utf16le` preserves the code units verbatim. Asserted in
`tests/lib/storage/encode-segment.test.ts`.

**3. The KEY is encoded; the OWNER PREFIX is not — and ADR-0008 depends on that.**

`objectKey` encodes only `key`, never `p.id` or `p.indexKey`. Both the encoded and unencoded forms of
any key therefore stay under the same `<owner-id>/<index-key>/` root, so the storage grant in
`supabase/migrations/0007_storage_and_rpcs.sql:12-15` — which matches on the **first** path segment —
covers them identically.

[ADR-0008](0008-serve-money-guard-depends-on-storage-grant-granularity.md) **survives unchanged.** Its
serve-path money guard is corroboration-by-ordering: reading the summary markdown successfully is
evidence that the magazine model is readable too, valid only while one grant covers both. Encoding the
owner prefix would have split that grant and silently dissolved the guard — a 6¢→12¢ double charge of
exactly the kind that ADR is written about. It does not, and that is deliberate rather than incidental.

## Premises, and what would falsify each

Copied from the spec (`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` §1.1),
which states them as premises because seven review rounds were spent on them stated as facts.

| # | Premise | Provenance | Falsified by |
|---|---|---|---|
| P1 | Storage rejects every non-ASCII object key | **MEASURED** (§2.1, 3 rounds) | any non-ASCII key uploading `ok` |
| P2 | Storage's limit is 255 per path **segment**, not per path | **MEASURED** (§2.2, re-derived twice) | a path >255 total with all segments ≤255 being *rejected* |
| P3 | Every **write** reaches Storage through `SupabaseBlobStore` | **QUOTED** — the only non-test write call site | a second non-test **write** call site |
| P4 | `list()` never needs to invert the encoding | **QUOTED** — all 3 callers pass `dig/${base}/` and read `{sectionId}.r{V}.md` leaves | a caller consuming a leaf it did not supply the prefix for |
| P5 | The serve guard's requirement is *single path component*, not ASCII | **QUOTED** — its own docstring; 2 callers | a downstream consumer that breaks on a non-ASCII but separator-free key |
| P6 | No URL is built from the key | **MEASURED** (grep, §3.4) | a URL built by string interpolation from `summaryMd`/`base` |
| P7 | The key reaching HTML is escaped | **QUOTED** — `render.ts:106`, `:114`, both via `esc()` | an unescaped interpolation |
| P8 | A vault filename is always a single path component | **Structural** — POSIX forbids `/` in a component | n/a |

P3's falsifier has already fired once and the premise survived: a gitignored read-only ops script
holds a second `client.storage.from(`, but only `download`s. Recorded rather than quietly reworded.

## The user's three decisions, which bound the design

Settled 2026-08-14 and not reopened:

- **①  The vault wins.** Local filenames keep their Unicode. The cloud adapts to the vault, never the
  reverse — which is why `slugify` is not ASCII-ified (declined, spec §6.3) and why the local and
  in-memory blob stores stay pure identity.
- **②  No refund, no ledger reconciliation.** The ~156¢ already spent on unstorable summaries stays
  recorded as spent.
- **③  An unreadable vault filename is not acceptable.** This killed the earlier `videoId`-based
  repair, which produced filenames like `003_dQw4w9WgXcQ.md`.

## No migration — and the shape of that claim

The encoder changes an existing key iff it is `¬SAFE` or over `LIMIT`. The length half is vacuous
(such a key was rejected at upload and is not in the bucket). The charset half is a subset of
*rejected* **except for five characters Storage accepts and `SAFE` excludes: space, `(`, `)`, `+`, `=`.**

The gate ran against prod as `claude_ro`, read-only, on **2026-08-14**: 19 objects, **0** rows outside
`SAFE`, exit 0.

> ⚠ **This is a claim about the bucket on a date, not a standing invariant.** Every ingest since adds
> objects that check never saw. If one carries a space or a bracket, the encoder computes a *different*
> physical key for an object that already exists and the summary behind it becomes unreachable. The
> gate is therefore **re-run as a merge step**, not treated as settled — a check that runs once and is
> never re-run is a decision with no falsifier.

## Consequences

- One function converts alphabets. A second one would be a defect, not a feature.
- `list()` is now the only method that can throw on a *shape* it cannot name. It fails loudly instead
  of returning a key that would 404 on the next `get`.
- The local and in-memory adapters remain **identity**. Divergence between them and the Supabase
  adapter is the failure mode to watch for, and behavior 13 asserts it.
- Non-ASCII titles beyond Korean — Japanese, Cyrillic, accented Latin in both NFC and NFD, emoji — are
  covered by the same change. The measured defect was always far wider than "Korean".
