# Task 1 — Supabase Storage put visibility-atomicity preflight (gate for ADR 0003 / Task 8)

## What was tested

`docs/adr/0003-cloud-pdf-serve-side-not-a-job.md` designs the cloud summary PDF cache as a
**bare atomic `blobStore.put`** to a content-addressed key, with **no** `committed → promoted`
staging. That design is safe only if `SupabaseBlobStore.put` (`upload(..., { upsert: true })`)
is **visibility-atomic**: a concurrent reader must observe either the whole old object, the
whole new object, or absent — never a torn/partial mix.

This preflight empirically verifies that assumption against a real local Supabase Storage
stack before Task 8 (the PDF serve+cache route) is implemented.

## Test

`tests/integration/pdf-put-atomicity.test.ts` — verbatim from the Task 1 brief:

- Seed a real user + playlist via `newUser`/`signInAs`/`seedPlaylist` (real RLS-scoped
  session client, not the admin client).
- Resolve a real `SupabaseBlobStore` via `getStorageBundle({ supabaseClient })` /
  `getPrincipalFromSession` with `STORAGE_BACKEND=supabase`.
- Write an initial 512 KB object (`0xaa` bytes) to `pdfs/atomicity-probe.bin`.
- Fire 8 concurrent `put` calls (alternating 512 KB buffers of `0xaa` / `0xbb`) **interleaved**
  with 8 concurrent `get` calls on the same key, via `Promise.all`.
- For every non-null read: assert the buffer is the full 512 KB, every byte in it is identical
  (homogeneous), and that byte is either `0xaa` or `0xbb` — i.e. never a mix of both buffers,
  never a truncated length.

## Exact command run

```
npm run test:integration -- pdf-put-atomicity
```

which expands to `jest --config jest.integration.config.ts --runInBand pdf-put-atomicity`,
loading `.env.test.local` (local Supabase: API 54321 / DB 54322 / Storage) via
`tests/integration/setup.ts`, same invocation convention as sibling `*-cloud` integration
tests (e.g. `html-download.test.ts`).

## Result

**PASS.** Ran 3 consecutive times (no flake):

```
Test Suites: 1 passed, 1 total
Tests:       1 passed, 1 total
Snapshots:   0 total
Time:        ~0.9s
Ran all test suites matching pdf-put-atomicity.
```

Zero torn reads across 8 concurrent overwrites x 8 concurrent reads (64 read/write
interleavings total across 3 runs). Every observed read was either the complete `0xaa` buffer,
the complete `0xbb` buffer, or absent (`null`) — never partial, never mixed.

**Sanity check on the test itself:** to confirm the assertions were exercising real data (not
a vacuous/skipped pass), the final byte-value assertion was temporarily inverted
(`toBe(false)` instead of `toBe(true)`) and re-run — it failed with `Received: true`, proving
the test reads actual bytes from real Supabase Storage on each run. The file was restored to
its original (verbatim brief) contents afterward; `git diff` on the test file is empty.

## Conclusion

The bare-put content-addressed cache design in ADR 0003 / Task 8 is **sound to proceed as
written** — no staging-key + atomic manifest pointer fallback is needed. Supabase Storage's
`upload(..., { upsert: true })` is visibility-atomic under concurrent overwrite+read on this
local stack.

**Caveat:** this verifies the **local** Supabase Storage stack (Docker-hosted, backed by the
storage-api server over local disk/S3-compatible backend). Production Supabase Storage rests
on real S3 (or S3-compatible) semantics, where a single PUT is documented as atomic
(no reader ever sees a partial object mid-upload) — this local result is consistent with, but
is not a substitute for, that production guarantee. If the production storage backend ever
differs from S3-object-PUT semantics, this assumption should be re-verified there.

## Gate verdict

**PASS → Task 8 proceeds** with the bare-put/content-addressed cache design, no re-plan needed.
