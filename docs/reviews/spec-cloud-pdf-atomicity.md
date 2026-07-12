# Task 1 — Supabase Storage put visibility-atomicity preflight (gate for ADR 0003 / Task 8)

## What was tested

`docs/adr/0003-cloud-pdf-serve-side-not-a-job.md` designs the cloud summary PDF cache as a
**bare atomic `blobStore.put`** to a content-addressed key, with **no** `committed → promoted`
staging. That design is safe only if `SupabaseBlobStore.put` (`upload(..., { upsert: true })`)
is **visibility-atomic**: a concurrent reader must observe either the whole old object, the
whole new object, or absent — never a torn/partial mix.

This preflight empirically probes that assumption against a real local Supabase Storage stack
before Task 8 (the PDF serve+cache route) is implemented. It is a probe of a fixed number of
overlapping operations, not an exhaustive proof — see "Precisely what this proves" below for
the exact, non-overclaimed scope.

## Test

`tests/integration/pdf-put-atomicity.test.ts` — strengthened in response to Codex review round 1
(`docs/reviews/task-cloud-pdf-1-codex.md`), which found the original version could pass
**vacuously**: it treated any read error as benign "absent" (B1), and never proved a read
actually overlapped an in-flight overwrite or observed more than one written generation (B2).

- Seed a real user + playlist via `newUser`/`signInAs`/`seedPlaylist` (real RLS-scoped session
  client, not the admin client).
- Resolve a real `SupabaseBlobStore` via `getStorageBundle({ supabaseClient })` /
  `getPrincipalFromSession` with `STORAGE_BACKEND=supabase`.
- Seed a 512 KB object (`A` = all `0xaa` bytes) at `pdfs/atomicity-probe.bin`. From this point on,
  the object always exists — a `get()` returning `null` is never benign absence.
- Run 14 rounds. Each round fires **one** `put` that flips the written value (round 0 → `B`
  = all `0xbb`, round 1 → `A`, alternating every round) together with 4 `get`s, all created in
  the same synchronous tick and awaited together via a single `Promise.all` — i.e. the write and
  that round's reads are genuinely in flight concurrently, not a sequenced write-then-read.
- For **every** read result across all 14 rounds (56 reads total):
  - assert it is **not null** (a null read here is a torn read that surfaced as a Storage error,
    not absence — the object always exists after the seed);
  - assert the buffer is the full 512 KB (never truncated);
  - assert every byte in the buffer equals its first byte (**homogeneous** — this is the tear
    detector: a buffer mixing bytes from `A` and `B` fails here);
  - assert that byte is exactly `0xaa` or `0xbb` (a valid generation, nothing else).
- Track the **set** of first-byte values seen across all 56 reads. After the loop, assert the set
  contains **both** `0xaa` and `0xbb`. Because the written value alternates every round and reads
  happen throughout the run, this deterministically proves overwrites became visible to a
  concurrent reader and that reads observed multiple generations — without depending on catching
  a mid-write tear at exactly the right instant (which would be flaky to rely on).
- Cleanup (`blobStore.delete`) runs in a `finally` so the probe object is removed even if an
  assertion fails.

## Exact command run

```
npm run test:integration -- pdf-put-atomicity
```

which expands to `jest --config jest.integration.config.ts --runInBand pdf-put-atomicity`,
loading `.env.test.local` (local Supabase: API 54321 / DB 54322 / Storage) via
`tests/integration/setup.ts`, same invocation convention as sibling `*-cloud` integration tests
(e.g. `html-download.test.ts`).

## Result

**PASS.** Ran repeatedly with no flake (8 total runs across the fix-and-verify session: 3 initial
runs of the strengthened test, plus 5 further runs during the sanity-check procedure below).

```
Test Suites: 1 passed, 1 total
Tests:       1 passed, 1 total
Snapshots:   0 total
Time:        ~1.6-1.9s
Ran all test suites matching pdf-put-atomicity.
```

Every one of the 56 reads per run was non-null, full-length, homogeneous, and a valid generation
byte — never partial, never a mix of `A` and `B`.

**Sanity checks on the test itself** (to confirm the assertions exercise real data, not a vacuous
pass — each temporarily edited, re-run, then reverted; `git diff` on the test file is clean
afterward):
- Inverted both `observedValues.has(0xaa)`/`has(0xbb)` assertions to `toBe(false)` → failed with
  `Expected: false, Received: true` on the `0xaa` line, proving at least one generation really was
  observed as a set member (not a default/empty value).
- Inverted `observedValues.has(0xaa)` alone to `toBe(false)` → failed with
  `Expected: false, Received: true`, proving `0xaa` specifically was observed after the seed
  (i.e. reads did see the original generation surviving past a subsequent overwrite window, or a
  round that wrote `A`).
- Inverted `observedValues.has(0xbb)` alone to `toBe(false)` → failed with
  `Expected: false, Received: true`, proving `0xbb` specifically was observed — i.e. a post-seed
  overwrite became visible to a reader during the concurrent-dispatch run. (The set retains no
  round/timing information, so this does not localize the observation to a specific round's
  in-flight write — see "Precisely what this proves.")

## Precisely what this proves

- Every read issued **after** the object was seeded returned non-null data (no torn read
  surfaced as a Storage error, and no read observed an absent object).
- Every read's buffer was **whole** (full expected length) and **homogeneous** (no byte-level
  mixing of the two written generations) — i.e. no torn/partial object was ever observed.
- Every read's buffer was a **valid generation** (`0xaa` or `0xbb`), never any other value.
- Overwrites **propagated to concurrent readers**: across 14 rounds of alternating writes issued
  concurrently with reads (same-tick dispatch + a single `Promise.all` per round), **both**
  generations (`0xaa` and `0xbb`) were observed — proving reads saw fresh post-seed overwrites,
  not just the seed value surviving untouched. This is **generation coverage**, not a per-read
  timing/overlap proof: because each round's pre-value also alternates, both generations would
  appear from alternation alone, so this set result does not by itself establish that any single
  read's server-side processing overlapped a write's commit window (see the disclaimer below).

This is what the test demonstrates — nothing more. **The atomicity evidence is the per-read
homogeneity / whole-length check never failing** across all 56 reads issued under concurrent
dispatch — that is the tear detector; the both-generations set check only establishes generation
coverage, not atomicity. It does not claim a specific count of "interleavings" (there is no way to
observe from the client which reads landed truly mid-write at the storage-server level; the
both-generations result is a value-based existence proof, not a timing measurement), and it does
not claim exhaustive coverage of every possible race window. The tear detector catches an
**observable** torn read (byte-level mixing of `A`/`B`, or truncation); a hypothetical backend
that was internally non-atomic but always returned a fully homogeneous old *or* new buffer would
be indistinguishable from atomic here — but by definition that is not an observable torn read,
which is exactly the property Task 8's cache depends on.

## Scope and caveat (read before treating this as a production guarantee)

**This verifies the local Supabase Storage stack only** — the Dockerized `storage-api` server
used by the local dev/test stack (see `docker ps` output: `supabase_storage_...`), run over
whatever backing store that container uses locally. It is **not** an independent verification of
production Supabase Storage's semantics.

Production Supabase Storage is documented by the vendor as backed by S3 (or S3-compatible)
semantics, where a single object PUT is described as atomic (a reader never sees a partial object
mid-upload). **This test does not independently verify that production claim** — it is a
separate, larger, differently-operated system, and this preflight's PASS result on the local
stack is not a substitute for that vendor guarantee. If the production storage backend's
behavior is ever in question, or if it's confirmed to diverge from S3-object-PUT semantics, this
assumption must be re-verified directly against production (or the relevant staging/vendor
environment), not re-inferred from this local result.

## Gate verdict

**PASS on the local stack, under the strengthened (non-vacuous) assertions above** → Task 8
proceeds with the bare-put/content-addressed cache design described in ADR 0003, no
staging-key + atomic manifest pointer fallback required — subject to the local-only scope caveat
above.
